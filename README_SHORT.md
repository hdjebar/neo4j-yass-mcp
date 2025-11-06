# Neo4j YASS MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-green.svg)](https://neo4j.com/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-00ADD8)](https://modelcontextprotocol.io/)
[![Security](https://img.shields.io/badge/Security-Hardened-red.svg)](docs/SECURITY_FIXES.md)

**YASS** (Yet Another Secure Server) - A production-ready, security-enhanced Model Context Protocol (MCP) server for Neo4j graph databases with LLM integration.

---

## 🎯 Overview

Neo4j YASS MCP Server enables Large Language Models (LLMs) to interact with Neo4j graph databases through natural language queries. It combines **LangChain's GraphCypherQAChain** with **enterprise-grade security features** including query sanitization, audit logging, and comprehensive access controls.

### Why YASS?

- 🔒 **Security First**: Query sanitization, UTF-8 attack prevention, weak password detection
- 📝 **Compliance Ready**: Comprehensive audit logging with PII redaction
- ⚡ **High Performance**: Async architecture with connection pooling and parallelization
- 🛡️ **Defense in Depth**: Multiple security layers (sanitizer + LangChain validation + read-only mode)
- 🎛️ **Production Ready**: Configurable, tested, and documented for enterprise deployments

---

## ✨ Key Features

### Security Features

- **Query Sanitization** (SISO Prevention)
  - Cypher injection blocking
  - SQL injection pattern detection
  - UTF-8/Unicode attack prevention (zero-width chars, homographs, directional overrides)
  - Dangerous APOC procedure filtering
  - Schema change protection

- **Access Control**
  - Read-only mode enforcement
  - Weak password detection and blocking
  - Configurable LangChain safety controls

- **Error Handling**
  - Sanitized error messages (prevents information leakage)
  - Debug mode for development
  - Full error logging to audit logs

### Compliance Features

- **Audit Logging**
  - JSON/text format logs
  - Automatic rotation (daily, weekly, size-based)
  - Configurable retention policies
  - Optional PII redaction
  - Complete query/response/error tracking

### Performance Features

- **Async Architecture**
  - Non-blocking I/O with asyncio
  - ThreadPoolExecutor for sync operations
  - Configurable worker pool size

- **Connection Management**
  - Neo4j driver connection pooling
  - Query timeout configuration
  - Response size limiting

### LLM Integration

- **Multi-Provider Support**
  - OpenAI (GPT-4, GPT-3.5)
  - Anthropic (Claude)
  - Google (Gemini)

- **Natural Language Queries**
  - Automatic Cypher query generation
  - Schema-aware query construction
  - Response token limiting for cost control

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Neo4j 5.x (Community or Enterprise)
- Docker (optional, for containerized deployment)

### Installation

#### Option 1: UV (Recommended)

```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/yourusername/neo4j-yass-mcp.git
cd neo4j-yass-mcp

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[all]"
```

#### Option 2: pip

```bash
git clone https://github.com/yourusername/neo4j-yass-mcp.git
cd neo4j-yass-mcp

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[all]"
```

#### Option 3: Docker

```bash
git clone https://github.com/yourusername/neo4j-yass-mcp.git
cd neo4j-yass-mcp

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start with Docker Compose
docker compose up -d
```

### Configuration

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Configure Neo4j connection**:
   ```bash
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-strong-password  # Change this!
   NEO4J_DATABASE=neo4j
   ```

3. **Configure LLM provider**:
   ```bash
   LLM_PROVIDER=openai  # or anthropic, google-genai
   LLM_MODEL=gpt-4
   LLM_API_KEY=sk-your-api-key-here
   LLM_TEMPERATURE=0.0
   ```

4. **Security settings** (Production):
   ```bash
   # Password security
   ALLOW_WEAK_PASSWORDS=false

   # LangChain safety
   LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=false

   # Error messages
   DEBUG_MODE=false

   # Query sanitization
   SANITIZER_ENABLED=true
   SANITIZER_STRICT_MODE=true

   # Audit logging
   AUDIT_LOG_ENABLED=true
   AUDIT_LOG_FORMAT=json
   AUDIT_LOG_RETENTION_DAYS=90
   ```

### Running the Server

#### Stdio Mode (for Claude Desktop, local CLI)

```bash
python server.py
```

#### HTTP Mode (for network access)

```bash
MCP_TRANSPORT=http MCP_SERVER_HOST=0.0.0.0 MCP_SERVER_PORT=8000 python server.py
```

#### Docker

```bash
docker compose up -d
docker compose logs -f
```

---

## 📖 Usage

### MCP Tools

The server provides the following MCP tools:

#### `query_graph(query: str)`
Query the Neo4j graph using natural language.

```python
# Example
query_graph("Who starred in Top Gun?")
```

#### `execute_cypher(cypher_query: str, parameters: dict)`
Execute a raw Cypher query (requires write permissions if not read-only).

```python
# Example
execute_cypher(
    "MATCH (n:Person {name: $name}) RETURN n",
    {"name": "Tom Cruise"}
)
```

#### `refresh_schema()`
Refresh the cached database schema.

```python
refresh_schema()
```

### MCP Resources

#### `neo4j://schema`
Get the complete Neo4j database schema.

#### `neo4j://database-info`
Get database connection information.

---

## 🔒 Security

### Security Layers

1. **Query Sanitizer** - Blocks malicious queries before execution
2. **LangChain Validation** - Optional secondary validation (configurable)
3. **Read-Only Mode** - Enforces read-only access at query level
4. **Password Validation** - Prevents weak/default passwords
5. **Error Sanitization** - Prevents information leakage

### Security Best Practices

✅ **Do**:
- Use strong passwords (12+ characters, mix of types)
- Enable audit logging in production
- Keep `SANITIZER_ENABLED=true`
- Set `DEBUG_MODE=false` in production
- Review audit logs regularly

❌ **Don't**:
- Use default passwords (`password`, `password123`, `neo4j`)
- Disable the sanitizer without additional controls
- Set `LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=true` without understanding risks
- Expose debug error messages in production

See [SECURITY_FIXES.md](docs/SECURITY_FIXES.md) for complete security documentation.

---

## 🧪 Testing

### Run Tests

```bash
# All tests
make test

# With coverage
make test-cov

# Specific tests
pytest tests/test_utf8_attacks.py -v
```

### Security Testing

```bash
# Test UTF-8 attack prevention
python tests/test_utf8_attacks.py

# Test weak password detection
NEO4J_PASSWORD=password123 python server.py  # Should fail

# Test read-only mode
NEO4J_READ_ONLY=true python server.py
```

---

## 🛠️ Development

### Development Setup

```bash
# Install with development dependencies
uv pip install -e ".[dev]"

# Run linters
make lint

# Auto-fix linting issues
make lint-fix

# Format code
make format

# Security checks
make security
```

### Available Make Commands

```bash
make install-dev    # Install all dev dependencies
make test           # Run all tests
make test-cov       # Run tests with coverage
make lint           # Run linters (ruff + mypy)
make lint-fix       # Auto-fix linting issues
make format         # Format code
make security       # Run security checks
make docker-up      # Start Docker services
make docker-logs    # View Docker logs
make clean          # Clean build artifacts
```

---

## 📊 Configuration Reference

### Environment Variables

#### Core Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio`, `http`, `sse` |
| `MCP_SERVER_HOST` | `127.0.0.1` | Server host (for http/sse) |
| `MCP_SERVER_PORT` | `8000` | Server port (for http/sse) |

#### Neo4j Connection
| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USERNAME` | `neo4j` | Database username |
| `NEO4J_PASSWORD` | `password` | Database password (change this!) |
| `NEO4J_DATABASE` | `neo4j` | Database name |
| `NEO4J_READ_TIMEOUT` | `30` | Query timeout (seconds) |

#### Security
| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOW_WEAK_PASSWORDS` | `false` | Allow weak passwords (dev only) |
| `LANGCHAIN_ALLOW_DANGEROUS_REQUESTS` | `false` | Bypass LangChain safety |
| `DEBUG_MODE` | `false` | Detailed error messages |
| `SANITIZER_ENABLED` | `true` | Enable query sanitization |
| `SANITIZER_STRICT_MODE` | `false` | Block suspicious patterns |
| `NEO4J_READ_ONLY` | `false` | Read-only mode |

#### LLM
| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | Provider: `openai`, `anthropic`, `google-genai` |
| `LLM_MODEL` | `gpt-4` | Model name |
| `LLM_API_KEY` | - | API key (required) |
| `LLM_TEMPERATURE` | `0.0` | Temperature (0.0-1.0) |

See [.env.example](.env.example) for complete configuration options.

---

## 📁 Project Structure

```
neo4j-yass-mcp/
├── server.py              # Main MCP server
├── config.py              # Configuration and LLM setup
├── utilities/             # Security and logging utilities
│   ├── __init__.py
│   ├── sanitizer.py       # Query sanitization
│   └── audit_logger.py    # Audit logging
├── tests/                 # Test suite
│   ├── __init__.py
│   └── test_utf8_attacks.py
├── docs/                  # Documentation
│   ├── SECURITY_FIXES.md
│   └── FIXES_APPLIED.md
├── .env.example           # Environment template
├── docker-compose.yml     # Docker deployment
├── pyproject.toml         # Python package config
├── Makefile               # Development commands
└── README.md              # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow existing code style
4. Add tests for new functionality
5. Update documentation
6. Commit with clear messages
7. Push to your branch
8. Open a Pull Request

See our [Code of Conduct](CODE_OF_CONDUCT.md) and [Contributing Guide](CONTRIBUTING.md).

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Neo4j](https://neo4j.com/) - Graph database platform
- [LangChain](https://python.langchain.com/) - LLM integration framework
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/neo4j-yass-mcp/issues)
- **Documentation**: [docs/](docs/)
- **Security**: See [SECURITY.md](SECURITY.md) for reporting vulnerabilities

---

## 🗺️ Roadmap

### Short Term
- [ ] Rate limiting for API endpoints
- [ ] Query timeout configuration
- [ ] Connection pool size limits
- [ ] Integration tests

### Medium Term
- [ ] Query result caching
- [ ] Prometheus metrics
- [ ] Automated security scanning
- [ ] Performance benchmarking

### Long Term
- [ ] JWT authentication
- [ ] OAuth2/OIDC support
- [ ] Role-based access control (RBAC)
- [ ] Multi-tenancy support

---

**Built with ❤️ for secure LLM-powered graph database applications**
