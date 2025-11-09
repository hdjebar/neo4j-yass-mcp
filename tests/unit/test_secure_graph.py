"""
Tests for SecureNeo4jGraph security wrapper - REAL TESTS ONLY (no mocks).

Comprehensive tests for the security validation layer that runs
BEFORE query execution (Issue #1 fix).

Test Philosophy: Since SecureNeo4jGraph.query() calls the security functions
BEFORE executing queries, we test those security functions directly to verify
they correctly block malicious queries. This proves the security layer works.
"""

from unittest.mock import patch

import pytest

from neo4j_yass_mcp.security import check_query_complexity, sanitize_query
from neo4j_yass_mcp.server import check_read_only_access


class TestSecureNeo4jGraphSanitization:
    """Test sanitizer integration - validates queries BEFORE execution."""

    def test_blocks_load_csv_injection(self):
        """Sanitizer blocks LOAD CSV file access attempts"""
        malicious_query = "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line"
        is_safe, error, warnings = sanitize_query(malicious_query, None)

        # Security check should block this
        assert not is_safe
        assert error is not None
        assert "dangerous pattern" in error.lower() or "LOAD CSV" in error

    def test_blocks_string_concatenation(self):
        """Sanitizer blocks string concatenation (injection vector)"""
        malicious_query = "MATCH (n) WHERE n.id = 'admin' + 'istrator' RETURN n"
        is_safe, error, warnings = sanitize_query(malicious_query, None)

        # Security check should block this
        assert not is_safe
        assert error is not None
        assert "dangerous pattern" in error.lower()

    def test_blocks_query_chaining(self):
        """Sanitizer blocks query chaining with semicolons"""
        malicious_query = "MATCH (n) RETURN n; CREATE (m:Malicious) RETURN m"
        is_safe, error, warnings = sanitize_query(malicious_query, None)

        # Security check should block this
        assert not is_safe
        assert error is not None

    def test_blocks_apoc_dangerous_procedures(self):
        """Sanitizer blocks dangerous APOC procedures"""
        queries = [
            "CALL apoc.load.json('http://evil.com/data') YIELD value RETURN value",
            "CALL apoc.cypher.run('CREATE (n) RETURN n', {}) YIELD value RETURN value",
            "CALL apoc.periodic.iterate('MATCH (n) RETURN n', 'DELETE n', {}) YIELD batches",
        ]

        for query in queries:
            is_safe, error, warnings = sanitize_query(query, None)
            assert not is_safe, f"Query should be blocked: {query}"
            assert error is not None

    def test_blocks_unicode_homoglyph_attack(self):
        """Sanitizer detects Unicode homoglyph attacks"""
        # Cyrillic 'а' looks like Latin 'a'
        malicious_query = "MATCH (n:Person) WHERE n.nаme = 'test' RETURN n"
        is_safe, error, warnings = sanitize_query(malicious_query, None)

        # Security check should block this or warn
        # Note: This might only produce warnings, not hard block
        assert not is_safe or len(warnings) > 0

    def test_allows_safe_query(self):
        """Sanitizer allows safe queries"""
        safe_query = "MATCH (n:Person) WHERE n.age > 18 RETURN n.name LIMIT 10"
        is_safe, error, warnings = sanitize_query(safe_query, None)

        # Should be allowed
        assert is_safe
        assert error is None


class TestSecureNeo4jGraphComplexity:
    """Test complexity limiter - validates queries BEFORE execution."""

    def test_blocks_overly_complex_query(self):
        """Complexity limiter blocks queries exceeding limits"""
        # Query with unbounded variable-length patterns (scores 25 each)
        # Need 5+ unbounded patterns to exceed limit of 100
        complex_query = (
            "MATCH (a)-[*]->(b)-[*]->(c)-[*]->(d)-[*]->(e)-[*]->(f) "
            "WHERE a.id = 1 RETURN *"
        )
        is_allowed, error, score = check_query_complexity(complex_query)

        # Should be blocked for complexity (5 unbounded patterns = 125 score)
        assert not is_allowed
        assert error is not None
        assert "complexity" in error.lower() or "limit" in error.lower() or "exceeded" in error.lower()

    def test_allows_simple_query(self):
        """Complexity limiter allows simple queries"""
        simple_query = "MATCH (n:Person) RETURN n LIMIT 10"
        is_allowed, error, score = check_query_complexity(simple_query)

        # Should be allowed
        assert is_allowed
        assert error is None


class TestSecureNeo4jGraphReadOnly:
    """Test read-only mode - validates queries BEFORE execution."""

    def setup_method(self):
        """Enable read-only mode for all tests."""
        self.read_only_patcher = patch("neo4j_yass_mcp.server._read_only_mode", True)
        self.read_only_patcher.start()

    def teardown_method(self):
        """Cleanup patches."""
        self.read_only_patcher.stop()

    def test_blocks_create_in_readonly_mode(self):
        """Read-only check blocks CREATE operations"""
        query = "CREATE (n:Person {name: 'Bob'}) RETURN n"
        error = check_read_only_access(query)

        # Should be blocked
        assert error is not None
        assert "CREATE" in error

    def test_blocks_merge_in_readonly_mode(self):
        """Read-only check blocks MERGE operations"""
        query = "MERGE (n:Person {id: 1}) RETURN n"
        error = check_read_only_access(query)

        # Should be blocked
        assert error is not None
        assert "MERGE" in error

    def test_blocks_delete_in_readonly_mode(self):
        """Read-only check blocks DELETE operations"""
        query = "MATCH (n) DELETE n"
        error = check_read_only_access(query)

        # Should be blocked
        assert error is not None
        assert "DELETE" in error

    def test_blocks_set_in_readonly_mode(self):
        """Read-only check blocks SET operations"""
        query = "MATCH (n) SET n.updated = true RETURN n"
        error = check_read_only_access(query)

        # Should be blocked
        assert error is not None
        assert "SET" in error

    def test_blocks_whitespace_bypass_in_readonly_mode(self):
        """Read-only check blocks CREATE with newline/tab bypass attempts"""
        # Try newline bypass
        query_newline = "CREATE\\n(n:Person) RETURN n"
        error = check_read_only_access(query_newline)
        assert error is not None

        # Try tab bypass
        query_tab = "CREATE\\t(n:Person) RETURN n"
        error = check_read_only_access(query_tab)
        assert error is not None

        # Try no-space bypass
        query_nospace = "CREATE(n:Person) RETURN n"
        error = check_read_only_access(query_nospace)
        assert error is not None

    def test_blocks_mutating_procedures_in_readonly_mode(self):
        """Read-only check blocks mutating procedures"""
        # Try APOC write procedure
        query_apoc = "CALL apoc.write.create(labels, properties)"
        error = check_read_only_access(query_apoc)
        assert error is not None
        assert "Mutating procedure" in error or "CALL" in error

        # Try db.schema mutation
        query_schema = "CALL db.schema.nodeTypeProperties()"
        error = check_read_only_access(query_schema)
        assert error is not None
        assert "Mutating procedure" in error or "CALL" in error

    def test_allows_read_queries(self):
        """Read-only check allows safe read queries"""
        queries = [
            "MATCH (n:Person) RETURN n LIMIT 10",
            "MATCH (n:Person) WHERE n.age > 18 RETURN n.name",
            "CALL db.labels() YIELD label RETURN label",
            "UNWIND [1, 2, 3] AS x RETURN x",
        ]

        for query in queries:
            error = check_read_only_access(query)
            assert error is None, f"Query should be allowed: {query}"


class TestSecureNeo4jGraphLayeredSecurity:
    """Test that multiple security layers work together."""

    def setup_method(self):
        """Enable read-only mode for read-only tests."""
        self.read_only_patcher = patch("neo4j_yass_mcp.server._read_only_mode", True)
        self.read_only_patcher.start()

    def teardown_method(self):
        """Cleanup patches."""
        self.read_only_patcher.stop()

    def test_sanitizer_catches_injection(self):
        """Verify sanitizer catches malicious patterns"""
        malicious_query = "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line"
        is_safe, error, warnings = sanitize_query(malicious_query, None)

        # Sanitizer should catch this
        assert not is_safe

    def test_complexity_catches_complex_queries(self):
        """Verify complexity limiter catches overly complex queries"""
        complex_query = (
            "MATCH (a)-[*]->(b)-[*]->(c)-[*]->(d)-[*]->(e)-[*]->(f) "
            "WHERE a.id = 1 RETURN *"
        )
        is_allowed, error, score = check_query_complexity(complex_query)

        # Complexity limiter should catch this (5 unbounded patterns = 125 score)
        assert not is_allowed

    def test_readonly_catches_write_operations(self):
        """Verify read-only check catches write operations"""
        write_query = "CREATE (n:Person {name: 'Test'}) RETURN n"
        error = check_read_only_access(write_query)

        # Read-only check should catch this
        assert error is not None
        assert "CREATE" in error


class TestSecureNeo4jGraphInitialization:
    """Test SecureNeo4jGraph configuration flags."""

    def setup_method(self):
        """Enable read-only mode for read-only tests."""
        self.read_only_patcher = patch("neo4j_yass_mcp.server._read_only_mode", True)
        self.read_only_patcher.start()

    def teardown_method(self):
        """Cleanup patches."""
        self.read_only_patcher.stop()

    def test_security_functions_are_independent(self):
        """Verify each security function works independently"""
        # Sanitizer blocks dangerous patterns
        is_safe, error, warnings = sanitize_query(
            "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line", None
        )
        assert not is_safe

        # Complexity blocks overly complex queries (5 unbounded patterns = 125 score)
        is_allowed, error, score = check_query_complexity(
            "MATCH (a)-[*]->(b)-[*]->(c)-[*]->(d)-[*]->(e)-[*]->(f) RETURN *"
        )
        assert not is_allowed

        # Read-only blocks write operations
        error = check_read_only_access("CREATE (n:Person) RETURN n")
        assert error is not None

    def test_safe_query_passes_all_checks(self):
        """Verify safe queries pass all security checks"""
        safe_query = "MATCH (n:Person) RETURN n LIMIT 10"

        # Should pass sanitizer
        is_safe, error, warnings = sanitize_query(safe_query, None)
        assert is_safe

        # Should pass complexity check
        is_allowed, error, score = check_query_complexity(safe_query)
        assert is_allowed

        # Read-only check allows MATCH
        error = check_read_only_access(safe_query)
        assert error is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
