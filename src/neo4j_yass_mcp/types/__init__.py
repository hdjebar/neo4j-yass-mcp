"""
Type definitions for Neo4j YASS MCP Server.

Provides TypedDict response types for all MCP tools.
"""

from .responses import (
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

__all__ = [
    # Base types
    "BaseSuccessResponse",
    "BaseErrorResponse",
    "SecurityBlockedResponse",
    # query_graph responses
    "QueryGraphSuccessResponse",
    "QueryGraphErrorResponse",
    # execute_cypher responses
    "ExecuteCypherSuccessResponse",
    "ExecuteCypherErrorResponse",
    # refresh_schema responses
    "RefreshSchemaSuccessResponse",
    "RefreshSchemaErrorResponse",
    # analyze_query_performance responses
    "AnalyzeQuerySuccessResponse",
    "AnalyzeQueryErrorResponse",
    # Analysis components
    "AnalysisSummary",
    "Bottleneck",
    "Recommendation",
    "CostEstimate",
    "ExecutionPlan",
    "DetailedAnalysis",
]
