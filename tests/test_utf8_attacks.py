#!/usr/bin/env python3
"""
Test UTF-8/Unicode Attack Prevention

Demonstrates the sanitizer blocking various UTF-8 encoding attacks.
"""

from utilities.sanitizer import QuerySanitizer

def test_utf8_attacks():
    """Test UTF-8 attack detection"""

    # Initialize sanitizer
    sanitizer = QuerySanitizer(block_non_ascii=False)

    print("=" * 70)
    print("UTF-8/Unicode Attack Prevention Tests")
    print("=" * 70)
    print()

    # Test cases
    test_cases = [
        # Zero-width character attacks
        (
            "MATCH (n:Person\u200B) RETURN n",  # U+200B zero-width space
            "Zero-width space (U+200B)"
        ),
        (
            "MATCH (n:Person\uFEFF) RETURN n",  # U+FEFF BOM
            "Zero-width no-break space (U+FEFF)"
        ),

        # Directional override attacks
        (
            "MATCH (n:Person\u202E) RETURN n",  # U+202E RTL override
            "Right-to-left override (U+202E)"
        ),

        # Homograph attacks
        (
            "MATCH (n:Persоn) RETURN n",  # Cyrillic 'о' instead of 'o'
            "Homograph attack - Cyrillic 'о' (U+043E)"
        ),
        (
            "MATCH (n:Pеrson) RETURN n",  # Cyrillic 'е' instead of 'e'
            "Homograph attack - Cyrillic 'е' (U+0435)"
        ),

        # Safe query
        (
            "MATCH (n:Person) RETURN n",
            "Safe query (should PASS)"
        ),
    ]

    for query, description in test_cases:
        print(f"Test: {description}")
        print(f"Query: {repr(query)}")

        is_safe, error, warnings = sanitizer.sanitize_query(query)

        if is_safe:
            print("✅ Result: PASSED (query allowed)")
        else:
            print(f"🛡️  Result: BLOCKED - {error}")

        print("-" * 70)
        print()

    # Test strict non-ASCII mode
    print("=" * 70)
    print("Strict Non-ASCII Mode Test")
    print("=" * 70)
    print()

    strict_sanitizer = QuerySanitizer(block_non_ascii=True)

    test_cases_strict = [
        ("MATCH (n:Person) RETURN n", "ASCII query (should PASS)"),
        ("MATCH (n:Persön) RETURN n", "UTF-8 'ö' (should BLOCK)"),
        ("MATCH (n:José) RETURN n", "UTF-8 'é' (should BLOCK)"),
    ]

    for query, description in test_cases_strict:
        print(f"Test: {description}")
        print(f"Query: {repr(query)}")

        is_safe, error, warnings = strict_sanitizer.sanitize_query(query)

        if is_safe:
            print("✅ Result: PASSED (query allowed)")
        else:
            print(f"🛡️  Result: BLOCKED - {error}")

        print("-" * 70)
        print()


if __name__ == "__main__":
    test_utf8_attacks()
