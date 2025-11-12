"""
Tests for types.responses module.

Tests TypedDict response types to ensure they correctly validate response structures.
"""

import pytest

from neo4j_yass_mcp.types.responses import (
    AnalysisSummary,
    AnalyzeQueryErrorResponse,
    AnalyzeQuerySuccessResponse,
    BaseErrorResponse,
    BaseSuccessResponse,
    Bottleneck,
    CostEstimate,
    DetailedAnalysis,
    ExecuteCypherErrorResponse,
    ExecuteCypherSuccessResponse,
    ExecutionPlan,
    QueryGraphErrorResponse,
    QueryGraphSuccessResponse,
    Recommendation,
    RefreshSchemaErrorResponse,
    RefreshSchemaSuccessResponse,
    SecurityBlockedResponse,
)


class TestBaseResponseTypes:
    """Test base response type structures."""

    def test_base_success_response(self):
        """Test BaseSuccessResponse structure."""
        response: BaseSuccessResponse = {"success": True}
        assert response["success"] is True

    def test_base_error_response(self):
        """Test BaseErrorResponse structure."""
        response: BaseErrorResponse = {
            "success": False,
            "error": "An error occurred",
        }
        assert response["success"] is False
        assert response["error"] == "An error occurred"

    def test_base_error_response_with_type(self):
        """Test BaseErrorResponse with error_type."""
        response: BaseErrorResponse = {
            "success": False,
            "error": "An error occurred",
            "error_type": "ValueError",
        }
        assert response["error_type"] == "ValueError"

    def test_security_blocked_response(self):
        """Test SecurityBlockedResponse structure."""
        response: SecurityBlockedResponse = {
            "success": False,
            "error": "Query blocked",
            "security_blocked": True,
            "block_type": "sanitizer_blocked",
        }
        assert response["security_blocked"] is True
        assert response["block_type"] == "sanitizer_blocked"


class TestQueryGraphResponses:
    """Test query_graph tool response types."""

    def test_query_graph_success_minimal(self):
        """Test minimal QueryGraphSuccessResponse."""
        response: QueryGraphSuccessResponse = {
            "success": True,
            "answer": "There are 5 nodes",
        }
        assert response["success"] is True
        assert response["answer"] == "There are 5 nodes"

    def test_query_graph_success_full(self):
        """Test complete QueryGraphSuccessResponse."""
        response: QueryGraphSuccessResponse = {
            "success": True,
            "answer": "There are 5 nodes",
            "cypher_query": "MATCH (n) RETURN count(n)",
            "intermediate_steps": [{"query": "MATCH (n) RETURN count(n)"}],
            "truncated": False,
        }
        assert response["cypher_query"] == "MATCH (n) RETURN count(n)"
        assert response["truncated"] is False

    def test_query_graph_success_truncated(self):
        """Test QueryGraphSuccessResponse with truncation."""
        response: QueryGraphSuccessResponse = {
            "success": True,
            "answer": "Results truncated",
            "truncated": True,
            "original_count": 1000,
            "returned_count": 100,
        }
        assert response["truncated"] is True
        assert response["original_count"] == 1000
        assert response["returned_count"] == 100

    def test_query_graph_error(self):
        """Test QueryGraphErrorResponse."""
        response: QueryGraphErrorResponse = {
            "success": False,
            "error": "Query execution failed",
            "error_type": "DatabaseError",
        }
        assert response["success"] is False
        assert response["error"] == "Query execution failed"


class TestExecuteCypherResponses:
    """Test execute_cypher tool response types."""

    def test_execute_cypher_success(self):
        """Test ExecuteCypherSuccessResponse."""
        response: ExecuteCypherSuccessResponse = {
            "success": True,
            "result": [{"name": "Alice"}, {"name": "Bob"}],
            "row_count": 2,
        }
        assert response["success"] is True
        assert len(response["result"]) == 2
        assert response["row_count"] == 2

    def test_execute_cypher_success_truncated(self):
        """Test ExecuteCypherSuccessResponse with truncation."""
        response: ExecuteCypherSuccessResponse = {
            "success": True,
            "result": [{"name": "Alice"}],
            "row_count": 1,
            "truncated": True,
            "original_count": 1000,
            "returned_count": 1,
        }
        assert response["truncated"] is True
        assert response["original_count"] == 1000

    def test_execute_cypher_error(self):
        """Test ExecuteCypherErrorResponse."""
        response: ExecuteCypherErrorResponse = {
            "success": False,
            "error": "Syntax error in query",
        }
        assert response["success"] is False
        assert "Syntax error" in response["error"]


class TestRefreshSchemaResponses:
    """Test refresh_schema tool response types."""

    def test_refresh_schema_success(self):
        """Test RefreshSchemaSuccessResponse."""
        response: RefreshSchemaSuccessResponse = {
            "success": True,
            "schema": "Node properties: Person(name, age)",
            "message": "Schema refreshed successfully",
        }
        assert response["success"] is True
        assert "Person" in response["schema"]
        assert response["message"] == "Schema refreshed successfully"

    def test_refresh_schema_error(self):
        """Test RefreshSchemaErrorResponse."""
        response: RefreshSchemaErrorResponse = {
            "success": False,
            "error": "Graph not initialized",
        }
        assert response["success"] is False


class TestAnalysisComponents:
    """Test analysis component types."""

    def test_analysis_summary(self):
        """Test AnalysisSummary structure."""
        summary: AnalysisSummary = {
            "total_db_hits": 100,
            "estimated_rows": 1000,
            "complexity_score": 50,
            "bottleneck_count": 2,
            "recommendation_count": 3,
        }
        assert summary["total_db_hits"] == 100
        assert summary["complexity_score"] == 50

    def test_bottleneck(self):
        """Test Bottleneck structure."""
        bottleneck: Bottleneck = {
            "type": "missing_index",
            "severity": "high",
            "description": "No index on Person.name",
        }
        assert bottleneck["type"] == "missing_index"
        assert bottleneck["severity"] == "high"

    def test_bottleneck_with_details(self):
        """Test Bottleneck with optional fields."""
        bottleneck: Bottleneck = {
            "type": "missing_index",
            "severity": "high",
            "description": "No index on Person.name",
            "location": "NodeByLabelScan",
            "estimated_rows": 5000,
            "db_hits": 10000,
        }
        assert bottleneck["estimated_rows"] == 5000
        assert bottleneck["db_hits"] == 10000

    def test_recommendation(self):
        """Test Recommendation structure."""
        rec: Recommendation = {
            "priority": "high",
            "category": "indexing",
            "issue": "Missing index",
            "recommendation": "CREATE INDEX FOR (p:Person) ON (p.name)",
        }
        assert rec["priority"] == "high"
        assert "CREATE INDEX" in rec["recommendation"]

    def test_recommendation_with_example(self):
        """Test Recommendation with example."""
        rec: Recommendation = {
            "priority": "medium",
            "category": "query_structure",
            "issue": "Unbounded pattern",
            "recommendation": "Add LIMIT clause",
            "example": "MATCH (n) RETURN n LIMIT 100",
        }
        assert rec["example"] == "MATCH (n) RETURN n LIMIT 100"

    def test_cost_estimate(self):
        """Test CostEstimate structure."""
        cost: CostEstimate = {
            "cost_score": 75,
            "risk_level": "medium",
        }
        assert cost["cost_score"] == 75
        assert cost["risk_level"] == "medium"

    def test_cost_estimate_with_details(self):
        """Test CostEstimate with optional fields."""
        cost: CostEstimate = {
            "cost_score": 90,
            "risk_level": "high",
            "estimated_memory_mb": 256.5,
            "estimated_time_ms": 1500.0,
        }
        assert cost["estimated_memory_mb"] == 256.5
        assert cost["estimated_time_ms"] == 1500.0

    def test_execution_plan(self):
        """Test ExecutionPlan structure."""
        plan: ExecutionPlan = {
            "root": {"operator": "ProduceResults"},
            "identifiers": ["n"],
            "operators": [
                {"operator": "AllNodesScan", "identifiers": ["n"]},
            ],
        }
        assert plan["root"]["operator"] == "ProduceResults"
        assert "n" in plan["identifiers"]

    def test_detailed_analysis(self):
        """Test DetailedAnalysis structure."""
        analysis: DetailedAnalysis = {
            "execution_plan": {
                "root": {"operator": "ProduceResults"},
                "identifiers": ["n"],
                "operators": [],
            },
            "cost_estimate": {
                "cost_score": 50,
                "risk_level": "low",
            },
            "bottlenecks": [],
            "recommendations": [],
        }
        assert analysis["cost_estimate"]["cost_score"] == 50
        assert len(analysis["bottlenecks"]) == 0


class TestAnalyzeQueryResponses:
    """Test analyze_query_performance tool response types."""

    def test_analyze_query_success_minimal(self):
        """Test minimal AnalyzeQuerySuccessResponse."""
        response: AnalyzeQuerySuccessResponse = {
            "success": True,
            "query": "MATCH (n) RETURN n",
            "mode": "explain",
            "analysis_summary": {
                "total_db_hits": 100,
                "estimated_rows": 1000,
                "complexity_score": 50,
                "bottleneck_count": 0,
                "recommendation_count": 0,
            },
            "bottlenecks_found": 0,
            "recommendations_count": 0,
            "cost_score": 50,
            "risk_level": "low",
            "execution_time_ms": 100,
            "detailed_analysis": {
                "execution_plan": {
                    "root": {"operator": "ProduceResults"},
                    "identifiers": ["n"],
                    "operators": [],
                },
                "cost_estimate": {
                    "cost_score": 50,
                    "risk_level": "low",
                },
                "bottlenecks": [],
                "recommendations": [],
            },
        }
        assert response["success"] is True
        assert response["query"] == "MATCH (n) RETURN n"
        assert response["mode"] == "explain"

    def test_analyze_query_success_with_report(self):
        """Test AnalyzeQuerySuccessResponse with analysis report."""
        response: AnalyzeQuerySuccessResponse = {
            "success": True,
            "query": "MATCH (n) RETURN n",
            "mode": "profile",
            "analysis_summary": {
                "total_db_hits": 5000,
                "estimated_rows": 10000,
                "complexity_score": 80,
                "bottleneck_count": 2,
                "recommendation_count": 3,
            },
            "bottlenecks_found": 2,
            "recommendations_count": 3,
            "cost_score": 80,
            "risk_level": "high",
            "execution_time_ms": 500,
            "detailed_analysis": {
                "execution_plan": {
                    "root": {"operator": "ProduceResults"},
                    "identifiers": ["n"],
                    "operators": [],
                },
                "cost_estimate": {
                    "cost_score": 80,
                    "risk_level": "high",
                },
                "bottlenecks": [
                    {
                        "type": "missing_index",
                        "severity": "high",
                        "description": "No index",
                    }
                ],
                "recommendations": [
                    {
                        "priority": "high",
                        "category": "indexing",
                        "issue": "Missing index",
                        "recommendation": "CREATE INDEX",
                    }
                ],
            },
            "analysis_report": "Query Analysis Report...",
        }
        assert response["analysis_report"] == "Query Analysis Report..."
        assert response["bottlenecks_found"] == 2
        assert response["recommendations_count"] == 3

    def test_analyze_query_error(self):
        """Test AnalyzeQueryErrorResponse."""
        response: AnalyzeQueryErrorResponse = {
            "success": False,
            "error": "Invalid mode specified",
            "error_type": "ValueError",
        }
        assert response["success"] is False
        assert "Invalid mode" in response["error"]


class TestResponseTypeConsistency:
    """Test response type consistency and patterns."""

    def test_all_success_responses_have_success_true(self):
        """Verify all success responses have success=True."""
        success_responses = [
            QueryGraphSuccessResponse({"success": True, "answer": "test"}),
            ExecuteCypherSuccessResponse({"success": True, "result": [], "row_count": 0}),
            RefreshSchemaSuccessResponse({
                "success": True,
                "schema": "test",
                "message": "test",
            }),
        ]

        for response in success_responses:
            assert response["success"] is True

    def test_all_error_responses_have_success_false(self):
        """Verify all error responses have success=False."""
        error_responses = [
            QueryGraphErrorResponse({"success": False, "error": "test"}),
            ExecuteCypherErrorResponse({"success": False, "error": "test"}),
            RefreshSchemaErrorResponse({"success": False, "error": "test"}),
            AnalyzeQueryErrorResponse({"success": False, "error": "test"}),
        ]

        for response in error_responses:
            assert response["success"] is False
            assert "error" in response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
