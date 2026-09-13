# LLM Architecture

## Unified Client (llm_client.py)
Provides a single abstraction layer for LLM interactions.

## Providers
- **Groq:** Primary provider.
- **OpenAI / Gemini:** Fallback providers.
- **Dynamic Fallback:** Handles Groq model deprecations by querying active models dynamically.