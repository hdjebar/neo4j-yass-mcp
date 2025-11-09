# Software Architecture Document: Neo4j YASS MCP

## Table of Contents
- [1. Introduction](#1-introduction)
- [2. Architecture Overview](#2-architecture-overview)
- [3. Component Architecture](#3-component-architecture)
- [4. Security Architecture](#4-security-architecture)
- [5. Data Flow](#5-data-flow)
- [6. Deployment Architecture](#6-deployment-architecture)
- [7. Performance & Scalability](#7-performance--scalability)
- [8. Monitoring & Observability](#8-monitoring--observability)

## 1. Introduction

### 1.1 Purpose
This document describes the software architecture of Neo4j YASS MCP (Yet Another Secure Server), a production-ready, security-enhanced Model Context Protocol (MCP) server that provides Neo4j graph database querying capabilities using LangChain's GraphCypherQAChain for natural language to Cypher query translation.

### 1.2 Scope
The architecture covers the MCP server implementation, security layer, LLM integration, and deployment considerations.

### 1.3 Architecture Goals
- **Security**: Multi-layered defense against injection and other attacks
- **Performance**: Async/await support with parallel query execution
- **Scalability**: Container-first design with resource limits
- **Compliance**: Audit logging for regulatory requirements
- **Usability**: Natural language query processing

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Client Layer                            │
│  (Claude Desktop, Web Apps, etc.)                             │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastMCP Framework                           │
│                (stdio/HTTP/SSE transport)                      │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Security Layer                               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Query Sanitizer │ │  Read-Only      │ │ Rate Limiter    │   │
│  │ (injection,     │ │  Validation     │ │    Service      │   │
│  │  UTF-8)        │ │                 │ │                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Audit Logging                                │
│              (Compliance & Forensics)                          │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                LangChain Layer                                 │
│        (GraphCypherQAChain, NLP → Cypher)                     │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Neo4j Database                                │
│              (Graph Database Engine)                           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Architecture Style
- **Microservice**: Single purpose MCP server service
- **Layered Architecture**: Security, business logic, and data layers
- **Event-Driven**: MCP protocol communication patterns
- **Security-First**: Security controls at multiple layers

## 3. Component Architecture

### 3.1 Core Components

```
src/neo4j_yass_mcp/
├── server.py                 # Main MCP server entry point
├── secure_graph.py           # Security wrapper for Neo4jGraph
├── tool_wrappers.py          # Rate limiting and logging decorators
├── config/
│   ├── __init__.py          # Configuration loading
│   ├── llm_config.py        # LLM provider configuration
│   └── utils.py             # General utilities
└── security/
    ├── __init__.py          # Security module exports
    ├── sanitizer.py         # Query sanitization logic
    ├── audit_logger.py      # Audit logging implementation
    ├── complexity_limiter.py # Query complexity analysis
    └── rate_limiter.py      # Rate limiting implementation
```

### 3.2 Component Responsibilities

#### 3.2.1 server.py
- MCP server initialization and entry point
- Tool and resource registration
- Global state management
- Connection and resource cleanup

#### 3.2.2 secure_graph.py
- Security wrapper for Neo4jGraph
- Intercepts queries before execution
- Applies all security checks sequentially
- Maintains security state and configurations

#### 3.2.3 tool_wrappers.py
- Rate limiting decorators
- Structured logging for tools
- Per-session rate limiting using ctx.session_id
- Error handling and response formatting

#### 3.2.4 Security Module Components
- **sanitizer.py**: Query and parameter sanitization
- **audit_logger.py**: Comprehensive logging for compliance
- **complexity_limiter.py**: Query complexity analysis
- **rate_limiter.py**: Token-based rate limiting

### 3.3 External Dependencies

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LangChain     │    │      FastMCP    │    │    neo4j driver │
│   - GraphCypher │    │   - MCP Protocol│    │   - Bolt Protocol│
│   - NLP models  │    │   - Transport   │    │   - Connection  │
│   - Schema intros│    │   - Decorators  │    │   - Pooling    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                       ┌─────────────────┐
                       │   LLM Providers │
                       │   - OpenAI      │
                       │   - Anthropic   │
                       │   - Google GenAI│
                       └─────────────────┘
```

## 4. Security Architecture

### 4.1 Defense-in-Depth Model

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Client                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                ┌─────────▼─────────┐
                │  Transport Layer  │
                │  - HTTP/SSE/stdio │
                │  - TLS (if HTTPS) │
                └─────────┬─────────┘
                          │
                ┌─────────▼─────────┐
                │  Input Validation │
                │  - Query length   │
                │  - Parameter names│
                │  - Format checks  │
                └─────────┬─────────┘
                          │
                ┌─────────▼─────────┐
                │ Query Sanitization│
                │ - Pattern blocking │
                │ - UTF-8 attacks   │
                │ - Injection       │
                └─────────┬─────────┘
                          │
                ┌─────────▼─────────┐
                │ Complexity Check  │
                │ - Resource limits │
                │ - Pattern limits  │
                │ - Depth analysis  │
                └─────────┬─────────┘
                          │
                ┌─────────▼─────────┐
                │ Read-Only Check   │
                │ - Write operation │
                │ - Procedure check │
                │ - Schema changes  │
                └─────────┬─────────┘
                          │
                ┌─────────▼─────────┐
                │ Audit Logging     │
                │ - Query logging   │
                │ - Response logging│
                │ - Error logging   │
                └─────────┬─────────┘
                          │
                ┌─────────▼─────────┐
                │ Neo4j Execution   │
                │ - Cypher execution│
                │ - Transaction     │
                │ - Result return   │
                └───────────────────┘
```

### 4.2 Security Controls

#### 4.2.1 Query Sanitization
- **Input Sanitization**: Prevents injection attacks
- **UTF-8 Attack Prevention**: Blocks homographs, zero-width chars
- **Pattern Blocking**: Dangerous Cypher patterns detection
- **Parameter Validation**: Secure parameter handling

#### 4.2.2 Access Control
- **Read-Only Mode**: Blocks write operations
- **Rate Limiting**: Prevents abuse and DoS
- **Session Management**: Per-session controls

#### 4.2.3 Compliance & Audit
- **Audit Logging**: Complete query/response logging
- **PII Redaction**: Optional data protection
- **Retention Policies**: Configurable log retention

## 5. Data Flow

### 5.1 Natural Language Query Flow

```
MCP Client                Server Components              Neo4j
   │                            │                         │
   │ query_graph("Who...")      │                         │
   ├───────────────────────────►│                         │
   │                            │                         │
   │                            │ 1. Security Validation  │
   │                            │ - Sanitization          │
   │                            │ - Complexity            │
   │                            │ - Read-only check       │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 2. Audit Log Query    │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 3. LLM Translation    │
   │                            │ - NLP to Cypher       │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 4. Generated Query    │
   │                            │ - Security Re-check   │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 5. Execute in Neo4j   │
   │                            │ - Cypher Execution    │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 6. Process Results    │
   │                            │ - Truncate if needed  │
   │                            │ - Format response     │
   │                            │                         │
   │◄───────────────────────────┤◄────────────────────────┤
   │ Response with answer       │                         │
   │ and generated Cypher       │                         │
```

### 5.2 Raw Cypher Query Flow

```
MCP Client                Server Components              Neo4j
   │                            │                         │
   │ execute_cypher("MATCH...") │                         │
   ├───────────────────────────►│                         │
   │                            │                         │
   │                            │ 1. Query Sanitization │
   │                            │ - Pattern validation  │
   │                            │ - Parameter check     │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 2. Complexity Check   │
   │                            │ - Resource analysis   │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 3. Read-Only Check    │
   │                            │ - Write op validation │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 4. Audit Logging      │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 5. Execute in Neo4j   │
   │                            │ - Direct Cypher exec  │
   │                            ├────────────────────────►│
   │                            │                         │
   │                            │ 6. Process Results    │
   │                            │ - Apply limits        │
   │                            │ - Format response     │
   │                            │                         │
   │◄───────────────────────────┤◄────────────────────────┤
   │ Response with results      │                         │
   │ and metadata               │                         │
```

## 6. Deployment Architecture

### 6.1 Container Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Docker Host                                   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Neo4j YASS MCP Container                      │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │           Application Layer                     │    │   │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│    │   │
│  │  │  │    FastMCP  │ │  LangChain  │ │    Neo4j    ││    │   │
│  │  │  │   Server    │ │    Client   │ │   Driver    ││    │   │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘│    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                         │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │           Security Layer                        │    │   │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│    │   │
│  │  │  │ Sanitization│ │ Rate Limit  │ │ Audit Log   ││    │   │
│  │  │  │    Engine   │ │   Engine    │ │   Service   ││    │   │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘│    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                         │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │         Runtime Dependencies                    │    │   │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│    │   │
│  │  │  │    UV       │ │   Python    │ │   Security  ││    │   │
│  │  │  │ Package Mgr │ │  3.13+     │ │  Libs       ││    │   │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘│    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Neo4j Database Container                 │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │      Neo4j Graph Database Engine              │    │   │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│    │   │
│  │  │  │   Storage   │ │   Query     │ │   Security  ││    │   │
│  │  │  │   Engine    │ │   Engine    │ │   Module    ││    │   │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘│    │   │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│    │   │
│  │  │  │   APOC      │ │   GDS       │ │   Backup    ││    │   │
│  │  │  │   Plugin    │ │   Plugin    │ │   Service   ││    │   │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘│    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Kubernetes Deployment (Optional)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   MCP Namespace                         │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │      Neo4j YASS MCP Deployment              │    │   │
│  │  │  ┌─────────────────────────────────────────┐  │    │   │
│  │  │  │     Pod (replicas: 2-5)              │  │    │   │
│  │  │  │  ┌─────────────────────────────────┐  │  │    │   │
│  │  │  │  │   Container: MCP Server       │  │  │    │   │
│  │  │  │  │   - Port: 8000                │  │  │    │   │
│  │  │  │  │   - Resources: 512Mi/1 CPU    │  │  │    │   │
│  │  │  │  │   - Health checks             │  │  │    │   │
│  │  │  │  └─────────────────────────────────┘  │  │    │   │
│  │  │  └────────────────────────────────────────┘  │    │   │
│  │  │                                              │    │   │
│  │  │  ┌─────────────────────────────────────────┐  │    │   │
│  │  │  │     Service: MCP Load Balancer        │  │    │   │
│  │  │  │   - Type: ClusterIP/LoadBalancer      │  │    │   │
│  │  │  │   - Port: 8000                        │  │    │   │
│  │  │  └────────────────────────────────────────┘  │    │   │
│  │  └────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Neo4j StatefulSet                        │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │     Neo4j Database Cluster                    │    │   │
│  │  │  ┌─────────────────────────────────────────┐  │    │   │
│  │  │  │     Pod (StatefulSet: neo4j-0,1,2)   │  │    │   │
│  │  │  │  ┌─────────────────────────────────┐  │  │    │   │
│  │  │  │  │   Container: Neo4j Server     │  │  │    │   │
│  │  │  │  │   - Port: 7687 (Bolt)         │  │  │    │   │
│  │  │  │  │   - Storage: Persistent Volumes│ │  │  │    │   │
│  │  │  │  │   - Plugins: APOC, GDS        │  │  │    │   │
│  │  │  │  └─────────────────────────────────┘  │  │    │   │
│  │  │  └────────────────────────────────────────┘  │    │   │
│  │  └────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 7. Performance & Scalability

### 7.1 Performance Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Performance Optimizations                      │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Async Workers  │  │    Caching      │  │ Connection      │ │
│  │   - Thread Pool │  │   - Schema      │  │   - Pooling     │ │
│  │   - 10 threads  │  │   - Query       │  │   - Bolt driver │ │
│  │   - Concurrency │  │   - LLM results │  │   - Reuse       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Rate Limits   │  │ Response        │  │ Token           │ │
│  │   - Per-session │  │   - Truncation  │  │   - Budgeting   │ │
│  │   - Sliding     │  │   - Size limits │  │   - Estimation  │ │
│  │   - Window      │  │   - Sampling    │  │   - Optimization│ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Scalability Patterns

#### 7.2.1 Horizontal Scaling
- **Stateless Design**: Server instances are stateless for horizontal scaling
- **Session Affinity**: Optional sticky sessions if needed
- **Load Balancing**: External load balancer distributes requests

#### 7.2.2 Vertical Scaling
- **Thread Pool Tuning**: Configurable worker threads
- **Resource Limits**: Memory and CPU constraints
- **Connection Pooling**: Efficient Neo4j connection management

## 8. Monitoring & Observability

### 8.1 Observability Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Observability Stack                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Application Metrics                     │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │  │   Query     │ │ Performance │ │ Error Rate  │     │   │
│  │  │  Counters   │ │   Timings   │ │   Tracking  │     │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Logs                                 │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │  │  Audit      │ │ Application │ │ Security    │     │   │
│  │  │  Logging    │ │   Logs      │ │   Events    │     │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Tracing                                │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │  │ Request     │ │ Security    │ │ LLM         │     │   │
│  │  │  Flow       │ │   Checks    │ │  Interaction│     │   │
│  │  │  Tracking   │ │   Timing    │ │   Metrics   │     │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              External Systems                           │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │  │  Prometheus │ │   Grafana   │ │  ELK Stack  │     │   │
│  │  │   Metrics   │ │   Dashboard │ │   Logging   │     │   │
│  │  │ Collection  │ │    & Alert  │ │   & Search  │     │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Health Checks

#### 8.2.1 Liveness Probe
- **Endpoint**: `/health`
- **Purpose**: Check if application is running
- **Response**: 200 OK if responsive

#### 8.2.2 Readiness Probe  
- **Endpoint**: `/ready`
- **Purpose**: Check if application is ready to serve traffic
- **Response**: 200 OK if Neo4j and LLM connections are healthy