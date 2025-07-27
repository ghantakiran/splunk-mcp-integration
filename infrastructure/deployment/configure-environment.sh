#!/bin/bash
# Environment Configuration Script for Splunk MCP Platform
# ========================================================
# Automates environment-specific configuration setup

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
ENVIRONMENT="production"
NAMESPACE="splunk-mcp-prod"
CONFIG_FILE=""
SECRETS_FILE=""
DRY_RUN=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
info() { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
debug() { [[ "$VERBOSE" == "true" ]] && echo -e "[DEBUG] $*"; }

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Environment configuration script for Splunk MCP Integration Platform

OPTIONS:
    -h, --help                  Show this help message
    -e, --environment ENV       Target environment (production|staging|development)
    -n, --namespace NAME        Kubernetes namespace [default: splunk-mcp-prod]
    -c, --config-file FILE      Environment configuration file
    -s, --secrets-file FILE     Secrets configuration file
    --dry-run                   Show what would be configured without executing
    -v, --verbose               Enable verbose logging

EXAMPLES:
    # Configure production environment
    $0 --environment production --config-file prod.env

    # Configure with custom secrets
    $0 -e staging -c staging.env -s staging.secrets

    # Dry run for production
    $0 --dry-run --environment production

CONFIGURATION FILES:
    Config files should contain environment variables in KEY=VALUE format.
    Secrets files should contain sensitive values that will be stored in Kubernetes secrets.

    Example config file (prod.env):
    ENVIRONMENT=production
    LOG_LEVEL=INFO
    CORS_ORIGINS=["https://splunk-mcp.company.com"]
    RATE_LIMITING_ENABLED=true

    Example secrets file (prod.secrets):
    DATABASE_URL=postgresql://user:password@postgres:5432/splunk_mcp
    JWT_SECRET_KEY=your-secure-jwt-secret
    OPENAI_API_KEY=your-openai-api-key
    ANTHROPIC_API_KEY=your-anthropic-api-key

EOF
}

# Function to generate default configuration
generate_default_config() {
    local env="$1"
    local config_file="$2"
    
    info "Generating default configuration for $env environment..."
    
    cat > "$config_file" << EOF
# Splunk MCP Platform Configuration - $env Environment
# Generated: $(date)

# Core Configuration
ENVIRONMENT=$env
LOG_LEVEL=INFO
DEBUG_MODE=false

# Security Configuration
CORS_ORIGINS=["https://splunk-mcp.company.com"]
SECURITY_HEADERS_ENABLED=true
RATE_LIMITING_ENABLED=true
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
MAX_QUERY_RESULTS=10000
QUERY_TIMEOUT_SECONDS=300
CACHE_TTL_SECONDS=3600
MAX_CONTEXT_LENGTH=8000

# Splunk Configuration
SPLUNK_HOST=splunk.company.com
SPLUNK_PORT=8089
SPLUNK_USE_SSL=true

# Email Configuration (if using email service)
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USE_TLS=true

# Monitoring Configuration
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
LOG_CORRELATION_ENABLED=true

# Performance Configuration
WORKER_PROCESSES=4
MAX_CONNECTIONS=100
CONNECTION_POOL_SIZE=20
CONNECTION_POOL_MAX_OVERFLOW=10

EOF

    success "Default configuration generated: $config_file"
}

# Function to generate default secrets template
generate_default_secrets() {
    local env="$1"
    local secrets_file="$2"
    
    info "Generating secrets template for $env environment..."
    
    cat > "$secrets_file" << EOF
# Splunk MCP Platform Secrets - $env Environment
# Generated: $(date)
# WARNING: This file contains sensitive information - do not commit to version control

# Database Configuration
DATABASE_URL=postgresql://splunk_user:CHANGE_ME@postgres.company.com:5432/splunk_mcp
REDIS_URL=redis://redis.company.com:6379

# Authentication Secrets
JWT_SECRET_KEY=$(openssl rand -base64 32)
SESSION_SECRET_KEY=$(openssl rand -base64 32)

# AI Service API Keys
OPENAI_API_KEY=sk-CHANGE_ME
ANTHROPIC_API_KEY=sk-ant-CHANGE_ME

# Splunk Credentials
SPLUNK_USERNAME=splunk_service_account
SPLUNK_PASSWORD=CHANGE_ME

# Email Service Credentials
SMTP_USERNAME=alerts@company.com
SMTP_PASSWORD=CHANGE_ME

# Integration API Keys
SLACK_BOT_TOKEN=xoxb-CHANGE_ME
SLACK_SIGNING_SECRET=CHANGE_ME
TEAMS_APP_ID=CHANGE_ME
TEAMS_APP_PASSWORD=CHANGE_ME

# External Service Credentials
WEBHOOK_SECRET_KEY=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)

# Monitoring Credentials
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)
PROMETHEUS_AUTH_TOKEN=$(openssl rand -base64 32)

EOF

    success "Secrets template generated: $secrets_file"
    warning "Please update all CHANGE_ME values with actual credentials"
}

# Function to validate configuration
validate_config() {
    local config_file="$1"
    
    info "Validating configuration file: $config_file"
    
    if [[ ! -f "$config_file" ]]; then
        error "Configuration file not found: $config_file"
        return 1
    fi
    
    # Check for required variables
    local required_vars=(
        "ENVIRONMENT"
        "LOG_LEVEL"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$config_file"; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required configuration variables: ${missing_vars[*]}"
        return 1
    fi
    
    success "Configuration validation passed"
}

# Function to validate secrets
validate_secrets() {
    local secrets_file="$1"
    
    info "Validating secrets file: $secrets_file"
    
    if [[ ! -f "$secrets_file" ]]; then
        error "Secrets file not found: $secrets_file"
        return 1
    fi
    
    # Check for placeholder values that need to be changed
    local placeholder_count=$(grep -c "CHANGE_ME" "$secrets_file" 2>/dev/null || echo 0)
    
    if [[ $placeholder_count -gt 0 ]]; then
        warning "Found $placeholder_count placeholder values (CHANGE_ME) in secrets file"
        warning "Please update these values before production deployment"
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            error "Production deployment requires all secrets to be configured"
            return 1
        fi
    fi
    
    # Check for required secrets
    local required_secrets=(
        "DATABASE_URL"
        "REDIS_URL"
        "JWT_SECRET_KEY"
    )
    
    local missing_secrets=()
    
    for secret in "${required_secrets[@]}"; do
        if ! grep -q "^${secret}=" "$secrets_file"; then
            missing_secrets+=("$secret")
        fi
    done
    
    if [[ ${#missing_secrets[@]} -gt 0 ]]; then
        error "Missing required secrets: ${missing_secrets[*]}"
        return 1
    fi
    
    success "Secrets validation passed"
}

# Function to create Kubernetes ConfigMap
create_configmap() {
    local config_file="$1"
    local configmap_name="splunk-mcp-config"
    
    info "Creating ConfigMap: $configmap_name"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        debug "DRY RUN: Would create ConfigMap from $config_file"
        return 0
    fi
    
    # Create ConfigMap from environment file
    kubectl create configmap "$configmap_name" \
        --from-env-file="$config_file" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Label the ConfigMap
    kubectl label configmap "$configmap_name" \
        app.kubernetes.io/name=splunk-mcp \
        app.kubernetes.io/component=config \
        environment="$ENVIRONMENT" \
        --namespace="$NAMESPACE" \
        --overwrite
    
    success "ConfigMap created: $configmap_name"
}

# Function to create Kubernetes Secrets
create_secrets() {
    local secrets_file="$1"
    local secret_name="splunk-mcp-secrets"
    
    info "Creating Secret: $secret_name"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        debug "DRY RUN: Would create Secret from $secrets_file"
        return 0
    fi
    
    # Create Secret from environment file
    kubectl create secret generic "$secret_name" \
        --from-env-file="$secrets_file" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Label the Secret
    kubectl label secret "$secret_name" \
        app.kubernetes.io/name=splunk-mcp \
        app.kubernetes.io/component=secrets \
        environment="$ENVIRONMENT" \
        --namespace="$NAMESPACE" \
        --overwrite
    
    success "Secret created: $secret_name"
}

# Function to create additional monitoring secrets
create_monitoring_secrets() {
    info "Creating monitoring secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        debug "DRY RUN: Would create monitoring secrets"
        return 0
    fi
    
    # Create Grafana admin secret
    local grafana_password=$(openssl rand -base64 16)
    kubectl create secret generic grafana-admin \
        --from-literal=admin-user=admin \
        --from-literal=admin-password="$grafana_password" \
        --namespace=monitoring \
        --dry-run=client -o yaml | kubectl apply -f -
    
    success "Monitoring secrets created"
    info "Grafana admin password: $grafana_password"
}

# Function to verify deployment
verify_configuration() {
    info "Verifying configuration deployment..."
    
    # Check ConfigMap
    if kubectl get configmap splunk-mcp-config -n "$NAMESPACE" &>/dev/null; then
        success "ConfigMap verified"
        debug "ConfigMap keys: $(kubectl get configmap splunk-mcp-config -n "$NAMESPACE" -o jsonpath='{.data}' | jq -r 'keys[]' 2>/dev/null || echo 'N/A')"
    else
        error "ConfigMap not found"
    fi
    
    # Check Secret
    if kubectl get secret splunk-mcp-secrets -n "$NAMESPACE" &>/dev/null; then
        success "Secret verified"
        debug "Secret keys: $(kubectl get secret splunk-mcp-secrets -n "$NAMESPACE" -o jsonpath='{.data}' | jq -r 'keys[]' 2>/dev/null || echo 'N/A')"
    else
        error "Secret not found"
    fi
}

# Function to generate environment-specific deployment patches
generate_deployment_patches() {
    local patch_dir="$PROJECT_ROOT/infrastructure/kubernetes/overlays/$ENVIRONMENT"
    
    info "Generating deployment patches for $ENVIRONMENT..."
    
    mkdir -p "$patch_dir"
    
    # Create kustomization.yaml
    cat > "$patch_dir/kustomization.yaml" << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: $NAMESPACE

resources:
  - ../../base

configMapGenerator:
  - name: splunk-mcp-config
    envs:
      - config.env

secretGenerator:
  - name: splunk-mcp-secrets
    envs:
      - secrets.env

images:
  - name: splunk-mcp/api-gateway
    newTag: $ENVIRONMENT
  - name: splunk-mcp/nlp-engine  
    newTag: $ENVIRONMENT
  - name: splunk-mcp/visualization
    newTag: $ENVIRONMENT

patchesStrategicMerge:
  - resource-limits.yaml

EOF

    # Create resource limits patch
    cat > "$patch_dir/resource-limits.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  template:
    spec:
      containers:
      - name: api-gateway
        resources:
          requests:
            memory: "${API_GATEWAY_MEMORY_REQUEST:-512Mi}"
            cpu: "${API_GATEWAY_CPU_REQUEST:-500m}"
          limits:
            memory: "${API_GATEWAY_MEMORY_LIMIT:-1Gi}"
            cpu: "${API_GATEWAY_CPU_LIMIT:-1000m}"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nlp-engine
spec:
  template:
    spec:
      containers:
      - name: nlp-engine
        resources:
          requests:
            memory: "${NLP_ENGINE_MEMORY_REQUEST:-1Gi}"
            cpu: "${NLP_ENGINE_CPU_REQUEST:-1000m}"
          limits:
            memory: "${NLP_ENGINE_MEMORY_LIMIT:-2Gi}"
            cpu: "${NLP_ENGINE_CPU_LIMIT:-2000m}"

EOF

    success "Deployment patches generated in: $patch_dir"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -c|--config-file)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -s|--secrets-file)
            SECRETS_FILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main configuration function
main() {
    info "Starting environment configuration for: $ENVIRONMENT"
    info "Target namespace: $NAMESPACE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        warning "DRY RUN MODE - No changes will be made"
    fi
    
    # Set default file names if not provided
    if [[ -z "$CONFIG_FILE" ]]; then
        CONFIG_FILE="$SCRIPT_DIR/${ENVIRONMENT}.env"
    fi
    
    if [[ -z "$SECRETS_FILE" ]]; then
        SECRETS_FILE="$SCRIPT_DIR/${ENVIRONMENT}.secrets"
    fi
    
    # Generate default files if they don't exist
    if [[ ! -f "$CONFIG_FILE" ]]; then
        warning "Configuration file not found, generating default: $CONFIG_FILE"
        generate_default_config "$ENVIRONMENT" "$CONFIG_FILE"
    fi
    
    if [[ ! -f "$SECRETS_FILE" ]]; then
        warning "Secrets file not found, generating template: $SECRETS_FILE"
        generate_default_secrets "$ENVIRONMENT" "$SECRETS_FILE"
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            error "Please configure all secrets before running in production"
            exit 1
        fi
    fi
    
    # Validate configuration and secrets
    validate_config "$CONFIG_FILE"
    validate_secrets "$SECRETS_FILE"
    
    # Create Kubernetes resources
    create_configmap "$CONFIG_FILE"
    create_secrets "$SECRETS_FILE"
    create_monitoring_secrets
    
    # Generate deployment patches
    generate_deployment_patches
    
    # Verify configuration
    verify_configuration
    
    success "Environment configuration completed successfully!"
    info "ConfigMap: splunk-mcp-config"
    info "Secret: splunk-mcp-secrets"
    info "Files: $CONFIG_FILE, $SECRETS_FILE"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    error "kubectl is required but not installed"
    exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    error "Cannot connect to Kubernetes cluster"
    exit 1
fi

# Run main function
main "$@"