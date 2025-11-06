# Quick Start Guide

Get Neo4j YASS MCP running in under 5 minutes!

## Prerequisites

- Python 3.11+
- Neo4j 5.x running (or Docker)
- An API key for your LLM provider (OpenAI, Anthropic, or Google)

## Option 1: Quick Start with Docker (Recommended)

### 1. Clone and Configure

```bash
git clone https://github.com/hdjebar/neo4j-yass-mcp.git
cd neo4j-yass-mcp

cp .env.example .env
```

### 2. Edit `.env` (Minimum Configuration)

```bash
# Neo4j connection (if using external Neo4j)
NEO4J_URI=bolt://neo4j:7687  # Use container name if Neo4j in same network
# Or: bolt://host.docker.internal:7687 for host Neo4j
NEO4J_PASSWORD=your-neo4j-password

# LLM Provider
LLM_PROVIDER=openai  # or anthropic, google-genai
LLM_API_KEY=sk-your-api-key-here

# Security (set strong password!)
ALLOW_WEAK_PASSWORDS=false  # Will fail if password is weak
```

### 3. Create Network and Start

```bash
# Create network for Neo4j communication (first time only)
make docker-network
# Or: docker network create neo4j-stack

# Start the server (uses uv for 10-100x faster builds!)
make docker-up
# Or: docker compose up -d

# View logs
make docker-logs
# Or: docker compose logs -f
```

**Note:** The Dockerfile uses `uv` with BuildKit cache for dramatically faster builds:

- First build: ~15-25s (vs 60-90s with pip)
- Rebuild: ~2-5s with cache

### 4. Test It

```bash
# Check health
curl http://localhost:8000/health

# Test Neo4j connection
make docker-test-neo4j

# The server is ready when you see:
# "Neo4j MCP Server initialized successfully"
```

---

## Option 2: Local Python Development

### 1. Install uv (Fast Python Package Manager)

**Why uv?** 10-100x faster than pip, with better dependency resolution.

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

### 2. Clone and Setup

```bash
git clone https://github.com/hdjebar/neo4j-yass-mcp.git
cd neo4j-yass-mcp

# Create virtual environment with uv (much faster than python -m venv)
uv venv

# Install dependencies with uv (10-100x faster than pip!)
uv pip install -e ".[all]"

# Note: With uv, you can skip activation and use 'uv run' instead!
# Activation is optional:
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\activate
```

**Performance comparison:**

- **uv pip install**: 2-5 seconds
- **pip install**: 30-60 seconds

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

### 4. Run

```bash
# Using uv run (recommended - no activation needed!)
uv run --module neo4j_yass_mcp.server

# Or shorter with python -m
uv run python -m neo4j_yass_mcp.server

# HTTP mode (for network access)
MCP_TRANSPORT=http MCP_SERVER_HOST=127.0.0.1 MCP_SERVER_PORT=8000 uv run --module neo4j_yass_mcp.server

# Or using Makefile
make run

# Or with activated venv (traditional)
source .venv/bin/activate
python -m neo4j_yass_mcp.server
```

**Why `uv run`?** Automatically uses the virtual environment without activation!

---

## Minimum `.env` Configuration

```bash
# === Neo4j Connection ===
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-strong-password  # CHANGE THIS!
NEO4J_DATABASE=neo4j

# === LLM Provider ===
LLM_PROVIDER=openai  # or: anthropic, google-genai
LLM_MODEL=gpt-4      # or: claude-3-5-sonnet-20241022, gemini-pro
LLM_API_KEY=sk-your-api-key-here
LLM_TEMPERATURE=0.0

# === Security (Production) ===
ALLOW_WEAK_PASSWORDS=false
LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=false
DEBUG_MODE=false
SANITIZER_ENABLED=true
```

---

## Testing Your Installation

### Test Query Sanitizer

```bash
# Using uv run (recommended)
uv run python tests/test_utf8_attacks.py

# Or with activated venv
source .venv/bin/activate
python tests/test_utf8_attacks.py
```

Expected output:
```
Testing improved sanitizer patterns...

✓ BLOCKED: Query chaining with newlines
✓ BLOCKED: Dynamic Cypher
...
```

### Test MCP Tools (HTTP Mode)

```bash
# Start server in HTTP mode with uv run
MCP_TRANSPORT=http uv run --module neo4j_yass_mcp.server &

# In another terminal:
# Install httpie with uv (fast!)
uv pip install httpie

# Get schema
http GET http://localhost:8000/schema

# Query
http POST http://localhost:8000/query query="Show me all node labels"
```

---

## Common Issues

### Issue: "Weak password detected"

**Solution**: Set a strong password in `.env`:
```bash
NEO4J_PASSWORD=MyStr0ng!P@ssw0rd123

# For development only:
ALLOW_WEAK_PASSWORDS=true
```

### Issue: "Cannot connect to Neo4j"

**Solutions**:
```bash
# 1. Check Neo4j is running
docker ps  # or
neo4j status

# 2. Verify connection settings
NEO4J_URI=bolt://localhost:7687  # For local Neo4j
# or
NEO4J_URI=bolt://host.docker.internal:7687  # From Docker to host Neo4j

# 3. Test connection
python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password')); driver.verify_connectivity(); print('Connected!')"
```

### Issue: "Module not found"

**Solution**:
```bash
# Reinstall dependencies with uv (recommended - faster)
uv pip install -e ".[all]"

# Or with pip (slower)
pip install -e ".[all]"

# Verify installation
python -c "import neo4j_yass_mcp; print('✓ Package installed')"
```

---

## Next Steps

1. **Read the Full Documentation**: [README.md](README.md)
2. **Security Hardening**: [SECURITY.md](SECURITY.md)
3. **Configure Advanced Features**: [.env.example](.env.example)
4. **Set Up Audit Logging**: See "Audit Logging" section in README
5. **Deploy to Production**: See "Production Deployment" in README

---

## Quick Reference

### Start/Stop Commands

```bash
# Docker (with uv-powered builds)
make docker-up            # Start (creates network, builds with uv cache)
make docker-down          # Stop
make docker-logs          # View logs
make docker-test-neo4j    # Test Neo4j connection

# Or with Docker Compose directly
docker compose up -d      # Start
docker compose stop       # Stop
docker compose down       # Stop and remove
docker compose logs -f    # View logs

# Local Python (with uv)
uv run --module neo4j_yass_mcp.server   # Run with uv (no activation needed!)
make run                                 # Run using Makefile
Ctrl+C                                   # Stop
```

### Installation Commands

```bash
# Install uv (first time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install (10-100x faster than pip)
uv venv
uv pip install -e ".[all]"

# Run without activation (uv magic!)
uv run --module neo4j_yass_mcp.server
# Or: uv run python -m neo4j_yass_mcp.server

# Or activate and run traditionally
source .venv/bin/activate
python -m neo4j_yass_mcp.server
```

**Traditional method (slower):**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
```

### Configuration Files

- `.env` - Your configuration (not in git)
- `.env.example` - Template with all options
- `docker-compose.yml` - Docker deployment
- `pyproject.toml` - Python package config

### Important Directories

- `src/neo4j_yass_mcp/` - Main application code
  - `config/` - Configuration modules
  - `security/` - Query sanitizer and audit logger
- `tests/` - Test suite
- `docs/` - Documentation
- `data/logs/audit/` - Audit logs (created at runtime)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/neo4j-yass-mcp/issues)
- **Documentation**: [docs/](docs/)
- **Security**: [SECURITY.md](SECURITY.md)

Happy graphing! 🚀
