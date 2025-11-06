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
	uv pip install -e ".[test]"

##@ Development

run: ## Run MCP server locally (Python/UV mode)
	@echo "Starting YASS MCP server..."
	@source .env 2>/dev/null || true && python server.py

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
	pytest --cov=utilities --cov=server --cov-report=html --cov-report=term

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
	mypy utilities/ server.py

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
	bandit -r utilities/ server.py
	@echo "Running safety..."
	safety check
	@echo "Running pip-audit..."
	pip-audit

security-bandit: ## Run bandit security scanner
	bandit -r utilities/ server.py -f json -o bandit-report.json

##@ Docker

docker-build: ## Build Docker image
	docker compose build

docker-up: ## Start services with Docker Compose
	docker compose up -d

docker-down: ## Stop Docker services
	docker compose down

docker-logs: ## Show Docker logs
	docker compose logs -f

docker-restart: ## Restart Docker services
	docker compose restart

docker-clean: ## Stop and remove Docker containers and volumes
	docker compose down -v

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
	pytest --cov=utilities --cov=server --cov-report=xml --cov-report=term -m "not slow"

ci-lint: ## Run CI linting
	ruff check .
	mypy utilities/ server.py

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

setup-ports: ## Run port allocation utility
	../utilities/setup-ports.sh .env.example

init-data-dirs: ## Initialize data directories
	./utilities/init-data-dirs.sh
