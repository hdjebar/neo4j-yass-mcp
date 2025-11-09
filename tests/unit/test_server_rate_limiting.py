"""
Tests for server rate limiting enforcement.

Covers rate limit checking in query_graph and execute_cypher tools.
Tests lines 478-491, 704-717 in server.py
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from fastmcp import Context
from neo4j_yass_mcp.security.rate_limiter import RateLimitInfo


def create_mock_context(session_id: str = "test_session_123") -> Mock:
    """Create a mock FastMCP Context for testing."""
    mock_ctx = Mock(spec=Context)
    mock_ctx.session_id = session_id
    mock_ctx.client_id = None
    return mock_ctx


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
            # Call query_graph with mock context
            mock_ctx = create_mock_context()
            result = await server.query_graph.fn(query="MATCH (n) RETURN n", ctx=mock_ctx)

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
            # Client ID should be stable session ID (session_{task_id})
            assert call_kwargs["client_id"].startswith("session_")

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
            # Call execute_cypher with mock context
            mock_ctx = create_mock_context()
            result = await server.execute_cypher(cypher_query="MATCH (n) RETURN n LIMIT 1", ctx=mock_ctx)

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
            # Client ID should be stable session ID (session_{task_id})
            assert call_kwargs["client_id"].startswith("session_")

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
            # Call query_graph with mock context
            mock_ctx = create_mock_context()
            result = await server.query_graph.fn(query="Show me all nodes", ctx=mock_ctx)

            # Verify it proceeded past rate limiting
            assert result["success"] is True
            assert "rate_limited" not in result or result.get("rate_limited") is False

            # Verify rate limit check was called with unique client ID
            mock_check_rate.assert_called_once()
            call_kwargs = mock_check_rate.call_args[1]
            assert "client_id" in call_kwargs
            # Client ID should be stable session ID (session_{task_id})
            assert call_kwargs["client_id"].startswith("session_")

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
            # Call query_graph with mock context
            mock_ctx = create_mock_context()
            result = await server.query_graph.fn(query="Show me all nodes", ctx=mock_ctx)

            # Verify rate limit check was NOT called
            mock_check_rate.assert_not_called()

            # Verify query proceeded
            assert result["success"] is True

        finally:
            # Restore original state
            server.rate_limit_enabled = original_rate_limit_enabled

    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.server.check_rate_limit")
    async def test_sequential_requests_share_same_client_id(self, mock_check_rate):
        """Test that sequential requests in same session share SAME client ID (per-session rate limiting)"""
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
            # Make 3 sequential requests in the same session with same context
            mock_ctx = create_mock_context()
            await server.query_graph.fn(query="Request 1", ctx=mock_ctx)
            await server.query_graph.fn(query="Request 2", ctx=mock_ctx)
            await server.query_graph.fn(query="Request 3", ctx=mock_ctx)

            # Verify check_rate_limit was called 3 times
            assert mock_check_rate.call_count == 3

            # Extract all client_ids from the calls
            client_ids = [
                call_kwargs["client_id"]
                for call_args, call_kwargs in mock_check_rate.call_args_list
            ]

            # CRITICAL ASSERTION: All client IDs must be SAME (per-session limiting)
            # This ensures rate limiting is enforced across multiple requests from same session
            assert len(set(client_ids)) == 1, (
                f"Expected same client ID for all 3 requests in same session, "
                f"but got different IDs: {client_ids}. "
                "This means rate limiting would not work - each request gets fresh bucket!"
            )

            # Verify ID follows the expected format (session_<task_id>)
            client_id = client_ids[0]
            assert client_id.startswith("session_"), f"Expected 'session_' prefix, got: {client_id}"

        finally:
            # Restore original state
            server.rate_limit_enabled = original_rate_limit_enabled


    @pytest.mark.asyncio
    @patch("neo4j_yass_mcp.security.rate_limiter._rate_limiter", None)
    async def test_rate_limiting_actually_blocks_after_limit(self):
        """Test that rate limiting ACTUALLY blocks requests after exceeding the limit (REAL functionality test)"""
        from neo4j_yass_mcp import server
        from neo4j_yass_mcp.security import initialize_rate_limiter

        # Initialize a real rate limiter with very restrictive limits for testing
        # Allow 5 requests per 60 seconds, burst of 5
        initialize_rate_limiter(rate=5, per_seconds=60, burst=5)

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
            # Create mock context for same session
            mock_ctx = create_mock_context()

            # Make 5 requests - should all succeed
            successful_requests = 0
            for i in range(5):
                result = await server.query_graph.fn(query=f"Request {i+1}", ctx=mock_ctx)
                if result.get("success"):
                    successful_requests += 1

            # All 5 should succeed (within burst limit)
            assert successful_requests == 5, f"Expected 5 successful requests, got {successful_requests}"

            # 6th request should be RATE LIMITED (bucket is empty)
            result_6 = await server.query_graph.fn(query="Request 6 - should be blocked", ctx=mock_ctx)
            assert result_6["success"] is False, "6th request should fail due to rate limiting"
            assert result_6.get("rate_limited") is True, "6th request should be marked as rate_limited"
            assert "Rate limit exceeded" in result_6.get("error", ""), "Error should mention rate limit"
            assert "retry_after_seconds" in result_6, "Should include retry_after_seconds"

            # 7th request should also be blocked
            result_7 = await server.query_graph.fn(query="Request 7 - should also be blocked", ctx=mock_ctx)
            assert result_7["success"] is False, "7th request should fail due to rate limiting"
            assert result_7.get("rate_limited") is True, "7th request should be marked as rate_limited"

        finally:
            # Restore original state
            server.rate_limit_enabled = original_rate_limit_enabled
            # Reinitialize with default settings for other tests
            initialize_rate_limiter()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
