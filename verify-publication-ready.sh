#!/bin/bash

# Neo4j YASS MCP - Publication Readiness Verification Script
# This script performs automated checks before GitHub publication

set -e

echo "============================================"
echo "Neo4j YASS MCP - Publication Verification"
echo "============================================"
echo ""

ERRORS=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

echo "1. Checking for sensitive files..."
echo "-----------------------------------"

# Check for .env files (only .env.example should exist)
if git ls-files | grep -q "^\.env$"; then
    check_fail ".env file is tracked by git (should be in .gitignore)"
else
    check_pass "No .env file in repository"
fi

if [ -f .env.example ]; then
    check_pass ".env.example exists"
    # Check if .env.example contains actual secrets
    if grep -qE "(sk-[a-zA-Z0-9]{32,}|xoxb-|ghp_|gho_)" .env.example; then
        check_fail ".env.example contains what looks like real API keys"
    else
        check_pass ".env.example has no real secrets"
    fi
else
    check_warn ".env.example not found"
fi

# Check for common secret patterns
echo ""
echo "2. Scanning for potential secrets..."
echo "-------------------------------------"

SECRET_PATTERNS=(
    "sk-[a-zA-Z0-9]{32,}"  # OpenAI API keys
    "AIza[0-9A-Za-z-_]{35}"  # Google API keys
    "xoxb-"  # Slack tokens
    "ghp_"  # GitHub personal access tokens
    "gho_"  # GitHub OAuth tokens
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    if git grep -qE "$pattern" -- ':(exclude).env.example' ':(exclude)docs/*' ':(exclude)verify-publication-ready.sh'; then
        check_fail "Found potential secret matching pattern: $pattern"
    fi
done

if [ $ERRORS -eq 0 ]; then
    check_pass "No obvious secrets found"
fi

# Check documentation files
echo ""
echo "3. Checking core documentation..."
echo "----------------------------------"

REQUIRED_DOCS=(
    "README.md"
    "QUICK_START.md"
    "CONTRIBUTING.md"
    "CODE_OF_CONDUCT.md"
    "LICENSE"
    "SECURITY.md"
    "CHANGELOG.md"
    "docs/README.md"
)

for doc in "${REQUIRED_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        check_pass "$doc exists"
    else
        check_fail "$doc is missing"
    fi
done

# Check GitHub templates
echo ""
echo "4. Checking GitHub templates..."
echo "--------------------------------"

if [ -d .github/ISSUE_TEMPLATE ]; then
    check_pass ".github/ISSUE_TEMPLATE directory exists"
    
    if [ -f .github/ISSUE_TEMPLATE/bug_report.yml ]; then
        check_pass "Bug report template exists"
    else
        check_warn "Bug report template missing"
    fi
    
    if [ -f .github/ISSUE_TEMPLATE/feature_request.yml ]; then
        check_pass "Feature request template exists"
    else
        check_warn "Feature request template missing"
    fi
else
    check_warn ".github/ISSUE_TEMPLATE directory missing"
fi

if [ -f .github/PULL_REQUEST_TEMPLATE.md ]; then
    check_pass "PR template exists"
else
    check_warn "PR template missing"
fi

# Check .gitignore
echo ""
echo "5. Checking .gitignore configuration..."
echo "----------------------------------------"

if [ -f .gitignore ]; then
    check_pass ".gitignore exists"
    
    IGNORE_PATTERNS=(
        "\.env$"
        "\.env\.local"
        "\.venv"
        "secrets/"
        "\*\.key"
        "\*\.pem"
    )
    
    for pattern in "${IGNORE_PATTERNS[@]}"; do
        if grep -qE "$pattern" .gitignore; then
            check_pass ".gitignore includes: $pattern"
        else
            check_warn ".gitignore missing pattern: $pattern"
        fi
    done
else
    check_fail ".gitignore missing"
fi

# Check Docker files
echo ""
echo "6. Checking Docker configuration..."
echo "------------------------------------"

if [ -f Dockerfile ]; then
    check_pass "Dockerfile exists"
else
    check_warn "Dockerfile missing"
fi

if [ -f docker-compose.yml ]; then
    check_pass "docker-compose.yml exists"
    
    # Check if docker-compose has any hardcoded secrets
    if grep -qE "(password:|PASSW|API_KEY:|SECRET)" docker-compose.yml; then
        check_warn "docker-compose.yml may contain hardcoded secrets (verify manually)"
    fi
else
    check_warn "docker-compose.yml missing"
fi

# Check pyproject.toml
echo ""
echo "7. Checking project configuration..."
echo "-------------------------------------"

if [ -f pyproject.toml ]; then
    check_pass "pyproject.toml exists"
    
    # Check for project metadata
    if grep -q "name = \"neo4j-yass-mcp\"" pyproject.toml; then
        check_pass "Project name configured"
    else
        check_warn "Project name not found in pyproject.toml"
    fi
    
    if grep -q "version =" pyproject.toml; then
        VERSION=$(grep "version =" pyproject.toml | head -1 | sed 's/.*version = "\(.*\)".*/\1/')
        check_pass "Version configured: $VERSION"
    else
        check_warn "Version not found in pyproject.toml"
    fi
else
    check_fail "pyproject.toml missing"
fi

# Summary
echo ""
echo "============================================"
echo "Verification Summary"
echo "============================================"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Repository is ready for publication.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review GITHUB_PRE_PUBLICATION_CHECKLIST.md"
    echo "2. Run security scan (git secrets or gitleaks)"
    echo "3. Test Docker build: docker build -t neo4j-yass-mcp:test ."
    echo "4. Commit and push to GitHub"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) found. Review before publishing.${NC}"
    exit 0
else
    echo -e "${RED}✗ $ERRORS error(s) and $WARNINGS warning(s) found.${NC}"
    echo ""
    echo "Please fix errors before publishing to GitHub."
    exit 1
fi
