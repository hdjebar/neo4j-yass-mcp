# Phase 3: Dependency Upgrade Analysis

**Date:** 2025-11-08
**Status:** Research Complete - Ready for Implementation
**Risk Level:** Medium

## Executive Summary

This document provides a comprehensive analysis of upgrading from current dependency versions to their latest stable releases:

- **FastMCP:** 0.4.1 → 2.13.0.2 (major version jump across 0.x → 1.0 → 2.x)
- **LangChain:** 0.3.27 → 1.0.5 (major version release 0.x → 1.0)
- **MCP Protocol:** 1.20.0 → 1.21.0 (minor version bump)

**Estimated Impact:** MEDIUM
**Estimated Effort:** 60-80 hours (10 business days)
**Breaking Changes:** YES (both FastMCP and LangChain have breaking changes)

---

## Current vs Target Versions

### Package Version Matrix

| Package | Current | Latest | Change Type | Risk |
|---------|---------|--------|-------------|------|
| `fastmcp` | 0.4.1 | 2.13.0.2 | Major | HIGH |
| `langchain` | 0.3.27 | 1.0.5 | Major | MEDIUM |
| `langchain-core` | 0.3.79 | 1.0.4+ | Major | MEDIUM |
| `langchain-neo4j` | 0.5.0 | Latest | Minor | LOW |
| `langchain-openai` | 0.3.35 | Latest | Minor | LOW |
| `langchain-anthropic` | 0.3.22 | Latest | Minor | LOW |
| `langchain-google-genai` | 2.1.12 | Latest | Patch | LOW |
| `mcp` | 1.20.0 | 1.21.0 | Minor | LOW |

---

## 1. FastMCP Migration (0.4.1 → 2.13.0.2)

### Overview
FastMCP has undergone significant evolution from version 0.4.1 to 2.13.0.2, transitioning through three major version milestones (0.x → 1.0 → 2.0 → 2.13). This represents a comprehensive architectural upgrade.

### Breaking Changes

#### 1.1. Import Path Changes (0.x → 1.0+)
**Severity:** HIGH
**Impact:** All FastMCP imports

**Before (0.4.1):**
```python
from mcp.server.fastmcp import FastMCP
```

**After (2.13.0.2):**
```python
from fastmcp import FastMCP
```

**Required Changes:**
- ✅ Already done! Our codebase uses `from fastmcp import FastMCP` (line 24 in server.py)
- No changes needed for imports

#### 1.2. Server Lifespan Behavior (2.13.0+)
**Severity:** MEDIUM
**Impact:** Server initialization/cleanup hooks

**Change:** Server lifespans now run once per server instance instead of per client session.

**Current Status:**
- ✅ No lifespan parameter currently used in our codebase
- No changes needed

**Future Consideration:**
- If we later add lifespan hooks for database connections or background tasks, use the new server-level lifespan API

#### 1.3. New Features Available (2.0+)

**2.13.0 "Cache Me If You Can":**
- ✨ Pluggable storage backends (persistent state)
- ⚡ Response caching middleware
- 🔄 Server lifespan hooks
- 🔐 Improved OAuth support
- 📦 Pydantic input validation
- 🎨 Icon support for richer UX

**2.4.0+:**
- Configuration improvements
- Better error handling

**Opportunity:**
- Consider adding response caching for expensive Neo4j queries
- Evaluate persistent storage for rate limiting state

### Migration Steps for FastMCP

1. **Update pyproject.toml dependency:**
   ```toml
   # Before
   "fastmcp>=0.2.0,<1.0.0"

   # After
   "fastmcp>=2.13.0,<3.0.0"
   ```

2. **Verify import statements** (already correct):
   ```python
   from fastmcp import FastMCP  # ✅ Already using this
   ```

3. **Test server initialization:**
   - Ensure `mcp = FastMCP("neo4j-yass-mcp", version="1.0.0")` works
   - Verify all tool decorators work correctly

4. **Run full test suite:**
   - Unit tests for all tools
   - Integration tests for query execution
   - Security feature tests (sanitizer, rate limiter, etc.)

### FastMCP Risk Assessment

| Area | Risk Level | Mitigation |
|------|-----------|------------|
| Import paths | LOW | Already using correct imports |
| Core API compatibility | LOW | FastMCP maintains backward compatibility |
| Tool decorators | LOW | No breaking changes in decorator API |
| Server initialization | LOW | Our usage is simple, no custom lifespans |
| **Overall Risk** | **LOW** | Minimal breaking changes for our use case |

---

## 2. LangChain Migration (0.3.27 → 1.0.5)

### Overview
LangChain 1.0 represents a major architectural shift focusing on stability, reduced scope, and better abstractions. The package has been restructured with legacy functionality moved to `langchain-classic`.

### Breaking Changes

#### 2.1. Python Version Requirement
**Severity:** HIGH
**Impact:** All environments

**Change:** Python 3.10+ required (was 3.8+)

**Current Status:**
- ✅ Using Python 3.13 (exceeds requirement)
- No changes needed

#### 2.2. Message Object API Changes
**Severity:** MEDIUM
**Impact:** Any code using LangChain message objects

**Change:** `.text()` method is now a property (drop parentheses)

**Before:**
```python
message.text()  # Method call
```

**After:**
```python
message.text  # Property access
```

**Current Status:**
- Need to audit codebase for `.text()` usage
- Likely not used in our query-focused implementation

#### 2.3. AIMessage Changes
**Severity:** LOW
**Impact:** Custom message handling

**Change:** `example` parameter removed from `AIMessage` objects

**Mitigation:**
- Use `additional_kwargs` for extra metadata
- Unlikely to affect our use case (we don't construct AIMessage objects manually)

#### 2.4. Package Scope Reduction
**Severity:** LOW
**Impact:** None (we use provider-specific packages)

**Change:** Legacy functionality moved to `langchain-classic`

**Affected Modules (if used):**
- Retrievers
- Embeddings
- Chains
- Indexing
- Hub

**Current Status:**
- ✅ We use `langchain-neo4j.GraphCypherQAChain` (provider-specific, not affected)
- ✅ We use `langchain-openai`, `langchain-anthropic`, `langchain-google-genai` (provider packages)
- No changes needed

#### 2.5. GraphCypherQAChain Compatibility
**Severity:** HIGH
**Impact:** Core query functionality

**Critical:** Need to verify `GraphCypherQAChain` compatibility with LangChain 1.0

**Current Usage (server.py):**
```python
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph

chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    allow_dangerous_requests=langchain_allow_dangerous,
    return_intermediate_steps=True,
    verbose=False,
)
```

**Verification Needed:**
- Check `langchain-neo4j` version compatibility with `langchain-core>=1.0.4`
- Test `GraphCypherQAChain.from_llm()` constructor
- Verify `allow_dangerous_requests` parameter still exists
- Test `return_intermediate_steps` and `verbose` parameters

### LangChain Provider Packages

**Current Usage:**
```python
# src/neo4j_yass_mcp/config/llm_config.py
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
```

**Changes Required:**
1. Update `langchain-openai`:
   - Now defaults to storing response items in message content (Responses API)
   - Verify ChatOpenAI initialization still works

2. Update `langchain-anthropic`:
   - `max_tokens` parameter now defaults to model-specific values (not 1024)
   - May need to adjust if we rely on old 1024 default

3. Update `langchain-google-genai`:
   - Already on 2.x (compatible with langchain-core 1.0)
   - Likely no changes needed

### Migration Steps for LangChain

1. **Update pyproject.toml dependencies:**
   ```toml
   # Before
   "langchain>=0.1.0,<0.4.0"
   "langchain-neo4j>=0.1.0,<1.0.0"
   "langchain-openai>=0.0.5,<1.0.0"
   "langchain-anthropic>=0.1.0,<1.0.0"

   # After
   "langchain>=1.0.0,<2.0.0"
   "langchain-neo4j>=0.5.0,<1.0.0"  # Verify compatibility
   "langchain-openai>=1.0.0,<2.0.0"
   "langchain-anthropic>=1.0.0,<2.0.0"
   "langchain-core>=1.0.4,<2.0.0"
   ```

2. **Search for `.text()` usage:**
   ```bash
   grep -r "\.text()" src/ tests/
   ```

3. **Test GraphCypherQAChain initialization:**
   - Run `test_connection.py`
   - Verify query generation works
   - Check intermediate steps extraction

4. **Test all LLM providers:**
   - OpenAI (ChatOpenAI)
   - Anthropic (ChatAnthropic)
   - Google (ChatGoogleGenerativeAI)

5. **Run full test suite:**
   - All 287 unit tests
   - Integration tests
   - Test with real Neo4j instance

### LangChain Risk Assessment

| Area | Risk Level | Mitigation |
|------|-----------|------------|
| Python version | LOW | Already using Python 3.13 |
| Message API | LOW | Likely not using `.text()` method |
| GraphCypherQAChain | MEDIUM | Core functionality - needs thorough testing |
| Provider packages | MEDIUM | Need to test all three providers |
| allow_dangerous_requests | HIGH | Critical security parameter - must verify |
| **Overall Risk** | **MEDIUM** | Core query chain needs careful validation |

---

## 3. MCP Protocol (1.20.0 → 1.21.0)

### Overview
Minor version upgrade in the MCP Protocol SDK maintained by Anthropic.

### Changes
- Bug fixes and improvements
- No breaking changes expected
- Maintains Python 3.10+ requirement

### Migration Steps

1. **Update pyproject.toml:**
   ```toml
   # After (add explicit mcp dependency)
   "mcp>=1.21.0,<2.0.0"
   ```

2. **Test server startup:**
   - Verify FastMCP compatibility with MCP 1.21.0
   - Test all transport modes (stdio, http, sse)

### Risk Assessment

| Area | Risk Level |
|------|-----------|
| Protocol compatibility | LOW |
| FastMCP integration | LOW |
| **Overall Risk** | **LOW** |

---

## 4. Testing Strategy

### Phase 3.1: FastMCP Upgrade (Week 4, Days 1-2)

**Duration:** 2 days (16 hours)

1. **Update Dependencies** (2 hours)
   - Update pyproject.toml
   - Run `uv pip install -e ".[dev]"`
   - Document version changes

2. **Smoke Tests** (2 hours)
   - Server starts successfully
   - FastMCP dev server works
   - All tools are registered

3. **Unit Tests** (4 hours)
   - Run full test suite: `uv run pytest tests/`
   - Target: All 287 tests pass
   - Fix any breaking changes

4. **Integration Tests** (4 hours)
   - Test with real Neo4j instance
   - Run `test_connection.py`
   - Test all security features (sanitizer, rate limiter, complexity limiter)
   - Test audit logging

5. **Manual Testing** (4 hours)
   - Test with MCP Inspector: `uv run fastmcp dev src/neo4j_yass_mcp/server.py`
   - Test all three LLM providers (OpenAI, Anthropic, Google)
   - Test query execution with various complexities
   - Test error handling

### Phase 3.2: LangChain Upgrade (Week 4, Days 3-5)

**Duration:** 3 days (24 hours)

1. **Audit Current Usage** (4 hours)
   - Search for `.text()` method usage
   - Review GraphCypherQAChain usage
   - Document all LangChain dependencies

2. **Update Dependencies** (2 hours)
   - Update langchain packages in pyproject.toml
   - Install with `uv pip install -e ".[dev]"`

3. **Code Modifications** (6 hours)
   - Fix any `.text()` calls to `.text` properties
   - Update GraphCypherQAChain initialization if needed
   - Handle any provider-specific changes

4. **Unit Tests** (4 hours)
   - Run full test suite
   - Fix breaking tests
   - Target: 100% test pass rate

5. **Integration Tests** (4 hours)
   - Test with all three LLM providers
   - Test complex queries
   - Test streaming (if enabled)
   - Test all security features

6. **Regression Testing** (4 hours)
   - Verify all existing functionality
   - Test edge cases
   - Performance testing
   - Load testing with rate limiter

### Phase 3.3: Final Validation (Week 5, Days 1-2)

**Duration:** 2 days (16 hours)

1. **Full System Testing** (8 hours)
   - End-to-end query execution
   - All transport modes (stdio, http, sse)
   - Multi-client testing
   - Rate limiting under load
   - Audit log verification

2. **Documentation Updates** (4 hours)
   - Update README with new versions
   - Update installation instructions
   - Document breaking changes
   - Update CHANGELOG.md

3. **Security Validation** (4 hours)
   - Verify sanitizer works
   - Test complexity limiter
   - Test rate limiter
   - Review audit logs
   - Password strength validation

---

## 5. Rollback Plan

### If Critical Issues Found

1. **Immediate Rollback:**
   ```bash
   git checkout main
   uv pip install -e ".[dev]"
   ```

2. **Version Pinning:**
   - Keep pyproject.toml with old versions
   - Document issues found
   - Create GitHub issues for each problem

3. **Incremental Upgrade:**
   - Try FastMCP upgrade alone first
   - Then try LangChain upgrade alone
   - Identify which dependency causes issues

### Rollback Triggers

- Test suite pass rate < 95%
- Critical functionality broken (query execution fails)
- Security features stop working
- Performance degradation > 20%
- Any data loss or corruption

---

## 6. Success Criteria

### Must Have (Blocking)
- ✅ All 287 unit tests pass
- ✅ Test coverage remains ≥ 80%
- ✅ Server starts without errors
- ✅ Query execution works with all LLM providers
- ✅ All security features functional (sanitizer, rate limiter, complexity limiter, audit logger)
- ✅ No regression in existing functionality

### Should Have (Important)
- ✅ Performance equal or better than before
- ✅ MCP Inspector works
- ✅ All transport modes work (stdio, http, sse)
- ✅ Documentation updated

### Nice to Have (Optional)
- 🎯 Leverage new FastMCP 2.13 features (caching, storage backends)
- 🎯 Improved error messages with LangChain 1.0
- 🎯 Better type hints with Pydantic validation

---

## 7. Current Codebase Analysis

### FastMCP Usage

**Files:**
- `src/neo4j_yass_mcp/server.py` (line 24)

**Usage Pattern:**
```python
from fastmcp import FastMCP

# Initialize server
mcp = FastMCP("neo4j-yass-mcp", version="1.0.0")

# Tool decorators (example)
@mcp.tool()
async def query_neo4j(question: str) -> dict:
    # Implementation
```

**Assessment:**
- ✅ Import path already correct (`from fastmcp import FastMCP`)
- ✅ Simple usage, no custom lifespans
- ✅ Standard tool decorators
- ✅ Low risk for breaking changes

### LangChain Usage

**Files:**
- `src/neo4j_yass_mcp/server.py` (line 25)
- `src/neo4j_yass_mcp/config/llm_config.py` (lines 48, 58, 68)

**Usage Pattern:**
```python
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# Create graph
graph = Neo4jGraph(
    url=neo4j_uri,
    username=neo4j_username,
    password=neo4j_password,
    database=neo4j_database,
)

# Create chain
chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    allow_dangerous_requests=True,  # Critical parameter!
    return_intermediate_steps=True,
    verbose=False,
)
```

**Assessment:**
- ⚠️ GraphCypherQAChain compatibility needs verification
- ⚠️ `allow_dangerous_requests` parameter must still exist
- ✅ Using provider-specific packages (good)
- ✅ No custom chain implementations
- 🔍 Need to search for `.text()` usage

### Security Features

**Not affected by upgrades:**
- ✅ Sanitizer (custom implementation)
- ✅ Rate limiter (custom implementation)
- ✅ Complexity limiter (custom implementation)
- ✅ Audit logger (custom implementation)

**May be affected:**
- ⚠️ LangChain's `allow_dangerous_requests` flag (must verify)

---

## 8. Dependencies to Update

### pyproject.toml Changes

```toml
[project]
requires-python = ">=3.13"  # Keep (already exceeds LangChain 1.0 requirement)

dependencies = [
    # FastMCP upgrade
    "fastmcp>=2.13.0,<3.0.0",  # Was: >=0.2.0,<1.0.0

    # LangChain core upgrade
    "langchain>=1.0.0,<2.0.0",  # Was: >=0.1.0,<0.4.0
    "langchain-core>=1.0.4,<2.0.0",  # Add explicit

    # LangChain providers upgrade
    "langchain-neo4j>=0.5.0,<1.0.0",  # Keep (verify compatibility)
    "langchain-openai>=1.0.0,<2.0.0",  # Was: >=0.0.5,<1.0.0
    "langchain-anthropic>=1.0.0,<2.0.0",  # Was: >=0.1.0,<1.0.0
    "langchain-google-genai>=2.0.0,<3.0.0",  # Keep (already 2.x)

    # MCP protocol upgrade
    "mcp>=1.21.0,<2.0.0",  # Add explicit

    # Other dependencies (no changes)
    "neo4j>=5.14.0,<6.0.0",
    "python-dotenv>=1.0.0,<2.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "tokenizers>=0.19.1,<1.0.0",
    "confusable-homoglyphs>=3.2.0,<4.0.0",
    "ftfy>=6.0.0,<7.0.0",
    "zxcvbn>=4.4.0,<5.0.0",
]
```

---

## 9. Action Items

### Sprint 3.1: Research & Planning (COMPLETED)
- ✅ Research FastMCP breaking changes
- ✅ Research LangChain breaking changes
- ✅ Analyze current codebase usage
- ✅ Create migration plan
- ✅ Document risks and mitigations

### Sprint 3.2: FastMCP Upgrade (Week 4, Days 1-2)
- [ ] Update pyproject.toml (fastmcp, mcp)
- [ ] Install dependencies: `uv pip install -e ".[dev]"`
- [ ] Run unit tests: `uv run pytest tests/ -v`
- [ ] Fix any breaking tests
- [ ] Run integration tests with Neo4j
- [ ] Test with MCP Inspector
- [ ] Document any issues found

### Sprint 3.3: LangChain Upgrade (Week 4, Days 3-5)
- [ ] Search for `.text()` usage
- [ ] Update pyproject.toml (langchain packages)
- [ ] Install dependencies: `uv pip install -e ".[dev]"`
- [ ] Fix any `.text()` calls
- [ ] Test GraphCypherQAChain compatibility
- [ ] Run unit tests
- [ ] Test all LLM providers (OpenAI, Anthropic, Google)
- [ ] Run integration tests
- [ ] Document any issues

### Sprint 3.4: Final Validation (Week 5, Days 1-2)
- [ ] Full end-to-end testing
- [ ] Test all transport modes
- [ ] Load testing with rate limiter
- [ ] Security feature validation
- [ ] Performance benchmarking
- [ ] Update README.md
- [ ] Update CHANGELOG.md
- [ ] Create pull request

---

## 10. Risk Mitigation

### High-Risk Areas

1. **GraphCypherQAChain Compatibility**
   - **Risk:** Core query functionality may break
   - **Mitigation:** Test thoroughly with real Neo4j instance
   - **Fallback:** Pin langchain-neo4j to compatible version

2. **allow_dangerous_requests Parameter**
   - **Risk:** Security parameter may be removed or renamed
   - **Mitigation:** Check LangChain 1.0 documentation
   - **Fallback:** Adjust code to new security API

3. **Provider Package Compatibility**
   - **Risk:** LLM provider packages may have breaking changes
   - **Mitigation:** Test each provider individually
   - **Fallback:** Pin provider packages to last working versions

### Medium-Risk Areas

1. **FastMCP 2.13 Behavioral Changes**
   - **Risk:** Subtle changes in server behavior
   - **Mitigation:** Comprehensive integration testing
   - **Fallback:** Downgrade to FastMCP 2.0 if needed

2. **Message Object API**
   - **Risk:** `.text()` method usage
   - **Mitigation:** Search and fix proactively
   - **Fallback:** Easy to fix (just remove parentheses)

---

## 11. Timeline

### Week 4
- **Mon-Tue:** FastMCP upgrade + testing (16 hours)
- **Wed-Fri:** LangChain upgrade + testing (24 hours)

### Week 5
- **Mon-Tue:** Final validation + documentation (16 hours)
- **Wed:** Buffer for issues (8 hours)
- **Thu-Fri:** PR review + merge (8 hours)

**Total:** 72 hours (9 business days)

---

## 12. References

### Official Documentation
- FastMCP Docs: https://gofastmcp.com/
- FastMCP GitHub: https://github.com/jlowin/fastmcp
- LangChain v1 Migration Guide: https://docs.langchain.com/oss/python/migrate/langchain-v1
- LangChain Changelog: https://changelog.langchain.com/

### Key Release Notes
- FastMCP 2.0: https://www.jlowin.dev/blog/fastmcp-2
- FastMCP 2.13: https://gofastmcp.com/updates
- LangChain 1.0: https://blog.langchain.com/langchain-langgraph-1dot0/

### PyPI Pages
- fastmcp: https://pypi.org/project/fastmcp/
- langchain: https://pypi.org/project/langchain/
- mcp: https://pypi.org/project/mcp/

---

## 13. Sign-Off

**Research Completed By:** Claude (Sonnet 4.5)
**Date:** 2025-11-08
**Review Status:** Ready for Implementation
**Next Steps:** Begin Sprint 3.2 (FastMCP Upgrade)

**Confidence Level:** HIGH
- FastMCP migration is low-risk (imports already correct)
- LangChain migration requires careful testing but is well-documented
- Comprehensive testing strategy in place
- Clear rollback plan available

---

## Appendix A: Test Command Reference

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=src/neo4j_yass_mcp --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_rate_limiter.py -v

# Run integration tests
uv run python test_connection.py

# Start MCP Inspector
uv run fastmcp dev src/neo4j_yass_mcp/server.py

# Check for .text() usage
grep -r "\.text()" src/ tests/
```

## Appendix B: Quick Win Features (Post-Migration)

After successful migration, consider leveraging new features:

1. **FastMCP 2.13 Response Caching**
   - Cache expensive Neo4j query results
   - Reduce redundant LLM calls
   - Improve performance for repeated queries

2. **FastMCP 2.13 Storage Backends**
   - Persist rate limiter state across restarts
   - Store audit logs in distributed systems
   - Encrypted disk storage for sensitive data

3. **FastMCP 2.13 Server Lifespans**
   - Proper Neo4j driver connection management
   - Background tasks for log rotation
   - Graceful shutdown handling

4. **LangChain 1.0 Stability**
   - No breaking changes until 2.0
   - Better long-term maintenance
   - Improved type hints
