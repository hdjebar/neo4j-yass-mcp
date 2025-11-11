# Query Plan Analysis Tool Implementation Plan

## Architecture Design

Based on my analysis of the codebase, here's the comprehensive implementation plan for the query plan analysis tool:

### **1. Core Architecture**

```python
# New file: src/neo4j_yass_mcp/tools/query_analyzer.py

class QueryPlanAnalyzer:
    """Analyzes Neo4j query execution plans and provides optimization recommendations."""
    
    def __init__(self, graph: SecureNeo4jGraph):
        self.graph = graph
        self.bottleneck_detector = BottleneckDetector()
        self.recommendation_engine = RecommendationEngine()
        self.cost_estimator = QueryCostEstimator()
    
    async def analyze_query(
        self, 
        query: str, 
        mode: str = "profile",
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """Main analysis entry point."""
```

### **2. Integration Points**

**Server Integration** (`server.py:654`):
- Add new MCP tool: `analyze_query_performance()`
- Follow existing pattern with security wrappers
- Integrate with current audit logging system
- Use existing rate limiting infrastructure

**Security Integration**:
- Leverage existing `SecureNeo4jGraph` for query execution
- Use current sanitizer and complexity limiter
- Add new security checks for analysis queries

### **3. Implementation Phases**

## Phase 1: Core Infrastructure (Week 1)

### **New Files to Create:**

1. **`src/neo4j_yass_mcp/tools/query_analyzer.py`**
   - Main analyzer class
   - Neo4j EXPLAIN/PROFILE integration
   - Result parsing and normalization

2. **`src/neo4j_yass_mcp/tools/bottleneck_detector.py`**
   - Performance bottleneck identification
   - Cartesian product detection
   - Missing index analysis
   - Pattern recognition algorithms

3. **`src/neo4j_yass_mcp/tools/recommendation_engine.py`**
   - Optimization suggestion generation
   - Rule-based recommendation system
   - Severity scoring

### **Key Implementation Details:**

```python
# Query execution with EXPLAIN/PROFILE
async def _execute_explain(self, query: str) -> Dict[str, Any]:
    """Execute EXPLAIN to get execution plan without running query."""
    explain_query = f"EXPLAIN {query}"
    return await self._execute_cypher_safe(explain_query)

async def _execute_profile(self, query: str) -> Dict[str, Any]:
    """Execute PROFILE to get execution plan with runtime statistics."""
    profile_query = f"PROFILE {query}"
    return await self._execute_cypher_safe(profile_query)
```

## Phase 2: Analysis Engine (Week 2)

### **Bottleneck Detection Algorithms:**

```python
class BottleneckDetector:
    """Detects performance bottlenecks in query execution plans."""
    
    def detect_cartesian_products(self, plan: Dict) -> List[Dict]:
        """Detect Cartesian products in execution plan."""
        # Look for nested loop joins without proper relationship constraints
        
    def detect_missing_indexes(self, plan: Dict, schema: Dict) -> List[Dict]:
        """Identify queries that would benefit from indexes."""
        # Analyze node scans vs index seeks
        
    def detect_expensive_operations(self, plan: Dict) -> List[Dict]:
        """Identify expensive operations like unbounded expansions."""
        # Check for [*], [*1..1000] patterns
```

### **Cost Estimation:**

```python
class QueryCostEstimator:
    """Estimates query execution cost and resource usage."""
    
    def estimate_execution_cost(self, query: str, plan: Dict) -> Dict[str, Any]:
        """Estimate CPU, memory, and I/O costs."""
        
    def predict_execution_time(self, plan: Dict) -> Dict[str, Any]:
        """Predict execution time based on plan complexity."""
```

## Phase 3: Recommendation Engine (Week 3)

### **Optimization Rules:**

```python
class RecommendationEngine:
    """Generates optimization recommendations based on analysis."""
    
    def generate_recommendations(
        self, 
        query: str, 
        plan: Dict, 
        bottlenecks: List[Dict]
    ) -> List[Dict]:
        """Generate prioritized optimization recommendations."""
        
    def score_recommendation_severity(
        self, 
        recommendation: Dict, 
        query_complexity: int
    ) -> int:
        """Score recommendation severity (1-10 scale)."""
```

### **Recommendation Categories:**

1. **Index Recommendations**
   - Missing index suggestions
   - Composite index optimization
   - Index selectivity analysis

2. **Query Structure Recommendations**
   - Relationship direction optimization
   - Pattern simplification
   - LIMIT clause suggestions

3. **Schema Recommendations**
   - Node label optimization
   - Relationship type consolidation

## Server Integration

### **MCP Tool Registration:**

```python
# In server.py, add to register_mcp_components()
ANALYZE_QUERY_RATE_LIMIT = int(os.getenv("MCP_ANALYZE_QUERY_LIMIT", "15"))
ANALYZE_QUERY_RATE_WINDOW = int(os.getenv("MCP_ANALYZE_QUERY_WINDOW", "60"))

mcp.tool()(
    log_tool_invocation("analyze_query_performance")(
        rate_limit_tool(
            limiter=lambda: tool_rate_limiter,
            client_id_extractor=get_client_id_from_context,
            limit=ANALYZE_QUERY_RATE_LIMIT,
            window=ANALYZE_QUERY_RATE_WINDOW,
            enabled=lambda: tool_rate_limit_enabled,
            tool_name="analyze_query_performance",
            build_error_response=_build_analyze_query_rate_limit_error,
        )(analyze_query_performance)
    )
)
```

### **Security Integration:**

```python
async def analyze_query_performance(
    query: str,
    mode: str = "profile",
    include_recommendations: bool = True,
    ctx: Context | None = None
) -> Dict[str, Any]:
    """Analyze query performance and provide optimization insights."""
    
    # Security checks via SecureNeo4jGraph
    # Audit logging
    # Rate limiting (already applied via decorator)
    
    if graph is None:
        return {"error": "Neo4j graph not initialized", "success": False}
    
    try:
        analyzer = QueryPlanAnalyzer(graph)
        result = await analyzer.analyze_query(
            query=query,
            mode=mode,
            include_recommendations=include_recommendations
        )
        return result
        
    except Exception as e:
        # Error handling with sanitization
        return {"error": sanitize_error_message(e), "success": False}
```

## Testing Strategy

### **Test Coverage Plan:**

1. **Unit Tests** (`tests/unit/test_query_analyzer.py`)
   - Bottleneck detection algorithms
   - Recommendation engine logic
   - Cost estimation accuracy

2. **Integration Tests** (`tests/integration/test_query_analyzer.py`)
   - End-to-end analysis workflow
   - Real Neo4j query plans
   - Security integration

3. **Performance Tests**
   - Analysis speed benchmarks
   - Memory usage validation
   - Concurrent analysis handling

## Implementation Timeline

### **Week 1: Foundation**
- [ ] Create core analyzer classes
- [ ] Implement Neo4j EXPLAIN/PROFILE integration
- [ ] Add basic result parsing

### **Week 2: Analysis Engine**
- [ ] Implement bottleneck detection algorithms
- [ ] Add cost estimation logic
- [ ] Create comprehensive test suite

### **Week 3: Integration & Polish**
- [ ] Integrate with server.py
- [ ] Add security wrappers
- [ ] Performance optimization
- [ ] Documentation and examples

## Success Metrics

### **Performance Targets:**
- Analysis completion: <5 seconds for typical queries
- Memory usage: <100MB for complex queries
- Zero false positives for bottleneck detection

### **User Experience:**
- Clear, actionable recommendations
- Severity scoring (1-10 scale)
- Multiple output formats (text, JSON)

## Risk Mitigation

### **Security Considerations:**
- All analysis queries run through existing security layer
- No direct user input execution
- Audit logging for all analysis requests

### **Performance Considerations:**
- Analysis runs in separate thread pool
- Configurable timeouts
- Resource usage monitoring

---

**Next Steps:**
1. Review and approve the architecture design
2. Begin Phase 1 implementation
3. Set up development branch
4. Create detailed task breakdown for each week

**Estimated Timeline:** 3 weeks (15 working days)
**Priority:** Highest ROI feature - immediate user value with zero dependencies