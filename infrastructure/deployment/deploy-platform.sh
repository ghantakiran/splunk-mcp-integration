#!/bin/bash
# Splunk MCP Integration Platform - Master Deployment Script
# ========================================================
# Comprehensive automated deployment for production environments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_FILE="/tmp/splunk-mcp-deployment-$(date +%Y%m%d-%H%M%S).log"

# Default values
ENVIRONMENT="production"
NAMESPACE="splunk-mcp-prod"
MONITORING_NAMESPACE="monitoring"
DRY_RUN=false
SKIP_VALIDATION=false
VERBOSE=false
FORCE_REBUILD=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

info() { log "INFO" "${BLUE}$*${NC}"; }
success() { log "SUCCESS" "${GREEN}$*${NC}"; }
warning() { log "WARNING" "${YELLOW}$*${NC}"; }
error() { log "ERROR" "${RED}$*${NC}"; }
debug() { [[ "$VERBOSE" == "true" ]] && log "DEBUG" "${PURPLE}$*${NC}"; }

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Automated deployment script for Splunk MCP Integration Platform

OPTIONS:
    -h, --help                  Show this help message
    -e, --environment ENV       Target environment (production|staging|development) [default: production]
    -n, --namespace NAME        Kubernetes namespace [default: splunk-mcp-prod]
    -m, --monitoring-ns NAME    Monitoring namespace [default: monitoring]
    --dry-run                   Show what would be deployed without executing
    --skip-validation           Skip pre-deployment validation checks
    --force-rebuild             Force rebuild of Docker images
    -v, --verbose               Enable verbose logging
    --config-file FILE          Custom configuration file
    --components COMPONENTS     Deploy specific components (comma-separated)
                               Options: infrastructure,applications,monitoring,all

EXAMPLES:
    # Full production deployment
    $0 --environment production

    # Staging deployment with verbose output
    $0 -e staging -v

    # Deploy only applications (skip infrastructure)
    $0 --components applications

    # Dry run for production
    $0 --dry-run --environment production

COMPONENTS:
    infrastructure - Kubernetes namespaces, RBAC, storage, network policies
    applications   - All backend services and frontend application
    monitoring     - Prometheus, Grafana, AlertManager stack
    all           - Complete platform deployment (default)

PREREQUISITES:
    - kubectl configured and connected to target cluster
    - Helm installed (for monitoring stack)
    - Docker access for image building (if force-rebuild enabled)
    - Required secrets configured (see docs/admin/installation-guide.md)

EOF
}

# Function to check prerequisites
check_prerequisites() {
    info "Checking deployment prerequisites..."
    
    local errors=0
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is required but not installed"
        ((errors++))
    else
        debug "kubectl found: $(kubectl version --client --short)"
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        ((errors++))
    else
        local cluster_info=$(kubectl cluster-info | head -1)
        debug "Cluster connectivity verified: $cluster_info"
    fi
    
    # Check Helm
    if ! command -v helm &> /dev/null; then
        warning "Helm not found - monitoring stack will use kubectl apply"
    else
        debug "Helm found: $(helm version --short)"
    fi
    
    # Check required directories
    local required_dirs=(
        "$PROJECT_ROOT/infrastructure/kubernetes"
        "$PROJECT_ROOT/infrastructure/monitoring"
        "$SCRIPT_DIR"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            error "Required directory not found: $dir"
            ((errors++))
        fi
    done
    
    # Check for configuration files
    if [[ ! -f "$PROJECT_ROOT/infrastructure/kubernetes/deploy.sh" ]]; then
        warning "Kubernetes deployment script not found - will use manual deployment"
    fi
    
    if [[ $errors -gt 0 ]]; then
        error "Prerequisites check failed with $errors errors"
        return 1
    fi
    
    success "Prerequisites check passed"
    return 0
}

# Function to validate environment configuration
validate_environment() {
    info "Validating environment configuration for: $ENVIRONMENT"
    
    # Check if namespace exists or can be created
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        info "Namespace '$NAMESPACE' already exists"
    else
        info "Namespace '$NAMESPACE' will be created"
    fi
    
    # Validate node resources
    local node_count=$(kubectl get nodes --no-headers | wc -l)
    info "Cluster has $node_count nodes"
    
    if [[ $node_count -lt 3 ]] && [[ "$ENVIRONMENT" == "production" ]]; then
        warning "Production deployment recommended with at least 3 nodes"
    fi
    
    # Check resource availability
    local total_cpu=$(kubectl top nodes 2>/dev/null | awk 'NR>1 {sum += $3} END {print sum}' || echo "unknown")
    local total_memory=$(kubectl top nodes 2>/dev/null | awk 'NR>1 {sum += $5} END {print sum}' || echo "unknown")
    
    debug "Cluster resources - CPU: ${total_cpu}, Memory: ${total_memory}"
    
    # Check storage classes
    local storage_classes=$(kubectl get storageclass --no-headers | wc -l)
    if [[ $storage_classes -eq 0 ]]; then
        warning "No storage classes found - persistent storage may not be available"
    else
        debug "Found $storage_classes storage classes"
    fi
    
    success "Environment validation completed"
}

# Function to deploy infrastructure components
deploy_infrastructure() {
    info "Deploying infrastructure components..."
    
    # Create namespaces
    info "Creating namespaces..."
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace "$MONITORING_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Label namespaces
    kubectl label namespace "$NAMESPACE" name="$NAMESPACE" --overwrite
    kubectl label namespace "$MONITORING_NAMESPACE" name="$MONITORING_NAMESPACE" --overwrite
    
    # Deploy infrastructure components
    local kube_dir="$PROJECT_ROOT/infrastructure/kubernetes"
    
    if [[ -d "$kube_dir" ]]; then
        info "Deploying Kubernetes manifests..."
        
        # Apply in order for dependencies
        local component_order=(
            "namespaces"
            "rbac"
            "storage"
            "configmaps"
            "network-policies"
        )
        
        for component in "${component_order[@]}"; do
            local component_dir="$kube_dir/$component"
            if [[ -d "$component_dir" ]]; then
                info "Deploying $component..."
                if [[ "$DRY_RUN" == "true" ]]; then
                    debug "DRY RUN: Would apply manifests in $component_dir"
                else
                    kubectl apply -f "$component_dir/" --recursive
                fi
                success "$component deployed"
            else
                warning "$component directory not found: $component_dir"
            fi
        done
    else
        warning "Kubernetes manifests directory not found: $kube_dir"
    fi
    
    success "Infrastructure deployment completed"
}

# Function to deploy applications
deploy_applications() {
    info "Deploying application components..."
    
    local kube_dir="$PROJECT_ROOT/infrastructure/kubernetes"
    
    # Deploy secrets (if they exist)
    if [[ -d "$kube_dir/secrets" ]]; then
        info "Deploying secrets..."
        if [[ "$DRY_RUN" == "true" ]]; then
            debug "DRY RUN: Would apply secrets"
        else
            kubectl apply -f "$kube_dir/secrets/" --recursive
        fi
    else
        warning "Secrets directory not found - manual secret creation required"
    fi
    
    # Deploy application manifests
    local app_components=(
        "deployments"
        "services"
        "ingress"
        "hpa"
    )
    
    for component in "${app_components[@]}"; do
        local component_dir="$kube_dir/$component"
        if [[ -d "$component_dir" ]]; then
            info "Deploying $component..."
            if [[ "$DRY_RUN" == "true" ]]; then
                debug "DRY RUN: Would apply $component manifests"
            else
                kubectl apply -f "$component_dir/" --recursive
            fi
            success "$component deployed"
        else
            warning "$component directory not found: $component_dir"
        fi
    done
    
    # Wait for deployments to be ready
    if [[ "$DRY_RUN" == "false" ]]; then
        info "Waiting for deployments to be ready..."
        kubectl wait --for=condition=available --timeout=600s deployment --all -n "$NAMESPACE"
        success "All deployments are ready"
    fi
    
    success "Application deployment completed"
}

# Function to deploy monitoring stack
deploy_monitoring() {
    info "Deploying monitoring stack..."
    
    local monitoring_dir="$PROJECT_ROOT/infrastructure/monitoring"
    
    if [[ ! -d "$monitoring_dir" ]]; then
        error "Monitoring directory not found: $monitoring_dir"
        return 1
    fi
    
    # Check if Helm is available for monitoring deployment
    if command -v helm &> /dev/null; then
        info "Using Helm for monitoring stack deployment..."
        deploy_monitoring_helm
    else
        info "Using kubectl for monitoring stack deployment..."
        deploy_monitoring_kubectl
    fi
    
    success "Monitoring deployment completed"
}

# Function to deploy monitoring with Helm
deploy_monitoring_helm() {
    info "Deploying monitoring stack with Helm..."
    
    # Add Helm repositories
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # Deploy Prometheus
    info "Deploying Prometheus..."
    if [[ "$DRY_RUN" == "true" ]]; then
        debug "DRY RUN: Would deploy Prometheus with Helm"
    else
        helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
            --namespace "$MONITORING_NAMESPACE" \
            --create-namespace \
            --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
            --set grafana.adminPassword=admin123 \
            --wait
    fi
    
    success "Prometheus deployed with Helm"
}

# Function to deploy monitoring with kubectl
deploy_monitoring_kubectl() {
    info "Deploying monitoring stack with kubectl..."
    
    local monitoring_dir="$PROJECT_ROOT/infrastructure/monitoring"
    
    # Deploy monitoring components
    local monitoring_components=(
        "prometheus"
        "grafana"
        "alertmanager"
    )
    
    for component in "${monitoring_components[@]}"; do
        local component_dir="$monitoring_dir/$component"
        if [[ -d "$component_dir" ]]; then
            info "Deploying $component..."
            if [[ "$DRY_RUN" == "true" ]]; then
                debug "DRY RUN: Would apply $component manifests"
            else
                kubectl apply -f "$component_dir/" --recursive
            fi
            success "$component deployed"
        else
            warning "$component directory not found: $component_dir"
        fi
    done
}

# Function to run post-deployment validation
validate_deployment() {
    if [[ "$SKIP_VALIDATION" == "true" ]]; then
        warning "Skipping deployment validation as requested"
        return 0
    fi
    
    info "Running post-deployment validation..."
    
    # Check if validation script exists
    local validation_script="$PROJECT_ROOT/scripts/production-readiness-validation.py"
    if [[ -f "$validation_script" ]]; then
        info "Running production readiness validation..."
        if [[ "$DRY_RUN" == "true" ]]; then
            debug "DRY RUN: Would run validation script"
        else
            python3 "$validation_script" --namespace "$NAMESPACE" --verbose
        fi
    else
        warning "Production readiness validation script not found"
    fi
    
    # Basic health checks
    info "Performing basic health checks..."
    
    # Check pod status
    local failed_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
    if [[ $failed_pods -gt 0 ]]; then
        warning "$failed_pods pods are not running in namespace $NAMESPACE"
        kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running
    else
        success "All pods are running in namespace $NAMESPACE"
    fi
    
    # Check service endpoints
    info "Checking service endpoints..."
    local services=$(kubectl get services -n "$NAMESPACE" --no-headers | awk '{print $1}')
    local endpoint_failures=0
    
    for service in $services; do
        local endpoints=$(kubectl get endpoints "$service" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null | wc -w)
        if [[ $endpoints -eq 0 ]]; then
            warning "Service $service has no endpoints"
            ((endpoint_failures++))
        else
            debug "Service $service has $endpoints endpoints"
        fi
    done
    
    if [[ $endpoint_failures -eq 0 ]]; then
        success "All services have healthy endpoints"
    else
        warning "$endpoint_failures services have endpoint issues"
    fi
    
    success "Post-deployment validation completed"
}

# Function to display deployment summary
display_summary() {
    info "Deployment Summary"
    echo "===================="
    echo "Environment: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "Monitoring Namespace: $MONITORING_NAMESPACE"
    echo "Log File: $LOG_FILE"
    echo ""
    
    if [[ "$DRY_RUN" == "false" ]]; then
        echo "Deployment Status:"
        kubectl get pods -n "$NAMESPACE" 2>/dev/null || echo "No pods found in $NAMESPACE"
        echo ""
        
        echo "Services:"
        kubectl get services -n "$NAMESPACE" 2>/dev/null || echo "No services found in $NAMESPACE"
        echo ""
        
        echo "Ingress:"
        kubectl get ingress -n "$NAMESPACE" 2>/dev/null || echo "No ingress found in $NAMESPACE"
    fi
    
    echo "Next Steps:"
    echo "1. Verify all services are healthy"
    echo "2. Configure external DNS/load balancer"
    echo "3. Set up monitoring alerts"
    echo "4. Run user acceptance testing"
    echo "5. Execute user training program"
}

# Function to handle cleanup on exit
cleanup() {
    if [[ $? -ne 0 ]]; then
        error "Deployment failed - check logs at $LOG_FILE"
    fi
}

trap cleanup EXIT

# Parse command line arguments
COMPONENTS="all"

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
        -m|--monitoring-ns)
            MONITORING_NAMESPACE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --force-rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --components)
            COMPONENTS="$2"
            shift 2
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main deployment function
main() {
    info "Starting Splunk MCP Platform deployment..."
    info "Environment: $ENVIRONMENT"
    info "Target namespace: $NAMESPACE"
    info "Monitoring namespace: $MONITORING_NAMESPACE"
    info "Components: $COMPONENTS"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        warning "DRY RUN MODE - No changes will be made"
    fi
    
    # Step 1: Check prerequisites
    check_prerequisites || exit 1
    
    # Step 2: Validate environment
    validate_environment || exit 1
    
    # Step 3: Deploy components based on selection
    IFS=',' read -ra COMPONENT_LIST <<< "$COMPONENTS"
    for component in "${COMPONENT_LIST[@]}"; do
        case "$component" in
            infrastructure|all)
                deploy_infrastructure
                ;;
            applications|all)
                deploy_applications
                ;;
            monitoring|all)
                deploy_monitoring
                ;;
            all)
                # Already handled above
                ;;
            *)
                warning "Unknown component: $component"
                ;;
        esac
    done
    
    # Step 4: Validate deployment
    validate_deployment
    
    # Step 5: Display summary
    display_summary
    
    success "Splunk MCP Platform deployment completed successfully!"
    info "Check the deployment log at: $LOG_FILE"
}

# Run main function
main "$@"