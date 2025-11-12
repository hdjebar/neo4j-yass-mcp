"""
Tests for server configuration and initialization.

Covers utility functions like executor lazy initialization.

Note: Module-level warning messages (lines 69, 81, 93) are marked with
# pragma: no cover in server.py since they execute once at import time
and are difficult to test reliably without complex module reloading.
"""

from concurrent.futures import ThreadPoolExecutor

import pytest


class TestGetExecutor:
    """Test thread pool executor lazy initialization."""

    def test_lazy_initialization(self):
        """Lines 121-123: Executor is lazily initialized"""
        from neo4j_yass_mcp import bootstrap, server

        # Save original bootstrap state
        original_state = bootstrap._server_state

        try:
            # Reset bootstrap state to force lazy initialization
            bootstrap._server_state = None

            # Get executor - should be created lazily
            executor1 = server.get_executor()

            assert executor1 is not None
            assert isinstance(executor1, ThreadPoolExecutor)
            # Phase 3.3: Bootstrap now uses config value (default 10 workers)
            assert executor1._max_workers == 10
            # Phase 3.3: Bootstrap uses "neo4j_yass_mcp_" prefix
            assert executor1._thread_name_prefix == "neo4j_yass_mcp_"

            # Phase 3.3: Verify it's stored in bootstrap state (not module-level)
            assert bootstrap._server_state is not None
            assert bootstrap._server_state._executor is executor1

        finally:
            # Restore original bootstrap state
            bootstrap._server_state = original_state

    def test_executor_reuse(self):
        """Verify same executor instance is reused"""
        from neo4j_yass_mcp import server

        # Save original
        original_executor = server._executor

        try:
            # Reset executor to None
            server._executor = None

            # Get executor twice
            executor1 = server.get_executor()
            executor2 = server.get_executor()

            # Should be same instance (lazy singleton pattern)
            assert executor1 is executor2

        finally:
            # Restore original
            server._executor = original_executor

    def test_executor_returns_existing_instance(self):
        """Verify executor returns existing instance if already initialized"""
        from neo4j_yass_mcp import bootstrap, server

        # Save original bootstrap state
        original_state = bootstrap._server_state

        try:
            # Reset bootstrap state to force re-initialization
            bootstrap._server_state = None

            # First call creates executor
            executor1 = server.get_executor()

            # Second call should return same instance (Phase 3.3: from bootstrap state)
            executor2 = server.get_executor()

            assert executor1 is executor2
            assert isinstance(executor1, ThreadPoolExecutor)

        finally:
            # Restore original bootstrap state
            bootstrap._server_state = original_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
