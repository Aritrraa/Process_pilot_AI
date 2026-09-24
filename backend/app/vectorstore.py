"""
VectorStore — Embedding + Vector Database abstraction for ProcessPilot AI.

Restored from the original lightweight architecture (pre-7cf961b).
Uses external embedding APIs (OpenAI / Gemini) — NO local PyTorch models.
The CEOAgent is responsible for resolving the correct embedding provider/key
before calling SearchAgent, which passes them through to this module.
"""

import hashlib
import logging
from typing import Any

import google.generativeai as genai
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings

logger = logging.getLogger("processpilot.vectorstore")

EMBEDDING_DIMENSION = 768


class EmbeddingProvider:
    """
    Handles embeddings via external APIs (OpenAI / Gemini).
    Falls back to deterministic hash-based mock vectors ONLY in development.
    Mock embeddings are blocked in production to prevent silent RAG corruption.

    The CEOAgent resolves provider + key before passing them here.
    """

    def __init__(self, api_key: str | None = None, llm_provider: str = "simulation"):
        self.api_key = api_key
        self.llm_provider = llm_provider
        if api_key and llm_provider == "gemini":
            genai.configure(api_key=api_key)

    def get_embedding(self, text: str) -> list[float]:
        if not text:
            text = "empty"

        if not self.api_key or self.llm_provider == "simulation":
            return self._local_mock_embedding(text)

        if self.llm_provider == "openai":
            try:
                @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
                def _call_openai():
                    from openai import OpenAI
                    client = OpenAI(api_key=self.api_key)
                    response = client.embeddings.create(
                        input=[text],
                        model="text-embedding-3-small",
                        dimensions=EMBEDDING_DIMENSION
                    )
                    return response.data[0].embedding
                return _call_openai()
            except Exception as e:
                logger.warning(f"OpenAI embedding failed after retries, using local mock fallback: {e}")
                return self._local_mock_embedding(text)

        elif self.llm_provider == "gemini":
            try:
                @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
                def _call_gemini():
                    response = genai.embed_content(
                        model="models/text-embedding-004",
                        content=text,
                        task_type="retrieval_document"
                    )
                    return response['embedding']
                return _call_gemini()
            except Exception as e:
                logger.warning(f"Gemini embedding failed after retries, using local mock fallback: {e}")
                return self._local_mock_embedding(text)
        else:
            return self._local_mock_embedding(text)

    def _local_mock_embedding(self, text: str) -> list[float]:
        """Deterministic hash-based 768-dim vector for development/testing only."""
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(
                "CRITICAL: Mock embeddings are blocked in production. "
                "A valid OpenAI or Gemini embedding API key must be configured. "
                "Set OPENAI_API_KEY or GEMINI_API_KEY as an environment variable, "
                "or provide a valid infrastructure embedding key via INFRA_EMBEDDING_API_KEY."
            )
        state = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % 10000
        rng = np.random.default_rng(state)
        vector = rng.standard_normal(EMBEDDING_DIMENSION).tolist()
        norm = sum(x**2 for x in vector)**0.5
        return [x / norm for x in vector] if norm > 0 else vector


class BaseVectorStore:

    def add_chunks(self, document_id: int, chunks: list[dict[str, Any]], api_key: str | None = None, llm_provider: str = "simulation"):
        raise NotImplementedError()

    def search(self, query: str, limit: int = 5, department_id: int | None = None, api_key: str | None = None, llm_provider: str = "simulation") -> list[dict[str, Any]]:
        raise NotImplementedError()

    def delete_document_chunks(self, document_id: int):
        raise NotImplementedError()


class ChromaVectorStore(BaseVectorStore):
    """Local ChromaDB store — used only when running with SQLite (development)."""

    def __init__(self):
        self.client = None

    def _init_client(self):
        if self.client is None:
            import chromadb
            self.client = chromadb.Client()

    def add_chunks(self, document_id: int, chunks: list[dict[str, Any]], api_key: str | None = None, llm_provider: str = "simulation"):
        if not chunks:
            return
        self._init_client()
        provider = EmbeddingProvider(api_key, llm_provider)
        department_id = chunks[0].get('metadata', {}).get('department_id')
        collection_name = f"dept_{department_id}" if department_id else "global"
        collection = self.client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

        BATCH_SIZE = 50
        for batch_start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[batch_start:batch_start + BATCH_SIZE]
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            for chunk in batch:
                chunk_text = chunk['text']
                chunk_id = f"doc_{document_id}_chunk_{chunk['index']}"
                ids.append(chunk_id)
                documents.append(chunk_text)
                embeddings.append(provider.get_embedding(chunk_text))
                meta = chunk.get('metadata', {})
                meta.update({"document_id": document_id, "chunk_index": chunk['index']})
                metadatas.append(meta)
            collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def search(self, query: str, limit: int = 5, department_id: int | None = None, api_key: str | None = None, llm_provider: str = "simulation") -> list[dict[str, Any]]:
        self._init_client()
        provider = EmbeddingProvider(api_key, llm_provider)
        query_embedding = provider.get_embedding(query)
        formatted_results = []
        collections = []
        if department_id is not None:
            try:
                collections.append(self.client.get_collection(f"dept_{department_id}"))
            except Exception:
                pass
        try:
            collections.append(self.client.get_collection("global"))
        except Exception:
            pass

        for collection in collections:
            try:
                results = collection.query(query_embeddings=[query_embedding], n_results=limit)
                if results and results['documents'] and results['documents'][0]:
                    for i in range(len(results['ids'][0])):
                        formatted_results.append({
                            "id": results['ids'][0][i],
                            "document": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                            "distance": results['distances'][0][i] if results.get('distances') else 0.0
                        })
            except Exception:
                pass

        formatted_results.sort(key=lambda x: x["distance"])
        return formatted_results[:limit]

    def delete_document_chunks(self, document_id: int):
        if not self.client:
            return
        for col in self.client.list_collections():
            try:
                col.delete(where={"document_id": document_id})
            except Exception:
                pass


class PGVectorStore(BaseVectorStore):
    """Native PostgreSQL vector store using pgvector via SQLAlchemy.

    Uses a SYNCHRONOUS session because all methods run inside asyncio.to_thread
    (background threads) — never directly on the async event loop.
    """

    def __init__(self):
        from .database import SyncSessionLocal
        self.SessionLocal = SyncSessionLocal

    def add_chunks(self, document_id: int, chunks: list[dict[str, Any]], api_key: str | None = None, llm_provider: str = "simulation"):
        if not chunks:
            return

        from .models import DocumentEmbedding
        provider = EmbeddingProvider(api_key, llm_provider)

        department_id = chunks[0].get('metadata', {}).get('department_id')

        db = self.SessionLocal()
        try:
            for chunk in chunks:
                chunk_text = chunk['text']
                chunk_id = f"doc_{document_id}_chunk_{chunk['index']}"
                emb = provider.get_embedding(chunk_text)

                meta = chunk.get('metadata', {})

                doc_emb = DocumentEmbedding(
                    id=chunk_id,
                    document_id=document_id,
                    department_id=department_id,
                    chunk_index=chunk['index'],
                    text=chunk_text,
                    embedding=emb,
                    metadata_json=meta
                )
                db.merge(doc_emb)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save pgvector embeddings: {e}")
            raise
        finally:
            db.close()

    def search(self, query: str, limit: int = 5, department_id: int | None = None, api_key: str | None = None, llm_provider: str = "simulation") -> list[dict[str, Any]]:
        from .models import DocumentEmbedding
        provider = EmbeddingProvider(api_key, llm_provider)
        query_embedding = provider.get_embedding(query)

        db = self.SessionLocal()
        try:
            # Query using pgvector cosine distance operator (<=>)
            q = db.query(DocumentEmbedding).order_by(
                DocumentEmbedding.embedding.cosine_distance(query_embedding)
            )

            if department_id is not None:
                q = q.filter(DocumentEmbedding.department_id == department_id)

            results = q.limit(limit).all()

            formatted_results = []
            for r in results:
                distance = r.embedding.cosine_distance(query_embedding) if hasattr(r.embedding, 'cosine_distance') else 0.0

                formatted_results.append({
                    "id": r.id,
                    "document": r.text,
                    "metadata": r.metadata_json,
                    "distance": distance
                })
            return formatted_results
        finally:
            db.close()

    def delete_document_chunks(self, document_id: int):
        from .models import DocumentEmbedding
        db = self.SessionLocal()
        try:
            db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == document_id).delete()
            db.commit()
        finally:
            db.close()


class VectorStoreManager:
    def __init__(self):
        self.store = None

        # Check if we are running in Postgres mode
        is_postgres = "postgresql" in settings.DATABASE_URL or "postgres" in settings.DATABASE_URL

        if is_postgres:
            # Native PostgreSQL vector store using pgvector
            self.store = PGVectorStore()

        if not self.store:
            self.store = ChromaVectorStore()

    def add_chunks(self, document_id: int, chunks: list[dict[str, Any]], api_key: str | None = None, llm_provider: str = "simulation"):
        self.store.add_chunks(document_id, chunks, api_key, llm_provider)

    def search(self, query: str, limit: int = 5, department_id: int | None = None, api_key: str | None = None, llm_provider: str = "simulation") -> list[dict[str, Any]]:
        return self.store.search(query, limit, department_id, api_key, llm_provider)

    def delete_document_chunks(self, document_id: int):
        self.store.delete_document_chunks(document_id)


vector_store_manager = VectorStoreManager()
