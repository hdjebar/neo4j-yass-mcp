"""
Shared pytest fixtures for neo4j-yass-mcp tests.

This module provides common fixtures for mocking Neo4j, LangChain,
and other dependencies used throughout the test suite.
"""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_neo4j_graph():
    """Mock Neo4jGraph instance."""
    graph = Mock()
    graph.get_schema = "Node: Movie\nRelationship: ACTED_IN"
    graph.query = Mock(return_value=[{"name": "Tom Cruise", "title": "Top Gun"}])
    graph.refresh_schema = Mock()
    graph._driver = Mock()
    graph._driver.close = Mock()
    return graph


@pytest.fixture
def mock_langchain_chain():
    """Mock GraphCypherQAChain instance."""
    chain = Mock()
    chain.invoke = Mock(
        return_value={
            "result": "Tom Cruise starred in Top Gun",
            "intermediate_steps": [
                {
                    "query": "MATCH (m:Movie {title: 'Top Gun'})<-[:ACTED_IN]-(p:Person) RETURN p.name"
                }
            ],
        }
    )
    return chain


@pytest.fixture
def mock_audit_logger():
    """Mock AuditLogger instance."""
    logger = Mock()
    logger.log_query = Mock()
    logger.log_response = Mock()
    logger.log_error = Mock()
    logger.close = Mock()
    return logger


@pytest.fixture
def sample_cypher_queries():
    """Sample Cypher queries for testing."""
    return {
        "safe": [
            "MATCH (n:Person) RETURN n.name LIMIT 10",
            "MATCH (m:Movie) WHERE m.year > 2000 RETURN m.title",
            "MATCH (p:Person)-[:ACTED_IN]->(m:Movie) RETURN p.name, m.title",
        ],
        "unsafe": [
            "MATCH (n) DELETE n",
            "CREATE (n:Malicious {data: 'bad'})",
            "CALL apoc.cypher.run('MATCH (n) DELETE n', {})",
            "MATCH (n) SET n.admin = true RETURN n",
        ],
        "utf8_attacks": [
            "MATCH (n) WHERE n.name = '\u200b' RETURN n",  # Zero-width space
            "MATCH (n) WHERE n.name = 'admin\u0000' RETURN n",  # Null byte
            "MATCH (n) WHERE n.name = 'test\ufeff' RETURN n",  # BOM
        ],
        "complex": [
            "MATCH (a)-[r1]->(b)-[r2]->(c)-[r3]->(d)-[r4]->(e) RETURN *",
            "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, collect(m) AS related",
        ],
    }


@pytest.fixture
def sample_llm_configs():
    """Sample LLM configurations for testing."""
    return {
        "openai": {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.0,
            "api_key": "sk-test-key",
            "streaming": False,
        },
        "anthropic": {
            "provider": "anthropic",
            "model": "claude-3-sonnet-20240229",
            "temperature": 0.0,
            "api_key": "sk-ant-test-key",
            "streaming": False,
        },
        "google": {
            "provider": "google-genai",
            "model": "gemini-pro",
            "temperature": 0.0,
            "api_key": "test-google-key",
            "streaming": False,
        },
    }


@pytest.fixture
def mock_environment_vars(monkeypatch):
    """Mock environment variables for testing."""
    env_vars = {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "test_password",
        "NEO4J_DATABASE": "neo4j",
        "LLM_PROVIDER": "openai",
        "LLM_MODEL": "gpt-4",
        "LLM_API_KEY": "sk-test-key",
        "SANITIZER_ENABLED": "true",
        "DEBUG_MODE": "false",
        "ENVIRONMENT": "development",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


@pytest.fixture
def mock_executor():
    """Mock ThreadPoolExecutor."""
    executor = Mock()
    executor.shutdown = Mock()
    return executor


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state between tests."""
    # This fixture runs automatically before each test
    # Import here to avoid circular imports
    import neo4j_yass_mcp.server as server_module

    # Reset global variables
    original_graph = getattr(server_module, "graph", None)
    original_chain = getattr(server_module, "chain", None)
    original_executor = getattr(server_module, "_executor", None)

    yield

    # Restore original values after test
    server_module.graph = original_graph
    server_module.chain = original_chain
    server_module._executor = original_executor
    # Reset decorator-based rate limiter state
    if hasattr(server_module, "tool_rate_limiter"):
        server_module.tool_rate_limiter.reset()
