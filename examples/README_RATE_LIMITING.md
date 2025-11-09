# Rate Limiting Example for FastMCP + Starlette

This example demonstrates production-ready rate limiting for both HTTP endpoints and MCP tools using standard Python logging.

## Features

✅ **Dual Rate Limiting**:
- HTTP endpoints: Via Starlette middleware (IP-based)
- MCP tools: Via Context-based decorator (session-based)

✅ **Standard Logging**:
- File logging (`rate_limiting.log`)
- Console logging with timestamps
- No in-memory counters for metrics

✅ **Proper Client Identification**:
- HTTP: Uses client IP address
- MCP: Uses FastMCP `Context.session_id` for stable per-session limiting

✅ **Sliding Window Algorithm**:
- Accurate request counting
- Automatic cleanup of old timestamps
- Per-client isolation

## Quick Start

### 1. Install Dependencies

```bash
pip install fastmcp starlette uvicorn
```

### 2. Run the Example

```bash
cd examples
python rate_limiting_example.py
```

The server will start on `http://localhost:8000`

### 3. Test HTTP Rate Limiting

**Test normal requests:**
```bash
curl http://localhost:8000/
curl http://localhost:8000/stats
```

**Test rate limiting (20 requests/minute for HTTP):**
```bash
# This script will hit the rate limit
for i in {1..25}; do
  echo "Request $i:"
  curl -s http://localhost:8000/ | jq .status || echo "Rate limited!"
  sleep 0.5
done
```

### 4. Test MCP Tool Rate Limiting

**Using MCP client:**
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_rate_limiting():
    server_params = StdioServerParameters(
        command="python",
        args=["rate_limiting_example.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Make 3 requests (should succeed)
            for i in range(3):
                result = await session.call_tool("get_time", {})
                print(f"Request {i+1}: {result}")

            # 4th request should be rate limited
            result = await session.call_tool("get_time", {})
            print(f"Request 4 (should fail): {result}")
```

## Architecture

### RateLimiterService

Centralized service managing rate limit state:

```python
class RateLimiterService:
    def __init__(self, default_limit: int = 10, default_window: int = 60):
        # Sliding window: {client_id: [timestamp1, timestamp2, ...]}
        self._request_log: dict[str, list[float]] = defaultdict(list)

    def check_and_record(self, client_id, limit, window) -> tuple[bool, dict]:
        # 1. Remove old timestamps
        # 2. Check if limit exceeded
        # 3. Record new request if allowed
        # 4. Return (is_allowed, rate_info)
```

**Key Features:**
- Sliding window algorithm (not fixed window)
- Automatic cleanup of expired timestamps
- Detailed rate info (remaining requests, reset time, retry_after)

### HTTP Rate Limiting (Middleware)

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        client_id = f"http_{request.client.host}"
        is_allowed, rate_info = limiter.check_and_record(client_id)

        if not is_allowed:
            return JSONResponse({...}, status_code=429)

        response = await call_next(request)
        # Add X-RateLimit-* headers
        return response
```

**Applied to:** ALL HTTP endpoints
**Client ID:** `http_{IP_ADDRESS}`
**Default:** 20 requests/minute

### MCP Tool Rate Limiting (Decorator)

```python
def rate_limit_mcp_tool(limit: int, window: int):
    def decorator(func):
        async def wrapper(*args, ctx: Context = None, **kwargs):
            # Extract session_id from Context
            client_id = f"mcp_session_{ctx.session_id}"

            is_allowed, rate_info = limiter.check_and_record(client_id)

            if not is_allowed:
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "rate_limited": True,
                    "retry_after": rate_info["retry_after"],
                }

            return await func(*args, ctx=ctx, **kwargs)
        return wrapper
    return decorator
```

**Usage:**
```python
@mcp.tool()
@rate_limit_mcp_tool(limit=3, window=10)  # 3 req/10s
async def get_time(ctx: Context) -> dict:
    return {"time": time.strftime("%Y-%m-%d %H:%M:%S")}
```

**Client ID:** `mcp_session_{SESSION_ID}` (stable across requests)
**Per-tool limits:** Configured individually

## Configuration

### Global Rate Limiter

```python
rate_limiter = RateLimiterService(
    default_limit=10,    # Default max requests
    default_window=60,   # Default time window (seconds)
)
```

### HTTP Middleware

```python
app.add_middleware(
    RateLimitMiddleware,
    limiter=rate_limiter,
    limit=20,      # HTTP-specific limit
    window=60,     # HTTP-specific window
)
```

### MCP Tool Decorator

```python
@rate_limit_mcp_tool(limit=3, window=10)  # Per-tool configuration
```

## Logging

### Log Levels

- **INFO**: Service initialization, request summaries
- **DEBUG**: Individual request details
- **WARNING**: Rate limit violations

### Log Outputs

**Console:**
```
2025-11-09 14:32:15,123 - __main__ - INFO - RateLimiterService initialized: 10 req/60s
2025-11-09 14:32:20,456 - __main__ - WARNING - Rate limit exceeded for client 'http_127.0.0.1'
```

**File (`rate_limiting.log`):**
```
2025-11-09 14:32:15,123 - __main__ - INFO - RateLimiterService initialized: 10 req/60s
2025-11-09 14:32:15,456 - __main__ - INFO - RateLimitMiddleware initialized: 20 req/60s for HTTP
2025-11-09 14:32:20,789 - __main__ - DEBUG - Request allowed for client 'mcp_session_abc123': 1/3 requests used
```

## Comparison with In-Memory Approach

### ❌ In-Memory Counters (Bad)
```python
request_count = defaultdict(int)  # Just counts

# Problems:
# - No sliding window (inaccurate)
# - No observability
# - No persistent logs
```

### ✅ Timestamp Logging (Good)
```python
request_log = defaultdict(list)  # Stores timestamps

# Benefits:
# - Sliding window (accurate)
# - Full observability via logging
# - Detailed rate info
# - Easy debugging
```

## Key Differences from Broken Example

### ❌ **Original Code (Broken)**

```python
# WRONG: Returns Starlette Response for MCP tool
@tool("get_time")
@rate_limit(limit=3, window=10)
async def get_time(request: Request):  # ❌ No Request in MCP
    return JSONResponse({...})  # ❌ Wrong response type
```

**Problems:**
1. MCP tools don't receive `Request` objects
2. Returns `JSONResponse` instead of dict
3. Uses IP-based limiting (not session-based)

### ✅ **This Example (Correct)**

```python
# CORRECT: Returns dict for MCP tool
@mcp.tool()
@rate_limit_mcp_tool(limit=3, window=10)
async def get_time(ctx: Context) -> dict:  # ✅ Uses Context
    return {"time": "..."}  # ✅ Returns dict
```

**Fixes:**
1. Uses `Context` (provided by FastMCP)
2. Returns dict (MCP format)
3. Uses `session_id` for stable identification

## Production Deployment

### Environment Variables

```bash
# .env
RATE_LIMIT_HTTP_LIMIT=20
RATE_LIMIT_HTTP_WINDOW=60
RATE_LIMIT_MCP_DEFAULT_LIMIT=10
RATE_LIMIT_MCP_DEFAULT_WINDOW=60
LOG_LEVEL=INFO
```

### Docker

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY rate_limiting_example.py .

ENV LOG_LEVEL=INFO
ENV RATE_LIMIT_HTTP_LIMIT=20

CMD ["python", "rate_limiting_example.py"]
```

### Redis Backend (Future)

For multi-worker deployments, replace `RateLimiterService` with Redis:

```python
class RedisRateLimiter(RateLimiterService):
    def __init__(self, redis_url: str, **kwargs):
        super().__init__(**kwargs)
        self.redis = redis.from_url(redis_url)

    def check_and_record(self, client_id, limit, window):
        # Use Redis sorted sets for distributed rate limiting
        key = f"rate_limit:{client_id}"
        now = time.time()

        # Remove old entries
        self.redis.zremrangebyscore(key, 0, now - window)

        # Check count
        count = self.redis.zcard(key)
        if count >= limit:
            return False, {...}

        # Record request
        self.redis.zadd(key, {now: now})
        self.redis.expire(key, window)

        return True, {...}
```

## Testing

### Unit Tests

```python
import pytest
from rate_limiting_example import RateLimiterService

def test_rate_limiter_allows_within_limit():
    limiter = RateLimiterService(default_limit=3, default_window=10)

    # Should allow 3 requests
    assert limiter.check_and_record("client1")[0] is True
    assert limiter.check_and_record("client1")[0] is True
    assert limiter.check_and_record("client1")[0] is True

    # 4th should be blocked
    assert limiter.check_and_record("client1")[0] is False

def test_rate_limiter_isolates_clients():
    limiter = RateLimiterService(default_limit=1, default_window=10)

    # Client 1 exhausts quota
    assert limiter.check_and_record("client1")[0] is True
    assert limiter.check_and_record("client1")[0] is False

    # Client 2 still has quota
    assert limiter.check_and_record("client2")[0] is True
```

### Integration Tests

```bash
# Test HTTP rate limiting
pytest tests/integration/test_http_rate_limiting.py

# Test MCP tool rate limiting
pytest tests/integration/test_mcp_rate_limiting.py
```

## Next Steps

1. **Phase 1 Refactoring** (Current Example ✅)
   - ✅ Centralized `RateLimiterService`
   - ✅ Standard logging
   - ✅ Proper client identification

2. **Phase 2: Redis Backend**
   - Distributed rate limiting
   - Multi-worker support
   - Persistent state

3. **Phase 3: Metrics**
   - Prometheus integration
   - Grafana dashboards
   - Real-time monitoring

4. **Phase 4: Advanced Features**
   - Per-user quotas
   - Tiered rate limits
   - Dynamic adjustment

## References

- [FastMCP Documentation](https://github.com/anthropics/fastmcp)
- [Starlette Middleware](https://www.starlette.io/middleware/)
- [Rate Limiting Algorithms](https://en.wikipedia.org/wiki/Rate_limiting)
- [Sliding Window](https://medium.com/@the.york.wei/rate-limiting-sliding-window-vs-token-bucket-7e5fc0e48b76)
