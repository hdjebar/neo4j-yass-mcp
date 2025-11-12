"""
Tests for bootstrap module.

Demonstrates how bootstrap module enables multi-instance support
and better test isolation.
"""

from unittest.mock import Mock, patch

import pytest

from neo4j_yass_mcp.bootstrap import (
    ServerState,
    get_server_state,
    initialize_server_state,
    reset_server_state,
    set_server_state,
)
from neo4j_yass_mcp.config import RuntimeConfig


class TestBootstrapInitialization:
    """Test server state initialization."""

    def teardown_method(self):
        """Reset server state after each test."""
        reset_server_state()

    def test_initialize_server_state_with_config(self):
        """Test initialization with explicit config."""
        # Create test config
        test_config = RuntimeConfig.from_env()

        # Initialize state
        state = initialize_server_state(config=test_config)

        assert state is not None
        assert isinstance(state, ServerState)
        assert state.config == test_config
        assert state.mcp is not None
        assert state.tool_rate_limiter is not None

    def test_initialize_server_state_with_defaults(self):
        """Test initialization with default config."""
        state = initialize_server_state()

        assert state is not None
        assert isinstance(state, ServerState)
        assert state.config is not None
        assert state.mcp is not None

    def test_get_server_state_lazy_initialization(self):
        """Test lazy initialization through get_server_state."""
        # First call should initialize
        state1 = get_server_state()
        assert state1 is not None

        # Second call should return same instance
        state2 = get_server_state()
        assert state2 is state1

    def test_set_and_get_server_state(self):
        """Test explicit state management."""
        # Create custom state
        test_config = RuntimeConfig.from_env()
        custom_state = initialize_server_state(config=test_config)

        # Set as current state
        set_server_state(custom_state)

        # Get should return same state
        retrieved_state = get_server_state()
        assert retrieved_state is custom_state

    def test_reset_server_state(self):
        """Test state reset."""
        # Initialize state
        _ = get_server_state()

        # Reset
        reset_server_state()

        # Next get should create new state
        new_state = get_server_state()
        assert new_state is not None


class TestServerStateStructure:
    """Test ServerState dataclass structure."""

    def test_server_state_attributes(self):
        """Test that ServerState has expected attributes."""
        config = RuntimeConfig.from_env()
        state = ServerState(
            config=config,
            mcp=Mock(),
        )

        # Core attributes
        assert hasattr(state, "config")
        assert hasattr(state, "mcp")
        assert hasattr(state, "graph")
        assert hasattr(state, "chain")

        # Rate limiting
        assert hasattr(state, "tool_rate_limiter")
        assert hasattr(state, "tool_rate_limit_enabled")
        assert hasattr(state, "resource_rate_limit_enabled")

        # Server flags
        assert hasattr(state, "_debug_mode")
        assert hasattr(state, "_read_only_mode")
        assert hasattr(state, "_response_token_limit")

    def test_server_state_defaults(self):
        """Test ServerState default values."""
        config = RuntimeConfig.from_env()
        state = ServerState(
            config=config,
            mcp=Mock(),
        )

        # Defaults
        assert state.graph is None
        assert state.chain is None
        assert state.tool_rate_limit_enabled is True
        assert state.resource_rate_limit_enabled is True
        assert state._debug_mode is False
        assert state._read_only_mode is False
        assert state._response_token_limit is None
        assert state._executor is None


class TestMultiInstanceSupport:
    """Test multi-instance capabilities."""

    def teardown_method(self):
        """Reset server state after each test."""
        reset_server_state()

    def test_multiple_isolated_states(self):
        """Test that multiple states can exist independently."""
        # Create two separate states with different configs
        config1 = RuntimeConfig.from_env()
        state1 = ServerState(config=config1, mcp=Mock())

        config2 = RuntimeConfig.from_env()
        state2 = ServerState(config=config2, mcp=Mock())

        # States should be independent
        assert state1 is not state2
        assert state1.config is not state2.config

    def test_state_switching(self):
        """Test switching between different states."""
        # Create two states
        state1 = initialize_server_state()
        state2 = initialize_server_state()

        # Switch to state1
        set_server_state(state1)
        assert get_server_state() is state1

        # Switch to state2
        set_server_state(state2)
        assert get_server_state() is state2


class TestBootstrapIntegration:
    """Test bootstrap integration with existing code."""

    def teardown_method(self):
        """Reset server state after each test."""
        reset_server_state()

    def test_bootstrap_with_mocked_dependencies(self):
        """Test bootstrap with mocked security dependencies."""
        with patch("neo4j_yass_mcp.bootstrap.initialize_audit_logger"):
            with patch("neo4j_yass_mcp.bootstrap.initialize_sanitizer"):
                with patch("neo4j_yass_mcp.bootstrap.initialize_complexity_limiter"):
                    with patch("neo4j_yass_mcp.bootstrap.initialize_rate_limiter"):
                        state = initialize_server_state()

                        assert state is not None
                        assert state.config is not None

    def test_bootstrap_respects_config_flags(self):
        """Test that bootstrap respects configuration flags."""
        state = initialize_server_state()

        # Flags should match config
        assert state.tool_rate_limit_enabled == state.config.tool_rate_limit.enabled
        assert state.resource_rate_limit_enabled == state.config.resource_rate_limit.enabled
        assert state._read_only_mode == state.config.neo4j.read_only
        assert state._debug_mode == state.config.environment.debug_mode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
