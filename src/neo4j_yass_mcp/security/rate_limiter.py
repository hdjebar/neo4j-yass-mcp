"""
Rate limiting for Neo4j YASS MCP Server.

Prevents abuse by limiting the number of queries per time window.
Uses token bucket algorithm for smooth rate limiting with burst support.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Information about rate limit status."""

    allowed: bool
    requests_remaining: int
    reset_time: datetime
    retry_after_seconds: float | None = None


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter with per-client tracking.

    The token bucket algorithm allows burst traffic while maintaining
    an average rate limit. Each request consumes one token.

    Features:
    - Per-client rate limiting (by client_id)
    - Configurable rate and burst capacity
    - Thread-safe implementation
    - Automatic token refill
    """

    def __init__(
        self,
        rate: int = 10,
        per_seconds: int = 60,
        burst: int | None = None,
    ):
        """
        Initialize token bucket rate limiter.

        Args:
            rate: Maximum number of requests allowed per time window
            per_seconds: Time window in seconds (default: 60s)
            burst: Maximum burst capacity (default: rate * 2)
        """
        self.rate = rate
        self.per_seconds = per_seconds
        self.burst = burst or (rate * 2)

        # Token refill rate (tokens per second)
        self.refill_rate = rate / per_seconds

        # Storage for per-client buckets: {client_id: (tokens, last_update)}
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = Lock()

        logger.info(
            f"Rate limiter initialized: {rate} requests per {per_seconds}s, "
            f"burst capacity: {self.burst}"
        )

    def _get_bucket(self, client_id: str) -> tuple[float, float]:
        """
        Get or create bucket for client.

        Returns:
            Tuple of (current_tokens, last_update_timestamp)
        """
        now = time.time()

        if client_id not in self._buckets:
            # New client starts with full bucket
            self._buckets[client_id] = (float(self.burst), now)

        return self._buckets[client_id]

    def _refill_tokens(self, client_id: str) -> float:
        """
        Refill tokens based on elapsed time since last update.

        Returns:
            Current number of tokens after refill
        """
        now = time.time()
        tokens, last_update = self._get_bucket(client_id)

        # Calculate elapsed time and new tokens
        elapsed = now - last_update
        new_tokens = elapsed * self.refill_rate

        # Add tokens but don't exceed burst capacity
        tokens = min(self.burst, tokens + new_tokens)

        # Update bucket
        self._buckets[client_id] = (tokens, now)

        return tokens

    def check_rate_limit(self, client_id: str = "default", cost: int = 1) -> RateLimitInfo:
        """
        Check if request is allowed under rate limit.

        Args:
            client_id: Unique identifier for client (default: "default")
            cost: Number of tokens to consume (default: 1)

        Returns:
            RateLimitInfo with allowance status and metadata
        """
        with self._lock:
            # Refill tokens
            tokens = self._refill_tokens(client_id)

            # Check if enough tokens available
            if tokens >= cost:
                # Consume tokens
                tokens -= cost
                now = time.time()
                self._buckets[client_id] = (tokens, now)

                # Calculate reset time (when bucket will be full again)
                tokens_to_fill = self.burst - tokens
                seconds_to_fill = tokens_to_fill / self.refill_rate
                reset_time = datetime.now() + timedelta(seconds=seconds_to_fill)

                return RateLimitInfo(
                    allowed=True,
                    requests_remaining=int(tokens),
                    reset_time=reset_time,
                )
            else:
                # Not enough tokens - calculate retry time
                tokens_needed = cost - tokens
                retry_after = tokens_needed / self.refill_rate
                reset_time = datetime.now() + timedelta(seconds=retry_after)

                logger.warning(
                    f"Rate limit exceeded for client '{client_id}': "
                    f"{tokens:.2f} tokens available, {cost} needed. "
                    f"Retry after {retry_after:.1f}s"
                )

                return RateLimitInfo(
                    allowed=False,
                    requests_remaining=0,
                    reset_time=reset_time,
                    retry_after_seconds=retry_after,
                )

    def reset_client(self, client_id: str) -> None:
        """Reset rate limit for a specific client."""
        with self._lock:
            if client_id in self._buckets:
                del self._buckets[client_id]
                logger.info(f"Rate limit reset for client '{client_id}'")

    def reset_all(self) -> None:
        """Reset rate limits for all clients."""
        with self._lock:
            count = len(self._buckets)
            self._buckets.clear()
            logger.info(f"Rate limit reset for all clients ({count} total)")

    def get_client_status(self, client_id: str = "default") -> dict:
        """
        Get current rate limit status for a client.

        Returns:
            Dictionary with client rate limit information
        """
        with self._lock:
            tokens = self._refill_tokens(client_id)

            return {
                "client_id": client_id,
                "tokens_available": tokens,
                "capacity": self.burst,
                "rate": f"{self.rate}/{self.per_seconds}s",
                "refill_rate": f"{self.refill_rate:.2f} tokens/second",
            }


# Global rate limiter instance
_rate_limiter: TokenBucketRateLimiter | None = None


def initialize_rate_limiter(
    rate: int = 10,
    per_seconds: int = 60,
    burst: int | None = None,
) -> TokenBucketRateLimiter:
    """
    Initialize global rate limiter.

    Args:
        rate: Maximum requests per time window
        per_seconds: Time window in seconds
        burst: Maximum burst capacity

    Returns:
        Initialized rate limiter instance
    """
    global _rate_limiter
    _rate_limiter = TokenBucketRateLimiter(rate=rate, per_seconds=per_seconds, burst=burst)
    return _rate_limiter


def get_rate_limiter() -> TokenBucketRateLimiter | None:
    """Get global rate limiter instance."""
    return _rate_limiter


def check_rate_limit(
    client_id: str = "default", cost: int = 1
) -> tuple[bool, RateLimitInfo | None]:
    """
    Check rate limit for a client.

    Args:
        client_id: Unique client identifier
        cost: Number of tokens to consume

    Returns:
        Tuple of (allowed, rate_limit_info)
        If rate limiter not initialized, returns (True, None)
    """
    if _rate_limiter is None:
        return True, None

    rate_info = _rate_limiter.check_rate_limit(client_id=client_id, cost=cost)
    return rate_info.allowed, rate_info
