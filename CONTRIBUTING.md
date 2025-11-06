# Contributing to Neo4j YASS MCP

Thank you for your interest in contributing to Neo4j YASS MCP! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct (coming soon).

## How to Contribute

### Reporting Issues

- Use GitHub Issues to report bugs or request features
- Search existing issues before creating a new one
- Provide clear, detailed information:
  - Steps to reproduce (for bugs)
  - Expected vs actual behavior
  - Environment details (OS, Python version, Neo4j version)
  - Relevant logs or error messages

### Submitting Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/neo4j-yass-mcp.git
   cd neo4j-yass-mcp
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set up development environment**
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[all]"
   ```

4. **Make your changes**
   - Follow the code style (see below)
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

5. **Run quality checks**
   ```bash
   make lint        # Check code style
   make test        # Run tests
   make security    # Run security checks
   ```

6. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

7. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Open a Pull Request**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure CI checks pass

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8, enforced by Ruff
- **Line length**: 100 characters
- **Type hints**: Use where appropriate
- **Docstrings**: Google style for functions/classes

### Commit Messages

Use conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test changes
- `refactor`: Code refactoring
- `chore`: Build/tool changes
- `security`: Security fixes

Examples:
```bash
feat(sanitizer): add regex pattern for APOC filtering
fix(server): handle null values in estimate_tokens
docs(readme): update installation instructions
security(auth): add weak password detection
```

### Testing

- Write tests for all new features
- Maintain or improve code coverage
- Test security features thoroughly
- Include edge cases and error conditions

Example test structure:
```python
def test_feature_name():
    """Test description"""
    # Arrange
    input_data = ...

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_value
```

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all functions/classes
- Update .env.example for new config options
- Create/update docs/ files for major features

## Security

### Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities.

Instead:
1. Email security@yourproject.com (or create private security advisory)
2. Provide detailed information about the vulnerability
3. Allow time for us to patch before public disclosure

### Security Considerations

When contributing, consider:
- Input validation and sanitization
- Authentication and authorization
- Data exposure in logs/errors
- Injection attacks (Cypher, SQL, command)
- Rate limiting and DoS protection

## Review Process

1. **Automated Checks**: CI runs tests, linting, security scans
2. **Code Review**: Maintainers review for:
   - Code quality and style
   - Test coverage
   - Documentation
   - Security implications
   - Performance impact
3. **Feedback**: Address review comments
4. **Approval**: Two maintainer approvals required
5. **Merge**: Squash and merge to main branch

## Release Process

1. Version bump in pyproject.toml
2. Update CHANGELOG.md
3. Create release tag
4. Publish to PyPI (maintainers only)

## Questions?

- Open a Discussion on GitHub
- Join our community chat (link coming soon)
- Email the maintainers

Thank you for contributing! 🎉
