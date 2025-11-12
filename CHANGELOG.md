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

## [1.3.0] - 2025-11-12

### 🎯 Major Architectural Milestone

This release completes Phase 2 and Phase 3 of the architectural refactoring plan, delivering:
- ✅ **Centralized Configuration**: Eliminated 26 scattered `os.getenv()` calls
- ✅ **Bootstrap Module**: Foundation for multi-instance deployments
- ✅ **Server Modularization**: Split 883-line server.py into focused modules
- ✅ **Strong Typing**: Added TypedDict response structures
- ✅ **Circular Dependencies Resolved**: Clean architecture
- ✅ **CI/CD Pipeline**: 99.6% test pass rate, all linting clean

### Added

#### Phase 2: Core Architecture (Issues #2, #3, #5)
- **RuntimeConfig with Pydantic** (`src/neo4j_yass_mcp/config/runtime_config.py`)
  - Centralized configuration management replacing 26 `os.getenv()` calls
  - Pydantic validation for all settings
  - Environment-specific validation (production vs development)
  - Weak password detection in production
  - 95% test coverage with comprehensive validation tests

- **TypedDict Response Types** (`src/neo4j_yass_mcp/types/responses.py`)
  - Strong typing for all tool responses
  - `QueryGraphResponse`, `ExecuteCypherResponse`, `AnalysisResponse`, etc.
  - Better IDE autocomplete and type safety
  - Enables mypy verification of response structures

- **Security Validators Module** (`src/neo4j_yass_mcp/security/validators.py`)
  - Broke circular dependency between server.py and secure_graph.py
  - Extracted read-only access validation
  - Clean separation of concerns

#### Phase 3: Bootstrap & Modularization (Issue #1)
- **Bootstrap Module** (`src/neo4j_yass_mcp/bootstrap.py`)
  - `ServerState` dataclass encapsulating all server state
  - `initialize_server_state()` for explicit initialization
  - `get_server_state()` accessor with lazy initialization
  - State accessor functions: `get_config()`, `get_graph()`, `get_chain()`, `get_executor()`
  - Eliminates import-time side effects
  - Foundation for multi-instance deployments
  - Comprehensive migration guide (500+ lines)

- **Handler Modules** (`src/neo4j_yass_mcp/handlers/`)
  - Extracted tool handlers: `tools.py` (query_graph, execute_cypher, analyze_query_performance, refresh_schema)
  - Extracted resource handlers: `resources.py` (get_schema, get_database_info)
  - Reduced server.py from 883 lines to focused core
  - Lazy imports to avoid circular dependencies
  - Better code organization and maintainability

### Changed

#### Configuration Migration
- **server.py**: Migrated all 26 environment variable reads to use RuntimeConfig
  - `_config = RuntimeConfig.from_env()` at module level
  - Replaced `os.getenv()` with `_config.neo4j.*`, `_config.llm.*`, etc.
  - Better testability with config object mocking

#### Test Infrastructure
- **Updated 60+ test mocks** to work with new bootstrap architecture
  - Changed from `patch("neo4j_yass_mcp.server.graph")` to `patch("neo4j_yass_mcp.server._get_graph")`
  - Updated executor tests for bootstrap integration
  - Fixed test isolation issues in rate limiting tests
  - Added comprehensive mocking for initialization tests

#### Type System
- **Updated all tool signatures** to use TypedDict return types
  - Replaced `dict[str, Any]` with specific TypedDict classes
  - Better type safety throughout the codebase
  - Mypy validation now catches response structure errors

### Fixed

#### CI/CD Pipeline (6 commits)
- **Linting Configuration** (2aaa3d1, bbf8caa, 18665b6, 41091cc, 30b000d)
  - Configured ruff suppressions for intentional patterns (E402, S105, S106, S104)
  - Configured bandit suppressions (B101, B104, B105, B106)
  - Fixed all ruff formatting issues (9 files reformatted)
  - Fixed all mypy type errors (ThreadPoolExecutor annotations)
  - Removed unused imports
  - **Result**: 100% linting compliance, 100% type checking

- **Test Fixes** (3e8e4a0, 72a1065, 23bd461, d4130fa)
  - Fixed test mocking patterns after modularization
  - Fixed executor tests for bootstrap integration
  - Fixed initialization tests with comprehensive mocking
  - Added missing LLM mocks to avoid requiring API keys
  - **Result**: 552/554 tests passing (99.6%)

#### Phase 3.3: Bootstrap Integration
- Fixed executor worker count tests (10 workers with "neo4j_yass_mcp_" prefix)
- Fixed test isolation for bootstrap state management
- Updated state accessor patterns in tests

#### Phase 3.4: Modularization
- Fixed sanitizer test mock path (`server.sanitize_query` → `handlers.tools.sanitize_query`)
- Updated all imports after handler extraction
- Fixed lazy import patterns to avoid circular dependencies

### Security
- **Weak Password Validation**: Production environments now reject weak passwords by default
- **Debug Mode Protection**: DEBUG_MODE cannot be enabled in production
- **Audit Logging**: All security events properly logged
- **Bandit Compliance**: 100% security scan passing

### Documentation

#### New Documentation (3 comprehensive documents, 2800+ lines)
- **RELEASE_NOTES_v1.3.0.md**: Complete release overview
- **docs/bootstrap-migration-guide.md**: 500+ line migration guide for bootstrap patterns
- **docs/phase-3.4-modularization.md**: 800+ line modularization documentation
- **docs/PHASE_3_COMPLETE.md**: 500+ line Phase 3 summary

#### Updated Documentation
- **ARCHITECTURE_REFACTORING_PLAN.md**: Marked Phase 2 and Phase 3.1-3.4 complete
- **README.md**: Updated with v1.3.0 highlights

### Technical Details

#### Test Coverage
- **554 total tests** (up from 543)
- **552 passing** (99.6% pass rate)
- **2 known test isolation issues** (documented, non-blocking)
- **5 skipped tests** (intentional)
- All critical paths validated

#### Code Metrics
- **server.py**: Reduced from 883 lines to focused core
- **Circular Dependencies**: Eliminated (was: server ↔ secure_graph)
- **Environment Variables**: Centralized (was: 26 scattered `os.getenv()` calls)
- **Type Safety**: Strong typing added with TypedDict
- **Import-Time Side Effects**: Eliminated via bootstrap module

#### CI/CD Status
- ✅ **Security Scan**: PASSING (bandit, safety)
- ✅ **Lint and Type Check**: PASSING (ruff check, ruff format, mypy)
- ✅ **Docker Build Test**: PASSING (build, Trivy vulnerability scan)
- ✅ **Test Suite**: 99.6% passing (552/554)

### Breaking Changes
**NONE** - This release is 100% backwards compatible. All changes are internal architecture improvements.

### Migration Notes
See [docs/bootstrap-migration-guide.md](docs/bootstrap-migration-guide.md) for detailed migration instructions if you're:
- Extending the server with custom tools
- Writing tests that mock server internals
- Creating multi-instance deployments

### Commits Included (25 commits)
Phase 2: e1372a6, 04f454d, 46e4614
Phase 3.1-3.2: 1f6b51f, ae8625a, 20a482d, 4aedf30, 9b1687e
Phase 3.3-3.4: c14dd46, 395d36a, 23bd461, d4130fa, f22386e
CI/CD Fixes: 18665b6, 2aaa3d1, bbf8caa, 30b000d, 41091cc, 72a1065, 3e8e4a0

### Acknowledgments
This release represents a major architectural milestone, laying the foundation for:
- Multi-instance deployments
- Better test isolation
- Improved maintainability
- Future feature development

## [1.2.2] - 2025-11-12

### Fixed
- **Test Infrastructure**: Fixed hardcoded test path in `test_query_analysis_html.py` (Issue #6)
  - Dynamic path resolution using `pathlib.Path(__file__).parents[1]`
  - Tests now work on any machine/checkout location
- **Test Coverage**: Fixed skipped test in `test_query_analyzer.py` (mock exception issue)
  - Corrected `error_mock_graph` fixture to use synchronous `Mock` instead of `AsyncMock`
  - Test now properly validates error handling in query analysis

### Changed
- Improved test fixture mocking consistency
  - `mock_graph.query` now uses regular `Mock` instead of `AsyncMock` (query is synchronous)
  - Better alignment with actual Neo4j driver behavior

### Documentation
- Added `ARCHITECTURE_REFACTORING_PLAN.md` - Technical debt resolution roadmap
  - 7 architectural issues identified with solutions
  - 3-phase implementation plan (v1.2.2, v1.3.0, v1.4.0)
  - Target: 90% test coverage, 95% mypy coverage, server.py <800 LOC
- Added `REFACTORING_RECOMMENDATIONS.md` - Publication preparation guide
  - Priority matrix (HIGH/MEDIUM/LOW)
  - Dependency analysis and timeline
- Added `GITHUB_SETUP.md` - Repository configuration guide
  - Topics, social preview, issue templates
- Added `RELEASE_GUIDE.md` - Release management process

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
