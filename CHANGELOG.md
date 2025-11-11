# Changelog

All notable changes to Neo4j YASS MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Features in development

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security improvements and fixes

## [1.2.1] - 2025-01-12

### Changed
- **CRITICAL**: Updated `langchain-neo4j` from 0.1.0 to 0.6.0 (security & stability)
  - Includes 11 months of bug fixes and improvements
  - Enhanced GraphRAG capabilities
  - Better LangChain 1.0 compatibility
  - Performance optimizations
- **CRITICAL**: Updated `neo4j` driver from 5.14.0 to 5.28.0 (security & performance)
  - Security: mTLS support for 2FA authentication
  - Performance: ~100x speedup for temporal operations
  - Bug fixes: DateTime arithmetic corrections
  - Python 3.13 full compatibility
  - GQL-compliant error handling
- Updated `pydantic` from 2.0.0 to 2.10.0 (latest stable)

### Security
- Addressed 14 months of security patches in Neo4j driver
- Addressed 11 months of security patches in langchain-neo4j
- Enhanced connection security with mTLS support

### Performance
- Temporal operations now ~100x faster (Neo4j driver 5.28.0)
- Improved schema introspection performance
- Better connection pool handling

## [1.2.0] - 2025-11-10

### Added
- 🎉 **Public Release**: Neo4j YASS MCP is now open source!
- Enhanced README badges for better visibility:
  - CI/CD pipeline status badge
  - Docker ready badge
  - MCP Protocol version badge
  - Security scanning (Bandit) badge
  - LangChain 1.0 compatibility badge
- Updated documentation metadata for public release
- Public repository links in all documentation

### Changed
- README badges reorganized for improved visual hierarchy
- Documentation index updated with public release status
- Version information updated across documentation (1.1.0 → 1.2.0)

### Documentation
- All documentation reviewed and verified for public release
- No sensitive information or credentials found in repository
- MIT License confirmed for open source distribution
- Security policy and vulnerability reporting guidelines in place
- Comprehensive documentation for users, developers, and security auditors

### Repository
- Repository visibility changed from private to public
- GitHub Actions CI/CD pipeline configured and running
- Security scanning with Trivy and Bandit enabled
- 287 tests passing with 81.89% code coverage
- Docker images ready for public deployment

## [1.1.0] - 2025-11-08

### Changed
- **BREAKING**: Upgraded FastMCP from 0.4.1 to 2.13.0.2
  - Major version jump across 0.x → 1.0 → 2.x
  - Tests now access underlying functions via `.fn()` attribute on decorated tools/resources
  - Server initialization compatible with new API (no changes needed)
  - All 287 tests passing with 81.89% coverage
- **BREAKING**: Upgraded LangChain from 0.3.27 to 1.0.5
  - Major version release with stability guarantees until 2.0
  - Python 3.10+ required (project already using 3.13)
  - `langchain-neo4j` upgraded to 0.6.0 (from 0.5.0)
  - `langchain-openai` upgraded to 1.0.2 (from 0.3.35)
  - `langchain-anthropic` upgraded to 1.0.2 (from 0.3.22)
  - `langchain-core` now explicit dependency at 1.0.4
  - All provider integrations tested and working
- Upgraded MCP Protocol SDK from 1.20.0 to 1.21.0 (minor update)

### Added
- Comprehensive Phase 3 dependency upgrade analysis document
- FastMCP 2.13 feature availability:
  - Response caching middleware (available for future use)
  - Pluggable storage backends with encryption (available for future use)
  - Server lifespan hooks for proper resource management (available for future use)
  - Pydantic input validation with better flexibility
  - Icon support for richer UX

### Fixed
- Test suite compatibility with FastMCP 2.13 FunctionTool API
- Rate limiter test floating point precision issues
- Updated all test imports to use `.fn()` for accessing decorated functions

### Documentation
- Added detailed migration guide: [docs/repo-arai/PHASE3_DEPENDENCY_UPGRADE_ANALYSIS.md](docs/repo-arai/PHASE3_DEPENDENCY_UPGRADE_ANALYSIS.md)
- Documented breaking changes and migration steps
- Updated dependency version matrix
- Added FastMCP 2.13 feature overview

### Technical Details
- All dependencies now on latest stable versions
- No code changes required for FastMCP upgrade (imports already correct)
- No `.text()` method usage found (LangChain 1.0 compatibility)
- `allow_dangerous_requests` parameter confirmed working (introduced in 0.2.19)
- GraphCypherQAChain fully compatible with LangChain 1.0
- Test coverage maintained above 80% threshold

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

### Added
- Added resource limits to Docker Compose configuration (CPU: 2.0 cores max, Memory: 2GB max)
- Added Trivy vulnerability scanning to CI/CD pipeline for automated security checks
- Added `ENVIRONMENT` variable to control environment-specific security restrictions
- Added production environment check for DEBUG_MODE to prevent information leakage
- Added Python 3.13 to CI/CD test matrix
- Added per-tool MCP rate limiter configuration knobs:
  - `MCP_TOOL_RATE_LIMIT_ENABLED`
  - `MCP_QUERY_GRAPH_LIMIT` / `MCP_QUERY_GRAPH_WINDOW`
  - `MCP_EXECUTE_CYPHER_LIMIT` / `MCP_EXECUTE_CYPHER_WINDOW`
  - `MCP_REFRESH_SCHEMA_LIMIT` / `MCP_REFRESH_SCHEMA_WINDOW`
  - `MCP_RESOURCE_RATE_LIMIT_ENABLED`
  - `MCP_RESOURCE_LIMIT` / `MCP_RESOURCE_WINDOW`

### Changed
- **BREAKING:** Upgraded minimum Python version from 3.11 to 3.13 for 5-15% performance improvement
- Replaced deprecated `asyncio.get_event_loop()` with modern `asyncio.to_thread()` pattern in 3 locations:
  - [server.py:458](src/neo4j_yass_mcp/server.py#L458) - `query_graph()` function
  - [server.py:662](src/neo4j_yass_mcp/server.py#L662) - `execute_cypher()` function
  - [server.py:763](src/neo4j_yass_mcp/server.py#L763) - `refresh_schema()` function
- Updated Docker Compose Python version default from 3.11 to 3.13
- Updated Dockerfile Python version default from 3.11 to 3.13.8
- Updated all tool configurations (ruff, black, mypy) to target Python 3.13
- Removed deprecated `version: '3.8'` field from docker-compose.yml (Compose V2 compatibility)

### Security
- **Critical:** DEBUG_MODE now blocked in production environments (ENVIRONMENT=production)
- Added automated vulnerability scanning with Trivy in GitHub Actions
- Implemented container resource limits to prevent resource exhaustion attacks
- Enhanced security logging for DEBUG_MODE usage

### Performance
- Expected 5-15% overall performance improvement from Python 3.13 upgrade
- Improved async operation handling with modern asyncio patterns
- Better memory efficiency (-7%) with updated Python runtime

### Documentation
- Added ENVIRONMENT variable documentation to .env.example
- Updated all configuration files with Python 3.13 requirements
- Added Docker Compose V2 compatibility note
- Created CHANGELOG.md migration guide for Python 3.13
- Documented decorator-based rate limiting across README, `.env`, `.env.example`, `docs/SOFTWARE_ARCHITECTURE.md`, and `docs/SECURITY.md`, including new mermaid diagrams and configuration tables.

---

## Planned for v1.1.0 (Q1 2025)
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
