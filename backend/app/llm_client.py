"""
Unified LLM Client with retry logic and cost tracking.
Replaces duplicated provider dispatch code across agents.py.
Free-tier compatible — no external dependencies beyond existing API clients.
"""
import time
import logging
from typing import Optional, Dict, Any, Generator
from sqlalchemy.orm import Session
from .models import LLMUsage

logger = logging.getLogger("processpilot.llm")


class LLMClient:
    """Unified LLM client with exponential backoff retry and cost tracking."""
    
    # Approximate token costs per 1K tokens (USD)
    COST_PER_1K = {
        "gemini": {"input": 0.000075, "output": 0.0003},
        "openai": {"input": 0.00015, "output": 0.0006},
        "groq": {"input": 0.00006, "output": 0.00006},
        "simulation": {"input": 0.0, "output": 0.0},
    }
    
    # Approximate context window sizes (tokens)
    CONTEXT_LIMITS = {
        "gemini": 128000,
        "openai": 128000,
        "groq": 8000,
        "simulation": 32000,
    }
    
    def __init__(self):
        self.total_usage = {
            "input_tokens": 0, "output_tokens": 0,
            "total_cost": 0.0, "calls": 0, "failures": 0
        }
        self._consecutive_failures = 0
        self._circuit_open = False
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~1.3 tokens per word."""
        if not text:
            return 0
        return int(len(text.split()) * 1.3)
    
    def get_context_limit(self, provider: str) -> int:
        """Get the context window limit for a provider."""
        return self.CONTEXT_LIMITS.get(provider, 32000)
    
    def is_context_safe(self, provider: str, system_prompt: str, user_message: str, threshold: float = 0.8) -> bool:
        """Check if the combined input is within safe context limits."""
        total_tokens = self.estimate_tokens(system_prompt + " " + user_message)
        limit = self.get_context_limit(provider)
        return total_tokens < limit * threshold
    
    def call(
        self,
        provider: str,
        api_key: str,
        system_prompt: str,
        user_message: str,
        max_retries: int = 3,
        db: Optional[Session] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """
        Make an LLM call with exponential backoff retry.
        Supports: gemini, openai, groq, simulation.
        """
        if provider == "simulation" or not api_key:
            return self._simulate(user_message)
        
        # Circuit breaker check
        if self._circuit_open and self._consecutive_failures >= 5:
            logger.warning("Circuit breaker OPEN: using simulation fallback")
            return self._simulate(user_message)
        
        last_error = None
        for attempt in range(max_retries):
            try:
                result = self._dispatch(provider, api_key, system_prompt, user_message)
                self._consecutive_failures = 0
                self._circuit_open = False
                
                # Track usage
                input_tokens = self.estimate_tokens(system_prompt + user_message)
                output_tokens = self.estimate_tokens(result)
                cost = self._calculate_cost(provider, input_tokens, output_tokens)
                self.total_usage["input_tokens"] += input_tokens
                self.total_usage["output_tokens"] += output_tokens
                self.total_usage["total_cost"] += cost
                self.total_usage["calls"] += 1
                
                # Persist to database if db provided
                if db and user_id:
                    try:
                        usage_record = LLMUsage(
                            user_id=user_id,
                            provider=provider,
                            model_name="default", # Could be parsed based on provider
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            estimated_cost=str(cost)
                        )
                        db.add(usage_record)
                        db.commit()
                    except Exception as db_err:
                        logger.error(f"Failed to log LLM usage to DB: {db_err}")
                
                return result
                
            except Exception as e:
                last_error = e
                self._consecutive_failures += 1
                self.total_usage["failures"] += 1
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** (attempt + 1), 16)
                    logger.warning(
                        f"LLM call attempt {attempt + 1}/{max_retries} failed ({provider}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"LLM call failed after {max_retries} attempts ({provider}): {e}")
        
        # Circuit breaker: after 5 consecutive failures, fall back
        if self._consecutive_failures >= 5:
            self._circuit_open = True
            logger.warning("Circuit breaker ACTIVATED: falling back to simulation mode")
            return self._simulate(user_message)
        
        return f"Error: LLM call failed after {max_retries} attempts. Last error: {str(last_error)}"
    
    def stream(
        self,
        provider: str,
        api_key: str,
        system_prompt: str,
        user_message: str,
        max_retries: int = 3,
        db: Optional[Session] = None,
        user_id: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """
        Stream an LLM call with exponential backoff retry for the initial connection.
        Yields text chunks.
        """
        if provider == "simulation" or not api_key:
            yield from self._simulate_stream(user_message)
            return
        
        # Circuit breaker check
        if self._circuit_open and self._consecutive_failures >= 5:
            logger.warning("Circuit breaker OPEN: using simulation fallback for streaming")
            yield from self._simulate_stream(user_message)
            return
        
        last_error = None
        for attempt in range(max_retries):
            try:
                full_text = ""
                for chunk in self._dispatch_stream(provider, api_key, system_prompt, user_message):
                    full_text += chunk
                    yield chunk
                    
                self._consecutive_failures = 0
                self._circuit_open = False
                
                # Track usage
                input_tokens = self.estimate_tokens(system_prompt + user_message)
                output_tokens = self.estimate_tokens(full_text)
                cost = self._calculate_cost(provider, input_tokens, output_tokens)
                self.total_usage["input_tokens"] += input_tokens
                self.total_usage["output_tokens"] += output_tokens
                self.total_usage["total_cost"] += cost
                self.total_usage["calls"] += 1
                
                # Persist to database if db provided
                if db and user_id:
                    try:
                        usage_record = LLMUsage(
                            user_id=user_id,
                            provider=provider,
                            model_name="default",
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            estimated_cost=str(cost)
                        )
                        db.add(usage_record)
                        db.commit()
                    except Exception as db_err:
                        logger.error(f"Failed to log LLM stream usage to DB: {db_err}")
                
                return
                
            except Exception as e:
                last_error = e
                self._consecutive_failures += 1
                self.total_usage["failures"] += 1
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** (attempt + 1), 16)
                    logger.warning(
                        f"LLM stream attempt {attempt + 1}/{max_retries} failed ({provider}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"LLM stream failed after {max_retries} attempts ({provider}): {e}")
        
        # Circuit breaker
        if self._consecutive_failures >= 5:
            self._circuit_open = True
            logger.warning("Circuit breaker ACTIVATED: falling back to simulation mode")
            yield from self._simulate_stream(user_message)
            return
            
        yield f"\n\n[Error: LLM call failed after {max_retries} attempts. Last error: {str(last_error)}]"
    
    def _dispatch(self, provider: str, api_key: str, system_prompt: str, user_message: str) -> str:
        """Dispatch to the appropriate LLM provider."""
        if provider == "gemini":
            return self._call_gemini(api_key, system_prompt, user_message)
        elif provider == "openai":
            return self._call_openai(api_key, system_prompt, user_message)
        elif provider == "groq":
            return self._call_groq(api_key, system_prompt, user_message)
        else:
            return self._simulate(user_message)
    
    def _call_gemini(self, api_key: str, system_prompt: str, user_message: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_prompt)
        response = model.generate_content(user_message)
        return response.text
    
    def _call_openai(self, api_key: str, system_prompt: str, user_message: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2048
        )
        return response.choices[0].message.content
    
    def _call_groq(self, api_key: str, system_prompt: str, user_message: str) -> str:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2048
        )
        return response.choices[0].message.content
    
    def _dispatch_stream(self, provider: str, api_key: str, system_prompt: str, user_message: str):
        if provider == "gemini":
            yield from self._stream_gemini(api_key, system_prompt, user_message)
        elif provider == "openai":
            yield from self._stream_openai(api_key, system_prompt, user_message)
        elif provider == "groq":
            yield from self._stream_groq(api_key, system_prompt, user_message)
        else:
            yield from self._simulate_stream(user_message)

    def _stream_gemini(self, api_key: str, system_prompt: str, user_message: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_prompt)
        response = model.generate_content(user_message, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def _stream_openai(self, api_key: str, system_prompt: str, user_message: str):
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2048,
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _stream_groq(self, api_key: str, system_prompt: str, user_message: str):
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2048,
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def _simulate(self, user_message: str) -> str:
        """Offline simulation mode."""
        return (
            f"[Simulation Mode] Based on available documentation, here is a synthesized response "
            f"to your query about: {user_message[:100]}...\n\n"
            f"This is a simulated response. Configure an API key in Settings to enable live AI responses."
        )
    
    def _simulate_stream(self, user_message: str):
        """Simulate a streaming response word by word."""
        text = self._simulate(user_message)
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.02)
    
    def _calculate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        costs = self.COST_PER_1K.get(provider, self.COST_PER_1K["simulation"])
        return (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Return current usage statistics."""
        return dict(self.total_usage)
    
    def reset_stats(self):
        """Reset usage statistics."""
        self.total_usage = {
            "input_tokens": 0, "output_tokens": 0,
            "total_cost": 0.0, "calls": 0, "failures": 0
        }


# Singleton
llm_client = LLMClient()
