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
        from neo4j_yass_mcp import server

        # Save original
        original_executor = server._executor

        try:
            # Reset executor to None
            server._executor = None

            # Get executor - should be created
            executor1 = server.get_executor()

            assert executor1 is not None
            assert isinstance(executor1, ThreadPoolExecutor)
            assert executor1._max_workers == 4
            assert executor1._thread_name_prefix == "langchain_"

            # Verify it's now stored
            assert server._executor is executor1

        finally:
            # Restore original
            server._executor = original_executor

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
        from neo4j_yass_mcp import server

        # Save original
        original_executor = server._executor

        try:
            # Create a custom executor
            custom_executor = ThreadPoolExecutor(max_workers=2)
            server._executor = custom_executor

            # get_executor should return the existing instance
            result = server.get_executor()

            assert result is custom_executor

        finally:
            # Restore original and clean up custom executor
            if custom_executor:
                custom_executor.shutdown(wait=False)
            server._executor = original_executor


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
