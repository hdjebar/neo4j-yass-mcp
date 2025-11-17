# AST-Based Cypher Query Validation Guide

**Date:** 2025-11-16
**Purpose:** Defense-in-depth enhancement for Cypher injection prevention
**Status:** Recommended implementation

---

## Executive Summary

This guide outlines how to implement **Abstract Syntax Tree (AST) based validation** for Cypher queries as an additional security layer beyond the existing regex-based `QuerySanitizer`.

### Why AST Validation?

**Current Approach (Regex-based):**
- ✅ Fast and lightweight
- ✅ Catches common injection patterns
- ⚠️ Can be bypassed with obfuscation
- ⚠️ May have false positives/negatives

**AST Approach (Parse tree validation):**
- ✅ Semantically understands query structure
- ✅ Cannot be bypassed with whitespace/encoding tricks
- ✅ Precise validation of allowed operations
- ⚠️ Slightly higher performance overhead
- ⚠️ Requires Cypher grammar/parser

### Recommendation: **Defense-in-Depth**

Use **both** approaches:
1. **Regex sanitizer** (existing) - Fast first-pass filter
2. **AST validator** (new) - Deep structural validation
3. **Parameter validation** (existing) - Enforce parameterized queries

---

## Current Security Architecture

### Existing Safeguards

```
User Query
    ↓
┌─────────────────────────────────────────┐
│ Layer 1: QuerySanitizer (Regex)        │
│  - Strip strings/comments               │
│  - Block dangerous patterns             │
│  - UTF-8 attack detection               │
│  - Parameter validation                 │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Layer 2: Complexity Limiter             │
│  - Cartesian product detection          │
│  - Variable-length path limits          │
│  - Complexity scoring                   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Layer 3: Read-Only Enforcement          │
│  - Block CREATE, MERGE, DELETE, etc.    │
└─────────────────────────────────────────┘
    ↓
Neo4j Driver
```

**Where to insert AST validation:** Between Layer 1 and Layer 2

---

## AST Validation Design

### Architecture

```python
from typing import Any
from dataclasses import dataclass

@dataclass
class ASTValidationResult:
    """Result of AST validation."""
    is_valid: bool
    error_message: str | None
    warnings: list[str]
    ast_tree: Any | None  # Parsed AST for debugging


class CypherASTValidator:
    """
    AST-based Cypher query validator using parse tree analysis.

    Provides deep structural validation that cannot be bypassed
    with obfuscation techniques.
    """

    def __init__(
        self,
        allow_write: bool = False,
        allow_apoc: bool = False,
        allow_schema_changes: bool = False,
        allowed_procedures: set[str] | None = None,
    ):
        """
        Initialize AST validator.

        Args:
            allow_write: Allow CREATE, MERGE, DELETE, etc.
            allow_apoc: Allow APOC procedure calls
            allow_schema_changes: Allow CREATE INDEX, CREATE CONSTRAINT, etc.
            allowed_procedures: Explicit set of allowed procedure names
        """
        self.allow_write = allow_write
        self.allow_apoc = allow_apoc
        self.allow_schema_changes = allow_schema_changes
        self.allowed_procedures = allowed_procedures or set()

    def validate_query(self, query: str) -> ASTValidationResult:
        """
        Validate Cypher query using AST analysis.

        Args:
            query: Cypher query to validate

        Returns:
            ASTValidationResult with validation outcome
        """
        try:
            # Step 1: Parse query into AST
            ast_tree = self._parse_cypher(query)

            # Step 2: Walk AST and validate structure
            is_valid, error = self._validate_ast(ast_tree)

            # Step 3: Collect warnings (non-blocking issues)
            warnings = self._collect_warnings(ast_tree)

            return ASTValidationResult(
                is_valid=is_valid,
                error_message=error,
                warnings=warnings,
                ast_tree=ast_tree if is_valid else None,
            )

        except Exception as e:
            # Parse failure = invalid query
            return ASTValidationResult(
                is_valid=False,
                error_message=f"Query parsing failed: {str(e)}",
                warnings=[],
                ast_tree=None,
            )

    def _parse_cypher(self, query: str) -> Any:
        """Parse Cypher query into AST."""
        # Implementation: Use ANTLR4 Cypher grammar or custom parser
        raise NotImplementedError("Requires Cypher parser implementation")

    def _validate_ast(self, ast_tree: Any) -> tuple[bool, str | None]:
        """
        Validate AST structure.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validation rules (see below for details)

        # Rule 1: Single statement only
        if self._has_multiple_statements(ast_tree):
            return False, "Multiple statements not allowed (no semicolons)"

        # Rule 2: No write operations (unless allowed)
        if not self.allow_write and self._has_write_operations(ast_tree):
            return False, "Write operations not allowed (CREATE/MERGE/DELETE/SET)"

        # Rule 3: No schema changes (unless allowed)
        if not self.allow_schema_changes and self._has_schema_operations(ast_tree):
            return False, "Schema operations not allowed (CREATE INDEX/CONSTRAINT)"

        # Rule 4: No dangerous procedure calls
        if not self._validate_procedure_calls(ast_tree):
            return False, "Dangerous procedure call detected"

        # Rule 5: No dynamic Cypher execution
        if self._has_dynamic_execution(ast_tree):
            return False, "Dynamic Cypher execution not allowed (apoc.cypher.run)"

        # Rule 6: No string concatenation in query structure
        if self._has_string_concatenation(ast_tree):
            return False, "String concatenation in query structure not allowed"

        # Rule 7: Validate LIMIT bounds
        if not self._validate_limit_clause(ast_tree):
            return False, "LIMIT clause exceeds maximum allowed"

        # Rule 8: Validate relationship pattern depth
        if not self._validate_relationship_patterns(ast_tree):
            return False, "Variable-length relationship exceeds maximum depth"

        return True, None

    def _has_multiple_statements(self, ast_tree: Any) -> bool:
        """Check if AST contains multiple statement roots."""
        # Look for multiple top-level query nodes
        # or semicolon-separated statements
        raise NotImplementedError

    def _has_write_operations(self, ast_tree: Any) -> bool:
        """Check if AST contains write operations."""
        # Look for AST nodes:
        # - CreateClause
        # - MergeClause
        # - DeleteClause
        # - RemoveClause
        # - SetClause
        # - DetachDeleteClause
        raise NotImplementedError

    def _has_schema_operations(self, ast_tree: Any) -> bool:
        """Check if AST contains schema operations."""
        # Look for AST nodes:
        # - CreateIndexStatement
        # - DropIndexStatement
        # - CreateConstraintStatement
        # - DropConstraintStatement
        raise NotImplementedError

    def _validate_procedure_calls(self, ast_tree: Any) -> bool:
        """Validate CALL statements against allowed procedures."""
        # Extract all CALL nodes from AST
        # For each CALL:
        #   1. Get procedure name (e.g., "apoc.cypher.run")
        #   2. Check against allowed_procedures set
        #   3. If allow_apoc=False, block all "apoc.*" procedures
        #   4. Always block dangerous procedures:
        #      - apoc.cypher.run
        #      - apoc.cypher.runMany
        #      - apoc.cypher.parallel
        #      - dbms.security.*
        #      - dbms.cluster.*
        raise NotImplementedError

    def _has_dynamic_execution(self, ast_tree: Any) -> bool:
        """Check for dynamic Cypher execution patterns."""
        # Specifically look for:
        # - apoc.cypher.run()
        # - apoc.cypher.runMany()
        # - apoc.cypher.parallel()
        # These allow arbitrary Cypher execution
        raise NotImplementedError

    def _has_string_concatenation(self, ast_tree: Any) -> bool:
        """Check for string concatenation in query structure."""
        # Look for BinaryExpression nodes with '+' operator
        # where operands are strings
        # This is a common injection vector
        raise NotImplementedError

    def _validate_limit_clause(self, ast_tree: Any) -> bool:
        """Validate LIMIT clause values."""
        # Extract LIMIT nodes
        # Check value doesn't exceed MAX_LIMIT (e.g., 10000)
        # Ensure LIMIT is a literal integer, not an expression
        raise NotImplementedError

    def _validate_relationship_patterns(self, ast_tree: Any) -> bool:
        """Validate variable-length relationship patterns."""
        # Look for RelationshipPattern nodes with variable length
        # e.g., -[*]-> or -[*1..10]->
        # Ensure max length <= MAX_PATH_LENGTH (e.g., 10)
        raise NotImplementedError

    def _collect_warnings(self, ast_tree: Any) -> list[str]:
        """Collect non-blocking warnings from AST."""
        warnings = []

        # Warning 1: Missing LIMIT on unbounded queries
        if self._is_unbounded_query(ast_tree) and not self._has_limit(ast_tree):
            warnings.append("Unbounded query without LIMIT - consider adding LIMIT")

        # Warning 2: Cartesian products
        if self._has_cartesian_product(ast_tree):
            warnings.append("Potential Cartesian product detected")

        # Warning 3: High complexity
        complexity = self._calculate_ast_complexity(ast_tree)
        if complexity > 50:
            warnings.append(f"High query complexity: {complexity}")

        return warnings
```

---

## Implementation Strategy

### Option 1: ANTLR4 Cypher Grammar (Recommended)

**Pros:**
- Official Neo4j Cypher grammar available
- Robust, battle-tested parser
- Full language coverage

**Cons:**
- Requires ANTLR4 dependency (~2MB)
- Additional build step for grammar compilation

**Implementation:**

```python
# Install dependencies
# pip install antlr4-python3-runtime

from antlr4 import InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener

# Import generated parser (requires grammar compilation)
# from .cypher.CypherLexer import CypherLexer
# from .cypher.CypherParser import CypherParser
# from .cypher.CypherListener import CypherListener

class CypherValidationListener(CypherListener):
    """Custom listener to validate AST structure."""

    def __init__(self, validator: CypherASTValidator):
        self.validator = validator
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def enterCreateClause(self, ctx):
        """Triggered when CREATE clause is encountered."""
        if not self.validator.allow_write:
            self.errors.append("CREATE operation not allowed")

    def enterProcedureInvocation(self, ctx):
        """Triggered when CALL procedure is encountered."""
        proc_name = ctx.procedureName().getText()

        # Block dangerous procedures
        dangerous = [
            "apoc.cypher.run",
            "apoc.cypher.runMany",
            "apoc.cypher.parallel",
            "dbms.security",
            "dbms.cluster",
        ]

        for pattern in dangerous:
            if proc_name.startswith(pattern):
                self.errors.append(f"Dangerous procedure: {proc_name}")
                return

        # Check against allowed list
        if self.validator.allowed_procedures:
            if proc_name not in self.validator.allowed_procedures:
                self.errors.append(f"Procedure not in allowed list: {proc_name}")


def parse_with_antlr(query: str) -> tuple[Any, list[str]]:
    """
    Parse Cypher query using ANTLR4.

    Returns:
        Tuple of (parse_tree, errors)
    """
    input_stream = InputStream(query)
    lexer = CypherLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = CypherParser(token_stream)

    # Custom error listener
    error_listener = CustomErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    # Parse query
    tree = parser.cypher()  # Start rule

    return tree, error_listener.errors


class CustomErrorListener(ErrorListener):
    """Custom error listener for ANTLR parser."""

    def __init__(self):
        super().__init__()
        self.errors: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"Line {line}:{column} - {msg}")
```

---

### Option 2: LibCST-style AST Walker (Lighter)

**Pros:**
- No external grammar needed
- Lighter dependency
- Easier to customize

**Cons:**
- Requires implementing custom Cypher parser
- May not cover all edge cases

**Implementation:**

```python
import re
from typing import Any
from dataclasses import dataclass

@dataclass
class ASTNode:
    """Lightweight AST node."""
    type: str  # "MATCH", "CREATE", "CALL", etc.
    children: list['ASTNode']
    value: Any | None = None


class SimpleCypherParser:
    """Simplified Cypher parser for security validation."""

    def parse(self, query: str) -> ASTNode:
        """
        Parse Cypher query into simplified AST.

        This is NOT a full Cypher parser - only enough for security validation.
        """
        # Normalize query
        query = query.strip()

        # Check for multiple statements
        if ';' in query:
            statements = [s.strip() for s in query.split(';') if s.strip()]
            if len(statements) > 1:
                raise ValueError("Multiple statements not allowed")

        # Extract clauses
        clauses = self._extract_clauses(query)

        # Build AST
        root = ASTNode(type="QUERY", children=clauses)
        return root

    def _extract_clauses(self, query: str) -> list[ASTNode]:
        """Extract top-level clauses from query."""
        clauses = []

        # Regex patterns for clause detection
        clause_patterns = [
            (r'\bMATCH\b', 'MATCH'),
            (r'\bCREATE\b', 'CREATE'),
            (r'\bMERGE\b', 'MERGE'),
            (r'\bDELETE\b', 'DELETE'),
            (r'\bRETURN\b', 'RETURN'),
            (r'\bWHERE\b', 'WHERE'),
            (r'\bWITH\b', 'WITH'),
            (r'\bCALL\b', 'CALL'),
            (r'\bSET\b', 'SET'),
            (r'\bREMOVE\b', 'REMOVE'),
        ]

        # Find clause positions
        positions = []
        for pattern, clause_type in clause_patterns:
            for match in re.finditer(pattern, query, re.IGNORECASE):
                positions.append((match.start(), clause_type, match.group()))

        # Sort by position
        positions.sort(key=lambda x: x[0])

        # Extract clause content
        for i, (pos, clause_type, keyword) in enumerate(positions):
            # Get content until next clause or end
            next_pos = positions[i + 1][0] if i + 1 < len(positions) else len(query)
            content = query[pos:next_pos].strip()

            clauses.append(ASTNode(
                type=clause_type,
                children=[],
                value=content,
            ))

        return clauses
```

---

## Integration with Existing Security Layer

### Modify `AsyncSecureNeo4jGraph.query()`

**File:** `src/neo4j_yass_mcp/async_graph.py`

```python
async def query(
    self,
    query: str,
    params: dict[str, Any] | None = None,
    session_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Execute a Cypher query with security checks BEFORE execution.

    Security checks (in order):
    1. Query sanitization - Blocks injections, malformed Unicode, dangerous patterns
    2. AST validation - Deep structural validation (NEW)
    3. Complexity limiting - Prevents resource exhaustion attacks
    4. Read-only enforcement - Blocks write operations if read_only_mode=True
    """
    logger.debug(f"AsyncSecureNeo4jGraph.query() called with: {query[:100]}...")

    # SECURITY CHECK 1: Sanitization (injection + Unicode attacks)
    if self.sanitizer_enabled:
        is_safe, sanitize_error, warnings = sanitize_query(query, params)

        if not is_safe:
            error_msg = f"Query blocked by sanitizer: {sanitize_error}"
            logger.warning(f"🔒 SECURITY: {error_msg}")
            raise ValueError(error_msg)

        if warnings:
            for warning in warnings:
                logger.warning(f"Query sanitizer warning: {warning}")

    # SECURITY CHECK 1.5: AST Validation (NEW - structural validation)
    if self.ast_validator_enabled:
        from neo4j_yass_mcp.security.ast_validator import validate_cypher_ast

        is_valid, ast_error, ast_warnings = validate_cypher_ast(query)

        if not is_valid:
            error_msg = f"Query blocked by AST validator: {ast_error}"
            logger.warning(f"🔒 SECURITY (AST): {error_msg}")
            raise ValueError(error_msg)

        if ast_warnings:
            for warning in ast_warnings:
                logger.info(f"AST validator warning: {warning}")

    # SECURITY CHECK 2: Complexity limiting (DoS protection)
    if self.complexity_limit_enabled:
        is_allowed, complexity_error, complexity_score = check_query_complexity(query)

        if not is_allowed:
            error_msg = f"Query blocked by complexity limiter: {complexity_error}"
            logger.warning(f"🔒 SECURITY: {error_msg}")
            raise ValueError(error_msg)

        if complexity_score and complexity_score.warnings:
            for warning in complexity_score.warnings:
                logger.info(f"Query complexity warning: {warning}")

    # SECURITY CHECK 3: Read-only mode enforcement
    if self.read_only_mode:
        from neo4j_yass_mcp.security.validators import check_read_only_access

        read_only_error = check_read_only_access(query, read_only_mode=True)

        if read_only_error:
            error_msg = f"Query blocked in read-only mode: {read_only_error}"
            logger.warning(f"🔒 SECURITY: {error_msg}")
            raise ValueError(error_msg)

    # ALL SECURITY CHECKS PASSED - Execute query
    logger.debug("All security checks passed, executing query")
    return await super().query(query, params or {})
```

---

## Configuration

### Add AST Validator to Runtime Config

**File:** `src/neo4j_yass_mcp/config/runtime_config.py`

```python
class ASTValidatorConfig(BaseModel):
    """AST validator configuration."""

    enabled: bool = Field(
        default=False,  # Opt-in for now
        description="Enable AST-based query validation",
    )
    allow_write: bool = Field(
        default=False,
        description="Allow write operations in AST validation",
    )
    allow_apoc: bool = Field(
        default=False,
        description="Allow APOC procedures in AST validation",
    )
    allow_schema_changes: bool = Field(
        default=False,
        description="Allow schema changes in AST validation",
    )
    max_query_depth: int = Field(
        default=10,
        ge=1,
        description="Maximum query depth (nested subqueries)",
    )
```

### Environment Variables

```bash
# .env.example

# AST Validator Configuration
AST_VALIDATOR_ENABLED=true                    # Enable AST validation (default: false)
AST_VALIDATOR_ALLOW_WRITE=false              # Allow write operations (default: false)
AST_VALIDATOR_ALLOW_APOC=false               # Allow APOC procedures (default: false)
AST_VALIDATOR_ALLOW_SCHEMA_CHANGES=false     # Allow schema changes (default: false)
AST_VALIDATOR_MAX_QUERY_DEPTH=10             # Max nested query depth (default: 10)
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/unit/test_ast_validator.py`

```python
import pytest
from neo4j_yass_mcp.security.ast_validator import CypherASTValidator

def test_ast_validator_blocks_multiple_statements():
    """AST validator should block semicolon-separated statements."""
    validator = CypherASTValidator()

    query = "MATCH (n) RETURN n; DROP DATABASE neo4j"
    result = validator.validate_query(query)

    assert not result.is_valid
    assert "Multiple statements" in result.error_message


def test_ast_validator_blocks_create_in_read_only():
    """AST validator should block CREATE when write not allowed."""
    validator = CypherASTValidator(allow_write=False)

    query = "CREATE (n:Person {name: 'Alice'})"
    result = validator.validate_query(query)

    assert not result.is_valid
    assert "Write operations not allowed" in result.error_message


def test_ast_validator_blocks_dangerous_apoc():
    """AST validator should block apoc.cypher.run()."""
    validator = CypherASTValidator(allow_apoc=True)  # Even with APOC allowed

    query = "CALL apoc.cypher.run('MATCH (n) RETURN n', {})"
    result = validator.validate_query(query)

    assert not result.is_valid
    assert "Dangerous procedure" in result.error_message


def test_ast_validator_blocks_string_concatenation():
    """AST validator should block string concatenation injection."""
    validator = CypherASTValidator()

    query = "MATCH (n) WHERE n.name = 'User' + $input RETURN n"
    result = validator.validate_query(query)

    assert not result.is_valid
    assert "String concatenation" in result.error_message


def test_ast_validator_allows_safe_query():
    """AST validator should allow safe parameterized queries."""
    validator = CypherASTValidator()

    query = "MATCH (n:Person) WHERE n.name = $name RETURN n LIMIT 10"
    result = validator.validate_query(query)

    assert result.is_valid
    assert result.error_message is None


def test_ast_validator_warns_on_unbounded_query():
    """AST validator should warn about unbounded queries."""
    validator = CypherASTValidator()

    query = "MATCH (n:Person) RETURN n"  # No LIMIT
    result = validator.validate_query(query)

    assert result.is_valid  # Warning, not error
    assert any("LIMIT" in w for w in result.warnings)


def test_ast_validator_validates_limit_bounds():
    """AST validator should validate LIMIT clause values."""
    validator = CypherASTValidator()

    query = "MATCH (n:Person) RETURN n LIMIT 1000000"  # Excessive
    result = validator.validate_query(query)

    assert not result.is_valid
    assert "LIMIT clause exceeds" in result.error_message


def test_ast_validator_validates_relationship_depth():
    """AST validator should validate variable-length relationships."""
    validator = CypherASTValidator()

    query = "MATCH (a)-[*1..100]->(b) RETURN a, b"  # Too deep
    result = validator.validate_query(query)

    assert not result.is_valid
    assert "relationship exceeds maximum depth" in result.error_message
```

### Integration Tests

```python
def test_ast_validator_integration_with_secure_graph():
    """Test AST validator integration with AsyncSecureNeo4jGraph."""
    graph = AsyncSecureNeo4jGraph(
        url="bolt://localhost:7687",
        username="neo4j",
        password="password",
        sanitizer_enabled=True,
        ast_validator_enabled=True,  # Enable AST validation
        complexity_limit_enabled=True,
        read_only_mode=False,
    )

    # Malicious query should be blocked by AST validator
    malicious = "MATCH (n) RETURN n; DROP DATABASE neo4j"

    with pytest.raises(ValueError) as exc_info:
        await graph.query(malicious)

    assert "AST validator" in str(exc_info.value)
    assert "Multiple statements" in str(exc_info.value)
```

---

## Performance Considerations

### Benchmarks

Expected performance impact:

| Security Layer | Time (μs) | Overhead |
|----------------|-----------|----------|
| No validation | 0 | Baseline |
| Regex sanitizer | 50-100 | +0.05ms |
| AST validation (ANTLR) | 200-500 | +0.2-0.5ms |
| AST validation (Simple) | 100-200 | +0.1-0.2ms |
| **Total security stack** | **350-700** | **+0.35-0.7ms** |

**Verdict:** AST validation adds ~0.2-0.5ms overhead, which is acceptable for security-critical operations.

### Optimization Strategies

1. **Cache parsed ASTs:**
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def parse_and_validate_cached(query: str) -> ASTValidationResult:
       """Cache AST parsing for repeated queries."""
       return validator.validate_query(query)
   ```

2. **Skip AST validation for trusted sources:**
   ```python
   # If query comes from internal system (not user input)
   if trusted_source:
       skip_ast_validation = True
   ```

3. **Async AST parsing:**
   ```python
   async def validate_query_async(query: str) -> ASTValidationResult:
       """Run AST validation in thread pool."""
       return await asyncio.to_thread(validator.validate_query, query)
   ```

---

## Deployment Strategy

### Phase 1: Warning Mode (Recommended)

Enable AST validator in **warning-only mode**:

```python
# Initially log violations but don't block
if ast_validation_result.is_valid:
    pass  # Allow query
else:
    logger.warning(f"AST validation failed: {ast_validation_result.error_message}")
    logger.warning("Query allowed in warning-only mode")
    # Continue execution (don't raise)
```

**Benefits:**
- Identify false positives
- Build confidence in AST validator
- No production disruption

### Phase 2: Enforcement Mode

After validation period (2-4 weeks):

```python
# Block queries that fail AST validation
if not ast_validation_result.is_valid:
    raise ValueError(f"AST validation failed: {ast_validation_result.error_message}")
```

### Phase 3: Optimization

After deployment:
- Add caching for common queries
- Tune validation rules based on logs
- Optimize parser performance

---

## Implementation Checklist

### Development

- [ ] Choose parser approach (ANTLR vs. Simple)
- [ ] Implement `CypherASTValidator` class
- [ ] Add AST validation to `AsyncSecureNeo4jGraph.query()`
- [ ] Write unit tests (100% coverage target)
- [ ] Write integration tests
- [ ] Add configuration to `RuntimeConfig`
- [ ] Update `.env.example` with AST validator settings
- [ ] Run performance benchmarks

### Documentation

- [ ] Update `SECURITY.md` with AST validation details
- [ ] Add AST validation to security architecture diagrams
- [ ] Document known limitations
- [ ] Write migration guide

### Deployment

- [ ] Deploy in warning-only mode
- [ ] Monitor logs for false positives
- [ ] Tune validation rules
- [ ] Enable enforcement mode
- [ ] Update security audit report

---

## Known Limitations

### What AST Validation Can't Prevent

1. **Logic Bombs:**
   - `MATCH (n) WHERE n.secret = 'trigger' DELETE n`
   - AST sees valid DELETE, can't detect malicious intent

2. **Data Exfiltration via RETURN:**
   - `MATCH (n:Secret) RETURN n`
   - AST can't distinguish legitimate from unauthorized reads

3. **Resource Exhaustion:**
   - `MATCH (a)-[*]->(b) RETURN a, b`
   - AST sees valid pattern, complexity limiter handles this

4. **Business Logic Bypasses:**
   - `MATCH (n:User {role: 'admin'}) SET n.balance = 1000000`
   - AST validates syntax, can't enforce business rules

### Complementary Controls

AST validation works best with:
- ✅ **Parameter validation** (existing)
- ✅ **Complexity limiting** (existing)
- ✅ **Read-only enforcement** (existing)
- ✅ **Rate limiting** (existing)
- ✅ **Audit logging** (existing)
- ⚠️ **Row-level security** (future - Neo4j Enterprise)
- ⚠️ **Query approval workflow** (future)

---

## Conclusion

### Summary

**AST-based validation** provides **defense-in-depth** against Cypher injection by:
- ✅ Semantically understanding query structure
- ✅ Preventing obfuscation bypasses
- ✅ Enforcing precise allow/deny rules
- ✅ Complementing existing regex-based sanitization

### Recommendation

**Implement AST validation as Phase 2 security enhancement:**

1. **Short-term:** Continue with existing regex sanitizer (already very strong)
2. **Medium-term:** Add AST validation in warning mode
3. **Long-term:** Enable AST enforcement mode

**Priority:** Medium (existing safeguards are already excellent)

**Estimated effort:** 2-3 weeks (including testing and validation)

---

**Document prepared:** 2025-11-16
**Next review:** After AST validator implementation
