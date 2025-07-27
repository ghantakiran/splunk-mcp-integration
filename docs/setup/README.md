# Setup Documentation

This directory contains comprehensive setup and deployment documentation for the Splunk MCP Integration platform.

## Quick Start

For a complete end-to-end setup, follow these guides in order:

1. **[Credentials Setup](./CREDENTIALS_SETUP.md)** - Configure all required credentials and API keys
2. **[Splunk Setup](./SPLUNK_SETUP.md)** - Configure Splunk REST API endpoints  
3. **[Complete Setup Guide](./COMPLETE_SETUP.md)** - End-to-end deployment instructions
4. **[Docker Deployment](./DOCKER_DEPLOYMENT.md)** OR **[Kubernetes Deployment](./KUBERNETES_DEPLOYMENT.md)**

## Documentation Overview

### Essential Setup Guides

#### 🔐 [Credentials Setup Guide](./CREDENTIALS_SETUP.md)
Complete guide for setting up all required credentials including:
- Database credentials (PostgreSQL, Redis)
- AI/ML service API keys (OpenAI, Anthropic)
- JWT authentication secrets
- Integration service credentials (Slack, Teams, Email)
- SSL/TLS certificates
- Comprehensive validation scripts

#### 🔗 [Splunk Setup Guide](./SPLUNK_SETUP.md)
Comprehensive Splunk configuration documentation covering:
- Splunk Enterprise setup and configuration
- Splunk Cloud setup and configuration
- REST API endpoint configuration
- User account and permission setup
- SSL/TLS configuration for production
- Connection testing and validation scripts

#### 📋 [Complete Setup Configuration](./COMPLETE_SETUP.md)
End-to-end deployment guide that covers:
- System prerequisites and dependencies
- Environment configuration
- Development and production deployment
- Validation and testing procedures
- Monitoring and security setup
- Troubleshooting and maintenance

### Deployment Options

#### 🐳 [Docker Deployment Guide](./DOCKER_DEPLOYMENT.md)
Complete Docker and Docker Compose deployment including:
- Docker Compose configurations for all environments
- Service scaling and load balancing
- Data persistence and backup strategies
- Development vs production configurations
- Health monitoring and troubleshooting

#### ☸️ [Kubernetes Deployment Guide](./KUBERNETES_DEPLOYMENT.md)
Production-ready Kubernetes deployment covering:
- Cluster setup and preparation
- Secrets and configuration management
- Storage and persistence configuration
- Service mesh and ingress setup
- Auto-scaling and monitoring
- Security hardening and network policies

## Environment Configuration

### Template Files

The project includes comprehensive environment configuration templates:

- **`.env.example`** - Master template with all configuration options
- **`.env.development`** - Development environment settings
- **`.env.staging`** - Staging environment configuration  
- **`.env.production`** - Production environment template

### Configuration Validation

Use the included validation script to verify your environment configuration:

```bash
# Validate current .env file
python scripts/validate-env-config.py

# Validate specific environment file
python scripts/validate-env-config.py --env-file .env.production --verbose

# Strict validation mode
python scripts/validate-env-config.py --strict
```

## Quick Reference

### System Requirements

#### Minimum (Development)
- **CPU**: 4 cores
- **Memory**: 8GB RAM
- **Storage**: 50GB free space
- **OS**: Linux, macOS, Windows (WSL2)

#### Recommended (Production)
- **CPU**: 16+ cores
- **Memory**: 32GB+ RAM
- **Storage**: 500GB+ SSD
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+)

### Required Software

#### Development
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.30+
- Python 3.8+
- Node.js 16+

#### Production (Kubernetes)
- kubectl 1.20+
- Helm 3.0+ (optional)
- Kubernetes cluster 1.20+

### Service Architecture

The platform consists of 21 backend services plus React frontend:

**Core Services (4):**
- API Gateway (8000) - Central authentication and routing
- NLP Engine (8001) - Natural language processing
- Visualization (8002) - Chart and dashboard generation
- Alert Manager (8003) - Alerting and notifications

**Integration Services (6):**
- Slack Bot (8004) - Slack integration
- Teams Bot (8005) - Microsoft Teams integration
- Email Service (8006) - Email processing
- Webhook Service (8007) - External webhooks
- ITSM Service - ServiceNow/Jira integration
- BI Integration (8008) - Tableau/Power BI

**Export Services (6):**
- PDF Export (8009) - PDF generation
- PowerPoint Export (8011) - Presentation generation
- Word Export (8013) - Document generation
- HTML Report (8012) - HTML reports
- CSV Export (8014) - CSV data export
- JSON/XML Export (8015) - Structured data export

**Platform Services (5):**
- Report Scheduling (8015) - Automated reports
- Secure Sharing (8016) - Secure file sharing
- WebSocket Service - Real-time communication
- Cloud Services - Splunk Cloud integration
- Frontend (3000) - React user interface

### Essential Commands

#### Development Workflow
```bash
# Start all services
make up-dev

# Run tests
make test

# Check service health
make health

# View logs
make logs

# Clean up
make clean
```

#### Validation and Testing
```bash
# Validate environment configuration
python scripts/validate-env-config.py

# Validate Splunk connection
python scripts/validate-splunk-config.py

# Run production readiness validation
./scripts/run-validation.sh --env development

# Run comprehensive tests
python tests/integration/test_runner.py
```

#### Database Operations
```bash
# Run migrations
make db-migrate

# Create migration
make db-create-migration MESSAGE="description"

# Reset database (development only)
make db-reset
```

## Troubleshooting

### Common Setup Issues

#### 1. Environment Configuration
```bash
# Validate configuration
python scripts/validate-env-config.py --verbose

# Check for missing variables
grep -E "^[A-Z_]+=.*change.*this" .env
```

#### 2. Service Connectivity
```bash
# Test all health endpoints
make health

# Test individual services
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # NLP Engine
```

#### 3. Database Issues
```bash
# Check database connectivity
docker-compose exec postgres pg_isready -U splunk_mcp_user

# Run database migrations
docker-compose run --rm api-gateway python -m alembic upgrade head
```

#### 4. Splunk Connectivity
```bash
# Test Splunk REST API
curl -k -u username:password \
  "https://splunk-server:8089/services/server/info"

# Validate Splunk configuration
python scripts/validate-splunk-config.py
```

### Getting Help

#### Documentation Resources
- **API Documentation**: Available at `http://localhost:8000/docs` when running
- **Service Documentation**: Each service has detailed README in `services/*/README.md`
- **Architecture Documentation**: See `docs/architecture/`
- **User Documentation**: See `docs/user/`

#### Support Channels
- **Issues**: Create issues in the project repository
- **Documentation**: Refer to comprehensive guides in `docs/`
- **Community**: Check project discussions and wikis

## Next Steps

After completing the basic setup:

1. **Configure Monitoring**: Set up Prometheus, Grafana, and alerting
2. **Security Hardening**: Implement production security measures
3. **Performance Tuning**: Optimize for your specific workload
4. **User Training**: Train end users on the platform features
5. **Operational Procedures**: Establish backup, maintenance, and support procedures

## Contributing

When adding new setup documentation:

1. Follow the existing documentation structure
2. Include comprehensive examples and code snippets
3. Add validation scripts where appropriate
4. Update this README with links to new documentation
5. Test all procedures on clean environments

---

**Last Updated**: January 2025  
**Version**: 1.0.0