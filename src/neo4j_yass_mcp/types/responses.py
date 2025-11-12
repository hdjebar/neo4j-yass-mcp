"""
TypedDict response types for Neo4j YASS MCP Server tools.

This module defines strongly-typed response structures for all MCP tools,
eliminating ambiguous dict[str, Any] return types and improving type safety
(ARCHITECTURE_REFACTORING_PLAN.md Issue #5).

All response types follow a consistent pattern:
- success: bool field indicating operation success
- For success=True: result data fields
- For success=False: error, error_type, and optional additional error context
"""

from typing import Any, Literal, NotRequired, TypedDict


# ============================================================================
# Base Response Types
# ============================================================================


class BaseSuccessResponse(TypedDict):
    """Base type for successful responses."""

    success: Literal[True]


class BaseErrorResponse(TypedDict):
    """Base type for error responses."""

    success: Literal[False]
    error: str
    error_type: NotRequired[str]


class SecurityBlockedResponse(BaseErrorResponse):
    """Response when a query is blocked by security policies."""

    security_blocked: Literal[True]
    block_type: Literal["sanitizer_blocked", "complexity_blocked", "read_only_blocked", "security_blocked"]


# ============================================================================
# query_graph Tool Responses
# ============================================================================


class QueryGraphSuccessResponse(BaseSuccessResponse):
    """
    Success response from query_graph tool.

    Example:
        {
            "success": True,
            "answer": "There are 5 nodes in the graph.",
            "cypher_query": "MATCH (n) RETURN count(n)",
            "intermediate_steps": [...],
            "truncated": False
        }
    """

    answer: str
    cypher_query: NotRequired[str]
    intermediate_steps: NotRequired[list[dict[str, Any]]]
    truncated: NotRequired[bool]
    original_count: NotRequired[int]
    returned_count: NotRequired[int]


class QueryGraphErrorResponse(BaseErrorResponse):
    """
    Error response from query_graph tool.

    Can be a security block or a general error.
    """

    pass


# ============================================================================
# execute_cypher Tool Responses
# ============================================================================


class ExecuteCypherSuccessResponse(BaseSuccessResponse):
    """
    Success response from execute_cypher tool.

    Example:
        {
            "success": True,
            "result": [...],
            "row_count": 10,
            "truncated": False
        }
    """

    result: list[dict[str, Any]]
    row_count: int
    truncated: NotRequired[bool]
    original_count: NotRequired[int]
    returned_count: NotRequired[int]


class ExecuteCypherErrorResponse(BaseErrorResponse):
    """Error response from execute_cypher tool."""

    pass


# ============================================================================
# refresh_schema Tool Responses
# ============================================================================


class RefreshSchemaSuccessResponse(BaseSuccessResponse):
    """
    Success response from refresh_schema tool.

    Example:
        {
            "success": True,
            "schema": "Node properties: ...",
            "message": "Schema refreshed successfully"
        }
    """

    schema: str
    message: str


class RefreshSchemaErrorResponse(BaseErrorResponse):
    """Error response from refresh_schema tool."""

    pass


# ============================================================================
# analyze_query_performance Tool Responses
# ============================================================================


class AnalysisSummary(TypedDict):
    """Summary of query analysis results."""

    total_db_hits: int
    estimated_rows: int
    complexity_score: int
    bottleneck_count: int
    recommendation_count: int


class Bottleneck(TypedDict):
    """Performance bottleneck detected in query."""

    type: str
    severity: Literal["high", "medium", "low"]
    description: str
    location: NotRequired[str]
    estimated_rows: NotRequired[int]
    db_hits: NotRequired[int]


class Recommendation(TypedDict):
    """Optimization recommendation for query."""

    priority: Literal["high", "medium", "low"]
    category: str
    issue: str
    recommendation: str
    example: NotRequired[str]


class CostEstimate(TypedDict):
    """Cost estimate for query execution."""

    cost_score: int
    risk_level: Literal["low", "medium", "high", "critical"]
    estimated_memory_mb: NotRequired[float]
    estimated_time_ms: NotRequired[float]


class ExecutionPlan(TypedDict):
    """Neo4j query execution plan."""

    root: dict[str, Any]
    identifiers: list[str]
    operators: list[dict[str, Any]]


class DetailedAnalysis(TypedDict):
    """Detailed analysis results."""

    execution_plan: ExecutionPlan
    cost_estimate: CostEstimate
    bottlenecks: list[Bottleneck]
    recommendations: list[Recommendation]


class AnalyzeQuerySuccessResponse(BaseSuccessResponse):
    """
    Success response from analyze_query_performance tool.

    Example:
        {
            "success": True,
            "query": "MATCH (n) RETURN n",
            "mode": "profile",
            "analysis_summary": {...},
            "bottlenecks_found": 2,
            "recommendations_count": 3,
            "cost_score": 75,
            "risk_level": "medium",
            "execution_time_ms": 120,
            "detailed_analysis": {...},
            "analysis_report": "..."
        }
    """

    query: str
    mode: Literal["explain", "profile"]
    analysis_summary: AnalysisSummary
    bottlenecks_found: int
    recommendations_count: int
    cost_score: int
    risk_level: Literal["low", "medium", "high", "critical", "unknown"]
    execution_time_ms: int
    detailed_analysis: DetailedAnalysis
    analysis_report: NotRequired[str]


class AnalyzeQueryErrorResponse(BaseErrorResponse):
    """Error response from analyze_query_performance tool."""

    pass
