# GitHub Release Guide - v1.2.1

Complete guide for creating and publishing the v1.2.1 release.

---

## Pre-Release Checklist

Before creating the release, verify:

- [x] **Code quality**: All tests passing (468 passed)
- [x] **CI/CD**: Latest run successful ✅
- [x] **Dependencies**: Updated to latest stable versions
- [x] **Documentation**: README and CHANGELOG up-to-date
- [x] **Version**: pyproject.toml version = "1.2.1"
- [x] **Git**: All changes committed and pushed

---

## Release Process

### Option 1: Create Release via GitHub UI (Recommended)

#### Step 1: Navigate to Releases

1. Go to: https://github.com/hdjebar/neo4j-yass-mcp/releases
2. Click **"Draft a new release"** button

#### Step 2: Configure Release

**Tag version**: `v1.2.1`
- Target: `main` branch
- Click "Create new tag: v1.2.1 on publish"

**Release title**: `v1.2.1 - Critical Dependency Updates & Security Fixes`

**Description** (paste this):

```markdown
## 🔒 Security & Stability Release

This release updates critical dependencies with 11-14 months of security patches, bug fixes, and performance improvements.

### 🎯 Highlights

- **langchain-neo4j**: 0.1.0 → 0.6.0 (11 months of improvements)
- **neo4j driver**: 5.14.0 → 5.28.2 (14 months of security/performance fixes)
- **pydantic**: 2.0.0 → 2.12.4 (latest stable)

### 🛡️ Security Improvements

- ✅ Addressed 14 months of security patches in Neo4j driver
- ✅ Addressed 11 months of security patches in langchain-neo4j
- ✅ Added mTLS support for 2FA authentication (enterprise-grade)
- ✅ Enhanced connection security and error handling

### ⚡ Performance Improvements

- **~100x faster** temporal operations (Neo4j driver 5.28.2)
- Improved schema introspection performance
- Better connection pool handling and stability

### 🐛 Critical Bug Fixes

- **DateTime arithmetic** - Fixed "wildly incorrect" calculations that affected query performance analysis
- GQL-compliant error handling
- Connection pool stability improvements
- Schema introspection bug fixes

### 📦 What's Changed

**Dependencies**:
- `langchain-neo4j>=0.6.0,<1.0.0` (was 0.1.0)
- `neo4j>=5.28.0,<6.0.0` (was 5.14.0)
- `pydantic>=2.10.0,<3.0.0` (was 2.0.0)

### ✅ Testing

- All 468 tests passing
- CI/CD pipeline: ✅ SUCCESS
- Python 3.13 fully supported
- No breaking changes detected

### 📚 Documentation

- [CHANGELOG.md](CHANGELOG.md#L28-L52) - Complete change history
- [REFACTORING_RECOMMENDATIONS.md](REFACTORING_RECOMMENDATIONS.md) - Publication roadmap
- [GITHUB_SETUP.md](GITHUB_SETUP.md) - Repository setup guide

### 🚀 Installation

**Python/UV**:
```bash
pip install neo4j-yass-mcp==1.2.1
# or
uv pip install neo4j-yass-mcp==1.2.1
```

**Docker**:
```bash
docker pull ghcr.io/hdjebar/neo4j-yass-mcp:v1.2.1
```

**From source**:
```bash
git clone https://github.com/hdjebar/neo4j-yass-mcp.git
cd neo4j-yass-mcp
git checkout v1.2.1
uv pip install -e .
```

### ⚠️ Breaking Changes

**None** - This is a drop-in replacement for v1.2.0.

### 🙏 Contributors

- [@hdjebar](https://github.com/hdjebar)
- Claude Code AI Assistant

### 📝 Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete details.

**Full Changelog**: https://github.com/hdjebar/neo4j-yass-mcp/compare/v1.2.0...v1.2.1

---

**Questions?** Open an issue or discussion: https://github.com/hdjebar/neo4j-yass-mcp/discussions
```

#### Step 3: Attach Assets (Optional)

You can attach the following files:
- Source code (auto-attached by GitHub)
- Built wheel/dist files (if published to PyPI)

#### Step 4: Publish

- [ ] **This is a pre-release** - UNCHECK (this is stable)
- [ ] **Set as the latest release** - CHECK
- [ ] **Create a discussion for this release** - CHECK (if Discussions enabled)

Click **"Publish release"**

---

### Option 2: Create Release via GitHub CLI

```bash
# Create and push tag
git tag -a v1.2.1 -m "v1.2.1 - Critical Dependency Updates & Security Fixes"
git push origin v1.2.1

# Create release
gh release create v1.2.1 \
  --title "v1.2.1 - Critical Dependency Updates & Security Fixes" \
  --notes-file - <<'EOF'
## 🔒 Security & Stability Release

This release updates critical dependencies with 11-14 months of security patches,
bug fixes, and performance improvements.

### 🎯 Highlights

- **langchain-neo4j**: 0.1.0 → 0.6.0 (11 months of improvements)
- **neo4j driver**: 5.14.0 → 5.28.2 (14 months of security/performance fixes)
- **pydantic**: 2.0.0 → 2.12.4 (latest stable)

### 🛡️ Security Improvements

- ✅ 14 months of security patches (Neo4j driver)
- ✅ 11 months of security patches (langchain-neo4j)
- ✅ mTLS support for 2FA authentication
- ✅ Enhanced connection security

### ⚡ Performance Improvements

- **~100x faster** temporal operations
- Improved schema introspection
- Better connection pool handling

### 🐛 Critical Bug Fixes

- DateTime arithmetic corrections
- GQL-compliant error handling
- Connection pool stability

### ✅ Testing

- All 468 tests passing
- CI/CD: ✅ SUCCESS
- No breaking changes

See [CHANGELOG.md](CHANGELOG.md) for complete details.

**Full Changelog**: https://github.com/hdjebar/neo4j-yass-mcp/compare/v1.2.0...v1.2.1
EOF
```

---

## Post-Release Actions

After publishing the release:

### 1. Verify Release

- [ ] Visit https://github.com/hdjebar/neo4j-yass-mcp/releases
- [ ] Confirm release is visible and marked as "Latest"
- [ ] Test download links work
- [ ] Verify tag exists: `git tag -l | grep v1.2.1`

### 2. Update Documentation References

If you have docs that reference "latest version", update them:

```bash
# Search for version references
grep -r "1.2.0" docs/ README.md

# Update as needed
```

### 3. Social Announcements (Optional)

Consider announcing on:

**Reddit**:
- r/Python
- r/Neo4j
- r/MachineLearning

**Twitter/X**:
```
🚀 Neo4j YASS MCP v1.2.1 released!

🔒 Critical security updates (14 months of patches)
⚡ 100x faster temporal operations
🐛 DateTime calculation fixes

Full changelog: https://github.com/hdjebar/neo4j-yass-mcp/releases/tag/v1.2.1

#Python #Neo4j #LLM #MCP
```

**LinkedIn**:
```
Excited to announce Neo4j YASS MCP v1.2.1! 🚀

This security-focused release addresses 11-14 months of accumulated patches
in critical dependencies, with performance improvements up to 100x for
temporal operations.

Key updates:
✅ langchain-neo4j 0.6.0 (was 0.1.0)
✅ neo4j driver 5.28.2 (was 5.14.0)
✅ All 468 tests passing
✅ Production-ready

Check it out: https://github.com/hdjebar/neo4j-yass-mcp

#OpenSource #GraphDatabase #AI #Security
```

**Hacker News**:
- Title: "Neo4j YASS MCP – Security-enhanced MCP server for Neo4j with LLM integration"
- URL: https://github.com/hdjebar/neo4j-yass-mcp

**Dev.to** / **Medium**:
Write a blog post about:
- Why you built this
- Key features and security approach
- How the Query Analysis Tool works
- Performance improvements in v1.2.1

### 4. Monitor and Respond

- [ ] Watch GitHub notifications for issues/PRs
- [ ] Respond to questions in Discussions
- [ ] Monitor Stars and Forks growth
- [ ] Engage with community feedback

---

## Rollback Plan (If Needed)

If critical issues are discovered:

### Option 1: Hotfix Release (v1.2.2)

```bash
# Fix the issue
git checkout main
# Make fixes...
git commit -m "hotfix: Critical fix for issue #X"

# Update version to 1.2.2
sed -i '' 's/version = "1.2.1"/version = "1.2.2"/' pyproject.toml

# Create hotfix release
git tag -a v1.2.2 -m "Hotfix: Critical fix"
git push origin v1.2.2
gh release create v1.2.2 --title "v1.2.2 - Hotfix" --notes "Critical fix for..."
```

### Option 2: Mark as Pre-release

1. Go to release page
2. Click "Edit release"
3. Check "This is a pre-release"
4. Add warning notice to release notes

### Option 3: Delete Release (Last Resort)

```bash
# Delete tag locally
git tag -d v1.2.1

# Delete tag on remote
git push origin :refs/tags/v1.2.1

# Delete release via GitHub UI or CLI
gh release delete v1.2.1 --yes
```

---

## Version Numbering Guide

For future releases, follow [Semantic Versioning](https://semver.org/):

**Format**: MAJOR.MINOR.PATCH

- **MAJOR** (1.x.x): Breaking changes
- **MINOR** (x.2.x): New features (backward-compatible)
- **PATCH** (x.x.1): Bug fixes (backward-compatible)

Examples:
- Bug fix: 1.2.1 → 1.2.2
- New feature: 1.2.1 → 1.3.0
- Breaking change: 1.2.1 → 2.0.0

---

## Success Metrics

Track these metrics post-release:

- [ ] GitHub Stars: Target 10+ in first week
- [ ] Forks: Target 5+ in first week
- [ ] Issues opened: Shows community engagement
- [ ] Pull requests: Shows community contribution
- [ ] Downloads: Track via GitHub Insights

---

**Ready to release?** Follow Option 1 or 2 above, then complete the Post-Release Actions!

**Questions?** See [GITHUB_SETUP.md](GITHUB_SETUP.md) or open a discussion.
