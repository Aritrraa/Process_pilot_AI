import asyncio
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rate_limiter import InMemoryRateLimiter


class TestRateLimiter:
    def test_allows_within_limit(self):
        async def run():
            rl = InMemoryRateLimiter()
            for _ in range(5):
                await rl.check_rate_limit("test_key", limit=5, window=60)
        asyncio.run(run())

    def test_blocks_over_limit(self):
        async def run():
            rl = InMemoryRateLimiter()
            for _ in range(5):
                await rl.check_rate_limit("over_key", limit=5, window=60)
            with pytest.raises(HTTPException):
                await rl.check_rate_limit("over_key", limit=5, window=60)
        asyncio.run(run())

    def test_different_keys_are_independent(self):
        async def run():
            rl = InMemoryRateLimiter()
            for _ in range(5):
                await rl.check_rate_limit("key_a", limit=5, window=60)
            with pytest.raises(HTTPException):
                await rl.check_rate_limit("key_a", limit=5, window=60)
            await rl.check_rate_limit("key_b", limit=5, window=60)
        asyncio.run(run())

    def test_window_expiry_allows_again(self):
        async def run():
            rl = InMemoryRateLimiter()
            for _ in range(3):
                await rl.check_rate_limit("expiry_test", limit=3, window=1)
            with pytest.raises(HTTPException):
                await rl.check_rate_limit("expiry_test", limit=3, window=1)
            await asyncio.sleep(1.1)
            await rl.check_rate_limit("expiry_test", limit=3, window=1)
        asyncio.run(run())

    def test_single_request_allowed(self):
        async def run():
            rl = InMemoryRateLimiter()
            await rl.check_rate_limit("single", limit=1, window=60)
        asyncio.run(run())

    def test_high_limit_allows_many(self):
        async def run():
            rl = InMemoryRateLimiter()
            for _ in range(100):
                await rl.check_rate_limit("high_limit", limit=1000, window=60)
        asyncio.run(run())

    def test_zero_limit_blocks_all(self):
        async def run():
            rl = InMemoryRateLimiter()
            with pytest.raises(HTTPException):
                await rl.check_rate_limit("zero_limit", limit=0, window=60)
        asyncio.run(run())


