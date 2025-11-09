"""
Tests for server complexity limiting enforcement.

Covers complexity limit checking in query_graph and execute_cypher tools.
Tests lines 562-587, 760-785 in server.py
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastmcp import Context

from neo4j_yass_mcp.security.complexity_limiter import ComplexityScore


def create_mock_context(session_id: str = "test_session_123") -> Mock:
    """Create a mock FastMCP Context for testing."""
    mock_ctx = Mock(spec=Context)
    mock_ctx.session_id = session_id
    mock_ctx.client_id = None
    return mock_ctx


class TestComplexityLimitEnforcement:
    """Test complexity limit enforcement in MCP tools."""

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_query_complexity")
    @patch("neo4j_yass_mcp.server.get_audit_logger")
    async def test_query_graph_complexity_exceeded_llm_generated(
        self, mock_get_audit, mock_check_complexity
    ):
        """Lines 562-587: Test query_graph blocks LLM-generated complex queries"""
        from neo4j_yass_mcp import server

        # Setup: Complexity exceeded
        complexity_score = ComplexityScore(is_within_limit=False,
            total_score=150,
            max_allowed=100,
            breakdown={"matches": 50, "relationships": 100},
            warnings=["Query too complex"],
        )
        mock_check_complexity.return_value = (
            False,
            "Query complexity 150 exceeds limit of 100",
            complexity_score,
        )

        # Setup audit logger mock
        mock_audit_logger = MagicMock()
        mock_get_audit.return_value = mock_audit_logger

        # Setup server state - SecureNeo4jGraph now raises ValueError when complexity exceeded
        mock_chain = Mock()
        # Chain will raise ValueError (what SecureNeo4jGraph does on complexity failure)
        mock_chain.invoke.side_effect = ValueError(
            "Query blocked by complexity limiter: Query complexity 150 exceeds limit of 100"
        )

        server.chain = mock_chain
        server.graph = MagicMock()
        original_complexity_enabled = server.complexity_limit_enabled
        server.complexity_limit_enabled = True

        try:
            # Call query_graph
            result = await server.query_graph.fn(query="Show me everything connected", ctx=create_mock_context())

            # Verify complexity block response
            assert result["success"] is False
            assert result["security_blocked"] is True
            assert "complexity" in result["block_type"]
            assert "complexity limiter" in result["error"].lower()

            # Verify audit logging
            mock_audit_logger.log_error.assert_called_once()
            call_args = mock_audit_logger.log_error.call_args[1]
            assert call_args["tool"] == "query_graph"
            assert call_args["error_type"] == "complexity_blocked"

        finally:
            # Restore original state
            server.complexity_limit_enabled = original_complexity_enabled

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_query_complexity")
    @patch("neo4j_yass_mcp.server.get_audit_logger")
    async def test_execute_cypher_complexity_exceeded(
        self, mock_get_audit, mock_check_complexity
    ):
        """Lines 760-785: Test execute_cypher blocks complex queries"""
        from neo4j_yass_mcp import server

        # Setup: Complexity exceeded
        complexity_score = ComplexityScore(is_within_limit=False,
            total_score=200,
            max_allowed=100,
            breakdown={"variable_length_paths": 150, "cartesian_products": 50},
            warnings=["Variable-length path without LIMIT"],
        )
        mock_check_complexity.return_value = (
            False,
            "Query has variable-length path without LIMIT",
            complexity_score,
        )

        # Setup audit logger mock
        mock_audit_logger = MagicMock()
        mock_get_audit.return_value = mock_audit_logger

        # Setup server state
        server.graph = MagicMock()
        original_complexity_enabled = server.complexity_limit_enabled
        server.complexity_limit_enabled = True

        try:
            # Call execute_cypher with complex query
            complex_query = "MATCH (n)-[r*1..20]->(m) RETURN n, r, m"
            result = await server.execute_cypher.fn(cypher_query=complex_query, ctx=create_mock_context())

            # Verify complexity block response
            assert result["success"] is False
            assert result["complexity_blocked"] is True
            assert "Query blocked by complexity limiter" in result["error"]
            assert result["complexity_score"] == 200
            assert result["complexity_limit"] == 100
            assert "query" in result
            assert complex_query[:50] in result["query"]

            # Verify audit logging
            mock_audit_logger.log_error.assert_called_once()
            call_args = mock_audit_logger.log_error.call_args[1]
            assert call_args["tool"] == "execute_cypher"
            assert "metadata" in call_args
            assert call_args["metadata"]["complexity_blocked"] is True
            assert call_args["metadata"]["complexity_score"] == 200

            # Verify complexity check was called
            mock_check_complexity.assert_called_once_with(complex_query)

        finally:
            # Restore original state
            server.complexity_limit_enabled = original_complexity_enabled

    @pytest.mark.asyncio
    async def test_query_graph_complexity_allowed(self):
        """Test query_graph proceeds when complexity is within limits.

        With SecureNeo4jGraph, complexity checks happen automatically.
        This test verifies that simple queries (within limits) succeed.
        """
        from neo4j_yass_mcp import server

        # Setup server state - simple query that should pass complexity check
        simple_cypher = "MATCH (n:Person) RETURN n LIMIT 10"
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "result": "Found 10 persons",
            "intermediate_steps": [{"query": simple_cypher}],
        }
        mock_graph = MagicMock()

        server.chain = mock_chain
        server.graph = mock_graph
        original_complexity_enabled = server.complexity_limit_enabled
        server.complexity_limit_enabled = True

        try:
            # Call query_graph
            result = await server.query_graph.fn(query="Show me 10 people", ctx=create_mock_context())

            # Verify it proceeded past complexity check
            assert result["success"] is True
            assert "security_blocked" not in result or result.get("security_blocked") is False

        finally:
            # Restore original state
            server.complexity_limit_enabled = original_complexity_enabled

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_query_complexity")
    async def test_complexity_limit_disabled_skips_check(self, mock_check_complexity):
        """Test that complexity check is skipped when disabled"""
        from neo4j_yass_mcp import server

        # Setup server state
        server.graph = MagicMock()
        mock_session = Mock()
        server.graph.query = mock_session
        mock_session.return_value = [{"n": 1}]

        original_complexity_enabled = server.complexity_limit_enabled
        server.complexity_limit_enabled = False

        try:
            # Call execute_cypher
            result = await server.execute_cypher.fn(cypher_query="MATCH (n) RETURN n LIMIT 1", ctx=create_mock_context())

            # Verify complexity check was NOT called
            mock_check_complexity.assert_not_called()

            # Verify query proceeded
            assert result["success"] is True

        finally:
            # Restore original state
            server.complexity_limit_enabled = original_complexity_enabled

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_query_complexity")
    async def test_complexity_score_none_handling(self, mock_check_complexity):
        """Test handling when complexity_score is None"""
        from neo4j_yass_mcp import server

        # Setup: Complexity check fails but no score
        mock_check_complexity.return_value = (False, "Unknown complexity error", None)

        # Setup server state
        server.graph = MagicMock()
        original_complexity_enabled = server.complexity_limit_enabled
        server.complexity_limit_enabled = True

        try:
            # Call execute_cypher
            result = await server.execute_cypher.fn(cypher_query="MATCH (n) RETURN n", ctx=create_mock_context())

            # Verify error response handles None score
            assert result["success"] is False
            assert result["complexity_blocked"] is True
            assert result["complexity_score"] is None
            assert result["complexity_limit"] is None

        finally:
            # Restore original state
            server.complexity_limit_enabled = original_complexity_enabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
