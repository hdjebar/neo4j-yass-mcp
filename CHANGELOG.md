# Changelog

All notable changes to Neo4j YASS MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-07

### Added
- Initial release of Neo4j YASS MCP (Yet Another Secure Server)
- FastMCP-based Model Context Protocol implementation
- LangChain integration for natural language to Cypher translation
- Comprehensive query sanitization with multi-layer security
- Audit logging with JSONL format for compliance
- Docker support with uv for 10-100x faster builds
- Support for multiple LLM providers (OpenAI, Anthropic, Google)
- Response size limiting and token counting
- Read-only mode for production safety
- Extensive documentation (README, QUICK_START, SECURITY, DOCKER guides)
- UTF-8/Unicode attack prevention with comprehensive test suite
- Weak password detection with configurable enforcement
- Automatic port allocation for development
- Health check endpoints
- Graceful shutdown with resource cleanup

### Security
- Query sanitization preventing injection attacks
  - Cypher injection prevention
  - Command injection blocking
  - Path traversal protection
  - Dangerous pattern detection (APOC, dynamic Cypher)
  - Balanced delimiter validation
  - String escape injection detection
  - UTF-8/Unicode attack prevention
- Audit logging for compliance tracking
- Weak password detection (14 known weak patterns)
- Error message sanitization (production vs debug modes)
- Parameter validation (count, size, naming)
- Rate limiting ready (configurable)
- Query complexity limits (length: 10KB, parameters: 100)

### Performance
- Docker builds with uv: 4-6x faster (first build), 10-30x faster (rebuilds)
- BuildKit cache integration
- Async/await support for parallel query execution
- Thread pool executor for Neo4j queries
- Optional LLM streaming for real-time responses
- Response token limiting to manage LLM context

### Documentation
- Comprehensive improvements summary ([docs/IMPROVEMENTS_SUMMARY.md](docs/IMPROVEMENTS_SUMMARY.md))
- Future features roadmap with 16 proposed enhancements ([docs/FutureFeatures/](docs/FutureFeatures/))
- Detailed security documentation ([SECURITY.md](SECURITY.md))
- Docker deployment guide ([DOCKER.md](DOCKER.md))
- Quick start guide with uv integration ([QUICK_START.md](QUICK_START.md))
- Software architecture documentation ([docs/SOFTWARE_ARCHITECTURE.md](docs/SOFTWARE_ARCHITECTURE.md))

### Fixed (from initial analysis)
- Duplicate `[build-system]` in [pyproject.toml](pyproject.toml)
- Broken console script entry point (now: `neo4j-yass-mcp`)
- 7 Makefile targets referencing old paths
- Test imports after package restructure
- Password logging security leak
- `SANITIZER_MAX_QUERY_LENGTH` environment variable wiring
- Incorrect langchain import (`langchain_neo4j`)
- `WEAK_PASSWORDS` import path
- Missing `sanitize_error_message()` function
- Executor shutdown without timeout
- tiktoken/tokenizers dependency mismatch
- Hardcoded weak passwords list (now uses centralized constant)
- test_utf8_attacks.py converted to proper pytest tests
- Missing utilities/ references in documentation

### Changed
- Package structure to src-layout (`src/neo4j_yass_mcp/`)
- Dependency versions with upper bounds for stability
- All documentation paths updated for src-layout
- Makefile targets updated to use `src/neo4j_yass_mcp/`
- Improved cleanup function with 30s timeout and comprehensive logging
- Enhanced error sanitization with debug mode support

## [Unreleased]

### Planned for v1.1.0 (Q1 2025)
- Query Plan Analysis & Optimization (Feature #1)
- Query Complexity Limits & Cost Estimation (Feature #15)
- Query Bookmarking (Feature #11)
- Monitoring & Alerting (Feature #7)

### Planned for v1.2.0 (Q2 2025)
- Advanced Schema Discovery (Feature #2)
- Query History & Caching (Feature #3)
- Graph Analytics Tools (Feature #10)

### Planned for v2.0.0 (Q3-Q4 2025)
- Advanced Security & Compliance (Feature #4)
- LLM-Powered Log Analysis & Anomaly Detection (Feature #16)
- Row-Level Security (Feature #13)
- Advanced NLP (Feature #9)

See [docs/FutureFeatures/](docs/FutureFeatures/) for detailed feature specifications.

---

## Version History Format

### [Version] - YYYY-MM-DD

#### Added
- New features

#### Changed
- Changes in existing functionality

#### Deprecated
- Soon-to-be removed features

#### Removed
- Removed features

#### Fixed
- Bug fixes

#### Security
- Security improvements and fixes

---

**Note**: This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR** version: Incompatible API changes
- **MINOR** version: Backward-compatible functionality additions
- **PATCH** version: Backward-compatible bug fixes
