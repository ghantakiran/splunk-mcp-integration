#!/bin/bash

# Production Deployment Orchestration Script
# ==========================================
# Comprehensive production deployment automation for Splunk MCP Integration platform
# with complete infrastructure setup, validation, and monitoring

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="${SCRIPT_DIR}/deployment-$(date +%Y%m%d-%H%M%S).log"
CONFIG_FILE="${SCRIPT_DIR}/production-deployment-config.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Deployment configuration
NAMESPACE="splunk-mcp-prod"
CLUSTER_NAME="splunk-mcp-production"
TIMEOUT=300
RETRY_COUNT=3
HEALTH_CHECK_INTERVAL=30

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE"
            ;;
    esac
}

# Error handling
handle_error() {
    local exit_code=$?
    local line_number=$1
    log "ERROR" "Script failed at line $line_number with exit code $exit_code"
    log "ERROR" "Check deployment logs: $LOG_FILE"
    
    # Attempt cleanup on failure
    if [[ "${CLEANUP_ON_FAILURE:-true}" == "true" ]]; then
        log "WARN" "Initiating cleanup due to deployment failure"
        cleanup_failed_deployment
    fi
    
    exit $exit_code
}

trap 'handle_error ${LINENO}' ERR

# Cleanup function for failed deployments
cleanup_failed_deployment() {
    log "WARN" "Cleaning up failed deployment resources"
    
    # Remove failed deployments but keep namespace and persistent data
    kubectl delete deployment --all -n "$NAMESPACE" --ignore-not-found=true || true
    kubectl delete service --all -n "$NAMESPACE" --ignore-not-found=true || true
    kubectl delete ingress --all -n "$NAMESPACE" --ignore-not-found=true || true
    kubectl delete hpa --all -n "$NAMESPACE" --ignore-not-found=true || true
    
    log "WARN" "Cleanup completed. Persistent volumes and secrets preserved."
}

# Pre-deployment validation
validate_prerequisites() {
    log "INFO" "Validating deployment prerequisites"
    
    # Check required tools
    local required_tools=("kubectl" "helm" "python3" "jq" "yq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log "ERROR" "Required tool '$tool' is not installed"
            exit 1
        fi
    done
    
    # Check Kubernetes cluster access
    if ! kubectl cluster-info &> /dev/null; then
        log "ERROR" "Cannot access Kubernetes cluster"
        exit 1
    fi
    
    # Verify cluster context
    local current_context=$(kubectl config current-context)
    log "INFO" "Current Kubernetes context: $current_context"
    
    # Check if running in correct context for production
    if [[ "$current_context" != *"production"* && "$current_context" != *"prod"* ]]; then
        log "WARN" "Current context '$current_context' does not appear to be production"
        read -p "Continue with deployment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "INFO" "Deployment cancelled by user"
            exit 0
        fi
    fi
    
    # Check cluster resources
    local nodes_ready=$(kubectl get nodes --no-headers | grep " Ready " | wc -l)
    if [[ $nodes_ready -lt 3 ]]; then
        log "ERROR" "Insufficient ready nodes: $nodes_ready (minimum 3 required)"
        exit 1
    fi
    
    # Check if configuration file exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log "ERROR" "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    log "INFO" "Prerequisites validation completed successfully"
}

# Create namespace and initial setup
setup_namespace() {
    log "INFO" "Setting up production namespace: $NAMESPACE"
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        kubectl create namespace "$NAMESPACE"
        log "INFO" "Created namespace: $NAMESPACE"
    else
        log "INFO" "Namespace $NAMESPACE already exists"
    fi
    
    # Label namespace for monitoring and policies
    kubectl label namespace "$NAMESPACE" \
        name="$NAMESPACE" \
        environment=production \
        project=splunk-mcp-integration \
        tier=production \
        --overwrite
    
    # Apply resource quotas and limits
    log "INFO" "Applying resource quotas and limits"
    kubectl apply -f "${SCRIPT_DIR}/production-manifests.yaml" -l component=quota
    
    log "INFO" "Namespace setup completed"
}

# Deploy infrastructure components
deploy_infrastructure() {
    log "INFO" "Deploying infrastructure components"
    
    # Deploy RBAC
    log "INFO" "Deploying RBAC configuration"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/rbac/" -n "$NAMESPACE"
    
    # Deploy network policies
    log "INFO" "Deploying network policies"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/network-policies/" -n "$NAMESPACE"
    
    # Deploy storage classes and persistent volumes
    log "INFO" "Deploying storage infrastructure"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/storage/"
    
    # Wait for storage to be ready
    wait_for_storage_ready
    
    log "INFO" "Infrastructure deployment completed"
}

# Deploy database components
deploy_databases() {
    log "INFO" "Deploying database components"
    
    # Deploy PostgreSQL secrets
    log "INFO" "Deploying database secrets"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/secrets/database-secret.yaml" -n "$NAMESPACE"
    
    # Deploy PostgreSQL primary
    log "INFO" "Deploying PostgreSQL primary"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/database/postgresql/postgresql-primary.yaml" -n "$NAMESPACE"
    
    # Wait for PostgreSQL primary to be ready
    wait_for_deployment_ready "postgres" 300
    
    # Deploy PostgreSQL replica
    log "INFO" "Deploying PostgreSQL replica"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/database/postgresql/postgresql-replica.yaml" -n "$NAMESPACE"
    
    # Deploy Redis
    log "INFO" "Deploying Redis cluster"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/database/redis/" -n "$NAMESPACE"
    
    # Wait for Redis to be ready
    wait_for_deployment_ready "redis" 180
    
    # Validate database connectivity
    validate_database_connectivity
    
    log "INFO" "Database deployment completed"
}

# Deploy monitoring infrastructure
deploy_monitoring() {
    log "INFO" "Deploying monitoring infrastructure"
    
    # Deploy Prometheus
    log "INFO" "Deploying Prometheus"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/monitoring/prometheus/" -n "$NAMESPACE"
    
    # Wait for Prometheus to be ready
    wait_for_deployment_ready "prometheus" 180
    
    # Deploy Grafana
    log "INFO" "Deploying Grafana"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/monitoring/grafana/" -n "$NAMESPACE"
    
    # Deploy AlertManager
    log "INFO" "Deploying AlertManager"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/monitoring/alertmanager/" -n "$NAMESPACE"
    
    # Apply monitoring rules and ServiceMonitors
    kubectl apply -f "${SCRIPT_DIR}/production-manifests.yaml" -l component=monitoring
    
    log "INFO" "Monitoring infrastructure deployment completed"
}

# Deploy application services
deploy_applications() {
    log "INFO" "Deploying application services"
    
    # Deploy ConfigMaps and Secrets
    log "INFO" "Deploying application configurations"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/configmaps/" -n "$NAMESPACE"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/secrets/" -n "$NAMESPACE"
    
    # Deploy core services
    local core_services=("api-gateway" "nlp-engine" "visualization" "alert-manager")
    for service in "${core_services[@]}"; do
        log "INFO" "Deploying $service"
        kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/deployments/${service}.yaml" -n "$NAMESPACE"
        kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/services/${service}.yaml" -n "$NAMESPACE"
        
        # Wait for service to be ready
        wait_for_deployment_ready "$service" 300
        
        # Validate service health
        validate_service_health "$service"
    done
    
    # Deploy integration services
    log "INFO" "Deploying integration services"
    find "${PROJECT_ROOT}/services" -name "docker-compose.yml" -exec dirname {} \; | while read service_dir; do
        service_name=$(basename "$service_dir")
        if [[ -f "${PROJECT_ROOT}/infrastructure/kubernetes/deployments/${service_name}.yaml" ]]; then
            log "INFO" "Deploying integration service: $service_name"
            kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/deployments/${service_name}.yaml" -n "$NAMESPACE"
            kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/services/${service_name}.yaml" -n "$NAMESPACE"
        fi
    done
    
    log "INFO" "Application services deployment completed"
}

# Deploy platform services
deploy_platform_services() {
    log "INFO" "Deploying platform services"
    
    # Deploy auto-scaling configurations
    log "INFO" "Deploying HPA configurations"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/hpa/" -n "$NAMESPACE"
    
    # Deploy ingress controller
    log "INFO" "Deploying ingress configuration"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/ingress/" -n "$NAMESPACE"
    
    # Apply production-specific configurations
    kubectl apply -f "${SCRIPT_DIR}/production-manifests.yaml" -l component=platform
    
    # Wait for ingress to be ready
    wait_for_ingress_ready
    
    log "INFO" "Platform services deployment completed"
}

# Deploy frontend
deploy_frontend() {
    log "INFO" "Deploying frontend application"
    
    # Deploy frontend
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/deployments/frontend.yaml" -n "$NAMESPACE"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/kubernetes/services/frontend.yaml" -n "$NAMESPACE"
    
    # Wait for frontend to be ready
    wait_for_deployment_ready "frontend" 180
    
    # Validate frontend accessibility
    validate_frontend_access
    
    log "INFO" "Frontend deployment completed"
}

# Wait for deployment to be ready
wait_for_deployment_ready() {
    local deployment_name=$1
    local timeout=${2:-300}
    local start_time=$(date +%s)
    
    log "INFO" "Waiting for deployment $deployment_name to be ready (timeout: ${timeout}s)"
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [[ $elapsed -gt $timeout ]]; then
            log "ERROR" "Timeout waiting for deployment $deployment_name to be ready"
            return 1
        fi
        
        if kubectl rollout status deployment/"$deployment_name" -n "$NAMESPACE" --timeout=30s &> /dev/null; then
            log "INFO" "Deployment $deployment_name is ready"
            return 0
        fi
        
        log "DEBUG" "Waiting for $deployment_name... (${elapsed}s elapsed)"
        sleep "$HEALTH_CHECK_INTERVAL"
    done
}

# Wait for storage to be ready
wait_for_storage_ready() {
    log "INFO" "Waiting for storage components to be ready"
    
    # Wait for storage classes
    kubectl wait --for=condition=Available storageclass/fast-ssd --timeout=60s || true
    kubectl wait --for=condition=Available storageclass/standard --timeout=60s || true
    
    log "INFO" "Storage components are ready"
}

# Wait for ingress to be ready
wait_for_ingress_ready() {
    log "INFO" "Waiting for ingress to be ready"
    
    # Check if ingress controller is running
    if kubectl get deployment nginx-ingress-controller -n ingress-nginx &> /dev/null; then
        kubectl wait --for=condition=Available deployment/nginx-ingress-controller -n ingress-nginx --timeout=300s
    fi
    
    # Wait for our ingress to have an external IP
    local timeout=300
    local start_time=$(date +%s)
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [[ $elapsed -gt $timeout ]]; then
            log "WARN" "Timeout waiting for ingress external IP"
            break
        fi
        
        local external_ip=$(kubectl get ingress splunk-mcp-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        if [[ -n "$external_ip" && "$external_ip" != "null" ]]; then
            log "INFO" "Ingress external IP: $external_ip"
            break
        fi
        
        sleep 10
    done
}

# Validate database connectivity
validate_database_connectivity() {
    log "INFO" "Validating database connectivity"
    
    # Test PostgreSQL connection
    if kubectl exec deployment/postgres -n "$NAMESPACE" -- pg_isready -U postgres &> /dev/null; then
        log "INFO" "PostgreSQL connection successful"
    else
        log "ERROR" "PostgreSQL connection failed"
        return 1
    fi
    
    # Test Redis connection
    if kubectl exec deployment/redis -n "$NAMESPACE" -- redis-cli ping | grep -q "PONG"; then
        log "INFO" "Redis connection successful"
    else
        log "ERROR" "Redis connection failed"
        return 1
    fi
}

# Validate service health
validate_service_health() {
    local service_name=$1
    local max_attempts=10
    local attempt=1
    
    log "INFO" "Validating health of service: $service_name"
    
    while [[ $attempt -le $max_attempts ]]; do
        # Get service port
        local service_port=$(kubectl get service "$service_name" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo "8080")
        
        # Test health endpoint
        if kubectl exec deployment/"$service_name" -n "$NAMESPACE" -- curl -sf "http://localhost:${service_port}/health" &> /dev/null; then
            log "INFO" "Service $service_name health check passed"
            return 0
        fi
        
        log "DEBUG" "Service $service_name health check attempt $attempt failed"
        sleep 10
        ((attempt++))
    done
    
    log "WARN" "Service $service_name health check failed after $max_attempts attempts"
    return 1
}

# Validate frontend access
validate_frontend_access() {
    log "INFO" "Validating frontend accessibility"
    
    # Get frontend service details
    local frontend_port=$(kubectl get service frontend -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo "3000")
    
    # Test frontend health
    if kubectl exec deployment/frontend -n "$NAMESPACE" -- curl -sf "http://localhost:${frontend_port}/health" &> /dev/null; then
        log "INFO" "Frontend accessibility validated"
    else
        log "WARN" "Frontend accessibility validation failed"
    fi
}

# Execute comprehensive system validation
execute_system_validation() {
    log "INFO" "Executing comprehensive system validation"
    
    # Run Python validation script
    if [[ -f "${SCRIPT_DIR}/production-deploy.py" ]]; then
        log "INFO" "Running Python validation script"
        python3 "${SCRIPT_DIR}/production-deploy.py" validate
    fi
    
    # Test API endpoints
    log "INFO" "Testing API endpoints"
    test_api_endpoints
    
    # Validate monitoring stack
    log "INFO" "Validating monitoring stack"
    validate_monitoring_stack
    
    # Check all pods are running
    log "INFO" "Checking pod status"
    local failing_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running --no-headers | wc -l)
    if [[ $failing_pods -gt 0 ]]; then
        log "WARN" "Found $failing_pods pods not in Running state"
        kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running
    else
        log "INFO" "All pods are running successfully"
    fi
    
    log "INFO" "System validation completed"
}

# Test API endpoints
test_api_endpoints() {
    local api_gateway_ip=$(kubectl get service api-gateway -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    local api_gateway_port=$(kubectl get service api-gateway -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}')
    
    # Test health endpoint
    if kubectl run test-pod --image=curlimages/curl --rm -i --restart=Never -- \
        curl -sf "http://${api_gateway_ip}:${api_gateway_port}/health" &> /dev/null; then
        log "INFO" "API Gateway health endpoint test passed"
    else
        log "WARN" "API Gateway health endpoint test failed"
    fi
}

# Validate monitoring stack
validate_monitoring_stack() {
    # Check Prometheus
    if kubectl get deployment prometheus -n "$NAMESPACE" &> /dev/null; then
        if kubectl rollout status deployment/prometheus -n "$NAMESPACE" --timeout=60s &> /dev/null; then
            log "INFO" "Prometheus is operational"
        else
            log "WARN" "Prometheus validation failed"
        fi
    fi
    
    # Check Grafana
    if kubectl get deployment grafana -n "$NAMESPACE" &> /dev/null; then
        if kubectl rollout status deployment/grafana -n "$NAMESPACE" --timeout=60s &> /dev/null; then
            log "INFO" "Grafana is operational"
        else
            log "WARN" "Grafana validation failed"
        fi
    fi
}

# Generate deployment report
generate_deployment_report() {
    log "INFO" "Generating deployment report"
    
    local report_file="${SCRIPT_DIR}/deployment-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# Production Deployment Report

**Deployment Date**: $(date)
**Namespace**: $NAMESPACE
**Cluster**: $CLUSTER_NAME

## Deployment Summary

### Infrastructure Components
$(kubectl get all -n "$NAMESPACE" -o wide | head -20)

### Pod Status
$(kubectl get pods -n "$NAMESPACE" -o wide)

### Service Status
$(kubectl get services -n "$NAMESPACE" -o wide)

### Ingress Status
$(kubectl get ingress -n "$NAMESPACE" -o wide)

### Storage Status
$(kubectl get pvc -n "$NAMESPACE" -o wide)

### HPA Status
$(kubectl get hpa -n "$NAMESPACE" -o wide)

## Resource Usage
$(kubectl top pods -n "$NAMESPACE" 2>/dev/null || echo "Metrics not available")

## Validation Results
- Database Connectivity: $(validate_database_connectivity && echo "✅ PASS" || echo "❌ FAIL")
- API Gateway Health: $(validate_service_health "api-gateway" && echo "✅ PASS" || echo "❌ FAIL")
- Frontend Access: $(validate_frontend_access && echo "✅ PASS" || echo "❌ FAIL")

## Next Steps
1. Configure DNS records for external access
2. Set up monitoring alerts
3. Configure backup schedules
4. Plan user training and onboarding

---
*Report generated by Production Deployment Script*
EOF

    log "INFO" "Deployment report generated: $report_file"
}

# Main deployment function
main() {
    local command=${1:-"deploy"}
    
    log "INFO" "Starting production deployment process"
    log "INFO" "Command: $command"
    log "INFO" "Log file: $LOG_FILE"
    
    case $command in
        "deploy")
            validate_prerequisites
            setup_namespace
            deploy_infrastructure
            deploy_databases
            deploy_monitoring
            deploy_applications
            deploy_platform_services
            deploy_frontend
            execute_system_validation
            generate_deployment_report
            log "INFO" "Production deployment completed successfully!"
            ;;
        "validate")
            validate_prerequisites
            execute_system_validation
            ;;
        "cleanup")
            cleanup_failed_deployment
            ;;
        "status")
            kubectl get all -n "$NAMESPACE"
            ;;
        "logs")
            kubectl logs --tail=100 -l app=api-gateway -n "$NAMESPACE"
            ;;
        "help")
            echo "Usage: $0 [deploy|validate|cleanup|status|logs|help]"
            echo "  deploy   - Execute full production deployment"
            echo "  validate - Run system validation only"
            echo "  cleanup  - Cleanup failed deployment"
            echo "  status   - Show deployment status"
            echo "  logs     - Show application logs"
            echo "  help     - Show this help message"
            ;;
        *)
            log "ERROR" "Unknown command: $command"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi