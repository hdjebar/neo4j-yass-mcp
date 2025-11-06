# Query Complexity Limits & Cost Estimation

**Status**: Proposed
**Priority**: High (Production Readiness & Security)
**Effort**: Medium-High (4-5 weeks)
**Dependencies**: Query Plan Analysis feature (Feature #1)

## Overview

Add comprehensive query complexity analysis and cost estimation to prevent resource exhaustion attacks and provide users with query performance predictions before execution. This builds on the existing basic protections (query length, large ranges) with sophisticated complexity scoring.

## Value Proposition

- **Security**: Prevent DoS attacks through expensive queries
- **Cost Control**: Predict and limit resource consumption
- **User Experience**: Warn users before executing expensive queries
- **Production Safety**: Protect database from accidental overload
- **SLA Compliance**: Enforce query execution time limits

## Current State Analysis

### Existing Protections (in sanitizer.py)

✅ **Already Implemented**:
- Query length limits (10,000 characters default)
- Detection of large range iterations (`FOREACH ... IN range(1, 1000000)`)
- Blocking of dangerous APOC procedures
- Parameter validation (count, size limits)

❌ **Missing Capabilities**:
- CPU-intensive operation detection
- Memory usage estimation
- Query execution time prediction
- Result set size estimation
- Cartesian product detection
- Variable-length path complexity analysis
- Aggregation complexity scoring
- Subquery complexity limits

## Use Cases

### 1. Preventing Accidental DoS

**Scenario**: Developer writes query that causes database slowdown

```
User Query (via LLM):
"Find everyone connected to everyone else within 10 degrees"

Generated Cypher:
MATCH (a:Person)-[*1..10]-(b:Person)
RETURN a, b

Complexity Analysis:
⚠️ CRITICAL - Estimated complexity: 950/1000
- Variable-length path: 10 hops (exponential growth)
- Estimated result set: 50M+ rows
- Estimated execution time: 5-10 minutes
- Estimated memory: 8GB+

Recommendation: BLOCK or require explicit approval
Alternative: Add LIMIT 100, reduce path length to 3 hops
```

### 2. Query Cost Estimation

**Scenario**: User wants to know query cost before execution

```
Tool: estimate_query_cost()
Input: MATCH (p:Person)-[:KNOWS*1..5]->(f) WHERE p.name = 'Alice' RETURN f

Output:
{
  "complexity_score": 650/1000,
  "risk_level": "medium",
  "estimated_time_ms": 2500,
  "estimated_memory_mb": 150,
  "estimated_db_hits": 50000,
  "estimated_rows": 1000,
  "bottlenecks": [
    "Variable-length path expansion (exponential)",
    "Missing index on Person.name"
  ],
  "recommendation": "Add index, reduce path depth",
  "allow_execution": true
}
```

### 3. Automatic Query Rejection

**Scenario**: Production safety - automatically block dangerous queries

```
Query: MATCH (a:Person), (b:Company) RETURN a, b

Complexity Analysis:
🛑 BLOCKED - Cartesian product detected
- Estimated rows: 10M (10K persons × 1K companies)
- No joining relationship
- Execution time: >1 minute
- Complexity score: 980/1000

Error: "Query complexity exceeds limit (980/1000). Use explicit relationship or add filtering."
```

## Technical Design

### 1. Complexity Scoring System

```python
class QueryComplexityAnalyzer:
    """
    Analyzes Cypher query complexity and estimates resource usage.
    """

    # Complexity score ranges
    SAFE = 0-300          # Fast queries (<100ms)
    MODERATE = 301-600    # Acceptable queries (<1s)
    HIGH = 601-800        # Expensive queries (1-10s)
    CRITICAL = 801-1000   # Dangerous queries (>10s)

    # Maximum allowed complexity
    MAX_COMPLEXITY = 800  # Block queries above this

    def __init__(self, graph: Neo4jGraph):
        self.graph = graph
        self.stats = self._collect_graph_stats()

    def analyze_complexity(
        self,
        query: str,
        parameters: Optional[Dict] = None
    ) -> ComplexityReport:
        """
        Analyze query complexity and estimate resource usage.

        Returns:
            ComplexityReport with scores, estimates, and recommendations
        """
```

### 2. Complexity Factors

#### Factor 1: Variable-Length Paths
```python
def _score_variable_paths(self, query: str) -> int:
    """
    Score: 0-400 based on path length and node counts.

    Examples:
    - [:KNOWS*1..2]     → 50 points (controlled)
    - [:KNOWS*1..5]     → 200 points (moderate risk)
    - [:KNOWS*1..10]    → 400 points (high risk)
    - [:KNOWS*]         → 400 points (unbounded - dangerous)
    """
    pattern = r'\[\*(\d+)?\.\.(\d+)?\]'
    matches = re.findall(pattern, query)

    score = 0
    for min_hops, max_hops in matches:
        max_hops = int(max_hops) if max_hops else 999

        # Exponential growth factor
        if max_hops <= 2:
            score += 50
        elif max_hops <= 5:
            score += 200
        elif max_hops <= 10:
            score += 400
        else:
            score += 400  # Cap at maximum

    return min(score, 400)
```

#### Factor 2: Cartesian Products
```python
def _detect_cartesian_products(self, query: str) -> int:
    """
    Score: 0 or 300 (presence/absence).

    Detects:
    - MATCH (a), (b) without relationship
    - Multiple unconnected MATCH clauses
    """
    # Parse query to detect unconnected patterns
    patterns = self._extract_match_patterns(query)

    if self._has_cartesian_product(patterns):
        return 300  # High penalty
    return 0
```

#### Factor 3: Aggregations
```python
def _score_aggregations(self, query: str) -> int:
    """
    Score: 0-150 based on aggregation complexity.

    Examples:
    - Simple COUNT(*)           → 20 points
    - Multiple aggregations     → 50 points
    - Nested aggregations       → 100 points
    - Aggregation with DISTINCT → +30 points
    """
    agg_functions = ['COUNT', 'SUM', 'AVG', 'COLLECT', 'MAX', 'MIN']

    count = sum(query.upper().count(func) for func in agg_functions)
    has_distinct = 'DISTINCT' in query.upper()

    score = count * 25  # 25 points per aggregation
    if has_distinct:
        score += 30

    return min(score, 150)
```

#### Factor 4: Result Set Size
```python
def _estimate_result_size(self, query: str) -> int:
    """
    Score: 0-200 based on estimated result rows.

    Uses:
    - EXPLAIN plan estimates
    - Graph statistics (node/relationship counts)
    - Pattern analysis
    """
    estimated_rows = self._get_explain_estimate(query)

    if estimated_rows < 100:
        return 0
    elif estimated_rows < 1000:
        return 50
    elif estimated_rows < 10000:
        return 100
    elif estimated_rows < 100000:
        return 150
    else:
        return 200  # Very large result set
```

#### Factor 5: Missing Indexes
```python
def _score_missing_indexes(self, query: str) -> int:
    """
    Score: 0-150 based on index coverage.

    Checks:
    - Property filters without indexes
    - Label scans vs. index seeks
    - Full node scans
    """
    plan = self._get_explain_plan(query)

    score = 0
    for operator in plan['operators']:
        if operator['name'] == 'AllNodesScan':
            score += 100  # Major penalty
        elif operator['name'] == 'NodeByLabelScan':
            score += 50   # Moderate penalty

    return min(score, 150)
```

### 3. Cost Estimation Models

```python
@dataclass
class QueryCostEstimate:
    """Query execution cost estimates"""

    # Complexity
    complexity_score: int        # 0-1000
    risk_level: str             # safe, moderate, high, critical

    # Resource estimates
    estimated_time_ms: int      # Predicted execution time
    estimated_memory_mb: int    # Predicted memory usage
    estimated_db_hits: int      # Database operations
    estimated_rows: int         # Result set size

    # Recommendations
    bottlenecks: List[str]      # Performance issues
    recommendations: List[str]   # Optimization suggestions
    allow_execution: bool       # Should query be allowed?

    # Breakdown
    complexity_breakdown: Dict[str, int]  # Score by factor

def estimate_execution_time(self, complexity_score: int, plan: Dict) -> int:
    """
    Estimate execution time in milliseconds.

    Model based on:
    - Historical query performance data
    - EXPLAIN plan estimates
    - Graph size and statistics
    """
    base_time = 10  # ms baseline

    # Add time based on complexity factors
    time_ms = base_time + (complexity_score * 5)  # 5ms per complexity point

    # Adjust based on plan operators
    for operator in plan['operators']:
        if operator['name'] in ['AllNodesScan', 'CartesianProduct']:
            time_ms *= 10  # Order of magnitude slower

    return time_ms
```

### 4. Integration with Sanitizer

```python
# Enhanced sanitizer with complexity checking
class QuerySanitizer:
    def __init__(
        self,
        # ... existing parameters ...
        enable_complexity_check: bool = True,
        max_complexity: int = 800,
        graph: Optional[Neo4jGraph] = None
    ):
        self.enable_complexity_check = enable_complexity_check
        self.max_complexity = max_complexity

        if enable_complexity_check and graph:
            self.complexity_analyzer = QueryComplexityAnalyzer(graph)

    def sanitize_query(self, query: str) -> Tuple[bool, Optional[str], list]:
        """Enhanced with complexity checking"""

        # ... existing checks ...

        # NEW: Check 8 - Query complexity analysis
        if self.enable_complexity_check:
            complexity = self.complexity_analyzer.analyze_complexity(query)

            if complexity.complexity_score > self.max_complexity:
                return False, (
                    f"Query complexity too high ({complexity.complexity_score}/{self.max_complexity}). "
                    f"Risk level: {complexity.risk_level}. "
                    f"Bottlenecks: {', '.join(complexity.bottlenecks[:2])}"
                ), warnings

            if complexity.risk_level in ['high', 'critical']:
                warnings.append(
                    f"⚠️ {complexity.risk_level.upper()} complexity query "
                    f"(score: {complexity.complexity_score}). "
                    f"Est. time: {complexity.estimated_time_ms}ms"
                )

        return True, None, warnings
```

### 5. New MCP Tools

```python
@mcp.tool()
async def estimate_query_cost(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    explain_factors: bool = True
) -> Dict[str, Any]:
    """
    Estimate the cost and complexity of a query before execution.

    Args:
        query: Cypher query to analyze
        parameters: Query parameters
        explain_factors: Include breakdown of complexity factors

    Returns:
        QueryCostEstimate with all predictions and recommendations
    """
    analyzer = QueryComplexityAnalyzer(graph)
    cost = analyzer.analyze_complexity(query, parameters)

    result = {
        "query": query,
        "complexity_score": cost.complexity_score,
        "risk_level": cost.risk_level,
        "allow_execution": cost.allow_execution,
        "estimates": {
            "time_ms": cost.estimated_time_ms,
            "memory_mb": cost.estimated_memory_mb,
            "db_hits": cost.estimated_db_hits,
            "rows": cost.estimated_rows
        },
        "bottlenecks": cost.bottlenecks,
        "recommendations": cost.recommendations
    }

    if explain_factors:
        result["complexity_breakdown"] = cost.complexity_breakdown

    return result

@mcp.tool()
async def set_complexity_limit(
    max_complexity: int = 800,
    mode: str = "enforce"  # enforce, warn, disabled
) -> Dict[str, Any]:
    """
    Configure query complexity limits.

    Args:
        max_complexity: Maximum allowed complexity score (0-1000)
        mode: enforcement mode (enforce=block, warn=allow with warning, disabled)

    Returns:
        Current configuration
    """
    global _sanitizer

    if mode == "enforce":
        _sanitizer.enable_complexity_check = True
        _sanitizer.max_complexity = max_complexity
    elif mode == "warn":
        _sanitizer.enable_complexity_check = True
        _sanitizer.max_complexity = 1000  # Don't block, just warn
    else:  # disabled
        _sanitizer.enable_complexity_check = False

    return {
        "complexity_check_enabled": _sanitizer.enable_complexity_check,
        "max_complexity": _sanitizer.max_complexity,
        "mode": mode
    }
```

## Implementation Plan

### Week 1: Core Complexity Scoring
- [ ] Implement `QueryComplexityAnalyzer` class
- [ ] Add scoring for variable-length paths
- [ ] Add Cartesian product detection
- [ ] Add aggregation complexity scoring
- [ ] Unit tests for scoring functions

### Week 2: Cost Estimation Models
- [ ] Implement result size estimation
- [ ] Add execution time prediction
- [ ] Add memory usage estimation
- [ ] Missing index detection
- [ ] Validate estimates against real queries

### Week 3: Integration & Tools
- [ ] Integrate complexity checker into sanitizer
- [ ] Add `estimate_query_cost()` MCP tool
- [ ] Add `set_complexity_limit()` MCP tool
- [ ] Configuration via environment variables
- [ ] Integration tests

### Week 4: Tuning & Documentation
- [ ] Calibrate complexity scores with production data
- [ ] Performance optimization
- [ ] User documentation
- [ ] Example queries and use cases
- [ ] Dashboard/monitoring integration

### Week 5: Polish & Testing
- [ ] Edge case testing
- [ ] Security audit
- [ ] Performance benchmarking
- [ ] User acceptance testing
- [ ] Production deployment guide

## Configuration

### Environment Variables

```bash
# Enable/disable complexity checking
ENABLE_COMPLEXITY_CHECK=true

# Maximum allowed complexity score (0-1000)
MAX_QUERY_COMPLEXITY=800

# Enforcement mode
COMPLEXITY_MODE=enforce  # enforce, warn, disabled

# Cost estimation settings
ESTIMATE_TIMEOUT_MS=1000  # Max time for EXPLAIN analysis
ENABLE_COST_CACHING=true  # Cache complexity scores

# Alert thresholds
COMPLEXITY_WARN_THRESHOLD=600
COMPLEXITY_CRITICAL_THRESHOLD=800
```

### Configuration Example

```python
# .env file
ENABLE_COMPLEXITY_CHECK=true
MAX_QUERY_COMPLEXITY=800
COMPLEXITY_MODE=enforce

# server.py initialization
initialize_sanitizer(
    strict_mode=False,
    enable_complexity_check=True,
    max_complexity=800,
    graph=graph  # Pass Neo4j connection for stats
)
```

## Security Considerations

### 1. DoS Prevention
- Limit EXPLAIN execution time (prevent analysis DoS)
- Cache complexity scores for identical queries
- Rate limit cost estimation requests

### 2. Bypass Prevention
```python
# Prevent users from disabling complexity checks
if user_role != "admin":
    raise PermissionError("Only admins can modify complexity limits")
```

### 3. Resource Exhaustion
```python
# Timeout for complexity analysis itself
COMPLEXITY_ANALYSIS_TIMEOUT = 1000  # ms

# Maximum cached complexity scores
MAX_COMPLEXITY_CACHE = 1000  # entries
```

## Testing Strategy

### Unit Tests
```python
def test_variable_path_scoring():
    """Test scoring of variable-length paths"""

def test_cartesian_product_detection():
    """Test detection of Cartesian products"""

def test_complexity_score_calculation():
    """Test overall complexity calculation"""

def test_cost_estimation_accuracy():
    """Validate cost estimates against actual execution"""
```

### Integration Tests
```python
@pytest.mark.integration
async def test_complexity_blocking():
    """Test that high-complexity queries are blocked"""

@pytest.mark.integration
async def test_estimate_query_cost_tool():
    """Test cost estimation MCP tool"""
```

### Performance Tests
```python
def test_complexity_analysis_performance():
    """Ensure analysis is fast (<100ms)"""

def test_explain_timeout():
    """Test timeout for EXPLAIN queries"""
```

## Example Usage

### Via MCP Tool

```python
# Estimate cost before execution
result = await mcp.call_tool(
    "estimate_query_cost",
    {
        "query": "MATCH (p:Person)-[:KNOWS*1..5]->(f) WHERE p.name = 'Alice' RETURN f",
        "explain_factors": True
    }
)

# Response
{
    "complexity_score": 650,
    "risk_level": "high",
    "allow_execution": true,  # Below 800 threshold
    "estimates": {
        "time_ms": 2500,
        "memory_mb": 150,
        "db_hits": 50000,
        "rows": 1000
    },
    "bottlenecks": [
        "Variable-length path expansion (exponential growth)",
        "Missing index on Person.name"
    ],
    "recommendations": [
        "Create index: CREATE INDEX person_name_idx FOR (p:Person) ON (p.name)",
        "Reduce max path depth from 5 to 3",
        "Add LIMIT clause to bound result set"
    ],
    "complexity_breakdown": {
        "variable_paths": 200,
        "cartesian_products": 0,
        "aggregations": 0,
        "result_size": 100,
        "missing_indexes": 100,
        "query_length": 50,
        "total": 650
    }
}
```

### Automatic Blocking

```python
# Query that exceeds complexity limit
query = "MATCH (a:Person)-[*1..10]-(b:Person) RETURN a, b"

# Sanitizer automatically blocks
is_safe, error, warnings = sanitizer.sanitize_query(query)

# Result
is_safe = False
error = "Query complexity too high (950/800). Risk level: critical. Bottlenecks: Variable-length path (10 hops), Cartesian product potential"
```

### Via Natural Language

```
User: "Can you check if this query is expensive before I run it?"
Query: MATCH (p:Person)-[:KNOWS*]->(f) RETURN f

MCP Response:
"⚠️ This query is CRITICAL complexity (score: 850/1000).

**Issues:**
1. Unbounded variable-length path [:KNOWS*] - will explore entire graph
2. Estimated execution time: >1 minute
3. Estimated result set: 100K+ rows
4. Risk: Database overload

**Recommendation:** I cannot execute this query due to complexity limits.

**Suggested fix:**
```cypher
MATCH (p:Person {name: $name})-[:KNOWS*1..3]->(f)
RETURN f
LIMIT 100
```

This limits the search to 3 hops and bounds the result set."
```

## Success Metrics

### Adoption
- 90%+ of queries analyzed for complexity
- <10% false positive rate (queries wrongly blocked)

### Performance
- Complexity analysis completes in <100ms
- <1% overhead on query execution

### Security
- Zero DoS incidents from expensive queries
- 100% detection of known problematic patterns

### User Satisfaction
- Positive feedback on cost estimates
- Reduced "slow query" support tickets

## Future Enhancements

### Phase 2
1. **Machine Learning Models**: Train on historical query performance
2. **Adaptive Thresholds**: Adjust limits based on database load
3. **Query Optimization Hints**: Automatic query rewriting
4. **Cost-Based Query Planning**: Help users choose between query alternatives

### Integration Opportunities
- Monitoring dashboard with complexity trends
- Alert on complexity threshold violations
- Query performance regression detection
- Automatic index creation suggestions

## References

- [Neo4j Query Tuning](https://neo4j.com/docs/cypher-manual/current/query-tuning/)
- [EXPLAIN and PROFILE](https://neo4j.com/docs/cypher-manual/current/execution-plans/)
- [Neo4j Performance](https://neo4j.com/docs/operations-manual/current/performance/)

## Appendix: Complexity Scoring Examples

### Example 1: Safe Query (Score: 50)
```cypher
MATCH (p:Person {email: 'alice@example.com'})
RETURN p.name, p.age

Complexity Breakdown:
- Variable paths: 0 (no paths)
- Cartesian products: 0 (single pattern)
- Aggregations: 0 (simple return)
- Result size: 10 (1 node expected)
- Missing indexes: 40 (no index on email)
Total: 50 (SAFE)
```

### Example 2: Moderate Query (Score: 450)
```cypher
MATCH (p:Person)-[:KNOWS*1..3]->(f:Person)
WHERE p.city = 'London'
RETURN p.name, COUNT(f) as friends

Complexity Breakdown:
- Variable paths: 150 (3 hops)
- Cartesian products: 0
- Aggregations: 50 (COUNT)
- Result size: 100 (estimated 1000 rows)
- Missing indexes: 150 (no index on city)
Total: 450 (MODERATE)
```

### Example 3: Dangerous Query (Score: 950)
```cypher
MATCH (a:Person)-[*1..10]-(b:Person)
RETURN a, b

Complexity Breakdown:
- Variable paths: 400 (10 hops - exponential)
- Cartesian products: 300 (potential cross join)
- Aggregations: 0
- Result size: 200 (estimated 1M+ rows)
- Missing indexes: 50 (label scan)
Total: 950 (CRITICAL - BLOCKED)
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-07
**Author**: Neo4j YASS MCP Team
