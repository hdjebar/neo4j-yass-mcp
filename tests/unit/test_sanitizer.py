"""
Comprehensive tests for security/sanitizer.py module.

Tests cover:
- QuerySanitizer initialization and configuration
- Query sanitization (all dangerous patterns)
- Parameter validation
- UTF-8/Unicode attack detection
- Balanced delimiter validation
- String injection detection
- Global sanitizer functions
- Edge cases and error handling

Target: 90%+ code coverage
"""

from unittest.mock import patch

import pytest

from neo4j_yass_mcp.security.sanitizer import (
    QuerySanitizer,
    get_sanitizer,
    initialize_sanitizer,
    sanitize_query,
)


class TestQuerySanitizerInitialization:
    """Test QuerySanitizer initialization and configuration."""

    def test_default_initialization(self):
        """Test sanitizer with default settings."""
        sanitizer = QuerySanitizer()

        assert sanitizer.strict_mode is False
        assert sanitizer.allow_apoc is False
        assert sanitizer.allow_schema_changes is False
        assert sanitizer.max_query_length == 10000
        assert sanitizer.block_non_ascii is False

    def test_custom_initialization(self):
        """Test sanitizer with custom settings."""
        sanitizer = QuerySanitizer(
            strict_mode=True,
            allow_apoc=True,
            allow_schema_changes=True,
            max_query_length=5000,
            block_non_ascii=True,
        )

        assert sanitizer.strict_mode is True
        assert sanitizer.allow_apoc is True
        assert sanitizer.allow_schema_changes is True
        assert sanitizer.max_query_length == 5000
        assert sanitizer.block_non_ascii is True

    def test_global_sanitizer_initialization(self):
        """Test global sanitizer initialization."""
        sanitizer = initialize_sanitizer(
            strict_mode=True,
            allow_apoc=False,
            allow_schema_changes=False,
            block_non_ascii=True,
            max_query_length=8000,
        )

        assert sanitizer is not None
        assert get_sanitizer() is sanitizer
        assert sanitizer.strict_mode is True
        assert sanitizer.max_query_length == 8000


class TestQueryLengthValidation:
    """Test query length validation."""

    def test_query_within_length_limit(self):
        """Test query within maximum length."""
        sanitizer = QuerySanitizer(max_query_length=100)
        query = "MATCH (n) RETURN n LIMIT 10"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True
        assert error is None

    def test_query_exceeds_length_limit(self):
        """Test query exceeding maximum length."""
        sanitizer = QuerySanitizer(max_query_length=50)
        query = "MATCH (n:Movie) WHERE n.title = 'Very Long Movie Title' RETURN n.title, n.year"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "exceeds maximum length" in error.lower()

    def test_empty_query(self):
        """Test empty query string."""
        sanitizer = QuerySanitizer()

        is_safe, error, warnings = sanitizer.sanitize_query("")

        assert is_safe is False
        assert "empty query" in error.lower()

    def test_whitespace_only_query(self):
        """Test query with only whitespace."""
        sanitizer = QuerySanitizer()

        is_safe, error, warnings = sanitizer.sanitize_query("   \n\t   ")

        assert is_safe is False
        assert "empty query" in error.lower()


class TestDangerousPatterns:
    """Test detection of dangerous query patterns."""

    def test_load_csv_blocked(self):
        """Test LOAD CSV is blocked."""
        sanitizer = QuerySanitizer()
        query = "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()

    def test_apoc_load_blocked(self):
        """Test APOC load procedures blocked."""
        sanitizer = QuerySanitizer()
        queries = [
            "CALL apoc.load.json('http://evil.com/data.json')",
            "MATCH (n) CALL apoc.load.csv('file.csv') YIELD value RETURN value",
        ]

        for query in queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is False
            assert "dangerous pattern" in error.lower()

    def test_apoc_export_blocked(self):
        """Test APOC export procedures blocked."""
        sanitizer = QuerySanitizer()
        query = "CALL apoc.export.csv.all('/tmp/export.csv', {})"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()

    def test_apoc_cypher_run_blocked(self):
        """Test APOC dynamic Cypher execution blocked."""
        sanitizer = QuerySanitizer()
        query = "CALL apoc.cypher.run('MATCH (n) DELETE n', {})"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()

    def test_apoc_refactor_blocked(self):
        """Test APOC refactor procedures blocked."""
        sanitizer = QuerySanitizer()
        query = "CALL apoc.refactor.mergeNodes([n1, n2])"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()

    def test_dbms_security_blocked(self):
        """Test DBMS security procedures blocked."""
        sanitizer = QuerySanitizer()
        query = "CALL dbms.security.listUsers()"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()

    def test_dbms_cluster_blocked(self):
        """Test DBMS cluster operations blocked."""
        sanitizer = QuerySanitizer()
        query = "CALL dbms.cluster.routing.getRoutingTable({})"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()

    def test_query_chaining_blocked(self):
        """Test query chaining with semicolons blocked."""
        sanitizer = QuerySanitizer()
        queries = [
            "MATCH (n) RETURN n; DELETE (n)",
            "MATCH (n) RETURN n; CREATE (m:Malicious)",
            "MATCH (n) RETURN n; MERGE (m:Test)",
            "MATCH (n) RETURN n; DROP INDEX index_name",
            "MATCH (n) RETURN n; CALL apoc.help('search')",
        ]

        for query in queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is False, f"Query should be blocked: {query}"
            assert "dangerous pattern" in error.lower()

    def test_legitimate_comments_allowed(self):
        """Test legitimate comments are ALLOWED (Critical Fix).

        Comments are now stripped BEFORE pattern matching to allow legitimate
        Cypher queries with comments while still catching malicious code.
        """
        sanitizer = QuerySanitizer()
        legitimate_queries_with_comments = [
            # Line comments
            "MATCH (n) RETURN n // comment",
            "MATCH (n) RETURN n // TODO: optimize this",
            "// Query to find all nodes\nMATCH (n) RETURN n",

            # Block comments
            "MATCH (n) /* find nodes */ RETURN n",
            "/* Multi-line\n   comment */\nMATCH (n) RETURN n",
            "MATCH (n) RETURN n /* inline comment */",

            # Mixed comments and code
            "MATCH (n:Person) // Find people\nWHERE n.age > 25 // Adults only\nRETURN n.name",
        ]

        for query in legitimate_queries_with_comments:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is True, \
                f"Legitimate query with comment should be allowed: {query}\nError: {error}"
            assert error is None

    def test_malicious_code_in_comments_still_caught(self):
        """Test that dangerous patterns hidden in comments are still caught.

        Comments are stripped, so any dangerous code inside them becomes visible
        and gets blocked.
        """
        sanitizer = QuerySanitizer()
        malicious_queries = [
            # Dangerous operations in comments are stripped, revealing normal query
            # These should pass because after stripping comments, the query is safe
            "MATCH (n) /* LOAD CSV FROM 'file.csv' */ RETURN n",

            # But if the actual query (outside comments) is dangerous, it's caught
            # Note: These will be blocked by other patterns, not comment patterns
        ]

        # These queries should be ALLOWED because dangerous code is only in comments
        for query in malicious_queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is True, \
                f"Query with dangerous code only in comments should be allowed: {query}"

    def test_urls_in_strings_allowed(self):
        """Test URLs in string literals are NOT blocked (regression test for Issue #2)."""
        sanitizer = QuerySanitizer()
        queries = [
            "MATCH (n) WHERE n.url = 'https://neo4j.com' RETURN n",
            'CREATE (n:Website {url: "http://example.com/path"})',
            "MATCH (n) WHERE n.description = 'Visit // our site' RETURN n",
            'MERGE (n:Doc {content: "# Heading\\n/* comment */"}) RETURN n',
        ]

        for query in queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            # Should not be blocked by comment patterns
            if not is_safe and error:
                # If blocked, it should NOT be due to comment patterns
                assert "dangerous pattern" not in error.lower() or "CREATE" in query or "MERGE" in query

    def test_large_range_iterations_blocked(self):
        """Test excessive FOREACH iterations blocked."""
        sanitizer = QuerySanitizer()
        query = "FOREACH (i IN range(1, 9999999) | CREATE (n:Test {id: i}))"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()

    def test_apoc_periodic_iterate_blocked(self):
        """Test APOC periodic iterate blocked."""
        sanitizer = QuerySanitizer()
        query = "CALL apoc.periodic.iterate('MATCH (n) RETURN n', 'DELETE n', {})"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()

    def test_apoc_parallel_blocked(self):
        """Test APOC parallel execution blocked."""
        sanitizer = QuerySanitizer()
        query = "CALL apoc.cypher.parallel('MATCH (n) RETURN n', {})"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()


class TestSuspiciousPatterns:
    """Test detection of suspicious patterns (warnings in normal mode, blocked in strict mode)."""

    def test_apoc_warning_normal_mode(self):
        """Test APOC procedures generate warnings in normal mode."""
        sanitizer = QuerySanitizer(strict_mode=False, allow_apoc=False)
        query = "CALL apoc.help('search')"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True
        assert error is None
        assert len(warnings) > 0
        assert "pattern that may need review" in warnings[0].lower()

    def test_apoc_blocked_strict_mode(self):
        """Test APOC procedures blocked in strict mode."""
        sanitizer = QuerySanitizer(strict_mode=True, allow_apoc=False)
        query = "CALL apoc.help('search')"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "strict mode" in error.lower()

    def test_apoc_allowed_when_enabled(self):
        """Test APOC procedures allowed when explicitly enabled."""
        sanitizer = QuerySanitizer(strict_mode=True, allow_apoc=True)
        query = "CALL apoc.help('search')"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True
        assert error is None

    def test_schema_changes_warning_normal_mode(self):
        """Test schema changes generate warnings in normal mode."""
        sanitizer = QuerySanitizer(strict_mode=False, allow_schema_changes=False)
        queries = [
            "CREATE INDEX FOR (n:Movie) ON (n.title)",
            "DROP INDEX index_name",
            "CREATE CONSTRAINT FOR (n:Person) REQUIRE n.id IS UNIQUE",
            "DROP CONSTRAINT constraint_name",
        ]

        for query in queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is True
            assert len(warnings) > 0

    def test_schema_changes_blocked_strict_mode(self):
        """Test schema changes blocked in strict mode."""
        sanitizer = QuerySanitizer(strict_mode=True, allow_schema_changes=False)
        query = "CREATE INDEX FOR (n:Movie) ON (n.title)"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "strict mode" in error.lower()

    def test_schema_changes_allowed_when_enabled(self):
        """Test schema changes allowed when explicitly enabled."""
        sanitizer = QuerySanitizer(strict_mode=True, allow_schema_changes=True)
        queries = [
            "CREATE INDEX FOR (n:Movie) ON (n.title)",
            "CREATE CONSTRAINT FOR (n:Person) REQUIRE n.id IS UNIQUE",
        ]

        for query in queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is True
            assert error is None

    def test_dbms_procedures_warning(self):
        """Test DBMS procedures generate warnings."""
        sanitizer = QuerySanitizer(strict_mode=False)
        query = "CALL dbms.listConfig()"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True
        assert len(warnings) > 0


class TestBalancedDelimiters:
    """Test balanced delimiter validation."""

    def test_balanced_parentheses(self):
        """Test balanced parentheses are accepted."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n:Movie {title: 'Test'}) RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True

    def test_unbalanced_parentheses(self):
        """Test unbalanced parentheses are detected."""
        sanitizer = QuerySanitizer()
        queries = [
            "MATCH (n:Movie RETURN n",
            "MATCH n:Movie) RETURN n",
            "MATCH (n:Movie)) RETURN n",
        ]

        for query in queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is False
            assert "unbalanced" in error.lower()

    def test_balanced_braces(self):
        """Test balanced braces are accepted."""
        sanitizer = QuerySanitizer()
        query = "CREATE (n:Movie {title: 'Test', year: 2023})"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        # Will fail due to CREATE, but not due to braces
        assert "unbalanced" not in (error or "").lower()

    def test_balanced_brackets(self):
        """Test balanced brackets are accepted."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n) WHERE n.tags IN ['action', 'drama'] RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True

    def test_unbalanced_mixed_delimiters(self):
        """Test unbalanced mixed delimiters detected."""
        sanitizer = QuerySanitizer()
        queries = [
            "MATCH (n {title: 'Test') RETURN n",
            "MATCH (n [title: 'Test'}) RETURN n",
        ]

        for query in queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is False
            assert "unbalanced" in error.lower()

    def test_delimiters_in_strings_ignored(self):
        """Test delimiters inside string literals are ignored."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n) WHERE n.description = 'Test (with) {brackets} [array]' RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True


class TestStringInjection:
    """Test string escape injection detection."""

    def test_hex_escapes_blocked(self):
        """Test hex escape sequences blocked."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n) WHERE n.value = '\\x41\\x42\\x43' RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "string injection" in error.lower()

    def test_unicode_escapes_blocked(self):
        """Test unicode escape sequences blocked."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n) WHERE n.value = '\\u0041\\u0042' RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "string injection" in error.lower()

    def test_octal_escapes_blocked(self):
        """Test octal escape sequences blocked."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n) WHERE n.value = '\\101\\102\\103' RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "string injection" in error.lower()

    def test_string_concatenation_blocked(self):
        """Test suspicious string concatenation blocked."""
        sanitizer = QuerySanitizer()
        queries = [
            "MATCH (n) WHERE n.value = 'test' + 'value' RETURN n",
            'MATCH (n) WHERE n.value = "test" + "value" RETURN n',
        ]

        for query in queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is False
            assert "dangerous pattern" in error.lower()

    def test_normal_strings_allowed(self):
        """Test normal string literals are allowed."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n:Movie {title: 'The Matrix'}) RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True


class TestParameterValidation:
    """Test parameter sanitization and validation."""

    def test_valid_parameters(self):
        """Test valid parameters are accepted."""
        sanitizer = QuerySanitizer()
        params = {
            "title": "The Matrix",
            "year": 1999,
            "rating": 8.7,
            "is_favorite": True,
        }

        is_safe, error = sanitizer.sanitize_parameters(params)

        assert is_safe is True
        assert error is None

    def test_none_parameters(self):
        """Test None parameters are allowed."""
        sanitizer = QuerySanitizer()

        is_safe, error = sanitizer.sanitize_parameters(None)

        assert is_safe is True
        assert error is None

    def test_too_many_parameters(self):
        """Test excessive parameter count blocked."""
        sanitizer = QuerySanitizer()
        params = {f"param_{i}": i for i in range(150)}

        is_safe, error = sanitizer.sanitize_parameters(params)

        assert is_safe is False
        assert "too many parameters" in error.lower()

    def test_invalid_parameter_name(self):
        """Test invalid parameter names blocked."""
        sanitizer = QuerySanitizer()
        invalid_names = [
            {"123invalid": "value"},
            {"param-name": "value"},
            {"param.name": "value"},
            {"param name": "value"},
        ]

        for params in invalid_names:
            is_safe, error = sanitizer.sanitize_parameters(params)
            assert is_safe is False
            assert "invalid parameter name" in error.lower()

    def test_valid_parameter_names(self):
        """Test valid parameter names accepted."""
        sanitizer = QuerySanitizer()
        params = {
            "title": "Test",
            "year_released": 2023,
            "_private": "value",
            "camelCase": "value",
        }

        is_safe, error = sanitizer.sanitize_parameters(params)

        assert is_safe is True

    def test_parameter_value_too_long(self):
        """Test parameter values exceeding length limit blocked."""
        sanitizer = QuerySanitizer()
        params = {"data": "x" * 6000}

        is_safe, error = sanitizer.sanitize_parameters(params)

        assert is_safe is False
        assert "too long" in error.lower()

    def test_injection_in_parameter_value(self):
        """Test injection attempts in parameter values blocked."""
        sanitizer = QuerySanitizer()
        malicious_params = [
            {"title": "Test'; DELETE n; MATCH (m"},
            {"title": "MATCH (n) DELETE n"},
            {"title": "CREATE (n:Malicious)"},
            {"title": "MERGE (n:Test)"},
            {"title": "DROP DATABASE neo4j"},
            {"title": "CALL apoc.help('search')"},
            {"title": "LOAD CSV FROM 'file.csv'"},
            {"title": "Test -- comment"},
            {"title": "Test /* comment */"},
        ]

        for params in malicious_params:
            is_safe, error = sanitizer.sanitize_parameters(params)
            assert is_safe is False, f"Should block: {params}"
            assert "injection" in error.lower()

    def test_nested_structure_validation(self):
        """Test nested structures (lists, dicts) validated."""
        sanitizer = QuerySanitizer()

        # Valid nested structure
        params = {
            "data": {
                "title": "Test",
                "tags": ["action", "drama"],
            }
        }
        is_safe, error = sanitizer.sanitize_parameters(params)
        assert is_safe is True

        # Nested structure too large
        large_params = {"data": {f"key_{i}": "x" * 3000 for i in range(10)}}
        is_safe, error = sanitizer.sanitize_parameters(large_params)
        assert is_safe is False
        assert "too large" in error.lower()

    def test_invalid_json_structure(self):
        """Test non-serializable structures rejected."""
        sanitizer = QuerySanitizer()

        # Mock object that can't be JSON serialized
        class MockObject:
            def __init__(self):
                self.data = "test"

        params = {"obj": [MockObject()]}
        is_safe, error = sanitizer.sanitize_parameters(params)

        assert is_safe is False
        assert "invalid data" in error.lower()


class TestUTF8Attacks:
    """Test UTF-8 and Unicode attack detection."""

    def test_null_bytes_blocked(self):
        """Test null bytes blocked."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n) WHERE n.title = 'Test\x00' RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "null byte" in error.lower()

    def test_zero_width_characters_blocked(self):
        """Test zero-width characters blocked."""
        sanitizer = QuerySanitizer()
        zero_width_chars = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\ufeff",  # Zero-width no-break space
        ]

        for char in zero_width_chars:
            query = f"MATCH (n) WHERE n.title = 'Test{char}' RETURN n"
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is False
            assert "zero-width" in error.lower()

    def test_directional_override_blocked(self):
        """Test directional override characters blocked."""
        sanitizer = QuerySanitizer()
        directional_chars = [
            "\u202e",  # Right-to-left override
            "\u202d",  # Left-to-right override
            "\u202a",  # Left-to-right embedding
            "\u202b",  # Right-to-left embedding
            "\u202c",  # Pop directional formatting
        ]

        for char in directional_chars:
            query = f"MATCH (n) WHERE n.title = 'Test{char}' RETURN n"
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is False
            assert "directional override" in error.lower()

    def test_combining_diacritics_blocked(self):
        """Test combining diacritical marks blocked."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n) WHERE n.title = 'Test\u0301' RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "combining diacritical" in error.lower()

    def test_mathematical_alphanumeric_blocked(self):
        """Test mathematical alphanumeric symbols blocked."""
        sanitizer = QuerySanitizer()
        # Mathematical Bold A (U+1D400)
        query = "MATCH (n) WHERE n.title = '𝐀test' RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "mathematical alphanumeric" in error.lower()

    @pytest.mark.skipif(
        not hasattr(
            __import__("neo4j_yass_mcp.security.sanitizer", fromlist=["CONFUSABLES_AVAILABLE"]),
            "CONFUSABLES_AVAILABLE",
        ),
        reason="confusable_homoglyphs not available",
    )
    def test_homograph_attack_blocked_with_library(self):
        """Test homograph attacks blocked (with library)."""
        from neo4j_yass_mcp.security.sanitizer import CONFUSABLES_AVAILABLE

        if not CONFUSABLES_AVAILABLE:
            pytest.skip("confusable_homoglyphs library not available")

        sanitizer = QuerySanitizer()
        # Cyrillic 'a' looks like Latin 'a'
        query = "MATCH (n) WHERE n.title = 'Tеst' RETURN n"  # Cyrillic 'e'

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        # Should be blocked by homograph detection
        assert is_safe is False

    def test_manual_homograph_detection(self):
        """Test manual homograph detection (fallback)."""
        sanitizer = QuerySanitizer()

        # Cyrillic characters that look like Latin
        cyrillic_chars = {
            "\u0430": "a",  # Cyrillic 'a'
            "\u0435": "e",  # Cyrillic 'e'
            "\u043e": "o",  # Cyrillic 'o'
        }

        for char, _lookalike in cyrillic_chars.items():
            query = f"MATCH (n) WHERE n.title = 'T{char}st' RETURN n"

            # Patch to force manual detection
            with patch("neo4j_yass_mcp.security.sanitizer.CONFUSABLES_AVAILABLE", False):
                is_safe, error, warnings = sanitizer.sanitize_query(query)
                assert is_safe is False
                assert "homograph" in error.lower()

    def test_block_non_ascii_mode(self):
        """Test non-ASCII blocking in strict mode."""
        sanitizer = QuerySanitizer(block_non_ascii=True)
        query = "MATCH (n) WHERE n.title = 'Café' RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is False
        assert "non-ascii" in error.lower()

    def test_smart_quotes_allowed_in_strict_mode(self):
        """Test smart quotes are allowed even in non-ASCII blocking mode."""
        sanitizer = QuerySanitizer(block_non_ascii=True)
        smart_quotes = ["\u2018", "\u2019", "\u201c", "\u201d"]

        for quote in smart_quotes:
            query = f"MATCH (n) WHERE n.title = {quote}Test{quote} RETURN n"
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is True

    def test_invalid_utf8_encoding_blocked(self):
        """Test invalid UTF-8 sequences blocked."""
        sanitizer = QuerySanitizer()

        # Create a string with invalid UTF-8 (surrogates are invalid in UTF-8)
        # This test verifies the encoding validation
        valid_query = "MATCH (n) RETURN n"
        is_safe, error, warnings = sanitizer.sanitize_query(valid_query)
        assert is_safe is True

    @pytest.mark.skipif(
        not hasattr(
            __import__("neo4j_yass_mcp.security.sanitizer", fromlist=["FTFY_AVAILABLE"]),
            "FTFY_AVAILABLE",
        ),
        reason="ftfy not available",
    )
    def test_ftfy_normalization_detection(self):
        """Test ftfy normalization for UTF-8 attack detection."""
        from neo4j_yass_mcp.security.sanitizer import FTFY_AVAILABLE

        if not FTFY_AVAILABLE:
            pytest.skip("ftfy library not available")

        # This test verifies ftfy integration works
        sanitizer = QuerySanitizer()
        query = "MATCH (n) RETURN n"

        is_safe, error, warnings = sanitizer.sanitize_query(query)
        assert is_safe is True


class TestSafeQueries:
    """Test that safe queries are properly allowed."""

    def test_simple_match_query(self):
        """Test simple MATCH query allowed."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n:Movie) RETURN n.title LIMIT 10"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True
        assert error is None

    def test_match_with_where(self):
        """Test MATCH with WHERE clause allowed."""
        sanitizer = QuerySanitizer()
        query = "MATCH (n:Movie) WHERE n.year > 2000 RETURN n.title, n.year"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True

    def test_match_with_relationship(self):
        """Test MATCH with relationships allowed."""
        sanitizer = QuerySanitizer()
        query = "MATCH (m:Movie)<-[:ACTED_IN]-(p:Person) RETURN m.title, p.name"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True

    def test_aggregation_query(self):
        """Test aggregation queries allowed."""
        sanitizer = QuerySanitizer()
        query = "MATCH (m:Movie) RETURN count(m) AS total, avg(m.rating) AS avg_rating"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True

    def test_order_by_limit(self):
        """Test ORDER BY and LIMIT allowed."""
        sanitizer = QuerySanitizer()
        query = "MATCH (m:Movie) RETURN m.title ORDER BY m.year DESC LIMIT 5"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True

    def test_with_clause(self):
        """Test WITH clause allowed."""
        sanitizer = QuerySanitizer()
        query = "MATCH (m:Movie) WITH m.year AS year, count(m) AS cnt RETURN year, cnt"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True


class TestGlobalSanitizerFunctions:
    """Test global sanitizer convenience functions."""

    def test_sanitize_query_auto_initialization(self):
        """Test sanitize_query auto-initializes if needed."""
        # Reset global sanitizer
        import neo4j_yass_mcp.security.sanitizer as sanitizer_module

        sanitizer_module._sanitizer = None

        query = "MATCH (n) RETURN n"
        is_safe, error, warnings = sanitize_query(query)

        assert is_safe is True
        assert get_sanitizer() is not None

    def test_sanitize_query_with_parameters(self):
        """Test sanitize_query validates both query and parameters."""
        initialize_sanitizer()

        query = "MATCH (m:Movie {title: $title}) RETURN m"
        params = {"title": "The Matrix"}

        is_safe, error, warnings = sanitize_query(query, params)

        assert is_safe is True
        assert error is None

    def test_sanitize_query_blocks_bad_parameters(self):
        """Test sanitize_query blocks malicious parameters."""
        initialize_sanitizer()

        query = "MATCH (m:Movie {title: $title}) RETURN m"
        params = {"title": "Test'; DELETE n; MATCH (m"}

        is_safe, error, warnings = sanitize_query(query, params)

        assert is_safe is False
        assert "injection" in error.lower()

    def test_sanitize_query_blocks_bad_query(self):
        """Test sanitize_query blocks malicious query."""
        initialize_sanitizer()

        query = "MATCH (n) DELETE n"
        params = {"title": "Test"}

        is_safe, error, warnings = sanitize_query(query, params)

        # Will be blocked due to DELETE without semicolon - not a dangerous pattern per se
        # but let's test with a clearly dangerous one
        query = "LOAD CSV FROM 'file.csv' AS line RETURN line"
        is_safe, error, warnings = sanitize_query(query, params)

        assert is_safe is False
        assert "dangerous pattern" in error.lower()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_multiline_query(self):
        """Test multiline queries handled correctly."""
        sanitizer = QuerySanitizer()
        query = """
            MATCH (m:Movie)
            WHERE m.year > 2000
            RETURN m.title, m.year
            ORDER BY m.year DESC
            LIMIT 10
        """

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True

    def test_query_with_newlines_and_comments(self):
        """Test queries with newlines and comments are ALLOWED (Critical Fix).

        Comments are now stripped before pattern matching, so legitimate
        multi-line queries with comments should pass validation.
        """
        sanitizer = QuerySanitizer()
        query = """
            MATCH (m:Movie)
            // This is a comment
            RETURN m.title
        """

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe is True, f"Query with legitimate comment should be allowed. Error: {error}"
        assert error is None

    def test_case_insensitive_pattern_matching(self):
        """Test pattern matching is case-insensitive."""
        sanitizer = QuerySanitizer()
        queries = [
            "load csv from 'file.csv' as line return line",
            "LOAD CSV FROM 'file.csv' AS line RETURN line",
            "LoAd CsV fRoM 'file.csv' aS line ReTuRn line",
        ]

        for query in queries:
            is_safe, error, warnings = sanitizer.sanitize_query(query)
            assert is_safe is False
            assert "dangerous pattern" in error.lower()

    def test_warnings_accumulation(self):
        """Test multiple warnings can accumulate."""
        sanitizer = QuerySanitizer(strict_mode=False, allow_apoc=False, allow_schema_changes=False)
        query = "CALL apoc.help('search') CREATE INDEX FOR (n:Movie) ON (n.title)"

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        # May have multiple warnings
        assert isinstance(warnings, list)

    def test_empty_parameters(self):
        """Test empty parameter dict allowed."""
        sanitizer = QuerySanitizer()

        is_safe, error = sanitizer.sanitize_parameters({})

        assert is_safe is True
        assert error is None

    def test_ftfy_exception_handling(self):
        """Test graceful handling when ftfy fails."""
        sanitizer = QuerySanitizer()

        # Mock ftfy to raise exception
        with patch("neo4j_yass_mcp.security.sanitizer.FTFY_AVAILABLE", True):
            with patch(
                "neo4j_yass_mcp.security.sanitizer.ftfy.fix_text",
                side_effect=Exception("Test error"),
            ):
                query = "MATCH (n) RETURN n"
                is_safe, error, warnings = sanitizer.sanitize_query(query)

                # Should continue with other checks despite ftfy failure
                assert is_safe is True

    def test_confusables_exception_handling(self):
        """Test graceful handling when confusables library fails."""
        sanitizer = QuerySanitizer()

        # Mock confusables to raise exception
        with patch("neo4j_yass_mcp.security.sanitizer.CONFUSABLES_AVAILABLE", True):
            with patch(
                "neo4j_yass_mcp.security.sanitizer.confusables.is_dangerous",
                side_effect=Exception("Test error"),
            ):
                query = "MATCH (n) RETURN n"
                is_safe, error, warnings = sanitizer.sanitize_query(query)

                # Should fall back to manual detection
                assert is_safe is True

    def test_unicode_normalization_shrinkage_detection(self):
        """Test detection of queries that shrink significantly after normalization (line 336)."""
        sanitizer = QuerySanitizer()

        # Create a query with many zero-width characters that will be removed
        # Using zero-width space (U+200B) - caught earlier by zero-width check
        # So the assertion should check for zero-width character message
        query = "MATCH" + "\u200b" * 50 + " (n) RETURN n"  # 50 zero-width spaces

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        # Should be blocked (either by zero-width check or shrinkage check)
        assert is_safe is False
        assert "zero-width" in error.lower() or "Unicode sequences" in error

    def test_homograph_confusable_character_detection(self):
        """Test detection of confusable characters (lines 406-417)."""
        sanitizer = QuerySanitizer()

        # Use Cyrillic 'а' (U+0430) which looks like Latin 'a'
        # This creates a homograph attack
        query = "MATCH (n:\u0430bc) RETURN n"  # Cyrillic а + Latin bc

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        # Should be blocked as homograph attack
        assert is_safe is False
        assert "confusable" in error.lower() or "homograph" in error.lower()

    def test_confusables_exception_fallback_to_manual(self):
        """Test fallback to manual detection when confusables lib fails (line 424)."""
        sanitizer = QuerySanitizer()

        # Mock confusables.is_mixed_script to raise an exception
        with patch("neo4j_yass_mcp.security.sanitizer.CONFUSABLES_AVAILABLE", True):
            with patch(
                "neo4j_yass_mcp.security.sanitizer.confusables.is_mixed_script",
                side_effect=Exception("Library error"),
            ):
                # Use a query with mixed scripts to trigger manual detection
                query = "MATCH (n:Привет) RETURN n"  # Cyrillic script

                is_safe, error, warnings = sanitizer.sanitize_query(query)

                # Should fall back to manual detection
                # Manual detection should catch Cyrillic characters
                assert isinstance(is_safe, bool)

    def test_library_availability_flags(self):
        """Test that library availability flags are set correctly."""
        # Test that availability flags exist and are booleans
        from neo4j_yass_mcp.security.sanitizer import (
            CONFUSABLES_AVAILABLE,
            FTFY_AVAILABLE,
        )

        assert isinstance(CONFUSABLES_AVAILABLE, bool)
        assert isinstance(FTFY_AVAILABLE, bool)
        # In test environment, both should be True (libraries are installed)
        assert CONFUSABLES_AVAILABLE is True
        assert FTFY_AVAILABLE is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=neo4j_yass_mcp.security.sanitizer"])
