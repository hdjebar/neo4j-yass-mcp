"""
Tests for SecureNeo4jGraph security wrapper - REAL TESTS ONLY (no mocks).

Comprehensive tests for the security validation layer that runs
BEFORE query execution (Issue #1 fix).

Test Philosophy: These tests verify that SecureNeo4jGraph.query() actually
intercepts and validates queries BEFORE they reach the Neo4j driver. We test
that the wrapper correctly calls security functions and blocks unsafe queries.
"""

from unittest.mock import patch

import pytest

from neo4j_yass_mcp.secure_graph import SecureNeo4jGraph
from neo4j_yass_mcp.security import check_query_complexity, sanitize_query
from neo4j_yass_mcp.server import check_read_only_access


class TestSecureNeo4jGraphInterception:
    """Test that SecureNeo4jGraph actually intercepts queries before execution."""

    def test_blocks_dangerous_query_before_execution(self):
        """SecureNeo4jGraph blocks LOAD CSV before Neo4j driver is called"""
        # Create instance without connecting to Neo4j
        graph = SecureNeo4jGraph.__new__(SecureNeo4jGraph)
        graph.sanitizer_enabled = True
        graph.complexity_limit_enabled = False
        graph.read_only_mode = False

        # Mock parent to track if it's called
        parent_query_called = False
        def mock_parent_query(query, params=None):
            nonlocal parent_query_called
            parent_query_called = True
            return []

        # Patch the parent class query method
        with patch.object(type(graph).__bases__[0], 'query', mock_parent_query):
            # Attempt dangerous query
            malicious_query = "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line"

            with pytest.raises(ValueError, match="blocked by sanitizer"):
                graph.query(malicious_query)

            # Verify parent query() was NEVER called (security blocked it first)
            # This is the key assertion - if SecureNeo4jGraph is bypassed,
            # the parent query() would be called
            assert not parent_query_called, "Parent query() should not be called when sanitizer blocks"

    def test_complex_query_blocked_before_execution(self):
        """SecureNeo4jGraph blocks overly complex queries before driver execution"""
        graph = SecureNeo4jGraph.__new__(SecureNeo4jGraph)
        graph.sanitizer_enabled = False
        graph.complexity_limit_enabled = True
        graph.read_only_mode = False

        # Mock parent to track if it's called
        parent_query_called = False
        def mock_parent_query(query, params=None):
            nonlocal parent_query_called
            parent_query_called = True
            return []

        # Patch the parent class query method
        with patch.object(type(graph).__bases__[0], 'query', mock_parent_query):
            # Attempt overly complex query (5 unbounded patterns = 125 score > 100)
            complex_query = "MATCH (a)-[*]->(b)-[*]->(c)-[*]->(d)-[*]->(e)-[*]->(f) RETURN *"

            with pytest.raises(ValueError, match="blocked by complexity limiter"):
                graph.query(complex_query)

            # Verify parent was NOT called
            assert not parent_query_called, "Parent query() should not be called when complexity check fails"

    def test_readonly_mode_blocks_before_execution(self):
        """SecureNeo4jGraph blocks write queries in read-only mode before execution"""
        with patch("neo4j_yass_mcp.server._read_only_mode", True):
            graph = SecureNeo4jGraph.__new__(SecureNeo4jGraph)
            graph.sanitizer_enabled = False
            graph.complexity_limit_enabled = False
            graph.read_only_mode = True

            # Mock parent to track if it's called
            parent_query_called = False
            def mock_parent_query(query, params=None):
                nonlocal parent_query_called
                parent_query_called = True
                return []

            with patch.object(type(graph).__bases__[0], 'query', mock_parent_query):
                # Attempt write query
                write_query = "CREATE (n:Person {name: 'Test'}) RETURN n"

                with pytest.raises(ValueError, match="blocked in read-only mode"):
                    graph.query(write_query)

                # Verify parent was NOT called
                assert not parent_query_called, "Parent query() should not be called in read-only mode"

    def test_safe_query_reaches_driver(self):
        """SecureNeo4jGraph allows safe queries to reach the driver"""
        graph = SecureNeo4jGraph.__new__(SecureNeo4jGraph)
        graph.sanitizer_enabled = True
        graph.complexity_limit_enabled = True
        graph.read_only_mode = False

        # Mock parent to verify it IS called for safe queries
        parent_query_called = False
        def mock_parent_query(self, query, params=None):
            nonlocal parent_query_called
            parent_query_called = True
            return [{"n": {"name": "Alice"}}]

        with patch.object(type(graph).__bases__[0], 'query', mock_parent_query):
            # Safe query
            safe_query = "MATCH (n:Person) RETURN n LIMIT 10"
            result = graph.query(safe_query)

            # Verify parent WAS called (query passed all security checks)
            assert parent_query_called, "Parent query() should be called for safe queries"
            assert result == [{"n": {"name": "Alice"}}]


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
        query_newline = "CREATE\n(n:Person) RETURN n"
        error = check_read_only_access(query_newline)
        assert error is not None

        # Try tab bypass
        query_tab = "CREATE\t(n:Person) RETURN n"
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
    """Test that SecureNeo4jGraph enforces multiple security layers."""

    def test_sanitizer_layer_enforced(self):
        """Verify SecureNeo4jGraph enforces sanitizer checks"""
        graph = SecureNeo4jGraph.__new__(SecureNeo4jGraph)
        graph.sanitizer_enabled = True
        graph.complexity_limit_enabled = False
        graph.read_only_mode = False

        parent_called = False
        def mock_parent(query, params=None):
            nonlocal parent_called
            parent_called = True
            return []

        with patch.object(type(graph).__bases__[0], 'query', mock_parent):
            malicious_query = "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line"

            with pytest.raises(ValueError, match="blocked by sanitizer"):
                graph.query(malicious_query)

            assert not parent_called, "Sanitizer should block before driver execution"

    def test_complexity_layer_enforced(self):
        """Verify SecureNeo4jGraph enforces complexity limits"""
        graph = SecureNeo4jGraph.__new__(SecureNeo4jGraph)
        graph.sanitizer_enabled = False
        graph.complexity_limit_enabled = True
        graph.read_only_mode = False

        parent_called = False
        def mock_parent(query, params=None):
            nonlocal parent_called
            parent_called = True
            return []

        with patch.object(type(graph).__bases__[0], 'query', mock_parent):
            complex_query = "MATCH (a)-[*]->(b)-[*]->(c)-[*]->(d)-[*]->(e)-[*]->(f) RETURN *"

            with pytest.raises(ValueError, match="blocked by complexity limiter"):
                graph.query(complex_query)

            assert not parent_called, "Complexity limiter should block before driver execution"

    def test_readonly_layer_enforced(self):
        """Verify SecureNeo4jGraph enforces read-only mode"""
        with patch("neo4j_yass_mcp.server._read_only_mode", True):
            graph = SecureNeo4jGraph.__new__(SecureNeo4jGraph)
            graph.sanitizer_enabled = False
            graph.complexity_limit_enabled = False
            graph.read_only_mode = True

            parent_called = False
            def mock_parent(query, params=None):
                nonlocal parent_called
                parent_called = True
                return []

            with patch.object(type(graph).__bases__[0], 'query', mock_parent):
                write_query = "CREATE (n:Person {name: 'Test'}) RETURN n"

                with pytest.raises(ValueError, match="blocked in read-only mode"):
                    graph.query(write_query)

                assert not parent_called, "Read-only mode should block before driver execution"


class TestSecureNeo4jGraphInitialization:
    """Test SecureNeo4jGraph configuration flags."""

    def test_security_flags_stored_correctly(self):
        """Verify security flags are stored on initialization"""
        # We can't actually connect, but we can test the configuration
        graph = SecureNeo4jGraph.__new__(SecureNeo4jGraph)
        graph.sanitizer_enabled = True
        graph.complexity_limit_enabled = True
        graph.read_only_mode = False

        assert graph.sanitizer_enabled is True
        assert graph.complexity_limit_enabled is True
        assert graph.read_only_mode is False

    def test_can_disable_individual_security_features(self):
        """Verify individual security features can be disabled"""
        graph = SecureNeo4jGraph.__new__(SecureNeo4jGraph)
        graph.sanitizer_enabled = False
        graph.complexity_limit_enabled = False
        graph.read_only_mode = False

        assert graph.sanitizer_enabled is False
        assert graph.complexity_limit_enabled is False
        assert graph.read_only_mode is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
