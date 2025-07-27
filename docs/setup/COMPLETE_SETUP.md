# Complete Setup Configuration Guide

This comprehensive guide walks you through the complete setup of the Splunk MCP Integration platform from scratch, including all dependencies, configurations, and deployment options.

## Overview

This guide provides step-by-step instructions for:
- System prerequisites and dependencies
- Credential setup and security configuration
- Splunk integration configuration
- Docker Compose deployment (development)
- Kubernetes deployment (production)
- Testing and validation
- Troubleshooting common issues

## Prerequisites

### System Requirements

#### Minimum Requirements (Development)
- **CPU**: 4 cores (Intel/AMD x64 or Apple Silicon)
- **Memory**: 8GB RAM
- **Storage**: 50GB free space
- **OS**: Linux (Ubuntu 20.04+), macOS (10.15+), Windows 10+ with WSL2
- **Network**: Internet connectivity for downloading dependencies

#### Recommended Requirements (Production)
- **CPU**: 16+ cores
- **Memory**: 32GB+ RAM
- **Storage**: 500GB+ SSD storage
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- **Network**: Dedicated network with firewall configuration

### Software Dependencies

#### Required Software
```bash
# Docker and Docker Compose
Docker Engine: 20.10+
Docker Compose: 2.0+

# Git
Git: 2.30+

# Python (for scripts and validation)
Python: 3.8+

# Node.js (for frontend development)
Node.js: 16+
npm: 8+

# Kubernetes (for production deployment)
kubectl: 1.20+
Helm: 3.0+ (optional)
```

#### Installation Instructions

##### Ubuntu/Debian
```bash
# Update package index
sudo apt update

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Install Git
sudo apt install -y git

# Install Python and pip
sudo apt install -y python3 python3-pip

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

##### CentOS/RHEL
```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Install Git
sudo yum install -y git

# Install Python and pip
sudo yum install -y python3 python3-pip

# Install Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

##### macOS
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Install Git
brew install git

# Install Python
brew install python@3.11

# Install Node.js
brew install node

# Install kubectl
brew install kubectl

# Install Helm (optional)
brew install helm
```

## Step 1: Project Setup

### 1.1 Clone Repository
```bash
# Clone the repository
git clone https://github.com/your-org/splunk-mcp-integration.git
cd splunk-mcp-integration

# Verify repository structure
ls -la
```

### 1.2 Create Environment Configuration
```bash
# Create environment file from template
cp .env.example .env

# Create setup directories
mkdir -p logs validation-reports backups
```

### 1.3 Install Python Dependencies for Setup Scripts
```bash
# Install setup and validation dependencies
pip3 install -r requirements-setup.txt

# If requirements-setup.txt doesn't exist, install manually:
pip3 install aiohttp asyncpg aioredis pyyaml requests openai anthropic
```

## Step 2: Credentials and Security Setup

### 2.1 Generate Security Keys
```bash
# Generate JWT secret key
JWT_SECRET=$(openssl rand -base64 32)
echo "JWT_SECRET_KEY=$JWT_SECRET" >> .env

# Generate database passwords
DB_PASSWORD=$(openssl rand -base64 16)
REDIS_PASSWORD=$(openssl rand -base64 16)

echo "POSTGRES_PASSWORD=$DB_PASSWORD" >> .env
echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> .env
```

### 2.2 Configure Environment Variables
```bash
# Edit the .env file with your specific configuration
vi .env

# Essential variables to configure:
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=splunk_mcp
POSTGRES_USER=splunk_mcp_user
POSTGRES_PASSWORD=your_generated_password

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_generated_password

SPLUNK_HOST=your-splunk-server.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=splunk_mcp_service
SPLUNK_PASSWORD=your_splunk_password
SPLUNK_SCHEME=https

OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here

JWT_SECRET_KEY=your_generated_jwt_secret
```

### 2.3 Set Up API Keys

#### OpenAI API Key
```bash
# Follow the guide in docs/setup/CREDENTIALS_SETUP.md
# 1. Create account at https://platform.openai.com/
# 2. Generate API key
# 3. Add to .env file

# Test API key
python3 -c "
import openai
import os
openai.api_key = os.getenv('OPENAI_API_KEY')
print('OpenAI API Key:', '✅ Valid' if openai.Model.list() else '❌ Invalid')
"
```

#### Anthropic API Key
```bash
# Follow the guide in docs/setup/CREDENTIALS_SETUP.md
# 1. Create account at https://console.anthropic.com/
# 2. Generate API key
# 3. Add to .env file

# Test API key (requires anthropic package)
python3 -c "
import anthropic
import os
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
try:
    response = client.messages.create(model='claude-3-sonnet-20240229', max_tokens=10, messages=[{'role': 'user', 'content': 'test'}])
    print('Anthropic API Key: ✅ Valid')
except:
    print('Anthropic API Key: ❌ Invalid')
"
```

## Step 3: Splunk Configuration

### 3.1 Configure Splunk Enterprise/Cloud
```bash
# Follow the detailed guide in docs/setup/SPLUNK_SETUP.md
# Key steps:
# 1. Enable REST API on port 8089
# 2. Create service user: splunk_mcp_service
# 3. Configure appropriate permissions
# 4. Test connectivity

# Quick test script
python3 scripts/validate-splunk-config.py
```

### 3.2 Test Splunk Connection
```bash
# Test basic connectivity
curl -k -u $SPLUNK_USERNAME:$SPLUNK_PASSWORD \
  "$SPLUNK_SCHEME://$SPLUNK_HOST:$SPLUNK_PORT/services/server/info"

# Test search capability
curl -k -u $SPLUNK_USERNAME:$SPLUNK_PASSWORD \
  -d "search=search index=_internal | head 5" \
  "$SPLUNK_SCHEME://$SPLUNK_HOST:$SPLUNK_PORT/services/search/jobs"
```

## Step 4: Development Deployment (Docker Compose)

### 4.1 Build and Start Services
```bash
# Build all Docker images
make build

# Start infrastructure services first
docker-compose up -d postgres redis

# Wait for databases to be ready
echo "Waiting for databases to start..."
sleep 30

# Check database health
docker-compose exec postgres pg_isready -U splunk_mcp_user
docker-compose exec redis redis-cli ping
```

### 4.2 Initialize Database
```bash
# Run database migrations
docker-compose run --rm api-gateway python -m alembic upgrade head

# Create initial admin user (optional)
docker-compose run --rm api-gateway python scripts/create_admin_user.py \
  --username admin \
  --email admin@yourcompany.com \
  --password AdminPassword123!
```

### 4.3 Start All Services
```bash
# Start all application services
docker-compose up -d

# Check service status
docker-compose ps

# View service logs
docker-compose logs -f api-gateway nlp-engine visualization
```

### 4.4 Verify Development Deployment
```bash
# Test all service health endpoints
make health

# Or test individually:
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # NLP Engine
curl http://localhost:8002/health  # Visualization
curl http://localhost:8003/health  # Alert Manager

# Test frontend
curl http://localhost:3000
```

## Step 5: Production Deployment (Kubernetes)

### 5.1 Prepare Kubernetes Cluster
```bash
# Verify kubectl connectivity
kubectl cluster-info

# Create namespace
kubectl create namespace splunk-mcp-prod

# Set default namespace
kubectl config set-context --current --namespace=splunk-mcp-prod
```

### 5.2 Create Kubernetes Secrets
```bash
# Create database secret
kubectl create secret generic database-secret \
  --from-literal=host=postgres-service \
  --from-literal=port=5432 \
  --from-literal=database=splunk_mcp \
  --from-literal=username=splunk_mcp_user \
  --from-literal=password="$POSTGRES_PASSWORD"

# Create Redis secret
kubectl create secret generic redis-secret \
  --from-literal=host=redis-service \
  --from-literal=port=6379 \
  --from-literal=password="$REDIS_PASSWORD"

# Create API keys secret
kubectl create secret generic api-keys \
  --from-literal=openai-api-key="$OPENAI_API_KEY" \
  --from-literal=anthropic-api-key="$ANTHROPIC_API_KEY" \
  --from-literal=jwt-secret="$JWT_SECRET_KEY"

# Create Splunk connection secret
kubectl create secret generic splunk-config \
  --from-literal=host="$SPLUNK_HOST" \
  --from-literal=port="$SPLUNK_PORT" \
  --from-literal=username="$SPLUNK_USERNAME" \
  --from-literal=password="$SPLUNK_PASSWORD" \
  --from-literal=scheme="$SPLUNK_SCHEME"
```

### 5.3 Deploy Infrastructure Services
```bash
# Deploy PostgreSQL
kubectl apply -f infrastructure/kubernetes/storage/postgres-storage.yaml
kubectl apply -f infrastructure/kubernetes/deployments/postgres-deployment.yaml
kubectl apply -f infrastructure/kubernetes/services/postgres-service.yaml

# Deploy Redis
kubectl apply -f infrastructure/kubernetes/storage/redis-storage.yaml
kubectl apply -f infrastructure/kubernetes/deployments/redis-deployment.yaml
kubectl apply -f infrastructure/kubernetes/services/redis-service.yaml

# Wait for infrastructure to be ready
kubectl wait --for=condition=Ready pod -l app=postgres --timeout=300s
kubectl wait --for=condition=Ready pod -l app=redis --timeout=300s
```

### 5.4 Initialize Production Database
```bash
# Run database migrations in Kubernetes
kubectl run migration-job --image=splunk-mcp/api-gateway:latest \
  --restart=Never \
  --rm -i --tty \
  --env-from=secretRef:database-secret \
  -- python -m alembic upgrade head

# Verify migration
kubectl logs migration-job
```

### 5.5 Deploy Application Services
```bash
# Deploy core services
kubectl apply -f infrastructure/kubernetes/deployments/api-gateway-deployment.yaml
kubectl apply -f infrastructure/kubernetes/services/api-gateway-service.yaml

kubectl apply -f infrastructure/kubernetes/deployments/nlp-engine-deployment.yaml
kubectl apply -f infrastructure/kubernetes/services/nlp-engine-service.yaml

kubectl apply -f infrastructure/kubernetes/deployments/visualization-deployment.yaml
kubectl apply -f infrastructure/kubernetes/services/visualization-service.yaml

kubectl apply -f infrastructure/kubernetes/deployments/alert-manager-deployment.yaml
kubectl apply -f infrastructure/kubernetes/services/alert-manager-service.yaml

# Deploy frontend
kubectl apply -f infrastructure/kubernetes/deployments/frontend-deployment.yaml
kubectl apply -f infrastructure/kubernetes/services/frontend-service.yaml

# Wait for deployments to be ready
kubectl wait --for=condition=Available deployment --all --timeout=600s
```

### 5.6 Configure Ingress and SSL
```bash
# Install NGINX Ingress Controller (if not already installed)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Install cert-manager for SSL certificates
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=Available deployment -l app.kubernetes.io/name=cert-manager --timeout=300s -n cert-manager

# Create cluster issuer for Let's Encrypt
kubectl apply -f infrastructure/kubernetes/ingress/cluster-issuer.yaml

# Deploy main ingress with SSL
kubectl apply -f infrastructure/kubernetes/ingress/main-ingress.yaml
```

### 5.7 Configure Auto-scaling
```bash
# Deploy Horizontal Pod Autoscalers
kubectl apply -f infrastructure/kubernetes/hpa/api-gateway-hpa.yaml
kubectl apply -f infrastructure/kubernetes/hpa/nlp-engine-hpa.yaml
kubectl apply -f infrastructure/kubernetes/hpa/visualization-hpa.yaml
kubectl apply -f infrastructure/kubernetes/hpa/alert-manager-hpa.yaml

# Verify HPA configuration
kubectl get hpa
```

## Step 6: Validation and Testing

### 6.1 Run Production Readiness Validation
```bash
# Run comprehensive validation
./scripts/run-validation.sh --env production --verbose

# Check validation results
cat validation-reports/production-readiness-report-production-*.json
```

### 6.2 Run Integration Tests
```bash
# Test end-to-end functionality
cd tests/integration
python test_runner.py --env production

# Run performance tests
cd tests/performance
python locustfile.py --host https://your-domain.com
```

### 6.3 Verify All Services
```bash
# For Docker Compose deployment
make health

# For Kubernetes deployment
kubectl get pods
kubectl get services
kubectl get ingress

# Test external access
curl https://your-domain.com/health
curl https://api.your-domain.com/health
```

## Step 7: Monitoring and Observability

### 7.1 Deploy Monitoring Stack
```bash
# Add Prometheus Community Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install monitoring stack
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values infrastructure/monitoring/prometheus-values.yaml

# Deploy custom ServiceMonitors
kubectl apply -f infrastructure/monitoring/servicemonitor.yaml
```

### 7.2 Configure Grafana Dashboards
```bash
# Access Grafana
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80

# Import custom dashboards
kubectl apply -f infrastructure/monitoring/grafana-dashboards.yaml
```

### 7.3 Set Up Alerting
```bash
# Configure AlertManager
kubectl apply -f infrastructure/monitoring/alertmanager-config.yaml

# Deploy custom alert rules
kubectl apply -f infrastructure/monitoring/alert-rules.yaml
```

## Step 8: Security Hardening

### 8.1 Network Security
```bash
# Apply network policies
kubectl apply -f infrastructure/kubernetes/network-policies/

# Verify network policies
kubectl get networkpolicies
```

### 8.2 RBAC Configuration
```bash
# Apply RBAC policies
kubectl apply -f infrastructure/kubernetes/rbac/

# Verify RBAC
kubectl get roles,rolebindings,clusterroles,clusterrolebindings
```

### 8.3 Security Scanning
```bash
# Run security validation
python scripts/security-scan.py --target production

# Check for vulnerabilities
make security-scan
```

## Step 9: Backup and Disaster Recovery

### 9.1 Configure Database Backups
```bash
# Set up automated PostgreSQL backups
kubectl apply -f infrastructure/kubernetes/backup/postgres-backup-cronjob.yaml

# Verify backup job
kubectl get cronjobs -n backups
```

### 9.2 Configure Application Backups
```bash
# Backup Kubernetes resources
kubectl get all -o yaml > backups/kubernetes-resources-$(date +%Y%m%d).yaml

# Create backup script
cp scripts/backup-production.sh /usr/local/bin/
chmod +x /usr/local/bin/backup-production.sh

# Schedule regular backups
echo "0 2 * * * /usr/local/bin/backup-production.sh" | crontab -
```

## Step 10: Operational Procedures

### 10.1 Health Monitoring
```bash
# Set up continuous health monitoring
python scripts/continuous-health-monitor.py --interval 60 &

# Create health check dashboard
kubectl apply -f infrastructure/monitoring/health-dashboard.yaml
```

### 10.2 Log Management
```bash
# Deploy centralized logging
helm install logging elastic/eck-operator \
  --namespace logging \
  --create-namespace

# Configure log forwarding
kubectl apply -f infrastructure/logging/filebeat-config.yaml
```

### 10.3 Maintenance Procedures
```bash
# Create maintenance scripts
cp scripts/maintenance/ /opt/splunk-mcp-maintenance/
chmod +x /opt/splunk-mcp-maintenance/*.sh

# Schedule regular maintenance
echo "0 3 * * 0 /opt/splunk-mcp-maintenance/weekly-maintenance.sh" | crontab -
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Service Startup Failures
```bash
# Check pod status
kubectl get pods
kubectl describe pod <failing-pod>

# Check logs
kubectl logs <failing-pod> --previous

# Common fixes:
# - Check resource limits
# - Verify secret configurations
# - Check image availability
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
kubectl exec -it <api-gateway-pod> -- python -c "
import asyncpg
import asyncio
import os

async def test_db():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    result = await conn.fetchval('SELECT version()')
    print(f'Database version: {result}')
    await conn.close()

asyncio.run(test_db())
"
```

#### 3. SSL Certificate Issues
```bash
# Check certificate status
kubectl describe certificate splunk-mcp-tls

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Force certificate renewal
kubectl delete secret splunk-mcp-tls
kubectl apply -f infrastructure/kubernetes/ingress/main-ingress.yaml
```

#### 4. Performance Issues
```bash
# Check resource usage
kubectl top pods
kubectl top nodes

# Check HPA status
kubectl describe hpa

# Scale manually if needed
kubectl scale deployment api-gateway --replicas=5
```

#### 5. Splunk Connectivity Issues
```bash
# Test Splunk connection from pod
kubectl exec -it <api-gateway-pod> -- python scripts/validate-splunk-config.py

# Check Splunk server logs
# (On Splunk server)
tail -f /opt/splunk/var/log/splunk/splunkd.log
```

## Post-Deployment Checklist

### Verification Steps
- [ ] All services are running and healthy
- [ ] Database migrations completed successfully
- [ ] Splunk connectivity verified
- [ ] API endpoints accessible and responding
- [ ] Frontend loading correctly
- [ ] SSL certificates installed and valid
- [ ] Monitoring and alerting configured
- [ ] Backup procedures tested
- [ ] Security policies applied
- [ ] Performance tests passed
- [ ] Documentation updated

### Configuration Validation
```bash
# Run complete validation suite
./scripts/run-validation.sh --env production --comprehensive

# Generate deployment report
python scripts/generate-deployment-report.py --output deployment-report.html

# Verify all integrations
python scripts/integration-test-suite.py --full-suite
```

## Next Steps

### 1. User Training and Onboarding
- Set up user accounts and permissions
- Conduct training sessions
- Create user documentation
- Establish support procedures

### 2. Ongoing Maintenance
- Monitor system performance and usage
- Apply security updates regularly
- Review and update configurations
- Conduct regular backup tests

### 3. Scaling and Optimization
- Monitor resource usage and scale as needed
- Optimize database queries and indexing
- Review and tune performance settings
- Plan for capacity growth

---

**Support**: For issues or questions, refer to the troubleshooting sections in individual service documentation or create an issue in the project repository.

**Documentation**: Complete documentation is available in the `docs/` directory, including API references, user guides, and operational procedures.