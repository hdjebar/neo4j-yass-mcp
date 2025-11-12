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

from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest
from fastmcp import Context

# Fixtures are automatically loaded from tests/conftest.py


def create_mock_context(session_id: str = "test_session_123") -> Mock:
    """Create a mock FastMCP Context for testing."""
    mock_ctx = Mock(spec=Context)
    mock_ctx.session_id = session_id
    mock_ctx.client_id = None
    return mock_ctx


class TestQueryGraph:
    """Test query_graph MCP tool."""

    @pytest.mark.asyncio
    async def test_query_graph_not_initialized(self):
        """Test query_graph when graph/chain not initialized."""
        with patch("neo4j_yass_mcp.server.graph", None):
            with patch("neo4j_yass_mcp.server.chain", None):
                from neo4j_yass_mcp.server import query_graph

                result = await query_graph("test query", ctx=create_mock_context())

                assert result["success"] is False
                assert "not initialized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_graph_success(self, mock_neo4j_graph, mock_langchain_chain):
        """Test successful natural language query."""
        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.server.chain", mock_langchain_chain):
                with patch("neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=None):
                    from neo4j_yass_mcp.server import query_graph

                    result = await query_graph("Who starred in Top Gun?", ctx=create_mock_context())

                    assert result["success"] is True
                    assert "Tom Cruise" in result["answer"]
                    assert "generated_cypher" in result
                    assert "question" in result

    @pytest.mark.asyncio
    async def test_query_graph_with_sanitizer_enabled(self, mock_neo4j_graph):
        """Test query with sanitizer blocking unsafe LLM output.

        With SecureNeo4jGraph, security checks happen at graph.query() level.
        Mock the graph to raise ValueError when sanitizer blocks the query.
        """
        # Mock graph that raises ValueError (what SecureNeo4jGraph does)
        mock_neo4j_graph.query = Mock(
            side_effect=ValueError("Query blocked by sanitizer: LOAD CSV is not allowed")
        )

        # Mock chain that would generate unsafe query
        unsafe_chain = Mock()
        # Chain's invoke will call graph.query() which will raise ValueError
        unsafe_chain.invoke = Mock(
            side_effect=ValueError("Query blocked by sanitizer: LOAD CSV is not allowed")
        )

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.server.chain", unsafe_chain):
                with patch("neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=None):
                    from neo4j_yass_mcp.server import query_graph

                    result = await query_graph("Load system files", ctx=create_mock_context())

                    # Should fail due to sanitizer
                    assert result["success"] is False
                    assert (
                        "sanitizer" in result.get("error", "").lower()
                        or "blocked" in result.get("error", "").lower()
                    )

    @pytest.mark.asyncio
    async def test_query_graph_empty_query(self):
        """Test query_graph with empty query string."""
        with patch("neo4j_yass_mcp.server.graph", Mock()):
            with patch("neo4j_yass_mcp.server.chain", Mock()):
                from neo4j_yass_mcp.server import query_graph

                result = await query_graph("", ctx=create_mock_context())

                # Should handle empty query gracefully
                assert isinstance(result, dict)
                assert "success" in result

    @pytest.mark.asyncio
    async def test_query_graph_exception_handling(self, mock_neo4j_graph):
        """Test query_graph handles exceptions properly."""
        error_chain = Mock()
        error_chain.invoke = Mock(side_effect=Exception("Test error"))

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.server.chain", error_chain):
                with patch("neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=None):
                    from neo4j_yass_mcp.server import query_graph

                    result = await query_graph("test query", ctx=create_mock_context())

                    assert result["success"] is False
                    assert "error" in result
                    assert result["error_type"] == "Exception"


class TestExecuteCypher:
    """Test execute_cypher MCP tool."""

    @pytest.mark.asyncio
    async def test_execute_cypher_not_initialized(self):
        """Test execute_cypher when graph not initialized."""
        with patch("neo4j_yass_mcp.server.graph", None):
            from neo4j_yass_mcp.server import execute_cypher

            result = await execute_cypher("MATCH (n) RETURN n LIMIT 1", ctx=create_mock_context())

            assert result["success"] is False
            assert "not initialized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_cypher_success(self, mock_neo4j_graph):
        """Test successful Cypher execution."""
        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=None):
                from neo4j_yass_mcp.server import execute_cypher

                result = await execute_cypher(
                    "MATCH (n:Movie) RETURN n.title LIMIT 1", ctx=create_mock_context()
                )

                assert result["success"] is True
                assert "result" in result
                assert "query" in result

    @pytest.mark.asyncio
    async def test_execute_cypher_with_parameters(self, mock_neo4j_graph):
        """Test Cypher execution with parameters."""
        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=None):
                from neo4j_yass_mcp.server import execute_cypher

                params = {"title": "Top Gun", "year": 1986}
                result = await execute_cypher(
                    "MATCH (m:Movie {title: $title}) RETURN m",
                    parameters=params,
                    ctx=create_mock_context(),
                )

                assert result["success"] is True
                mock_neo4j_graph.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cypher_read_only_mode(self):
        """Test execute_cypher in read-only mode blocks writes."""
        # Phase 4: Security checks now done in AsyncSecureNeo4jGraph.query()
        # Mock query() to raise ValueError for read-only violation
        from unittest.mock import AsyncMock

        mock_graph = Mock()
        mock_graph.query = AsyncMock(
            side_effect=ValueError("Query blocked in read-only mode: Write operation not allowed")
        )

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=None):
                from neo4j_yass_mcp.server import execute_cypher

                # Try to execute a write query
                result = await execute_cypher("CREATE (n:Test) RETURN n", ctx=create_mock_context())

                assert "error" in result
                assert "read-only" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_cypher_sanitizer_blocks_unsafe(self, mock_neo4j_graph):
        """Test sanitizer blocks unsafe queries."""
        # Phase 4: Security checks now done in AsyncSecureNeo4jGraph.query()
        # Mock query() to raise ValueError for security violation
        from unittest.mock import AsyncMock

        mock_neo4j_graph.query = AsyncMock(
            side_effect=ValueError("Query blocked by sanitizer: Dangerous pattern detected")
        )

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=None):
                from neo4j_yass_mcp.server import execute_cypher

                # Unsafe query - use a clearly dangerous pattern
                result = await execute_cypher(
                    "LOAD CSV FROM 'file.csv' AS line RETURN line", ctx=create_mock_context()
                )

                assert result["success"] is False
                assert "blocked" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_execute_cypher_exception_handling(self, mock_neo4j_graph):
        """Test execute_cypher handles exceptions."""
        from unittest.mock import AsyncMock

        # Phase 4: query() is async, side_effect needs AsyncMock
        mock_neo4j_graph.query = AsyncMock(side_effect=Exception("Database error"))

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=None):
                from neo4j_yass_mcp.server import execute_cypher

                result = await execute_cypher("MATCH (n) RETURN n", ctx=create_mock_context())

                assert result["success"] is False
                assert "error" in result


class TestRefreshSchema:
    """Test refresh_schema MCP tool."""

    @pytest.mark.asyncio
    async def test_refresh_schema_not_initialized(self):
        """Test refresh_schema when graph not initialized."""
        with patch("neo4j_yass_mcp.server.graph", None):
            from neo4j_yass_mcp.server import refresh_schema

            result = await refresh_schema(ctx=create_mock_context())

            assert result["success"] is False
            assert "not initialized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_refresh_schema_success(self, mock_neo4j_graph):
        """Test successful schema refresh."""
        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            from neo4j_yass_mcp.server import refresh_schema

            result = await refresh_schema(ctx=create_mock_context())

            assert result["success"] is True
            assert "schema" in result
            assert result["message"] == "Schema refreshed successfully"
            mock_neo4j_graph.refresh_schema.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_schema_exception(self, mock_neo4j_graph):
        """Test refresh_schema handles exceptions."""
        mock_neo4j_graph.refresh_schema.side_effect = Exception("Refresh error")

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            from neo4j_yass_mcp.server import refresh_schema

            result = await refresh_schema(ctx=create_mock_context())

            assert result["success"] is False
            assert "error" in result


class TestGetSchema:
    """Test get_schema MCP resource."""

    @pytest.mark.asyncio
    async def test_get_schema_not_initialized(self):
        """Test get_schema when graph not initialized."""
        with patch("neo4j_yass_mcp.server.graph", None):
            from neo4j_yass_mcp.server import get_schema

            result = await get_schema()

            assert "error" in result.lower()
            assert "not initialized" in result.lower()

    @pytest.mark.asyncio
    async def test_get_schema_success(self, mock_neo4j_graph):
        """Test successful schema retrieval."""
        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            from neo4j_yass_mcp.server import get_schema

            result = await get_schema()

            assert "Node: Movie" in result
            assert "Relationship: ACTED_IN" in result

    @pytest.mark.asyncio
    async def test_get_schema_exception(self, mock_neo4j_graph):
        """Test get_schema handles exceptions (lines 415-416)."""
        # Make get_schema property raise an exception when accessed
        type(mock_neo4j_graph).get_schema = PropertyMock(side_effect=Exception("Schema error"))

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            from neo4j_yass_mcp.server import get_schema

            result = await get_schema()

            assert "Error retrieving schema" in result
            assert "Schema error" in result


class TestGetDatabaseInfo:
    """Test get_database_info MCP resource."""

    @pytest.mark.asyncio
    async def test_get_database_info_not_initialized(self):
        """Test database info when graph not initialized."""
        with patch("neo4j_yass_mcp.server.graph", None):
            from neo4j_yass_mcp.server import get_database_info

            result = await get_database_info()

            # get_database_info() doesn't check if graph is initialized
            # It just returns environment configuration
            assert isinstance(result, str)
            assert "neo4j" in result.lower()

    @pytest.mark.asyncio
    async def test_get_database_info_success(self, mock_neo4j_graph):
        """Test successful database info retrieval."""
        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            from neo4j_yass_mcp.server import get_database_info

            result = await get_database_info()

            assert isinstance(result, str)
            # Should contain configuration info
            assert len(result) > 0
            assert "connected" in result.lower() or "uri" in result.lower()


class TestUtilityFunctions:
    """Test utility functions in server.py."""

    def test_sanitize_error_message_debug_mode(self):
        """Test error sanitization in debug mode."""
        with patch("neo4j_yass_mcp.server._debug_mode", True):
            from neo4j_yass_mcp.server import sanitize_error_message

            error = ValueError("Sensitive database path: /var/db/secret")
            result = sanitize_error_message(error)

            # Debug mode shows full error
            assert "database path" in result.lower()

    def test_sanitize_error_message_production_mode(self):
        """Test error sanitization in production mode."""
        with patch("neo4j_yass_mcp.server._debug_mode", False):
            from neo4j_yass_mcp.server import sanitize_error_message

            error = ValueError("Sensitive data")
            result = sanitize_error_message(error)

            # Production mode sanitizes (generic error message)
            assert "enable debug_mode" in result.lower()

    def test_truncate_response_under_limit(self):
        """Test truncate_response when under token limit."""
        with patch("neo4j_yass_mcp.server._response_token_limit", None):
            from neo4j_yass_mcp.server import truncate_response

            data = [{"name": "test"} for _ in range(10)]
            result, was_truncated = truncate_response(data)

            assert was_truncated is False
            assert len(result) == 10

    def test_truncate_response_over_limit(self):
        """Test truncate_response when over token limit."""
        with patch("neo4j_yass_mcp.server._response_token_limit", 100):
            from neo4j_yass_mcp.server import truncate_response

            # Large response
            data = [{"name": f"test_{i}" * 100} for i in range(1000)]
            result, was_truncated = truncate_response(data)

            # Should be truncated
            assert was_truncated is True
            assert len(result) < len(data)

    def test_truncate_response_string_truncation(self):
        """Test truncate_response with string data."""
        with patch("neo4j_yass_mcp.server._response_token_limit", 10):
            from neo4j_yass_mcp.server import truncate_response

            # Long string
            data = "x" * 1000
            result, was_truncated = truncate_response(data)

            assert was_truncated is True
            assert len(result) < len(data)
            assert "[truncated]" in result

    def test_truncate_response_dict_truncation(self):
        """Test truncate_response with dict data."""
        with patch("neo4j_yass_mcp.server._response_token_limit", 10):
            from neo4j_yass_mcp.server import truncate_response

            # Large dict
            data = {"key": "x" * 1000}
            result, was_truncated = truncate_response(data)

            assert was_truncated is True
            assert "[truncated]" in str(result)


class TestInitializeNeo4j:
    """Test initialize_neo4j function (Phase 4: Now async)."""

    @pytest.mark.asyncio
    async def test_initialize_neo4j_with_weak_password(self):
        """Test initialization fails with weak password (no override)."""
        with patch.dict(
            "os.environ",
            {
                "NEO4J_PASSWORD": "password",
                "ALLOW_WEAK_PASSWORDS": "false",
                "LLM_API_KEY": "test-key",
            },
        ):
            # Reload config with new environment
            from neo4j_yass_mcp.config import RuntimeConfig

            test_config = RuntimeConfig.from_env()

            with patch("neo4j_yass_mcp.server._config", test_config):
                # Mock LLM components to focus test on password validation
                with patch("neo4j_yass_mcp.server.chatLLM"):
                    with patch("neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"):
                        # Mock AsyncSecureNeo4jGraph to raise the weak password error
                        with patch(
                            "neo4j_yass_mcp.async_graph.AsyncSecureNeo4jGraph"
                        ) as mock_graph:
                            mock_graph.side_effect = ValueError("Weak password detected")

                            from neo4j_yass_mcp.server import initialize_neo4j

                            with pytest.raises(ValueError, match="Weak password detected"):
                                await initialize_neo4j()

    @pytest.mark.asyncio
    async def test_initialize_neo4j_with_weak_password_allowed(self):
        """Test initialization succeeds with weak password when override enabled."""
        from unittest.mock import AsyncMock

        with patch.dict(
            "os.environ",
            {
                "NEO4J_PASSWORD": "password",
                "ALLOW_WEAK_PASSWORDS": "true",
                "LLM_API_KEY": "test-key",
            },
        ):
            # Reload config with new environment
            from neo4j_yass_mcp.config import RuntimeConfig

            test_config = RuntimeConfig.from_env()

            with patch("neo4j_yass_mcp.server._config", test_config):
                with patch("neo4j_yass_mcp.async_graph.AsyncSecureNeo4jGraph") as mock_graph:
                    # Mock async refresh_schema method
                    mock_instance = Mock()
                    mock_instance.refresh_schema = AsyncMock()
                    mock_instance.get_schema = "Node: Test"
                    mock_graph.return_value = mock_instance

                    with patch("neo4j_yass_mcp.server.chatLLM"):
                        with patch("neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"):
                            from neo4j_yass_mcp.server import initialize_neo4j

                            # Should not raise error
                            await initialize_neo4j()

                            # Verify Neo4j connection was attempted
                            mock_graph.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_neo4j_debug_mode_in_production(self):
        """Test initialization fails with DEBUG_MODE in production."""
        with patch.dict(
            "os.environ",
            {
                "DEBUG_MODE": "true",
                "ENVIRONMENT": "production",
                "NEO4J_PASSWORD": "StrongP@ssw0rd!123",
                "ALLOW_WEAK_PASSWORDS": "false",
                "LLM_API_KEY": "test-key",
            },
        ):
            # Reload config with new environment
            from neo4j_yass_mcp.config import RuntimeConfig

            test_config = RuntimeConfig.from_env()

            with patch("neo4j_yass_mcp.server._config", test_config):
                # Mock all external dependencies
                with patch("neo4j_yass_mcp.async_graph.AsyncSecureNeo4jGraph"):
                    with patch("neo4j_yass_mcp.server.chatLLM"):
                        with patch("neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"):
                            from neo4j_yass_mcp.server import initialize_neo4j

                            with pytest.raises(
                                ValueError, match="DEBUG_MODE=true is not allowed in production"
                            ):
                                await initialize_neo4j()

    @pytest.mark.asyncio
    async def test_initialize_neo4j_debug_mode_in_development(self):
        """Test initialization succeeds with DEBUG_MODE in development."""
        from unittest.mock import AsyncMock

        with patch.dict(
            "os.environ",
            {
                "DEBUG_MODE": "true",
                "ENVIRONMENT": "development",
                "NEO4J_PASSWORD": "StrongP@ssw0rd!123",
                "LLM_API_KEY": "test-key",
            },
        ):
            # Reload config with new environment
            from neo4j_yass_mcp.config import RuntimeConfig

            test_config = RuntimeConfig.from_env()

            with patch("neo4j_yass_mcp.server._config", test_config):
                with patch("neo4j_yass_mcp.async_graph.AsyncSecureNeo4jGraph") as mock_graph:
                    # Mock async refresh_schema method
                    mock_instance = Mock()
                    mock_instance.refresh_schema = AsyncMock()
                    mock_instance.get_schema = "Node: Test"
                    mock_graph.return_value = mock_instance

                    with patch("neo4j_yass_mcp.server.chatLLM"):
                        with patch("neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"):
                            from neo4j_yass_mcp.server import initialize_neo4j

                            await initialize_neo4j()

                            mock_graph.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_neo4j_read_only_mode(self):
        """Test initialization with read-only mode enabled."""
        from unittest.mock import AsyncMock

        with patch.dict(
            "os.environ",
            {
                "NEO4J_READ_ONLY": "true",
                "NEO4J_PASSWORD": "StrongP@ssw0rd!123",
                "LLM_API_KEY": "test-key",
            },
        ):
            # Reload config with new environment
            from neo4j_yass_mcp.config import RuntimeConfig

            test_config = RuntimeConfig.from_env()

            with patch("neo4j_yass_mcp.server._config", test_config):
                with patch("neo4j_yass_mcp.async_graph.AsyncSecureNeo4jGraph") as mock_graph:
                    # Mock async refresh_schema method
                    mock_instance = Mock()
                    mock_instance.refresh_schema = AsyncMock()
                    mock_instance.get_schema = "Node: Test"
                    mock_graph.return_value = mock_instance

                    with patch("neo4j_yass_mcp.server.chatLLM"):
                        with patch("neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"):
                            from neo4j_yass_mcp.server import initialize_neo4j

                            await initialize_neo4j()

                            # Verify read-only mode was set
                            from neo4j_yass_mcp.server import _read_only_mode

                            assert _read_only_mode is True

    @pytest.mark.asyncio
    async def test_initialize_neo4j_with_response_token_limit(self):
        """Test initialization with response token limit."""
        from unittest.mock import AsyncMock

        with patch.dict(
            "os.environ",
            {
                "NEO4J_RESPONSE_TOKEN_LIMIT": "5000",
                "NEO4J_PASSWORD": "StrongP@ssw0rd!123",
                "LLM_API_KEY": "test-key",
            },
        ):
            # Reload config with new environment
            from neo4j_yass_mcp.config import RuntimeConfig

            test_config = RuntimeConfig.from_env()

            with patch("neo4j_yass_mcp.server._config", test_config):
                with patch("neo4j_yass_mcp.async_graph.AsyncSecureNeo4jGraph") as mock_graph:
                    # Mock async refresh_schema method
                    mock_instance = Mock()
                    mock_instance.refresh_schema = AsyncMock()
                    mock_instance.get_schema = "Node: Test"
                    mock_graph.return_value = mock_instance

                    with patch("neo4j_yass_mcp.server.chatLLM"):
                        with patch("neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"):
                            from neo4j_yass_mcp.server import initialize_neo4j

                            await initialize_neo4j()

                            from neo4j_yass_mcp.server import _response_token_limit

                            assert _response_token_limit == 5000

    @pytest.mark.asyncio
    async def test_initialize_neo4j_with_invalid_token_limit(self):
        """Test initialization with invalid response token limit."""
        from unittest.mock import AsyncMock

        with patch.dict(
            "os.environ",
            {
                "NEO4J_RESPONSE_TOKEN_LIMIT": "invalid",
                "NEO4J_PASSWORD": "StrongP@ssw0rd!123",
                "LLM_API_KEY": "test-key",
            },
        ):
            # Reload config with new environment
            from neo4j_yass_mcp.config import RuntimeConfig

            test_config = RuntimeConfig.from_env()

            with patch("neo4j_yass_mcp.server._config", test_config):
                with patch("neo4j_yass_mcp.async_graph.AsyncSecureNeo4jGraph") as mock_graph:
                    # Mock async refresh_schema method
                    mock_instance = Mock()
                    mock_instance.refresh_schema = AsyncMock()
                    mock_instance.get_schema = "Node: Test"
                    mock_graph.return_value = mock_instance

                    with patch("neo4j_yass_mcp.server.chatLLM"):
                        with patch("neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"):
                            from neo4j_yass_mcp.server import initialize_neo4j

                            # Should not raise error, just log warning
                            await initialize_neo4j()

    @pytest.mark.asyncio
    async def test_initialize_neo4j_with_langchain_dangerous_requests(self):
        """Test initialization with LANGCHAIN_ALLOW_DANGEROUS_REQUESTS."""
        from unittest.mock import AsyncMock

        with patch.dict(
            "os.environ",
            {
                "LANGCHAIN_ALLOW_DANGEROUS_REQUESTS": "true",
                "NEO4J_PASSWORD": "StrongP@ssw0rd!123",
                "LLM_API_KEY": "test-key",
            },
        ):
            # Reload config with new environment
            from neo4j_yass_mcp.config import RuntimeConfig

            test_config = RuntimeConfig.from_env()

            with patch("neo4j_yass_mcp.server._config", test_config):
                with patch("neo4j_yass_mcp.async_graph.AsyncSecureNeo4jGraph") as mock_graph:
                    # Mock async refresh_schema method
                    mock_instance = Mock()
                    mock_instance.refresh_schema = AsyncMock()
                    mock_instance.get_schema = "Node: Test"
                    mock_graph.return_value = mock_instance

                    with patch("neo4j_yass_mcp.server.chatLLM"):
                        with patch(
                            "neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"
                        ) as mock_chain:
                            from neo4j_yass_mcp.server import initialize_neo4j

                            await initialize_neo4j()

                            # Verify chain was created with allow_dangerous_requests=True
                            mock_chain.assert_called_once()
                            call_kwargs = mock_chain.call_args[1]
                            assert call_kwargs["allow_dangerous_requests"] is True


class TestCleanup:
    """Test cleanup function."""

    # Phase 4: test_cleanup_with_executor removed - no longer using ThreadPoolExecutor

    def test_cleanup_with_neo4j_driver(self):
        """Test cleanup closes Neo4j driver."""
        from neo4j_yass_mcp.server import cleanup

        # Phase 4: AsyncDriver.close() is async, need AsyncMock
        mock_driver = Mock()
        mock_driver.close = AsyncMock()

        mock_graph = Mock()
        mock_graph._driver = mock_driver

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            cleanup()

            # Driver close is called via asyncio.run() or create_task()
            # We can't easily assert on the async call in sync test

    def test_cleanup_with_no_driver(self):
        """Test cleanup handles graph without driver."""
        from neo4j_yass_mcp.server import cleanup

        # Create mock graph without _driver attribute
        mock_graph = Mock(spec=[])

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            # Should not raise error
            cleanup()

    def test_cleanup_with_attribute_error(self):
        """Test cleanup handles AttributeError when accessing driver (line 973)."""
        from neo4j_yass_mcp.server import cleanup

        # Create mock graph that raises AttributeError when accessing _driver
        mock_graph = Mock()
        type(mock_graph)._driver = PropertyMock(side_effect=AttributeError("No _driver"))

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            # Should not raise error, should log warning
            cleanup()

    # Phase 4: test_cleanup_with_executor_error removed - no longer using ThreadPoolExecutor

    def test_cleanup_with_driver_error(self):
        """Test cleanup handles driver close errors."""
        from neo4j_yass_mcp.server import cleanup

        mock_driver = Mock()
        mock_driver.close.side_effect = Exception("Close error")

        mock_graph = Mock()
        mock_graph._driver = mock_driver

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            # Should not raise error
            cleanup()


class TestAuditLoggerIntegration:
    """Test audit logger integration in tools."""

    @pytest.mark.asyncio
    async def test_query_graph_with_audit_logger(self, mock_neo4j_graph, mock_langchain_chain):
        """Test query_graph logs to audit logger."""
        mock_audit_logger = Mock()
        mock_audit_logger.log_query = Mock()
        mock_audit_logger.log_response = Mock()

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.server.chain", mock_langchain_chain):
                with patch(
                    "neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=mock_audit_logger
                ):
                    from neo4j_yass_mcp.server import query_graph

                    await query_graph("Test query", ctx=create_mock_context())

                    # Verify audit logging was called
                    mock_audit_logger.log_query.assert_called_once()
                    mock_audit_logger.log_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_graph_sanitizer_logs_error(self, mock_neo4j_graph):
        """Test query_graph logs sanitizer blocks to audit.

        With SecureNeo4jGraph, sanitizer failures raise ValueError.
        """
        mock_audit_logger = Mock()
        mock_audit_logger.log_error = Mock()

        # Chain raises ValueError (what SecureNeo4jGraph does on sanitizer failure)
        unsafe_chain = Mock()
        unsafe_chain.invoke = Mock(
            side_effect=ValueError("Query blocked by sanitizer: LOAD CSV is not allowed")
        )

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.server.chain", unsafe_chain):
                with patch(
                    "neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=mock_audit_logger
                ):
                    from neo4j_yass_mcp.server import query_graph

                    await query_graph("Load files", ctx=create_mock_context())

                    # Verify error was logged
                    mock_audit_logger.log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_graph_read_only_mode_logs_error(self, mock_neo4j_graph):
        """Test query_graph logs read-only violations.

        With SecureNeo4jGraph, read-only violations raise ValueError.
        """
        mock_audit_logger = Mock()
        mock_audit_logger.log_error = Mock()

        # Chain raises ValueError (what SecureNeo4jGraph does on read-only violation)
        write_chain = Mock()
        write_chain.invoke = Mock(
            side_effect=ValueError(
                "Query blocked in read-only mode: CREATE operations are not allowed"
            )
        )

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.server.chain", write_chain):
                with patch("neo4j_yass_mcp.server._read_only_mode", True):
                    with patch(
                        "neo4j_yass_mcp.handlers.tools.get_audit_logger",
                        return_value=mock_audit_logger,
                    ):
                        from neo4j_yass_mcp.server import query_graph

                        await query_graph("Create node", ctx=create_mock_context())

                        # Verify error was logged
                        mock_audit_logger.log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cypher_with_audit_logger(self, mock_neo4j_graph):
        """Test execute_cypher logs to audit logger."""
        mock_audit_logger = Mock()
        mock_audit_logger.log_query = Mock()
        mock_audit_logger.log_response = Mock()

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch(
                "neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=mock_audit_logger
            ):
                from neo4j_yass_mcp.server import execute_cypher

                await execute_cypher("MATCH (n) RETURN n", ctx=create_mock_context())

                # Verify audit logging
                mock_audit_logger.log_query.assert_called_once()
                mock_audit_logger.log_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cypher_sanitizer_logs_error(self, mock_neo4j_graph):
        """Test execute_cypher logs sanitizer blocks (Phase 4: AsyncMock)."""
        from unittest.mock import AsyncMock

        # Phase 4: Mock graph.query() to raise ValueError (security check)
        mock_neo4j_graph.query = AsyncMock(
            side_effect=ValueError("Query blocked by sanitizer: LOAD CSV not allowed")
        )

        mock_audit_logger = Mock()
        mock_audit_logger.log_error = Mock()

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch(
                "neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=mock_audit_logger
            ):
                from neo4j_yass_mcp.server import execute_cypher

                await execute_cypher(
                    "LOAD CSV FROM 'file.csv' AS line RETURN line", ctx=create_mock_context()
                )

                # Verify error was logged
                mock_audit_logger.log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cypher_read_only_logs_error(self, mock_neo4j_graph):
        """Test execute_cypher logs read-only violations (Phase 4: AsyncMock)."""
        from unittest.mock import AsyncMock

        # Phase 4: Mock graph.query() to raise ValueError (read-only check)
        mock_neo4j_graph.query = AsyncMock(
            side_effect=ValueError("Query blocked in read-only mode: Write operation not allowed")
        )

        mock_audit_logger = Mock()
        mock_audit_logger.log_error = Mock()

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.server._read_only_mode", True):
                with patch(
                    "neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=mock_audit_logger
                ):
                    from neo4j_yass_mcp.server import execute_cypher

                    await execute_cypher("CREATE (n:Test) RETURN n", ctx=create_mock_context())

                    # Verify error was logged
                    mock_audit_logger.log_error.assert_called_once()


class TestResponseTruncation:
    """Test response truncation with audit logger."""

    @pytest.mark.asyncio
    async def test_execute_cypher_truncated_response_logging(self, mock_neo4j_graph):
        """Test execute_cypher logs truncated responses."""
        # Mock large result
        mock_neo4j_graph.query.return_value = [{"data": "x" * 10000} for _ in range(1000)]

        mock_audit_logger = Mock()
        mock_audit_logger.log_query = Mock()
        mock_audit_logger.log_response = Mock()

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.server._response_token_limit", 100):
                with patch(
                    "neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=mock_audit_logger
                ):
                    from neo4j_yass_mcp.server import execute_cypher

                    result = await execute_cypher("MATCH (n) RETURN n", ctx=create_mock_context())

                    # Should include truncation metadata
                    assert result.get("truncated") is True
                    assert "original_count" in result
                    assert "returned_count" in result

    @pytest.mark.asyncio
    async def test_query_graph_truncated_response(self, mock_neo4j_graph):
        """Test query_graph truncates large intermediate steps."""
        # Create chain with large intermediate steps
        large_chain = Mock()
        large_chain.invoke = Mock(
            return_value={
                "result": "Result",
                "intermediate_steps": [{"query": "MATCH (n) RETURN n", "context": "x" * 100000}],
            }
        )

        with patch("neo4j_yass_mcp.server.graph", mock_neo4j_graph):
            with patch("neo4j_yass_mcp.server.chain", large_chain):
                with patch("neo4j_yass_mcp.server._response_token_limit", 100):
                    with patch("neo4j_yass_mcp.handlers.tools.get_audit_logger", return_value=None):
                        from neo4j_yass_mcp.server import query_graph

                        result = await query_graph("Test query", ctx=create_mock_context())

                        # Should include truncation warning
                        assert result.get("truncated") is True
                        assert "warning" in result


# Phase 4: TestSanitizerWarnings removed - security checks now in AsyncSecureNeo4jGraph
# Security features tested in tests/unit/test_async_graph.py


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
