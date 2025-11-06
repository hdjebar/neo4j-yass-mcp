# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

**DO NOT** open public GitHub issues for security vulnerabilities.

### How to Report

1. **Email**: security@yourproject.com (preferred)
2. **GitHub Security Advisory**: Use the "Security" tab to create a private advisory
3. **Encrypted**: Use our PGP key (available on request) for sensitive information

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)
- Your contact information

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Development**: Depends on severity
- **Disclosure**: Coordinated after fix is available

### Security Update Process

1. We validate the report
2. Develop and test a fix
3. Prepare a security advisory
4. Release the fix
5. Publish the advisory (after grace period)

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

- **Security Team**: security@yourproject.com
- **Maintainers**: See CODEOWNERS file

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities.

Hall of Fame:
- (Coming soon)

---

**Security is a shared responsibility. If you see something, say something.**
