# Query Plan Analysis Tool - Production Guide

## Deployment Overview

The Query Plan Analysis Tool is production-ready and deployed as part of the Neo4j YASS MCP server. This guide covers deployment strategies, configuration, monitoring, and operational best practices.

## Prerequisites

### System Requirements
- **Python**: 3.11+ (tested up to 3.12)
- **Neo4j**: 4.4+ (Aura, Enterprise, or Community)
- **Memory**: 2GB+ available RAM
- **CPU**: 2+ cores recommended
- **Network**: Low-latency connection to Neo4j (<100ms)

### Dependencies
```bash
# Core dependencies (already in pyproject.toml)
neo4j>=5.15.0
pydantic>=2.0.0
fastapi>=0.104.0
mcp>=1.0.0
```

## Deployment Options

### 1. Docker Deployment (Recommended)

#### Production Dockerfile
```dockerfile
FROM python:3.12-slim

# Security: Create non-root user
RUN groupadd -r mcp && useradd -r -g mcp mcp

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv pip install --system -e .

# Copy application code
COPY . .

# Security: Set ownership and permissions
RUN chown -R mcp:mcp /app
USER mcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from src.neo4j_yass_mcp.server import health_check; asyncio.run(health_check())"

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "-m", "src.neo4j_yass_mcp.server"]
```

#### Docker Compose Production
```yaml
version: '3.8'

services:
  neo4j-yass-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      # Neo4j Connection
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      
      # Rate Limiting
      - MCP_ANALYZE_QUERY_LIMIT=30
      - MCP_ANALYZE_QUERY_WINDOW=60
      
      # Performance
      - MCP_ANALYZE_TIMEOUT=30
      - MCP_ANALYZE_MAX_MEMORY=500
      
      # Security
      - SANITIZE_ERRORS=true
      - ENABLE_AUDIT_LOGGING=true
      
      # Monitoring
      - ENABLE_METRICS=true
      - METRICS_PORT=9090
    
    # Resource limits
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
    
    # Health checks
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    # Restart policy
    restart: unless-stopped
    
    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Optional: Neo4j for testing
  neo4j:
    image: neo4j:5.15-enterprise
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

### 2. Kubernetes Deployment

#### Deployment Manifest
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neo4j-yass-mcp
  labels:
    app: neo4j-yass-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: neo4j-yass-mcp
  template:
    metadata:
      labels:
        app: neo4j-yass-mcp
    spec:
      containers:
      - name: neo4j-yass-mcp
        image: your-registry/neo4j-yass-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEO4J_URI
          valueFrom:
            secretKeyRef:
              name: neo4j-credentials
              key: uri
        - name: NEO4J_USER
          valueFrom:
            secretKeyRef:
              name: neo4j-credentials
              key: user
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: neo4j-credentials
              key: password
        - name: MCP_ANALYZE_QUERY_LIMIT
          value: "30"
        - name: MCP_ANALYZE_TIMEOUT
          value: "30"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: neo4j-yass-mcp-service
spec:
  selector:
    app: neo4j-yass-mcp
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Configuration

### Environment Variables

#### Core Settings
```bash
# Neo4j Connection (Required)
NEO4J_URI=bolt://your-neo4j-instance:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password

# Analysis Tool Settings
MCP_ANALYZE_QUERY_LIMIT=30        # requests per window (default: 15)
MCP_ANALYZE_QUERY_WINDOW=60         # window in seconds (default: 60)
MCP_ANALYZE_TIMEOUT=30            # analysis timeout (default: 30)
MCP_ANALYZE_MAX_MEMORY=500          # memory limit in MB (default: 500)
```

#### Security Settings
```bash
# Error Handling
SANITIZE_ERRORS=true              # sanitize error messages (default: true)
ENABLE_AUDIT_LOGGING=true         # enable audit logging (default: true)

# Rate Limiting
RATE_LIMIT_ENABLED=true           # enable rate limiting (default: true)
RATE_LIMIT_STORAGE_URL=redis://redis:6379  # optional Redis backend
```

#### Performance Settings
```bash
# Connection Pooling
NEO4J_MAX_CONNECTION_LIFETIME=3600
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_ACQUISITION_TIMEOUT=60

# Analysis Performance
MAX_PLAN_DEPTH=10                 # maximum plan tree depth
MAX_RECOMMENDATIONS=20            # max recommendations returned
MIN_SEVERITY_THRESHOLD=3          # minimum severity to report
```

### Production Checklist

#### Pre-Deployment
- [ ] Neo4j connection tested and validated
- [ ] Security credentials properly configured
- [ ] Rate limits appropriate for expected load
- [ ] Memory limits sufficient for analysis workload
- [ ] Health check endpoints configured
- [ ] Monitoring and alerting set up

#### Post-Deployment
- [ ] Health checks passing
- [ ] Analysis tool responding to requests
- [ ] Rate limiting working correctly
- [ ] Error handling and sanitization active
- [ ] Audit logs being generated
- [ ] Performance metrics collected

## Monitoring

### Key Metrics

#### Performance Metrics
```python
# Analysis duration
analysis_duration_seconds = Histogram(
    'mcp_analysis_duration_seconds',
    'Time spent analyzing queries',
    ['mode', 'complexity']
)

# Analysis results
analysis_results_total = Counter(
    'mcp_analysis_results_total',
    'Total analysis results by outcome',
    ['success', 'error_type']
)

# Memory usage
analysis_memory_bytes = Gauge(
    'mcp_analysis_memory_bytes',
    'Memory used during analysis',
    ['query_id']
)
```

#### Business Metrics
```python
# Bottlenecks detected
bottlenecks_detected_total = Counter(
    'mcp_bottlenecks_detected_total',
    'Total bottlenecks detected by type',
    ['bottleneck_type', 'severity']
)

# Recommendations generated
recommendations_generated_total = Counter(
    'mcp_recommendations_generated_total',
    'Total recommendations by type',
    ['recommendation_type', 'priority']
)
```

### Alerting Rules

#### Critical Alerts
```yaml
# High error rate
groups:
- name: mcp_critical
  rules:
  - alert: MCPHighErrorRate
    expr: rate(mcp_analysis_results_total{success="false"}[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High error rate in query analysis"
      description: "Error rate is {{ $value | humanizePercentage }}"

  - alert: MCPAnalysisTimeout
    expr: histogram_quantile(0.95, mcp_analysis_duration_seconds_bucket) > 25
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Analysis timeouts detected"
      description: "95th percentile analysis time is {{ $value }}s"
```

#### Warning Alerts
```yaml
# High memory usage
groups:
- name: mcp_warnings
  rules:
  - alert: MCPHighMemoryUsage
    expr: mcp_analysis_memory_bytes > 400000000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage in analysis"
      description: "Memory usage is {{ $value | humanize1024 }}B"

  - alert: MCPRateLimitingActive
    expr: rate(mcp_analysis_results_total{error_type="rate_limit_exceeded"}[5m]) > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Rate limiting is active"
      description: "Clients are being rate limited"
```

## Scaling

### Horizontal Scaling
- **Stateless Design**: Each instance is independent
- **Load Balancing**: Round-robin or least-connections
- **Session Affinity**: Not required
- **Auto-scaling**: Based on CPU/memory or request rate

### Vertical Scaling
- **CPU**: More cores improve concurrent analysis
- **Memory**: 2-4GB per instance recommended
- **Network**: Low-latency Neo4j connection critical

### Capacity Planning
```python
# Analysis capacity per instance
ANALYSES_PER_SECOND = 10  # Conservative estimate
MEMORY_PER_ANALYSIS = 100  # MB

# For 100 requests/second
INSTANCES_NEEDED = 100 / 10 = 10 instances
TOTAL_MEMORY = 10 * 2GB = 20GB
```

## Security

### Network Security
- **TLS**: Always use TLS for Neo4j connections
- **Network Policies**: Restrict ingress/egress in Kubernetes
- **Service Mesh**: Consider Istio/Linkerd for mTLS

### Access Control
- **Neo4j User**: Dedicated read-only user for analysis
- **RBAC**: Kubernetes RBAC for pod service accounts
- **Secrets**: Use Kubernetes secrets or external secret management

### Audit Logging
```json
{
  "timestamp": "2025-11-11T10:30:00Z",
  "level": "INFO",
  "event": "query_analysis",
  "user_id": "user123",
  "query_hash": "sha256:abc123...",
  "analysis_mode": "profile",
  "duration_ms": 1250,
  "bottlenecks_found": 2,
  "recommendations_generated": 3,
  "success": true
}
```

## Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
kubectl top pods -l app=neo4j-yass-mcp

# View logs
kubectl logs -f deployment/neo4j-yass-mcp

# Reduce memory limit
MCP_ANALYZE_MAX_MEMORY=250
```

#### Neo4j Connection Issues
```bash
# Test connection
python -c "from neo4j import GraphDatabase; GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'password')).verify_connectivity()"

# Check Neo4j logs
kubectl logs -f deployment/neo4j
```

#### Analysis Timeouts
```bash
# Increase timeout
MCP_ANALYZE_TIMEOUT=60

# Check for complex queries in logs
grep "analysis_timeout" /var/log/mcp.log
```

### Debug Mode
```bash
# Enable debug logging
LOG_LEVEL=DEBUG
DEBUG_ANALYSIS=true

# Get detailed analysis timing
DEBUG_PERFORMANCE=true
```

## Backup and Recovery

### Configuration Backup
- Store environment variables in version control (encrypted)
- Backup Kubernetes manifests and ConfigMaps
- Document custom configurations

### Disaster Recovery
- **RTO**: 5 minutes (pod restart)
- **RPO**: No data loss (stateless design)
- **Procedure**: Redeploy from container image

## Maintenance

### Regular Tasks
- **Weekly**: Review metrics and alerts
- **Monthly**: Update dependencies
- **Quarterly**: Performance optimization review

### Updates
- **Rolling Updates**: Zero-downtime deployments
- **Blue-Green**: For major version updates
- **Canary**: For testing new features

---

**Next Steps**:
- Review monitoring setup
- Configure alerting
- Test disaster recovery procedures
- Document operational runbooks

**Support**: For production issues, check logs and metrics first, then consult troubleshooting section.