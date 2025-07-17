# Splunk MCP Integration - Kubernetes Infrastructure

## Overview
This directory contains production-ready Kubernetes manifests for deploying the Splunk MCP Integration project. The infrastructure supports both development and production environments with comprehensive security, monitoring, and scalability features.

## Directory Structure
```
kubernetes/
├── namespaces/                 # Namespace configurations
│   ├── development.yaml        # Development environment namespaces
│   └── production.yaml         # Production environment namespaces
├── deployments/                # Application deployments
│   ├── api-gateway.yaml        # API Gateway deployment
│   ├── nlp-engine.yaml         # NLP Engine deployment
│   ├── visualization.yaml      # Visualization service deployment
│   ├── alert-manager.yaml      # Alert Manager deployment
│   └── frontend.yaml           # Frontend application deployment
├── services/                   # Service definitions
│   ├── api-gateway.yaml        # API Gateway services
│   ├── nlp-engine.yaml         # NLP Engine services
│   ├── visualization.yaml      # Visualization services
│   ├── alert-manager.yaml      # Alert Manager services
│   ├── frontend.yaml           # Frontend services
│   ├── postgres-service.yaml   # PostgreSQL services
│   └── redis-service.yaml      # Redis services
├── configmaps/                 # Configuration maps
│   ├── api-gateway.yaml        # API Gateway configuration
│   ├── nlp-engine.yaml         # NLP Engine configuration
│   ├── visualization.yaml      # Visualization configuration
│   ├── alert-manager.yaml      # Alert Manager configuration
│   └── frontend.yaml           # Frontend configuration
├── secrets/                    # Secret definitions (templates)
│   ├── database-secret.yaml    # Database credentials
│   ├── redis-secret.yaml       # Redis credentials
│   ├── api-secrets.yaml        # API keys and JWT secrets
│   └── notification-secrets.yaml # Notification service secrets
├── storage/                    # Persistent storage
│   ├── postgres-storage.yaml   # PostgreSQL storage and StatefulSet
│   ├── redis-storage.yaml      # Redis storage and StatefulSet
│   └── storage-classes.yaml    # Storage class definitions
├── hpa/                        # Horizontal Pod Autoscaler
│   ├── api-gateway-hpa.yaml    # API Gateway HPA
│   ├── nlp-engine-hpa.yaml     # NLP Engine HPA
│   ├── visualization-hpa.yaml  # Visualization HPA
│   ├── alert-manager-hpa.yaml  # Alert Manager HPA
│   └── frontend-hpa.yaml       # Frontend HPA
├── ingress/                    # Ingress configurations
│   ├── main-ingress.yaml       # Main application ingress
│   ├── cert-manager.yaml       # SSL certificate management
│   └── nginx-ingress.yaml      # NGINX ingress controller
├── rbac/                       # Role-based access control
│   ├── service-accounts.yaml   # Service account definitions
│   ├── roles.yaml              # Role definitions
│   ├── cluster-roles.yaml      # Cluster role definitions
│   ├── role-bindings.yaml      # Role bindings
│   └── cluster-role-bindings.yaml # Cluster role bindings
├── network-policies/           # Network security policies
│   ├── default-deny.yaml       # Default deny-all policy
│   ├── api-gateway-policy.yaml # API Gateway network policy
│   ├── nlp-engine-policy.yaml  # NLP Engine network policy
│   ├── visualization-policy.yaml # Visualization network policy
│   ├── database-policy.yaml    # Database network policies
│   ├── frontend-policy.yaml    # Frontend network policy
│   └── monitoring-policy.yaml  # Monitoring network policies
├── monitoring/                 # Monitoring stack (Prometheus, Grafana)
├── logging/                    # Logging infrastructure (ELK stack)
├── backup/                     # Backup and disaster recovery
├── service-mesh/               # Istio service mesh configuration
├── environments/               # Environment-specific configurations
│   ├── development/            # Development environment overrides
│   └── production/             # Production environment overrides
└── README.md                   # This file
```

## Quick Start

### Prerequisites
- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.x installed
- cert-manager installed
- NGINX Ingress Controller
- Persistent Volume provisioner (EBS, GCE, etc.)

### Deployment Steps

#### 1. Create Namespaces
```bash
kubectl apply -f namespaces/
```

#### 2. Deploy Storage Classes
```bash
kubectl apply -f storage/storage-classes.yaml
```

#### 3. Create Secrets (Update values first!)
```bash
# Update secret values in secrets/ directory
kubectl apply -f secrets/
```

#### 4. Create ConfigMaps
```bash
kubectl apply -f configmaps/
```

#### 5. Deploy Storage (PostgreSQL and Redis)
```bash
kubectl apply -f storage/
```

#### 6. Deploy RBAC
```bash
kubectl apply -f rbac/
```

#### 7. Deploy Applications
```bash
kubectl apply -f deployments/
```

#### 8. Create Services
```bash
kubectl apply -f services/
```

#### 9. Deploy Network Policies
```bash
kubectl apply -f network-policies/
```

#### 10. Deploy Ingress
```bash
kubectl apply -f ingress/
```

#### 11. Deploy HPA
```bash
kubectl apply -f hpa/
```

## Environment Configuration

### Development Environment
- Single replica deployments
- Relaxed security policies
- Debug logging enabled
- No SSL/TLS requirements
- Namespace: `splunk-mcp-dev`

### Production Environment
- Multi-replica deployments
- Strict security policies
- Production logging levels
- SSL/TLS mandatory
- Namespace: `splunk-mcp-prod`

## Security Features

### Network Security
- Default deny-all network policies
- Service-specific ingress/egress rules
- Namespace isolation
- Ingress controller with rate limiting

### RBAC
- Service-specific service accounts
- Least privilege principle
- Role-based access control
- Cluster-wide monitoring permissions

### Secrets Management
- Encrypted secrets at rest
- Service-specific secret access
- Base64 encoded sensitive data
- Kubernetes native secret management

## Monitoring and Observability

### Metrics
- Prometheus metrics collection
- Grafana dashboards
- Service-specific metrics endpoints
- Application performance monitoring

### Logging
- Centralized log aggregation
- Structured logging
- Log retention policies
- Search and analysis capabilities

### Health Checks
- Liveness probes
- Readiness probes
- Startup probes
- Service health endpoints

## Scaling and Performance

### Horizontal Pod Autoscaling
- CPU and memory-based scaling
- Custom metrics support
- Service-specific scaling policies
- Production-ready scaling configurations

### Resource Management
- Resource requests and limits
- Quality of Service (QoS) classes
- Node affinity and anti-affinity
- Pod disruption budgets

## Disaster Recovery

### Backup Strategy
- Automated database backups
- Persistent volume snapshots
- Configuration backup
- Point-in-time recovery

### High Availability
- Multi-zone deployments
- Database replication
- Load balancer configuration
- Failover mechanisms

## Troubleshooting

### Common Issues
1. **Pod Startup Failures**
   - Check resource limits
   - Verify secret availability
   - Review security contexts

2. **Network Connectivity**
   - Verify network policies
   - Check service discovery
   - Validate ingress configuration

3. **Storage Issues**
   - Check persistent volume claims
   - Verify storage class provisioning
   - Review volume permissions

### Debugging Commands
```bash
# Check pod status
kubectl get pods -n splunk-mcp-prod

# View pod logs
kubectl logs -f <pod-name> -n splunk-mcp-prod

# Describe pod for events
kubectl describe pod <pod-name> -n splunk-mcp-prod

# Check service endpoints
kubectl get endpoints -n splunk-mcp-prod

# Verify network policies
kubectl get networkpolicies -n splunk-mcp-prod

# Check ingress status
kubectl get ingress -n splunk-mcp-prod
```

## Maintenance

### Regular Tasks
- Certificate renewal monitoring
- Security policy updates
- Resource usage monitoring
- Log rotation and cleanup

### Upgrade Process
1. Test in development environment
2. Backup critical data
3. Rolling update deployment
4. Monitor application health
5. Rollback if necessary

## Performance Optimization

### Resource Tuning
- Monitor resource usage
- Adjust CPU/memory limits
- Optimize JVM settings
- Database connection pooling

### Caching Strategy
- Redis configuration optimization
- Application-level caching
- CDN integration
- Static asset optimization

## Security Hardening

### Container Security
- Non-root user execution
- Read-only root filesystem
- Security context configuration
- Image vulnerability scanning

### Network Security
- mTLS communication
- Network segmentation
- Firewall rules
- DDoS protection

## Compliance

### Data Protection
- Encryption at rest
- Encryption in transit
- Data retention policies
- Privacy controls

### Audit Logging
- Security event logging
- Access control auditing
- Compliance reporting
- Log integrity verification

## Support and Documentation

### Resources
- Kubernetes documentation
- Application-specific guides
- Troubleshooting runbooks
- Performance tuning guides

### Contacts
- Development team: dev@splunk-mcp.com
- Operations team: ops@splunk-mcp.com
- Security team: security@splunk-mcp.com
- Support team: support@splunk-mcp.com

---

For detailed deployment instructions and advanced configurations, please refer to the main infrastructure documentation at `/infrastructure/CLAUDE.md`.