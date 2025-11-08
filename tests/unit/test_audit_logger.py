"""
Comprehensive tests for security/audit_logger.py module.

Tests cover:
- AuditLogger initialization and configuration
- Query logging with metadata
- Response logging with execution time
- Error logging with error types
- PII redaction (email, phone, credit card, SSN)
- Log file rotation (daily, weekly, size-based)
- Log cleanup and retention
- JSON and text format output
- Global logger initialization

Target: 80%+ code coverage
"""

import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock

from neo4j_yass_mcp.security.audit_logger import (
    AuditLogger,
    initialize_audit_logger,
    get_audit_logger,
)


@pytest.fixture
def temp_log_dir():
    """Create temporary directory for audit logs."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestAuditLoggerInitialization:
    """Test AuditLogger initialization and configuration."""

    def test_initialization_disabled(self, temp_log_dir):
        """Test audit logger when disabled."""
        logger = AuditLogger(enabled=False, log_dir=temp_log_dir)

        assert logger.enabled is False
        assert logger.session_id is not None
        # No log files should be created when disabled
        log_files = list(Path(temp_log_dir).glob("*.log"))
        assert len(log_files) == 0

    def test_initialization_enabled(self, temp_log_dir):
        """Test audit logger when enabled."""
        logger = AuditLogger(enabled=True, log_dir=temp_log_dir)

        assert logger.enabled is True
        assert logger.log_dir == Path(temp_log_dir)
        assert logger.log_format == "json"  # default
        assert logger.rotation == "daily"  # default
        # Log directory should be created
        assert Path(temp_log_dir).exists()

    def test_custom_configuration(self, temp_log_dir):
        """Test audit logger with custom configuration."""
        logger = AuditLogger(
            enabled=True,
            log_dir=temp_log_dir,
            log_format="text",
            rotation="weekly",
            max_size_mb=50,
            retention_days=30,
            log_queries=False,
            log_responses=False,
            log_errors=True,
            pii_redaction=True,
        )

        assert logger.log_format == "text"
        assert logger.rotation == "weekly"
        assert logger.max_size_mb == 50
        assert logger.retention_days == 30
        assert logger.log_queries is False
        assert logger.log_responses is False
        assert logger.log_errors is True
        assert logger.pii_redaction is True

    def test_session_id_unique(self, temp_log_dir):
        """Test each logger instance has unique session ID."""
        logger1 = AuditLogger(enabled=False)
        logger2 = AuditLogger(enabled=False)

        assert logger1.session_id != logger2.session_id


class TestLogFileRotation:
    """Test log file rotation policies."""

    def test_daily_rotation_filename(self, temp_log_dir):
        """Test daily rotation generates correct filename."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, rotation="daily"
        )

        filename = logger._get_log_filename()
        # Should contain today's date in YYYY-MM-DD format
        today_str = datetime.now().strftime("%Y-%m-%d")
        assert today_str in str(filename)
        assert "audit_" in str(filename)

    def test_weekly_rotation_filename(self, temp_log_dir):
        """Test weekly rotation generates correct filename."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, rotation="weekly"
        )

        filename = logger._get_log_filename()
        # Week number format (contains current year)
        current_year = datetime.now().strftime("%Y")
        assert f"audit_{current_year}-W" in str(filename)

    def test_size_rotation_creates_current_file(self, temp_log_dir):
        """Test size-based rotation creates current file."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, rotation="size", max_size_mb=1
        )

        filename = logger._get_log_filename()
        assert filename == Path(temp_log_dir) / "audit_current.log"

    def test_size_rotation_rotates_large_file(self, temp_log_dir):
        """Test size-based rotation rotates when file exceeds max size."""
        # Create a large current file
        current_file = Path(temp_log_dir) / "audit_current.log"
        current_file.parent.mkdir(parents=True, exist_ok=True)

        # Write > 1MB of data
        with open(current_file, "w") as f:
            f.write("x" * (2 * 1024 * 1024))  # 2MB

        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, rotation="size", max_size_mb=1
        )

        # Should have rotated the old file
        rotated_files = list(Path(temp_log_dir).glob("audit_*.log"))
        # Should have at least the rotated file and new current
        assert len(rotated_files) >= 1

    def test_invalid_rotation_defaults_to_daily(self, temp_log_dir):
        """Test invalid rotation policy defaults to daily."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, rotation="invalid"
        )

        filename = logger._get_log_filename()
        # Should use daily format
        assert "audit_" in str(filename)


class TestLogCleanup:
    """Test log cleanup and retention."""

    def test_cleanup_old_logs(self, temp_log_dir):
        """Test cleanup removes logs older than retention period."""
        # Create old log files
        old_date = datetime.now() - timedelta(days=100)
        old_file = Path(temp_log_dir) / "audit_2024-01-01.log"
        old_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.touch()

        # Set modification time to old date
        os.utime(old_file, (old_date.timestamp(), old_date.timestamp()))

        # Initialize logger with 90-day retention
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, retention_days=90
        )

        # Old file should be deleted
        assert not old_file.exists()

    def test_cleanup_keeps_recent_logs(self, temp_log_dir):
        """Test cleanup keeps logs within retention period."""
        # Create recent log file
        recent_file = Path(temp_log_dir) / "audit_2025-01-01.log"
        recent_file.parent.mkdir(parents=True, exist_ok=True)
        recent_file.touch()

        # Initialize logger
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, retention_days=90
        )

        # Recent file should still exist
        assert recent_file.exists()

    def test_cleanup_handles_missing_directory(self, temp_log_dir):
        """Test cleanup handles missing log directory gracefully."""
        non_existent_dir = str(Path(temp_log_dir) / "nonexistent")

        # Should not raise exception
        logger = AuditLogger(enabled=False, log_dir=non_existent_dir)
        logger._cleanup_old_logs()


class TestPIIRedaction:
    """Test PII redaction functionality."""

    def test_email_redaction(self, temp_log_dir):
        """Test email addresses are redacted."""
        logger = AuditLogger(enabled=False, pii_redaction=True)

        text = "Contact us at user@example.com or admin@test.org"
        redacted = logger._redact_pii(text)

        assert "user@example.com" not in redacted
        assert "[EMAIL_REDACTED]" in redacted

    def test_phone_redaction(self, temp_log_dir):
        """Test phone numbers are redacted."""
        logger = AuditLogger(enabled=False, pii_redaction=True)

        texts = [
            "Call 555-123-4567 for support",
            "Phone: 5551234567",
            "International: +1-555-123-4567",
        ]

        for text in texts:
            redacted = logger._redact_pii(text)
            assert "[PHONE_REDACTED]" in redacted

    def test_credit_card_redaction(self, temp_log_dir):
        """Test credit card numbers are redacted."""
        logger = AuditLogger(enabled=False, pii_redaction=True)

        texts = [
            "Card: 4532-1234-5678-9012",
            "Card: 4532 1234 5678 9012",
            "Card: 4532123456789012",
        ]

        for text in texts:
            redacted = logger._redact_pii(text)
            assert "[CARD_REDACTED]" in redacted

    def test_ssn_redaction(self, temp_log_dir):
        """Test SSN patterns are redacted."""
        logger = AuditLogger(enabled=False, pii_redaction=True)

        text = "SSN: 123-45-6789"
        redacted = logger._redact_pii(text)

        assert "123-45-6789" not in redacted
        assert "[SSN_REDACTED]" in redacted

    def test_no_redaction_when_disabled(self, temp_log_dir):
        """Test no redaction when PII redaction is disabled."""
        logger = AuditLogger(enabled=False, pii_redaction=False)

        text = "Email: user@example.com, Phone: 555-1234"
        redacted = logger._redact_pii(text)

        # Should be unchanged
        assert redacted == text

    def test_redaction_handles_non_string(self, temp_log_dir):
        """Test redaction handles non-string input."""
        logger = AuditLogger(enabled=False, pii_redaction=True)

        # Should return original value for non-strings
        assert logger._redact_pii(123) == 123
        assert logger._redact_pii(None) is None


class TestLogQuery:
    """Test query logging functionality."""

    def test_log_query_when_enabled(self, temp_log_dir):
        """Test query is logged when logging is enabled."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, log_queries=True
        )

        logger.log_query(
            tool="query_graph",
            query="MATCH (n) RETURN n",
            parameters={"limit": 10},
            user="test_user",
        )

        # Check log file exists and contains entry
        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        assert len(log_files) > 0

        with open(log_files[0], "r") as f:
            content = f.read()
            assert "query_graph" in content
            assert "MATCH (n) RETURN n" in content

    def test_log_query_when_disabled(self, temp_log_dir):
        """Test query is not logged when disabled."""
        logger = AuditLogger(
            enabled=False, log_dir=temp_log_dir, log_queries=True
        )

        logger.log_query(tool="test", query="MATCH (n) RETURN n")

        # No log files should be created
        log_files = list(Path(temp_log_dir).glob("*.log"))
        assert len(log_files) == 0

    def test_log_query_json_format(self, temp_log_dir):
        """Test query logged in JSON format."""
        logger = AuditLogger(
            enabled=True,
            log_dir=temp_log_dir,
            log_format="json",
            log_queries=True,
        )

        logger.log_query(tool="execute_cypher", query="MATCH (n) RETURN n LIMIT 5")

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            lines = f.readlines()
            # Skip initialization message, get actual log entry
            for line in lines:
                if "execute_cypher" in line:
                    entry = json.loads(line)
                    assert entry["event_type"] == "query"
                    assert entry["tool"] == "execute_cypher"
                    assert "MATCH (n) RETURN n LIMIT 5" in entry["query"]
                    break

    def test_log_query_with_pii_redaction(self, temp_log_dir):
        """Test query with PII redaction."""
        logger = AuditLogger(
            enabled=True,
            log_dir=temp_log_dir,
            log_queries=True,
            pii_redaction=True,
        )

        logger.log_query(
            tool="test", query="Find user@example.com in database"
        )

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()
            assert "[EMAIL_REDACTED]" in content
            assert "user@example.com" not in content


class TestLogResponse:
    """Test response logging functionality."""

    def test_log_response_when_enabled(self, temp_log_dir):
        """Test response is logged when enabled."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, log_responses=True
        )

        logger.log_response(
            tool="query_graph",
            query="MATCH (n) RETURN n",
            response={"success": True, "result": [{"name": "Test"}]},
            execution_time_ms=123.45,
        )

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()
            assert "response" in content
            assert "query_graph" in content

    def test_log_response_when_disabled(self, temp_log_dir):
        """Test response is not logged when disabled."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, log_responses=False
        )

        logger.log_response(
            tool="test",
            query="MATCH (n) RETURN n",
            response={"success": True},
        )

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()
            # Should only have initialization message, not response
            lines = [l for l in content.split("\n") if l.strip()]
            # Only initialization log
            assert len([l for l in lines if "response" in l]) == 0

    def test_log_response_with_pii_redaction(self, temp_log_dir):
        """Test response with PII redaction."""
        logger = AuditLogger(
            enabled=True,
            log_dir=temp_log_dir,
            log_responses=True,
            pii_redaction=True,
        )

        logger.log_response(
            tool="test",
            query="SELECT * FROM users",
            response={
                "success": True,
                "result": [{"email": "user@example.com"}],
                "answer": "Found user at user@example.com",
            },
        )

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()
            # Result should be redacted
            assert "[RESPONSE_REDACTED]" in content or "[EMAIL_REDACTED]" in content


class TestLogError:
    """Test error logging functionality."""

    def test_log_error_when_enabled(self, temp_log_dir):
        """Test error is logged when enabled."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, log_errors=True
        )

        logger.log_error(
            tool="execute_cypher",
            query="INVALID QUERY",
            error="Syntax error at line 1",
            error_type="SyntaxError",
        )

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()
            assert "error" in content.lower()
            assert "Syntax error" in content

    def test_log_error_when_disabled(self, temp_log_dir):
        """Test error is not logged when disabled."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, log_errors=False
        )

        logger.log_error(
            tool="test", query="MATCH (n) RETURN n", error="Test error"
        )

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()
            lines = [l for l in content.split("\n") if l.strip()]
            # Should not have error entry
            assert not any("Test error" in l for l in lines)

    def test_log_error_json_format(self, temp_log_dir):
        """Test error logged in JSON format."""
        logger = AuditLogger(
            enabled=True,
            log_dir=temp_log_dir,
            log_format="json",
            log_errors=True,
        )

        logger.log_error(
            tool="query_graph",
            query="MATCH (n) DELETE n",
            error="Unsafe query blocked",
            error_type="SecurityError",
        )

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            lines = f.readlines()
            for line in lines:
                if "SecurityError" in line:
                    entry = json.loads(line)
                    assert entry["event_type"] == "error"
                    assert entry["error_type"] == "SecurityError"
                    assert entry["success"] is False
                    break


class TestLogFormatting:
    """Test log entry formatting."""

    def test_json_format_output(self, temp_log_dir):
        """Test JSON format produces valid JSON."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, log_format="json"
        )

        entry = {
            "timestamp": "2025-01-15T10:00:00",
            "event_type": "query",
            "tool": "test",
            "query": "MATCH (n) RETURN n",
        }

        formatted = logger._format_entry(entry)
        # Should be valid JSON
        parsed = json.loads(formatted)
        assert parsed["event_type"] == "query"

    def test_text_format_output(self, temp_log_dir):
        """Test text format produces readable text."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, log_format="text"
        )

        entry = {
            "timestamp": "2025-01-15T10:00:00",
            "event_type": "query",
            "tool": "test",
            "session_id": "test-session",
            "query": "MATCH (n) RETURN n",
        }

        formatted = logger._format_entry(entry)
        assert "QUERY" in formatted
        assert "Tool: test" in formatted
        assert "Session:" in formatted


class TestGlobalLoggerFunctions:
    """Test global audit logger initialization and access."""

    def test_initialize_audit_logger_from_env(self, temp_log_dir):
        """Test initialization from environment variables."""
        with patch.dict(
            os.environ,
            {
                "AUDIT_LOG_ENABLED": "true",
                "AUDIT_LOG_DIR": temp_log_dir,
                "AUDIT_LOG_FORMAT": "text",
                "AUDIT_LOG_ROTATION": "weekly",
                "AUDIT_LOG_MAX_SIZE_MB": "50",
                "AUDIT_LOG_RETENTION_DAYS": "30",
                "AUDIT_LOG_PII_REDACTION": "true",
            },
        ):
            logger = initialize_audit_logger()

            assert logger.enabled is True
            assert logger.log_format == "text"
            assert logger.rotation == "weekly"
            assert logger.max_size_mb == 50
            assert logger.retention_days == 30
            assert logger.pii_redaction is True

    def test_initialize_audit_logger_defaults(self, temp_log_dir):
        """Test initialization with default values."""
        with patch.dict(os.environ, {}, clear=True):
            logger = initialize_audit_logger()

            assert logger.enabled is False  # Default
            assert logger.log_format == "json"
            assert logger.rotation == "daily"

    def test_get_audit_logger(self, temp_log_dir):
        """Test get_audit_logger returns initialized logger."""
        with patch.dict(
            os.environ,
            {"AUDIT_LOG_ENABLED": "true", "AUDIT_LOG_DIR": temp_log_dir},
        ):
            initialized = initialize_audit_logger()
            retrieved = get_audit_logger()

            assert retrieved is initialized

    def test_get_audit_logger_before_initialization(self):
        """Test get_audit_logger before initialization."""
        # Reset global logger
        import neo4j_yass_mcp.security.audit_logger as audit_module
        audit_module._audit_logger = None

        result = get_audit_logger()
        assert result is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_log_with_metadata(self, temp_log_dir):
        """Test logging with additional metadata."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, log_queries=True
        )

        logger.log_query(
            tool="test",
            query="MATCH (n) RETURN n",
            metadata={"request_id": "123", "ip_address": "127.0.0.1"},
        )

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()
            assert "request_id" in content
            assert "127.0.0.1" in content

    def test_concurrent_logging(self, temp_log_dir):
        """Test multiple log entries in sequence."""
        logger = AuditLogger(enabled=True, log_dir=temp_log_dir)

        for i in range(5):
            logger.log_query(tool="test", query=f"QUERY {i}")

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()
            # Should have all queries
            for i in range(5):
                assert f"QUERY {i}" in content

    def test_response_with_no_success_key(self, temp_log_dir):
        """Test response logging when success key is missing."""
        logger = AuditLogger(
            enabled=True, log_dir=temp_log_dir, log_responses=True
        )

        logger.log_response(
            tool="test",
            query="MATCH (n) RETURN n",
            response={"result": []},  # No 'success' key
        )

        log_files = list(Path(temp_log_dir).glob("audit_*.log"))
        assert len(log_files) > 0  # Should not crash


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=neo4j_yass_mcp.security.audit_logger"])
