import pytest
from app.vectorstore import PGVectorStore
from unittest.mock import patch, MagicMock

def test_pgvector_rejects_mock():
    store = PGVectorStore()
    with pytest.raises(ValueError, match="Mock embeddings are not permitted"):
        store.search("query", llm_provider="simulation")
    with pytest.raises(ValueError, match="Mock embeddings are not permitted"):
        store.search("query", llm_provider="groq")

def test_pgvector_accepts_valid():
    store = PGVectorStore()
    with patch("app.vectorstore.EmbeddingProvider"), patch.object(store, 'SessionLocal'):
        store.search("query", llm_provider="openai")
        store.search("query", llm_provider="gemini")
