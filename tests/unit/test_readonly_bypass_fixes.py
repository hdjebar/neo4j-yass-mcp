"""
Tests for read-only mode bypass fixes (Issue #2 - HIGH priority).

Tests all bypass scenarios identified in the security audit:
- Whitespace bypass (newlines, tabs)
- No-space bypass (keyword immediately followed by parenthesis)
- Mutating procedures (CALL apoc.write.*, CALL db.schema.*)
- Dangerous operations (LOAD CSV, FOREACH)

These tests validate that the regex-based check_read_only_access() function
properly detects ALL write operations regardless of formatting.
"""

import pytest
from neo4j_yass_mcp.server import check_read_only_access
from unittest.mock import patch


class TestReadOnlyBypassFixes:
    """Test that read-only mode cannot be bypassed."""

    def setup_method(self):
        """Enable read-only mode for all tests."""
        # Patch the global _read_only_mode variable
        self.read_only_patcher = patch("neo4j_yass_mcp.server._read_only_mode", True)
        self.read_only_patcher.start()

    def teardown_method(self):
        """Cleanup patches."""
        self.read_only_patcher.stop()

    # --- Whitespace Bypass Tests ---

    def test_create_with_newline_blocked(self):
        """Test CREATE followed by newline is blocked."""
        query = "CREATE\n(m:Node) RETURN m"
        error = check_read_only_access(query)
        assert error is not None
        assert "CREATE" in error

    def test_create_with_tab_blocked(self):
        """Test CREATE followed by tab is blocked."""
        query = "CREATE\t(m:Node) RETURN m"
        error = check_read_only_access(query)
        assert error is not None
        assert "CREATE" in error

    def test_create_with_multiple_spaces_blocked(self):
        """Test CREATE followed by multiple spaces is blocked."""
        query = "CREATE    (m:Node) RETURN m"
        error = check_read_only_access(query)
        assert error is not None
        assert "CREATE" in error

    def test_delete_with_newline_blocked(self):
        """Test DELETE followed by newline is blocked."""
        query = "MATCH (n)\nDELETE\nn"
        error = check_read_only_access(query)
        assert error is not None
        assert "DELETE" in error

    def test_merge_with_tab_blocked(self):
        """Test MERGE followed by tab is blocked."""
        query = "MERGE\t(n:Person {id: 1})"
        error = check_read_only_access(query)
        assert error is not None
        assert "MERGE" in error

    # --- No-Space Bypass Tests ---

    def test_create_no_space_blocked(self):
        """Test CREATE immediately followed by parenthesis is blocked."""
        query = "CREATE(m:Node) RETURN m"
        error = check_read_only_access(query)
        assert error is not None
        assert "CREATE" in error

    def test_delete_no_space_blocked(self):
        """Test DELETE immediately followed by variable is blocked."""
        query = "MATCH (n) DELETE(n)"
        error = check_read_only_access(query)
        assert error is not None
        assert "DELETE" in error

    def test_set_no_space_blocked(self):
        """Test SET immediately followed by variable is blocked."""
        query = "MATCH (n) SET(n.name = 'test')"
        error = check_read_only_access(query)
        assert error is not None
        assert "SET" in error

    # --- Mutating Procedures Tests ---

    def test_call_apoc_write_blocked(self):
        """Test CALL apoc.write.* procedures are blocked."""
        query = "CALL apoc.write.create(labels, properties)"
        error = check_read_only_access(query)
        assert error is not None
        assert "Mutating procedure" in error

    def test_call_apoc_create_blocked(self):
        """Test CALL apoc.create.* procedures are blocked."""
        query = "CALL apoc.create.node(['Person'], {name: 'test'})"
        error = check_read_only_access(query)
        assert error is not None
        assert "Mutating procedure" in error

    def test_call_apoc_merge_blocked(self):
        """Test CALL apoc.merge.* procedures are blocked."""
        query = "CALL apoc.merge.node(['Person'], {id: 1})"
        error = check_read_only_access(query)
        assert error is not None
        assert "Mutating procedure" in error

    def test_call_apoc_refactor_blocked(self):
        """Test CALL apoc.refactor.* procedures are blocked."""
        query = "CALL apoc.refactor.rename.label('Old', 'New')"
        error = check_read_only_access(query)
        assert error is not None
        assert "Mutating procedure" in error

    def test_call_db_schema_blocked(self):
        """Test CALL db.schema.* procedures are blocked."""
        query = "CALL db.schema.nodeTypeProperties()"
        error = check_read_only_access(query)
        assert error is not None
        assert "Mutating procedure" in error

    # --- Dangerous Operations Tests ---

    def test_load_csv_blocked(self):
        """Test LOAD CSV operations are blocked."""
        query = "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line"
        error = check_read_only_access(query)
        assert error is not None
        assert "LOAD CSV" in error

    def test_load_csv_with_headers_blocked(self):
        """Test LOAD CSV WITH HEADERS is blocked."""
        query = "LOAD CSV WITH HEADERS FROM 'http://example.com/data.csv' AS row RETURN row"
        error = check_read_only_access(query)
        assert error is not None
        assert "LOAD CSV" in error

    def test_foreach_blocked(self):
        """Test FOREACH operations are blocked."""
        query = "FOREACH (x in [1,2,3] | CREATE (n:Node {value: x}))"
        error = check_read_only_access(query)
        assert error is not None
        assert "FOREACH" in error

    def test_foreach_with_merge_blocked(self):
        """Test FOREACH with MERGE is blocked."""
        query = "FOREACH (name in ['Alice', 'Bob'] | MERGE (p:Person {name: name}))"
        error = check_read_only_access(query)
        assert error is not None
        # Should be blocked by either FOREACH or MERGE
        assert error is not None

    # --- Case Sensitivity Tests ---

    def test_lowercase_create_blocked(self):
        """Test lowercase 'create' is blocked."""
        query = "create (n:Node) return n"
        error = check_read_only_access(query)
        assert error is not None
        assert "CREATE" in error

    def test_mixed_case_delete_blocked(self):
        """Test mixed case 'DeLeTe' is blocked."""
        query = "MATCH (n) DeLeTe n"
        error = check_read_only_access(query)
        assert error is not None
        assert "DELETE" in error

    # --- Valid Read Operations Tests ---

    def test_match_return_allowed(self):
        """Test simple MATCH RETURN is allowed."""
        query = "MATCH (n:Person) RETURN n LIMIT 10"
        error = check_read_only_access(query)
        assert error is None

    def test_match_where_return_allowed(self):
        """Test MATCH WHERE RETURN is allowed."""
        query = "MATCH (n:Person) WHERE n.age > 18 RETURN n.name"
        error = check_read_only_access(query)
        assert error is None

    def test_call_dbms_procedures_allowed(self):
        """Test CALL dbms.* procedures (read-only) are allowed."""
        query = "CALL dbms.procedures() YIELD name RETURN name"
        error = check_read_only_access(query)
        assert error is None

    def test_call_db_labels_allowed(self):
        """Test CALL db.labels() (read-only) is allowed."""
        query = "CALL db.labels() YIELD label RETURN label"
        error = check_read_only_access(query)
        assert error is None

    def test_unwind_return_allowed(self):
        """Test UNWIND RETURN is allowed."""
        query = "UNWIND [1, 2, 3] AS x RETURN x"
        error = check_read_only_access(query)
        assert error is None

    def test_with_clause_allowed(self):
        """Test WITH clause is allowed."""
        query = "MATCH (n:Person) WITH n.name AS name RETURN name"
        error = check_read_only_access(query)
        assert error is None

    # --- Edge Cases ---

    def test_word_containing_create_allowed(self):
        """Test words containing 'create' (like 'created') are allowed."""
        query = "MATCH (n:Person) RETURN n.created_at"
        error = check_read_only_access(query)
        assert error is None

    def test_property_named_delete_allowed(self):
        """Test properties named 'delete' are allowed."""
        query = "MATCH (n) RETURN n.delete_flag"
        error = check_read_only_access(query)
        assert error is None

    def test_detach_delete_blocked(self):
        """Test DETACH DELETE is blocked."""
        query = "MATCH (n:Node) DETACH DELETE n"
        error = check_read_only_access(query)
        assert error is not None
        # Should match either DETACH or DELETE
        assert "DETACH" in error or "DELETE" in error

    def test_remove_property_blocked(self):
        """Test REMOVE property is blocked."""
        query = "MATCH (n:Person) REMOVE n.age"
        error = check_read_only_access(query)
        assert error is not None
        assert "REMOVE" in error

    def test_drop_index_blocked(self):
        """Test DROP INDEX is blocked."""
        query = "DROP INDEX person_name_index"
        error = check_read_only_access(query)
        assert error is not None
        assert "DROP" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
