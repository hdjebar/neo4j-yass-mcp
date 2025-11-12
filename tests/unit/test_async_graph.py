"""
Unit tests for AsyncNeo4jGraph and AsyncSecureNeo4jGraph.

These tests verify the async graph wrapper functionality including:
- Connection management
- Query execution
- Schema refresh
- Security layer integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from neo4j_yass_mcp.async_graph import AsyncNeo4jGraph, AsyncSecureNeo4jGraph


class TestAsyncNeo4jGraph:
    """Test suite for AsyncNeo4jGraph base class."""

    @pytest.fixture
    def mock_driver(self):
        """Create a mock async Neo4j driver."""
        driver = AsyncMock()
        driver.session = MagicMock()
        return driver

    @pytest.fixture
    def mock_session(self):
        """Create a mock async Neo4j session."""
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_initialization(self, mock_driver):
        """Test AsyncNeo4jGraph initialization."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver

            graph = AsyncNeo4jGraph(
                url="bolt://localhost:7687",
                username="neo4j",
                password="password",
                database="test_db",
                driver_config={"max_connection_pool_size": 50},
            )

            assert graph._url == "bolt://localhost:7687"
            assert graph._username == "neo4j"
            assert graph._password == "password"
            assert graph._database == "test_db"
            assert graph._driver_config == {"max_connection_pool_size": 50}

            # Verify driver was created with correct parameters
            mock_db.assert_called_once_with(
                "bolt://localhost:7687",
                auth=("neo4j", "password"),
                max_connection_pool_size=50,
            )

    @pytest.mark.asyncio
    async def test_query_execution(self, mock_driver, mock_session):
        """Test async query execution."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver
            mock_driver.session.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.data = AsyncMock(
                return_value=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
            )
            mock_session.run = AsyncMock(return_value=mock_result)

            graph = AsyncNeo4jGraph(
                url="bolt://localhost:7687", username="neo4j", password="password"
            )

            result = await graph.query("MATCH (n:Person) RETURN n.name AS name, n.age AS age")

            assert len(result) == 2
            assert result[0] == {"name": "Alice", "age": 30}
            assert result[1] == {"name": "Bob", "age": 25}

            # Verify session was created with correct database
            mock_driver.session.assert_called_once_with(database="neo4j")

            # Verify query was executed
            mock_session.run.assert_called_once_with(
                "MATCH (n:Person) RETURN n.name AS name, n.age AS age", {}
            )

    @pytest.mark.asyncio
    async def test_query_with_parameters(self, mock_driver, mock_session):
        """Test async query execution with parameters."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver
            mock_driver.session.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.data = AsyncMock(return_value=[{"name": "Alice", "age": 30}])
            mock_session.run = AsyncMock(return_value=mock_result)

            graph = AsyncNeo4jGraph(
                url="bolt://localhost:7687", username="neo4j", password="password"
            )

            result = await graph.query(
                "MATCH (n:Person {name: $name}) RETURN n.name AS name, n.age AS age",
                params={"name": "Alice"},
            )

            assert len(result) == 1
            assert result[0]["name"] == "Alice"

            # Verify parameters were passed
            mock_session.run.assert_called_once_with(
                "MATCH (n:Person {name: $name}) RETURN n.name AS name, n.age AS age",
                {"name": "Alice"},
            )

    @pytest.mark.asyncio
    async def test_refresh_schema(self, mock_driver, mock_session):
        """Test async schema refresh."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver
            mock_driver.session.return_value = mock_session

            # Mock schema queries
            labels_result = AsyncMock()
            labels_result.data = AsyncMock(return_value=[{"label": "Person"}, {"label": "Movie"}])

            rels_result = AsyncMock()
            rels_result.data = AsyncMock(
                return_value=[{"relationshipType": "ACTED_IN"}, {"relationshipType": "DIRECTED"}]
            )

            props_result = AsyncMock()
            props_result.data = AsyncMock(
                return_value=[{"key": "name", "type": "STRING"}, {"key": "age", "type": "INTEGER"}]
            )

            patterns_result = AsyncMock()
            patterns_result.data = AsyncMock(
                return_value=[
                    {"pattern": "(:Person)-[:ACTED_IN]->(:Movie)"},
                    {"pattern": "(:Person)-[:DIRECTED]->(:Movie)"},
                ]
            )

            # Mock session.run to return different results based on query
            async def mock_run(query, *args, **kwargs):
                if "db.labels()" in query:
                    return labels_result
                elif "db.relationshipTypes()" in query:
                    return rels_result
                elif "MATCH (a)-[r]->(b)" in query:
                    return patterns_result
                else:
                    return props_result

            mock_session.run = AsyncMock(side_effect=mock_run)

            graph = AsyncNeo4jGraph(
                url="bolt://localhost:7687", username="neo4j", password="password"
            )

            await graph.refresh_schema()

            # Verify schema was cached
            assert "Person" in graph.get_schema
            assert "Movie" in graph.get_schema
            assert "ACTED_IN" in graph.get_schema
            assert "DIRECTED" in graph.get_schema

            # Verify structured schema
            assert "Person" in graph.get_structured_schema["labels"]
            assert "Movie" in graph.get_structured_schema["labels"]
            assert "ACTED_IN" in graph.get_structured_schema["relationships"]

    @pytest.mark.asyncio
    async def test_close(self, mock_driver):
        """Test closing the driver connection."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver

            graph = AsyncNeo4jGraph(
                url="bolt://localhost:7687", username="neo4j", password="password"
            )

            await graph.close()

            # Verify driver was closed
            mock_driver.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_driver):
        """Test async context manager support."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver

            async with AsyncNeo4jGraph(
                url="bolt://localhost:7687", username="neo4j", password="password"
            ) as graph:
                assert graph is not None

            # Verify driver was closed on exit
            mock_driver.close.assert_called_once()


class TestAsyncSecureNeo4jGraph:
    """Test suite for AsyncSecureNeo4jGraph security layer."""

    @pytest.fixture
    def mock_driver(self):
        """Create a mock async Neo4j driver."""
        driver = AsyncMock()
        driver.session = MagicMock()
        return driver

    @pytest.fixture
    def mock_session(self):
        """Create a mock async Neo4j session."""
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_security_initialization(self, mock_driver):
        """Test security layer initialization."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver

            graph = AsyncSecureNeo4jGraph(
                url="bolt://localhost:7687",
                username="neo4j",
                password="password",
                sanitizer_enabled=True,
                complexity_limit_enabled=True,
                read_only_mode=True,
            )

            assert graph.sanitizer_enabled is True
            assert graph.complexity_limit_enabled is True
            assert graph.read_only_mode is True

    @pytest.mark.asyncio
    async def test_query_with_sanitization(self, mock_driver, mock_session):
        """Test query execution with sanitization enabled."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver
            mock_driver.session.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.data = AsyncMock(return_value=[{"name": "Alice"}])
            mock_session.run = AsyncMock(return_value=mock_result)

            # Mock sanitizer (safe query)
            with patch("neo4j_yass_mcp.async_graph.sanitize_query") as mock_sanitize:
                mock_sanitize.return_value = (True, None, [])  # Safe, no error, no warnings

                graph = AsyncSecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    sanitizer_enabled=True,
                    complexity_limit_enabled=False,
                    read_only_mode=False,
                )

                result = await graph.query("MATCH (n:Person) RETURN n.name AS name")

                # Verify sanitizer was called
                mock_sanitize.assert_called_once_with(
                    "MATCH (n:Person) RETURN n.name AS name", None
                )

                # Verify query was executed
                assert len(result) == 1
                assert result[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_query_blocked_by_sanitizer(self, mock_driver):
        """Test query blocked by sanitizer."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver

            # Mock sanitizer (unsafe query)
            with patch("neo4j_yass_mcp.async_graph.sanitize_query") as mock_sanitize:
                mock_sanitize.return_value = (
                    False,
                    "SQL injection detected",
                    [],
                )  # Unsafe, error

                graph = AsyncSecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    sanitizer_enabled=True,
                )

                with pytest.raises(ValueError, match="Query blocked by sanitizer"):
                    await graph.query("MATCH (n) WHERE n.id = '1 OR 1=1' RETURN n")

    @pytest.mark.asyncio
    async def test_query_with_complexity_limiting(self, mock_driver, mock_session):
        """Test query execution with complexity limiting enabled."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver
            mock_driver.session.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.data = AsyncMock(return_value=[{"count": 100}])
            mock_session.run = AsyncMock(return_value=mock_result)

            # Mock complexity checker (allowed)
            with patch("neo4j_yass_mcp.async_graph.check_query_complexity") as mock_complexity:
                mock_complexity.return_value = (True, None, None)  # Allowed, no error

                graph = AsyncSecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    sanitizer_enabled=False,
                    complexity_limit_enabled=True,
                    read_only_mode=False,
                )

                result = await graph.query("MATCH (n) RETURN count(n)")

                # Verify complexity checker was called
                mock_complexity.assert_called_once_with("MATCH (n) RETURN count(n)")

                # Verify query was executed
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_query_blocked_by_complexity(self, mock_driver):
        """Test query blocked by complexity limiter."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver

            # Mock complexity checker (too complex)
            with patch("neo4j_yass_mcp.async_graph.check_query_complexity") as mock_complexity:
                mock_complexity.return_value = (False, "Query too complex", None)  # Blocked

                graph = AsyncSecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    sanitizer_enabled=False,
                    complexity_limit_enabled=True,
                )

                with pytest.raises(ValueError, match="Query blocked by complexity limiter"):
                    await graph.query("MATCH (a)-[*10]-(b) RETURN a, b")

    @pytest.mark.asyncio
    async def test_query_blocked_by_read_only_mode(self, mock_driver):
        """Test query blocked in read-only mode."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver

            # Mock read-only checker (write operation)
            with patch(
                "neo4j_yass_mcp.security.validators.check_read_only_access"
            ) as mock_read_only:
                mock_read_only.return_value = "Write operation not allowed in read-only mode"

                graph = AsyncSecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    sanitizer_enabled=False,
                    complexity_limit_enabled=False,
                    read_only_mode=True,
                )

                with pytest.raises(ValueError, match="Query blocked in read-only mode"):
                    await graph.query("CREATE (n:Person {name: 'Alice'})")

    @pytest.mark.asyncio
    async def test_all_security_checks_pass(self, mock_driver, mock_session):
        """Test query execution with all security checks passing."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver
            mock_driver.session.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.data = AsyncMock(return_value=[{"name": "Alice"}])
            mock_session.run = AsyncMock(return_value=mock_result)

            # Mock all security checks (all pass)
            with patch("neo4j_yass_mcp.async_graph.sanitize_query") as mock_sanitize:
                mock_sanitize.return_value = (True, None, [])

                with patch("neo4j_yass_mcp.async_graph.check_query_complexity") as mock_complexity:
                    mock_complexity.return_value = (True, None, None)

                    with patch(
                        "neo4j_yass_mcp.security.validators.check_read_only_access"
                    ) as mock_read_only:
                        mock_read_only.return_value = None  # No error

                        graph = AsyncSecureNeo4jGraph(
                            url="bolt://localhost:7687",
                            username="neo4j",
                            password="password",
                            sanitizer_enabled=True,
                            complexity_limit_enabled=True,
                            read_only_mode=False,
                        )

                        result = await graph.query("MATCH (n:Person) RETURN n.name AS name")

                        # Verify all checks were called
                        mock_sanitize.assert_called_once()
                        mock_complexity.assert_called_once()
                        # read_only not called because read_only_mode=False

                        # Verify query was executed
                        assert len(result) == 1
                        assert result[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_security_checks_disabled(self, mock_driver, mock_session):
        """Test query execution with all security checks disabled."""
        with patch("neo4j_yass_mcp.async_graph.AsyncGraphDatabase.driver") as mock_db:
            mock_db.return_value = mock_driver
            mock_driver.session.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.data = AsyncMock(return_value=[{"name": "Alice"}])
            mock_session.run = AsyncMock(return_value=mock_result)

            # Mock security checks (shouldn't be called)
            with patch("neo4j_yass_mcp.async_graph.sanitize_query") as mock_sanitize:
                with patch("neo4j_yass_mcp.async_graph.check_query_complexity") as mock_complexity:
                    graph = AsyncSecureNeo4jGraph(
                        url="bolt://localhost:7687",
                        username="neo4j",
                        password="password",
                        sanitizer_enabled=False,
                        complexity_limit_enabled=False,
                        read_only_mode=False,
                    )

                    result = await graph.query("MATCH (n:Person) RETURN n.name AS name")

                    # Verify security checks were NOT called
                    mock_sanitize.assert_not_called()
                    mock_complexity.assert_not_called()

                    # Verify query was executed
                    assert len(result) == 1
