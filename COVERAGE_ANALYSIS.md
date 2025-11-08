# Coverage Analysis for neo4j_yass_mcp/server.py

## Executive Summary
Analyzed 22 uncovered code blocks (70 total lines) across 4 categories. Most gaps are in error handling paths and security feature toggles that require integration testing with Neo4j/LLM backends.

---

## 1. ENVIRONMENT VARIABLE BRANCHES (Disabled Features Warnings)

These are **low-priority** for unit testing as they're initialization-time warnings. Coverage can be achieved through environment variable mocking.

### Line 69 - Query Sanitizer Disabled Warning
```python
else:
    logger.warning("⚠️  Query sanitizer disabled - injection protection is OFF!")
```
- **Type**: Configuration warning for disabled security feature
- **Trigger**: `SANITIZER_ENABLED=false`
- **What to test**: Verify warning is logged when sanitizer is disabled
- **Test approach**:
  ```python
  def test_query_sanitizer_disabled_warning(monkeypatch, caplog):
      monkeypatch.setenv("SANITIZER_ENABLED", "false")
      # Re-import or reload module
      import logging
      assert any("Query sanitizer disabled" in record.message
                 for record in caplog.records if record.levelname == "WARNING")
  ```
- **Effort**: Low (1-2 lines of test code)

### Line 81 - Query Complexity Limiter Disabled Warning
```python
else:
    logger.warning("⚠️  Query complexity limiter disabled - no protection against complex queries!")
```
- **Type**: Configuration warning for disabled security feature
- **Trigger**: `COMPLEXITY_LIMIT_ENABLED=false`
- **What to test**: Verify warning is logged when complexity limiter is disabled
- **Test approach**:
  ```python
  def test_complexity_limiter_disabled_warning(monkeypatch, caplog):
      monkeypatch.setenv("COMPLEXITY_LIMIT_ENABLED", "false")
      # Re-import or reload module
      assert any("Query complexity limiter disabled" in record.message
                 for record in caplog.records if record.levelname == "WARNING")
  ```
- **Effort**: Low (1-2 lines of test code)

### Line 93 - Rate Limiter Disabled Warning
```python
else:
    logger.warning("⚠️  Rate limiter disabled - no protection against request flooding!")
```
- **Type**: Configuration warning for disabled security feature
- **Trigger**: `RATE_LIMIT_ENABLED=false`
- **What to test**: Verify warning is logged when rate limiter is disabled
- **Test approach**:
  ```python
  def test_rate_limiter_disabled_warning(monkeypatch, caplog):
      monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
      # Re-import or reload module
      assert any("Rate limiter disabled" in record.message
                 for record in caplog.records if record.levelname == "WARNING")
  ```
- **Effort**: Low (1-2 lines of test code)

**Summary for Category 1**: These 3 lines can be tested by setting environment variables and verifying log output. They're initialization-time warnings with no runtime impact.

---

## 2. ERROR HANDLING PATHS (Exception Handlers)

These are **critical** for production reliability. They require integration testing with actual Neo4j failures and malformed inputs.

### Line 176 - Non-string Input Handling in estimate_tokens()
```python
if not isinstance(text, str):
    text = str(text)
```
- **Location**: Lines 175-178 in `estimate_tokens()` function
- **What to test**: Token estimation handles non-string types (None, dict, list, int)
- **Current coverage**:
  - Line 175 checks `if text is None` (covered)
  - Line 177-178 converts non-strings (NOT covered)
- **Test approach**:
  ```python
  @pytest.mark.asyncio
  async def test_estimate_tokens_with_non_string_input():
      """Test token estimation with non-string inputs"""
      assert estimate_tokens(12345) > 0  # int
      assert estimate_tokens({"key": "value"}) > 0  # dict
      assert estimate_tokens([1, 2, 3]) > 0  # list
  ```
- **Effort**: Medium (3-5 test cases)
- **Impact**: Defensive coding - handles edge cases in downstream tools

### Line 225 - Safe Error Pattern Matching in sanitize_error_message()
```python
if pattern in error_lower:
    return error_str
```
- **Location**: Lines 223-225 in `sanitize_error_message()` function
- **What to test**: Verify safe error patterns are returned as-is
- **Current coverage**:
  - Function is called in error handlers
  - Debug mode path (line 205) is covered
  - Safe pattern match path (line 225) is NOT covered
- **Test approach**:
  ```python
  def test_sanitize_error_message_safe_patterns():
      """Test that safe patterns are returned as-is"""
      safe_error = Exception("authentication failed: invalid credentials")
      result = sanitize_error_message(safe_error)
      assert "authentication failed" in result

      timeout_error = TimeoutError("connection timeout after 30s")
      result = sanitize_error_message(timeout_error)
      assert "timeout" in result
  ```
- **Effort**: Low (4-6 test cases for each safe pattern)
- **Impact**: Security - ensures safe errors aren't over-sanitized

### Lines 249-250 - JSON Serialization Fallback in truncate_response()
```python
except (TypeError, ValueError):
    json_str = str(data)
```
- **Location**: Lines 247-250 in `truncate_response()` function
- **What to test**: Graceful fallback when data isn't JSON-serializable
- **Current coverage**:
  - Try block (line 248) is covered
  - Exception handler (lines 249-250) is NOT covered
- **Test approach**:
  ```python
  def test_truncate_response_non_serializable():
      """Test truncation with non-JSON-serializable data"""
      class CustomObject:
          def __str__(self):
              return "custom_object_data"

      obj = CustomObject()
      result, truncated = truncate_response(obj, max_tokens=100)
      assert isinstance(result, str)
      assert "custom_object_data" in result
  ```
- **Effort**: Low (2-3 test cases)
- **Impact**: Robustness - prevents crashes when logging unusual data types

### Lines 415-416 - Schema Retrieval Exception in get_schema()
```python
except Exception as e:
    return f"Error retrieving schema: {str(e)}"
```
- **Location**: Lines 412-416 in `get_schema()` resource
- **What to test**: Graceful error handling when schema retrieval fails
- **Current coverage**:
  - Success path (line 414) is covered
  - Exception handler (lines 415-416) is NOT covered
- **Trigger conditions**:
  - Neo4j connection lost
  - Permission denied on schema query
  - Database corruption
- **Test approach**:
  ```python
  @pytest.mark.asyncio
  async def test_get_schema_neo4j_error(monkeypatch):
      """Test schema retrieval with Neo4j error"""
      mock_graph = MagicMock()
      mock_graph.get_schema.side_effect = Exception("Connection refused")
      monkeypatch.setattr("server.graph", mock_graph)

      result = get_schema()
      assert "Error retrieving schema" in result
      assert "Connection refused" in result
  ```
- **Effort**: Medium (requires mocking graph object)
- **Impact**: User-facing resource - users see error messages

### Lines 478-491 - Rate Limit Exceeded Response in query_graph()
```python
if not is_allowed and rate_info is not None:
    error_msg = f"Rate limit exceeded. Retry after {rate_info.retry_after_seconds:.1f}s"
    logger.warning(f"Rate limit exceeded for query_graph: {query[:50]}...")

    # Log rate limit violation
    audit_logger = get_audit_logger()
    if audit_logger:
        audit_logger.log_error(
            tool="query_graph",
            query=query,
            error=error_msg,
            error_type="rate_limit",
        )

    return {
        "error": error_msg,
        "rate_limited": True,
        "retry_after_seconds": rate_info.retry_after_seconds,
        "reset_time": rate_info.reset_time.isoformat(),
        "success": False,
    }
```
- **Location**: Lines 475-497 in `query_graph()` tool
- **What to test**: Rate limit enforcement with proper response metadata
- **Current coverage**:
  - Check and error path (lines 478-491) is NOT covered
  - Normal query path (lines 505+) is covered
- **Trigger conditions**:
  - `RATE_LIMIT_ENABLED=true`
  - More than N requests in M seconds
- **Test approach**:
  ```python
  @pytest.mark.asyncio
  async def test_query_graph_rate_limited():
      """Test rate limit enforcement in query_graph"""
      # Mock rate limiter to return rate_limited=True
      mock_rate_info = MagicMock()
      mock_rate_info.retry_after_seconds = 45.5
      mock_rate_info.reset_time = datetime.now()

      with patch("server.check_rate_limit", return_value=(False, mock_rate_info)):
          result = await query_graph("test query")
          assert result["success"] is False
          assert result["rate_limited"] is True
          assert result["retry_after_seconds"] == 45.5
  ```
- **Effort**: Medium (requires mocking rate limiter and time objects)
- **Impact**: Critical - prevents resource exhaustion attacks

### Lines 552-553 - Query Sanitizer Warning Logging in query_graph()
```python
if warnings:
    for warning in warnings:
        logger.warning(f"LLM-generated Cypher warning: {warning}")
```
- **Location**: Lines 551-553 in `query_graph()` tool
- **What to test**: Query sanitizer warnings are logged for generated queries
- **Current coverage**:
  - Sanitizer run (line 528) is covered
  - Warning logging (lines 552-553) is NOT covered
- **Trigger conditions**:
  - LLM generates query with sanitizer warnings but not blocking
  - `sanitizer_enabled=true`
- **Test approach**:
  ```python
  @pytest.mark.asyncio
  async def test_query_graph_sanitizer_warnings(monkeypatch, caplog):
      """Test that sanitizer warnings are logged"""
      # Mock sanitize_query to return warnings
      mock_warnings = ["Query uses APOC without explicit allowance"]

      with patch("server.sanitize_query", return_value=(True, None, mock_warnings)):
          with patch("server.chain") as mock_chain:
              mock_chain.invoke.return_value = {
                  "result": "answer",
                  "intermediate_steps": [{"query": "MATCH..."}]
              }
              result = await query_graph("test query")
              assert any("sanitizer warning" in r.message.lower()
                        for r in caplog.records)
  ```
- **Effort**: Medium (requires mocking sanitizer and chain)
- **Impact**: Observability - warnings help debug query quality

### Lines 562-587 - Query Complexity Limiter Blocking in query_graph()
```python
if not is_allowed:
    logger.warning(f"LLM generated complex query: {complexity_error}")
    error_response = {
        "error": f"LLM-generated query blocked by complexity limiter: {complexity_error}",
        "generated_cypher": generated_cypher,
        "complexity_score": complexity_score.total_score if complexity_score else None,
        "complexity_limit": complexity_score.max_allowed if complexity_score else None,
        "complexity_blocked": True,
        "success": False,
    }

    # Audit log the blocked query
    if audit_logger:
        audit_logger.log_error(
            tool="query_graph",
            query=query,
            error=complexity_error or "Query blocked by complexity limiter",
            metadata={
                "generated_cypher": generated_cypher,
                "complexity_blocked": True,
                "complexity_score": complexity_score.total_score
                if complexity_score
                else None,
            },
        )

    return error_response
```
- **Location**: Lines 561-587 in `query_graph()` tool
- **What to test**: Complex query rejection with audit logging
- **Current coverage**: NOT covered (integration test needed)
- **Trigger conditions**:
  - LLM generates query exceeding complexity threshold
  - `COMPLEXITY_LIMIT_ENABLED=true`
- **Test approach**:
  ```python
  @pytest.mark.asyncio
  async def test_query_graph_complexity_blocked(monkeypatch):
      """Test query_graph blocks complex LLM-generated queries"""
      mock_complexity_score = MagicMock()
      mock_complexity_score.total_score = 250
      mock_complexity_score.max_allowed = 100

      with patch("server.check_query_complexity",
                return_value=(False, "Complexity exceeded", mock_complexity_score)):
          with patch("server.chain") as mock_chain:
              mock_chain.invoke.return_value = {
                  "result": "answer",
                  "intermediate_steps": [{"query": "MATCH (n)--()--()--()--()..."}]
              }
              result = await query_graph("complex query")
              assert result["success"] is False
              assert result["complexity_blocked"] is True
              assert result["complexity_score"] == 250
  ```
- **Effort**: High (requires mocking complexity scorer and chain)
- **Impact**: Critical - prevents DoS through complex queries

### Lines 653 - Audit Logging in query_graph() Exception Handler
```python
if audit_logger:
    audit_logger.log_error(...)
```
- **Location**: Lines 652-658 in `query_graph()` exception handler
- **What to test**: Errors are properly audited
- **Current coverage**: NOT covered (requires exception injection)
- **Test approach**:
  ```python
  @pytest.mark.asyncio
  async def test_query_graph_error_audit_logged(monkeypatch):
      """Test that query_graph errors are audit logged"""
      mock_audit_logger = MagicMock()

      with patch("server.get_audit_logger", return_value=mock_audit_logger):
          with patch("server.chain") as mock_chain:
              mock_chain.invoke.side_effect = RuntimeError("Neo4j connection lost")
              result = await query_graph("test query")
              assert result["success"] is False
              mock_audit_logger.log_error.assert_called_once()
  ```
- **Effort**: Medium
- **Impact**: Compliance - audit trails for debugging

### Lines 704-717 - Rate Limit Exceeded Response in execute_cypher()
```python
if not is_allowed and rate_info is not None:
    error_msg = f"Rate limit exceeded. Retry after {rate_info.retry_after_seconds:.1f}s"
    logger.warning(f"Rate limit exceeded for execute_cypher: {cypher_query[:50]}...")

    # Log rate limit violation
    audit_logger = get_audit_logger()
    if audit_logger:
        audit_logger.log_error(
            tool="execute_cypher",
            query=cypher_query,
            error=error_msg,
            error_type="rate_limit",
        )

    return {
        "error": error_msg,
        "rate_limited": True,
        "retry_after_seconds": rate_info.retry_after_seconds,
        "reset_time": rate_info.reset_time.isoformat(),
        "success": False,
    }
```
- **Location**: Lines 701-723 in `_execute_cypher_impl()` function
- **What to test**: Rate limit enforcement for raw Cypher queries
- **Current coverage**: NOT covered (same as query_graph rate limiting)
- **Test approach**: Similar to query_graph rate limiting test
- **Effort**: Medium
- **Impact**: Critical - prevents resource exhaustion

### Lines 760-785 - Query Complexity Blocking in execute_cypher()
```python
if not is_allowed:
    logger.warning(f"Blocked complex query: {complexity_error}")
    error_response = {
        "error": f"Query blocked by complexity limiter: {complexity_error}",
        "query": cypher_query[:200],
        "complexity_score": complexity_score.total_score if complexity_score else None,
        "complexity_limit": complexity_score.max_allowed if complexity_score else None,
        "complexity_blocked": True,
        "success": False,
    }

    # Audit log the blocked query
    audit_logger = get_audit_logger()
    if audit_logger:
        audit_logger.log_error(
            tool="execute_cypher",
            query=cypher_query,
            error=complexity_error or "Query blocked by complexity limiter",
            metadata={
                "complexity_blocked": True,
                "complexity_score": complexity_score.total_score
                if complexity_score
                else None,
            },
        )

    return error_response
```
- **Location**: Lines 759-785 in `_execute_cypher_impl()` function
- **What to test**: Complex raw Cypher queries are rejected
- **Current coverage**: NOT covered
- **Test approach**: Similar to query_graph complexity blocking
- **Effort**: High
- **Impact**: Critical - prevents DoS

### Line 868 - Audit Logging in execute_cypher() Exception Handler
```python
if audit_logger:
    audit_logger.log_error(...)
```
- **Location**: Lines 867-873 in `_execute_cypher_impl()` exception handler
- **What to test**: Cypher execution errors are audited
- **Current coverage**: NOT covered
- **Test approach**: Similar to query_graph error audit test
- **Effort**: Medium
- **Impact**: Compliance

### Line 973 - AttributeError Handling in cleanup()
```python
except AttributeError as e:
    logger.warning(f"⚠ Could not access Neo4j driver: {e}")
```
- **Location**: Lines 972-973 in `cleanup()` function
- **What to test**: Graceful handling when Neo4j driver structure is unexpected
- **Current coverage**: NOT covered (requires mocking Neo4j object)
- **Test approach**:
  ```python
  def test_cleanup_missing_driver_attribute():
      """Test cleanup when _driver attribute doesn't exist"""
      mock_graph = MagicMock(spec=[])  # No _driver attribute
      with patch("server.graph", mock_graph):
          cleanup()  # Should not raise, just warn
  ```
- **Effort**: Low
- **Impact**: Robustness - unexpected Neo4j versions

### Lines 984-1048 - Network Transport Configuration in main()
```python
transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

if transport in ("sse", "http"):
    # Network transport logic (lines 1005-1043)
    ...
else:
    # stdio transport (lines 1044-1048)
    ...
```
- **Location**: Lines 1002-1048 in `main()` function
- **What to test**: Different transport modes are configured correctly
- **Current coverage**: NOT covered (requires full integration test)
- **Branches NOT covered**:
  - Lines 1004-1043: Network transport (SSE/HTTP)
  - Lines 1031-1043: HTTP transport setup
  - Lines 1039-1043: SSE transport setup
- **Test approach**:
  ```python
  def test_main_with_http_transport(monkeypatch):
      """Test main() with HTTP transport"""
      monkeypatch.setenv("MCP_TRANSPORT", "http")
      monkeypatch.setenv("MCP_SERVER_HOST", "127.0.0.1")
      monkeypatch.setenv("MCP_SERVER_PORT", "8000")

      with patch("server.initialize_neo4j"):
          with patch("server.mcp.run") as mock_run:
              main()
              mock_run.assert_called_once()
              args, kwargs = mock_run.call_args
              assert kwargs["transport"] == "http"

  def test_main_with_sse_transport(monkeypatch):
      """Test main() with SSE transport"""
      monkeypatch.setenv("MCP_TRANSPORT", "sse")
      monkeypatch.setenv("MCP_SERVER_HOST", "127.0.0.1")
      monkeypatch.setenv("MCP_SERVER_PORT", "8000")

      with patch("server.initialize_neo4j"):
          with patch("server.mcp.run") as mock_run:
              main()
              args, kwargs = mock_run.call_args
              assert kwargs["transport"] == "sse"

  def test_main_with_stdio_transport(monkeypatch):
      """Test main() with stdio transport (default)"""
      monkeypatch.setenv("MCP_TRANSPORT", "stdio")

      with patch("server.initialize_neo4j"):
          with patch("server.mcp.run") as mock_run:
              main()
              # stdio has no args
              mock_run.assert_called_once()
  ```
- **Effort**: High (3+ test functions with mocking)
- **Impact**: Critical - server startup behavior

---

## 3. UTILITY FUNCTIONS (Helper Methods)

These are low-priority but still valuable for defensive programming verification.

### Lines 121-123 - Executor Initialization in get_executor()
```python
if _executor is None:
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="langchain_")
return _executor
```
- **Location**: Lines 118-123 in `get_executor()` function
- **What to test**: Thread pool executor is created lazily and reused
- **Current coverage**: NOT covered (initialization happens at first use)
- **Test approach**:
  ```python
  def test_get_executor_lazy_initialization():
      """Test executor is lazily initialized"""
      global _executor
      _executor = None  # Reset

      executor1 = get_executor()
      assert isinstance(executor1, ThreadPoolExecutor)

      executor2 = get_executor()
      assert executor1 is executor2  # Same instance

  def test_get_executor_configuration():
      """Test executor has correct configuration"""
      global _executor
      _executor = None

      executor = get_executor()
      assert executor._max_workers == 4
      assert executor._thread_name_prefix == "langchain_"
  ```
- **Effort**: Low
- **Impact**: Observability - ensures proper thread pool setup

---

## 4. TOOL EXECUTION PATHS (MCP Tool Handlers)

These are **high-priority** integration tests requiring Neo4j/LLM backends.

### Summary of Tool Handler Coverage Gaps

| Tool | Uncovered Lines | Issue Type | Trigger |
|------|-----------------|-----------|---------|
| `query_graph` | 478-491, 552-553, 562-587, 653 | Rate limit, warnings, complexity block, error audit | Rate limit exceeded, complex queries, LLM errors |
| `execute_cypher` | 704-717, 760-785, 868 | Rate limit, complexity block, error audit | Same as above |
| `refresh_schema` | (No gaps identified) | - | - |
| `get_schema` | 415-416 | Schema retrieval error | Neo4j error |

---

## TESTING STRATEGY SUMMARY

### Priority 1 (Critical - Production Impact)
1. **Rate limiting enforcement** (Lines 478-491, 704-717)
   - Prevents resource exhaustion attacks
   - Requires mock rate limiter
   - 2-3 tests × 2 tools = 4-6 tests

2. **Complexity limiting** (Lines 562-587, 760-785)
   - Prevents DoS through complex queries
   - Requires mock complexity scorer
   - 2-3 tests × 2 tools = 4-6 tests

3. **Transport configuration** (Lines 984-1048)
   - Server startup behavior
   - Requires environment mocking and module patching
   - 3 tests (stdio, http, sse)

### Priority 2 (High - Data Integrity)
4. **Error handling and audit logging** (Lines 415-416, 653, 868)
   - Ensures errors are logged for compliance
   - Requires exception injection
   - 3 tests

### Priority 3 (Medium - Edge Cases)
5. **Non-string token estimation** (Line 177-178)
   - Defensive programming
   - Simple unit tests
   - 3-5 tests

6. **Safe error pattern matching** (Line 225)
   - Security - prevents over-sanitization
   - Simple unit tests
   - 4-6 tests

7. **JSON serialization fallback** (Lines 249-250)
   - Robustness - handles unusual data
   - Simple unit tests
   - 2-3 tests

8. **Executor lazy initialization** (Lines 121-123)
   - Ensures proper thread pool setup
   - Simple unit tests
   - 2 tests

### Priority 4 (Low - Initialization Warnings)
9. **Environment variable warnings** (Lines 69, 81, 93)
   - Initialization-time configuration
   - Can be tested with module reloading
   - 3 tests

---

## RECOMMENDED TEST IMPLEMENTATION ORDER

1. **Start with Priority 3-4** (infrastructure)
   - Easy wins with high visibility
   - Establish mocking patterns
   - 10-15 tests, ~2-3 hours

2. **Then Priority 2** (audit logging)
   - Foundation for security testing
   - Reuse exception mocking from Priority 1
   - 3 tests, ~1-2 hours

3. **Finally Priority 1** (security features)
   - Most complex, highest value
   - Requires Neo4j/LLM mocking expertise
   - 7-12 tests, ~4-6 hours

**Total estimated effort**: 20-30 tests, 7-11 hours development

---

## COVERAGE TARGETS

| Category | Current | Target | Gap |
|----------|---------|--------|-----|
| Environment variables | 0% | 100% | 3 lines |
| Error handling | ~30% | 100% | 18+ lines |
| Tool execution | ~60% | 100% | 12+ lines |
| Utility functions | ~70% | 100% | 2 lines |
| **Overall** | **~40%** | **95%+** | **~35 lines** |
