"""
Comprehensive tests for query complexity limiter.

Tests cover complexity scoring, limit enforcement, and various query patterns.
"""

import pytest

from neo4j_yass_mcp.security.complexity_limiter import (
    QueryComplexityAnalyzer,
    check_query_complexity,
    initialize_complexity_limiter,
)


class TestComplexityScoring:
    """Test complexity scoring for various query patterns."""

    def test_simple_match_query(self):
        """Test simple MATCH query has low complexity."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query = "MATCH (n:Person) RETURN n LIMIT 10"
        score = analyzer.analyze_query(query)

        # Should have low complexity (base MATCH + has LIMIT)
        assert score.total_score < 30
        assert score.is_within_limit is True
        assert "match_clauses" in score.breakdown

    def test_cartesian_product_detection(self):
        """Test Cartesian product increases complexity."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        # Query with potential Cartesian product
        query = """
        MATCH (p:Person)
        MATCH (m:Movie)
        RETURN p, m
        """
        score = analyzer.analyze_query(query)

        # Should detect Cartesian product risk
        assert "cartesian_product_risk" in score.breakdown
        assert score.breakdown["cartesian_product_risk"] == 50
        assert any("Cartesian product" in w for w in score.warnings)

    def test_variable_length_pattern(self):
        """Test variable-length pattern scoring."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100, max_variable_path_length=10)

        query = "MATCH (a)-[*1..5]->(b) RETURN a, b"
        score = analyzer.analyze_query(query)

        # Should score variable-length pattern
        assert "variable_length_patterns" in score.breakdown
        assert score.breakdown["variable_length_patterns"] == 10  # 1 pattern * 10

    def test_unbounded_variable_pattern(self):
        """Test unbounded variable-length pattern."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query = "MATCH (a)-[*]->(b) RETURN a, b"
        score = analyzer.analyze_query(query)

        # Should penalize unbounded pattern
        assert "unbounded_patterns" in score.breakdown
        assert score.breakdown["unbounded_patterns"] == 25
        assert any("unbounded" in w.lower() for w in score.warnings)

    def test_excessive_variable_path_length(self):
        """Test excessive variable path length detection."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100, max_variable_path_length=5)

        query = "MATCH (a)-[*1..20]->(b) RETURN a, b"
        score = analyzer.analyze_query(query)

        # Should detect excessive path length
        assert "excessive_variable_path" in score.breakdown
        assert any("exceeds limit" in w for w in score.warnings)

    def test_missing_limit_on_unbounded_query(self):
        """Test penalty for missing LIMIT on unbounded query."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100, require_limit_unbounded=True)

        query = "MATCH (n:Person) RETURN n"
        score = analyzer.analyze_query(query)

        # Should penalize missing LIMIT
        assert "missing_limit" in score.breakdown
        assert score.breakdown["missing_limit"] == 20
        assert any("without LIMIT" in w for w in score.warnings)

    def test_query_with_limit(self):
        """Test query with LIMIT doesn't get penalized."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100, require_limit_unbounded=True)

        query = "MATCH (n:Person) RETURN n LIMIT 100"
        score = analyzer.analyze_query(query)

        # Should NOT have missing_limit penalty
        assert "missing_limit" not in score.breakdown

    def test_with_clauses(self):
        """Test WITH clause complexity."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query = """
        MATCH (p:Person)
        WITH p, p.age AS age
        WHERE age > 30
        WITH p
        RETURN p
        """
        score = analyzer.analyze_query(query)

        # Should score WITH clauses
        assert "with_clauses" in score.breakdown
        assert score.breakdown["with_clauses"] == 10  # 2 WITH * 5

    def test_subqueries(self):
        """Test CALL subquery complexity."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query = """
        MATCH (p:Person)
        CALL {
            MATCH (m:Movie)
            RETURN m
        }
        RETURN p, m
        """
        score = analyzer.analyze_query(query)

        # Should score subqueries
        assert "call_subqueries" in score.breakdown
        assert score.breakdown["call_subqueries"] == 15  # 1 CALL * 15

    def test_multiple_subqueries(self):
        """Test multiple CALL subqueries trigger warning."""
        analyzer = QueryComplexityAnalyzer(max_complexity=200)

        query = """
        CALL { MATCH (n) RETURN n }
        CALL { MATCH (m) RETURN m }
        CALL { MATCH (p) RETURN p }
        CALL { MATCH (q) RETURN q }
        RETURN *
        """
        score = analyzer.analyze_query(query)

        # Should warn about high nesting
        assert any("High subquery nesting" in w for w in score.warnings)

    def test_aggregation_complexity(self):
        """Test aggregation function complexity."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query = """
        MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
        RETURN p.name, COUNT(m) AS movie_count, AVG(m.rating) AS avg_rating
        """
        score = analyzer.analyze_query(query)

        # Should score aggregations
        assert "aggregations" in score.breakdown
        assert score.breakdown["aggregations"] == 6  # 2 aggregations * 3

    def test_union_operations(self):
        """Test UNION operation complexity."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query = """
        MATCH (p:Person) RETURN p.name
        UNION
        MATCH (m:Movie) RETURN m.title AS name
        """
        score = analyzer.analyze_query(query)

        # Should score UNION
        assert "union_operations" in score.breakdown
        assert score.breakdown["union_operations"] == 10  # 1 UNION * 10

    def test_optional_match(self):
        """Test OPTIONAL MATCH complexity."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query = """
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[:DIRECTED]->(m:Movie)
        RETURN p, m
        """
        score = analyzer.analyze_query(query)

        # Should score OPTIONAL MATCH
        assert "optional_matches" in score.breakdown
        assert score.breakdown["optional_matches"] == 5  # 1 OPTIONAL * 5


class TestComplexityLimits:
    """Test complexity limit enforcement."""

    def test_query_within_limit(self):
        """Test query within complexity limit is allowed."""
        analyzer = QueryComplexityAnalyzer(max_complexity=50)

        query = "MATCH (n:Person) RETURN n LIMIT 10"
        is_allowed, error, score = analyzer.check_complexity(query)

        assert is_allowed is True
        assert error is None
        assert score.is_within_limit is True

    def test_query_exceeds_limit(self):
        """Test query exceeding complexity limit is blocked."""
        analyzer = QueryComplexityAnalyzer(max_complexity=20)

        # Complex query with Cartesian product
        query = """
        MATCH (p:Person)
        MATCH (m:Movie)
        MATCH (d:Director)
        RETURN p, m, d
        """
        is_allowed, error, score = analyzer.check_complexity(query)

        assert is_allowed is False
        assert error is not None
        assert "exceeds limit" in error
        assert score.is_within_limit is False
        assert score.total_score > 20

    def test_complex_unbounded_query(self):
        """Test complex unbounded query is blocked."""
        analyzer = QueryComplexityAnalyzer(max_complexity=50)

        query = """
        MATCH (a)-[*]->(b)
        MATCH (c)-[*]->(d)
        RETURN a, b, c, d
        """
        is_allowed, error, score = analyzer.check_complexity(query)

        assert is_allowed is False
        assert score.total_score > 50


class TestComplexityWarnings:
    """Test complexity warning generation."""

    def test_warnings_for_risky_patterns(self):
        """Test warnings are generated for risky patterns."""
        analyzer = QueryComplexityAnalyzer(max_complexity=200)

        query = """
        MATCH (a)-[*]->(b)
        MATCH (c)
        MATCH (d)
        RETURN a, b, c, d
        """
        score = analyzer.analyze_query(query)

        # Should have multiple warnings
        assert len(score.warnings) > 0
        assert any("unbounded" in w.lower() for w in score.warnings)
        assert any("LIMIT" in w for w in score.warnings)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_query(self):
        """Test empty query handling."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        score = analyzer.analyze_query("")

        assert score.total_score == 0
        assert score.is_within_limit is False
        assert len(score.warnings) > 0

    def test_invalid_query_type(self):
        """Test invalid query type handling."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        score = analyzer.analyze_query(None)  # type: ignore

        assert score.total_score == 0
        assert score.is_within_limit is False

    def test_case_insensitive_analysis(self):
        """Test analysis is case-insensitive."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query1 = "MATCH (n:Person) RETURN n"
        query2 = "match (n:Person) return n"
        query3 = "MaTcH (n:Person) ReTuRn n"

        score1 = analyzer.analyze_query(query1)
        score2 = analyzer.analyze_query(query2)
        score3 = analyzer.analyze_query(query3)

        # All should have same score
        assert score1.total_score == score2.total_score == score3.total_score


class TestGlobalAnalyzer:
    """Test global analyzer functions."""

    def test_initialize_complexity_limiter(self):
        """Test global analyzer initialization."""
        initialize_complexity_limiter(max_complexity=150, max_variable_path_length=8)

        # Test with a query
        is_allowed, error, score = check_query_complexity("MATCH (n) RETURN n LIMIT 10")

        assert is_allowed is True
        assert score is not None
        assert score.max_allowed == 150

    def test_check_query_complexity_not_initialized(self):
        """Test check_query_complexity when not initialized."""
        # Reset global analyzer
        from neo4j_yass_mcp.security import complexity_limiter

        complexity_limiter._complexity_analyzer = None

        # Should allow query when not initialized
        is_allowed, error, score = check_query_complexity("MATCH (n) RETURN n")

        assert is_allowed is True
        assert error is None
        assert score is None


class TestRealWorldQueries:
    """Test realistic query scenarios."""

    def test_movie_recommendation_query(self):
        """Test typical movie recommendation query."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query = """
        MATCH (p:Person {name: 'Tom Cruise'})-[:ACTED_IN]->(m:Movie)
        RETURN m.title AS title, m.year AS year
        ORDER BY m.year DESC
        LIMIT 10
        """
        score = analyzer.analyze_query(query)

        # Should be within limit
        assert score.is_within_limit is True
        assert score.total_score < 100

    def test_deep_relationship_traversal(self):
        """Test deep relationship traversal query with explicit arrow direction."""
        analyzer = QueryComplexityAnalyzer(max_complexity=50, max_variable_path_length=5)

        # Use directed pattern that the regex will catch
        query = """
        MATCH (a:Person {name: 'Alice'})-[*1..10]->(b:Person)
        RETURN DISTINCT b.name
        """
        is_allowed, error, score = analyzer.check_complexity(query)

        # Should have excessive variable path penalty
        assert "excessive_variable_path" in score.breakdown
        assert any("exceeds limit" in w for w in score.warnings)

    def test_aggregation_report_query(self):
        """Test aggregation report query."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)

        query = """
        MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
        WITH p, COUNT(m) AS movies, COLLECT(m.title) AS titles
        WHERE movies > 5
        RETURN p.name, movies, titles
        ORDER BY movies DESC
        LIMIT 20
        """
        score = analyzer.analyze_query(query)

        # Should be within limit
        assert score.is_within_limit is True

    def test_single_match_not_cartesian(self):
        """Test that single MATCH statement is not detected as cartesian (line 211)."""
        analyzer = QueryComplexityAnalyzer()

        # Single MATCH should return False from _detect_cartesian_product
        query = "MATCH (n:Person) RETURN n"
        result = analyzer._detect_cartesian_product(query)

        assert result is False

    def test_connected_matches_not_cartesian(self):
        """Test that connected MATCH statements are not cartesian (line 231)."""
        analyzer = QueryComplexityAnalyzer()

        # Two MATCH statements with shared variables (both define with :)
        # The regex looks for (var: pattern, so both matches need to define variables
        query = """
        MATCH (a:Person)
        MATCH (a:Person)-[:KNOWS]->(b:Person)
        RETURN a, b
        """
        result = analyzer._detect_cartesian_product(query)

        assert result is False

    def test_get_complexity_analyzer_returns_instance(self):
        """Test get_complexity_analyzer returns the global instance (line 282)."""
        from neo4j_yass_mcp.security.complexity_limiter import (
            get_complexity_analyzer,
            initialize_complexity_limiter,
        )

        # Initialize the global analyzer
        initialize_complexity_limiter(max_complexity=50)

        # Get the analyzer
        analyzer = get_complexity_analyzer()

        # Verify it's the correct instance
        assert analyzer is not None
        assert analyzer.max_complexity == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
