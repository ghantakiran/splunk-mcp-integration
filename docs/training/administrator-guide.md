# Administrator Training Program

## Course Overview

This comprehensive training program equips system administrators with the knowledge and skills needed to deploy, configure, manage, and maintain the Splunk MCP Integration Platform in enterprise environments.

### Training Objectives
By the end of this program, administrators will be able to:
- Deploy the platform using Kubernetes in production environments
- Configure authentication, authorization, and security policies
- Monitor system performance and troubleshoot issues
- Manage user access and permissions effectively
- Perform maintenance, updates, and scaling operations
- Implement backup and disaster recovery procedures

### Target Audience
- System Administrators
- DevOps Engineers
- Site Reliability Engineers
- Infrastructure Managers
- Security Administrators

### Prerequisites
- Experience with Kubernetes and Docker containerization
- Understanding of microservices architecture
- Basic knowledge of PostgreSQL and Redis
- Familiarity with monitoring tools (Prometheus, Grafana)
- Experience with enterprise authentication systems

---

## Module 1: Platform Architecture & Components (2 hours)

### Learning Objectives
- Understand the complete system architecture
- Identify all microservices and their relationships
- Comprehend data flow and communication patterns
- Learn about security and compliance features

### 1.1 System Architecture Overview

#### Microservices Architecture
The platform consists of **19 backend microservices** organized into logical groups:

**Core Services:**
- **API Gateway** (Port 8000) - Main entry point, authentication, rate limiting
- **NLP Engine** (Port 8001) - Natural language processing and SPL translation
- **Visualization** (Port 8002) - Chart generation and dashboard management
- **Alert Manager** (Port 8003) - Alerting system with multi-channel notifications

**Integration Services:**
- **Slack Bot** (Port 8004) - Conversational AI interface for Slack
- **Teams Bot** (Port 8005) - Enterprise Teams bot integration
- **Email Service** (Port 8006) - Email integration and report delivery
- **Webhook Service** (Port 8007) - Enterprise webhook management
- **ITSM Service** (Port 8010) - ServiceNow and Jira integration
- **BI Integration** (Port 8008) - Tableau and Power BI connectivity

**Export Services:**
- **PDF Export** (Port 8009) - Advanced PDF generation
- **PowerPoint Export** (Port 8011) - Enterprise presentation generation
- **HTML Report** (Port 8012) - Interactive HTML reports
- **Word Export** (Port 8013) - Professional document generation
- **CSV Export** (Port 8014) - Advanced CSV formatting
- **JSON/XML Export** (Port 8015) - Structured data export

**Platform Services:**
- **Secure Sharing** (Port 8016) - Enterprise sharing with permissions
- **Report Scheduling** (Port 8010) - Automated report delivery
- **WebSocket Service** - Real-time communication

**Infrastructure:**
- **Frontend** (Port 3000) - React-based user interface
- **PostgreSQL** (Port 5432) - Primary database for metadata
- **Redis** (Port 6379) - Caching and session management

#### Data Flow Architecture
```
User Request → API Gateway → Core Services → Integration Layer → Splunk API
                   ↓              ↓              ↓
            Authentication → Processing → Data Storage
                   ↓              ↓              ↓
            Authorization → Visualization → Response
```

#### Security Architecture
- **Authentication**: JWT tokens with refresh mechanism
- **Authorization**: Role-based access control (RBAC) with Splunk integration
- **Audit Logging**: Comprehensive activity tracking with correlation IDs
- **Data Protection**: Encryption at rest and in transit
- **Network Security**: Service mesh with network policies

### 1.2 Component Dependencies

#### Critical Dependencies
- **Splunk Enterprise** - Primary data source and search engine
- **PostgreSQL** - Metadata storage and user management
- **Redis** - Caching, session management, rate limiting
- **AI Services** - OpenAI GPT-4 or Claude-3 for NLP processing

#### External Integrations
- **Authentication Providers** - LDAP, Active Directory, SAML, OAuth
- **Notification Channels** - SMTP, Slack, Teams, PagerDuty
- **Enterprise Tools** - ServiceNow, Jira, Tableau, Power BI

### 1.3 Hands-On Lab: Architecture Exploration
**Duration: 30 minutes**

**Exercise 1: Service Discovery**
```bash
# Check all running services
kubectl get pods -n splunk-mcp-prod

# Examine service configurations
kubectl describe service api-gateway -n splunk-mcp-prod

# Review resource usage
kubectl top pods -n splunk-mcp-prod
```

**Exercise 2: Health Checks**
```bash
# Test service health endpoints
curl http://api-gateway:8000/health
curl http://nlp-engine:8001/health
curl http://visualization:8002/health

# Check database connectivity
kubectl exec -it postgres-0 -n splunk-mcp-prod -- psql -U postgres -c "\\l"
```

---

## Module 2: Installation & Deployment (4 hours)

### Learning Objectives
- Deploy the platform in Kubernetes environments
- Configure environment-specific settings
- Validate successful deployment
- Troubleshoot common deployment issues

### 2.1 Prerequisites & Environment Preparation

#### Infrastructure Requirements
**Minimum Production Environment:**
- **Kubernetes Cluster**: 1.28+ with 3+ worker nodes
- **Compute Resources**: 16 vCPU, 32GB RAM, 100GB storage per node
- **Network**: Load balancer, SSL termination, firewall rules
- **Monitoring**: Prometheus, Grafana, alerting configured

**Required Access:**
- Kubernetes cluster admin access
- Container registry with platform images
- Splunk Enterprise admin credentials
- External service API keys (OpenAI, Slack, etc.)

#### Pre-Deployment Checklist
```bash
# Verify Kubernetes cluster
kubectl cluster-info
kubectl get nodes

# Check resource availability
kubectl describe nodes

# Verify storage classes
kubectl get storageclass

# Test network connectivity
kubectl run test-pod --image=busybox --rm -it -- nslookup kubernetes.default
```

### 2.2 Kubernetes Deployment

#### Namespace Setup
```bash
# Create production namespace
kubectl create namespace splunk-mcp-prod

# Apply network policies
kubectl apply -f infrastructure/kubernetes/network-policies/

# Set up RBAC
kubectl apply -f infrastructure/kubernetes/rbac/
```

#### Database Deployment
```bash
# Deploy PostgreSQL
kubectl apply -f infrastructure/kubernetes/storage/postgres-statefulset.yaml

# Deploy Redis
kubectl apply -f infrastructure/kubernetes/storage/redis-statefulset.yaml

# Verify database pods
kubectl get pods -n splunk-mcp-prod -l app=postgresql
kubectl get pods -n splunk-mcp-prod -l app=redis
```

#### Core Services Deployment
```bash
# Deploy core services
kubectl apply -f infrastructure/kubernetes/deployments/

# Check deployment status
kubectl rollout status deployment/api-gateway -n splunk-mcp-prod
kubectl rollout status deployment/nlp-engine -n splunk-mcp-prod

# Verify services are running
kubectl get pods -n splunk-mcp-prod
```

#### Configuration Management
```bash
# Create configuration secrets
kubectl create secret generic splunk-config \
  --from-literal=host=splunk.company.com \
  --from-literal=port=8089 \
  --from-literal=username=service-account \
  --from-literal=password=secure-password \
  -n splunk-mcp-prod

# Create AI service secrets
kubectl create secret generic ai-config \
  --from-literal=openai-key=sk-... \
  --from-literal=anthropic-key=sk-ant-... \
  -n splunk-mcp-prod

# Apply configmaps
kubectl apply -f infrastructure/kubernetes/configmaps/
```

### 2.3 Environment Configuration

#### Environment Variables
Create environment-specific configuration:

```yaml
# production-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: splunk-mcp-prod
data:
  # Database Configuration
  POSTGRES_HOST: "postgres-service"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "splunk_mcp"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  
  # Splunk Configuration
  SPLUNK_HOST: "splunk.company.com"
  SPLUNK_PORT: "8089"
  SPLUNK_SCHEME: "https"
  
  # Application Configuration
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  ENABLE_METRICS: "true"
  
  # Security Configuration
  JWT_SECRET_KEY: "secure-production-key"
  SESSION_TIMEOUT: "3600"
  RATE_LIMIT_REQUESTS: "100"
  RATE_LIMIT_WINDOW: "60"
```

#### Service-Specific Configuration
```bash
# Configure API Gateway
kubectl create configmap api-gateway-config \
  --from-file=config.yaml=configs/api-gateway-prod.yaml \
  -n splunk-mcp-prod

# Configure NLP Engine
kubectl create configmap nlp-engine-config \
  --from-file=config.yaml=configs/nlp-engine-prod.yaml \
  -n splunk-mcp-prod
```

### 2.4 SSL/TLS and Ingress Setup

#### Certificate Management
```bash
# Install cert-manager
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f infrastructure/kubernetes/ingress/cluster-issuer.yaml

# Create SSL certificates
kubectl apply -f infrastructure/kubernetes/ingress/certificates.yaml
```

#### Ingress Configuration
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: splunk-mcp-ingress
  namespace: splunk-mcp-prod
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - splunk-mcp.company.com
    secretName: splunk-mcp-tls
  rules:
  - host: splunk-mcp.company.com
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

### 2.5 Hands-On Lab: Complete Deployment
**Duration: 2 hours**

**Exercise 1: Deploy from Scratch**
Students will deploy the complete platform in a test environment:

1. Set up namespace and RBAC
2. Deploy databases and storage
3. Configure secrets and configmaps
4. Deploy core services
5. Set up ingress and SSL
6. Validate deployment

**Exercise 2: Deployment Troubleshooting**
Common issues and resolution:
- Pod startup failures
- Service connectivity issues
- Configuration problems
- Resource constraints

---

## Module 3: Authentication & Authorization (3 hours)

### Learning Objectives
- Configure enterprise authentication systems
- Set up role-based access control
- Manage user permissions and groups
- Implement security best practices

### 3.1 Authentication Configuration

#### JWT Token Management
The platform uses JWT tokens for authentication with the following configuration:

```yaml
# JWT Configuration
JWT_SECRET_KEY: "your-secure-secret-key"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: 60
JWT_REFRESH_TOKEN_EXPIRE_DAYS: 7
JWT_ALGORITHM: "HS256"
```

#### LDAP/Active Directory Integration
```yaml
# LDAP Configuration
LDAP_SERVER: "ldap://ad.company.com:389"
LDAP_BIND_DN: "CN=service-account,OU=Service Accounts,DC=company,DC=com"
LDAP_BIND_PASSWORD: "secure-password"
LDAP_SEARCH_BASE: "OU=Users,DC=company,DC=com"
LDAP_USER_FILTER: "(sAMAccountName={username})"
LDAP_GROUP_FILTER: "(member={user_dn})"
```

#### SAML 2.0 Integration
```xml
<!-- SAML Configuration -->
<saml:Issuer>https://splunk-mcp.company.com</saml:Issuer>
<saml:NameIDPolicy Format="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"/>
<saml:AttributeStatement>
  <saml:Attribute Name="email"/>
  <saml:Attribute Name="groups"/>
  <saml:Attribute Name="displayName"/>
</saml:AttributeStatement>
```

#### Multi-Factor Authentication (MFA)
```python
# MFA Configuration
MFA_ENABLED: true
MFA_METHODS: ["totp", "sms", "email"]
MFA_GRACE_PERIOD: 86400  # 24 hours
MFA_BACKUP_CODES: 10
```

### 3.2 Role-Based Access Control (RBAC)

#### Default Roles
The platform includes pre-defined roles with specific permissions:

**Administrator Role:**
- Full system access and configuration
- User management and role assignment
- Service monitoring and maintenance
- Security audit and compliance

**Power User Role:**
- Create and manage dashboards
- Set up alerts and notifications
- Export reports in all formats
- Access to advanced analytics features

**Analyst Role:**
- Create queries and visualizations
- View shared dashboards
- Export basic reports
- Limited alert management

**Viewer Role:**
- View shared dashboards and reports
- Basic query capabilities
- Read-only access to most features

#### Custom Role Creation
```yaml
# Custom Role Definition
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: security-analyst
  namespace: splunk-mcp-prod
rules:
- apiGroups: [""]
  resources: ["alerts", "dashboards"]
  verbs: ["get", "list", "create"]
- apiGroups: [""]
  resources: ["reports"]
  verbs: ["get", "list"]
```

#### Permission Management
```bash
# Assign role to user
kubectl create rolebinding security-analyst-binding \
  --role=security-analyst \
  --user=john.doe@company.com \
  -n splunk-mcp-prod

# Create group-based permissions
kubectl create rolebinding security-team-binding \
  --role=security-analyst \
  --group=security-team \
  -n splunk-mcp-prod
```

### 3.3 Splunk Integration Security

#### Service Account Configuration
```bash
# Create Splunk service account
curl -k -u admin:password \
  -d name=splunk-mcp-service \
  -d password=secure-service-password \
  -d roles=user,power \
  https://splunk.company.com:8089/servicesNS/admin/search/authentication/users

# Assign appropriate capabilities
curl -k -u admin:password \
  -d capabilities=search,list_search_head_clustering \
  https://splunk.company.com:8089/servicesNS/admin/search/authentication/users/splunk-mcp-service
```

#### Index-Level Permissions
```bash
# Configure index access
curl -k -u admin:password \
  -d indexes=main,security,application \
  -d srchIndexesAllowed=main,security,application \
  https://splunk.company.com:8089/servicesNS/admin/search/authorization/roles/splunk-mcp-role
```

### 3.4 Security Hardening

#### Network Security
```yaml
# Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-default
  namespace: splunk-mcp-prod
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
```

#### Pod Security Standards
```yaml
# Pod Security Policy
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

#### Secrets Management
```bash
# Rotate secrets regularly
kubectl create secret generic new-jwt-secret \
  --from-literal=key=$(openssl rand -base64 32) \
  -n splunk-mcp-prod

# Use Kubernetes secrets for sensitive data
kubectl create secret generic database-credentials \
  --from-literal=username=postgres \
  --from-literal=password=$(openssl rand -base64 20) \
  -n splunk-mcp-prod
```

### 3.5 Hands-On Lab: Authentication Setup
**Duration: 1.5 hours**

**Exercise 1: Configure LDAP Authentication**
1. Set up LDAP connection configuration
2. Test user authentication
3. Map LDAP groups to platform roles
4. Validate access controls

**Exercise 2: Implement RBAC**
1. Create custom roles for specific teams
2. Assign permissions based on job functions
3. Test role-based access scenarios
4. Audit user permissions

---

## Module 4: Monitoring & Maintenance (3 hours)

### Learning Objectives
- Set up comprehensive monitoring and alerting
- Perform routine maintenance tasks
- Troubleshoot common issues
- Optimize system performance

### 4.1 Monitoring Infrastructure

#### Prometheus Configuration
```yaml
# Prometheus Config
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
- job_name: 'splunk-mcp-services'
  kubernetes_sd_configs:
  - role: endpoints
  relabel_configs:
  - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
    action: keep
    regex: true
```

#### Grafana Dashboards
Pre-configured dashboards for monitoring:

**System Overview Dashboard:**
- Service health status
- Request rates and response times
- Error rates and success metrics
- Resource utilization (CPU, memory, disk)

**Application Performance Dashboard:**
- Query execution times
- NLP processing performance
- Database connection pool status
- Cache hit/miss ratios

**Security Dashboard:**
- Authentication failures
- Rate limiting events
- Suspicious activity patterns
- Audit log analysis

#### Key Metrics to Monitor
```yaml
# Service-Level Metrics
- http_requests_total
- http_request_duration_seconds
- http_requests_errors_total
- active_connections_current

# Application Metrics
- nlp_processing_duration_seconds
- spl_query_execution_time
- dashboard_load_time
- export_generation_time

# Infrastructure Metrics
- container_cpu_usage_seconds_total
- container_memory_usage_bytes
- postgres_connections_active
- redis_connected_clients
```

### 4.2 Alerting Configuration

#### Critical Alerts
```yaml
# High Error Rate Alert
- alert: HighErrorRate
  expr: rate(http_requests_errors_total[5m]) > 0.1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value }} errors per second"

# Service Down Alert
- alert: ServiceDown
  expr: up{job="splunk-mcp-services"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Service {{ $labels.instance }} is down"
```

#### Performance Alerts
```yaml
# Slow Response Time Alert
- alert: SlowResponseTime
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Slow response time detected"

# High Memory Usage Alert
- alert: HighMemoryUsage
  expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8
  for: 5m
  labels:
    severity: warning
```

### 4.3 Log Management

#### Centralized Logging
```yaml
# Fluentd Configuration
<source>
  @type kubernetes_metadata_filter
  @id filter_kube_metadata
</source>

<filter kubernetes.**>
  @type parser
  key_name log
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </parse>
</filter>

<match kubernetes.**>
  @type elasticsearch
  host elasticsearch.logging.svc.cluster.local
  port 9200
  index_name kubernetes-logs
</match>
```

#### Log Analysis Queries
```bash
# Error analysis
kubectl logs -n splunk-mcp-prod deployment/api-gateway --since=1h | grep ERROR

# Performance analysis
kubectl logs -n splunk-mcp-prod deployment/nlp-engine --since=1h | grep "processing_time"

# Security analysis
kubectl logs -n splunk-mcp-prod deployment/api-gateway --since=1h | grep "auth_failure"
```

### 4.4 Routine Maintenance Tasks

#### Daily Tasks
```bash
# Check service health
kubectl get pods -n splunk-mcp-prod
kubectl top pods -n splunk-mcp-prod

# Monitor resource usage
kubectl describe nodes | grep -A 5 "Allocated resources"

# Check for failed jobs
kubectl get jobs -n splunk-mcp-prod --field-selector status.successful=0
```

#### Weekly Tasks
```bash
# Database maintenance
kubectl exec -it postgres-0 -n splunk-mcp-prod -- \
  psql -U postgres -d splunk_mcp -c "VACUUM ANALYZE;"

# Clean up old logs
kubectl exec -it elasticsearch-0 -n logging -- \
  curl -X DELETE "localhost:9200/kubernetes-logs-$(date -d '30 days ago' +%Y.%m.%d)"

# Update container images
kubectl set image deployment/api-gateway api-gateway=splunk-mcp/api-gateway:latest -n splunk-mcp-prod
```

#### Monthly Tasks
```bash
# Security audit
kubectl auth can-i --list --as=system:serviceaccount:splunk-mcp-prod:default

# Performance review
kubectl top nodes
kubectl describe hpa -n splunk-mcp-prod

# Backup verification
kubectl exec -it postgres-0 -n splunk-mcp-prod -- \
  pg_dump -U postgres splunk_mcp > backup-$(date +%Y%m%d).sql
```

### 4.5 Troubleshooting Guide

#### Common Issues and Solutions

**Pod Startup Failures:**
```bash
# Check pod status
kubectl describe pod <pod-name> -n splunk-mcp-prod

# View pod logs
kubectl logs <pod-name> -n splunk-mcp-prod

# Check resource constraints
kubectl describe nodes
```

**Database Connection Issues:**
```bash
# Test database connectivity
kubectl exec -it postgres-0 -n splunk-mcp-prod -- psql -U postgres -l

# Check connection pool status
kubectl logs deployment/api-gateway -n splunk-mcp-prod | grep "connection"

# Monitor active connections
kubectl exec -it postgres-0 -n splunk-mcp-prod -- \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

**Performance Issues:**
```bash
# Check resource utilization
kubectl top pods -n splunk-mcp-prod

# Analyze slow queries
kubectl logs deployment/nlp-engine -n splunk-mcp-prod | grep "slow_query"

# Review cache performance
kubectl exec -it redis-0 -n splunk-mcp-prod -- redis-cli info stats
```

**Authentication Problems:**
```bash
# Check authentication service logs
kubectl logs deployment/api-gateway -n splunk-mcp-prod | grep "auth"

# Validate JWT configuration
kubectl get secret jwt-secret -n splunk-mcp-prod -o yaml

# Test LDAP connectivity
kubectl exec -it api-gateway-pod -n splunk-mcp-prod -- \
  ldapsearch -x -H ldap://ad.company.com -D "service-account" -W
```

### 4.6 Hands-On Lab: Monitoring Setup
**Duration: 2 hours**

**Exercise 1: Configure Monitoring**
1. Deploy Prometheus and Grafana
2. Import pre-built dashboards
3. Set up alerting rules
4. Test alert notifications

**Exercise 2: Troubleshooting Scenarios**
1. Simulate service failures
2. Investigate performance issues
3. Analyze log patterns
4. Implement fixes and verify resolution

---

## Module 5: Backup & Disaster Recovery (2 hours)

### Learning Objectives
- Implement comprehensive backup strategies
- Create disaster recovery procedures
- Test backup and restore processes
- Plan for business continuity

### 5.1 Backup Strategy

#### Database Backup
```bash
# Automated PostgreSQL backup
kubectl create cronjob postgres-backup \
  --image=postgres:13 \
  --schedule="0 2 * * *" \
  --restart=OnFailure \
  -- /bin/sh -c "pg_dump -h postgres-service -U postgres splunk_mcp > /backup/backup-$(date +%Y%m%d).sql"

# Redis backup
kubectl create cronjob redis-backup \
  --image=redis:7 \
  --schedule="0 3 * * *" \
  --restart=OnFailure \
  -- /bin/sh -c "redis-cli -h redis-service --rdb /backup/dump-$(date +%Y%m%d).rdb"
```

#### Configuration Backup
```bash
# Backup Kubernetes manifests
kubectl get all -n splunk-mcp-prod -o yaml > k8s-backup-$(date +%Y%m%d).yaml

# Backup secrets and configmaps
kubectl get secrets,configmaps -n splunk-mcp-prod -o yaml > config-backup-$(date +%Y%m%d).yaml

# Backup persistent volumes
kubectl get pv,pvc -n splunk-mcp-prod -o yaml > storage-backup-$(date +%Y%m%d).yaml
```

#### Application State Backup
```bash
# Export user configurations
kubectl exec -it api-gateway-pod -n splunk-mcp-prod -- \
  python manage.py export_user_data > user-backup-$(date +%Y%m%d).json

# Export dashboard configurations
kubectl exec -it visualization-pod -n splunk-mcp-prod -- \
  python manage.py export_dashboards > dashboard-backup-$(date +%Y%m%d).json
```

### 5.2 Disaster Recovery Planning

#### Recovery Time Objectives (RTO)
- **Critical Services**: 15 minutes
- **Core Platform**: 30 minutes
- **Full Functionality**: 60 minutes
- **Historical Data**: 4 hours

#### Recovery Point Objectives (RPO)
- **Configuration Data**: 0 minutes (real-time replication)
- **User Data**: 15 minutes (continuous backup)
- **Application Logs**: 5 minutes (stream processing)
- **Analytics Data**: 60 minutes (batch processing)

#### Disaster Recovery Procedures
```bash
# Emergency failover script
#!/bin/bash
set -e

echo "Starting disaster recovery process..."

# 1. Assess damage and determine recovery scope
kubectl get pods -n splunk-mcp-prod
kubectl get nodes

# 2. Restore database from backup
kubectl apply -f disaster-recovery/postgres-restore.yaml

# 3. Restore Redis cache
kubectl apply -f disaster-recovery/redis-restore.yaml

# 4. Deploy services in priority order
kubectl apply -f disaster-recovery/core-services.yaml
kubectl apply -f disaster-recovery/integration-services.yaml

# 5. Validate service health
for service in api-gateway nlp-engine visualization alert-manager; do
  kubectl wait --for=condition=ready pod -l app=$service -n splunk-mcp-prod --timeout=300s
done

# 6. Run health checks
kubectl exec -it api-gateway-pod -n splunk-mcp-prod -- python manage.py health_check

echo "Disaster recovery completed successfully"
```

### 5.3 High Availability Configuration

#### Multi-Zone Deployment
```yaml
# High Availability Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway-ha
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - api-gateway
            topologyKey: kubernetes.io/hostname
```

#### Database High Availability
```yaml
# PostgreSQL HA with streaming replication
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres-ha
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: postgres
        image: postgres:13
        env:
        - name: POSTGRES_REPLICATION_MODE
          value: master
        - name: POSTGRES_REPLICATION_USER
          value: replicator
```

### 5.4 Hands-On Lab: Backup & Recovery
**Duration: 1.5 hours**

**Exercise 1: Implement Backup**
1. Set up automated database backups
2. Configure application state exports
3. Test backup integrity
4. Create backup monitoring

**Exercise 2: Disaster Recovery Simulation**
1. Simulate system failure
2. Execute recovery procedures
3. Validate system functionality
4. Document lessons learned

---

## Module 6: Performance Optimization (2 hours)

### Learning Objectives
- Identify performance bottlenecks
- Optimize resource allocation
- Implement caching strategies
- Scale services effectively

### 6.1 Performance Monitoring

#### Key Performance Indicators
- **Response Time**: <100ms for simple queries, <3s for complex analytics
- **Throughput**: 1000+ requests per minute per service
- **Availability**: 99.9% uptime
- **Resource Utilization**: <80% CPU, <85% memory

#### Performance Metrics Collection
```yaml
# Custom metrics for performance monitoring
custom_metrics:
  - name: query_processing_time
    help: Time taken to process natural language queries
    type: histogram
    buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]

  - name: database_query_duration
    help: Database query execution time
    type: histogram
    buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1.0]

  - name: cache_hit_ratio
    help: Cache hit ratio percentage
    type: gauge
```

### 6.2 Resource Optimization

#### Horizontal Pod Autoscaling
```yaml
# HPA Configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Vertical Pod Autoscaling
```yaml
# VPA Configuration
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: nlp-engine-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nlp-engine
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: nlp-engine
      maxAllowed:
        cpu: 2
        memory: 4Gi
      minAllowed:
        cpu: 100m
        memory: 128Mi
```

### 6.3 Caching Optimization

#### Redis Cache Configuration
```yaml
# Redis cluster for improved caching
redis_cluster:
  enabled: true
  nodes: 6
  replicas: 1
  maxmemory: 2gb
  maxmemory_policy: allkeys-lru
  
cache_strategies:
  query_results:
    ttl: 300  # 5 minutes
    max_size: 1000
  
  user_sessions:
    ttl: 3600  # 1 hour
    max_size: 10000
    
  dashboard_data:
    ttl: 900  # 15 minutes
    max_size: 500
```

#### Application-Level Caching
```python
# Intelligent caching strategy
@cache(ttl=300, key_prefix="query_result")
def process_natural_language_query(query: str, user_context: dict):
    # Generate cache key based on query and user permissions
    cache_key = f"{hash(query)}_{hash(json.dumps(user_context, sort_keys=True))}"
    return execute_query(query, user_context)

@cache(ttl=900, key_prefix="dashboard")
def generate_dashboard(dashboard_id: str, time_range: str):
    return build_dashboard_data(dashboard_id, time_range)
```

### 6.4 Database Optimization

#### Connection Pool Optimization
```yaml
# Database connection pool settings
database_config:
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
  pool_pre_ping: true
  
  # Query optimization
  statement_timeout: 30000
  idle_in_transaction_session_timeout: 60000
```

#### Query Optimization
```sql
-- Index optimization for common queries
CREATE INDEX CONCURRENTLY idx_queries_user_timestamp 
ON queries(user_id, created_at) WHERE status = 'completed';

CREATE INDEX CONCURRENTLY idx_dashboards_shared_public 
ON dashboards(is_shared, is_public, updated_at);

-- Analyze and vacuum regularly
ANALYZE;
VACUUM (ANALYZE, VERBOSE);
```

### 6.5 Hands-On Lab: Performance Tuning
**Duration: 1.5 hours**

**Exercise 1: Performance Baseline**
1. Measure current performance metrics
2. Identify bottlenecks using profiling tools
3. Analyze resource utilization patterns
4. Document performance baseline

**Exercise 2: Optimization Implementation**
1. Configure autoscaling policies
2. Optimize cache strategies
3. Tune database performance
4. Validate improvements with load testing

---

## Assessment & Certification (1 hour)

### Practical Assessment
Students complete a comprehensive practical assessment covering:

#### Scenario-Based Questions (30 minutes)
1. **Deployment Issue**: Troubleshoot a failed service deployment
2. **Performance Problem**: Identify and resolve a performance bottleneck
3. **Security Incident**: Respond to a security alert and implement fixes
4. **Disaster Recovery**: Execute recovery procedures for a simulated failure

#### Hands-On Tasks (30 minutes)
1. Deploy a new service to the platform
2. Configure monitoring and alerting for the service
3. Implement a backup strategy
4. Optimize service performance

### Certification Requirements
To receive certification, administrators must:
- Complete all training modules with 80% score
- Pass the practical assessment
- Demonstrate proficiency in real-world scenarios
- Commit to ongoing education and best practices

### Continuing Education
- Monthly platform updates and new feature training
- Advanced troubleshooting workshops
- Security best practices seminars
- Performance optimization masterclasses

---

## Training Resources

### Documentation
- [Platform Architecture Guide](../architecture/README.md)
- [Security Procedures](../security/README.md)
- [Troubleshooting Guide](../user/faq.md)
- [API Documentation](../api/README.md)

### Tools and Scripts
- Deployment automation scripts
- Monitoring configuration templates
- Backup and recovery procedures
- Performance testing tools

### Support Channels
- **Technical Support**: support@splunk-mcp.com
- **Training Questions**: training@splunk-mcp.com
- **Emergency Support**: +1-800-SPLUNK-MCP
- **Community Forum**: https://community.splunk-mcp.com

---

*This training program is designed to be delivered over 2-3 days in an intensive format or spread across 2-3 weeks for part-time learning. Regular updates ensure content remains current with platform evolution.*