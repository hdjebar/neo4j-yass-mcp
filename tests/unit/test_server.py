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

from unittest.mock import Mock, patch

import pytest

# Fixtures are automatically loaded from tests/conftest.py


class TestQueryGraph:
    """Test query_graph MCP tool."""

    @pytest.mark.asyncio
    async def test_query_graph_not_initialized(self):
        """Test query_graph when graph/chain not initialized."""
        with patch('neo4j_yass_mcp.server.graph', None):
            with patch('neo4j_yass_mcp.server.chain', None):
                from neo4j_yass_mcp.server import query_graph

                result = await query_graph.fn("test query")

                assert result["success"] is False
                assert "not initialized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_graph_success(self, mock_neo4j_graph, mock_langchain_chain):
        """Test successful natural language query."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.chain', mock_langchain_chain):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                    from neo4j_yass_mcp.server import query_graph

                    result = await query_graph.fn("Who starred in Top Gun?")

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

                        result = await query_graph.fn("Load system files")

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

                result = await query_graph.fn("")

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

                    result = await query_graph.fn("test query")

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

            result = await refresh_schema.fn()

            assert result["success"] is False
            assert "not initialized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_refresh_schema_success(self, mock_neo4j_graph):
        """Test successful schema refresh."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            from neo4j_yass_mcp.server import refresh_schema

            result = await refresh_schema.fn()

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

            result = await refresh_schema.fn()

            assert result["success"] is False
            assert "error" in result


class TestGetSchema:
    """Test get_schema MCP resource."""

    def test_get_schema_not_initialized(self):
        """Test get_schema when graph not initialized."""
        with patch('neo4j_yass_mcp.server.graph', None):
            from neo4j_yass_mcp.server import get_schema

            result = get_schema.fn()

            assert "error" in result.lower()
            assert "not initialized" in result.lower()

    def test_get_schema_success(self, mock_neo4j_graph):
        """Test successful schema retrieval."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            from neo4j_yass_mcp.server import get_schema

            result = get_schema.fn()

            assert "Node: Movie" in result
            assert "Relationship: ACTED_IN" in result


class TestGetDatabaseInfo:
    """Test get_database_info MCP resource."""

    def test_get_database_info_not_initialized(self):
        """Test database info when graph not initialized."""
        with patch('neo4j_yass_mcp.server.graph', None):
            from neo4j_yass_mcp.server import get_database_info

            result = get_database_info.fn()

            # get_database_info.fn() doesn't check if graph is initialized
            # It just returns environment configuration
            assert isinstance(result, str)
            assert "neo4j" in result.lower()

    def test_get_database_info_success(self, mock_neo4j_graph):
        """Test successful database info retrieval."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.sanitizer_enabled', True):
                with patch('neo4j_yass_mcp.server._read_only_mode', False):
                    from neo4j_yass_mcp.server import get_database_info

                    result = get_database_info.fn()

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

    def test_truncate_response_string_truncation(self):
        """Test truncate_response with string data."""
        with patch('neo4j_yass_mcp.server._response_token_limit', 10):
            from neo4j_yass_mcp.server import truncate_response

            # Long string
            data = "x" * 1000
            result, was_truncated = truncate_response(data)

            assert was_truncated is True
            assert len(result) < len(data)
            assert "[truncated]" in result

    def test_truncate_response_dict_truncation(self):
        """Test truncate_response with dict data."""
        with patch('neo4j_yass_mcp.server._response_token_limit', 10):
            from neo4j_yass_mcp.server import truncate_response

            # Large dict
            data = {"key": "x" * 1000}
            result, was_truncated = truncate_response(data)

            assert was_truncated is True
            assert "[truncated]" in str(result)


class TestInitializeNeo4j:
    """Test initialize_neo4j function."""

    def test_initialize_neo4j_with_weak_password(self):
        """Test initialization fails with weak password (no override)."""
        with patch.dict('os.environ', {
            'NEO4J_PASSWORD': 'password',
            'ALLOW_WEAK_PASSWORDS': 'false'
        }):
            from neo4j_yass_mcp.server import initialize_neo4j

            with pytest.raises(ValueError, match="Weak password detected"):
                initialize_neo4j()

    def test_initialize_neo4j_with_weak_password_allowed(self):
        """Test initialization succeeds with weak password when override enabled."""
        with patch.dict('os.environ', {
            'NEO4J_PASSWORD': 'password',
            'ALLOW_WEAK_PASSWORDS': 'true',
            'LLM_API_KEY': 'test-key'
        }):
            with patch('neo4j_yass_mcp.server.Neo4jGraph') as mock_graph:
                with patch('neo4j_yass_mcp.server.chatLLM'):
                    with patch('neo4j_yass_mcp.server.GraphCypherQAChain.from_llm'):
                        from neo4j_yass_mcp.server import initialize_neo4j

                        # Should not raise error
                        initialize_neo4j()

                        # Verify Neo4j connection was attempted
                        mock_graph.assert_called_once()

    def test_initialize_neo4j_debug_mode_in_production(self):
        """Test initialization fails with DEBUG_MODE in production."""
        with patch.dict('os.environ', {
            'DEBUG_MODE': 'true',
            'ENVIRONMENT': 'production',
            'NEO4J_PASSWORD': 'StrongP@ssw0rd!123',
        }):
            from neo4j_yass_mcp.server import initialize_neo4j

            with pytest.raises(ValueError, match="DEBUG_MODE=true is not allowed in production"):
                initialize_neo4j()

    def test_initialize_neo4j_debug_mode_in_development(self):
        """Test initialization succeeds with DEBUG_MODE in development."""
        with patch.dict('os.environ', {
            'DEBUG_MODE': 'true',
            'ENVIRONMENT': 'development',
            'NEO4J_PASSWORD': 'StrongP@ssw0rd!123',
            'LLM_API_KEY': 'test-key'
        }):
            with patch('neo4j_yass_mcp.server.Neo4jGraph') as mock_graph:
                with patch('neo4j_yass_mcp.server.chatLLM'):
                    with patch('neo4j_yass_mcp.server.GraphCypherQAChain.from_llm'):
                        from neo4j_yass_mcp.server import initialize_neo4j

                        initialize_neo4j()

                        mock_graph.assert_called_once()

    def test_initialize_neo4j_read_only_mode(self):
        """Test initialization with read-only mode enabled."""
        with patch.dict('os.environ', {
            'NEO4J_READ_ONLY': 'true',
            'NEO4J_PASSWORD': 'StrongP@ssw0rd!123',
            'LLM_API_KEY': 'test-key'
        }):
            with patch('neo4j_yass_mcp.server.Neo4jGraph'):
                with patch('neo4j_yass_mcp.server.chatLLM'):
                    with patch('neo4j_yass_mcp.server.GraphCypherQAChain.from_llm'):
                        from neo4j_yass_mcp.server import initialize_neo4j

                        initialize_neo4j()

                        # Verify read-only mode was set
                        from neo4j_yass_mcp.server import _read_only_mode
                        assert _read_only_mode is True

    def test_initialize_neo4j_with_response_token_limit(self):
        """Test initialization with response token limit."""
        with patch.dict('os.environ', {
            'NEO4J_RESPONSE_TOKEN_LIMIT': '5000',
            'NEO4J_PASSWORD': 'StrongP@ssw0rd!123',
            'LLM_API_KEY': 'test-key'
        }):
            with patch('neo4j_yass_mcp.server.Neo4jGraph'):
                with patch('neo4j_yass_mcp.server.chatLLM'):
                    with patch('neo4j_yass_mcp.server.GraphCypherQAChain.from_llm'):
                        from neo4j_yass_mcp.server import initialize_neo4j

                        initialize_neo4j()

                        from neo4j_yass_mcp.server import _response_token_limit
                        assert _response_token_limit == 5000

    def test_initialize_neo4j_with_invalid_token_limit(self):
        """Test initialization with invalid response token limit."""
        with patch.dict('os.environ', {
            'NEO4J_RESPONSE_TOKEN_LIMIT': 'invalid',
            'NEO4J_PASSWORD': 'StrongP@ssw0rd!123',
            'LLM_API_KEY': 'test-key'
        }):
            with patch('neo4j_yass_mcp.server.Neo4jGraph'):
                with patch('neo4j_yass_mcp.server.chatLLM'):
                    with patch('neo4j_yass_mcp.server.GraphCypherQAChain.from_llm'):
                        from neo4j_yass_mcp.server import initialize_neo4j

                        # Should not raise error, just log warning
                        initialize_neo4j()

    def test_initialize_neo4j_with_langchain_dangerous_requests(self):
        """Test initialization with LANGCHAIN_ALLOW_DANGEROUS_REQUESTS."""
        with patch.dict('os.environ', {
            'LANGCHAIN_ALLOW_DANGEROUS_REQUESTS': 'true',
            'NEO4J_PASSWORD': 'StrongP@ssw0rd!123',
            'LLM_API_KEY': 'test-key'
        }):
            with patch('neo4j_yass_mcp.server.Neo4jGraph'):
                with patch('neo4j_yass_mcp.server.chatLLM'):
                    with patch('neo4j_yass_mcp.server.GraphCypherQAChain.from_llm') as mock_chain:
                        from neo4j_yass_mcp.server import initialize_neo4j

                        initialize_neo4j()

                        # Verify chain was created with allow_dangerous_requests=True
                        mock_chain.assert_called_once()
                        call_kwargs = mock_chain.call_args[1]
                        assert call_kwargs['allow_dangerous_requests'] is True


class TestCleanup:
    """Test cleanup function."""

    def test_cleanup_with_executor(self):
        """Test cleanup shuts down executor."""
        from neo4j_yass_mcp.server import cleanup

        # Create mock executor
        mock_executor = Mock()
        mock_executor.shutdown = Mock()

        with patch('neo4j_yass_mcp.server._executor', mock_executor):
            cleanup()

            mock_executor.shutdown.assert_called_once_with(wait=True)

    def test_cleanup_with_neo4j_driver(self):
        """Test cleanup closes Neo4j driver."""
        from neo4j_yass_mcp.server import cleanup

        # Create mock graph with driver
        mock_driver = Mock()
        mock_driver.close = Mock()

        mock_graph = Mock()
        mock_graph._driver = mock_driver

        with patch('neo4j_yass_mcp.server.graph', mock_graph):
            cleanup()

            mock_driver.close.assert_called_once()

    def test_cleanup_with_no_driver(self):
        """Test cleanup handles graph without driver."""
        from neo4j_yass_mcp.server import cleanup

        # Create mock graph without _driver attribute
        mock_graph = Mock(spec=[])

        with patch('neo4j_yass_mcp.server.graph', mock_graph):
            # Should not raise error
            cleanup()

    def test_cleanup_with_executor_error(self):
        """Test cleanup handles executor shutdown errors."""
        from neo4j_yass_mcp.server import cleanup

        mock_executor = Mock()
        mock_executor.shutdown.side_effect = Exception("Shutdown error")

        with patch('neo4j_yass_mcp.server._executor', mock_executor):
            # Should not raise error
            cleanup()

    def test_cleanup_with_driver_error(self):
        """Test cleanup handles driver close errors."""
        from neo4j_yass_mcp.server import cleanup

        mock_driver = Mock()
        mock_driver.close.side_effect = Exception("Close error")

        mock_graph = Mock()
        mock_graph._driver = mock_driver

        with patch('neo4j_yass_mcp.server.graph', mock_graph):
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

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.chain', mock_langchain_chain):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=mock_audit_logger):
                    from neo4j_yass_mcp.server import query_graph

                    await query_graph.fn("Test query")

                    # Verify audit logging was called
                    mock_audit_logger.log_query.assert_called_once()
                    mock_audit_logger.log_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_graph_sanitizer_logs_error(self, mock_neo4j_graph):
        """Test query_graph logs sanitizer blocks to audit."""
        mock_audit_logger = Mock()
        mock_audit_logger.log_error = Mock()

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
                    with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=mock_audit_logger):
                        from neo4j_yass_mcp.server import query_graph

                        await query_graph.fn("Load files")

                        # Verify error was logged
                        mock_audit_logger.log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_graph_read_only_mode_logs_error(self, mock_neo4j_graph):
        """Test query_graph logs read-only violations."""
        mock_audit_logger = Mock()
        mock_audit_logger.log_error = Mock()

        write_chain = Mock()
        write_chain.invoke = Mock(return_value={
            "result": "Created",
            "intermediate_steps": [
                {"query": "CREATE (n:Test) RETURN n"}
            ]
        })

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.chain', write_chain):
                with patch('neo4j_yass_mcp.server._read_only_mode', True):
                    with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=mock_audit_logger):
                        from neo4j_yass_mcp.server import query_graph

                        await query_graph.fn("Create node")

                        # Verify error was logged
                        mock_audit_logger.log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cypher_with_audit_logger(self, mock_neo4j_graph):
        """Test execute_cypher logs to audit logger."""
        mock_audit_logger = Mock()
        mock_audit_logger.log_query = Mock()
        mock_audit_logger.log_response = Mock()

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=mock_audit_logger):
                from neo4j_yass_mcp.server import execute_cypher

                await execute_cypher("MATCH (n) RETURN n")

                # Verify audit logging
                mock_audit_logger.log_query.assert_called_once()
                mock_audit_logger.log_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cypher_sanitizer_logs_error(self, mock_neo4j_graph):
        """Test execute_cypher logs sanitizer blocks."""
        mock_audit_logger = Mock()
        mock_audit_logger.log_error = Mock()

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.sanitizer_enabled', True):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=mock_audit_logger):
                    from neo4j_yass_mcp.server import execute_cypher

                    await execute_cypher("LOAD CSV FROM 'file.csv' AS line RETURN line")

                    # Verify error was logged
                    mock_audit_logger.log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cypher_read_only_logs_error(self, mock_neo4j_graph):
        """Test execute_cypher logs read-only violations."""
        mock_audit_logger = Mock()
        mock_audit_logger.log_error = Mock()

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server._read_only_mode', True):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=mock_audit_logger):
                    from neo4j_yass_mcp.server import execute_cypher

                    await execute_cypher("CREATE (n:Test) RETURN n")

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

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server._response_token_limit', 100):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=mock_audit_logger):
                    from neo4j_yass_mcp.server import execute_cypher

                    result = await execute_cypher("MATCH (n) RETURN n")

                    # Should include truncation metadata
                    assert result.get("truncated") is True
                    assert "original_count" in result
                    assert "returned_count" in result

    @pytest.mark.asyncio
    async def test_query_graph_truncated_response(self, mock_neo4j_graph):
        """Test query_graph truncates large intermediate steps."""
        # Create chain with large intermediate steps
        large_chain = Mock()
        large_chain.invoke = Mock(return_value={
            "result": "Result",
            "intermediate_steps": [{"query": "MATCH (n) RETURN n", "context": "x" * 100000}]
        })

        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.chain', large_chain):
                with patch('neo4j_yass_mcp.server._response_token_limit', 100):
                    with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                        from neo4j_yass_mcp.server import query_graph

                        result = await query_graph.fn("Test query")

                        # Should include truncation warning
                        assert result.get("truncated") is True
                        assert "warning" in result


class TestSanitizerWarnings:
    """Test sanitizer warning handling."""

    @pytest.mark.asyncio
    async def test_execute_cypher_sanitizer_warnings(self, mock_neo4j_graph):
        """Test execute_cypher logs sanitizer warnings."""
        with patch('neo4j_yass_mcp.server.graph', mock_neo4j_graph):
            with patch('neo4j_yass_mcp.server.sanitizer_enabled', True):
                with patch('neo4j_yass_mcp.server.get_audit_logger', return_value=None):
                    # Mock sanitize_query to return warnings
                    with patch('neo4j_yass_mcp.server.sanitize_query') as mock_sanitize:
                        mock_sanitize.return_value = (
                            True,  # is_safe
                            None,  # error
                            ["Query uses complex pattern"]  # warnings
                        )

                        from neo4j_yass_mcp.server import execute_cypher

                        result = await execute_cypher("MATCH (n)-->(m) RETURN n, m")

                        # Query should succeed but log warnings
                        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
