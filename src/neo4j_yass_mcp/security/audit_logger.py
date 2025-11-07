"""
Audit Logging Module for Compliance

Provides comprehensive audit logging of all queries, responses, and errors
for compliance, security, and forensic analysis purposes.

Features:
- JSON or text format logging
- Automatic log rotation (daily, weekly, or size-based)
- Configurable retention periods
- Optional PII redaction
- Timestamp and session tracking
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4


class AuditLogger:
    """
    Audit logger for compliance and security tracking.

    Logs all queries, responses, and errors to dedicated audit files
    with automatic rotation and retention management.
    """

    def __init__(
        self,
        enabled: bool = False,
        log_dir: str = "./logs/audit",
        log_format: str = "json",
        rotation: str = "daily",
        max_size_mb: int = 100,
        retention_days: int = 90,
        log_queries: bool = True,
        log_responses: bool = True,
        log_errors: bool = True,
        pii_redaction: bool = False,
    ):
        """
        Initialize audit logger.

        Args:
            enabled: Enable audit logging
            log_dir: Directory for audit logs
            log_format: Format (json or text)
            rotation: Rotation policy (daily, weekly, size)
            max_size_mb: Max file size for size-based rotation
            retention_days: Keep logs for N days
            log_queries: Log query details
            log_responses: Log response details
            log_errors: Log errors
            pii_redaction: Redact potential PII
        """
        self.enabled = enabled
        self.log_dir = Path(log_dir)
        self.log_format = log_format
        self.rotation = rotation
        self.max_size_mb = max_size_mb
        self.retention_days = retention_days
        self.log_queries = log_queries
        self.log_responses = log_responses
        self.log_errors = log_errors
        self.pii_redaction = pii_redaction

        # Session ID for tracking related operations
        self.session_id = str(uuid4())

        # Logger instance
        self.logger = logging.getLogger("audit")

        if self.enabled:
            self._setup_audit_logging()
            self._cleanup_old_logs()

    def _setup_audit_logging(self):
        """Setup audit log directory and file handler"""
        # Create audit log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Generate log filename based on rotation policy
        log_file = self._get_log_filename()

        # Configure file handler
        handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        handler.setLevel(logging.INFO)

        # Simple format for audit logs (we handle formatting ourselves)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Don't propagate to root logger

        self.logger.info(f"Audit logging initialized (session: {self.session_id})")

    def _get_log_filename(self) -> Path:
        """Generate log filename based on rotation policy"""
        timestamp = datetime.now()

        if self.rotation == "daily":
            date_str = timestamp.strftime("%Y-%m-%d")
            return self.log_dir / f"audit_{date_str}.log"
        elif self.rotation == "weekly":
            # ISO week number
            date_str = timestamp.strftime("%Y-W%W")
            return self.log_dir / f"audit_{date_str}.log"
        elif self.rotation == "size":
            # Check current file size
            current_file = self.log_dir / "audit_current.log"
            if current_file.exists():
                size_mb = current_file.stat().st_size / (1024 * 1024)
                if size_mb >= self.max_size_mb:
                    # Rotate: rename current to timestamped
                    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
                    rotated_file = self.log_dir / f"audit_{timestamp_str}.log"
                    current_file.rename(rotated_file)
            return current_file
        else:
            # Default to daily
            date_str = timestamp.strftime("%Y-%m-%d")
            return self.log_dir / f"audit_{date_str}.log"

    def _cleanup_old_logs(self):
        """Remove audit logs older than retention period"""
        if not self.log_dir.exists():
            return

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        for log_file in self.log_dir.glob("audit_*.log"):
            # Get file modification time
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff_date:
                try:
                    log_file.unlink()
                    self.logger.info(f"Deleted old audit log: {log_file.name}")
                except Exception as e:
                    logging.getLogger(__name__).warning(
                        f"Failed to delete old audit log {log_file.name}: {e}"
                    )

    def _redact_pii(self, text: str) -> str:
        """
        Redact potential PII from text.

        Simple pattern-based redaction for common PII:
        - Email addresses
        - Phone numbers
        - Credit card numbers (patterns)
        - Social security numbers (patterns)
        """
        if not self.pii_redaction or not isinstance(text, str):
            return text

        # Email addresses
        text = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]", text
        )

        # Phone numbers (various formats)
        text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE_REDACTED]", text)
        text = re.sub(
            r"\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b", "[PHONE_REDACTED]", text
        )

        # Credit card patterns (simple)
        text = re.sub(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD_REDACTED]", text)

        # SSN patterns (US)
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]", text)

        return text

    def _format_entry(self, entry: dict[str, Any]) -> str:
        """Format audit log entry based on configured format"""
        if self.log_format == "json":
            return json.dumps(entry, ensure_ascii=False, default=str)
        else:
            # Text format
            timestamp = entry.get("timestamp", "")
            event_type = entry.get("event_type", "")
            tool = entry.get("tool", "")
            success = entry.get("success", True)

            lines = [
                f"[{timestamp}] {event_type.upper()} - Tool: {tool}",
                f"  Session: {entry.get('session_id', '')}",
                f"  Success: {success}",
            ]

            if "query" in entry:
                lines.append(f"  Query: {entry['query'][:200]}...")

            if "error" in entry:
                lines.append(f"  Error: {entry['error']}")

            return "\n".join(lines)

    def log_query(
        self,
        tool: str,
        query: str,
        parameters: dict[str, Any | None] = None,
        user: str | None = None,
        metadata: dict[str, Any | None] = None,
    ):
        """
        Log a query execution.

        Args:
            tool: Tool name (query_graph, execute_cypher, etc.)
            query: Query string
            parameters: Query parameters
            user: User identifier (optional)
            metadata: Additional metadata
        """
        if not self.enabled or not self.log_queries:
            return

        # Redact PII if enabled
        query_logged = self._redact_pii(query) if self.pii_redaction else query

        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "query",
            "session_id": self.session_id,
            "tool": tool,
            "query": query_logged,
            "parameters": parameters or {},
            "user": user,
            "metadata": metadata or {},
        }

        self.logger.info(self._format_entry(entry))

    def log_response(
        self,
        tool: str,
        query: str,
        response: dict[str, Any],
        execution_time_ms: float | None = None,
        user: str | None = None,
        metadata: dict[str, Any | None] = None,
    ):
        """
        Log a query response.

        Args:
            tool: Tool name
            query: Original query
            response: Response data
            execution_time_ms: Execution time in milliseconds
            user: User identifier (optional)
            metadata: Additional metadata
        """
        if not self.enabled or not self.log_responses:
            return

        # Redact PII if enabled
        query_logged = self._redact_pii(query) if self.pii_redaction else query

        # Redact response if needed
        response_logged = response.copy()
        if self.pii_redaction and "result" in response_logged:
            response_logged["result"] = "[RESPONSE_REDACTED]"
        if self.pii_redaction and "answer" in response_logged:
            response_logged["answer"] = self._redact_pii(str(response_logged["answer"]))

        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "response",
            "session_id": self.session_id,
            "tool": tool,
            "query": query_logged,
            "response": response_logged,
            "success": response.get("success", True),
            "execution_time_ms": execution_time_ms,
            "user": user,
            "metadata": metadata or {},
        }

        self.logger.info(self._format_entry(entry))

    def log_error(
        self,
        tool: str,
        query: str,
        error: str,
        error_type: str | None = None,
        user: str | None = None,
        metadata: dict[str, Any | None] = None,
    ):
        """
        Log an error.

        Args:
            tool: Tool name
            query: Original query
            error: Error message
            error_type: Error type/class
            user: User identifier (optional)
            metadata: Additional metadata
        """
        if not self.enabled or not self.log_errors:
            return

        # Redact PII if enabled
        query_logged = self._redact_pii(query) if self.pii_redaction else query
        error_logged = self._redact_pii(error) if self.pii_redaction else error

        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "error",
            "session_id": self.session_id,
            "tool": tool,
            "query": query_logged,
            "error": error_logged,
            "error_type": error_type,
            "success": False,
            "user": user,
            "metadata": metadata or {},
        }

        self.logger.info(self._format_entry(entry))


# Global audit logger instance
_audit_logger: AuditLogger | None = None


def initialize_audit_logger() -> AuditLogger:
    """
    Initialize global audit logger from environment variables.

    Returns:
        Configured AuditLogger instance
    """
    global _audit_logger

    enabled = os.getenv("AUDIT_LOG_ENABLED", "false").lower() == "true"
    log_dir = os.getenv("AUDIT_LOG_DIR", "./logs/audit")
    log_format = os.getenv("AUDIT_LOG_FORMAT", "json")
    rotation = os.getenv("AUDIT_LOG_ROTATION", "daily")
    max_size_mb = int(os.getenv("AUDIT_LOG_MAX_SIZE_MB", "100"))
    retention_days = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))
    log_queries = os.getenv("AUDIT_LOG_QUERIES", "true").lower() == "true"
    log_responses = os.getenv("AUDIT_LOG_RESPONSES", "true").lower() == "true"
    log_errors = os.getenv("AUDIT_LOG_ERRORS", "true").lower() == "true"
    pii_redaction = os.getenv("AUDIT_LOG_PII_REDACTION", "false").lower() == "true"

    _audit_logger = AuditLogger(
        enabled=enabled,
        log_dir=log_dir,
        log_format=log_format,
        rotation=rotation,
        max_size_mb=max_size_mb,
        retention_days=retention_days,
        log_queries=log_queries,
        log_responses=log_responses,
        log_errors=log_errors,
        pii_redaction=pii_redaction,
    )

    if enabled:
        logging.getLogger(__name__).info(f"Audit logging enabled: {log_dir}")

    return _audit_logger


def get_audit_logger() -> AuditLogger | None:
    """Get the global audit logger instance"""
    return _audit_logger
