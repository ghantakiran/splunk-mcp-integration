#!/bin/bash
################################################################################
# Splunk MCP Integration Platform - Automated Deployment Script
# 
# This script automates the complete deployment of the Splunk MCP Integration
# platform to Kubernetes environments with comprehensive validation, health
# checks, and rollback capabilities.
#
# Usage:
#   ./deploy.sh [environment] [options]
#
# Environments:
#   development  - Deploy to development environment
#   staging      - Deploy to staging environment  
#   production   - Deploy to production environment
#
# Options:
#   --dry-run           Validate deployment without applying changes
#   --skip-tests        Skip post-deployment tests
#   --force             Force deployment even if validation fails
#   --rollback          Rollback to previous deployment
#   --verbose           Enable verbose logging
#   --help              Show this help message
#
# Examples:
#   ./deploy.sh production                    # Deploy to production
#   ./deploy.sh staging --dry-run            # Validate staging deployment
#   ./deploy.sh development --verbose        # Deploy to dev with verbose output
#   ./deploy.sh production --rollback        # Rollback production deployment
#
################################################################################

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="${SCRIPT_DIR}/deployment-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default configuration
ENVIRONMENT=""
DRY_RUN=false
SKIP_TESTS=false
FORCE=false
ROLLBACK=false
VERBOSE=false
TIMEOUT=600
NAMESPACE=""

# Deployment components in order
DEPLOYMENT_COMPONENTS=(
    "namespaces"
    "rbac"
    "storage"
    "secrets"
    "configmaps"
    "deployments"
    "services"
    "network-policies"
    "ingress"
    "hpa"
)

################################################################################
# Utility Functions
################################################################################

log() {
    echo -e "${1}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "${BLUE}[INFO]${NC} ${1}"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} ${1}"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} ${1}"
}

log_error() {
    log "${RED}[ERROR]${NC} ${1}"
}

log_debug() {
    if [[ "${VERBOSE}" == "true" ]]; then
        log "${PURPLE}[DEBUG]${NC} ${1}"
    fi
}

print_banner() {
    log ""
    log "${CYAN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    log "${CYAN}║                                                                        ║${NC}"
    log "${CYAN}║           Splunk MCP Integration Platform Deployment                   ║${NC}"
    log "${CYAN}║                                                                        ║${NC}"
    log "${CYAN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    log ""
}

show_help() {
    cat << EOF
Splunk MCP Integration Platform - Automated Deployment Script

USAGE:
    ./deploy.sh [ENVIRONMENT] [OPTIONS]

ENVIRONMENTS:
    development     Deploy to development environment (single replicas, relaxed security)
    staging         Deploy to staging environment (production-like with reduced resources)
    production      Deploy to production environment (full HA, strict security)

OPTIONS:
    --dry-run       Validate deployment configuration without applying changes
    --skip-tests    Skip post-deployment health checks and integration tests
    --force         Force deployment even if pre-deployment validation fails
    --rollback      Rollback to the previous successful deployment
    --verbose       Enable detailed logging and debug output
    --help          Show this help message and exit

EXAMPLES:
    ./deploy.sh production
        Deploy the platform to production environment with full validation

    ./deploy.sh staging --dry-run
        Validate staging deployment configuration without applying changes

    ./deploy.sh development --verbose
        Deploy to development with detailed logging output

    ./deploy.sh production --rollback
        Rollback production deployment to previous version

PREREQUISITES:
    - kubectl configured with cluster access
    - Helm 3.x installed
    - Docker registry access configured
    - Environment secrets properly configured
    - Sufficient cluster resources available

For detailed documentation, see: docs/operations/deployment-handoff.md
EOF
}

check_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    local errors=0
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        ((errors++))
    else
        log_debug "kubectl version: $(kubectl version --client --short 2>/dev/null || echo 'unknown')"
    fi
    
    # Check Helm
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed or not in PATH"
        ((errors++))
    else
        log_debug "Helm version: $(helm version --short 2>/dev/null || echo 'unknown')"
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        ((errors++))
    else
        log_debug "Cluster info: $(kubectl cluster-info --request-timeout=10s 2>/dev/null | head -1 || echo 'unknown')"
    fi
    
    # Check namespace permissions
    if ! kubectl auth can-i create namespaces &> /dev/null; then
        log_error "Insufficient permissions to create namespaces"
        ((errors++))
    fi
    
    # Check if deployment directory exists
    if [[ ! -d "${SCRIPT_DIR}" ]]; then
        log_error "Kubernetes deployment directory not found: ${SCRIPT_DIR}"
        ((errors++))
    fi
    
    # Check environment-specific directory
    if [[ ! -d "${SCRIPT_DIR}/environments/${ENVIRONMENT}" ]]; then
        log_error "Environment directory not found: ${SCRIPT_DIR}/environments/${ENVIRONMENT}"
        ((errors++))
    fi
    
    if [[ ${errors} -gt 0 ]]; then
        log_error "Prerequisites check failed with ${errors} error(s)"
        if [[ "${FORCE}" != "true" ]]; then
            exit 1
        else
            log_warning "Continuing with --force flag despite prerequisite failures"
        fi
    else
        log_success "All prerequisites satisfied"
    fi
}

validate_environment() {
    log_info "Validating environment configuration..."
    
    case "${ENVIRONMENT}" in
        development)
            NAMESPACE="splunk-mcp-dev"
            ;;
        staging)
            NAMESPACE="splunk-mcp-staging"
            ;;
        production)
            NAMESPACE="splunk-mcp-prod"
            ;;
        *)
            log_error "Invalid environment: ${ENVIRONMENT}"
            log_error "Valid environments: development, staging, production"
            exit 1
            ;;
    esac
    
    log_debug "Environment: ${ENVIRONMENT}"
    log_debug "Namespace: ${NAMESPACE}"
    log_debug "Deployment directory: ${SCRIPT_DIR}/environments/${ENVIRONMENT}"
}

validate_manifests() {
    log_info "Validating Kubernetes manifests..."
    
    local validation_errors=0
    local env_dir="${SCRIPT_DIR}/environments/${ENVIRONMENT}"
    
    # Check if kubeval is available
    if command -v kubeval &> /dev/null; then
        log_debug "Using kubeval for manifest validation"
        
        for component in "${DEPLOYMENT_COMPONENTS[@]}"; do
            local manifest_file="${env_dir}/${component}.yaml"
            if [[ -f "${manifest_file}" ]]; then
                log_debug "Validating ${manifest_file}"
                if ! kubeval "${manifest_file}" > /dev/null 2>&1; then
                    log_error "Manifest validation failed: ${manifest_file}"
                    ((validation_errors++))
                fi
            fi
        done
    else
        log_debug "kubeval not available, using kubectl dry-run validation"
        
        # Use kubectl dry-run for validation
        for component in "${DEPLOYMENT_COMPONENTS[@]}"; do
            local manifest_file="${env_dir}/${component}.yaml"
            if [[ -f "${manifest_file}" ]]; then
                log_debug "Validating ${manifest_file}"
                if ! kubectl apply --dry-run=client -f "${manifest_file}" > /dev/null 2>&1; then
                    log_error "Manifest validation failed: ${manifest_file}"
                    ((validation_errors++))
                fi
            fi
        done
    fi
    
    if [[ ${validation_errors} -gt 0 ]]; then
        log_error "Manifest validation failed with ${validation_errors} error(s)"
        if [[ "${FORCE}" != "true" ]]; then
            exit 1
        else
            log_warning "Continuing with --force flag despite validation failures"
        fi
    else
        log_success "All manifests validated successfully"
    fi
}

check_cluster_resources() {
    log_info "Checking cluster resource availability..."
    
    # Get cluster resource information
    local node_count
    local total_cpu
    local total_memory
    
    node_count=$(kubectl get nodes --no-headers 2>/dev/null | wc -l || echo "0")
    
    if [[ ${node_count} -eq 0 ]]; then
        log_error "No cluster nodes found"
        return 1
    fi
    
    log_debug "Cluster nodes: ${node_count}"
    
    # Check minimum requirements based on environment
    local min_nodes
    case "${ENVIRONMENT}" in
        production)
            min_nodes=3
            ;;
        staging)
            min_nodes=2
            ;;
        development)
            min_nodes=1
            ;;
    esac
    
    if [[ ${node_count} -lt ${min_nodes} ]]; then
        log_error "Insufficient cluster nodes. Required: ${min_nodes}, Available: ${node_count}"
        if [[ "${FORCE}" != "true" ]]; then
            exit 1
        fi
    fi
    
    log_success "Cluster resources validated"
}

backup_existing_deployment() {
    log_info "Creating backup of existing deployment..."
    
    local backup_dir="${SCRIPT_DIR}/backups/$(date +%Y%m%d-%H%M%S)-${ENVIRONMENT}"
    mkdir -p "${backup_dir}"
    
    # Backup existing resources if they exist
    local resources=(
        "deployments"
        "services"
        "configmaps"
        "secrets"
        "ingresses"
        "hpa"
    )
    
    for resource in "${resources[@]}"; do
        if kubectl get "${resource}" -n "${NAMESPACE}" &> /dev/null; then
            log_debug "Backing up ${resource}"
            kubectl get "${resource}" -n "${NAMESPACE}" -o yaml > "${backup_dir}/${resource}.yaml" 2>/dev/null || true
        fi
    done
    
    log_success "Backup created: ${backup_dir}"
    echo "${backup_dir}" > "${SCRIPT_DIR}/.last_backup_${ENVIRONMENT}"
}

deploy_component() {
    local component="${1}"
    local env_dir="${SCRIPT_DIR}/environments/${ENVIRONMENT}"
    local manifest_file="${env_dir}/${component}.yaml"
    
    # Also check for component-specific directory
    local component_dir="${SCRIPT_DIR}/${component}"
    
    log_info "Deploying component: ${component}"
    
    if [[ -f "${manifest_file}" ]]; then
        log_debug "Applying manifest: ${manifest_file}"
        
        if [[ "${DRY_RUN}" == "true" ]]; then
            kubectl apply --dry-run=client -f "${manifest_file}"
        else
            kubectl apply -f "${manifest_file}"
            
            # Wait for component-specific resources to be ready
            case "${component}" in
                deployments)
                    wait_for_deployments
                    ;;
                services)
                    wait_for_services
                    ;;
                ingress)
                    wait_for_ingress
                    ;;
            esac
        fi
        
        log_success "Component deployed: ${component}"
        
    elif [[ -d "${component_dir}" ]]; then
        log_debug "Applying component directory: ${component_dir}"
        
        if [[ "${DRY_RUN}" == "true" ]]; then
            kubectl apply --dry-run=client -f "${component_dir}/"
        else
            kubectl apply -f "${component_dir}/"
        fi
        
        log_success "Component deployed: ${component}"
        
    else
        log_warning "No manifest found for component: ${component}"
    fi
}

wait_for_deployments() {
    log_info "Waiting for deployments to be ready..."
    
    local deployments
    deployments=$(kubectl get deployments -n "${NAMESPACE}" -o name 2>/dev/null || echo "")
    
    if [[ -n "${deployments}" ]]; then
        for deployment in ${deployments}; do
            log_debug "Waiting for ${deployment} to be ready..."
            if ! kubectl rollout status "${deployment}" -n "${NAMESPACE}" --timeout="${TIMEOUT}s"; then
                log_error "Deployment failed: ${deployment}"
                return 1
            fi
        done
        log_success "All deployments are ready"
    else
        log_debug "No deployments found in namespace ${NAMESPACE}"
    fi
}

wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    local services
    services=$(kubectl get services -n "${NAMESPACE}" -o name 2>/dev/null || echo "")
    
    if [[ -n "${services}" ]]; then
        for service in ${services}; do
            log_debug "Checking service: ${service}"
            # Services are ready immediately, but we can check for endpoints
            local service_name
            service_name=$(echo "${service}" | cut -d'/' -f2)
            
            # Wait for endpoints to be ready
            local retries=30
            while [[ ${retries} -gt 0 ]]; do
                if kubectl get endpoints "${service_name}" -n "${NAMESPACE}" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null | grep -q .; then
                    log_debug "Service ${service_name} has endpoints"
                    break
                fi
                ((retries--))
                sleep 2
            done
            
            if [[ ${retries} -eq 0 ]]; then
                log_warning "Service ${service_name} has no endpoints"
            fi
        done
        log_success "All services are ready"
    else
        log_debug "No services found in namespace ${NAMESPACE}"
    fi
}

wait_for_ingress() {
    log_info "Waiting for ingress to be ready..."
    
    local ingresses
    ingresses=$(kubectl get ingress -n "${NAMESPACE}" -o name 2>/dev/null || echo "")
    
    if [[ -n "${ingresses}" ]]; then
        for ingress in ${ingresses}; do
            log_debug "Checking ingress: ${ingress}"
            local ingress_name
            ingress_name=$(echo "${ingress}" | cut -d'/' -f2)
            
            # Wait for ingress to get an IP/hostname
            local retries=60
            while [[ ${retries} -gt 0 ]]; do
                local ingress_ip
                ingress_ip=$(kubectl get ingress "${ingress_name}" -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
                
                if [[ -n "${ingress_ip}" ]]; then
                    log_debug "Ingress ${ingress_name} has address: ${ingress_ip}"
                    break
                fi
                ((retries--))
                sleep 5
            done
            
            if [[ ${retries} -eq 0 ]]; then
                log_warning "Ingress ${ingress_name} did not get an external address"
            fi
        done
        log_success "Ingress configuration complete"
    else
        log_debug "No ingress found in namespace ${NAMESPACE}"
    fi
}

run_health_checks() {
    if [[ "${SKIP_TESTS}" == "true" ]]; then
        log_info "Skipping health checks (--skip-tests)"
        return 0
    fi
    
    log_info "Running post-deployment health checks..."
    
    # Check pod health
    check_pod_health
    
    # Check service endpoints
    check_service_endpoints
    
    # Run application-specific health checks
    check_application_health
    
    log_success "All health checks completed"
}

check_pod_health() {
    log_info "Checking pod health..."
    
    local failed_pods=0
    local pods
    pods=$(kubectl get pods -n "${NAMESPACE}" --no-headers 2>/dev/null || echo "")
    
    if [[ -z "${pods}" ]]; then
        log_warning "No pods found in namespace ${NAMESPACE}"
        return 0
    fi
    
    while IFS= read -r pod_line; do
        if [[ -n "${pod_line}" ]]; then
            local pod_name
            local pod_status
            pod_name=$(echo "${pod_line}" | awk '{print $1}')
            pod_status=$(echo "${pod_line}" | awk '{print $3}')
            
            log_debug "Pod: ${pod_name}, Status: ${pod_status}"
            
            if [[ "${pod_status}" != "Running" ]]; then
                log_error "Pod not healthy: ${pod_name} (${pod_status})"
                ((failed_pods++))
                
                # Get pod details for debugging
                log_debug "Pod details:"
                kubectl describe pod "${pod_name}" -n "${NAMESPACE}" | tail -20 || true
            fi
        fi
    done <<< "${pods}"
    
    if [[ ${failed_pods} -gt 0 ]]; then
        log_error "${failed_pods} pod(s) are not healthy"
        return 1
    else
        log_success "All pods are healthy"
    fi
}

check_service_endpoints() {
    log_info "Checking service endpoints..."
    
    local core_services=("api-gateway" "nlp-engine" "visualization" "frontend")
    local failed_services=0
    
    for service in "${core_services[@]}"; do
        if kubectl get service "${service}" -n "${NAMESPACE}" &> /dev/null; then
            log_debug "Checking service: ${service}"
            
            # Check if service has endpoints
            local endpoints
            endpoints=$(kubectl get endpoints "${service}" -n "${NAMESPACE}" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || echo "")
            
            if [[ -z "${endpoints}" ]]; then
                log_error "Service has no endpoints: ${service}"
                ((failed_services++))
            else
                log_debug "Service ${service} has endpoints: ${endpoints}"
            fi
        else
            log_debug "Service not found (optional): ${service}"
        fi
    done
    
    if [[ ${failed_services} -gt 0 ]]; then
        log_error "${failed_services} service(s) have no endpoints"
        return 1
    else
        log_success "All services have healthy endpoints"
    fi
}

check_application_health() {
    log_info "Checking application health endpoints..."
    
    # Port-forward to services and check health endpoints
    local services_health=(
        "api-gateway:8000:/health"
        "nlp-engine:8001:/health"
        "visualization:8002:/health"
    )
    
    for service_health in "${services_health[@]}"; do
        local service_name
        local service_port
        local health_path
        
        IFS=':' read -r service_name service_port health_path <<< "${service_health}"
        
        if kubectl get service "${service_name}" -n "${NAMESPACE}" &> /dev/null; then
            log_debug "Checking health endpoint: ${service_name}${health_path}"
            
            # Start port-forward in background
            kubectl port-forward "service/${service_name}" "${service_port}:${service_port}" -n "${NAMESPACE}" &> /dev/null &
            local pf_pid=$!
            
            # Wait a moment for port-forward to establish
            sleep 3
            
            # Check health endpoint
            local health_status
            health_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${service_port}${health_path}" || echo "000")
            
            # Kill port-forward
            kill ${pf_pid} 2>/dev/null || true
            
            if [[ "${health_status}" == "200" ]]; then
                log_debug "Health check passed: ${service_name}"
            else
                log_warning "Health check failed: ${service_name} (HTTP ${health_status})"
            fi
        else
            log_debug "Service not deployed: ${service_name}"
        fi
    done
    
    log_success "Application health checks completed"
}

perform_rollback() {
    log_info "Performing deployment rollback for environment: ${ENVIRONMENT}"
    
    local backup_file="${SCRIPT_DIR}/.last_backup_${ENVIRONMENT}"
    
    if [[ ! -f "${backup_file}" ]]; then
        log_error "No backup information found for ${ENVIRONMENT}"
        log_error "Cannot perform rollback without previous backup"
        exit 1
    fi
    
    local backup_dir
    backup_dir=$(cat "${backup_file}")
    
    if [[ ! -d "${backup_dir}" ]]; then
        log_error "Backup directory not found: ${backup_dir}"
        exit 1
    fi
    
    log_info "Rolling back to backup: ${backup_dir}"
    
    # Apply backup manifests
    for manifest in "${backup_dir}"/*.yaml; do
        if [[ -f "${manifest}" ]]; then
            log_debug "Applying backup manifest: $(basename "${manifest}")"
            kubectl apply -f "${manifest}" || true
        fi
    done
    
    # Wait for rollback to complete
    wait_for_deployments
    
    log_success "Rollback completed successfully"
}

cleanup_resources() {
    log_info "Cleaning up temporary resources..."
    
    # Kill any remaining port-forward processes
    pkill -f "kubectl port-forward" 2>/dev/null || true
    
    log_debug "Cleanup completed"
}

print_deployment_summary() {
    log ""
    log "${CYAN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    log "${CYAN}║                        Deployment Summary                             ║${NC}"
    log "${CYAN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    log ""
    log "${BLUE}Environment:${NC}     ${ENVIRONMENT}"
    log "${BLUE}Namespace:${NC}       ${NAMESPACE}"
    log "${BLUE}Timestamp:${NC}       $(date)"
    log "${BLUE}Log File:${NC}        ${LOG_FILE}"
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "${YELLOW}Mode:${NC}            Dry Run (validation only)"
    else
        log "${GREEN}Mode:${NC}            Live Deployment"
    fi
    
    log ""
    
    # Show deployed resources
    if [[ "${DRY_RUN}" != "true" && "${ROLLBACK}" != "true" ]]; then
        log "${BLUE}Deployed Resources:${NC}"
        
        local deployments
        deployments=$(kubectl get deployments -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l || echo "0")
        log "  • Deployments: ${deployments}"
        
        local services
        services=$(kubectl get services -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l || echo "0")
        log "  • Services: ${services}"
        
        local ingresses
        ingresses=$(kubectl get ingress -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l || echo "0")
        log "  • Ingresses: ${ingresses}"
        
        local hpas
        hpas=$(kubectl get hpa -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l || echo "0")
        log "  • HPAs: ${hpas}"
    fi
    
    log ""
    log "${GREEN}✅ Deployment completed successfully!${NC}"
    log ""
}

# Signal handlers for cleanup
trap cleanup_resources EXIT
trap 'log_error "Deployment interrupted"; exit 130' INT TERM

################################################################################
# Main Deployment Logic
################################################################################

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            development|staging|production)
                ENVIRONMENT="$1"
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --rollback)
                ROLLBACK=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown argument: $1"
                log_error "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Validate arguments
    if [[ -z "${ENVIRONMENT}" ]]; then
        log_error "Environment not specified"
        log_error "Usage: $0 [development|staging|production] [options]"
        log_error "Use --help for more information"
        exit 1
    fi
    
    # Start deployment
    print_banner
    
    log_info "Starting deployment to ${ENVIRONMENT} environment"
    log_info "Deployment log: ${LOG_FILE}"
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "Running in DRY-RUN mode (validation only)"
    fi
    
    if [[ "${ROLLBACK}" == "true" ]]; then
        log_info "Performing rollback operation"
        perform_rollback
        print_deployment_summary
        exit 0
    fi
    
    # Pre-deployment validation
    validate_environment
    check_prerequisites
    validate_manifests
    check_cluster_resources
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log_success "Dry-run validation completed successfully"
        log_info "All deployment manifests are valid for ${ENVIRONMENT} environment"
        exit 0
    fi
    
    # Create backup before deployment
    backup_existing_deployment
    
    # Deploy components in order
    for component in "${DEPLOYMENT_COMPONENTS[@]}"; do
        deploy_component "${component}"
    done
    
    # Post-deployment validation
    run_health_checks
    
    # Deployment complete
    print_deployment_summary
    
    log_success "🎉 Deployment to ${ENVIRONMENT} completed successfully!"
}

# Run main function
main "$@"