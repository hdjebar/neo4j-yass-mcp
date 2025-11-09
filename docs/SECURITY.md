# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

**For security vulnerabilities**, please use GitHub's private security reporting:

### How to Report

1. **GitHub Security Advisory** (Recommended):
   - Go to the "Security" tab in the repository
   - Click "Report a vulnerability"
   - Create a private security advisory
   - This allows secure, private discussion with maintainers

2. **GitHub Issues** (For non-critical security concerns):
   - Use for security improvements or questions
   - **DO NOT** disclose critical vulnerabilities in public issues

### What to Include

- Clear description of the vulnerability
- Steps to reproduce the issue
- Potential impact and attack scenarios
- Suggested fix or mitigation (if any)
- Environment details (OS, Python version, Neo4j version)
- Your GitHub username for credit

### Response Timeline

- **Acknowledgment**: Within 72 hours
- **Initial Assessment**: Within 1 week
- **Fix Development**: Depends on severity (critical: days, medium: weeks)
- **Disclosure**: Coordinated after fix is released

### Security Update Process

1. **Validation**: We verify and assess the reported vulnerability
2. **Fix Development**: Create and test a patch in a private branch
3. **Security Advisory**: Prepare detailed advisory (CVE if applicable)
4. **Release**: Deploy the fix in a new version
5. **Public Disclosure**: Publish advisory 7-14 days after release
6. **Credit**: Acknowledge reporter in release notes and advisory

## Security Features

Neo4j YASS MCP includes multiple security layers:

### Query Sanitization (SISO Prevention)

- Cypher injection blocking
- SQL injection pattern detection
- UTF-8/Unicode attack prevention
- Dangerous APOC procedure filtering
- Schema change protection

See [SECURITY_FIXES.md](docs/SECURITY_FIXES.md) for details.

### Access Control

- Read-only mode enforcement
- Weak password detection
- Configurable LangChain safety controls
- Parameter validation

### Audit & Compliance

- Comprehensive query logging
- Error tracking
- Optional PII redaction
- Configurable retention policies

### Rate Limiting & Abuse Prevention

- Decorator-driven throttling for every MCP tool (`query_graph`, `execute_cypher`, `refresh_schema`) and resource (`get_schema`, `get_database_info`)
- Sliding-window enforcement powered by `RateLimiterService` with async locks to prevent race conditions
- Per-session buckets derived from `ctx.session_id` (falls back to `client_id`/`request_id`)
- Independent knobs for each surface:

| Surface | Limit Variables | Default |
|---------|-----------------|---------|
| All tools (global toggle) | `MCP_TOOL_RATE_LIMIT_ENABLED` | `true` |
| Natural language queries | `MCP_QUERY_GRAPH_LIMIT`, `MCP_QUERY_GRAPH_WINDOW` | `10 / 60s` |
| Raw Cypher | `MCP_EXECUTE_CYPHER_LIMIT`, `MCP_EXECUTE_CYPHER_WINDOW` | `10 / 60s` |
| Schema refresh | `MCP_REFRESH_SCHEMA_LIMIT`, `MCP_REFRESH_SCHEMA_WINDOW` | `5 / 120s` |
| Resources (schema & db info) | `MCP_RESOURCE_RATE_LIMIT_ENABLED`, `MCP_RESOURCE_LIMIT`, `MCP_RESOURCE_WINDOW` | `true / 20 / 60s` |

These limits mitigate credential stuffing, scripted scraping of schema metadata, and accidental denial-of-service by runaway agents.

### Error Handling

- Sanitized error messages (production)
- Full error logging to audit logs
- Debug mode for development

## Security Best Practices

### Production Deployment

✅ **Do**:
- Use strong passwords (12+ characters minimum)
- Enable `SANITIZER_ENABLED=true`
- Set `DEBUG_MODE=false`
- Enable `AUDIT_LOG_ENABLED=true`
- Keep `LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=false`
- Use HTTPS for network transport
- Regularly review audit logs
- Keep dependencies updated

❌ **Don't**:
- Use default/weak passwords
- Disable security features without additional controls
- Expose debug error messages in production
- Run with unrestricted APOC access
- Skip security testing

### Configuration Hardening

```bash
# Strong authentication
NEO4J_PASSWORD=<strong-random-password>
ALLOW_WEAK_PASSWORDS=false

# Query security
SANITIZER_ENABLED=true
SANITIZER_STRICT_MODE=true
SANITIZER_BLOCK_NON_ASCII=false

# LangChain safety
LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=false

# Error handling
DEBUG_MODE=false

# Read-only mode (if applicable)
NEO4J_READ_ONLY=true

# Audit logging
AUDIT_LOG_ENABLED=true
AUDIT_LOG_FORMAT=json
AUDIT_LOG_RETENTION_DAYS=90
AUDIT_LOG_PII_REDACTION=true
```

### Network Security

For HTTP/SSE transport:

```bash
# Bind to specific interface
MCP_SERVER_HOST=127.0.0.1  # localhost only

# CORS restrictions
MCP_SERVER_ALLOW_ORIGINS=https://yourdomain.com

# DNS rebinding protection
MCP_SERVER_ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
```

### Dependency Security

```bash
# Check for vulnerabilities
make security

# Or manually
pip install safety
safety check

bandit -r . -x tests/
```

## Known Security Considerations

### LangChain allow_dangerous_requests

Setting `LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=true` bypasses LangChain's built-in safety checks. Only use when:

1. You fully trust the LLM output
2. The query sanitizer is enabled (`SANITIZER_ENABLED=true`)
3. You have additional security controls in place

**Default**: `false` (recommended)

### Read-Only Mode Limitations

Read-only mode is enforced at the application level, not database level. For maximum security:

1. Create a read-only Neo4j user
2. Use that user's credentials
3. Enable application read-only mode as defense-in-depth

### UTF-8 Attack Prevention

The sanitizer blocks various UTF-8 encoding attacks, but may interfere with legitimate international text. If you need non-ASCII support:

```bash
SANITIZER_BLOCK_NON_ASCII=false  # Allow UTF-8
```

Consider additional validation for your use case.

## Security Audits

- **Last Audit**: 2025-11-06
- **Audit Scope**: Code review, security fix implementation
- **Findings**: 6 critical issues fixed (see FIXES_APPLIED.md)

## Compliance

- **OWASP Top 10**: Addresses injection, broken access control, security misconfiguration
- **CWE Coverage**: CWE-89 (Injection), CWE-200 (Information Exposure), CWE-521 (Weak Passwords)

## Security Contacts

- **Primary Contact**: Use GitHub Security Advisories (see "Reporting a Vulnerability" above)
- **General Questions**: Open a GitHub issue with the `security` label
- **Maintainers**: See [CODEOWNERS](CODEOWNERS) file or repository contributors

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities through GitHub Security Advisories.

**Hall of Fame** (Responsible Disclosure):
- (Future contributors will be listed here with their consent)

---

**Security is a shared responsibility. If you see something, say something.**
