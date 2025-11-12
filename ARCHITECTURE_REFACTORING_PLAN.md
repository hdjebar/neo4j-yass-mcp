# ✅ ARCHIVED: Architecture Refactoring Plan - COMPLETE

> **Status**: All phases completed successfully (v1.2.2, v1.3.0, v1.4.0)
>
> **See**: [docs/ARCHITECTURE_REFACTORING_COMPLETE.md](docs/ARCHITECTURE_REFACTORING_COMPLETE.md) for completion summary
>
> This document is preserved for historical reference only.

---

# Architecture Refactoring Plan - Technical Debt Resolution

**Analysis Date**: 2025-01-12
**Current Version**: 1.2.1
**Target Version**: 1.3.0 (Post-refactoring)
**Priority**: HIGH (Technical Debt) - ✅ **COMPLETED**

---

## Executive Summary

Your analysis has identified 7 critical architectural issues that, while the code is production-ready, create technical debt that will hinder future development. This plan provides a systematic approach to resolve these issues.

**Key Issues Identified**:
1. ❌ Import-time side effects (initialization at module load)
2. ❌ Circular dependencies (server ↔ secure_graph)
3. ❌ Scattered configuration (env vars everywhere)
4. ❌ Inconsistent async execution patterns
5. ❌ Weak typing (dict[str, Any] responses)
6. ❌ Hardcoded test paths
7. ❌ Skipped critical tests

**Impact**: These issues don't affect current functionality but will cause problems during:
- Multi-instance deployments
- Test isolation
- Type safety verification
- Future refactoring

---

## Issue 1: Import-Time Side Effects

### Current Problem

**Location**: [src/neo4j_yass_mcp/server.py:63-138](src/neo4j_yass_mcp/server.py#L63-L138)

```python
# Executed IMMEDIATELY on import
sanitizer_enabled = os.getenv("SANITIZER_ENABLED", "true").lower() == "true"
sanitizer = QuerySanitizer(strict_mode=strict_mode, ...) if sanitizer_enabled else None
complexity_limiter = ComplexityLimiter() if complexity_enabled else None

# Creates global rate limiters
query_graph_limiter = RateLimiterService.create_limiter(...)
execute_cypher_limiter = RateLimiterService.create_limiter(...)
# ... more global state
```

**Problems**:
- Tests cannot reconfigure server without reloading interpreter
- Subprocesses inherit global state
- Cannot run multiple instances with different configs
- Harder to reason about initialization order

### Proposed Solution

**Create**: `src/neo4j_yass_mcp/bootstrap.py`

```python
"""
Server bootstrap and initialization.

This module handles all import-time side effects in a controlled manner.
"""

from dataclasses import dataclass
from typing import Optional
import os

from .security import QuerySanitizer, ComplexityLimiter, AuditLogger
from .security.rate_limiter import RateLimiterService


@dataclass
class ServerState:
    """
    Encapsulates all server-wide state.

    Replaces module-level globals with explicit state object.
    """
    sanitizer: Optional[QuerySanitizer] = None
    complexity_limiter: Optional[ComplexityLimiter] = None
    audit_logger: Optional[AuditLogger] = None
    query_graph_limiter: Optional[RateLimiterService] = None
    execute_cypher_limiter: Optional[RateLimiterService] = None
    refresh_schema_limiter: Optional[RateLimiterService] = None
    analyze_query_limiter: Optional[RateLimiterService] = None
    graph: Optional[Any] = None  # Neo4jGraph or SecureNeo4jGraph


def initialize_server_state(config: 'RuntimeConfig') -> ServerState:
    """
    Initialize server state from configuration.

    Called explicitly during startup, not at import time.

    Args:
        config: Runtime configuration object

    Returns:
        Initialized server state
    """
    state = ServerState()

    # Initialize sanitizer
    if config.sanitizer_enabled:
        state.sanitizer = QuerySanitizer(
            strict_mode=config.sanitizer_strict_mode,
            block_non_ascii=config.sanitizer_block_non_ascii,
            allow_apoc=config.sanitizer_allow_apoc,
            allow_file_operations=config.sanitizer_allow_file_ops,
        )

    # Initialize complexity limiter
    if config.complexity_enabled:
        state.complexity_limiter = ComplexityLimiter(
            max_depth=config.complexity_max_depth,
            max_nodes=config.complexity_max_nodes,
        )

    # Initialize audit logger
    if config.audit_log_enabled:
        state.audit_logger = AuditLogger(
            log_dir=config.audit_log_dir,
            format=config.audit_log_format,
        )

    # Initialize rate limiters
    if config.tool_rate_limit_enabled:
        state.query_graph_limiter = RateLimiterService.create_limiter(
            "query_graph",
            limit=config.query_graph_limit,
            window=config.query_graph_window,
        )
        # ... other limiters

    return state


# Module-level state (lazy initialization)
_server_state: Optional[ServerState] = None


def get_server_state() -> ServerState:
    """
    Get current server state.

    Raises:
        RuntimeError: If server not initialized
    """
    if _server_state is None:
        raise RuntimeError(
            "Server not initialized. Call initialize_server() first."
        )
    return _server_state


def initialize_server(config: Optional['RuntimeConfig'] = None):
    """
    Initialize server with configuration.

    Args:
        config: Runtime configuration (uses defaults if None)
    """
    global _server_state

    if config is None:
        from .config import load_runtime_config
        config = load_runtime_config()

    _server_state = initialize_server_state(config)
```

**Update**: `src/neo4j_yass_mcp/server.py`

```python
# Remove all module-level initialization
# Replace with:

from .bootstrap import get_server_state, initialize_server


# In main():
def main():
    """Run the MCP server."""
    # Explicit initialization
    initialize_server()

    # Get state
    state = get_server_state()

    # Use state.sanitizer, state.graph, etc.
    ...
```

**Benefits**:
- ✅ Tests can create isolated server instances
- ✅ Explicit initialization order
- ✅ No module-level side effects
- ✅ Multi-instance support

**Testing**:
```python
# tests/conftest.py
@pytest.fixture
def test_server_state():
    """Create isolated server state for testing."""
    from neo4j_yass_mcp.config import RuntimeConfig
    from neo4j_yass_mcp.bootstrap import initialize_server_state

    config = RuntimeConfig(
        sanitizer_enabled=True,
        neo4j_uri="bolt://localhost:7687",
        # ... test config
    )

    return initialize_server_state(config)
```

---

## Issue 2: Circular Dependencies

### Current Problem

**Location**: [src/neo4j_yass_mcp/secure_graph.py:71-134](src/neo4j_yass_mcp/secure_graph.py#L71-L134)

```python
from .server import check_read_only_access  # ❌ Imports from server!

class SecureNeo4jGraph(Neo4jGraph):
    def query(self, query: str, params: dict = None):
        # Calls back into server module
        error_msg = check_read_only_access(query)
        if error_msg:
            raise ValueError(error_msg)
```

**Dependency Graph**:
```
server.py ────imports───> secure_graph.py
    ↑                            │
    └───────imports──────────────┘
         (circular!)
```

**Problems**:
- Cannot use `SecureNeo4jGraph` without importing entire server
- Harder to test security in isolation
- Import order matters
- Violates single responsibility

### Proposed Solution

**Create**: `src/neo4j_yass_mcp/security/validators.py`

```python
"""
Security validators for Cypher queries.

Extracted from server.py to break circular dependency.
"""

import re
from typing import Optional


# Patterns for write operations
WRITE_OPERATIONS = [
    r"\bCREATE\b",
    r"\bMERGE\b",
    r"\bDELETE\b",
    r"\bREMOVE\b",
    r"\bSET\b",
    r"\bDROP\b",
    r"\bCALL\s+\{",  # CALL subqueries
]


def check_read_only_access(cypher_query: str) -> Optional[str]:
    """
    Check if query contains write operations.

    Moved from server.py to break circular dependency.

    Args:
        cypher_query: Cypher query to validate

    Returns:
        Error message if write operation detected, None otherwise
    """
    if not cypher_query:
        return None

    # Normalize query
    normalized = cypher_query.upper().strip()

    # Allow EXPLAIN/PROFILE
    if normalized.startswith(("EXPLAIN", "PROFILE")):
        # Extract actual query after EXPLAIN/PROFILE
        parts = cypher_query.split(maxsplit=1)
        if len(parts) > 1:
            normalized = parts[1].upper().strip()
        else:
            return None

    # Check for write operations
    for pattern in WRITE_OPERATIONS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return (
                f"Write operation detected: {pattern}. "
                "Server is in read-only mode."
            )

    return None
```

**Update**: `src/neo4j_yass_mcp/secure_graph.py`

```python
from langchain_neo4j import Neo4jGraph

from .security.validators import check_read_only_access  # ✅ No server import!


class SecureNeo4jGraph(Neo4jGraph):
    """Neo4j graph with security controls."""

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        *,
        read_only: bool = False,
        sanitizer: Optional['QuerySanitizer'] = None,
        complexity_limiter: Optional['ComplexityLimiter'] = None,
    ):
        super().__init__(url=url, username=username, password=password)
        self.read_only = read_only
        self.sanitizer = sanitizer
        self.complexity_limiter = complexity_limiter

    def query(self, query: str, params: dict = None):
        """Execute query with security checks."""
        # Read-only check (no circular import!)
        if self.read_only:
            error_msg = check_read_only_access(query)
            if error_msg:
                raise ValueError(error_msg)

        # Sanitizer check
        if self.sanitizer:
            sanitized = self.sanitizer.sanitize_query(query)
            query = sanitized["query"]

        # Complexity check
        if self.complexity_limiter:
            self.complexity_limiter.check_query(query)

        return super().query(query, params)
```

**Update**: `src/neo4j_yass_mcp/server.py`

```python
# Import validator instead of defining it
from .security.validators import check_read_only_access

# Remove check_read_only_access function definition (lines 273-321)
# It's now in security/validators.py
```

**Dependency Graph After Fix**:
```
server.py ────imports───> secure_graph.py
                                 │
                                 └───imports───> security/validators.py
```

**Benefits**:
- ✅ No circular dependencies
- ✅ `SecureNeo4jGraph` is standalone
- ✅ Security validators are testable in isolation
- ✅ Clear separation of concerns

---

## Issue 3: Scattered Configuration

### Current Problem

**Location**: [src/neo4j_yass_mcp/server.py:498-569](src/neo4j_yass_mcp/server.py#L498-L569)

```python
def initialize_neo4j():
    # Reads 15+ env vars directly
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    neo4j_read_only = os.getenv("NEO4J_READ_ONLY", "false").lower() == "true"
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    # ... 10+ more env vars

    # Password validation logic inline
    if not neo4j_password:
        raise ValueError("...")
    # ... more validation

    # Instantiation logic inline
    if llm_provider == "openai":
        llm = ChatOpenAI(...)
    elif llm_provider == "anthropic":
        llm = ChatAnthropic(...)
    # ... more branching
```

**Problems**:
- Cannot swap configs without env var manipulation
- No validation until runtime
- Hard to test different configurations
- Scattered across multiple functions
- Existing `config/` package underutilized

### Proposed Solution

**Create**: `src/neo4j_yass_mcp/config/runtime_config.py`

```python
"""
Runtime configuration for Neo4j YASS MCP server.

Consolidates all configuration logic into a single, testable object.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
import os
from pathlib import Path

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class RuntimeConfig(BaseSettings):
    """
    Complete server runtime configuration.

    Uses Pydantic for validation and env var parsing.
    """

    # === Neo4j Configuration ===
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI"
    )
    neo4j_username: str = Field(default="neo4j")
    neo4j_password: str = Field(default="", min_length=1)  # Validates not empty
    neo4j_database: str = Field(default="neo4j")
    neo4j_read_only: bool = Field(default=False)
    neo4j_timeout: int = Field(default=30, ge=1, le=300)

    # === LLM Configuration ===
    llm_provider: Literal["openai", "anthropic", "google-genai"] = Field(
        default="openai"
    )
    llm_model: str = Field(default="gpt-4")
    llm_api_key: str = Field(default="", min_length=1)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    # === Security Configuration ===
    sanitizer_enabled: bool = Field(default=True)
    sanitizer_strict_mode: bool = Field(default=False)
    sanitizer_block_non_ascii: bool = Field(default=False)
    sanitizer_allow_apoc: bool = Field(default=True)
    sanitizer_allow_file_ops: bool = Field(default=False)

    complexity_enabled: bool = Field(default=True)
    complexity_max_depth: int = Field(default=5, ge=1)
    complexity_max_nodes: int = Field(default=1000, ge=10)

    audit_log_enabled: bool = Field(default=True)
    audit_log_dir: Path = Field(default=Path("logs/audit"))
    audit_log_format: Literal["json", "csv"] = Field(default="json")
    audit_log_rotation: Literal["daily", "weekly", "size"] = Field(default="daily")
    audit_log_retention_days: int = Field(default=90, ge=1)

    # === Rate Limiting Configuration ===
    tool_rate_limit_enabled: bool = Field(default=True)
    query_graph_limit: int = Field(default=10, ge=1)
    query_graph_window: int = Field(default=60, ge=1)
    execute_cypher_limit: int = Field(default=10, ge=1)
    execute_cypher_window: int = Field(default=60, ge=1)
    refresh_schema_limit: int = Field(default=5, ge=1)
    refresh_schema_window: int = Field(default=120, ge=1)
    analyze_query_limit: int = Field(default=15, ge=1)
    analyze_query_window: int = Field(default=60, ge=1)

    resource_rate_limit_enabled: bool = Field(default=True)
    resource_limit: int = Field(default=20, ge=1)
    resource_window: int = Field(default=60, ge=1)

    # === Transport Configuration ===
    mcp_transport: Literal["stdio", "http", "sse"] = Field(default="stdio")
    mcp_server_host: str = Field(default="127.0.0.1")
    mcp_server_port: int = Field(default=8000, ge=1024, le=65535)
    mcp_server_path: str = Field(default="/mcp/")

    # === Performance Configuration ===
    response_token_limit: int = Field(default=10000, ge=100)
    max_workers: int = Field(default=10, ge=1, le=100)

    # === Environment ===
    environment: Literal["development", "production"] = Field(default="production")
    debug: bool = Field(default=False)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Map env vars to fields (NEO4J_URI -> neo4j_uri)

    @validator("neo4j_password")
    def validate_password_strength(cls, v, values):
        """Validate Neo4j password strength."""
        if not v:
            raise ValueError("NEO4J_PASSWORD is required")

        # Check if weak passwords are allowed (development only)
        allow_weak = os.getenv("ALLOW_WEAK_PASSWORDS", "false").lower() == "true"
        env = values.get("environment", "production")

        if not allow_weak and env == "production":
            # Use zxcvbn for password strength
            from zxcvbn import zxcvbn
            result = zxcvbn(v)
            if result["score"] < 3:
                raise ValueError(
                    f"Weak password detected (score: {result['score']}/4). "
                    "Use a stronger password or set ALLOW_WEAK_PASSWORDS=true"
                )

        return v

    @validator("llm_api_key")
    def validate_api_key(cls, v, values):
        """Validate LLM API key format."""
        provider = values.get("llm_provider")

        if not v:
            raise ValueError(f"LLM_API_KEY is required for provider: {provider}")

        # Provider-specific validation
        if provider == "openai" and not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")
        elif provider == "anthropic" and not v.startswith("sk-ant-"):
            raise ValueError("Anthropic API key must start with 'sk-ant-'")

        return v


def load_runtime_config(env_file: Optional[Path] = None) -> RuntimeConfig:
    """
    Load runtime configuration from environment.

    Args:
        env_file: Optional .env file path

    Returns:
        Validated runtime configuration

    Raises:
        ValidationError: If configuration is invalid
    """
    if env_file:
        return RuntimeConfig(_env_file=env_file)
    return RuntimeConfig()
```

**Update**: `src/neo4j_yass_mcp/server.py`

```python
from .config.runtime_config import RuntimeConfig, load_runtime_config


def initialize_neo4j(config: RuntimeConfig):
    """
    Initialize Neo4j connection and LLM.

    Args:
        config: Validated runtime configuration
    """
    # Simple, clean initialization using config object
    if config.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=config.llm_model,
            api_key=config.llm_api_key,
            temperature=config.llm_temperature,
        )
    elif config.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(
            model=config.llm_model,
            api_key=config.llm_api_key,
            temperature=config.llm_temperature,
        )
    # ... etc

    # Create graph with config
    if config.neo4j_read_only:
        from .secure_graph import SecureNeo4jGraph
        graph = SecureNeo4jGraph(
            url=config.neo4j_uri,
            username=config.neo4j_username,
            password=config.neo4j_password,
            read_only=True,
        )
    else:
        from langchain_neo4j import Neo4jGraph
        graph = Neo4jGraph(
            url=config.neo4j_uri,
            username=config.neo4j_username,
            password=config.neo4j_password,
        )

    return graph, llm
```

**Benefits**:
- ✅ All configuration in one place
- ✅ Pydantic validation at load time
- ✅ Type-safe access (config.neo4j_uri vs os.getenv)
- ✅ Easy to test (just pass different config)
- ✅ Environment-aware (dev vs prod)

**Testing**:
```python
# tests/conftest.py
@pytest.fixture
def test_config():
    """Test configuration."""
    return RuntimeConfig(
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="test_password_12345",
        llm_provider="openai",
        llm_api_key="sk-test-key",
        environment="development",
        sanitizer_enabled=True,
    )


def test_initialization_with_config(test_config):
    """Test that initialization works with config object."""
    graph, llm = initialize_neo4j(test_config)
    assert graph is not None
    assert llm is not None
```

---

## Issue 4: Inconsistent Async Execution

### Current Problem

**Locations**:
- [src/neo4j_yass_mcp/server.py:265-270](src/neo4j_yass_mcp/server.py#L265-L270) - Unused ThreadPoolExecutor
- [src/neo4j_yass_mcp/server.py:714](src/neo4j_yass_mcp/server.py#L714) - `asyncio.to_thread`
- [src/neo4j_yass_mcp/server.py:962](src/neo4j_yass_mcp/server.py#L962) - `asyncio.to_thread`
- [src/neo4j_yass_mcp/server.py:1068](src/neo4j_yass_mcp/server.py#L1068) - `asyncio.to_thread`

```python
# UNUSED executor
_executor: Optional[ThreadPoolExecutor] = None

def get_executor() -> ThreadPoolExecutor:
    """Get or create the thread pool executor."""
    global _executor
    if _executor is None:
        max_workers = int(os.getenv("MCP_MAX_WORKERS", "10"))
        _executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="neo4j_yass_worker"
        )
    return _executor


# But actual code uses asyncio.to_thread instead!
@mcp.tool()
async def query_graph(query: str, ctx: Context | None = None):
    result = await asyncio.to_thread(  # ❌ Doesn't use executor!
        _query_graph_impl,
        query=query,
        chain=chain,
        sanitizer=sanitizer,
        # ...
    )
```

**Problems**:
- Dead code (executor created but never used)
- Memory leak (executor threads never cleaned up properly)
- Inconsistent - some code might use executor, some uses to_thread
- Blocks event loop when LangChain/Neo4j call sync hooks

### Proposed Solution

**Option A: Standardize on asyncio.to_thread** (Recommended)

Remove the unused executor entirely:

```python
# Remove from server.py:
# - _executor global
# - get_executor() function
# - cleanup logic in cleanup()

# Keep using asyncio.to_thread everywhere:
@mcp.tool()
async def query_graph(query: str, ctx: Context | None = None):
    result = await asyncio.to_thread(
        _query_graph_impl,
        query=query,
        # ...
    )
```

**Option B: Use Native Async Neo4j Driver** (Best Long-term)

```python
# Install async driver
# pip install neo4j>=5.28.0  # Already has async support!

from neo4j import AsyncGraphDatabase


class AsyncNeo4jGraph:
    """Async wrapper for Neo4j."""

    def __init__(self, uri: str, username: str, password: str):
        self.driver = AsyncGraphDatabase.driver(
            uri, auth=(username, password)
        )

    async def query(self, cypher: str, params: dict = None):
        """Execute Cypher query asynchronously."""
        async with self.driver.session() as session:
            result = await session.run(cypher, params or {})
            return await result.data()

    async def close(self):
        await self.driver.close()


# Then tools become truly async:
@mcp.tool()
async def execute_cypher(
    cypher_query: str,
    parameters: dict | None = None,
    ctx: Context | None = None
):
    # No thread spawning needed!
    result = await graph.query(cypher_query, parameters)
    return {"success": True, "data": result}
```

**Recommended Approach**: Start with Option A (remove executor), then migrate to Option B in v1.4.0.

**Benefits**:
- ✅ Removes dead code
- ✅ Consistent execution pattern
- ✅ Better async performance (Option B)
- ✅ No thread pool overhead

---

## Issue 5: Weak Typing

### Current Problem

**Locations**: All tool functions return `dict[str, Any]`

```python
async def query_graph(query: str, ctx: Context | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "question": query,
        "answer": result["answer"],
        "generated_cypher": result.get("cypher"),
        # ... 10+ more fields
    }


async def _execute_cypher_impl(...) -> dict[str, Any]:
    return {
        "success": True,
        "data": result,
        "query": cypher_query,
        "row_count": len(result),
        # ... more fields
    }
```

**Problems**:
- No IDE autocomplete
- Runtime errors if field renamed
- mypy cannot verify correctness
- Unclear what fields are required vs optional

### Proposed Solution

**Create**: `src/neo4j_yass_mcp/types/responses.py`

```python
"""
Response types for MCP tools.

Provides strong typing for all tool responses.
"""

from typing import TypedDict, Literal, Optional, Any
from enum import Enum


class AnalysisMode(str, Enum):
    """Query analysis modes."""
    EXPLAIN = "explain"
    PROFILE = "profile"


class RiskLevel(str, Enum):
    """Query risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QueryGraphResult(TypedDict, total=False):
    """Result from query_graph tool."""
    success: bool
    question: str
    answer: str
    generated_cypher: Optional[str]
    context_used: Optional[list[dict[str, Any]]]
    intermediate_steps: Optional[list[Any]]
    execution_time_ms: int
    truncated: bool
    error: Optional[str]  # Only present if success=False


class ExecuteCypherResult(TypedDict, total=False):
    """Result from execute_cypher tool."""
    success: bool
    data: list[dict[str, Any]]
    query: str
    row_count: int
    execution_time_ms: int
    truncated: bool
    error: Optional[str]


class RefreshSchemaResult(TypedDict):
    """Result from refresh_schema tool."""
    success: bool
    schema: str
    node_count: int
    relationship_count: int
    execution_time_ms: int


class AnalyzeQueryResult(TypedDict, total=False):
    """Result from analyze_query_performance tool."""
    success: bool
    mode: AnalysisMode
    cost_score: int  # 1-10
    risk_level: RiskLevel
    bottlenecks_found: int
    recommendations_count: int
    execution_time_ms: int
    analysis_summary: dict[str, Any]
    detailed_analysis: Optional[dict[str, Any]]
    analysis_report: str
    error: Optional[str]
    error_type: Optional[str]


class RateLimitError(TypedDict):
    """Rate limit error response."""
    error: str
    success: Literal[False]
    rate_limit_info: dict[str, Any]
```

**Update Tool Signatures**:

```python
from .types.responses import (
    QueryGraphResult,
    ExecuteCypherResult,
    RefreshSchemaResult,
    AnalyzeQueryResult,
    AnalysisMode,
    RiskLevel,
)


@mcp.tool()
async def query_graph(
    query: str,
    ctx: Context | None = None
) -> QueryGraphResult:  # ✅ Strongly typed!
    """Query the Neo4j graph using natural language."""
    # Implementation...
    return QueryGraphResult(
        success=True,
        question=query,
        answer=result["answer"],
        generated_cypher=result.get("cypher"),
        execution_time_ms=int(elapsed * 1000),
        truncated=was_truncated,
    )


@mcp.tool()
async def analyze_query_performance(
    query: str,
    mode: Literal["explain", "profile"] = "profile",  # ✅ Typed mode!
    include_recommendations: bool = True,
    ctx: Context | None = None
) -> AnalyzeQueryResult:  # ✅ Strongly typed!
    """Analyze query performance."""
    # Use enum
    analysis_mode = AnalysisMode(mode)

    # Implementation...
    return AnalyzeQueryResult(
        success=True,
        mode=analysis_mode,
        cost_score=5,
        risk_level=RiskLevel.LOW,
        bottlenecks_found=1,
        # ... IDE autocomplete works here!
    )
```

**Benefits**:
- ✅ IDE autocomplete for all response fields
- ✅ mypy catches field typos at type-check time
- ✅ Self-documenting code
- ✅ Easier refactoring (rename field → mypy finds all uses)
- ✅ Better API documentation

---

## Issue 6: Hardcoded Test Paths

### Current Problem

**Location**: [tests/test_query_analysis_html.py:15](tests/test_query_analysis_html.py#L15)

```python
# Hardcoded path from different repo!
sys.path.insert(0, "/Users/hdjebar/Projects/kimi/neo4j-yass-mcp/src")
```

**Problems**:
- Breaks on different machines
- Breaks in CI/CD
- Wrong repo path ("kimi" vs "cl111125")
- Will cause import errors for other developers

### Proposed Solution

```python
# tests/test_query_analysis_html.py
import sys
from pathlib import Path

# ✅ Dynamic path resolution
project_root = Path(__file__).parents[1]
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from neo4j_yass_mcp.server import analyze_query_performance
```

**Even Better**: Remove sys.path manipulation entirely

```python
# tests/conftest.py (pytest automatically loads this)
import sys
from pathlib import Path

# Add src to path for all tests
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
```

Then in test files:
```python
# tests/test_query_analysis_html.py
# No sys.path needed - conftest.py handles it
from neo4j_yass_mcp.server import analyze_query_performance
```

**Benefits**:
- ✅ Works on any machine
- ✅ Works in CI/CD
- ✅ Works for all contributors
- ✅ Centralized in conftest.py

---

## Issue 7: Skipped Critical Tests

### Current Problem

**Locations**:
- [tests/unit/test_query_analyzer.py:108](tests/unit/test_query_analyzer.py#L108) - `@pytest.mark.skip("needs debugging")`
- [tests/unit/test_server_rate_limiting.py:35-175](tests/unit/test_server_rate_limiting.py#L35-L175) - 4 skipped tests

```python
@pytest.mark.skip(reason="needs debugging")  # ❌
async def test_analyze_query_with_profile_mode(self, ...):
    """Test analyzer with PROFILE mode."""
    # Critical functionality untested!
```

**Problems**:
- New analyzer code paths untested
- Rate limiting untested
- Could hide regressions
- Tech debt accumulates

### Proposed Solution

**Step 1**: Fix the test issues

Most skipped tests fail due to async mocking issues:

```python
# Problem: Mock not awaitable
mock_graph.query = Mock(return_value=plan_data)

# Solution: Use AsyncMock for async code, Mock for sync code
from unittest.mock import AsyncMock, Mock

# For sync methods (current Neo4j driver):
mock_graph.query = Mock(return_value=plan_data)

# For async methods (future async driver):
mock_graph.query = AsyncMock(return_value=plan_data)
```

**Step 2**: Fix test return values

```python
# Problem: Returns True/False (causes pytest warning)
@pytest.mark.asyncio
async def test_query_analysis_integration():
    # ... test code ...
    return True  # ❌ PytestReturnNotNoneWarning


# Solution: Use assertions instead
@pytest.mark.asyncio
async def test_query_analysis_integration():
    result = await analyze_query_performance(query="...", mode="explain")

    assert result["success"] is True  # ✅
    assert result["cost_score"] > 0
    assert "analysis_summary" in result
    # No return statement needed!
```

**Step 3**: Unskip tests systematically

```python
# tests/unit/test_query_analyzer.py

# Remove @pytest.mark.skip
async def test_analyze_query_with_profile_mode(self, analyzer, mock_graph):
    """Test analyzer with PROFILE mode."""
    # Fix mocking
    mock_graph.query = Mock(return_value=[
        {"name": "NodeIndexSeek", "estimated_rows": 100},
    ])

    # Test
    result = await analyzer.analyze_query(
        "MATCH (n:Person) RETURN n",
        mode="profile"
    )

    # Assertions (not return values!)
    assert result["mode"] == "profile"
    assert "statistics" in result
    assert result["execution_plan"] is not None
```

**Benefits**:
- ✅ Full test coverage restored
- ✅ No pytest warnings
- ✅ Catches regressions
- ✅ Validates critical paths

---

## Implementation Roadmap

### Phase 1: Foundation (v1.2.2) - 1 week

**Priority**: Fix immediate issues

1. ✅ Fix hardcoded test paths (Issue 6)
   - Update test_query_analysis_html.py
   - Add path resolution to conftest.py
   - **Testing**: All tests still pass
   - **Time**: 1 hour

2. ✅ Fix skipped tests (Issue 7)
   - Fix async mocking
   - Remove return statements
   - Unskip all tests
   - **Testing**: All tests pass with no warnings
   - **Time**: 4 hours

3. ✅ Remove unused executor (Issue 4, partial)
   - Delete ThreadPoolExecutor code
   - Keep asyncio.to_thread pattern
   - **Testing**: All tools still work
   - **Time**: 2 hours

**Outcome**: v1.2.2 release with test coverage restored

### Phase 2: Architecture (v1.3.0) - 2 weeks

**Priority**: Break circular dependencies and centralize config

1. ✅ Extract security validators (Issue 2)
   - Create security/validators.py
   - Move check_read_only_access
   - Update imports
   - **Testing**: All security tests pass
   - **Time**: 4 hours

2. ✅ Create runtime configuration (Issue 3)
   - Create config/runtime_config.py
   - Migrate all env var reads
   - Update initialization
   - **Testing**: Server starts with all configs
   - **Time**: 8 hours

3. ✅ Add response types (Issue 5)
   - Create types/responses.py
   - Add TypedDict classes
   - Update tool signatures
   - Run mypy verification
   - **Testing**: mypy passes, tools work
   - **Time**: 6 hours

**Outcome**: v1.3.0 release with improved architecture

### Phase 3: Modularization (v1.4.0) - 3 weeks

**Priority**: Split server.py and add native async

1. ✅ Create bootstrap module (Issue 1)
   - Create bootstrap.py
   - Move initialization logic
   - Remove module-level side effects
   - **Testing**: Multi-instance support
   - **Time**: 12 hours

2. ✅ Split server.py into modules
   - Create handlers/ directory
   - Split into query.py, execute.py, schema.py, analysis.py
   - Create resources/ for MCP resources
   - **Testing**: All tools still work
   - **Time**: 16 hours

3. ✅ Migrate to async Neo4j driver (Issue 4, complete)
   - Create AsyncNeo4jGraph wrapper
   - Remove all asyncio.to_thread calls
   - Update all tools to use async graph
   - **Testing**: Performance benchmarks
   - **Time**: 20 hours

**Outcome**: v1.4.0 release with modular architecture and native async

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_bootstrap.py
def test_server_state_initialization():
    """Test ServerState initialization."""
    config = RuntimeConfig(
        sanitizer_enabled=True,
        neo4j_uri="bolt://localhost:7687",
        # ...
    )

    state = initialize_server_state(config)

    assert state.sanitizer is not None
    assert state.complexity_limiter is not None


# tests/unit/test_runtime_config.py
def test_config_validation():
    """Test config validation."""
    with pytest.raises(ValidationError):
        RuntimeConfig(
            neo4j_password="",  # Should fail validation
        )

    config = RuntimeConfig(
        neo4j_password="strong_password_123",
        llm_api_key="sk-test",
        environment="development",
    )

    assert config.neo4j_password == "strong_password_123"
```

### Integration Tests

```python
# tests/integration/test_server_initialization.py
@pytest.mark.asyncio
async def test_multi_instance():
    """Test that multiple server instances can coexist."""
    config1 = RuntimeConfig(
        neo4j_database="db1",
        mcp_server_port=8001,
    )

    config2 = RuntimeConfig(
        neo4j_database="db2",
        mcp_server_port=8002,
    )

    state1 = initialize_server_state(config1)
    state2 = initialize_server_state(config2)

    # Should be independent
    assert state1.graph != state2.graph
```

### Type Checking

```bash
# Run mypy after adding types
mypy src/neo4j_yass_mcp/ --strict

# Should pass with no errors after Phase 2
```

---

## Risk Assessment

| Phase | Risk Level | Mitigation |
|-------|-----------|------------|
| Phase 1 | 🟢 LOW | Small changes, high test coverage |
| Phase 2 | 🟡 MEDIUM | Extensive testing, gradual migration |
| Phase 3 | 🟠 HIGH | Feature flags, beta testing, rollback plan |

**Rollback Strategy**: Each phase is a separate release (1.2.2, 1.3.0, 1.4.0) so rollback is just reverting the git tag.

---

## Success Metrics

| Metric | Current | Phase 1 | Phase 2 | Phase 3 |
|--------|---------|---------|---------|---------|
| Test Coverage | 83.54% | 85% | 87% | 90% |
| Mypy Coverage | ~60% | ~60% | 85% | 95% |
| Skipped Tests | 7 | 0 | 0 | 0 |
| Circular Deps | 1 | 1 | 0 | 0 |
| server.py LOC | 1459 | 1400 | 1200 | <800 |
| Module Count | 18 | 19 | 23 | 30+ |

---

## Conclusion

These refactorings will transform the codebase from "production-ready" to "production-hardened with excellent maintainability."

**Recommended Next Steps**:

1. **Immediate** (This week): Phase 1 items (test fixes, remove executor)
2. **Short-term** (This month): Phase 2 items (types, config, validators)
3. **Medium-term** (Next quarter): Phase 3 items (modularization, async)

**Priority**: Start with Phase 1 (low risk, high value) to build confidence before tackling larger architectural changes.

---

**Questions?** Discuss in [GitHub Issues](https://github.com/hdjebar/neo4j-yass-mcp/issues) or [Discussions](https://github.com/hdjebar/neo4j-yass-mcp/discussions).
