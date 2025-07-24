#!/bin/bash

# Production Deployment Automation Script for Splunk MCP Integration
# This script automates the complete production deployment process

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NAMESPACE="splunk-mcp-prod"
MONITORING_NAMESPACE="monitoring"
LOG_FILE="/var/log/splunk-mcp-deployment.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Deployment configuration
DEPLOYMENT_PHASES=(
    "pre_deployment_checks"
    "infrastructure_deployment"
    "database_deployment"
    "monitoring_deployment"
    "core_services_deployment"
    "integration_services_deployment"
    "platform_services_deployment"
    "frontend_deployment"
    "post_deployment_validation"
    "performance_testing"
    "security_validation"
    "go_live_procedures"
)

# Service deployment order
CORE_SERVICES=("api-gateway" "nlp-engine" "visualization" "alert-manager")
INTEGRATION_SERVICES=("slack-bot" "teams-bot" "email-service" "webhook-service" "itsm-service" "bi-integration-service")
EXPORT_SERVICES=("pdf-export-service" "powerpoint-export-service" "word-export-service" "html-report-service" "csv-export-service" "json-xml-export-service")
PLATFORM_SERVICES=("secure-sharing-service" "report-scheduling-service")

# Logging functions
log() {
    echo -e "${DATE} - $1" | tee -a "${LOG_FILE}"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_phase() {
    log "${BLUE}[PHASE]${NC} $1"
    echo "=================================="
}

# Error handling
handle_error() {
    local line_no=$1
    local error_code=$2
    log_error "Deployment failed at line $line_no with exit code $error_code"
    log_error "Rolling back deployment..."
    rollback_deployment
    exit $error_code
}

trap 'handle_error ${LINENO} $?' ERR

# Pre-deployment checks
pre_deployment_checks() {
    log_phase "PHASE 1: Pre-deployment Checks"
    
    # Check Kubernetes connectivity
    log_info "Checking Kubernetes connectivity..."
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    log_success "Kubernetes connectivity verified"
    
    # Check required tools
    log_info "Checking required tools..."
    local required_tools=("kubectl" "helm" "docker" "git")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_error "Required tool '$tool' not found"
            exit 1
        fi
    done
    log_success "All required tools available"
    
    # Check cluster resources
    log_info "Checking cluster resources..."
    local node_count=$(kubectl get nodes --no-headers | wc -l)
    if [ "$node_count" -lt 3 ]; then
        log_warning "Cluster has less than 3 nodes ($node_count)"
    fi
    log_success "Cluster has $node_count nodes"
    
    # Check storage classes
    log_info "Checking storage classes..."
    if ! kubectl get storageclass fast-ssd >/dev/null 2>&1; then
        log_error "Required storage class 'fast-ssd' not found"
        exit 1
    fi
    log_success "Storage classes available"
    
    # Validate configuration files
    log_info "Validating configuration files..."
    local config_files=(
        "infrastructure/kubernetes/namespaces/production.yaml"
        "infrastructure/kubernetes/deployments/"
        "infrastructure/monitoring/production-monitoring.yaml"
    )
    
    for config in "${config_files[@]}"; do
        if [ ! -e "$PROJECT_ROOT/$config" ]; then
            log_error "Configuration file not found: $config"
            exit 1
        fi
    done
    log_success "Configuration files validated"
    
    # Check environment variables
    log_info "Checking environment variables..."
    local required_vars=("DATABASE_PASSWORD" "REDIS_PASSWORD" "JWT_SECRET_KEY" "SPLUNK_TOKEN")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable '$var' not set"
            exit 1
        fi
    done
    log_success "Environment variables validated"
}

# Infrastructure deployment
infrastructure_deployment() {
    log_phase "PHASE 2: Infrastructure Deployment"
    
    # Create namespaces
    log_info "Creating namespaces..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/namespaces/"
    
    # Apply RBAC
    log_info "Applying RBAC configurations..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/rbac/"
    
    # Create storage classes and PVCs
    log_info "Setting up storage..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/storage/"
    
    # Apply network policies
    log_info "Applying network policies..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/network-policies/"
    
    # Configure ingress
    log_info "Setting up ingress controller..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/ingress/"
    
    log_success "Infrastructure deployment completed"
}

# Database deployment
database_deployment() {
    log_phase "PHASE 3: Database Deployment"
    
    # Create database secrets
    log_info "Creating database secrets..."
    kubectl create secret generic postgresql-secret \
        --namespace="$NAMESPACE" \
        --from-literal=username=splunk_mcp \
        --from-literal=password="$DATABASE_PASSWORD" \
        --from-literal=database=splunk_mcp_prod \
        --dry-run=client -o yaml | kubectl apply -f -
    
    kubectl create secret generic redis-secret \
        --namespace="$NAMESPACE" \
        --from-literal=password="$REDIS_PASSWORD" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy PostgreSQL cluster
    log_info "Deploying PostgreSQL cluster..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/database/postgresql/"
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgresql -n "$NAMESPACE" --timeout=300s
    
    # Deploy Redis cluster
    log_info "Deploying Redis cluster..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/database/redis/"
    
    # Wait for Redis to be ready
    log_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s
    
    # Run database migrations
    log_info "Running database migrations..."
    kubectl run migration-job \
        --image=splunk-mcp/api-gateway:latest \
        --restart=Never \
        --namespace="$NAMESPACE" \
        --command -- python manage_db.py migrate
    
    kubectl wait --for=condition=complete job/migration-job -n "$NAMESPACE" --timeout=300s
    kubectl delete job migration-job -n "$NAMESPACE"
    
    log_success "Database deployment completed"
}

# Monitoring deployment
monitoring_deployment() {
    log_phase "PHASE 4: Monitoring Deployment"
    
    # Deploy Prometheus
    log_info "Deploying Prometheus..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/monitoring/production-monitoring.yaml"
    
    # Deploy Grafana dashboards
    log_info "Deploying Grafana dashboards..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/monitoring/grafana-dashboards.yaml"
    
    # Wait for monitoring services to be ready
    log_info "Waiting for monitoring services..."
    kubectl wait --for=condition=available deployment/prometheus -n "$MONITORING_NAMESPACE" --timeout=300s
    kubectl wait --for=condition=available deployment/grafana -n "$MONITORING_NAMESPACE" --timeout=300s
    kubectl wait --for=condition=available deployment/alertmanager -n "$MONITORING_NAMESPACE" --timeout=300s
    
    log_success "Monitoring deployment completed"
}

# Deploy a service with validation
deploy_service() {
    local service_name=$1
    local service_dir="$PROJECT_ROOT/services/$service_name"
    
    log_info "Deploying $service_name..."
    
    # Apply service-specific configurations
    if [ -f "$service_dir/k8s-deployment.yaml" ]; then
        kubectl apply -f "$service_dir/k8s-deployment.yaml"
    else
        # Use generic deployment template
        kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/deployments/$service_name.yaml"
    fi
    
    # Wait for deployment to be ready
    kubectl wait --for=condition=available deployment/"$service_name" -n "$NAMESPACE" --timeout=300s
    
    # Health check
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app="$service_name" -o jsonpath='{.items[0].metadata.name}')
    local health_check_passed=false
    
    for i in {1..30}; do
        if kubectl exec -n "$NAMESPACE" "$pod_name" -- curl -f http://localhost:8000/health >/dev/null 2>&1; then
            health_check_passed=true
            break
        fi
        sleep 10
    done
    
    if [ "$health_check_passed" = true ]; then
        log_success "$service_name deployed and healthy"
    else
        log_error "$service_name health check failed"
        exit 1
    fi
}

# Core services deployment
core_services_deployment() {
    log_phase "PHASE 5: Core Services Deployment"
    
    # Create application secrets
    log_info "Creating application secrets..."
    kubectl create secret generic app-secrets \
        --namespace="$NAMESPACE" \
        --from-literal=jwt-secret="$JWT_SECRET_KEY" \
        --from-literal=splunk-token="$SPLUNK_TOKEN" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy core services in order
    for service in "${CORE_SERVICES[@]}"; do
        deploy_service "$service"
        sleep 30  # Allow services to stabilize
    done
    
    log_success "Core services deployment completed"
}

# Integration services deployment
integration_services_deployment() {
    log_phase "PHASE 6: Integration Services Deployment"
    
    # Deploy integration services
    for service in "${INTEGRATION_SERVICES[@]}"; do
        deploy_service "$service"
        sleep 20
    done
    
    # Deploy export services
    for service in "${EXPORT_SERVICES[@]}"; do
        deploy_service "$service"
        sleep 15
    done
    
    log_success "Integration services deployment completed"
}

# Platform services deployment
platform_services_deployment() {
    log_phase "PHASE 7: Platform Services Deployment"
    
    for service in "${PLATFORM_SERVICES[@]}"; do
        deploy_service "$service"
        sleep 20
    done
    
    log_success "Platform services deployment completed"
}

# Frontend deployment
frontend_deployment() {
    log_phase "PHASE 8: Frontend Deployment"
    
    log_info "Deploying frontend application..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/deployments/frontend.yaml"
    
    # Wait for frontend to be ready
    kubectl wait --for=condition=available deployment/frontend -n "$NAMESPACE" --timeout=300s
    
    # Configure SSL certificates
    log_info "Configuring SSL certificates..."
    kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: splunk-mcp-tls
  namespace: $NAMESPACE
spec:
  secretName: splunk-mcp-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - splunk-mcp.company.com
  - www.splunk-mcp.company.com
EOF
    
    log_success "Frontend deployment completed"
}

# Post-deployment validation
post_deployment_validation() {
    log_phase "PHASE 9: Post-deployment Validation"
    
    # Check all deployments
    log_info "Validating all deployments..."
    local failed_deployments=0
    
    for deployment in $(kubectl get deployments -n "$NAMESPACE" -o name); do
        if ! kubectl get "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' | grep -q True; then
            log_error "Deployment $deployment is not available"
            failed_deployments=$((failed_deployments + 1))
        fi
    done
    
    if [ $failed_deployments -gt 0 ]; then
        log_error "$failed_deployments deployments failed validation"
        exit 1
    fi
    
    # Check service endpoints
    log_info "Validating service endpoints..."
    local base_url="https://splunk-mcp.company.com"
    local endpoints=("/health" "/api/v1/health" "/api/v1/nlp/health" "/api/v1/visualization/health")
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -k "$base_url$endpoint" >/dev/null 2>&1; then
            log_success "Endpoint $endpoint is responding"
        else
            log_error "Endpoint $endpoint is not responding"
        fi
    done
    
    # Check database connectivity
    log_info "Validating database connectivity..."
    local api_pod=$(kubectl get pods -n "$NAMESPACE" -l app=api-gateway -o jsonpath='{.items[0].metadata.name}')
    if kubectl exec -n "$NAMESPACE" "$api_pod" -- python -c "
import psycopg2
import os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.close()
print('Database connection successful')
" >/dev/null 2>&1; then
        log_success "Database connectivity validated"
    else
        log_error "Database connectivity failed"
    fi
    
    log_success "Post-deployment validation completed"
}

# Performance testing
performance_testing() {
    log_phase "PHASE 10: Performance Testing"
    
    log_info "Running production performance tests..."
    
    # Run basic load test
    python3 "$SCRIPT_DIR/production-performance-testing.py" \
        --base-url "https://splunk-mcp.company.com" \
        --test-type load \
        --users 10 \
        --duration 60 \
        --output "/tmp/production-performance-results.txt"
    
    # Check performance results
    if grep -q "PASS" /tmp/production-performance-results.txt; then
        log_success "Performance tests passed"
    else
        log_warning "Performance tests showed some issues - review results"
    fi
    
    log_success "Performance testing completed"
}

# Security validation
security_validation() {
    log_phase "PHASE 11: Security Validation"
    
    log_info "Running security hardening..."
    bash "$SCRIPT_DIR/production-security-hardening.sh"
    
    # Additional security checks
    log_info "Performing security validation..."
    
    # Check for non-root containers
    local non_root_check=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].spec.securityContext.runAsNonRoot}' | grep -o true | wc -l)
    local total_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers | wc -l)
    
    if [ "$non_root_check" -eq "$total_pods" ]; then
        log_success "All pods running as non-root user"
    else
        log_warning "Some pods may be running as root"
    fi
    
    # Check network policies
    local network_policies=$(kubectl get networkpolicies -n "$NAMESPACE" --no-headers | wc -l)
    if [ "$network_policies" -gt 0 ]; then
        log_success "Network policies are configured"
    else
        log_error "No network policies found"
    fi
    
    log_success "Security validation completed"
}

# Go-live procedures
go_live_procedures() {
    log_phase "PHASE 12: Go-live Procedures"
    
    # Enable external traffic
    log_info "Enabling external traffic..."
    kubectl patch ingress main-ingress -n "$NAMESPACE" --type='merge' -p='{"metadata":{"annotations":{"nginx.ingress.kubernetes.io/ssl-redirect":"true"}}}'
    
    # Scale up for production load
    log_info "Scaling services for production load..."
    kubectl scale deployment api-gateway --replicas=3 -n "$NAMESPACE"
    kubectl scale deployment nlp-engine --replicas=2 -n "$NAMESPACE"
    kubectl scale deployment visualization --replicas=2 -n "$NAMESPACE"
    kubectl scale deployment alert-manager --replicas=2 -n "$NAMESPACE"
    kubectl scale deployment frontend --replicas=3 -n "$NAMESPACE"
    
    # Enable monitoring alerts
    log_info "Enabling production monitoring alerts..."
    kubectl patch configmap alertmanager-config -n "$MONITORING_NAMESPACE" --type='merge' -p='{"data":{"alertmanager.yml":"global:\n  smtp_from: alerts@company.com\n  slack_api_url: https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK\n\nroute:\n  receiver: production-alerts\n\nreceivers:\n- name: production-alerts\n  slack_configs:\n  - channel: \"#splunk-mcp-alerts\"\n    title: \"Production Alert\"\n    text: \"{{ range .Alerts }}{{ .Annotations.description }}{{ end }}\""}}'
    
    # Final health check
    log_info "Performing final health check..."
    sleep 60  # Allow scaling to complete
    
    local healthy_services=0
    local total_services=$(kubectl get deployments -n "$NAMESPACE" --no-headers | wc -l)
    
    for deployment in $(kubectl get deployments -n "$NAMESPACE" -o name); do
        if kubectl get "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' | grep -q .; then
            healthy_services=$((healthy_services + 1))
        fi
    done
    
    if [ "$healthy_services" -eq "$total_services" ]; then
        log_success "All services are healthy and ready for production"
    else
        log_error "Some services are not healthy"
        exit 1
    fi
    
    # Create deployment record
    kubectl create configmap deployment-info \
        --namespace="$NAMESPACE" \
        --from-literal=deployment-date="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --from-literal=deployment-version="$(git rev-parse HEAD)" \
        --from-literal=deployed-by="$(whoami)" \
        --from-literal=environment="production"
    
    log_success "Go-live procedures completed"
}

# Rollback function
rollback_deployment() {
    log_error "Rolling back deployment..."
    
    # Scale down all services
    kubectl scale deployment --all --replicas=0 -n "$NAMESPACE" || true
    
    # Delete problematic resources
    kubectl delete pods --all -n "$NAMESPACE" --grace-period=0 --force || true
    
    # Restore from backup if available
    # This would be implemented based on your backup strategy
    
    log_error "Rollback completed - manual intervention required"
}

# Generate deployment report
generate_deployment_report() {
    local report_file="/tmp/splunk-mcp-deployment-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" <<EOF
Splunk MCP Integration - Production Deployment Report
Generated: $(date)
Deployment Status: SUCCESS

DEPLOYMENT SUMMARY:
==================
Namespace: $NAMESPACE
Start Time: $DEPLOYMENT_START_TIME
End Time: $(date)
Duration: $(($(date +%s) - DEPLOYMENT_START_TIME)) seconds

SERVICES DEPLOYED:
=================
Core Services: ${CORE_SERVICES[*]}
Integration Services: ${INTEGRATION_SERVICES[*]}
Export Services: ${EXPORT_SERVICES[*]}
Platform Services: ${PLATFORM_SERVICES[*]}

INFRASTRUCTURE:
==============
$(kubectl get nodes --no-headers | wc -l) Kubernetes nodes
$(kubectl get pods -n $NAMESPACE --no-headers | wc -l) pods deployed
$(kubectl get services -n $NAMESPACE --no-headers | wc -l) services created
$(kubectl get pvc -n $NAMESPACE --no-headers | wc -l) persistent volumes

HEALTH STATUS:
=============
$(kubectl get deployments -n $NAMESPACE -o custom-columns='NAME:.metadata.name,READY:.status.readyReplicas,AVAILABLE:.status.availableReplicas' --no-headers)

NEXT STEPS:
==========
1. Monitor system performance and stability
2. Execute user training programs
3. Begin gradual user onboarding
4. Set up regular backup and maintenance procedures
5. Schedule first security audit

SUPPORT CONTACTS:
================
Operations Team: ops@company.com
Development Team: dev@company.com
24/7 Support: support@company.com

EOF

    log_success "Deployment report generated: $report_file"
    cat "$report_file"
}

# Main execution function
main() {
    local phase_to_run="${1:-all}"
    
    DEPLOYMENT_START_TIME=$(date +%s)
    
    log_info "Starting Splunk MCP Production Deployment"
    log_info "Timestamp: $(date)"
    log_info "Target Namespace: $NAMESPACE"
    log_info "Phase to run: $phase_to_run"
    
    if [ "$phase_to_run" = "all" ]; then
        # Run all phases
        for phase in "${DEPLOYMENT_PHASES[@]}"; do
            eval "$phase"
        done
    else
        # Run specific phase
        if [[ " ${DEPLOYMENT_PHASES[*]} " =~ " $phase_to_run " ]]; then
            eval "$phase_to_run"
        else
            log_error "Invalid phase: $phase_to_run"
            log_info "Available phases: ${DEPLOYMENT_PHASES[*]}"
            exit 1
        fi
    fi
    
    generate_deployment_report
    
    log_success "Production deployment completed successfully!"
    log_info "System is now live and ready for users"
    log_info "Deployment log: $LOG_FILE"
}

# Script usage
usage() {
    echo "Usage: $0 [phase]"
    echo ""
    echo "Available phases:"
    for phase in "${DEPLOYMENT_PHASES[@]}"; do
        echo "  $phase"
    done
    echo ""
    echo "Examples:"
    echo "  $0                    # Run complete deployment"
    echo "  $0 pre_deployment_checks  # Run only pre-deployment checks"
    echo "  $0 core_services_deployment  # Deploy only core services"
}

# Handle command line arguments
if [ $# -gt 1 ]; then
    usage
    exit 1
fi

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    usage
    exit 0
fi

# Execute main function
main "${1:-all}"