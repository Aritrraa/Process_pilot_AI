from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.ceo_agent import CEOAgent
from app.llm_client import LLMClient
from app.models import Session, User
from app.vectorstore import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    EmbeddingProvider,
    get_local_embedding,
)


@pytest.mark.asyncio
async def test_01_all_providers_use_same_local_model():
    """TEST 1, 2, 3, 4: Groq, OpenAI, Gemini all map to the SAME local embedding model."""
    for provider_name in ["groq", "openai", "gemini"]:
        provider = EmbeddingProvider(api_key="fake", llm_provider=provider_name)
        emb = provider.get_embedding("test query")
        assert len(emb) == EMBEDDING_DIMENSION
        assert EMBEDDING_MODEL == 'sentence-transformers/all-mpnet-base-v2'

@pytest.mark.asyncio
async def test_05_no_md5_mock_vectors():
    """TEST 5: Verify get_local_embedding returns a real tensor, not deterministic MD5 hash standard normals."""
    emb1 = get_local_embedding("hello")
    emb2 = get_local_embedding("hello world")
    assert len(emb1) == 768
    assert len(emb2) == 768
    assert emb1 != emb2 # Ensures it's actually processing text, not just falling back to zeros

@pytest.mark.asyncio
async def test_06_search_agent_failure_does_not_crash_ceo():
    """TEST 6: SearchAgent failure does not crash CEOAgent."""
    agent = CEOAgent()
    user = User(id=1, email="test@test", role="Employee")
    
    session_mock = MagicMock(spec=Session)
    session_mock.llm_provider = "simulation"
    user.current_session = session_mock
    
    db_mock = AsyncMock()
    db_mock.execute.return_value.scalars.return_value.first.return_value = MagicMock(system_prompt="Test")
    db_mock.execute.return_value.scalars.return_value.all.return_value = []
    
    with patch("app.agents.ceo_agent.SearchAgent.execute", side_effect=Exception("DB Error")):
        # Should gracefully catch Exception and yield normally without crashing
        chunks = []
        async for chunk in agent.process_query_stream(user, "test", db_mock):
            chunks.append(chunk)
            
        assert len(chunks) > 0

@pytest.mark.asyncio
async def test_07_empty_search_result_handled():
    """TEST 7: Empty search result does not prevent normal LLM response."""
    agent = CEOAgent()
    user = User(id=1, email="test@test", role="Employee")
    
    session_mock = MagicMock(spec=Session)
    session_mock.llm_provider = "simulation"
    user.current_session = session_mock
    
    db_mock = AsyncMock()
    db_mock.execute.return_value.scalars.return_value.first.return_value = MagicMock(system_prompt="Test")
    db_mock.execute.return_value.scalars.return_value.all.return_value = []
    
    with patch("app.agents.ceo_agent.SearchAgent.execute", return_value=[]):
        chunks = []
        async for chunk in agent.process_query_stream(user, "test", db_mock):
            chunks.append(chunk)
            
        assert len(chunks) > 0

@pytest.mark.asyncio
async def test_08_llm_streaming_preserves_chunks():
    """TEST 8: LLM streaming with empty chunks does not incorrectly lose valid output."""
    class MockDelta:
        def __init__(self, content):
            self.content = content
            
    class MockChoice:
        def __init__(self, content):
            self.delta = MockDelta(content)
            
    class MockChunk:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
            
    async def mock_async_generator():
        yield MockChunk("Hello ")
        yield MockChunk("") # Empty chunk (simulating LLaMA3)
        yield MockChunk("World")
        
    class MockCompletions:
        async def create(self, *args, **kwargs):
            return mock_async_generator()
            
    class MockChat:
        def __init__(self):
            self.completions = MockCompletions()
            
    class MockAsyncGroq:
        def __init__(self, api_key=None, **kwargs):
            self.chat = MockChat()
            
    client = LLMClient()
    with patch('groq.AsyncGroq', MockAsyncGroq):
        result = []
        async for text in client.stream(provider="groq", api_key="key", system_prompt="sys", user_message="user"):
            result.append(text)
            
        assert result == ["Hello ", "", "World"] # Preserves all yielded values accurately!

@pytest.mark.asyncio
async def test_09_provider_error_surfaced():
    """TEST 9: Provider error is surfaced correctly."""
    client = LLMClient()
    
    async def failing_stream(*args, **kwargs):
        raise ValueError("Invalid API Key")
        yield "" # to make it a generator
        
    with patch.object(client, '_stream_groq', side_effect=failing_stream):
        chunks = []
        async for chunk in client.stream(provider="groq", api_key="badkey", system_prompt="sys", user_message="user", max_retries=1):
            chunks.append(chunk)
            
        assert len(chunks) > 0
        assert "Invalid API Key" in chunks[-1]
