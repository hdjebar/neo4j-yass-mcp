# Query Plan Analysis Tool - User Guide

## Overview

The Query Plan Analysis Tool is a powerful feature of Neo4j YASS MCP that analyzes Cypher query performance and provides actionable optimization recommendations. It leverages Neo4j's built-in EXPLAIN and PROFILE capabilities to identify performance bottlenecks and suggest improvements.

## Features

- **Execution Plan Analysis**: Detailed analysis of query execution plans
- **Performance Bottleneck Detection**: Identifies common performance issues
- **Optimization Recommendations**: Actionable suggestions with severity scoring
- **Cost Estimation**: Predicts resource usage and execution time
- **Risk Assessment**: Evaluates query risk level before execution
- **Multiple Output Formats**: Text and JSON formats for different use cases

## Quick Start

### Basic Usage

```python
# Analyze a simple query
result = await analyze_query_performance(
    query="MATCH (n:Person) RETURN n.name",
    mode="explain"
)

print(f"Analysis Summary: {result['analysis_summary']}")
print(f"Bottlenecks Found: {result['bottlenecks_found']}")
print(f"Recommendations: {result['recommendations_count']}")
```

### Detailed Analysis with Recommendations

```python
# Get detailed analysis with optimization recommendations
result = await analyze_query_performance(
    query="""
    MATCH (user:Person)-[:FRIENDS_WITH]-(friend)-[:FRIENDS_WITH]-(fof)
    WHERE user.name = 'Alice' AND NOT (user)-[:FRIENDS_WITH]-(fof)
    RETURN fof.name, count(*) as mutual_friends
    ORDER BY mutual_friends DESC LIMIT 10
    """,
    mode="profile",
    include_recommendations=True
)

# Print the formatted analysis report
print(result['analysis_report'])
```

## Analysis Modes

### EXPLAIN Mode
- **Purpose**: Quick plan analysis without executing the query
- **Speed**: Fast (typically < 100ms)
- **Use Case**: Initial query validation and basic bottleneck detection
- **Output**: Execution plan structure and estimated costs

```python
result = await analyze_query_performance(
    query="MATCH (n:Person) RETURN n",
    mode="explain"
)
```

### PROFILE Mode
- **Purpose**: Detailed analysis with runtime statistics
- **Speed**: Slower (executes the query)
- **Use Case**: In-depth performance analysis with actual metrics
- **Output**: Execution plan + runtime statistics (rows, time, db hits)

```python
result = await analyze_query_performance(
    query="MATCH (n:Person) RETURN n",
    mode="profile"
)
```

## Understanding Results

### Analysis Summary

```json
{
  "analysis_summary": {
    "overall_severity": 7,
    "bottleneck_count": 3,
    "recommendation_count": 4,
    "critical_issues": 1,
    "estimated_impact": "high",
    "estimated_cost": 8500
  }
}
```

**Severity Scale (1-10):**
- 1-3: Low impact, minor optimizations
- 4-6: Medium impact, noticeable performance improvement
- 7-10: High impact, significant performance improvement

### Bottleneck Types

1. **Cartesian Products** (Severity: 9/10)
   - Multiple patterns in MATCH without relationships
   - Can cause exponential row growth

2. **Missing Indexes** (Severity: 8/10)
   - Node scans instead of index seeks
   - Significant performance impact on large datasets

3. **Unbounded Patterns** (Severity: 7/10)
   - `[*]` patterns without bounds
   - Can explore entire graph

4. **Missing LIMIT Clauses** (Severity: 4/10)
   - Unbounded result sets
   - Memory and performance impact

### Recommendation Format

```json
{
  "recommendations": [
    {
      "title": "Create index on frequently queried property",
      "description": "Add an index to speed up node lookups by property",
      "priority": "high",
      "severity": 8,
      "effort": "low",
      "impact": "high",
      "example": "CREATE INDEX person_name FOR (p:Person) ON (p.name)",
      "implementation": "1. Analyze property selectivity 2. Create index 3. Test performance"
    }
  ]
}
```

## Common Use Cases

### 1. Query Performance Tuning

**Problem**: Slow query execution
**Solution**: Use PROFILE mode to identify bottlenecks

```python
# Analyze slow query
slow_query = """
MATCH (user:Person)-[:FRIENDS_WITH*1..5]-(friend:Person)
WHERE user.name = 'Alice'
RETURN friend.name, friend.age
"""

result = await analyze_query_performance(
    query=slow_query,
    mode="profile"
)

# Implement recommendations
for rec in result['detailed_analysis']['recommendations']:
    if rec['priority'] == 'high':
        print(f"High Priority: {rec['title']}")
        print(f"Implementation: {rec['example']}")
```

### 2. Schema Optimization

**Problem**: Frequent full table scans
**Solution**: Identify missing indexes

```python
# Check for missing indexes
result = await analyze_query_performance(
    query="MATCH (n:Product) WHERE n.category = 'Electronics' RETURN n",
    mode="explain"
)

# Look for missing index recommendations
for rec in result['detailed_analysis']['recommendations']:
    if 'index' in rec['title'].lower():
        print(f"Index Recommendation: {rec['example']}")
```

### 3. Query Validation

**Problem**: Prevent expensive queries in production
**Solution**: Risk assessment before execution

```python
# Validate query before execution
result = await analyze_query_performance(
    query=user_submitted_query,
    mode="explain"
)

# Check risk level
if result['risk_level'] == 'high':
    print("Warning: High risk query detected")
    print("Consider adding LIMIT or optimizing the query")
    # Optionally block execution or require approval
```

### 4. Performance Monitoring

**Problem**: Track query performance over time
**Solution**: Regular analysis and comparison

```python
# Analyze query performance regularly
results = []
for query in important_queries:
    result = await analyze_query_performance(
        query=query,
        mode="profile"
    )
    results.append({
        'query': query,
        'cost_score': result['cost_score'],
        'execution_time': result['execution_time_ms'],
        'bottlenecks': result['bottlenecks_found']
    })

# Track performance trends
for result in results:
    if result['cost_score'] > 7:
        print(f"High cost query detected: {result['query'][:50]}...")
```

## Best Practices

### 1. Choose the Right Mode

- **EXPLAIN**: Use for quick validation and basic analysis
- **PROFILE**: Use for detailed performance tuning
- **Development**: Start with EXPLAIN, use PROFILE for optimization

### 2. Interpret Results Correctly

- **Severity 7+**: Address immediately
- **Severity 4-6**: Plan for optimization
- **Severity 1-3**: Nice to have improvements

### 3. Implement Recommendations Safely

```python
# Test recommendations in development first
dev_result = await analyze_query_performance(query=query, mode="profile")

# Apply recommendations incrementally
for rec in dev_result['recommendations']:
    if rec['effort'] == 'low' and rec['impact'] == 'high':
        # Implement this recommendation first
        print(f"Quick win: {rec['example']}")
```

### 4. Monitor After Changes

```python
# Before optimization
before_result = await analyze_query_performance(query=query, mode="profile")

# Apply optimization (e.g., create index)
# ... create index code ...

# After optimization
after_result = await analyze_query_performance(query=query, mode="profile")

# Compare results
print(f"Cost improvement: {before_result['cost_score']} -> {after_result['cost_score']}")
print(f"Time improvement: {before_result['execution_time_ms']} -> {after_result['execution_time_ms']}")
```

## Advanced Usage

### Custom Analysis Parameters

```python
# Focus on specific bottleneck types
result = await analyze_query_performance(
    query=complex_query,
    mode="profile",
    include_recommendations=True
)

# Filter recommendations by category
index_recommendations = [
    rec for rec in result['recommendations'] 
    if rec['category'] == 'indexing'
]

# Focus on high-impact recommendations
high_impact = [
    rec for rec in result['recommendations'] 
    if rec['impact'] == 'high' and rec['priority'] == 'high'
]
```

### Batch Analysis

```python
# Analyze multiple queries
queries = [
    "MATCH (n:Person) RETURN n",
    "MATCH (n:Movie) RETURN n.title",
    "MATCH (n:Person)-[:ACTED_IN]->(m:Movie) RETURN n.name, m.title"
]

results = []
for query in queries:
    result = await analyze_query_performance(
        query=query,
        mode="explain"  # Use EXPLAIN for batch analysis (faster)
    )
    results.append(result)

# Find the most expensive queries
expensive_queries = sorted(
    results, 
    key=lambda x: x['cost_score'], 
    reverse=True
)

for result in expensive_queries[:3]:
    print(f"High cost query: {result['query'][:50]}... (score: {result['cost_score']})")
```

### Integration with Monitoring

```python
# Log analysis results for monitoring
import logging

logger = logging.getLogger("query_analysis")

async def monitor_query_performance(query: str):
    result = await analyze_query_performance(query=query, mode="profile")
    
    logger.info(
        f"Query Analysis - Score: {result['cost_score']}, "
        f"Risk: {result['risk_level']}, "
        f"Bottlenecks: {result['bottlenecks_found']}, "
        f"Time: {result['execution_time_ms']}ms"
    )
    
    # Alert on high-risk queries
    if result['risk_level'] == 'high':
        logger.warning(f"High risk query detected: {query[:100]}...")
```

## Troubleshooting

### Common Issues

1. **"Query analysis failed" errors**
   - Check query syntax
   - Verify Neo4j connection
   - Check security settings

2. **No bottlenecks detected**
   - Query might already be optimized
   - Try PROFILE mode for more detailed analysis
   - Check if query is too simple

3. **High cost scores without clear bottlenecks**
   - Check for expensive procedures
   - Look for complex patterns
   - Consider data volume impact

### Performance Issues

1. **Slow analysis**
   - Use EXPLAIN mode for faster analysis
   - Limit concurrent analyses
   - Check Neo4j server performance

2. **Memory usage**
   - Analysis runs in separate thread pool
   - Large execution plans can use memory
   - Consider limiting analysis frequency

## API Reference

### analyze_query_performance()

```python
async def analyze_query_performance(
    query: str,
    mode: str = "profile",
    include_recommendations: bool = True,
    ctx: Context | None = None
) -> dict[str, Any]
```

**Parameters:**
- `query` (str): Cypher query to analyze
- `mode` (str): Analysis mode - "explain" or "profile" (default: "profile")
- `include_recommendations` (bool): Whether to include optimization recommendations (default: True)
- `ctx` (Context | None): FastMCP context for rate limiting (auto-injected)

**Returns:**
Dictionary containing analysis results with keys:
- `success`: Boolean indicating success/failure
- `query`: Original query string
- `mode`: Analysis mode used
- `analysis_summary`: High-level summary of findings
- `bottlenecks_found`: Number of detected bottlenecks
- `recommendations_count`: Number of recommendations
- `cost_score`: Overall cost score (1-10)
- `risk_level`: Risk assessment (low/medium/high)
- `execution_time_ms`: Analysis execution time
- `detailed_analysis`: Complete analysis results
- `analysis_report`: Formatted text report

### QueryPlanAnalyzer Class

```python
from neo4j_yass_mcp.tools import QueryPlanAnalyzer

analyzer = QueryPlanAnalyzer(graph)
result = await analyzer.analyze_query(query, mode="profile")
report = analyzer.format_analysis_report(result, format_type="text")
```

## Examples Repository

### Example 1: Social Network Analysis

```python
# Friend recommendation query analysis
query = """
MATCH (user:Person {name: 'Alice'})-[:FRIENDS_WITH]-(friend)-[:FRIENDS_WITH]-(fof)
WHERE NOT (user)-[:FRIENDS_WITH]-(fof) AND user <> fof
WITH fof, count(*) as mutual_friends
WHERE mutual_friends >= 2
RETURN fof.name, mutual_friends
ORDER BY mutual_friends DESC LIMIT 10
"""

result = await analyze_query_performance(query=query, mode="profile")
print(result['analysis_report'])
```

### Example 2: E-commerce Recommendation

```python
# Product recommendation query analysis
query = """
MATCH (user:User)-[:PURCHASED]->(product:Product)<-[:PURCHASED]-(similar:User)
WHERE similar <> user
WITH similar, collect(product) as purchased_products
MATCH (similar)-[:PURCHASED]->(recommended:Product)
WHERE NOT recommended IN purchased_products
RETURN recommended.name, count(*) as purchase_count
ORDER BY purchase_count DESC LIMIT 20
"""

result = await analyze_query_performance(query=query, mode="explain")
print(f"Risk Level: {result['risk_level']}")
print(f"Cost Score: {result['cost_score']}")
```

### Example 3: Knowledge Graph Query

```python
# Entity relationship analysis
query = """
MATCH (entity1:Entity)-[r:RELATED_TO]->(entity2:Entity)
WHERE r.confidence > 0.8
WITH entity1, entity2, r
MATCH (entity2)-[r2:RELATED_TO]->(entity3:Entity)
WHERE r2.confidence > 0.8 AND entity3 <> entity1
RETURN entity1.name, entity2.name, entity3.name, r.confidence, r2.confidence
LIMIT 100
"""

result = await analyze_query_performance(query=query, mode="profile")
for rec in result['detailed_analysis']['recommendations']:
    if rec['priority'] == 'high':
        print(f"High Priority: {rec['title']}")
        print(f"Example: {rec['example']}")
```

## Conclusion

The Query Plan Analysis Tool provides comprehensive performance analysis for Neo4j queries. By following this guide and using the tool regularly, you can:

- Identify performance bottlenecks before they impact production
- Get actionable optimization recommendations
- Understand query execution costs and risks
- Improve overall application performance
- Make data-driven optimization decisions

Start with basic EXPLAIN analysis for quick validation, then use PROFILE mode for detailed performance tuning. Always test optimizations in development before applying to production.