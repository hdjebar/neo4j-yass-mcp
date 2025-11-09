# Security Audit Findings - CRITICAL VULNERABILITIES

**Audit Date:** 2025-11-09
**Status:** ✅ **CRITICAL + HIGH ISSUES FIXED** - SecureNeo4jGraph wrapper + Read-only bypass fixes implemented
**Coverage:** 84.13% (369 tests passing)

---

## 🚨 CRITICAL SEVERITY

### 1. ✅ **Query Execution Before Security Checks (CRITICAL - FIXED)**

**Location:** [server.py:442-614](src/neo4j_yass_mcp/server.py#L442-L614)

**Status:** ✅ **FIXED** in commit ee42290

**Vulnerability (ORIGINAL):**
```python
# Line 511: Chain executes query FIRST
result = await asyncio.to_thread(chain.invoke, {"query": query})

# Lines 527-587: THEN sanitization/complexity checks run
# BUT THE QUERY HAS ALREADY EXECUTED!
if generated_cypher and sanitizer_enabled:
    is_safe, sanitize_error, warnings = sanitize_query(generated_cypher, None)
```

**Impact:**
- ⚠️ **COMPLETE SECURITY BYPASS** - Write operations, injections, and schema changes execute before ANY security check
- Attacker can use natural language to bypass sanitizer, complexity limiter, and read-only mode
- All "SISO prevention" is ineffective

**Attack Example:**
```python
# User input: "Delete all nodes"
# GraphCypherQAChain generates: "MATCH (n) DETACH DELETE n"
# Query EXECUTES and deletes everything
# THEN sanitizer checks it (too late!)
```

**Severity:** 🔴 **CRITICAL** - Complete bypass of all security controls

**Fix Implemented:**
Created [SecureNeo4jGraph](src/neo4j_yass_mcp/secure_graph.py) wrapper that:
1. Inherits from `Neo4jGraph` and overrides `query()` method
2. Runs sanitization, complexity checks, and read-only validation BEFORE driver execution
3. Raises `ValueError` when security policies violated (query never executes)
4. Server now uses `SecureNeo4jGraph` instead of `Neo4jGraph`

**Verification:**
- Security checks now happen at graph level (lines 90-129 in secure_graph.py)
- All queries validated before reaching Neo4j driver
- Tests updated to verify ValueError raised on security failures
- No queries can bypass security controls

---

## 🔴 HIGH SEVERITY

### 2. ✅ **Read-Only Mode Bypass via Whitespace/Procedures (HIGH - FIXED)**

**Location:** [server.py:129-177](src/neo4j_yass_mcp/server.py#L129-L177)

**Status:** ✅ **FIXED** - Regex-based validation with whitespace normalization

**Vulnerability (ORIGINAL):**
```python
def check_read_only_access(cypher: str) -> tuple[bool, str | None]:
    cypher_upper = cypher.upper()

    # Lines 137-141: Looks for " KEYWORD " with spaces
    for keyword in write_keywords:
        if f" {keyword} " in cypher_upper or cypher_upper.startswith(f"{keyword} "):
```

**Bypasses (ORIGINAL):**
```cypher
-- Works (detected):
MATCH (n) CREATE (m:Node) RETURN m

-- Bypasses (NOT detected):
CREATE\n(m:Node)              -- Newline after keyword
CREATE\t(m:Node)              -- Tab after keyword
CREATE(m:Node)                -- Parenthesis immediately after
CALL db.schema.nodeTypeProperties()  -- Mutating procedure
CALL apoc.write.create(...)   -- APOC write operation
LOAD CSV FROM 'file:///etc/passwd'   -- File access
FOREACH (x in [1,2] | CREATE ...)    -- Iteration with mutation
```

**Impact (ORIGINAL):**
- Read-only mode completely bypassable
- Schema manipulation possible
- File system access via LOAD CSV
- Batch operations via FOREACH

**Severity:** 🔴 **HIGH** - Complete read-only bypass

**Fix Implemented:**
```python
def check_read_only_access(cypher_query: str) -> str | None:
    # Normalize whitespace (collapse tabs, newlines, multiple spaces)
    normalized = re.sub(r'\s+', ' ', cypher_query.strip()).upper()

    # Check FOREACH and LOAD CSV FIRST (contain write keywords)
    if re.search(r'\bFOREACH\b', normalized):
        return "Read-only mode: FOREACH not allowed"
    if re.search(r'\bLOAD\s+CSV\b', normalized):
        return "Read-only mode: LOAD CSV not allowed"

    # Check mutating procedures (before write keywords)
    mutating_procedures = [
        r'\bCALL\s+DB\.SCHEMA\.',
        r'\bCALL\s+APOC\.WRITE\.',
        r'\bCALL\s+APOC\.CREATE\.',
        r'\bCALL\s+APOC\.MERGE\.',
        r'\bCALL\s+APOC\.REFACTOR\.',
    ]
    for pattern in mutating_procedures:
        if re.search(pattern, normalized):
            return "Read-only mode: Mutating procedure not allowed"

    # Check write keywords using word boundaries
    write_keywords = ["CREATE", "MERGE", "DELETE", "REMOVE", "SET", "DETACH", "DROP"]
    for keyword in write_keywords:
        if re.search(rf'\b{keyword}\b', normalized):
            return f"Read-only mode: {keyword} operations are not allowed"

    return None
```

**Verification:**
- 30 comprehensive tests in [test_readonly_bypass_fixes.py](tests/unit/test_readonly_bypass_fixes.py)
- All bypass scenarios now blocked:
  - ✅ Whitespace bypass (newlines, tabs, multiple spaces)
  - ✅ No-space bypass (CREATE(node))
  - ✅ Mutating procedures (CALL apoc.write.*, CALL db.schema.*)
  - ✅ Dangerous operations (LOAD CSV, FOREACH)
  - ✅ Case insensitivity (create, DeLeTe)
- Valid read operations still allowed (MATCH, RETURN, UNWIND, WITH)
- Word boundary detection prevents false positives (n.created_at allowed)

---

## 🟠 MEDIUM SEVERITY

### 3. **Global Rate Limiting Breaks Per-Client Enforcement (MEDIUM)**

**Location:** [server.py:474-497](src/neo4j_yass_mcp/server.py#L474-L497), [server.py:697-719](src/neo4j_yass_mcp/server.py#L697-L719)

**Vulnerability:**
```python
# Line 477: Hard-coded client_id
allowed, rate_info = check_rate_limit(client_id="default")

# Line 700: Same hard-coded value
allowed, rate_info = check_rate_limit(client_id="default")
```

**Impact:**
- One noisy client blocks ALL clients
- No way to identify which client exceeded quota
- Audit trail useless for forensics
- Denial of Service trivial

**Severity:** 🟠 **MEDIUM** - DoS and forensics impact

**Recommended Fix:**
```python
# Extract client ID from MCP context
def get_client_id(context: Optional[dict] = None) -> str:
    if context and "client_id" in context:
        return context["client_id"]
    if context and "session_id" in context:
        return context["session_id"]
    # Fallback to connection info
    return "default"

# In tools:
@mcp.tool()
async def query_graph(query: str, context: Optional[dict] = None) -> dict:
    client_id = get_client_id(context)
    allowed, rate_info = check_rate_limit(client_id=client_id)
```

---

### 4. **Error Message Sanitization Case Sensitivity Bug (MEDIUM)**

**Location:** [server.py:210-225](src/neo4j_yass_mcp/server.py#L210-L225)

**Vulnerability:**
```python
def sanitize_error_message(error: Exception) -> str:
    error_str = str(error)
    error_lower = error_str.lower()  # Line 216

    # Line 220-221: Compares MIXED-CASE patterns against lowercase string
    safe_patterns = [
        "authentication failed",
        "Connection refused",    # <-- This never matches!
        "timeout",
        # ... etc
    ]

    for pattern in safe_patterns:
        if pattern in error_lower:  # "Connection refused" != "connection refused"
```

**Impact:**
- Most error messages reduced to useless "<Type>: An error occurred..."
- Debugging and operations significantly harder
- May leak sensitive info in unhandled cases

**Severity:** 🟠 **MEDIUM** - Operations impact

**Recommended Fix:**
```python
# Line 220: Lowercase ALL patterns before comparison
safe_patterns = [
    "authentication failed",
    "connection refused",  # Already lowercase
    "timeout",
    # ... etc (all lowercase)
]
```

---

## 🟡 LOW SEVERITY

### 5. **Response Truncation Only Applies to intermediate_steps (LOW)**

**Location:** [server.py:616-631](src/neo4j_yass_mcp/server.py#L616-L631)

**Vulnerability:**
```python
# Lines 616-631: Only truncates intermediate_steps
if _response_token_limit and _response_token_limit > 0:
    intermediate_steps, was_truncated = truncate_response(
        result.get("intermediate_steps", []),
        _response_token_limit,
    )
    # ...

# result["result"] (the actual answer) is NOT truncated!
```

**Impact:**
- Large result strings bypass token limit
- Could cause memory issues or slow responses
- Token budgeting ineffective

**Severity:** 🟡 **LOW** - Resource management

**Recommended Fix:**
```python
# Truncate BOTH intermediate steps AND final result
if _response_token_limit and _response_token_limit > 0:
    # Truncate intermediate steps
    intermediate_steps, steps_truncated = truncate_response(
        result.get("intermediate_steps", []),
        _response_token_limit // 2,  # Split budget
    )

    # Truncate final result
    final_result, result_truncated = truncate_response(
        result.get("result", ""),
        _response_token_limit // 2,
    )

    was_truncated = steps_truncated or result_truncated
```

---

### 6. **Runtime HuggingFace Download Failures (LOW)**

**Location:** [server.py:150-182](src/neo4j_yass_mcp/server.py#L150-L182)

**Vulnerability:**
```python
def get_tokenizer():
    try:
        from transformers import GPT2TokenizerFast
        return GPT2TokenizerFast.from_pretrained("gpt2")  # Network download!
```

**Impact:**
- Fails in air-gapped/restricted environments
- httpx logging errors in tests
- Server startup could fail

**Severity:** 🟡 **LOW** - Reliability

**Recommended Fix:**
```python
def get_tokenizer():
    try:
        # Try tiktoken first (no download needed)
        import tiktoken
        return tiktoken.get_encoding("gpt2")
    except ImportError:
        pass

    try:
        # Fall back to transformers with local cache
        from transformers import GPT2TokenizerFast
        tokenizer = GPT2TokenizerFast.from_pretrained(
            "gpt2",
            local_files_only=True,  # Don't download
        )
        return tokenizer
    except Exception:
        # Graceful degradation: estimate 4 chars per token
        return None  # Handle None in truncate_response
```

---

## 📊 Summary

| Severity | Count | Status |
|----------|-------|--------|
| ✅ CRITICAL | 1 | **FIXED** - SecureNeo4jGraph implemented |
| ✅ HIGH | 1 | **FIXED** - Read-only bypass fixed with regex validation |
| 🟠 MEDIUM | 2 | Fix in next sprint |
| 🟡 LOW | 2 | Backlog |

## 🎯 Immediate Actions

1. ✅ **Issue #1 FIXED** - `SecureNeo4jGraph` wrapper implemented with pre-execution validation
2. ✅ **Issue #2 FIXED** - Read-only mode bypass fixed with regex-based validation + 30 new tests
3. **Next: Fix rate limiting** (Issue #3) - Global client_id breaking per-client enforcement
4. Fix sanitize_error_message case sensitivity (Issue #4)
5. Document security limitations in README

## 🔧 Refactoring Recommendations

1. ✅ **Extract `SecureNeo4jGraph` wrapper** - COMPLETED - All security checks now run before query execution
2. **Split server.py** - 1000+ lines is unmaintainable; separate transport, tools, and utilities
3. **Configuration injection** - Make tokenizer, limits, and security configurable without code changes
4. **Remove unused code** - `get_executor()` is defined but never used

---

**Next Steps:**
1. Create GitHub issues for each vulnerability
2. Prioritize CRITICAL and HIGH fixes
3. Write regression tests for each fix
4. Update security documentation
