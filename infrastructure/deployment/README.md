# Deployment Automation Framework
# ================================

This directory contains a comprehensive deployment automation framework for the Splunk MCP Integration Platform, designed to streamline production infrastructure deployment, configuration, monitoring, and maintenance.

## Overview

The deployment automation framework provides enterprise-grade tools for:

- **Automated Infrastructure Deployment** - Complete platform deployment with validation
- **Environment Configuration Management** - Automated environment-specific configuration 
- **Health Monitoring & Validation** - Comprehensive health checks and monitoring
- **Automated Rollback Capabilities** - Safe rollback with backup and validation
- **Dynamic Service Scaling** - Intelligent scaling with preset configurations

## Framework Components

### 🚀 Core Deployment Scripts

#### `deploy-platform.sh` - Master Deployment Orchestrator
Comprehensive automated deployment for production environments.

**Features:**
- Complete infrastructure deployment (namespaces, RBAC, storage, networking)
- Application deployment with dependency management
- Monitoring stack deployment (Prometheus, Grafana, AlertManager)
- Pre-deployment validation and post-deployment verification
- Component-based deployment (infrastructure, applications, monitoring)
- Dry-run capability for safe deployment testing

**Usage Examples:**
```bash
# Full production deployment
./deploy-platform.sh --environment production

# Deploy only applications (skip infrastructure)
./deploy-platform.sh --components applications

# Dry run for staging
./deploy-platform.sh --dry-run --environment staging
```

#### `configure-environment.sh` - Environment Configuration Manager
Automates environment-specific configuration setup with secrets management.

**Features:**
- Automatic configuration generation for different environments
- Kubernetes ConfigMap and Secret management
- Environment validation and security checks
- Kustomize overlay generation for environment-specific deployments
- Template-based configuration with security best practices

**Usage Examples:**
```bash
# Configure production environment
./configure-environment.sh --environment production --config-file prod.env

# Generate configuration templates
./configure-environment.sh --environment staging

# Dry run configuration
./configure-environment.sh --dry-run --environment production
```

### 🔍 Monitoring & Validation Scripts

#### `health-check.sh` - Comprehensive Health Monitoring
Advanced health monitoring and validation for deployed platform.

**Features:**
- Kubernetes cluster and pod health validation
- Service endpoint availability checking
- Database and Redis connectivity testing
- Application health endpoint verification
- External service integration validation
- Multiple output formats (text, JSON, Prometheus metrics)
- Continuous monitoring mode

**Usage Examples:**
```bash
# Basic health check
./health-check.sh

# Continuous monitoring
./health-check.sh --continuous --interval 60

# JSON output for automation
./health-check.sh --format json --check-external
```

### 🔄 Rollback & Recovery Scripts

#### `rollback.sh` - Automated Rollback System
Safe and automated rollback capabilities with backup and validation.

**Features:**
- Gradual service rollback with dependency awareness
- Automatic backup creation before rollback
- Rollback verification and health checks
- Specific revision targeting
- Force rollback capabilities for emergency scenarios
- Comprehensive rollback validation

**Usage Examples:**
```bash
# Rollback to previous version
./rollback.sh

# Rollback to specific revision
./rollback.sh --revision 5

# Emergency rollback without confirmation
./rollback.sh --force --revision 3
```

### ⚖️ Scaling & Performance Scripts

#### `scale-services.sh` - Dynamic Service Scaling
Intelligent service scaling with preset configurations and validation.

**Features:**
- Individual service scaling with validation
- Bulk scaling operations for all services
- Predefined scaling presets (minimal, development, staging, production, high-load)
- Current replica status monitoring
- Resource-aware scaling with confirmation prompts
- Wait-for-ready validation

**Usage Examples:**
```bash
# Scale specific service
./scale-services.sh api-gateway 5

# Apply production scaling preset
./scale-services.sh --preset production

# Scale all services
./scale-services.sh --all 3
```

## Deployment Architecture

### Component Deployment Order

The framework follows a structured deployment order to ensure proper dependency resolution:

**1. Infrastructure Components:**
- Kubernetes namespaces and RBAC policies
- Storage classes and persistent volumes
- Network policies and security configurations
- ConfigMaps and Secrets

**2. Application Components:**
- Backend microservices (19 services)
- Frontend application
- Service mesh and ingress configuration
- Horizontal Pod Autoscaler (HPA) setup

**3. Monitoring Components:**
- Prometheus metrics collection
- Grafana dashboards and visualization
- AlertManager notification routing
- Custom monitoring rules and alerts

### Service Dependencies

The framework manages service dependencies intelligently:

```
Frontend → API Gateway → Core Services → Infrastructure
   ↓           ↓              ↓              ↓
Ingress → Load Balancer → Services → ConfigMaps/Secrets
   ↓           ↓              ↓              ↓
SSL/TLS → Network Policies → Pods → Storage/Database
```

## Environment Configuration

### Supported Environments

The framework supports multiple deployment environments:

- **Development** - Single-node development with minimal resources
- **Staging** - Multi-node staging environment with moderate scaling
- **Production** - High-availability production with auto-scaling
- **High-Load** - Maximum performance configuration for peak loads

### Configuration Management

Environment-specific configurations are managed through:

**ConfigMaps:**
- Application settings and feature flags
- Environment-specific parameters
- Non-sensitive configuration data

**Secrets:**
- Database connection strings and credentials
- API keys for external services (OpenAI, Anthropic)
- JWT secrets and encryption keys
- Integration credentials (Slack, Teams, SMTP)

### Resource Allocation

**Production Resource Recommendations:**
```yaml
# API Gateway
resources:
  requests: { memory: "512Mi", cpu: "500m" }
  limits: { memory: "1Gi", cpu: "1000m" }

# NLP Engine
resources:
  requests: { memory: "1Gi", cpu: "1000m" }
  limits: { memory: "2Gi", cpu: "2000m" }

# Visualization Service
resources:
  requests: { memory: "512Mi", cpu: "500m" }
  limits: { memory: "1Gi", cpu: "1000m" }
```

## Security Features

### Zero-Trust Security Model

The framework implements comprehensive security measures:

**Network Security:**
- Default deny-all network policies
- Service-to-service communication restrictions
- TLS encryption for all external traffic
- Secure internal service communication

**Access Control:**
- Role-Based Access Control (RBAC) for all services
- Service accounts with minimal required permissions
- Pod security contexts with non-root users
- Read-only root filesystems where applicable

**Secrets Management:**
- Kubernetes native secret storage
- Automatic secret validation and rotation
- Environment-specific secret isolation
- Security scanning and validation

### Compliance Features

- **Audit Logging** - Comprehensive audit trails for all operations
- **Data Encryption** - Encryption at rest and in transit
- **Access Monitoring** - Real-time access pattern monitoring
- **Vulnerability Scanning** - Automated security vulnerability detection

## Monitoring & Alerting

### Health Check Categories

**Infrastructure Health:**
- Kubernetes cluster connectivity and node status
- Pod health, readiness, and restart monitoring
- Service endpoint availability and load balancing
- Storage and network connectivity validation

**Application Health:**
- Service-specific health endpoint monitoring
- Database and Redis connectivity testing
- External API integration validation
- Performance metric collection and analysis

**Business Health:**
- User session and activity monitoring
- Query processing performance tracking
- Export and report generation metrics
- Integration service availability monitoring

### Alert Management

**Critical Alerts (Immediate Response):**
- Service unavailability (>30 seconds)
- High error rates (>5% for 2 minutes)
- Database connectivity failures
- Authentication system failures

**Warning Alerts (Review Required):**
- Elevated response times (>1 second)
- Resource usage above 80%
- Queue backup conditions
- SSL certificate expiration warnings

**Info Alerts (Awareness):**
- Deployment completion notifications
- Scaling operation confirmations
- Backup completion status
- Configuration change notifications

## Performance Optimization

### Auto-Scaling Configuration

**Horizontal Pod Autoscaler (HPA):**
- CPU-based scaling (target: 70% utilization)
- Memory-based scaling (target: 80% utilization)
- Custom metrics scaling (request queue depth)
- Minimum and maximum replica constraints

**Vertical Pod Autoscaler (VPA):**
- Automatic resource request optimization
- Resource limit recommendations
- Historical usage pattern analysis
- Cost-aware resource allocation

### Caching Strategy

**Multi-Level Caching:**
- Application-level caching with Redis
- Database query result caching
- Static asset caching with CDN
- API response caching for frequently accessed data

## Disaster Recovery

### Backup Strategy

**Automated Backup System:**
- Daily PostgreSQL database backups
- Configuration and secrets backup
- Application state preservation
- Cross-region backup replication

**Recovery Procedures:**
- Point-in-time database recovery
- Configuration rollback capabilities
- Service-level recovery procedures
- Full platform disaster recovery

### Business Continuity

**High Availability:**
- Multi-zone deployment distribution
- Database clustering with failover
- Load balancer health checks
- Automatic failover mechanisms

**Data Protection:**
- Real-time database replication
- Incremental backup strategies
- Data integrity validation
- Recovery testing procedures

## Usage Guidelines

### Pre-Deployment Checklist

Before running deployment scripts:

1. **Environment Preparation:**
   - [ ] Kubernetes cluster provisioned and accessible
   - [ ] Required RBAC permissions configured
   - [ ] Storage classes available
   - [ ] Network connectivity verified

2. **Configuration Preparation:**
   - [ ] Environment-specific configuration files created
   - [ ] Secrets and credentials prepared
   - [ ] SSL certificates obtained
   - [ ] External service integrations configured

3. **Validation Preparation:**
   - [ ] Health check endpoints accessible
   - [ ] Monitoring infrastructure ready
   - [ ] Backup systems configured
   - [ ] Alert notification channels tested

### Deployment Process

**Recommended Deployment Flow:**

1. **Environment Configuration:**
   ```bash
   ./configure-environment.sh --environment production --config-file prod.env
   ```

2. **Infrastructure Deployment:**
   ```bash
   ./deploy-platform.sh --components infrastructure --environment production
   ```

3. **Application Deployment:**
   ```bash
   ./deploy-platform.sh --components applications --environment production
   ```

4. **Monitoring Setup:**
   ```bash
   ./deploy-platform.sh --components monitoring --environment production
   ```

5. **Health Validation:**
   ```bash
   ./health-check.sh --check-external --verbose
   ```

6. **Performance Scaling:**
   ```bash
   ./scale-services.sh --preset production
   ```

### Post-Deployment Operations

**Regular Maintenance:**
- Daily health check monitoring
- Weekly configuration validation
- Monthly scaling optimization
- Quarterly disaster recovery testing

**Performance Monitoring:**
- Continuous health monitoring
- Resource utilization tracking
- Performance metric analysis
- Capacity planning assessments

## Troubleshooting

### Common Issues

**Deployment Failures:**
```bash
# Check cluster connectivity
kubectl cluster-info

# Verify namespace and RBAC
kubectl auth can-i create pods --namespace splunk-mcp-prod

# Check resource constraints
kubectl describe nodes
```

**Service Health Issues:**
```bash
# Check pod status
kubectl get pods -n splunk-mcp-prod

# Check service endpoints
kubectl get endpoints -n splunk-mcp-prod

# Check service logs
kubectl logs deployment/api-gateway -n splunk-mcp-prod
```

**Configuration Problems:**
```bash
# Verify ConfigMaps
kubectl get configmap splunk-mcp-config -n splunk-mcp-prod -o yaml

# Check Secrets
kubectl get secret splunk-mcp-secrets -n splunk-mcp-prod

# Validate environment variables
kubectl exec deployment/api-gateway -n splunk-mcp-prod -- env | grep -E "(DATABASE|REDIS|API_KEY)"
```

### Emergency Procedures

**Emergency Rollback:**
```bash
# Immediate rollback without confirmation
./rollback.sh --force

# Rollback to specific known-good revision
./rollback.sh --force --revision 5
```

**Emergency Scaling:**
```bash
# Scale down all services for resource conservation
./scale-services.sh --all 1

# Scale up critical services only
./scale-services.sh api-gateway 10
./scale-services.sh nlp-engine 5
```

**Service Recovery:**
```bash
# Restart problematic services
kubectl rollout restart deployment/api-gateway -n splunk-mcp-prod

# Force pod recreation
kubectl delete pods -l app=api-gateway -n splunk-mcp-prod
```

## Integration with CI/CD

### GitHub Actions Integration

The deployment scripts integrate seamlessly with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Deploy to Production
  run: |
    ./infrastructure/deployment/configure-environment.sh --environment production
    ./infrastructure/deployment/deploy-platform.sh --environment production
    ./infrastructure/deployment/health-check.sh --check-external
```

### GitOps Integration

Support for GitOps workflows:
- Kustomize overlay generation
- Environment-specific configuration management
- Automated drift detection and reconciliation
- Policy-as-code integration

## Support and Documentation

### Additional Resources

- **Architecture Documentation**: `/docs/planning/architecture.md`
- **Service Documentation**: `/docs/project/services.md`
- **Administrator Guides**: `/docs/admin/`
- **Troubleshooting Guide**: `/docs/admin/troubleshooting-guide.md`

### Contact Information

- **Development Team**: [Team Contact Information]
- **DevOps Support**: [DevOps Contact Information]
- **Emergency Contact**: [Emergency Contact Information]

---

*This deployment automation framework provides comprehensive tools for enterprise-grade deployment, monitoring, and maintenance of the Splunk MCP Integration Platform. For detailed information about specific scripts or procedures, refer to the individual script help documentation using the `--help` flag.*

**Framework Version**: 2.0.0
**Last Updated**: December 2024
**Compatibility**: Kubernetes 1.24+, Helm 3.0+