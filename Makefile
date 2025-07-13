# Splunk MCP Integration - Development Makefile

.PHONY: help setup up down logs clean build test lint format install-deps

# Default target
help:
	@echo "Splunk MCP Integration - Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup          - Initial project setup (copy .env, install deps)"
	@echo "  install-deps   - Install all dependencies"
	@echo ""
	@echo "Docker Commands:"
	@echo "  up             - Start all services in background"
	@echo "  up-dev         - Start all services with logs"
	@echo "  down           - Stop all services"
	@echo "  logs           - View logs from all services"
	@echo "  logs-api       - View API gateway logs"
	@echo "  logs-frontend  - View frontend logs"
	@echo "  build          - Build all Docker images"
	@echo "  clean          - Clean up containers, volumes, and images"
	@echo ""
	@echo "Development Commands:"
	@echo "  test           - Run all tests"
	@echo "  test-backend   - Run backend tests"
	@echo "  test-frontend  - Run frontend tests"
	@echo "  lint           - Run linting for all code"
	@echo "  format         - Format all code"
	@echo ""
	@echo "Database Commands:"
	@echo "  db-init        - Initialize database schema"
	@echo "  db-migrate     - Run database migrations"
	@echo "  db-reset       - Reset database (WARNING: destroys data)"
	@echo "  db-backup      - Create database backup"
	@echo ""
	@echo "Monitoring Commands:"
	@echo "  health         - Check health of all services"
	@echo "  status         - Show status of all containers"

# Setup commands
setup: .env install-deps
	@echo "✅ Project setup complete!"

.env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📝 Created .env file from .env.example"; \
		echo "🔧 Please edit .env with your actual configuration values"; \
	fi

install-deps:
	@echo "📦 Installing backend dependencies..."
	@find services -name "requirements.txt" -exec pip install -r {} \;
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "✅ Dependencies installed!"

# Docker commands
up:
	@echo "🚀 Starting all services..."
	@docker-compose up -d
	@echo "✅ All services started! Access the app at http://localhost:3000"

up-dev:
	@echo "🚀 Starting all services with logs..."
	@docker-compose up

down:
	@echo "🛑 Stopping all services..."
	@docker-compose down

logs:
	@docker-compose logs -f

logs-api:
	@docker-compose logs -f api-gateway

logs-frontend:
	@docker-compose logs -f frontend

logs-nlp:
	@docker-compose logs -f nlp-engine

logs-db:
	@docker-compose logs -f postgres

logs-redis:
	@docker-compose logs -f redis

build:
	@echo "🔨 Building all Docker images..."
	@docker-compose build
	@echo "✅ All images built!"

clean:
	@echo "🧹 Cleaning up containers, volumes, and images..."
	@docker-compose down -v --remove-orphans
	@docker system prune -f
	@echo "✅ Cleanup complete!"

# Development commands
test: test-backend test-frontend

test-backend:
	@echo "🧪 Running backend tests..."
	@find services -name "pytest.ini" -o -name "test_*.py" | head -1 | xargs -I {} dirname {} | xargs -I {} sh -c 'cd {} && python -m pytest'

test-frontend:
	@echo "🧪 Running frontend tests..."
	@cd frontend && npm test -- --watchAll=false

lint:
	@echo "🔍 Running linting..."
	@find services -name "*.py" | xargs flake8
	@cd frontend && npm run lint

format:
	@echo "✨ Formatting code..."
	@find services -name "*.py" | xargs black
	@find services -name "*.py" | xargs isort
	@cd frontend && npm run format

# Database commands
db-init:
	@echo "🗄️ Initializing database..."
	@docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -f /docker-entrypoint-initdb.d/init.sql
	@echo "✅ Database initialized!"

db-migrate:
	@echo "🗄️ Running database migrations..."
	@docker-compose exec api-gateway alembic upgrade head
	@echo "✅ Migrations complete!"

db-reset:
	@echo "⚠️ This will destroy all data. Are you sure? [y/N]" && read ans && [ $${ans:-N} = y ]
	@docker-compose down postgres
	@docker volume rm mcp_postgres_data
	@docker-compose up -d postgres
	@sleep 5
	@make db-init
	@echo "✅ Database reset complete!"

db-backup:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	@docker-compose exec postgres pg_dump -U splunk_mcp_user -d splunk_mcp > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup created in backups/ directory!"

# Monitoring commands
health:
	@echo "🏥 Checking service health..."
	@curl -f http://localhost:8000/health || echo "❌ API Gateway health check failed"
	@curl -f http://localhost:3000 || echo "❌ Frontend health check failed"
	@docker-compose exec postgres pg_isready -U splunk_mcp_user || echo "❌ PostgreSQL health check failed"
	@docker-compose exec redis redis-cli ping || echo "❌ Redis health check failed"

status:
	@echo "📊 Container status:"
	@docker-compose ps

# Development shortcuts
dev: up-dev

stop: down

restart: down up

rebuild: down build up

shell-api:
	@docker-compose exec api-gateway bash

shell-db:
	@docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp

shell-redis:
	@docker-compose exec redis redis-cli

# Production commands (use with caution)
prod-build:
	@echo "🏭 Building production images..."
	@docker-compose -f docker-compose.prod.yml build

prod-up:
	@echo "🏭 Starting production services..."
	@docker-compose -f docker-compose.prod.yml up -d