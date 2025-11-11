# Query Plan Analysis Tool

The Query Plan Analysis Tool is a comprehensive Neo4j query performance analysis and optimization feature that provides real-time insights into query execution plans, bottlenecks, and optimization recommendations.

## Overview

This tool leverages Neo4j's EXPLAIN and PROFILE capabilities to analyze Cypher queries and provide actionable optimization recommendations. It helps developers and database administrators understand query performance characteristics before executing expensive operations.

## Key Features

### 🔍 **Execution Plan Analysis**
- **EXPLAIN Mode**: Fast analysis without query execution
- **PROFILE Mode**: Detailed analysis with runtime statistics
- **Multi-format Output**: Text and JSON report formats

### 🚨 **Bottleneck Detection**
- **Cartesian Products**: Identifies potentially expensive cross-products
- **Missing Indexes**: Detects opportunities for index optimization
- **Unbounded Patterns**: Flags variable-length patterns without limits
- **Expensive Operations**: Identifies costly procedures and operations

### 💡 **Smart Recommendations**
- **Priority-based**: Recommendations ranked by severity (1-10 scale)
- **Actionable**: Specific optimization suggestions with implementation guidance
- **Context-aware**: Tailored to your specific query patterns and schema

### 📊 **Cost Estimation**
- **Resource Usage**: Estimates CPU, memory, and I/O requirements
- **Risk Assessment**: Low/medium/high risk evaluation
- **Performance Scoring**: 1-10 cost scoring system
- **Confidence Levels**: Reliability indicators for estimates

## Quick Start

### Basic Usage

```python
# Analyze a simple query
result = await analyzer.analyze_query(
    "MATCH (n:Person)-[:FRIENDS_WITH]->(m:Person) RETURN n.name, m.name",
    mode="explain"
)

# Access results
print(f"Found {len(result['bottlenecks'])} bottlenecks")
print(f"Generated {len(result['recommendations'])} recommendations")
print(f"Risk level: {result['cost_estimate']['risk']}")
```

### Profile Mode for Detailed Analysis

```python
# Get detailed analysis with runtime statistics
result = await analyzer.analyze_query(
    "MATCH (n:Person) WHERE n.age > 25 RETURN n.name, n.city",
    mode="profile"
)

# Access detailed statistics
stats = result['execution_plan']['statistics']
print(f"Actual rows processed: {stats['rows']}")
print(f"Execution time: {stats['time_ms']}ms")
print(f"Database hits: {stats['db_hits']}")
```

### JSON Output for Integration

```python
# Get structured data for programmatic use
result = await analyzer.analyze_query(query, mode="explain")
json_report = analyzer.format_analysis_report(result, format_type="json")
```

## Analysis Modes

### EXPLAIN Mode (Recommended for Development)
- **Speed**: Fast analysis without query execution
- **Safety**: No impact on database performance
- **Use Case**: Development, query optimization, code reviews

### PROFILE Mode (For Production Analysis)
- **Detail**: Complete runtime statistics
- **Accuracy**: Real performance measurements
- **Use Case**: Production troubleshooting, performance tuning

## Bottleneck Detection Capabilities

| Bottleneck Type | Description | Severity Impact |
|----------------|-------------|-----------------|
| **Cartesian Products** | Multiple patterns without relationships | High (8-10) |
| **Missing Indexes** | Node/relationship property scans | Medium (5-7) |
| **Unbounded Patterns** | Variable-length paths without limits | High (7-9) |
| **Expensive Procedures** | Complex operations like apoc procedures | Medium (4-6) |
| **Missing Limits** | Large result sets without pagination | Low-Medium (3-5) |

## Recommendation Categories

### Index Optimization
- Create indexes on frequently queried properties
- Composite indexes for complex queries
- Full-text indexes for text searches

### Query Structure
- Break complex MATCH clauses into smaller parts
- Use relationship types to reduce search space
- Add appropriate LIMIT clauses

### Pattern Optimization
- Add bounds to variable-length patterns
- Use relationship direction when possible
- Optimize property filters

## Integration Examples

### With MCP Server
```python
# The tool is automatically available via the MCP server
# Use the analyze_query_performance tool in your MCP client
```

### Direct Usage
```python
from neo4j_yass_mcp.tools import QueryPlanAnalyzer

analyzer = QueryPlanAnalyzer(secure_graph)
result = await analyzer.analyze_query(your_query, mode="explain")
```

### With LangChain
```python
# Integrate with LangChain for automated optimization
# Use analysis results to guide query generation
```

## Best Practices

1. **Use EXPLAIN mode first** for initial analysis
2. **Review high-severity recommendations** (7-10) immediately
3. **Test optimizations** in development before production
4. **Monitor performance** after implementing recommendations
5. **Regular analysis** for evolving query patterns

## Security Considerations

- All queries are sanitized before analysis
- No direct query execution without security checks
- Analysis respects existing security policies
- No sensitive data exposure in reports

## Next Steps

- 📖 Read the [User Guide](USER_GUIDE.md) for detailed usage
- 🔍 Check the [Quick Reference](QUICK_REFERENCE.md) for command syntax
- 💻 Explore [Examples](EXAMPLES.md) for common use cases
- 🚀 See [Implementation Plan](../inprogress/QUERY_PLAN_ANALYSIS_IMPLEMENTATION_PLAN.md) for technical details

## Support

For questions or issues:
- Check the [troubleshooting guide](../../user-guides/TROUBLESHOOTING.md)
- Review [security documentation](../../architecture/SECURITY.md)
- Report issues on GitHub