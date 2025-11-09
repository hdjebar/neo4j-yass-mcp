"""
Tests for server utility functions.

Covers edge cases in estimate_tokens, sanitize_error_message, and truncate_response.
Tests lines 176, 178, 225, 249-250 in server.py
"""

from unittest.mock import patch

import pytest


class TestEstimateTokens:
    """Test estimate_tokens utility function edge cases."""

    def test_estimate_tokens_none_input(self):
        """Line 176: Test estimate_tokens handles None input"""
        from neo4j_yass_mcp.server import estimate_tokens

        # None should return 0
        result = estimate_tokens(None)
        assert result == 0

    def test_estimate_tokens_non_string_input(self):
        """Line 178: Test estimate_tokens converts non-string to string"""
        from neo4j_yass_mcp.server import estimate_tokens

        # Integer
        result = estimate_tokens(12345)
        assert isinstance(result, int)
        assert result > 0

        # Dict
        result = estimate_tokens({"key": "value"})
        assert isinstance(result, int)
        assert result > 0

        # List
        result = estimate_tokens([1, 2, 3])
        assert isinstance(result, int)
        assert result > 0

    def test_estimate_tokens_normal_string(self):
        """Test estimate_tokens works with normal strings"""
        from neo4j_yass_mcp.server import estimate_tokens

        result = estimate_tokens("Hello world")
        assert isinstance(result, int)
        assert result > 0


class TestSanitizeErrorMessage:
    """Test sanitize_error_message utility function."""

    def test_sanitize_safe_pattern_match(self):
        """Line 225: Test safe patterns are returned unchanged"""
        from neo4j_yass_mcp import server

        # Test safe patterns that will match (case-insensitive substring match)
        safe_errors = [
            ValueError("Database authentication failed"),
            RuntimeError("connection refused by server"),
            Exception("Connection timeout occurred"),
            ValueError("Resource not found"),
            RuntimeError("User unauthorized to access"),
        ]

        # Ensure we're in production mode (debug_mode=False) to test pattern matching
        original_debug_mode = server._debug_mode
        server._debug_mode = False

        try:
            for error in safe_errors:
                result = server.sanitize_error_message(error)
                # Should return the original error message unchanged (line 225 return)
                assert str(error) in result, f"Expected '{str(error)}' in '{result}'"
        finally:
            server._debug_mode = original_debug_mode


class TestTruncateResponse:
    """Test truncate_response utility function."""

    def test_truncate_response_json_encoding_error(self):
        """Lines 249-250: Test truncate_response handles JSON encoding errors"""
        from neo4j_yass_mcp.server import truncate_response

        # Create an object that can't be JSON serialized easily
        class UnserializableClass:
            def __init__(self):
                self.circular_ref = self

        # Should fall back to str() representation
        obj = UnserializableClass()
        result, was_truncated = truncate_response(obj, max_tokens=1000)

        # Should have handled the error and used str() fallback
        assert result is not None

    def test_truncate_response_type_error(self):
        """Line 249: Test truncate_response handles TypeError in JSON encoding"""
        from neo4j_yass_mcp.server import truncate_response

        # Mock json.dumps to raise TypeError
        with patch("neo4j_yass_mcp.server.json.dumps") as mock_dumps:
            mock_dumps.side_effect = TypeError("Not JSON serializable")

            # Should fall back to str()
            result, was_truncated = truncate_response({"test": "data"}, max_tokens=1000)
            assert result is not None

    def test_truncate_response_value_error(self):
        """Line 249: Test truncate_response handles ValueError in JSON encoding"""
        from neo4j_yass_mcp.server import truncate_response

        # Mock json.dumps to raise ValueError
        with patch("neo4j_yass_mcp.server.json.dumps") as mock_dumps:
            mock_dumps.side_effect = ValueError("Circular reference")

            # Should fall back to str()
            result, was_truncated = truncate_response({"test": "data"}, max_tokens=1000)
            assert result is not None

    def test_truncate_response_no_limit(self):
        """Test truncate_response with no limit returns unchanged"""
        from neo4j_yass_mcp.server import truncate_response

        data = {"key": "value"}
        result, was_truncated = truncate_response(data, max_tokens=None)

        assert result == data
        assert was_truncated is False

    def test_truncate_response_within_limit(self):
        """Test truncate_response with data within limit"""
        from neo4j_yass_mcp.server import truncate_response

        data = {"small": "data"}
        result, was_truncated = truncate_response(data, max_tokens=10000)

        assert result == data
        assert was_truncated is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
