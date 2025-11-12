"""
Tests for config.runtime_config module.

Tests centralized configuration loading from environment variables
with Pydantic validation and type safety.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from neo4j_yass_mcp.config.runtime_config import (
    ComplexityLimiterConfig,
    EnvironmentConfig,
    LLMConfig,
    Neo4jConfig,
    RateLimiterConfig,
    ResourceRateLimitConfig,
    RuntimeConfig,
    SanitizerConfig,
    ServerConfig,
    ToolRateLimitConfig,
)


class TestNeo4jConfig:
    """Test Neo4j configuration."""

    def test_defaults(self):
        """Test default values."""
        config = Neo4jConfig()
        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.password == "password"
        assert config.database == "neo4j"
        assert config.read_timeout == 30
        assert config.read_only is False
        assert config.response_token_limit is None
        assert config.allow_dangerous_requests is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = Neo4jConfig(
            uri="bolt://prod:7687",
            username="admin",
            password="secure123",
            database="proddb",
            read_timeout=60,
            read_only=True,
            response_token_limit=1000,
            allow_dangerous_requests=True,
        )
        assert config.uri == "bolt://prod:7687"
        assert config.username == "admin"
        assert config.password == "secure123"
        assert config.database == "proddb"
        assert config.read_timeout == 60
        assert config.read_only is True
        assert config.response_token_limit == 1000
        assert config.allow_dangerous_requests is True

    def test_read_timeout_validation(self):
        """Test read_timeout must be >= 1."""
        with pytest.raises(ValidationError):
            Neo4jConfig(read_timeout=0)

        with pytest.raises(ValidationError):
            Neo4jConfig(read_timeout=-1)

    def test_response_token_limit_validation(self):
        """Test response_token_limit must be >= 1 or None."""
        config = Neo4jConfig(response_token_limit=None)
        assert config.response_token_limit is None

        config = Neo4jConfig(response_token_limit=100)
        assert config.response_token_limit == 100

        with pytest.raises(ValidationError):
            Neo4jConfig(response_token_limit=0)


class TestSanitizerConfig:
    """Test sanitizer configuration."""

    def test_defaults(self):
        """Test default values."""
        config = SanitizerConfig()
        assert config.enabled is True
        assert config.strict_mode is False
        assert config.allow_apoc is False
        assert config.allow_schema_changes is False
        assert config.block_non_ascii is False
        assert config.max_query_length == 10000

    def test_max_query_length_validation(self):
        """Test max_query_length must be >= 1."""
        with pytest.raises(ValidationError):
            SanitizerConfig(max_query_length=0)


class TestComplexityLimiterConfig:
    """Test complexity limiter configuration."""

    def test_defaults(self):
        """Test default values."""
        config = ComplexityLimiterConfig()
        assert config.enabled is True
        assert config.max_complexity == 100
        assert config.max_variable_path_length == 10
        assert config.require_limit_unbounded is True

    def test_validation(self):
        """Test field validation."""
        with pytest.raises(ValidationError):
            ComplexityLimiterConfig(max_complexity=0)

        with pytest.raises(ValidationError):
            ComplexityLimiterConfig(max_variable_path_length=0)


class TestRateLimiterConfig:
    """Test rate limiter configuration."""

    def test_defaults(self):
        """Test default values."""
        config = RateLimiterConfig()
        assert config.enabled is True
        assert config.rate == 10
        assert config.per_seconds == 60
        assert config.burst is None

    def test_burst_optional(self):
        """Test burst is optional."""
        config = RateLimiterConfig(burst=None)
        assert config.burst is None

        config = RateLimiterConfig(burst=20)
        assert config.burst == 20


class TestToolRateLimitConfig:
    """Test tool rate limit configuration."""

    def test_defaults(self):
        """Test default values."""
        config = ToolRateLimitConfig()
        assert config.enabled is True
        assert config.query_graph_limit == 10
        assert config.query_graph_window == 60
        assert config.execute_cypher_limit == 10
        assert config.execute_cypher_window == 60
        assert config.refresh_schema_limit == 5
        assert config.refresh_schema_window == 120
        assert config.analyze_query_limit == 15
        assert config.analyze_query_window == 60


class TestResourceRateLimitConfig:
    """Test resource rate limit configuration."""

    def test_defaults(self):
        """Test default values."""
        config = ResourceRateLimitConfig()
        assert config.enabled is True
        assert config.limit == 20
        assert config.window == 60


class TestLLMConfig:
    """Test LLM configuration."""

    def test_defaults(self):
        """Test default values."""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.0
        assert config.api_key == ""
        assert config.streaming is False

    def test_temperature_validation(self):
        """Test temperature must be between 0 and 2."""
        config = LLMConfig(temperature=0.0)
        assert config.temperature == 0.0

        config = LLMConfig(temperature=2.0)
        assert config.temperature == 2.0

        with pytest.raises(ValidationError):
            LLMConfig(temperature=-0.1)

        with pytest.raises(ValidationError):
            LLMConfig(temperature=2.1)


class TestServerConfig:
    """Test server configuration."""

    def test_defaults(self):
        """Test default values."""
        config = ServerConfig()
        assert config.transport == "stdio"
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.path == "/mcp/"
        assert config.max_workers == 10

    def test_port_validation(self):
        """Test port must be between 1 and 65535."""
        config = ServerConfig(port=1)
        assert config.port == 1

        config = ServerConfig(port=65535)
        assert config.port == 65535

        with pytest.raises(ValidationError):
            ServerConfig(port=0)

        with pytest.raises(ValidationError):
            ServerConfig(port=65536)

    def test_transport_validation(self):
        """Test transport must be stdio or sse."""
        config = ServerConfig(transport="stdio")
        assert config.transport == "stdio"

        config = ServerConfig(transport="sse")
        assert config.transport == "sse"

        with pytest.raises(ValidationError):
            ServerConfig(transport="invalid")


class TestEnvironmentConfig:
    """Test environment configuration."""

    def test_defaults(self):
        """Test default values."""
        config = EnvironmentConfig()
        assert config.environment == "development"
        assert config.debug_mode is False
        assert config.allow_weak_passwords is False

    def test_weak_passwords_validation(self):
        """Test weak passwords not allowed in production."""
        # Should work in development
        config = EnvironmentConfig(
            environment="development",
            allow_weak_passwords=True,
        )
        assert config.allow_weak_passwords is True

        # Should fail in production
        with pytest.raises(ValidationError, match="Weak passwords not allowed in production"):
            EnvironmentConfig(
                environment="production",
                allow_weak_passwords=True,
            )


class TestRuntimeConfig:
    """Test complete runtime configuration."""

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_defaults(self):
        """Test from_env with no environment variables uses defaults."""
        config = RuntimeConfig.from_env()

        # Neo4j defaults
        assert config.neo4j.uri == "bolt://localhost:7687"
        assert config.neo4j.username == "neo4j"
        assert config.neo4j.password == "password"
        assert config.neo4j.database == "neo4j"

        # Sanitizer defaults
        assert config.sanitizer.enabled is True
        assert config.sanitizer.max_query_length == 10000

        # Complexity limiter defaults
        assert config.complexity_limiter.enabled is True
        assert config.complexity_limiter.max_complexity == 100

        # Rate limiter defaults
        assert config.rate_limiter.enabled is True
        assert config.rate_limiter.rate == 10

        # Tool rate limit defaults
        assert config.tool_rate_limit.enabled is True
        assert config.tool_rate_limit.query_graph_limit == 10

        # LLM defaults
        assert config.llm.provider == "openai"
        assert config.llm.model == "gpt-4"

        # Server defaults
        assert config.server.transport == "stdio"
        assert config.server.port == 8000

        # Environment defaults
        assert config.environment.environment == "development"
        assert config.environment.debug_mode is False

    @patch.dict(
        os.environ,
        {
            "NEO4J_URI": "bolt://prod:7687",
            "NEO4J_USERNAME": "admin",
            "NEO4J_PASSWORD": "secure123",
            "NEO4J_DATABASE": "proddb",
            "NEO4J_READ_TIMEOUT": "60",
            "NEO4J_READ_ONLY": "true",
            "NEO4J_RESPONSE_TOKEN_LIMIT": "2000",
            "LANGCHAIN_ALLOW_DANGEROUS_REQUESTS": "true",
            "SANITIZER_ENABLED": "false",
            "SANITIZER_STRICT_MODE": "true",
            "SANITIZER_MAX_QUERY_LENGTH": "5000",
            "COMPLEXITY_LIMIT_ENABLED": "false",
            "MAX_QUERY_COMPLEXITY": "200",
            "RATE_LIMIT_ENABLED": "false",
            "RATE_LIMIT_REQUESTS": "20",
            "RATE_LIMIT_BURST": "30",
            "MCP_TOOL_RATE_LIMIT_ENABLED": "false",
            "MCP_QUERY_GRAPH_LIMIT": "20",
            "LLM_PROVIDER": "anthropic",
            "LLM_MODEL": "claude-3-opus",
            "LLM_TEMPERATURE": "0.7",
            "LLM_API_KEY": "sk-test-key",
            "LLM_STREAMING": "true",
            "MCP_TRANSPORT": "sse",
            "MCP_SERVER_HOST": "0.0.0.0",
            "MCP_SERVER_PORT": "9000",
            "ENVIRONMENT": "production",
            "DEBUG_MODE": "true",
        },
        clear=True,
    )
    def test_from_env_custom_values(self):
        """Test from_env with custom environment variables."""
        config = RuntimeConfig.from_env()

        # Neo4j custom values
        assert config.neo4j.uri == "bolt://prod:7687"
        assert config.neo4j.username == "admin"
        assert config.neo4j.password == "secure123"
        assert config.neo4j.database == "proddb"
        assert config.neo4j.read_timeout == 60
        assert config.neo4j.read_only is True
        assert config.neo4j.response_token_limit == 2000
        assert config.neo4j.allow_dangerous_requests is True

        # Sanitizer custom values
        assert config.sanitizer.enabled is False
        assert config.sanitizer.strict_mode is True
        assert config.sanitizer.max_query_length == 5000

        # Complexity limiter custom values
        assert config.complexity_limiter.enabled is False
        assert config.complexity_limiter.max_complexity == 200

        # Rate limiter custom values
        assert config.rate_limiter.enabled is False
        assert config.rate_limiter.rate == 20
        assert config.rate_limiter.burst == 30

        # Tool rate limit custom values
        assert config.tool_rate_limit.enabled is False
        assert config.tool_rate_limit.query_graph_limit == 20

        # LLM custom values
        assert config.llm.provider == "anthropic"
        assert config.llm.model == "claude-3-opus"
        assert config.llm.temperature == 0.7
        assert config.llm.api_key == "sk-test-key"
        assert config.llm.streaming is True

        # Server custom values
        assert config.server.transport == "sse"
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 9000

        # Environment custom values
        assert config.environment.environment == "production"
        assert config.environment.debug_mode is True

    @patch.dict(os.environ, {}, clear=True)
    def test_model_dump_safe(self):
        """Test model_dump_safe redacts sensitive fields."""
        config = RuntimeConfig.from_env()
        safe_dict = config.model_dump_safe()

        # Password should be redacted
        assert safe_dict["neo4j"]["password"] == "***REDACTED***"

        # Non-sensitive fields should be present
        assert safe_dict["neo4j"]["username"] == "neo4j"
        assert safe_dict["neo4j"]["uri"] == "bolt://localhost:7687"

    @patch.dict(
        os.environ,
        {"LLM_API_KEY": "sk-super-secret"},
        clear=True,
    )
    def test_model_dump_safe_api_key(self):
        """Test model_dump_safe redacts API keys."""
        config = RuntimeConfig.from_env()
        safe_dict = config.model_dump_safe()

        # API key should be redacted
        assert safe_dict["llm"]["api_key"] == "***REDACTED***"

        # Non-sensitive LLM fields should be present
        assert safe_dict["llm"]["provider"] == "openai"
        assert safe_dict["llm"]["model"] == "gpt-4"

    @patch.dict(
        os.environ,
        {"RATE_LIMIT_BURST": ""},
        clear=True,
    )
    def test_burst_empty_string(self):
        """Test burst with empty string becomes None."""
        config = RuntimeConfig.from_env()
        assert config.rate_limiter.burst is None

    @patch.dict(
        os.environ,
        {"NEO4J_RESPONSE_TOKEN_LIMIT": ""},
        clear=True,
    )
    def test_token_limit_empty_string(self):
        """Test response_token_limit with empty string becomes None."""
        config = RuntimeConfig.from_env()
        assert config.neo4j.response_token_limit is None

    @patch.dict(
        os.environ,
        {
            "SANITIZER_ENABLED": "TRUE",
            "NEO4J_READ_ONLY": "TRUE",
            "RATE_LIMIT_ENABLED": "TRUE",
        },
        clear=True,
    )
    def test_case_insensitive_booleans(self):
        """Test boolean parsing is case insensitive."""
        config = RuntimeConfig.from_env()
        assert config.sanitizer.enabled is True
        assert config.neo4j.read_only is True
        assert config.rate_limiter.enabled is True

    @patch.dict(
        os.environ,
        {
            "SANITIZER_ENABLED": "yes",
            "NEO4J_READ_ONLY": "1",
            "RATE_LIMIT_ENABLED": "false",
        },
        clear=True,
    )
    def test_boolean_edge_cases(self):
        """Test boolean parsing edge cases."""
        config = RuntimeConfig.from_env()
        # Only "true" (case insensitive) should parse as True
        assert config.sanitizer.enabled is False  # "yes" != "true"
        assert config.neo4j.read_only is False  # "1" != "true"
        assert config.rate_limiter.enabled is False  # "false" != "true"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
