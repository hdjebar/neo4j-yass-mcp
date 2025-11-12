"""
MCP Tool and Resource Handlers.

This package contains the implementation of MCP tools and resources for
the Neo4j YASS MCP server.

Phase 3.4: Extracted from server.py for better code organization.
"""

from .resources import get_database_info, get_schema
from .tools import (
    analyze_query_performance,
    execute_cypher,
    query_graph,
    refresh_schema,
)

__all__ = [
    # Resources
    "get_schema",
    "get_database_info",
    # Tools
    "query_graph",
    "execute_cypher",
    "refresh_schema",
    "analyze_query_performance",
]
