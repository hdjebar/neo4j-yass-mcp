"""
Shared decorators and utilities for MCP tool cross-cutting concerns.

Provides:
- RateLimiterService: sliding window rate limiting with async safety
- rate_limit_tool: decorator for MCP tools
- log_tool_invocation: decorator for consistent structured logging
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

from fastmcp import Context

logger = logging.getLogger(__name__)


class RateLimiterService:
    """Async-safe sliding window rate limiter."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._request_log: defaultdict[str, list[float]] = defaultdict(list)

    async def check_and_record(
        self,
        client_id: str,
        *,
        limit: int,
        window: int,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Check whether a client is within the rate limit and record the request.

        Returns (allowed, info) where info contains rate metadata.
        """
        now = time.time()
        window_start = now - window

        async with self._lock:
            timestamps = self._request_log[client_id]
            # Trim stale timestamps
            timestamps = [ts for ts in timestamps if ts > window_start]
            self._request_log[client_id] = timestamps

            if len(timestamps) >= limit:
                oldest = timestamps[0] if timestamps else now
                reset_time = oldest + window
                retry_after = max(0.0, reset_time - now)
                return False, {
                    "requests_remaining": 0,
                    "reset_time": reset_time,
                    "retry_after": retry_after,
                    "limit": limit,
                    "window": window,
                }

            timestamps.append(now)
            self._request_log[client_id] = timestamps

            requests_remaining = max(0, limit - len(timestamps))
            return True, {
                "requests_remaining": requests_remaining,
                "reset_time": timestamps[0] + window if timestamps else now + window,
                "retry_after": 0.0,
                "limit": limit,
                "window": window,
            }

    def reset(self) -> None:
        """Reset all tracked request data (primarily for tests)."""
        self._request_log.clear()


def log_tool_invocation(tool_name: str) -> Callable:
    """
    Decorator to emit consistent logging around MCP tool invocations.
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx: Context | None = kwargs.get("ctx")
            client_label = _describe_client(ctx)
            start = time.perf_counter()
            logger.info("Tool '%s' invoked (client=%s)", tool_name, client_label)
            try:
                result = await func(*args, **kwargs)
            except Exception:
                logger.exception("Tool '%s' raised exception (client=%s)", tool_name, client_label)
                raise

            duration_ms = (time.perf_counter() - start) * 1000
            success = True
            if isinstance(result, dict) and result.get("success") is False:
                success = False

            level = logging.INFO if success else logging.WARNING
            logger.log(
                level,
                "Tool '%s' completed (client=%s, duration=%.1fms, success=%s)",
                tool_name,
                client_label,
                duration_ms,
                success,
            )
            return result

        return wrapper

    return decorator


def rate_limit_tool(
    *,
    limiter: RateLimiterService | Callable[[], RateLimiterService | None],
    client_id_extractor: Callable[[Context | None], str],
    limit: int,
    window: int,
    enabled: bool | Callable[[], bool],
    tool_name: str,
    build_error_response: Callable[[dict[str, Any]], Any] | None = None,
) -> Callable:
    """
    Decorator to enforce rate limiting for MCP tools.
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            enabled_flag = enabled() if callable(enabled) else enabled
            if not enabled_flag:
                return await func(*args, **kwargs)

            limiter_instance = limiter() if callable(limiter) else limiter
            if limiter_instance is None:
                logger.warning(
                    "Tool '%s' rate limiter is unavailable; skipping enforcement",
                    tool_name,
                )
                return await func(*args, **kwargs)

            ctx: Context | None = kwargs.get("ctx")
            client_id = client_id_extractor(ctx)
            allowed, info = await limiter_instance.check_and_record(
                client_id, limit=limit, window=window
            )

            if not allowed:
                logger.warning(
                    "Tool '%s' rate limit exceeded (client=%s, limit=%s per %ss)",
                    tool_name,
                    client_id,
                    limit,
                    window,
                )
                if build_error_response:
                    return build_error_response(info)
                return {
                    "success": False,
                    "error": f"Rate limit exceeded. Retry after {info['retry_after']:.1f}s",
                    "rate_limited": True,
                    **info,
                }

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _describe_client(ctx: Context | None) -> str:
    if ctx is None:
        return "unknown"
    return (
        getattr(ctx, "session_id", None)
        or getattr(ctx, "client_id", None)
        or getattr(ctx, "request_id", None)
        or "unknown"
    )


__all__ = ["RateLimiterService", "log_tool_invocation", "rate_limit_tool"]
