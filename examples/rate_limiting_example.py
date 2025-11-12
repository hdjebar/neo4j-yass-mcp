#!/usr/bin/env python3
"""
Complete Rate Limiting Example for FastMCP + Starlette

Demonstrates:
1. HTTP rate limiting via Starlette middleware
2. MCP tool rate limiting via Context-based decorator
3. Standard Python logging (not in-memory storage)
4. Proper per-session client identification

Architecture:
- RateLimiterService: Manages rate limit state using sliding window algorithm
- RateLimitMiddleware: Applies rate limiting to HTTP endpoints
- rate_limit_mcp_tool: Decorator for FastMCP tools using Context
"""

import asyncio
import logging
import time
from collections import defaultdict
from functools import wraps
from typing import Any

from fastmcp import Context, FastMCP
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rate_limiting.log"),
    ],
)

logger = logging.getLogger(__name__)


# ============================================================================
# RATE LIMITER SERVICE (Shared State)
# ============================================================================


class RateLimiterService:
    """
    Centralized rate limiting service using sliding window algorithm.

    Uses standard logging instead of in-memory counters for observability.
    Maintains per-client request timestamps for accurate rate limiting.
    """

    def __init__(self, default_limit: int = 10, default_window: int = 60):
        """
        Initialize rate limiter service.

        Args:
            default_limit: Maximum requests per window
            default_window: Time window in seconds
        """
        self.default_limit = default_limit
        self.default_window = default_window
        # Store: {client_id: [timestamp1, timestamp2, ...]}
        self._request_log: dict[str, list[float]] = defaultdict(list)
        logger.info(f"RateLimiterService initialized: {default_limit} req/{default_window}s")

    def check_and_record(
        self, client_id: str, limit: int | None = None, window: int | None = None
    ) -> tuple[bool, dict[str, Any]]:
        """
        Check if request is allowed and record it if so.

        Args:
            client_id: Unique identifier for the client
            limit: Custom limit (overrides default)
            window: Custom window (overrides default)

        Returns:
            Tuple of (is_allowed, rate_info)
            rate_info contains: requests_remaining, reset_time, retry_after
        """
        limit = limit or self.default_limit
        window = window or self.default_window
        now = time.time()
        window_start = now - window

        # Remove old timestamps (sliding window)
        self._request_log[client_id] = [
            ts for ts in self._request_log[client_id] if ts > window_start
        ]

        current_count = len(self._request_log[client_id])
        requests_remaining = max(0, limit - current_count)

        if current_count >= limit:
            # Rate limit exceeded
            oldest_request = (
                min(self._request_log[client_id]) if self._request_log[client_id] else now
            )
            reset_time = oldest_request + window
            retry_after = max(0, reset_time - now)

            logger.warning(
                f"Rate limit exceeded for client '{client_id}': "
                f"{current_count}/{limit} requests in {window}s window. "
                f"Retry after {retry_after:.1f}s"
            )

            return False, {
                "requests_remaining": 0,
                "reset_time": reset_time,
                "retry_after": retry_after,
                "limit": limit,
                "window": window,
            }

        # Allow request and record timestamp
        self._request_log[client_id].append(now)

        logger.debug(
            f"Request allowed for client '{client_id}': "
            f"{current_count + 1}/{limit} requests used. "
            f"{requests_remaining - 1} remaining"
        )

        return True, {
            "requests_remaining": requests_remaining - 1,
            "reset_time": now + window,
            "retry_after": 0,
            "limit": limit,
            "window": window,
        }

    def get_stats(self, client_id: str) -> dict[str, Any]:
        """Get current rate limit stats for a client."""
        now = time.time()
        window_start = now - self.default_window
        self._request_log[client_id] = [
            ts for ts in self._request_log[client_id] if ts > window_start
        ]

        current_count = len(self._request_log[client_id])
        return {
            "client_id": client_id,
            "current_requests": current_count,
            "limit": self.default_limit,
            "window": self.default_window,
            "requests_remaining": max(0, self.default_limit - current_count),
        }


# Global rate limiter instance
rate_limiter = RateLimiterService(default_limit=10, default_window=60)


# ============================================================================
# STARLETTE MIDDLEWARE (HTTP Rate Limiting)
# ============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware for HTTP rate limiting.

    Uses client IP address for identification.
    Applies to all HTTP endpoints (not MCP tools).
    """

    def __init__(self, app, limiter: RateLimiterService, limit: int = 20, window: int = 60):
        """
        Initialize HTTP rate limiting middleware.

        Args:
            app: Starlette application
            limiter: RateLimiterService instance
            limit: Max requests per window for HTTP endpoints
            window: Time window in seconds
        """
        super().__init__(app)
        self.limiter = limiter
        self.limit = limit
        self.window = window
        logger.info(f"RateLimitMiddleware initialized: {limit} req/{window}s for HTTP")

    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiter."""
        # Extract client IP
        client_ip = request.client.host if request.client else "unknown"
        client_id = f"http_{client_ip}"

        # Check rate limit
        is_allowed, rate_info = self.limiter.check_and_record(
            client_id, limit=self.limit, window=self.window
        )

        if not is_allowed:
            logger.warning(f"HTTP rate limit exceeded for {client_ip} on {request.url.path}")
            return JSONResponse(
                {
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Retry after {rate_info['retry_after']:.1f}s",
                    "limit": rate_info["limit"],
                    "window": rate_info["window"],
                    "retry_after": rate_info["retry_after"],
                },
                status_code=429,
                headers={"Retry-After": str(int(rate_info["retry_after"]))},
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["requests_remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(rate_info["reset_time"]))

        return response


# ============================================================================
# MCP TOOL DECORATOR (FastMCP Context-based Rate Limiting)
# ============================================================================


def rate_limit_mcp_tool(limit: int = 5, window: int = 10):
    """
    Rate limit decorator for FastMCP tools using Context.

    Uses FastMCP Context for stable session identification.
    Returns error as dict (MCP format, not HTTP response).

    Args:
        limit: Maximum requests per window
        window: Time window in seconds

    Example:
        @mcp.tool()
        @rate_limit_mcp_tool(limit=3, window=10)
        async def my_tool(ctx: Context, arg: str) -> dict:
            return {"result": "success"}
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, ctx: Context | None = None, **kwargs):
            # Extract client ID from FastMCP Context
            if ctx and ctx.session_id:
                client_id = f"mcp_session_{ctx.session_id}"
            elif ctx and ctx.client_id:
                client_id = f"mcp_client_{ctx.client_id}"
            else:
                client_id = "mcp_unknown"
                logger.warning(
                    f"No session_id in Context for {func.__name__}, using shared 'unknown' bucket"
                )

            # Check rate limit
            is_allowed, rate_info = rate_limiter.check_and_record(
                client_id, limit=limit, window=window
            )

            if not is_allowed:
                logger.warning(f"MCP tool '{func.__name__}' rate limit exceeded for {client_id}")
                # Return error as dict (MCP format)
                return {
                    "success": False,
                    "error": f"Rate limit exceeded. Retry after {rate_info['retry_after']:.1f}s",
                    "rate_limited": True,
                    "retry_after": rate_info["retry_after"],
                    "limit": rate_info["limit"],
                    "window": rate_info["window"],
                }

            # Log successful request
            logger.debug(
                f"MCP tool '{func.__name__}' called by {client_id}. "
                f"{rate_info['requests_remaining']} requests remaining"
            )

            # Proceed with function
            return await func(*args, ctx=ctx, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# FASTMCP + STARLETTE SETUP
# ============================================================================

# Initialize FastMCP
mcp = FastMCP(title="Rate-Limited FastMCP Example")

# Initialize Starlette
app = Starlette(debug=True)

# Add HTTP rate limiting middleware (20 req/min for HTTP endpoints)
app.add_middleware(
    RateLimitMiddleware,
    limiter=rate_limiter,
    limit=20,
    window=60,
)

# Attach MCP to Starlette
mcp.attach_to(app)


# ============================================================================
# EXAMPLE MCP TOOLS (with rate limiting)
# ============================================================================


@mcp.tool()
@rate_limit_mcp_tool(limit=3, window=10)  # 3 requests per 10 seconds
async def get_time(ctx: Context) -> dict:
    """
    Get current server time (rate limited: 3 req/10s).

    This demonstrates MCP tool rate limiting using Context-based
    session identification.
    """
    return {
        "success": True,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "session_id": ctx.session_id if ctx else "unknown",
    }


@mcp.tool()
@rate_limit_mcp_tool(limit=10, window=60)  # 10 requests per minute
async def heavy_operation(ctx: Context, data: str) -> dict:
    """
    Simulate heavy operation (rate limited: 10 req/min).

    Args:
        data: Input data to process

    Returns:
        Result dictionary with success status
    """
    logger.info(f"Processing heavy operation for data: {data[:50]}")

    # Simulate processing without blocking the event loop
    await asyncio.sleep(0.1)

    return {
        "success": True,
        "processed": len(data),
        "result": f"Processed {len(data)} characters",
    }


# ============================================================================
# EXAMPLE HTTP ENDPOINTS (rate limited by middleware)
# ============================================================================


@app.route("/")
async def index(request: Request):
    """Root endpoint (rate limited by middleware)."""
    return JSONResponse(
        {
            "status": "running",
            "service": "FastMCP + Starlette Rate Limiting Example",
            "endpoints": {
                "/": "This page",
                "/stats": "Rate limit statistics",
                "/health": "Health check",
            },
        }
    )


@app.route("/stats")
async def stats(request: Request):
    """Get rate limit stats for current client."""
    client_ip = request.client.host if request.client else "unknown"
    client_id = f"http_{client_ip}"

    stats = rate_limiter.get_stats(client_id)

    return JSONResponse(
        {
            "client_ip": client_ip,
            "rate_limit_stats": stats,
            "message": f"You have {stats['requests_remaining']} requests remaining",
        }
    )


@app.route("/health")
async def health(request: Request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy"})


# ============================================================================
# MAIN (Run Server)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastMCP + Starlette with rate limiting...")
    logger.info("HTTP endpoints rate limited at 20 req/min")
    logger.info("MCP tools have individual rate limits (see tool docstrings)")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
