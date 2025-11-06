# Security Policy

## Reporting a Vulnerability

The Neo4j YASS MCP team takes security vulnerabilities seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report

**For Critical Vulnerabilities (Private Disclosure)**

If you discover a critical security vulnerability that could be exploited (e.g., remote code execution, authentication bypass, data breach), please report it privately:

- **Email**: hdjebar@gmail.com
- **Subject**: [SECURITY] Neo4j YASS MCP - Brief Description
- **Include**:
  - Detailed description of the vulnerability
  - Steps to reproduce
  - Potential impact
  - Suggested mitigation (if any)

**For Non-Critical Security Issues (Public Issue)**

For lower-severity security issues that don't pose immediate exploitation risk, you can:

1. Create a [Security Vulnerability Issue](https://github.com/hdjebar/neo4j-yass-mcp/issues/new?template=security_vulnerability.yml)
2. Provide detailed information using the issue template

### What to Expect

- **Acknowledgment**: Within 48 hours of receiving your report
- **Initial Assessment**: Within 5 business days
- **Regular Updates**: At least every 7 days until resolution
- **Fix Timeline**:
  - Critical vulnerabilities: 7-14 days
  - High severity: 30 days
  - Medium/Low severity: 60-90 days

### Responsible Disclosure Guidelines

We ask that security researchers:

1. **Give us reasonable time** to investigate and fix the vulnerability before public disclosure
2. **Do not exploit** the vulnerability beyond what's necessary to demonstrate it
3. **Do not access or modify** user data that doesn't belong to you
4. **Act in good faith** to avoid privacy violations, data destruction, or service disruption

### Recognition

We appreciate security researchers who help keep Neo4j YASS MCP secure. With your permission, we will:

- Acknowledge your contribution in our CHANGELOG
- Credit you in the security advisory (unless you prefer to remain anonymous)
- List you in our Hall of Fame (coming soon)

## Supported Versions

We currently support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Security Features

Neo4j YASS MCP includes multiple layers of security protection:

### Query Security
- **Multi-layer Cypher Injection Prevention**: Blocks malicious Cypher patterns
- **UTF-8 Attack Protection**: Detects homographs, zero-width characters, directional overrides
- **Read-Only Mode**: Optional restriction to prevent write operations
- **Query Pattern Validation**: Validates query structure before execution

### Audit & Compliance
- **Comprehensive Audit Logging**: GDPR, HIPAA, SOC 2, PCI-DSS compliant logging
- **Immutable Audit Trails**: Tamper-resistant JSON log format
- **Sensitive Data Filtering**: Automatic redaction of credentials in logs

### Network Security
- **Transport Encryption**: TLS support for network transports
- **DNS Rebinding Protection**: Validates Host headers
- **CORS Configuration**: Configurable cross-origin policies
- **Rate Limiting**: Planned (see Feature #15)

### Authentication & Authorization
- **Neo4j Authentication**: Secure credential management
- **Weak Password Detection**: Prevents common weak passwords
- **Environment Variable Secrets**: No hardcoded credentials

## Security Best Practices

When deploying Neo4j YASS MCP:

### Configuration
1. **Always use strong passwords** for Neo4j
2. **Enable read-only mode** if write access isn't needed
3. **Use TLS/SSL** for Neo4j connections in production
4. **Restrict network access** using firewalls and network policies
5. **Keep audit logs secure** and monitor them regularly

### Environment Variables
1. **Never commit** `.env` files to version control
2. **Use secrets management** (AWS Secrets Manager, HashiCorp Vault, etc.)
3. **Rotate credentials** regularly
4. **Limit environment variable access** to necessary users

### Deployment
1. **Keep dependencies updated** using `safety` and `dependabot`
2. **Run security scans** using `bandit` before deployment
3. **Monitor for vulnerabilities** in dependencies
4. **Use container scanning** for Docker deployments

### LLM Security
1. **Validate LLM outputs** before executing generated queries
2. **Set response size limits** to prevent token exhaustion
3. **Monitor LLM API usage** for anomalies
4. **Use least-privilege LLM API keys**

## Known Security Considerations

### LLM-Generated Queries
While we implement multiple layers of sanitization, LLM-generated queries should be treated with caution:
- Review generated Cypher before execution in production
- Use read-only mode when possible
- Monitor audit logs for suspicious patterns

### Neo4j Plugin Requirements
This server requires APOC plugin for schema introspection. Ensure you:
- Use official APOC releases from Neo4j
- Keep APOC updated to the latest version
- Review APOC security advisories

## Security Roadmap

Planned security enhancements (see [docs/FutureFeatures/](docs/FutureFeatures/)):

1. **Query Complexity Limits** (Feature #15)
   - Query cost estimation
   - Complexity thresholds
   - DoS prevention

2. **Row-Level Security** (Feature #13)
   - Fine-grained access control
   - User-based data filtering

3. **Query Approval Workflow** (Feature #14)
   - Multi-stage approval for write queries
   - Audit trail for approvals

4. **LLM-Powered Security Analysis** (Feature #16)
   - Anomaly detection in audit logs
   - Real-time security alerts

## External Security Reviews

We welcome external security reviews and penetration testing. Please contact us before conducting any security assessment to coordinate timing and scope.

## Vulnerability Disclosure Timeline

When we receive a vulnerability report:

1. **Day 0**: Acknowledgment sent
2. **Day 1-5**: Vulnerability validated and severity assessed
3. **Day 7-90**: Fix developed and tested (timeline varies by severity)
4. **Day X**: Coordinated disclosure with reporter
5. **Day X+1**: Security advisory published, fix released

## Contact

- **Security Email**: hdjebar@gmail.com
- **General Issues**: https://github.com/hdjebar/neo4j-yass-mcp/issues
- **Security Advisories**: https://github.com/hdjebar/neo4j-yass-mcp/security/advisories

---

**Last Updated**: 2025-11-07
