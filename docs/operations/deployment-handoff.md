# Deployment Handoff Documentation

## Overview

This document provides the operations team with comprehensive information for deploying and maintaining the **Splunk MCP Integration Platform** in production environments.

## System Architecture Summary

### Core Components
- **19 Backend Microservices** - All implemented in FastAPI with comprehensive testing
- **React Frontend** - TypeScript-based user interface with real-time communication
- **PostgreSQL Database** - Primary data storage with high availability configuration
- **Redis Cache** - Session management and caching layer
- **Kubernetes Infrastructure** - Container orchestration with auto-scaling capabilities

### Service Dependencies
```mermaid
graph TD
    A[Frontend] --> B[API Gateway]
    B --> C[NLP Engine]
    B --> D[Visualization Service]
    B --> E[Alert Manager]
    C --> F[PostgreSQL]
    C --> G[Redis]
    D --> F
    E --> F
    H[Slack Bot] --> B
    I[Teams Bot] --> B
    J[Email Service] --> B
```

## Production Deployment Checklist

### Pre-Deployment Requirements
- [ ] Kubernetes cluster provisioned (minimum 3 nodes, 8 CPU, 16GB RAM each)
- [ ] PostgreSQL instance configured (high availability recommended)
- [ ] Redis cluster configured (sentinel mode for HA)
- [ ] SSL certificates obtained (Let's Encrypt integration available)
- [ ] Container registry access configured (GitHub Container Registry)
- [ ] Environment secrets prepared (see Environment Configuration section)

### Infrastructure Components
- [ ] Kubernetes namespaces created (`splunk-mcp-prod`, `monitoring`)
- [ ] RBAC policies applied (see `infrastructure/kubernetes/rbac/`)
- [ ] Network policies configured (see `infrastructure/kubernetes/network-policies/`)
- [ ] Storage classes configured (see `infrastructure/kubernetes/storage/`)
- [ ] Ingress controller deployed (NGINX recommended)
- [ ] Certificate manager deployed (cert-manager)

### Application Deployment
- [ ] Database migrations applied (see Database Setup section)
- [ ] ConfigMaps deployed (see `infrastructure/kubernetes/configmaps/`)
- [ ] Secrets deployed (see `infrastructure/kubernetes/secrets/`)
- [ ] Services deployed (see `infrastructure/kubernetes/deployments/`)
- [ ] Ingress configured (see `infrastructure/kubernetes/ingress/`)
- [ ] Horizontal Pod Autoscaler configured (see `infrastructure/kubernetes/hpa/`)

### Monitoring & Observability
- [ ] Prometheus deployed and configured
- [ ] Grafana deployed with dashboards imported
- [ ] AlertManager configured with notification channels
- [ ] Log aggregation configured (ELK stack recommended)
- [ ] Health check endpoints validated

## Environment Configuration

### Required Environment Variables

#### API Gateway Service
```bash
# Core Configuration
DATABASE_URL=postgresql://user:password@postgres:5432/splunk_mcp
REDIS_URL=redis://redis:6379
JWT_SECRET_KEY=<secure-random-key>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# External Integrations
OPENAI_API_KEY=<openai-api-key>
ANTHROPIC_API_KEY=<anthropic-api-key>
SPLUNK_HOST=<splunk-enterprise-host>
SPLUNK_PORT=8089
SPLUNK_USERNAME=<service-account>
SPLUNK_PASSWORD=<service-password>

# Security Configuration
CORS_ORIGINS=["https://yourdomain.com"]
SECURITY_HEADERS_ENABLED=true
RATE_LIMITING_ENABLED=true
```

#### NLP Engine Service
```bash
DATABASE_URL=postgresql://user:password@postgres:5432/splunk_mcp
REDIS_URL=redis://redis:6379
OPENAI_API_KEY=<openai-api-key>
ANTHROPIC_API_KEY=<anthropic-api-key>
MODEL_CACHE_TTL=3600
MAX_CONTEXT_LENGTH=8000
```

#### Visualization Service
```bash
DATABASE_URL=postgresql://user:password@postgres:5432/splunk_mcp
REDIS_URL=redis://redis:6379
CHART_CACHE_TTL=1800
MAX_CHART_DATA_POINTS=10000
```

### Secrets Management
All sensitive configuration should be stored in Kubernetes secrets:

```bash
kubectl create secret generic splunk-mcp-secrets \
  --from-literal=database-url="postgresql://user:password@postgres:5432/splunk_mcp" \
  --from-literal=redis-url="redis://redis:6379" \
  --from-literal=jwt-secret-key="<secure-random-key>" \
  --from-literal=openai-api-key="<openai-api-key>" \
  --from-literal=anthropic-api-key="<anthropic-api-key>" \
  --from-literal=splunk-password="<service-password>"
```

## Database Setup

### Initial Database Creation
```sql
-- Create database and user
CREATE DATABASE splunk_mcp;
CREATE USER splunk_user WITH ENCRYPTED PASSWORD '<secure-password>';
GRANT ALL PRIVILEGES ON DATABASE splunk_mcp TO splunk_user;

-- Create schemas
\c splunk_mcp;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS chat;
CREATE SCHEMA IF NOT EXISTS spl;
CREATE SCHEMA IF NOT EXISTS viz;
CREATE SCHEMA IF NOT EXISTS alerts;
CREATE SCHEMA IF NOT EXISTS audit;
```

### Migration Procedure
```bash
# Run migrations for each service
kubectl exec deployment/api-gateway -- python manage_db.py upgrade
kubectl exec deployment/nlp-engine -- python manage_db.py upgrade
kubectl exec deployment/visualization -- python manage_db.py upgrade
kubectl exec deployment/alert-manager -- python manage_db.py upgrade
```

## Deployment Commands

### Automated Deployment Script
Use the comprehensive deployment script:
```bash
cd infrastructure/kubernetes
./deploy.sh production
```

### Manual Deployment Steps
```bash
# 1. Create namespaces
kubectl apply -f namespaces/

# 2. Apply RBAC
kubectl apply -f rbac/

# 3. Deploy storage
kubectl apply -f storage/

# 4. Deploy secrets (after configuration)
kubectl apply -f secrets/

# 5. Deploy ConfigMaps
kubectl apply -f configmaps/

# 6. Deploy services
kubectl apply -f deployments/
kubectl apply -f services/

# 7. Configure networking
kubectl apply -f network-policies/
kubectl apply -f ingress/

# 8. Enable autoscaling
kubectl apply -f hpa/
```

## Monitoring Configuration

### Prometheus Configuration
The monitoring stack is configured in `infrastructure/monitoring/`. Key components:

- **Prometheus**: Metrics collection from all services
- **Grafana**: Visualization dashboards for system monitoring
- **AlertManager**: Alert routing and notification management

### Key Metrics to Monitor
- **API Response Times**: 95th percentile should be <3 seconds
- **Database Connection Pool**: Should maintain healthy connection counts
- **Memory Usage**: Should stay below 80% of allocated resources
- **Error Rates**: Should remain below 1% for critical endpoints
- **WebSocket Connections**: Monitor active connection counts

### Alert Rules
Critical alerts are configured for:
- Service unavailability (>30 seconds downtime)
- High error rates (>5% error rate for 2 minutes)
- Resource exhaustion (>85% memory or CPU usage)
- Database connection issues
- Authentication failures

## Security Configuration

### Network Policies
Zero-trust network security is implemented with default deny-all policies. Services can only communicate through explicitly allowed routes.

### RBAC Configuration
Each service runs with minimal required permissions:
- Service accounts with specific roles
- Pod security contexts (non-root users)
- Read-only root filesystems where possible

### SSL/TLS Configuration
- All external traffic uses HTTPS with Let's Encrypt certificates
- Internal service communication uses TLS where configured
- Certificate auto-renewal is configured

## Backup & Recovery

### Automated Backup
Database backups are configured to run daily:
```bash
# PostgreSQL backup
kubectl create cronjob postgres-backup \
  --image=postgres:15 \
  --schedule="0 2 * * *" \
  -- /bin/bash -c "pg_dump -h postgres -U splunk_user splunk_mcp > /backup/splunk_mcp_$(date +%Y%m%d).sql"
```

### Recovery Procedures
1. **Database Recovery**: Restore from most recent backup
2. **Service Recovery**: Rolling restart of affected services
3. **Configuration Recovery**: Restore from GitOps repository

## Performance Tuning

### Resource Allocation
Recommended resource limits for production:

```yaml
# API Gateway
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"

# NLP Engine
resources:
  requests:
    memory: "1Gi"
    cpu: "1000m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Auto-Scaling Configuration
HPA is configured for all services based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Custom metrics (request rate, queue depth)

## Troubleshooting Guide

### Common Issues

#### Service Startup Failures
```bash
# Check pod status
kubectl get pods -n splunk-mcp-prod

# Check pod logs
kubectl logs deployment/api-gateway -n splunk-mcp-prod

# Check events
kubectl get events -n splunk-mcp-prod --sort-by='.lastTimestamp'
```

#### Database Connection Issues
```bash
# Test database connectivity
kubectl exec deployment/api-gateway -- python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')"

# Check database pod status
kubectl get pods -l app=postgres -n splunk-mcp-prod
```

#### Performance Issues
```bash
# Check resource usage
kubectl top pods -n splunk-mcp-prod

# Check HPA status
kubectl get hpa -n splunk-mcp-prod

# Check service metrics
curl http://<service>/metrics
```

### Log Analysis
All services use structured JSON logging with correlation IDs:
```bash
# Filter logs by correlation ID
kubectl logs deployment/api-gateway -n splunk-mcp-prod | jq '.correlation_id=="<id>"'

# Filter error logs
kubectl logs deployment/api-gateway -n splunk-mcp-prod | jq '.level=="ERROR"'
```

## Health Checks

### Service Health Endpoints
All services expose health check endpoints:
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### Monitoring Commands
```bash
# Check all service health
kubectl get pods -n splunk-mcp-prod

# Test health endpoints
curl https://api.yourdomain.com/health

# Check ingress status
kubectl get ingress -n splunk-mcp-prod
```

## Contact Information

### Development Team
- **Technical Lead**: [Team Lead Contact]
- **DevOps Engineer**: [DevOps Contact]
- **Security Lead**: [Security Contact]

### Documentation References
- **Technical Documentation**: `/docs/architecture/`
- **API Documentation**: `/docs/api/`
- **User Documentation**: `/docs/user/`
- **Troubleshooting**: `/docs/troubleshooting/`

### Support Channels
- **Emergency**: [Emergency Contact]
- **General Issues**: [Support Email]
- **Documentation**: [Documentation Repository]

## Appendix

### Service Port Mapping
- API Gateway: 8000
- NLP Engine: 8001
- Visualization: 8002
- Alert Manager: 8003
- Slack Bot: 8004
- Teams Bot: 8005
- Email Service: 8006
- Webhook Service: 8007
- BI Integration: 8008
- PDF Export: 8009
- PowerPoint Export: 8011
- HTML Report: 8012
- Word Export: 8013
- CSV Export: 8014
- JSON/XML Export: 8015
- Report Scheduling: 8015
- Secure Sharing: 8016
- Frontend: 3000

### External Dependencies
- OpenAI API (for GPT-4 integration)
- Anthropic API (for Claude integration)
- Splunk Enterprise API
- Email SMTP server
- Slack API (for bot integration)
- Microsoft Teams API (for bot integration)

---

*This handoff document provides comprehensive deployment and operational guidance for the production Splunk MCP Integration Platform. Refer to the detailed documentation in the `/docs/` directory for additional technical information.*