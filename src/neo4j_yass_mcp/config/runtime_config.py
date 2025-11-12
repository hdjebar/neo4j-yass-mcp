"""
Runtime Configuration for Neo4j YASS MCP Server.

This module centralizes all runtime configuration from environment variables
using Pydantic for validation, type safety, and clear defaults.

Extracted from server.py to eliminate scattered configuration and improve
maintainability (ARCHITECTURE_REFACTORING_PLAN.md Issue #3).
"""

import os
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Neo4jConfig(BaseModel):
    """Neo4j database connection configuration."""

    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI",
    )
    username: str = Field(
        default="neo4j",
        description="Neo4j authentication username",
    )
    password: str = Field(
        default="password",
        description="Neo4j authentication password",
    )
    database: str = Field(
        default="neo4j",
        description="Neo4j database name",
    )
    read_timeout: int = Field(
        default=30,
        ge=1,
        description="Neo4j read timeout in seconds",
    )
    read_only: bool = Field(
        default=False,
        description="Enable read-only mode (blocks write operations)",
    )
    response_token_limit: int | None = Field(
        default=None,
        ge=1,
        description="Maximum tokens in response (None = unlimited)",
    )
    allow_dangerous_requests: bool = Field(
        default=False,
        description="Allow LangChain dangerous requests flag",
    )


class SanitizerConfig(BaseModel):
    """Query sanitizer configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable query sanitization",
    )
    strict_mode: bool = Field(
        default=False,
        description="Enable strict sanitization mode",
    )
    allow_apoc: bool = Field(
        default=False,
        description="Allow APOC procedures",
    )
    allow_schema_changes: bool = Field(
        default=False,
        description="Allow schema modification operations",
    )
    block_non_ascii: bool = Field(
        default=False,
        description="Block non-ASCII characters in queries",
    )
    max_query_length: int = Field(
        default=10000,
        ge=1,
        description="Maximum query length in characters",
    )


class ComplexityLimiterConfig(BaseModel):
    """Query complexity limiter configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable complexity limiting",
    )
    max_complexity: int = Field(
        default=100,
        ge=1,
        description="Maximum query complexity score",
    )
    max_variable_path_length: int = Field(
        default=10,
        ge=1,
        description="Maximum variable-length path depth",
    )
    require_limit_unbounded: bool = Field(
        default=True,
        description="Require LIMIT clause for unbounded queries",
    )


class RateLimiterConfig(BaseModel):
    """Global rate limiter configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable rate limiting",
    )
    rate: int = Field(
        default=10,
        ge=1,
        description="Number of requests allowed",
    )
    per_seconds: int = Field(
        default=60,
        ge=1,
        description="Time window in seconds",
    )
    burst: int | None = Field(
        default=None,
        ge=1,
        description="Burst capacity (None = no burst)",
    )


class ToolRateLimitConfig(BaseModel):
    """MCP tool-specific rate limiting configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable tool-level rate limiting",
    )
    query_graph_limit: int = Field(
        default=10,
        ge=1,
        description="query_graph tool rate limit",
    )
    query_graph_window: int = Field(
        default=60,
        ge=1,
        description="query_graph window in seconds",
    )
    execute_cypher_limit: int = Field(
        default=10,
        ge=1,
        description="execute_cypher tool rate limit",
    )
    execute_cypher_window: int = Field(
        default=60,
        ge=1,
        description="execute_cypher window in seconds",
    )
    refresh_schema_limit: int = Field(
        default=5,
        ge=1,
        description="refresh_schema tool rate limit",
    )
    refresh_schema_window: int = Field(
        default=120,
        ge=1,
        description="refresh_schema window in seconds",
    )
    analyze_query_limit: int = Field(
        default=15,
        ge=1,
        description="analyze_query tool rate limit",
    )
    analyze_query_window: int = Field(
        default=60,
        ge=1,
        description="analyze_query window in seconds",
    )


class ResourceRateLimitConfig(BaseModel):
    """MCP resource rate limiting configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable resource-level rate limiting",
    )
    limit: int = Field(
        default=20,
        ge=1,
        description="Resource access rate limit",
    )
    window: int = Field(
        default=60,
        ge=1,
        description="Rate limit window in seconds",
    )


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = Field(
        default="openai",
        description="LLM provider name (openai, anthropic, google)",
    )
    model: str = Field(
        default="gpt-4",
        description="LLM model name",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="LLM temperature setting",
    )
    api_key: str = Field(
        default="",
        description="LLM provider API key",
    )
    streaming: bool = Field(
        default=False,
        description="Enable streaming responses",
    )


class ServerConfig(BaseModel):
    """MCP server transport and network configuration."""

    transport: Literal["stdio", "sse"] = Field(
        default="stdio",
        description="MCP transport protocol",
    )
    host: str = Field(
        default="127.0.0.1",
        description="Server host address (SSE mode)",
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Server port (SSE mode)",
    )
    path: str = Field(
        default="/mcp/",
        description="Server path (SSE mode)",
    )
    max_workers: int = Field(
        default=10,
        ge=1,
        description="Maximum async worker threads",
    )


class EnvironmentConfig(BaseModel):
    """Environment and operational configuration."""

    environment: Literal["development", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    allow_weak_passwords: bool = Field(
        default=False,
        description="Allow weak passwords (dev only)",
    )

    @field_validator("allow_weak_passwords")
    @classmethod
    def validate_weak_passwords(cls, v: bool, info) -> bool:
        """Ensure weak passwords only allowed in development."""
        if v and info.data.get("environment") == "production":
            raise ValueError("Weak passwords not allowed in production")
        return v


class RuntimeConfig(BaseModel):
    """
    Complete runtime configuration for Neo4j YASS MCP Server.

    This class centralizes all configuration from environment variables,
    providing type safety, validation, and clear defaults.

    Example:
        >>> config = RuntimeConfig.from_env()
        >>> print(config.neo4j.uri)
        'bolt://localhost:7687'
    """

    neo4j: Neo4jConfig
    sanitizer: SanitizerConfig
    complexity_limiter: ComplexityLimiterConfig
    rate_limiter: RateLimiterConfig
    tool_rate_limit: ToolRateLimitConfig
    resource_rate_limit: ResourceRateLimitConfig
    llm: LLMConfig
    server: ServerConfig
    environment: EnvironmentConfig

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        """
        Create RuntimeConfig from environment variables.

        This method reads all configuration from environment variables,
        providing sensible defaults for missing values.

        Returns:
            RuntimeConfig instance with values from environment

        Example:
            >>> config = RuntimeConfig.from_env()
            >>> config.neo4j.uri
            'bolt://localhost:7687'
        """
        return cls(
            neo4j=Neo4jConfig(
                uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                username=os.getenv("NEO4J_USERNAME", "neo4j"),
                password=os.getenv("NEO4J_PASSWORD", "password"),
                database=os.getenv("NEO4J_DATABASE", "neo4j"),
                read_timeout=int(os.getenv("NEO4J_READ_TIMEOUT", "30")),
                read_only=os.getenv("NEO4J_READ_ONLY", "false").lower() == "true",
                response_token_limit=(
                    int(token_limit)
                    if (token_limit := os.getenv("NEO4J_RESPONSE_TOKEN_LIMIT"))
                    else None
                ),
                allow_dangerous_requests=(
                    os.getenv("LANGCHAIN_ALLOW_DANGEROUS_REQUESTS", "false").lower() == "true"
                ),
            ),
            sanitizer=SanitizerConfig(
                enabled=os.getenv("SANITIZER_ENABLED", "true").lower() == "true",
                strict_mode=os.getenv("SANITIZER_STRICT_MODE", "false").lower() == "true",
                allow_apoc=os.getenv("SANITIZER_ALLOW_APOC", "false").lower() == "true",
                allow_schema_changes=(
                    os.getenv("SANITIZER_ALLOW_SCHEMA_CHANGES", "false").lower() == "true"
                ),
                block_non_ascii=os.getenv("SANITIZER_BLOCK_NON_ASCII", "false").lower() == "true",
                max_query_length=int(os.getenv("SANITIZER_MAX_QUERY_LENGTH", "10000")),
            ),
            complexity_limiter=ComplexityLimiterConfig(
                enabled=os.getenv("COMPLEXITY_LIMIT_ENABLED", "true").lower() == "true",
                max_complexity=int(os.getenv("MAX_QUERY_COMPLEXITY", "100")),
                max_variable_path_length=int(os.getenv("MAX_VARIABLE_PATH_LENGTH", "10")),
                require_limit_unbounded=(
                    os.getenv("REQUIRE_LIMIT_UNBOUNDED", "true").lower() == "true"
                ),
            ),
            rate_limiter=RateLimiterConfig(
                enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
                rate=int(os.getenv("RATE_LIMIT_REQUESTS", "10")),
                per_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
                burst=(
                    int(burst) if (burst := os.getenv("RATE_LIMIT_BURST")) else None
                ),
            ),
            tool_rate_limit=ToolRateLimitConfig(
                enabled=os.getenv("MCP_TOOL_RATE_LIMIT_ENABLED", "true").lower() == "true",
                query_graph_limit=int(os.getenv("MCP_QUERY_GRAPH_LIMIT", "10")),
                query_graph_window=int(os.getenv("MCP_QUERY_GRAPH_WINDOW", "60")),
                execute_cypher_limit=int(os.getenv("MCP_EXECUTE_CYPHER_LIMIT", "10")),
                execute_cypher_window=int(os.getenv("MCP_EXECUTE_CYPHER_WINDOW", "60")),
                refresh_schema_limit=int(os.getenv("MCP_REFRESH_SCHEMA_LIMIT", "5")),
                refresh_schema_window=int(os.getenv("MCP_REFRESH_SCHEMA_WINDOW", "120")),
                analyze_query_limit=int(os.getenv("MCP_ANALYZE_QUERY_LIMIT", "15")),
                analyze_query_window=int(os.getenv("MCP_ANALYZE_QUERY_WINDOW", "60")),
            ),
            resource_rate_limit=ResourceRateLimitConfig(
                enabled=os.getenv("MCP_RESOURCE_RATE_LIMIT_ENABLED", "true").lower() == "true",
                limit=int(os.getenv("MCP_RESOURCE_LIMIT", "20")),
                window=int(os.getenv("MCP_RESOURCE_WINDOW", "60")),
            ),
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "openai"),
                model=os.getenv("LLM_MODEL", "gpt-4"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
                api_key=os.getenv("LLM_API_KEY", ""),
                streaming=os.getenv("LLM_STREAMING", "false").lower() == "true",
            ),
            server=ServerConfig(
                transport=os.getenv("MCP_TRANSPORT", "stdio").lower(),  # type: ignore[arg-type]
                host=os.getenv("MCP_SERVER_HOST", "127.0.0.1"),
                port=int(os.getenv("MCP_SERVER_PORT", "8000")),
                path=os.getenv("MCP_SERVER_PATH", "/mcp/"),
                max_workers=int(os.getenv("MCP_MAX_WORKERS", "10")),
            ),
            environment=EnvironmentConfig(
                environment=os.getenv("ENVIRONMENT", "development").lower(),  # type: ignore[arg-type]
                debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
                allow_weak_passwords=os.getenv("ALLOW_WEAK_PASSWORDS", "false").lower() == "true",
            ),
        )

    def model_dump_safe(self) -> dict:
        """
        Dump configuration to dictionary with sensitive fields redacted.

        Returns:
            Dictionary with API keys and passwords masked

        Example:
            >>> config = RuntimeConfig.from_env()
            >>> safe_dict = config.model_dump_safe()
            >>> safe_dict['neo4j']['password']
            '***REDACTED***'
        """
        data = self.model_dump()

        # Redact sensitive fields
        if "neo4j" in data:
            data["neo4j"]["password"] = "***REDACTED***"
        if "llm" in data and data["llm"].get("api_key"):
            data["llm"]["api_key"] = "***REDACTED***"

        return data
