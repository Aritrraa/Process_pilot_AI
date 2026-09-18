from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_groq_single_key_rag_fallback():
    from app.vectorstore import get_local_embedding
    # verify local embedding works
    emb = get_local_embedding("test")
    assert len(emb) == 768
    
    # Try searching with simulation/groq provider (should succeed using local embedding)
    from app.vectorstore import PGVectorStore
    store = PGVectorStore()
    
    with patch.object(store, 'SessionLocal') as mock_session:
        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_session.return_value = mock_db
        
        results = store.search("test query", llm_provider="groq")
        assert results == [] # Should not raise ValueError anymore!
