# Query Plan Analysis Tool - Quick Reference Card

## 🚀 Quick Start

```python
# Basic analysis
result = await analyze_query_performance(
    query="MATCH (n:Person) RETURN n.name",
    mode="explain"  # or "profile"
)

# Key metrics
print(f"Severity: {result['analysis_summary']['overall_severity']}/10")
print(f"Bottlenecks: {result['bottlenecks_found']}")
print(f"Recommendations: {result['recommendations_count']}")
print(f"Risk: {result['risk_level']}")
```

## 📊 Severity Scale

| Score | Impact | Action Required |
|-------|--------|-----------------|
| 1-3   | Low    | Optional optimization |
| 4-6   | Medium | Plan for optimization |
| 7-10  | High   | **Address immediately** |

## 🔍 Analysis Modes

### EXPLAIN Mode
```python
# Fast analysis (no execution)
result = await analyze_query_performance(
    query=your_query,
    mode="explain"
)
```
- ✅ **Fast** (< 100ms)
- ✅ **Safe** (no query execution)
- ❌ **Basic** (no runtime stats)

### PROFILE Mode
```python
# Detailed analysis (with execution)
result = await analyze_query_performance(
    query=your_query,
    mode="profile"
)
```
- ✅ **Detailed** (with runtime stats)
- ✅ **Accurate** (real measurements)
- ❌ **Slower** (executes query)

## 🎯 Common Bottlenecks

| Type | Severity | Quick Fix |
|------|----------|-----------|
| **Cartesian Product** | 9/10 | Add relationship constraints |
| **Missing Index** | 8/10 | `CREATE INDEX` on property |
| **Unbounded Pattern** | 7/10 | Add bounds `[*1..4]` |
| **No LIMIT** | 4/10 | Add `LIMIT` clause |

## 🛠️ Quick Fixes

### 1. Cartesian Product
```cypher
❌ MATCH (a), (b), (c) RETURN a, b, c
✅ MATCH (a) WITH a MATCH (b) WITH a, b MATCH (c) RETURN a, b, c
```

### 2. Missing Index
```cypher
✅ CREATE INDEX person_name FOR (p:Person) ON (p.name)
```

### 3. Unbounded Pattern
```cypher
❌ MATCH (a)-[*]->(b) RETURN a, b
✅ MATCH (a)-[*1..4]->(b) RETURN a, b
✅ MATCH shortestPath((a)-[*]->(b)) RETURN a, b
```

### 4. Add LIMIT
```cypher
❌ MATCH (n:Person) RETURN n
✅ MATCH (n:Person) RETURN n LIMIT 100
```

## 📈 Risk Assessment

| Risk Level | Meaning | Action |
|------------|---------|--------|
| **Low** | Safe to execute | Proceed normally |
| **Medium** | Monitor performance | Add LIMIT if needed |
| **High** | **Dangerous** | Review before execution |

## 🎛️ Configuration

### Environment Variables
```bash
# Rate limiting (requests per minute)
MCP_ANALYZE_QUERY_LIMIT=15
MCP_ANALYZE_QUERY_WINDOW=60
```

### Security Settings
```bash
# Enable/disable analysis tool
ANALYZE_QUERY_ENABLED=true

# Maximum analysis time (seconds)
ANALYZE_QUERY_TIMEOUT=30
```

## 🧪 Testing Your Queries

### Development Workflow
```python
# 1. Quick check with EXPLAIN
quick_check = await analyze_query_performance(query, mode="explain")
if quick_check['risk_level'] == 'high':
    # 2. Detailed analysis with PROFILE
    detailed = await analyze_query_performance(query, mode="profile")
    # 3. Implement high-priority recommendations
    for rec in detailed['recommendations']:
        if rec['priority'] == 'high':
            print(f"Fix: {rec['example']}")
```

### Production Validation
```python
# Before deploying new queries
validation = await analyze_query_performance(
    query=new_query,
    mode="explain"
)

if validation['cost_score'] > 7:
    raise Exception("Query too expensive for production")
```

## 📋 Checklist

### Before Analysis
- [ ] Query syntax is correct
- [ ] Neo4j connection is working
- [ ] Security settings allow analysis

### During Analysis
- [ ] Choose appropriate mode (EXPLAIN vs PROFILE)
- [ ] Check overall severity score
- [ ] Identify critical issues (severity ≥ 8)
- [ ] Review risk level assessment

### After Analysis
- [ ] Implement high-priority recommendations
- [ ] Test optimizations in development
- [ ] Monitor performance improvements
- [ ] Document changes made

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| "Query analysis failed" | Check query syntax and Neo4j connection |
| No bottlenecks found | Query might already be optimized |
| High cost, no clear issues | Check for expensive procedures |
| Slow analysis | Use EXPLAIN mode for faster results |

## 🔗 Related Tools

- **Complexity Limiter**: Prevents expensive queries
- **Rate Limiter**: Controls analysis frequency
- **Audit Logger**: Tracks analysis history
- **Schema Analyzer**: Database structure insights

## 💡 Pro Tips

1. **Start with EXPLAIN**: Always use EXPLAIN first for quick validation
2. **Focus on severity 7+**: Address high-severity issues first
3. **Test incrementally**: Apply one optimization at a time
4. **Monitor changes**: Compare before/after performance
5. **Use in CI/CD**: Automate query validation in deployment

## 📚 Quick Commands

```bash
# Run analysis on sample query
python -c "
import asyncio
from neo4j_yass_mcp.server import analyze_query_performance
async def test():
    result = await analyze_query_performance('MATCH (n) RETURN n LIMIT 10', 'explain')
    print(f'Severity: {result[\"analysis_summary\"][\"overall_severity\"]}')
asyncio.run(test())
"
```

## 🎯 Next Steps

1. **Try it now**: Analyze your first query
2. **Read the guide**: Full user guide for detailed usage
3. **Check examples**: Real-world query analysis examples
4. **Join community**: Share your optimization success stories

---
*Keep this card handy for quick reference during query optimization!*