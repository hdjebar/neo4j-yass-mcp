"""
Tests for server error audit logging.

Covers audit logging in exception handlers for query_graph and execute_cypher.
Tests lines 653, 868 in server.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch


class TestErrorAuditLogging:
    """Test audit logging for errors in MCP tools."""

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.get_audit_logger")
    async def test_query_graph_error_audit_logging(self, mock_get_audit):
        """Line 653: Test query_graph logs errors to audit logger"""
        from neo4j_yass_mcp import server

        # Setup audit logger mock
        mock_audit_logger = MagicMock()
        mock_get_audit.return_value = mock_audit_logger

        # Setup server state to cause an exception
        mock_chain = Mock()
        mock_chain.invoke.side_effect = ValueError("Database connection failed")

        server.chain = mock_chain
        server.graph = MagicMock()

        # Call query_graph (should catch exception)
        result = await server.query_graph.fn(query="MATCH (n) RETURN n")

        # Verify error response
        assert result["success"] is False
        assert "error" in result
        assert result["type"] == "ValueError"

        # Verify audit logging was called
        mock_audit_logger.log_error.assert_called_once()
        call_args = mock_audit_logger.log_error.call_args[1]

        assert call_args["tool"] == "query_graph"
        assert call_args["query"] == "MATCH (n) RETURN n"
        assert "Database connection failed" in call_args["error"]
        assert call_args["error_type"] == "ValueError"

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.get_audit_logger")
    async def test_execute_cypher_error_audit_logging(self, mock_get_audit):
        """Line 868: Test execute_cypher logs errors to audit logger"""
        from neo4j_yass_mcp import server

        # Setup audit logger mock
        mock_audit_logger = MagicMock()
        mock_get_audit.return_value = mock_audit_logger

        # Setup server state to cause an exception
        mock_graph = MagicMock()
        mock_session = Mock()
        mock_graph.query = mock_session
        mock_session.side_effect = RuntimeError("Cypher syntax error")

        server.graph = mock_graph

        # Call execute_cypher (should catch exception)
        cypher_query = "INVALID CYPHER QUERY"
        result = await server.execute_cypher(cypher_query=cypher_query)

        # Verify error response
        assert result["success"] is False
        assert "error" in result
        assert result["type"] == "RuntimeError"
        assert "query" in result

        # Verify audit logging was called
        mock_audit_logger.log_error.assert_called_once()
        call_args = mock_audit_logger.log_error.call_args[1]

        assert call_args["tool"] == "execute_cypher"
        assert call_args["query"] == cypher_query
        assert "Cypher syntax error" in call_args["error"]
        assert call_args["error_type"] == "RuntimeError"

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.get_audit_logger")
    async def test_query_graph_no_audit_logger(self, mock_get_audit):
        """Test query_graph handles missing audit logger gracefully"""
        from neo4j_yass_mcp import server

        # Setup: No audit logger available
        mock_get_audit.return_value = None

        # Setup server state to cause an exception
        mock_chain = Mock()
        mock_chain.invoke.side_effect = Exception("Test error")

        server.chain = mock_chain
        server.graph = MagicMock()

        # Call query_graph (should not crash without audit logger)
        result = await server.query_graph.fn(query="test query")

        # Verify error response (should still work)
        assert result["success"] is False
        assert "error" in result

        # Verify get_audit_logger was called but no logging occurred
        mock_get_audit.assert_called_once()

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.get_audit_logger")
    async def test_execute_cypher_no_audit_logger(self, mock_get_audit):
        """Test execute_cypher handles missing audit logger gracefully"""
        from neo4j_yass_mcp import server

        # Setup: No audit logger available
        mock_get_audit.return_value = None

        # Setup server state to cause an exception
        mock_graph = MagicMock()
        mock_session = Mock()
        mock_graph.query = mock_session
        mock_session.side_effect = Exception("Test error")

        server.graph = mock_graph

        # Call execute_cypher (should not crash without audit logger)
        result = await server.execute_cypher(cypher_query="test query")

        # Verify error response (should still work)
        assert result["success"] is False
        assert "error" in result

        # Verify get_audit_logger was called but no logging occurred
        mock_get_audit.assert_called_once()

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.get_audit_logger")
    async def test_audit_logging_with_complex_exception(self, mock_get_audit):
        """Test audit logging captures complex exception details"""
        from neo4j_yass_mcp import server

        # Setup audit logger mock
        mock_audit_logger = MagicMock()
        mock_get_audit.return_value = mock_audit_logger

        # Setup server state with nested exception
        mock_chain = Mock()
        inner_exception = ConnectionError("Network timeout")
        outer_exception = RuntimeError("Query failed")
        outer_exception.__cause__ = inner_exception
        mock_chain.invoke.side_effect = outer_exception

        server.chain = mock_chain
        server.graph = MagicMock()

        # Call query_graph
        result = await server.query_graph.fn(query="complex query")

        # Verify error response
        assert result["success"] is False
        assert result["type"] == "RuntimeError"

        # Verify audit logging captured full error
        mock_audit_logger.log_error.assert_called_once()
        call_args = mock_audit_logger.log_error.call_args[1]
        assert "Query failed" in call_args["error"]
        assert call_args["error_type"] == "RuntimeError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
