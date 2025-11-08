# Next Steps to Reach 90%+ Test Coverage

## Current Status: 83.30% Coverage

**Achievement Summary:**
- Started at: 81.79%
- Current: 83.30% (+1.51%)
- Target: 90%+
- Remaining gap: ~6.7%

**10 Modules at 100% Coverage:**
✓ All config modules (llm_config, security_config, utils)
✓ All security modules (audit_logger, complexity_limiter, rate_limiter)
✓ Tools module

**Remaining Gaps:**
- sanitizer.py: 94.19% (10 lines)
- server.py: 79.42% (78 lines)

---

## Implementation Plan: 3 Phases

### Phase 3b: Quick Environment Tests (30 min → 84%)
**Effort:** LOW | **Impact:** +0.5-0.7%

Implement simple environment variable tests for disabled security features:
- Lines 69, 81, 93 (warning messages when features disabled)
- Lines 121-123 (executor lazy initialization)

**Files to create:**
1. `tests/unit/test_server_config.py` - Environment variable tests
2. Add 5 simple tests (templates in TEST_IMPLEMENTATION_GUIDE.md lines 42-100)

**Expected coverage:** 83.30% → ~84%

---

### Phase 3c: Security-Critical Tests (4-6 hours → 88-90%)
**Effort:** MEDIUM-HIGH | **Impact:** +4-6%

Focus on security enforcement paths that are currently untested:

#### Priority 1A: Rate Limiting Enforcement (2 hours)
**Lines:** 478-491, 704-717
**Tests needed:** 4-6 tests
**Coverage impact:** +2%

```python
# Test rate limit exceeded scenario
# Test rate limit info in response
# Test client ID extraction
# Test rate limit headers
```

#### Priority 1B: Complexity Limiting Enforcement (2 hours)
**Lines:** 562-587, 760-785
**Tests needed:** 4-6 tests
**Coverage impact:** +2%

```python
# Test query complexity exceeded
# Test complexity warnings
# Test complexity scoring
# Test complexity error responses
```

#### Priority 1C: Error Audit Logging (1 hour)
**Lines:** 653, 868
**Tests needed:** 2-3 tests
**Coverage impact:** +0.5%

```python
# Test audit logging on errors
# Test audit log format
# Test error metadata capture
```

**Expected coverage:** 84% → 88-90%

---

### Phase 3d: Tool Execution Integration Tests (2-3 hours → 92-95%)
**Effort:** HIGH | **Impact:** +4-5%

Add integration tests for MCP tool handlers:

#### Uncovered Tool Paths
**Lines:** 225, 249-250, 415-416, 552-553

**Tests needed:** 8-12 integration tests
- execute_query tool with various scenarios
- get_schema tool edge cases
- analyze_query tool with complex queries
- Error handling in each tool

**Files:**
- Extend `tests/integration/test_server_integration.py`
- Add mock Neo4j driver responses
- Test async tool execution

**Expected coverage:** 88-90% → 92-95%

---

## Quick Start Guide

### Option A: Immediate Quick Wins (30 min)
```bash
# 1. Create environment variable tests
cp TEST_IMPLEMENTATION_GUIDE.md /tmp/guide.md
# Copy tests from lines 42-100 into new file

# 2. Run tests
uv run pytest tests/ --cov=src/neo4j_yass_mcp --cov-report=term

# Expected: 83.30% → 84%
```

### Option B: Security-Critical Path (4-6 hours)
```bash
# 1. Review COVERAGE_ANALYSIS.md for detailed line analysis
# 2. Review TEST_IMPLEMENTATION_GUIDE.md for test templates
# 3. Implement Priority 1 tests (rate limit, complexity, audit)
# 4. Run full test suite

# Expected: 83.30% → 88-90%
```

### Option C: Complete Implementation (8-12 hours)
```bash
# Implement all phases in order:
# Phase 3b → Phase 3c → Phase 3d

# Expected: 83.30% → 92-95%
```

---

## Pre-Made Test Templates

All test templates are ready in:
- **TEST_IMPLEMENTATION_GUIDE.md** - 37 copy-paste templates
- **COVERAGE_ANALYSIS.md** - Detailed line-by-line analysis
- **COVERAGE_REFERENCE_CARD.md** - Visual guides

### Test Files to Create:

1. **tests/unit/test_server_config.py**
   - Environment variable tests
   - Executor initialization
   - Lines: 69, 81, 93, 121-123

2. **tests/unit/test_server_rate_limiting.py**
   - Rate limit enforcement
   - Rate limit error responses
   - Lines: 478-491, 704-717

3. **tests/unit/test_server_complexity.py**
   - Complexity limit enforcement
   - Complexity warnings
   - Lines: 562-587, 760-785

4. **tests/unit/test_server_audit.py**
   - Error audit logging
   - Audit entry format
   - Lines: 653, 868

5. **tests/integration/test_server_tools.py** (extend existing)
   - Tool execution paths
   - Tool error handling
   - Lines: 225, 249-250, 415-416, 552-553

---

## Testing Strategy

### Mock Objects Needed:
```python
# Neo4j Driver Mock
mock_driver = AsyncMock()
mock_session = AsyncMock()
mock_driver.session.return_value.__aenter__.return_value = mock_session

# Rate Limiter Mock
mock_rate_limiter = MagicMock()
mock_rate_limiter.check_rate_limit.return_value = (False, rate_limit_info)

# Complexity Analyzer Mock
mock_analyzer = MagicMock()
mock_analyzer.check_complexity.return_value = (False, "Too complex", score)

# Audit Logger Mock
mock_audit = MagicMock()
```

### Common Patterns:
```python
# Pattern 1: Test disabled feature warning
@patch.dict(os.environ, {"FEATURE_ENABLED": "false"})
def test_feature_disabled_warning(caplog):
    # Trigger module reload or initialization
    # Assert warning in logs

# Pattern 2: Test rate limit exceeded
@patch("server.check_rate_limit")
def test_rate_limit_exceeded(mock_check):
    mock_check.return_value = (False, RateLimitInfo(...))
    # Call tool
    # Assert error response

# Pattern 3: Test complexity exceeded
@patch("server.check_query_complexity")
def test_complexity_exceeded(mock_check):
    mock_check.return_value = (False, "Too complex", score)
    # Call tool
    # Assert error response
```

---

## Coverage Goals

| Phase | Coverage | Lines Added | Tests Added | Time |
|-------|----------|-------------|-------------|------|
| Current | 83.30% | - | 300 | - |
| Phase 3b | ~84% | +3-4 | +5 | 30min |
| Phase 3c | 88-90% | +30-40 | +12-15 | 4-6h |
| Phase 3d | 92-95% | +40-50 | +8-12 | 2-3h |
| **Total** | **92-95%** | **+70-90** | **+25-32** | **~8h** |

---

## Success Criteria

✓ **Minimum Target: 90% coverage**
✓ All security-critical paths tested (rate limit, complexity, audit)
✓ All tool execution paths covered
✓ No regressions in existing tests
✓ CI/CD pipeline passes

---

## Resources

- **Detailed Analysis:** COVERAGE_ANALYSIS.md (23 KB)
- **Test Templates:** TEST_IMPLEMENTATION_GUIDE.md (27 KB)
- **Quick Reference:** COVERAGE_REFERENCE_CARD.md (17 KB)
- **Line Mapping:** UNCOVERED_LINES_SUMMARY.md (9 KB)
- **Navigation:** COVERAGE_ANALYSIS_INDEX.md (12 KB)

---

## Notes

- All analysis files are in project root
- Test templates are copy-paste ready
- Mock patterns are included
- Async testing examples provided
- Integration test extensions documented

**Recommended Approach:**
Start with Phase 3b (30 min) for quick wins, then decide whether to continue with Phase 3c based on coverage requirements.
