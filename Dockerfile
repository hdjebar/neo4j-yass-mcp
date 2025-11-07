# Multi-stage build for Neo4j YASS MCP Server
# Production-ready, optimized, and secure

# Build arguments for versioning and customization
ARG PYTHON_VERSION=3.11
ARG APP_VERSION=1.0.0

# =============================================================================
# Stage 1: Builder - Install dependencies
# =============================================================================
FROM python:${PYTHON_VERSION}-slim as builder

# Install build dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the official installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH for subsequent commands
ENV PATH="/root/.cargo/bin:$PATH"

# Verify uv installation
RUN uv --version

# Create virtual environment using uv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

# Copy dependency files AND minimal source structure for installation
# This allows uv to properly install the package with dependencies
COPY pyproject.toml /tmp/
COPY src/ /tmp/src/

# Install Python dependencies in virtual environment using uv
# uv is 10-100x faster than pip for dependency resolution and installation
# Using BuildKit cache mount for uv cache dramatically speeds up rebuilds
WORKDIR /tmp
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install .

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:${PYTHON_VERSION}-slim

# Labels for image metadata and security scanning
ARG APP_VERSION
LABEL maintainer="Neo4j YASS Contributors"
LABEL description="YASS (Yet Another Simple/Smart) MCP server for Neo4j"
LABEL version="${APP_VERSION}"
LABEL org.opencontainers.image.source="https://github.com/hdjebar/neo4j-yass-mcp"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.version="${APP_VERSION}"

# Create non-root user for security
RUN groupadd -r mcp && \
    useradd -r -g mcp -s /bin/bash -d /app mcp

# Install runtime dependencies only (procps for better health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder (includes installed package)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application source code (exclude tests from production)
COPY --chown=mcp:mcp src/ ./src/
COPY --chown=mcp:mcp .env.example ./
COPY --chown=mcp:mcp pyproject.toml ./

# Create directories for logs and data with proper permissions
RUN mkdir -p /app/logs/audit /app/data && \
    chown -R mcp:mcp /app/logs /app/data

# Switch to non-root user
USER mcp

# Expose port for HTTP/SSE transport
# Note: stdio transport doesn't need ports
EXPOSE 8000

# Environment variables (can be overridden)
ENV MCP_TRANSPORT=http \
    MCP_SERVER_HOST=0.0.0.0 \
    MCP_SERVER_PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Improved health check using pidof (more efficient than ps parsing)
# Checks if python process is running with our module
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD pgrep -f "python.*neo4j_yass_mcp.server" > /dev/null || exit 1

# Run the server
# Note: Package already installed in virtual environment from builder stage
CMD ["python", "-m", "neo4j_yass_mcp.server"]
