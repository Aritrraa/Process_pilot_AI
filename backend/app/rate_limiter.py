"""
Simple In-Memory Rate Limiter for ProcessPilot AI.
Tracks rate limits per client IP in a standard Python dictionary.
(Best for single-server deployments like Render Free Tier).
"""
import time
import asyncio
from typing import Dict, List
from fastapi import HTTPException, Request, status
import logging

logger = logging.getLogger("processpilot.rate_limiter")

class InMemoryRateLimiter:
    def __init__(self):
        self.requests: Dict[str, List[float]] = {}
        self.lock = asyncio.Lock()

    async def check_rate_limit(self, key: str, limit: int, window: int):
        now = time.time()
        async with self.lock:
            if key not in self.requests:
                self.requests[key] = []
            
            # Filter old requests outside the window
            self.requests[key] = [t for t in self.requests[key] if now - t < window]
            
            if len(self.requests[key]) >= limit:
                logger.warning(f"Rate limit exceeded for {key}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            self.requests[key].append(now)

# Global singleton
_limiter = InMemoryRateLimiter()

def rate_limit(limit: int = 10, window: int = 60):
    """
    FastAPI dependency factory for rate limiting.
    
    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit(5, 60))])
        async def login(...):
    """
    async def _rate_limit(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"{client_ip}:{path}"
        await _limiter.check_rate_limit(key, limit, window)
    
    return _rate_limit
