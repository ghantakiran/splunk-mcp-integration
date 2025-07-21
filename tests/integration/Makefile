# Integration Testing Makefile for Splunk MCP Integration
# This Makefile provides convenient commands for running integration tests

.PHONY: help install test test-all test-e2e test-performance test-security test-health test-quick clean setup-env
.DEFAULT_GOAL := help

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Configuration
PYTHON := python3
PIP := pip3
TEST_DIR := tests/integration
OUTPUT_DIR := test_results
VENV_DIR := venv

help: ## Show this help message
	@echo "$(BLUE)Splunk MCP Integration - Integration Testing$(NC)"
	@echo "$(BLUE)==============================================$(NC)"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Examples:"
	@echo "  $(YELLOW)make test-all$(NC)          # Run all integration tests"
	@echo "  $(YELLOW)make test-e2e$(NC)          # Run end-to-end tests only"
	@echo "  $(YELLOW)make test-performance$(NC)  # Run performance tests only"
	@echo "  $(YELLOW)make test-security$(NC)     # Run security tests only"

install: ## Install test dependencies
	@echo "$(BLUE)Installing test dependencies...$(NC)"
	$(PIP) install -r requirements-test.txt
	@echo "$(GREEN)Dependencies installed successfully$(NC)"

setup-env: ## Set up test environment
	@echo "$(BLUE)Setting up test environment...$(NC)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "$(GREEN)Virtual environment created$(NC)"; \
	fi
	@echo "$(YELLOW)Activate with: source $(VENV_DIR)/bin/activate$(NC)"

test-health: ## Check service health before running tests
	@echo "$(BLUE)Checking service health...$(NC)"
	$(PYTHON) test_runner.py --skip-health-check=false --paths=[] --output-dir=$(OUTPUT_DIR)

test-quick: ## Run quick smoke tests
	@echo "$(BLUE)Running quick smoke tests...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) -m pytest test_e2e_conversation_flow.py::TestCompleteConversationFlow::test_query_to_visualization_flow -v --tb=short
	@echo "$(GREEN)Quick tests completed$(NC)"

test-e2e: ## Run end-to-end conversation flow tests
	@echo "$(BLUE)Running end-to-end integration tests...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) test_runner.py --markers="not performance and not security" --paths=test_e2e_conversation_flow.py --output-dir=$(OUTPUT_DIR)
	@echo "$(GREEN)End-to-end tests completed$(NC)"

test-performance: ## Run performance and load tests
	@echo "$(BLUE)Running performance integration tests...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) test_runner.py --markers="performance" --paths=test_performance_integration.py --output-dir=$(OUTPUT_DIR)
	@echo "$(GREEN)Performance tests completed$(NC)"

test-security: ## Run security integration tests
	@echo "$(BLUE)Running security integration tests...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) test_runner.py --markers="security" --paths=test_security_integration.py --output-dir=$(OUTPUT_DIR)
	@echo "$(GREEN)Security tests completed$(NC)"

test-all: ## Run all integration tests with full reporting
	@echo "$(BLUE)Running complete integration test suite...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) test_runner.py --paths=test_e2e_conversation_flow.py test_performance_integration.py test_security_integration.py --output-dir=$(OUTPUT_DIR)
	@echo "$(GREEN)All integration tests completed$(NC)"
	@echo "$(YELLOW)Check $(OUTPUT_DIR)/integration_summary.html for detailed results$(NC)"

test: test-all ## Alias for test-all

test-ci: ## Run tests suitable for CI environment (with timeouts and retries)
	@echo "$(BLUE)Running CI integration tests...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	timeout 1800 $(PYTHON) test_runner.py --skip-health-check --paths=test_e2e_conversation_flow.py --output-dir=$(OUTPUT_DIR) || exit 1
	@echo "$(GREEN)CI tests completed$(NC)"

test-local: ## Run tests for local development (skip flaky tests)
	@echo "$(BLUE)Running local development tests...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) -m pytest test_e2e_conversation_flow.py -v --tb=short -m "not flaky"
	@echo "$(GREEN)Local tests completed$(NC)"

test-services: ## Test individual service endpoints
	@echo "$(BLUE)Testing individual service endpoints...$(NC)"
	@echo "Testing API Gateway..."
	@curl -f http://localhost:8000/health || echo "$(RED)API Gateway not responding$(NC)"
	@echo "Testing NLP Engine..."
	@curl -f http://localhost:8001/health || echo "$(RED)NLP Engine not responding$(NC)"
	@echo "Testing Visualization Service..."
	@curl -f http://localhost:8002/health || echo "$(RED)Visualization Service not responding$(NC)"
	@echo "Testing Alert Manager..."
	@curl -f http://localhost:8003/health || echo "$(RED)Alert Manager not responding$(NC)"

benchmark: ## Run performance benchmarks
	@echo "$(BLUE)Running performance benchmarks...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) -m pytest test_performance_integration.py::TestPerformanceIntegration::test_nlp_engine_response_time -v --benchmark-only
	@echo "$(GREEN)Benchmarks completed$(NC)"

stress-test: ## Run stress tests with high load
	@echo "$(BLUE)Running stress tests...$(NC)"
	@echo "$(RED)Warning: This will put high load on the system$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) -m pytest test_performance_integration.py::TestLoadTesting -v --tb=short
	@echo "$(GREEN)Stress tests completed$(NC)"

security-scan: ## Run security vulnerability scans
	@echo "$(BLUE)Running security scans...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) -m pytest test_security_integration.py -v --tb=short
	@echo "$(GREEN)Security scans completed$(NC)"

generate-report: ## Generate test reports from existing results
	@echo "$(BLUE)Generating test reports...$(NC)"
	@if [ -f "test_results.json" ]; then \
		$(PYTHON) -c "import json; from test_runner import IntegrationTestRunner; runner = IntegrationTestRunner({}); runner.generate_html_summary_from_json('test_results.json')"; \
		echo "$(GREEN)Reports generated$(NC)"; \
	else \
		echo "$(RED)No test results found. Run tests first.$(NC)"; \
	fi

clean: ## Clean up test artifacts and reports
	@echo "$(BLUE)Cleaning up test artifacts...$(NC)"
	rm -rf $(OUTPUT_DIR)
	rm -f test_results.json
	rm -f test_report.html
	rm -f integration_test_report.json
	rm -f integration_summary.html
	rm -rf __pycache__
	rm -rf .pytest_cache
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	@echo "$(GREEN)Cleanup completed$(NC)"

watch: ## Watch for changes and run tests automatically
	@echo "$(BLUE)Watching for changes...$(NC)"
	@echo "$(YELLOW)Install 'entr' for file watching: brew install entr$(NC)"
	find . -name "*.py" | entr -c make test-quick

docker-test: ## Run tests in Docker container
	@echo "$(BLUE)Running tests in Docker...$(NC)"
	docker run --rm -v $(PWD):/workspace -w /workspace python:3.9 bash -c "pip install -r requirements-test.txt && make test-all"

lint: ## Run code quality checks on test files
	@echo "$(BLUE)Running code quality checks...$(NC)"
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	@echo "$(GREEN)Code quality checks completed$(NC)"

coverage: ## Run tests with coverage reporting
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) -m pytest --cov=. --cov-report=html:$(OUTPUT_DIR)/coverage --cov-report=term
	@echo "$(GREEN)Coverage report generated in $(OUTPUT_DIR)/coverage$(NC)"

debug: ## Run tests in debug mode with verbose output
	@echo "$(BLUE)Running tests in debug mode...$(NC)"
	$(PYTHON) -m pytest test_e2e_conversation_flow.py -v -s --tb=long --log-cli-level=DEBUG

profile: ## Profile test performance
	@echo "$(BLUE)Profiling test performance...$(NC)"
	mkdir -p $(OUTPUT_DIR)
	$(PYTHON) -m pytest --profile --profile-svg --profile-dump=$(OUTPUT_DIR)/profile.pstats
	@echo "$(GREEN)Profile data saved to $(OUTPUT_DIR)/profile.pstats$(NC)"

verify-setup: ## Verify test setup and dependencies
	@echo "$(BLUE)Verifying test setup...$(NC)"
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Pytest version: $$($(PYTHON) -m pytest --version)"
	@echo "Required packages:"
	@$(PYTHON) -c "import pytest, aiohttp, asyncio; print('✓ All required packages available')" || echo "$(RED)Missing required packages$(NC)"
	@echo "Test files:"
	@ls -la test_*.py || echo "$(RED)Test files not found$(NC)"
	@echo "$(GREEN)Setup verification completed$(NC)"

# Development helpers
dev-setup: setup-env install ## Set up development environment
	@echo "$(GREEN)Development environment ready$(NC)"

dev-test: test-health test-quick ## Quick development test cycle
	@echo "$(GREEN)Development test cycle completed$(NC)"

# CI/CD targets
ci-install: ## Install dependencies for CI
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-test.txt

ci-test: ci-install test-ci ## Run full CI test suite

# Documentation
docs: ## Generate test documentation
	@echo "$(BLUE)Generating test documentation...$(NC)"
	@echo "# Integration Test Documentation" > TEST_DOCS.md
	@echo "" >> TEST_DOCS.md
	@echo "## Test Files" >> TEST_DOCS.md
	@echo "" >> TEST_DOCS.md
	@for file in test_*.py; do \
		echo "### $$file" >> TEST_DOCS.md; \
		$(PYTHON) -c "import ast; import sys; \
		with open('$$file') as f: tree = ast.parse(f.read()); \
		[print('- ' + node.name + ': ' + ast.get_docstring(node, '')) for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]" >> TEST_DOCS.md; \
		echo "" >> TEST_DOCS.md; \
	done
	@echo "$(GREEN)Documentation generated in TEST_DOCS.md$(NC)"

# Environment management
env-check: ## Check environment variables
	@echo "$(BLUE)Checking environment variables...$(NC)"
	@echo "Required variables:"
	@echo "  API_GATEWAY_HOST=${API_GATEWAY_HOST:-localhost}"
	@echo "  API_GATEWAY_PORT=${API_GATEWAY_PORT:-8000}"
	@echo "  NLP_ENGINE_HOST=${NLP_ENGINE_HOST:-localhost}"
	@echo "  NLP_ENGINE_PORT=${NLP_ENGINE_PORT:-8001}"
	@echo "  REDIS_HOST=${REDIS_HOST:-localhost}"
	@echo "  POSTGRES_HOST=${POSTGRES_HOST:-localhost}"

env-template: ## Create environment template
	@echo "$(BLUE)Creating environment template...$(NC)"
	@cat > .env.template << 'EOF'
# Integration Test Environment Configuration
# Copy this file to .env and adjust values as needed

# Service Endpoints
API_GATEWAY_HOST=localhost
API_GATEWAY_PORT=8000
NLP_ENGINE_HOST=localhost
NLP_ENGINE_PORT=8001
VISUALIZATION_HOST=localhost
VISUALIZATION_PORT=8002
ALERT_MANAGER_HOST=localhost
ALERT_MANAGER_PORT=8003

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_TEST_DB=test_splunk_mcp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_TEST_DB=15

# Test Configuration
TEST_TIMEOUT=30
TEST_RETRIES=3
SKIP_SLOW_TESTS=false
EOF
	@echo "$(GREEN)Environment template created as .env.template$(NC)"

# Show current configuration
config: ## Show current test configuration
	@echo "$(BLUE)Current Test Configuration$(NC)"
	@echo "=========================="
	@echo "Test Directory: $(TEST_DIR)"
	@echo "Output Directory: $(OUTPUT_DIR)"
	@echo "Python: $(PYTHON)"
	@echo "Virtual Environment: $(VENV_DIR)"
	@echo ""
	@$(MAKE) env-check