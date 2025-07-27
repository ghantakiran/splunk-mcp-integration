# Docker Deployment Guide

This guide provides step-by-step instructions for deploying the Splunk MCP Integration platform using Docker and Docker Compose for development and testing environments.

## Overview

Docker deployment offers:
- Quick setup for development and testing
- Isolated service containers
- Easy service scaling and management
- Consistent development environment
- Simple backup and restore procedures

## Prerequisites

### System Requirements
- **Docker Engine**: 20.10+
- **Docker Compose**: 2.0+
- **Memory**: 8GB+ RAM
- **Storage**: 20GB+ free space
- **CPU**: 4+ cores

### Software Installation

#### Ubuntu/Debian
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt update
sudo apt install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

#### CentOS/RHEL
```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

#### macOS
```bash
# Install Docker Desktop
brew install --cask docker

# Or download from: https://www.docker.com/products/docker-desktop/
```

#### Windows
```powershell
# Install Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop/

# Or using Chocolatey
choco install docker-desktop
```

## Project Setup

### 1. Clone and Prepare Repository
```bash
# Clone repository
git clone https://github.com/your-org/splunk-mcp-integration.git
cd splunk-mcp-integration

# Create environment file
cp .env.example .env

# Create required directories
mkdir -p logs data/postgres data/redis
```

### 2. Configure Environment Variables
```bash
# Edit .env file with your configuration
vi .env

# Essential variables for Docker deployment:
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=splunk_mcp
POSTGRES_USER=splunk_mcp_user
POSTGRES_PASSWORD=secure_db_password

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_redis_password

SPLUNK_HOST=your-splunk-server.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=splunk_mcp_service
SPLUNK_PASSWORD=your_splunk_password
SPLUNK_SCHEME=https

OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

JWT_SECRET_KEY=your-generated-jwt-secret
```

## Docker Compose Configuration

### 1. Main Docker Compose File
```yaml
# docker-compose.yml
version: '3.8'

services:
  # Database Services
  postgres:
    image: postgres:15-alpine
    container_name: splunk-mcp-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infrastructure/docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - splunk-mcp-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: splunk-mcp-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    environment:
      REDIS_PASSWORD: ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
      - ./infrastructure/docker/redis/redis.conf:/etc/redis/redis.conf
    ports:
      - "6379:6379"
    networks:
      - splunk-mcp-network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Core Application Services
  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile
    container_name: splunk-mcp-api-gateway
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SPLUNK_HOST=${SPLUNK_HOST}
      - SPLUNK_PORT=${SPLUNK_PORT}
      - SPLUNK_USERNAME=${SPLUNK_USERNAME}
      - SPLUNK_PASSWORD=${SPLUNK_PASSWORD}
      - SPLUNK_SCHEME=${SPLUNK_SCHEME}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENVIRONMENT=development
    ports:
      - "8000:8000"
    networks:
      - splunk-mcp-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nlp-engine:
    build:
      context: ./services/nlp-engine
      dockerfile: Dockerfile
    container_name: splunk-mcp-nlp-engine
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - ENVIRONMENT=development
    ports:
      - "8001:8001"
    networks:
      - splunk-mcp-network
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  visualization:
    build:
      context: ./services/visualization
      dockerfile: Dockerfile
    container_name: splunk-mcp-visualization
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/2
      - ENVIRONMENT=development
    ports:
      - "8002:8002"
    networks:
      - splunk-mcp-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  alert-manager:
    build:
      context: ./services/alert-manager
      dockerfile: Dockerfile
    container_name: splunk-mcp-alert-manager
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/3
      - ENVIRONMENT=development
    ports:
      - "8003:8003"
    networks:
      - splunk-mcp-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: splunk-mcp-frontend
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_ENVIRONMENT=development
    ports:
      - "3000:3000"
    networks:
      - splunk-mcp-network
    depends_on:
      - api-gateway
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Integration Services (Optional)
  slack-bot:
    build:
      context: ./services/slack-bot
      dockerfile: Dockerfile
    container_name: splunk-mcp-slack-bot
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET}
      - API_GATEWAY_URL=http://api-gateway:8000
      - ENVIRONMENT=development
    ports:
      - "8004:8004"
    networks:
      - splunk-mcp-network
    depends_on:
      - api-gateway
    profiles:
      - integrations

  teams-bot:
    build:
      context: ./services/teams-bot
      dockerfile: Dockerfile
    container_name: splunk-mcp-teams-bot
    environment:
      - TEAMS_APP_ID=${TEAMS_APP_ID}
      - TEAMS_APP_PASSWORD=${TEAMS_APP_PASSWORD}
      - API_GATEWAY_URL=http://api-gateway:8000
      - ENVIRONMENT=development
    ports:
      - "8005:8005"
    networks:
      - splunk-mcp-network
    depends_on:
      - api-gateway
    profiles:
      - integrations

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  splunk-mcp-network:
    driver: bridge
```

### 2. Development Override File
```yaml
# docker-compose.override.yml
version: '3.8'

services:
  api-gateway:
    volumes:
      - ./services/api-gateway:/app
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG

  nlp-engine:
    volumes:
      - ./services/nlp-engine:/app
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG

  visualization:
    volumes:
      - ./services/visualization:/app
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG

  frontend:
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    command: npm run dev
```

### 3. Production Override File
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    restart: unless-stopped
    volumes:
      - redis_data:/data

  api-gateway:
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=INFO
    restart: unless-stopped

  nlp-engine:
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=INFO
    restart: unless-stopped

  visualization:
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=INFO
    restart: unless-stopped

  alert-manager:
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=INFO
    restart: unless-stopped

  frontend:
    environment:
      - REACT_APP_ENVIRONMENT=production
    restart: unless-stopped
```

## Deployment Procedures

### 1. Development Deployment

#### Quick Start
```bash
# Start core services only
docker compose up -d postgres redis

# Wait for databases to be ready
echo "Waiting for databases..."
sleep 30

# Run database migrations
docker compose run --rm api-gateway python -m alembic upgrade head

# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

#### Step-by-Step Deployment
```bash
# Step 1: Build all images
docker compose build

# Step 2: Start infrastructure services
docker compose up -d postgres redis

# Step 3: Wait for health checks
docker compose exec postgres pg_isready -U splunk_mcp_user
docker compose exec redis redis-cli ping

# Step 4: Initialize database
docker compose run --rm api-gateway python -m alembic upgrade head

# Step 5: Start core application services
docker compose up -d api-gateway nlp-engine visualization alert-manager

# Step 6: Start frontend
docker compose up -d frontend

# Step 7: Verify all services
make health  # or run individual health checks
```

### 2. Production Deployment

#### Using Production Configuration
```bash
# Use production configuration
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or use production environment file
cp .env.production .env
docker compose up -d
```

#### With SSL/TLS
```bash
# Generate SSL certificates
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes

# Add SSL proxy service
docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d
```

### 3. Service-Specific Deployment

#### Deploy Only Core Services
```bash
docker compose up -d postgres redis api-gateway nlp-engine visualization
```

#### Deploy with Integration Services
```bash
# Deploy with Slack and Teams integration
docker compose --profile integrations up -d
```

#### Deploy Individual Services
```bash
# Deploy only API Gateway
docker compose up -d postgres redis
docker compose up -d api-gateway

# Deploy only NLP Engine
docker compose up -d redis
docker compose up -d nlp-engine
```

## Service Management

### 1. Monitoring and Health Checks

#### Check Service Status
```bash
# View all service status
docker compose ps

# Check specific service logs
docker compose logs -f api-gateway
docker compose logs -f nlp-engine

# Follow logs for all services
docker compose logs -f

# Check resource usage
docker stats
```

#### Health Check Commands
```bash
# Test all health endpoints
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # NLP Engine
curl http://localhost:8002/health  # Visualization
curl http://localhost:8003/health  # Alert Manager
curl http://localhost:3000         # Frontend

# Test database connectivity
docker compose exec postgres pg_isready -U splunk_mcp_user
docker compose exec redis redis-cli ping
```

### 2. Scaling Services

#### Scale Specific Services
```bash
# Scale API Gateway to 3 instances
docker compose up -d --scale api-gateway=3

# Scale NLP Engine to 2 instances
docker compose up -d --scale nlp-engine=2

# Scale with load balancer
docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d
```

#### Load Balancer Configuration
```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: splunk-mcp-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infrastructure/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - api-gateway
    networks:
      - splunk-mcp-network

  api-gateway:
    ports: []  # Remove direct port exposure
```

### 3. Data Management

#### Database Operations
```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U splunk_mcp_user -d splunk_mcp

# Run SQL commands
docker compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "SELECT version();"

# Backup database
docker compose exec postgres pg_dump -U splunk_mcp_user splunk_mcp > backup.sql

# Restore database
docker compose exec -T postgres psql -U splunk_mcp_user -d splunk_mcp < backup.sql
```

#### Redis Operations
```bash
# Connect to Redis
docker compose exec redis redis-cli

# Check Redis info
docker compose exec redis redis-cli info

# Backup Redis data
docker compose exec redis redis-cli save
docker cp $(docker compose ps -q redis):/data/dump.rdb ./redis-backup.rdb
```

### 4. Maintenance Operations

#### Update Services
```bash
# Pull latest images
docker compose pull

# Rebuild and restart services
docker compose up -d --build

# Rolling update (one service at a time)
docker compose up -d --no-deps api-gateway
docker compose up -d --no-deps nlp-engine
```

#### Clean Up Resources
```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: destroys data)
docker compose down -v

# Clean up unused images
docker image prune -f

# Clean up everything
docker system prune -af
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Service Won't Start
```bash
# Check service logs
docker compose logs service-name

# Check if ports are already in use
netstat -tlnp | grep :8000

# Restart specific service
docker compose restart service-name

# Rebuild and restart
docker compose up -d --build service-name
```

#### 2. Database Connection Issues
```bash
# Check if PostgreSQL is running
docker compose exec postgres pg_isready

# Test connection with correct credentials
docker compose exec postgres psql -U splunk_mcp_user -d splunk_mcp

# Check environment variables
docker compose config

# Reset database
docker compose down
docker volume rm splunk-mcp-integration_postgres_data
docker compose up -d postgres
```

#### 3. Memory Issues
```bash
# Check memory usage
docker stats

# Increase memory limits in docker-compose.yml
services:
  api-gateway:
    mem_limit: 1g
    mem_reservation: 512m

# Restart with more memory
docker compose down
docker compose up -d
```

#### 4. Network Issues
```bash
# Check network connectivity
docker compose exec api-gateway ping nlp-engine

# Inspect network
docker network ls
docker network inspect splunk-mcp-integration_splunk-mcp-network

# Recreate network
docker compose down
docker network prune
docker compose up -d
```

### Debugging Tools

#### Container Debugging
```bash
# Access container shell
docker compose exec api-gateway /bin/bash

# Run commands in container
docker compose exec api-gateway python -c "import sys; print(sys.path)"

# Check environment variables
docker compose exec api-gateway env

# Copy files from container
docker cp $(docker compose ps -q api-gateway):/app/logs ./container-logs
```

#### Performance Monitoring
```bash
# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Check disk usage
docker system df

# Monitor logs in real-time
docker compose logs -f --tail=100
```

## Security Configuration

### 1. Network Security
```yaml
# Add network isolation
networks:
  frontend-network:
    driver: bridge
  backend-network:
    driver: bridge
    internal: true

services:
  frontend:
    networks:
      - frontend-network
  
  api-gateway:
    networks:
      - frontend-network
      - backend-network
  
  postgres:
    networks:
      - backend-network
```

### 2. Secret Management
```bash
# Use Docker secrets
docker secret create postgres_password /path/to/password/file

# Reference in docker-compose.yml
services:
  postgres:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password

secrets:
  postgres_password:
    external: true
```

### 3. Security Hardening
```yaml
# Add security options
services:
  api-gateway:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    user: "1000:1000"
```

## Backup and Recovery

### 1. Automated Backups
```bash
# Create backup script
cat > scripts/docker-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker compose exec postgres pg_dump -U splunk_mcp_user splunk_mcp > $BACKUP_DIR/postgres.sql

# Backup Redis
docker compose exec redis redis-cli save
docker cp $(docker compose ps -q redis):/data/dump.rdb $BACKUP_DIR/redis.rdb

# Backup application logs
cp -r logs $BACKUP_DIR/

# Compress backup
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR
EOF

chmod +x scripts/docker-backup.sh

# Schedule backup
echo "0 2 * * * /path/to/scripts/docker-backup.sh" | crontab -
```

### 2. Disaster Recovery
```bash
# Create recovery script
cat > scripts/docker-restore.sh << 'EOF'
#!/bin/bash
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

# Extract backup
tar -xzf $BACKUP_FILE

# Stop services
docker compose down

# Restore PostgreSQL
docker compose up -d postgres
sleep 30
docker compose exec -T postgres psql -U splunk_mcp_user -d splunk_mcp < */postgres.sql

# Restore Redis
docker cp */redis.rdb $(docker compose ps -q redis):/data/dump.rdb
docker compose restart redis

# Start all services
docker compose up -d
EOF

chmod +x scripts/docker-restore.sh
```

---

**Next Steps**: For production deployments, consider migrating to Kubernetes using the [Kubernetes Deployment Guide](./KUBERNETES_DEPLOYMENT.md).