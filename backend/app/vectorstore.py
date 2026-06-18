import os
import numpy as np
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import chromadb
import hashlib
from .config import settings

class EmbeddingProvider:
    """
    Handles embeddings. Falls back to basic local numeric simulator 
    if Gemini/OpenAI API key is not configured or fails.
    """
    def __init__(self, api_key: Optional[str] = None, llm_provider: str = "simulation"):
        self.api_key = api_key
        self.llm_provider = llm_provider
        if api_key and llm_provider == "gemini":
            genai.configure(api_key=api_key)

    def get_embedding(self, text: str) -> List[float]:
        def local_mock_embedding():
            # Stable hash-based deterministic vector generator (768 dimensions)
            state = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % 10000
            rng = np.random.default_rng(state)
            vector = rng.standard_normal(768).tolist()
            # Normalize vector
            norm = sum(x**2 for x in vector)**0.5
            return [x/norm for x in vector] if norm > 0 else vector

        if not self.api_key or self.llm_provider == "simulation":
            return local_mock_embedding()
            
        if self.llm_provider == "openai":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)
                response = client.embeddings.create(
                    input=[text],
                    model="text-embedding-3-small",
                    dimensions=768
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"OpenAI embedding failed, using local simulator fallback: {e}")
                return local_mock_embedding()
                
        elif self.llm_provider == "gemini":
            try:
                response = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document"
                )
                return response['embedding']
            except Exception as e:
                print(f"Gemini embedding failed, using local simulator fallback: {e}")
                return local_mock_embedding()
        else:
            return local_mock_embedding()

class BaseVectorStore:
    def add_chunks(self, document_id: int, chunks: List[Dict[str, Any]], api_key: Optional[str] = None, llm_provider: str = "simulation"):
        raise NotImplementedError()

    def search(self, query: str, limit: int = 5, department_id: Optional[int] = None, api_key: Optional[str] = None, llm_provider: str = "simulation") -> List[Dict[str, Any]]:
        raise NotImplementedError()

    def delete_document_chunks(self, document_id: int):
        raise NotImplementedError()

class ChromaVectorStore(BaseVectorStore):
    def __init__(self):
        self.client = None
        self.collection = None

    def _init_client(self):
        if self.client is None:
            os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
            self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            self.collection = self.client.get_or_create_collection(
                name="processpilot_chunks"
            )

    def add_chunks(self, document_id: int, chunks: List[Dict[str, Any]], api_key: Optional[str] = None, llm_provider: str = "simulation"):
        self._init_client()
        provider = EmbeddingProvider(api_key, llm_provider)
        
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        for chunk in chunks:
            chunk_text = chunk['text']
            chunk_id = f"doc_{document_id}_chunk_{chunk['index']}"
            
            ids.append(chunk_id)
            documents.append(chunk_text)
            embeddings.append(provider.get_embedding(chunk_text))
            
            # Enrich metadata
            meta = chunk.get('metadata', {})
            meta.update({
                "document_id": document_id,
                "chunk_index": chunk['index']
            })
            metadatas.append(meta)
            
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def search(self, query: str, limit: int = 5, department_id: Optional[int] = None, api_key: Optional[str] = None, llm_provider: str = "simulation") -> List[Dict[str, Any]]:
        self._init_client()
        provider = EmbeddingProvider(api_key, llm_provider)
        query_embedding = provider.get_embedding(query)
        
        where_filter = None
        if department_id is not None:
            where_filter = {"department_id": department_id}
            
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter
        )
        
        formatted_results = []
        if not results or not results['documents']:
            return []
            
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "document": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if 'distances' in results else 0.0
            })
            
        return formatted_results

    def delete_document_chunks(self, document_id: int):
        self._init_client()
        self.collection.delete(
            where={"document_id": document_id}
        )

class PineconeVectorStore(BaseVectorStore):
    def __init__(self):
        try:
            from pinecone import Pinecone, ServerlessSpec
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index_name = settings.PINECONE_INDEX
            
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            if self.index_name not in existing_indexes:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=768,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
            self.index = self.pc.Index(self.index_name)
        except Exception as e:
            print(f"Failed to initialize Pinecone vector store: {e}")
            self.index = None

    def add_chunks(self, document_id: int, chunks: List[Dict[str, Any]], api_key: Optional[str] = None, llm_provider: str = "simulation"):
        if not self.index:
            raise RuntimeError("Pinecone is not initialized.")
        provider = EmbeddingProvider(api_key, llm_provider)
        vectors = []
        for chunk in chunks:
            chunk_text = chunk['text']
            chunk_id = f"doc_{document_id}_chunk_{chunk['index']}"
            emb = provider.get_embedding(chunk_text)
            meta = chunk.get('metadata', {})
            meta.update({
                "document_id": document_id,
                "chunk_index": chunk['index'],
                "text": chunk_text
            })
            vectors.append((chunk_id, emb, meta))
        self.index.upsert(vectors=vectors)

    def search(self, query: str, limit: int = 5, department_id: Optional[int] = None, api_key: Optional[str] = None, llm_provider: str = "simulation") -> List[Dict[str, Any]]:
        if not self.index:
            return []
        provider = EmbeddingProvider(api_key, llm_provider)
        query_embedding = provider.get_embedding(query)
        
        filter_dict = {}
        if department_id is not None:
            filter_dict["department_id"] = department_id
            
        results = self.index.query(
            vector=query_embedding,
            top_k=limit,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        formatted_results = []
        for match in results.get('matches', []):
            metadata = match.get('metadata', {})
            text = metadata.pop('text', '')
            formatted_results.append({
                "id": match['id'],
                "document": text,
                "metadata": metadata,
                "distance": match.get('score', 0.0)
            })
        return formatted_results

    def delete_document_chunks(self, document_id: int):
        if self.index:
            self.index.delete(filter={"document_id": document_id})

class QdrantVectorStore(BaseVectorStore):
    def __init__(self):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            self.collection_name = "processpilot_chunks"
            
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"Failed to initialize Qdrant vector store: {e}")
            self.client = None

    def add_chunks(self, document_id: int, chunks: List[Dict[str, Any]], api_key: Optional[str] = None, llm_provider: str = "simulation"):
        if not self.client:
            raise RuntimeError("Qdrant is not initialized.")
        from qdrant_client.models import PointStruct
        provider = EmbeddingProvider(api_key, llm_provider)
        points = []
        for chunk in chunks:
            chunk_text = chunk['text']
            chunk_id_int = hash(f"doc_{document_id}_chunk_{chunk['index']}") & 0xffffffffffffffff
            emb = provider.get_embedding(chunk_text)
            meta = chunk.get('metadata', {})
            meta.update({
                "document_id": document_id,
                "chunk_index": chunk['index'],
                "text": chunk_text
            })
            points.append(PointStruct(id=chunk_id_int, vector=emb, payload=meta))
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query: str, limit: int = 5, department_id: Optional[int] = None, api_key: Optional[str] = None, llm_provider: str = "simulation") -> List[Dict[str, Any]]:
        if not self.client:
            return []
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        provider = EmbeddingProvider(api_key, llm_provider)
        query_embedding = provider.get_embedding(query)
        
        query_filter = None
        if department_id is not None:
            query_filter = Filter(
                must=[
                    FieldCondition(key="department_id", match=MatchValue(value=department_id))
                ]
            )
            
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            query_filter=query_filter
        )
        
        formatted_results = []
        for hit in results:
            payload = hit.payload or {}
            text = payload.pop('text', '')
            formatted_results.append({
                "id": str(hit.id),
                "document": text,
                "metadata": payload,
                "distance": hit.score
            })
        return formatted_results

    def delete_document_chunks(self, document_id: int):
        if self.client:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="document_id", match=MatchValue(value=document_id))
                    ]
                )
            )

class VectorStoreManager:
    def __init__(self):
        self.store = None
        db_type = settings.VECTOR_DB_TYPE.lower()
        if db_type == "pinecone" and settings.PINECONE_API_KEY:
            self.store = PineconeVectorStore()
        elif db_type == "qdrant" and settings.QDRANT_URL:
            self.store = QdrantVectorStore()
            
        if not self.store:
            if db_type in ("pinecone", "qdrant"):
                print(f"Requested managed vector db ({db_type}) but missing key or URL. Falling back to local Chroma.")
            self.store = ChromaVectorStore()

    def add_chunks(self, document_id: int, chunks: List[Dict[str, Any]], api_key: Optional[str] = None, llm_provider: str = "simulation"):
        self.store.add_chunks(document_id, chunks, api_key, llm_provider)

    def search(self, query: str, limit: int = 5, department_id: Optional[int] = None, api_key: Optional[str] = None, llm_provider: str = "simulation") -> List[Dict[str, Any]]:
        return self.store.search(query, limit, department_id, api_key, llm_provider)

    def delete_document_chunks(self, document_id: int):
        self.store.delete_document_chunks(document_id)

vector_store_manager = VectorStoreManager()
