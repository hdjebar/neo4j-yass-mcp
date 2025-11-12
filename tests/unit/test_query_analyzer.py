"""
Unit tests for query analysis tools.

Tests cover:
- QueryPlanAnalyzer: Main analysis functionality
- BottleneckDetector: Performance bottleneck detection
- RecommendationEngine: Optimization recommendation generation
- QueryCostEstimator: Cost estimation accuracy
- Integration with security layer
"""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from neo4j_yass_mcp.tools import (
    BottleneckDetector,
    QueryCostEstimator,
    QueryPlanAnalyzer,
    RecommendationEngine,
)


class TestQueryPlanAnalyzer:
    """Test QueryPlanAnalyzer functionality."""

    @pytest.fixture
    def mock_graph(self):
        """Create a mock SecureNeo4jGraph."""
        graph = Mock()
        # Mock for PROFILE mode
        profile_result = [
            {
                "plan": [{"operator": "AllNodesScan", "estimatedRows": 100, "actualRows": 50}],
                "stats": {"rows": 50, "time": 10, "db_hits": 25, "memory": 1024},
            }
        ]

        # graph.query is synchronous (not async), so use regular Mock
        graph.query = Mock(return_value=profile_result)
        return graph

    @pytest.fixture
    def error_mock_graph(self):
        """Create a mock SecureNeo4jGraph that raises errors."""
        graph = Mock()

        # graph.query is synchronous (not async), so use Mock with side_effect
        graph.query = Mock(side_effect=Exception("Query execution failed"))
        return graph

    @pytest.fixture
    def analyzer(self, mock_graph):
        """Create QueryPlanAnalyzer with mock graph."""
        return QueryPlanAnalyzer(mock_graph)

    @pytest.mark.asyncio
    async def test_analyze_query_explain_mode(self, analyzer, mock_graph):
        """Test query analysis in explain mode."""
        query = "MATCH (n:Person) RETURN n.name"

        result = await analyzer.analyze_query(query, mode="explain")

        assert result["success"] is True
        assert result["query"] == query
        assert result["mode"] == "explain"
        assert "execution_plan" in result
        assert "bottlenecks" in result
        assert "recommendations" in result
        assert "cost_estimate" in result

    @pytest.mark.asyncio
    async def test_analyze_query_profile_mode(self, analyzer, mock_graph):
        """Test query analysis in profile mode."""
        query = "MATCH (n:Person) RETURN n.name"

        result = await analyzer.analyze_query(query, mode="profile")

        assert result["success"] is True
        assert result["mode"] == "profile"
        assert result["execution_plan"]["type"] == "profile"
        assert result["execution_plan"]["statistics"] is not None

    @pytest.mark.asyncio
    async def test_analyze_query_invalid_mode(self, analyzer):
        """Test query analysis with invalid mode."""
        query = "MATCH (n) RETURN n"

        with pytest.raises(ValueError, match="Invalid analysis mode"):
            await analyzer.analyze_query(query, mode="invalid")

    @pytest.mark.asyncio
    async def test_analyze_query_without_recommendations(self, analyzer, mock_graph):
        """Test query analysis without recommendations."""
        query = "MATCH (n) RETURN n"

        result = await analyzer.analyze_query(query, mode="explain", include_recommendations=False)

        assert result["success"] is True
        assert result["recommendations"] == []
        assert result["bottlenecks"] == []

    @pytest.mark.asyncio
    async def test_analyze_query_execution_error(self, error_mock_graph):
        """Test query analysis when execution fails."""
        query = "MATCH (n) RETURN n"
        # Create analyzer with error mock
        analyzer = QueryPlanAnalyzer(error_mock_graph)

        with pytest.raises(ValueError, match="Query analysis failed"):
            await analyzer.analyze_query(query, mode="explain")

    def test_parse_execution_plan(self, analyzer):
        """Test execution plan parsing."""
        plan_result = {
            "type": "explain",
            "plan": [{"name": "NodeByLabelScan", "estimated_rows": 100}],
            "statistics": None,
        }

        parsed = analyzer._parse_execution_plan(plan_result)

        assert parsed["operators"][0]["name"] == "NodeByLabelScan"
        assert parsed["operators"][0]["estimated_rows"] == 100
        assert parsed["root_operator"] is not None

    def test_extract_profile_statistics(self, analyzer):
        """Test profile statistics extraction."""
        result = [{"rows": 50, "time": 10.5, "db_hits": 200}]

        stats = analyzer._extract_profile_statistics(result)

        assert stats["rows"] == 50
        assert stats["time_ms"] == 10.5
        assert stats["db_hits"] == 200

    def test_generate_summary(self, analyzer):
        """Test analysis summary generation."""
        bottlenecks = [
            {"type": "missing_index", "severity": 8},
            {"type": "cartesian_product", "severity": 9},
        ]
        recommendations = [{}, {}]
        cost_estimate = {"total_cost": 5000}

        summary = analyzer._generate_summary(bottlenecks, recommendations, cost_estimate)

        assert summary["bottleneck_count"] == 2
        assert summary["recommendation_count"] == 2
        assert summary["critical_issues"] == 2  # Both severity >= 8
        assert summary["overall_severity"] == 8  # Average of 8 and 9
        assert summary["estimated_cost"] == 5000

    def test_format_analysis_report(self, analyzer):
        """Test analysis report formatting."""
        analysis_result = {
            "query": "MATCH (n) RETURN n",
            "mode": "explain",
            "analysis_summary": {"overall_severity": 5},
            "bottlenecks": [{"type": "test", "description": "Test bottleneck", "severity": 5}],
            "recommendations": [
                {"title": "Test rec", "description": "Test recommendation", "priority": "high"}
            ],
        }

        report = analyzer.format_analysis_report(analysis_result, "text")

        assert "Query Performance Analysis Report" in report
        assert "MATCH (n) RETURN n" in report
        assert "Test bottleneck" in report
        assert "Test rec" in report

    def test_format_analysis_report_json(self, analyzer):
        """Test JSON format analysis report."""
        analysis_result = {"query": "MATCH (n) RETURN n", "mode": "explain"}

        report = analyzer.format_analysis_report(analysis_result, "json")

        # Should be valid JSON
        parsed = json.loads(report)
        assert parsed["query"] == "MATCH (n) RETURN n"


class TestBottleneckDetector:
    """Test BottleneckDetector functionality."""

    @pytest.fixture
    def detector(self):
        """Create BottleneckDetector instance."""
        return BottleneckDetector()

    @pytest.mark.asyncio
    async def test_detect_cartesian_products(self, detector):
        """Test Cartesian product detection."""
        query = "MATCH (a), (b), (c) RETURN a, b, c"

        bottlenecks = detector._detect_cartesian_products(query)

        assert len(bottlenecks) > 0
        assert any(b["type"] == "cartesian_product" for b in bottlenecks)
        assert any("3 patterns" in b["description"] for b in bottlenecks)

    @pytest.mark.asyncio
    async def test_detect_unbounded_varlength_patterns(self, detector):
        """Test unbounded variable-length pattern detection."""
        query = "MATCH (a)-[*]->(b) RETURN a, b"

        bottlenecks = detector._detect_unbounded_varlength_patterns(query)

        assert len(bottlenecks) > 0
        assert any(b["type"] == "unbounded_varlength" for b in bottlenecks)
        assert any("Completely unbounded" in b["description"] for b in bottlenecks)

    @pytest.mark.asyncio
    async def test_detect_missing_limit_clauses(self, detector):
        """Test missing LIMIT clause detection."""
        query = "MATCH (n:Person) WHERE n.age > 25 RETURN n"

        bottlenecks = detector._detect_missing_limit_clauses(query.upper())

        assert len(bottlenecks) > 0
        assert any(b["type"] == "missing_limit" for b in bottlenecks)

    @pytest.mark.asyncio
    async def test_detect_expensive_procedures(self, detector):
        """Test expensive procedure detection."""
        query = "CALL apoc.path.expandConfig(n, {relationshipFilter: 'KNOWS'}) YIELD path"

        bottlenecks = detector._detect_expensive_procedures(query)

        assert len(bottlenecks) > 0
        assert any(b["type"] == "expensive_procedure" for b in bottlenecks)
        assert any("apoc.path" in b["location"] for b in bottlenecks)

    @pytest.mark.asyncio
    async def test_detect_inefficient_patterns(self, detector):
        """Test inefficient pattern detection."""
        query = "OPTIONAL MATCH (a) OPTIONAL MATCH (b) OPTIONAL MATCH (c) OPTIONAL MATCH (d) RETURN a, b, c, d"

        bottlenecks = detector._detect_inefficient_patterns(query.upper())

        assert len(bottlenecks) > 0
        assert any("OPTIONAL MATCH clauses" in b["description"] for b in bottlenecks)

    @pytest.mark.asyncio
    async def test_detect_plan_bottlenecks(self, detector):
        """Test execution plan bottleneck detection."""
        execution_plan = {
            "operators": [
                {"name": "NodeByLabelScan", "estimated_rows": 5000},
                {"name": "NodeHashJoin", "estimated_cost": 15000},
            ]
        }

        bottlenecks = detector._detect_plan_bottlenecks(execution_plan, None)

        assert len(bottlenecks) > 0
        assert any(b["type"] == "missing_index" for b in bottlenecks)
        assert any("5000 nodes" in b["impact"] for b in bottlenecks)

    @pytest.mark.asyncio
    async def test_detect_schema_bottlenecks(self, detector):
        """Test schema-related bottleneck detection."""
        query = "MATCH (n:NonExistentLabel) RETURN n"
        schema_info = {"node_labels": ["Person", "Movie"]}

        bottlenecks = detector._detect_schema_bottlenecks(query, schema_info)

        assert len(bottlenecks) > 0
        assert any(b["type"] == "schema_mismatch" for b in bottlenecks)
        assert any("NonExistentLabel" in b["description"] for b in bottlenecks)

    @pytest.mark.asyncio
    async def test_deduplicate_bottlenecks(self, detector):
        """Test bottleneck deduplication."""
        bottlenecks = [
            {"type": "test", "location": "loc1", "severity": 5},
            {"type": "test", "location": "loc1", "severity": 6},  # Duplicate
            {"type": "other", "location": "loc2", "severity": 3},
            {"type": "test", "location": "loc3", "severity": 7},  # Different location
        ]

        unique = detector._deduplicate_bottlenecks(bottlenecks)

        assert len(unique) == 3  # Should remove one duplicate
        locations = [b["location"] for b in unique]
        assert locations.count("loc1") == 1  # Only one "loc1" should remain

    @pytest.mark.asyncio
    async def test_comprehensive_bottleneck_detection(self, detector):
        """Test comprehensive bottleneck detection."""
        query = """
        MATCH (a), (b), (c)
        WHERE a.name = 'test'
        OPTIONAL MATCH (a)-[*]->(d)
        WITH *
        RETURN a, b, c, d
        """

        execution_plan = {"operators": [{"name": "NodeByLabelScan", "estimated_rows": 5000}]}

        bottlenecks = await detector.detect_bottlenecks(execution_plan, query)

        # Should detect multiple types of bottlenecks
        bottleneck_types = [b["type"] for b in bottlenecks]
        assert "cartesian_product" in bottleneck_types
        assert "unbounded_varlength" in bottleneck_types
        assert "missing_limit" in bottleneck_types
        assert "missing_index" in bottleneck_types


class TestRecommendationEngine:
    """Test RecommendationEngine functionality."""

    @pytest.fixture
    def engine(self):
        """Create RecommendationEngine instance."""
        return RecommendationEngine()

    def test_generate_cartesian_product_recommendations(self, engine):
        """Test recommendations for Cartesian products."""
        bottlenecks = [
            {
                "type": "cartesian_product",
                "description": "Potential Cartesian product: 3 patterns in single MATCH",
                "severity": 9,
                "location": "MATCH (a), (b), (c)",
            }
        ]

        recommendations = engine.generate_recommendations("test query", {}, bottlenecks)

        assert len(recommendations) > 0
        assert any("Break complex MATCH" in rec["title"] for rec in recommendations)
        assert any(rec["category"] == "query_structure" for rec in recommendations)

    def test_generate_missing_index_recommendations(self, engine):
        """Test recommendations for missing indexes."""
        bottlenecks = [
            {
                "type": "missing_index",
                "description": "NodeByLabelScan on large dataset",
                "severity": 8,
                "location": "NodeByLabelScan",
            }
        ]

        recommendations = engine.generate_recommendations("test query", {}, bottlenecks)

        assert len(recommendations) > 0
        assert any("Create index" in rec["title"] for rec in recommendations)
        assert any("CREATE INDEX" in rec["example"] for rec in recommendations)

    def test_generate_unbounded_varlength_recommendations(self, engine):
        """Test recommendations for unbounded patterns."""
        bottlenecks = [
            {
                "type": "unbounded_varlength",
                "description": "Completely unbounded variable-length pattern",
                "severity": 7,
                "location": "[*]",
            }
        ]

        recommendations = engine.generate_recommendations("test query", {}, bottlenecks)

        assert len(recommendations) > 0
        assert any("Add reasonable bounds" in rec["title"] for rec in recommendations)
        assert any("shortestPath" in rec["example"] for rec in recommendations)

    def test_priority_adjustment_by_severity(self, engine):
        """Test priority adjustment based on severity."""
        # High severity should result in high priority
        adjusted = engine._adjust_priority_by_severity("medium", 9)
        assert adjusted == "high"

        # Low severity should keep original priority
        adjusted = engine._adjust_priority_by_severity("high", 2)
        assert adjusted == "high"

    def test_deduplicate_recommendations(self, engine):
        """Test recommendation deduplication."""
        recommendations = [
            {"bottleneck_type": "test", "bottleneck_location": "loc1", "title": "Rec 1"},
            {
                "bottleneck_type": "test",
                "bottleneck_location": "loc1",
                "title": "Rec 2",
            },  # Duplicate
            {"bottleneck_type": "other", "bottleneck_location": "loc2", "title": "Rec 3"},
        ]

        unique = engine._deduplicate_recommendations(recommendations)

        assert len(unique) == 2  # Should remove one duplicate

    def test_score_recommendation_severity(self, engine):
        """Test recommendation severity scoring."""
        recommendation = {"severity": 6, "priority": "high", "impact": "high"}

        score = engine.score_recommendation_severity(recommendation, 75)  # High complexity

        # Formula: ((severity + priority_score + impact_score) / 3) * (1 + complexity_factor * 0.2)
        # = ((6 + 3 + 3) / 3) * (1 + 1.5 * 0.2) = 4 * 1.3 = 5.2 → 5
        assert score >= 5  # Should be boosted by high complexity
        assert score <= 10


class TestQueryCostEstimator:
    """Test QueryCostEstimator functionality."""

    @pytest.fixture
    def estimator(self):
        """Create QueryCostEstimator instance."""
        return QueryCostEstimator()

    def test_calculate_base_cost(self, estimator):
        """Test base cost calculation."""
        query = "MATCH (n:Person) WHERE n.age > 25 RETURN n"

        base_cost = estimator._calculate_base_cost(query)

        assert base_cost > 0
        assert isinstance(base_cost, float)

    def test_calculate_pattern_multiplier(self, estimator):
        """Test pattern multiplier calculation."""
        # Test unbounded pattern
        query_with_unbounded = "MATCH (a)-[*]->(b) RETURN a, b"
        multiplier = estimator._calculate_pattern_multiplier(query_with_unbounded)
        assert multiplier > 1.0

        # Test normal pattern
        query_normal = "MATCH (a:Person) RETURN a"
        multiplier_normal = estimator._calculate_pattern_multiplier(query_normal)
        assert multiplier_normal == 1.0

    def test_calculate_plan_cost(self, estimator):
        """Test plan cost calculation."""
        execution_plan = {
            "operators": [
                {"name": "NodeByLabelScan", "estimated_rows": 1000},
                {"name": "Filter", "estimated_rows": 500},
            ]
        }

        plan_cost = estimator._calculate_plan_cost(execution_plan)

        assert plan_cost > 0
        assert isinstance(plan_cost, float)

    def test_estimate_row_count(self, estimator):
        """Test row count estimation."""
        # Test with LIMIT
        query_with_limit = "MATCH (n) RETURN n LIMIT 50"
        rows = estimator._estimate_row_count(query_with_limit, None)
        assert rows == 50

        # Test with COUNT
        query_with_count = "MATCH (n) RETURN COUNT(n)"
        rows = estimator._estimate_row_count(query_with_count, None)
        assert rows == 1

    def test_assess_risk(self, estimator):
        """Test risk assessment."""
        query = "MATCH (n) RETURN n"
        total_cost = 15000  # High cost
        resource_costs = {"cpu_cost": 6000, "memory_cost": 4500, "io_cost": 4500}

        risk = estimator._assess_risk(query, total_cost, resource_costs)

        assert risk["risk_level"] == "high"
        assert len(risk["risk_factors"]) > 0

    def test_calculate_cost_score(self, estimator):
        """Test cost score calculation."""
        assert estimator._calculate_cost_score(50) == 1
        assert estimator._calculate_cost_score(500) == 2
        assert estimator._calculate_cost_score(5000) == 5
        assert estimator._calculate_cost_score(50000) == 10

    def test_estimate_execution_time(self, estimator):
        """Test execution time estimation."""
        time_ms = estimator._estimate_execution_time(5000, 1000)

        assert time_ms > 0
        assert time_ms <= 60000  # Max 60 seconds

    def test_estimate_memory_usage(self, estimator):
        """Test memory usage estimation."""
        memory_mb = estimator._estimate_memory_usage(5000, 1000)

        assert memory_mb > 0
        assert memory_mb <= 1000  # Max 1GB
        assert isinstance(memory_mb, int)

    def test_comprehensive_cost_estimation(self, estimator):
        """Test comprehensive cost estimation."""
        query = """
        MATCH (a:Person)-[*1..5]->(b:Person)
        WHERE a.age > 25 AND b.city = 'New York'
        RETURN a.name, b.name, count(*) as connections
        ORDER BY connections DESC
        LIMIT 100
        """

        execution_plan = {
            "operators": [
                {"name": "NodeByLabelScan", "estimated_rows": 5000},
                {"name": "VarLengthExpand", "estimated_rows": 2000},
                {"name": "Filter", "estimated_rows": 1500},
                {"name": "Aggregation", "estimated_rows": 100},
                {"name": "Sort", "estimated_rows": 100},
                {"name": "Limit", "estimated_rows": 100},
            ]
        }

        cost_estimate = estimator.estimate_cost(query, execution_plan, 100)

        # Cost estimator returns cost data directly, no success key
        assert cost_estimate["total_cost"] > 0
        assert cost_estimate["cost_score"] >= 1
        assert cost_estimate["confidence"] in ["low", "medium", "high"]
        assert "resource_breakdown" in cost_estimate
        assert cost_estimate["estimated_rows"] == 100
        assert cost_estimate["risk_level"] in ["low", "medium", "high"]


class TestSecurityIntegration:
    """Test security integration for query analysis tools."""

    @pytest.mark.asyncio
    async def test_analyzer_respects_security_layer(self):
        """Test that analyzer respects the security layer."""
        # Mock graph that raises ValueError (security violation)
        mock_graph = Mock()
        mock_graph.query.side_effect = ValueError("Query blocked by sanitizer: dangerous pattern")

        analyzer = QueryPlanAnalyzer(mock_graph)

        with pytest.raises(ValueError, match="Query blocked by sanitizer"):
            await analyzer.analyze_query("MATCH (n) RETURN n", mode="explain")

    @pytest.mark.asyncio
    async def test_safe_query_execution(self):
        """Test safe query execution through secure graph."""
        mock_graph = Mock()
        mock_graph.query = AsyncMock(return_value=[{"plan": "safe_plan"}])

        analyzer = QueryPlanAnalyzer(mock_graph)

        # Should use the secure graph's query method
        await analyzer._execute_cypher_safe("EXPLAIN MATCH (n) RETURN n")

        mock_graph.query.assert_called_once_with("EXPLAIN MATCH (n) RETURN n", params={})

    def test_no_direct_query_execution(self):
        """Test that tools don't execute queries directly."""
        # All query execution should go through the secure graph
        analyzer = QueryPlanAnalyzer(Mock())

        # The _execute_cypher_safe method should delegate to the graph
        assert hasattr(analyzer, "_execute_cypher_safe")
        assert not hasattr(analyzer, "execute_query_directly")
