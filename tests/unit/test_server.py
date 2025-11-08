"""
Comprehensive tests for server.py MCP tools and resources.

Tests cover:
- query_graph: Natural language query processing
- execute_cypher: Direct Cypher execution
- refresh_schema: Schema refresh operations
- get_schema: Schema retrieval
- get_database_info: Database information
- Error handling and edge cases
- Security validations
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from typing import Any, Dict

# Fixtures are automatically loaded from tests/conftest.py


class TestQueryGraph:
    """Test query_graph MCP tool."""

    @pytest.mark.asyncio
    async def test_query_graph_not_initialized(self):
        """Test query_graph when graph/chain not initialized."""
        with patch('neo4j_yass_mcp.server.graph', None):
            with patch('neo4j_yass_mcp.server.chain', None):
                from neo4j_yass_mcp.server import query_graph

                result = await query_graph("test query")

                assert result["success"] is False
                assert "not initialized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_graph_success(self, mock_neo4j_graph, mock_langchain_chain):
        """Test successful natural language query."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.chain', mock_langchain_chain):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                    from neo4j_yass_mcp.server import query_graph

                    result = await query_graph("Who starred in Top Gun?")

                    assert result["success"] is True
                    assert "Tom Cruise" in result["answer"]
                    assert "generated_cypher" in result
                    assert "question" in result

    @pytest.mark.asyncio
    async def test_query_graph_with_sanitizer_enabled(self, mock_neo4j_graph):
        """Test query with sanitizer blocking unsafe LLM output."""
        # Mock chain that generates unsafe query (use a clearly dangerous pattern)
        unsafe_chain = Mock()
        unsafe_chain.invoke = Mock(return_value={
            "result": "Data loaded",
            "intermediate_steps": [
                {"query": "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line"}
            ]
        })

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.chain', unsafe_chain):
                with patch('neo4j_yass_mcp.server.sanitizer_enabled', True):
                    with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                        from neo4j_yass_mcp.server import query_graph

                        result = await query_graph("Load system files")

                        # Should fail due to sanitizer
                        assert result["success"] is False
                        assert "sanitizer" in result.get("error", "").lower() or \
                               "blocked" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_query_graph_empty_query(self):
        """Test query_graph with empty query string."""
        with patch('neo4j_yass_mcp.server.graph', Mock()):
            with patch('neo4j_yass_mcp.server.chain', Mock()):
                from neo4j_yass_mcp.server import query_graph

                result = await query_graph("")

                # Should handle empty query gracefully
                assert isinstance(result, dict)
                assert "success" in result

    @pytest.mark.asyncio
    async def test_query_graph_exception_handling(self, mock_neo4j_graph):
        """Test query_graph handles exceptions properly."""
        error_chain = Mock()
        error_chain.invoke = Mock(side_effect=Exception("Test error"))

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.chain', error_chain):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                    from neo4j_yass_mcp.server import query_graph

                    result = await query_graph("test query")

                    assert result["success"] is False
                    assert "error" in result
                    assert result["type"] == "Exception"


class TestExecuteCypher:
    """Test execute_cypher MCP tool."""

    @pytest.mark.asyncio
    async def test_execute_cypher_not_initialized(self):
        """Test execute_cypher when graph not initialized."""
        with patch('neo4j_yass_mcp.server.graph', None):
            from neo4j_yass_mcp.server import execute_cypher

            result = await execute_cypher("MATCH (n) RETURN n LIMIT 1")

            assert result["success"] is False
            assert "not initialized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_cypher_success(self, mock_neo4j_graph):
        """Test successful Cypher execution."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                from neo4j_yass_mcp.server import execute_cypher

                result = await execute_cypher("MATCH (n:Movie) RETURN n.title LIMIT 1")

                assert result["success"] is True
                assert "result" in result
                assert "query" in result

    @pytest.mark.asyncio
    async def test_execute_cypher_with_parameters(self, mock_neo4j_graph):
        """Test Cypher execution with parameters."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                from neo4j_yass_mcp.server import execute_cypher

                params = {"title": "Top Gun", "year": 1986}
                result = await execute_cypher(
                    "MATCH (m:Movie {title: $title}) RETURN m",
                    parameters=params
                )

                assert result["success"] is True
                mock_neo4j_graph.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cypher_read_only_mode(self):
        """Test execute_cypher in read-only mode blocks writes."""
        with patch('neo4j_yass_mcp.server.graph', Mock()):
            with patch('neo4j_yass_mcp.server._read_only_mode', True):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                    from neo4j_yass_mcp.server import execute_cypher

                    # Try to execute a write query
                    result = await execute_cypher("CREATE (n:Test) RETURN n")

                    assert "error" in result
                    assert "read-only" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_cypher_sanitizer_blocks_unsafe(self, mock_neo4j_graph):
        """Test sanitizer blocks unsafe queries."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.sanitizer_enabled', True):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                    from neo4j_yass_mcp.server import execute_cypher

                    # Unsafe query - use a clearly dangerous pattern
                    result = await execute_cypher("LOAD CSV FROM 'file.csv' AS line RETURN line")

                    assert result["success"] is False
                    assert "blocked" in result.get("error", "").lower() or \
                           "dangerous" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_execute_cypher_exception_handling(self, mock_neo4j_graph):
        """Test execute_cypher handles exceptions."""
        mock_neo4j_graph.query.side_effect = Exception("Database error")

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                from neo4j_yass_mcp.server import execute_cypher

                result = await execute_cypher("MATCH (n) RETURN n")

                assert result["success"] is False
                assert "error" in result


class TestRefreshSchema:
    """Test refresh_schema MCP tool."""

    @pytest.mark.asyncio
    async def test_refresh_schema_not_initialized(self):
        """Test refresh_schema when graph not initialized."""
        with patch('neo4j_yass_mcp.server.graph', None):
            from neo4j_yass_mcp.server import refresh_schema

            result = await refresh_schema()

            assert result["success"] is False
            assert "not initialized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_refresh_schema_success(self, mock_neo4j_graph):
        """Test successful schema refresh."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            from neo4j_yass_mcp.server import refresh_schema

            result = await refresh_schema()

            assert result["success"] is True
            assert "schema" in result
            assert result["message"] == "Schema refreshed successfully"
            mock_neo4j_graph.refresh_schema.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_schema_exception(self, mock_neo4j_graph):
        """Test refresh_schema handles exceptions."""
        mock_neo4j_graph.refresh_schema.side_effect = Exception("Refresh error")

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            from neo4j_yass_mcp.server import refresh_schema

            result = await refresh_schema()

            assert result["success"] is False
            assert "error" in result


class TestGetSchema:
    """Test get_schema MCP resource."""

    def test_get_schema_not_initialized(self):
        """Test get_schema when graph not initialized."""
        with patch('neo4j_yass_mcp.server.graph', None):
            from neo4j_yass_mcp.server import get_schema

            result = get_schema()

            assert "error" in result.lower()
            assert "not initialized" in result.lower()

    def test_get_schema_success(self, mock_neo4j_graph):
        """Test successful schema retrieval."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            from neo4j_yass_mcp.server import get_schema

            result = get_schema()

            assert "Node: Movie" in result
            assert "Relationship: ACTED_IN" in result


class TestGetDatabaseInfo:
    """Test get_database_info MCP resource."""

    def test_get_database_info_not_initialized(self):
        """Test database info when graph not initialized."""
        with patch('neo4j_yass_mcp.server.graph', None):
            from neo4j_yass_mcp.server import get_database_info

            result = get_database_info()

            # get_database_info() doesn't check if graph is initialized
            # It just returns environment configuration
            assert isinstance(result, str)
            assert "neo4j" in result.lower()

    def test_get_database_info_success(self, mock_neo4j_graph):
        """Test successful database info retrieval."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.sanitizer_enabled', True):
                with patch('neo4j_yass_mcp.server._read_only_mode', False):
                    from neo4j_yass_mcp.server import get_database_info

                    result = get_database_info()

                    assert isinstance(result, str)
                    # Should contain configuration info
                    assert len(result) > 0
                    assert "connected" in result.lower() or "uri" in result.lower()


class TestUtilityFunctions:
    """Test utility functions in server.py."""

    def test_sanitize_error_message_debug_mode(self):
        """Test error sanitization in debug mode."""
        with patch('neo4j_yass_mcp.server._debug_mode', True):
            from neo4j_yass_mcp.server import sanitize_error_message

            error = ValueError("Sensitive database path: /var/db/secret")
            result = sanitize_error_message(error)

            # Debug mode shows full error
            assert "database path" in result.lower()

    def test_sanitize_error_message_production_mode(self):
        """Test error sanitization in production mode."""
        with patch('neo4j_yass_mcp.server._debug_mode', False):
            from neo4j_yass_mcp.server import sanitize_error_message

            error = ValueError("Sensitive data")
            result = sanitize_error_message(error)

            # Production mode sanitizes (generic error message)
            assert "enable debug_mode" in result.lower()

    def test_truncate_response_under_limit(self):
        """Test truncate_response when under token limit."""
        with patch('neo4j_yass_mcp.server._response_token_limit', None):
            from neo4j_yass_mcp.server import truncate_response

            data = [{"name": "test"} for _ in range(10)]
            result, was_truncated = truncate_response(data)

            assert was_truncated is False
            assert len(result) == 10

    def test_truncate_response_over_limit(self):
        """Test truncate_response when over token limit."""
        with patch('neo4j_yass_mcp.server._response_token_limit', 100):
            from neo4j_yass_mcp.server import truncate_response

            # Large response
            data = [{"name": f"test_{i}" * 100} for i in range(1000)]
            result, was_truncated = truncate_response(data)

            # Should be truncated
            assert was_truncated is True
            assert len(result) < len(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
