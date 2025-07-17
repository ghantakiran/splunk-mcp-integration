# Infrastructure - CLAUDE.md

## Inherits From
- [Main Project Guidelines](../CLAUDE.md)
- [Shared Standards](../CLAUDE.md#development-practices)

## Infrastructure Overview
The Infrastructure component provides containerization, orchestration, and deployment configurations for the Splunk MCP Integration project. It includes Docker configurations, Kubernetes manifests, and Terraform infrastructure as code.

## Architecture
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Kubernetes for production deployment
- **Infrastructure as Code**: Terraform for cloud resources
- **Monitoring**: Prometheus and Grafana for metrics
- **Security**: Vault for secrets management

## Development Guidelines

### Directory Structure
```
infrastructure/
├── docker/                  # Docker configurations
│   ├── postgres/            # PostgreSQL configuration
│   │   └── init.sql         # Database initialization
│   ├── redis/               # Redis configuration
│   │   └── redis.conf       # Redis settings
│   ├── nginx/               # Nginx configuration
│   └── monitoring/          # Monitoring stack
├── kubernetes/              # Kubernetes manifests
│   ├── namespaces/          # Namespace definitions
│   ├── services/            # Service definitions
│   ├── deployments/         # Application deployments
│   ├── configmaps/          # Configuration maps
│   ├── secrets/             # Secret definitions
│   └── ingress/             # Ingress configurations
├── terraform/               # Infrastructure as Code
│   ├── modules/             # Reusable Terraform modules
│   ├── environments/        # Environment-specific configs
│   │   ├── dev/             # Development environment
│   │   ├── staging/         # Staging environment
│   │   └── prod/            # Production environment
│   └── variables.tf         # Variable definitions
└── scripts/                 # Deployment scripts
```

### Key Components

#### Docker Configuration
- **Multi-stage Builds**: Optimized container images
- **Security**: Non-root users and minimal base images
- **Caching**: Efficient layer caching
- **Health Checks**: Container health monitoring

#### Kubernetes Deployment
- **Microservices**: Service mesh architecture
- **Scaling**: Horizontal Pod Autoscaling
- **Security**: RBAC and network policies
- **Monitoring**: Prometheus and Grafana integration

#### Infrastructure as Code
- **Terraform**: Cloud resource management
- **Modules**: Reusable infrastructure components
- **State Management**: Remote state storage
- **CI/CD**: Automated deployment pipelines

## Docker Configuration

### Service Images
```yaml
# docker-compose.yml structure
version: '3.8'
services:
  api-gateway:
    build:
      context: ../services/api-gateway
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/splunk_mcp
      - REDIS_URL=redis://redis:6379
  
  nlp-engine:
    build:
      context: ../services/nlp-engine
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
  
  visualization:
    build:
      context: ../services/visualization
      dockerfile: Dockerfile
    ports:
      - "8002:8002"
```

### Database Configuration
```sql
-- PostgreSQL initialization
CREATE DATABASE splunk_mcp;
CREATE USER splunk_user WITH ENCRYPTED PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE splunk_mcp TO splunk_user;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS chat;
CREATE SCHEMA IF NOT EXISTS spl;
CREATE SCHEMA IF NOT EXISTS viz;
CREATE SCHEMA IF NOT EXISTS alerts;
CREATE SCHEMA IF NOT EXISTS audit;
```

### Redis Configuration
```conf
# Redis configuration
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

## Kubernetes Deployment

### Namespace Configuration
```yaml
# namespaces/splunk-mcp.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: splunk-mcp
  labels:
    name: splunk-mcp
    environment: production
```

### Service Definitions
```yaml
# services/api-gateway.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: splunk-mcp
spec:
  selector:
    app: api-gateway
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
  type: ClusterIP
```

### Deployment Configuration
```yaml
# deployments/api-gateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: splunk-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: splunk-mcp/api-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Ingress Configuration
```yaml
# ingress/main.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: splunk-mcp-ingress
  namespace: splunk-mcp
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.splunk-mcp.com
    secretName: splunk-mcp-tls
  rules:
  - host: api.splunk-mcp.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 8000
```

## Terraform Configuration

### Provider Configuration
```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
  
  backend "s3" {
    bucket = "splunk-mcp-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}
```

### EKS Cluster Configuration
```hcl
# terraform/modules/eks/main.tf
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  node_groups = {
    main = {
      desired_capacity = 3
      max_capacity     = 10
      min_capacity     = 1
      
      instance_types = ["t3.medium"]
      
      k8s_labels = {
        Environment = var.environment
        Application = "splunk-mcp"
      }
    }
  }
}
```

### RDS Configuration
```hcl
# terraform/modules/rds/main.tf
resource "aws_db_instance" "postgres" {
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "postgres"
  engine_version       = "15.3"
  instance_class       = "db.t3.micro"
  db_name              = "splunk_mcp"
  username             = var.db_username
  password             = var.db_password
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  
  tags = {
    Environment = var.environment
    Application = "splunk-mcp"
  }
}
```

## Monitoring and Logging

### Prometheus Configuration
```yaml
# monitoring/prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    scrape_configs:
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

### Grafana Dashboards
```json
{
  "dashboard": {
    "title": "Splunk MCP Services",
    "panels": [
      {
        "title": "API Gateway Metrics",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      }
    ]
  }
}
```

## Security Configuration

### Network Policies
```yaml
# security/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: splunk-mcp-network-policy
  namespace: splunk-mcp
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
```

### RBAC Configuration
```yaml
# security/rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: splunk-mcp
  name: splunk-mcp-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
```

## CI/CD Pipeline

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Deploy to EKS
      run: |
        aws eks update-kubeconfig --name splunk-mcp-cluster
        kubectl apply -f kubernetes/
```

## Environment Configuration

### Development Environment
```bash
# Development environment variables
export ENVIRONMENT=development
export DATABASE_URL=postgresql://user:pass@localhost:5432/splunk_mcp_dev
export REDIS_URL=redis://localhost:6379
export LOG_LEVEL=DEBUG
```

### Production Environment
```bash
# Production environment variables
export ENVIRONMENT=production
export DATABASE_URL=${DATABASE_URL}
export REDIS_URL=${REDIS_URL}
export LOG_LEVEL=INFO
export MONITORING_ENABLED=true
```

## Deployment Scripts

### Build and Deploy Script
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-development}
VERSION=${2:-latest}

echo "Deploying to $ENVIRONMENT with version $VERSION"

# Build Docker images
docker build -t splunk-mcp/api-gateway:$VERSION services/api-gateway/
docker build -t splunk-mcp/nlp-engine:$VERSION services/nlp-engine/
docker build -t splunk-mcp/visualization:$VERSION services/visualization/

# Push to registry
docker push splunk-mcp/api-gateway:$VERSION
docker push splunk-mcp/nlp-engine:$VERSION
docker push splunk-mcp/visualization:$VERSION

# Deploy to Kubernetes
kubectl apply -f kubernetes/namespaces/
kubectl apply -f kubernetes/configmaps/
kubectl apply -f kubernetes/secrets/
kubectl apply -f kubernetes/deployments/
kubectl apply -f kubernetes/services/
kubectl apply -f kubernetes/ingress/

echo "Deployment completed successfully"
```

## Troubleshooting

### Common Issues
1. **Container Startup Failures**: Check resource limits and health checks
2. **Database Connection Issues**: Verify connection strings and network policies
3. **Service Discovery Problems**: Check DNS resolution and service definitions
4. **Load Balancer Issues**: Verify ingress configuration and SSL certificates

### Debugging Tools
- `kubectl logs` for container logs
- `kubectl describe` for resource details
- `kubectl exec` for container access
- Prometheus metrics for monitoring

## Best Practices

### Container Security
- Use non-root users in containers
- Scan images for vulnerabilities
- Minimize image size and dependencies
- Use multi-stage builds

### Kubernetes Security
- Implement RBAC policies
- Use network policies for isolation
- Secure secrets management
- Regular security updates

### Monitoring
- Implement comprehensive logging
- Set up alerting for critical metrics
- Monitor resource usage
- Track application performance

## Comprehensive Kubernetes Infrastructure

### Production-Ready Deployment Architecture

The Splunk MCP Integration project now includes a complete Kubernetes infrastructure with the following components:

#### Core Infrastructure Components

**1. Namespaces and Environment Separation**
- Production namespace: `splunk-mcp-prod`
- Development namespace: `splunk-mcp-dev`
- Monitoring namespaces: `splunk-mcp-monitoring-[env]`
- Logging namespaces: `splunk-mcp-logging-[env]`

**2. Application Deployments**
- API Gateway: 3 replicas (prod), 1 replica (dev)
- NLP Engine: 2 replicas (prod), 1 replica (dev)
- Visualization Service: 2 replicas (prod), 1 replica (dev)
- Alert Manager: 2 replicas (prod), 1 replica (dev)
- Frontend: 3 replicas (prod), 1 replica (dev)

**3. Data Layer**
- PostgreSQL: StatefulSet with persistent volumes
- Redis: StatefulSet with persistent volumes
- Storage classes: fast-ssd (prod), standard (dev)

**4. Service Mesh and Networking**
- NGINX Ingress Controller with SSL/TLS termination
- Network policies for service isolation
- Service discovery and load balancing
- Rate limiting and DDoS protection

**5. Security Framework**
- RBAC with service accounts and roles
- Pod security contexts (non-root users)
- Network segmentation policies
- Secrets management with encryption

**6. Autoscaling and Performance**
- Horizontal Pod Autoscaler (HPA) for all services
- CPU and memory-based scaling
- Custom metrics support
- Resource requests and limits

#### Deployment Instructions

**Prerequisites:**
```bash
# Install required tools
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx
```

**Step-by-Step Deployment:**

1. **Create Namespaces**
   ```bash
   kubectl apply -f infrastructure/kubernetes/namespaces/
   ```

2. **Deploy Storage Infrastructure**
   ```bash
   kubectl apply -f infrastructure/kubernetes/storage/storage-classes.yaml
   kubectl apply -f infrastructure/kubernetes/storage/postgres-storage.yaml
   kubectl apply -f infrastructure/kubernetes/storage/redis-storage.yaml
   ```

3. **Configure Secrets (Update values first!)**
   ```bash
   # Edit secret values in infrastructure/kubernetes/secrets/
   kubectl apply -f infrastructure/kubernetes/secrets/
   ```

4. **Deploy Configuration**
   ```bash
   kubectl apply -f infrastructure/kubernetes/configmaps/
   ```

5. **Set up RBAC**
   ```bash
   kubectl apply -f infrastructure/kubernetes/rbac/
   ```

6. **Deploy Applications**
   ```bash
   kubectl apply -f infrastructure/kubernetes/deployments/
   kubectl apply -f infrastructure/kubernetes/services/
   ```

7. **Configure Networking**
   ```bash
   kubectl apply -f infrastructure/kubernetes/network-policies/
   kubectl apply -f infrastructure/kubernetes/ingress/
   ```

8. **Enable Autoscaling**
   ```bash
   kubectl apply -f infrastructure/kubernetes/hpa/
   ```

#### Environment-Specific Configurations

**Production Environment:**
- High availability with multiple replicas
- Strict security policies and network isolation
- SSL/TLS termination with Let's Encrypt
- Production-grade monitoring and alerting
- Automated backup and disaster recovery

**Development Environment:**
- Single replica deployments for cost efficiency
- Relaxed security policies for development
- Debug logging and extended timeouts
- Development-specific feature flags

#### Security Features

**Network Security:**
- Default deny-all network policies
- Service-specific ingress/egress rules
- Ingress controller with rate limiting
- DDoS protection and WAF integration

**Application Security:**
- Non-root container execution
- Read-only root filesystems
- Security context constraints
- Pod security policies

**Data Security:**
- Encryption at rest and in transit
- Secret management with Kubernetes secrets
- JWT token authentication
- Role-based access control

#### Monitoring and Observability

**Metrics Collection:**
- Prometheus metrics endpoints on all services
- Grafana dashboards for visualization
- Custom application metrics
- Infrastructure monitoring

**Logging:**
- Centralized log aggregation
- Structured logging with correlation IDs
- Log retention and rotation policies
- Search and analysis capabilities

**Health Monitoring:**
- Liveness, readiness, and startup probes
- Service health endpoints
- Application performance monitoring
- Error tracking and alerting

#### Scaling and Performance

**Horizontal Pod Autoscaling:**
- CPU and memory-based scaling
- Custom metrics support (request rate, queue length)
- Service-specific scaling policies
- Predictive scaling capabilities

**Resource Management:**
- Quality of Service (QoS) classes
- Resource requests and limits
- Node affinity and anti-affinity
- Pod disruption budgets

#### Disaster Recovery

**Backup Strategy:**
- Automated database backups
- Persistent volume snapshots
- Configuration backup
- Point-in-time recovery

**High Availability:**
- Multi-zone deployments
- Database replication
- Load balancer configuration
- Failover mechanisms

#### Troubleshooting Guide

**Common Issues and Solutions:**

1. **Pod Startup Failures:**
   ```bash
   kubectl describe pod <pod-name> -n splunk-mcp-prod
   kubectl logs <pod-name> -n splunk-mcp-prod
   ```

2. **Network Connectivity Issues:**
   ```bash
   kubectl get networkpolicies -n splunk-mcp-prod
   kubectl get endpoints -n splunk-mcp-prod
   ```

3. **Storage Issues:**
   ```bash
   kubectl get pvc -n splunk-mcp-prod
   kubectl describe pvc <pvc-name> -n splunk-mcp-prod
   ```

4. **SSL/TLS Certificate Issues:**
   ```bash
   kubectl get certificates -n splunk-mcp-prod
   kubectl describe certificate splunk-mcp-tls -n splunk-mcp-prod
   ```

**Monitoring Commands:**
```bash
# Check application health
kubectl get pods -n splunk-mcp-prod
kubectl top pods -n splunk-mcp-prod

# Verify services
kubectl get svc -n splunk-mcp-prod
kubectl get ingress -n splunk-mcp-prod

# Check autoscaling
kubectl get hpa -n splunk-mcp-prod
kubectl describe hpa api-gateway-hpa -n splunk-mcp-prod

# Monitor network policies
kubectl get networkpolicies -n splunk-mcp-prod
```

#### Performance Optimization

**Resource Tuning:**
- Monitor resource usage patterns
- Adjust CPU/memory limits based on metrics
- Optimize JVM settings for Java applications
- Database connection pooling optimization

**Caching Strategy:**
- Redis configuration optimization
- Application-level caching
- CDN integration for static assets
- Query result caching

#### Maintenance and Operations

**Regular Tasks:**
- Certificate renewal monitoring
- Security policy updates
- Resource usage monitoring
- Log rotation and cleanup
- Database maintenance

**Upgrade Process:**
1. Test in development environment
2. Backup critical data
3. Rolling update deployment
4. Monitor application health
5. Rollback if necessary

#### Cost Optimization

**Resource Efficiency:**
- Right-sizing pod resources
- Vertical pod autoscaling
- Node autoscaling
- Spot instance utilization

**Development Environment:**
- Scheduled pod shutdown
- Shared development resources
- Resource quotas and limits
- Cost monitoring and alerts

## Advanced Features

### Service Mesh Integration (Istio)

The infrastructure is prepared for Istio service mesh integration with the following benefits:

**Traffic Management:**
- Advanced load balancing
- Circuit breaker patterns
- Retry and timeout policies
- Canary deployments

**Security:**
- Mutual TLS (mTLS) between services
- Fine-grained authorization policies
- Traffic encryption
- Certificate management

**Observability:**
- Distributed tracing
- Service mesh metrics
- Traffic visualization
- Performance monitoring

### Backup and Disaster Recovery

**Automated Backup:**
- Scheduled database backups
- Persistent volume snapshots
- Configuration backup
- Cross-region replication

**Disaster Recovery:**
- Multi-region deployment
- Automated failover
- Data synchronization
- Recovery time objectives (RTO)

### Compliance and Governance

**Data Protection:**
- GDPR compliance features
- Data retention policies
- Privacy controls
- Audit logging

**Security Compliance:**
- SOC 2 Type II compliance
- ISO 27001 standards
- NIST framework alignment
- Regular security assessments

## Next Steps

### Immediate Priorities
1. Complete monitoring infrastructure (Prometheus/Grafana)
2. Implement logging infrastructure (ELK stack)
3. Set up backup and disaster recovery
4. Deploy service mesh (Istio)

### Long-term Roadmap
1. Advanced security with admission controllers
2. Multi-cluster deployment
3. GitOps integration with ArgoCD
4. Chaos engineering implementation
5. Performance optimization automation

### Integration Tasks
1. CI/CD pipeline integration
2. Infrastructure as Code (Terraform)
3. Monitoring alerts and runbooks
4. Security scanning and compliance
5. Cost optimization strategies