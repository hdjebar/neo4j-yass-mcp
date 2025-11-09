"""
Tests for server rate limiting enforcement.

Covers rate limit checking in query_graph and execute_cypher tools.
Tests lines 478-491, 704-717 in server.py
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from neo4j_yass_mcp.security.rate_limiter import RateLimitInfo


class TestRateLimitEnforcement:
    """Test rate limit enforcement in MCP tools."""

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_rate_limit")
    @patch("neo4j_yass_mcp.server.get_audit_logger")
    async def test_query_graph_rate_limit_exceeded(self, mock_get_audit, mock_check_rate):
        """Lines 478-491: Test query_graph blocks when rate limit exceeded"""
        from neo4j_yass_mcp import server

        # Setup: Rate limit exceeded
        rate_info = RateLimitInfo(
            allowed=False,
            requests_remaining=0,
            reset_time=datetime.now() + timedelta(seconds=60),
            retry_after_seconds=60.0,
        )
        mock_check_rate.return_value = (False, rate_info)

        # Setup audit logger mock
        mock_audit_logger = MagicMock()
        mock_get_audit.return_value = mock_audit_logger

        # Setup server state
        server.chain = MagicMock()  # Ensure chain is initialized
        server.graph = MagicMock()  # Ensure graph is initialized
        original_rate_limit_enabled = server.rate_limit_enabled
        server.rate_limit_enabled = True

        try:
            # Call query_graph
            result = await server.query_graph.fn(query="MATCH (n) RETURN n")

            # Verify rate limit error response
            assert result["success"] is False
            assert result["rate_limited"] is True
            assert "Rate limit exceeded" in result["error"]
            assert result["retry_after_seconds"] == 60.0
            assert "reset_time" in result
            assert isinstance(result["reset_time"], str)  # ISO format

            # Verify audit logging
            mock_audit_logger.log_error.assert_called_once()
            call_args = mock_audit_logger.log_error.call_args[1]
            assert call_args["tool"] == "query_graph"
            assert call_args["error_type"] == "rate_limit"
            assert "Rate limit exceeded" in call_args["error"]

            # Verify rate limit check was called with unique client ID
            mock_check_rate.assert_called_once()
            call_kwargs = mock_check_rate.call_args[1]
            assert "client_id" in call_kwargs
            # Client ID should be unique (client_{counter}_{task_id})
            assert call_kwargs["client_id"].startswith("client_")

        finally:
            # Restore original state
            server.rate_limit_enabled = original_rate_limit_enabled

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_rate_limit")
    @patch("neo4j_yass_mcp.server.get_audit_logger")
    async def test_execute_cypher_rate_limit_exceeded(self, mock_get_audit, mock_check_rate):
        """Lines 704-717: Test execute_cypher blocks when rate limit exceeded"""
        from neo4j_yass_mcp import server

        # Setup: Rate limit exceeded
        rate_info = RateLimitInfo(
            allowed=False,
            requests_remaining=0,
            reset_time=datetime.now() + timedelta(seconds=45),
            retry_after_seconds=45.0,
        )
        mock_check_rate.return_value = (False, rate_info)

        # Setup audit logger mock
        mock_audit_logger = MagicMock()
        mock_get_audit.return_value = mock_audit_logger

        # Setup server state
        server.graph = MagicMock()  # Ensure graph is initialized
        original_rate_limit_enabled = server.rate_limit_enabled
        server.rate_limit_enabled = True

        try:
            # Call execute_cypher
            result = await server.execute_cypher(cypher_query="MATCH (n) RETURN n LIMIT 1")

            # Verify rate limit error response
            assert result["success"] is False
            assert result["rate_limited"] is True
            assert "Rate limit exceeded" in result["error"]
            assert result["retry_after_seconds"] == 45.0
            assert "reset_time" in result
            assert isinstance(result["reset_time"], str)  # ISO format

            # Verify audit logging
            mock_audit_logger.log_error.assert_called_once()
            call_args = mock_audit_logger.log_error.call_args[1]
            assert call_args["tool"] == "execute_cypher"
            assert call_args["error_type"] == "rate_limit"
            assert "Rate limit exceeded" in call_args["error"]

            # Verify rate limit check was called with unique client ID
            mock_check_rate.assert_called_once()
            call_kwargs = mock_check_rate.call_args[1]
            assert "client_id" in call_kwargs
            # Client ID should be unique (client_{counter}_{task_id})
            assert call_kwargs["client_id"].startswith("client_")

        finally:
            # Restore original state
            server.rate_limit_enabled = original_rate_limit_enabled

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_rate_limit")
    async def test_query_graph_rate_limit_allowed(self, mock_check_rate):
        """Test query_graph proceeds when rate limit not exceeded"""
        from neo4j_yass_mcp import server

        # Setup: Rate limit allowed
        rate_info = RateLimitInfo(
            allowed=True,
            requests_remaining=10,
            reset_time=datetime.now() + timedelta(seconds=60),
            retry_after_seconds=None,
        )
        mock_check_rate.return_value = (True, rate_info)

        # Setup server state with full mocks
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "result": "Query executed",
            "intermediate_steps": [{"query": "MATCH (n) RETURN n"}],
        }
        server.chain = mock_chain
        server.graph = MagicMock()
        original_rate_limit_enabled = server.rate_limit_enabled
        server.rate_limit_enabled = True

        try:
            # Call query_graph
            result = await server.query_graph.fn(query="Show me all nodes")

            # Verify it proceeded past rate limiting
            assert result["success"] is True
            assert "rate_limited" not in result or result.get("rate_limited") is False

            # Verify rate limit check was called with unique client ID
            mock_check_rate.assert_called_once()
            call_kwargs = mock_check_rate.call_args[1]
            assert "client_id" in call_kwargs
            # Client ID should be unique (client_{counter}_{task_id})
            assert call_kwargs["client_id"].startswith("client_")

        finally:
            # Restore original state
            server.rate_limit_enabled = original_rate_limit_enabled

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_rate_limit")
    async def test_rate_limit_disabled_skips_check(self, mock_check_rate):
        """Test that rate limit check is skipped when disabled"""
        from neo4j_yass_mcp import server

        # Setup server state
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "result": "Query executed",
            "intermediate_steps": [{"query": "MATCH (n) RETURN n"}],
        }
        server.chain = mock_chain
        server.graph = MagicMock()
        original_rate_limit_enabled = server.rate_limit_enabled
        server.rate_limit_enabled = False

        try:
            # Call query_graph
            result = await server.query_graph.fn(query="Show me all nodes")

            # Verify rate limit check was NOT called
            mock_check_rate.assert_not_called()

            # Verify query proceeded
            assert result["success"] is True

        finally:
            # Restore original state
            server.rate_limit_enabled = original_rate_limit_enabled

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_rate_limit")
    async def test_sequential_requests_get_different_client_ids(self, mock_check_rate):
        """Test that sequential requests in same task get DIFFERENT client IDs (per-request rate limiting)"""
        from neo4j_yass_mcp import server

        # Setup: Always allow requests
        rate_info = RateLimitInfo(
            allowed=True,
            requests_remaining=10,
            reset_time=datetime.now() + timedelta(seconds=60),
            retry_after_seconds=None,
        )
        mock_check_rate.return_value = (True, rate_info)

        # Setup server state
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "result": "Query executed",
            "intermediate_steps": [{"query": "MATCH (n) RETURN n"}],
        }
        server.chain = mock_chain
        server.graph = MagicMock()
        original_rate_limit_enabled = server.rate_limit_enabled
        server.rate_limit_enabled = True

        try:
            # Make 3 sequential requests
            await server.query_graph.fn(query="Request 1")
            await server.query_graph.fn(query="Request 2")
            await server.query_graph.fn(query="Request 3")

            # Verify check_rate_limit was called 3 times
            assert mock_check_rate.call_count == 3

            # Extract all client_ids from the calls
            client_ids = [
                call_kwargs["client_id"]
                for call_args, call_kwargs in mock_check_rate.call_args_list
            ]

            # CRITICAL ASSERTION: All client IDs must be different (per-request limiting)
            assert len(set(client_ids)) == 3, (
                f"Expected 3 different client IDs for 3 requests, "
                f"but got: {client_ids}. "
                "This means rate limiting is still per-session, not per-request!"
            )

            # Verify all IDs follow the expected format
            for client_id in client_ids:
                assert client_id.startswith("client_")

        finally:
            # Restore original state
            server.rate_limit_enabled = original_rate_limit_enabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
