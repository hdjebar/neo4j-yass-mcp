#!/usr/bin/env python3
"""
Neo4j MCP Server with LangChain Integration using FastMCP

This MCP server provides Neo4j graph database querying capabilities using LangChain's
GraphCypherQAChain for natural language to Cypher query translation.

Features:
- Async/await support for parallel query execution
- Optional LLM streaming for real-time token generation
- Automatic port allocation
- Response size limiting and read-only mode
"""

import asyncio
import json
import logging
import os
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from langchain_neo4j import GraphCypherQAChain

# Tokenizer imports - use Hugging Face tokenizers exclusively
try:
    from tokenizers import Tokenizer

    TOKENIZER_BACKEND = "tokenizers"
except ImportError:
    Tokenizer = None  # type: ignore[assignment]
    TOKENIZER_BACKEND = "fallback"

from neo4j_yass_mcp.bootstrap import (
    ServerState,
    get_server_state,
    initialize_server_state,
)
from neo4j_yass_mcp.config import (
    LLMConfig,
    RuntimeConfig,
    chatLLM,
    configure_logging,
    find_available_port,
    get_preferred_ports_from_env,
)
from neo4j_yass_mcp.config.security_config import is_password_weak
from neo4j_yass_mcp.secure_graph import SecureNeo4jGraph
from neo4j_yass_mcp.security import (
    check_query_complexity,
    get_audit_logger,
    initialize_audit_logger,
    initialize_complexity_limiter,
    initialize_rate_limiter,
    initialize_sanitizer,
    sanitize_query,
)
from neo4j_yass_mcp.security.validators import (
    check_read_only_access as _check_read_only_access_impl,
)
from neo4j_yass_mcp.tool_wrappers import (
    RateLimiterService,
    log_tool_invocation,
    rate_limit_tool,
)

# Load environment variables first (needed for logging config)
load_dotenv()

# Configure logging from environment variables
configure_logging()
logger = logging.getLogger(__name__)

# Load runtime configuration from environment
_config = RuntimeConfig.from_env()

# Initialize audit logger for compliance
initialize_audit_logger()

# Initialize query sanitizer for security
if _config.sanitizer.enabled:
    initialize_sanitizer(
        strict_mode=_config.sanitizer.strict_mode,
        allow_apoc=_config.sanitizer.allow_apoc,
        allow_schema_changes=_config.sanitizer.allow_schema_changes,
        block_non_ascii=_config.sanitizer.block_non_ascii,
        max_query_length=_config.sanitizer.max_query_length,
    )
    logger.info("Query sanitizer enabled (injection + UTF-8 attack protection active)")
else:  # pragma: no cover - Module initialization, tested in production
    logger.warning("⚠️  Query sanitizer disabled - injection protection is OFF!")

# Initialize query complexity limiter
if _config.complexity_limiter.enabled:
    initialize_complexity_limiter(
        max_complexity=_config.complexity_limiter.max_complexity,
        max_variable_path_length=_config.complexity_limiter.max_variable_path_length,
        require_limit_unbounded=_config.complexity_limiter.require_limit_unbounded,
    )
    logger.info("Query complexity limiter enabled (prevents resource exhaustion attacks)")
else:  # pragma: no cover - Module initialization, tested in production
    logger.warning("⚠️  Query complexity limiter disabled - no protection against complex queries!")

# Initialize rate limiter
if _config.rate_limiter.enabled:
    initialize_rate_limiter(
        rate=_config.rate_limiter.rate,
        per_seconds=_config.rate_limiter.per_seconds,
        burst=_config.rate_limiter.burst,
    )
    logger.info("Rate limiter enabled (prevents abuse through excessive requests)")
else:  # pragma: no cover - Module initialization, tested in production
    logger.warning("⚠️  Rate limiter disabled - no protection against request flooding!")

# Decorator-based MCP tool rate limiter
tool_rate_limiter = RateLimiterService()
tool_rate_limit_enabled = _config.tool_rate_limit.enabled
QUERY_GRAPH_RATE_LIMIT = _config.tool_rate_limit.query_graph_limit
QUERY_GRAPH_RATE_WINDOW = _config.tool_rate_limit.query_graph_window
EXECUTE_CYPHER_RATE_LIMIT = _config.tool_rate_limit.execute_cypher_limit
EXECUTE_CYPHER_RATE_WINDOW = _config.tool_rate_limit.execute_cypher_window
REFRESH_SCHEMA_RATE_LIMIT = _config.tool_rate_limit.refresh_schema_limit
REFRESH_SCHEMA_RATE_WINDOW = _config.tool_rate_limit.refresh_schema_window
resource_rate_limit_enabled = _config.resource_rate_limit.enabled
RESOURCE_RATE_LIMIT = _config.resource_rate_limit.limit
RESOURCE_RATE_WINDOW = _config.resource_rate_limit.window

# Query analysis rate limits
ANALYZE_QUERY_RATE_LIMIT = _config.tool_rate_limit.analyze_query_limit
ANALYZE_QUERY_RATE_WINDOW = _config.tool_rate_limit.analyze_query_window


def _format_reset_time(timestamp: float) -> str:
    """Convert a UNIX timestamp to ISO 8601."""
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _build_query_graph_rate_limit_error(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "error": f"Rate limit exceeded. Retry after {info['retry_after']:.1f}s",
        "rate_limited": True,
        "retry_after_seconds": info["retry_after"],
        "reset_time": _format_reset_time(info["reset_time"]),
        "limit": info["limit"],
        "window": info["window"],
        "success": False,
    }


def _build_execute_rate_limit_error(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "error": f"Rate limit exceeded. Retry after {info['retry_after']:.1f}s",
        "rate_limited": True,
        "retry_after_seconds": info["retry_after"],
        "reset_time": _format_reset_time(info["reset_time"]),
        "limit": info["limit"],
        "window": info["window"],
        "success": False,
    }


def _build_refresh_schema_rate_limit_error(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "error": f"Rate limit exceeded. Retry after {info['retry_after']:.1f}s",
        "rate_limited": True,
        "retry_after_seconds": info["retry_after"],
        "reset_time": _format_reset_time(info["reset_time"]),
        "limit": info["limit"],
        "window": info["window"],
        "success": False,
    }


def _build_analyze_query_rate_limit_error(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "error": f"Query analysis rate limit exceeded. Retry after {info['retry_after']:.1f}s",
        "rate_limited": True,
        "retry_after_seconds": info["retry_after"],
        "reset_time": _format_reset_time(info["reset_time"]),
        "limit": info["limit"],
        "window": info["window"],
        "success": False,
    }


def _resource_rate_limit_message(resource_label: str) -> Callable[[dict[str, Any]], str]:
    def builder(info: dict[str, Any]) -> str:
        return (
            f"{resource_label} rate limit exceeded. "
            f"Retry after {info['retry_after']:.1f}s "
            f"(limit {info['limit']} per {info['window']}s)."
        )

    return builder


# ============================================================================
# Bootstrap Integration - Gradual Migration Pattern
# ============================================================================
#
# Strategy: Keep existing module-level variables but add opt-in bootstrap support
# This allows gradual migration without breaking existing code
#
# Phase 3.2 (Completed): Added bootstrap imports and helper functions
# Phase 3.3 (Current): Replace module variables with state delegation
# Phase 3.4 (Future): Remove module variables entirely
# ============================================================================


def _get_config() -> RuntimeConfig:
    """
    Get runtime configuration with bootstrap support.

    Phase 3.3: Tries to get config from bootstrap state first,
    falls back to module-level _config for backwards compatibility.
    """
    # Check if bootstrap state is available (but don't force initialization)
    from neo4j_yass_mcp.bootstrap import _server_state

    if _server_state is not None:
        return _server_state.config
    return _config


def _get_graph() -> SecureNeo4jGraph | None:
    """
    Get Neo4j graph instance with bootstrap support.

    Phase 3.3: Tries to get graph from bootstrap state first,
    falls back to module-level graph for backwards compatibility.
    """
    # Check if bootstrap state is available (but don't force initialization)
    from neo4j_yass_mcp.bootstrap import _server_state

    if _server_state is not None:
        return _server_state.graph
    return graph


def _get_chain() -> GraphCypherQAChain | None:
    """
    Get LangChain chain instance with bootstrap support.

    Phase 3.3: Tries to get chain from bootstrap state first,
    falls back to module-level chain for backwards compatibility.
    """
    # Check if bootstrap state is available (but don't force initialization)
    from neo4j_yass_mcp.bootstrap import _server_state

    if _server_state is not None:
        return _server_state.chain
    return chain


# Initialize FastMCP server (module-level for now, will move to bootstrap state)
mcp = FastMCP("neo4j-yass-mcp", version="1.3.0")

# Global variables for Neo4j and LangChain components
graph: SecureNeo4jGraph | None = None
chain: GraphCypherQAChain | None = None

# Thread pool for async operations (LangChain is sync)
_executor: ThreadPoolExecutor | None = None

# Read-only mode flag
_read_only_mode: bool = False

# Response token limit
_response_token_limit: int | None = None

# Debug mode for detailed error messages (disable in production)
_debug_mode: bool = False

# Tokenizer for accurate token counting (can be tiktoken, tokenizers, or None)
_tokenizer: Any = None


def get_client_id_from_context(ctx: Context | None = None) -> str:
    """
    Extract client identifier from FastMCP Context for rate limiting.

    Uses FastMCP's session_id when available for stable per-session rate limiting.
    Each MCP client connection gets a unique session_id that persists across
    multiple tool calls, enabling proper rate limit enforcement per client.

    Args:
        ctx: FastMCP Context object (auto-injected into tool functions)

    Returns:
        Client identifier string for rate limiting bucket selection.
        Format: "session_{session_id}" or "unknown" if no context available.

    Note:
        When session_id is None (can happen in some FastMCP versions/transports),
        returns "unknown" which means all requests share one bucket - a known
        limitation that requires FastMCP session tracking improvements.
    """
    if ctx is None:
        logger.warning("No Context provided to get_client_id_from_context - using 'unknown'")
        return "unknown"

    # Use FastMCP session_id if available (persistent across requests from same client)
    session_id = getattr(ctx, "session_id", None)
    if session_id:
        return f"session_{session_id}"

    # Fallback: Use client_id if available
    client_id = getattr(ctx, "client_id", None)
    if client_id:
        return f"client_{client_id}"

    # Last resort: fall back to request_id (unique per invocation)
    request_id = getattr(ctx, "request_id", None)
    if request_id:
        logger.warning(
            "FastMCP Context missing session_id/client_id - using request_id '%s' as fallback",
            request_id,
        )
        return f"request_{request_id}"

    logger.warning(
        "FastMCP Context missing session_id, client_id, and request_id - using 'unknown' bucket"
    )
    return "unknown"


def get_executor() -> ThreadPoolExecutor:
    """
    Get or create the thread pool executor for running sync LangChain operations.

    Phase 3.3: Now delegates to bootstrap module's get_executor() for better
    state management. Falls back to module-level _executor for backwards compatibility.
    """
    global _executor

    # Try to get executor from bootstrap state (preferred)
    try:
        from neo4j_yass_mcp.bootstrap import get_executor as bootstrap_get_executor
        return bootstrap_get_executor()
    except Exception:
        # Fallback to module-level executor for backwards compatibility
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="langchain_")
        return _executor


def check_read_only_access(cypher_query: str) -> str | None:
    """
    Check if a Cypher query is allowed in read-only mode.

    This is a backward compatibility wrapper that delegates to the
    security.validators module implementation.

    Args:
        cypher_query: The Cypher query to check

    Returns:
        Error message if query is not allowed, None if allowed
    """
    return _check_read_only_access_impl(cypher_query, read_only_mode=_read_only_mode)


def get_tokenizer() -> Any:
    """
    Get or create tokenizer for token estimation.

    Uses Hugging Face tokenizers library as the primary option:
    1. tokenizers (Hugging Face, handles most models including GPT-2, GPT-3, Llama, etc.)
    2. None (graceful degradation to character-based estimation)

    Returns:
        Tokenizer instance or None if unavailable
    """
    global _tokenizer
    if _tokenizer is None:
        # Try Hugging Face tokenizers first (handles most models including GPT-2, GPT-3, Llama, etc.)
        if Tokenizer is not None:
            try:
                logger.info("Initializing Hugging Face tokenizer (gpt2)")
                _tokenizer = Tokenizer.from_pretrained("gpt2")
                return _tokenizer
            except Exception as e:
                logger.warning(
                    f"Hugging Face tokenizer initialization failed: {e}, trying next backend. "
                    "Consider running 'python -c \"from tokenizers import Tokenizer; Tokenizer.from_pretrained('gpt2')\"' "
                    "to download tokenizer data."
                )

        # If tokenizer failed, use None to signal fallback mode
        if _tokenizer is None:
            logger.warning(
                "No tokenizer backend available. Using fallback character-based estimation (4 chars per token)."
            )

    return _tokenizer


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a text string using available tokenizer backend.

    Uses: tokenizers (Hugging Face) or character-based fallback.

    Args:
        text: The text to estimate tokens for

    Returns:
        Estimated token count
    """
    if text is None:
        return 0
    if not isinstance(text, str):
        text = str(text)

    tokenizer = get_tokenizer()

    if tokenizer is None:
        # Fallback: estimate 4 characters per token (conservative for GPT-2/3)
        return len(text) // 4

    # Handle tiktoken backend
    if TOKENIZER_BACKEND == "tiktoken":
        return len(tokenizer.encode(text))

    # Handle tokenizers backend
    if TOKENIZER_BACKEND == "tokenizers":
        encoding = tokenizer.encode(text)
        return len(encoding.ids)

    # Should never reach here, but fallback just in case
    return len(text) // 4


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error messages for security.

    In production mode (DEBUG_MODE=false), removes sensitive information
    from error messages while preserving enough context for debugging.

    Args:
        error: The exception to sanitize

    Returns:
        Sanitized error message safe for client exposure
    """
    global _debug_mode

    error_str = str(error)
    error_type = type(error).__name__

    # In debug mode, return full error details
    if _debug_mode:
        return error_str

    # Production mode: sanitize error messages
    # Remove potential sensitive information (paths, credentials, IPs)

    # Known safe error patterns that can be shown as-is
    # All patterns must be lowercase for case-insensitive matching
    safe_patterns = [
        "query exceeds maximum length",
        "empty query not allowed",
        "blocked: query contains dangerous pattern",
        "authentication failed",
        "connection refused",
        "timeout",
        "not found",
        "unauthorized",
    ]

    error_lower = error_str.lower()
    for pattern in safe_patterns:
        if pattern in error_lower:
            return error_str

    # For other errors, return generic message with error type
    return f"{error_type}: An error occurred. Enable DEBUG_MODE for details."


def truncate_response(data: Any, max_tokens: int | None = None) -> tuple[Any, bool]:
    """
    Truncate response data if it exceeds token limit.

    Args:
        data: The response data (can be string, dict, list, etc.)
        max_tokens: Maximum tokens allowed (uses global limit if None)

    Returns:
        Tuple of (truncated_data, was_truncated)
    """
    limit = max_tokens or _response_token_limit
    if limit is None:
        return data, False

    # Convert to JSON string for token estimation
    try:
        json_str = json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        json_str = str(data)

    estimated_tokens = estimate_tokens(json_str)

    if estimated_tokens <= limit:
        return data, False

    # Response is too large, truncate
    logger.warning(
        f"Response size ({estimated_tokens} tokens) exceeds limit ({limit} tokens). Truncating..."
    )

    if isinstance(data, list):
        # Truncate list items
        truncated = []
        current_tokens = 0
        for item in data:
            item_str = json.dumps(item, ensure_ascii=False, default=str)
            item_tokens = estimate_tokens(item_str)
            if current_tokens + item_tokens > limit:
                break
            truncated.append(item)
            current_tokens += item_tokens
        return truncated, True

    elif isinstance(data, str):
        # Truncate string
        char_limit = limit * 4  # Rough conversion back to characters
        return data[:char_limit] + "... [truncated]", True

    else:
        # For other types, convert to string and truncate
        char_limit = limit * 4
        truncated_str = json_str[:char_limit] + "... [truncated]"
        return truncated_str, True


def initialize_neo4j():
    """Initialize Neo4j graph and LangChain components"""
    global graph, chain, _read_only_mode, _response_token_limit, _debug_mode

    # Neo4j connection from config
    neo4j_uri = _config.neo4j.uri
    neo4j_username = _config.neo4j.username
    neo4j_password = _config.neo4j.password
    neo4j_database = _config.neo4j.database
    neo4j_timeout = _config.neo4j.read_timeout

    # Security: Check for default/weak passwords using zxcvbn (DRY approach)
    is_weak, weakness_reason = is_password_weak(
        neo4j_password, user_inputs=[neo4j_username, "neo4j"]
    )
    if is_weak:
        logger.error("🚨 SECURITY ERROR: Weak password detected!")
        logger.error(f"   Reason: {weakness_reason}")
        logger.error("   Set a strong password in NEO4J_PASSWORD environment variable")

        # Only allow weak passwords in development environment
        if _config.environment.allow_weak_passwords:
            if _config.environment.environment == "production":
                logger.error("❌ ALLOW_WEAK_PASSWORDS cannot be enabled in production environment")
                raise ValueError(
                    "ALLOW_WEAK_PASSWORDS=true is not allowed in production. "
                    "Set ENVIRONMENT=development to allow weak passwords during development."
                )
            else:
                logger.warning(
                    f"⚠️  ALLOW_WEAK_PASSWORDS=true - Weak password allowed (DEVELOPMENT ONLY!): {weakness_reason}"
                )
        else:
            raise ValueError(
                f"Weak password detected: {weakness_reason}. Set ALLOW_WEAK_PASSWORDS=true to override (NOT recommended for production)"
            )

    # Debug mode with production environment check
    _debug_mode = _config.environment.debug_mode
    if _debug_mode:
        if _config.environment.environment == "production":
            logger.error("❌ DEBUG_MODE cannot be enabled in production environment")
            raise ValueError(
                "DEBUG_MODE=true is not allowed in production. "
                "Set ENVIRONMENT=development to use DEBUG_MODE."
            )
        logger.warning(
            "⚠️  DEBUG_MODE=true - Detailed error messages will be returned (DEVELOPMENT ONLY!)"
        )
    else:
        logger.info("Production mode: Error messages will be sanitized")

    # Read-only mode
    _read_only_mode = _config.neo4j.read_only
    if _read_only_mode:
        logger.warning(
            "⚠️  Server running in READ-ONLY mode - write-capable tools will be hidden from MCP clients"
        )

    # Response token limit
    if _config.neo4j.response_token_limit:
        _response_token_limit = _config.neo4j.response_token_limit
        logger.info(f"Response token limit set to {_response_token_limit}")

    logger.info(f"Connecting to Neo4j at {neo4j_uri} (timeout: {neo4j_timeout}s)")
    graph = SecureNeo4jGraph(
        url=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
        database=neo4j_database,
        timeout=neo4j_timeout,
        sanitizer_enabled=_config.sanitizer.enabled,
        complexity_limit_enabled=_config.complexity_limiter.enabled,
        read_only_mode=_read_only_mode,
    )

    # LLM configuration from config
    llm_config = LLMConfig(
        provider=_config.llm.provider,
        model=_config.llm.model,
        temperature=_config.llm.temperature,
        api_key=_config.llm.api_key,
        streaming=_config.llm.streaming,
    )

    logger.info(f"Initializing LLM: {llm_config.provider}/{llm_config.model}")
    llm = chatLLM(llm_config)

    # Create GraphCypherQAChain
    # Note: allow_dangerous_requests is required for LangChain's GraphCypherQAChain
    # but we add our own security layer via query sanitizer
    allow_dangerous = _config.neo4j.allow_dangerous_requests

    if allow_dangerous:
        logger.warning(
            "⚠️  LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=true - LangChain safety checks DISABLED!"
        )
        logger.warning("⚠️  Relying solely on query sanitizer for security. Use with caution!")

    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        allow_dangerous_requests=allow_dangerous,
        verbose=True,
        return_intermediate_steps=True,
    )

    logger.info("Neo4j MCP Server initialized successfully")


# NOTE: Initialization is deferred to the main() entry point to avoid
# performing network/LLM connections at import time (improves testability).



# =============================================================================
# MCP Tools and Resources (Phase 3.4: Extracted to handlers/ module)
# =============================================================================

# Import tool and resource handlers from extracted modules
from neo4j_yass_mcp.handlers import (
    analyze_query_performance,
    execute_cypher,
    get_database_info,
    get_schema,
    query_graph,
    refresh_schema,
)

# =============================================================================
# Main Entry Point
# =============================================================================


def cleanup():
    """
    Cleanup resources on shutdown.

    Ensures graceful shutdown of:
    - Thread pool executor (waits for running tasks)
    - Neo4j driver connections

    This function is registered with atexit to ensure cleanup
    happens even on unexpected termination.
    """
    global _executor, graph

    logger.info("Starting cleanup process...")

    # Shutdown thread pool executor
    if _executor is not None:
        logger.info("Shutting down thread pool executor...")
        try:
            # Wait for tasks to complete
            _executor.shutdown(wait=True)
            logger.info("✓ Thread pool executor shutdown complete")
        except Exception as e:
            logger.error(f"✗ Error shutting down executor: {e}", exc_info=True)
        finally:
            _executor = None
    else:
        logger.debug("Thread pool executor already cleaned up or not initialized")

    # Close Neo4j driver connections
    if graph is not None:
        logger.info("Closing Neo4j driver connections...")
        try:
            # Check if graph has a driver attribute
            if hasattr(graph, "_driver") and graph._driver is not None:
                # Close the driver (this closes all sessions and connections)
                graph._driver.close()
                logger.info("✓ Neo4j driver closed successfully")
            else:
                logger.warning("Neo4j graph has no driver to close")
        except AttributeError as e:
            logger.warning(f"⚠ Could not access Neo4j driver: {e}")
        except Exception as e:
            logger.error(f"✗ Error closing Neo4j connections: {e}", exc_info=True)
    else:
        logger.debug("Neo4j graph already cleaned up or not initialized")

    logger.info("Cleanup process complete")


def register_mcp_components():
    """Register all MCP resources and tools with their decorators.

    This function applies all FastMCP decorators that were deferred during import
    to avoid validation issues during pytest collection.
    """
    # Register resources
    mcp.resource("neo4j://schema")(
        log_tool_invocation("get_schema")(
            rate_limit_tool(
                limiter=lambda: tool_rate_limiter,
                client_id_extractor=get_client_id_from_context,
                limit=RESOURCE_RATE_LIMIT,
                window=RESOURCE_RATE_WINDOW,
                enabled=lambda: resource_rate_limit_enabled,
                tool_name="get_schema",
                build_error_response=_resource_rate_limit_message("Schema access"),
            )(get_schema)
        )
    )

    mcp.resource("neo4j://database-info")(
        log_tool_invocation("get_database_info")(
            rate_limit_tool(
                limiter=lambda: tool_rate_limiter,
                client_id_extractor=get_client_id_from_context,
                limit=RESOURCE_RATE_LIMIT,
                window=RESOURCE_RATE_WINDOW,
                enabled=lambda: resource_rate_limit_enabled,
                tool_name="get_database_info",
                build_error_response=_resource_rate_limit_message("Database info access"),
            )(get_database_info)
        )
    )

    # Register tools
    mcp.tool()(
        log_tool_invocation("query_graph")(
            rate_limit_tool(
                limiter=lambda: tool_rate_limiter,
                client_id_extractor=get_client_id_from_context,
                limit=QUERY_GRAPH_RATE_LIMIT,
                window=QUERY_GRAPH_RATE_WINDOW,
                enabled=lambda: tool_rate_limit_enabled,
                tool_name="query_graph",
                build_error_response=_build_query_graph_rate_limit_error,
            )(query_graph)
        )
    )

    # Register execute_cypher tool only if not in read-only mode
    if not _read_only_mode:
        mcp.tool()(
            log_tool_invocation("execute_cypher")(
                rate_limit_tool(
                    limiter=lambda: tool_rate_limiter,
                    client_id_extractor=get_client_id_from_context,
                    limit=EXECUTE_CYPHER_RATE_LIMIT,
                    window=EXECUTE_CYPHER_RATE_WINDOW,
                    enabled=lambda: tool_rate_limit_enabled,
                    tool_name="execute_cypher",
                    build_error_response=_build_execute_rate_limit_error,
                )(execute_cypher)
            )
        )
        logger.info("Tool 'execute_cypher' registered (write operations enabled)")
    else:
        logger.info("Tool 'execute_cypher' registration skipped (read-only mode active)")

    mcp.tool()(
        log_tool_invocation("refresh_schema")(
            rate_limit_tool(
                limiter=lambda: tool_rate_limiter,
                client_id_extractor=get_client_id_from_context,
                limit=REFRESH_SCHEMA_RATE_LIMIT,
                window=REFRESH_SCHEMA_RATE_WINDOW,
                enabled=lambda: tool_rate_limit_enabled,
                tool_name="refresh_schema",
                build_error_response=_build_refresh_schema_rate_limit_error,
            )(refresh_schema)
        )
    )

    # Register query analysis tool
    mcp.tool()(
        log_tool_invocation("analyze_query_performance")(
            rate_limit_tool(
                limiter=lambda: tool_rate_limiter,
                client_id_extractor=get_client_id_from_context,
                limit=ANALYZE_QUERY_RATE_LIMIT,
                window=ANALYZE_QUERY_RATE_WINDOW,
                enabled=lambda: tool_rate_limit_enabled,
                tool_name="analyze_query_performance",
                build_error_response=_build_analyze_query_rate_limit_error,
            )(analyze_query_performance)
        )
    )

    # The tools and resources are now registered with FastMCP


def main():
    """Main entry point for the MCP server"""
    import atexit

    atexit.register(cleanup)

    # Initialize connections (Neo4j, LLM, chain) here instead of at import time.
    try:
        initialize_neo4j()
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j/LLM components: {e}", exc_info=True)
        raise

    # Register all MCP resources and tools with their decorators
    register_mcp_components()

    # Register execute_cypher tool after initialization so read-only mode is respected
    if not _read_only_mode:
        logger.info("Tool 'execute_cypher' registered (write operations enabled)")
    else:
        logger.info("Tool 'execute_cypher' hidden (read-only mode active)")

    transport = _config.server.transport

    if transport in ("sse", "http"):
        # Network transport (SSE legacy or HTTP modern)
        host = _config.server.host

        # Get preferred ports from environment
        preferred_ports = get_preferred_ports_from_env()
        requested_port = _config.server.port

        # If requested port is not in preferred list, add it as first choice
        if requested_port not in preferred_ports:
            preferred_ports.insert(0, requested_port)

        # Find an available port
        port = find_available_port(host, preferred_ports)

        if port is None:
            logger.error("No available ports found. Cannot start network server.")
            raise RuntimeError(
                f"No available ports found. Tried: {preferred_ports} and fallback range 8000-9000"
            )

        if port != requested_port:
            logger.warning(
                f"Requested port {requested_port} is not available. Using port {port} instead."
            )

        # Start server based on transport mode
        if transport == "http":
            # Modern Streamable HTTP transport (recommended for production)
            server_path = _config.server.path
            logger.info(f"Starting MCP server with HTTP transport on {host}:{port}{server_path}")
            logger.info(f"Async worker threads: {_config.server.max_workers}")
            logger.info("HTTP transport uses modern Streamable HTTP protocol (MCP 2025 standard)")
            mcp.run(transport="http", host=host, port=port, path=server_path)
        else:
            # SSE transport (legacy, backward compatibility)
            logger.info(f"Starting MCP server with SSE transport on {host}:{port}")
            logger.warning("SSE transport is legacy. Consider using 'http' for new deployments.")
            logger.info(f"Async worker threads: {_config.server.max_workers}")
            mcp.run(transport="sse", host=host, port=port)
    else:
        # stdio transport (default) for MCP clients like Claude Desktop
        logger.info("Starting MCP server with stdio transport")
        logger.info(f"Async worker threads: {_config.server.max_workers}")
        mcp.run()
