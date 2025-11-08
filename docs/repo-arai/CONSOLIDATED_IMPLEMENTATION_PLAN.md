# Consolidated Implementation Plan
## Neo4j YASS MCP - Master Roadmap from Audit Findings

**Plan Date:** 2025-11-08
**Version:** 1.0.0
**Branch:** claude/analyse-review-audit-011CUuZPXdUtf7GLSPAyNwiP
**Source:** Analysis of 3 comprehensive audit reports

---

## Executive Summary

This consolidated plan synthesizes findings from three comprehensive audits:
1. **Security & Code Audit** - 94.8% production readiness (A)
2. **Docker Best Practices** - 90% excellent (4.5/5)
3. **Python Upgrade Analysis** - 15-30% performance opportunity

**Current State:**
- ✅ Production-ready with excellent security practices
- ✅ Well-architected with modern Python patterns
- ⚠️ Minor improvements needed for optimal performance
- ⚠️ Some dependencies outdated

**Target State:**
- 🎯 100% production confidence with 80%+ test coverage
- 🎯 15-30% performance improvement
- 🎯 Latest stable dependencies (Python 3.13, LangChain 1.0, FastMCP 2.10)
- 🎯 Full MCP specification compliance
- 🎯 Enhanced security monitoring and rate limiting

**Timeline:** 6-8 weeks total
**Estimated Effort:** 120-160 hours
**Expected ROI:** High (performance + stability + security)

---

## Priority Matrix

### Critical (Do Immediately - Week 1)

| Item | Effort | Impact | Source Report |
|------|--------|--------|---------------|
| Add resource limits to Docker | 5 min | High | Docker |
| Prevent DEBUG_MODE in production | 30 min | High | Security |
| Update Python to 3.13 | 2-3 days | Very High | Python |
| Refactor asyncio.get_event_loop() | 1 day | Medium | Python |
| Add vulnerability scanning to CI | 15 min | High | Docker |

### High (Week 2-3)

| Item | Effort | Impact | Source Report |
|------|--------|--------|---------------|
| Increase test coverage to 80%+ | 1-2 weeks | Very High | Security |
| Add query complexity limits | 1 week | High | Security |
| Upgrade FastMCP to 2.10+ | 3-4 days | High | Python |
| Add rate limiting | 1 week | Medium | Security |
| Remove deprecated compose version | 1 min | Low | Docker |

### Medium (Week 4-5)

| Item | Effort | Impact | Source Report |
|------|--------|--------|---------------|
| Upgrade LangChain to 1.0 | 4-5 days | High | Python |
| Improve secret management | 2-4 hours | Medium | Docker |
| Pin Python base image version | 2 min | Low | Docker |
| Implement dependency updates | 1 day | Medium | Security |

### Low (Week 6-8)

| Item | Effort | Impact | Source Report |
|------|--------|--------|---------------|
| Code refactoring (match/case) | 1-2 weeks | Medium | Python |
| Add distributed tracing | 1 week | Low | Security |
| Implement caching layer | 1 week | Low | Security |
| SBOM generation | 30 min | Low | Docker |

---

## Phase 1: Critical Security & Performance (Week 1)

**Goal:** Address critical issues and set foundation for upgrades
**Duration:** 5 business days
**Effort:** 24-32 hours
**Risk:** Low

### Day 1: Docker Security & Python Setup

#### Morning: Docker Hardening (2 hours)

**Task 1.1: Add Resource Limits (5 minutes)**
```yaml
# docker-compose.yml
services:
  neo4j-yass-mcp:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

**Validation:**
```bash
docker compose config
docker compose up -d
docker stats neo4j-yass-mcp
```

**Success Criteria:** Container uses ≤2GB memory, ≤2 CPU cores

---

**Task 1.2: Add Vulnerability Scanning (15 minutes)**
```yaml
# .github/workflows/ci.yml - Add to docker-build job
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: neo4j-yass-mcp:test
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'

- name: Upload Trivy results
  uses: github/codeql-action/upload-sarif@v2
  if: always()
  with:
    sarif_file: 'trivy-results.sarif'
```

**Validation:**
```bash
git add .github/workflows/ci.yml
git commit -m "ci: Add Trivy vulnerability scanning"
git push
# Verify GitHub Actions run passes
```

**Success Criteria:** CI pipeline includes security scanning

---

**Task 1.3: Remove Deprecated docker-compose version (1 minute)**
```yaml
# docker-compose.yml - Remove this line:
# version: '3.8'

# File should start with:
services:
  neo4j-yass-mcp:
    ...
```

**Validation:**
```bash
docker compose config  # Should not show deprecation warning
```

**Success Criteria:** No deprecation warnings

---

#### Afternoon: Python 3.13 Setup (3 hours)

**Task 1.4: Update Python Version Constraints**

**File: pyproject.toml**
```toml
[project]
requires-python = ">=3.13"

classifiers = [
    "Programming Language :: Python :: 3.13",
]

[tool.ruff]
target-version = "py313"

[tool.black]
target-version = ["py313"]

[tool.mypy]
python_version = "3.13"
```

**File: Dockerfile**
```dockerfile
ARG PYTHON_VERSION=3.13.8
FROM python:${PYTHON_VERSION}-slim AS builder
```

**File: .github/workflows/ci.yml**
```yaml
matrix:
  python-version: ['3.11', '3.12', '3.13']
```

**Validation:**
```bash
# Test locally with Python 3.13
pyenv install 3.13.8
pyenv local 3.13.8
python --version  # Should show 3.13.8
uv pip install -e ".[dev]"
pytest tests/
```

**Success Criteria:** Tests pass on Python 3.13

---

**Task 1.5: Prevent DEBUG_MODE in Production (30 minutes)**

**File: src/neo4j_yass_mcp/server.py**
```python
# In initialize_neo4j() function, add after line 290:
if _debug_mode:
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment in ("production", "prod"):
        logger.error("❌ DEBUG_MODE cannot be enabled in production environment")
        raise ValueError(
            "DEBUG_MODE=true is not allowed in production. "
            "Set ENVIRONMENT=development to use DEBUG_MODE."
        )
    logger.warning(
        "⚠️  DEBUG_MODE=true - Detailed error messages enabled (DEVELOPMENT ONLY!)"
    )
```

**File: .env.example**
```bash
# Add environment detection
ENVIRONMENT=development  # Options: development, staging, production
```

**Validation:**
```bash
# Test production mode
export ENVIRONMENT=production
export DEBUG_MODE=true
python -m neo4j_yass_mcp.server  # Should fail with error

# Test development mode
export ENVIRONMENT=development
python -m neo4j_yass_mcp.server  # Should work with warning
```

**Success Criteria:** DEBUG_MODE blocked in production environment

---

### Day 2-3: asyncio Refactoring (16 hours)

**Task 1.6: Replace asyncio.get_event_loop() Calls**

**Background:** `asyncio.get_event_loop()` is deprecated in Python 3.10+

**Locations to Update:** 3 places in `server.py`
1. Line 450 - `query_graph` function
2. Line 654 - `execute_cypher` function
3. Line 757 - `refresh_schema` function

**Before:**
```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(get_executor(), lambda: chain.invoke(...))
```

**After (Option 1 - Simple):**
```python
result = await asyncio.to_thread(chain.invoke, {"query": query})
```

**After (Option 2 - Keep ThreadPoolExecutor for control):**
```python
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(get_executor(), lambda: chain.invoke(...))
```

**Implementation:**

**Location 1: query_graph (line 450)**
```python
async def query_graph(query: str) -> dict[str, Any]:
    # ... existing code ...

    try:
        logger.info(f"Processing natural language query: {query}")
        start_time = time.time()

        # NEW: Modern asyncio pattern
        result = await asyncio.to_thread(
            chain.invoke,
            {"query": query}
        )

        execution_time_ms = (time.time() - start_time) * 1000
        # ... rest of function
```

**Location 2: _execute_cypher_impl (line 654)**
```python
async def _execute_cypher_impl(...):
    # ... existing code ...

    try:
        logger.info(f"Executing Cypher query: {cypher_query}")
        params = parameters or {}
        start_time = time.time()

        # NEW: Modern asyncio pattern
        result = await asyncio.to_thread(
            graph.query,
            cypher_query,
            params=params
        )

        execution_time_ms = (time.time() - start_time) * 1000
        # ... rest of function
```

**Location 3: refresh_schema (line 757)**
```python
async def refresh_schema() -> dict[str, Any]:
    if graph is None:
        return {"error": "Neo4j graph not initialized", "success": False}

    try:
        logger.info("Refreshing graph schema")

        # NEW: Modern asyncio pattern
        await asyncio.to_thread(graph.refresh_schema)
        schema = graph.get_schema

        return {"schema": schema, "message": "Schema refreshed successfully", "success": True}
```

**Validation:**
```bash
# Run tests
pytest tests/ -v

# Test async operations
pytest tests/test_utf8_attacks.py -v

# Check for deprecation warnings
python -W all -m pytest tests/

# Manual testing
python -m neo4j_yass_mcp.server  # Should start without warnings
```

**Success Criteria:**
- ✅ No deprecation warnings
- ✅ All async operations work
- ✅ Tests pass
- ✅ No performance regression

---

### Day 4: Testing & Validation (8 hours)

**Task 1.7: Comprehensive Testing**

**Test Plan:**

1. **Unit Tests**
   ```bash
   pytest tests/ -v --cov=src --cov-report=term-missing
   ```

2. **Type Checking**
   ```bash
   mypy src/neo4j_yass_mcp/
   ```

3. **Linting**
   ```bash
   ruff check src/ tests/
   ruff format --check src/ tests/
   ```

4. **Security Scan**
   ```bash
   bandit -r src/neo4j_yass_mcp/
   ```

5. **Integration Tests**
   ```bash
   docker compose up -d
   pytest tests/ -m integration -v
   docker compose down -v
   ```

6. **Performance Benchmark**
   ```bash
   # Create simple benchmark script
   python benchmark.py
   # Compare with baseline
   ```

**Success Criteria:**
- ✅ 100% of existing tests pass
- ✅ No type errors
- ✅ No linting errors
- ✅ No security issues
- ✅ Integration tests pass
- ✅ Performance within 5% of baseline

---

### Day 5: Documentation & Commit (4 hours)

**Task 1.8: Update Documentation**

**Files to Update:**

1. **README.md**
   ```markdown
   ## Requirements
   - Python 3.13+ (recommended for best performance)
   - Docker with Docker Compose V2
   - Neo4j 5.x with APOC plugin
   ```

2. **CHANGELOG.md** (create if doesn't exist)
   ```markdown
   # Changelog

   ## [Unreleased]

   ### Changed
   - Upgraded to Python 3.13.8 for 5-15% performance improvement
   - Replaced deprecated asyncio.get_event_loop() with asyncio.to_thread()
   - Added resource limits to Docker Compose configuration
   - Added Trivy vulnerability scanning to CI/CD pipeline
   - Enforced DEBUG_MODE restriction in production environments

   ### Security
   - Prevented DEBUG_MODE in production to avoid information leakage
   - Added automated vulnerability scanning
   - Implemented container resource limits
   ```

3. **docs/UPGRADE_GUIDE.md** (create)
   ```markdown
   # Upgrade Guide: Phase 1 Improvements

   ## Python 3.13 Upgrade

   ### Prerequisites
   - Install Python 3.13.8+
   - Update dependencies: `uv pip install --upgrade -e ".[dev]"`

   ### Breaking Changes
   - None (backward compatible)

   ### Performance Improvements
   - 5-15% faster overall execution
   - Reduced memory usage (-7%)
   - Better error messages
   ```

**Commit Strategy:**
```bash
# Commit 1: Docker improvements
git add docker-compose.yml .github/workflows/ci.yml
git commit -m "feat: Add Docker resource limits and vulnerability scanning

- Add CPU and memory limits to prevent resource exhaustion
- Integrate Trivy security scanning in CI/CD
- Remove deprecated docker-compose version field

Refs: Docker Best Practices Audit Report"

# Commit 2: Python 3.13 upgrade
git add pyproject.toml Dockerfile .github/workflows/ci.yml
git commit -m "feat: Upgrade to Python 3.13.8 for performance improvements

- Update Python version to 3.13.8 (5-15% performance gain)
- Update all tool configurations (ruff, black, mypy)
- Add Python 3.13 to CI/CD test matrix

Refs: Python Upgrade & Refactoring Report"

# Commit 3: asyncio refactoring
git add src/neo4j_yass_mcp/server.py
git commit -m "refactor: Replace deprecated asyncio.get_event_loop()

- Replace asyncio.get_event_loop() with asyncio.to_thread()
- Update 3 async functions: query_graph, execute_cypher, refresh_schema
- Remove deprecation warnings

Refs: Python Upgrade & Refactoring Report"

# Commit 4: Production safety
git add src/neo4j_yass_mcp/server.py .env.example
git commit -m "feat: Prevent DEBUG_MODE in production environments

- Add environment detection (ENVIRONMENT variable)
- Block DEBUG_MODE when ENVIRONMENT=production
- Add comprehensive logging for security

Refs: Comprehensive Security Audit Report"

# Commit 5: Documentation
git add README.md CHANGELOG.md docs/UPGRADE_GUIDE.md
git commit -m "docs: Update documentation for Phase 1 improvements

- Add Python 3.13 requirement
- Create CHANGELOG.md
- Add upgrade guide for Phase 1"

# Push all changes
git push origin <branch-name>
```

**Success Criteria:**
- ✅ All documentation updated
- ✅ Clear commit messages
- ✅ Changes pushed to repository
- ✅ CI/CD pipeline passes

---

### Phase 1 Summary

**Deliverables:**
- ✅ Python 3.13.8 running
- ✅ Docker resource limits configured
- ✅ Vulnerability scanning in CI
- ✅ asyncio code modernized
- ✅ DEBUG_MODE protection
- ✅ Updated documentation

**Metrics:**
- **Performance:** 5-15% improvement expected
- **Security:** No critical or high vulnerabilities
- **Code Quality:** No deprecation warnings
- **Test Coverage:** Maintained at current level

**Risks Mitigated:**
- Resource exhaustion attacks
- Information leakage via DEBUG_MODE
- Unknown CVEs in dependencies
- Deprecated code patterns

---

## Phase 2: Test Coverage & Security Features (Week 2-3)

**Goal:** Achieve production-grade test coverage and add security features
**Duration:** 10 business days
**Effort:** 60-80 hours
**Risk:** Low-Medium

### Sprint 2.1: Test Coverage Expansion (Week 2)

**Current State:** ~20-30% coverage (UTF-8 attacks only)
**Target:** 80%+ coverage

#### Day 6-7: Server Tests (16 hours)

**Task 2.1: Create test_server.py**

**File: tests/test_server.py**
```python
"""
Comprehensive tests for server.py MCP tools and resources.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from neo4j_yass_mcp.server import (
    query_graph,
    execute_cypher,
    refresh_schema,
    get_schema,
    get_database_info,
    check_read_only_access,
    sanitize_error_message,
    truncate_response,
)


class TestQueryGraph:
    """Test query_graph MCP tool"""

    @pytest.mark.asyncio
    async def test_query_graph_success(self, mock_chain, mock_audit_logger):
        """Test successful natural language query"""
        # Setup
        mock_chain.invoke.return_value = {
            "result": "Tom Cruise starred in Top Gun",
            "intermediate_steps": [
                {"query": "MATCH (m:Movie {title: 'Top Gun'})<-[:ACTED_IN]-(p:Person) RETURN p.name"}
            ]
        }

        # Execute
        result = await query_graph("Who starred in Top Gun?")

        # Assert
        assert result["success"] is True
        assert "Tom Cruise" in result["answer"]
        assert result["generated_cypher"]
        assert mock_audit_logger.log_query.called

    @pytest.mark.asyncio
    async def test_query_graph_sanitizer_blocks_unsafe(self):
        """Test that sanitizer blocks unsafe LLM-generated queries"""
        # Setup - LLM generates dangerous query
        with patch('neo4j_yass_mcp.server.chain') as mock_chain:
            mock_chain.invoke.return_value = {
                "intermediate_steps": [
                    {"query": "MATCH (n) DELETE n; // Malicious"}
                ]
            }

            # Execute
            result = await query_graph("Delete all data")

            # Assert
            assert result["success"] is False
            assert "sanitizer" in result["error"].lower()
            assert result.get("sanitizer_blocked") is True

    @pytest.mark.asyncio
    async def test_query_graph_read_only_mode(self):
        """Test read-only mode blocks write operations"""
        # Setup
        with patch('neo4j_yass_mcp.server._read_only_mode', True):
            with patch('neo4j_yass_mcp.server.chain') as mock_chain:
                mock_chain.invoke.return_value = {
                    "intermediate_steps": [
                        {"query": "CREATE (n:Person {name: 'Test'})"}
                    ]
                }

                # Execute
                result = await query_graph("Create a person")

                # Assert
                assert result["success"] is False
                assert "read-only" in result["error"].lower()


class TestExecuteCypher:
    """Test execute_cypher MCP tool"""

    @pytest.mark.asyncio
    async def test_execute_cypher_simple_query(self, mock_graph):
        """Test simple Cypher query execution"""
        # Setup
        mock_graph.query.return_value = [
            {"name": "Tom Cruise", "born": 1962}
        ]

        # Execute
        result = await execute_cypher(
            "MATCH (p:Person {name: $name}) RETURN p",
            parameters={"name": "Tom Cruise"}
        )

        # Assert
        assert result["success"] is True
        assert len(result["result"]) == 1
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_execute_cypher_sanitizer_blocks(self):
        """Test sanitizer blocks dangerous queries"""
        # Execute
        result = await execute_cypher(
            "MATCH (n) DELETE n; DROP DATABASE neo4j"
        )

        # Assert
        assert result["success"] is False
        assert "sanitizer" in result["error"].lower()


# Add 20+ more test cases...
# - Response truncation
# - Token limit handling
# - Error scenarios
# - Concurrent queries
# - Parameter validation
```

**Coverage Targets:**
- `query_graph`: 90%+
- `execute_cypher`: 90%+
- `refresh_schema`: 85%+
- Resources: 80%+

---

#### Day 8-9: Sanitizer Tests (16 hours)

**Task 2.2: Expand test_sanitizer.py**

**File: tests/test_sanitizer.py**
```python
"""
Comprehensive sanitizer tests for Cypher injection prevention.
"""

import pytest
from neo4j_yass_mcp.security.sanitizer import QuerySanitizer


class TestCypherInjection:
    """Test Cypher injection attack prevention"""

    @pytest.fixture
    def sanitizer(self):
        return QuerySanitizer()

    def test_query_chaining_semicolon(self, sanitizer):
        """Test detection of query chaining with semicolons"""
        query = "MATCH (n:Person) RETURN n; DELETE (n)"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe
        assert "dangerous pattern" in error.lower()

    def test_comment_injection(self, sanitizer):
        """Test detection of comment-based injection"""
        query = "MATCH (n:Person) /* comment */ RETURN n"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe
        assert "comment" in error.lower() or "dangerous" in error.lower()

    def test_load_csv_blocked(self, sanitizer):
        """Test LOAD CSV is blocked"""
        query = "LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe

    def test_apoc_blocked_by_default(self, sanitizer):
        """Test APOC procedures blocked by default"""
        query = "CALL apoc.cypher.run('MATCH (n) DELETE n', {})"
        is_safe, error, warnings = sanitizer.sanitize_query(query)

        assert not is_safe

    # Add 30+ more injection test cases
    # - File operations
    # - System commands
    # - Parameter injection
    # - String escape attacks
```

**Coverage Target:** 95%+ for sanitizer

---

#### Day 10: Audit Logger & Config Tests (8 hours)

**Task 2.3: Create test_audit_logger.py**

Test audit logging functionality:
- Log rotation
- PII redaction
- Retention policies
- JSON/text formats

**Task 2.4: Create test_config.py**

Test configuration modules:
- LLM provider selection
- Password strength validation
- Port allocation
- Logging configuration

---

### Sprint 2.2: Security Features (Week 3)

#### Day 11-13: Query Complexity Limits (24 hours)

**Task 2.5: Implement Query Complexity Analysis**

**File: src/neo4j_yass_mcp/security/complexity.py** (new)
```python
"""
Query Complexity Analysis Module

Prevents resource exhaustion from complex queries.
"""

from dataclasses import dataclass
from typing import Tuple
import re


@dataclass
class QueryComplexity:
    """Complexity metrics for a Cypher query"""

    node_count: int = 0         # Number of MATCH patterns
    relationship_count: int = 0  # Number of relationship traversals
    depth: int = 0              # Maximum pattern depth
    cartesian_products: int = 0  # Unbounded pattern products
    range_size: int = 0         # Total range() iterations
    aggregations: int = 0       # COUNT, SUM, etc.

    @property
    def complexity_score(self) -> int:
        """Calculate overall complexity score"""
        return (
            self.node_count * 1 +
            self.relationship_count * 2 +
            self.depth * 5 +
            self.cartesian_products * 100 +
            self.range_size // 1000 +
            self.aggregations * 2
        )


class ComplexityAnalyzer:
    """Analyze and limit query complexity"""

    def __init__(
        self,
        max_complexity: int = 1000,
        max_depth: int = 5,
        max_range: int = 100000,
        allow_cartesian: bool = False
    ):
        self.max_complexity = max_complexity
        self.max_depth = max_depth
        self.max_range = max_range
        self.allow_cartesian = allow_cartesian

    def analyze(self, query: str) -> Tuple[bool, str | None, QueryComplexity]:
        """
        Analyze query complexity.

        Returns:
            (is_allowed, error_message, complexity_metrics)
        """
        complexity = self._calculate_complexity(query)

        # Check complexity score
        if complexity.complexity_score > self.max_complexity:
            return False, f"Query too complex (score: {complexity.complexity_score}, max: {self.max_complexity})", complexity

        # Check depth
        if complexity.depth > self.max_depth:
            return False, f"Query too deep (depth: {complexity.depth}, max: {self.max_depth})", complexity

        # Check range iterations
        if complexity.range_size > self.max_range:
            return False, f"Range too large (size: {complexity.range_size}, max: {self.max_range})", complexity

        # Check Cartesian products
        if not self.allow_cartesian and complexity.cartesian_products > 0:
            return False, "Cartesian products not allowed (multiple MATCH without relationships)", complexity

        return True, None, complexity

    def _calculate_complexity(self, query: str) -> QueryComplexity:
        """Calculate complexity metrics from query"""
        complexity = QueryComplexity()

        # Count MATCH clauses
        complexity.node_count = len(re.findall(r'\bMATCH\b', query, re.IGNORECASE))

        # Count relationship patterns
        complexity.relationship_count = len(re.findall(r'--|\-\[.*?\]\-', query))

        # Detect Cartesian products (multiple MATCH without WHERE)
        matches = re.findall(r'\bMATCH\b.*?(?=\bMATCH\b|\bRETURN\b|$)', query, re.IGNORECASE | re.DOTALL)
        if len(matches) > 1:
            # Check if there's a WHERE clause joining them
            where_clauses = re.findall(r'\bWHERE\b', query, re.IGNORECASE)
            if len(where_clauses) < len(matches) - 1:
                complexity.cartesian_products = len(matches) - 1

        # Analyze range() calls
        range_patterns = re.findall(r'range\s*\(\s*(\d+)\s*,\s*(\d+)', query, re.IGNORECASE)
        for start, end in range_patterns:
            complexity.range_size += abs(int(end) - int(start))

        # Count aggregations
        agg_functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COLLECT']
        for func in agg_functions:
            complexity.aggregations += len(re.findall(rf'\b{func}\b', query, re.IGNORECASE))

        # Estimate depth (simplified)
        max_bracket_depth = 0
        current_depth = 0
        for char in query:
            if char in '([':
                current_depth += 1
                max_bracket_depth = max(max_bracket_depth, current_depth)
            elif char in ')]':
                current_depth -= 1
        complexity.depth = max_bracket_depth

        return complexity
```

**Integration with server.py:**
```python
# In server.py, add after sanitizer
from neo4j_yass_mcp.security.complexity import ComplexityAnalyzer

# Initialize complexity analyzer
_complexity_analyzer = None

def initialize_complexity_analyzer():
    global _complexity_analyzer

    if os.getenv("COMPLEXITY_CHECK_ENABLED", "true").lower() == "true":
        _complexity_analyzer = ComplexityAnalyzer(
            max_complexity=int(os.getenv("MAX_QUERY_COMPLEXITY", "1000")),
            max_depth=int(os.getenv("MAX_QUERY_DEPTH", "5")),
            max_range=int(os.getenv("MAX_RANGE_SIZE", "100000")),
            allow_cartesian=os.getenv("ALLOW_CARTESIAN", "false").lower() == "true"
        )
        logger.info("Query complexity analyzer enabled")

# In query execution, add check:
if _complexity_analyzer:
    is_allowed, error, metrics = _complexity_analyzer.analyze(cypher_query)
    if not is_allowed:
        logger.warning(f"Query blocked by complexity analyzer: {error}")
        return {"error": f"Query complexity limit exceeded: {error}", "success": False}
```

**Success Criteria:**
- ✅ Complexity analysis implemented
- ✅ Integration with sanitizer
- ✅ Configurable limits
- ✅ Comprehensive tests

---

#### Day 14-15: Rate Limiting (16 hours)

**Task 2.6: Implement Rate Limiting**

**File: src/neo4j_yass_mcp/middleware/rate_limiter.py** (new)
```python
"""
Rate Limiting Middleware for HTTP/SSE transports.
"""

import time
from typing import Dict, Tuple
from collections import defaultdict
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket algorithm for rate limiting"""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens.

        Returns:
            True if tokens available, False if rate limited
        """
        with self.lock:
            now = time.time()

            # Refill tokens based on time elapsed
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

            # Check if enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False


class RateLimiter:
    """IP-based rate limiter using token bucket algorithm"""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        """
        Args:
            requests_per_minute: Sustained rate limit
            burst_size: Maximum burst requests
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=burst_size,
                refill_rate=requests_per_minute / 60.0
            )
        )
        self.cleanup_interval = 300  # Clean up old entries every 5 min
        self.last_cleanup = time.time()

    def check_rate_limit(self, client_ip: str) -> Tuple[bool, dict]:
        """
        Check if request is allowed.

        Returns:
            (is_allowed, rate_limit_info)
        """
        # Periodic cleanup of old buckets
        self._cleanup_old_buckets()

        bucket = self.buckets[client_ip]
        allowed = bucket.consume(tokens=1)

        info = {
            "client_ip": client_ip,
            "tokens_remaining": int(bucket.tokens),
            "capacity": bucket.capacity,
            "refill_rate": bucket.refill_rate
        }

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_ip}")

        return allowed, info

    def _cleanup_old_buckets(self):
        """Remove buckets that haven't been used recently"""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Remove buckets not used in last 10 minutes
        to_remove = [
            ip for ip, bucket in self.buckets.items()
            if now - bucket.last_refill > 600
        ]

        for ip in to_remove:
            del self.buckets[ip]

        self.last_cleanup = now
        logger.debug(f"Cleaned up {len(to_remove)} old rate limit buckets")


# FastMCP middleware integration
# TODO: Add to FastMCP server initialization
```

**Environment Configuration:**
```bash
# .env.example
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST_SIZE=10
```

**Success Criteria:**
- ✅ Token bucket algorithm implemented
- ✅ Per-IP rate limiting
- ✅ Configurable limits
- ✅ Memory efficient (cleanup)

---

### Phase 2 Summary

**Deliverables:**
- ✅ Test coverage: 80%+
- ✅ Query complexity limits
- ✅ Rate limiting implemented
- ✅ Comprehensive test suite

**Metrics:**
- **Test Coverage:** 20% → 80%+
- **Security:** DoS protection added
- **Code Quality:** 95%+ coverage on critical paths

---

## Phase 3: Dependency Upgrades (Week 4-5)

**Goal:** Upgrade to latest stable dependencies
**Duration:** 10 business days
**Effort:** 60-80 hours
**Risk:** Medium

### Sprint 3.1: FastMCP 2.10 Upgrade (Week 4)

#### Day 16-17: FastMCP Migration Research (16 hours)

**Task 3.1: Review Breaking Changes**

1. Read FastMCP 2.0 migration guide
2. Document breaking changes
3. Create migration checklist
4. Plan code updates

**Task 3.2: Update Dependencies**
```toml
# pyproject.toml
dependencies = [
    "fastmcp>=2.10.0,<3.0.0",  # Upgraded from 0.2.0
    ...
]
```

---

#### Day 18-19: Code Migration (16 hours)

**Task 3.3: Update FastMCP Code**

Changes needed (example):
```python
# OLD (FastMCP 0.2)
from fastmcp import FastMCP
mcp = FastMCP("neo4j-yass-mcp", version="1.0.0")

@mcp.tool()
async def query_graph(query: str) -> dict[str, Any]:
    ...

# NEW (FastMCP 2.10) - Check actual API changes
from fastmcp import FastMCP
mcp = FastMCP(
    name="neo4j-yass-mcp",
    version="1.0.0",
    # May have new parameters
)

@mcp.tool()
async def query_graph(query: str) -> dict[str, Any]:
    ...
```

---

#### Day 20: Testing & Validation (8 hours)

**Task 3.4: Test All Transports**

1. stdio transport (Claude Desktop)
2. HTTP transport (production)
3. SSE transport (legacy)

---

### Sprint 3.2: LangChain 1.0 Upgrade (Week 5)

#### Day 21-23: LangChain Migration (24 hours)

**Task 3.5: Review LangChain 1.0 Changes**

**Task 3.6: Update Dependencies**
```toml
dependencies = [
    "langchain>=1.0.0,<2.0.0",
    "langchain-neo4j>=0.2.0,<1.0.0",
    "langchain-openai>=1.0.0,<2.0.0",
    "langchain-anthropic>=1.0.0,<2.0.0",
    "langchain-google-genai>=2.0.0,<3.0.0",
]
```

**Task 3.7: Update Chain Usage**

Review and update:
- GraphCypherQAChain initialization
- LLM provider integrations
- Error handling
- Callback mechanisms

---

#### Day 24-25: Testing & Validation (16 hours)

**Task 3.8: Test LLM Providers**

1. OpenAI (gpt-4, gpt-3.5-turbo)
2. Anthropic (claude-3.5-sonnet, claude-opus)
3. Google (Gemini models)

**Task 3.9: Integration Tests**

- Query translation accuracy
- Error handling
- Streaming support
- Performance benchmarks

---

### Phase 3 Summary

**Deliverables:**
- ✅ FastMCP 2.10+ running
- ✅ LangChain 1.0+ running
- ✅ All transports working
- ✅ All LLM providers tested

**Metrics:**
- **Performance:** Additional 5-10% from LangChain
- **Stability:** Production-ready versions
- **Features:** Full MCP spec compliance

---

## Phase 4: Code Refactoring & Polish (Week 6-8)

**Goal:** Modernize code with Python 3.13 features
**Duration:** 15 business days
**Effort:** 40-60 hours
**Risk:** Low

### Refactoring Tasks

#### Week 6: Pattern Matching

**Task 4.1: Implement match/case** (8 hours)

Locations:
1. LLM provider selection (`config/llm_config.py`)
2. Transport mode selection (`server.py`)
3. Error type handling

**Task 4.2: Add Type Guards** (8 hours)

Use `TypeIs` for:
- Graph initialization checks
- Chain initialization checks
- Sanitizer validation

---

#### Week 7: Performance Optimizations

**Task 4.3: Optimize ThreadPoolExecutor** (8 hours)

- CPU-aware worker count
- Environment configuration
- Monitoring

**Task 4.4: Add dataclass slots** (4 hours)

Update all dataclasses with `slots=True`

---

#### Week 8: Documentation & Final Polish

**Task 4.5: Complete Documentation** (16 hours)

1. API documentation
2. Architecture diagrams
3. Deployment guides
4. Troubleshooting guides

**Task 4.6: Performance Benchmarking** (8 hours)

- Create benchmark suite
- Compare with baseline
- Document improvements

---

## Success Metrics

### Performance Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Query Response Time | 100ms | 85ms (-15%) | Benchmark suite |
| Memory Usage | 200MB | 186MB (-7%) | Docker stats |
| Concurrent Throughput | 10 qps | 12 qps (+20%) | Load testing |
| Startup Time | 10s | 10s (same) | Timer |
| CPU Usage (idle) | 5% | 4% | htop |

### Quality Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Test Coverage | 30% | 80%+ | pytest --cov |
| Type Coverage | 100% | 100% | mypy --strict |
| Security Score | A | A+ | Audit reports |
| Linting Issues | 0 | 0 | ruff check |
| Documentation | Good | Excellent | Manual review |

### Security Metrics

| Metric | Baseline | Target | Tool |
|--------|----------|--------|------|
| Known CVEs | Unknown | 0 CRITICAL/HIGH | Trivy |
| Resource Limits | None | Configured | Docker |
| Rate Limiting | None | Active | Custom |
| Query Complexity | None | Active | Custom |
| Test Attack Vectors | 27 | 100+ | pytest |

---

## Risk Management

### High Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **LangChain 1.0 breaking changes** | Medium | High | Thorough testing, gradual rollout |
| **FastMCP API changes** | Medium | Medium | Review docs, test all features |
| **Performance regression** | Low | High | Benchmark before/after, rollback plan |
| **Test coverage gaps** | Low | Medium | Code review, continuous testing |

### Rollback Plans

**For each phase:**

1. **Git rollback**
   ```bash
   git revert <commit-hash>
   git push
   ```

2. **Dependency rollback**
   ```bash
   git checkout HEAD~1 pyproject.toml
   uv pip install -e ".[dev]"
   ```

3. **Docker rollback**
   ```bash
   docker pull neo4j-yass-mcp:previous-version
   docker tag neo4j-yass-mcp:previous-version neo4j-yass-mcp:latest
   ```

---

## Resource Requirements

### Team

- **Developer Time:** 120-160 hours total
- **QA Time:** 40 hours (testing)
- **DevOps Time:** 20 hours (deployment)
- **Code Review:** 20 hours

### Infrastructure

- **Development Environment:** Python 3.13, Neo4j 5.x
- **CI/CD:** GitHub Actions (existing)
- **Testing:** Neo4j test instance
- **Staging:** Docker Compose deployment

---

## Timeline Gantt Chart

```
Week 1: Phase 1 - Critical Security & Performance
├── Day 1: Docker hardening & Python setup
├── Day 2-3: asyncio refactoring
├── Day 4: Testing & validation
└── Day 5: Documentation & commit

Week 2: Phase 2.1 - Test Coverage
├── Day 6-7: Server tests
├── Day 8-9: Sanitizer tests
└── Day 10: Config & audit tests

Week 3: Phase 2.2 - Security Features
├── Day 11-13: Query complexity limits
└── Day 14-15: Rate limiting

Week 4: Phase 3.1 - FastMCP Upgrade
├── Day 16-17: Migration research
├── Day 18-19: Code migration
└── Day 20: Testing

Week 5: Phase 3.2 - LangChain Upgrade
├── Day 21-23: Migration & updates
└── Day 24-25: Testing & validation

Week 6: Phase 4.1 - Pattern Matching
├── Task 4.1: match/case implementation
└── Task 4.2: Type guards

Week 7: Phase 4.2 - Performance
├── Task 4.3: ThreadPool optimization
└── Task 4.4: dataclass slots

Week 8: Phase 4.3 - Final Polish
├── Task 4.5: Documentation
└── Task 4.6: Benchmarking
```

---

## Communication Plan

### Weekly Status Updates

**Every Friday:**
1. Progress report
2. Metrics update
3. Blockers identified
4. Next week plan

### Stakeholder Reviews

**After each phase:**
1. Demo of new features
2. Performance metrics
3. Security improvements
4. Go/no-go decision for next phase

---

## Conclusion

This consolidated plan provides a clear roadmap from the current state (94.8% production ready) to an optimized, fully tested, and modern Python 3.13-based system.

**Expected Outcomes:**
- ✅ 15-30% performance improvement
- ✅ 80%+ test coverage
- ✅ Latest stable dependencies
- ✅ Enhanced security features
- ✅ Production-ready codebase

**Total Timeline:** 6-8 weeks
**Total Effort:** 120-160 hours
**Expected ROI:** Very High

**Recommendation:** ✅ **APPROVE AND BEGIN PHASE 1 IMMEDIATELY**

---

**Document Version:** 1.0
**Last Updated:** 2025-11-08
**Next Review:** After Phase 1 completion
**Approval:** Pending

---

## Appendix A: Quick Start Commands

### Phase 1 Quick Start

```bash
# 1. Docker improvements
vim docker-compose.yml  # Add resource limits
vim .github/workflows/ci.yml  # Add Trivy

# 2. Python 3.13 upgrade
vim pyproject.toml  # Update Python version
vim Dockerfile  # Update Python version
vim .github/workflows/ci.yml  # Add Python 3.13 to matrix

# 3. asyncio refactoring
vim src/neo4j_yass_mcp/server.py  # Replace get_event_loop()

# 4. Production safety
vim src/neo4j_yass_mcp/server.py  # Add DEBUG_MODE check

# 5. Test everything
pytest tests/ -v --cov=src
docker compose up -d
docker compose logs -f

# 6. Commit and push
git add -A
git commit -m "feat: Phase 1 improvements"
git push
```

---

## Appendix B: Checklist

### Phase 1 Checklist

- [ ] Docker resource limits added
- [ ] Trivy scanning configured
- [ ] Python 3.13 updated in all configs
- [ ] asyncio.get_event_loop() replaced (3 locations)
- [ ] DEBUG_MODE production check added
- [ ] All tests pass on Python 3.13
- [ ] No deprecation warnings
- [ ] Documentation updated
- [ ] Changes committed and pushed
- [ ] CI/CD pipeline passes

### Phase 2 Checklist

- [ ] Server tests written (90%+ coverage)
- [ ] Sanitizer tests expanded (95%+ coverage)
- [ ] Audit logger tests added
- [ ] Config tests added
- [ ] Overall coverage 80%+
- [ ] Query complexity analyzer implemented
- [ ] Rate limiter implemented
- [ ] Integration tests pass

### Phase 3 Checklist

- [ ] FastMCP 2.10 migration complete
- [ ] All transports tested (stdio, HTTP, SSE)
- [ ] LangChain 1.0 migration complete
- [ ] All LLM providers tested
- [ ] Performance benchmarks pass
- [ ] No functionality regression

### Phase 4 Checklist

- [ ] match/case refactoring complete
- [ ] Type guards added
- [ ] ThreadPool optimized
- [ ] dataclass slots added
- [ ] Documentation complete
- [ ] Final benchmarks run
- [ ] Production deployment ready

---

**End of Consolidated Implementation Plan**
