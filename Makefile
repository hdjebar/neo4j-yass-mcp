# Makefile for Neo4j YASS MCP development
# Provides convenient commands for development, testing, and deployment

.PHONY: help install install-dev test test-cov test-security lint format clean run run-docker build docker-up docker-down docs

# Default target
.DEFAULT_GOAL := help

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation

install: ## Install production dependencies
	uv pip install -e .

install-dev: ## Install all dependencies (dev + test + security + docs)
	uv pip install -e ".[all]"

install-test: ## Install test dependencies only
	uv pip install -e ".[dev]"

##@ Development

run: ## Run MCP server locally (Python/UV mode)
	@echo "Starting YASS MCP server..."
	@source .env 2>/dev/null || true && python -m neo4j_yass_mcp.server

run-interactive: ## Run server with interactive script
	@./run-server.sh

dev: install-dev ## Setup development environment
	@echo "Development environment ready!"
	@echo "Run 'make run' to start the server"

##@ Testing

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest -m unit

test-integration: ## Run integration tests only
	pytest -m integration

test-security: ## Run security tests only
	pytest -m security

test-cov: ## Run tests with coverage report
	pytest --cov=src/neo4j_yass_mcp --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	pytest-watch

test-parallel: ## Run tests in parallel (faster)
	pytest -n auto

test-verbose: ## Run tests with verbose output
	pytest -vv

##@ Code Quality

lint: ## Run all linters (ruff + mypy)
	@echo "Running ruff..."
	ruff check .
	@echo "Running mypy..."
	mypy src/neo4j_yass_mcp/

lint-fix: ## Run linters and auto-fix issues
	ruff check --fix .
	ruff format .

format: ## Format code with black and isort
	black .
	isort .

check: lint test ## Run linters and tests

##@ Security

security: ## Run security checks (bandit + safety + pip-audit)
	@echo "Running bandit..."
	bandit -r src/neo4j_yass_mcp/
	@echo "Running safety..."
	safety check
	@echo "Running pip-audit..."
	pip-audit

security-bandit: ## Run bandit security scanner
	bandit -r src/neo4j_yass_mcp/ -f json -o bandit-report.json

##@ Docker

docker-network: ## Create neo4j-stack network (required for first run)
	@echo "Creating neo4j-stack network..."
	@docker network inspect neo4j-stack >/dev/null 2>&1 || \
		docker network create neo4j-stack && echo "✓ Network created" || echo "✓ Network already exists"

docker-build: ## Build Docker image with uv and BuildKit cache
	@echo "Building with uv and BuildKit cache..."
	DOCKER_BUILDKIT=1 docker compose build
	@echo "✓ Build complete"

docker-up: docker-network ## Start services with Docker Compose (creates network)
	@echo "Starting services..."
	docker compose up -d
	@echo "✓ Services started"
	@echo ""
	@echo "Check logs: make docker-logs"
	@echo "Check health: docker inspect neo4j-yass-mcp | grep -A5 Health"

docker-down: ## Stop Docker services
	docker compose down

docker-logs: ## Show Docker logs
	docker compose logs -f

docker-restart: ## Restart Docker services
	docker compose restart

docker-shell: ## Open bash shell in MCP container
	docker compose exec neo4j-yass-mcp bash

docker-test-neo4j: ## Test connection to Neo4j from container
	@echo "Testing Neo4j connection..."
	@docker compose exec neo4j-yass-mcp python -c "\
		from neo4j import GraphDatabase; \
		import os; \
		uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687'); \
		user = os.getenv('NEO4J_USERNAME', 'neo4j'); \
		pwd = os.getenv('NEO4J_PASSWORD', 'password'); \
		driver = GraphDatabase.driver(uri, auth=(user, pwd)); \
		driver.verify_connectivity(); \
		print('✓ Connected to Neo4j at', uri)" || echo "✗ Connection failed"

docker-clean: ## Stop and remove Docker containers and volumes
	docker compose down -v

docker-clean-cache: ## Clean BuildKit cache (use sparingly)
	@echo "Cleaning BuildKit cache..."
	docker builder prune -f
	@echo "✓ Cache cleaned"

docker-cache-size: ## Show BuildKit cache size
	@echo "BuildKit cache usage:"
	@docker system df | grep -A1 "Build Cache"

##@ Cleanup

clean: ## Clean build artifacts and cache files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean docker-clean ## Clean everything including Docker volumes

##@ Documentation

docs-serve: ## Serve documentation locally
	mkdocs serve

docs-build: ## Build documentation
	mkdocs build

##@ CI/CD

ci-test: ## Run CI test suite
	pytest --cov=src/neo4j_yass_mcp --cov-report=xml --cov-report=term -m "not slow"

ci-lint: ## Run CI linting
	ruff check .
	mypy src/neo4j_yass_mcp/

ci: ci-lint ci-test security ## Run full CI pipeline

##@ Utilities

version: ## Show version information
	@python -c "import sys; print(f'Python: {sys.version}')"
	@uv --version || echo "uv not installed"
	@pytest --version
	@ruff --version

env: ## Show environment variables
	@echo "Environment file:"
	@cat .env 2>/dev/null || echo "No .env file found"

# Note: setup-ports and init-data-dirs utilities have been deprecated
# Port configuration is now handled via environment variables in .env
# Data directories are created automatically by the application
