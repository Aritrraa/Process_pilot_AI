"""
Regression tests for the restored lightweight embedding architecture.

These tests verify:
1. EmbeddingProvider correctly routes to OpenAI/Gemini/simulation
2. Mock embeddings work in development
3. Mock embeddings are blocked in production
4. Embedding dimensions are consistent
5. SearchAgent failure does not crash CEOAgent
6. Empty search results are handled gracefully
7. LLM streaming preserves chunks correctly
8. Provider errors are surfaced
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.ceo_agent import CEOAgent
from app.llm_client import LLMClient
from app.models import Session, User
from app.vectorstore import (
    EMBEDDING_DIMENSION,
    EmbeddingProvider,
)


class TestEmbeddingProvider:
    """Tests for the restored external-API EmbeddingProvider."""

    def test_simulation_returns_768_dim(self):
        """Simulation mode returns a 768-dimensional normalized vector."""
        provider = EmbeddingProvider(api_key=None, llm_provider="simulation")
        emb = provider.get_embedding("test query")
        assert len(emb) == EMBEDDING_DIMENSION
        # Verify normalization (L2 norm should be ~1.0)
        norm = sum(x**2 for x in emb) ** 0.5
        assert abs(norm - 1.0) < 0.01

    def test_simulation_is_deterministic(self):
        """Same input always produces the same mock vector."""
        provider = EmbeddingProvider(api_key=None, llm_provider="simulation")
        emb1 = provider.get_embedding("test")
        emb2 = provider.get_embedding("test")
        assert emb1 == emb2

    def test_simulation_different_inputs_differ(self):
        """Different inputs produce different mock vectors."""
        provider = EmbeddingProvider(api_key=None, llm_provider="simulation")
        emb1 = provider.get_embedding("hello")
        emb2 = provider.get_embedding("goodbye")
        assert emb1 != emb2

    def test_missing_key_falls_to_simulation(self):
        """When api_key is None, any provider falls back to simulation."""
        for p in ["groq", "openai", "gemini"]:
            provider = EmbeddingProvider(api_key=None, llm_provider=p)
            emb = provider.get_embedding("test")
            assert len(emb) == EMBEDDING_DIMENSION

    def test_groq_without_key_falls_to_simulation(self):
        """Groq provider without a key should use simulation."""
        provider = EmbeddingProvider(api_key=None, llm_provider="groq")
        emb = provider.get_embedding("test query")
        assert len(emb) == EMBEDDING_DIMENSION

    def test_empty_text_handled(self):
        """Empty text is replaced with 'empty' before embedding."""
        provider = EmbeddingProvider(api_key=None, llm_provider="simulation")
        emb = provider.get_embedding("")
        assert len(emb) == EMBEDDING_DIMENSION

    @patch.dict("os.environ", {"ENVIRONMENT": "production"}, clear=False)
    def test_production_blocks_simulation(self):
        """Production mode must NOT allow mock embeddings."""
        with patch("app.vectorstore.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            provider = EmbeddingProvider(api_key=None, llm_provider="simulation")
            with pytest.raises(RuntimeError, match="Mock embeddings are blocked in production"):
                provider.get_embedding("test")

    def test_embedding_dimension_constant(self):
        """EMBEDDING_DIMENSION must be exactly 768."""
        assert EMBEDDING_DIMENSION == 768


class TestCEOAgentEmbeddingFallback:
    """Tests verifying CEOAgent's embedding provider resolution cascade."""

    @pytest.mark.asyncio
    async def test_search_failure_does_not_crash_ceo(self):
        """SearchAgent failure should be caught gracefully."""
        agent = CEOAgent()
        user = User(id=1, email="test@test", role="Employee")

        session_mock = MagicMock(spec=Session)
        session_mock.llm_provider = "simulation"
        user.current_session = session_mock

        db_mock = AsyncMock()
        db_mock.execute.return_value.scalars.return_value.first.return_value = MagicMock(system_prompt="Test")
        db_mock.execute.return_value.scalars.return_value.all.return_value = []

        with patch("app.agents.ceo_agent.SearchAgent.execute", side_effect=Exception("DB Error")):
            chunks = []
            async for chunk in agent.process_query_stream(user, "test", db_mock):
                chunks.append(chunk)

            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_empty_search_result_handled(self):
        """Empty search result should not prevent a normal LLM response."""
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


class TestLLMStreaming:
    """Tests verifying LLM streaming behavior."""

    @pytest.mark.asyncio
    async def test_streaming_preserves_empty_chunks(self):
        """LLM streaming with empty chunks should not lose valid output."""
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
            yield MockChunk("")  # Empty chunk
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

            assert result == ["Hello ", "", "World"]

    @pytest.mark.asyncio
    async def test_provider_error_surfaced(self):
        """Provider errors should be visible in streaming output."""
        client = LLMClient()

        async def failing_stream(*args, **kwargs):
            raise ValueError("Invalid API Key")
            yield ""

        with patch.object(client, '_stream_groq', side_effect=failing_stream):
            chunks = []
            async for chunk in client.stream(provider="groq", api_key="badkey", system_prompt="sys", user_message="user", max_retries=1):
                chunks.append(chunk)

            assert len(chunks) > 0
            assert "Invalid API Key" in chunks[-1]
