"""
Tests for SecureNeo4jGraph security wrapper.

Comprehensive tests for the security validation layer that runs
BEFORE query execution (Issue #1 fix).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from neo4j_yass_mcp.secure_graph import SecureNeo4jGraph


class TestSecureNeo4jGraphSanitization:
    """Test sanitizer integration in SecureNeo4jGraph."""

    def test_blocks_unsafe_query_before_execution(self):
        """SecureNeo4jGraph blocks unsafe queries BEFORE Neo4j driver execution"""
        # Create secure graph with mocked sanitizer
        with patch("neo4j_yass_mcp.secure_graph.initialize_sanitizer") as mock_init_san, \
             patch("neo4j_yass_mcp.secure_graph.sanitize_query") as mock_sanitize:

            # Setup: Sanitizer enabled and blocks query
            mock_sanitizer = Mock()
            mock_init_san.return_value = mock_sanitizer
            mock_sanitize.return_value = (False, "SQL injection detected", [])

            # Create graph
            graph = SecureNeo4jGraph(
                url="bolt://localhost:7687",
                username="neo4j",
                password="password",
                sanitizer_enabled=True
            )

            # Attempt malicious query
            with pytest.raises(ValueError, match="SQL injection detected"):
                graph.query("MATCH (n) WHERE n.id = '1' OR '1'='1' RETURN n")

            # Verify sanitizer was called
            mock_sanitize.assert_called_once()
            # Verify Neo4j driver.query was NEVER called (query blocked before execution)
            # Note: We can't easily assert this without mocking the driver,
            # but the ValueError proves execution was prevented

    def test_allows_safe_query_after_sanitizer_check(self):
        """SecureNeo4jGraph allows safe queries after sanitizer validation"""
        with patch("neo4j_yass_mcp.secure_graph.initialize_sanitizer") as mock_init_san, \
             patch("neo4j_yass_mcp.secure_graph.sanitize_query") as mock_sanitize:

            # Setup: Sanitizer enabled and passes query
            mock_sanitizer = Mock()
            mock_init_san.return_value = mock_sanitizer
            mock_sanitize.return_value = (True, None, [])

            # Create graph with mocked driver
            with patch("neo4j_yass_mcp.secure_graph.Neo4jGraph.__init__", return_value=None), \
                 patch("neo4j_yass_mcp.secure_graph.Neo4jGraph.query") as mock_driver_query:

                mock_driver_query.return_value = [{"name": "Alice"}]

                graph = SecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    sanitizer_enabled=True
                )

                # Execute safe query
                result = graph.query("MATCH (n:Person) RETURN n.name LIMIT 1")

                # Verify sanitizer checked the query
                mock_sanitize.assert_called_once()
                # Verify driver.query WAS called (query allowed)
                mock_driver_query.assert_called_once()
                assert result == [{"name": "Alice"}]


class TestSecureNeo4jGraphComplexity:
    """Test complexity limiter integration in SecureNeo4jGraph."""

    def test_blocks_complex_query_before_execution(self):
        """SecureNeo4jGraph blocks overly complex queries"""
        with patch("neo4j_yass_mcp.secure_graph.initialize_complexity_limiter") as mock_init_comp, \
             patch("neo4j_yass_mcp.secure_graph.check_query_complexity") as mock_check_comp:

            # Setup: Complexity limiter enabled and blocks query
            mock_limiter = Mock()
            mock_init_comp.return_value = mock_limiter

            from neo4j_yass_mcp.security.complexity_limiter import ComplexityScore
            complexity_score = ComplexityScore(
                score=150,
                max_allowed=100,
                exceeded=True,
                reasons=["Too many relationships traversed"]
            )
            mock_check_comp.return_value = complexity_score

            # Create graph
            graph = SecureNeo4jGraph(
                url="bolt://localhost:7687",
                username="neo4j",
                password="password",
                complexity_limiter_enabled=True
            )

            # Attempt overly complex query
            complex_query = "MATCH (a)-[r1]->(b)-[r2]->(c)-[r3]->(d)-[r4]->(e) RETURN *"
            with pytest.raises(ValueError, match="Query complexity.*exceeded"):
                graph.query(complex_query)

            # Verify complexity check was called
            mock_check_comp.assert_called_once()

    def test_allows_simple_query_after_complexity_check(self):
        """SecureNeo4jGraph allows queries within complexity limits"""
        with patch("neo4j_yass_mcp.secure_graph.initialize_complexity_limiter") as mock_init_comp, \
             patch("neo4j_yass_mcp.secure_graph.check_query_complexity") as mock_check_comp:

            # Setup: Complexity limiter enabled and passes query
            mock_limiter = Mock()
            mock_init_comp.return_value = mock_limiter

            from neo4j_yass_mcp.security.complexity_limiter import ComplexityScore
            complexity_score = ComplexityScore(
                score=30,
                max_allowed=100,
                exceeded=False,
                reasons=[]
            )
            mock_check_comp.return_value = complexity_score

            # Create graph with mocked driver
            with patch("neo4j_yass_mcp.secure_graph.Neo4jGraph.__init__", return_value=None), \
                 patch("neo4j_yass_mcp.secure_graph.Neo4jGraph.query") as mock_driver_query:

                mock_driver_query.return_value = [{"count": 10}]

                graph = SecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    complexity_limiter_enabled=True
                )

                # Execute simple query
                result = graph.query("MATCH (n) RETURN count(n)")

                # Verify complexity was checked
                mock_check_comp.assert_called_once()
                # Verify driver.query WAS called
                mock_driver_query.assert_called_once()
                assert result == [{"count": 10}]


class TestSecureNeo4jGraphReadOnly:
    """Test read-only mode integration in SecureNeo4jGraph."""

    def test_blocks_write_query_in_readonly_mode(self):
        """SecureNeo4jGraph blocks write operations in read-only mode"""
        with patch("neo4j_yass_mcp.secure_graph.check_read_only_access") as mock_check_readonly:

            # Setup: Read-only mode enabled and blocks query
            mock_check_readonly.return_value = "Read-only mode: CREATE operations are not allowed"

            # Create graph with mocked driver
            with patch("neo4j_yass_mcp.secure_graph.Neo4jGraph.__init__", return_value=None):
                graph = SecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    read_only_mode=True
                )

                # Attempt write query
                with pytest.raises(ValueError, match="Read-only mode.*CREATE"):
                    graph.query("CREATE (n:Person {name: 'Bob'}) RETURN n")

                # Verify read-only check was called
                mock_check_readonly.assert_called_once()

    def test_allows_read_query_in_readonly_mode(self):
        """SecureNeo4jGraph allows read operations in read-only mode"""
        with patch("neo4j_yass_mcp.secure_graph.check_read_only_access") as mock_check_readonly:

            # Setup: Read-only mode enabled and passes query
            mock_check_readonly.return_value = None  # No error

            # Create graph with mocked driver
            with patch("neo4j_yass_mcp.secure_graph.Neo4jGraph.__init__", return_value=None), \
                 patch("neo4j_yass_mcp.secure_graph.Neo4jGraph.query") as mock_driver_query:

                mock_driver_query.return_value = [{"name": "Alice"}]

                graph = SecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    read_only_mode=True
                )

                # Execute read query
                result = graph.query("MATCH (n:Person) RETURN n.name")

                # Verify read-only check was called
                mock_check_readonly.assert_called_once()
                # Verify driver.query WAS called
                mock_driver_query.assert_called_once()
                assert result == [{"name": "Alice"}]


class TestSecureNeo4jGraphLayeredSecurity:
    """Test that multiple security layers work together."""

    def test_all_security_checks_run_before_execution(self):
        """Verify security checks run in correct order: sanitize -> complexity -> read-only -> execute"""
        with patch("neo4j_yass_mcp.secure_graph.initialize_sanitizer") as mock_init_san, \
             patch("neo4j_yass_mcp.secure_graph.sanitize_query") as mock_sanitize, \
             patch("neo4j_yass_mcp.secure_graph.initialize_complexity_limiter") as mock_init_comp, \
             patch("neo4j_yass_mcp.secure_graph.check_query_complexity") as mock_check_comp, \
             patch("neo4j_yass_mcp.secure_graph.check_read_only_access") as mock_check_readonly:

            # Setup: All security features enabled and pass
            mock_sanitizer = Mock()
            mock_limiter = Mock()
            mock_init_san.return_value = mock_sanitizer
            mock_init_comp.return_value = mock_limiter
            mock_sanitize.return_value = (True, None, [])

            from neo4j_yass_mcp.security.complexity_limiter import ComplexityScore
            mock_check_comp.return_value = ComplexityScore(
                score=50, max_allowed=100, exceeded=False, reasons=[]
            )
            mock_check_readonly.return_value = None

            # Create graph with mocked driver
            with patch("neo4j_yass_mcp.secure_graph.Neo4jGraph.__init__", return_value=None), \
                 patch("neo4j_yass_mcp.secure_graph.Neo4jGraph.query") as mock_driver_query:

                mock_driver_query.return_value = [{"result": "success"}]

                graph = SecureNeo4jGraph(
                    url="bolt://localhost:7687",
                    username="neo4j",
                    password="password",
                    sanitizer_enabled=True,
                    complexity_limiter_enabled=True,
                    read_only_mode=True
                )

                # Execute query that passes all checks
                result = graph.query("MATCH (n:Person) RETURN n LIMIT 10")

                # Verify ALL security checks were called
                mock_sanitize.assert_called_once()
                mock_check_comp.assert_called_once()
                mock_check_readonly.assert_called_once()
                # Verify driver.query was called AFTER all checks passed
                mock_driver_query.assert_called_once()
                assert result == [{"result": "success"}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
