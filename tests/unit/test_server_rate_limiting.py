"""
Tests for decorator-based rate limiting on MCP tools.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest
from fastmcp import Context


def create_mock_context(session_id: str = "test_session_123") -> Mock:
    """Create a mock FastMCP Context for testing."""
    mock_ctx = Mock(spec=Context)
    mock_ctx.session_id = session_id
    mock_ctx.client_id = None
    mock_ctx.request_id = f"req-{session_id}"
    return mock_ctx


class TestRateLimitDecorators:
    """Test the rate limiting decorators applied to MCP tools."""

    def _rate_info(self, retry_after: float) -> dict:
        reset = datetime.now(tz=UTC).timestamp() + retry_after
        return {
            "requests_remaining": 0,
            "reset_time": reset,
            "retry_after": retry_after,
            "limit": 3,
            "window": 60,
        }

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Requires MCP decorator registration - tested in integration tests instead"
    )
    @patch("neo4j_yass_mcp.server.tool_rate_limiter")
    async def test_query_graph_rate_limit_exceeded(self, mock_limiter):
        """query_graph should return rate-limited response when decorator blocks it."""
        mock_limiter.check_and_record = AsyncMock(return_value=(False, self._rate_info(60)))

        from neo4j_yass_mcp import server

        server.chain = Mock()
        server.graph = Mock()

        result = await server.query_graph(query="MATCH (n) RETURN n", ctx=create_mock_context())

        assert result["success"] is False
        assert result["rate_limited"] is True
        assert "Rate limit exceeded" in result["error"]
        mock_limiter.check_and_record.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Requires MCP decorator registration - tested in integration tests instead"
    )
    @patch("neo4j_yass_mcp.server.tool_rate_limiter")
    async def test_execute_cypher_rate_limit_exceeded(self, mock_limiter):
        """execute_cypher should surface rate limit errors from the decorator."""
        mock_limiter.check_and_record = AsyncMock(return_value=(False, self._rate_info(30)))

        from neo4j_yass_mcp import server

        server.graph = Mock()

        result = await server.execute_cypher(
            cypher_query="MATCH (n) RETURN n",
            ctx=create_mock_context(),
        )

        assert result["success"] is False
        assert result["rate_limited"] is True
        mock_limiter.check_and_record.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Requires MCP decorator registration - tested in integration tests instead"
    )
    @patch("neo4j_yass_mcp.server.tool_rate_limiter")
    async def test_query_graph_rate_limit_allowed(self, mock_limiter):
        """When limiter allows the request, tool executes normally."""
        mock_limiter.check_and_record = AsyncMock(
            return_value=(
                True,
                {
                    "requests_remaining": 5,
                    "reset_time": datetime.now(tz=UTC).timestamp() + 60,
                    "retry_after": 0.0,
                    "limit": 10,
                    "window": 60,
                },
            )
        )

        from neo4j_yass_mcp import server

        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "result": "ok",
            "intermediate_steps": [{"query": "MATCH (n) RETURN n"}],
        }
        server.chain = mock_chain
        server.graph = Mock()

        result = await server.query_graph(query="Show me nodes", ctx=create_mock_context())

        assert result["success"] is True
        mock_limiter.check_and_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_disabled_skips_check(self):
        """If tool rate limiting is disabled, decorator should bypass limiter."""
        from neo4j_yass_mcp import server

        original_flag = server.tool_rate_limit_enabled
        server.chain = Mock()
        server.chain.invoke.return_value = {
            "result": "ok",
            "intermediate_steps": [{"query": "MATCH (n) RETURN n"}],
        }
        server.graph = Mock()

        try:
            server.tool_rate_limit_enabled = False
            with patch.object(
                server.tool_rate_limiter,
                "check_and_record",
                AsyncMock(return_value=(True, {})),
            ) as mock_check:
                result = await server.query_graph(query="Show me nodes", ctx=create_mock_context())

            assert result["success"] is True
            mock_check.assert_not_called()
        finally:
            server.tool_rate_limit_enabled = original_flag

    @pytest.mark.asyncio
    async def test_rate_limiter_service_blocks_after_threshold(self):
        """Integration-style test on RateLimiterService."""
        from neo4j_yass_mcp.tool_wrappers import RateLimiterService

        limiter = RateLimiterService()

        for _ in range(3):
            allowed, _ = await limiter.check_and_record("client", limit=3, window=60)
            assert allowed is True

        allowed, info = await limiter.check_and_record("client", limit=3, window=60)
        assert allowed is False
        assert info["retry_after"] >= 0

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Requires MCP decorator registration - tested in integration tests instead"
    )
    @patch("neo4j_yass_mcp.server.tool_rate_limiter")
    async def test_refresh_schema_rate_limit_exceeded(self, mock_limiter):
        """refresh_schema should respect rate-limit decorator."""
        mock_limiter.check_and_record = AsyncMock(return_value=(False, self._rate_info(45)))

        from neo4j_yass_mcp import server

        server.graph = Mock()

        result = await server.refresh_schema(ctx=create_mock_context())

        assert result["success"] is False
        assert result["rate_limited"] is True
        mock_limiter.check_and_record.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Requires MCP decorator registration - tested in integration tests instead"
    )
    @patch("neo4j_yass_mcp.server.tool_rate_limiter")
    async def test_get_schema_rate_limit_exceeded(self, mock_limiter):
        """get_schema resource should surface friendly message when limited."""
        mock_limiter.check_and_record = AsyncMock(return_value=(False, self._rate_info(15)))

        from neo4j_yass_mcp import server

        server.graph = Mock()
        type(server.graph).get_schema = PropertyMock(return_value="schema")

        result = await server.get_schema()

        assert "rate limit exceeded" in result.lower()
        mock_limiter.check_and_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_resource_rate_limit_disabled_skips_check(self):
        """Resource limiter can be toggled off separately."""
        from neo4j_yass_mcp import server

        original_flag = server.resource_rate_limit_enabled
        server.graph = Mock()
        server.graph.get_schema = "schema"

        try:
            server.resource_rate_limit_enabled = False
            with patch.object(
                server.tool_rate_limiter,
                "check_and_record",
                AsyncMock(return_value=(True, {})),
            ) as mock_check:
                result = await server.get_schema()

            assert "schema" in result.lower()
            mock_check.assert_not_called()
        finally:
            server.resource_rate_limit_enabled = original_flag
