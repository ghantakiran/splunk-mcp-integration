# Kubernetes Deployment Guide

This guide provides comprehensive instructions for deploying the Splunk MCP Integration platform on Kubernetes for production environments.

## Overview

Kubernetes deployment provides:
- High availability and fault tolerance
- Automatic scaling and load balancing
- Rolling updates and rollback capabilities
- Service discovery and load balancing
- Persistent storage management
- Advanced monitoring and logging

## Prerequisites

### System Requirements

#### Kubernetes Cluster
- **Kubernetes Version**: 1.20+
- **Node Count**: 3+ nodes (for HA)
- **CPU**: 16+ cores total
- **Memory**: 32GB+ RAM total
- **Storage**: 500GB+ persistent storage

#### Management Tools
- **kubectl**: Latest version
- **Helm**: 3.0+ (optional but recommended)
- **Docker**: For building images

### Cluster Setup Options

#### 1. Managed Kubernetes Services
```bash
# AWS EKS
eksctl create cluster --name splunk-mcp --region us-west-2 --nodes 3

# Google GKE
gcloud container clusters create splunk-mcp --num-nodes=3 --zone=us-central1-a

# Azure AKS
az aks create --resource-group myResourceGroup --name splunk-mcp --node-count 3
```

#### 2. Self-Managed Cluster (kubeadm)
```bash
# Initialize master node
sudo kubeadm init --pod-network-cidr=10.244.0.0/16

# Set up kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install network plugin (Flannel)
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml

# Join worker nodes
kubeadm token create --print-join-command
```

### Verify Cluster Setup
```bash
# Check cluster status
kubectl cluster-info
kubectl get nodes
kubectl get pods --all-namespaces

# Check available storage classes
kubectl get storageclass

# Verify RBAC is enabled
kubectl auth can-i create pods --all-namespaces
```

## Project Preparation

### 1. Image Registry Setup

#### Option A: Docker Hub (Public)
```bash
# Build and push images
docker build -t your-username/splunk-mcp-api-gateway:latest services/api-gateway/
docker push your-username/splunk-mcp-api-gateway:latest

docker build -t your-username/splunk-mcp-nlp-engine:latest services/nlp-engine/
docker push your-username/splunk-mcp-nlp-engine:latest

# Continue for all services...
```

#### Option B: Private Registry
```bash
# Set up private registry
docker run -d -p 5000:5000 --name registry registry:2

# Tag and push images
docker tag splunk-mcp-api-gateway:latest localhost:5000/splunk-mcp-api-gateway:latest
docker push localhost:5000/splunk-mcp-api-gateway:latest

# Create registry secret for Kubernetes
kubectl create secret docker-registry regcred \
  --docker-server=localhost:5000 \
  --docker-username=username \
  --docker-password=password \
  --docker-email=email@example.com
```

#### Option C: Cloud Registry
```bash
# AWS ECR
aws ecr create-repository --repository-name splunk-mcp-api-gateway
docker tag splunk-mcp-api-gateway:latest 123456789012.dkr.ecr.us-west-2.amazonaws.com/splunk-mcp-api-gateway:latest
docker push 123456789012.dkr.ecr.us-west-2.amazonaws.com/splunk-mcp-api-gateway:latest

# Google Container Registry
docker tag splunk-mcp-api-gateway:latest gcr.io/project-id/splunk-mcp-api-gateway:latest
docker push gcr.io/project-id/splunk-mcp-api-gateway:latest
```

### 2. Namespace and RBAC Setup

#### Create Namespace
```bash
# Create production namespace
kubectl create namespace splunk-mcp-prod

# Set as default namespace
kubectl config set-context --current --namespace=splunk-mcp-prod

# Label namespace
kubectl label namespace splunk-mcp-prod environment=production
```

#### RBAC Configuration
```yaml
# infrastructure/kubernetes/rbac/service-account.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: splunk-mcp-service-account
  namespace: splunk-mcp-prod
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: splunk-mcp-prod
  name: splunk-mcp-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: splunk-mcp-rolebinding
  namespace: splunk-mcp-prod
subjects:
- kind: ServiceAccount
  name: splunk-mcp-service-account
  namespace: splunk-mcp-prod
roleRef:
  kind: Role
  name: splunk-mcp-role
  apiGroup: rbac.authorization.k8s.io
```

```bash
# Apply RBAC configuration
kubectl apply -f infrastructure/kubernetes/rbac/service-account.yaml
```

## Secrets and Configuration Management

### 1. Create Application Secrets

#### Database Secrets
```bash
# Create PostgreSQL secret
kubectl create secret generic postgres-secret \
  --from-literal=host=postgres-service \
  --from-literal=port=5432 \
  --from-literal=database=splunk_mcp \
  --from-literal=username=splunk_mcp_user \
  --from-literal=password=$(openssl rand -base64 16) \
  --namespace=splunk-mcp-prod

# Create Redis secret
kubectl create secret generic redis-secret \
  --from-literal=host=redis-service \
  --from-literal=port=6379 \
  --from-literal=password=$(openssl rand -base64 16) \
  --namespace=splunk-mcp-prod
```

#### API Keys Secret
```bash
# Create API keys secret
kubectl create secret generic api-keys \
  --from-literal=openai-api-key="$OPENAI_API_KEY" \
  --from-literal=anthropic-api-key="$ANTHROPIC_API_KEY" \
  --from-literal=jwt-secret=$(openssl rand -base64 32) \
  --namespace=splunk-mcp-prod
```

#### Splunk Configuration Secret
```bash
# Create Splunk connection secret
kubectl create secret generic splunk-config \
  --from-literal=host="$SPLUNK_HOST" \
  --from-literal=port="$SPLUNK_PORT" \
  --from-literal=username="$SPLUNK_USERNAME" \
  --from-literal=password="$SPLUNK_PASSWORD" \
  --from-literal=scheme="$SPLUNK_SCHEME" \
  --namespace=splunk-mcp-prod
```

### 2. Configuration Maps

#### Application Configuration
```yaml
# infrastructure/kubernetes/configmaps/app-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: splunk-mcp-prod
data:
  environment: "production"
  log_level: "INFO"
  debug: "false"
  max_workers: "4"
  timeout: "30"
  max_connections: "100"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
  namespace: splunk-mcp-prod
data:
  nginx.conf: |
    upstream api_backend {
        server api-gateway-service:8000;
    }
    
    server {
        listen 80;
        server_name _;
        
        location / {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
```

```bash
# Apply configuration maps
kubectl apply -f infrastructure/kubernetes/configmaps/
```

## Storage Configuration

### 1. Persistent Volume Claims

#### PostgreSQL Storage
```yaml
# infrastructure/kubernetes/storage/postgres-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: splunk-mcp-prod
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd  # Use your cluster's fast storage class
  resources:
    requests:
      storage: 100Gi
```

#### Redis Storage
```yaml
# infrastructure/kubernetes/storage/redis-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: splunk-mcp-prod
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 20Gi
```

#### Application Logs Storage
```yaml
# infrastructure/kubernetes/storage/logs-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: logs-pvc
  namespace: splunk-mcp-prod
spec:
  accessModes:
    - ReadWriteMany  # Shared across pods
  storageClassName: standard
  resources:
    requests:
      storage: 50Gi
```

```bash
# Apply storage configurations
kubectl apply -f infrastructure/kubernetes/storage/
```

## Database Deployment

### 1. PostgreSQL Deployment

#### StatefulSet Configuration
```yaml
# infrastructure/kubernetes/deployments/postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: splunk-mcp-prod
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      serviceAccountName: splunk-mcp-service-account
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: database
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        - name: postgres-init
          mountPath: /docker-entrypoint-initdb.d
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - $(POSTGRES_USER)
            - -d
            - $(POSTGRES_DB)
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - $(POSTGRES_USER)
            - -d
            - $(POSTGRES_DB)
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: postgres-init
        configMap:
          name: postgres-init
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 100Gi
```

#### Service Configuration
```yaml
# infrastructure/kubernetes/services/postgres-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: splunk-mcp-prod
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

### 2. Redis Deployment

#### StatefulSet Configuration
```yaml
# infrastructure/kubernetes/deployments/redis-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: splunk-mcp-prod
spec:
  serviceName: redis-service
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      serviceAccountName: splunk-mcp-service-account
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command:
        - redis-server
        - /etc/redis/redis.conf
        - --requirepass
        - $(REDIS_PASSWORD)
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: password
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        - name: redis-config
          mountPath: /etc/redis
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
  volumeClaimTemplates:
  - metadata:
      name: redis-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 20Gi
```

```bash
# Deploy databases
kubectl apply -f infrastructure/kubernetes/deployments/postgres-statefulset.yaml
kubectl apply -f infrastructure/kubernetes/services/postgres-service.yaml
kubectl apply -f infrastructure/kubernetes/deployments/redis-statefulset.yaml
kubectl apply -f infrastructure/kubernetes/services/redis-service.yaml

# Wait for databases to be ready
kubectl wait --for=condition=Ready pod -l app=postgres --timeout=300s
kubectl wait --for=condition=Ready pod -l app=redis --timeout=300s
```

## Application Services Deployment

### 1. API Gateway Deployment

```yaml
# infrastructure/kubernetes/deployments/api-gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: splunk-mcp-prod
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
      serviceAccountName: splunk-mcp-service-account
      containers:
      - name: api-gateway
        image: your-registry/splunk-mcp-api-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)"
        - name: POSTGRES_HOST
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: host
        - name: POSTGRES_PORT
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: port
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: database
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: REDIS_URL
          value: "redis://:$(REDIS_PASSWORD)@$(REDIS_HOST):$(REDIS_PORT)/0"
        - name: REDIS_HOST
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: host
        - name: REDIS_PORT
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: port
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: password
        - name: SPLUNK_HOST
          valueFrom:
            secretKeyRef:
              name: splunk-config
              key: host
        - name: SPLUNK_PORT
          valueFrom:
            secretKeyRef:
              name: splunk-config
              key: port
        - name: SPLUNK_USERNAME
          valueFrom:
            secretKeyRef:
              name: splunk-config
              key: username
        - name: SPLUNK_PASSWORD
          valueFrom:
            secretKeyRef:
              name: splunk-config
              key: password
        - name: SPLUNK_SCHEME
          valueFrom:
            secretKeyRef:
              name: splunk-config
              key: scheme
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: jwt-secret
        - name: ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: environment
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: log_level
        volumeMounts:
        - name: logs
          mountPath: /app/logs
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: logs
        persistentVolumeClaim:
          claimName: logs-pvc
      imagePullSecrets:
      - name: regcred
```

### 2. NLP Engine Deployment

```yaml
# infrastructure/kubernetes/deployments/nlp-engine-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nlp-engine
  namespace: splunk-mcp-prod
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nlp-engine
  template:
    metadata:
      labels:
        app: nlp-engine
    spec:
      serviceAccountName: splunk-mcp-service-account
      containers:
      - name: nlp-engine
        image: your-registry/splunk-mcp-nlp-engine:latest
        ports:
        - containerPort: 8001
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai-api-key
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: anthropic-api-key
        - name: REDIS_URL
          value: "redis://:$(REDIS_PASSWORD)@$(REDIS_HOST):$(REDIS_PORT)/1"
        - name: REDIS_HOST
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: host
        - name: REDIS_PORT
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: port
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: password
        - name: ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: environment
        volumeMounts:
        - name: logs
          mountPath: /app/logs
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: logs
        persistentVolumeClaim:
          claimName: logs-pvc
      imagePullSecrets:
      - name: regcred
```

### 3. Service Definitions

```yaml
# infrastructure/kubernetes/services/api-gateway-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
  namespace: splunk-mcp-prod
  labels:
    app: api-gateway
spec:
  selector:
    app: api-gateway
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: ClusterIP
---
# infrastructure/kubernetes/services/nlp-engine-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nlp-engine-service
  namespace: splunk-mcp-prod
  labels:
    app: nlp-engine
spec:
  selector:
    app: nlp-engine
  ports:
  - port: 8001
    targetPort: 8001
    name: http
  type: ClusterIP
```

```bash
# Deploy application services
kubectl apply -f infrastructure/kubernetes/deployments/api-gateway-deployment.yaml
kubectl apply -f infrastructure/kubernetes/services/api-gateway-service.yaml
kubectl apply -f infrastructure/kubernetes/deployments/nlp-engine-deployment.yaml
kubectl apply -f infrastructure/kubernetes/services/nlp-engine-service.yaml

# Wait for deployments to be ready
kubectl wait --for=condition=Available deployment api-gateway --timeout=300s
kubectl wait --for=condition=Available deployment nlp-engine --timeout=300s
```

## Ingress and Load Balancing

### 1. Install NGINX Ingress Controller

```bash
# Install NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Verify installation
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

### 2. SSL Certificate Management

#### Install cert-manager
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=Available deployment -l app.kubernetes.io/name=cert-manager --timeout=300s -n cert-manager
```

#### Create ClusterIssuer
```yaml
# infrastructure/kubernetes/ingress/cluster-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@yourdomain.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

### 3. Ingress Configuration

```yaml
# infrastructure/kubernetes/ingress/main-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: splunk-mcp-ingress
  namespace: splunk-mcp-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
spec:
  tls:
  - hosts:
    - yourdomain.com
    - api.yourdomain.com
    secretName: splunk-mcp-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway-service
            port:
              number: 8000
```

```bash
# Apply ingress configuration
kubectl apply -f infrastructure/kubernetes/ingress/cluster-issuer.yaml
kubectl apply -f infrastructure/kubernetes/ingress/main-ingress.yaml

# Check certificate status
kubectl describe certificate splunk-mcp-tls -n splunk-mcp-prod
```

## Auto-scaling Configuration

### 1. Horizontal Pod Autoscaler (HPA)

```yaml
# infrastructure/kubernetes/hpa/api-gateway-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: splunk-mcp-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
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
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### 2. Vertical Pod Autoscaler (VPA)

```yaml
# infrastructure/kubernetes/vpa/api-gateway-vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-gateway-vpa
  namespace: splunk-mcp-prod
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: api-gateway
      maxAllowed:
        cpu: 2
        memory: 4Gi
      minAllowed:
        cpu: 100m
        memory: 128Mi
```

```bash
# Apply autoscaling configurations
kubectl apply -f infrastructure/kubernetes/hpa/
kubectl apply -f infrastructure/kubernetes/vpa/

# Verify HPA
kubectl get hpa -n splunk-mcp-prod
```

## Monitoring and Observability

### 1. Deploy Prometheus and Grafana

```bash
# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus stack
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values infrastructure/monitoring/prometheus-values.yaml \
  --wait
```

### 2. ServiceMonitor Configuration

```yaml
# infrastructure/monitoring/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: splunk-mcp-metrics
  namespace: monitoring
  labels:
    app: splunk-mcp
spec:
  selector:
    matchLabels:
      app: api-gateway
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
  namespaceSelector:
    matchNames:
    - splunk-mcp-prod
```

### 3. Custom Dashboards

```yaml
# infrastructure/monitoring/grafana-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: splunk-mcp-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  dashboard.json: |
    {
      "dashboard": {
        "title": "Splunk MCP Platform",
        "panels": [
          {
            "title": "API Gateway Requests",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(http_requests_total{service=\"api-gateway-service\"}[5m])"
              }
            ]
          }
        ]
      }
    }
```

```bash
# Apply monitoring configuration
kubectl apply -f infrastructure/monitoring/
```

## Security Configuration

### 1. Network Policies

```yaml
# infrastructure/kubernetes/network-policies/default-deny.yaml
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
# infrastructure/kubernetes/network-policies/api-gateway-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-gateway-policy
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
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to: []  # Allow external traffic for Splunk API calls
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 8089
```

### 2. Pod Security Standards

```yaml
# infrastructure/kubernetes/security/pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: splunk-mcp-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

```bash
# Apply security policies
kubectl apply -f infrastructure/kubernetes/network-policies/
kubectl apply -f infrastructure/kubernetes/security/
```

## Backup and Disaster Recovery

### 1. Database Backup CronJob

```yaml
# infrastructure/kubernetes/backup/postgres-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: splunk-mcp-prod
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres-service -U $POSTGRES_USER -d $POSTGRES_DB > /backup/postgres-$(date +%Y%m%d_%H%M%S).sql
              aws s3 cp /backup/postgres-$(date +%Y%m%d_%H%M%S).sql s3://your-backup-bucket/
            env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: username
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: database
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

### 2. Application State Backup

```bash
# Create backup script
cat > scripts/k8s-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup Kubernetes resources
kubectl get all -o yaml -n splunk-mcp-prod > $BACKUP_DIR/resources.yaml
kubectl get secrets -o yaml -n splunk-mcp-prod > $BACKUP_DIR/secrets.yaml
kubectl get configmaps -o yaml -n splunk-mcp-prod > $BACKUP_DIR/configmaps.yaml
kubectl get pvc -o yaml -n splunk-mcp-prod > $BACKUP_DIR/pvc.yaml

# Compress and upload
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
aws s3 cp $BACKUP_DIR.tar.gz s3://your-backup-bucket/k8s-backups/
rm -rf $BACKUP_DIR
EOF

chmod +x scripts/k8s-backup.sh
```

## Deployment and Management

### 1. Deployment Script

```bash
# Create deployment script
cat > scripts/deploy-k8s.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting Kubernetes deployment..."

# Apply namespace and RBAC
kubectl apply -f infrastructure/kubernetes/rbac/

# Apply storage
kubectl apply -f infrastructure/kubernetes/storage/

# Apply configurations
kubectl apply -f infrastructure/kubernetes/configmaps/

# Deploy databases
kubectl apply -f infrastructure/kubernetes/deployments/postgres-statefulset.yaml
kubectl apply -f infrastructure/kubernetes/services/postgres-service.yaml
kubectl apply -f infrastructure/kubernetes/deployments/redis-statefulset.yaml
kubectl apply -f infrastructure/kubernetes/services/redis-service.yaml

echo "⏳ Waiting for databases to be ready..."
kubectl wait --for=condition=Ready pod -l app=postgres --timeout=300s
kubectl wait --for=condition=Ready pod -l app=redis --timeout=300s

# Run database migrations
kubectl run migration-job --image=your-registry/splunk-mcp-api-gateway:latest \
  --restart=Never --rm -i --tty \
  --env-from=secretRef:postgres-secret \
  -- python -m alembic upgrade head

# Deploy application services
kubectl apply -f infrastructure/kubernetes/deployments/
kubectl apply -f infrastructure/kubernetes/services/

echo "⏳ Waiting for applications to be ready..."
kubectl wait --for=condition=Available deployment --all --timeout=600s

# Apply ingress
kubectl apply -f infrastructure/kubernetes/ingress/

# Apply autoscaling
kubectl apply -f infrastructure/kubernetes/hpa/

# Apply monitoring
kubectl apply -f infrastructure/monitoring/

echo "✅ Deployment complete!"
kubectl get pods -n splunk-mcp-prod
EOF

chmod +x scripts/deploy-k8s.sh
```

### 2. Health Check Script

```bash
# Create health check script
cat > scripts/health-check-k8s.sh << 'EOF'
#!/bin/bash

echo "🔍 Checking Kubernetes deployment health..."

# Check pod status
echo "📋 Pod Status:"
kubectl get pods -n splunk-mcp-prod

# Check service endpoints
echo "🌐 Service Endpoints:"
kubectl get endpoints -n splunk-mcp-prod

# Check ingress
echo "🚪 Ingress Status:"
kubectl get ingress -n splunk-mcp-prod

# Test health endpoints
echo "🏥 Health Checks:"
INGRESS_IP=$(kubectl get ingress splunk-mcp-ingress -n splunk-mcp-prod -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

if [ ! -z "$INGRESS_IP" ]; then
    curl -f http://$INGRESS_IP/health || echo "❌ Health check failed"
else
    echo "⚠️  Ingress IP not available"
fi

# Check HPA status
echo "📊 Auto-scaling Status:"
kubectl get hpa -n splunk-mcp-prod

echo "✅ Health check complete!"
EOF

chmod +x scripts/health-check-k8s.sh
```

### 3. Rolling Update Script

```bash
# Create rolling update script
cat > scripts/rolling-update-k8s.sh << 'EOF'
#!/bin/bash
set -e

SERVICE=$1
NEW_IMAGE=$2

if [ -z "$SERVICE" ] || [ -z "$NEW_IMAGE" ]; then
    echo "Usage: $0 <service-name> <new-image>"
    echo "Example: $0 api-gateway your-registry/splunk-mcp-api-gateway:v1.1.0"
    exit 1
fi

echo "🔄 Rolling update for $SERVICE to $NEW_IMAGE..."

# Update deployment
kubectl set image deployment/$SERVICE $SERVICE=$NEW_IMAGE -n splunk-mcp-prod

# Watch rollout status
kubectl rollout status deployment/$SERVICE -n splunk-mcp-prod

# Verify health
sleep 30
kubectl get pods -l app=$SERVICE -n splunk-mcp-prod

echo "✅ Rolling update complete for $SERVICE!"
EOF

chmod +x scripts/rolling-update-k8s.sh
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Pod Startup Issues
```bash
# Check pod events
kubectl describe pod <pod-name> -n splunk-mcp-prod

# Check pod logs
kubectl logs <pod-name> -n splunk-mcp-prod

# Check previous container logs
kubectl logs <pod-name> -n splunk-mcp-prod --previous

# Debug with temporary pod
kubectl run debug --image=busybox --rm -it --restart=Never -- /bin/sh
```

#### 2. Service Discovery Issues
```bash
# Test DNS resolution
kubectl run test-dns --image=busybox --rm -it --restart=Never -- nslookup api-gateway-service.splunk-mcp-prod.svc.cluster.local

# Check service endpoints
kubectl get endpoints api-gateway-service -n splunk-mcp-prod

# Test service connectivity
kubectl run test-connectivity --image=curlimages/curl --rm -it --restart=Never -- curl http://api-gateway-service.splunk-mcp-prod.svc.cluster.local:8000/health
```

#### 3. Storage Issues
```bash
# Check PVC status
kubectl get pvc -n splunk-mcp-prod

# Check storage class
kubectl get storageclass

# Check persistent volumes
kubectl get pv

# Debug storage access
kubectl run storage-debug --image=busybox --rm -it --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"storage-debug","image":"busybox","command":["/bin/sh"],"volumeMounts":[{"mountPath":"/data","name":"test-vol"}]}],"volumes":[{"name":"test-vol","persistentVolumeClaim":{"claimName":"postgres-pvc"}}]}}' \
  -n splunk-mcp-prod
```

#### 4. Certificate Issues
```bash
# Check certificate status
kubectl describe certificate splunk-mcp-tls -n splunk-mcp-prod

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Force certificate renewal
kubectl delete secret splunk-mcp-tls -n splunk-mcp-prod
kubectl delete certificate splunk-mcp-tls -n splunk-mcp-prod
kubectl apply -f infrastructure/kubernetes/ingress/main-ingress.yaml
```

---

**Completion**: Your Kubernetes deployment is now ready for production use. Monitor the cluster regularly and follow the operational procedures for maintenance and updates.