# Quick Start Guide

Get Neo4j YASS MCP running in under 5 minutes!

## Prerequisites

- Python 3.11+
- Neo4j 5.x running (or Docker)
- An API key for your LLM provider (OpenAI, Anthropic, or Google)

## Option 1: Quick Start with Docker (Recommended)

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/neo4j-yass-mcp.git
cd neo4j-yass-mcp

cp .env.example .env
```

### 2. Edit `.env` (Minimum Configuration)

```bash
# Neo4j connection (if using external Neo4j)
NEO4J_URI=bolt://host.docker.internal:7687
NEO4J_PASSWORD=your-neo4j-password

# LLM Provider
LLM_PROVIDER=openai  # or anthropic, google-genai
LLM_API_KEY=sk-your-api-key-here

# Security (set strong password!)
ALLOW_WEAK_PASSWORDS=false  # Will fail if password is weak
```

### 3. Start the Server

```bash
docker compose up -d
docker compose logs -f
```

### 4. Test It

```bash
# Check health
curl http://localhost:8000/health

# The server is ready when you see:
# "Neo4j MCP Server initialized successfully"
```

---

## Option 2: Local Python Development

### 1. Install UV (Fast Python Package Manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Setup

```bash
git clone https://github.com/yourusername/neo4j-yass-mcp.git
cd neo4j-yass-mcp

# Create virtual environment and install
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[all]"
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Run

```bash
# Stdio mode (for Claude Desktop)
python server.py

# HTTP mode (for network access)
MCP_TRANSPORT=http MCP_SERVER_HOST=127.0.0.1 MCP_SERVER_PORT=8000 python server.py
```

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
# Start server in HTTP mode
MCP_TRANSPORT=http python server.py &

# In another terminal:
# (Install httpie or use curl)
pip install httpie

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
# Reinstall dependencies
pip install -e ".[all]"

# or with UV
uv pip install -e ".[all]"
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
# Docker
docker compose up -d      # Start
docker compose stop       # Stop
docker compose down       # Stop and remove
docker compose logs -f    # View logs

# Local Python
python server.py          # Run
Ctrl+C                    # Stop
```

### Configuration Files

- `.env` - Your configuration (not in git)
- `.env.example` - Template with all options
- `docker-compose.yml` - Docker deployment
- `pyproject.toml` - Python package config

### Important Directories

- `utilities/` - Security and logging modules
- `tests/` - Test suite
- `docs/` - Documentation
- `data/logs/audit/` - Audit logs (created at runtime)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/neo4j-yass-mcp/issues)
- **Documentation**: [docs/](docs/)
- **Security**: [SECURITY.md](SECURITY.md)

Happy graphing! 🚀
