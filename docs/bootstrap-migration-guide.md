# Bootstrap Module Migration Guide

This guide explains how to use the new `bootstrap.py` module for better state management and multi-instance support.

## Table of Contents
- [Overview](#overview)
- [Current State (v1.3.0)](#current-state-v130)
- [Usage Patterns](#usage-patterns)
- [Migration Path](#migration-path)
- [Benefits](#benefits)
- [Examples](#examples)

## Overview

The `bootstrap.py` module provides a clean separation between initialization logic and runtime behavior, eliminating import-time side effects.

### The Problem

Previously, `server.py` executed initialization code at import time:

```python
# server.py - EXECUTED ON IMPORT!
_config = RuntimeConfig.from_env()
initialize_audit_logger()
if _config.sanitizer.enabled:
    initialize_sanitizer(...)
# ... more initialization

# Global state
graph = None
chain = None
```

**Issues:**
- ❌ Tests cannot reconfigure server without reloading Python
- ❌ Subprocesses inherit parent's global state
- ❌ Cannot run multiple instances with different configs
- ❌ Hard to reason about initialization order

### The Solution

`bootstrap.py` provides explicit initialization:

```python
from neo4j_yass_mcp.bootstrap import initialize_server_state

# Explicit, controllable initialization
state = initialize_server_state()
graph = state.graph
config = state.config
```

**Benefits:**
- ✅ No import-time side effects
- ✅ Multi-instance support
- ✅ Better test isolation
- ✅ Clear initialization order

## Current State (v1.3.0)

### Status: Opt-In Foundation

The bootstrap module is **available but optional** in v1.3.0:

- ✅ `bootstrap.py` module fully implemented and tested
- ✅ All tests passing (11 bootstrap tests + 543 existing tests)
- ✅ 100% backwards compatible
- ⏳ `server.py` still uses import-time initialization (unchanged)
- ⏳ Full migration planned for future releases

### Why Gradual?

We're taking a conservative, incremental approach:

1. **v1.3.0 (Current)**: Bootstrap foundation - opt-in, fully tested
2. **v1.4.0 (Future)**: Migrate `server.py` to use bootstrap internally
3. **v1.5.0 (Future)**: Remove import-time side effects completely

This ensures stability while enabling new use cases immediately.

## Usage Patterns

### Pattern 1: Default (Lazy Initialization)

Works exactly like before, but with lazy init:

```python
from neo4j_yass_mcp.bootstrap import get_server_state

# First call initializes, subsequent calls return cached state
state = get_server_state()
graph = state.graph
config = state.config
```

### Pattern 2: Explicit Initialization

Full control over initialization:

```python
from neo4j_yass_mcp.bootstrap import initialize_server_state
from neo4j_yass_mcp.config import RuntimeConfig

# Create custom config
config = RuntimeConfig.from_env()

# Initialize with custom config
state = initialize_server_state(config=config)

# Use state
graph = state.graph
chain = state.chain
```

### Pattern 3: Multi-Instance

Run multiple independent server instances:

```python
from neo4j_yass_mcp.bootstrap import initialize_server_state

# Instance 1: Production database
config1 = RuntimeConfig(neo4j_uri="bolt://prod:7687", ...)
state1 = initialize_server_state(config1)

# Instance 2: Development database
config2 = RuntimeConfig(neo4j_uri="bolt://dev:7687", ...)
state2 = initialize_server_state(config2)

# Each state is completely independent
state1.graph  # Connected to prod
state2.graph  # Connected to dev
```

### Pattern 4: Test Isolation

Clean state for each test:

```python
import pytest
from neo4j_yass_mcp.bootstrap import (
    initialize_server_state,
    set_server_state,
    reset_server_state,
)

@pytest.fixture
def isolated_server_state():
    """Provide isolated server state for testing."""
    # Create test config
    test_config = RuntimeConfig(
        neo4j_uri="bolt://test:7687",
        sanitizer_enabled=True,
        # ... test settings
    )

    # Initialize and set as current
    test_state = initialize_server_state(test_config)
    set_server_state(test_state)

    yield test_state

    # Cleanup
    reset_server_state()

def test_with_isolated_state(isolated_server_state):
    """Test with clean, isolated state."""
    assert isolated_server_state.graph is None
    # Test code here
    # State automatically cleaned up after test
```

## Migration Path

### Phase 3.2 (Current Release - v1.3.0)

**Status**: ✅ Complete

- Bootstrap module created
- Comprehensive tests added
- Documentation written
- No changes to `server.py` (backwards compatible)

**For Users**: Bootstrap is available but optional. Existing code works unchanged.

### Phase 3.3 (Future - v1.4.0)

**Planned Changes**:
1. Update `server.py` to use bootstrap internally
2. Replace module-level globals with state delegation
3. Maintain backwards-compatible API

**For Users**: Still backwards compatible. Can start using bootstrap patterns.

### Phase 3.4 (Future - v1.5.0)

**Planned Changes**:
1. Remove import-time side effects from `server.py`
2. Make `initialize_server_state()` required for new instances
3. Update `main()` entry point

**For Users**: Breaking changes possible. Migration guide will be provided.

## Benefits

### 1. Multi-Instance Support

```python
# Production API server
prod_state = initialize_server_state(prod_config)
prod_app = create_app(prod_state)

# Development API server (same process!)
dev_state = initialize_server_state(dev_config)
dev_app = create_app(dev_state)

# Run both simultaneously
```

### 2. Better Testing

```python
# Before: Tests interfere with each other
def test_a():
    # Modifies global state
    server.graph = Mock()

def test_b():
    # Sees modified state from test_a!

# After: Complete isolation
def test_a(isolated_state):
    isolated_state.graph = Mock()

def test_b(isolated_state):
    # Fresh state, no interference!
```

### 3. Clear Dependencies

```python
# ServerState makes all dependencies explicit
@dataclass
class ServerState:
    config: RuntimeConfig
    mcp: FastMCP
    graph: SecureNeo4jGraph | None
    chain: GraphCypherQAChain | None
    tool_rate_limiter: RateLimiterService
    # ... all state in one place
```

### 4. Resource Cleanup

```python
from neo4j_yass_mcp.bootstrap import cleanup

try:
    state = initialize_server_state()
    # ... use server
finally:
    cleanup()  # Properly closes connections, shuts down threads
```

## Examples

### Example 1: Multi-Environment Testing

```python
"""Test against multiple Neo4j versions simultaneously."""
import pytest
from neo4j_yass_mcp.bootstrap import initialize_server_state

@pytest.fixture(params=["4.4", "5.0", "5.1"])
def neo4j_version(request):
    """Test against multiple Neo4j versions."""
    version = request.param
    config = RuntimeConfig(
        neo4j_uri=f"bolt://neo4j-{version}:7687",
        neo4j_username="neo4j",
        neo4j_password="password",
    )
    return initialize_server_state(config)

def test_query_compatibility(neo4j_version):
    """Verify queries work across Neo4j versions."""
    state = neo4j_version
    # Test runs 3 times, once per version
    assert state.graph is not None
```

### Example 2: Request-Scoped State (Future)

```python
"""Each HTTP request gets isolated state (future pattern)."""
from fastapi import FastAPI, Depends
from neo4j_yass_mcp.bootstrap import initialize_server_state

app = FastAPI()

def get_request_state():
    """Create fresh state per request."""
    return initialize_server_state()

@app.get("/query")
async def query_graph(
    question: str,
    state: ServerState = Depends(get_request_state)
):
    """Each request gets isolated state."""
    return await query_graph_impl(question, state)
```

### Example 3: Blue-Green Deployment

```python
"""Gradually migrate traffic between configs."""
import random
from neo4j_yass_mcp.bootstrap import initialize_server_state

# Blue deployment (old config)
blue_state = initialize_server_state(old_config)

# Green deployment (new config)
green_state = initialize_server_state(new_config)

def handle_request(request):
    # Gradual traffic shift
    if random.random() < TRAFFIC_TO_GREEN:
        return process_with_state(request, green_state)
    else:
        return process_with_state(request, blue_state)
```

## API Reference

### Functions

#### `initialize_server_state(config=None, mcp_instance=None) -> ServerState`

Initialize server state with explicit configuration.

**Parameters:**
- `config` (RuntimeConfig, optional): Configuration object. Loads from environment if None.
- `mcp_instance` (FastMCP, optional): FastMCP instance. Creates new if None.

**Returns:**
- `ServerState`: Initialized server state

**Example:**
```python
from neo4j_yass_mcp.bootstrap import initialize_server_state
state = initialize_server_state()
```

#### `get_server_state() -> ServerState`

Get current server state (lazy initialization).

**Returns:**
- `ServerState`: Current server state

**Example:**
```python
from neo4j_yass_mcp.bootstrap import get_server_state
state = get_server_state()  # Auto-initializes if needed
```

#### `set_server_state(state: ServerState) -> None`

Set custom server state as current.

**Parameters:**
- `state` (ServerState): State to set as current

**Example:**
```python
test_state = initialize_server_state(test_config)
set_server_state(test_state)
```

#### `reset_server_state() -> None`

Reset server state to uninitialized.

**Example:**
```python
reset_server_state()  # Cleanup after tests
```

#### `get_executor() -> ThreadPoolExecutor`

Get or create thread pool executor for sync operations.

**Returns:**
- `ThreadPoolExecutor`: Thread pool instance

#### `cleanup() -> None`

Clean up server resources (connections, threads).

**Example:**
```python
try:
    state = initialize_server_state()
    # ... use server
finally:
    cleanup()
```

### ServerState Class

```python
@dataclass
class ServerState:
    """Encapsulates all server-wide state."""

    # Core components
    config: RuntimeConfig
    mcp: FastMCP
    graph: Optional[SecureNeo4jGraph] = None
    chain: Optional[GraphCypherQAChain] = None

    # Rate limiting
    tool_rate_limiter: RateLimiterService
    tool_rate_limit_enabled: bool = True
    resource_rate_limit_enabled: bool = True

    # Server flags
    _debug_mode: bool = False
    _read_only_mode: bool = False
    _response_token_limit: Optional[int] = None
    _executor: Any = None  # ThreadPoolExecutor
```

## FAQ

### Q: Do I need to change my code for v1.3.0?

**A:** No. Bootstrap is completely opt-in. Existing code works unchanged.

### Q: When should I use bootstrap?

**A:** Use bootstrap when you need:
- Multi-instance deployments
- Better test isolation
- Explicit state management
- Clean resource cleanup

### Q: Will there be breaking changes?

**A:** Not in v1.3.0 or v1.4.0. Breaking changes (if any) will come in v1.5.0+ with advance notice and migration guides.

### Q: Can I mix old and new patterns?

**A:** Yes! Bootstrap works alongside existing code. Migrate gradually at your own pace.

### Q: How do I test multi-instance?

**A:** See the test examples in `tests/unit/test_bootstrap.py` for patterns.

### Q: What about performance?

**A:** Bootstrap adds minimal overhead (one extra function call). The lazy initialization pattern means no impact until you use it.

## Contributing

Found issues or have suggestions? Please:
1. Check existing issues at GitHub
2. Review the migration plan in `ARCHITECTURE_REFACTORING_PLAN.md`
3. Submit PRs with tests!

## See Also

- [ARCHITECTURE_REFACTORING_PLAN.md](../ARCHITECTURE_REFACTORING_PLAN.md) - Full refactoring roadmap
- [tests/unit/test_bootstrap.py](../tests/unit/test_bootstrap.py) - Usage examples
- [src/neo4j_yass_mcp/bootstrap.py](../src/neo4j_yass_mcp/bootstrap.py) - Source code
