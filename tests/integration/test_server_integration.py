"""
Integration tests for Neo4j YASS MCP Server.

These tests verify the full server initialization, configuration,
and integration between components (Neo4j, LangChain, sanitizer, audit logger).
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastmcp import Context


def create_mock_context(session_id: str = "test_session_123") -> Mock:
    """Create a mock FastMCP Context for testing."""
    mock_ctx = Mock(spec=Context)
    mock_ctx.session_id = session_id
    mock_ctx.client_id = None
    return mock_ctx


class TestServerInitialization:
    """Test complete server initialization flow."""

    def test_initialize_neo4j_full_flow(self):
        """Test complete Neo4j initialization with all components."""
        # Set up a full environment with valid configuration
        env_vars = {
            "NEO4J_URI": "bolt://testhost:7687",
            "NEO4J_USERNAME": "testuser",
            "NEO4J_PASSWORD": "StrongP@ssw0rd!123",
            "NEO4J_DATABASE": "testdb",
            "NEO4J_READ_TIMEOUT": "60",
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4",
            "LLM_TEMPERATURE": "0.5",
            "LLM_API_KEY": "test-api-key-12345",
            "LLM_STREAMING": "true",
            "LANGCHAIN_ALLOW_DANGEROUS_REQUESTS": "false",
            "DEBUG_MODE": "false",
            "ENVIRONMENT": "production",
            "NEO4J_READ_ONLY": "false",
            "NEO4J_RESPONSE_TOKEN_LIMIT": "10000",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Mock Neo4j and LangChain components
            with patch("neo4j_yass_mcp.server.SecureNeo4jGraph") as mock_graph_class:
                with patch("neo4j_yass_mcp.server.chatLLM") as mock_llm_func:
                    with patch(
                        "neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"
                    ) as mock_chain_func:
                        # Set up mock returns
                        mock_graph_instance = Mock()
                        mock_graph_class.return_value = mock_graph_instance

                        mock_llm_instance = Mock()
                        mock_llm_func.return_value = mock_llm_instance

                        mock_chain_instance = Mock()
                        mock_chain_func.return_value = mock_chain_instance

                        # Import and call initialize
                        from neo4j_yass_mcp.server import initialize_neo4j

                        initialize_neo4j()

                        # Verify SecureNeo4jGraph was created with security params
                        mock_graph_class.assert_called_once_with(
                            url="bolt://testhost:7687",
                            username="testuser",
                            password="StrongP@ssw0rd!123",
                            database="testdb",
                            timeout=60,
                            sanitizer_enabled=True,
                            complexity_limit_enabled=True,
                            read_only_mode=False,
                        )

                        # Verify LLM was created
                        mock_llm_func.assert_called_once()
                        llm_config = mock_llm_func.call_args[0][0]
                        assert llm_config.provider == "openai"
                        assert llm_config.model == "gpt-4"
                        assert llm_config.temperature == 0.5
                        assert llm_config.api_key == "test-api-key-12345"
                        assert llm_config.streaming is True

                        # Verify chain was created
                        mock_chain_func.assert_called_once()
                        chain_kwargs = mock_chain_func.call_args[1]
                        assert chain_kwargs["allow_dangerous_requests"] is False
                        assert chain_kwargs["verbose"] is True
                        assert chain_kwargs["return_intermediate_steps"] is True

    def test_security_configuration_integration(self):
        """Test security features work together (password check, debug mode, read-only)."""
        env_vars = {
            "NEO4J_PASSWORD": "StrongP@ssw0rd!123",  # Strong password
            "DEBUG_MODE": "true",
            "ENVIRONMENT": "production",
            "LLM_API_KEY": "test-key",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            from neo4j_yass_mcp.server import initialize_neo4j

            # Should raise ValueError due to DEBUG_MODE in production
            with pytest.raises(ValueError, match="DEBUG_MODE=true is not allowed in production"):
                initialize_neo4j()

    def test_development_environment_allows_debug(self):
        """Test development environment allows debug mode with weak password override."""
        env_vars = {
            "NEO4J_PASSWORD": "password",
            "ALLOW_WEAK_PASSWORDS": "true",
            "DEBUG_MODE": "true",
            "ENVIRONMENT": "development",
            "LLM_API_KEY": "test-key",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("neo4j_yass_mcp.server.SecureNeo4jGraph"):
                with patch("neo4j_yass_mcp.server.chatLLM"):
                    with patch("neo4j_yass_mcp.server.GraphCypherQAChain.from_llm"):
                        from neo4j_yass_mcp.server import _debug_mode, initialize_neo4j

                        # Should succeed
                        initialize_neo4j()

                        # Verify debug mode is set
                        assert _debug_mode is True


class TestEndToEndQueryFlow:
    """Test end-to-end query execution flow with all components."""

    @pytest.mark.asyncio
    async def test_query_graph_end_to_end(self):
        """Test complete query_graph flow from input to output."""
        # Mock graph and chain
        mock_graph = Mock()
        mock_graph.get_schema = "Node: Person\nRelationship: KNOWS"

        mock_chain = Mock()
        mock_chain.invoke = Mock(
            return_value={
                "result": "John Doe is 35 years old",
                "intermediate_steps": [
                    {"query": "MATCH (p:Person {name: 'John Doe'}) RETURN p.age AS age"}
                ],
            }
        )

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.server.chain", mock_chain):
                with patch("neo4j_yass_mcp.server.sanitizer_enabled", True):
                    with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                        from neo4j_yass_mcp.server import query_graph

                        result = await query_graph.fn(
                            "How old is John Doe?", ctx=create_mock_context()
                        )

                        # Verify result structure
                        assert result["success"] is True
                        assert "John Doe is 35 years old" in result["answer"]
                        assert (
                            result["generated_cypher"]
                            == "MATCH (p:Person {name: 'John Doe'}) RETURN p.age AS age"
                        )
                        assert result["question"] == "How old is John Doe?"

                        # Verify chain was invoked with question
                        mock_chain.invoke.assert_called_once()
                        call_args = mock_chain.invoke.call_args[0][0]
                        assert "How old is John Doe?" in call_args["query"]

    @pytest.mark.asyncio
    async def test_query_graph_with_suspicious_cypher_warning(self):
        """Test query_graph logs warnings for suspicious LLM-generated Cypher (lines 552-553)."""
        # Mock graph and chain
        mock_graph = Mock()
        mock_graph.get_schema = "Node: Person\nRelationship: KNOWS"

        # Mock chain to return Cypher with CALL apoc (triggers SUSPICIOUS_PATTERNS)
        mock_chain = Mock()
        mock_chain.invoke = Mock(
            return_value={
                "result": "Database info retrieved",
                "intermediate_steps": [
                    {"query": "CALL apoc.help('count')"}  # Triggers warning
                ],
            }
        )

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.server.chain", mock_chain):
                with patch("neo4j_yass_mcp.server.sanitizer_enabled", True):
                    with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                        from neo4j_yass_mcp.server import query_graph

                        result = await query_graph.fn(
                            "Show me the apoc count function", ctx=create_mock_context()
                        )

                        # Should succeed but with warnings logged
                        assert result["success"] is True
                        assert "CALL apoc.help('count')" in result["generated_cypher"]

    @pytest.mark.asyncio
    async def test_execute_cypher_end_to_end(self):
        """Test complete execute_cypher flow with sanitizer and audit."""
        mock_graph = Mock()
        mock_graph.query = Mock(
            return_value=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        )

        mock_audit_logger = Mock()
        mock_audit_logger.log_query = Mock()
        mock_audit_logger.log_response = Mock()

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.server.sanitizer_enabled", True):
                with patch(
                    "neo4j_yass_mcp.server.get_audit_logger", return_value=mock_audit_logger
                ):
                    from neo4j_yass_mcp.server import execute_cypher

                    query = "MATCH (p:Person) RETURN p.name AS name, p.age AS age"
                    result = await execute_cypher.fn(query, ctx=create_mock_context())

                    # Verify successful execution
                    assert result["success"] is True
                    assert len(result["result"]) == 2
                    assert result["query"] == query

                    # Verify audit logging
                    mock_audit_logger.log_query.assert_called_once()
                    mock_audit_logger.log_response.assert_called_once()

                    # Verify graph was queried
                    mock_graph.query.assert_called_once_with(query, params={})

    @pytest.mark.asyncio
    async def test_sanitizer_blocks_unsafe_query_end_to_end(self):
        """Test sanitizer integration blocks unsafe queries."""
        mock_graph = Mock()

        mock_audit_logger = Mock()
        mock_audit_logger.log_error = Mock()

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.server.sanitizer_enabled", True):
                with patch(
                    "neo4j_yass_mcp.server.get_audit_logger", return_value=mock_audit_logger
                ):
                    from neo4j_yass_mcp.server import execute_cypher

                    # Attempt unsafe query
                    unsafe_query = "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line"
                    result = await execute_cypher.fn(unsafe_query, ctx=create_mock_context())

                    # Verify query was blocked
                    assert result["success"] is False
                    assert (
                        "blocked" in result["error"].lower()
                        or "dangerous" in result["error"].lower()
                    )

                    # Verify audit logger recorded the block
                    mock_audit_logger.log_error.assert_called_once()

                    # Verify graph was never queried
                    mock_graph.query.assert_not_called()


class TestReadOnlyModeIntegration:
    """Test read-only mode across all tools."""

    @pytest.mark.asyncio
    async def test_read_only_blocks_write_queries(self):
        """Test read-only mode blocks write queries in execute_cypher."""
        mock_graph = Mock()
        mock_audit_logger = Mock()

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.server._read_only_mode", True):
                with patch(
                    "neo4j_yass_mcp.server.get_audit_logger", return_value=mock_audit_logger
                ):
                    from neo4j_yass_mcp.server import execute_cypher

                    write_queries = [
                        "CREATE (n:Person {name: 'Test'})",
                        "MERGE (n:Node)",
                        "DELETE n",
                        "SET n.prop = 'value'",
                        "REMOVE n.prop",
                    ]

                    for query in write_queries:
                        result = await execute_cypher.fn(query, ctx=create_mock_context())

                        # Check for error (read-only mode returns {"error": msg})
                        assert "error" in result
                        assert "read-only" in result["error"].lower()
                        mock_graph.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_read_only_allows_read_queries(self):
        """Test read-only mode allows read queries."""
        mock_graph = Mock()
        mock_graph.query = Mock(return_value=[{"n": "data"}])

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.server._read_only_mode", True):
                with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                    from neo4j_yass_mcp.server import execute_cypher

                    read_queries = [
                        "MATCH (n) RETURN n",
                        "MATCH (p:Person) WHERE p.age > 30 RETURN p",
                        "CALL db.labels()",
                    ]

                    for query in read_queries:
                        result = await execute_cypher.fn(query, ctx=create_mock_context())

                        assert result["success"] is True
                        mock_graph.query.assert_called()


class TestResponseTruncationIntegration:
    """Test response truncation with large results."""

    @pytest.mark.asyncio
    async def test_large_result_truncation(self):
        """Test execute_cypher truncates large results."""
        # Generate large result set
        large_result = [{"id": i, "data": "x" * 1000} for i in range(10000)]

        mock_graph = Mock()
        mock_graph.query = Mock(return_value=large_result)

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.server._response_token_limit", 1000):
                with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                    from neo4j_yass_mcp.server import execute_cypher

                    result = await execute_cypher.fn(
                        "MATCH (n) RETURN n", ctx=create_mock_context()
                    )

                    # Verify truncation
                    assert result["success"] is True
                    assert result.get("truncated") is True
                    assert result["original_count"] == 10000
                    assert result["returned_count"] < 10000


class TestCleanupIntegration:
    """Test cleanup function integration."""

    def test_cleanup_all_resources(self):
        """Test cleanup properly cleans all resources."""
        # Create mock executor and graph
        mock_executor = Mock()
        mock_executor.shutdown = Mock()

        mock_driver = Mock()
        mock_driver.close = Mock()

        mock_graph = Mock()
        mock_graph._driver = mock_driver

        with patch("neo4j_yass_mcp.server._executor", mock_executor):
            with patch("neo4j_yass_mcp.server.graph", mock_graph):
                from neo4j_yass_mcp.server import cleanup

                cleanup()

                # Verify both cleanup operations
                mock_executor.shutdown.assert_called_once_with(wait=True)
                mock_driver.close.assert_called_once()

    def test_cleanup_handles_partial_initialization(self):
        """Test cleanup handles partially initialized state."""
        # Only executor exists, no graph
        mock_executor = Mock()
        mock_executor.shutdown = Mock()

        with patch("neo4j_yass_mcp.server._executor", mock_executor):
            with patch("neo4j_yass_mcp.server.graph", None):
                from neo4j_yass_mcp.server import cleanup

                # Should not raise error
                cleanup()

                # Executor should still be cleaned
                mock_executor.shutdown.assert_called_once()


class TestAuditLoggerIntegration:
    """Test audit logger integration across all tools."""

    @pytest.mark.asyncio
    async def test_audit_logger_full_lifecycle(self):
        """Test audit logger captures complete query lifecycle."""
        import shutil
        import tempfile

        # Create temporary audit log directory
        temp_dir = tempfile.mkdtemp()

        try:
            # Initialize audit logger with temp directory
            with patch.dict(
                os.environ,
                {
                    "AUDIT_LOG_ENABLED": "true",
                    "AUDIT_LOG_DIR": temp_dir,
                    "AUDIT_LOG_ROTATION": "daily",
                },
            ):
                # Re-initialize audit logger
                from neo4j_yass_mcp.security import get_audit_logger, initialize_audit_logger

                initialize_audit_logger()
                audit_logger = get_audit_logger()

                # Mock graph
                mock_graph = Mock()
                mock_graph.query = Mock(return_value=[{"result": "data"}])

                with patch("neo4j_yass_mcp.server.graph", mock_graph):
                    from neo4j_yass_mcp.server import execute_cypher

                    # Execute query
                    query = "MATCH (n:Test) RETURN n"
                    result = await execute_cypher.fn(query, ctx=create_mock_context())

                    assert result["success"] is True

                # Verify log file was created
                log_files = list(Path(temp_dir).glob("*.log"))
                assert len(log_files) > 0

                # Verify log content (if audit logger was enabled)
                if audit_logger and audit_logger.enabled:
                    log_file = log_files[0]
                    content = log_file.read_text()
                    assert len(content) > 0

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
