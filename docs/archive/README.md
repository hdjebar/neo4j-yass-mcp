# Archived Documentation

This directory contains documentation that has been archived due to implementation changes.

## Rate Limiting Refactoring (2025-11-09)

The following files were archived after the rate limiting implementation was refactored from function-based to decorator-based architecture:

### Outdated Coverage Documentation

- **UNCOVERED_LINES_SUMMARY.md** - References old function-based rate limiting (lines 478-491, 704-717 in server.py)
- **COVERAGE_ANALYSIS.md** - Coverage analysis based on old implementation
- **COVERAGE_ANALYSIS_INDEX.md** - Index of coverage documentation
- **TEST_IMPLEMENTATION_GUIDE.md** - Test templates for old patterns
- **COVERAGE_REFERENCE_CARD.md** - Quick reference with old line numbers
- **ANALYSIS_COMPLETE.txt** - Summary document referencing the above outdated coverage docs

### Why Archived

These files reference the **old function-based rate limiting approach** where:
- Rate limit checks were manual function calls in each tool
- Tests used `@patch("neo4j_yass_mcp.server.check_rate_limit")`
- Line numbers referenced specific rate limiting code blocks

### New Implementation

See [REFACTORING_SUMMARY.md](../../REFACTORING_SUMMARY.md) for details on the new decorator-based architecture.

**New rate limiting files:**
- `src/neo4j_yass_mcp/tool_wrappers.py` - `RateLimiterService` and decorators
- `tests/unit/test_server_rate_limiting.py` - Updated tests
- `examples/rate_limiting_example.py` - Standalone example

### Other Archived Files

This directory also contains historical documentation from GitHub publication preparation and other project milestones.

---

**Last Updated**: 2025-11-09
