# Query Plan Analysis & Optimization

**Status**: Proposed
**Priority**: High ⭐ **Recommended First Implementation**
**Effort**: Medium (2-3 weeks)
**Dependencies**: None (uses existing Neo4j capabilities)

## Overview

Add a feature that analyzes Cypher query execution plans and provides performance insights to users. This leverages Neo4j's built-in `EXPLAIN` and `PROFILE` capabilities to help users understand and optimize their queries.

## Value Proposition

- **Immediate Value**: Users get actionable performance insights
- **Educational**: Teaches users about Cypher query optimization
- **Production-Ready**: Helps identify performance issues before they impact production
- **Zero Dependencies**: Uses existing Neo4j functionality
- **Complements Existing Features**: Integrates seamlessly with current architecture

## Use Cases

### 1. Performance Debugging
**Scenario**: A user's query is slow and they need to understand why.

```
User: "Why is my query slow?"
Query: MATCH (p:Person)-[:KNOWS*1..5]->(f) WHERE p.name = 'Alice' RETURN f

MCP Response:
- Query plan shows missing index on Person.name
- Recommendation: CREATE INDEX ON :Person(name)
- Estimated speedup: 100x faster with index
```

### 2. Proactive Optimization
**Scenario**: Developer wants to optimize a query before deploying to production.

```
Tool: analyze_query_performance()
Input: Complex Cypher query
Output:
- Execution plan visualization
- Performance bottlenecks identified
- Optimization suggestions
- Alternative query patterns
```

### 3. Learning Tool
**Scenario**: User learning Cypher wants to understand query efficiency.

```
Feature: Side-by-side comparison of query plans
- Shows "before" and "after" optimization
- Explains impact of indexes, relationship directions, etc.
- Provides learning resources
```

## Technical Design

### New MCP Tool: `analyze_query_performance`

```python
@mcp.tool()
async def analyze_query_performance(
    query: str,
    mode: str = "profile",  # "explain" or "profile"
    include_recommendations: bool = True
) -> Dict[str, Any]:
    """
    Analyze Cypher query performance and provide optimization insights.

    Args:
        query: Cypher query to analyze
        mode: "explain" (estimated plan) or "profile" (actual execution)
        include_recommendations: Include AI-generated optimization suggestions

    Returns:
        {
            "query": original_query,
            "execution_plan": plan_details,
            "performance_metrics": {
                "db_hits": number,
                "rows": number,
                "time_ms": execution_time
            },
            "bottlenecks": [
                {
                    "type": "missing_index",
                    "severity": "high",
                    "description": "No index on :Person(name)",
                    "recommendation": "CREATE INDEX ON :Person(name)"
                }
            ],
            "optimizations": [
                {
                    "original": original_query,
                    "optimized": optimized_query,
                    "explanation": "Added index hint",
                    "expected_improvement": "10x faster"
                }
            ]
        }
    """
```

### Implementation Components

#### 1. Query Plan Parser
```python
class QueryPlanAnalyzer:
    """Analyzes Neo4j query execution plans"""

    def analyze_plan(self, query: str, mode: str) -> Dict:
        """Execute EXPLAIN/PROFILE and parse results"""

    def identify_bottlenecks(self, plan: Dict) -> List[Bottleneck]:
        """Detect performance issues in execution plan"""

    def generate_recommendations(self, bottlenecks: List) -> List[Recommendation]:
        """Generate actionable optimization suggestions"""
```

#### 2. Performance Metrics Extractor
```python
class PerformanceMetrics:
    """Extract and format performance metrics"""

    db_hits: int
    rows: int
    time_ms: float
    memory_mb: float
    operators: List[OperatorMetrics]
```

#### 3. Optimization Suggester
```python
class OptimizationEngine:
    """AI-powered query optimization suggestions"""

    def suggest_indexes(self, plan: Dict) -> List[IndexSuggestion]:
        """Suggest missing indexes"""

    def suggest_query_rewrite(self, query: str, plan: Dict) -> List[str]:
        """Suggest alternative query patterns"""

    def estimate_improvement(self, original: Dict, optimized: Dict) -> float:
        """Estimate performance improvement"""
```

### Integration Points

#### Security Layer
```python
# Add to sanitizer
ANALYSIS_PATTERNS = [
    r"^\s*EXPLAIN\s+",
    r"^\s*PROFILE\s+"
]

def is_analysis_query(query: str) -> bool:
    """Check if query is for analysis (allow EXPLAIN/PROFILE)"""
```

#### Audit Logging
```python
# Log query analysis requests
audit_logger.log_tool_call(
    tool="analyze_query_performance",
    query=query,
    mode=mode,
    findings=bottlenecks
)
```

#### LLM Integration
```python
# Use LLM to generate human-friendly explanations
async def explain_bottleneck(bottleneck: Dict) -> str:
    """Use LLM to explain performance issue in plain language"""
    prompt = f"""
    Explain this Neo4j query performance issue to a developer:
    Type: {bottleneck['type']}
    Details: {bottleneck['details']}

    Provide:
    1. What's happening
    2. Why it's slow
    3. How to fix it
    """
    return await llm.generate(prompt)
```

## Implementation Plan

### Week 1: Core Functionality
- [ ] Implement `QueryPlanAnalyzer` class
- [ ] Add EXPLAIN/PROFILE execution
- [ ] Parse and structure plan output
- [ ] Extract performance metrics
- [ ] Write unit tests

### Week 2: Analysis & Recommendations
- [ ] Implement bottleneck detection
- [ ] Add index recommendation engine
- [ ] Implement query rewrite suggestions
- [ ] Add LLM-powered explanations
- [ ] Integration tests

### Week 3: Integration & Polish
- [ ] Integrate with MCP tool system
- [ ] Add security controls (sanitizer updates)
- [ ] Add audit logging
- [ ] Documentation and examples
- [ ] Performance testing
- [ ] User acceptance testing

## Example Usage

### Via MCP Tool

```python
# Request query analysis
result = await mcp.call_tool(
    "analyze_query_performance",
    {
        "query": "MATCH (p:Person)-[:KNOWS*1..5]->(f) WHERE p.name = 'Alice' RETURN f",
        "mode": "profile",
        "include_recommendations": True
    }
)

# Response
{
    "query": "MATCH (p:Person)-[:KNOWS*1..5]->(f) WHERE p.name = 'Alice' RETURN f",
    "execution_plan": {
        "operators": [
            {
                "name": "Filter",
                "db_hits": 1000000,
                "rows": 1,
                "time_ms": 1500,
                "details": "Filter on p.name = 'Alice'"
            },
            {
                "name": "VarLengthExpand",
                "db_hits": 50000,
                "rows": 100,
                "time_ms": 200
            }
        ]
    },
    "performance_metrics": {
        "total_db_hits": 1050000,
        "total_rows": 100,
        "total_time_ms": 1700,
        "memory_mb": 45
    },
    "bottlenecks": [
        {
            "operator": "Filter",
            "severity": "critical",
            "type": "missing_index",
            "description": "Full node scan on :Person label - checking 1M nodes",
            "impact": "1500ms delay, 1M db_hits",
            "recommendation": {
                "action": "create_index",
                "cypher": "CREATE INDEX person_name_idx FOR (p:Person) ON (p.name)",
                "expected_improvement": "100x faster (1500ms → 15ms)"
            }
        },
        {
            "operator": "VarLengthExpand",
            "severity": "medium",
            "type": "unbounded_expansion",
            "description": "Variable length path up to 5 hops can explore many paths",
            "impact": "Exponential growth with graph size",
            "recommendation": {
                "action": "limit_depth",
                "suggestion": "Consider reducing max depth or adding LIMIT clause",
                "alternative_query": "MATCH (p:Person {name: 'Alice'})-[:KNOWS*1..3]->(f) RETURN f LIMIT 100"
            }
        }
    ],
    "optimizations": [
        {
            "original": "MATCH (p:Person)-[:KNOWS*1..5]->(f) WHERE p.name = 'Alice' RETURN f",
            "optimized": "MATCH (p:Person {name: 'Alice'})-[:KNOWS*1..3]->(f) RETURN f LIMIT 100",
            "changes": [
                "Moved filter to match clause (better planner hints)",
                "Reduced max path depth from 5 to 3",
                "Added LIMIT to bound result set"
            ],
            "expected_improvement": "95% faster",
            "requires": ["Index on :Person(name)"]
        }
    ],
    "summary": {
        "overall_rating": "poor",
        "primary_issue": "Missing index on Person.name causing full scan",
        "quick_fix": "CREATE INDEX person_name_idx FOR (p:Person) ON (p.name)",
        "expected_speedup": "100x"
    }
}
```

### Via Natural Language

```
User: "Analyze the performance of my query:
      MATCH (p:Person)-[:KNOWS*1..5]->(f) WHERE p.name = 'Alice' RETURN f"

MCP Response:
"I've analyzed your query and found a critical performance issue:

**Primary Bottleneck**: Missing index on Person.name
- Impact: Full scan of 1 million Person nodes (1500ms)
- Solution: Create an index: `CREATE INDEX person_name_idx FOR (p:Person) ON (p.name)`
- Expected speedup: 100x faster (1500ms → 15ms)

**Secondary Issue**: Unbounded path expansion
- Your query explores paths up to 5 hops, which grows exponentially
- Recommendation: Reduce to 3 hops and add LIMIT

**Optimized Query**:
```cypher
CREATE INDEX person_name_idx FOR (p:Person) ON (p.name);
MATCH (p:Person {name: 'Alice'})-[:KNOWS*1..3]->(f)
RETURN f
LIMIT 100
```

This will reduce execution time from 1700ms to approximately 50ms (95% improvement)."
```

## Security Considerations

### 1. Query Sanitization
- EXPLAIN/PROFILE queries still need sanitization
- Prevent injection through analyzed queries
- Rate limiting on analysis requests

```python
# Allow EXPLAIN/PROFILE but sanitize the underlying query
if mode in ["explain", "profile"]:
    # Strip EXPLAIN/PROFILE prefix
    base_query = remove_analysis_prefix(query)
    # Sanitize the base query
    is_safe, error, warnings = sanitize_query(base_query)
    if not is_safe:
        raise SecurityError(f"Unsafe query: {error}")
```

### 2. Resource Limits
```python
# Prevent DoS via expensive query analysis
MAX_ANALYSIS_TIME = 30  # seconds
MAX_PLAN_SIZE = 10_000  # operators
MAX_CONCURRENT_ANALYSIS = 5

# Add to configuration
ANALYSIS_ENABLED = os.getenv("ENABLE_QUERY_ANALYSIS", "true").lower() == "true"
```

### 3. Permission Checks
```python
# Only allow analysis if user has query permissions
if not user_has_query_permission():
    raise PermissionError("Query analysis requires query permissions")
```

## Testing Strategy

### Unit Tests
```python
def test_query_plan_parsing():
    """Test parsing of Neo4j execution plans"""

def test_bottleneck_detection():
    """Test identification of performance bottlenecks"""

def test_index_recommendations():
    """Test index suggestion logic"""

def test_query_rewrite_suggestions():
    """Test query optimization suggestions"""
```

### Integration Tests
```python
@pytest.mark.integration
async def test_analyze_query_performance():
    """Test full query analysis workflow"""

@pytest.mark.integration
async def test_analysis_with_real_database():
    """Test against real Neo4j database"""
```

### Performance Tests
```python
def test_analysis_performance():
    """Ensure analysis doesn't add significant overhead"""

def test_concurrent_analysis():
    """Test multiple concurrent analysis requests"""
```

## Documentation

### User Documentation
- [ ] Add to README.md under "Features"
- [ ] Create tutorial: "Optimizing Your Queries"
- [ ] Add examples to QUICK_START.md
- [ ] Update API reference

### Developer Documentation
- [ ] Architecture decision record (ADR)
- [ ] API documentation for new tool
- [ ] Code comments and docstrings
- [ ] Integration guide

## Success Metrics

- **Usage**: 50+ query analyses per week within first month
- **Performance**: Analysis completes in <5 seconds for typical queries
- **User Satisfaction**: Positive feedback on optimization suggestions
- **Impact**: Documented query performance improvements from users

## Future Enhancements

### Phase 2 Features
1. **Historical Analysis**: Track query performance over time
2. **A/B Testing**: Compare performance of different query variants
3. **Automatic Optimization**: Auto-apply safe optimizations
4. **Cost Estimation**: Estimate query cost before execution
5. **Visual Plan Diagrams**: Generate visual execution plan diagrams

### Integration Opportunities
- Integrate with monitoring/alerting system
- Add to query builder assistant
- Export analysis reports (PDF, HTML)
- Query performance dashboards

## References

- [Neo4j Query Tuning](https://neo4j.com/docs/cypher-manual/current/query-tuning/)
- [Neo4j Execution Plans](https://neo4j.com/docs/cypher-manual/current/execution-plans/)
- [EXPLAIN and PROFILE](https://neo4j.com/docs/cypher-manual/current/query-tuning/how-do-i-profile-a-query/)

## Appendix: Example Plans

### Example 1: Missing Index

```
Query: MATCH (p:Person) WHERE p.email = 'alice@example.com' RETURN p

Plan:
┌────────────────────────────────┐
│ Filter (db_hits: 1000000)      │ ← BOTTLENECK
│ p.email = 'alice@example.com'  │
├────────────────────────────────┤
│ AllNodesScan (rows: 1000000)   │ ← FULL SCAN
└────────────────────────────────┘

Recommendation:
CREATE INDEX person_email_idx FOR (p:Person) ON (p.email)

After Index:
┌────────────────────────────────┐
│ NodeIndexSeek (db_hits: 1)     │ ← OPTIMIZED
│ p.email = 'alice@example.com'  │
└────────────────────────────────┘
```

### Example 2: Cartesian Product

```
Query: MATCH (a:Person), (b:Company) WHERE a.company_id = b.id RETURN a, b

Plan:
┌────────────────────────────────┐
│ Filter (db_hits: 10000000)     │ ← BOTTLENECK
├────────────────────────────────┤
│ CartesianProduct               │ ← PROBLEM
│ (rows: 10000000)               │
├────────────────────────────────┤
│ AllNodesScan (rows: 10000)     │
│ AllNodesScan (rows: 1000)      │
└────────────────────────────────┘

Recommendation:
Use explicit relationship or better join pattern

Optimized:
MATCH (a:Person)-[:WORKS_AT]->(b:Company) RETURN a, b
OR
MATCH (a:Person), (b:Company {id: a.company_id}) RETURN a, b
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-07
**Author**: Neo4j YASS MCP Team
