"""
MCP Resource Handlers.

Provides read-only access to server resources like schema and database info.

Phase 3.4: Extracted from server.py for better code organization.
"""

from fastmcp import Context


async def get_schema(ctx: Context | None = None) -> str:
    """
    Get the Neo4j graph database schema.

    Returns the complete schema including node labels, relationship types,
    and their properties.

    Args:
        ctx: FastMCP context (optional)

    Returns:
        String containing the schema or error message
    """
    # Lazy import to avoid circular dependency at import time
    from neo4j_yass_mcp.server import _get_graph

    current_graph = _get_graph()

    if current_graph is None:
        return "Error: Neo4j graph not initialized"

    try:
        schema = current_graph.get_schema
        return f"Neo4j Graph Schema:\n\n{schema}"
    except Exception as e:
        return f"Error retrieving schema: {str(e)}"


async def get_database_info(ctx: Context | None = None) -> str:
    """
    Get information about the Neo4j database connection.

    Returns details about the connected database.

    Args:
        ctx: FastMCP context (optional)

    Returns:
        String containing database connection information
    """
    # Lazy import to avoid circular dependency at import time
    from neo4j_yass_mcp.server import _get_config

    config = _get_config()
    neo4j_uri = config.neo4j.uri
    neo4j_database = config.neo4j.database

    return f"""Neo4j Database Information:

URI: {neo4j_uri}
Database: {neo4j_database}
Status: Connected
"""
