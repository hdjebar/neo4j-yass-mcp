"""
Query utility functions for Neo4j Cypher query manipulation.

This module provides utilities for safe query modification, including
automatic LIMIT injection to prevent resource exhaustion.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Extended list of Cypher clause keywords that can appear after LIMIT
# This prevents bypass attacks like "MATCH (n) RETURN n LIMIT UNION MATCH (m)"
# where the attacker uses a clause keyword immediately after LIMIT to fool detection
CLAUSE_KEYWORDS = (
    r'RETURN|WITH|MATCH|ORDER|WHERE|'
    r'UNION|SKIP|UNWIND|'
    r'CREATE|MERGE|DELETE|DETACH|SET|REMOVE|'
    r'CALL|FOREACH|LOAD|USE|OPTIONAL|YIELD'
)


def _strip_string_literals_and_comments(query: str) -> str:
    """
    Remove string literals and comments from a Cypher query to prevent false positives.

    This helps avoid detecting keywords that appear inside string literals or comments.
    For example:
    - "WHERE n.note CONTAINS 'LIMIT 999'" should not be detected as having a LIMIT clause
    - "MATCH (n) RETURN n // LIMIT 1" should not be detected as having a LIMIT clause
    - "CALL db.labels() /* RETURN name */" should not be detected as having a RETURN clause

    Args:
        query: The Cypher query to process

    Returns:
        Query with string literals and comments replaced by placeholders

    Note:
        Handles:
        - Single-quoted strings ('...')
        - Double-quoted strings ("...")
        - Backtick-quoted identifiers (`...`)
        - Escaped quotes within strings
        - Single-line comments (// ...)
        - Multi-line comments (/* ... */)

        Uses UUID-based placeholder to prevent collision with actual identifiers.
    """
    import uuid

    # Generate collision-resistant placeholder using UUID prefix
    # This prevents false positives when users have identifiers named '__ID__'
    placeholder = f'__CYV_{uuid.uuid4().hex[:8]}__'

    # Remove single-quoted strings (handle escaped quotes)
    query = re.sub(r"'(?:[^'\\]|\\.)*'", "''", query)

    # Remove double-quoted strings (handle escaped quotes)
    query = re.sub(r'"(?:[^"\\]|\\.)*"', '""', query)

    # Replace backtick-quoted identifiers with collision-resistant placeholder
    # Preserves query structure while neutralizing identifier content
    query = re.sub(r'`(?:[^`\\]|\\.)*`', placeholder, query)

    # Remove single-line comments (// to end of line)
    query = re.sub(r'//.*?$', '', query, flags=re.MULTILINE)

    # Remove multi-line comments (/* ... */)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

    return query


def has_limit_clause(query: str) -> bool:
    """
    Check if a Cypher query has a LIMIT clause.

    Uses regex to detect LIMIT keyword followed by any expression.
    Case-insensitive matching. Strips string literals and comments to avoid false positives.

    Args:
        query: The Cypher query to check

    Returns:
        True if query contains LIMIT clause, False otherwise

    Examples:
        >>> has_limit_clause("MATCH (n) RETURN n LIMIT 100")
        True
        >>> has_limit_clause("MATCH (n) RETURN n")
        False
        >>> has_limit_clause("MATCH (n) RETURN n limit 50")
        True
        >>> has_limit_clause("MATCH (n) RETURN n LIMIT $pageSize")
        True
        >>> has_limit_clause("MATCH (n) RETURN n LIMIT $params.limit")
        True
        >>> has_limit_clause("MATCH (n) RETURN n LIMIT $cfg['rows']")
        True
        >>> has_limit_clause("MATCH (n) RETURN n LIMIT {pageSize}")
        True
        >>> has_limit_clause("MATCH (n) RETURN n LIMIT\\n$pageSize")
        True
        >>> has_limit_clause("WHERE n.note CONTAINS 'LIMIT 999' RETURN n")
        False
        >>> has_limit_clause("MATCH (n) RETURN n // LIMIT 1")
        False
        >>> has_limit_clause("MATCH (n) RETURN n /* LIMIT 100 */")
        False
    """
    # Strip string literals and comments to avoid false positives
    stripped_query = _strip_string_literals_and_comments(query)

    # Use regex lookahead to detect LIMIT followed by an expression
    # Stops at: semicolon, end of string, or any clause keyword
    # This prevents bypass attacks like "LIMIT UNION" from being detected as valid
    match = re.search(
        rf'\bLIMIT\s+(.+?)(?=\s*(?:;|$|\b(?:{CLAUSE_KEYWORDS})\b))',
        stripped_query,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return False

    # Verify the captured expression is not just whitespace
    limit_expr = match.group(1).strip()
    if not limit_expr:
        return False

    # Verify it's not a clause keyword itself (bypass attempt)
    if re.match(rf'\b(?:{CLAUSE_KEYWORDS})\b', limit_expr, re.IGNORECASE):
        return False

    return True


def inject_limit_clause(
    query: str,
    max_rows: int = 1000,
    force: bool = False
) -> tuple[str, bool]:
    """
    Inject LIMIT clause into a Cypher query if it doesn't have one.

    This function helps prevent resource exhaustion by ensuring queries
    have a maximum result set size. It safely appends a LIMIT clause
    to queries that don't already have one.

    Args:
        query: The Cypher query to modify
        max_rows: Maximum number of rows to return (default: 1000)
        force: If True, inject LIMIT even if one exists (default: False)

    Returns:
        Tuple of (modified_query, was_injected)
        - modified_query: The query with LIMIT clause
        - was_injected: True if LIMIT was added, False if already present

    Examples:
        >>> inject_limit_clause("MATCH (n) RETURN n", max_rows=100)
        ('MATCH (n) RETURN n LIMIT 100', True)

        >>> inject_limit_clause("MATCH (n) RETURN n LIMIT 50", max_rows=100)
        ('MATCH (n) RETURN n LIMIT 50', False)

        >>> inject_limit_clause("MATCH (n) RETURN n;", max_rows=100)
        ('MATCH (n) RETURN n LIMIT 100', True)

    Note:
        - Removes trailing semicolons before injecting LIMIT
        - Does not modify queries with existing LIMIT (unless force=True)
        - Simple regex-based approach (may not handle all edge cases)
    """
    # Check if query already has LIMIT
    if not force and has_limit_clause(query):
        logger.debug("Query already has LIMIT clause, skipping injection")
        return query, False

    # Remove trailing whitespace and semicolon
    query = query.rstrip().rstrip(';')

    # Inject LIMIT
    modified_query = f"{query} LIMIT {max_rows}"

    logger.info(
        f"Injected LIMIT {max_rows} to prevent resource exhaustion"
    )

    return modified_query, True


def should_inject_limit(query: str) -> bool:
    """
    Determine if a query should have a LIMIT clause injected.

    LIMIT can only be added to queries with RETURN or WITH clauses.
    The RETURN/WITH must be the FINAL clause (queries ending with DELETE, CREATE, etc.
    cannot have LIMIT).

    Args:
        query: The Cypher query to analyze

    Returns:
        True if LIMIT should be injected, False otherwise

    Examples:
        >>> should_inject_limit("MATCH (n) RETURN n")
        True

        >>> should_inject_limit("MATCH (n) RETURN count(n)")
        True

        >>> should_inject_limit("MATCH (n) RETURN n LIMIT 100")
        False

        >>> should_inject_limit("CREATE (n:Log {ts: timestamp()})")
        False

        >>> should_inject_limit("CALL db.labels()")
        False

        >>> should_inject_limit("CALL db.labels() // RETURN name")
        False

        >>> should_inject_limit("MATCH (n) RETURN n DELETE n")
        False
    """
    # Don't inject if query already has LIMIT
    if has_limit_clause(query):
        return False

    # Strip string literals and comments for accurate detection
    stripped_query = _strip_string_literals_and_comments(query)
    if not stripped_query or not stripped_query.strip():
        logger.debug("Query stripped to empty, skipping LIMIT injection")
        return False

    # Find the last clause keyword in the query
    # LIMIT can only be added after RETURN or WITH as the final clause
    last_clause_match = None
    for match in re.finditer(
        rf'\b(?:{CLAUSE_KEYWORDS})\b',
        stripped_query,
        re.IGNORECASE
    ):
        last_clause_match = match

    if not last_clause_match:
        logger.debug("No clause keywords found, cannot inject LIMIT")
        return False

    last_clause = last_clause_match.group().upper()

    # Only inject LIMIT if the last clause is RETURN or WITH
    if last_clause not in ('RETURN', 'WITH'):
        logger.debug(
            f"Last clause '{last_clause}' does not support LIMIT injection"
        )
        return False

    return True
