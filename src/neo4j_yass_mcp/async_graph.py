"""
AsyncNeo4jGraph - Async Neo4j graph wrapper with security layer.

This module provides async alternatives to langchain_neo4j.Neo4jGraph, which
only supports synchronous operations. The async implementation uses the native
Neo4j async driver for better performance and eliminates the need for
asyncio.to_thread() calls.

Phase 4: Async Migration - Native async Neo4j driver support
"""

import logging
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from neo4j_yass_mcp.security import check_query_complexity, sanitize_query

logger = logging.getLogger(__name__)


class AsyncNeo4jGraph:
    """
    Async Neo4j graph wrapper (replacement for langchain_neo4j.Neo4jGraph).

    This class provides async methods for querying Neo4j and managing schema,
    compatible with the langchain_neo4j.Neo4jGraph API but fully async.

    Features:
    - Native async Neo4j driver (no thread blocking)
    - Schema introspection and caching
    - Connection management
    - Compatible API with langchain_neo4j.Neo4jGraph
    """

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        database: str = "neo4j",
        driver_config: dict[str, Any] | None = None,
    ):
        """
        Initialize AsyncNeo4jGraph with connection parameters.

        Args:
            url: Neo4j connection URL (e.g., "bolt://localhost:7687")
            username: Neo4j username
            password: Neo4j password
            database: Database name (default: "neo4j")
            driver_config: Optional driver configuration (max_connection_pool_size, etc.)
        """
        self._url = url
        self._username = username
        self._password = password
        self._database = database
        self._driver_config = driver_config or {}

        # Create async driver
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            url, auth=(username, password), **self._driver_config
        )

        # Schema cache
        self._schema: str = ""
        self._structured_schema: dict[str, Any] = {}

        logger.info(f"AsyncNeo4jGraph initialized: {url} (database: {database})")

    async def query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Execute a Cypher query asynchronously.

        Args:
            query: Cypher query to execute
            params: Optional query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            Exception: If query execution fails
        """
        logger.debug(f"Executing async query: {query[:100]}...")

        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, params or {})
            records = await result.data()
            return records

    async def query_with_summary(
        self, query: str, params: dict[str, Any] | None = None, *, fetch_records: bool = False
    ) -> tuple[list[dict[str, Any]], Any]:
        """
        Execute a Cypher query and return both data and result summary.

        This method provides access to the full Neo4j result summary, including
        execution plan information from EXPLAIN/PROFILE queries.

        IMPORTANT: By default (fetch_records=False), this method returns an EMPTY
        records list []. Only the summary is fetched. This is optimal for plan
        analysis but may surprise callers expecting query results. Set fetch_records=True
        if you need the actual query results.

        Args:
            query: Cypher query to execute
            params: Optional query parameters
            fetch_records: If True, materialize all records. If False (default), only fetch
                          the summary. For EXPLAIN/PROFILE queries, set to False to avoid
                          unnecessary result streaming.

        Returns:
            Tuple of (records, summary) where:
            - records: List of result records as dictionaries (EMPTY [] if fetch_records=False)
            - summary: Neo4j ResultSummary containing plan, statistics, etc.

        Raises:
            Exception: If query execution fails

        Examples:
            # Plan analysis (no record materialization)
            records, summary = await graph.query_with_summary("EXPLAIN MATCH (n) RETURN n")
            # records = []
            # summary.plan contains execution plan

            # Fetch both records and summary
            records, summary = await graph.query_with_summary(
                "MATCH (n:Person) RETURN n", fetch_records=True
            )
            # records = [{...}, {...}]
            # summary contains metadata
        """
        logger.debug(f"Executing async query with summary: {query[:100]}...")

        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, params or {})

            # For EXPLAIN/PROFILE queries, we typically only need the summary
            # Avoid materializing records unless explicitly requested
            if fetch_records:
                records = await result.data()
            else:
                records = []

            summary = await result.consume()
            return records, summary

    async def refresh_schema(self) -> None:
        """
        Refresh the graph schema asynchronously.

        Queries Neo4j for node labels, relationship types, and properties,
        then caches the schema for fast access.
        """
        logger.info("Refreshing graph schema (async)")

        async with self._driver.session(database=self._database) as session:
            # Query node labels
            labels_result = await session.run("CALL db.labels() YIELD label RETURN label")
            labels_data = await labels_result.data()
            labels = [record["label"] for record in labels_data]

            # Query relationship types
            rels_result = await session.run(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
            )
            rels_data = await rels_result.data()
            rel_types = [record["relationshipType"] for record in rels_data]

            # Query properties for each label
            node_properties: dict[str, list[dict[str, Any]]] = {}
            for label in labels:
                props_query = f"""
                MATCH (n:`{label}`)
                WITH n LIMIT 100
                UNWIND keys(n) AS key
                RETURN DISTINCT key,
                       head([label IN labels(n) WHERE label = '{label}']) AS label,
                       apoc.meta.cypher.type(n[key]) AS type
                ORDER BY key
                """
                try:
                    props_result = await session.run(props_query)
                    props_data = await props_result.data()
                    node_properties[label] = props_data
                except Exception as e:
                    logger.warning(
                        f"Could not fetch properties for label {label} "
                        f"(apoc.meta.cypher.type may not be available): {e}"
                    )
                    # Fallback: just get keys without types
                    fallback_query = f"""
                    MATCH (n:`{label}`)
                    WITH n LIMIT 100
                    UNWIND keys(n) AS key
                    RETURN DISTINCT key
                    ORDER BY key
                    """
                    fallback_result = await session.run(fallback_query)
                    fallback_data = await fallback_result.data()
                    node_properties[label] = [
                        {"key": record["key"], "type": "ANY"} for record in fallback_data
                    ]

            # Query relationship properties
            rel_properties: dict[str, list[dict[str, Any]]] = {}
            for rel_type in rel_types:
                props_query = f"""
                MATCH ()-[r:`{rel_type}`]->()
                WITH r LIMIT 100
                UNWIND keys(r) AS key
                RETURN DISTINCT key,
                       type(r) AS type,
                       apoc.meta.cypher.type(r[key]) AS property_type
                ORDER BY key
                """
                try:
                    props_result = await session.run(props_query)
                    props_data = await props_result.data()
                    rel_properties[rel_type] = props_data
                except Exception as e:
                    logger.warning(
                        f"Could not fetch properties for relationship {rel_type} "
                        f"(apoc.meta.cypher.type may not be available): {e}"
                    )
                    # Fallback: just get keys without types
                    fallback_query = f"""
                    MATCH ()-[r:`{rel_type}`]->()
                    WITH r LIMIT 100
                    UNWIND keys(r) AS key
                    RETURN DISTINCT key
                    ORDER BY key
                    """
                    fallback_result = await session.run(fallback_query)
                    fallback_data = await fallback_result.data()
                    rel_properties[rel_type] = [
                        {"key": record["key"], "property_type": "ANY"} for record in fallback_data
                    ]

        # Format schema as string (compatible with langchain_neo4j format)
        schema_lines = ["Node properties:"]
        for label in labels:
            props = node_properties.get(label, [])
            if props:
                props_str = ", ".join(
                    [f"{p['key']}: {p.get('type', p.get('property_type', 'ANY'))}" for p in props]
                )
                schema_lines.append(f"  {label} {{{props_str}}}")
            else:
                schema_lines.append(f"  {label}")

        schema_lines.append("\nRelationship properties:")
        for rel_type in rel_types:
            props = rel_properties.get(rel_type, [])
            if props:
                props_str = ", ".join(
                    [f"{p['key']}: {p.get('property_type', p.get('type', 'ANY'))}" for p in props]
                )
                schema_lines.append(f"  {rel_type} {{{props_str}}}")
            else:
                schema_lines.append(f"  {rel_type}")

        schema_lines.append("\nRelationships:")
        # Query relationship patterns
        patterns_query = """
        MATCH (a)-[r]->(b)
        WITH DISTINCT labels(a) AS aLabels, type(r) AS rel, labels(b) AS bLabels
        UNWIND aLabels AS aLabel
        UNWIND bLabels AS bLabel
        RETURN DISTINCT
            '(:' + aLabel + ')-[:' + rel + ']->(:' + bLabel + ')' AS pattern
        ORDER BY pattern
        LIMIT 100
        """
        async with self._driver.session(database=self._database) as session:
            try:
                patterns_result = await session.run(patterns_query)
                patterns_data = await patterns_result.data()
                for record in patterns_data:
                    schema_lines.append(f"  {record['pattern']}")
            except Exception as e:
                logger.warning(f"Could not fetch relationship patterns: {e}")

        self._schema = "\n".join(schema_lines)

        # Store structured schema
        self._structured_schema = {
            "node_props": node_properties,
            "rel_props": rel_properties,
            "relationships": rel_types,
            "labels": labels,
        }

        logger.info(f"Schema refreshed: {len(labels)} labels, {len(rel_types)} relationship types")

    @property
    def get_schema(self) -> str:
        """
        Get the cached schema as a formatted string.

        Returns:
            Schema string with node labels, properties, and relationships
        """
        return self._schema

    @property
    def get_structured_schema(self) -> dict[str, Any]:
        """
        Get the cached schema as a structured dictionary.

        Returns:
            Dictionary with node_props, rel_props, relationships, labels
        """
        return self._structured_schema

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        logger.info("Closing AsyncNeo4jGraph driver connection")
        await self._driver.close()

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()


class AsyncSecureNeo4jGraph(AsyncNeo4jGraph):
    """
    Async security wrapper for AsyncNeo4jGraph.

    This class adds security checks before query execution:
    1. Query sanitization (injection protection)
    2. Complexity limiting (DoS protection)
    3. Read-only mode enforcement

    All security checks run BEFORE the query reaches the Neo4j driver.

    This is the async equivalent of SecureNeo4jGraph.
    """

    def __init__(
        self,
        *args,
        sanitizer_enabled: bool = True,
        complexity_limit_enabled: bool = True,
        read_only_mode: bool = False,
        **kwargs,
    ):
        """
        Initialize AsyncSecureNeo4jGraph with security policies.

        Args:
            *args: Positional arguments passed to AsyncNeo4jGraph
            sanitizer_enabled: Enable query sanitization (injection protection)
            complexity_limit_enabled: Enable complexity limiting (DoS protection)
            read_only_mode: Block all write operations (CREATE, MERGE, DELETE, etc.)
            **kwargs: Keyword arguments passed to AsyncNeo4jGraph
        """
        super().__init__(*args, **kwargs)
        self.sanitizer_enabled = sanitizer_enabled
        self.complexity_limit_enabled = complexity_limit_enabled
        self.read_only_mode = read_only_mode

        logger.info("AsyncSecureNeo4jGraph initialized:")
        logger.info(f"  - Sanitizer: {'ENABLED' if sanitizer_enabled else 'DISABLED'}")
        logger.info(
            f"  - Complexity limiter: {'ENABLED' if complexity_limit_enabled else 'DISABLED'}"
        )
        logger.info(f"  - Read-only mode: {'ENABLED' if read_only_mode else 'DISABLED'}")

    async def query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Execute a Cypher query with security checks BEFORE execution.

        Security checks (in order):
        1. Query sanitization - Blocks injections, malformed Unicode, dangerous patterns
        2. Complexity limiting - Prevents resource exhaustion attacks
        3. Read-only enforcement - Blocks write operations if read_only_mode=True

        Args:
            query: Cypher query to execute
            params: Optional query parameters

        Returns:
            Query results from Neo4j

        Raises:
            ValueError: If query violates any security policy
        """
        logger.debug(f"AsyncSecureNeo4jGraph.query() called with: {query[:100]}...")

        # SECURITY CHECK 1: Sanitization (injection + Unicode attacks)
        if self.sanitizer_enabled:
            is_safe, sanitize_error, warnings = sanitize_query(query, params)

            if not is_safe:
                error_msg = f"Query blocked by sanitizer: {sanitize_error}"
                # Phase 4: Use warning for expected security violations (not system errors)
                logger.warning(f"🔒 SECURITY: {error_msg}")
                raise ValueError(error_msg)

            # Log warnings (non-blocking)
            if warnings:
                for warning in warnings:
                    logger.warning(f"Query sanitizer warning: {warning}")

        # SECURITY CHECK 2: Complexity limiting (DoS protection)
        if self.complexity_limit_enabled:
            is_allowed, complexity_error, complexity_score = check_query_complexity(query)

            if not is_allowed:
                error_msg = f"Query blocked by complexity limiter: {complexity_error}"
                # Phase 4: Use warning for expected security violations (not system errors)
                logger.warning(f"🔒 SECURITY: {error_msg}")
                raise ValueError(error_msg)

            # Log complexity warnings (non-blocking)
            if complexity_score and complexity_score.warnings:
                for warning in complexity_score.warnings:
                    logger.info(f"Query complexity warning: {warning}")

        # SECURITY CHECK 3: Read-only mode enforcement
        if self.read_only_mode:
            from neo4j_yass_mcp.security.validators import check_read_only_access

            read_only_error = check_read_only_access(query, read_only_mode=True)

            if read_only_error:
                error_msg = f"Query blocked in read-only mode: {read_only_error}"
                # Phase 4: Use warning for expected security violations (not system errors)
                logger.warning(f"🔒 SECURITY: {error_msg}")
                raise ValueError(error_msg)

        # ALL SECURITY CHECKS PASSED - Execute query
        logger.debug("All security checks passed, executing async query")
        return await super().query(query, params)

    async def query_with_summary(
        self, query: str, params: dict[str, Any] | None = None, *, fetch_records: bool = False
    ) -> tuple[list[dict[str, Any]], Any]:
        """
        Execute a Cypher query with security checks and return both data and summary.

        Security checks (in order):
        1. Query sanitization - Blocks injections, malformed Unicode, dangerous patterns
        2. Complexity limiting - Prevents resource exhaustion attacks
        3. Read-only enforcement - Blocks write operations if read_only_mode=True

        Args:
            query: Cypher query to execute
            params: Optional query parameters
            fetch_records: If True, materialize all records. If False (default), only fetch
                          the summary. For EXPLAIN/PROFILE queries, set to False to avoid
                          unnecessary result streaming.

        Returns:
            Tuple of (records, summary) where:
            - records: List of result records as dictionaries (empty if fetch_records=False)
            - summary: Neo4j ResultSummary containing plan, statistics, etc.

        Raises:
            ValueError: If query violates any security policy
        """
        logger.debug(f"AsyncSecureNeo4jGraph.query_with_summary() called with: {query[:100]}...")

        # SECURITY CHECK 1: Sanitization (injection + Unicode attacks)
        if self.sanitizer_enabled:
            is_safe, sanitize_error, warnings = sanitize_query(query, params)

            if not is_safe:
                error_msg = f"Query blocked by sanitizer: {sanitize_error}"
                logger.warning(f"🔒 SECURITY: {error_msg}")
                raise ValueError(error_msg)

            # Log warnings (non-blocking)
            if warnings:
                for warning in warnings:
                    logger.warning(f"Query sanitizer warning: {warning}")

        # SECURITY CHECK 2: Complexity limiting (DoS protection)
        if self.complexity_limit_enabled:
            is_allowed, complexity_error, complexity_score = check_query_complexity(query)

            if not is_allowed:
                error_msg = f"Query blocked by complexity limiter: {complexity_error}"
                logger.warning(f"🔒 SECURITY: {error_msg}")
                raise ValueError(error_msg)

            # Log complexity warnings (non-blocking)
            if complexity_score and complexity_score.warnings:
                for warning in complexity_score.warnings:
                    logger.info(f"Query complexity warning: {warning}")

        # SECURITY CHECK 3: Read-only mode enforcement
        if self.read_only_mode:
            from neo4j_yass_mcp.security.validators import check_read_only_access

            read_only_error = check_read_only_access(query, read_only_mode=True)

            if read_only_error:
                error_msg = f"Query blocked in read-only mode: {read_only_error}"
                logger.warning(f"🔒 SECURITY: {error_msg}")
                raise ValueError(error_msg)

        # ALL SECURITY CHECKS PASSED - Execute query
        logger.debug("All security checks passed, executing async query with summary")
        return await super().query_with_summary(query, params, fetch_records=fetch_records)
