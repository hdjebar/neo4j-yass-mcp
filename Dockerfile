# Multi-stage build for Neo4j YASS MCP Server
# Production-ready, optimized, and secure

# =============================================================================
# Stage 1: Builder - Install dependencies
# =============================================================================
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only dependency files first (layer caching)
COPY pyproject.toml /tmp/

# Install Python dependencies
WORKDIR /tmp
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.11-slim

# Labels
LABEL maintainer="Neo4j YASS Contributors"
LABEL description="YASS (Yet Another Secure Server) - Security-enhanced MCP server for Neo4j"
LABEL version="1.0.0"

# Create non-root user for security
RUN groupadd -r mcp && \
    useradd -r -g mcp -s /bin/bash -d /app mcp

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=mcp:mcp server.py config.py ./
COPY --chown=mcp:mcp utilities/ ./utilities/
COPY --chown=mcp:mcp tests/ ./tests/
COPY --chown=mcp:mcp .env.example ./

# Create directories for logs and data
RUN mkdir -p /app/logs/audit /app/data && \
    chown -R mcp:mcp /app/logs /app/data

# Switch to non-root user
USER mcp

# Expose port for HTTP/SSE transport
# Note: stdio transport doesn't need ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import sys,os; sys.exit(0 if any('server.py' in str(p) for p in os.popen('ps aux').readlines()) else 1)" || exit 1

# Environment variables (can be overridden)
ENV MCP_TRANSPORT=http \
    MCP_SERVER_HOST=0.0.0.0 \
    MCP_SERVER_PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run the server
CMD ["python", "server.py"]
