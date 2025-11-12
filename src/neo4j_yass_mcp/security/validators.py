"""
Security validators for Cypher queries.

This module provides validation functions for Cypher queries to enforce
security policies such as read-only mode restrictions.

Extracted from server.py to break circular dependency between server and secure_graph modules.
"""

import re


def check_read_only_access(cypher_query: str, read_only_mode: bool = False) -> str | None:
    """
    Check if a Cypher query is allowed in read-only mode.

    This function uses regex-based pattern matching to detect write operations,
    mutating procedures, and dangerous operations. It normalizes whitespace to
    prevent bypass via tabs, newlines, or missing spaces.

    Args:
        cypher_query: The Cypher query to check
        read_only_mode: Whether read-only mode is enabled (default: False)

    Returns:
        Error message if query is not allowed, None if allowed

    Examples:
        >>> check_read_only_access("MATCH (n) RETURN n", read_only_mode=True)
        None
        >>> check_read_only_access("CREATE (n:Person)", read_only_mode=True)
        'Read-only mode: CREATE operations are not allowed'
        >>> check_read_only_access("CREATE (n:Person)", read_only_mode=False)
        None
    """
    if not read_only_mode:
        return None

    # Normalize whitespace (collapse tabs, newlines, multiple spaces into single space)
    normalized = re.sub(r"\s+", " ", cypher_query.strip()).upper()

    # Check for dangerous operations FIRST (before write keywords)
    # FOREACH and procedures often contain write keywords, so check them first
    if re.search(r"\bFOREACH\b", normalized):
        return "Read-only mode: FOREACH not allowed"

    if re.search(r"\bLOAD\s+CSV\b", normalized):
        return "Read-only mode: LOAD CSV not allowed"

    # Check for mutating procedures (before write keywords)
    # These procedures can modify the database even without explicit write keywords
    mutating_procedures = [
        r"\bCALL\s+DB\.SCHEMA\.",
        r"\bCALL\s+APOC\.WRITE\.",
        r"\bCALL\s+APOC\.CREATE\.",
        r"\bCALL\s+APOC\.MERGE\.",
        r"\bCALL\s+APOC\.REFACTOR\.",
    ]
    for pattern in mutating_procedures:
        if re.search(pattern, normalized):
            return "Read-only mode: Mutating procedure not allowed"

    # Check for write keywords using word boundaries
    # \b ensures we match whole words, not parts of identifiers
    write_keywords = ["CREATE", "MERGE", "DELETE", "REMOVE", "SET", "DETACH", "DROP"]
    for keyword in write_keywords:
        if re.search(rf"\b{keyword}\b", normalized):
            return f"Read-only mode: {keyword} operations are not allowed"

    return None
