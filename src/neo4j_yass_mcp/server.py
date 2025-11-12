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

from neo4j_yass_mcp.config import (
    LLMConfig,
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

# Initialize audit logger for compliance
initialize_audit_logger()

# Initialize query sanitizer for security
sanitizer_enabled = os.getenv("SANITIZER_ENABLED", "true").lower() == "true"
if sanitizer_enabled:
    initialize_sanitizer(
        strict_mode=os.getenv("SANITIZER_STRICT_MODE", "false").lower() == "true",
        allow_apoc=os.getenv("SANITIZER_ALLOW_APOC", "false").lower() == "true",
        allow_schema_changes=os.getenv("SANITIZER_ALLOW_SCHEMA_CHANGES", "false").lower() == "true",
        block_non_ascii=os.getenv("SANITIZER_BLOCK_NON_ASCII", "false").lower() == "true",
        max_query_length=int(os.getenv("SANITIZER_MAX_QUERY_LENGTH", "10000")),
    )
    logger.info("Query sanitizer enabled (injection + UTF-8 attack protection active)")
else:  # pragma: no cover - Module initialization, tested in production
    logger.warning("⚠️  Query sanitizer disabled - injection protection is OFF!")

# Initialize query complexity limiter
complexity_limit_enabled = os.getenv("COMPLEXITY_LIMIT_ENABLED", "true").lower() == "true"
if complexity_limit_enabled:
    initialize_complexity_limiter(
        max_complexity=int(os.getenv("MAX_QUERY_COMPLEXITY", "100")),
        max_variable_path_length=int(os.getenv("MAX_VARIABLE_PATH_LENGTH", "10")),
        require_limit_unbounded=os.getenv("REQUIRE_LIMIT_UNBOUNDED", "true").lower() == "true",
    )
    logger.info("Query complexity limiter enabled (prevents resource exhaustion attacks)")
else:  # pragma: no cover - Module initialization, tested in production
    logger.warning("⚠️  Query complexity limiter disabled - no protection against complex queries!")

# Initialize rate limiter
rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
if rate_limit_enabled:
    initialize_rate_limiter(
        rate=int(os.getenv("RATE_LIMIT_REQUESTS", "10")),
        per_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
        burst=int(os.getenv("RATE_LIMIT_BURST", "20")) if os.getenv("RATE_LIMIT_BURST") else None,
    )
    logger.info("Rate limiter enabled (prevents abuse through excessive requests)")
else:  # pragma: no cover - Module initialization, tested in production
    logger.warning("⚠️  Rate limiter disabled - no protection against request flooding!")

# Decorator-based MCP tool rate limiter
tool_rate_limiter = RateLimiterService()
tool_rate_limit_enabled = os.getenv("MCP_TOOL_RATE_LIMIT_ENABLED", "true").lower() == "true"
QUERY_GRAPH_RATE_LIMIT = int(os.getenv("MCP_QUERY_GRAPH_LIMIT", "10"))
QUERY_GRAPH_RATE_WINDOW = int(os.getenv("MCP_QUERY_GRAPH_WINDOW", "60"))
EXECUTE_CYPHER_RATE_LIMIT = int(os.getenv("MCP_EXECUTE_CYPHER_LIMIT", "10"))
EXECUTE_CYPHER_RATE_WINDOW = int(os.getenv("MCP_EXECUTE_CYPHER_WINDOW", "60"))
REFRESH_SCHEMA_RATE_LIMIT = int(os.getenv("MCP_REFRESH_SCHEMA_LIMIT", "5"))
REFRESH_SCHEMA_RATE_WINDOW = int(os.getenv("MCP_REFRESH_SCHEMA_WINDOW", "120"))
resource_rate_limit_enabled = os.getenv("MCP_RESOURCE_RATE_LIMIT_ENABLED", "true").lower() == "true"
RESOURCE_RATE_LIMIT = int(os.getenv("MCP_RESOURCE_LIMIT", "20"))
RESOURCE_RATE_WINDOW = int(os.getenv("MCP_RESOURCE_WINDOW", "60"))

# Query analysis rate limits
ANALYZE_QUERY_RATE_LIMIT = int(os.getenv("MCP_ANALYZE_QUERY_LIMIT", "15"))
ANALYZE_QUERY_RATE_WINDOW = int(os.getenv("MCP_ANALYZE_QUERY_WINDOW", "60"))


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


# Initialize FastMCP server
mcp = FastMCP("neo4j-yass-mcp", version="1.1.0")

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
    """Get or create the thread pool executor for running sync LangChain operations."""
    global _executor
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

    # Neo4j connection
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    neo4j_timeout = int(os.getenv("NEO4J_READ_TIMEOUT", "30"))

    # Security: Check for default/weak passwords using zxcvbn (DRY approach)
    is_weak, weakness_reason = is_password_weak(
        neo4j_password, user_inputs=[neo4j_username, "neo4j"]
    )
    if is_weak:
        logger.error("🚨 SECURITY ERROR: Weak password detected!")
        logger.error(f"   Reason: {weakness_reason}")
        logger.error("   Set a strong password in NEO4J_PASSWORD environment variable")

        # Only allow weak passwords in development environment
        allow_weak_passwords = os.getenv("ALLOW_WEAK_PASSWORDS", "false").lower() == "true"
        environment = os.getenv("ENVIRONMENT", "development").lower()

        if allow_weak_passwords:
            if environment in ("production", "prod"):
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
    _debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
    if _debug_mode:
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment in ("production", "prod"):
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
    _read_only_mode = os.getenv("NEO4J_READ_ONLY", "false").lower() == "true"
    if _read_only_mode:
        logger.warning(
            "⚠️  Server running in READ-ONLY mode - write-capable tools will be hidden from MCP clients"
        )

    # Response token limit
    token_limit_str = os.getenv("NEO4J_RESPONSE_TOKEN_LIMIT")
    if token_limit_str:
        try:
            _response_token_limit = int(token_limit_str)
            logger.info(f"Response token limit set to {_response_token_limit}")
        except ValueError:
            logger.warning(f"Invalid NEO4J_RESPONSE_TOKEN_LIMIT value: {token_limit_str}")

    logger.info(f"Connecting to Neo4j at {neo4j_uri} (timeout: {neo4j_timeout}s)")
    graph = SecureNeo4jGraph(
        url=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
        database=neo4j_database,
        timeout=neo4j_timeout,
        sanitizer_enabled=sanitizer_enabled,
        complexity_limit_enabled=complexity_limit_enabled,
        read_only_mode=_read_only_mode,
    )

    # LLM configuration
    llm_config = LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        model=os.getenv("LLM_MODEL", "gpt-4"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        api_key=os.getenv("LLM_API_KEY", ""),
        streaming=os.getenv("LLM_STREAMING", "false").lower() == "true",
    )

    logger.info(f"Initializing LLM: {llm_config.provider}/{llm_config.model}")
    llm = chatLLM(llm_config)

    # Create GraphCypherQAChain
    # Note: allow_dangerous_requests is required for LangChain's GraphCypherQAChain
    # but we add our own security layer via query sanitizer
    allow_dangerous = os.getenv("LANGCHAIN_ALLOW_DANGEROUS_REQUESTS", "false").lower() == "true"

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
# Resources
# =============================================================================


# Resource and tool definitions without decorators applied at import time
# to avoid FastMCP validation during import/pytest collection
# Decorators are applied in register_mcp_components() called from main()
async def get_schema(ctx: Context | None = None) -> str:
    """
    Get the Neo4j graph database schema.

    Returns the complete schema including node labels, relationship types,
    and their properties.
    """
    if graph is None:
        return "Error: Neo4j graph not initialized"

    try:
        schema = graph.get_schema
        return f"Neo4j Graph Schema:\n\n{schema}"
    except Exception as e:
        return f"Error retrieving schema: {str(e)}"


async def get_database_info(ctx: Context | None = None) -> str:
    """
    Get information about the Neo4j database connection.

    Returns details about the connected database.
    """
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    return f"""Neo4j Database Information:

URI: {neo4j_uri}
Database: {neo4j_database}
Status: Connected
"""


# =============================================================================
# Tools
# =============================================================================


# Tool definitions without decorators applied at import time
# to avoid FastMCP validation during import/pytest collection
# Decorators are applied in register_mcp_components() called from main()
async def query_graph(query: str, ctx: Context | None = None) -> dict[str, Any]:
    """
    Query the Neo4j graph database using natural language.

    The LLM will automatically translate your natural language question into a
    Cypher query, execute it against the Neo4j database, and return the results
    in a human-readable format.

    This function runs asynchronously, allowing parallel query execution.

    Notes:
    - When NEO4J_READ_ONLY=true, if the LLM generates a write operation (CREATE, MERGE, etc.),
      the query will be blocked and return an error.
    - When NEO4J_RESPONSE_TOKEN_LIMIT is set, large intermediate steps will be
      automatically truncated to stay within token limits.

    Args:
        query: Natural language question about the graph data

    Returns:
        Dictionary containing the answer, generated Cypher query, and intermediate steps.
        If truncated, includes 'truncated': true and a warning message.

    Examples:
        - "Who starred in Top Gun?"
        - "What are all the movies in the database?"
        - "Show me actors who have worked together"
    """
    if chain is None or graph is None:
        return {"error": "Neo4j or LangChain not initialized", "success": False}

    # Audit log the query
    audit_logger = get_audit_logger()
    if audit_logger:
        audit_logger.log_query(tool="query_graph", query=query)

    try:
        logger.info(f"Processing natural language query: {query}")

        # Run LangChain's GraphCypherQAChain in thread pool (it's sync)
        # Security checks (sanitization, complexity, read-only) now happen
        # at the SecureNeo4jGraph layer BEFORE query execution
        start_time = time.time()

        # Use modern asyncio.to_thread() pattern (Python 3.9+)
        result = await asyncio.to_thread(chain.invoke, {"query": query})

        execution_time_ms = (time.time() - start_time) * 1000

        # Extract generated Cypher query from intermediate steps (for logging/audit)
        generated_cypher = ""
        if "intermediate_steps" in result and result["intermediate_steps"]:
            if (
                isinstance(result["intermediate_steps"], list)
                and len(result["intermediate_steps"]) > 0
            ):
                first_step = result["intermediate_steps"][0]
                if isinstance(first_step, dict) and "query" in first_step:
                    generated_cypher = first_step["query"]

        # Apply response size limiting to both intermediate steps AND final answer
        truncated_steps, steps_truncated = truncate_response(result.get("intermediate_steps", []))
        truncated_answer, answer_truncated = truncate_response(result.get("result", ""))

        was_truncated = steps_truncated or answer_truncated

        response = {
            "question": query,
            "answer": truncated_answer,
            "generated_cypher": generated_cypher,
            "intermediate_steps": truncated_steps,
            "success": True,
        }

        if was_truncated:
            response["truncated"] = True
            truncation_parts = []
            if steps_truncated:
                truncation_parts.append("intermediate steps")
            if answer_truncated:
                truncation_parts.append("answer")
            response["warning"] = (
                f"Response truncated ({', '.join(truncation_parts)}) due to size limits"
            )
            logger.info(f"query_graph response truncated: {', '.join(truncation_parts)}")

        # Audit log the response
        if audit_logger:
            audit_logger.log_response(
                tool="query_graph",
                query=query,
                response=response,
                execution_time_ms=execution_time_ms,
            )

        return response

    except ValueError as e:
        # ValueError raised by SecureNeo4jGraph when security checks fail
        # (sanitization, complexity, or read-only mode violations)
        logger.warning(f"Security check blocked query: {str(e)}")

        # Extract generated Cypher if available for audit logging
        generated_cypher = ""
        try:
            # Try to extract from error context if possible
            # For now, just use the error message
            pass
        except Exception:
            logger.debug("Could not extract generated Cypher from error context.")

        # Determine which security check failed based on error message
        error_msg = str(e)
        if "sanitizer" in error_msg.lower():
            error_type = "sanitizer_blocked"
        elif "complexity" in error_msg.lower():
            error_type = "complexity_blocked"
        elif "read-only" in error_msg.lower():
            error_type = "read_only_blocked"
        else:
            error_type = "security_blocked"

        error_response = {
            "error": error_msg,
            "security_blocked": True,
            "block_type": error_type,
            "success": False,
        }

        # Audit log the security block
        if audit_logger:
            audit_logger.log_error(
                tool="query_graph",
                query=query,
                error=error_msg,
                error_type=error_type,
                metadata={"security_blocked": True},
            )

        return error_response

    except Exception as e:
        logger.error(f"Error in query_graph: {str(e)}", exc_info=True)

        # Sanitize error message for security
        safe_error_message = sanitize_error_message(e)

        error_response = {"error": safe_error_message, "type": type(e).__name__, "success": False}

        # Audit log the error (with full details)
        if audit_logger:
            audit_logger.log_error(
                tool="query_graph",
                query=query,
                error=str(e),  # Log full error for debugging
                error_type=type(e).__name__,
            )

        return error_response


async def _execute_cypher_impl(
    cypher_query: str,
    ctx: Context | None,
    parameters: dict[str, Any | None] | None = None,
) -> dict[str, Any]:
    """
    Internal implementation of execute_cypher.

    Execute a raw Cypher query against the Neo4j database.

    Use this when you need precise control over the query or when natural
    language translation isn't suitable.

    This function runs asynchronously, allowing parallel query execution.

    Note:
    - When NEO4J_READ_ONLY=true, write operations (CREATE, MERGE, SET, DELETE, etc.)
      will be blocked and return an error.
    - When NEO4J_RESPONSE_TOKEN_LIMIT is set, large responses will be automatically
      truncated. The response will include 'truncated': true and counts of items.

    Args:
        cypher_query: The Cypher query to execute
        ctx: FastMCP Context for session identification
        parameters: Optional dictionary of parameters for the query

    Returns:
        Dictionary containing the query results and metadata. If truncated, includes:
        - truncated: true
        - original_count: number of items before truncation
        - returned_count: number of items after truncation

    Examples:
        - cypher_query: "MATCH (n:Person) RETURN n.name LIMIT 5"
        - cypher_query: "MATCH (p:Person {name: $name}) RETURN p"
          parameters: {"name": "Tom Cruise"}
    """
    if graph is None:
        return {"error": "Neo4j graph not initialized", "success": False}

    # Sanitize query and parameters (SISO prevention)
    if sanitizer_enabled:
        is_safe, sanitize_error, warnings = sanitize_query(cypher_query, parameters)

        if not is_safe:
            logger.warning(f"Blocked unsafe query: {sanitize_error}")
            error_response = {
                "error": f"Query blocked by sanitizer: {sanitize_error}",
                "query": cypher_query[:200],  # Only show first 200 chars
                "sanitizer_blocked": True,
                "success": False,
            }

            # Audit log the blocked query
            audit_logger = get_audit_logger()
            if audit_logger:
                audit_logger.log_error(
                    tool="execute_cypher",
                    query=cypher_query,
                    error=sanitize_error or "Query blocked by sanitizer",
                    metadata={"sanitizer_blocked": True},
                )

            return error_response

        # Log warnings if any
        if warnings:
            for warning in warnings:
                logger.warning(f"Query sanitizer warning: {warning}")

    # Check query complexity
    if complexity_limit_enabled:
        is_allowed, complexity_error, complexity_score = check_query_complexity(cypher_query)

        if not is_allowed:
            logger.warning(f"Blocked complex query: {complexity_error}")
            error_response = {
                "error": f"Query blocked by complexity limiter: {complexity_error}",
                "query": cypher_query[:200],
                "complexity_score": complexity_score.total_score if complexity_score else None,
                "complexity_limit": complexity_score.max_allowed if complexity_score else None,
                "complexity_blocked": True,
                "success": False,
            }

            # Audit log the blocked query
            audit_logger = get_audit_logger()
            if audit_logger:
                audit_logger.log_error(
                    tool="execute_cypher",
                    query=cypher_query,
                    error=complexity_error or "Query blocked by complexity limiter",
                    metadata={
                        "complexity_blocked": True,
                        "complexity_score": complexity_score.total_score
                        if complexity_score
                        else None,
                    },
                )

            return error_response

        # Log complexity warnings if any
        if complexity_score and complexity_score.warnings:
            for warning in complexity_score.warnings:
                logger.info(f"Query complexity warning: {warning}")

    # Audit log the query
    audit_logger = get_audit_logger()
    if audit_logger:
        audit_logger.log_query(tool="execute_cypher", query=cypher_query, parameters=parameters)

    # Check read-only access control
    read_only_error_msg = check_read_only_access(cypher_query)
    if read_only_error_msg:
        # Audit log the error
        if audit_logger:
            audit_logger.log_error(
                tool="execute_cypher", query=cypher_query, error=read_only_error_msg
            )
        return {"error": read_only_error_msg}

    try:
        logger.info(f"Executing Cypher query: {cypher_query}")

        params = parameters or {}

        # Run query in thread pool (Neo4j driver is sync)
        start_time = time.time()

        # Use modern asyncio.to_thread() pattern (Python 3.9+)
        result = await asyncio.to_thread(graph.query, cypher_query, params=params)

        execution_time_ms = (time.time() - start_time) * 1000

        # Apply response size limiting
        truncated_result, was_truncated = truncate_response(result)

        response = {
            "query": cypher_query,
            "parameters": params,
            "result": truncated_result,
            "count": len(result) if isinstance(result, list) else 1,
            "success": True,
        }

        if was_truncated:
            response["truncated"] = True
            response["original_count"] = len(result) if isinstance(result, list) else 1
            response["returned_count"] = (
                len(truncated_result) if isinstance(truncated_result, list) else None
            )
            logger.info(
                f"Response truncated: {response.get('original_count')} → {response.get('returned_count')} items"
            )

        # Audit log the response
        if audit_logger:
            audit_logger.log_response(
                tool="execute_cypher",
                query=cypher_query,
                response=response,
                execution_time_ms=execution_time_ms,
                metadata={"parameters": params},
            )

        return response

    except Exception as e:
        logger.error(f"Error in execute_cypher: {str(e)}", exc_info=True)

        # Sanitize error message for security
        safe_error_message = sanitize_error_message(e)

        error_response = {
            "error": safe_error_message,
            "type": type(e).__name__,
            "query": cypher_query[:100] + "..." if len(cypher_query) > 100 else cypher_query,
            "success": False,
        }

        # Audit log the error (with full details)
        if audit_logger:
            audit_logger.log_error(
                tool="execute_cypher",
                query=cypher_query,
                error=str(e),  # Log full error for debugging
                error_type=type(e).__name__,
            )

        return error_response


# The `execute_cypher` implementation is defined here but registered with
# the MCP runtime only after `initialize_neo4j()` runs in `main()`. This
# ensures `_read_only_mode` is set correctly before deciding whether to
# expose the tool to MCP clients.
# Tool definition without decorator applied at import time
# Decorator is applied in register_mcp_components() called from main()
async def execute_cypher(
    cypher_query: str,
    ctx: Context | None = None,
    parameters: dict[str, Any | None] | None = None,
) -> dict[str, Any]:
    """
    Execute a raw Cypher query against the Neo4j database.

    Use this when you need precise control over the query or when natural
    language translation isn't suitable. Supports both read and write operations.

    This function runs asynchronously, allowing parallel query execution.
    """
    return await _execute_cypher_impl(cypher_query, ctx, parameters)


# Tool definition without decorator applied at import time
# Decorator is applied in register_mcp_components() called from main()
async def refresh_schema(ctx: Context | None = None) -> dict[str, Any]:
    """
    Refresh the cached schema information from the Neo4j database.

    Call this after making structural changes to the database (adding/removing
    labels, relationship types, or properties) to ensure the schema is up to date.

    This function runs asynchronously.

    Returns:
        Dictionary containing the updated schema and success status
    """
    if graph is None:
        return {"error": "Neo4j graph not initialized", "success": False}

    try:
        logger.info("Refreshing graph schema")

        # Run schema refresh in thread pool
        # Use modern asyncio.to_thread() pattern (Python 3.9+)
        await asyncio.to_thread(graph.refresh_schema)
        schema = graph.get_schema

        return {"schema": schema, "message": "Schema refreshed successfully", "success": True}

    except Exception as e:
        logger.error(f"Error in refresh_schema: {str(e)}", exc_info=True)
        return {"error": str(e), "type": type(e).__name__, "success": False}


# Tool definition without decorator applied at import time
# Decorator is applied in register_mcp_components() called from main()
async def analyze_query_performance(
    query: str,
    mode: str = "profile",
    include_recommendations: bool = True,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """
    Analyze Cypher query performance and provide optimization recommendations.

    This tool analyzes query execution plans using Neo4j's EXPLAIN and PROFILE
    capabilities to identify performance bottlenecks and suggest optimizations.

    Analysis modes:
    - "explain": Shows execution plan without running the query (faster)
    - "profile": Shows execution plan with runtime statistics (more detailed)

    The analysis includes:
    - Performance bottleneck detection
    - Optimization recommendations with severity scoring
    - Cost estimation and resource usage prediction
    - Execution time and memory usage estimates

    This function runs asynchronously and integrates with the existing security
    layer to ensure safe query analysis.

    Args:
        query: The Cypher query to analyze
        mode: Analysis mode - "explain" or "profile" (default: "profile")
        include_recommendations: Whether to include optimization recommendations (default: True)

    Returns:
        Dictionary containing analysis results including:
        - execution_plan: Parsed execution plan details
        - bottlenecks: List of detected performance bottlenecks
        - recommendations: Prioritized optimization suggestions
        - cost_estimate: Resource usage and risk assessment
        - analysis_summary: High-level summary of findings

    Examples:
        - query: "MATCH (n:Person)-[:KNOWS]->(m:Person) RETURN n.name, m.name"
        - query: "MATCH (n:Movie) WHERE n.rating > 8 RETURN n.title, n.rating"
        - mode: "explain" for quick plan analysis
        - mode: "profile" for detailed performance statistics
    """
    if graph is None:
        return {"error": "Neo4j graph not initialized", "success": False}

    # Audit log the analysis request
    audit_logger = get_audit_logger()
    if audit_logger:
        audit_logger.log_query(
            tool="analyze_query_performance", query=query, parameters={"mode": mode}
        )

    try:
        logger.info(f"Analyzing query performance in {mode} mode: {query[:100]}...")

        # Import the query analyzer (lazy import to avoid circular dependencies)
        from neo4j_yass_mcp.tools import QueryPlanAnalyzer

        # Initialize the analyzer with the secure graph
        analyzer = QueryPlanAnalyzer(graph)

        # Run the analysis
        start_time = time.time()
        result = await analyzer.analyze_query(
            query=query,
            mode=mode,
            include_recommendations=include_recommendations,
            include_cost_estimate=True,
        )
        execution_time_ms = (time.time() - start_time) * 1000

        # Format the result for user-friendly output
        formatted_result = {
            "query": query,
            "mode": mode,
            "success": True,
            "analysis_summary": result.get("analysis_summary", {}),
            "bottlenecks_found": len(result.get("bottlenecks", [])),
            "recommendations_count": len(result.get("recommendations", [])),
            "cost_score": result.get("cost_estimate", {}).get("cost_score", 0),
            "risk_level": result.get("cost_estimate", {}).get("risk_level", "unknown"),
            "execution_time_ms": int(execution_time_ms),
            "detailed_analysis": result
            if include_recommendations
            else {
                "execution_plan": result.get("execution_plan", {}),
                "cost_estimate": result.get("cost_estimate", {}),
                "bottlenecks": [],  # Empty list when recommendations disabled
                "recommendations": [],  # Empty list when recommendations disabled
            },
        }

        # Add formatted report if recommendations are included
        if include_recommendations:
            formatted_report = analyzer.format_analysis_report(result, format_type="text")
            formatted_result["analysis_report"] = formatted_report

        # Audit log the successful analysis
        if audit_logger:
            audit_logger.log_response(
                tool="analyze_query_performance",
                query=query,
                response=formatted_result,
                execution_time_ms=execution_time_ms,
                metadata={"mode": mode, "bottlenecks_found": formatted_result["bottlenecks_found"]},
            )

        logger.info(
            f"Query analysis completed successfully. Found {formatted_result['bottlenecks_found']} bottlenecks, {formatted_result['recommendations_count']} recommendations"
        )
        return formatted_result

    except ValueError as e:
        # Handle analysis-specific errors (like invalid mode)
        logger.warning(f"Query analysis failed: {str(e)}")
        error_response = {"error": str(e), "success": False, "error_type": "ValueError"}

        # Audit log the error
        if audit_logger:
            audit_logger.log_error(
                tool="analyze_query_performance",
                query=query,
                error=str(e),
                error_type="analysis_error",
            )

        return error_response

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in analyze_query_performance: {str(e)}", exc_info=True)

        # Sanitize error message for security
        safe_error_message = sanitize_error_message(e)

        error_response = {
            "error": safe_error_message,
            "error_type": type(e).__name__,
            "success": False,
        }

        # Audit log the error (with full details for debugging)
        if audit_logger:
            audit_logger.log_error(
                tool="analyze_query_performance",
                query=query,
                error=str(e),  # Log full error for debugging
                error_type=type(e).__name__,
            )

        return error_response


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

    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

    if transport in ("sse", "http"):
        # Network transport (SSE legacy or HTTP modern)
        host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")

        # Get preferred ports from environment
        preferred_ports = get_preferred_ports_from_env()
        requested_port = int(os.getenv("MCP_SERVER_PORT", "8000"))

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
            server_path = os.getenv("MCP_SERVER_PATH", "/mcp/")
            logger.info(f"Starting MCP server with HTTP transport on {host}:{port}{server_path}")
            logger.info(f"Async worker threads: {os.getenv('MCP_MAX_WORKERS', '10')}")
            logger.info("HTTP transport uses modern Streamable HTTP protocol (MCP 2025 standard)")
            mcp.run(transport="http", host=host, port=port, path=server_path)
        else:
            # SSE transport (legacy, backward compatibility)
            logger.info(f"Starting MCP server with SSE transport on {host}:{port}")
            logger.warning("SSE transport is legacy. Consider using 'http' for new deployments.")
            logger.info(f"Async worker threads: {os.getenv('MCP_MAX_WORKERS', '10')}")
            mcp.run(transport="sse", host=host, port=port)
    else:
        # stdio transport (default) for MCP clients like Claude Desktop
        logger.info("Starting MCP server with stdio transport")
        logger.info(f"Async worker threads: {os.getenv('MCP_MAX_WORKERS', '10')}")
        mcp.run()
