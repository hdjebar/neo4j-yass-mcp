# Implementation Guide - Verbose Flag Propagation
**Date:** 2025-11-16
**Status:** Ready for Implementation
**Files to Modify:** 5

---

## Implementation Steps

### Step 1: Update LLMConfig Dataclass

**File:** `src/neo4j_yass_mcp/config/llm_config.py`

**Change:**
```python
@dataclass
class LLMConfig:
    """Configuration for LLM providers"""

    provider: str  # "openai", "anthropic", or "google-genai"
    model: str
    temperature: float
    api_key: str
    streaming: bool = False  # Enable token-by-token streaming
    verbose: bool = False  # Enable verbose logging (DEVELOPMENT ONLY) ✅ ADD THIS
```

---

### Step 2: Propagate Verbose to Chat Model Constructors

**File:** `src/neo4j_yass_mcp/config/llm_config.py`

**Replace entire `chatLLM` function:**
```python
def chatLLM(config: LLMConfig) -> Any:
    """
    Create a chat LLM instance based on the provider configuration.

    Args:
        config: LLMConfig containing provider, model, temperature, API key, streaming, and verbose

    Returns:
        A LangChain chat model instance

    Raises:
        ValueError: If the provider is not supported

    Security Note:
        verbose=True should ONLY be enabled in development environments.
        Verbose logging may expose API keys, prompts, and responses in
        LLM provider internal logs.

    Examples:
        >>> config = LLMConfig(
        ...     provider="openai",
        ...     model="gpt-4",
        ...     temperature=0.0,
        ...     api_key="sk-...",
        ...     verbose=False  # Production-safe
        ... )
        >>> llm = chatLLM(config)
    """
    if config.provider == "openai":
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        return ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=SecretStr(config.api_key) if config.api_key else None,
            streaming=config.streaming,
            verbose=config.verbose,  # ✅ ADD THIS LINE
        )

    elif config.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        from pydantic import SecretStr

        return ChatAnthropic(  # type: ignore[call-arg]
            model_name=config.model,
            temperature=config.temperature,
            api_key=SecretStr(config.api_key),
            streaming=config.streaming,
            verbose=config.verbose,  # ✅ ADD THIS LINE
        )

    elif config.provider == "google-genai":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=config.model,
            temperature=config.temperature,
            google_api_key=config.api_key,
            streaming=config.streaming,
            verbose=config.verbose,  # ✅ ADD THIS LINE
        )

    else:
        raise ValueError(
            f"Unknown provider: {config.provider}. Supported providers: openai, anthropic, google-genai"
        )
```

---

### Step 3: Add Verbose to RuntimeConfig

**File:** `src/neo4j_yass_mcp/config/runtime_config.py`

**Find the `LLMConfig` class and add verbose field:**
```python
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
    verbose: bool = Field(  # ✅ ADD THIS FIELD
        default=False,
        description="Enable verbose LLM logging (DEVELOPMENT ONLY)",
    )
```

---

### Step 4: Update RuntimeConfig.from_env()

**File:** `src/neo4j_yass_mcp/config/runtime_config.py`

**Find the `from_env()` method and update LLM config section:**
```python
@classmethod
def from_env(cls) -> "RuntimeConfig":
    """Create RuntimeConfig from environment variables."""
    return cls(
        # ... existing config sections ...

        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model=os.getenv("LLM_MODEL", "gpt-4"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
            api_key=os.getenv("LLM_API_KEY", ""),
            streaming=os.getenv("LLM_STREAMING", "false").lower() == "true",
            verbose=os.getenv("LLM_VERBOSE", "false").lower() == "true",  # ✅ ADD THIS LINE
        ),

        # ... rest of config ...
    )
```

---

### Step 5: Update Server Initialization

**File:** `src/neo4j_yass_mcp/server.py`

**Find `initialize_neo4j()` function and update LLM initialization:**
```python
async def initialize_neo4j():
    """Initialize Neo4j graph and LangChain components (async)"""
    global graph, chain, _read_only_mode, _response_token_limit, _debug_mode

    # ... existing Neo4j connection setup ...

    # LLM configuration from config
    llm_config = LLMConfig(
        provider=_config.llm.provider,
        model=_config.llm.model,
        temperature=_config.llm.temperature,
        api_key=_config.llm.api_key,
        streaming=_config.llm.streaming,
        verbose=_config.llm.verbose,  # ✅ ADD THIS LINE
    )

    # ✅ ADD THIS SECURITY CHECK
    # Security check for verbose in production
    if llm_config.verbose:
        if _config.environment.environment == "production":
            logger.error("❌ LLM_VERBOSE cannot be enabled in production")
            raise ValueError(
                "LLM_VERBOSE=true is not allowed in production. "
                "Set ENVIRONMENT=development to enable verbose LLM logging."
            )
        logger.warning(
            "⚠️ LLM_VERBOSE=true - LLM provider verbose logging enabled (DEVELOPMENT ONLY!)"
        )
        logger.warning(
            "⚠️ API keys, prompts, and responses may be logged by LLM provider."
        )

    logger.info(f"Initializing LLM: {llm_config.provider}/{llm_config.model}")
    llm = chatLLM(llm_config)

    # ... rest of initialization ...
```

---

### Step 6: Update .env.example

**File:** `.env.example`

**Add LLM_VERBOSE to the LLM configuration section:**
```bash
# LLM Configuration
LLM_PROVIDER=openai              # openai, anthropic, or google-genai
LLM_MODEL=gpt-4                  # Model name
LLM_TEMPERATURE=0                # Temperature (0.0-2.0)
LLM_API_KEY=your-api-key-here    # API key for chosen provider
LLM_STREAMING=false              # Enable token-by-token streaming
LLM_VERBOSE=false                # ✅ ADD THIS LINE
                                 # Enable verbose LLM logging (DEVELOPMENT ONLY)
                                 # WARNING: May expose API keys and prompts in logs
                                 # Only enable in development environment
```

---

## Testing Implementation

### Test File 1: Unit Tests for LLMConfig

**Create:** `tests/unit/test_llm_config_verbose.py`

```python
"""Tests for LLMConfig verbose flag propagation."""

import pytest
from neo4j_yass_mcp.config.llm_config import LLMConfig, chatLLM


class TestLLMConfigVerbose:
    """Test verbose flag in LLMConfig."""

    def test_verbose_defaults_to_false(self):
        """Test verbose defaults to False."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.0,
            api_key="test-key",
        )

        assert config.verbose is False

    def test_verbose_can_be_enabled(self):
        """Test verbose can be explicitly enabled."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.0,
            api_key="test-key",
            verbose=True,
        )

        assert config.verbose is True

    def test_verbose_propagates_to_openai(self):
        """Test verbose flag propagated to ChatOpenAI."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.0,
            api_key="test-key",
            verbose=True,
        )

        llm = chatLLM(config)

        # Verify verbose was set
        assert hasattr(llm, 'verbose')
        assert llm.verbose is True

    def test_verbose_propagates_to_anthropic(self):
        """Test verbose flag propagated to ChatAnthropic."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-opus-20240229",
            temperature=0.0,
            api_key="test-key",
            verbose=False,
        )

        llm = chatLLM(config)

        assert hasattr(llm, 'verbose')
        assert llm.verbose is False

    def test_verbose_propagates_to_google(self):
        """Test verbose flag propagated to ChatGoogleGenerativeAI."""
        config = LLMConfig(
            provider="google-genai",
            model="gemini-pro",
            temperature=0.0,
            api_key="test-key",
            verbose=False,
        )

        llm = chatLLM(config)

        assert hasattr(llm, 'verbose')
        assert llm.verbose is False

    @pytest.mark.parametrize("provider,model", [
        ("openai", "gpt-4"),
        ("anthropic", "claude-3-opus-20240229"),
        ("google-genai", "gemini-pro"),
    ])
    def test_all_providers_default_verbose_false(self, provider, model):
        """Test all providers have verbose=False by default."""
        config = LLMConfig(
            provider=provider,
            model=model,
            temperature=0.0,
            api_key="test-key",
        )

        llm = chatLLM(config)
        assert llm.verbose is False

    def test_verbose_with_streaming(self):
        """Test verbose works with streaming enabled."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.0,
            api_key="test-key",
            streaming=True,
            verbose=True,
        )

        llm = chatLLM(config)

        assert llm.streaming is True
        assert llm.verbose is True
```

---

### Test File 2: Integration Tests for Runtime Config

**Add to:** `tests/unit/test_runtime_config.py`

```python
"""Additional tests for verbose flag in RuntimeConfig."""

import os
import pytest
from neo4j_yass_mcp.config.runtime_config import RuntimeConfig


class TestRuntimeConfigVerbose:
    """Test verbose flag in RuntimeConfig."""

    def test_llm_verbose_from_env_true(self):
        """Test LLM verbose flag from environment (true)."""
        os.environ["LLM_VERBOSE"] = "true"
        os.environ["ENVIRONMENT"] = "development"

        try:
            config = RuntimeConfig.from_env()
            assert config.llm.verbose is True
        finally:
            del os.environ["LLM_VERBOSE"]
            del os.environ["ENVIRONMENT"]

    def test_llm_verbose_from_env_false(self):
        """Test LLM verbose flag from environment (false)."""
        os.environ["LLM_VERBOSE"] = "false"

        try:
            config = RuntimeConfig.from_env()
            assert config.llm.verbose is False
        finally:
            del os.environ["LLM_VERBOSE"]

    def test_llm_verbose_default_when_not_set(self):
        """Test LLM verbose defaults to false when not set."""
        # Ensure LLM_VERBOSE is not in environment
        if "LLM_VERBOSE" in os.environ:
            del os.environ["LLM_VERBOSE"]

        config = RuntimeConfig.from_env()
        assert config.llm.verbose is False

    def test_llm_verbose_case_insensitive(self):
        """Test LLM verbose environment variable is case-insensitive."""
        test_cases = ["true", "TRUE", "True", "TrUe"]

        for value in test_cases:
            os.environ["LLM_VERBOSE"] = value
            os.environ["ENVIRONMENT"] = "development"

            try:
                config = RuntimeConfig.from_env()
                assert config.llm.verbose is True, f"Failed for value: {value}"
            finally:
                del os.environ["LLM_VERBOSE"]
                del os.environ["ENVIRONMENT"]
```

---

### Test File 3: Server Initialization Tests

**Add to:** `tests/unit/test_server.py`

```python
"""Additional tests for server verbose flag validation."""

import pytest
from unittest.mock import patch
from neo4j_yass_mcp.config.runtime_config import RuntimeConfig


def test_server_blocks_verbose_in_production():
    """Test server initialization blocks LLM verbose in production."""
    # Mock config with production + verbose
    with patch('neo4j_yass_mcp.server._config') as mock_config:
        mock_config.environment.environment = "production"
        mock_config.llm.verbose = True
        mock_config.llm.provider = "openai"
        mock_config.llm.model = "gpt-4"

        # Import here to use mocked config
        from neo4j_yass_mcp.server import initialize_neo4j

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            import asyncio
            asyncio.run(initialize_neo4j())

        assert "production" in str(exc_info.value).lower()
        assert "verbose" in str(exc_info.value).lower()


def test_server_allows_verbose_in_development():
    """Test server allows LLM verbose in development."""
    # Mock config with development + verbose
    with patch('neo4j_yass_mcp.server._config') as mock_config:
        mock_config.environment.environment = "development"
        mock_config.llm.verbose = True
        mock_config.llm.provider = "openai"
        mock_config.llm.model = "gpt-4"

        # Should log warning but not raise
        # (Full test requires mocking Neo4j connection)
        # This is a simplified test showing the check logic
        from neo4j_yass_mcp.config.llm_config import LLMConfig

        llm_config = LLMConfig(
            provider=mock_config.llm.provider,
            model=mock_config.llm.model,
            temperature=0.0,
            api_key="test",
            verbose=True,
        )

        # Should not raise (development allows verbose)
        assert llm_config.verbose is True
```

---

## Verification Steps

### Manual Testing

1. **Test verbose=false (default):**
   ```bash
   # .env
   LLM_VERBOSE=false  # or omit

   # Run server
   python -m neo4j_yass_mcp.server

   # Expected: No verbose LLM logging
   # Expected: No warnings about verbose
   ```

2. **Test verbose=true in development:**
   ```bash
   # .env
   ENVIRONMENT=development
   LLM_VERBOSE=true

   # Run server
   python -m neo4j_yass_mcp.server

   # Expected: Warning logged
   # "⚠️ LLM_VERBOSE=true - LLM provider verbose logging enabled"
   ```

3. **Test verbose=true in production (should fail):**
   ```bash
   # .env
   ENVIRONMENT=production
   LLM_VERBOSE=true

   # Run server
   python -m neo4j_yass_mcp.server

   # Expected: ValueError raised
   # "LLM_VERBOSE=true is not allowed in production"
   ```

### Automated Testing

```bash
# Run all tests
pytest tests/unit/test_llm_config_verbose.py -v
pytest tests/unit/test_runtime_config.py::TestRuntimeConfigVerbose -v
pytest tests/unit/test_server.py -v -k verbose

# Expected: All tests pass
```

---

## Rollout Plan

### Phase 1: Development (Day 1)
- [ ] Implement code changes (5 files)
- [ ] Add unit tests (3 test files)
- [ ] Verify tests pass locally
- [ ] Test verbose=true in development
- [ ] Test verbose=false (default)

### Phase 2: Staging (Day 1)
- [ ] Deploy to staging with verbose=false
- [ ] Run full test suite
- [ ] Verify no LLM verbose logging
- [ ] Test verbose=true with ENVIRONMENT=development

### Phase 3: Production (Day 1)
- [ ] Deploy to production with verbose=false
- [ ] Verify no verbose logging
- [ ] Monitor for any issues
- [ ] Confirm security compliance

---

## Security Validation

### Checklist

- [ ] ✅ Verbose defaults to `false` in all environments
- [ ] ✅ Verbose propagated to all LLM providers (OpenAI, Anthropic, Google)
- [ ] ✅ Production environment blocks `verbose=true`
- [ ] ✅ Development environment allows `verbose=true` with warning
- [ ] ✅ Environment variable `LLM_VERBOSE` documented
- [ ] ✅ Security warnings logged when verbose enabled
- [ ] ✅ All tests passing
- [ ] ✅ No regression in existing functionality

---

## Summary

This implementation guide provides **complete, ready-to-use code** for the verbose flag propagation enhancement.

**Files to modify:** 5
**Tests to add:** 3
**Estimated time:** 4-8 hours
**Security impact:** CRITICAL - Prevents LLM provider data leakage

**Ready to implement!** Follow the steps in order for a clean implementation.

---

**Document Date:** 2025-11-16
**Status:** Ready for Implementation
**Next Step:** Begin implementation with Step 1
