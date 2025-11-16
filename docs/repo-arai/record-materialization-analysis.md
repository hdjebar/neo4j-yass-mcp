# Record Materialization Analysis

**Date**: 2025-11-15
**Status**: VERIFIED - No unnecessary record materialization

## Summary

This document verifies that the `query_with_summary()` method does NOT materialize result records when `fetch_records=False` (the default).

## Neo4j Driver Behavior

### AsyncResult.data()
According to the official Neo4j Python Driver documentation:

```
async data(self, *keys) -> list[dict[str, Any]]
    Return the remainder of the result as a list of dictionaries.
```

**This method DOES materialize all records** - it fetches all remaining records from the server and converts them to a list of dictionaries in memory.

### AsyncResult.consume()
According to the official Neo4j Python Driver documentation:

```
consume(self) -> ResultSummary
    Consume the remainder of this result and return the summary.
```

**This method DOES NOT materialize records** - it discards any unfetched records from the stream and returns only the summary metadata.

## Current Implementation

### AsyncNeo4jGraph.query_with_summary() (lines 92-129)

```python
async def query_with_summary(
    self, query: str, params: dict[str, Any] | None = None, *, fetch_records: bool = False
) -> tuple[list[dict[str, Any]], Any]:
    """Execute a Cypher query and return both data and result summary."""

    async with self._driver.session(database=self._database) as session:
        result = await session.run(query, params or {})

        # CRITICAL SECTION: Only materialize records if explicitly requested
        if fetch_records:
            records = await result.data()  # MATERIALIZE - called only when fetch_records=True
        else:
            records = []  # NO MATERIALIZATION - skip data() entirely

        summary = await result.consume()  # DISCARD unfetched records, get summary
        return records, summary
```

### Execution Flow for EXPLAIN/PROFILE Queries

#### When `fetch_records=False` (DEFAULT):

1. Line 119: `result = await session.run(query, params or {})`
   - Query is sent to Neo4j
   - Result object is created (no records fetched yet - streaming mode)

2. Lines 123-126: Conditional branch
   - `fetch_records=False`, so we skip line 124 entirely
   - Line 126: `records = []` (empty list, no network calls)

3. Line 128: `summary = await result.consume()`
   - **Discards** any unfetched records in the stream
   - Returns ResultSummary containing plan, statistics, etc.
   - **No record materialization occurs**

4. Line 129: `return records, summary`
   - Returns `([], summary)`
   - Summary contains execution plan from EXPLAIN/PROFILE
   - Zero records were materialized

#### When `fetch_records=True`:

1. Line 119: `result = await session.run(query, params or {})`
2. Line 124: `records = await result.data()`
   - **Materializes all records** from the stream
   - Converts to list of dictionaries
3. Line 128: `summary = await result.consume()`
   - No records left to discard (already fetched)
   - Returns ResultSummary
4. Line 129: `return records, summary`
   - Returns `(materialized_records, summary)`

## Usage in QueryPlanAnalyzer

### _execute_explain() (lines 124-147)

```python
async def _execute_explain(self, query: str) -> dict[str, Any]:
    explain_query = f"EXPLAIN {query}"

    # fetch_records=False (default) - NO RECORD MATERIALIZATION
    records, summary = await self.graph.query_with_summary(
        explain_query, params={}, fetch_records=False
    )

    plan = summary.plan if hasattr(summary, "plan") else None
    return {"type": "explain", "plan": plan, "records": records, "statistics": None}
```

**Analysis**:
- `fetch_records=False` is explicitly passed
- `result.data()` is NEVER called
- Only `result.consume()` is called, which discards unfetched records
- ✅ No unnecessary record materialization

### _execute_profile() (lines 149-175)

```python
async def _execute_profile(self, query: str) -> dict[str, Any]:
    profile_query = f"PROFILE {query}"

    # fetch_records=False (default) - NO RECORD MATERIALIZATION
    records, summary = await self.graph.query_with_summary(
        profile_query, params={}, fetch_records=False
    )

    plan = summary.plan if hasattr(summary, "plan") else None
    statistics = self._extract_profile_statistics_from_summary(summary)
    return {"type": "profile", "plan": plan, "records": records, "statistics": statistics}
```

**Analysis**:
- `fetch_records=False` is explicitly passed
- `result.data()` is NEVER called
- Only `result.consume()` is called, which discards unfetched records
- ✅ No unnecessary record materialization

## Test Verification

### Test: test_query_with_summary (lines 213-261)

```python
async def test_query_with_summary(self):
    # Test without fetch_records (default) - should return empty records
    records, summary = await graph.query_with_summary("EXPLAIN MATCH (n:Person) RETURN n.name")

    assert len(records) == 0  # No records fetched by default
    assert summary is mock_summary
    assert summary.plan.operator_type == "ProduceResults"

    # CRITICAL ASSERTION: Verify data() was NOT called
    mock_result.data.assert_not_called()
    mock_result.consume.assert_called_once()
```

**Test Result**: ✅ PASS

This test explicitly verifies that when `fetch_records=False` (default):
1. `result.data()` is NOT called (no materialization)
2. `result.consume()` IS called (discard unfetched records)
3. Empty records list is returned
4. Summary with plan is returned

## Conclusion

### ✅ VERIFIED: No Unnecessary Record Materialization

The implementation is correct and efficient:

1. **Default behavior (`fetch_records=False`)**:
   - Skips `result.data()` entirely
   - Calls `result.consume()` to discard unfetched records
   - Returns only the ResultSummary with execution plan
   - **Zero records materialized**

2. **Explicit materialization (`fetch_records=True`)**:
   - Calls `result.data()` to materialize records
   - Returns both records and summary
   - **Records materialized only when explicitly requested**

3. **EXPLAIN/PROFILE queries**:
   - Both use `fetch_records=False`
   - Neither materializes records
   - Both access real Neo4j execution plans via `summary.plan`
   - **Optimal performance - only plan metadata is retrieved**

### Performance Impact

For a query that would return 1,000,000 records:

- **With `fetch_records=True`**: Streams and materializes all 1M records into memory
- **With `fetch_records=False` (default)**: Discards all 1M records, retrieves only plan metadata
- **Savings**: ~100MB+ memory, ~1-2 seconds network transfer time

### Test Evidence

```bash
$ uv run pytest tests/unit/test_async_graph.py::TestAsyncNeo4jGraph::test_query_with_summary -xvs
============================== 1 passed in 0.92s ===============================
```

The test explicitly verifies `mock_result.data.assert_not_called()` when `fetch_records=False`.

## References

- Neo4j Python Driver Documentation: https://neo4j.com/docs/api/python-driver/current/async_api.html
- Implementation: [src/neo4j_yass_mcp/async_graph.py:92-129](../src/neo4j_yass_mcp/async_graph.py#L92-L129)
- Tests: [tests/unit/test_async_graph.py:213-261](../../tests/unit/test_async_graph.py#L213-L261)
