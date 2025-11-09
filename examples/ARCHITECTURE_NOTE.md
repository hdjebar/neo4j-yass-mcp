# Examples Directory - Architecture Note

## Purpose

The examples in this directory are **standalone demonstrations** that showcase rate limiting concepts in a simplified, self-contained manner for educational purposes.

## Key Differences from Main Codebase

### Main Codebase (`src/neo4j_yass_mcp/`)

**Architecture**: Decorator-based with dependency injection

```python
# src/neo4j_yass_mcp/tool_wrappers.py
class RateLimiterService:
    """Async-safe with asyncio.Lock"""
    async def check_and_record(...) -> tuple[bool, dict]:
        async with self._lock:
            # Thread-safe rate limiting
            ...

# src/neo4j_yass_mcp/server.py
tool_rate_limiter = RateLimiterService()  # Singleton instance

@mcp.tool()
@rate_limit_tool(
    limiter=lambda: tool_rate_limiter,  # Injected dependency
    client_id_extractor=get_client_id_from_context,  # Callback
    limit=10,
    window=60,
    enabled=lambda: tool_rate_limit_enabled,  # Dynamic flag
    tool_name="query_graph",
)
async def query_graph(query: str, ctx: Context) -> dict:
    # Clean business logic - no rate limiting code
    ...
```

**Key Features:**
- ✅ Dependency injection via lambda functions
- ✅ Async-safe with `asyncio.Lock`
- ✅ Dynamic configuration via callbacks
- ✅ Separation of concerns (decorator handles cross-cutting concerns)
- ✅ Testable with mocks

### Examples Directory (`examples/`)

**Architecture**: Self-contained with global state

```python
# examples/rate_limiting_example.py
class RateLimiterService:
    """Simplified without async lock (for clarity)"""
    def check_and_record(...) -> tuple[bool, dict]:
        # Synchronous sliding window logic
        ...

rate_limiter = RateLimiterService()  # Global instance

def rate_limit_mcp_tool(limit: int, window: int):
    """Simple decorator without dependency injection"""
    def decorator(func):
        async def wrapper(*args, ctx: Context = None, **kwargs):
            # Direct reference to global rate_limiter
            is_allowed, rate_info = rate_limiter.check_and_record(...)
            if not is_allowed:
                return {"error": "Rate limited", ...}
            return await func(*args, ctx=ctx, **kwargs)
        return wrapper
    return decorator

@mcp.tool()
@rate_limit_mcp_tool(limit=3, window=10)
async def get_time(ctx: Context) -> dict:
    # Tool logic
    ...
```

**Key Features:**
- ✅ Simpler to understand for educational purposes
- ✅ No dependency injection (direct global reference)
- ✅ Synchronous operations (no async lock)
- ✅ Static configuration (hardcoded limits)
- ✅ Self-contained in single file

## Why Two Different Approaches?

### Main Codebase Priorities
1. **Production-ready**: Thread-safe, testable, maintainable
2. **Scalability**: Proper async handling for high concurrency
3. **Flexibility**: Dynamic configuration, dependency injection
4. **Testability**: Easy to mock and test in isolation

### Examples Directory Priorities
1. **Educational**: Easy to read and understand
2. **Self-contained**: Copy-paste and run immediately
3. **Demonstration**: Shows concepts without production complexity
4. **Clarity**: Simpler code without abstractions

## When to Use Each

### Use Main Codebase Pattern When:
- Building production MCP servers
- Need thread safety and concurrency support
- Want testable, maintainable code
- Require dynamic configuration

### Use Examples Pattern When:
- Learning rate limiting concepts
- Prototyping quickly
- Need a standalone demonstration
- Building simple single-purpose tools

## Migration Path

If you want to adopt the main codebase pattern:

1. **Install the package**: The decorators are available via `neo4j_yass_mcp.tool_wrappers`
2. **Create rate limiter instance**: `tool_rate_limiter = RateLimiterService()`
3. **Apply decorator**: Use `@rate_limit_tool` with dependency injection
4. **Configure dynamically**: Use lambda functions for runtime configuration

See [REFACTORING_SUMMARY.md](../REFACTORING_SUMMARY.md) for full migration guide.

## Summary

| Aspect | Main Codebase | Examples Directory |
|--------|---------------|-------------------|
| **Async Safety** | ✅ `asyncio.Lock` | ❌ No lock (simplified) |
| **Dependency Injection** | ✅ Lambda injection | ❌ Global state |
| **Dynamic Config** | ✅ Runtime callbacks | ❌ Static values |
| **Testability** | ✅ Easy mocking | ⚠️ Harder to test |
| **Complexity** | ⚠️ More abstractions | ✅ Simpler code |
| **Purpose** | 🏭 Production | 📚 Education |

Both approaches are **correct** - they just optimize for different goals.

---

**Last Updated**: 2025-11-09
