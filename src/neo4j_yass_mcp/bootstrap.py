"""
Server bootstrap and initialization.

This module handles all server initialization in a controlled manner,
eliminating import-time side effects for better testability and
multi-instance support.

Architecture Pattern:
- ServerState: Encapsulates all server-wide state
- initialize_server_state(): Explicit initialization from config
- get_server_state(): Access current state (lazy initialization support)

Benefits:
- ✅ No import-time side effects
- ✅ Multi-instance support (each with own state)
- ✅ Better test isolation
- ✅ Clear initialization order
- ✅ Easy to mock for testing
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from fastmcp import FastMCP
from langchain_neo4j import GraphCypherQAChain

from .config import RuntimeConfig
from .secure_graph import SecureNeo4jGraph
from .security import initialize_audit_logger
from .security.complexity_limiter import initialize_complexity_limiter
from .security.rate_limiter import initialize_rate_limiter
from .security.sanitizer import initialize_sanitizer
from .tool_wrappers import RateLimiterService

logger = logging.getLogger(__name__)


@dataclass
class ServerState:
    """
    Encapsulates all server-wide state.

    Replaces module-level globals with explicit state object.
    This enables:
    - Multi-instance deployments
    - Better test isolation
    - Clear state management
    - No import-time side effects
    """

    # Core components
    config: RuntimeConfig
    mcp: FastMCP
    graph: SecureNeo4jGraph | None = None
    chain: GraphCypherQAChain | None = None

    # Rate limiting
    tool_rate_limiter: RateLimiterService = field(default_factory=RateLimiterService)
    tool_rate_limit_enabled: bool = True
    resource_rate_limit_enabled: bool = True

    # Server flags
    _debug_mode: bool = False
    _read_only_mode: bool = False
    _response_token_limit: int | None = None

    # Thread pool executor (for LangChain sync operations)
    _executor: Any = None  # ThreadPoolExecutor, created on demand


def initialize_server_state(
    config: RuntimeConfig | None = None,
    mcp_instance: FastMCP | None = None,
) -> ServerState:
    """
    Initialize server state from configuration.

    Called explicitly during startup, not at import time.

    Args:
        config: Runtime configuration object (loads from env if None)
        mcp_instance: FastMCP instance (creates new if None)

    Returns:
        Initialized server state

    Example:
        >>> config = RuntimeConfig.from_env()
        >>> state = initialize_server_state(config)
        >>> # Use state.graph, state.chain, etc.
    """
    # Load config if not provided
    if config is None:
        config = RuntimeConfig.from_env()

    # Create MCP instance if not provided
    if mcp_instance is None:
        mcp_instance = FastMCP("neo4j-yass-mcp", version="1.3.0")

    # Create state object
    state = ServerState(
        config=config,
        mcp=mcp_instance,
        tool_rate_limit_enabled=config.tool_rate_limit.enabled,
        resource_rate_limit_enabled=config.resource_rate_limit.enabled,
        _read_only_mode=config.neo4j.read_only,
        _response_token_limit=config.neo4j.response_token_limit,
        _debug_mode=config.environment.debug_mode,
    )

    # Initialize audit logger
    logger.info("Initializing audit logger...")
    initialize_audit_logger()

    # Initialize query sanitizer
    if config.sanitizer.enabled:
        logger.info("Initializing query sanitizer...")
        initialize_sanitizer(
            strict_mode=config.sanitizer.strict_mode,
            allow_apoc=config.sanitizer.allow_apoc,
            allow_schema_changes=config.sanitizer.allow_schema_changes,
            block_non_ascii=config.sanitizer.block_non_ascii,
            max_query_length=config.sanitizer.max_query_length,
        )
        logger.info("✅ Query sanitizer enabled (injection + UTF-8 attack protection active)")
    else:
        logger.warning("⚠️  Query sanitizer disabled - injection protection is OFF!")

    # Initialize complexity limiter
    if config.complexity_limiter.enabled:
        logger.info("Initializing complexity limiter...")
        initialize_complexity_limiter(
            max_complexity=config.complexity_limiter.max_complexity,
            max_variable_path_length=config.complexity_limiter.max_variable_path_length,
            require_limit_unbounded=config.complexity_limiter.require_limit_unbounded,
        )
        logger.info("✅ Query complexity limiter enabled (prevents resource exhaustion attacks)")
    else:
        logger.warning("⚠️  Query complexity limiter disabled - no protection against complex queries!")

    # Initialize rate limiter
    if config.rate_limiter.enabled:
        logger.info("Initializing rate limiter...")
        initialize_rate_limiter(
            rate=config.rate_limiter.rate,
            per_seconds=config.rate_limiter.per_seconds,
            burst=config.rate_limiter.burst,
        )
        logger.info("✅ Rate limiter enabled (prevents abuse through excessive requests)")
    else:
        logger.warning("⚠️  Rate limiter disabled - no protection against request flooding!")

    logger.info("✅ Server state initialized successfully")
    return state


# Module-level state (lazy initialization)
_server_state: ServerState | None = None


def get_server_state() -> ServerState:
    """
    Get current server state.

    Performs lazy initialization if needed (backwards compatibility).

    Returns:
        Current server state

    Raises:
        RuntimeError: If server not initialized and lazy init fails

    Example:
        >>> state = get_server_state()
        >>> graph = state.graph
    """
    global _server_state

    if _server_state is None:
        logger.info("Lazy-initializing server state (consider explicit initialization)")
        _server_state = initialize_server_state()

    return _server_state


def set_server_state(state: ServerState) -> None:
    """
    Set the current server state.

    Used for testing and multi-instance deployments.

    Args:
        state: Server state to set as current

    Example:
        >>> # Test with isolated state
        >>> test_config = RuntimeConfig(...)
        >>> test_state = initialize_server_state(test_config)
        >>> set_server_state(test_state)
    """
    global _server_state
    _server_state = state


def reset_server_state() -> None:
    """
    Reset server state to uninitialized.

    Used for testing and cleanup.

    Example:
        >>> # Clean up after test
        >>> reset_server_state()
    """
    global _server_state
    _server_state = None


def get_executor():
    """
    Get or create thread pool executor for sync LangChain operations.

    Returns:
        ThreadPoolExecutor instance
    """
    from concurrent.futures import ThreadPoolExecutor

    state = get_server_state()

    if state._executor is None:
        max_workers = state.config.server.max_workers
        state._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="neo4j_yass_mcp_",
        )
        logger.info(f"Created ThreadPoolExecutor with {max_workers} workers")

    return state._executor


def cleanup():
    """
    Clean up server resources.

    Shuts down thread pool and closes connections.

    Example:
        >>> # On server shutdown
        >>> cleanup()
    """
    state = get_server_state()

    # Shutdown executor
    if state._executor is not None:
        logger.info("Shutting down thread pool executor...")
        state._executor.shutdown(wait=True)
        state._executor = None

    # Close Neo4j driver
    if state.graph is not None and hasattr(state.graph, "_driver"):
        logger.info("Closing Neo4j driver...")
        state.graph._driver.close()

    logger.info("✅ Server cleanup complete")
