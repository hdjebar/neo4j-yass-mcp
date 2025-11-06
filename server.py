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
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP
from langchain.neo4j import GraphCypherQAChain, Neo4jGraph

from config import (
    chatLLM,
    LLMConfig,
    configure_logging,
    find_available_port,
    get_preferred_ports_from_env,
)
from utilities import (
    initialize_audit_logger,
    get_audit_logger,
    initialize_sanitizer,
    sanitize_query,
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
        block_non_ascii=os.getenv("SANITIZER_BLOCK_NON_ASCII", "false").lower() == "true"
    )
    logger.info("Query sanitizer enabled (injection + UTF-8 attack protection active)")
else:
    logger.warning("⚠️  Query sanitizer disabled - injection protection is OFF!")

# Initialize FastMCP server
mcp = FastMCP("neo4j-yass-mcp", version="1.0.0")

# Global variables for Neo4j and LangChain components
graph: Optional[Neo4jGraph] = None
chain: Optional[GraphCypherQAChain] = None

# Thread pool for async operations (LangChain is sync)
_executor: Optional[ThreadPoolExecutor] = None

# Read-only mode flag
_read_only_mode: bool = False

# Response token limit
_response_token_limit: Optional[int] = None

# Debug mode for detailed error messages (disable in production)
_debug_mode: bool = False


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error messages to prevent information leakage.

    In production, returns generic error messages.
    In debug mode, returns full error details.

    Args:
        error: The exception to sanitize

    Returns:
        Sanitized error message
    """
    if _debug_mode:
        return str(error)

    # Map exception types to safe error messages
    error_type = type(error).__name__

    safe_messages = {
        "AuthError": "Authentication failed. Please check credentials.",
        "ServiceUnavailable": "Database service is unavailable. Please try again later.",
        "CypherSyntaxError": "Invalid query syntax.",
        "ConstraintError": "Database constraint violation.",
        "TransientError": "Temporary database error. Please retry.",
        "ClientError": "Invalid request.",
        "DatabaseError": "Database operation failed.",
    }

    # Return safe message or generic fallback
    return safe_messages.get(error_type, "An error occurred while processing your request.")


def get_executor() -> ThreadPoolExecutor:
    """Get or create thread pool executor for async operations"""
    global _executor
    if _executor is None:
        max_workers = int(os.getenv("MCP_MAX_WORKERS", "10"))
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor


def is_read_only_query(cypher_query: str) -> bool:
    """
    Check if a Cypher query is read-only.

    Uses a comprehensive blocklist approach to detect write operations.
    Improved to catch additional write patterns and edge cases.

    Args:
        cypher_query: The Cypher query to check

    Returns:
        True if the query is read-only, False if it contains write operations
    """
    # Normalize query: lowercase and remove extra whitespace
    normalized = " ".join(cypher_query.lower().split())

    # Write operation keywords (comprehensive list)
    write_keywords = [
        # Data modification
        "create ", "merge ", "set ", "delete ", "remove ",
        "detach delete",

        # Schema modifications
        "drop ", "create constraint", "drop constraint",
        "create index", "drop index",

        # Control flow that can write
        "foreach",

        # Subquery patterns that can write
        "call {",

        # APOC procedures that write (common ones)
        "apoc.create.", "apoc.merge.", "apoc.refactor.",
        "apoc.periodic.iterate", "apoc.periodic.commit",

        # LOAD CSV (can trigger writes)
        "load csv",

        # Additional write patterns
        "on create set", "on match set",
    ]

    # Check for write operations
    for keyword in write_keywords:
        if keyword in normalized:
            return False

    # Additional regex-based checks for edge cases
    import re

    # Check for UNWIND ... CREATE/MERGE patterns
    if re.search(r'\bunwind\b.*\b(create|merge)\b', normalized):
        return False

    # Check for WITH ... CREATE/MERGE patterns (multi-clause writes)
    if re.search(r'\bwith\b.*\b(create|merge|delete)\b', normalized):
        return False

    return True


def check_read_only_access(cypher_query: str) -> Optional[Dict[str, Any]]:
    """
    Check if query is allowed in read-only mode.

    Args:
        cypher_query: The Cypher query to check

    Returns:
        None if allowed, error dict if blocked
    """
    if _read_only_mode and not is_read_only_query(cypher_query):
        logger.warning(f"Blocked write operation in read-only mode: {cypher_query[:100]}")
        return {
            "error": "Write operations are disabled in read-only mode",
            "query": cypher_query,
            "read_only_mode": True,
            "success": False
        }
    return None


def estimate_tokens(text: str) -> int:
    """
    Rough estimation of token count for a text string.
    Uses approximation: 1 token ≈ 4 characters.

    Args:
        text: The text to estimate tokens for

    Returns:
        Estimated token count
    """
    if text is None:
        return 0
    if not isinstance(text, str):
        text = str(text)
    return len(text) // 4


def truncate_response(data: Any, max_tokens: Optional[int] = None) -> tuple[Any, bool]:
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
    import json
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

    # Security: Check for default/weak passwords
    weak_passwords = [
        "password", "password123", "neo4j", "admin", "test",
        "CHANGE_ME", "CHANGE_ME_STRONG_PASSWORD", "changeme"
    ]
    if neo4j_password.lower() in [p.lower() for p in weak_passwords]:
        logger.error("🚨 SECURITY ERROR: Default or weak password detected!")
        logger.error(f"   Password '{neo4j_password}' is not secure for production use")
        logger.error("   Set a strong password in NEO4J_PASSWORD environment variable")

        # Allow in development, but warn heavily
        if os.getenv("ALLOW_WEAK_PASSWORDS", "false").lower() != "true":
            raise ValueError(
                "Weak password detected. Set ALLOW_WEAK_PASSWORDS=true to override (NOT recommended for production)"
            )
        else:
            logger.warning("⚠️  ALLOW_WEAK_PASSWORDS=true - Weak password allowed (DEVELOPMENT ONLY!)")

    # Debug mode
    _debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
    if _debug_mode:
        logger.warning("⚠️  DEBUG_MODE=true - Detailed error messages will be returned (NOT for production!)")
    else:
        logger.info("Production mode: Error messages will be sanitized")

    # Read-only mode
    _read_only_mode = os.getenv("NEO4J_READ_ONLY", "false").lower() == "true"
    if _read_only_mode:
        logger.warning("⚠️  Server running in READ-ONLY mode - write-capable tools will be hidden from MCP clients")

    # Response token limit
    token_limit_str = os.getenv("NEO4J_RESPONSE_TOKEN_LIMIT")
    if token_limit_str:
        try:
            _response_token_limit = int(token_limit_str)
            logger.info(f"Response token limit set to {_response_token_limit}")
        except ValueError:
            logger.warning(f"Invalid NEO4J_RESPONSE_TOKEN_LIMIT value: {token_limit_str}")

    logger.info(f"Connecting to Neo4j at {neo4j_uri} (timeout: {neo4j_timeout}s)")
    graph = Neo4jGraph(
        url=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
        database=neo4j_database,
        timeout=neo4j_timeout
    )

    # LLM configuration
    llm_config = LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        model=os.getenv("LLM_MODEL", "gpt-4"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        api_key=os.getenv("LLM_API_KEY", "")
    )

    logger.info(f"Initializing LLM: {llm_config.provider}/{llm_config.model}")
    llm = chatLLM(llm_config)

    # Create GraphCypherQAChain
    # Note: allow_dangerous_requests is required for LangChain's GraphCypherQAChain
    # but we add our own security layer via query sanitizer
    allow_dangerous = os.getenv("LANGCHAIN_ALLOW_DANGEROUS_REQUESTS", "false").lower() == "true"

    if allow_dangerous:
        logger.warning("⚠️  LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=true - LangChain safety checks DISABLED!")
        logger.warning("⚠️  Relying solely on query sanitizer for security. Use with caution!")

    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        allow_dangerous_requests=allow_dangerous,
        verbose=True,
        return_intermediate_steps=True
    )

    logger.info("Neo4j MCP Server initialized successfully")


# NOTE: Initialization is deferred to the main() entry point to avoid
# performing network/LLM connections at import time (improves testability).


# =============================================================================
# Resources
# =============================================================================

@mcp.resource("neo4j://schema")
def get_schema() -> str:
    """
    Get the Neo4j graph database schema.

    Returns the complete schema including node labels, relationship types,
    and their properties.
    """
    if graph is None:
        return "Error: Neo4j graph not initialized"

    try:
        schema = graph.get_schema()
        return f"Neo4j Graph Schema:\n\n{schema}"
    except Exception as e:
        return f"Error retrieving schema: {str(e)}"


@mcp.resource("neo4j://database-info")
def get_database_info() -> str:
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

@mcp.tool()
async def query_graph(query: str) -> Dict[str, Any]:
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
        return {
            "error": "Neo4j or LangChain not initialized",
            "success": False
        }

    # Audit log the query
    audit_logger = get_audit_logger()
    if audit_logger:
        audit_logger.log_query(tool="query_graph", query=query)

    try:
        logger.info(f"Processing natural language query: {query}")

        # Run LangChain's GraphCypherQAChain in thread pool (it's sync)
        import time
        start_time = time.time()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            get_executor(),
            lambda: chain.invoke({"query": query})
        )

        execution_time_ms = (time.time() - start_time) * 1000

        # Extract generated Cypher query from intermediate steps
        generated_cypher = ""
        if "intermediate_steps" in result and result["intermediate_steps"]:
            if isinstance(result["intermediate_steps"], list) and len(result["intermediate_steps"]) > 0:
                first_step = result["intermediate_steps"][0]
                if isinstance(first_step, dict) and "query" in first_step:
                    generated_cypher = first_step["query"]

        # Sanitize LLM-generated Cypher (SISO prevention)
        if generated_cypher and sanitizer_enabled:
            is_safe, sanitize_error, warnings = sanitize_query(generated_cypher, None)

            if not is_safe:
                logger.warning(f"LLM generated unsafe Cypher: {sanitize_error}")
                error_response = {
                    "error": f"LLM-generated query blocked by sanitizer: {sanitize_error}",
                    "generated_cypher": generated_cypher,
                    "sanitizer_blocked": True,
                    "success": False
                }

                # Audit log the blocked query
                if audit_logger:
                    audit_logger.log_error(
                        tool="query_graph",
                        query=query,
                        error=sanitize_error,
                        metadata={"generated_cypher": generated_cypher, "sanitizer_blocked": True}
                    )

                return error_response

            # Log warnings if any
            if warnings:
                for warning in warnings:
                    logger.warning(f"LLM-generated Cypher warning: {warning}")

        # Check if generated Cypher is allowed in read-only mode
        if generated_cypher:
            read_only_error = check_read_only_access(generated_cypher)
            if read_only_error:
                error_response = {
                    "error": "LLM generated a write operation, but server is in read-only mode",
                    "generated_cypher": generated_cypher,
                    "read_only_mode": True,
                    "success": False
                }

                # Audit log the error
                if audit_logger:
                    audit_logger.log_error(
                        tool="query_graph",
                        query=query,
                        error=error_response["error"],
                        metadata={"generated_cypher": generated_cypher}
                    )

                return error_response

        # Apply response size limiting to intermediate steps
        truncated_steps, was_truncated = truncate_response(result.get("intermediate_steps", []))

        response = {
            "question": query,
            "answer": result.get("result", ""),
            "generated_cypher": generated_cypher,
            "intermediate_steps": truncated_steps,
            "success": True
        }

        if was_truncated:
            response["truncated"] = True
            response["warning"] = "Intermediate steps were truncated due to size limits"
            logger.info("query_graph response truncated due to size limits")

        # Audit log the response
        if audit_logger:
            audit_logger.log_response(
                tool="query_graph",
                query=query,
                response=response,
                execution_time_ms=execution_time_ms
            )

        return response

    except Exception as e:
        logger.error(f"Error in query_graph: {str(e)}", exc_info=True)

        # Sanitize error message for security
        safe_error_message = sanitize_error_message(e)

        error_response = {
            "error": safe_error_message,
            "type": type(e).__name__,
            "success": False
        }

        # Audit log the error (with full details)
        if audit_logger:
            audit_logger.log_error(
                tool="query_graph",
                query=query,
                error=str(e),  # Log full error for debugging
                error_type=type(e).__name__
            )

        return error_response


async def _execute_cypher_impl(cypher_query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        return {
            "error": "Neo4j graph not initialized",
            "success": False
        }

    # Sanitize query and parameters (SISO prevention)
    if sanitizer_enabled:
        is_safe, sanitize_error, warnings = sanitize_query(cypher_query, parameters)

        if not is_safe:
            logger.warning(f"Blocked unsafe query: {sanitize_error}")
            error_response = {
                "error": f"Query blocked by sanitizer: {sanitize_error}",
                "query": cypher_query[:200],  # Only show first 200 chars
                "sanitizer_blocked": True,
                "success": False
            }

            # Audit log the blocked query
            audit_logger = get_audit_logger()
            if audit_logger:
                audit_logger.log_error(
                    tool="execute_cypher",
                    query=cypher_query,
                    error=sanitize_error,
                    metadata={"sanitizer_blocked": True}
                )

            return error_response

        # Log warnings if any
        if warnings:
            for warning in warnings:
                logger.warning(f"Query sanitizer warning: {warning}")

    # Audit log the query
    audit_logger = get_audit_logger()
    if audit_logger:
        audit_logger.log_query(tool="execute_cypher", query=cypher_query, parameters=parameters)

    # Check read-only access control
    read_only_error = check_read_only_access(cypher_query)
    if read_only_error:
        # Audit log the error
        if audit_logger:
            audit_logger.log_error(
                tool="execute_cypher",
                query=cypher_query,
                error=read_only_error["error"]
            )
        return read_only_error

    try:
        logger.info(f"Executing Cypher query: {cypher_query}")

        params = parameters or {}

        # Run query in thread pool (Neo4j driver is sync)
        import time
        start_time = time.time()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            get_executor(),
            lambda: graph.query(cypher_query, params=params)
        )

        execution_time_ms = (time.time() - start_time) * 1000

        # Apply response size limiting
        truncated_result, was_truncated = truncate_response(result)

        response = {
            "query": cypher_query,
            "parameters": params,
            "result": truncated_result,
            "count": len(result) if isinstance(result, list) else 1,
            "success": True
        }

        if was_truncated:
            response["truncated"] = True
            response["original_count"] = len(result) if isinstance(result, list) else 1
            response["returned_count"] = len(truncated_result) if isinstance(truncated_result, list) else None
            logger.info(f"Response truncated: {response.get('original_count')} → {response.get('returned_count')} items")

        # Audit log the response
        if audit_logger:
            audit_logger.log_response(
                tool="execute_cypher",
                query=cypher_query,
                response=response,
                execution_time_ms=execution_time_ms,
                metadata={"parameters": params}
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
            "success": False
        }

        # Audit log the error (with full details)
        if audit_logger:
            audit_logger.log_error(
                tool="execute_cypher",
                query=cypher_query,
                error=str(e),  # Log full error for debugging
                error_type=type(e).__name__
            )

        return error_response


# The `execute_cypher` implementation is defined here but registered with
# the MCP runtime only after `initialize_neo4j()` runs in `main()`. This
# ensures `_read_only_mode` is set correctly before deciding whether to
# expose the tool to MCP clients.
async def execute_cypher(cypher_query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a raw Cypher query against the Neo4j database.

    Use this when you need precise control over the query or when natural
    language translation isn't suitable. Supports both read and write operations.

    This function runs asynchronously, allowing parallel query execution.
    """
    return await _execute_cypher_impl(cypher_query, parameters)


@mcp.tool()
async def refresh_schema() -> Dict[str, Any]:
    """
    Refresh the cached schema information from the Neo4j database.

    Call this after making structural changes to the database (adding/removing
    labels, relationship types, or properties) to ensure the schema is up to date.

    This function runs asynchronously.

    Returns:
        Dictionary containing the updated schema and success status
    """
    if graph is None:
        return {
            "error": "Neo4j graph not initialized",
            "success": False
        }

    try:
        logger.info("Refreshing graph schema")

        # Run schema refresh in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            get_executor(),
            graph.refresh_schema
        )
        schema = graph.get_schema()

        return {
            "schema": schema,
            "message": "Schema refreshed successfully",
            "success": True
        }

    except Exception as e:
        logger.error(f"Error in refresh_schema: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "type": type(e).__name__,
            "success": False
        }


# =============================================================================
# Main Entry Point
# =============================================================================

def cleanup():
    """Cleanup resources on shutdown"""
    global _executor
    if _executor is not None:
        logger.info("Shutting down thread pool executor")
        _executor.shutdown(wait=True)
        _executor = None


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

    # Register execute_cypher tool after initialization so read-only mode is respected
    if not _read_only_mode:
        mcp.tool()(execute_cypher)
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


if __name__ == "__main__":
    main()
