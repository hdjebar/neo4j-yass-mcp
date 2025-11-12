"""
MCP Tool Handlers.

Implements the core MCP tools for Neo4j query execution and analysis.

Phase 3.4: Extracted from server.py for better code organization.
"""

import asyncio
import logging
import time
from typing import Any

from fastmcp import Context

from neo4j_yass_mcp.security import (
    check_query_complexity,
    get_audit_logger,
    sanitize_query,
)

logger = logging.getLogger(__name__)


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
    # Lazy imports to avoid circular dependencies
    from neo4j_yass_mcp.server import (
        _get_chain,
        _get_graph,
        sanitize_error_message,
        truncate_response,
    )

    # Phase 3.3: Use state accessor functions for bootstrap support
    current_chain = _get_chain()
    current_graph = _get_graph()

    if current_chain is None or current_graph is None:
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
        result = await asyncio.to_thread(current_chain.invoke, {"query": query})

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
        # Phase 4: ValueError raised by AsyncSecureNeo4jGraph when security checks fail
        # Use warning (not error) since these are expected security violations, not system errors
        logger.warning(f"🔒 Security check blocked query in query_graph: {str(e)}")

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
        # Phase 4: Unexpected errors (LLM, database, or chain errors)
        logger.error(f"❌ Unexpected error in query_graph: {str(e)}", exc_info=True)

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
    # Lazy imports to avoid circular dependencies
    from neo4j_yass_mcp.server import (
        _get_config,
        _get_graph,
        check_read_only_access,
        sanitize_error_message,
        truncate_response,
    )

    # Phase 3.3: Use state accessor functions for bootstrap support
    current_graph = _get_graph()
    current_config = _get_config()

    if current_graph is None:
        return {"error": "Neo4j graph not initialized", "success": False}

    # Audit log the query
    audit_logger = get_audit_logger()
    if audit_logger:
        audit_logger.log_query(tool="execute_cypher", query=cypher_query, parameters=parameters)

    try:
        logger.info(f"Executing Cypher query: {cypher_query}")

        params = parameters or {}

        # Phase 4: Native async query execution (no asyncio.to_thread)
        # Security checks (sanitization, complexity, read-only) now handled by AsyncSecureNeo4jGraph
        start_time = time.time()

        # ✅ NATIVE ASYNC - NO asyncio.to_thread!
        result = await current_graph.query(cypher_query, params=params)

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

    except ValueError as e:
        # Phase 4: ValueError raised by AsyncSecureNeo4jGraph when security checks fail
        # Use warning (not error) since these are expected security violations, not system errors
        logger.warning(f"🔒 Security check blocked query in execute_cypher: {str(e)}")

        error_response = {
            "error": str(e),
            "error_type": "SecurityError",
            "query": cypher_query[:100] + "..." if len(cypher_query) > 100 else cypher_query,
            "success": False,
        }

        # Audit log the security violation
        if audit_logger:
            audit_logger.log_error(
                tool="execute_cypher",
                query=cypher_query,
                error=str(e),
                metadata={"security_blocked": True},
            )

        return error_response

    except Exception as e:
        # Phase 4: Unexpected errors (system/database errors)
        logger.error(f"❌ Unexpected error in execute_cypher: {str(e)}", exc_info=True)

        # Sanitize error message for security
        safe_error_message = sanitize_error_message(e)

        error_response = {
            "error": safe_error_message,
            "error_type": type(e).__name__,
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
    # Lazy imports to avoid circular dependencies
    from neo4j_yass_mcp.server import _get_graph

    # Phase 3.3: Use state accessor function for bootstrap support
    current_graph = _get_graph()

    if current_graph is None:
        return {"error": "Neo4j graph not initialized", "success": False}

    try:
        logger.info("Refreshing graph schema")

        # Phase 4: Native async schema refresh (no asyncio.to_thread)
        # ✅ NATIVE ASYNC - NO asyncio.to_thread!
        await current_graph.refresh_schema()
        schema = current_graph.get_schema

        return {"schema": schema, "message": "Schema refreshed successfully", "success": True}

    except Exception as e:
        # Phase 4: Unexpected errors (database connection, driver errors)
        logger.error(f"❌ Unexpected error in refresh_schema: {str(e)}", exc_info=True)
        return {"error": str(e), "error_type": type(e).__name__, "success": False}


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
    # Lazy imports to avoid circular dependencies
    from neo4j_yass_mcp.server import _get_graph, sanitize_error_message

    # Phase 3.3: Use state accessor function for bootstrap support
    current_graph = _get_graph()

    if current_graph is None:
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
        analyzer = QueryPlanAnalyzer(current_graph)

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
        # Phase 4: ValueError from validation or security checks
        # Could be security violations OR analysis failures (invalid mode, etc.)
        if "blocked" in str(e).lower():
            # Security violation from AsyncSecureNeo4jGraph
            logger.warning(f"🔒 Security check blocked query in analyze_query_performance: {str(e)}")
        else:
            # Analysis-specific validation error (e.g., invalid mode)
            logger.warning(f"⚠️  Query analysis validation failed: {str(e)}")

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
        # Phase 4: Unexpected errors (system/analysis errors)
        logger.error(f"❌ Unexpected error in analyze_query_performance: {str(e)}", exc_info=True)

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
