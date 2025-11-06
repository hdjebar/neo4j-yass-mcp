# LLM-Powered Log Analysis & Anomaly Detection

**Status**: Proposed
**Priority**: Medium-High (Operational Excellence)
**Effort**: Medium (3-4 weeks)
**Dependencies**: None (optional: Prometheus, Grafana)

## Overview

Integrate LLM-powered analysis into the existing audit logging system to provide intelligent anomaly detection, pattern recognition, and automated alerting. This feature bridges traditional log viewers (lnav, multitail) with LLM capabilities for real-time and ad-hoc analysis.

## Value Proposition

- **Proactive Security**: Detect anomalous query patterns before they become incidents
- **Operational Insights**: Surface patterns humans might miss in large log volumes
- **Time Savings**: Automated analysis reduces manual log review time
- **Context-Aware Alerts**: LLM understands semantic meaning, not just regex patterns
- **Developer Experience**: Natural language queries about system behavior

## Use Cases

### 1. Real-Time Anomaly Detection

**Scenario**: Production system receives suspicious query patterns

```bash
# Traditional: Manual grep through logs
tail -f data/logs/audit/audit_*.jsonl | grep "BLOCKED"

# With LLM: Automated analysis with context
multitail data/logs/audit/audit_*.jsonl | \
  tee >(llm -m anthropic:claude-3-haiku \
    "Flag security anomalies in these Neo4j audit logs. \
     Focus on: repeated blocked queries, unusual access patterns, \
     injection attempts.")
```

**LLM Output**:
```
🚨 ANOMALY DETECTED (Severity: HIGH)
- IP 192.168.1.100 attempted 15 blocked queries in 2 minutes
- Pattern: Testing different injection vectors
- Recommendation: Block IP temporarily, investigate source
- Similar pattern seen: 2025-11-05 (different IP, same technique)
```

### 2. Ad-Hoc Investigation with lnav

**Scenario**: Developer investigating why a specific query failed

```bash
# 1. Open logs in lnav
lnav data/logs/audit/audit_*.jsonl

# 2. Filter to relevant timeframe and error type
# (lnav interactive filtering)

# 3. Export filtered view
:write-to /tmp/investigation.jsonl

# 4. Ask LLM for analysis
llm -m anthropic:claude-sonnet-4 < /tmp/investigation.jsonl \
  --system "You are a Neo4j expert analyzing audit logs. \
            Explain the root cause and suggest fixes."
```

**LLM Response**:
```
Root Cause Analysis:
The query failed due to a missing index on Person.email (line 42).
This caused a full node scan (1M nodes), exceeding the 30s timeout.

Evidence:
- db_hits: 1,000,000 (line 45)
- execution_time_ms: 31,247 (line 46)
- error: "Transaction timeout" (line 47)

Recommended Fix:
CREATE INDEX person_email_idx FOR (p:Person) ON (p.email)

Expected Impact:
- Reduce query time from 31s to <50ms
- Eliminate timeouts for this query pattern
```

### 3. Periodic Security Digest

**Scenario**: Nightly summary of security-relevant events

```bash
# Cron job: Daily security digest
0 2 * * * /usr/local/bin/security-digest.sh

# security-digest.sh
#!/bin/bash
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
LOGS=/data/logs/audit/audit_${YESTERDAY}_*.jsonl

cat $LOGS | llm -m groq:llama3-70b \
  --system "Summarize security events from Neo4j audit logs. \
            Flag: blocked queries, authentication failures, \
            suspicious patterns, performance issues." \
  > /tmp/digest.txt

# Send via email/Slack
mail -s "Neo4j Security Digest - $YESTERDAY" team@example.com < /tmp/digest.txt
```

### 4. Compliance Reporting

**Scenario**: Generate audit report for compliance team

```bash
# Export month's audit logs
:write-json /tmp/november_audit.json

# Generate compliance report
llm -m anthropic:claude-opus < /tmp/november_audit.json \
  --system "Generate a SOC2 compliance report for these Neo4j audit logs. \
            Include: query patterns, access controls enforcement, \
            data modification tracking, security incidents."
```

## Technical Design

### 1. LLM Integration Module

```python
# src/neo4j_yass_mcp/llm_analysis/log_analyzer.py

from typing import List, Dict, Optional
import json
from dataclasses import dataclass

@dataclass
class AnomalyAlert:
    """Detected anomaly in audit logs"""
    severity: str  # critical, high, medium, low
    category: str  # security, performance, compliance
    description: str
    evidence: List[Dict]
    recommendation: str
    timestamp: str

class LLMLogAnalyzer:
    """
    Analyzes audit logs using LLM for pattern detection and anomaly identification.
    """

    def __init__(
        self,
        llm_provider: str = "anthropic",
        model: str = "claude-3-haiku",
        real_time: bool = False
    ):
        self.llm_provider = llm_provider
        self.model = model
        self.real_time = real_time

    async def analyze_logs(
        self,
        log_entries: List[Dict],
        analysis_type: str = "security"
    ) -> Dict[str, Any]:
        """
        Analyze log entries using LLM.

        Args:
            log_entries: List of audit log entries (JSONL format)
            analysis_type: Type of analysis (security, performance, compliance)

        Returns:
            Analysis results with anomalies, insights, recommendations
        """
        # Prepare context for LLM
        context = self._prepare_context(log_entries, analysis_type)

        # Call LLM with appropriate prompt
        prompt = self._build_prompt(analysis_type)
        analysis = await self._call_llm(prompt, context)

        # Parse LLM response into structured format
        return self._parse_analysis(analysis)

    def _prepare_context(self, log_entries: List[Dict], analysis_type: str) -> str:
        """
        Prepare log context for LLM analysis.

        Includes:
        - Summary statistics (query counts, error rates)
        - Recent patterns (last N entries)
        - Historical context (if available)
        """
        stats = self._compute_statistics(log_entries)
        recent = log_entries[-100:]  # Last 100 entries

        return f"""
        Log Statistics:
        - Total entries: {stats['total']}
        - Blocked queries: {stats['blocked']}
        - Error rate: {stats['error_rate']}%
        - Unique IPs: {stats['unique_ips']}

        Recent Activity (last 100 entries):
        {json.dumps(recent, indent=2)}
        """

    def _build_prompt(self, analysis_type: str) -> str:
        """Build LLM prompt based on analysis type"""
        prompts = {
            "security": """
                You are a security analyst reviewing Neo4j audit logs.

                Analyze for:
                1. Injection attempts (SQL injection, Cypher injection)
                2. Brute force patterns (repeated failures from same IP)
                3. Data exfiltration attempts (large result sets, unusual queries)
                4. Access control violations (unauthorized operations)
                5. Anomalous behavior (unusual times, locations, patterns)

                For each finding:
                - Severity: critical, high, medium, low
                - Evidence: Specific log entries
                - Impact: Potential damage
                - Recommendation: Immediate action

                Format as JSON:
                {
                  "anomalies": [...],
                  "summary": "...",
                  "recommendations": [...]
                }
            """,

            "performance": """
                You are a database performance analyst.

                Identify:
                1. Slow queries (>1s execution time)
                2. Missing indexes (high db_hits, long scans)
                3. Inefficient patterns (Cartesian products, unbounded paths)
                4. Resource exhaustion (memory, timeouts)
                5. Optimization opportunities

                Provide:
                - Root cause analysis
                - Query optimization suggestions
                - Index recommendations
                - Expected performance gains
            """,

            "compliance": """
                You are a compliance auditor.

                Review for:
                1. Data access logging (all queries logged)
                2. Authentication tracking (who accessed what)
                3. Modification tracking (CREATE, DELETE, SET operations)
                4. Security controls (blocked dangerous operations)
                5. Audit trail completeness

                Generate SOC2/GDPR compliance report.
            """
        }

        return prompts.get(analysis_type, prompts["security"])

    async def _call_llm(self, prompt: str, context: str) -> str:
        """Call LLM API with prompt and context"""
        # Implementation depends on LLM provider
        # For now, placeholder
        pass

    def _parse_analysis(self, llm_response: str) -> Dict:
        """Parse LLM response into structured format"""
        try:
            # Attempt to parse as JSON
            return json.loads(llm_response)
        except json.JSONDecodeError:
            # Fallback to text response
            return {
                "raw_analysis": llm_response,
                "structured": False
            }
```

### 2. Integration with Existing Audit Logger

```python
# Enhance existing audit logger with LLM analysis hooks

class AuditLogger:
    def __init__(self, llm_analyzer: Optional[LLMLogAnalyzer] = None):
        self.llm_analyzer = llm_analyzer
        self.log_buffer = []  # Buffer for batch analysis

    def log_event(self, event: Dict):
        """Log audit event and optionally analyze"""
        # Existing logging
        self._write_to_file(event)

        # Real-time analysis (if enabled)
        if self.llm_analyzer and self.llm_analyzer.real_time:
            self.log_buffer.append(event)

            # Analyze in batches of 100
            if len(self.log_buffer) >= 100:
                asyncio.create_task(self._analyze_batch())

    async def _analyze_batch(self):
        """Analyze batch of logs with LLM"""
        analysis = await self.llm_analyzer.analyze_logs(
            self.log_buffer,
            analysis_type="security"
        )

        # Send alerts if anomalies detected
        if analysis.get("anomalies"):
            self._send_alerts(analysis["anomalies"])

        self.log_buffer = []
```

### 3. CLI Tools for Hybrid Analysis

```bash
# tools/llm-log-analysis.sh

#!/bin/bash
# LLM-powered log analysis tool for Neo4j YASS MCP

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${LOG_DIR:-data/logs/audit}"

usage() {
  cat <<EOF
Usage: $0 [command] [options]

Commands:
  analyze-live    Real-time analysis with multitail
  analyze-recent  Analyze last N hours of logs
  security-scan   Security-focused analysis
  performance     Performance bottleneck detection
  compliance      Generate compliance report

Options:
  --model MODEL   LLM model to use 
  --hours N       Hours to analyze (default: 24)
  --alert         Send alerts via configured channels

Examples:
  # Real-time security monitoring
  $0 analyze-live --alert

  # Analyze last 4 hours for performance issues
  $0 analyze-recent --hours 4 --model claude-sonnet-4

  # Generate compliance report
  $0 compliance --hours 720  # 30 days
EOF
  exit 1
}

analyze_live() {
  local model="${1:-claude-3-haiku}"

  echo "Starting real-time log analysis with $model..."
  echo "Press Ctrl+C to stop"

  multitail "$LOG_DIR"/audit_*.jsonl | \
    tee >(llm -m "anthropic:$model" \
      --system "Monitor Neo4j audit logs for anomalies. \
                Alert on: security incidents, performance issues, \
                unusual patterns. Format alerts with emoji indicators.")
}

analyze_recent() {
  local hours="${1:-24}"
  local model="${2:-claude-3-haiku}"

  echo "Analyzing last $hours hours with $model..."

  # Find logs from last N hours
  find "$LOG_DIR" -name "audit_*.jsonl" -mmin -$((hours * 60)) | \
    xargs cat | \
    llm -m "anthropic:$model" \
      --system "Analyze Neo4j audit logs. \
                Provide: summary of activity, anomalies detected, \
                recommendations for improvements."
}

security_scan() {
  local model="${1:-claude-3-haiku}"

  echo "Running security scan with $model..."

  cat "$LOG_DIR"/audit_*.jsonl | \
    llm -m "anthropic:$model" \
      --system "Security audit of Neo4j logs. \
                Focus on: injection attempts, authentication failures, \
                suspicious access patterns, data exfiltration risks."
}

# Parse command
COMMAND="${1:-}"
shift || true

case "$COMMAND" in
  analyze-live)
    analyze_live "$@"
    ;;
  analyze-recent)
    analyze_recent "$@"
    ;;
  security-scan)
    security_scan "$@"
    ;;
  *)
    usage
    ;;
esac
```

### 4. MCP Tool for Log Analysis

```python
@mcp.tool()
async def analyze_audit_logs(
    hours: int = 24,
    analysis_type: str = "security",
    alert_on_anomalies: bool = False
) -> Dict[str, Any]:
    """
    Analyze audit logs using LLM for pattern detection.

    Args:
        hours: Hours of logs to analyze (default: 24)
        analysis_type: Type of analysis (security, performance, compliance)
        alert_on_anomalies: Send alerts if anomalies detected

    Returns:
        Analysis results with anomalies, insights, recommendations
    """
    # Load logs from last N hours
    logs = load_recent_logs(hours)

    # Analyze with LLM
    analyzer = LLMLogAnalyzer(
        llm_provider=os.getenv("LLM_PROVIDER", "anthropic"),
        model=os.getenv("LLM_MODEL", "claude-3-haiku")
    )

    analysis = await analyzer.analyze_logs(logs, analysis_type)

    # Send alerts if requested
    if alert_on_anomalies and analysis.get("anomalies"):
        send_alerts(analysis["anomalies"])

    return analysis
```

## Configuration

### Environment Variables

```bash
# LLM Configuration
LLM_LOG_ANALYSIS_ENABLED=true
LLM_LOG_ANALYSIS_PROVIDER=anthropic  # anthropic, openai, groq
LLM_LOG_ANALYSIS_MODEL=claude-3-haiku
LLM_LOG_ANALYSIS_REAL_TIME=false  # Enable real-time analysis
LLM_LOG_ANALYSIS_BATCH_SIZE=100  # Logs per batch
LLM_LOG_ANALYSIS_INTERVAL=300  # Seconds between batches

# Alert Configuration
ALERT_ON_CRITICAL=true
ALERT_ON_HIGH=true
ALERT_CHANNELS=slack,email  # Comma-separated
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
ALERT_EMAIL=security@example.com
```

## Security Considerations

### 1. Sensitive Data Protection
```python
def sanitize_logs_for_llm(logs: List[Dict]) -> List[Dict]:
    """
    Remove sensitive data before sending to LLM.

    Redacts:
    - Passwords, API keys, tokens
    - Personal identifiable information (PII)
    - Query parameters with sensitive data
    """
    sanitized = []
    for log in logs:
        clean_log = log.copy()

        # Redact query parameters
        if "parameters" in clean_log:
            clean_log["parameters"] = "[REDACTED]"

        # Redact IP addresses (optional)
        if "client_ip" in clean_log:
            clean_log["client_ip"] = redact_ip(clean_log["client_ip"])

        sanitized.append(clean_log)

    return sanitized
```

### 2. Cost Controls
```python
# Limit LLM API calls
MAX_LLM_CALLS_PER_HOUR = 100
MAX_TOKENS_PER_ANALYSIS = 4000

# Use cheaper models for routine analysis
ROUTINE_MODEL = "claude-3-haiku"  # Fast, cheap
DEEP_ANALYSIS_MODEL = "claude-sonnet-4"  # Expensive, thorough
```

### 3. Rate Limiting
```python
# Prevent abuse of LLM analysis endpoint
ANALYSIS_RATE_LIMIT = "10/hour"  # Per user/IP
```

## Implementation Plan

### Week 1: Core LLM Integration
- [ ] Implement `LLMLogAnalyzer` class
- [ ] Add log sanitization for LLM safety
- [ ] Integrate with existing audit logger
- [ ] Unit tests for LLM interactions

### Week 2: CLI Tools & Real-Time Analysis
- [ ] Create `llm-log-analysis.sh` script
- [ ] Implement multitail/lnav integration
- [ ] Add real-time anomaly detection
- [ ] Batch analysis scheduler

### Week 3: MCP Tool & Alerting
- [ ] Add `analyze_audit_logs()` MCP tool
- [ ] Implement alert channels (Slack, email)
- [ ] Create compliance report generator
- [ ] Integration tests

### Week 4: Documentation & Optimization
- [ ] User documentation with examples
- [ ] Cost optimization (model selection)
- [ ] Performance tuning
- [ ] Security audit

## Example Workflows

### Workflow 1: Daily Security Review
```bash
# Morning routine: Check yesterday's activity
./tools/llm-log-analysis.sh analyze-recent --hours 24 > daily-report.txt

# Review report
less daily-report.txt

# If issues found, deep dive
lnav data/logs/audit/audit_*.jsonl
# Filter to suspicious entries, then export and analyze
```

### Workflow 2: Incident Response
```bash
# 1. Detect anomaly (real-time monitoring alerts)
# Alert: "Suspicious query pattern detected from 192.168.1.100"

# 2. Investigate with lnav
lnav data/logs/audit/audit_*.jsonl
# Filter: client_ip == "192.168.1.100"

# 3. Export and analyze
:write-to /tmp/incident.jsonl

# 4. Get LLM analysis
llm -m anthropic:claude-opus < /tmp/incident.jsonl \
  --system "Incident analysis: Assess threat level, \
            provide timeline of events, recommend response actions."

# 5. Take action based on LLM recommendations
```

### Workflow 3: Performance Optimization
```bash
# Analyze slow queries from last week
./tools/llm-log-analysis.sh performance --hours 168

# LLM identifies: Missing index on Person.email causing slowdowns

# Apply fix
CREATE INDEX person_email_idx FOR (p:Person) ON (p.email)

# Verify improvement next day
./tools/llm-log-analysis.sh performance --hours 24
```

## Success Metrics

### Adoption
- 80%+ of security incidents identified by LLM before manual detection
- Daily usage of log analysis tools by ops team

### Performance
- Analysis completes in <30 seconds for 24 hours of logs
- <5% false positive rate for anomaly detection

### Cost
- LLM API costs <$50/month for typical usage
- Effective use of cheaper models (haiku) for routine tasks

### Security
- Zero sensitive data leaks to LLM provider
- 100% of critical security events detected and alerted

## Future Enhancements

### Phase 2
1. **Pattern Learning**: Train on historical logs to improve anomaly detection
2. **Automated Remediation**: LLM suggests and applies fixes (with approval)
3. **Natural Language Queries**: "Show me all failed logins from yesterday"
4. **Correlation Analysis**: Cross-reference with other system logs (nginx, system)

### Integration Opportunities
- Prometheus/Grafana dashboard with LLM insights
- PagerDuty integration for critical alerts
- SIEM integration (Splunk, ELK)
- ChatOps (query logs via Slack)

## References

- [lnav Documentation](https://lnav.org/)
- [multitail](https://www.vanheusden.com/multitail/)
- [llm CLI](https://llm.datasette.io/)
- [Log Analysis Best Practices](https://www.loggly.com/ultimate-guide/logging-best-practices/)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-07
**Author**: Neo4j YASS MCP Team
