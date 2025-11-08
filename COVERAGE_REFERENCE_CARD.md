# Coverage Reference Card - At a Glance

## The 4 Categories

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. ENVIRONMENT VARIABLE BRANCHES (3 lines)                          │
│    Disabled features warnings during module initialization          │
│    Priority: 4 (Low) - Fastest to test                            │
│                                                                      │
│    Lines: 69, 81, 93                                               │
│    Tests: 3 simple warning verification tests                      │
│    Time: ~0.5 hours                                                │
│    Effort: LOW                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 2. ERROR HANDLING PATHS (15 lines)                                  │
│    Exception handlers and error logging throughout app             │
│    Priority: 2-3 (Medium) - Defensive programming                 │
│                                                                      │
│    Lines: 176-178, 225, 249-250, 415-416, 653, 868, 973          │
│    Tests: 14 tests covering edge cases and exceptions              │
│    Time: ~2-3 hours                                                │
│    Effort: MEDIUM                                                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 3. TOOL EXECUTION PATHS (35 lines)                                  │
│    MCP tool handlers with security checks and audit logging        │
│    Priority: 1 (Critical) - Security-sensitive code                │
│                                                                      │
│    Lines: 478-491, 552-553, 562-587, 704-717, 760-785, 984-1048   │
│    Tests: 11 complex integration tests                              │
│    Time: ~5-6 hours                                                │
│    Effort: HIGH                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 4. UTILITY FUNCTIONS (2 lines)                                      │
│    Helper methods for lazy initialization and thread pools         │
│    Priority: 3 (Medium) - Functional but non-critical              │
│                                                                      │
│    Lines: 121-123                                                  │
│    Tests: 2 tests for lazy initialization                          │
│    Time: ~0.5 hours                                                │
│    Effort: LOW                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Test Mapping

### Environment Variables (3 tests)
```python
Line 69  → test_sanitizer_disabled_warning()
Line 81  → test_complexity_limiter_disabled_warning()
Line 93  → test_rate_limiter_disabled_warning()
```

### Utility Functions (10 tests)
```python
Line 121-123 → test_get_executor_lazy_initialization()
           → test_get_executor_configuration()

Line 176-178 → test_estimate_tokens_with_integer()
           → test_estimate_tokens_with_dict()
           → test_estimate_tokens_with_list()
           → test_estimate_tokens_with_float()
           → test_estimate_tokens_with_none()
           → test_estimate_tokens_with_empty_string()
           → test_estimate_tokens_consistency()
```

### Error Handling (9 tests)
```python
Line 225     → test_safe_pattern_authentication_failed()
           → test_safe_pattern_connection_refused()
           → test_safe_pattern_timeout()
           → test_safe_pattern_not_found()
           → test_safe_pattern_unauthorized()
           → test_unsafe_pattern_generic_error()
           → test_debug_mode_returns_full_error()

Line 249-250 → test_truncate_response_non_serializable()
           → test_truncate_response_no_limit()
           → test_truncate_response_list_exceeds_limit()
           → test_truncate_response_string_exceeds_limit()
           → test_truncate_response_preserves_small_data()

Line 415-416 → test_get_schema_success()
           → test_get_schema_neo4j_error()
           → test_get_schema_permission_error()
           → test_get_schema_no_graph()

Line 653     → test_query_graph_error_audit_logged()

Line 868     → test_execute_cypher_error_audit_logged()

Line 973     → test_cleanup_missing_driver_attribute()
           → test_cleanup_closes_executor()
           → test_cleanup_closes_neo4j_driver()
```

### Tool Execution - query_graph() (5 tests)
```python
Line 478-491 → test_query_graph_rate_limited()
           → test_query_graph_rate_limit_with_none_info()

Line 552-553 → test_query_graph_sanitizer_warnings_logged()

Line 562-587 → test_query_graph_complex_query_blocked()
```

### Tool Execution - execute_cypher() (2 tests)
```python
Line 704-717 → test_execute_cypher_rate_limited()

Line 760-785 → test_execute_cypher_complex_query_blocked()
```

### Tool Execution - main() (5 tests)
```python
Line 984-1048 → test_main_with_stdio_transport()
            → test_main_with_http_transport()
            → test_main_with_sse_transport()
            → test_main_http_port_not_available()
            → test_main_http_port_fallback()
```

---

## The 22 Uncovered Blocks at a Glance

```
Security-Critical (Test First!)
┌─────────────────────────────────────┐
│ Block 1: Line 478-491               │
│ query_graph() rate limit check      │
│ ⚠️  Prevents DoS attacks           │
│ Test: test_query_graph_rate_limited()│
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Block 2: Line 562-587               │
│ query_graph() complexity block      │
│ ⚠️  Prevents resource exhaustion    │
│ Test: test_query_graph_complex_..()│
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Block 3: Line 704-717               │
│ execute_cypher() rate limit check   │
│ ⚠️  Prevents DoS attacks           │
│ Test: test_execute_cypher_rate...()│
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Block 4: Line 760-785               │
│ execute_cypher() complexity block   │
│ ⚠️  Prevents resource exhaustion    │
│ Test: test_execute_cypher_complex()│
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Block 5: Line 984-1048              │
│ main() transport configuration      │
│ ⚠️  Server startup & routing        │
│ Test: test_main_with_*_transport() │
└─────────────────────────────────────┘
```

---

## What Each Block Does

### Block 1: Environment Variable Branch (Line 69)
```python
else:
    logger.warning("⚠️  Query sanitizer disabled...")
```
**When**: `SANITIZER_ENABLED=false`
**Why**: Logs that SQL injection protection is OFF
**Test**: Mock env var, verify warning logged

---

### Block 2: Environment Variable Branch (Line 81)
```python
else:
    logger.warning("⚠️  Query complexity limiter disabled...")
```
**When**: `COMPLEXITY_LIMIT_ENABLED=false`
**Why**: Logs that DoS protection via query limits is OFF
**Test**: Mock env var, verify warning logged

---

### Block 3: Environment Variable Branch (Line 93)
```python
else:
    logger.warning("⚠️  Rate limiter disabled...")
```
**When**: `RATE_LIMIT_ENABLED=false`
**Why**: Logs that request flooding protection is OFF
**Test**: Mock env var, verify warning logged

---

### Block 4: Executor Lazy Initialization (Lines 121-123)
```python
if _executor is None:
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="langchain_")
return _executor
```
**When**: First call to `get_executor()`
**Why**: Create thread pool on demand
**Test**: Call twice, verify same instance returned

---

### Block 5: Non-String Token Estimation (Lines 176-178)
```python
if not isinstance(text, str):
    text = str(text)
```
**When**: `estimate_tokens()` called with int/dict/list
**Why**: Defensive programming - handle edge cases
**Test**: Call with dict, list, int - verify token count

---

### Block 6: Safe Error Pattern Matching (Line 225)
```python
if pattern in error_lower:
    return error_str
```
**When**: Error contains known-safe keyword (e.g., "timeout")
**Why**: Don't over-sanitize safe errors in production
**Test**: Create timeout error, verify message returned

---

### Block 7: JSON Serialization Fallback (Lines 249-250)
```python
except (TypeError, ValueError):
    json_str = str(data)
```
**When**: Data is not JSON serializable
**Why**: Gracefully handle unusual object types
**Test**: Pass custom object to `truncate_response()`

---

### Block 8: Schema Retrieval Exception (Lines 415-416)
```python
except Exception as e:
    return f"Error retrieving schema: {str(e)}"
```
**When**: Neo4j connection fails during schema fetch
**Why**: Return user-friendly error message
**Test**: Mock `graph.get_schema` to raise exception

---

### Block 9: Rate Limit Exceeded (Lines 478-491)
```python
if not is_allowed and rate_info is not None:
    return {"error": "Rate limit exceeded...", ...}
```
**When**: Request exceeds rate limit (>10/min)
**Why**: Prevent DoS attacks
**Test**: Mock `check_rate_limit()` to return limited=True

---

### Block 10: Sanitizer Warnings Logged (Lines 552-553)
```python
if warnings:
    for warning in warnings:
        logger.warning(f"LLM-generated Cypher warning: {warning}")
```
**When**: LLM generates Cypher with warnings but still safe
**Why**: Observability - track query quality
**Test**: Mock `sanitize_query()` to return warnings

---

### Block 11: Complexity Blocked (Lines 562-587)
```python
if not is_allowed:
    return {"error": "Query blocked by complexity...", ...}
```
**When**: LLM-generated query exceeds complexity threshold
**Why**: Prevent DoS via expensive queries
**Test**: Mock `check_query_complexity()` to return blocked=True

---

### Block 12: Error Audit Logged (Line 653)
```python
if audit_logger:
    audit_logger.log_error(tool="query_graph", ...)
```
**When**: Exception caught in `query_graph()`
**Why**: Compliance - audit all errors
**Test**: Mock `chain.invoke()` to raise exception

---

### Block 13: Rate Limit Exceeded in execute_cypher (Lines 704-717)
```python
if not is_allowed and rate_info is not None:
    return {"error": "Rate limit exceeded...", ...}
```
**When**: Raw Cypher request exceeds rate limit
**Why**: Prevent DoS via direct query API
**Test**: Similar to Block 9, but for `execute_cypher()`

---

### Block 14: Complexity Blocked in execute_cypher (Lines 760-785)
```python
if not is_allowed:
    return {"error": "Query blocked by complexity...", ...}
```
**When**: Raw Cypher query exceeds complexity
**Why**: Prevent DoS via expensive direct queries
**Test**: Similar to Block 11, but for `execute_cypher()`

---

### Block 15: Error Audit in execute_cypher (Line 868)
```python
if audit_logger:
    audit_logger.log_error(tool="execute_cypher", ...)
```
**When**: Exception caught in `execute_cypher()`
**Why**: Compliance audit
**Test**: Similar to Block 12, but for `execute_cypher()`

---

### Block 16: Cleanup AttributeError (Line 973)
```python
except AttributeError as e:
    logger.warning(f"Could not access Neo4j driver: {e}")
```
**When**: Neo4j object missing `_driver` attribute
**Why**: Handle unexpected Neo4j versions gracefully
**Test**: Mock graph without `_driver` attribute

---

### Block 17-22: Transport Configuration (Lines 984-1048)
```python
if transport in ("sse", "http"):
    # Network setup
else:
    # stdio setup (default)
```
**When**: `main()` startup with different transports
**Why**: Support multiple server communication modes
**Test**: 5 tests covering stdio, HTTP, SSE, and port fallback

---

## Testing Order by Difficulty

### Easiest (Start Here)
1. Environment warnings (3 tests) - Just verify log message
2. Utility functions (10 tests) - Simple assertions
3. Error sanitization (9 tests) - Create exceptions, verify responses

### Medium
4. Resource errors (4 tests) - Mock graph object
5. Cleanup errors (3 tests) - Mock Neo4j driver
6. Audit logging (2 tests) - Mock audit logger

### Hardest (End Here)
7. Rate limiting (3 tests) - Complex mock setup
8. Complexity limiting (3 tests) - More complex mocks
9. Transport/main (5 tests) - Full integration mocking

---

## File Locations in server.py

```
Module Initialization
├── Lines 1-96 (module-level setup)
│   ├── Line 69   [ENV BLOCK] Sanitizer warning
│   ├── Line 81   [ENV BLOCK] Complexity warning
│   └── Line 93   [ENV BLOCK] Rate limiter warning
│
Utility Functions
├── Lines 118-285 (helper functions)
│   ├── Lines 121-123 [UTIL] get_executor()
│   ├── Lines 176-178 [ERROR] estimate_tokens()
│   ├── Line 225      [ERROR] sanitize_error_message()
│   └── Lines 249-250 [ERROR] truncate_response()
│
Resource Handlers
├── Lines 401-435 (MCP resources)
│   └── Lines 415-416 [ERROR] get_schema()
│
Tool: query_graph()
├── Lines 442-661
│   ├── Lines 478-491 [TOOL] Rate limit check
│   ├── Lines 552-553 [TOOL] Sanitizer warnings
│   ├── Lines 562-587 [TOOL] Complexity blocking
│   └── Line 653      [ERROR] Error audit
│
Tool: execute_cypher()
├── Lines 663-876
│   ├── Lines 704-717 [TOOL] Rate limit check
│   ├── Lines 760-785 [TOOL] Complexity blocking
│   └── Line 868      [ERROR] Error audit
│
Cleanup Function
├── Lines 932-980
│   └── Line 973      [ERROR] AttributeError handling
│
Main Entry Point
├── Lines 982-1048
│   └── Lines 984-1048 [TOOL] Transport config
```

---

## Copy-Paste Commands

```bash
# Run all tests
pytest tests/test_server_*.py -v

# Run by priority
pytest tests/test_server_utilities.py tests/test_server_error_sanitization.py -v     # Priority 3
pytest tests/test_server_resources.py tests/test_server_audit_logging.py -v          # Priority 2
pytest tests/test_server_rate_limiting.py tests/test_server_complexity_limiting.py -v # Priority 1

# Generate coverage report
pytest tests/test_server_*.py --cov=neo4j_yass_mcp.server --cov-report=html

# Run single test file
pytest tests/test_server_utilities.py -v
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Total lines | 70 | 0 (covered) |
| Uncovered blocks | 22 | 0 |
| Code coverage | ~40% | 95%+ |
| Security paths | Partial | Complete |
| Error handling | Partial | Complete |
| Audit logging | Partial | Complete |
| Test count | 0 | 37 |

---

## Key Takeaways

✓ **Priority 1 (5 blocks)**: Security-critical - rate limiting & complexity limits
✓ **Priority 2 (5 blocks)**: Data integrity - error handling & audit logging
✓ **Priority 3 (10 blocks)**: Edge cases - utility functions & error sanitization
✓ **Priority 4 (3 blocks)**: Initialization - configuration warnings

**Total Effort**: ~10 hours development, 37 tests

**Documents**:
- `COVERAGE_ANALYSIS.md` - Detailed analysis of each block
- `TEST_IMPLEMENTATION_GUIDE.md` - Copy-paste test templates
- `UNCOVERED_LINES_SUMMARY.md` - Quick reference tables
- `COVERAGE_REFERENCE_CARD.md` - This document
