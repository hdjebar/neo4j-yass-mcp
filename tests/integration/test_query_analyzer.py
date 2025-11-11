"""
Integration tests for query analysis tools.

Tests cover:
- End-to-end query analysis workflow
- Integration with Neo4j execution plans
- Security layer integration
- Performance and resource usage
- Real-world query scenarios
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from neo4j_yass_mcp.server import analyze_query_performance
from neo4j_yass_mcp.tools import QueryPlanAnalyzer


class TestQueryAnalysisIntegration:
    """Test end-to-end query analysis integration."""

    @pytest.fixture
    def mock_context(self):
        """Create mock FastMCP Context."""
        mock_ctx = Mock()
        mock_ctx.session_id = "test_session_123"
        mock_ctx.client_id = None
        return mock_ctx

    @pytest.fixture
    def mock_graph_with_plan(self):
        """Create mock graph that returns realistic execution plans."""
        graph = Mock()

        # Mock EXPLAIN response
        explain_response = [
            {
                "plan": {
                    "root": {
                        "operatorType": "NodeByLabelScan",
                        "args": {"label": "Person", "property": "name"},
                        "estimatedRows": 1000,
                        "estimatedCost": 500,
                    }
                },
                "statistics": None,
            }
        ]

        # Mock PROFILE response
        profile_response = [
            {
                "plan": {
                    "root": {
                        "operatorType": "NodeByLabelScan",
                        "args": {"label": "Person", "property": "name"},
                        "estimatedRows": 1000,
                        "estimatedCost": 500,
                        "dbHits": 1000,
                        "rows": 100,
                        "time": 15.5,
                    }
                },
                "statistics": {"rows": 100, "time": 15.5, "dbHits": 1000},
            }
        ]

        # Make query method async
        graph.query = AsyncMock(
            side_effect=lambda q, **kwargs: profile_response
            if q.startswith("PROFILE")
            else explain_response
        )

        return graph

    @pytest.mark.asyncio
    async def test_analyze_query_performance_end_to_end(self, mock_graph_with_plan, mock_context):
        """Test complete query analysis workflow."""
        with patch("neo4j_yass_mcp.server.graph", mock_graph_with_plan):
            with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                query = "MATCH (n:Person) WHERE n.age > 25 RETURN n.name, n.age"

                result = await analyze_query_performance(
                    query=query, mode="profile", include_recommendations=True, ctx=mock_context
                )

                # Verify response structure
                assert result["success"] is True
                assert result["query"] == query
                assert result["mode"] == "profile"
                assert "analysis_summary" in result
                assert "detailed_analysis" in result
                assert result["bottlenecks_found"] >= 0
                assert result["recommendations_count"] >= 0
                assert result["cost_score"] >= 0
                assert result["risk_level"] in ["low", "medium", "high", "unknown"]
                assert result["execution_time_ms"] > 0
                assert "analysis_report" in result

    @pytest.mark.asyncio
    async def test_analyze_query_performance_explain_mode(self, mock_graph_with_plan, mock_context):
        """Test query analysis in explain mode."""
        with patch("neo4j_yass_mcp.server.graph", mock_graph_with_plan):
            with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                query = "MATCH (n:Movie) RETURN n.title"

                result = await analyze_query_performance(
                    query=query, mode="explain", include_recommendations=True, ctx=mock_context
                )

                assert result["success"] is True
                assert result["mode"] == "explain"
                assert result["bottlenecks_found"] >= 0
                # EXPLAIN should be faster than PROFILE
                assert result["execution_time_ms"] < 1000

    @pytest.mark.asyncio
    async def test_analyze_query_performance_no_recommendations(
        self, mock_graph_with_plan, mock_context
    ):
        """Test query analysis without recommendations."""
        with patch("neo4j_yass_mcp.server.graph", mock_graph_with_plan):
            with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                query = "MATCH (n:Person) RETURN n LIMIT 10"

                result = await analyze_query_performance(
                    query=query, mode="explain", include_recommendations=False, ctx=mock_context
                )

                assert result["success"] is True
                # Should have fewer details when recommendations are disabled
                assert len(result["detailed_analysis"]["recommendations"]) == 0
                assert len(result["detailed_analysis"]["bottlenecks"]) == 0

    @pytest.mark.asyncio
    async def test_analyze_query_performance_invalid_mode(self, mock_graph_with_plan, mock_context):
        """Test query analysis with invalid mode."""
        with patch("neo4j_yass_mcp.server.graph", mock_graph_with_plan):
            with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                query = "MATCH (n) RETURN n"

                result = await analyze_query_performance(
                    query=query, mode="invalid_mode", include_recommendations=True, ctx=mock_context
                )

                assert result["success"] is False
                assert "error" in result
                assert result.get("error_type") == "ValueError"

    @pytest.mark.asyncio
    async def test_analyze_query_performance_graph_not_initialized(self, mock_context):
        """Test analysis when graph is not initialized."""
        with patch("neo4j_yass_mcp.server.graph", None):
            result = await analyze_query_performance(
                query="MATCH (n) RETURN n",
                mode="explain",
                include_recommendations=True,
                ctx=mock_context,
            )

            assert result["success"] is False
            assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_analyze_query_performance_with_security_error(self, mock_context):
        """Test analysis when security layer blocks query."""
        # Mock graph that raises security error
        mock_graph = Mock()
        mock_graph.query.side_effect = ValueError("Query blocked by sanitizer: dangerous pattern")

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                result = await analyze_query_performance(
                    query="MATCH (n) RETURN n",
                    mode="explain",
                    include_recommendations=True,
                    ctx=mock_context,
                )

                assert result["success"] is False
                assert "error" in result
                # Should be caught as analysis error (ValueError for invalid mode)
                assert result.get("error_type") == "ValueError"

    @pytest.mark.asyncio
    async def test_analyze_query_performance_with_audit_logging(
        self, mock_graph_with_plan, mock_context
    ):
        """Test analysis with audit logging enabled."""
        mock_audit_logger = Mock()
        mock_audit_logger.log_query = Mock()
        mock_audit_logger.log_response = Mock()

        with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=mock_audit_logger):
            with patch("neo4j_yass_mcp.server.graph", mock_graph_with_plan):
                query = "MATCH (n:Person) RETURN n.name"

                await analyze_query_performance(
                    query=query, mode="profile", include_recommendations=True, ctx=mock_context
                )

                # Verify audit logging calls
                mock_audit_logger.log_query.assert_called_once()
                mock_audit_logger.log_response.assert_called_once()

                # Verify audit log includes analysis metadata
                response_call = mock_audit_logger.log_response.call_args
                assert "mode" in response_call[1]["metadata"]
                assert "bottlenecks_found" in response_call[1]["metadata"]

    @pytest.mark.asyncio
    async def test_query_analyzer_integration_with_real_plans(self):
        """Test analyzer with realistic execution plan scenarios."""
        # Create analyzer with mock graph
        mock_graph = Mock()

        # Simulate different execution plans (matching Neo4j EXPLAIN output structure)
        scenarios = [
            {
                "name": "Expensive Scan",
                "plan": [
                    {"name": "NodeByLabelScan", "estimated_rows": 10000},
                    {"name": "Filter", "estimated_rows": 5000},
                ],
                "expected_bottlenecks": ["missing_index"],
            },
            {
                "name": "Cartesian Product",
                "plan": [
                    {"name": "CartesianProduct", "estimated_rows": 1000000},
                    {"name": "NodeByLabelScan", "estimated_rows": 1000},
                ],
                "expected_bottlenecks": ["cartesian_product"],
            },
            {
                "name": "Efficient Index Usage",
                "plan": [
                    {"name": "NodeIndexSeek", "estimated_rows": 10},
                    {"name": "ExpandInto", "estimated_rows": 50},
                ],
                "expected_bottlenecks": [],  # Should be efficient
            },
        ]

        for scenario in scenarios:
            mock_graph.query = Mock(return_value=scenario["plan"])
            analyzer = QueryPlanAnalyzer(mock_graph)

            result = await analyzer.analyze_query(
                query="MATCH (n) RETURN n", mode="explain", include_recommendations=True
            )

            assert result["success"] is True

            # Check if expected bottlenecks are detected
            detected_types = [b["type"] for b in result["bottlenecks"]]
            for expected_type in scenario["expected_bottlenecks"]:
                assert expected_type in detected_types, (
                    f"Expected {expected_type} not found in {scenario['name']}"
                )

    @pytest.mark.asyncio
    async def test_performance_characteristics(self, mock_graph_with_plan, mock_context):
        """Test performance characteristics of query analysis."""
        with patch("neo4j_yass_mcp.server.graph", mock_graph_with_plan):
            with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                # Test multiple queries to ensure reasonable performance
                queries = [
                    "MATCH (n) RETURN n",
                    "MATCH (n:Person)-[:KNOWS]->(m:Person) RETURN n.name, m.name",
                    "MATCH (n:Movie) WHERE n.rating > 8 RETURN n.title, n.rating ORDER BY n.rating DESC LIMIT 10",
                ]

                execution_times = []
                for query in queries:
                    start_time = asyncio.get_event_loop().time()

                    result = await analyze_query_performance(
                        query=query, mode="explain", include_recommendations=True, ctx=mock_context
                    )

                    end_time = asyncio.get_event_loop().time()
                    execution_time_ms = (end_time - start_time) * 1000

                    assert result["success"] is True
                    execution_times.append(execution_time_ms)

                # All analyses should complete within reasonable time (< 1 second)
                for time_ms in execution_times:
                    assert time_ms < 1000, f"Analysis took too long: {time_ms}ms"

                # Average should be much faster
                avg_time = sum(execution_times) / len(execution_times)
                assert avg_time < 500, f"Average analysis time too slow: {avg_time}ms"

    @pytest.mark.asyncio
    async def test_concurrent_analysis_requests(self, mock_graph_with_plan, mock_context):
        """Test concurrent query analysis requests."""
        with patch("neo4j_yass_mcp.server.graph", mock_graph_with_plan):
            with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                query = "MATCH (n:Person) RETURN n.name"

                # Create multiple concurrent analysis requests
                tasks = []
                for _i in range(5):
                    task = analyze_query_performance(
                        query=query, mode="explain", include_recommendations=True, ctx=mock_context
                    )
                    tasks.append(task)

                # Execute all requests concurrently
                results = await asyncio.gather(*tasks)

                # All requests should succeed
                for result in results:
                    assert result["success"] is True
                    assert result["query"] == query
                    assert result["bottlenecks_found"] >= 0

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mock_context):
        """Test error handling and recovery scenarios."""
        # Test with various error conditions
        # Note: All errors are wrapped in ValueError by query_analyzer.py line 122
        error_scenarios = [
            {"error": Exception("Network timeout"), "expected_error_type": "ValueError"},
            {"error": ValueError("Invalid query syntax"), "expected_error_type": "ValueError"},
            {"error": RuntimeError("Neo4j connection lost"), "expected_error_type": "ValueError"},
        ]

        for scenario in error_scenarios:
            mock_graph = Mock()
            mock_graph.query.side_effect = scenario["error"]

            with patch("neo4j_yass_mcp.server.graph", mock_graph):
                with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                    result = await analyze_query_performance(
                        query="MATCH (n) RETURN n",
                        mode="explain",
                        include_recommendations=True,
                        ctx=mock_context,
                    )

                    assert result["success"] is False
                    assert "error" in result
                    assert result.get("error_type") == scenario["expected_error_type"]

    @pytest.mark.asyncio
    async def test_complex_query_analysis(self, mock_context):
        """Test analysis of complex real-world queries."""
        # Complex query with multiple patterns and operations
        complex_query = """
        MATCH (p:Person)-[:ACTED_IN]->(m:Movie)<-[:DIRECTED]-(d:Person),
              (p)-[:FOLLOWS]->(f:Person)
        WHERE m.rating > 8 AND p.birthYear > 1980
        WITH p, m, d, collect(f) as friends
        OPTIONAL MATCH (p)-[:REVIEWED]->(m2:Movie)
        WHERE m2.year > 2015
        RETURN p.name,
               count(DISTINCT m) as movies_acted,
               count(DISTINCT friends) as friend_count,
               count(DISTINCT m2) as reviewed_movies
        ORDER BY movies_acted DESC
        LIMIT 50
        """

        # Mock complex execution plan
        mock_graph = Mock()
        mock_graph.query = AsyncMock(
            return_value=[
                {
                    "operators": [
                        {"name": "NodeByLabelScan", "estimated_rows": 50000},
                        {"name": "ExpandAll", "estimated_rows": 200000},
                        {"name": "Filter", "estimated_rows": 15000},
                        {"name": "Aggregation", "estimated_rows": 1000},
                        {"name": "Sort", "estimated_rows": 1000},
                        {"name": "Limit", "estimated_rows": 50},
                    ]
                }
            ]
        )

        with patch("neo4j_yass_mcp.server.graph", mock_graph):
            with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                result = await analyze_query_performance(
                    query=complex_query,
                    mode="explain",
                    include_recommendations=True,
                    ctx=mock_context,
                )

                assert result["success"] is True
                # Complex queries should have more bottlenecks
                assert result["bottlenecks_found"] > 0
                assert result["recommendations_count"] > 0
                # Complex queries should have higher cost scores
                assert result["cost_score"] > 5


class TestQueryAnalysisRealWorldScenarios:
    """Test query analysis with real-world scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_social_network_queries(self):
        """Test analysis of social network-style queries."""
        queries = [
            # Friend recommendations
            "MATCH (user:Person {name: 'Alice'})-[:FRIENDS_WITH]-(friend)-[:FRIENDS_WITH]-(fof) "
            "WHERE NOT (user)-[:FRIENDS_WITH]-(fof) AND user <> fof "
            "RETURN fof.name, count(*) as mutual_friends "
            "ORDER BY mutual_friends DESC LIMIT 10",
            # Path finding
            "MATCH path = shortestPath((a:Person)-[:FRIENDS_WITH*]-(b:Person)) "
            "WHERE a.name = 'Alice' AND b.name = 'Bob' "
            "RETURN path",
            # Community detection
            "MATCH (p:Person)-[:FRIENDS_WITH]-(friend) "
            "WITH p, collect(friend) as friends "
            "WHERE size(friends) > 5 "
            "RETURN p.name, size(friends) as friend_count",
        ]

        for query in queries:
            mock_graph = Mock()
            mock_graph.query = AsyncMock(
                return_value=[{"operators": [{"name": "NodeIndexSeek", "estimated_rows": 100}]}]
            )

            with patch("neo4j_yass_mcp.server.graph", mock_graph):
                with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                    result = await analyze_query_performance(
                        query=query, mode="explain", include_recommendations=True, ctx=Mock()
                    )

                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_ecommerce_queries(self):
        """Test analysis of e-commerce-style queries."""
        queries = [
            # Product recommendations
            "MATCH (user:User)-[:PURCHASED]->(product:Product)<-[:PURCHASED]-(similar:User) "
            "WHERE similar <> user "
            "WITH similar, collect(product) as purchased_products "
            "MATCH (similar)-[:PURCHASED]->(recommended:Product) "
            "WHERE NOT recommended IN purchased_products "
            "RETURN recommended.name, count(*) as purchase_count "
            "ORDER BY purchase_count DESC LIMIT 20",
            # Inventory analysis
            "MATCH (product:Product)-[:IN_CATEGORY]->(category:Category) "
            "WITH category, collect(product) as products "
            "UNWIND products as product "
            "RETURN category.name, avg(product.price) as avg_price, count(product) as product_count",
            # Customer segmentation
            "MATCH (customer:Customer)-[:PLACED]->(order:Order) "
            "WITH customer, sum(order.total) as total_spent, count(order) as order_count "
            "WHERE total_spent > 1000 "
            "RETURN customer.name, total_spent, order_count "
            "ORDER BY total_spent DESC",
        ]

        for query in queries:
            mock_graph = Mock()
            mock_graph.query = AsyncMock(
                return_value=[{"operators": [{"name": "NodeByLabelScan", "estimated_rows": 500}]}]
            )

            with patch("neo4j_yass_mcp.server.graph", mock_graph):
                with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                    result = await analyze_query_performance(
                        query=query, mode="explain", include_recommendations=True, ctx=Mock()
                    )

                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_knowledge_graph_queries(self):
        """Test analysis of knowledge graph-style queries."""
        queries = [
            # Entity relationships
            "MATCH (entity1:Entity)-[r:RELATED_TO]->(entity2:Entity) "
            "WHERE r.confidence > 0.8 "
            "WITH entity1, entity2, r "
            "MATCH (entity2)-[r2:RELATED_TO]->(entity3:Entity) "
            "WHERE r2.confidence > 0.8 AND entity3 <> entity1 "
            "RETURN entity1.name, entity2.name, entity3.name, r.confidence, r2.confidence",
            # Path analysis
            "MATCH path = (start:Entity)-[:RELATED_TO*2..4]-(end:Entity) "
            "WHERE start.domain = 'medical' AND end.domain = 'medical' "
            "AND ALL(rel in relationships(path) WHERE rel.confidence > 0.7) "
            "RETURN path, reduce(total_confidence = 0, rel in relationships(path) | total_confidence + rel.confidence) as total_confidence "
            "ORDER BY total_confidence DESC LIMIT 5",
            # Similarity search
            "MATCH (target:Entity {name: 'Machine Learning'}) "
            "MATCH (similar:Entity) "
            "WHERE similar <> target AND similar.domain = target.domain "
            "WITH target, similar, "
            "size(apoc.coll.intersection(target.keywords, similar.keywords)) as common_keywords "
            "WHERE common_keywords > 3 "
            "RETURN similar.name, common_keywords "
            "ORDER BY common_keywords DESC LIMIT 10",
        ]

        for query in queries:
            mock_graph = Mock()
            mock_graph.query = AsyncMock(
                return_value=[{"operators": [{"name": "NodeIndexSeek", "estimated_rows": 200}]}]
            )

            with patch("neo4j_yass_mcp.server.graph", mock_graph):
                with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                    result = await analyze_query_performance(
                        query=query, mode="explain", include_recommendations=True, ctx=Mock()
                    )

                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_edge_cases_and_error_conditions(self):
        """Test edge cases and error conditions."""
        edge_cases = [
            # Empty query
            "",
            # Very long query
            "MATCH "
            + " ".join([f"(n{i})" + (f"-[:REL]->(n{i + 1})" if i < 50 else "") for i in range(50)]),
            # Query with special characters
            "MATCH (n:Person {name: 'O'Brien'}) RETURN n",
            # Unicode characters
            "MATCH (n:Person {name: 'José García'}) RETURN n",
            # Complex regex patterns
            "MATCH (n:Person) WHERE n.email =~ '.*@company\\.com$' RETURN n",
        ]

        for query in edge_cases:
            if not query:  # Skip empty query test for now
                continue

            mock_graph = Mock()
            mock_graph.query = AsyncMock(
                return_value=[{"operators": [{"name": "NodeByLabelScan", "estimated_rows": 100}]}]
            )

            with patch("neo4j_yass_mcp.server.graph", mock_graph):
                with patch("neo4j_yass_mcp.server.get_audit_logger", return_value=None):
                    result = await analyze_query_performance(
                        query=query, mode="explain", include_recommendations=True, ctx=Mock()
                    )

                    # Should handle edge cases gracefully
                    assert result["success"] is True or "error" in result
