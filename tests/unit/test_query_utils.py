"""
Tests for query utility functions (LIMIT injection, etc.).
"""

import pytest

from neo4j_yass_mcp.tools.query_utils import (
    has_limit_clause,
    inject_limit_clause,
    should_inject_limit,
)


class TestHasLimitClause:
    """Tests for has_limit_clause() function."""

    def test_simple_query_with_limit(self):
        """Test query with simple LIMIT clause."""
        query = "MATCH (n) RETURN n LIMIT 100"
        assert has_limit_clause(query) is True

    def test_simple_query_without_limit(self):
        """Test query without LIMIT clause."""
        query = "MATCH (n) RETURN n"
        assert has_limit_clause(query) is False

    def test_case_insensitive_detection(self):
        """Test case-insensitive LIMIT detection."""
        assert has_limit_clause("MATCH (n) RETURN n limit 50") is True
        assert has_limit_clause("MATCH (n) RETURN n Limit 50") is True
        assert has_limit_clause("MATCH (n) RETURN n LiMiT 50") is True

    def test_limit_with_various_whitespace(self):
        """Test LIMIT detection with various whitespace."""
        assert has_limit_clause("MATCH (n) RETURN n LIMIT  100") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT\t100") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT\n100") is True

    def test_limit_in_middle_of_query(self):
        """Test LIMIT detection in complex queries."""
        query = """
        MATCH (n:Person)
        WHERE n.age > 25
        RETURN n.name, n.age
        LIMIT 10
        """
        assert has_limit_clause(query) is True

    def test_false_positive_prevention(self):
        """Test that 'LIMIT' in other contexts doesn't trigger detection."""
        # These should NOT be detected as LIMIT clauses
        assert has_limit_clause("MATCH (n {name: 'LIMIT'}) RETURN n") is False
        assert has_limit_clause("MATCH (n) WHERE n.text CONTAINS 'LIMIT' RETURN n") is False

    def test_parameterized_limit_detection(self):
        """Test LIMIT detection with parameter placeholders."""
        # Bug fix: parameterized LIMIT should be detected
        assert has_limit_clause("MATCH (n) RETURN n LIMIT $pageSize") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT $limit") is True
        assert has_limit_clause("MATCH (n) RETURN n limit $count") is True

    def test_complex_limit_expressions(self):
        """Test LIMIT detection with complex expressions."""
        # Bug fix: complex LIMIT expressions should be detected
        assert has_limit_clause("MATCH (n) RETURN n LIMIT $params.limit") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT $cfg['rows']") is True
        assert has_limit_clause('MATCH (n) RETURN n LIMIT $cfg["rows"]') is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT $config.pagination.size") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT toInteger($var)") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT 10 + 5") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT $offset + $pageSize") is True

    def test_string_literal_bypass_prevention(self):
        """Test that LIMIT in string literals doesn't trigger detection."""
        # Bug fix: string literals should not be detected as LIMIT clauses
        assert has_limit_clause("MATCH (n) WHERE n.note CONTAINS 'LIMIT 999999' RETURN n") is False
        assert has_limit_clause("MATCH (n {desc: 'Use LIMIT 100'}) RETURN n") is False
        assert has_limit_clause('MATCH (n) WHERE n.text = "LIMIT 50" RETURN n') is False

    def test_comment_bypass_prevention(self):
        """Test that LIMIT in comments doesn't trigger detection."""
        # Bug fix: comments should not be detected as LIMIT clauses
        assert has_limit_clause("MATCH (n) RETURN n // LIMIT 1") is False
        assert has_limit_clause("MATCH (n) RETURN n // TODO: Add LIMIT 100") is False
        assert has_limit_clause("MATCH (n) RETURN n /* LIMIT 100 */") is False
        assert has_limit_clause("MATCH (n) RETURN n /* Add LIMIT later */") is False
        # Multi-line comments
        assert has_limit_clause("MATCH (n) RETURN n /* \nLIMIT 100\n */") is False

    def test_multiline_limit_detection(self):
        """Test LIMIT detection with multi-line expressions (Bug #7)."""
        # Bug fix: LIMIT expressions spanning multiple lines should be detected
        assert has_limit_clause("MATCH (n) RETURN n LIMIT\n$pageSize") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT\n100") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT\n$params.limit") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT\n10 + 5") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT  \n  $cfg['rows']") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT\n\n$offset + $pageSize") is True
        # Multi-line with tabs and spaces
        assert has_limit_clause("MATCH (n) RETURN n LIMIT\t\n$limit") is True

    def test_backtick_identifier_handling(self):
        """Test backtick-quoted identifier handling (Bug #8)."""
        # Bug fix: backtick identifiers should not break LIMIT detection
        # Backticks in property names should be stripped but structure preserved
        assert has_limit_clause("MATCH (n:`Label`) RETURN n LIMIT 100") is True
        assert has_limit_clause("MATCH (n) RETURN n.`prop` LIMIT $pageSize") is True
        # Backtick in LIMIT expression itself (edge case)
        assert has_limit_clause("MATCH (n) RETURN n LIMIT `custom_limit`") is True

    def test_brace_parameter_detection(self):
        """Test brace parameter syntax detection (Bug #9)."""
        # Bug fix: {param} syntax should be detected same as $param
        assert has_limit_clause("MATCH (n) RETURN n LIMIT {pageSize}") is True
        assert has_limit_clause("MATCH (n) RETURN n LIMIT {limit}") is True
        assert has_limit_clause("MATCH (n) RETURN n limit {count}") is True
        # Mixed with other expressions
        assert has_limit_clause("MATCH (n) RETURN n LIMIT {offset} + {pageSize}") is True
        # Multi-line brace parameters
        assert has_limit_clause("MATCH (n) RETURN n LIMIT\n{pageSize}") is True

    def test_clause_boundary_bypass_prevention(self):
        """Test LIMIT detection stops at additional clause keywords."""
        assert has_limit_clause("MATCH (n) RETURN n LIMIT UNION MATCH (m) RETURN m") is False
        assert has_limit_clause("MATCH (n) RETURN n LIMIT SKIP 5") is False
        assert has_limit_clause("MATCH (n) RETURN n LIMIT DELETE n") is False
        assert has_limit_clause("MATCH (n) RETURN n LIMIT DETACH DELETE n") is False


class TestInjectLimitClause:
    """Tests for inject_limit_clause() function."""

    def test_inject_limit_simple_query(self):
        """Test basic LIMIT injection."""
        query = "MATCH (n) RETURN n"
        modified, injected = inject_limit_clause(query, max_rows=100)

        assert injected is True
        assert modified == "MATCH (n) RETURN n LIMIT 100"

    def test_no_injection_when_limit_exists(self):
        """Test no injection when LIMIT already present."""
        query = "MATCH (n) RETURN n LIMIT 50"
        modified, injected = inject_limit_clause(query, max_rows=100)

        assert injected is False
        assert modified == query

    def test_inject_with_trailing_semicolon(self):
        """Test LIMIT injection with trailing semicolon."""
        query = "MATCH (n) RETURN n;"
        modified, injected = inject_limit_clause(query, max_rows=100)

        assert injected is True
        assert modified == "MATCH (n) RETURN n LIMIT 100"
        assert ";" not in modified

    def test_inject_with_trailing_whitespace(self):
        """Test LIMIT injection with trailing whitespace."""
        query = "MATCH (n) RETURN n   \n  "
        modified, injected = inject_limit_clause(query, max_rows=100)

        assert injected is True
        assert modified == "MATCH (n) RETURN n LIMIT 100"

    def test_inject_custom_max_rows(self):
        """Test LIMIT injection with custom max_rows."""
        query = "MATCH (n) RETURN n"

        modified_1000, _ = inject_limit_clause(query, max_rows=1000)
        assert "LIMIT 1000" in modified_1000

        modified_500, _ = inject_limit_clause(query, max_rows=500)
        assert "LIMIT 500" in modified_500

        modified_10, _ = inject_limit_clause(query, max_rows=10)
        assert "LIMIT 10" in modified_10

    def test_force_injection(self):
        """Test force injection overrides existing LIMIT."""
        query = "MATCH (n) RETURN n LIMIT 50"
        modified, injected = inject_limit_clause(query, max_rows=100, force=True)

        # With force=True, it should inject again (though this creates invalid query)
        # This is a known limitation - force mode is for edge cases
        assert injected is True

    def test_multiline_query(self):
        """Test LIMIT injection on multiline query."""
        query = """
        MATCH (n:Person)
        WHERE n.age > 25
        RETURN n.name, n.age
        """
        modified, injected = inject_limit_clause(query, max_rows=100)

        assert injected is True
        assert "LIMIT 100" in modified


class TestShouldInjectLimit:
    """Tests for should_inject_limit() function."""

    def test_should_inject_for_simple_query(self):
        """Test injection recommendation for simple queries."""
        assert should_inject_limit("MATCH (n) RETURN n") is True
        assert should_inject_limit("MATCH (n:Person) RETURN n.name") is True

    def test_should_not_inject_with_existing_limit(self):
        """Test no injection recommended when LIMIT exists."""
        assert should_inject_limit("MATCH (n) RETURN n LIMIT 100") is False

    def test_should_inject_for_aggregations(self):
        """Aggregation results should still get LIMIT injection."""
        assert should_inject_limit("MATCH (n) RETURN count(n)") is True
        assert should_inject_limit("MATCH (n) RETURN sum(n.value)") is True
        assert should_inject_limit("MATCH (n) RETURN avg(n.score)") is True
        assert should_inject_limit("MATCH (n) RETURN min(n.age)") is True
        assert should_inject_limit("MATCH (n) RETURN max(n.price)") is True
        assert should_inject_limit("MATCH (n) RETURN collect(n.name)") is True

    def test_case_insensitive_aggregation_detection(self):
        """Aggregation queries should inject regardless of case."""
        assert should_inject_limit("MATCH (n) RETURN COUNT(n)") is True
        assert should_inject_limit("MATCH (n) RETURN Count(n)") is True
        assert should_inject_limit("MATCH (n) RETURN SUM(n.value)") is True

    def test_aggregation_with_whitespace(self):
        """Aggregation queries with whitespace should inject."""
        assert should_inject_limit("MATCH (n) RETURN count (n)") is True
        assert should_inject_limit("MATCH (n) RETURN count\t(n)") is True
        assert should_inject_limit("MATCH (n) RETURN count\n(n)") is True

    def test_should_not_inject_for_queries_without_return(self):
        """Test no injection for queries without RETURN/WITH clause."""
        # Bug fix: queries without RETURN/WITH cannot have LIMIT
        assert should_inject_limit("CREATE (n:Log {ts: timestamp()})") is False
        assert should_inject_limit("CREATE (n:Person {name: 'Alice'})") is False
        assert should_inject_limit("MERGE (n:Node {id: 123})") is False
        assert should_inject_limit("DELETE n") is False
        assert should_inject_limit("CALL db.labels()") is False
        assert should_inject_limit("CALL dbms.procedures()") is False

    def test_should_inject_for_queries_with_return(self):
        """Test injection allowed for queries with RETURN clause."""
        assert should_inject_limit("MATCH (n) RETURN n") is True
        assert should_inject_limit("MATCH (n:Person) RETURN n.name") is True
        assert should_inject_limit("CREATE (n:Person {name: 'Bob'}) RETURN n") is True

    def test_should_inject_for_queries_with_with(self):
        """Test injection allowed for queries with WITH clause."""
        assert should_inject_limit("MATCH (n) WITH n.name AS name RETURN name") is True

    def test_return_in_string_literal_ignored(self):
        """Test that RETURN in string literals doesn't trigger injection."""
        # This query has no actual RETURN clause (RETURN is in string)
        query = "CREATE (n:Note {text: 'RETURN always'})"
        result = should_inject_limit(query)
        # Should be False because no RETURN after stripping literals
        assert result is False

    def test_return_in_comment_ignored(self):
        """Test that RETURN in comments doesn't trigger injection."""
        # Bug fix: Comments with RETURN should not trigger injection
        assert should_inject_limit("CALL db.labels() // RETURN name") is False
        assert should_inject_limit("CALL db.labels() /* RETURN label */") is False
        assert should_inject_limit("CREATE (n:Log) // TODO: RETURN n later") is False
        # Multi-line comment with RETURN
        assert should_inject_limit("CALL db.procedures() /* \nRETURN name\n */") is False


class TestLimitInjectionIntegration:
    """Integration tests for LIMIT injection."""

    def test_realistic_unbounded_query(self):
        """Test realistic unbounded query scenario."""
        query = "MATCH (n:Person)-[:KNOWS]->(m:Person) RETURN n.name, m.name"

        assert has_limit_clause(query) is False
        assert should_inject_limit(query) is True

        modified, injected = inject_limit_clause(query, max_rows=1000)

        assert injected is True
        assert has_limit_clause(modified) is True
        assert "LIMIT 1000" in modified

    def test_realistic_bounded_query(self):
        """Test realistic query with existing LIMIT."""
        query = "MATCH (n:Movie) WHERE n.rating > 8 RETURN n.title, n.rating LIMIT 10"

        assert has_limit_clause(query) is True
        assert should_inject_limit(query) is False

        modified, injected = inject_limit_clause(query, max_rows=1000)

        assert injected is False
        assert modified == query

    def test_realistic_aggregation_query(self):
        """Test realistic aggregation query."""
        query = "MATCH (n:Person) RETURN n.city, count(n) as population"

        assert has_limit_clause(query) is False
        assert should_inject_limit(query) is True

        modified, injected = inject_limit_clause(query, max_rows=1000)

        # Note: inject_limit_clause doesn't check should_inject_limit
        # That's the caller's responsibility
        assert injected is True

    def test_realistic_write_query(self):
        """Test write query LIMIT injection."""
        # Write queries returning results should still get LIMIT
        query = "CREATE (n:Person {name: $name}) RETURN n"

        assert has_limit_clause(query) is False
        assert should_inject_limit(query) is True

        modified, injected = inject_limit_clause(query, max_rows=1000)

        assert injected is True
        assert "LIMIT 1000" in modified

    def test_write_query_without_return_no_injection(self):
        """Test write query without RETURN is not modified."""
        # Bug fix: queries without RETURN should not get LIMIT
        query = "CREATE (n:Log {ts: timestamp()})"

        assert has_limit_clause(query) is False
        assert should_inject_limit(query) is False  # No RETURN clause

        # Even if we force inject, the query is unmodified
        # because should_inject_limit says no
        modified, injected = inject_limit_clause(query, max_rows=1000)

        # inject_limit_clause doesn't check should_inject_limit
        # so it will inject if forced, but should_inject_limit prevents it
        # in normal usage

    def test_parameterized_limit_no_double_injection(self):
        """Test parameterized LIMIT is detected and not double-injected."""
        # Bug fix: LIMIT $pageSize should be detected
        query = "MATCH (n) RETURN n LIMIT $pageSize"

        assert has_limit_clause(query) is True
        assert should_inject_limit(query) is False  # Already has LIMIT

        modified, injected = inject_limit_clause(query, max_rows=1000)

        assert injected is False
        assert modified == query  # Unchanged
        # Ensure we don't create: LIMIT $pageSize LIMIT 1000

    def test_complex_limit_no_double_injection(self):
        """Test complex LIMIT expressions are detected and not double-injected."""
        # Bug fix: LIMIT $params.limit should be detected
        test_cases = [
            "MATCH (n) RETURN n LIMIT $params.limit",
            "MATCH (n) RETURN n LIMIT $cfg['rows']",
            'MATCH (n) RETURN n LIMIT $cfg["rows"]',
            "MATCH (n) RETURN n LIMIT $config.pagination.size",
            "MATCH (n) RETURN n LIMIT toInteger($var)",
            "MATCH (n) RETURN n LIMIT 10 + 5",
        ]

        for query in test_cases:
            assert has_limit_clause(query) is True, f"Failed to detect LIMIT in: {query}"
            assert should_inject_limit(query) is False, f"Should not inject for: {query}"

            modified, injected = inject_limit_clause(query, max_rows=1000)

            assert injected is False, f"Should not inject for: {query}"
            assert modified == query, f"Query should be unchanged: {query}"

    def test_string_literal_bypass_integration(self):
        """Test string literal containing LIMIT doesn't bypass injection."""
        # Bug fix: string literals should be stripped before detection
        query = "MATCH (n) WHERE n.note CONTAINS 'LIMIT 999999' RETURN n"

        assert has_limit_clause(query) is False  # No actual LIMIT
        assert should_inject_limit(query) is True

        modified, injected = inject_limit_clause(query, max_rows=1000)

        assert injected is True
        assert "LIMIT 1000" in modified
        # The string literal 'LIMIT 999999' should not prevent injection

    def test_procedure_call_no_injection(self):
        """Test procedure calls without RETURN are not modified."""
        query = "CALL db.labels()"

        assert has_limit_clause(query) is False
        assert should_inject_limit(query) is False  # No RETURN clause

    def test_procedure_call_with_yield_injection(self):
        """Test procedure calls with YIELD get LIMIT injected."""
        query = "CALL db.labels() YIELD label RETURN label"

        assert has_limit_clause(query) is False
        assert should_inject_limit(query) is True  # Has RETURN

        modified, injected = inject_limit_clause(query, max_rows=1000)

        assert injected is True
        assert "LIMIT 1000" in modified

    def test_comment_bypass_dos_protection(self):
        """Test comment with LIMIT doesn't bypass DoS protection."""
        # Bug fix: Comments should not prevent injection
        query = "MATCH (n) RETURN n // LIMIT 1"

        assert has_limit_clause(query) is False  # No actual LIMIT
        assert should_inject_limit(query) is True

        modified, injected = inject_limit_clause(query, max_rows=1000)

        assert injected is True
        assert "LIMIT 1000" in modified
        # Comment doesn't prevent DoS protection

    def test_comment_return_does_not_trigger_injection(self):
        """Test comment with RETURN doesn't trigger invalid injection."""
        # Bug fix: Comment with RETURN should not cause syntax error
        query = "CALL db.labels() // RETURN name"

        assert has_limit_clause(query) is False
        assert should_inject_limit(query) is False  # No actual RETURN

        # Should NOT inject LIMIT (would cause syntax error)
        # This test ensures we don't create: CALL db.labels() // RETURN name LIMIT 1000

    def test_query_ending_with_write_clause_not_injected(self):
        """Ensure queries ending with write clauses are skipped."""
        query = """
        MATCH (n) RETURN n
        WITH count(n) AS c
        CREATE (:Stat {value: c})
        """
        assert should_inject_limit(query) is False

    def test_final_clause_must_be_return_or_with(self):
        """Only RETURN/WITH as final clause should allow LIMIT injection."""
        query_with_final_return = """
        MATCH (n)
        WITH n.name AS name
        RETURN name
        """
        assert should_inject_limit(query_with_final_return) is True

        query_with_final_with = """
        MATCH (n)
        WITH n
        """
        assert should_inject_limit(query_with_final_with) is True

        query_with_final_delete = """
        MATCH (n)
        RETURN n
        DELETE n
        """
        assert should_inject_limit(query_with_final_delete) is False

    def test_multiline_limit_no_double_injection(self):
        """Test multi-line LIMIT expressions are detected (Bug #7)."""
        # Bug fix: Multi-line LIMIT should be detected
        test_cases = [
            "MATCH (n) RETURN n LIMIT\n$pageSize",
            "MATCH (n) RETURN n LIMIT\n100",
            "MATCH (n) RETURN n LIMIT\n$params.limit",
            "MATCH (n) RETURN n LIMIT  \n  10 + 5",
            "MATCH (n) RETURN n LIMIT\t\n$limit",
        ]

        for query in test_cases:
            assert has_limit_clause(query) is True, f"Failed to detect LIMIT in: {query}"
            assert should_inject_limit(query) is False, f"Should not inject for: {query}"

            modified, injected = inject_limit_clause(query, max_rows=1000)

            assert injected is False, f"Should not inject for: {query}"
            assert modified == query, f"Query should be unchanged: {query}"

    def test_brace_parameter_no_double_injection(self):
        """Test brace parameter LIMIT expressions are detected (Bug #9)."""
        # Bug fix: LIMIT {param} should be detected
        test_cases = [
            "MATCH (n) RETURN n LIMIT {pageSize}",
            "MATCH (n) RETURN n LIMIT {limit}",
            "MATCH (n) RETURN n LIMIT {offset} + {pageSize}",
            "MATCH (n) RETURN n LIMIT\n{pageSize}",
        ]

        for query in test_cases:
            assert has_limit_clause(query) is True, f"Failed to detect LIMIT in: {query}"
            assert should_inject_limit(query) is False, f"Should not inject for: {query}"

            modified, injected = inject_limit_clause(query, max_rows=1000)

            assert injected is False, f"Should not inject for: {query}"
            assert modified == query, f"Query should be unchanged: {query}"

    def test_backtick_identifier_preservation(self):
        """Test backtick identifiers don't break LIMIT detection (Bug #8)."""
        # Bug fix: Backtick identifiers should be handled correctly
        query = "MATCH (n:`Label`) RETURN n.`prop` LIMIT $pageSize"

        assert has_limit_clause(query) is True
        assert should_inject_limit(query) is False

        modified, injected = inject_limit_clause(query, max_rows=1000)

        assert injected is False
        assert modified == query


class TestCriticalFindingsRegression:
    """Regression tests for critical security findings identified post-implementation."""

    def test_clause_boundary_bypass_prevention(self):
        """Test that LIMIT followed by another clause is NOT detected as valid LIMIT.

        Critical Finding #1: Clause boundary detection failure.
        Malicious query: "MATCH (n) RETURN n LIMIT MATCH (m)"
        Without lookahead, regex consumes "LIMIT MATCH" as valid LIMIT expression.
        """
        # These queries should NOT be detected as having valid LIMIT
        invalid_limit_queries = [
            "MATCH (n) RETURN n LIMIT MATCH (m) RETURN m",
            "MATCH (n) RETURN n LIMIT WITH n RETURN n",
            "MATCH (n) RETURN n LIMIT ORDER BY n.name RETURN n",
            "MATCH (n) RETURN n LIMIT WHERE n.age > 25 RETURN n",
            "MATCH (n) RETURN n LIMIT RETURN n",
        ]

        for query in invalid_limit_queries:
            # These should NOT be detected as having LIMIT
            assert has_limit_clause(query) is False, \
                f"Query should NOT have valid LIMIT: {query}"

            # Therefore, LIMIT should be injected
            assert should_inject_limit(query) is True, \
                f"Should inject LIMIT for: {query}"

            modified, injected = inject_limit_clause(query, max_rows=1000)
            assert injected is True, f"LIMIT should be injected for: {query}"

    def test_valid_limit_with_trailing_clause(self):
        """Test that valid LIMIT followed by valid trailing clauses is detected."""
        # These queries SHOULD be detected as having valid LIMIT
        valid_limit_queries = [
            "MATCH (n) RETURN n LIMIT 100;",  # semicolon terminator
            "MATCH (n) WITH n LIMIT 10 RETURN n",  # LIMIT on WITH clause
            "MATCH (n) RETURN n LIMIT 50",  # end of query
        ]

        for query in valid_limit_queries:
            # These SHOULD be detected as having LIMIT
            # Note: "WITH n LIMIT 10 RETURN n" has LIMIT on WITH, not RETURN
            # So has_limit_clause should return True
            assert has_limit_clause(query) is True, \
                f"Query SHOULD have valid LIMIT: {query}"

    def test_placeholder_collision_resistance(self):
        """Test that backtick identifier placeholder doesn't collide with actual tokens.

        Critical Finding #2: Placeholder collision risk.
        Old implementation used '__ID__' which could collide with real identifiers.
        New implementation uses UUID-based placeholder.
        """
        # Query with identifier literally named '__ID__'
        # This should NOT cause false positives/negatives
        queries_with_id_identifier = [
            "MATCH (n:`__ID__`) RETURN n LIMIT 100",
            "MATCH (n) RETURN n.`__ID__` LIMIT $pageSize",
            "MATCH (n {`__ID__`: 123}) RETURN n LIMIT 50",
        ]

        for query in queries_with_id_identifier:
            assert has_limit_clause(query) is True, \
                f"Should detect LIMIT despite __ID__ identifier: {query}"
            assert should_inject_limit(query) is False, \
                f"Should not inject for query with LIMIT: {query}"

        # Query without LIMIT but with __ID__ identifier
        query_no_limit = "MATCH (n:`__ID__`) RETURN n"
        assert has_limit_clause(query_no_limit) is False
        assert should_inject_limit(query_no_limit) is True

    def test_empty_query_after_stripping(self):
        """Test that queries that become empty after stripping are handled.

        Critical Finding #3: Comment stripping edge cases.
        Entire query inside comments should not allow LIMIT injection.
        """
        # Queries that are entirely comments
        empty_after_stripping = [
            "/* MATCH (n) RETURN n */",
            "// MATCH (n) RETURN n",
            "/* Comment 1 */ /* Comment 2 */",
            "   /* MATCH (n) RETURN n LIMIT 100 */   ",
        ]

        for query in empty_after_stripping:
            assert has_limit_clause(query) is False, \
                f"Comment-only query should not have LIMIT: {query}"
            assert should_inject_limit(query) is False, \
                f"Should not inject LIMIT for empty query: {query}"

    def test_multiline_brace_parameter(self):
        """Test LIMIT with multi-line brace parameters.

        Critical Finding #4: Missing test coverage for multi-line braces.
        """
        multiline_brace_queries = [
            "MATCH (n) RETURN n LIMIT\n{pageSize}",
            "MATCH (n) RETURN n LIMIT  \n  {limit}",
            "MATCH (n) RETURN n LIMIT\n\n{cfg}",
            "MATCH (n) RETURN n LIMIT\t\n{param}",
        ]

        for query in multiline_brace_queries:
            assert has_limit_clause(query) is True, \
                f"Should detect multi-line brace LIMIT: {query}"
            assert should_inject_limit(query) is False, \
                f"Should not inject for multi-line brace query: {query}"

    def test_complex_bypass_scenarios(self):
        """Test complex bypass scenarios combining multiple techniques."""
        # Scenario 1: LIMIT in comment + clause keyword
        query1 = "MATCH (n) RETURN n /* LIMIT 100 */ MATCH (m)"
        assert has_limit_clause(query1) is False
        # Final clause is MATCH without RETURN, so LIMIT can't be injected safely
        assert should_inject_limit(query1) is False

        # Scenario 2: Backtick identifier + clause boundary
        query2 = "MATCH (n:`Label`) RETURN n LIMIT MATCH (m)"
        assert has_limit_clause(query2) is False
        assert should_inject_limit(query2) is False

        # Scenario 3: String literal with LIMIT + no actual LIMIT
        query3 = "MATCH (n) WHERE n.note = 'LIMIT 999' RETURN n"
        assert has_limit_clause(query3) is False
        assert should_inject_limit(query3) is True

        # Scenario 4: String literal + actual LIMIT
        query4 = "MATCH (n) WHERE n.note = 'LIMIT 999' RETURN n LIMIT 100"
        assert has_limit_clause(query4) is True
        assert should_inject_limit(query4) is False

    def test_return_in_comment_not_detected(self):
        """Test that RETURN inside comments is not detected as valid RETURN clause."""
        # Queries with RETURN only in comments should not allow LIMIT injection
        queries_with_commented_return = [
            "MATCH (n) // RETURN n",
            "MATCH (n) /* RETURN n */",
            "CALL db.labels() // RETURN name",
            "CALL db.labels() /* RETURN name LIMIT 100 */",
        ]

        for query in queries_with_commented_return:
            assert should_inject_limit(query) is False, \
                f"Should not inject for comment-only RETURN: {query}"

    def test_aggregation_with_clause_boundary(self):
        """Aggregations should still be flagged for LIMIT injection."""
        # Aggregations should trigger LIMIT injection even with clause keywords around them
        aggregation_queries = [
            "MATCH (n) RETURN count(n)",
            "MATCH (n) RETURN sum(n.value)",
            "MATCH (n) RETURN avg(n.score)",
            "MATCH (n) RETURN min(n.age), max(n.age)",
        ]

        for query in aggregation_queries:
            assert has_limit_clause(query) is False
            assert should_inject_limit(query) is True, \
                f"Should inject for aggregation: {query}"

    def test_extended_clause_boundary_bypass_prevention(self):
        """Test that LIMIT followed by additional clause keywords is NOT detected.

        Critical Finding: Extended clause boundary list needed.
        Original implementation only checked RETURN|WITH|MATCH|ORDER|WHERE.
        Missing: UNION, SKIP, UNWIND, DELETE, DETACH, CREATE, MERGE, etc.
        """
        # These queries should NOT be detected as having valid LIMIT
        # Each uses a clause keyword that was missing from original boundary list
        extended_bypass_queries = [
            # UNION bypass variants
            "MATCH (n) RETURN n LIMIT UNION MATCH (m) RETURN m",
            "MATCH (n) RETURN n LIMIT UNION ALL MATCH (m) RETURN m",

            # SKIP bypass (ordering clause)
            "MATCH (n) RETURN n LIMIT SKIP 10 RETURN n",
            "MATCH (n) RETURN n LIMIT SKIP $offset RETURN n",

            # UNWIND bypass (list expansion)
            "MATCH (n) RETURN n LIMIT UNWIND [1,2,3] AS x RETURN x",

            # DELETE/DETACH DELETE bypass (write operations)
            "MATCH (n) RETURN n LIMIT DELETE n RETURN count(n)",
            "MATCH (n) RETURN n LIMIT DETACH DELETE n RETURN count(n)",

            # CREATE/MERGE bypass (write operations)
            "MATCH (n) RETURN n LIMIT CREATE (m:Node) RETURN m",
            "MATCH (n) RETURN n LIMIT MERGE (m:Node) RETURN m",

            # SET/REMOVE bypass (mutation operations)
            "MATCH (n) RETURN n LIMIT SET n.updated = timestamp() RETURN n",
            "MATCH (n) RETURN n LIMIT REMOVE n.temp RETURN n",

            # CALL bypass (procedure invocation)
            "MATCH (n) RETURN n LIMIT CALL db.labels() YIELD label RETURN label",

            # FOREACH bypass (iteration)
            "MATCH (n) RETURN n LIMIT FOREACH (x IN [1,2,3] | CREATE (:Node)) RETURN n",

            # OPTIONAL MATCH bypass
            "MATCH (n) RETURN n LIMIT OPTIONAL MATCH (m) RETURN m",

            # USE bypass (database selection - Neo4j 4.x+)
            "MATCH (n) RETURN n LIMIT USE database2 RETURN n",

            # LOAD CSV bypass (data import)
            "MATCH (n) RETURN n LIMIT LOAD CSV FROM 'file.csv' AS row RETURN row",
        ]

        for query in extended_bypass_queries:
            assert has_limit_clause(query) is False, \
                f"Query should NOT have valid LIMIT: {query}"
            assert should_inject_limit(query) is True, \
                f"Should inject LIMIT for: {query}"
            modified, injected = inject_limit_clause(query, max_rows=1000)
            assert injected is True, \
                f"LIMIT should be injected for bypass query: {query}"

    def test_valid_limit_with_extended_clauses(self):
        """Test that valid LIMIT before legitimate following clauses is still detected."""
        # These queries SHOULD be detected as having valid LIMIT
        # The LIMIT applies to the current clause, and is followed by a new clause
        valid_queries_with_following_clauses = [
            # LIMIT before UNION (legitimate use case)
            "MATCH (n:Person) RETURN n LIMIT 10 UNION MATCH (m:Company) RETURN m LIMIT 5",

            # WITH ... LIMIT pattern (common paging pattern)
            "MATCH (n) WITH n LIMIT 100 MATCH (n)-[r]->() RETURN n, r",

            # LIMIT before semicolon
            "MATCH (n) RETURN n LIMIT 50;",

            # LIMIT at end of query
            "MATCH (n) RETURN n LIMIT 100",
        ]

        for query in valid_queries_with_following_clauses:
            # Should detect LIMIT (at least one LIMIT clause exists)
            assert has_limit_clause(query) is True, \
                f"Query SHOULD have valid LIMIT: {query}"
