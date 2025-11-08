# Quick Reference: Uncovered Lines Summary

## All 22 Uncovered Code Blocks (70 Lines Total)

### Grouped by Line Number

| Line(s) | Function | Category | Type | Trigger | Effort | Priority |
|---------|----------|----------|------|---------|--------|----------|
| 69 | Module init | Environment | Warning | `SANITIZER_ENABLED=false` | Low | 4 |
| 81 | Module init | Environment | Warning | `COMPLEXITY_LIMIT_ENABLED=false` | Low | 4 |
| 93 | Module init | Environment | Warning | `RATE_LIMIT_ENABLED=false` | Low | 4 |
| 121-123 | `get_executor()` | Utility | Function | First call or reset | Low | 3 |
| 176-178 | `estimate_tokens()` | Utility | Function | Non-string input | Low | 3 |
| 225 | `sanitize_error_message()` | Error handling | Function | Safe error pattern | Low | 3 |
| 249-250 | `truncate_response()` | Error handling | Function | Non-serializable data | Low | 3 |
| 415-416 | `get_schema()` | Error handling | Resource | Neo4j error | Medium | 2 |
| 478-491 | `query_graph()` | Tool execution | Tool | Rate limit exceeded | Medium | 1 |
| 552-553 | `query_graph()` | Tool execution | Tool | Sanitizer warnings | Medium | 1 |
| 562-587 | `query_graph()` | Tool execution | Tool | Complex query blocked | High | 1 |
| 653 | `query_graph()` | Error handling | Tool | Exception in chain | Medium | 2 |
| 704-717 | `_execute_cypher_impl()` | Tool execution | Tool | Rate limit exceeded | Medium | 1 |
| 760-785 | `_execute_cypher_impl()` | Tool execution | Tool | Complex query blocked | High | 1 |
| 868 | `_execute_cypher_impl()` | Error handling | Tool | Exception in query | Medium | 2 |
| 973 | `cleanup()` | Error handling | Utility | Missing driver attr | Low | 2 |
| 984-1048 | `main()` | Tool execution | Function | Transport config | High | 1 |

---

## Test Implementation Summary

### By Priority Level

#### Priority 1 (7-12 tests, 4-6 hours) - CRITICAL SECURITY
- **Rate limiting** (3 tests)
  - `query_graph` rate limited
  - `execute_cypher` rate limited
  - Edge case: None rate_info

- **Complexity limiting** (3 tests)
  - `query_graph` blocks complex queries
  - `execute_cypher` blocks complex queries
  - Sanitizer warnings logged

- **Main/Transport** (5 tests)
  - stdio transport
  - HTTP transport
  - SSE transport
  - Port not available
  - Port fallback

#### Priority 2 (3-4 tests, 1-2 hours) - DATA INTEGRITY
- **Resource errors** (4 tests)
  - `get_schema()` success
  - Connection error
  - Permission error
  - No graph initialized

- **Audit logging** (2 tests)
  - `query_graph` error audit
  - `execute_cypher` error audit

- **Cleanup** (3 tests)
  - Missing driver attribute
  - Executor shutdown
  - Neo4j driver close

#### Priority 3 (10-16 tests, 2-3 hours) - EDGE CASES
- **Utilities** (8 tests)
  - Executor lazy init (2)
  - Token estimation types (6)

- **Error sanitization** (6 tests)
  - Safe patterns (5)
  - Debug mode
  - Unsafe pattern
  - Fallback

#### Priority 4 (3 tests, <1 hour) - INITIALIZATION
- **Config warnings** (3 tests)
  - Sanitizer disabled
  - Complexity limiter disabled
  - Rate limiter disabled

---

## Code Locations Reference

### Module Initialization (Lines 1-96)
```python
# Line 69  - Sanitizer disabled warning
# Line 81  - Complexity limiter disabled warning
# Line 93  - Rate limiter disabled warning
```

### Utility Functions (Lines 118-285)
```python
# Line 121-123 - get_executor() initialization
# Line 176-178 - estimate_tokens() non-string handling
# Line 225    - sanitize_error_message() safe pattern matching
# Line 249-250 - truncate_response() JSON serialization fallback
```

### Resource Handlers (Lines 401-435)
```python
# Line 415-416 - get_schema() exception handler
```

### Tool: query_graph() (Lines 442-661)
```python
# Line 478-491 - Rate limit exceeded response
# Line 552-553 - Sanitizer warning logging
# Line 562-587 - Complexity limiter blocking
# Line 653     - Error audit logging
```

### Tool: execute_cypher() (Lines 663-876)
```python
# Line 704-717 - Rate limit exceeded response
# Line 760-785 - Complexity limiter blocking
# Line 868     - Error audit logging
```

### Cleanup (Lines 932-980)
```python
# Line 973 - AttributeError handling in cleanup()
```

### Main Entry Point (Lines 982-1048)
```python
# Line 984-1048 - Transport configuration (stdio, HTTP, SSE)
```

---

## Test Patterns & Utilities

### Common Mock Objects

```python
# Rate limit info
mock_rate_info = MagicMock()
mock_rate_info.retry_after_seconds = 45.5
mock_rate_info.reset_time = datetime.now()

# Complexity score
mock_complexity_score = MagicMock()
mock_complexity_score.total_score = 250
mock_complexity_score.max_allowed = 100
mock_complexity_score.warnings = ["warning text"]

# Audit logger
mock_audit_logger = MagicMock()
mock_audit_logger.log_error = MagicMock()
mock_audit_logger.log_query = MagicMock()

# Graph
mock_graph = MagicMock()
mock_graph.get_schema = "SCHEMA"
mock_graph.query = MagicMock(return_value=[{"result": 1}])

# Chain
mock_chain = MagicMock()
mock_chain.invoke = MagicMock(return_value={
    "result": "answer",
    "intermediate_steps": [{"query": "MATCH..."}]
})
```

### Common Patches

```python
# Environment & configuration
@patch("neo4j_yass_mcp.server.rate_limit_enabled", True)
@patch("neo4j_yass_mcp.server.sanitizer_enabled", True)
@patch("neo4j_yass_mcp.server.complexity_limit_enabled", True)

# Global objects
@patch("neo4j_yass_mcp.server.graph", mock_graph)
@patch("neo4j_yass_mcp.server.chain", mock_chain)
@patch("neo4j_yass_mcp.server._debug_mode", False)

# Functions
@patch("neo4j_yass_mcp.server.get_audit_logger", return_value=mock_audit_logger)
@patch("neo4j_yass_mcp.server.check_rate_limit", return_value=(False, mock_rate_info))
@patch("neo4j_yass_mcp.server.check_query_complexity", return_value=(False, "error", mock_complexity_score))
@patch("neo4j_yass_mcp.server.sanitize_query", return_value=(True, None, []))
```

---

## Execution Flow Diagrams

### query_graph() Uncovered Paths

```
query_graph(query)
├─ Rate limit check
│  ├─ [COVERED] is_allowed=True
│  └─ [UNCOVERED 478-491] is_allowed=False → return rate_limit_error
├─ LLM invoke via chain.invoke()
│  └─ intermediate_steps → Cypher generation
├─ Sanitizer check (if enabled)
│  ├─ [COVERED] is_safe=True
│  ├─ [COVERED] is_safe=False → return sanitizer_error
│  └─ [UNCOVERED 552-553] warnings logged
├─ Complexity check (if enabled)
│  ├─ [COVERED] is_allowed=True
│  ├─ [UNCOVERED 562-587] is_allowed=False → return complexity_error
│  └─ [COVERED] warnings logged
├─ [COVERED] Success path → return results
└─ Exception handler
   └─ [UNCOVERED 653] audit_logger.log_error()
```

### execute_cypher() Uncovered Paths

```
_execute_cypher_impl(query, params)
├─ Rate limit check
│  ├─ [COVERED] is_allowed=True
│  └─ [UNCOVERED 704-717] is_allowed=False → return rate_limit_error
├─ Sanitizer check (if enabled)
│  ├─ [COVERED] is_safe=True
│  ├─ [COVERED] is_safe=False → return sanitizer_error
│  └─ [COVERED] warnings logged
├─ Complexity check (if enabled)
│  ├─ [COVERED] is_allowed=True
│  ├─ [UNCOVERED 760-785] is_allowed=False → return complexity_error
│  └─ [COVERED] warnings logged
├─ Graph query execution
│  └─ [COVERED] Success path → return results
└─ Exception handler
   └─ [UNCOVERED 868] audit_logger.log_error()
```

---

## Environment Variables Required for Coverage

### For Configuration Warnings (Priority 4)
```bash
SANITIZER_ENABLED=false          # Triggers line 69
COMPLEXITY_LIMIT_ENABLED=false   # Triggers line 81
RATE_LIMIT_ENABLED=false         # Triggers line 93
```

### For Rate Limiting (Priority 1)
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60
```

### For Complexity Limiting (Priority 1)
```bash
COMPLEXITY_LIMIT_ENABLED=true
MAX_QUERY_COMPLEXITY=100
MAX_VARIABLE_PATH_LENGTH=10
```

### For Transport Configuration (Priority 1)
```bash
# stdio (default)
MCP_TRANSPORT=stdio

# HTTP
MCP_TRANSPORT=http
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8000
MCP_SERVER_PATH=/mcp/

# SSE
MCP_TRANSPORT=sse
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=9000
```

---

## Estimated Timeline

| Phase | Tasks | Time | Tests |
|-------|-------|------|-------|
| Setup | Create test fixtures, mocks, utilities | 0.5h | - |
| Priority 4 | Config warnings | 0.5h | 3 |
| Priority 3 | Utilities + Error sanitization | 2h | 14 |
| Priority 2 | Resource + Audit + Cleanup | 1.5h | 9 |
| Priority 1 | Rate limiting + Complexity + Main | 5h | 11 |
| Refinement | Fix test failures, coverage cleanup | 1.5h | - |
| **TOTAL** | | **10.5h** | **37** |

---

## Success Criteria

✓ All 22 uncovered blocks have corresponding test functions
✓ All 37 test functions pass
✓ Overall code coverage increases from ~40% to 95%+
✓ Security-critical paths (rate limiting, complexity) have integration tests
✓ All error handling paths logged/audited
✓ Documentation in COVERAGE_ANALYSIS.md and TEST_IMPLEMENTATION_GUIDE.md

---

## Quick Implementation Checklist

- [ ] Review COVERAGE_ANALYSIS.md for detailed explanation of each gap
- [ ] Review TEST_IMPLEMENTATION_GUIDE.md for copy-paste test templates
- [ ] Start with Priority 4 tests (fastest wins)
- [ ] Use provided mock patterns for consistency
- [ ] Run tests with: `pytest tests/test_server_*.py -v --cov`
- [ ] Achieve 95%+ coverage before merging
