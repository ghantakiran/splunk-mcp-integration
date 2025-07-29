# Installation & Deployment Guide

This comprehensive guide provides step-by-step instructions for installing and deploying the Splunk MCP Integration Platform in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Service Configuration](#service-configuration)
5. [SSL/TLS Setup](#ssltls-setup)
6. [Monitoring Configuration](#monitoring-configuration)
7. [Post-Installation Validation](#post-installation-validation)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

#### Minimum Production Environment
- **Kubernetes Cluster**: Version 1.28 or higher
- **Worker Nodes**: Minimum 3 nodes
- **Compute Resources per Node**:
  - vCPU: 8 cores
  - Memory: 16 GB RAM
  - Storage: 100 GB SSD
- **Network**: Load balancer support, ingress controller
- **Operating System**: Linux (Ubuntu 20.04+ or RHEL 8+)

#### Recommended Production Environment
- **Kubernetes Cluster**: Version 1.29+
- **Worker Nodes**: 5+ nodes for high availability
- **Compute Resources per Node**:
  - vCPU: 16 cores
  - Memory: 32 GB RAM
  - Storage: 200 GB NVMe SSD
- **Network**: Multiple availability zones, redundant networking
- **Operating System**: Latest LTS versions with security updates

### Required Software

#### Container Runtime
```bash
# Docker (if using Docker runtime)
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io

# Or containerd (recommended)
sudo apt-get update
sudo apt-get install containerd.io
```

#### Kubernetes Tools
```bash
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Helm (for package management)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### External Dependencies

#### Required Services
- **Splunk Enterprise**: Version 8.0+ or Splunk Cloud
- **PostgreSQL**: Version 13+ (can be deployed within cluster)
- **Redis**: Version 6+ (can be deployed within cluster)
- **SMTP Server**: For email notifications
- **DNS**: Proper DNS resolution for external access

#### API Keys and Credentials
- **OpenAI API Key**: For GPT-4 integration
- **Anthropic API Key**: For Claude integration (optional)
- **Splunk Service Account**: With appropriate permissions
- **SSL Certificates**: For HTTPS termination
- **Container Registry Access**: To pull platform images

### Access Requirements

#### Administrator Access
```bash
# Verify Kubernetes cluster access
kubectl cluster-info
kubectl get nodes

# Check cluster permissions
kubectl auth can-i "*" "*" --all-namespaces
```

#### Network Access
- **Kubernetes API Server**: Port 6443
- **Splunk API**: Port 8089 (default)
- **External APIs**: OpenAI, Anthropic (HTTPS/443)
- **SMTP Server**: Port 587 or 25
- **Container Registry**: HTTPS access

---

## Infrastructure Setup

### Kubernetes Cluster Preparation

#### Namespace Creation
```bash
# Create production namespace
kubectl create namespace splunk-mcp-prod

# Create monitoring namespace
kubectl create namespace monitoring

# Create logging namespace
kubectl create namespace logging

# Label namespaces for policy enforcement
kubectl label namespace splunk-mcp-prod environment=production
kubectl label namespace monitoring purpose=monitoring
kubectl label namespace logging purpose=logging
```

#### Storage Classes
```yaml
# storage-class.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ssd-retain
  annotations:
    storageclass.kubernetes.io/is-default-class: "false"
provisioner: kubernetes.io/aws-ebs  # Adjust for your cloud provider
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

```bash
# Apply storage configuration
kubectl apply -f infrastructure/kubernetes/storage/storage-class.yaml
```

#### Network Policies
```yaml
# network-policy-default-deny.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: splunk-mcp-prod
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-gateway
  namespace: splunk-mcp-prod
spec:
  podSelector:
    matchLabels:
      app: api-gateway
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: nlp-engine
    ports:
    - protocol: TCP
      port: 8001
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
```

```bash
# Apply network policies
kubectl apply -f infrastructure/kubernetes/network-policies/
```

### Database Setup

#### PostgreSQL Deployment
```yaml
# postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql
  namespace: splunk-mcp-prod
spec:
  serviceName: postgresql
  replicas: 1
  selector:
    matchLabels:
      app: postgresql
  template:
    metadata:
      labels:
        app: postgresql
    spec:
      securityContext:
        fsGroup: 999
      containers:
      - name: postgresql
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: splunk_mcp
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgresql-storage
          mountPath: /var/lib/postgresql/data
        - name: postgresql-config
          mountPath: /etc/postgresql/postgresql.conf
          subPath: postgresql.conf
        readinessProbe:
          exec:
            command:
            - /bin/sh
            - -c
            - pg_isready -U postgres
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          exec:
            command:
            - /bin/sh
            - -c
            - pg_isready -U postgres
          initialDelaySeconds: 30
          periodSeconds: 30
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      volumes:
      - name: postgresql-config
        configMap:
          name: postgresql-config
  volumeClaimTemplates:
  - metadata:
      name: postgresql-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: ssd-retain
      resources:
        requests:
          storage: 50Gi
```

#### Redis Deployment
```yaml
# redis-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: splunk-mcp-prod
spec:
  serviceName: redis
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7
        command:
        - redis-server
        - /etc/redis/redis.conf
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        - name: redis-config
          mountPath: /etc/redis/redis.conf
          subPath: redis.conf
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 30
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
  volumeClaimTemplates:
  - metadata:
      name: redis-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: ssd-retain
      resources:
        requests:
          storage: 10Gi
```

```bash
# Create database secrets
kubectl create secret generic postgres-secret \
  --from-literal=password=$(openssl rand -base64 32) \
  -n splunk-mcp-prod

# Deploy databases
kubectl apply -f infrastructure/kubernetes/storage/postgres-statefulset.yaml
kubectl apply -f infrastructure/kubernetes/storage/redis-statefulset.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgresql -n splunk-mcp-prod --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n splunk-mcp-prod --timeout=300s
```

---

## Kubernetes Deployment

### Secret Management

#### Application Secrets
```bash
# Create core application secrets
kubectl create secret generic app-secrets \
  --from-literal=jwt-secret-key=$(openssl rand -base64 64) \
  --from-literal=database-url="postgresql://postgres:$(kubectl get secret postgres-secret -n splunk-mcp-prod -o jsonpath='{.data.password}' | base64 -d)@postgresql:5432/splunk_mcp" \
  --from-literal=redis-url="redis://redis:6379" \
  -n splunk-mcp-prod

# Create Splunk integration secrets
kubectl create secret generic splunk-secrets \
  --from-literal=host="your-splunk-host.com" \
  --from-literal=port="8089" \
  --from-literal=username="service-account" \
  --from-literal=password="your-splunk-password" \
  -n splunk-mcp-prod

# Create AI service secrets
kubectl create secret generic ai-secrets \
  --from-literal=openai-api-key="your-openai-key" \
  --from-literal=anthropic-api-key="your-anthropic-key" \
  -n splunk-mcp-prod

# Create email service secrets
kubectl create secret generic email-secrets \
  --from-literal=smtp-host="smtp.your-domain.com" \
  --from-literal=smtp-port="587" \
  --from-literal=smtp-username="your-smtp-user" \
  --from-literal=smtp-password="your-smtp-password" \
  -n splunk-mcp-prod
```

#### ConfigMaps
```yaml
# app-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: splunk-mcp-prod
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  DEBUG: "false"
  
  # Security settings
  CORS_ORIGINS: '["https://your-domain.com"]'
  RATE_LIMITING_ENABLED: "true"
  RATE_LIMIT_REQUESTS: "100"
  RATE_LIMIT_WINDOW: "60"
  
  # Session settings
  SESSION_TIMEOUT: "3600"
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES: "60"
  JWT_REFRESH_TOKEN_EXPIRE_DAYS: "7"
  
  # Cache settings
  CACHE_TTL: "300"
  QUERY_CACHE_TTL: "900"
  DASHBOARD_CACHE_TTL: "1800"
  
  # External service timeouts
  SPLUNK_TIMEOUT: "30"
  AI_SERVICE_TIMEOUT: "60"
  EMAIL_TIMEOUT: "30"
```

```bash
# Apply configuration
kubectl apply -f infrastructure/kubernetes/configmaps/app-config.yaml
```

### Core Services Deployment

#### API Gateway
```yaml
# api-gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: splunk-mcp-prod
  labels:
    app: api-gateway
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: api-gateway
        image: ghcr.io/your-org/splunk-mcp/api-gateway:latest
        ports:
        - containerPort: 8000
          protocol: TCP
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: jwt-secret-key
        - name: SPLUNK_HOST
          valueFrom:
            secretKeyRef:
              name: splunk-secrets
              key: host
        - name: SPLUNK_USERNAME
          valueFrom:
            secretKeyRef:
              name: splunk-secrets
              key: username
        - name: SPLUNK_PASSWORD
          valueFrom:
            secretKeyRef:
              name: splunk-secrets
              key: password
        envFrom:
        - configMapRef:
            name: app-config
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp-volume
          mountPath: /tmp
        - name: app-logs
          mountPath: /app/logs
      volumes:
      - name: tmp-volume
        emptyDir: {}
      - name: app-logs
        emptyDir: {}
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - api-gateway
              topologyKey: kubernetes.io/hostname
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: splunk-mcp-prod
  labels:
    app: api-gateway
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
    name: http
  selector:
    app: api-gateway
```

#### NLP Engine
```yaml
# nlp-engine-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nlp-engine
  namespace: splunk-mcp-prod
  labels:
    app: nlp-engine
    version: v1
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: nlp-engine
  template:
    metadata:
      labels:
        app: nlp-engine
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8001"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: nlp-engine
        image: ghcr.io/your-org/splunk-mcp/nlp-engine:latest
        ports:
        - containerPort: 8001
          protocol: TCP
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-api-key
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: anthropic-api-key
        envFrom:
        - configMapRef:
            name: app-config
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8001
          initialDelaySeconds: 15
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8001
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp-volume
          mountPath: /tmp
        - name: model-cache
          mountPath: /app/model_cache
      volumes:
      - name: tmp-volume
        emptyDir: {}
      - name: model-cache
        emptyDir:
          sizeLimit: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: nlp-engine
  namespace: splunk-mcp-prod
  labels:
    app: nlp-engine
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8001"
spec:
  type: ClusterIP
  ports:
  - port: 8001
    targetPort: 8001
    protocol: TCP
    name: http
  selector:
    app: nlp-engine
```

#### Automated Deployment Script
```bash
#!/bin/bash
# deploy-services.sh

set -e

NAMESPACE="splunk-mcp-prod"
DEPLOYMENT_DIR="infrastructure/kubernetes"

echo "Starting Splunk MCP Platform deployment..."

# Function to wait for deployment
wait_for_deployment() {
    local deployment=$1
    echo "Waiting for deployment $deployment to be ready..."
    kubectl rollout status deployment/$deployment -n $NAMESPACE --timeout=600s
}

# Function to check service health
check_service_health() {
    local service=$1
    local port=$2
    echo "Checking health of $service..."
    kubectl exec -n $NAMESPACE deployment/$service -- wget --quiet --tries=1 --timeout=10 --spider http://localhost:$port/health || {
        echo "Health check failed for $service"
        return 1
    }
}

# Deploy core services
echo "Deploying core services..."
kubectl apply -f $DEPLOYMENT_DIR/deployments/api-gateway-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/nlp-engine-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/visualization-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/alert-manager-deployment.yaml

# Wait for core services
wait_for_deployment api-gateway
wait_for_deployment nlp-engine
wait_for_deployment visualization
wait_for_deployment alert-manager

echo "Core services deployed successfully"

# Deploy integration services
echo "Deploying integration services..."
kubectl apply -f $DEPLOYMENT_DIR/deployments/slack-bot-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/teams-bot-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/email-service-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/webhook-service-deployment.yaml

# Deploy export services
echo "Deploying export services..."
kubectl apply -f $DEPLOYMENT_DIR/deployments/pdf-export-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/powerpoint-export-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/word-export-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/csv-export-deployment.yaml

# Deploy platform services
echo "Deploying platform services..."
kubectl apply -f $DEPLOYMENT_DIR/deployments/secure-sharing-deployment.yaml
kubectl apply -f $DEPLOYMENT_DIR/deployments/report-scheduling-deployment.yaml

# Deploy frontend
echo "Deploying frontend..."
kubectl apply -f $DEPLOYMENT_DIR/deployments/frontend-deployment.yaml

echo "All services deployed. Running health checks..."

# Health checks
check_service_health api-gateway 8000
check_service_health nlp-engine 8001
check_service_health visualization 8002
check_service_health alert-manager 8003

echo "Deployment completed successfully!"
echo "Access the platform at: https://your-domain.com"
```

```bash
# Make script executable and run
chmod +x deploy-services.sh
./deploy-services.sh
```

---

## Service Configuration

### Environment-Specific Configuration

#### Production ConfigMap
```yaml
# production-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: production-config
  namespace: splunk-mcp-prod
data:
  # Application Configuration
  ENVIRONMENT: "production"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  
  # Performance Configuration
  WORKERS: "4"
  MAX_CONNECTIONS: "1000"
  CONNECTION_TIMEOUT: "30"
  REQUEST_TIMEOUT: "60"
  
  # Cache Configuration
  CACHE_TTL: "300"
  QUERY_CACHE_SIZE: "1000"
  DASHBOARD_CACHE_SIZE: "500"
  USER_SESSION_CACHE_SIZE: "10000"
  
  # Security Configuration
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES: "60"
  JWT_REFRESH_TOKEN_EXPIRE_DAYS: "7"
  PASSWORD_MIN_LENGTH: "12"
  MFA_ENABLED: "true"
  
  # Rate Limiting
  RATE_LIMITING_ENABLED: "true"
  RATE_LIMIT_REQUESTS: "100"
  RATE_LIMIT_WINDOW: "60"
  BURST_LIMIT: "200"
  
  # External Service Configuration
  SPLUNK_TIMEOUT: "30"
  SPLUNK_MAX_RETRIES: "3"
  AI_SERVICE_TIMEOUT: "60"
  AI_SERVICE_MAX_RETRIES: "2"
  
  # Email Configuration
  EMAIL_TIMEOUT: "30"
  EMAIL_MAX_RETRIES: "3"
  EMAIL_BATCH_SIZE: "50"
  
  # Monitoring Configuration
  METRICS_ENABLED: "true"
  HEALTH_CHECK_INTERVAL: "30"
  PROMETHEUS_METRICS_PORT: "9090"
```

### Database Migration

#### Initial Schema Setup
```bash
# Create database initialization job
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: database-init
  namespace: splunk-mcp-prod
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: db-init
        image: ghcr.io/your-org/splunk-mcp/api-gateway:latest
        command:
        - python
        - manage_db.py
        - init
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        envFrom:
        - configMapRef:
            name: app-config
EOF

# Wait for job completion
kubectl wait --for=condition=complete job/database-init -n splunk-mcp-prod --timeout=300s

# Run migrations for each service
services=("api-gateway" "nlp-engine" "visualization" "alert-manager")
for service in "${services[@]}"; do
    echo "Running migrations for $service..."
    kubectl exec deployment/$service -n splunk-mcp-prod -- python manage_db.py upgrade
done
```

#### Database Validation
```bash
# Validate database schema
kubectl exec -it postgresql-0 -n splunk-mcp-prod -- psql -U postgres -d splunk_mcp -c "
SELECT schemaname, tablename, tableowner 
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY schemaname, tablename;
"

# Check table counts
kubectl exec -it postgresql-0 -n splunk-mcp-prod -- psql -U postgres -d splunk_mcp -c "
SELECT schemaname, tablename, 
       (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', schemaname, tablename), false, true, '')))[1]::text::int AS row_count
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY schemaname, tablename;
"
```

---

## SSL/TLS Setup

### Certificate Management with cert-manager

#### Install cert-manager
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -l app=cert-manager -n cert-manager --timeout=300s
kubectl wait --for=condition=ready pod -l app=cainjector -n cert-manager --timeout=300s
kubectl wait --for=condition=ready pod -l app=webhook -n cert-manager --timeout=300s
```

#### Configure Let's Encrypt Issuer
```yaml
# cluster-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@your-domain.com
    privateKeySecretRef:
      name: letsencrypt-prod-private-key
    solvers:
    - http01:
        ingress:
          class: nginx
          podTemplate:
            spec:
              nodeSelector:
                "kubernetes.io/os": linux
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@your-domain.com
    privateKeySecretRef:
      name: letsencrypt-staging-private-key
    solvers:
    - http01:
        ingress:
          class: nginx
```

```bash
# Apply certificate issuers
kubectl apply -f infrastructure/kubernetes/ingress/cluster-issuer.yaml
```

#### Certificate Configuration
```yaml
# certificates.yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: splunk-mcp-tls
  namespace: splunk-mcp-prod
spec:
  secretName: splunk-mcp-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - splunk-mcp.your-domain.com
  - api.splunk-mcp.your-domain.com
  - www.splunk-mcp.your-domain.com
```

```bash
# Apply certificate configuration
kubectl apply -f infrastructure/kubernetes/ingress/certificates.yaml

# Check certificate status
kubectl describe certificate splunk-mcp-tls -n splunk-mcp-prod
kubectl get certificaterequest -n splunk-mcp-prod
```

### Ingress Configuration

#### NGINX Ingress Controller
```bash
# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.service.type=LoadBalancer \
  --set controller.metrics.enabled=true \
  --set controller.podSecurityContext.runAsUser=101 \
  --set controller.podSecurityContext.runAsGroup=82

# Wait for ingress controller to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=ingress-nginx -n ingress-nginx --timeout=300s
```

#### Ingress Resources
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: splunk-mcp-ingress
  namespace: splunk-mcp-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "60"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Strict-Transport-Security: max-age=31536000; includeSubDomains";
      more_set_headers "Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'";
spec:
  tls:
  - hosts:
    - splunk-mcp.your-domain.com
    secretName: splunk-mcp-tls
  rules:
  - host: splunk-mcp.your-domain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
```

```bash
# Apply ingress configuration
kubectl apply -f infrastructure/kubernetes/ingress/ingress.yaml

# Check ingress status
kubectl get ingress -n splunk-mcp-prod
kubectl describe ingress splunk-mcp-ingress -n splunk-mcp-prod
```

---

## Monitoring Configuration

### Prometheus Stack Deployment

#### Prometheus Operator
```bash
# Add Prometheus community Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
helm install prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.accessModes[0]=ReadWriteOnce \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.accessModes[0]=ReadWriteOnce \
  --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.resources.requests.storage=10Gi \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.size=10Gi

# Wait for monitoring stack to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=300s
```

#### Service Monitors
```yaml
# service-monitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: splunk-mcp-services
  namespace: monitoring
  labels:
    app: splunk-mcp
spec:
  selector:
    matchLabels:
      prometheus.io/scrape: "true"
  namespaceSelector:
    matchNames:
    - splunk-mcp-prod
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: splunk-mcp-databases
  namespace: monitoring
  labels:
    app: splunk-mcp-databases
spec:
  selector:
    matchLabels:
      app: postgresql
  namespaceSelector:
    matchNames:
    - splunk-mcp-prod
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

```bash
# Apply service monitors
kubectl apply -f infrastructure/kubernetes/monitoring/service-monitor.yaml
```

#### Custom Alert Rules
```yaml
# alert-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: splunk-mcp-alerts
  namespace: monitoring
  labels:
    app: splunk-mcp
spec:
  groups:
  - name: splunk-mcp.rules
    rules:
    - alert: SplunkMCPServiceDown
      expr: up{job="splunk-mcp-services"} == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Splunk MCP service {{ $labels.instance }} is down"
        description: "Service {{ $labels.instance }} has been down for more than 1 minute."
    
    - alert: SplunkMCPHighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "High error rate detected in {{ $labels.service }}"
        description: "Error rate is {{ $value | humanizePercentage }} for service {{ $labels.service }}"
    
    - alert: SplunkMCPHighResponseTime
      expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High response time detected"
        description: "95th percentile response time is {{ $value }}s"
    
    - alert: SplunkMCPDatabaseConnectionFailed
      expr: postgres_up == 0
      for: 30s
      labels:
        severity: critical
      annotations:
        summary: "Database connection failed"
        description: "PostgreSQL database is not accessible"
    
    - alert: SplunkMCPHighMemoryUsage
      expr: container_memory_usage_bytes{container!="POD",container!=""} / container_spec_memory_limit_bytes > 0.9
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage in {{ $labels.pod }}"
        description: "Memory usage is {{ $value | humanizePercentage }} in pod {{ $labels.pod }}"
```

```bash
# Apply alert rules
kubectl apply -f infrastructure/kubernetes/monitoring/alert-rules.yaml
```

### Grafana Dashboard Configuration

#### Import Dashboards
```bash
# Get Grafana admin password
kubectl get secret prometheus-stack-grafana -n monitoring -o jsonpath="{.data.admin-password}" | base64 --decode

# Port forward to access Grafana
kubectl port-forward svc/prometheus-stack-grafana 3000:80 -n monitoring

# Import dashboards (can be done via UI or API)
curl -X POST \
  http://admin:$(kubectl get secret prometheus-stack-grafana -n monitoring -o jsonpath="{.data.admin-password}" | base64 --decode)@localhost:3000/api/dashboards/import \
  -H 'Content-Type: application/json' \
  -d @infrastructure/kubernetes/monitoring/dashboards/platform-overview.json
```

---

## Post-Installation Validation

### Health Check Script
```bash
#!/bin/bash
# health-check.sh

NAMESPACE="splunk-mcp-prod"
DOMAIN="splunk-mcp.your-domain.com"

echo "=== Splunk MCP Platform Health Check ==="

# Check namespace exists
if ! kubectl get namespace $NAMESPACE >/dev/null 2>&1; then
    echo "❌ Namespace $NAMESPACE does not exist"
    exit 1
fi
echo "✅ Namespace $NAMESPACE exists"

# Check all pods are running
echo "📋 Checking pod status..."
kubectl get pods -n $NAMESPACE --no-headers | while read line; do
    pod_name=$(echo $line | awk '{print $1}')
    pod_status=$(echo $line | awk '{print $3}')
    if [[ "$pod_status" != "Running" ]]; then
        echo "❌ Pod $pod_name is not running (Status: $pod_status)"
    else
        echo "✅ Pod $pod_name is running"
    fi
done

# Check services are accessible
services=("api-gateway:8000" "nlp-engine:8001" "visualization:8002" "alert-manager:8003")
for service in "${services[@]}"; do
    service_name=$(echo $service | cut -d: -f1)
    service_port=$(echo $service | cut -d: -f2)
    
    if kubectl exec -n $NAMESPACE deployment/$service_name -- wget --quiet --tries=1 --timeout=10 --spider http://localhost:$service_port/health; then
        echo "✅ $service_name health check passed"
    else
        echo "❌ $service_name health check failed"
    fi
done

# Check external access
echo "🌐 Checking external access..."
if curl -sSf https://$DOMAIN/health >/dev/null; then
    echo "✅ External access to https://$DOMAIN is working"
else
    echo "❌ External access to https://$DOMAIN failed"
fi

# Check SSL certificate
echo "🔒 Checking SSL certificate..."
if echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -text | grep -q "Let's Encrypt"; then
    echo "✅ SSL certificate is valid and from Let's Encrypt"
else
    echo "❌ SSL certificate check failed"
fi

# Check database connectivity
echo "🗃️ Checking database connectivity..."
if kubectl exec -n $NAMESPACE deployment/api-gateway -- python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
"; then
    echo "✅ Database connectivity check passed"
else
    echo "❌ Database connectivity check failed"
fi

# Check Redis connectivity
echo "📦 Checking Redis connectivity..."
if kubectl exec -n $NAMESPACE deployment/api-gateway -- python -c "
import os
import redis
try:
    r = redis.from_url(os.environ['REDIS_URL'])
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
    exit(1)
"; then
    echo "✅ Redis connectivity check passed"
else
    echo "❌ Redis connectivity check failed"
fi

echo "🎉 Health check completed!"
```

```bash
# Make script executable and run
chmod +x health-check.sh
./health-check.sh
```

### Functional Testing

#### API Testing Script
```bash
#!/bin/bash
# api-test.sh

DOMAIN="splunk-mcp.your-domain.com"
API_BASE="https://$DOMAIN/api/v1"

echo "=== API Functional Testing ==="

# Test health endpoint
echo "Testing health endpoint..."
if curl -sSf "$API_BASE/health" | jq -e '.status == "ok"' >/dev/null; then
    echo "✅ Health endpoint working"
else
    echo "❌ Health endpoint failed"
fi

# Test authentication (requires manual token setup)
echo "Testing authentication..."
# Create test user and get token (this would be done through admin interface)
# TOKEN=$(curl -sSf -X POST "$API_BASE/auth/login" -d '{"username":"test","password":"test"}' | jq -r '.access_token')

# Test protected endpoint
# if curl -sSf -H "Authorization: Bearer $TOKEN" "$API_BASE/user/profile" >/dev/null; then
#     echo "✅ Authentication working"
# else
#     echo "❌ Authentication failed"
# fi

echo "Manual testing required for authentication flow"
```

### Performance Baseline

#### Load Testing
```bash
# Install k6 for load testing
sudo apt-get update
sudo apt-get install k6

# Create basic load test
cat <<EOF > load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 10 },
    { duration: '5m', target: 10 },
    { duration: '2m', target: 20 },
    { duration: '5m', target: 20 },
    { duration: '2m', target: 0 },
  ],
};

export default function() {
  let response = http.get('https://splunk-mcp.your-domain.com/health');
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
EOF

# Run load test
k6 run load-test.js
```

---

## Troubleshooting

### Common Installation Issues

#### Pod Startup Failures
```bash
# Check pod status and events
kubectl get pods -n splunk-mcp-prod
kubectl describe pod <pod-name> -n splunk-mcp-prod

# Check pod logs
kubectl logs <pod-name> -n splunk-mcp-prod
kubectl logs <pod-name> -n splunk-mcp-prod --previous

# Check resource constraints
kubectl describe nodes
kubectl top nodes
kubectl top pods -n splunk-mcp-prod
```

#### Image Pull Errors
```bash
# Check image pull secrets
kubectl get secrets -n splunk-mcp-prod
kubectl describe secret <image-pull-secret> -n splunk-mcp-prod

# Verify image exists
docker pull ghcr.io/your-org/splunk-mcp/api-gateway:latest

# Check node capacity
kubectl describe node <node-name>
```

#### Network Connectivity Issues
```bash
# Test service connectivity
kubectl exec -it <pod-name> -n splunk-mcp-prod -- nslookup postgresql
kubectl exec -it <pod-name> -n splunk-mcp-prod -- telnet postgresql 5432

# Check network policies
kubectl get networkpolicy -n splunk-mcp-prod
kubectl describe networkpolicy <policy-name> -n splunk-mcp-prod

# Test ingress
kubectl get ingress -n splunk-mcp-prod
kubectl describe ingress splunk-mcp-ingress -n splunk-mcp-prod
```

#### SSL Certificate Issues
```bash
# Check certificate status
kubectl get certificate -n splunk-mcp-prod
kubectl describe certificate splunk-mcp-tls -n splunk-mcp-prod

# Check certificate request
kubectl get certificaterequest -n splunk-mcp-prod
kubectl describe certificaterequest <request-name> -n splunk-mcp-prod

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

### Recovery Procedures

#### Service Recovery
```bash
# Restart failed service
kubectl rollout restart deployment/<service-name> -n splunk-mcp-prod

# Scale service
kubectl scale deployment/<service-name> --replicas=0 -n splunk-mcp-prod
kubectl scale deployment/<service-name> --replicas=2 -n splunk-mcp-prod

# Force pod recreation
kubectl delete pod <pod-name> -n splunk-mcp-prod
```

#### Database Recovery
```bash
# Check database connectivity
kubectl exec -it postgresql-0 -n splunk-mcp-prod -- psql -U postgres -l

# Restart database
kubectl delete pod postgresql-0 -n splunk-mcp-prod

# Check database logs
kubectl logs postgresql-0 -n splunk-mcp-prod
```

### Support Information

#### Collecting Debug Information
```bash
# Create debug bundle
mkdir -p debug-bundle
cd debug-bundle

# Collect pod information
kubectl get pods -n splunk-mcp-prod -o yaml > pods.yaml
kubectl get services -n splunk-mcp-prod -o yaml > services.yaml
kubectl get ingress -n splunk-mcp-prod -o yaml > ingress.yaml

# Collect logs
for pod in $(kubectl get pods -n splunk-mcp-prod -o jsonpath='{.items[*].metadata.name}'); do
    kubectl logs $pod -n splunk-mcp-prod > $pod.log 2>&1
done

# Collect events
kubectl get events -n splunk-mcp-prod --sort-by='.lastTimestamp' > events.txt

# Collect node information
kubectl get nodes -o yaml > nodes.yaml
kubectl top nodes > node-usage.txt

# Create tarball
cd ..
tar -czf debug-bundle-$(date +%Y%m%d-%H%M%S).tar.gz debug-bundle/
```

---

*This installation guide provides comprehensive instructions for deploying the Splunk MCP Integration Platform. For additional support or questions, contact the platform support team.*