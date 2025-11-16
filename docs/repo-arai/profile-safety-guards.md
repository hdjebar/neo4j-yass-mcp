# PROFILE Mode Safety Guards

**Date**: 2025-11-15
**Feature**: Write-Query Detection for PROFILE Mode
**Status**: ✅ Implemented

## Overview

PROFILE mode in Neo4j executes queries to gather runtime statistics. To prevent accidental execution of write operations during performance analysis, we've implemented safety guards that block write queries by default.

## Implementation

### Write Query Detection

Added `_is_write_query()` method to QueryPlanAnalyzer ([query_analyzer.py:158-182](../../src/neo4j_yass_mcp/tools/query_analyzer.py#L158-L182)):

```python
def _is_write_query(self, query: str) -> bool:
    """
    Detect if a query contains write operations.

    Returns:
        True if query contains write operations, False otherwise
    """
    query_upper = query.upper()

    write_keywords = [
        "CREATE ",
        "MERGE ",
        "DELETE ",
        "DETACH DELETE ",
        "SET ",
        "REMOVE ",
        "DROP ",
    ]

    return any(keyword in query_upper for keyword in write_keywords)
```

### PROFILE Safety Guard

Updated `_execute_profile()` with mandatory safety check ([query_analyzer.py:184-243](../../src/neo4j_yass_mcp/tools/query_analyzer.py#L184-L243)):

```python
async def _execute_profile(
    self, query: str, allow_write_queries: bool = False
) -> dict[str, Any]:
    """
    Execute PROFILE to get execution plan with runtime statistics.

    IMPORTANT: PROFILE executes the query to gather runtime statistics.
    By default, write queries (CREATE/MERGE/DELETE/SET) are blocked unless
    explicitly allowed via allow_write_queries=True.
    """
    # Safety check: Block write queries unless explicitly allowed
    if not allow_write_queries and self._is_write_query(query):
        raise ValueError(
            "PROFILE mode blocked: Query contains write operations "
            "(CREATE/MERGE/DELETE/SET/REMOVE/DROP). "
            "Use EXPLAIN mode for safe analysis, or explicitly allow write queries if intentional."
        )
```

### API Updates

Updated `analyze_query()` method signature ([query_analyzer.py:48-80](../../src/neo4j_yass_mcp/tools/query_analyzer.py#L48-L80)):

```python
async def analyze_query(
    self,
    query: str,
    mode: str = "explain",
    include_recommendations: bool = True,
    include_cost_estimate: bool = True,
    allow_write_queries: bool = False,  # NEW parameter
) -> dict[str, Any]:
```

## Behavior

### Default Behavior (Safe by Default)

PROFILE mode blocks all write queries by default:

```python
# ❌ Blocked by default
analyzer.analyze_query("CREATE (n:Person {name: 'Alice'})", mode="profile")
# Raises: ValueError - PROFILE mode blocked: Query contains write operations

analyzer.analyze_query("MATCH (n) DELETE n", mode="profile")
# Raises: ValueError - PROFILE mode blocked: Query contains write operations

analyzer.analyze_query("MATCH (n) SET n.updated = true", mode="profile")
# Raises: ValueError - PROFILE mode blocked: Query contains write operations
```

### Read Queries (Always Allowed)

Read-only queries work normally in PROFILE mode:

```python
# ✅ Allowed
analyzer.analyze_query("MATCH (n:Person) RETURN n", mode="profile")
# Returns: Analysis with runtime statistics

analyzer.analyze_query("MATCH (a)-[:KNOWS]->(b) RETURN a, b", mode="profile")
# Returns: Analysis with runtime statistics
```

### Explicit Override

When write query profiling is intentional, use `allow_write_queries=True`:

```python
# ✅ Explicitly allowed
analyzer.analyze_query(
    "CREATE (n:Person {name: 'Alice'})",
    mode="profile",
    allow_write_queries=True
)
# Returns: Analysis with runtime statistics (query IS executed)
```

## Detected Write Operations

The safety guard detects the following write operations:

- `CREATE` - Creating new nodes or relationships
- `MERGE` - Matching or creating nodes/relationships
- `DELETE` - Deleting nodes or relationships
- `DETACH DELETE` - Deleting nodes with their relationships
- `SET` - Setting or updating properties
- `REMOVE` - Removing properties or labels
- `DROP` - Dropping indexes or constraints

Detection is case-insensitive: `CREATE`, `create`, and `CrEaTe` are all detected.

## EXPLAIN Mode (Always Safe)

EXPLAIN mode never executes queries and is always safe for all query types:

```python
# ✅ Always safe - no execution
analyzer.analyze_query("CREATE (n:Person)", mode="explain")
analyzer.analyze_query("MATCH (n) DELETE n", mode="explain")
analyzer.analyze_query("MATCH (n) SET n.value = 1", mode="explain")
```

## Test Coverage

### Write Query Blocking

**Test**: `test_profile_blocks_write_queries_by_default`
**Location**: [tests/unit/test_query_analyzer.py:577-598](../../tests/unit/test_query_analyzer.py#L577-L598)

Verifies that all write operations are blocked by default:
- CREATE statements
- MERGE statements
- DELETE statements
- DETACH DELETE statements
- SET statements
- REMOVE statements
- DROP statements

### Read Query Allowance

**Test**: `test_profile_allows_read_queries`
**Location**: [tests/unit/test_query_analyzer.py:600-628](../../tests/unit/test_query_analyzer.py#L600-L628)

Verifies that read-only queries work normally in PROFILE mode:
- Simple MATCH queries
- Filtered MATCH queries
- Relationship traversal queries

### Explicit Override

**Test**: `test_profile_allows_write_queries_when_explicitly_enabled`
**Location**: [tests/unit/test_query_analyzer.py:630-653](../../tests/unit/test_query_analyzer.py#L630-L653)

Verifies that write queries can be profiled when `allow_write_queries=True`.

### Write Detection Logic

**Test**: `test_is_write_query_detection`
**Location**: [tests/unit/test_query_analyzer.py:655-675](../../tests/unit/test_query_analyzer.py#L655-L675)

Verifies correct detection of write vs. read queries, including case-insensitivity.

## Error Messages

Clear, actionable error messages guide users to safe alternatives:

```
ValueError: PROFILE mode blocked: Query contains write operations
(CREATE/MERGE/DELETE/SET/REMOVE/DROP). Use EXPLAIN mode for safe analysis,
or explicitly allow write queries if intentional.
```

## Logging

Warning logged when PROFILE is blocked:

```
WARNING - PROFILE blocked: Query contains write operations.
Use EXPLAIN for safe analysis or set allow_write_queries=True to override.
```

## Security Benefits

### 1. Safe by Default
- Write queries blocked in PROFILE mode unless explicitly allowed
- Prevents accidental data modifications during performance analysis
- Aligns with "EXPLAIN is safe, PROFILE is powerful" principle

### 2. Explicit Intent Required
- `allow_write_queries=True` makes write-query profiling intentional
- Clear API contract prevents surprises
- Easy to audit: grep for `allow_write_queries=True`

### 3. Layered Security
- Complements existing sanitizer and complexity checks
- Adds query-type awareness to analysis layer
- Defense in depth: multiple safeguards prevent issues

## Usage Recommendations

### For Development
```python
# Use EXPLAIN for validation (fast, safe, no execution)
analyzer.analyze_query(query, mode="explain")
```

### For Performance Tuning (Read Queries)
```python
# Use PROFILE for runtime stats on read queries
analyzer.analyze_query(read_query, mode="profile")
```

### For Performance Tuning (Write Queries)
```python
# Explicitly allow PROFILE for write queries when needed
analyzer.analyze_query(
    write_query,
    mode="profile",
    allow_write_queries=True  # Explicit opt-in
)
```

## Related Documentation

- [FINAL_SUMMARY.md](FINAL_SUMMARY.md) - Query plan analysis refactoring overview
- [codex5.1-resolution-record.md](codex5.1-resolution-record.md) - Security findings resolution
- [record-materialization-analysis.md](record-materialization-analysis.md) - Technical verification

## Future Enhancements

Potential improvements for consideration:

1. **Granular Permissions**: Allow specific write operations (e.g., allow SET but block DELETE)
2. **Transaction Rollback**: Execute PROFILE in transaction that's always rolled back
3. **Dry-Run Mode**: Combine PROFILE with read-only transaction mode
4. **Query Fingerprinting**: Detect write queries via AST parsing instead of string matching

---

**Status**: Production-ready safety feature implemented and tested
**Test Coverage**: 4 new tests, all passing
**Backward Compatibility**: Fully backward compatible (new optional parameter)
