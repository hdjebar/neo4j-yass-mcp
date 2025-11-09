"""
SecureNeo4jGraph - Security wrapper for Neo4jGraph

This module provides a security layer that intercepts ALL queries before execution.
It enforces sanitization, complexity limits, and read-only mode BEFORE the query
reaches the Neo4j driver.

CRITICAL SECURITY FIX:
Previously, GraphCypherQAChain.invoke() would execute queries and THEN we'd check
security constraints. This allowed complete bypass of all security controls.

Now, SecureNeo4jGraph intercepts Neo4jGraph.query() and runs security checks
BEFORE the driver executes anything.
"""

import logging
from typing import Any

from langchain_neo4j import Neo4jGraph

from neo4j_yass_mcp.security import (
    check_query_complexity,
    sanitize_query,
)

logger = logging.getLogger(__name__)


class SecureNeo4jGraph(Neo4jGraph):
    """
    Security wrapper for Neo4jGraph that enforces security policies BEFORE query execution.

    This class intercepts the query() method to:
    1. Sanitize queries for injection attacks and malformed Unicode
    2. Check query complexity to prevent resource exhaustion
    3. Enforce read-only mode by blocking write operations

    All security checks run BEFORE the query reaches the Neo4j driver.
    """

    def __init__(
        self,
        *args,
        sanitizer_enabled: bool = True,
        complexity_limit_enabled: bool = True,
        read_only_mode: bool = False,
        **kwargs,
    ):
        """
        Initialize SecureNeo4jGraph with security policies.

        Args:
            *args: Positional arguments passed to Neo4jGraph
            sanitizer_enabled: Enable query sanitization (injection protection)
            complexity_limit_enabled: Enable complexity limiting (DoS protection)
            read_only_mode: Block all write operations (CREATE, MERGE, DELETE, etc.)
            **kwargs: Keyword arguments passed to Neo4jGraph
        """
        super().__init__(*args, **kwargs)
        self.sanitizer_enabled = sanitizer_enabled
        self.complexity_limit_enabled = complexity_limit_enabled
        self.read_only_mode = read_only_mode

        logger.info("SecureNeo4jGraph initialized:")
        logger.info(f"  - Sanitizer: {'ENABLED' if sanitizer_enabled else 'DISABLED'}")
        logger.info(
            f"  - Complexity limiter: {'ENABLED' if complexity_limit_enabled else 'DISABLED'}"
        )
        logger.info(f"  - Read-only mode: {'ENABLED' if read_only_mode else 'DISABLED'}")

    def query(
        self,
        query: str,
        params: dict[Any, Any] | None = None,
        session_params: dict[Any, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a Cypher query with security checks BEFORE execution.

        Security checks (in order):
        1. Query sanitization - Blocks injections, malformed Unicode, dangerous patterns
        2. Complexity limiting - Prevents resource exhaustion attacks
        3. Read-only enforcement - Blocks write operations if read_only_mode=True

        Args:
            query: Cypher query to execute
            params: Optional query parameters

        Returns:
            Query results from Neo4j

        Raises:
            ValueError: If query violates any security policy
        """
        logger.debug(f"SecureNeo4jGraph.query() called with: {query[:100]}...")

        # SECURITY CHECK 1: Sanitization (injection + Unicode attacks)
        if self.sanitizer_enabled:
            is_safe, sanitize_error, warnings = sanitize_query(query, params)

            if not is_safe:
                error_msg = f"Query blocked by sanitizer: {sanitize_error}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Log warnings (non-blocking)
            if warnings:
                for warning in warnings:
                    logger.warning(f"Query sanitizer warning: {warning}")

        # SECURITY CHECK 2: Complexity limiting (DoS protection)
        if self.complexity_limit_enabled:
            is_allowed, complexity_error, complexity_score = check_query_complexity(query)

            if not is_allowed:
                error_msg = f"Query blocked by complexity limiter: {complexity_error}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Log complexity warnings (non-blocking)
            if complexity_score and complexity_score.warnings:
                for warning in complexity_score.warnings:
                    logger.info(f"Query complexity warning: {warning}")

        # SECURITY CHECK 3: Read-only mode enforcement
        if self.read_only_mode:
            from neo4j_yass_mcp.server import check_read_only_access

            read_only_error = check_read_only_access(query)

            if read_only_error:
                error_msg = f"Query blocked in read-only mode: {read_only_error}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        # ALL SECURITY CHECKS PASSED - Execute query
        logger.debug("All security checks passed, executing query")
        # Call parent with appropriate arguments - pass only what's expected
        if session_params is not None:
            return super().query(query, params or {}, session_params)
        else:
            # If session_params is None, call with only the first two arguments (default in parent)
            return super().query(query, params or {})
