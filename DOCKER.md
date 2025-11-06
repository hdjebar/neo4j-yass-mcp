# Docker Deployment Guide

Complete guide to deploying Neo4j YASS MCP Server with Docker.

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Dockerfile Explained](#dockerfile-explained)
- [Docker Compose](#docker-compose)
- [Configuration](#configuration)
- [Networking](#networking)
- [Storage & Volumes](#storage--volumes)
- [Security](#security)
- [Multi-Instance Deployment](#multi-instance-deployment)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+ (or docker-compose 1.29+)
- Neo4j 5.x running (separate instance)

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/neo4j-yass-mcp.git
cd neo4j-yass-mcp

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Start the Server

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

### 3. Verify

```bash
# Check health
curl http://localhost:8000/health

# View logs for "initialized successfully"
docker compose logs | grep "initialized successfully"
```

---

## 📦 Dockerfile Explained

### Multi-Stage Build

The [Dockerfile](Dockerfile) uses a **multi-stage build** for optimization:

```dockerfile
# Stage 1: Builder - Install dependencies
FROM python:3.11-slim as builder
# ... install dependencies in virtual environment

# Stage 2: Runtime - Minimal image
FROM python:3.11-slim
# ... copy only virtual environment and code
```

**Benefits:**
- ✅ Smaller final image (~150MB vs ~500MB)
- ✅ Faster builds (layer caching)
- ✅ No build tools in production image
- ✅ Better security (minimal attack surface)

### Security Features

```dockerfile
# Non-root user
RUN groupadd -r mcp && useradd -r -g mcp mcp
USER mcp

# Minimal dependencies
RUN apt-get install ca-certificates # Only essentials

# No cache files
RUN pip install --no-cache-dir ...
```

### Build Arguments

You can customize the build:

```bash
# Build with different Python version
docker build --build-arg PYTHON_VERSION=3.12 -t neo4j-yass-mcp .

# Build for specific platform
docker build --platform linux/amd64 -t neo4j-yass-mcp .
```

---

## 🐳 Docker Compose

### Basic Usage

```bash
# Start
docker compose up -d

# Stop
docker compose stop

# Restart
docker compose restart

# Stop and remove
docker compose down

# View logs
docker compose logs -f

# Execute command in container
docker compose exec neo4j-yass-mcp bash
```

### Environment Variables

Configure via `.env` file:

```bash
# Minimum configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_PASSWORD=your-strong-password
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-api-key
```

All variables from [.env.example](.env.example) are supported.

---

## ⚙️ Configuration

### Transport Modes

#### HTTP (Recommended for Docker)

```bash
# In .env
MCP_TRANSPORT=http
MCP_SERVER_HOST=0.0.0.0  # Listen on all interfaces
MCP_SERVER_PORT=8000
MCP_SERVER_PATH=/mcp/
```

Access: `http://localhost:8000/mcp/`

#### SSE (Legacy)

```bash
# In .env
MCP_TRANSPORT=sse
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
```

#### Stdio (Not for Docker)

Stdio mode is for local/CLI use, not Docker networking.

---

## 🌐 Networking

### Option 1: External Neo4j Network (Recommended)

If Neo4j is in another Docker Compose stack:

```yaml
# docker-compose.yml
networks:
  neo4j-stack:
    external: true  # Connects to existing network
```

```bash
# .env
NEO4J_URI=bolt://neo4j:7687  # Use container name
```

**Setup:**
```bash
# 1. Create network (if not exists)
docker network create neo4j-stack

# 2. Start Neo4j in that network
cd /path/to/neo4j
docker compose up -d

# 3. Start MCP server (auto-joins neo4j-stack)
cd /path/to/neo4j-yass-mcp
docker compose up -d
```

### Option 2: Host Network

If Neo4j is on host machine (localhost):

```yaml
# docker-compose.yml - uncomment this
network_mode: "host"
```

```bash
# .env
NEO4J_URI=bolt://localhost:7687
```

**Note:** Disables Docker networking, uses host's network directly.

### Option 3: host.docker.internal

If Neo4j is on host, but you want Docker networking:

```bash
# .env
NEO4J_URI=bolt://host.docker.internal:7687
```

Works on Docker Desktop (Mac/Windows). On Linux, add:

```yaml
# docker-compose.yml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

### Option 4: Cloud Neo4j (AuraDB)

```bash
# .env
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-aura-password
```

No network configuration needed (uses internet).

---

## 💾 Storage & Volumes

### Volumes in docker-compose.yml

```yaml
volumes:
  # Audit logs (persistent)
  - ./data/logs:/app/logs

  # Environment file (read-only)
  - ./.env:/app/.env:ro
```

### Directory Structure

```
neo4j-yass-mcp/
├── data/
│   └── logs/
│       └── audit/          # Audit logs (if enabled)
│           ├── audit_2024-11-06.log
│           └── audit_2024-11-07.log
└── .env                    # Configuration (mounted read-only)
```

### Backup Audit Logs

```bash
# Backup logs directory
tar -czf audit-logs-$(date +%Y%m%d).tar.gz data/logs/

# Restore
tar -xzf audit-logs-20241106.tar.gz
```

---

## 🔒 Security

### Non-Root User

The container runs as `mcp:mcp` (UID 999):

```dockerfile
USER mcp  # Not root!
```

### File Permissions

```bash
# On host, logs are owned by UID 999
ls -la data/logs/
# drwxr-xr-x 2 999 999 4096 Nov  6 20:00 audit/

# To access as current user
sudo chown -R $USER:$USER data/logs/
```

### Secrets Management

**❌ Don't:**
```bash
# Hardcode in docker-compose.yml
environment:
  LLM_API_KEY: sk-hardcoded-key  # BAD!
```

**✅ Do:**
```bash
# Use .env file
LLM_API_KEY=sk-your-key

# Or Docker secrets (Swarm mode)
docker secret create llm_api_key /path/to/key
```

### Image Scanning

```bash
# Scan for vulnerabilities
docker scan neo4j-yass-mcp

# Or with Trivy
trivy image neo4j-yass-mcp:latest
```

---

## 🚀 Multi-Instance Deployment

For high availability or multi-database setups:

```bash
# Use multi-instance compose
docker compose -f docker-compose.multi-instance.yml up -d
```

See [docker-compose.multi-instance.yml](docker-compose.multi-instance.yml) for details.

**Features:**
- Multiple MCP servers on different ports
- Each connects to different Neo4j database
- Load balancing ready
- Horizontal scaling

---

## 🐛 Troubleshooting

### Issue: Container Exits Immediately

```bash
# Check logs
docker compose logs

# Common causes:
# 1. Weak password detected
# Solution: Set strong password or ALLOW_WEAK_PASSWORDS=true

# 2. Cannot connect to Neo4j
# Solution: Check NEO4J_URI and Neo4j is running

# 3. Missing LLM_API_KEY
# Solution: Set in .env file
```

### Issue: Cannot Connect to Neo4j

```bash
# Test from container
docker compose exec neo4j-yass-mcp bash

# Inside container:
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver(
    'bolt://neo4j:7687',
    auth=('neo4j', 'password')
)
driver.verify_connectivity()
print('Connected!')
"

# Check Neo4j network
docker network inspect neo4j-stack
```

### Issue: Port Already in Use

```bash
# Error: bind: address already in use

# Solution 1: Change port
MCP_SERVER_PORT=8001  # In .env

# Solution 2: Kill process using port
lsof -ti:8000 | xargs kill -9

# Solution 3: Remove conflicting container
docker rm -f $(docker ps -q -f "publish=8000")
```

### Issue: Permission Denied (Logs)

```bash
# Error: Permission denied: '/app/logs/audit/audit.log'

# Solution: Fix permissions on host
sudo chown -R 999:999 data/logs/

# Or run as current user (less secure)
docker compose run --user $(id -u):$(id -g) neo4j-yass-mcp
```

### Issue: Health Check Failing

```bash
# Check health status
docker inspect neo4j-yass-mcp | grep -A 10 Health

# View health check logs
docker inspect --format='{{json .State.Health}}' neo4j-yass-mcp | jq

# Common causes:
# 1. Server not starting (check logs)
# 2. Wrong health check command
# 3. Server timeout (increase start_period)
```

---

## 📊 Build & Push to Registry

### Build Image

```bash
# Build locally
docker build -t neo4j-yass-mcp:latest .

# Build for specific platform
docker build --platform linux/amd64 -t neo4j-yass-mcp:latest .

# Build with tag
docker build -t yourusername/neo4j-yass-mcp:1.0.0 .
```

### Push to Docker Hub

```bash
# Login
docker login

# Tag
docker tag neo4j-yass-mcp:latest yourusername/neo4j-yass-mcp:1.0.0

# Push
docker push yourusername/neo4j-yass-mcp:1.0.0
```

### Push to Private Registry

```bash
# Tag for private registry
docker tag neo4j-yass-mcp:latest registry.example.com/neo4j-yass-mcp:1.0.0

# Push
docker push registry.example.com/neo4j-yass-mcp:1.0.0
```

---

## 🔧 Advanced Configuration

### Custom Entrypoint

```yaml
# docker-compose.yml
services:
  neo4j-yass-mcp:
    # ...
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        echo "Starting server..."
        python server.py
```

### Resource Limits

```yaml
# docker-compose.yml
services:
  neo4j-yass-mcp:
    # ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Logging Driver

```yaml
# docker-compose.yml
services:
  neo4j-yass-mcp:
    # ...
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 📚 References

- **Dockerfile Best Practices**: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
- **Docker Compose Reference**: https://docs.docker.com/compose/compose-file/
- **Multi-stage Builds**: https://docs.docker.com/build/building/multi-stage/
- **Docker Security**: https://docs.docker.com/engine/security/

---

## ✅ Quick Reference

```bash
# Build
docker build -t neo4j-yass-mcp .

# Run standalone
docker run -d -p 8000:8000 --env-file .env neo4j-yass-mcp

# Docker Compose
docker compose up -d        # Start
docker compose down         # Stop
docker compose logs -f      # Logs
docker compose ps           # Status
docker compose exec neo4j-yass-mcp bash  # Shell

# Debug
docker compose logs --tail=100
docker exec -it neo4j-yass-mcp bash
docker inspect neo4j-yass-mcp

# Cleanup
docker compose down -v      # Remove volumes
docker system prune -a      # Clean all
```

---

**The Dockerfile is production-ready and optimized for security and performance!** 🐳
