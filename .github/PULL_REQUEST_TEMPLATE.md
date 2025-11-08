# Pull Request

## Description

<!-- Please include a summary of the changes and the related issue. -->

Fixes # (issue)

## Type of Change

<!-- Please delete options that are not relevant. -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Security enhancement
- [ ] Dependency update

## Motivation and Context

<!-- Why is this change required? What problem does it solve? -->

## How Has This Been Tested?

<!-- Please describe the tests you ran to verify your changes. -->

- [ ] Unit tests pass (`pytest`)
- [ ] Integration tests pass
- [ ] Manual testing performed
- [ ] Code coverage maintained or improved

**Test Configuration**:
- Python version:
- Neo4j version:
- LLM provider tested:
- Operating System:

## Checklist

<!-- Put an 'x' in all the boxes that apply. -->

### Code Quality
- [ ] My code follows the project's style guidelines (Ruff, Black)
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings or errors

### Testing
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have tested this with at least one LLM provider (OpenAI, Anthropic, Google, or Ollama)
- [ ] I have tested edge cases and error handling

### Documentation
- [ ] I have updated the documentation (README, docs/, inline comments)
- [ ] I have updated the CHANGELOG.md if applicable
- [ ] I have added/updated docstrings for new/modified functions
- [ ] I have updated type hints where applicable

### Security
- [ ] My changes do not introduce security vulnerabilities
- [ ] I have redacted all sensitive information from this PR
- [ ] I have tested for SQL/Cypher injection vulnerabilities (if applicable)
- [ ] I have tested for prompt injection vulnerabilities (if applicable)

### Dependencies
- [ ] I have added new dependencies to `pyproject.toml` with version constraints
- [ ] I have regenerated `uv.lock` if dependencies changed (`uv lock`)
- [ ] All dependencies are compatible with Python 3.11+

## Screenshots / Videos (if applicable)

<!-- If your change affects the UI or behavior, please provide screenshots or videos. -->

## Breaking Changes

<!-- List any breaking changes and how users should migrate. -->

- [ ] This PR introduces breaking changes

**Migration Guide**:
<!-- If breaking changes, provide migration steps for users. -->

## Additional Notes

<!-- Any additional information that reviewers should know. -->

## Reviewer Checklist

<!-- For reviewers - do not edit as PR author -->

- [ ] Code follows project conventions
- [ ] Tests are comprehensive and pass
- [ ] Documentation is clear and complete
- [ ] Security implications have been considered
- [ ] Performance impact is acceptable
- [ ] Breaking changes are documented
- [ ] CHANGELOG.md is updated (if applicable)

---

**Built with Claude Code** 🤖
