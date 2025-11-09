# Mermaid Architecture Diagrams: Neo4j YASS MCP

## High-Level Architecture

```mermaid
graph TB
    subgraph "MCP Client Layer"
        A["MCP Client (Claude Desktop, Web Apps, etc.)"]
    end

    subgraph "Neo4j YASS MCP Server"
        B["FastMCP Framework<br/>(stdio/HTTP/SSE transport)"]
        
        subgraph "Security Layer"
            C["Query Sanitizer<br/>(injection, UTF-8)"]
            D["Read-Only Validation"]
            E["Rate Limiter Service"]
        end
        
        F["Audit Logger<br/>(Compliance & Forensics)"]
        G["LangChain Layer<br/>(GraphCypherQAChain)"]
        H["Neo4j Driver<br/>(Database Connection)"]
    end

    subgraph "Neo4j Database Layer"
        I["Neo4j Graph Database<br/>(Graph Database Engine)"]
    end

    A --> B
    B --> C
    B --> D
    B --> E
    C --> F
    D --> F
    E --> F
    F --> G
    G --> H
    H --> I
```

## Component Architecture

```mermaid
graph TB
    subgraph "Server Components"
        SA["server.py<br/>Main MCP server entry point"]
        SB["secure_graph.py<br/>Security wrapper for Neo4jGraph"]
        SC["tool_wrappers.py<br/>Rate limiting and logging decorators"]
    end

    subgraph "Configuration Module"
        CA["config/llm_config.py<br/>LLM provider configuration"]
        CB["config/utils.py<br/>General utilities"]
    end

    subgraph "Security Module"
        SAA["security/sanitizer.py<br/>Query sanitization logic"]
        SAB["security/audit_logger.py<br/>Audit logging implementation"]
        SAC["security/complexity_limiter.py<br/>Query complexity analysis"]
        SAD["security/rate_limiter.py<br/>Rate limiting implementation"]
    end

    SA --> SB
    SA --> SC
    SA --> CA
    SA --> SAA
    SA --> SAB
    SA --> SAC
    SA --> SAD
```

## Security Architecture (Defense-in-Depth)

```mermaid
graph TB
    A["MCP Client"] --> B["Transport Layer<br/>- HTTP/SSE/stdio<br/>- TLS (if HTTPS)"]
    B --> C["Input Validation<br/>- Query length<br/>- Parameter names<br/>- Format checks"]
    C --> D["Query Sanitization<br/>- Pattern blocking<br/>- UTF-8 attacks<br/>- Injection"]
    D --> E["Complexity Check<br/>- Resource limits<br/>- Pattern limits<br/>- Depth analysis"]
    E --> F["Read-Only Check<br/>- Write operation<br/>- Procedure check<br/>- Schema changes"]
    F --> G["Audit Logging<br/>- Query logging<br/>- Response logging<br/>- Error logging"]
    G --> H["Neo4j Execution<br/>- Cypher execution<br/>- Transaction<br/>- Result return"]
```

## Natural Language Query Flow

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Server as Server Components
    participant Neo4j as Neo4j Database
    
    Client->>Server: query_graph("Who starred in Top Gun?")
    Note over Server: 1. Security Validation<br/>- Sanitization<br/>- Complexity<br/>- Read-only check
    Server->>Neo4j: Audit Log Query
    Note over Server: 2. LLM Translation<br/>- NLP to Cypher
    Server->>Neo4j: Generated Query Validation
    Note over Server: 3. Execute in Neo4j<br/>- Cypher Execution
    Server->>Neo4j: Process Results
    Note over Server: 4. Process Results<br/>- Truncate if needed<br/>- Format response
    Server->>Client: Response with answer and generated Cypher
```

## Raw Cypher Query Flow

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Server as Server Components
    participant Neo4j as Neo4j Database
    
    Client->>Server: execute_cypher("MATCH (n:Movie) RETURN n")
    Note over Server: 1. Query Sanitization<br/>- Pattern validation<br/>- Parameter check
    Server->>Neo4j: 2. Complexity Check<br/>- Resource analysis
    Server->>Neo4j: 3. Read-Only Check<br/>- Write op validation
    Server->>Neo4j: 4. Audit Logging
    Note over Server: 5. Execute in Neo4j<br/>- Direct Cypher exec
    Server->>Neo4j: 6. Process Results<br/>- Apply limits<br/>- Format response
    Server->>Client: Response with results and metadata
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Host"
        subgraph "Neo4j YASS MCP Container"
            SA["Application Layer"]
            subgraph "App Services"
                SAA["FastMCP Server"]
                SAB["LangChain Client"]
                SAC["Neo4j Driver"]
            end
            
            SB["Security Layer"]
            subgraph "Security Services"
                SBA["Sanitization Engine"]
                SBB["Rate Limit Engine"]
                SBC["Audit Log Service"]
            end
            
            SC["Runtime Dependencies"]
            subgraph "Runtime"
                SCC["UV Package Manager"]
                SCB["Python 3.13+"]
                SCD["Security Libraries"]
            end
        end
        
        subgraph "Neo4j Database Container"
            DA["Neo4j Graph Database Engine"]
            subgraph "Database Services"
                DAA["Storage Engine"]
                DAB["Query Engine"]
                DAC["Security Module"]
                DAD["APOC Plugin"]
                DAE["GDS Plugin"]
                DAF["Backup Service"]
            end
        end
    end

    SAA -.-> DAA
    SAB -.-> DA
    SAC -.-> DA
    SBA -.-> DA
    SBB -.-> DA
    SBC -.-> DA
```

## Kubernetes Deployment Architecture

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "MCP Namespace"
            subgraph "Neo4j YASS MCP Deployment"
                subgraph "MCP Pod (replicas: 2-5)"
                    MA["Container: MCP Server<br/>- Port: 8000<br/>- Resources: 512Mi/1 CPU<br/>- Health checks"]
                end
                
                MB["Service: MCP Load Balancer<br/>- Type: ClusterIP/LoadBalancer<br/>- Port: 8000"]
            end
        end
        
        subgraph "Neo4j StatefulSet"
            subgraph "Neo4j Database Cluster"
                subgraph "Pod (StatefulSet: neo4j-0,1,2)"
                    NA["Container: Neo4j Server<br/>- Port: 7687 (Bolt)<br/>- Storage: Persistent Volumes<br/>- Plugins: APOC, GDS"]
                end
            end
        end
    end
```

## Performance & Scalability Architecture

```mermaid
graph TB
    subgraph "Performance Optimizations"
        A["Async Workers<br/>- Thread Pool<br/>- 10 threads<br/>- Concurrency"]
        B["Caching<br/>- Schema<br/>- Query<br/>- LLM results"]
        C["Connection<br/>- Pooling<br/>- Bolt driver<br/>- Reuse"]
        D["Rate Limits<br/>- Per-session<br/>- Sliding<br/>- Window"]
        E["Response<br/>- Truncation<br/>- Size limits<br/>- Sampling"]
        F["Token<br/>- Budgeting<br/>- Estimation<br/>- Optimization"]
    end

    A --> B
    A --> C
    B --> D
    C --> D
    D --> E
    E --> F
```

## Observability Architecture

```mermaid
graph TB
    subgraph "Application Metrics"
        MA["Query Counters"]
        MB["Performance Timings"]
        MC["Error Rate Tracking"]
    end

    subgraph "Logs"
        LA["Audit Logging"]
        LB["Application Logs"]
        LC["Security Events"]
    end

    subgraph "Tracing"
        TA["Request Flow Tracking"]
        TB["Security Checks Timing"]
        TC["LLM Interaction Metrics"]
    end

    subgraph "External Systems"
        EA["Prometheus<br/>Metrics Collection"]
        EB["Grafana<br/>Dashboard & Alert"]
        EC["ELK Stack<br/>Logging & Search"]
    end

    MA --> EA
    MB --> EA
    MC --> EA
    LA --> EB
    LB --> EB
    LC --> EB
    TA --> EC
    TB --> EC
    TC --> EC
```

## Layered Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        A["MCP Protocol Layer<br/>- FastMCP Framework<br/>- Transport: stdio/HTTP/SSE"]
    end

    subgraph "Security Layer"
        B1["Query Sanitizer<br/>- Injection Prevention<br/>- UTF-8 Attack Prevention"]
        B2["Access Control<br/>- Read-Only Mode<br/>- Rate Limiting"]
        B3["Audit Layer<br/>- Query Logging<br/>- Compliance"]
    end

    subgraph "Business Logic Layer"
        C["LangChain Integration<br/>- Natural Language Processing<br/>- Cypher Query Generation"]
    end

    subgraph "Data Access Layer"
        D["Neo4j Driver<br/>- Bolt Protocol<br/>- Connection Pooling"]
    end

    subgraph "Data Layer"
        E["Neo4j Graph Database<br/>- Graph Storage Engine<br/>- APOC & GDS Plugins"]
    end

    A --> B1
    A --> B2
    A --> B3
    B1 --> C
    B2 --> C
    B3 --> C
    C --> D
    D --> E
```