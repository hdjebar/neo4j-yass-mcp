# ADR-001: FastMCP Proxy Router & Dynamic Registry Pattern

**Status**: Proposed
**Date**: 2025-11-22
**Authors**: Architecture Team
**Deciders**: Engineering Lead, Platform Team

## Context

### Problem Statement

As MCP ecosystems grow, organizations face critical scaling challenges:

1. **Token Exhaustion**: Each tool definition consumes ~400-500 tokens. With 50+ tools, 20,000-25,000 tokens are consumed before any actual work begins.

2. **Context Window Saturation**: Claude Code users report 66,000+ tokens burned loading MCP tools—1/3 of the 200K context window wasted on tool definitions.

3. **Tool Selection Degradation**: LLM performance degrades when choosing from large, flat tool lists, even with 1M context windows ("context rot").

4. **Multi-Server Complexity**: Organizations using multiple MCP servers (Neo4j, GitHub, Slack, Asana) must manage scattered configurations and credentials.

### Current State

Neo4j YASS MCP currently exposes 4 tools directly:
- `query_graph` (~450 tokens)
- `execute_cypher` (~400 tokens)
- `refresh_schema` (~200 tokens)
- `analyze_query_performance` (~500 tokens)

**Current token cost**: ~1,550 tokens (acceptable)

**Future state with enterprise integrations**: 50+ tools = 20,000+ tokens (problematic)

### Industry Trends (2025)

| Solution | Provider | Token Reduction | Approach |
|----------|----------|-----------------|----------|
| Code Execution with MCP | Anthropic | 98.7% | Tools as filesystem |
| Dynamic Toolsets v2 | Speakeasy | 96% | On-demand loading |
| MCP Optimizer | ToolHive | 80%+ | Semantic filtering |
| Hierarchical Tools | MCP Spec Proposal | 80% | Category browsing |

## Decision

We will implement a **Token-Optimized Dynamic Registry** using FastMCP's proxy and composition features, combining multiple token reduction strategies.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Token-Optimized MCP Gateway                  │
├─────────────────────────────────────────────────────────────────┤
│  Meta-Tools (Always Loaded - ~800 tokens)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  discover   │  │  activate   │  │   execute   │             │
│  │  (search)   │  │  (load)     │  │   (run)     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  Tool Index (Metadata Only - Not in LLM Context)                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  {name, category, description_short, server}             │   │
│  │  Semantic embeddings for search                          │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  Backend Servers (Loaded On-Demand via Proxy)                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Neo4j   │ │ GitHub  │ │ Slack   │ │ Asana   │ │ Custom  │  │
│  │ YASS    │ │ MCP     │ │ MCP     │ │ MCP     │ │ MCP     │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Selected Pattern: Hybrid Dynamic Registry

Combines three strategies:

1. **Meta-Tool Interface** (3 tools always loaded)
2. **Semantic Search** (pre-filter before loading)
3. **On-Demand Proxy** (load full definitions only when needed)

## Implementation

### Core Components

#### 1. Token-Optimized Registry Server

```python
# src/neo4j_yass_mcp/registry/gateway.py

from fastmcp import FastMCP
from fastmcp.server.proxy import ProxyClient
from pydantic import Field
import numpy as np

class TokenOptimizedRegistry:
    """
    MCP Gateway with 98% token reduction.

    Only 3 meta-tools exposed by default (~800 tokens).
    All other tools loaded on-demand.
    """

    def __init__(self):
        self.mcp = FastMCP(
            "EnterpriseGateway",
            description="Token-optimized MCP tool registry"
        )

        # Tool catalog (metadata only - not in LLM context)
        self.tool_index: dict[str, ToolMetadata] = {}

        # Semantic embeddings for search
        self.embeddings: dict[str, np.ndarray] = {}

        # Currently active tools (in LLM context)
        self.active_tools: set[str] = set()

        # Backend server connections
        self.backends: dict[str, ProxyClient] = {}

        self._register_meta_tools()

    def _register_meta_tools(self):
        """Register the 3 always-available meta-tools"""

        @self.mcp.tool()
        async def discover(
            query: str = Field(description="What do you need to do?"),
            limit: int = Field(default=5, description="Max results")
        ) -> list[dict]:
            """
            Search available tools across all servers.
            Returns metadata only - doesn't load tool definitions.
            """
            results = await self._semantic_search(query, limit)
            return [
                {
                    "name": r.name,
                    "server": r.server,
                    "category": r.category,
                    "description": r.description[:100],
                    "relevance": r.score
                }
                for r in results
            ]

        @self.mcp.tool()
        async def activate(
            tools: list[str] = Field(description="Tool names to load")
        ) -> dict:
            """
            Load specific tools into active context.
            Only activated tools consume context tokens.
            """
            loaded = []
            for tool_name in tools:
                if tool_name in self.tool_index:
                    meta = self.tool_index[tool_name]
                    await self._mount_tool(meta)
                    self.active_tools.add(tool_name)
                    loaded.append(tool_name)

            return {
                "loaded": loaded,
                "active_count": len(self.active_tools),
                "estimated_tokens": len(self.active_tools) * 450
            }

        @self.mcp.tool()
        async def execute(
            tool: str = Field(description="Tool name"),
            args: dict = Field(default={}, description="Tool arguments")
        ) -> dict:
            """
            Execute any tool by name (proxy mode).
            Tool doesn't need to be activated first.
            """
            if tool not in self.tool_index:
                return {"error": f"Tool '{tool}' not found"}

            meta = self.tool_index[tool]
            backend = self.backends.get(meta.server)

            if not backend:
                return {"error": f"Server '{meta.server}' not connected"}

            return await backend.call_tool(meta.original_name, args)

    async def _semantic_search(
        self,
        query: str,
        limit: int
    ) -> list[ToolMetadata]:
        """Search tools using semantic similarity"""
        query_embedding = await self._embed(query)

        scores = {}
        for name, embedding in self.embeddings.items():
            scores[name] = self._cosine_similarity(query_embedding, embedding)

        top_names = sorted(scores, key=scores.get, reverse=True)[:limit]
        return [
            ToolMetadata(**self.tool_index[name].__dict__, score=scores[name])
            for name in top_names
        ]

    async def _mount_tool(self, meta: ToolMetadata):
        """Dynamically mount a tool from backend server"""
        if meta.name not in self.active_tools:
            backend = self.backends[meta.server]
            # Mount creates live proxy to backend tool
            self.mcp.mount(
                meta.name,
                FastMCP.as_proxy(backend),
                prefix=meta.server
            )

    def register_backend(self, name: str, config: ServerConfig):
        """Register a backend MCP server"""
        self.backends[name] = ProxyClient(config.url or config.command)

        # Index all tools from this backend (metadata only)
        for tool in config.tools:
            self.tool_index[f"{name}_{tool.name}"] = ToolMetadata(
                name=f"{name}_{tool.name}",
                original_name=tool.name,
                server=name,
                category=tool.category,
                description=tool.description
            )
            # Pre-compute embeddings
            self.embeddings[f"{name}_{tool.name}"] = self._embed_sync(
                f"{tool.name} {tool.description}"
            )
```

#### 2. Configuration Schema

```python
# src/neo4j_yass_mcp/registry/config.py

from pydantic import BaseModel
from typing import Optional

class ToolConfig(BaseModel):
    name: str
    category: str
    description: str

class ServerConfig(BaseModel):
    name: str
    url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[list[str]] = None
    tools: list[ToolConfig] = []

class RegistryConfig(BaseModel):
    """Configuration for the token-optimized registry"""

    # Meta-tool settings
    max_search_results: int = 5
    max_active_tools: int = 10

    # Token budget
    token_budget: int = 5000  # Max tokens for tool definitions
    tokens_per_tool: int = 450  # Estimated tokens per tool

    # Backend servers
    servers: dict[str, ServerConfig] = {}

    # Embedding model for semantic search
    embedding_model: str = "all-MiniLM-L6-v2"
```

#### 3. Example Configuration

```yaml
# config/registry.yaml

meta_tools:
  max_search_results: 5
  max_active_tools: 10

token_budget:
  total: 5000
  per_tool: 450
  reserved_for_meta: 800

servers:
  neo4j:
    command: "python"
    args: ["-m", "neo4j_yass_mcp.server"]
    tools:
      - name: query_graph
        category: database
        description: "Query Neo4j with natural language"
      - name: execute_cypher
        category: database
        description: "Execute raw Cypher queries"
      - name: analyze_query_performance
        category: database
        description: "Analyze query execution plans"

  github:
    url: "https://api.github.com/mcp"
    tools:
      - name: create_pr
        category: devops
        description: "Create pull request"
      - name: list_issues
        category: devops
        description: "List repository issues"

  slack:
    command: "npx"
    args: ["-y", "@anthropic/mcp-slack"]
    tools:
      - name: send_message
        category: communication
        description: "Send Slack message"
      - name: list_channels
        category: communication
        description: "List Slack channels"
```

### Token Budget Analysis

#### Before (Direct Tool Exposure)

| Component | Tools | Tokens |
|-----------|-------|--------|
| Neo4j YASS | 4 | 1,550 |
| GitHub MCP | 15 | 6,750 |
| Slack MCP | 10 | 4,500 |
| Asana MCP | 12 | 5,400 |
| **Total** | **41** | **18,200** |

#### After (Token-Optimized Registry)

| Component | Tools | Tokens |
|-----------|-------|--------|
| Meta-tools | 3 | 800 |
| On-demand (avg 3 active) | 3 | 1,350 |
| **Total** | **6** | **2,150** |

**Reduction: 88%** (18,200 → 2,150 tokens)

### API Flow

```
User: "I need to query the database and create a PR"

1. LLM calls discover(query="query database create PR")
   → Returns: [
       {name: "neo4j_query_graph", relevance: 0.92},
       {name: "github_create_pr", relevance: 0.89}
     ]
   → Token cost: ~100 tokens (response only)

2. LLM calls activate(tools=["neo4j_query_graph", "github_create_pr"])
   → Tools now available in context
   → Token cost: +900 tokens (2 tool definitions)

3. LLM calls neo4j_query_graph(query="Find all users")
   → Proxied to Neo4j backend
   → Returns results

4. LLM calls github_create_pr(title="Add users feature")
   → Proxied to GitHub backend
   → Returns PR URL

Total tokens: 800 (meta) + 900 (active) = 1,700
vs Traditional: 18,200 tokens
```

### Alternative: Execute-Only Mode (Maximum Token Savings)

For maximum savings, skip activation entirely:

```python
# User flow with execute-only mode
discover("query database")  # Find tools
execute("neo4j_query_graph", {"query": "Find users"})  # Direct execution

# Token cost: Only 800 tokens (meta-tools)
# 95.6% reduction vs traditional
```

## Consequences

### Positive

1. **Dramatic Token Reduction**: 88-96% fewer tokens for tool definitions
2. **Scalability**: Support 100+ tools without context exhaustion
3. **Unified Access**: Single gateway for all MCP servers
4. **Semantic Discovery**: AI can find relevant tools via natural language
5. **Backward Compatible**: Existing tools work unchanged
6. **Security Centralization**: Single point for auth, audit, rate limiting

### Negative

1. **Latency Overhead**: Extra round-trip for discover + activate (~200ms)
2. **Complexity**: Additional infrastructure to maintain
3. **Semantic Search Quality**: Depends on embedding model quality
4. **State Management**: Must track active tools per session

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Search misses relevant tools | Medium | High | Fallback to category browsing |
| Proxy latency issues | Low | Medium | Connection pooling, caching |
| Embedding model drift | Low | Low | Periodic re-indexing |
| Session state corruption | Low | High | Stateless execute mode |

## Alternatives Considered

### 1. Static Tool Filtering

**Description**: Manually curate tool subsets per use case
**Rejected because**: Doesn't scale, requires manual maintenance

### 2. Full Code Execution Pattern (Anthropic)

**Description**: Tools as filesystem, agents write code to use them
**Rejected because**: Requires secure sandbox infrastructure, higher complexity

### 3. No Change (Accept Token Cost)

**Description**: Keep current direct tool exposure
**Rejected because**: Blocks enterprise multi-server integration

### 4. Client-Side Filtering (Claude Desktop)

**Description**: Let clients like Claude Desktop filter tools
**Rejected because**: Not all clients support this, inconsistent experience

## Implementation Plan

### Phase 1: Core Registry (Week 1-2)
- [ ] Create registry module structure
- [ ] Implement meta-tools (discover, activate, execute)
- [ ] Add tool indexing from configuration
- [ ] Basic semantic search with sentence-transformers

### Phase 2: Backend Integration (Week 2-3)
- [ ] Proxy client connections to backends
- [ ] Tool metadata extraction from MCP servers
- [ ] Connection pooling and health checks
- [ ] Error handling and fallbacks

### Phase 3: Token Optimization (Week 3-4)
- [ ] Token budget enforcement
- [ ] Auto-unload inactive tools
- [ ] Session state management
- [ ] Metrics and monitoring

### Phase 4: Production Hardening (Week 4-5)
- [ ] Security audit (auth, rate limiting)
- [ ] Performance optimization
- [ ] Documentation and examples
- [ ] Integration tests

## References

1. [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) - 98.7% token reduction pattern
2. [FastMCP Proxy Servers](https://gofastmcp.com/servers/proxy) - Proxy and composition patterns
3. [MCP Hierarchical Tool Management](https://github.com/orgs/modelcontextprotocol/discussions/532) - Spec proposal
4. [Speakeasy Dynamic Toolsets](https://www.speakeasy.com/blog/how-we-reduced-token-usage-by-100x-dynamic-toolsets-v2) - 160x reduction benchmarks
5. [MCP Gateway Registry](https://github.com/agentic-community/mcp-gateway-registry) - Enterprise patterns

## Decision Record

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-22 | Proposed | Initial ADR creation |
| | | |

---

**Appendix A: Token Calculation Formula**

```
Base tokens = 800 (meta-tools)
Active tokens = num_active_tools × 450
Total = Base + Active

Budget check: Total ≤ token_budget (default 5000)
Max active tools = (token_budget - 800) / 450 ≈ 9 tools
```

**Appendix B: Semantic Search Implementation**

```python
from sentence_transformers import SentenceTransformer

class SemanticIndex:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.embeddings = {}

    def index(self, name: str, text: str):
        self.embeddings[name] = self.model.encode(text)

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        query_emb = self.model.encode(query)
        scores = {
            name: np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
            for name, emb in self.embeddings.items()
        }
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
```
