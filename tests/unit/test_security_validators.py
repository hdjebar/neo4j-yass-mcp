"""
Tests for security.validators module.

Tests the check_read_only_access function that validates Cypher queries
against read-only mode restrictions.
"""

import pytest

from neo4j_yass_mcp.security.validators import check_read_only_access


class TestCheckReadOnlyAccess:
    """Test check_read_only_access function."""

    def test_read_only_disabled_allows_all_queries(self):
        """When read_only_mode=False, all queries should be allowed."""
        queries = [
            "CREATE (n:Person {name: 'Alice'})",
            "MERGE (n:User {id: 123})",
            "DELETE n",
            "SET n.name = 'Bob'",
            "REMOVE n.label",
            "DETACH DELETE n",
            "DROP INDEX my_index",
            "FOREACH (x in [1,2,3] | CREATE (:Node {val: x}))",
            "LOAD CSV FROM 'file.csv' AS row CREATE (:Node)",
            "CALL db.schema.nodeTypeProperties()",
            "CALL apoc.create.node(['Label'], {name: 'test'})",
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=False)
            assert result is None, f"Expected None for query: {query}"

    def test_read_only_allows_read_queries(self):
        """Read queries should be allowed in read-only mode."""
        queries = [
            "MATCH (n) RETURN n",
            "MATCH (n:Person) WHERE n.age > 30 RETURN n.name",
            "MATCH (a)-[:KNOWS]->(b) RETURN a, b",
            "OPTIONAL MATCH (n) RETURN n",
            "WITH 1 as x RETURN x",
            "UNWIND [1,2,3] AS x RETURN x",
            "RETURN 1 + 1",
            "CALL db.labels()",
            "CALL db.relationshipTypes()",
            "CALL dbms.components()",
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is None, f"Expected None for read query: {query}"

    def test_read_only_blocks_create(self):
        """CREATE operations should be blocked in read-only mode."""
        queries = [
            "CREATE (n:Person)",
            "CREATE (n {name: 'Alice'})",
            "MATCH (n) CREATE (m:NewNode)",
            "create (n:lowercase)",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            assert "CREATE" in result

    def test_read_only_blocks_merge(self):
        """MERGE operations should be blocked in read-only mode."""
        queries = [
            "MERGE (n:Person {id: 123})",
            "MATCH (n) MERGE (m:NewNode)",
            "merge (n)",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            assert "MERGE" in result

    def test_read_only_blocks_delete(self):
        """DELETE operations should be blocked in read-only mode."""
        queries = [
            "MATCH (n) DELETE n",
            "DELETE n",
            "delete n",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            assert "DELETE" in result

    def test_read_only_blocks_detach_delete(self):
        """DETACH DELETE operations should be blocked in read-only mode."""
        queries = [
            "MATCH (n) DETACH DELETE n",
            "DETACH DELETE n",
            "detach delete n",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            # Should catch either DETACH or DELETE
            assert "DETACH" in result or "DELETE" in result

    def test_read_only_blocks_set(self):
        """SET operations should be blocked in read-only mode."""
        queries = [
            "MATCH (n) SET n.name = 'Bob'",
            "SET n:Label",
            "set n.prop = 123",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            assert "SET" in result

    def test_read_only_blocks_remove(self):
        """REMOVE operations should be blocked in read-only mode."""
        queries = [
            "MATCH (n) REMOVE n.name",
            "REMOVE n:Label",
            "remove n.prop",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            assert "REMOVE" in result

    def test_read_only_blocks_drop(self):
        """DROP operations should be blocked in read-only mode."""
        queries = [
            "DROP INDEX my_index",
            "DROP CONSTRAINT my_constraint",
            "drop index idx",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            assert "DROP" in result

    def test_read_only_blocks_foreach(self):
        """FOREACH operations should be blocked in read-only mode."""
        queries = [
            "FOREACH (x in [1,2,3] | CREATE (:Node {val: x}))",
            "UNWIND [1,2,3] AS x FOREACH (y in [x] | CREATE (:Node))",
            "foreach (x in [1] | create (:N))",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            assert "FOREACH" in result

    def test_read_only_blocks_load_csv(self):
        """LOAD CSV operations should be blocked in read-only mode."""
        queries = [
            "LOAD CSV FROM 'file.csv' AS row CREATE (:Node)",
            "load csv from 'data.csv' as r return r",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            assert "LOAD CSV" in result

    def test_read_only_blocks_mutating_procedures(self):
        """Mutating APOC and DB procedures should be blocked in read-only mode."""
        queries = [
            "CALL db.schema.nodeTypeProperties()",
            "CALL apoc.write.something()",
            "CALL apoc.create.node(['Label'], {name: 'test'})",
            "CALL apoc.merge.node(['Label'], {id: 1})",
            "CALL apoc.refactor.rename.label('Old', 'New')",
            "call APOC.CREATE.node(['L'], {})",  # Case insensitive
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query: {query}"
            assert "procedure" in result.lower()

    def test_read_only_allows_safe_procedures(self):
        """Safe read-only procedures should be allowed."""
        queries = [
            "CALL db.labels()",
            "CALL db.relationshipTypes()",
            "CALL dbms.components()",
            "CALL apoc.help('text')",
            "CALL apoc.meta.graph()",
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is None, f"Expected None for safe procedure: {query}"

    def test_whitespace_normalization(self):
        """Whitespace variations should not bypass read-only checks."""
        queries = [
            "CREATE\n(n:Person)",
            "CREATE\t(n:Person)",
            "CREATE  (n:Person)",  # Multiple spaces
            "  CREATE (n:Person)  ",  # Leading/trailing whitespace
            "MATCH (n)\nCREATE (m)",
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is not None, f"Expected error for query with whitespace: {query}"
            assert "CREATE" in result

    def test_word_boundary_matching(self):
        """Write keywords should only match whole words, not parts of identifiers."""
        # These queries contain words that include write keywords but are not write operations
        queries = [
            "MATCH (n:Recreate) RETURN n",  # "Recreate" contains "CREATE"
            "MATCH (n) WHERE n.name = 'CREATED' RETURN n",  # String contains "CREATE"
            "MATCH (n {deleted: false}) RETURN n",  # Property name contains "DELETE"
        ]

        for query in queries:
            result = check_read_only_access(query, read_only_mode=True)
            assert result is None, f"Expected None for query with embedded keyword: {query}"

    def test_default_parameter_value(self):
        """read_only_mode should default to False."""
        # When read_only_mode is not specified, it should default to False
        result = check_read_only_access("CREATE (n:Person)")
        assert result is None

    def test_explicit_false_parameter(self):
        """Explicitly passing read_only_mode=False should allow writes."""
        result = check_read_only_access("CREATE (n:Person)", read_only_mode=False)
        assert result is None

    def test_explicit_true_parameter(self):
        """Explicitly passing read_only_mode=True should block writes."""
        result = check_read_only_access("CREATE (n:Person)", read_only_mode=True)
        assert result is not None
        assert "CREATE" in result

    def test_empty_query(self):
        """Empty queries should be allowed."""
        result = check_read_only_access("", read_only_mode=True)
        assert result is None

    def test_whitespace_only_query(self):
        """Whitespace-only queries should be allowed."""
        result = check_read_only_access("   \n\t  ", read_only_mode=True)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
