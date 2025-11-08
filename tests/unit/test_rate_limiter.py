"""
Comprehensive tests for rate limiting functionality.

Tests cover token bucket algorithm, per-client tracking, and rate enforcement.
"""

import time
from datetime import datetime

import pytest

from neo4j_yass_mcp.security.rate_limiter import (
    RateLimitInfo,
    TokenBucketRateLimiter,
    check_rate_limit,
    get_rate_limiter,
    initialize_rate_limiter,
)


class TestTokenBucketBasics:
    """Test basic token bucket functionality."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        assert limiter.rate == 10
        assert limiter.per_seconds == 60
        assert limiter.burst == 20
        assert limiter.refill_rate == 10 / 60  # tokens per second

    def test_default_burst_capacity(self):
        """Test default burst capacity is 2x rate."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60)

        assert limiter.burst == 20  # 2 * rate

    def test_new_client_starts_with_full_bucket(self):
        """Test new client gets full bucket capacity."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        info = limiter.check_rate_limit(client_id="client1")

        assert info.allowed is True
        # Should have close to burst - 1, allowing for minor time-based refill
        assert info.requests_remaining >= 18
        assert info.requests_remaining <= 19


class TestRateLimitChecking:
    """Test rate limit checking and enforcement."""

    def test_request_allowed_with_tokens(self):
        """Test request is allowed when tokens available."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        info = limiter.check_rate_limit(client_id="client1")

        assert info.allowed is True
        assert info.requests_remaining >= 0
        assert info.reset_time > datetime.now()
        assert info.retry_after_seconds is None

    def test_request_blocked_without_tokens(self):
        """Test request is blocked when no tokens available."""
        limiter = TokenBucketRateLimiter(rate=1, per_seconds=60, burst=2)

        # Consume all tokens
        limiter.check_rate_limit(client_id="client1")  # 2 -> 1
        limiter.check_rate_limit(client_id="client1")  # 1 -> 0

        # Next request should be blocked
        info = limiter.check_rate_limit(client_id="client1")

        assert info.allowed is False
        assert info.requests_remaining == 0
        assert info.retry_after_seconds is not None
        assert info.retry_after_seconds > 0

    def test_multiple_tokens_consumed(self):
        """Test consuming multiple tokens at once."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        info = limiter.check_rate_limit(client_id="client1", cost=5)

        assert info.allowed is True
        # Should have close to 15, allowing for minor time-based refill
        assert info.requests_remaining >= 14
        assert info.requests_remaining <= 15

    def test_insufficient_tokens_for_cost(self):
        """Test request blocked when cost exceeds available tokens."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        # Consume most tokens
        limiter.check_rate_limit(client_id="client1", cost=18)

        # Try to consume more than available
        info = limiter.check_rate_limit(client_id="client1", cost=5)

        assert info.allowed is False
        assert info.requests_remaining == 0


class TestTokenRefill:
    """Test token refill mechanism."""

    def test_tokens_refill_over_time(self):
        """Test tokens refill at the correct rate."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=1, burst=20)

        # Consume all tokens
        limiter.check_rate_limit(client_id="client1", cost=20)

        # Wait for refill (0.5 seconds = 5 tokens at 10 tokens/second)
        time.sleep(0.5)

        # Check tokens refilled
        info = limiter.check_rate_limit(client_id="client1", cost=4)
        assert info.allowed is True

    def test_tokens_dont_exceed_burst(self):
        """Test tokens don't exceed burst capacity."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=1, burst=20)

        # Start with full bucket
        limiter.check_rate_limit(client_id="client1")

        # Wait long enough to refill many times over
        time.sleep(2)

        # Get bucket status
        status = limiter.get_client_status(client_id="client1")

        # Should be at burst capacity, not higher
        assert status["tokens_available"] <= 20

    def test_refill_rate_calculation(self):
        """Test token refill rate is calculated correctly."""
        limiter = TokenBucketRateLimiter(rate=60, per_seconds=60, burst=100)

        # Refill rate should be 1 token per second
        assert limiter.refill_rate == 1.0


class TestPerClientTracking:
    """Test per-client rate limiting."""

    def test_different_clients_independent_buckets(self):
        """Test different clients have independent rate limits."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=5)

        # Client 1 consumes all tokens
        for _ in range(5):
            limiter.check_rate_limit(client_id="client1")

        # Client 1 should be blocked
        info1 = limiter.check_rate_limit(client_id="client1")
        assert info1.allowed is False

        # Client 2 should still have tokens
        info2 = limiter.check_rate_limit(client_id="client2")
        assert info2.allowed is True

    def test_client_reset(self):
        """Test resetting rate limit for specific client."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=5)

        # Consume all tokens
        for _ in range(5):
            limiter.check_rate_limit(client_id="client1")

        # Should be blocked
        info = limiter.check_rate_limit(client_id="client1")
        assert info.allowed is False

        # Reset client
        limiter.reset_client("client1")

        # Should have full bucket again
        info = limiter.check_rate_limit(client_id="client1")
        assert info.allowed is True
        # Should have close to 4, allowing for minor time-based refill
        assert info.requests_remaining >= 3
        assert info.requests_remaining <= 4

    def test_reset_all_clients(self):
        """Test resetting all client rate limits."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=3)

        # Create multiple clients and consume tokens
        limiter.check_rate_limit(client_id="client1", cost=3)
        limiter.check_rate_limit(client_id="client2", cost=3)

        # Reset all
        limiter.reset_all()

        # Both should have full buckets
        info1 = limiter.check_rate_limit(client_id="client1")
        info2 = limiter.check_rate_limit(client_id="client2")

        assert info1.allowed is True
        assert info2.allowed is True


class TestClientStatus:
    """Test client status queries."""

    def test_get_client_status(self):
        """Test getting client rate limit status."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        # Consume some tokens
        limiter.check_rate_limit(client_id="client1", cost=5)

        # Get status
        status = limiter.get_client_status(client_id="client1")

        assert status["client_id"] == "client1"
        assert status["capacity"] == 20
        assert status["rate"] == "10/60s"
        assert "tokens_available" in status
        assert "refill_rate" in status

    def test_new_client_status(self):
        """Test getting status for new client."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        status = limiter.get_client_status(client_id="new_client")

        # New client should have full bucket (allowing for minor time-based refill)
        assert abs(status["tokens_available"] - 20) < 0.01


class TestRateLimitInfo:
    """Test RateLimitInfo dataclass."""

    def test_allowed_info_structure(self):
        """Test structure of allowed rate limit info."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        info = limiter.check_rate_limit(client_id="client1")

        assert isinstance(info, RateLimitInfo)
        assert info.allowed is True
        assert isinstance(info.requests_remaining, int)
        assert isinstance(info.reset_time, datetime)
        assert info.retry_after_seconds is None

    def test_blocked_info_structure(self):
        """Test structure of blocked rate limit info."""
        limiter = TokenBucketRateLimiter(rate=1, per_seconds=600, burst=2)

        # Consume all tokens
        limiter.check_rate_limit(client_id="client1")  # 2 -> 1
        limiter.check_rate_limit(client_id="client1")  # 1 -> 0

        # Get blocked info (slow refill rate ensures no refill between calls)
        info = limiter.check_rate_limit(client_id="client1")

        assert isinstance(info, RateLimitInfo)
        assert info.allowed is False
        assert info.requests_remaining == 0
        assert isinstance(info.reset_time, datetime)
        assert isinstance(info.retry_after_seconds, float)
        assert info.retry_after_seconds > 0


class TestGlobalRateLimiter:
    """Test global rate limiter functions."""

    def test_initialize_rate_limiter(self):
        """Test global rate limiter initialization."""
        limiter = initialize_rate_limiter(rate=10, per_seconds=60, burst=20)

        assert limiter is not None
        assert limiter.rate == 10
        assert limiter.burst == 20

        # Should be accessible via get_rate_limiter
        assert get_rate_limiter() == limiter

    def test_check_rate_limit_with_initialized_limiter(self):
        """Test check_rate_limit with initialized global limiter."""
        initialize_rate_limiter(rate=10, per_seconds=60, burst=20)

        is_allowed, info = check_rate_limit(client_id="test")

        assert is_allowed is True
        assert info is not None
        assert isinstance(info, RateLimitInfo)

    def test_check_rate_limit_not_initialized(self):
        """Test check_rate_limit when limiter not initialized."""
        # Reset global limiter
        from neo4j_yass_mcp.security import rate_limiter

        rate_limiter._rate_limiter = None

        is_allowed, info = check_rate_limit(client_id="test")

        assert is_allowed is True
        assert info is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_cost_request(self):
        """Test request with zero cost."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        info = limiter.check_rate_limit(client_id="client1", cost=0)

        assert info.allowed is True
        # Should have close to 20 (no tokens consumed), allowing for minor time-based refill
        assert info.requests_remaining >= 19
        assert info.requests_remaining <= 20

    def test_very_high_cost_request(self):
        """Test request with cost exceeding burst capacity."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        info = limiter.check_rate_limit(client_id="client1", cost=100)

        assert info.allowed is False
        assert info.retry_after_seconds is not None

    def test_rapid_sequential_requests(self):
        """Test many rapid sequential requests."""
        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=10)

        allowed_count = 0
        blocked_count = 0

        for _ in range(20):
            info = limiter.check_rate_limit(client_id="client1")
            if info.allowed:
                allowed_count += 1
            else:
                blocked_count += 1

        # Should allow burst capacity, block the rest
        assert allowed_count == 10
        assert blocked_count == 10


class TestThreadSafety:
    """Test thread safety of rate limiter."""

    def test_concurrent_access(self):
        """Test rate limiter handles concurrent access correctly."""
        import concurrent.futures

        limiter = TokenBucketRateLimiter(rate=10, per_seconds=60, burst=20)

        def make_request(client_id):
            return limiter.check_rate_limit(client_id=f"client{client_id}")

        # Make concurrent requests (100 requests to 3 clients = ~33 each)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i % 3) for i in range(100)]
            results = [f.result() for f in futures]

        # Should have a mix of allowed and blocked (burst=20, so >20 per client should be blocked)
        allowed = sum(1 for r in results if r.allowed)
        blocked = sum(1 for r in results if not r.allowed)

        assert allowed > 0
        assert blocked > 0
        assert allowed + blocked == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
