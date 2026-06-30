"""
In-Memory Rate Limiter for ProcessPilot AI.
Uses sliding window algorithm — no Redis required (free-tier compatible).
Resets on server restart, which is acceptable for Render free tier.
"""
import time
import threading
from typing import Dict, List
from fastapi import Request, HTTPException, status

class InMemoryRateLimiter:
    """Thread-safe sliding window rate limiter."""
    
    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Clean every 5 minutes
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """Check if a request is allowed under the rate limit."""
        now = time.time()
        cutoff = now - window_seconds
        
        with self._lock:
            # Periodic cleanup of stale entries
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup()
                self._last_cleanup = now
            
            if key not in self._requests:
                self._requests[key] = []
            
            # Remove expired timestamps
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            
            # Check limit
            if len(self._requests[key]) >= limit:
                return False
            
            # Record this request
            self._requests[key].append(now)
            return True
    
    def _cleanup(self):
        """Remove keys with no recent requests."""
        now = time.time()
        stale_keys = []
        for key, timestamps in self._requests.items():
            if not timestamps or timestamps[-1] < now - 3600:  # 1 hour stale
                stale_keys.append(key)
        for key in stale_keys:
            del self._requests[key]


# Singleton
limiter = InMemoryRateLimiter()


def rate_limit(limit: int = 10, window: int = 60):
    """
    FastAPI dependency factory for rate limiting.
    
    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit(5, 60))])
        def login(...):
    
    Args:
        limit: Max requests allowed in the window
        window: Window size in seconds
    """
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        
        if not limiter.is_allowed(key, limit, window):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit} requests per {window} seconds.",
                headers={"Retry-After": str(window)}
            )
    return dependency
