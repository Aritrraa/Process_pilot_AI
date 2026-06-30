"""
Rate limiter unit tests — sliding window, cleanup, key isolation.
"""
import pytest
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rate_limiter import InMemoryRateLimiter


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = InMemoryRateLimiter()
        for _ in range(5):
            assert rl.is_allowed("test_key", limit=5, window_seconds=60) is True

    def test_blocks_over_limit(self):
        rl = InMemoryRateLimiter()
        for _ in range(5):
            rl.is_allowed("over_key", limit=5, window_seconds=60)
        assert rl.is_allowed("over_key", limit=5, window_seconds=60) is False

    def test_different_keys_are_independent(self):
        rl = InMemoryRateLimiter()
        for _ in range(5):
            rl.is_allowed("key_a", limit=5, window_seconds=60)
        assert rl.is_allowed("key_a", limit=5, window_seconds=60) is False
        assert rl.is_allowed("key_b", limit=5, window_seconds=60) is True

    def test_window_expiry_allows_again(self):
        rl = InMemoryRateLimiter()
        for _ in range(3):
            rl.is_allowed("expiry_test", limit=3, window_seconds=1)
        assert rl.is_allowed("expiry_test", limit=3, window_seconds=1) is False
        time.sleep(1.1)
        assert rl.is_allowed("expiry_test", limit=3, window_seconds=1) is True

    def test_cleanup_removes_stale_entries(self):
        rl = InMemoryRateLimiter()
        rl.is_allowed("stale", limit=5, window_seconds=1)
        # Manually age the timestamps to be > 1 hour old
        rl._requests["stale"] = [time.time() - 7200]  # 2 hours ago
        rl._cleanup()
        assert "stale" not in rl._requests or len(rl._requests.get("stale", [])) == 0

    def test_single_request_allowed(self):
        rl = InMemoryRateLimiter()
        assert rl.is_allowed("single", limit=1, window_seconds=60) is True
        assert rl.is_allowed("single", limit=1, window_seconds=60) is False

    def test_high_limit_allows_many(self):
        rl = InMemoryRateLimiter()
        for _ in range(100):
            assert rl.is_allowed("high", limit=1000, window_seconds=60) is True

    def test_zero_limit_blocks_all(self):
        rl = InMemoryRateLimiter()
        assert rl.is_allowed("zero", limit=0, window_seconds=60) is False

    def test_thread_safety(self):
        """Basic thread safety — concurrent access shouldn't crash."""
        import threading
        rl = InMemoryRateLimiter()
        results = []

        def make_requests():
            for _ in range(50):
                results.append(rl.is_allowed("thread_test", limit=100, window_seconds=60))

        threads = [threading.Thread(target=make_requests) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed since limit=100 and we make 200 total
        assert len(results) == 200
