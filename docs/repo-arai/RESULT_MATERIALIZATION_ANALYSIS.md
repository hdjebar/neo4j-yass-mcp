# Result Materialization Limits - Analysis and Recommendations

**Date**: 2025-11-15
**Finding**: #3 from CRITICAL_FINDINGS_2025-11-15.md
**Severity**: MEDIUM-HIGH (Performance/DoS Vector)
**Status**: ⏳ Analysis Complete - Implementation Deferred

## Problem Statement

The advertised response/token limits do not prevent materialization of huge result sets. Results are fully loaded into memory, serialized to JSON, token-counted, and only then truncated.

### Current Flow (Problematic)

```python
# handlers/tools.py:277
result = await current_graph.query(cypher_query, params=params)  # ← Full materialization!

# Line 282
truncated_result, was_truncated = truncate_response(result)  # ← Truncate after
```

### Attack Scenario

```cypher
MATCH (n) RETURN n
-- Database has 10 million nodes
-- All 10M nodes loaded into memory (~1GB+)
-- Serialized to huge JSON string
-- Token counted (expensive)
-- THEN truncated to small response
```

### Impact

**Memory Exhaustion**:
- Query returning 10M nodes → ~1GB+ RAM
- Multiple concurrent queries → OOM crash
- Process killed by OS

**CPU Exhaustion**:
- JSON serialization of huge objects
- Token counting on multi-GB strings
- Wasted computation

**Database Load**:
- Full result set transferred from Neo4j
- Network bandwidth wasted
- Database resources consumed unnecessarily

---

## Affected Code Locations

### 1. execute_cypher Tool
**File**: [src/neo4j_yass_mcp/handlers/tools.py](../../src/neo4j_yass_mcp/handlers/tools.py#L277-L282)

```python
result = await current_graph.query(cypher_query, params=params)  # Full materialization
truncated_result, was_truncated = truncate_response(result)  # Then truncate
```

### 2. query_graph Tool
**File**: [src/neo4j_yass_mcp/handlers/tools.py](../../src/neo4j_yass_mcp/handlers/tools.py#L91-L108)

```python
result = await asyncio.to_thread(current_chain.invoke, {"query": query})
truncated_steps, steps_truncated = truncate_response(result.get("intermediate_steps", []))
truncated_answer, answer_truncated = truncate_response(result.get("result", ""))
```

**Note**: Query analyzer is NOT affected - it uses `query_with_summary(..., fetch_records=False)` which doesn't materialize records.

---

## Solution Options

### Option A: Query-Level LIMIT Injection (Recommended)

**Approach**: Detect queries without LIMIT clause and inject `LIMIT <configurable_max>`

**Pros**:
- ✅ Prevents materialization at source
- ✅ Minimal memory impact
- ✅ Works with Neo4j's query optimizer
- ✅ Clear user feedback (warning about limit)

**Cons**:
- ⚠️ Requires Cypher parsing (regex or AST)
- ⚠️ May modify user intent (needs clear warnings)
- ⚠️ Complex edge cases (UNION, subqueries, etc.)

**Implementation**:
```python
def inject_limit_if_needed(query: str, max_rows: int = 1000) -> tuple[str, bool]:
    """
    Inject LIMIT clause if query doesn't have one.

    Returns: (modified_query, was_injected)
    """
    # Simple regex approach (may not catch all cases)
    if not re.search(r'\bLIMIT\s+\d+', query, re.IGNORECASE):
        # Check if query ends with semicolon
        query = query.rstrip().rstrip(';')
        return f"{query} LIMIT {max_rows}", True
    return query, False

# Usage
modified_query, injected = inject_limit_if_needed(cypher_query, max_rows=1000)
result = await current_graph.query(modified_query, params=params)

if injected:
    response["warning"] = f"Query modified: LIMIT {max_rows} injected to prevent resource exhaustion"
```

**Configuration**:
```python
# config/runtime_config.py
max_query_rows: int = 1000  # Maximum rows to return from queries
```

---

### Option B: Streaming Truncation

**Approach**: Stream results from database and truncate during iteration

**Pros**:
- ✅ Doesn't modify queries
- ✅ Precise control over result size
- ✅ Preserves user intent

**Cons**:
- ⚠️ Requires Neo4j driver API changes
- ⚠️ More complex implementation
- ⚠️ May not work with LangChain integration

**Implementation Challenge**:
```python
# Current: result.data() fetches all records
result = await session.run(query, params)
records = result.data()  # ← Materializes everything

# Streaming approach would need:
async for record in result:  # ← Not supported by current driver usage
    if row_count >= max_rows:
        break
    records.append(record)
```

**Blocker**: The current Neo4j async driver usage pattern (`result.data()`) materializes all records. Would need significant refactoring.

---

### Option C: Neo4j Driver Features (fetch limit)

**Approach**: Use `result.fetch(n)` to limit retrieval at driver level

**Pros**:
- ✅ Native driver support
- ✅ Efficient (doesn't transfer excess data)
- ✅ No query modification

**Cons**:
- ⚠️ Requires investigating async driver API
- ⚠️ May need changes to AsyncSecureNeo4jGraph
- ⚠️ Compatibility with LangChain

**Investigation Needed**:
```python
# Check if neo4j-driver supports:
result = await session.run(query, params)
records = await result.fetch(max_rows)  # Fetch limited records
```

---

## Recommended Implementation: Hybrid Approach

Combine Option A (LIMIT injection) with smarter detection:

### Phase 1: Simple LIMIT Injection (Quick Win)

1. **Regex-based LIMIT detection**:
   ```python
   def has_limit_clause(query: str) -> bool:
       """Check if query has LIMIT clause (simple regex)."""
       return bool(re.search(r'\bLIMIT\s+\d+', query, re.IGNORECASE))
   ```

2. **Safe LIMIT injection**:
   ```python
   def inject_safe_limit(query: str, max_rows: int = 1000) -> tuple[str, bool]:
       """
       Inject LIMIT clause if missing.

       Returns: (modified_query, was_injected)
       """
       if has_limit_clause(query):
           return query, False

       # Remove trailing semicolon if present
       query = query.rstrip().rstrip(';')

       # Inject LIMIT
       modified = f"{query} LIMIT {max_rows}"

       logger.info(f"Injected LIMIT {max_rows} to prevent resource exhaustion")
       return modified, True
   ```

3. **Update execute_cypher**:
   ```python
   # Before query execution
   modified_query, limit_injected = inject_safe_limit(cypher_query, max_rows=1000)
   result = await current_graph.query(modified_query, params=params)

   if limit_injected:
       response["warning"] = (
           f"Query modified: LIMIT 1000 injected to prevent resource exhaustion. "
           f"Add explicit LIMIT clause to control result size."
       )
   ```

4. **Configuration**:
   ```python
   # Add to RuntimeConfig
   max_query_result_rows: int = 1000  # Configurable via MAX_QUERY_RESULT_ROWS
   ```

### Phase 2: Enhanced Detection (Future)

1. **Handle edge cases**:
   - UNION queries (each part needs LIMIT)
   - Subqueries (only outer query needs LIMIT)
   - Queries with existing LIMIT (respect user's limit if < max)

2. **Cypher AST parsing** (if simple regex insufficient):
   - Use proper Cypher parser for accurate detection
   - Handle complex query structures

3. **Per-tool limits**:
   - `execute_cypher`: Strict limit (1000 rows)
   - `query_graph`: More lenient (LangChain handles)
   - `analyze_query_performance`: N/A (uses fetch_records=False)

---

## Edge Cases to Handle

### 1. Queries with Existing LIMIT
```cypher
MATCH (n:Person) RETURN n LIMIT 10
-- Don't inject another LIMIT
```

### 2. UNION Queries
```cypher
MATCH (n:Person) RETURN n.name
UNION
MATCH (m:Movie) RETURN m.title
-- Both parts may need LIMIT
```

### 3. Subqueries
```cypher
MATCH (n:Person)
WHERE n.age IN [
  MATCH (m:Person) RETURN m.age LIMIT 5
]
RETURN n LIMIT 100
-- Only outer LIMIT matters for result size
```

### 4. Aggregations (Don't Need LIMIT)
```cypher
MATCH (n:Person) RETURN count(n)
-- Returns single row, no LIMIT needed
```

---

## Testing Strategy

### Unit Tests

```python
def test_limit_injection_simple():
    """Test basic LIMIT injection."""
    query = "MATCH (n) RETURN n"
    modified, injected = inject_safe_limit(query, max_rows=100)

    assert injected is True
    assert "LIMIT 100" in modified
    assert modified == "MATCH (n) RETURN n LIMIT 100"

def test_limit_injection_already_has_limit():
    """Test no injection when LIMIT exists."""
    query = "MATCH (n) RETURN n LIMIT 50"
    modified, injected = inject_safe_limit(query, max_rows=100)

    assert injected is False
    assert modified == query

def test_limit_injection_with_semicolon():
    """Test LIMIT injection with trailing semicolon."""
    query = "MATCH (n) RETURN n;"
    modified, injected = inject_safe_limit(query, max_rows=100)

    assert injected is True
    assert modified == "MATCH (n) RETURN n LIMIT 100"

def test_limit_injection_case_insensitive():
    """Test case-insensitive LIMIT detection."""
    queries = [
        "MATCH (n) RETURN n limit 50",
        "MATCH (n) RETURN n Limit 50",
        "MATCH (n) RETURN n LiMiT 50",
    ]

    for query in queries:
        modified, injected = inject_safe_limit(query, max_rows=100)
        assert injected is False
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_execute_cypher_with_limit_injection():
    """Test that execute_cypher injects LIMIT for unbounded queries."""
    # Mock graph that would return huge result set
    mock_graph = Mock()
    mock_graph.query = AsyncMock(return_value=[{"n": {"id": i}} for i in range(100)])

    # Execute query without LIMIT
    response = await execute_cypher_impl(
        graph=mock_graph,
        cypher_query="MATCH (n) RETURN n",
        parameters=None
    )

    # Verify LIMIT was injected
    assert "warning" in response
    assert "LIMIT" in response["warning"]

    # Verify query was modified
    call_args = mock_graph.query.call_args
    assert "LIMIT" in call_args[0][0]
```

---

## Performance Impact

### Before Fix (Current State)
- Query returning 1M rows: **~100MB-1GB RAM**, **10-60 seconds**
- Memory spike visible in monitoring
- Possible OOM crash

### After Fix (with LIMIT injection)
- Query auto-limited to 1000 rows: **~100KB-1MB RAM**, **< 1 second**
- Consistent memory usage
- No OOM risk

---

## Configuration

### Environment Variables

```bash
# Maximum rows to return from queries (default: 1000)
MAX_QUERY_RESULT_ROWS=1000

# Enable/disable automatic LIMIT injection (default: true)
AUTO_INJECT_LIMIT=true
```

### Runtime Config

```python
class QueryLimitsConfig:
    """Query result size limits configuration."""

    max_result_rows: int = 1000  # Maximum rows to return
    auto_inject_limit: bool = True  # Auto-inject LIMIT clause
    warn_on_injection: bool = True  # Warn user about injection
```

---

## Security Considerations

### DoS Prevention
- ✅ Prevents memory exhaustion attacks
- ✅ Limits CPU consumption
- ✅ Protects database from excessive data transfer

### User Experience
- ⚠️ May surprise users expecting full result set
- ✅ Clear warnings about limit injection
- ✅ Guidance to add explicit LIMIT clause

### Bypass Protection
- ✅ Cannot be bypassed (enforced at tool level)
- ✅ Configuration-based (admin-controlled)
- ✅ Logged for audit trail

---

## Implementation Priority

### Priority: MEDIUM
- Not as critical as security vulnerabilities (Findings #1, #2)
- Important for production stability
- Can be deployed incrementally

### Complexity: MEDIUM
- Simple regex approach: **2-4 hours**
- Full Cypher parsing: **1-2 days**
- Testing: **2-4 hours**

### Risk: LOW
- Changes are opt-in via configuration
- Clear warnings to users
- Can be disabled if issues arise

---

## Recommendation

**Implement Phase 1 (Simple LIMIT Injection)** with the following approach:

1. **Quick Win**: Regex-based LIMIT detection + injection
2. **Configuration**: Make max_rows configurable (default: 1000)
3. **Warnings**: Clear user feedback about limit injection
4. **Testing**: Comprehensive unit + integration tests
5. **Monitoring**: Log all limit injections for analysis

**Defer Phase 2** until we see real-world usage patterns and edge cases.

---

## Related Documentation

- [CRITICAL_FINDINGS_2025-11-15.md](CRITICAL_FINDINGS_2025-11-15.md) - Original finding
- [Neo4j Driver Documentation](https://neo4j.com/docs/python-manual/current/) - Driver API reference

---

## Conclusion

Result materialization limits are a real performance/DoS concern but lower priority than the security and functionality issues already fixed. The recommended approach is a simple LIMIT injection with clear user warnings, which provides:

- ✅ Significant protection against resource exhaustion
- ✅ Low implementation complexity
- ✅ Clear user feedback
- ✅ Configurable behavior
- ✅ Can be enhanced later if needed

**Status**: Analysis complete, implementation deferred to future sprint
**Estimated Implementation Time**: 4-8 hours (Phase 1 only)
**Risk Level**: LOW (with proper testing)

---

**Analysis Date**: 2025-11-15
**Analyst**: AI Code Review (Claude)
**Status**: Ready for implementation when prioritized
