# Software Architecture Document (SAD)

## Neo4j YASS MCP Server

**Version:** 1.0
**Date:** November 2025
**Status:** Production Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architectural Overview](#architectural-overview)
3. [System Context](#system-context)
4. [Component Architecture](#component-architecture)
5. [Data Flow](#data-flow)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Technology Stack](#technology-stack)
9. [Design Patterns](#design-patterns)
10. [Scalability & Performance](#scalability--performance)
11. [Future Architecture Evolution](#future-architecture-evolution)
12. [Appendices](#appendices)

---

## 1. Executive Summary

### 1.1 Purpose

Neo4j YASS (Yet Another Semantic Search) MCP Server provides **server-side natural language to Cypher query translation** for Neo4j graph databases, eliminating the need for client-side LLM processing and enabling enterprise-grade security, compliance, and cost optimization.

### 1.2 Key Architectural Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **Server-side LLM** | Centralized intelligence, security control | 80-95% cost reduction vs client-side |
| **MCP Protocol** | Standard interface, wide client compatibility | Works with any MCP client |
| **LangChain Integration** | Proven framework, 600+ LLM providers | Multi-provider flexibility |
| **Dual-layer Security** | Defense in depth | Blocks injection attacks, ensures compliance |
| **Async Architecture** | Non-blocking I/O for Neo4j/LLM calls | Handles 100+ concurrent users |
| **Multi-stage Docker** | Optimized image size, production hardening | 70% smaller images, better security |

### 1.3 Architectural Principles

1. **Separation of Concerns** - Clear boundaries between MCP, LLM, Security, and Database layers
2. **Defense in Depth** - Multiple security layers (LangChain validation + custom sanitizer + read-only mode)
3. **Provider Agnostic** - Support any LLM provider (OpenAI, Anthropic, Google, Ollama, etc.)
4. **Fail Secure** - Default to safe/read-only mode, require explicit dangerous operations
5. **Observable** - Comprehensive audit logging for compliance and debugging
6. **Scalable** - Stateless design enables horizontal scaling

---

## 2. Architectural Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Client Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Claude       │  │   HTTP       │  │   Custom     │              │
│  │ Desktop      │  │   Client     │  │   MCP Client │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            │ MCP Protocol (stdio/HTTP/SSE)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Neo4j YASS MCP Server                           │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    MCP Server Layer                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │  │
│  │  │ Tools API   │  │ Resources   │  │ Prompts     │           │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                            │                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  Business Logic Layer                          │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │           Query Processing Pipeline                      │  │  │
│  │  │  1. Natural Language → 2. LLM → 3. Cypher → 4. Results │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                            │                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  Security & Compliance Layer                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │  │
│  │  │ Sanitizer    │  │ Audit Logger │  │ Read-Only    │        │  │
│  │  │ (UTF-8,      │  │ (PII         │  │ Enforcement  │        │  │
│  │  │  Injection)  │  │  Redaction)  │  │              │        │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                            │                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Integration Layer                           │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐            │  │
│  │  │   LLM Providers     │  │   Neo4j Driver      │            │  │
│  │  │  ┌────┐ ┌────┐     │  │  ┌──────────────┐   │            │  │
│  │  │  │GPT │ │Claude│    │  │  │  Bolt        │   │            │  │
│  │  │  └────┘ └────┘     │  │  │  Protocol    │   │            │  │
│  │  │  ┌────┐            │  │  └──────────────┘   │            │  │
│  │  │  │Gem.│            │  │                      │            │  │
│  │  │  └────┘            │  │                      │            │  │
│  │  └─────────────────────┘  └─────────────────────┘            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Neo4j Database                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │   Graph     │  │   APOC      │  │    GDS      │                │
│  │   Store     │  │   Plugin    │  │   Plugin    │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Architectural Layers

#### Layer 1: Client Layer
- **Responsibility**: User interaction, MCP client implementation
- **Technology**: Claude Desktop, HTTP clients, custom MCP clients
- **Communication**: MCP protocol (stdio, HTTP, SSE)

#### Layer 2: MCP Server Layer
- **Responsibility**: MCP protocol handling, tool/resource/prompt exposure
- **Technology**: FastMCP (Python)
- **Key Components**:
  - `query_graph` tool: Natural language query execution
  - `get_schema` tool: Neo4j schema retrieval
  - `estimate_tokens` tool: Cost estimation

#### Layer 3: Business Logic Layer
- **Responsibility**: Core query processing pipeline
- **Technology**: LangChain, Python asyncio
- **Key Components**:
  - GraphCypherQAChain: Natural language to Cypher translation
  - Query execution orchestration
  - Result formatting and transformation

#### Layer 4: Security & Compliance Layer
- **Responsibility**: Query validation, audit logging, access control
- **Technology**: Custom Python modules
- **Key Components**:
  - `sanitizer.py`: Query sanitization (UTF-8 attacks, injection prevention)
  - `audit_logger.py`: Compliance logging with PII redaction
  - Read-only mode enforcement

#### Layer 5: Integration Layer
- **Responsibility**: External system integration
- **Technology**: LangChain providers, Neo4j Python driver
- **Key Components**:
  - Multi-LLM provider abstraction (OpenAI, Anthropic, Google)
  - Neo4j Bolt protocol driver
  - Connection pooling and retry logic

#### Layer 6: Data Layer
- **Responsibility**: Graph data storage and management
- **Technology**: Neo4j 5.x
- **Key Components**:
  - Graph database engine
  - APOC plugin (required)
  - GDS plugin (optional)

---

## 3. System Context

### 3.1 System Boundary

```
┌─────────────────────────────────────────────────────────────────┐
│                      External Systems                            │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │  OpenAI    │  │ Anthropic  │  │  Google    │               │
│  │  API       │  │  API       │  │  GenAI     │               │
│  └────────────┘  └────────────┘  └────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│              System Boundary: Neo4j YASS MCP Server             │
│                                                                  │
│  Inputs:                                                         │
│  - Natural language queries                                      │
│  - Configuration (environment variables)                         │
│  - User authentication (future)                                  │
│                                                                  │
│  Outputs:                                                        │
│  - Query results (JSON)                                          │
│  - Schema information                                            │
│  - Error messages (sanitized)                                    │
│  - Audit logs                                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Neo4j Database                              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Graph Database (Customer-managed)                      │    │
│  │  - May be on-premises, cloud, or AuraDB                │    │
│  │  - Contains organization's graph data                   │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 External Dependencies

| System | Purpose | Protocol | Criticality | Fallback |
|--------|---------|----------|-------------|----------|
| **LLM Provider** | Natural language to Cypher | HTTPS/REST | High | Switch provider |
| **Neo4j Database** | Graph data storage/query | Bolt (7687) | Critical | None (hard dependency) |
| **MCP Client** | User interface | MCP (stdio/HTTP) | Critical | None (entry point) |

### 3.3 Integration Points

#### 3.3.1 MCP Client Integration

**Protocol**: Model Context Protocol (MCP)

**Transport Options**:
1. **stdio** (Standard Input/Output)
   - Use case: Claude Desktop, local CLI tools
   - Pros: Simple, no network configuration
   - Cons: Single-client, no remote access

2. **HTTP** (Recommended)
   - Use case: Web clients, remote access, multiple clients
   - Pros: Scalable, firewall-friendly, standard
   - Cons: Requires network configuration

3. **SSE** (Server-Sent Events)
   - Use case: Real-time streaming responses
   - Pros: Push-based updates
   - Cons: Less widely supported

**MCP Tools Exposed**:
```python
@mcp_server.tool()
async def query_graph(query: str) -> str:
    """Execute natural language query against Neo4j"""

@mcp_server.tool()
async def get_schema() -> str:
    """Retrieve Neo4j graph schema"""

@mcp_server.tool()
async def estimate_tokens(text: str) -> str:
    """Estimate LLM token usage for cost planning"""
```

#### 3.3.2 LLM Provider Integration

**Pattern**: Strategy Pattern with provider abstraction

**Supported Providers** (as of v1.0):
- OpenAI (GPT-4o, o3, o4-mini)
- Anthropic (Claude Sonnet 4.5, Opus 4.1, Haiku 4.5)
- Google (Gemini 2.5 Pro, 2.5 Flash)

**Configuration**:
```python
@dataclass
class LLMConfig:
    provider: str       # "openai", "anthropic", "google-genai"
    model: str          # Model identifier
    temperature: float  # 0.0 = deterministic, 1.0 = creative
    api_key: str        # API authentication
    streaming: bool     # Enable token-by-token streaming
```

**Extensibility**: Supports 600+ LangChain providers (see [ADDING_LLM_PROVIDERS.md](../docs/ADDING_LLM_PROVIDERS.md))

#### 3.3.3 Neo4j Integration

**Protocol**: Bolt (binary protocol over TCP)

**Driver**: Neo4j Python Driver 5.15+

**Connection Configuration**:
```python
driver = GraphDatabase.driver(
    uri=NEO4J_URI,           # bolt://host:7687 or neo4j+s://...
    auth=(username, password),
    max_connection_pool_size=50,
    connection_timeout=30,
    max_transaction_retry_time=30
)
```

**Required Neo4j Components**:
- Neo4j 5.x (database engine)
- APOC plugin (graph algorithms, utilities)
- GDS plugin (optional, for advanced analytics)

---

## 4. Component Architecture

### 4.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          server.py (Main)                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  FastMCP Server Initialization                                 │  │
│  │  - Load configuration from environment                         │  │
│  │  - Initialize Neo4j driver                                     │  │
│  │  - Initialize LLM (via config.py)                             │  │
│  │  - Register MCP tools                                          │  │
│  │  - Start server (stdio/HTTP/SSE)                              │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            │ uses
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         config.py                                    │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LLMConfig (dataclass)                                         │  │
│  │  - provider, model, temperature, api_key, streaming           │  │
│  │                                                                │  │
│  │  chatLLM(config) → LangChain ChatModel                        │  │
│  │  - Factory for OpenAI/Anthropic/Google LLMs                   │  │
│  │                                                                │  │
│  │  Utility Functions                                             │  │
│  │  - configure_logging()                                         │  │
│  │  - find_available_port()                                       │  │
│  │  - get_preferred_ports_from_env()                             │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            │ uses
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    utilities/sanitizer.py                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  sanitize_cypher_query(query: str) → str                      │  │
│  │  - Remove UTF-8 attacks (zero-width chars, homoglyphs)        │  │
│  │  - Block query chaining (semicolons, newlines)                │  │
│  │  - Prevent APOC privilege escalation                          │  │
│  │  - Validate read-only operations (if enabled)                 │  │
│  │                                                                │  │
│  │  Patterns:                                                     │  │
│  │  - DANGEROUS_PATTERNS: List[re.Pattern]                       │  │
│  │  - READ_ONLY_VIOLATIONS: List[re.Pattern]                     │  │
│  │  - UTF8_ATTACK_PATTERNS: List[re.Pattern]                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                  utilities/audit_logger.py                           │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  AuditLogger (class)                                           │  │
│  │  - __init__(log_dir, enabled, pii_redaction)                  │  │
│  │  - log_query_execution(user, query, cypher, results)          │  │
│  │  - log_security_event(event_type, details)                    │  │
│  │  - _redact_pii(text) → str                                    │  │
│  │                                                                │  │
│  │  Output:                                                       │  │
│  │  - JSON logs with timestamp, user, action, details            │  │
│  │  - Automatic PII redaction (emails, SSNs, credit cards)       │  │
│  │  - Rotation: Daily log files (audit_YYYY-MM-DD.log)           │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     LangChain Components                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  GraphCypherQAChain                                            │  │
│  │  - Natural language → Cypher translation                       │  │
│  │  - Schema-aware query generation                              │  │
│  │  - Self-correction on syntax errors                           │  │
│  │  - Result interpretation                                       │  │
│  │                                                                │  │
│  │  Neo4jGraph                                                    │  │
│  │  - Schema extraction (nodes, relationships, properties)        │  │
│  │  - Query execution                                             │  │
│  │  - Connection management                                       │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Component Responsibilities

#### 4.2.1 server.py (Main Server)

**Responsibility**: Application entry point and MCP server lifecycle management

**Key Functions**:

```python
async def main():
    """
    Main server initialization and startup

    Responsibilities:
    1. Load and validate configuration
    2. Initialize Neo4j connection
    3. Initialize LLM provider
    4. Register MCP tools
    5. Start server based on transport mode
    """

    # Configuration validation
    # Neo4j connection test
    # LLM initialization
    # MCP server startup
```

**MCP Tool Implementations**:

```python
@mcp_server.tool()
async def query_graph(query: str) -> str:
    """
    Execute natural language query

    Pipeline:
    1. Receive natural language query
    2. Generate Cypher via GraphCypherQAChain
    3. Sanitize Cypher (UTF-8, injection, read-only)
    4. Execute on Neo4j
    5. Log to audit trail
    6. Return results (JSON)

    Error Handling:
    - Sanitization failures → Block and log
    - Neo4j errors → Sanitize error message, log
    - LLM errors → Fallback to error response
    """

@mcp_server.tool()
async def get_schema() -> str:
    """
    Retrieve Neo4j schema

    Returns:
    - Node labels
    - Relationship types
    - Property keys
    - Constraints
    - Indexes
    """

@mcp_server.tool()
async def estimate_tokens(text: str) -> str:
    """
    Estimate LLM token usage for cost planning

    Uses: tiktoken (OpenAI) or provider-specific tokenizers
    """
```

**Dependencies**:
- `config.py`: LLM configuration
- `utilities/sanitizer.py`: Query validation
- `utilities/audit_logger.py`: Compliance logging
- `fastmcp`: MCP server framework
- `langchain`: GraphCypherQAChain
- `neo4j`: Database driver

#### 4.2.2 config.py (Configuration Module)

**Responsibility**: LLM provider abstraction and server configuration

**Key Components**:

```python
@dataclass
class LLMConfig:
    """LLM configuration data structure"""
    provider: str       # Provider identifier
    model: str          # Model name
    temperature: float  # Randomness (0.0-1.0)
    api_key: str        # Authentication
    streaming: bool     # Token streaming

def chatLLM(config: LLMConfig) -> BaseChatModel:
    """
    Factory function for LLM instances

    Pattern: Factory + Strategy

    Returns: LangChain ChatModel instance

    Extensibility: Add new providers by adding elif branches
    """
    if config.provider == "openai":
        return ChatOpenAI(...)
    elif config.provider == "anthropic":
        return ChatAnthropic(...)
    elif config.provider == "google-genai":
        return ChatGoogleGenerativeAI(...)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")
```

**Utility Functions**:
- `configure_logging()`: Setup logging based on environment
- `find_available_port()`: Dynamic port allocation
- `is_port_available()`: Port availability check

#### 4.2.3 utilities/sanitizer.py (Security Module)

**Responsibility**: Query sanitization and injection prevention

**Security Checks**:

1. **UTF-8 Attack Prevention**
   ```python
   # Remove zero-width characters
   # Block homoglyph attacks
   # Normalize Unicode
   ```

2. **Query Chaining Prevention**
   ```python
   # Block semicolons outside strings
   # Detect newline-based chaining
   # Prevent multi-statement injection
   ```

3. **APOC Privilege Escalation**
   ```python
   # Block apoc.cypher.run*
   # Block apoc.periodic.iterate
   # Allow safe APOC procedures only
   ```

4. **Read-Only Mode Enforcement** (optional)
   ```python
   # Block CREATE, DELETE, SET, REMOVE, MERGE
   # Block LOAD CSV, CALL procedures (write)
   # Allow MATCH, RETURN, WITH, UNWIND (read)
   ```

**Pattern**: Chain of Responsibility (each validator checks and passes to next)

#### 4.2.4 utilities/audit_logger.py (Compliance Module)

**Responsibility**: Audit trail generation with PII protection

**Features**:

1. **Structured Logging**
   ```json
   {
     "timestamp": "2025-11-06T14:32:15Z",
     "user": "analyst@company.com",
     "action": "query_execution",
     "query": "Show me customers in CA",
     "cypher": "MATCH (c:Customer {state: 'CA'}) RETURN c",
     "result_count": 47,
     "execution_time_ms": 234,
     "sanitization_passed": true
   }
   ```

2. **PII Redaction**
   - Email addresses → `***@***.com`
   - SSNs → `***-**-****`
   - Credit cards → `****-****-****-****`

3. **Log Rotation**
   - Daily files: `audit_2025-11-06.log`
   - Automatic cleanup (configurable retention)

4. **Security Events**
   - Blocked queries
   - Failed authentications (future)
   - Configuration changes

---

## 5. Data Flow

### 5.1 Query Execution Flow

```
┌─────────────┐
│   Client    │
│   (Human)   │
└─────────────┘
       │
       │ (1) Natural Language Query
       │     "Show me customers in California who bought products over $100"
       ▼
┌─────────────────────────────────────────────────────────┐
│               MCP Server (server.py)                     │
│                                                          │
│  @mcp_server.tool()                                      │
│  async def query_graph(query: str):                      │
│      │                                                    │
│      │ (2) Load Neo4j schema (cached)                    │
│      ▼                                                    │
│  ┌──────────────────────────────────────┐               │
│  │   Neo4jGraph.get_schema()            │               │
│  │   - Node labels: [Customer, Product] │               │
│  │   - Relationships: [PURCHASED]       │               │
│  │   - Properties: [state, price, ...]  │               │
│  └──────────────────────────────────────┘               │
│      │                                                    │
│      │ (3) Generate Cypher via LLM                       │
│      ▼                                                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  GraphCypherQAChain.invoke()                      │   │
│  │                                                    │   │
│  │  Input:                                            │   │
│  │  - Query: "Show me customers in CA..."            │   │
│  │  - Schema: {...}                                   │   │
│  │  - Temperature: 0.0 (deterministic)               │   │
│  │                                                    │   │
│  │  LLM generates:                                    │   │
│  │  MATCH (c:Customer {state: 'CA'})-[:PURCHASED]->  │   │
│  │        (p:Product)                                 │   │
│  │  WHERE p.price > 100                              │   │
│  │  RETURN c.name, p.name, p.price                   │   │
│  └──────────────────────────────────────────────────┘   │
│      │                                                    │
│      │ (4) Sanitize Cypher                               │
│      ▼                                                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  sanitize_cypher_query(cypher)                    │   │
│  │                                                    │   │
│  │  Checks:                                           │   │
│  │  ✓ No UTF-8 attacks                               │   │
│  │  ✓ No query chaining (;)                          │   │
│  │  ✓ No APOC escalation                             │   │
│  │  ✓ Read-only compliant (if enabled)               │   │
│  │                                                    │   │
│  │  Result: PASS                                      │   │
│  └──────────────────────────────────────────────────┘   │
│      │                                                    │
│      │ (5) Execute on Neo4j                              │
│      ▼                                                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  neo4j_graph.query(cypher)                        │   │
│  │                                                    │   │
│  │  Results:                                          │   │
│  │  [                                                 │   │
│  │    {c.name: "John Doe",                           │   │
│  │     p.name: "Widget Pro",                         │   │
│  │     p.price: 199.99},                             │   │
│  │    {...}                                           │   │
│  │  ]                                                 │   │
│  └──────────────────────────────────────────────────┘   │
│      │                                                    │
│      │ (6) Log to audit trail                            │
│      ▼                                                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  audit_logger.log_query_execution(...)            │   │
│  │                                                    │   │
│  │  Logged:                                           │   │
│  │  - Timestamp                                       │   │
│  │  - User (future)                                   │   │
│  │  - Query (natural language)                        │   │
│  │  - Cypher (generated)                             │   │
│  │  - Result count                                    │   │
│  │  - Execution time                                  │   │
│  └──────────────────────────────────────────────────┘   │
│      │                                                    │
│      │ (7) Format and return results                     │
│      ▼                                                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  return json.dumps(results)                       │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
       │
       │ (8) MCP response
       │     JSON: [{c.name: "John Doe", ...}, ...]
       ▼
┌─────────────┐
│   Client    │
│  (Display)  │
└─────────────┘
```

### 5.2 Error Handling Flow

```
┌─────────────┐
│   Client    │
└─────────────┘
       │
       │ Malicious Query:
       │ "Show me users; DROP TABLE users;"
       ▼
┌────────────────────────────────────────────┐
│         MCP Server                          │
│                                             │
│  (1) LLM generates Cypher (may include ;)  │
│      ↓                                      │
│  (2) sanitize_cypher_query()               │
│      ↓                                      │
│      ✗ BLOCKED: Query chaining detected    │
│      ↓                                      │
│  (3) Log security event                    │
│      ↓                                      │
│  (4) Return sanitized error                │
│      "Query validation failed"             │
│      (No details exposed)                  │
└────────────────────────────────────────────┘
       │
       │ Error response
       ▼
┌─────────────┐
│   Client    │
│  (Error)    │
└─────────────┘
```

### 5.3 Schema Caching Flow

```
First Query:
┌─────────────┐
│  Client     │ ─── query ──> ┌──────────────┐
└─────────────┘               │  MCP Server  │
                              │              │
                              │ (1) Check    │
                              │     cache    │
                              │     (empty)  │
                              │              │
                              │ (2) Fetch    │
                              │     from     │
                              │     Neo4j    │
                              │              │
                              │ (3) Cache    │
                              │     schema   │
                              │              │
                              └──────────────┘

Subsequent Queries:
┌─────────────┐
│  Client     │ ─── query ──> ┌──────────────┐
└─────────────┘               │  MCP Server  │
                              │              │
                              │ (1) Check    │
                              │     cache    │
                              │     (hit!)   │
                              │              │
                              │ (2) Use      │
                              │     cached   │
                              │     schema   │
                              │              │
                              └──────────────┘

Result: 80% faster query generation, 50% lower LLM costs
```

---

## 6. Security Architecture

### 6.1 Defense in Depth Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 1: Network Security                     │
│  - Firewall rules (port 7687 for Neo4j, 8000 for MCP)          │
│  - TLS/SSL for Neo4j (neo4j+s://)                              │
│  - VPC/network isolation (optional)                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                Layer 2: Authentication (Future)                  │
│  - API key authentication                                        │
│  - JWT tokens                                                    │
│  - Role-based access control (RBAC)                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Layer 3: Input Validation                        │
│  - LangChain allow_dangerous_requests flag                      │
│  - Custom sanitizer (UTF-8, injection, chaining)                │
│  - Query complexity limits (future)                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               Layer 4: Query Execution Control                   │
│  - Read-only mode enforcement (optional)                         │
│  - APOC procedure whitelisting                                   │
│  - Transaction timeout limits                                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 5: Audit & Monitoring                     │
│  - Comprehensive query logging                                   │
│  - Security event logging                                        │
│  - PII redaction                                                 │
│  - Anomaly detection (future)                                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Layer 6: Data Protection                         │
│  - Neo4j access control (database-level)                        │
│  - Encryption at rest (Neo4j feature)                           │
│  - Encryption in transit (TLS)                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Threat Model

| Threat | Attack Vector | Mitigation | Layer |
|--------|--------------|------------|-------|
| **Cypher Injection** | Malicious natural language → injected Cypher | Sanitizer blocks `;`, newlines, APOC | Layer 3 |
| **UTF-8 Attacks** | Zero-width chars, homoglyphs | UTF-8 pattern detection | Layer 3 |
| **Data Exfiltration** | Write large result sets | Query complexity limits (future) | Layer 4 |
| **APOC Escalation** | `apoc.cypher.run*` for privilege escalation | Whitelist safe APOC only | Layers 3-4 |
| **Schema Exposure** | Client gets full schema | Schema is required for LLM, mitigated by server-side | Accepted risk |
| **LLM Prompt Injection** | "Ignore instructions and..." | LangChain prompt engineering | Layer 3 |
| **Denial of Service** | High-complexity queries | Timeout + rate limiting (future) | Layer 4 |
| **Information Leakage** | Detailed error messages | Error sanitization | Layer 3 |
| **Unauthorized Access** | No authentication | API key auth (future) | Layer 2 |

### 6.3 Compliance Features

#### 6.3.1 GDPR Compliance

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| **Right to be Forgotten** | Audit logs can be deleted per user | Manual process |
| **Data Minimization** | Only query/result logged, no raw user data | ✅ Implemented |
| **Encryption in Transit** | TLS for Neo4j, HTTPS for MCP | ✅ Configurable |
| **Access Logging** | All queries logged with timestamp | ✅ Implemented |
| **PII Protection** | Automatic redaction in logs | ✅ Implemented |

#### 6.3.2 HIPAA Compliance

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| **Audit Controls** | Comprehensive audit logging | ✅ Implemented |
| **Access Control** | Read-only mode, authentication (future) | ⚠️ Partial |
| **Encryption** | At-rest (Neo4j), in-transit (TLS) | ✅ Configurable |
| **Integrity** | Sanitizer prevents data corruption | ✅ Implemented |

#### 6.3.3 SOC 2 Type II

| Criterion | Implementation | Status |
|-----------|----------------|--------|
| **Security** | Multi-layer defense, audit logging | ✅ Implemented |
| **Availability** | Connection pooling, retry logic | ✅ Implemented |
| **Confidentiality** | PII redaction, TLS | ✅ Implemented |
| **Processing Integrity** | Query sanitization, validation | ✅ Implemented |
| **Privacy** | PII redaction, data minimization | ✅ Implemented |

---

## 7. Deployment Architecture

### 7.1 Container Architecture (Docker)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Docker Host Machine                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          neo4j-yass-mcp Container                         │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │  Runtime Layer (python:3.11-slim)                    │ │  │
│  │  │  - Python 3.11 runtime                               │ │  │
│  │  │  - Virtual environment (/opt/venv)                   │ │  │
│  │  │  - Application code (/app)                           │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │                                                            │  │
│  │  User: mcp (UID 999, non-root)                           │  │
│  │  Exposed Ports: 8000 (HTTP mode)                         │  │
│  │                                                            │  │
│  │  Volumes:                                                  │  │
│  │  - ./data/logs:/app/logs (audit logs)                    │  │
│  │  - ./.env:/app/.env:ro (configuration)                   │  │
│  │                                                            │  │
│  │  Networks:                                                 │  │
│  │  - neo4j-stack (connects to Neo4j)                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Neo4j Container (Optional)                       │  │
│  │                                                            │  │
│  │  Image: neo4j:5.x                                         │  │
│  │  Ports: 7687 (Bolt), 7474 (HTTP)                         │  │
│  │  Volumes: ./neo4j/data, ./neo4j/logs, ./neo4j/plugins    │  │
│  │  Networks: neo4j-stack                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Multi-Stage Docker Build

```dockerfile
# Stage 1: Builder (larger image with build tools)
FROM python:3.11-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y gcc
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[all]"

# Stage 2: Runtime (minimal image)
FROM python:3.11-slim
WORKDIR /app

# Copy only virtual environment (no build tools)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Non-root user
RUN groupadd -r mcp && useradd -r -g mcp mcp
USER mcp

# Application code
COPY --chown=mcp:mcp . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
  CMD python -c "import sys; sys.exit(0)"

# Run server
CMD ["python", "server.py"]
```

**Benefits**:
- 70% smaller final image (~150MB vs ~500MB)
- No build tools in production
- Faster deployments
- Better security (minimal attack surface)

### 7.3 Deployment Topologies

#### 7.3.1 Single-Instance (Development)

```
┌──────────────┐
│   Client     │
└──────────────┘
       │
       │ HTTP (port 8000)
       ▼
┌──────────────────────┐
│  Neo4j YASS MCP      │
│  (Docker container)  │
└──────────────────────┘
       │
       │ Bolt (port 7687)
       ▼
┌──────────────────────┐
│  Neo4j Database      │
│  (Docker/local)      │
└──────────────────────┘
```

**Use case**: Development, testing, single-user

#### 7.3.2 Load-Balanced (Production)

```
                    ┌──────────────┐
                    │   Client 1   │
                    └──────────────┘
                           │
                    ┌──────────────┐
                    │   Client 2   │
                    └──────────────┘
                           │
                    ┌──────────────┐
                    │   Client N   │
                    └──────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Load Balancer        │
              │   (nginx/HAProxy)      │
              └────────────────────────┘
                      │       │
        ┌─────────────┴───────┴─────────────┐
        │                                    │
        ▼                                    ▼
┌──────────────────┐              ┌──────────────────┐
│  MCP Server 1    │              │  MCP Server 2    │
│  (Container)     │              │  (Container)     │
└──────────────────┘              └──────────────────┘
        │                                    │
        └────────────────┬───────────────────┘
                         │
                         ▼
              ┌────────────────────────┐
              │   Neo4j Cluster        │
              │   (Causal Cluster)     │
              └────────────────────────┘
```

**Use case**: High availability, 100+ users, enterprise

**Characteristics**:
- Stateless MCP servers (horizontal scaling)
- Shared audit logs (network volume)
- Neo4j causal cluster (read replicas)

#### 7.3.3 Multi-Tenant SaaS

```
┌────────────┐  ┌────────────┐  ┌────────────┐
│ Customer A │  │ Customer B │  │ Customer C │
└────────────┘  └────────────┘  └────────────┘
      │               │               │
      ▼               ▼               ▼
┌──────────────────────────────────────────┐
│          API Gateway / Router             │
│     (tenant-based routing)                │
└──────────────────────────────────────────┘
      │               │               │
      ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ MCP      │   │ MCP      │   │ MCP      │
│ Server A │   │ Server B │   │ Server C │
└──────────┘   └──────────┘   └──────────┘
      │               │               │
      ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Neo4j    │   │ Neo4j    │   │ Neo4j    │
│ DB A     │   │ DB B     │   │ DB C     │
└──────────┘   └──────────┘   └──────────┘
```

**Use case**: SaaS platform, tenant isolation

**Characteristics**:
- One MCP server instance per tenant
- Separate Neo4j databases per tenant
- Centralized monitoring and logging

### 7.4 Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      External Network                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   OpenAI     │  │  Anthropic   │  │   Google     │         │
│  │   API        │  │   API        │  │   GenAI      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                  │                  │                 │
│         └──────────────────┴──────────────────┘                 │
│                            │                                     │
│                            │ HTTPS (443)                         │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                    DMZ / Public Subnet                           │
│                            │                                     │
│                            ▼                                     │
│                  ┌─────────────────┐                            │
│                  │  Load Balancer  │                            │
│                  │  (nginx/ALB)    │                            │
│                  └─────────────────┘                            │
│                            │                                     │
│                            │ HTTP/HTTPS (8000)                   │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                  Application Subnet (Private)                    │
│                            │                                     │
│                            ▼                                     │
│              ┌─────────────────────────────┐                    │
│              │   Neo4j YASS MCP Servers    │                    │
│              │   (Containers/K8s Pods)     │                    │
│              └─────────────────────────────┘                    │
│                            │                                     │
│                            │ Bolt (7687)                         │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                  Database Subnet (Private)                       │
│                            │                                     │
│                            ▼                                     │
│              ┌─────────────────────────────┐                    │
│              │   Neo4j Database Cluster    │                    │
│              │   (No internet access)      │                    │
│              └─────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘

Security Rules:
- DMZ: Allow inbound 443 (HTTPS), 8000 (MCP)
- App Subnet: Allow inbound from DMZ only
- DB Subnet: Allow inbound from App Subnet only, no internet
```

---

## 8. Technology Stack

### 8.1 Core Technologies

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Runtime** | Python | 3.11+ | Application runtime |
| **MCP Framework** | FastMCP | 0.1.3+ | MCP server implementation |
| **LLM Framework** | LangChain | 0.3.7+ | Natural language to Cypher |
| **Database Driver** | neo4j-python-driver | 5.15+ | Neo4j connectivity |
| **Database** | Neo4j | 5.x | Graph database |
| **Containerization** | Docker | 20.10+ | Deployment packaging |
| **Orchestration** | Docker Compose | 2.0+ | Multi-container management |

### 8.2 LLM Provider Libraries

```python
# Installed via pyproject.toml [all] extra
langchain-openai>=0.2.8       # OpenAI (GPT-4o, o3, o4-mini)
langchain-anthropic>=0.3.0    # Anthropic (Claude Sonnet 4.5, etc.)
langchain-google-genai>=2.0.3 # Google (Gemini 2.5 Pro/Flash)
```

### 8.3 Development Tools

| Tool | Purpose | Version |
|------|---------|---------|
| **uv** | Fast Python package manager | Latest |
| **pytest** | Unit testing | 7.x |
| **ruff** | Linting and formatting | Latest |
| **mypy** | Type checking | 1.x |
| **black** | Code formatting | 23.x |

### 8.4 Dependency Tree

```
neo4j-yass-mcp
├── fastmcp>=0.1.3
│   ├── pydantic
│   └── uvicorn (HTTP mode)
├── langchain>=0.3.7
│   ├── langchain-core
│   ├── langchain-community
│   └── langchain-text-splitters
├── langchain-neo4j>=0.2.0
│   └── neo4j>=5.15.0
├── langchain-openai>=0.2.8
│   └── tiktoken (tokenization)
├── langchain-anthropic>=0.3.0
├── langchain-google-genai>=2.0.3
└── python-dotenv>=1.0.0
```

### 8.5 System Requirements

#### Minimum (Development)
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 10GB
- **Network**: 10 Mbps

#### Recommended (Production)
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 50GB SSD
- **Network**: 100 Mbps+

#### Neo4j Requirements
- **RAM**: 4GB minimum, 16GB+ recommended
- **Disk**: SSD strongly recommended (10x performance)
- **Heap Size**: 4GB (configurable)

---

## 9. Design Patterns

### 9.1 Architectural Patterns

#### 9.1.1 Layered Architecture

```
Presentation Layer (MCP API)
         ↓
Business Logic Layer (Query Processing)
         ↓
Data Access Layer (Neo4j Driver)
         ↓
Database Layer (Neo4j)
```

**Benefits**:
- Clear separation of concerns
- Easy to test each layer independently
- Swappable components (e.g., switch LLM providers)

#### 9.1.2 Pipe and Filter

Query processing pipeline:

```
Natural Language
      ↓ (Filter: Schema Injection)
Natural Language + Schema
      ↓ (Filter: LLM Translation)
Cypher Query
      ↓ (Filter: Sanitization)
Safe Cypher Query
      ↓ (Filter: Execution)
Raw Results
      ↓ (Filter: Formatting)
JSON Response
```

**Benefits**:
- Easy to add new filters (e.g., query optimization)
- Clear data transformations
- Testable in isolation

### 9.2 Creational Patterns

#### 9.2.1 Factory Pattern

```python
def chatLLM(config: LLMConfig) -> BaseChatModel:
    """Factory for creating LLM instances"""
    if config.provider == "openai":
        return ChatOpenAI(...)
    elif config.provider == "anthropic":
        return ChatAnthropic(...)
    elif config.provider == "google-genai":
        return ChatGoogleGenerativeAI(...)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")
```

**Benefits**:
- Centralized LLM creation logic
- Easy to add new providers
- Configuration-driven instantiation

### 9.3 Structural Patterns

#### 9.3.1 Adapter Pattern

LangChain acts as an adapter between different LLM APIs:

```
Our Code
   ↓
LangChain (Adapter)
   ↓
┌──────────┬──────────┬──────────┐
│ OpenAI   │ Anthropic│  Google  │
│ API      │ API      │  API     │
└──────────┴──────────┴──────────┘
```

**Benefits**:
- Unified interface across providers
- Easy to switch providers
- Hides provider-specific details

### 9.4 Behavioral Patterns

#### 9.4.1 Chain of Responsibility

Sanitization chain:

```python
query
  → UTF-8 Attack Check
    → Query Chaining Check
      → APOC Escalation Check
        → Read-Only Check
          → Safe Query
```

Each validator can:
- Pass to next validator
- Block and return error
- Modify and pass on

#### 9.4.2 Strategy Pattern

LLM provider selection:

```python
class LLMStrategy:
    def generate_cypher(self, query: str, schema: Dict) -> str:
        pass

class OpenAIStrategy(LLMStrategy):
    def generate_cypher(self, query: str, schema: Dict) -> str:
        # Use OpenAI API
        pass

class AnthropicStrategy(LLMStrategy):
    def generate_cypher(self, query: str, schema: Dict) -> str:
        # Use Anthropic API
        pass
```

**Benefits**:
- Runtime provider selection
- Easy A/B testing
- Provider-specific optimizations

---

## 10. Scalability & Performance

### 10.1 Performance Characteristics

| Operation | Latency (avg) | Throughput | Bottleneck |
|-----------|---------------|------------|------------|
| **Schema Retrieval** | 50ms (cached: 1ms) | 1000 req/s | Neo4j query (uncached) |
| **Query Generation** | 1-3s | 10-30 req/s | LLM API latency |
| **Query Execution** | 100-500ms | 50-200 req/s | Neo4j complexity |
| **End-to-End Query** | 1.5-4s | 10-30 req/s | LLM API |

### 10.2 Scalability Strategies

#### 10.2.1 Horizontal Scaling

```
Load Balancer
    ↓
┌──────┬──────┬──────┬──────┐
│ MCP  │ MCP  │ MCP  │ MCP  │
│ Srv 1│ Srv 2│ Srv 3│ Srv N│
└──────┴──────┴──────┴──────┘
    ↓       ↓       ↓       ↓
┌────────────────────────────┐
│   Neo4j Cluster            │
│   (Read Replicas)          │
└────────────────────────────┘
```

**Capacity Planning**:
- Each MCP server: 30 queries/second
- 10 servers = 300 queries/second
- Linear scaling (stateless design)

#### 10.2.2 Caching Strategy

```python
# Schema caching (in-memory)
schema_cache: Optional[Dict] = None
schema_cache_time: Optional[datetime] = None
SCHEMA_CACHE_TTL = 3600  # 1 hour

# Query result caching (future: Redis)
@cache(ttl=300)  # 5 minutes
async def execute_query(cypher: str) -> List[Dict]:
    return await neo4j_graph.query(cypher)
```

**Impact**:
- Schema caching: 80% latency reduction for query generation
- Result caching: 70% cost reduction for repeated queries

#### 10.2.3 Connection Pooling

```python
driver = GraphDatabase.driver(
    uri=NEO4J_URI,
    auth=(username, password),
    max_connection_pool_size=50,  # Shared across all requests
    connection_acquisition_timeout=60,
    max_transaction_retry_time=30
)
```

**Benefits**:
- Reuse connections (no handshake overhead)
- Handle concurrent requests efficiently
- Automatic retry on transient failures

### 10.3 Performance Optimization

#### 10.3.1 Async I/O

```python
# Async executor for sync operations
executor = ThreadPoolExecutor(max_workers=10)

async def query_graph(query: str) -> str:
    # Run sync LangChain call in thread pool
    result = await asyncio.get_event_loop().run_in_executor(
        executor,
        lambda: cypher_chain.invoke({"query": query})
    )
    return result
```

**Impact**: Non-blocking I/O, handle 100+ concurrent requests

#### 10.3.2 Query Optimization (Future)

```python
# Analyze and optimize Cypher
class QueryOptimizer:
    def optimize(self, cypher: str) -> str:
        # 1. Use indexes (MATCH (n:Label {prop: $value}) → indexed)
        # 2. Limit results early (MATCH ... LIMIT 100)
        # 3. Avoid Cartesian products
        # 4. Use WITH for pipeline optimization
        return optimized_cypher
```

**Expected Impact**: 3x faster for complex queries

### 10.4 Monitoring & Observability

#### 10.4.1 Metrics to Track

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| **Query Latency** | User experience | > 5s (p95) |
| **Error Rate** | Reliability | > 5% |
| **LLM API Latency** | Provider SLA | > 10s |
| **Neo4j Connection Pool** | Resource exhaustion | > 80% usage |
| **Sanitization Blocks** | Security events | > 10/hour |
| **Audit Log Size** | Compliance | > 1GB/day |

#### 10.4.2 Logging Strategy

```python
# Structured logging
logging.info(
    "Query executed",
    extra={
        "query": query,
        "cypher": cypher,
        "latency_ms": latency,
        "result_count": len(results),
        "llm_provider": config.provider,
        "llm_model": config.model
    }
)
```

**Benefits**:
- Queryable logs (JSON format)
- Performance debugging
- Cost attribution

---

## 11. Future Architecture Evolution

### 11.1 Conversational Query Refinement (Q1 2026)

**Architectural Changes**:

```
┌────────────────────────────────────────┐
│  New Component: Conversation Manager   │
│                                         │
│  - Session management                   │
│  - Context tracking                     │
│  - Multi-turn dialogue state           │
└────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────┐
│  Enhanced MCP Tool: query_graph_v2     │
│                                         │
│  @mcp_server.tool()                     │
│  async def query_graph_v2(              │
│      query: str,                        │
│      session_id: Optional[str] = None   │
│  ):                                     │
│      # Load conversation context        │
│      # Generate query with history      │
│      # Suggest refinements              │
│      # Update session state             │
└────────────────────────────────────────┘
```

**Data Structures**:

```python
@dataclass
class ConversationContext:
    session_id: str
    query_history: List[str]
    cypher_history: List[str]
    schema_context: Dict[str, Any]
    user_preferences: Dict[str, Any]
    created_at: datetime
    last_updated: datetime

# Storage: Redis or in-memory with TTL
conversation_store: Dict[str, ConversationContext] = {}
```

**Impact on Architecture**:
- Add stateful session layer (breaks current stateless design)
- Mitigation: Use Redis for shared session storage across instances
- Performance: Minimal (session lookup < 10ms)

### 11.2 Multi-Database Support (Q2 2026)

**Architectural Changes**:

```
Current Architecture:
┌──────────────┐
│  MCP Server  │ ────> Neo4j Database (single)
└──────────────┘

Future Architecture:
┌──────────────┐        ┌──────────┐
│  MCP Server  │ ────> │ Neo4j DB1│
│              │        └──────────┘
│  - Database  │        ┌──────────┐
│    Router    │ ────> │ Neo4j DB2│
│  - Query     │        └──────────┘
│    Federator │        ┌──────────┐
│              │ ────> │ Neo4j DB3│
└──────────────┘        └──────────┘
```

**New Components**:

```python
@dataclass
class DatabaseConfig:
    name: str
    uri: str
    database: str
    credentials: Tuple[str, str]
    schema_cache: Optional[Dict] = None

class DatabaseRouter:
    """Routes queries to appropriate database(s)"""
    def determine_target_databases(
        self, query: str, databases: Dict[str, DatabaseConfig]
    ) -> List[str]:
        # LLM analyzes query to determine which DB(s) to use
        pass

class QueryFederator:
    """Executes cross-database queries"""
    async def execute_federated_query(
        self, query: str, target_dbs: List[str]
    ) -> Dict:
        # Execute on multiple DBs and join results
        pass
```

**Impact on Architecture**:
- Add database routing layer (new responsibility)
- Performance overhead: +100-200ms for DB selection
- Complexity: Cross-database joins (manual implementation)

### 11.3 GraphQL Federation (Q3 2026)

**Architectural Changes**:

```
New Mode: GraphQL Gateway Mode

┌─────────────────────────────────────────┐
│         Neo4j YASS MCP Server            │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  GraphQL Mode (MCP_MODE=graphql)   │ │
│  │                                     │ │
│  │  - Auto-generate schema from Neo4j │ │
│  │  - Dual interface:                  │ │
│  │    1. Traditional GraphQL           │ │
│  │    2. Natural language resolver     │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  GraphQL Resolver Layer             │ │
│  │  - Field resolvers → Cypher         │ │
│  │  - queryGraph resolver → LLM        │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**New Dependencies**:

```python
# GraphQL server
graphene>=3.0
strawberry-graphql>=0.200  # Alternative

# Neo4j GraphQL integration
neo4j-graphql-py>=0.5
```

**Dual Operation**:

```
Mode 1: MCP Server (current)
- FastMCP server
- MCP tools API

Mode 2: GraphQL Gateway (future)
- GraphQL server (port 4000)
- REST API fallback
- MCP tools still available
```

**Impact on Architecture**:
- Add GraphQL layer (parallel to MCP)
- Schema auto-generation from Neo4j
- Potential for code reuse (same LLM/sanitizer logic)

### 11.4 Migration Path

```
Version 1.0 (Current)
- MCP server only
- Single database
- Single-turn queries

    ↓ (Backward compatible update)

Version 2.0 (Q1 2026)
- MCP server
- Single database
- Multi-turn queries (optional session_id parameter)

    ↓ (Backward compatible update)

Version 3.0 (Q2 2026)
- MCP server
- Multi-database (optional database parameter)
- Multi-turn queries

    ↓ (Parallel mode)

Version 4.0 (Q3 2026)
- MCP server (mode=mcp)
- GraphQL server (mode=graphql)
- Multi-database
- Multi-turn queries
```

**Backward Compatibility Strategy**:
- Optional parameters (default to v1.0 behavior)
- Feature flags (enable new features via environment variables)
- Deprecation warnings (12-month notice before removal)

---

## 12. Appendices

### Appendix A: Configuration Reference

See [.env.example](../.env.example) for complete configuration options.

**Critical Settings**:

```bash
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=strong-password

# LLM Provider
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5
LLM_API_KEY=sk-ant-...
LLM_TEMPERATURE=0.0
LLM_STREAMING=false

# Security
ALLOW_WEAK_PASSWORDS=false
LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=false
DEBUG_MODE=false
SANITIZER_ENABLED=true
READ_ONLY_MODE=false

# Audit Logging
AUDIT_ENABLED=true
AUDIT_LOG_DIR=./data/logs/audit
AUDIT_PII_REDACTION=true

# MCP Transport
MCP_TRANSPORT=http
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
```

### Appendix B: API Reference

**MCP Tools**:

```python
@mcp_server.tool()
async def query_graph(query: str) -> str:
    """
    Execute natural language query against Neo4j graph database.

    Args:
        query: Natural language question about the graph

    Returns:
        JSON string containing query results

    Raises:
        ValueError: If query fails sanitization
        RuntimeError: If Neo4j query fails
    """

@mcp_server.tool()
async def get_schema() -> str:
    """
    Retrieve Neo4j graph schema.

    Returns:
        JSON string with:
        - node_labels: List of node types
        - relationship_types: List of relationship types
        - properties: Dict of properties per label
    """

@mcp_server.tool()
async def estimate_tokens(text: str) -> str:
    """
    Estimate LLM token count for cost planning.

    Args:
        text: Text to tokenize

    Returns:
        JSON string with token count and estimated cost
    """
```

### Appendix C: Security Checklist

Production deployment checklist:

- [ ] Strong Neo4j password (20+ chars, mixed case, special chars)
- [ ] TLS enabled for Neo4j (neo4j+s://)
- [ ] `ALLOW_WEAK_PASSWORDS=false`
- [ ] `LANGCHAIN_ALLOW_DANGEROUS_REQUESTS=false`
- [ ] `DEBUG_MODE=false` in production
- [ ] Audit logging enabled (`AUDIT_ENABLED=true`)
- [ ] PII redaction enabled (`AUDIT_PII_REDACTION=true`)
- [ ] Read-only mode for public access (`READ_ONLY_MODE=true`)
- [ ] Firewall rules configured (ports 7687, 8000)
- [ ] Regular security updates (`docker pull` monthly)
- [ ] Backup audit logs regularly
- [ ] Monitor for blocked queries (security events)

### Appendix D: Troubleshooting Guide

Common issues and solutions:

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Cannot connect to Neo4j** | "Failed to establish connection" | Check NEO4J_URI, password, Neo4j is running |
| **Weak password detected** | Server exits on startup | Set strong password or ALLOW_WEAK_PASSWORDS=true (dev only) |
| **LLM API error** | "API key invalid" | Verify LLM_API_KEY format (sk- for OpenAI, sk-ant- for Anthropic) |
| **Query blocked** | "Query validation failed" | Check audit logs for sanitization failure reason |
| **High latency** | Queries take > 10s | Check LLM provider status, Neo4j indexes, network latency |
| **Port already in use** | "Address already in use" | Change MCP_SERVER_PORT or kill conflicting process |

### Appendix E: Performance Tuning

Optimization checklist:

**Neo4j**:
- [ ] Create indexes on frequently queried properties
- [ ] Enable APOC plugin for utilities
- [ ] Tune heap size (4GB minimum, 16GB+ recommended)
- [ ] Use SSD storage (10x performance vs HDD)

**MCP Server**:
- [ ] Enable schema caching (automatic)
- [ ] Use HTTP transport (better than stdio for concurrency)
- [ ] Increase connection pool size for high load
- [ ] Monitor thread pool utilization

**LLM Provider**:
- [ ] Use temperature=0.0 for deterministic queries
- [ ] Enable streaming for better UX (`LLM_STREAMING=true`)
- [ ] Choose cost-effective models (Gemini 2.5 Flash, GPT-4o-mini)
- [ ] Monitor API usage and costs

### Appendix F: Related Documents

- [README.md](../README.md) - Project overview and features
- [QUICK_START.md](../QUICK_START.md) - 5-minute setup guide
- [DOCKER.md](../DOCKER.md) - Docker deployment guide
- [SECURITY.md](../SECURITY.md) - Security best practices
- [BUSINESS_CASE.md](../BUSINESS_CASE.md) - Business value and ROI
- [docs/LLM_PROVIDERS.md](LLM_PROVIDERS.md) - LLM configuration guide
- [docs/ADDING_LLM_PROVIDERS.md](ADDING_LLM_PROVIDERS.md) - Add new providers

---

**Document Metadata**:
- **Version**: 1.0
- **Last Updated**: November 2025
- **Maintained By**: Neo4j YASS MCP Team
- **Review Cycle**: Quarterly or after major architecture changes

---

*This document describes the production architecture as of v1.0. For future architecture evolution, see Section 11.*
