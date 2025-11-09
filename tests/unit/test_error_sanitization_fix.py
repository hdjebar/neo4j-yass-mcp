"""
Tests for error message sanitization case sensitivity fix (Issue #4 - MEDIUM).

Tests that sanitize_error_message() correctly matches error patterns
regardless of case, fixing the bug where mixed-case patterns never matched.
"""

from unittest.mock import patch

import pytest

from neo4j_yass_mcp.server import sanitize_error_message


class TestErrorSanitizationCaseSensitivity:
    """Test error message sanitization with different case patterns."""

    def setup_method(self):
        """Set production mode (non-debug) for all tests."""
        self.debug_patcher = patch("neo4j_yass_mcp.server._debug_mode", False)
        self.debug_patcher.start()

    def teardown_method(self):
        """Cleanup patches."""
        self.debug_patcher.stop()

    # --- Test Case Sensitivity Fixes ---

    def test_connection_refused_lowercase(self):
        """Test 'connection refused' in lowercase is recognized."""
        error = Exception("connection refused by server")
        result = sanitize_error_message(error)
        # Should return the full error message, not generic
        assert result == "connection refused by server"

    def test_connection_refused_uppercase(self):
        """Test 'Connection Refused' in mixed case is recognized (was broken before fix)."""
        error = Exception("Connection Refused by server")
        result = sanitize_error_message(error)
        # Should return the full error message, not generic
        assert result == "Connection Refused by server"

    def test_connection_refused_all_caps(self):
        """Test 'CONNECTION REFUSED' in all caps is recognized."""
        error = Exception("CONNECTION REFUSED BY SERVER")
        result = sanitize_error_message(error)
        # Should return the full error message, not generic
        assert result == "CONNECTION REFUSED BY SERVER"

    def test_authentication_failed_mixed_case(self):
        """Test 'Authentication Failed' in mixed case."""
        error = Exception("Authentication Failed for user")
        result = sanitize_error_message(error)
        assert result == "Authentication Failed for user"

    def test_timeout_uppercase(self):
        """Test 'TIMEOUT' in uppercase."""
        error = Exception("TIMEOUT occurred after 30s")
        result = sanitize_error_message(error)
        assert result == "TIMEOUT occurred after 30s"

    def test_not_found_title_case(self):
        """Test 'Not Found' in title case."""
        error = Exception("Not Found: Resource does not exist")
        result = sanitize_error_message(error)
        assert result == "Not Found: Resource does not exist"

    def test_unauthorized_mixed_case(self):
        """Test 'UnAuthorized' in mixed case."""
        error = Exception("UnAuthorized access attempt")
        result = sanitize_error_message(error)
        assert result == "UnAuthorized access attempt"

    def test_query_exceeds_mixed_case(self):
        """Test 'Query Exceeds Maximum Length' (was broken before fix)."""
        error = Exception("Query Exceeds Maximum Length of 10000 characters")
        result = sanitize_error_message(error)
        # Should return the full error message, not generic
        assert result == "Query Exceeds Maximum Length of 10000 characters"

    def test_empty_query_mixed_case(self):
        """Test 'Empty Query Not Allowed' (was broken before fix)."""
        error = Exception("Empty Query Not Allowed")
        result = sanitize_error_message(error)
        assert result == "Empty Query Not Allowed"

    def test_blocked_query_mixed_case(self):
        """Test 'Blocked: Query Contains Dangerous Pattern' (was broken before fix)."""
        error = Exception("Blocked: Query Contains Dangerous Pattern LOAD CSV")
        result = sanitize_error_message(error)
        assert result == "Blocked: Query Contains Dangerous Pattern LOAD CSV"

    # --- Test Generic Sanitization ---

    def test_sensitive_error_sanitized(self):
        """Test error with sensitive info is sanitized to generic message."""
        error = ValueError("Failed to connect to bolt://neo4j:password@localhost:7687")
        result = sanitize_error_message(error)
        # Should NOT contain the sensitive URI
        assert "password" not in result
        assert "bolt://" not in result
        # Should be generic message with error type
        assert result == "ValueError: An error occurred. Enable DEBUG_MODE for details."

    def test_path_disclosure_sanitized(self):
        """Test error with file paths is sanitized."""
        error = Exception("Failed to read /home/user/.ssh/id_rsa")
        result = sanitize_error_message(error)
        # Should NOT contain the file path
        assert "/home/user" not in result
        assert result == "Exception: An error occurred. Enable DEBUG_MODE for details."

    def test_ip_address_sanitized(self):
        """Test error with IP addresses is sanitized."""
        error = Exception("Connection failed to 192.168.1.100:7687")
        result = sanitize_error_message(error)
        # Should NOT contain the IP
        assert "192.168.1.100" not in result
        assert result == "Exception: An error occurred. Enable DEBUG_MODE for details."

    # --- Test Debug Mode ---

    def test_debug_mode_returns_full_error(self):
        """Test that debug mode returns full error message."""
        self.debug_patcher.stop()  # Disable the production mode patch
        with patch("neo4j_yass_mcp.server._debug_mode", True):
            error = Exception("Sensitive information: password=secret123")
            result = sanitize_error_message(error)
            # In debug mode, should return full message
            assert result == "Sensitive information: password=secret123"
        self.debug_patcher.start()  # Re-enable production mode

    # --- Test Partial Matches ---

    def test_timeout_in_longer_message(self):
        """Test 'timeout' pattern matches in longer message."""
        error = Exception("Operation timeout after waiting 60 seconds")
        result = sanitize_error_message(error)
        assert result == "Operation timeout after waiting 60 seconds"

    def test_authentication_partial_match(self):
        """Test 'authentication failed' matches in middle of message."""
        error = Exception("Neo4j authentication failed due to invalid credentials")
        result = sanitize_error_message(error)
        assert result == "Neo4j authentication failed due to invalid credentials"


class TestErrorSanitizationEdgeCases:
    """Test edge cases in error sanitization."""

    def setup_method(self):
        """Set production mode for all tests."""
        self.debug_patcher = patch("neo4j_yass_mcp.server._debug_mode", False)
        self.debug_patcher.start()

    def teardown_method(self):
        """Cleanup patches."""
        self.debug_patcher.stop()

    def test_empty_error_message(self):
        """Test error with empty message."""
        error = Exception("")
        result = sanitize_error_message(error)
        assert result == "Exception: An error occurred. Enable DEBUG_MODE for details."

    def test_none_in_error_message(self):
        """Test error containing 'None'."""
        error = Exception("Value is None")
        result = sanitize_error_message(error)
        # Should be sanitized (not in safe patterns)
        assert result == "Exception: An error occurred. Enable DEBUG_MODE for details."

    def test_multiple_safe_patterns(self):
        """Test error containing multiple safe patterns."""
        error = Exception("Connection refused: authentication failed")
        result = sanitize_error_message(error)
        # Should match and return full message
        assert result == "Connection refused: authentication failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
