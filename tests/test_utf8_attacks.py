#!/usr/bin/env python3
"""
Test UTF-8/Unicode Attack Prevention

Tests the sanitizer's ability to detect and block various UTF-8 encoding attacks.
"""

import pytest

from neo4j_yass_mcp.security.sanitizer import QuerySanitizer


@pytest.fixture
def sanitizer():
    """Create a QuerySanitizer with default settings (allow non-ASCII)"""
    return QuerySanitizer(block_non_ascii=False)


@pytest.fixture
def strict_sanitizer():
    """Create a QuerySanitizer with strict non-ASCII blocking enabled"""
    return QuerySanitizer(block_non_ascii=True)


class TestUTF8Attacks:
    """Test UTF-8 and Unicode-based injection attacks"""

    def test_zero_width_space(self, sanitizer):
        """Test detection of zero-width space (U+200B)"""
        query = "MATCH (n:Person\u200B) RETURN n"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Zero-width space should be blocked"
        assert error is not None
        assert "zero-width" in error.lower() or "unicode" in error.lower()

    def test_zero_width_no_break_space(self, sanitizer):
        """Test detection of zero-width no-break space / BOM (U+FEFF)"""
        query = "MATCH (n:Person\uFEFF) RETURN n"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Zero-width no-break space (BOM) should be blocked"
        assert error is not None

    def test_right_to_left_override(self, sanitizer):
        """Test detection of right-to-left override (U+202E)"""
        query = "MATCH (n:Person\u202E) RETURN n"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Right-to-left override should be blocked"
        assert error is not None

    def test_homograph_attack_cyrillic_o(self, sanitizer):
        """Test detection of Cyrillic 'о' (U+043E) instead of ASCII 'o'"""
        query = "MATCH (n:Persоn) RETURN n"  # Cyrillic 'о'
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Cyrillic 'о' homograph should be blocked"
        assert error is not None

    def test_homograph_attack_cyrillic_e(self, sanitizer):
        """Test detection of Cyrillic 'е' (U+0435) instead of ASCII 'e'"""
        query = "MATCH (n:Pеrson) RETURN n"  # Cyrillic 'е'
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Cyrillic 'е' homograph should be blocked"
        assert error is not None

    def test_safe_ascii_query(self, sanitizer):
        """Test that safe ASCII queries are allowed"""
        query = "MATCH (n:Person) RETURN n"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert is_safe, "Safe ASCII query should be allowed"
        assert error is None


class TestStrictNonASCIIMode:
    """Test strict non-ASCII blocking mode"""

    def test_ascii_query_allowed(self, strict_sanitizer):
        """Test that ASCII queries pass in strict mode"""
        query = "MATCH (n:Person) RETURN n"
        is_safe, error, warnings = strict_sanitizer.sanitize_query(query)

        assert is_safe, "ASCII query should be allowed in strict mode"
        assert error is None

    def test_utf8_umlaut_blocked(self, strict_sanitizer):
        """Test that UTF-8 umlaut is blocked in strict mode"""
        query = "MATCH (n:Persön) RETURN n"
        is_safe, error, warnings = strict_sanitizer.sanitize_query(query)

        assert not is_safe, "UTF-8 'ö' should be blocked in strict mode"
        assert error is not None
        assert "non-ascii" in error.lower() or "unicode" in error.lower()

    def test_utf8_accent_blocked(self, strict_sanitizer):
        """Test that UTF-8 accent is blocked in strict mode"""
        query = "MATCH (n:José) RETURN n"
        is_safe, error, warnings = strict_sanitizer.sanitize_query(query)

        assert not is_safe, "UTF-8 'é' should be blocked in strict mode"
        assert error is not None

    def test_emoji_blocked(self, strict_sanitizer):
        """Test that emoji is blocked in strict mode"""
        query = "MATCH (n:Person {name: '😀'}) RETURN n"
        is_safe, error, warnings = strict_sanitizer.sanitize_query(query)

        assert not is_safe, "Emoji should be blocked in strict mode"
        assert error is not None


class TestUnicodeNormalization:
    """Test various Unicode normalization attacks"""

    def test_combining_diacritic_attack(self, sanitizer):
        """Test detection of combining diacritical marks"""
        # Combining diacritic that could hide injection
        query = "MATCH (n:Persoǹ) RETURN n"  # Has combining grave accent
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Combining diacritics should be blocked"
        assert error is not None

    def test_look_alike_characters(self, sanitizer):
        """Test detection of look-alike characters"""
        # Mathematical bold capital M (U+1D40C) looks like M
        query = "MATCH (n:𝐌ATCH) RETURN n"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Look-alike characters should be blocked"
        assert error is not None


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_query_blocked(self, sanitizer):
        """Test that empty queries are blocked"""
        query = ""
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Empty query should be blocked"
        assert error is not None

    def test_whitespace_only_blocked(self, sanitizer):
        """Test that whitespace-only queries are blocked"""
        query = "   \t\n  "
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Whitespace-only query should be blocked"
        assert error is not None

    def test_null_bytes_blocked(self, sanitizer):
        """Test that null bytes are blocked"""
        query = "MATCH (n:Person\x00) RETURN n"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe, "Null bytes should be blocked"
        assert error is not None


# Parameterized test for multiple attack vectors
@pytest.mark.parametrize("attack_char,description", [
    ("\u200B", "Zero-width space"),
    ("\u200C", "Zero-width non-joiner"),
    ("\u200D", "Zero-width joiner"),
    ("\uFEFF", "Zero-width no-break space (BOM)"),
    ("\u202A", "Left-to-right embedding"),
    ("\u202B", "Right-to-left embedding"),
    ("\u202C", "Pop directional formatting"),
    ("\u202D", "Left-to-right override"),
    ("\u202E", "Right-to-left override"),
])
def test_zero_width_and_directional_characters(attack_char, description):
    """Parametrized test for various zero-width and directional characters"""
    sanitizer = QuerySanitizer(block_non_ascii=False)
    query = f"MATCH (n:Person{attack_char}) RETURN n"
    is_safe, error, warnings = sanitizer.sanitize_query(query)

    assert not is_safe, f"{description} ({repr(attack_char)}) should be blocked"
    assert error is not None


@pytest.mark.parametrize("homograph_query,description", [
    ("MATCH (n:Persоn) RETURN n", "Cyrillic 'о' (U+043E)"),
    ("MATCH (n:Pеrson) RETURN n", "Cyrillic 'е' (U+0435)"),
    ("MATCH (n:Pеrsоn) RETURN n", "Multiple Cyrillic chars"),
    ("MATCH (n:Реrson) RETURN n", "Cyrillic 'Р' (U+0420)"),
])
def test_homograph_attacks(homograph_query, description):
    """Parametrized test for various homograph attacks"""
    sanitizer = QuerySanitizer(block_non_ascii=False)
    is_safe, error, warnings = sanitizer.sanitize_query(homograph_query)

    assert not is_safe, f"Homograph attack with {description} should be blocked"
    assert error is not None


if __name__ == "__main__":
    # Allow running with pytest or directly
    pytest.main([__file__, "-v"])
