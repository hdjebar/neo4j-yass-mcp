"""
Tests for server complexity limiting enforcement.

Covers complexity limit checking in query_graph and execute_cypher tools.
Tests lines 562-587, 760-785 in server.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from neo4j_yass_mcp.security.complexity_limiter import ComplexityScore


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

        # Setup server state - need to generate Cypher first
        mock_chain = Mock()
        complex_cypher = "MATCH (n)-[r*1..10]->(m) RETURN n, r, m"
        mock_chain.invoke.return_value = {
            "result": "Would execute complex query",
            "intermediate_steps": [{"query": complex_cypher}],
        }

        server.chain = mock_chain
        server.graph = MagicMock()
        original_complexity_enabled = server.complexity_limit_enabled
        server.complexity_limit_enabled = True

        try:
            # Call query_graph
            result = await server.query_graph.fn(query="Show me everything connected")

            # Verify complexity block response
            assert result["success"] is False
            assert result["complexity_blocked"] is True
            assert "LLM-generated query blocked by complexity limiter" in result["error"]
            assert result["complexity_score"] == 150
            assert result["complexity_limit"] == 100
            assert "generated_cypher" in result
            assert result["generated_cypher"] == complex_cypher

            # Verify audit logging
            mock_audit_logger.log_error.assert_called_once()
            call_args = mock_audit_logger.log_error.call_args[1]
            assert call_args["tool"] == "query_graph"
            assert "metadata" in call_args
            assert call_args["metadata"]["complexity_blocked"] is True
            assert call_args["metadata"]["complexity_score"] == 150
            assert call_args["metadata"]["generated_cypher"] == complex_cypher

            # Verify complexity check was called
            mock_check_complexity.assert_called_once_with(complex_cypher)

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
            result = await server.execute_cypher(cypher_query=complex_query)

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
    @patch("neo4j_yass_mcp.server.check_query_complexity")
    async def test_query_graph_complexity_allowed(self, mock_check_complexity):
        """Test query_graph proceeds when complexity is within limits"""
        from neo4j_yass_mcp import server

        # Setup: Complexity allowed
        complexity_score = ComplexityScore(is_within_limit=True, 
            total_score=50,
            max_allowed=100,
            breakdown={"matches": 25, "relationships": 25},
            warnings=[],
        )
        mock_check_complexity.return_value = (True, None, complexity_score)

        # Setup server state
        simple_cypher = "MATCH (n:Person) RETURN n LIMIT 10"
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "result": "Found 10 persons",
            "intermediate_steps": [{"query": simple_cypher}],
        }
        mock_graph = MagicMock()
        mock_session = Mock()
        mock_graph.query = mock_session
        mock_session.return_value = [{"n": {"name": "Alice"}}]

        server.chain = mock_chain
        server.graph = mock_graph
        original_complexity_enabled = server.complexity_limit_enabled
        server.complexity_limit_enabled = True

        try:
            # Call query_graph
            result = await server.query_graph.fn(query="Show me 10 people")

            # Verify it proceeded past complexity check
            assert result["success"] is True
            assert "complexity_blocked" not in result or result.get("complexity_blocked") is False

            # Verify complexity check was called
            mock_check_complexity.assert_called_once_with(simple_cypher)

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
            result = await server.execute_cypher(cypher_query="MATCH (n) RETURN n LIMIT 1")

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
            result = await server.execute_cypher(cypher_query="MATCH (n) RETURN n")

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
