# Neo4j YASS MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Neo4j 5.x](https://img.shields.io/badge/neo4j-5.x-green.svg)](https://neo4j.com/)
[![FastMCP](https://img.shields.io/badge/framework-FastMCP-orange.svg)](https://github.com/jlowin/fastmcp)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Yet Another Secure Server (YASS)** - A production-ready, security-enhanced Model Context Protocol (MCP) server that provides Neo4j graph database querying capabilities using LangChain's GraphCypherQAChain for natural language to Cypher query translation.

> Transform natural language into graph insights with enterprise-grade security and compliance.

## Features

### Core Capabilities
- 🔍 **Natural Language Queries**: Ask questions in plain English and get answers from your Neo4j graph
- ⚡ **Async & Parallel Execution**: Handle multiple concurrent queries with async/await support
- 🔌 **Multiple Transports**: stdio (local), HTTP (modern network), or SSE (legacy) modes
- 🎯 **Automatic Port Allocation**: Intelligently finds available ports to avoid conflicts

### Security & Compliance
- 🛡️ **Query Sanitization (SISO Prevention)**: Blocks Cypher injection, UTF-8 attacks, and malicious patterns
- 🔒 **Read-Only Access Control**: Restrict to read-only queries for maximum security
- 📝 **Comprehensive Audit Logging**: Full compliance logging for GDPR, HIPAA, SOC 2, PCI-DSS
- 🚫 **UTF-8 Attack Prevention**: Blocks homographs, zero-width chars, directional overrides

### Performance & Scale
- 📊 **Response Size Limiting**: Automatic truncation to manage LLM context limits
- 🎛️ **Token-Based Truncation**: Smart response sizing for optimal LLM performance
- 🔄 **Connection Pooling**: Efficient Neo4j connection management

### Developer Experience
- 🤖 **Multiple LLM Providers**: OpenAI, Anthropic (Claude), Google Generative AI
- 🚀 **FastMCP Framework**: Built with modern FastMCP using decorators
- 📦 **UV Package Manager**: Fast, modern Python package management
- 📚 **MCP Resources**: Access database schema and connection information
- 🛠️ **MCP Tools**: Query with natural language, execute raw Cypher, refresh schema

## Quick Start

### Prerequisites

**Required:**
- Python 3.10+ (for Python mode) OR Docker (for containerized mode)
- **Neo4j 5.x database** (separate instance - see [Neo4j Setup](#neo4j-setup) below)
  - **APOC plugin installed and enabled** (required for advanced operations)
  - Bolt protocol accessible (default port 7687)
- API key for your chosen LLM provider (OpenAI, Anthropic, or Google)

**Optional:**
- [UV package manager](https://github.com/astral-sh/uv) (for Python mode, recommended)

### Neo4j Setup

This MCP server requires a **separate Neo4j instance** with **APOC plugin** (mandatory) and **GDS plugin** (recommended) enabled.

#### Required Plugins

| Plugin | Status | Purpose | Installation |
|--------|--------|---------|--------------|
| **APOC Core** | ✅ **MANDATORY** | Schema introspection, utilities (required by LangChain) | See options below |
| **GDS** | ⚠️ Recommended | Graph algorithms, machine learning | See options below |

#### Why These Plugins Are Required

##### APOC Core (Mandatory)

This MCP server uses **LangChain's Neo4jGraph** for schema introspection and query generation. LangChain internally calls APOC procedures to retrieve the graph schema:

- `apoc.meta.nodeTypeProperties()` - Retrieves node labels and their properties
- `apoc.meta.relTypeProperties()` - Retrieves relationship types and their properties
- Schema information is essential for LLM-generated Cypher queries

**What happens without APOC:**

```text
❌ Neo4jError: There is no procedure with the name `apoc.meta.nodeTypeProperties`
❌ Schema retrieval fails → LLM cannot generate accurate Cypher queries
❌ MCP server tools will fail to execute
```

##### GDS - Graph Data Science (Recommended)

The GDS plugin enables advanced graph algorithms that enhance query capabilities:

- **Pathfinding**: Shortest path, all simple paths, A* algorithm
- **Centrality**: PageRank, betweenness, closeness (identify important nodes)
- **Community Detection**: Louvain, Label Propagation (discover clusters)
- **Similarity**: Node similarity, cosine similarity (recommendations)
- **Graph Embeddings**: Node2Vec, GraphSAGE (machine learning features)

**What happens without GDS:**

```text
⚠️  Advanced graph algorithms are unavailable
⚠️  Limited to basic Cypher pattern matching
✅  Basic MCP server functionality still works
```

##### Installation Priority

1. **APOC Core** - Install first (mandatory for server operation)
2. **GDS** - Install second (recommended for advanced analytics)

---

#### Option 1: Use neo4j-stack with NEO4J_PLUGINS ⭐ **RECOMMENDED**

The `neo4j-stack/neo4j` service automatically downloads APOC and GDS plugins using the built-in `NEO4J_PLUGINS` environment variable:

```bash
# Navigate to neo4j-stack directory
cd ../neo4j

# Start Neo4j (plugins download automatically on first startup)
docker-compose up -d

# Verify plugins are installed (wait 30-60s for Neo4j to start)
docker-compose exec neo4j cypher-shell -u neo4j -p password123 \
  "RETURN apoc.version() AS apoc, gds.version() AS gds;"
```

**How it works:**
- Uses `NEO4J_PLUGINS='["apoc", "graph-data-science"]'` in [docker-compose.yml](../neo4j/docker-compose.yml#L28)
- Plugins download automatically from Neo4j's official repository on container startup
- Downloads are cached in `./plugins` volume for faster restarts
- No custom Dockerfile or manual downloads needed

**Configuration in docker-compose.yml:**
```yaml
environment:
  NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
volumes:
  - ./plugins:/plugins  # Persists downloaded plugins
```

**Benefits:**
- ✅ Zero configuration - works out of the box
- ✅ Official Neo4j feature (maintained by Neo4j Labs)
- ✅ Automatic version matching (downloads compatible plugin versions)
- ✅ Plugins cached in volume (no re-download on container restart)
- ✅ No custom image build required
- ✅ Works offline after first download (plugins persisted in `./plugins` volume)

**When it needs internet:**
- ⚠️ First container creation (downloads plugins once)
- ⚠️ After deleting `./plugins` folder
- ✅ No internet needed after plugins are cached in volume

---

#### Option 2: Manual Plugin Download to plugins/ Folder

If you prefer manual control, download plugins to the `plugins/` directory:

```bash
# Navigate to neo4j-stack/neo4j directory
cd ../neo4j

# Create plugins directory
mkdir -p plugins

# Download APOC Core (MANDATORY)
curl -L https://github.com/neo4j/apoc/releases/download/5.25.1/apoc-5.25.1-core.jar \
  -o plugins/apoc-5.25.1-core.jar

# Download GDS (RECOMMENDED)
curl -L https://graphdatascience.ninja/neo4j-graph-data-science-2.12.1.jar \
  -o plugins/neo4j-graph-data-science-2.12.1.jar

# Start Neo4j (will mount plugins/ folder)
docker-compose up -d
```

**Plugin Sources:**
- APOC Core: [github.com/neo4j/apoc/releases](https://github.com/neo4j/apoc/releases)
- GDS: [graphdatascience.ninja](https://graphdatascience.ninja/)

**When to use:**
- You need specific plugin versions (not latest compatible)
- You want full control over plugin downloads
- You're working offline or in air-gapped environments

---

#### Option 3: Custom Docker Build with Baked-In Plugins

Build a custom Neo4j image with plugins pre-installed (alternative to `NEO4J_PLUGINS`):

```bash
# Navigate to neo4j-stack directory
cd ../neo4j

# Update docker-compose.yml to use the custom Dockerfile:
# Uncomment the 'build' section and comment out 'image' line
# See Dockerfile.custom-build-alternative for details

# Build custom image
docker-compose build

# Start Neo4j (plugins already in image)
docker-compose up -d
```

**Configuration reference:** See [Dockerfile.custom-build-alternative](../neo4j/Dockerfile.custom-build-alternative)

**When to use:**
- You need specific plugin versions (not latest compatible)
- You want plugins baked into image (immutable infrastructure)
- You're building for air-gapped environments (no internet at runtime)
- You want faster container startup (plugins pre-downloaded)

**Trade-offs:**
- ✅ Faster startup (plugins pre-installed in image)
- ✅ Works offline (no download on startup)
- ❌ Requires custom image build step
- ❌ More complex updates (rebuild image for new plugin versions)

---

#### Option 4: Standalone Neo4j with Docker

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
  -v $PWD/data/neo4j/data:/data \
  neo4j:5.25-community
```

**What `NEO4J_PLUGINS` does:**

The `NEO4J_PLUGINS` environment variable is a **built-in Neo4j Docker feature** that automatically downloads and installs plugins during container startup.

- **Format**: JSON array of plugin names: `'["plugin1", "plugin2"]'`
- **When it runs**: On container startup (before Neo4j starts)
- **Where it downloads from**: Neo4j's official plugin repository
- **Supported plugins**: `apoc`, `apoc-core`, `graph-data-science`, `bloom`, `streams`, `n10s`
- **Version matching**: Automatically downloads the plugin version matching your Neo4j version

**How it works internally:**

1. Container starts → checks `NEO4J_PLUGINS` environment variable
2. Downloads each plugin JAR from `https://dist.neo4j.org/` (official repository)
3. Places JAR files in `/var/lib/neo4j/plugins/` directory
4. Configures Neo4j to enable these plugins
5. Starts Neo4j with plugins loaded

**Pros:**
- Zero manual download required
- Version compatibility guaranteed (matches Neo4j version)
- Simple one-line configuration
- Official Neo4j feature (maintained by Neo4j Labs)

**Cons:**
- Requires internet connection on container startup
- Downloads happen every time container is created (not persisted if no volume mount)
- Limited to plugins available in Neo4j's official repository
- Cannot specify specific plugin versions (always uses latest compatible)

**Persistence tip:**
```bash
# Mount plugins directory to persist downloads across container restarts
docker run -d \
  --name neo4j \
  -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
  -v $PWD/data/neo4j/data:/data \
  -v $PWD/data/neo4j/plugins:/plugins \  # ⭐ Persist plugins
  neo4j:5.25-community
```

---

#### Option 5: Neo4j Desktop

1. Download from [neo4j.com/download](https://neo4j.com/download/)
2. Create database
3. Install plugins via Desktop UI:
   - Go to database → Plugins tab
   - Click "Install" for APOC and Graph Data Science

---

#### Option 6: Neo4j AuraDB (Cloud)

- Sign up at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/)
- APOC is **pre-installed** in AuraDB
- GDS available in Enterprise tier
- Set `NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io` in .env

---

#### Verify Plugin Installation

```cypher
// Check APOC version (should return 5.25.1 or similar)
RETURN apoc.version() AS apoc_version;

// Check GDS version (should return 2.12.1 or similar)
RETURN gds.version() AS gds_version;

// List all APOC procedures (should return 100+ procedures)
SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'apoc' RETURN count(name);

// List all GDS procedures (should return 50+ procedures)
SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'gds' RETURN count(name);
```

**Expected output:**
```
╒══════════════╕
│apoc_version  │
╞══════════════╡
│"5.25.1"      │
└──────────────┘

╒═════════════╕
│gds_version  │
╞═════════════╡
│"2.12.1"     │
└─────────────┘
```

### Automated Setup (Recommended)

The fastest way to get started:

```bash
# Run the automated startup script
./run-server.sh

# This will:
# 1. Create/configure .env automatically
# 2. Allocate free port
# 3. Let you choose: Python/UV or Docker
# 4. Start the server
```

### Manual Installation

#### Option 1: Python/UV

```bash
# 1. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Setup environment
cd neo4j-yass-mcp
cp .env.example .env
nano .env  # Edit configuration (set MCP_SERVER_PORT if needed)

# 3. Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 5. Install dependencies
uv pip install -e .

# 6. Run server
python server.py
```

#### Option 2: Docker Compose

```bash
# 1. Setup environment
cd neo4j-yass-mcp
cp .env.example .env
nano .env  # Edit configuration (set MCP_SERVER_PORT if needed)

# 2. Start with Docker
docker-compose up -d

# 4. View logs
docker-compose logs -f
```

### Essential Configuration

```bash
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# LLM Provider
LLM_PROVIDER=openai  # or "anthropic", "google-genai"
LLM_MODEL=gpt-4
LLM_API_KEY=your-api-key-here

# Security (Recommended)
SANITIZER_ENABLED=true           # Query injection protection
NEO4J_READ_ONLY=false            # Set to 'true' for read-only mode
AUDIT_LOG_ENABLED=true           # Compliance logging
```

### Running the Server

**For Claude Desktop (stdio):**
```bash
# .env configuration
MCP_TRANSPORT=stdio

# Run
python server.py
```

**For HTTP Mode (recommended for network):**
```bash
# .env configuration
MCP_TRANSPORT=http
MCP_SERVER_PORT=8000
MCP_SERVER_PATH=/mcp/

# Run
python server.py
# Server will start at http://127.0.0.1:8000/mcp/
```

**For SSE Mode (legacy):**
```bash
# .env configuration
MCP_TRANSPORT=sse
MCP_SERVER_PORT=8000

# Run
python server.py
# Server will start at http://127.0.0.1:8000
```

## Available Tools

### 1. `query_graph(query: str)`

Query the Neo4j graph using natural language. The LLM automatically translates your question into Cypher.

**Example:**
```python
query_graph(query="Who starred in Top Gun?")
```

**Response:**
```json
{
  "question": "Who starred in Top Gun?",
  "answer": "Tom Cruise starred in Top Gun",
  "generated_cypher": "MATCH (a:Actor)-[:ACTED_IN]->(m:Movie {title: 'Top Gun'}) RETURN a.name",
  "success": true
}
```

### 2. `execute_cypher(cypher_query: str, parameters: Optional[Dict])`

Execute raw Cypher queries with full control. **Hidden in read-only mode.**

**Example:**
```python
execute_cypher(
  cypher_query="MATCH (n:Person {name: $name}) RETURN n",
  parameters={"name": "Tom Cruise"}
)
```

### 3. `refresh_schema()`

Refresh the cached Neo4j schema after structural changes.

## Available Resources

### 1. `neo4j://schema`

Access the current Neo4j database schema (node labels, relationships, properties).

### 2. `neo4j://database-info`

Get database connection information and server details.

## Security Features

> **SISO: "Shit In, Shit Out"** - If you accept malicious input, you get compromised output.

### Query Sanitization

Comprehensive protection against injection attacks:

```bash
# Enable (highly recommended!)
SANITIZER_ENABLED=true
SANITIZER_STRICT_MODE=false
SANITIZER_BLOCK_NON_ASCII=false
```

**Protection Layers:**
- ✅ Cypher injection detection
- ✅ Dangerous pattern blocking (file ops, system commands)
- ✅ Parameter validation
- ✅ UTF-8/Unicode attack prevention (homographs, zero-width chars)
- ✅ Query complexity limits

**📖 Detailed Documentation:** [docs/architecture/security.md](docs/architecture/security.md)

### Audit Logging

Full compliance logging for regulatory requirements:

```bash
# Enable
AUDIT_LOG_ENABLED=true
AUDIT_LOG_FORMAT=json
AUDIT_LOG_ROTATION=daily
AUDIT_LOG_RETENTION_DAYS=90
AUDIT_LOG_PII_REDACTION=false
```

**Use Cases:**
- GDPR, HIPAA, SOC 2, PCI-DSS compliance
- Security forensics and incident response
- Performance monitoring
- Usage analytics

**📖 Detailed Documentation:** [docs/architecture/audit-logging.md](docs/architecture/audit-logging.md)

### Read-Only Mode

Prevent write operations by hiding write-capable tools:

```bash
NEO4J_READ_ONLY=true
```

- `execute_cypher` tool hidden from MCP clients
- LLM-generated write queries blocked
- Maximum safety for production environments

## Configuration

### Transport Modes

**stdio (Default for local)** - For Claude Desktop and CLI tools:
```bash
MCP_TRANSPORT=stdio
```

**HTTP (Recommended for network)** ⭐ - Modern Streamable HTTP (MCP 2025):
```bash
MCP_TRANSPORT=http
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8000
MCP_SERVER_PATH=/mcp/
MCP_SERVER_ALLOWED_HOSTS=localhost,127.0.0.1
```
- Full bidirectional communication
- Multiple concurrent clients
- Load balancing and auto-scaling support
- Production-ready for Docker deployments

**SSE (Legacy)** - Server-Sent Events for backward compatibility:
```bash
MCP_TRANSPORT=sse
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8000
MCP_SERVER_ALLOWED_HOSTS=localhost,127.0.0.1
```
- Unidirectional (server → client)
- Consider migrating to HTTP for new deployments

### LLM Providers

**OpenAI:**
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_API_KEY=sk-...
```

**Anthropic (Claude):**
```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_API_KEY=sk-ant-...
```

**Google Generative AI:**
```bash
LLM_PROVIDER=google-genai
LLM_MODEL=gemini-1.5-flash
LLM_API_KEY=...
```

### Multi-Database Support

Neo4j **Enterprise Edition** supports multiple named databases. Connect to specific databases using the `NEO4J_DATABASE` environment variable.

**⚠️ Note:** Neo4j Community Edition supports only ONE user database (`neo4j`).

#### Single Database Selection

Connect to a specific database at startup:

```bash
# Default database (works in both Community & Enterprise)
NEO4J_DATABASE=neo4j

# Custom database (Enterprise Edition only)
NEO4J_DATABASE=analytics
NEO4J_DATABASE=production
```

#### Multi-Instance Pattern (Recommended)

Run multiple MCP server instances, each connected to a different database:

**Using docker-compose.multi-instance.yml:**
```bash
# Start all instances (analytics, production, dev)
docker-compose -f docker-compose.multi-instance.yml up -d

# Access different databases:
# - Analytics:  http://localhost:8001/mcp/
# - Production: http://localhost:8002/mcp/ (read-only)
# - Development: http://localhost:8003/mcp/
```

**Manual multi-instance:**
```bash
# Instance 1: Analytics database
NEO4J_DATABASE=analytics MCP_SERVER_PORT=8001 python server.py

# Instance 2: Production database (read-only)
NEO4J_DATABASE=production NEO4J_READ_ONLY=true MCP_SERVER_PORT=8002 python server.py

# Instance 3: Development database
NEO4J_DATABASE=dev MCP_SERVER_PORT=8003 python server.py
```

#### Community Edition Workarounds

##### Option 1: Label-Based Separation (within single database)

```cypher
// Separate data using labels
CREATE (:Analytics:Product {name: "Widget"})
CREATE (:Production:Product {name: "Gadget"})

// Query specific domain
MATCH (p:Analytics:Product) RETURN p
```

##### Option 2: DozerDB Plugin

- Adds multi-database support to Community Edition
- Install: Add `dozerdb` to Neo4j plugins
- See: [DozerDB Documentation](https://github.com/dozerdb/dozerdb-community)

### Performance Tuning

```bash
# Response size limiting
NEO4J_RESPONSE_TOKEN_LIMIT=10000  # Truncate large responses

# Async workers
MCP_MAX_WORKERS=10  # Concurrent query execution threads

# Neo4j timeout
NEO4J_READ_TIMEOUT=30  # Query timeout in seconds
```

### Logging

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Complete Configuration Reference

See [.env.example](.env.example) for all available configuration options with detailed comments.

## Architecture

### High-Level Overview

```
MCP Client (Claude Desktop, web apps, etc.)
    ↓
FastMCP Server (stdio/HTTP/SSE transport)
    ↓
Security Layer (Sanitizer + Read-Only Check)
    ↓
Audit Logger (Compliance)
    ↓
LangChain GraphCypherQAChain (NL → Cypher)
    ↓
Neo4j Graph Database
```

### Key Components

- **FastMCP**: MCP protocol implementation with decorators
- **LangChain**: Natural language to Cypher translation (GraphCypherQAChain)
- **Query Sanitizer**: Multi-layer injection prevention ([src/neo4j_yass_mcp/security/sanitizer.py](src/neo4j_yass_mcp/security/sanitizer.py))
- **Audit Logger**: Compliance logging ([src/neo4j_yass_mcp/security/audit_logger.py](src/neo4j_yass_mcp/security/audit_logger.py))
- **Async Executor**: Thread pool for parallel Neo4j queries
- **Response Limiter**: Token-based truncation for LLM context management

### Security Architecture

**📖 Detailed Documentation:** [docs/architecture/security.md](docs/architecture/security.md)

**Defense in Depth:**
1. Input sanitization (injection prevention)
2. Access control (read-only mode)
3. Runtime validation (Cypher analysis)
4. Audit logging (forensics)
5. Response limiting (data exfiltration prevention)

## Example Workflows

### Natural Language Query

```
User: "Show me all actors who worked with Tom Cruise"
    ↓
query_graph() tool
    ↓
Sanitizer validates query
    ↓
LangChain generates: MATCH (a:Actor)-[:ACTED_IN]->(:Movie)<-[:ACTED_IN]-(tc:Actor {name: 'Tom Cruise'}) RETURN a.name
    ↓
Sanitizer validates generated Cypher
    ↓
Execute in Neo4j
    ↓
Return results + generated Cypher
```

### Direct Cypher Execution

```
User: Execute custom Cypher with parameters
    ↓
execute_cypher(query, parameters)
    ↓
Sanitizer validates query + parameters
    ↓
Read-only check (if enabled)
    ↓
Execute in Neo4j
    ↓
Audit log: query + response + execution time
    ↓
Return results
```

## Development

### Install Development Dependencies

```bash
uv pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

### Format Code

```bash
black .
ruff check .
```

## Troubleshooting

### Neo4j Connection Issues

1. Verify Neo4j is running: `neo4j status`
2. Check URI format: `bolt://localhost:7687`
3. Verify credentials in `.env`
4. Check firewall settings

### LLM API Issues

1. Verify API key is set correctly
2. Check provider and model names
3. Review LLM provider quotas/limits
4. Check network connectivity

### Schema Not Loading

1. Run `refresh_schema()` tool
2. Check Neo4j database has data
3. Verify database name in `NEO4J_DATABASE`
4. Check Neo4j user permissions

### Sanitizer Blocking Valid Queries

1. Review blocked pattern in error message
2. Adjust `SANITIZER_STRICT_MODE` if too restrictive
3. Enable specific features: `SANITIZER_ALLOW_APOC=true`
4. Check audit logs for details

## Project Structure

```
neo4j-yass-mcp/
├── src/
│   └── neo4j_yass_mcp/          # Main package
│       ├── server.py            # MCP server entry point
│       ├── config/              # Configuration modules
│       │   ├── llm_config.py    # LLM provider configuration
│       │   └── utils.py         # General utilities
│       └── security/            # Security & compliance
│           ├── sanitizer.py     # Query sanitization
│           └── audit_logger.py  # Audit logging
├── tests/                       # Test suite
├── docs/                        # Documentation
├── Dockerfile                   # Container image definition
├── docker-compose.yml           # Multi-container orchestration
├── .dockerignore                # Docker build exclusions
├── run-server.sh                # Automated startup script
├── .env.example                 # Configuration template
├── pyproject.toml               # Package dependencies
└── README.md                    # This file
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Resources

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [LangChain Documentation](https://python.langchain.com/)

## Security Disclosure

For security issues, please email security@[your-domain] instead of using the public issue tracker.

---

**📖 For detailed documentation:**
- Security Architecture: [docs/architecture/security.md](docs/architecture/security.md)
- Audit Logging: [docs/architecture/audit-logging.md](docs/architecture/audit-logging.md)
- Docker Deployment: [docs/architecture/docker-deployment.md](docs/architecture/docker-deployment.md)
- Configuration Reference: [.env.example](.env.example)
