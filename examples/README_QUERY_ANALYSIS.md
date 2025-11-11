# Query Analysis Tool Examples

This directory contains practical examples demonstrating how to use the Neo4j Query Analysis Tool for various use cases.

## Files

- **`query_analysis_examples.py`** - Comprehensive examples covering:
  - Basic query analysis
  - Performance optimization workflow
  - Schema optimization recommendations
  - Production query validation
  - Batch analysis of multiple queries
  - Monitoring and alerting setup

## Quick Start

```bash
# Run all examples
python query_analysis_examples.py

# The examples will use mock data if Neo4j is not configured
# Set NEO4J_URI environment variable to analyze real queries
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
```

## Example Use Cases

### 1. Basic Analysis
Learn how to analyze a simple query and interpret the results.

### 2. Performance Optimization
See how to identify and fix performance bottlenecks in complex queries.

### 3. Schema Optimization
Discover missing indexes and schema improvements.

### 4. Production Validation
Validate user queries before deploying to production.

### 5. Batch Analysis
Analyze multiple queries efficiently for performance comparison.

### 6. Monitoring Setup
Set up automated monitoring and alerting for critical queries.

## Integration Examples

### Basic Integration
```python
from neo4j_yass_mcp.server import analyze_query_performance

# Analyze a query
result = await analyze_query_performance(
    query="MATCH (n:Person) RETURN n.name",
    mode="explain"
)

print(f"Cost Score: {result['cost_score']}")
print(f"Risk Level: {result['risk_level']}")
```

### Production Validation
```python
# Validate before deployment
validation = await analyze_query_performance(
    query=user_query,
    mode="explain"
)

if validation['cost_score'] > 7:
    raise Exception("Query too expensive for production")
```

### Performance Monitoring
```python
# Monitor critical queries
for query in critical_queries:
    result = await analyze_query_performance(query, mode="explain")
    if result['risk_level'] == 'high':
        send_alert(f"High risk query detected: {query}")
```

## Best Practices

1. **Start with EXPLAIN**: Use EXPLAIN mode for quick validation
2. **Use PROFILE for optimization**: Get detailed stats for tuning
3. **Focus on severity 7+**: Address high-impact issues first
4. **Test incrementally**: Apply one optimization at a time
5. **Monitor changes**: Compare before/after performance

## Common Patterns

### Quick Health Check
```python
async def health_check(query: str) -> bool:
    result = await analyze_query_performance(query, mode="explain")
    return result['risk_level'] != 'high' and result['cost_score'] <= 5
```

### Optimization Pipeline
```python
async def optimize_query(query: str) -> str:
    # Analyze current query
    result = await analyze_query_performance(query, mode="profile")
    
    # Get high-priority recommendations
    recommendations = [
        rec for rec in result['recommendations']
        if rec['priority'] == 'high' and rec['effort'] == 'low'
    ]
    
    # Apply recommendations (simplified example)
    optimized_query = query
    for rec in recommendations:
        if 'index' in rec['title'].lower():
            # Log index recommendation
            print(f"Create index: {rec['example']}")
        else:
            # Apply query structure changes
            optimized_query = apply_recommendation(optimized_query, rec)
    
    return optimized_query
```

### Batch Performance Audit
```python
async def audit_queries(queries: List[str]) -> Dict[str, Any]:
    results = []
    for query in queries:
        result = await analyze_query_performance(query, mode="explain")
        results.append({
            'query': query,
            'cost_score': result['cost_score'],
            'risk_level': result['risk_level'],
            'bottlenecks': result['bottlenecks_found']
        })
    
    # Sort by cost score
    results.sort(key=lambda x: x['cost_score'], reverse=True)
    return results
```

## Environment Setup

### Required Environment Variables
```bash
# Neo4j connection (optional for examples)
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j" 
export NEO4J_PASSWORD="password"

# Analysis tool settings
export MCP_ANALYZE_QUERY_LIMIT=15  # Rate limit: 15 requests per minute
export MCP_ANALYZE_QUERY_WINDOW=60
```

### Optional Settings
```bash
# Security settings
export ANALYZE_QUERY_ENABLED=true
export ANALYZE_QUERY_TIMEOUT=30

# Logging
export LOG_LEVEL=INFO
```

## Next Steps

1. **Run the examples**: `python query_analysis_examples.py`
2. **Try your queries**: Modify the examples with your own queries
3. **Integrate into your app**: Use the patterns in your application
4. **Set up monitoring**: Implement automated query validation
5. **Read the full guide**: Check out the comprehensive user guide

## Support

- **User Guide**: `QUERY_ANALYSIS_USER_GUIDE.md` for detailed documentation
- **Quick Reference**: `QUERY_ANALYSIS_QUICK_REFERENCE.md` for quick lookup
- **Implementation Plan**: `QUERY_PLAN_ANALYSIS_IMPLEMENTATION_PLAN.md` for technical details
- **GitHub Issues**: Report problems or request features

---

*Happy query optimization! 🚀*