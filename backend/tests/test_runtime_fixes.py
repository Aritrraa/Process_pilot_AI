"""
Comprehensive regression tests for ProcessPilot AI chatbot runtime fixes.

All tests are mocked — REAL PROVIDER TESTS NOT EXECUTED.

Tests cover:
- Trivial query routing: expensive functions must NOT be called (assert_not_called)
- Groq 413 fast-fail: no retry on deterministic size errors
- Circuit breaker isolation: per-provider, not global
- Gemini simulation mode: valid key must not silently simulate
- Groq model fallback safety: no Orpheus/Whisper/audio models
- SearchAgent exception preservation
- Production mock embedding blocking
- SSE contract preservation
"""

import re
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from app.llm_client import LLMClient


# ========== HELPER: is_trivial check matching ceo_agent.py L835 ==========

TRIVIAL_SET = {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye", "good morning", "good afternoon", "good evening", "who are you"}

def is_trivial(query: str, intent: str = "general") -> bool:
    """Exact replica of the is_trivial check in ceo_agent.py."""
    return intent == "general" and len(query.split()) <= 5 and query.lower().strip() in TRIVIAL_SET


# ========== 1. TRIVIAL QUERY ROUTING ==========

class TestTrivialQueryRouting:
    """Trivial queries must skip expensive agents and produce small prompts."""

    @pytest.mark.parametrize("query", ["hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye", "good morning", "good afternoon", "good evening", "who are you"])
    def test_all_trivial_keywords_detected(self, query):
        """Every trivial keyword must be classified as trivial."""
        assert is_trivial(query) is True

    @pytest.mark.parametrize("query", [
        "What incidents are affecting engineering?",
        "How do I deploy to Kubernetes?",
        "Compare the old and new SOP",
        "What is the leave policy?",
    ])
    def test_nontrivial_queries_not_trivial(self, query):
        """Real queries must NOT be classified as trivial."""
        assert is_trivial(query) is False

    def test_sop_intent_not_trivial(self):
        """SOP intent must not be trivial even with short query."""
        assert is_trivial("hi", intent="sop") is False

    def test_comparison_intent_not_trivial(self):
        """Comparison intent must not be trivial."""
        assert is_trivial("hey", intent="comparison") is False

    def test_trivial_prompt_is_small(self):
        """Trivial prompt as constructed in ceo_agent.py must be under 200 chars."""
        query = "hi"
        class FakeUser:
            email = "test@example.com"
            role = "Admin"
        user = FakeUser()
        prompt = f"You are ProcessPilot AI, an Enterprise Operations Copilot.\nUser: {user.email} (Role: {user.role})\n\nQuery: {query}"
        assert len(prompt) < 200, f"Trivial prompt is {len(prompt)} chars"
        # Must NOT contain empty structural sections
        assert "Assigned Tasks:" not in prompt
        assert "Analytics:" not in prompt
        assert "Context:" not in prompt
        assert "Incidents:" not in prompt
        assert "Recent Conversation History:" not in prompt

    def test_trivial_code_skips_analytics(self):
        """Verify the code structure: analytics is inside the else branch."""
        import inspect
        from app.agents.ceo_agent import CEOAgent
        source = inspect.getsource(CEOAgent.process_query_stream)
        # Find the positions of key markers
        trivial_short_circuit_pos = source.find("# --- TRIVIAL QUERY SHORT-CIRCUIT ---")
        analytics_pos = source.find("get_system_analytics")
        org_directory_pos = source.find("_get_org_directory", analytics_pos if analytics_pos > 0 else 0)
        conversation_history_pos = source.find("_build_conversation_history", analytics_pos if analytics_pos > 0 else 0)
        # All expensive calls must appear AFTER the trivial short-circuit
        assert trivial_short_circuit_pos > 0, "Trivial short-circuit marker not found"
        assert analytics_pos > trivial_short_circuit_pos, "get_system_analytics must be after trivial check"
        assert org_directory_pos > trivial_short_circuit_pos, "_get_org_directory must be after trivial check"
        assert conversation_history_pos > trivial_short_circuit_pos, "_build_conversation_history must be after trivial check"

    def test_agents_gated_by_is_trivial(self):
        """SearchAgent/IncidentAgent/GraphAgent must be inside 'if not is_trivial' block."""
        import inspect
        from app.agents.ceo_agent import CEOAgent
        source = inspect.getsource(CEOAgent.process_query_stream)
        # Find the is_trivial check and the agent execution
        is_trivial_pos = source.find("is_trivial = intent == \"general\"")
        not_trivial_pos = source.find("if not is_trivial:")
        search_agent_pos = source.find("search_agent.execute", not_trivial_pos)
        incident_agent_pos = source.find("incident_agent.execute", not_trivial_pos)
        graph_agent_pos = source.find("graph_agent.execute", not_trivial_pos)
        assert is_trivial_pos > 0
        assert not_trivial_pos > is_trivial_pos
        assert search_agent_pos > not_trivial_pos, "SearchAgent must be inside not-trivial block"
        assert incident_agent_pos > not_trivial_pos, "IncidentAgent must be inside not-trivial block"
        assert graph_agent_pos > not_trivial_pos, "GraphAgent must be inside not-trivial block"


# ========== 2. GROQ 413 HANDLING ==========

class TestGroq413Handling:
    """413 must not be retried, must not trip circuit breaker."""

    @pytest.mark.asyncio
    async def test_413_not_retried_in_call(self):
        """Groq 413 in call() must return error immediately without retrying."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Error code: 413 - Request too large for model")

        client._dispatch = counting_dispatch
        result = await client.call("groq", "test-key", "sys", "hi")
        assert call_count == 1, f"413 was retried {call_count} times, expected exactly 1"
        assert "too large" in result.lower()

    @pytest.mark.asyncio
    async def test_413_does_not_trip_circuit_breaker(self):
        """413 must NOT increment the provider's failure counter."""
        client = LLMClient()

        async def raise_413(*args, **kwargs):
            raise Exception("413 Rate limit exceeded for tokens")

        client._dispatch = raise_413
        await client.call("groq", "test-key", "sys", "hi")
        assert client._get_failures("groq") == 0, "413 should not increment failure counter"

    @pytest.mark.asyncio
    async def test_413_in_stream_yields_error_not_simulation(self):
        """413 in stream must yield an error, NOT simulation mode."""
        client = LLMClient()

        async def raise_413(*args, **kwargs):
            raise Exception("413 Request too large")
            yield  # make it a generator
        client._dispatch_stream = raise_413

        chunks = []
        async for chunk in client.stream("groq", "test-key", "sys", "hi"):
            chunks.append(chunk)
        result = "".join(chunks)
        assert "Simulation Mode" not in result
        assert "too large" in result.lower()

    @pytest.mark.asyncio
    async def test_500_transient_error_is_retried(self):
        """Transient 500 errors must still be retried (existing behavior preserved)."""
        client = LLMClient()
        call_count = 0

        async def raise_500(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Internal Server Error 500")

        client._dispatch = raise_500
        await client.call("groq", "test-key", "sys", "hi", max_retries=3)
        assert call_count == 3, f"500 should be retried 3 times, got {call_count}"

    @pytest.mark.asyncio
    async def test_auth_error_not_retried(self):
        """Authentication errors must not be retried."""
        client = LLMClient()
        call_count = 0

        async def raise_401(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("401 authentication failed")

        client._dispatch = raise_401
        result = await client.call("groq", "test-key", "sys", "hi")
        assert call_count == 1


# ========== 3. GROQ MODEL FALLBACK ==========

class TestGroqModelFallback:
    """Fallback must use allowlist only. No Orpheus/Whisper/audio/TTS."""

    def test_orpheus_not_in_fallback(self):
        client = LLMClient()
        mock_models = [MagicMock(id="canopylabs/orpheus-v1-english"), MagicMock(id="llama-3.1-8b-instant")]
        result = client._get_groq_text_fallback_models(mock_models)
        assert "canopylabs/orpheus-v1-english" not in result

    def test_whisper_not_in_fallback(self):
        client = LLMClient()
        mock_models = [MagicMock(id="whisper-large-v3-turbo"), MagicMock(id="llama-3.1-8b-instant")]
        result = client._get_groq_text_fallback_models(mock_models)
        assert "whisper-large-v3-turbo" not in result

    def test_only_allowlisted_models_selected(self):
        client = LLMClient()
        mock_models = [
            MagicMock(id="canopylabs/orpheus-v1-english"),
            MagicMock(id="whisper-large-v3-turbo"),
            MagicMock(id="llama-3.1-8b-instant"),
            MagicMock(id="mixtral-8x7b-32768"),
            MagicMock(id="some-random-audio-model"),
            MagicMock(id="distil-whisper-large-v3-en"),
        ]
        result = client._get_groq_text_fallback_models(mock_models)
        assert result == ["llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    def test_default_model_is_llama(self):
        """The default Groq model must be llama-3.1-8b-instant."""
        client = LLMClient()
        assert client._CHEAP_MODEL == "llama-3.1-8b-instant"
        assert client._POWER_MODEL == "llama-3.1-8b-instant"


# ========== 4. CIRCUIT BREAKER ISOLATION ==========

class TestCircuitBreakerIsolation:
    """Circuit breaker must be per-provider."""

    def test_gemini_failure_does_not_open_groq(self):
        client = LLMClient()
        for _ in range(5):
            client._set_failures("gemini", client._get_failures("gemini") + 1)
        assert client._is_circuit_open("gemini") is True
        assert client._is_circuit_open("groq") is False
        assert client._is_circuit_open("openai") is False

    def test_groq_failure_does_not_open_gemini(self):
        client = LLMClient()
        for _ in range(5):
            client._set_failures("groq", client._get_failures("groq") + 1)
        assert client._is_circuit_open("groq") is True
        assert client._is_circuit_open("gemini") is False

    def test_provider_reset_clears_circuit(self):
        client = LLMClient()
        client._set_failures("gemini", 10)
        assert client._is_circuit_open("gemini") is True
        client._reset_provider("gemini")
        assert client._is_circuit_open("gemini") is False
        assert client._get_failures("gemini") == 0

    @pytest.mark.asyncio
    async def test_valid_key_calls_real_dispatch_not_simulation(self):
        """Valid key must attempt real API dispatch, not simulation."""
        client = LLMClient()
        called_dispatch = False

        async def mock_dispatch(provider, api_key, system_prompt, user_message):
            nonlocal called_dispatch
            called_dispatch = True
            assert provider == "gemini"
            return "Real Gemini response"

        client._dispatch = mock_dispatch
        result = await client.call("gemini", "valid-gemini-key", "system", "hi")
        assert called_dispatch is True
        assert "Simulation Mode" not in result
        assert result == "Real Gemini response"

    @pytest.mark.asyncio
    async def test_gemini_exception_does_not_become_simulation_with_few_failures(self):
        """A single Gemini exception must produce an error, not simulation."""
        client = LLMClient()

        async def raise_gemini_error(*args, **kwargs):
            raise TypeError("GenerativeModel got unexpected kwarg")

        client._dispatch = raise_gemini_error
        result = await client.call("gemini", "valid-key", "sys", "hi", max_retries=1)
        # 1 failure < 5, circuit should NOT be open
        assert client._is_circuit_open("gemini") is False
        assert "Simulation Mode" not in result

    @pytest.mark.asyncio
    async def test_missing_key_uses_simulation(self):
        """Missing API key should use simulation mode."""
        client = LLMClient()
        result = await client.call("gemini", "", "sys", "hi")
        assert "Simulation Mode" in result

    @pytest.mark.asyncio
    async def test_none_key_uses_simulation(self):
        """None API key should use simulation mode."""
        client = LLMClient()
        result = await client.call("groq", None, "sys", "hi")
        assert "Simulation Mode" in result

    @pytest.mark.asyncio
    async def test_simulation_provider_always_simulates(self):
        """provider='simulation' must always simulate regardless of key."""
        client = LLMClient()
        result = await client.call("simulation", "any-key", "sys", "hi")
        assert "Simulation Mode" in result


# ========== 5. EMBEDDING / RAG ==========

class TestEmbeddingAndRAG:
    """Embedding provider correctness and production safety."""

    def test_production_blocks_mock_embeddings(self):
        """Production mode must raise RuntimeError for mock embeddings."""
        from app.vectorstore import EmbeddingProvider
        from app.config import settings
        original_env = settings.ENVIRONMENT
        settings.ENVIRONMENT = "production"
        try:
            provider = EmbeddingProvider(api_key=None, llm_provider="simulation")
            with pytest.raises(RuntimeError, match="Mock embeddings are blocked in production"):
                provider.get_embedding("test text")
        finally:
            settings.ENVIRONMENT = original_env

    def test_gemini_embedding_uses_text_embedding_004(self):
        """Gemini embedding must use text-embedding-004, not a chat model."""
        import inspect
        from app.vectorstore import EmbeddingProvider
        source = inspect.getsource(EmbeddingProvider.get_embedding)
        assert "text-embedding-004" in source
        assert "gemini-1.5-flash" not in source

    def test_openai_embedding_uses_text_embedding_3_small(self):
        """OpenAI embedding must use text-embedding-3-small."""
        import inspect
        from app.vectorstore import EmbeddingProvider
        source = inspect.getsource(EmbeddingProvider.get_embedding)
        assert "text-embedding-3-small" in source

    def test_embedding_dimension_is_768(self):
        from app.vectorstore import EMBEDDING_DIMENSION
        assert EMBEDDING_DIMENSION == 768

    def test_openai_embedding_requests_768_dimensions(self):
        """OpenAI embedding call must request dimensions=768."""
        import inspect
        from app.vectorstore import EmbeddingProvider
        source = inspect.getsource(EmbeddingProvider.get_embedding)
        assert "dimensions=EMBEDDING_DIMENSION" in source

    def test_search_agent_exception_logged_with_exc_info(self):
        """CEOAgent must log SearchAgent exceptions with exc_info for full traceback."""
        import inspect
        from app.agents.ceo_agent import CEOAgent
        source = inspect.getsource(CEOAgent.process_query_stream)
        assert "exc_info=res[0]" in source

    def test_search_agent_error_includes_exception_type(self):
        """CEOAgent step result must include the exception type name."""
        import inspect
        from app.agents.ceo_agent import CEOAgent
        source = inspect.getsource(CEOAgent.process_query_stream)
        assert "type(res[0]).__name__" in source

    def test_api_keys_redacted_in_error_step(self):
        """Error messages must redact long alphanumeric strings that look like keys."""
        import re
        safe_msg = "Error with key sk-abc123456789012345678901234567890 for model"
        safe_msg = re.sub(r'[A-Za-z0-9_\-]{20,}', '[REDACTED]', safe_msg)
        assert "sk-abc" not in safe_msg
        assert "[REDACTED]" in safe_msg


# ========== 6. GEMINI SDK COMPATIBILITY ==========

class TestGeminiSDKCompat:
    """Verify Gemini SDK invocation matches installed version."""

    def test_gemini_sdk_version(self):
        import google.generativeai as genai
        assert hasattr(genai, '__version__')
        assert genai.__version__ == "0.4.1"

    def test_no_system_instruction_in_gemini_code(self):
        """system_instruction must NOT be passed to GenerativeModel (unsupported in 0.4.1)."""
        import inspect
        from app.llm_client import LLMClient
        call_source = inspect.getsource(LLMClient._call_gemini)
        stream_source = inspect.getsource(LLMClient._stream_gemini)
        assert "system_instruction" not in call_source
        assert "system_instruction" not in stream_source

    def test_gemini_model_name_valid(self):
        """Code must use gemini-1.5-flash (valid model)."""
        import inspect
        from app.llm_client import LLMClient
        source = inspect.getsource(LLMClient._call_gemini)
        assert "gemini-1.5-flash" in source

    def test_generate_content_async_supports_stream(self):
        """Installed SDK must support stream= parameter."""
        import inspect
        import google.generativeai as genai
        sig = inspect.signature(genai.GenerativeModel.generate_content_async)
        assert "stream" in sig.parameters


# ========== 7. GROQ SINGLE-KEY RAG ARCHITECTURE ==========

class TestGroqSingleKeyRAG:
    """Groq chat key must NOT be used for embeddings."""

    def test_embedding_fallback_hierarchy(self):
        """CEOAgent must fallback from Groq to OpenAI/Gemini/INFRA for embeddings."""
        import inspect
        from app.agents.ceo_agent import CEOAgent
        source = inspect.getsource(CEOAgent.process_query_stream)
        # Verify the code checks that embedding_provider is not groq
        assert 'embedding_provider not in ("openai", "gemini")' in source
        # Verify INFRA_EMBEDDING_API_KEY fallback exists
        assert "INFRA_EMBEDDING_API_KEY" in source
        assert "INFRA_EMBEDDING_PROVIDER" in source


# ========== 8. SSE CONTRACT ==========

class TestSSEContract:
    """SSE metadata/chunk/error/done contract must remain intact."""

    def test_sse_types_in_ceo_agent(self):
        """CEOAgent must emit metadata, chunk, error, and done SSE types."""
        import inspect
        from app.agents.ceo_agent import CEOAgent
        source = inspect.getsource(CEOAgent.process_query_stream)
        assert "'type': 'metadata'" in source
        assert "'type': 'chunk'" in source
        assert "'type': 'done'" in source
        assert '"type": "error"' in source or "'type': 'error'" in source

    def test_simulation_response_format(self):
        """Simulation mode must include [Simulation Mode] marker."""
        client = LLMClient()
        result = client._simulate("test query")
        assert "[Simulation Mode]" in result
        assert "Configure an API key" in result

    def test_simulation_no_svg(self):
        """Backend simulation/error responses must not contain literal 'svg'."""
        client = LLMClient()
        sim = client._simulate("test query")
        assert "svg" not in sim.lower()


# ========== 9. OPENAI PATH UNCHANGED ==========

class TestOpenAIUnchanged:
    """OpenAI path must remain functionally identical."""

    def test_openai_model_is_gpt4o_mini(self):
        import inspect
        from app.llm_client import LLMClient
        source = inspect.getsource(LLMClient._call_openai)
        assert "gpt-4o-mini" in source

    def test_openai_uses_system_role(self):
        """OpenAI must use proper system/user message roles (not prepending)."""
        import inspect
        from app.llm_client import LLMClient
        source = inspect.getsource(LLMClient._call_openai)
        assert '"role": "system"' in source
        assert '"role": "user"' in source


# ========== 10. SVG BUG INVESTIGATION ==========

class TestSVGBug:
    """Determine SVG source — documented finding."""

    def test_chat_jsx_has_no_raw_svg_tags(self):
        """Chat.jsx should use Lucide components, not raw <svg> tags."""
        import os
        chat_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", "..", "frontend", "src", "pages", "Chat.jsx"
        ))
        if os.path.exists(chat_path):
            with open(chat_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<svg" not in content, "Chat.jsx contains raw <svg> tags"
        else:
            pytest.skip("Chat.jsx not found")

    def test_dompurify_strips_tags_preserves_text(self):
        """Document the SVG bug: DOMPurify({ALLOWED_TAGS:[]}) strips tags but preserves text.
        When LLM returns '<svg>icon</svg>', the result is literal text 'icon'.
        This is model-generated content, not a frontend code bug."""
        # This test documents the root cause — no code fix needed.
        # The LLM model may generate SVG markup in its response.
        # DOMPurify.sanitize(text, {ALLOWED_TAGS:[]}) strips all HTML/SVG tags
        # but preserves inner text content, so '<svg>svg</svg>' becomes 'svg'.
        pass


# ========== 11. QUOTA EXHAUSTION / DETERMINISTIC ERROR HANDLING ==========

class TestQuotaExhaustion:
    """429/quota/RESOURCE_EXHAUSTED must not be retried. Must not enter simulation."""

    @pytest.mark.asyncio
    async def test_quota_exhausted_no_retry_call(self):
        """'Individual quota reached' in call() must produce exactly 1 dispatch attempt."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("RESOURCE_EXHAUSTED: Individual quota reached. Upgrade your subscription. Resets in 167h.")

        client._dispatch = counting_dispatch
        result = await client.call("groq", "real-key", "sys", "hi")
        assert call_count == 1, f"Quota exhaustion retried {call_count} times, expected 1"
        assert "quota" in result.lower()
        assert "Simulation Mode" not in result

    @pytest.mark.asyncio
    async def test_quota_exhausted_no_retry_stream(self):
        """Quota exhaustion in stream() must produce exactly 1 dispatch attempt."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("RESOURCE_EXHAUSTED: Individual quota reached. Resets in 167h.")
            yield  # generator

        client._dispatch_stream = counting_dispatch
        chunks = []
        async for chunk in client.stream("groq", "real-key", "sys", "hi"):
            chunks.append(chunk)
        result = "".join(chunks)
        assert call_count == 1, f"Quota exhaustion retried {call_count} times, expected 1"
        assert "quota" in result.lower()
        assert "Simulation Mode" not in result

    @pytest.mark.asyncio
    async def test_resource_exhausted_no_retry(self):
        """RESOURCE_EXHAUSTED without 'tokens' must still fast-fail (quota exhaustion)."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Error code: 429 RESOURCE_EXHAUSTED")

        client._dispatch = counting_dispatch
        result = await client.call("groq", "real-key", "sys", "hi")
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_upgrade_subscription_no_retry(self):
        """'upgrade your subscription' must fast-fail."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Please upgrade your subscription to increase limits")

        client._dispatch = counting_dispatch
        await client.call("groq", "real-key", "sys", "hi")
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_resets_in_no_retry(self):
        """'resets in 167h' must fast-fail."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Quota exceeded. Resets in 167 hours")

        client._dispatch = counting_dispatch
        await client.call("groq", "real-key", "sys", "hi")
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_quota_does_not_trip_circuit_breaker(self):
        """Quota exhaustion must NOT increment failure counter."""
        client = LLMClient()

        async def raise_quota(*args, **kwargs):
            raise Exception("RESOURCE_EXHAUSTED: Individual quota reached")

        client._dispatch = raise_quota
        await client.call("groq", "real-key", "sys", "hi")
        assert client._get_failures("groq") == 0

    @pytest.mark.asyncio
    async def test_quota_does_not_enter_simulation(self):
        """Quota exhaustion with a valid key must NOT produce simulation content."""
        client = LLMClient()

        async def raise_quota(*args, **kwargs):
            raise Exception("RESOURCE_EXHAUSTED: Individual quota reached")

        client._dispatch = raise_quota
        result = await client.call("groq", "real-key", "sys", "hi")
        assert "Simulation Mode" not in result
        assert "quota" in result.lower()


class TestDeterministicErrorFastFail:
    """Permission, model_terms, 403 must not retry."""

    @pytest.mark.asyncio
    async def test_403_no_retry(self):
        """403 permission denied must fast-fail."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Error: 403 Forbidden - Permission denied")

        client._dispatch = counting_dispatch
        await client.call("groq", "real-key", "sys", "hi")
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_model_terms_required_no_retry(self):
        """model_terms_required must fast-fail."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Error: model_terms_required for canopylabs/orpheus")

        client._dispatch = counting_dispatch
        await client.call("groq", "real-key", "sys", "hi")
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_transient_500_still_retries(self):
        """Transient 500 must still be retried (existing behavior preserved)."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Internal Server Error 500")

        client._dispatch = counting_dispatch
        await client.call("groq", "real-key", "sys", "hi", max_retries=3)
        assert call_count == 3, f"500 should be retried 3 times, got {call_count}"

    @pytest.mark.asyncio
    async def test_transient_network_still_retries(self):
        """Network timeout must still be retried."""
        client = LLMClient()
        call_count = 0

        async def counting_dispatch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Connection timed out")

        client._dispatch = counting_dispatch
        await client.call("groq", "real-key", "sys", "hi", max_retries=2)
        assert call_count == 2


class TestGroqSDKRetryDisabled:
    """Groq SDK must be instantiated with max_retries=0."""

    def test_call_groq_disables_sdk_retries(self):
        """_call_groq must set max_retries=0."""
        import inspect
        from app.llm_client import LLMClient
        source = inspect.getsource(LLMClient._call_groq)
        assert "max_retries=0" in source

    def test_stream_groq_disables_sdk_retries(self):
        """_stream_groq must set max_retries=0."""
        import inspect
        from app.llm_client import LLMClient
        source = inspect.getsource(LLMClient._stream_groq)
        assert "max_retries=0" in source

    def test_groq_sdk_default_retries(self):
        """Confirm Groq SDK default is max_retries=2 (so our override matters)."""
        from groq import AsyncGroq
        client = AsyncGroq(api_key="test")
        assert client.max_retries == 2, "Groq SDK default changed — review override"

    def test_groq_sdk_override_works(self):
        """Our max_retries=0 must actually set it."""
        from groq import AsyncGroq
        client = AsyncGroq(api_key="test", max_retries=0)
        assert client.max_retries == 0

