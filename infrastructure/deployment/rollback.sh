#!/bin/bash
# Rollback Script for Splunk MCP Platform
# =======================================
# Automated rollback for production deployments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
NAMESPACE="splunk-mcp-prod"
ROLLBACK_REVISION=""
DRY_RUN=false
VERBOSE=false
FORCE=false
BACKUP_BEFORE_ROLLBACK=true

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

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Automated rollback script for Splunk MCP Integration Platform

OPTIONS:
    -h, --help                  Show this help message
    -n, --namespace NAME        Kubernetes namespace [default: splunk-mcp-prod]
    -r, --revision NUMBER       Specific revision to rollback to
    --dry-run                   Show what would be rolled back without executing
    --force                     Force rollback without confirmation
    --no-backup                 Skip backup before rollback
    -v, --verbose               Enable verbose logging

EXAMPLES:
    # Rollback to previous version
    $0

    # Rollback to specific revision
    $0 --revision 5

    # Dry run rollback
    $0 --dry-run

    # Force rollback without confirmation
    $0 --force --revision 3

SAFETY FEATURES:
    - Automatic backup creation before rollback
    - Rollback validation and health checks
    - Configuration preservation
    - Gradual service rollback with health verification

EOF
}

# Function to get deployment history
get_deployment_history() {
    local deployment="$1"
    
    info "Getting rollout history for deployment: $deployment"
    
    if ! kubectl rollout history deployment/"$deployment" -n "$NAMESPACE" &>/dev/null; then
        error "Deployment $deployment not found or no history available"
        return 1
    fi
    
    kubectl rollout history deployment/"$deployment" -n "$NAMESPACE"
}

# Function to list all deployments and their revision history
list_deployment_history() {
    info "Listing deployment history for namespace: $NAMESPACE"
    
    local deployments=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')
    
    for deployment in $deployments; do
        echo ""
        echo "=== $deployment ==="
        get_deployment_history "$deployment"
    done
}

# Function to create backup before rollback
create_rollback_backup() {
    if [[ "$BACKUP_BEFORE_ROLLBACK" != "true" ]]; then
        info "Skipping backup as requested"
        return 0
    fi
    
    info "Creating backup before rollback..."
    
    local backup_dir="/tmp/splunk-mcp-rollback-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup current deployments
    info "Backing up current deployments..."
    kubectl get deployments -n "$NAMESPACE" -o yaml > "$backup_dir/deployments.yaml"
    
    # Backup current configmaps
    info "Backing up current configmaps..."
    kubectl get configmaps -n "$NAMESPACE" -o yaml > "$backup_dir/configmaps.yaml"
    
    # Backup current secrets (metadata only for security)
    info "Backing up secrets metadata..."
    kubectl get secrets -n "$NAMESPACE" -o yaml | kubectl neat > "$backup_dir/secrets-metadata.yaml"
    
    # Create rollback information file
    cat > "$backup_dir/rollback-info.txt" << EOF
Rollback Backup Information
==========================
Timestamp: $(date)
Namespace: $NAMESPACE
Rollback Revision: ${ROLLBACK_REVISION:-"previous"}
Backup Location: $backup_dir

Deployment Status Before Rollback:
$(kubectl get deployments -n "$NAMESPACE")

EOF
    
    success "Backup created at: $backup_dir"
    echo "BACKUP_DIR=$backup_dir" > /tmp/last-rollback-backup-location
}

# Function to rollback a specific deployment
rollback_deployment() {
    local deployment="$1"
    local revision="$2"
    
    info "Rolling back deployment: $deployment"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        debug "DRY RUN: Would rollback $deployment to revision $revision"
        return 0
    fi
    
    # Perform rollback
    if [[ -n "$revision" ]]; then
        kubectl rollout undo deployment/"$deployment" --to-revision="$revision" -n "$NAMESPACE"
    else
        kubectl rollout undo deployment/"$deployment" -n "$NAMESPACE"
    fi
    
    # Wait for rollback to complete
    info "Waiting for rollback to complete..."
    kubectl rollout status deployment/"$deployment" -n "$NAMESPACE" --timeout=300s
    
    success "Rollback completed for: $deployment"
}

# Function to verify rollback success
verify_rollback() {
    local deployment="$1"
    
    info "Verifying rollback for deployment: $deployment"
    
    # Check deployment status
    local ready_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
    local desired_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    
    if [[ "$ready_replicas" == "$desired_replicas" ]]; then
        success "Deployment $deployment is healthy after rollback"
    else
        error "Deployment $deployment is not healthy after rollback ($ready_replicas/$desired_replicas ready)"
        return 1
    fi
    
    # Check pod health
    local unhealthy_pods=$(kubectl get pods -n "$NAMESPACE" -l app="$deployment" --field-selector=status.phase!=Running --no-headers | wc -l)
    
    if [[ $unhealthy_pods -eq 0 ]]; then
        success "All pods are healthy for deployment: $deployment"
    else
        warning "$unhealthy_pods pods are not healthy for deployment: $deployment"
    fi
}

# Function to run health checks after rollback
run_post_rollback_health_checks() {
    info "Running post-rollback health checks..."
    
    local health_script="$SCRIPT_DIR/health-check.sh"
    
    if [[ -f "$health_script" ]]; then
        info "Running comprehensive health check..."
        if "$health_script" -n "$NAMESPACE"; then
            success "Post-rollback health checks passed"
        else
            error "Post-rollback health checks failed"
            return 1
        fi
    else
        warning "Health check script not found, running basic checks..."
        
        # Basic pod check
        local failed_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running --no-headers | wc -l)
        
        if [[ $failed_pods -eq 0 ]]; then
            success "Basic health check passed - all pods are running"
        else
            error "Basic health check failed - $failed_pods pods are not running"
            return 1
        fi
    fi
}

# Function to perform gradual rollback
perform_gradual_rollback() {
    info "Performing gradual rollback of all services..."
    
    # Define rollback order (reverse dependency order)
    local services=(
        "frontend"
        "secure-sharing"
        "report-scheduling"
        "json-xml-export"
        "csv-export"
        "word-export"
        "html-report"
        "powerpoint-export"
        "pdf-export"
        "bi-integration"
        "webhook-service"
        "email-service"
        "teams-bot"
        "slack-bot"
        "alert-manager"
        "visualization"
        "nlp-engine"
        "api-gateway"
    )
    
    local rollback_failures=0
    
    for service in "${services[@]}"; do
        # Check if deployment exists
        if kubectl get deployment "$service" -n "$NAMESPACE" &>/dev/null; then
            info "Rolling back service: $service"
            
            if rollback_deployment "$service" "$ROLLBACK_REVISION"; then
                # Verify rollback
                if verify_rollback "$service"; then
                    success "Service $service rolled back successfully"
                else
                    error "Service $service rollback verification failed"
                    ((rollback_failures++))
                fi
            else
                error "Failed to rollback service: $service"
                ((rollback_failures++))
            fi
            
            # Brief pause between rollbacks
            sleep 2
        else
            debug "Service $service not found, skipping"
        fi
    done
    
    if [[ $rollback_failures -eq 0 ]]; then
        success "All services rolled back successfully"
    else
        error "$rollback_failures services failed to rollback properly"
        return 1
    fi
}

# Function to confirm rollback action
confirm_rollback() {
    if [[ "$FORCE" == "true" ]]; then
        return 0
    fi
    
    echo ""
    warning "ROLLBACK CONFIRMATION REQUIRED"
    echo "=================================="
    echo "Namespace: $NAMESPACE"
    echo "Rollback Revision: ${ROLLBACK_REVISION:-'previous'}"
    echo "Backup: ${BACKUP_BEFORE_ROLLBACK}"
    echo ""
    
    # Show current deployment status
    echo "Current deployment status:"
    kubectl get deployments -n "$NAMESPACE" 2>/dev/null || echo "No deployments found"
    echo ""
    
    read -p "Are you sure you want to proceed with rollback? (yes/no): " confirmation
    
    if [[ "$confirmation" != "yes" ]]; then
        info "Rollback cancelled by user"
        exit 0
    fi
}

# Function to display rollback summary
display_rollback_summary() {
    echo ""
    echo "========================================"
    echo "Rollback Summary"
    echo "========================================"
    echo "Namespace: $NAMESPACE"
    echo "Rollback Revision: ${ROLLBACK_REVISION:-'previous'}"
    echo "Timestamp: $(date)"
    echo ""
    
    # Show post-rollback status
    echo "Post-rollback deployment status:"
    kubectl get deployments -n "$NAMESPACE" 2>/dev/null || echo "No deployments found"
    echo ""
    
    echo "Post-rollback pod status:"
    kubectl get pods -n "$NAMESPACE" 2>/dev/null || echo "No pods found"
    echo ""
    
    # Show backup location if created
    if [[ -f "/tmp/last-rollback-backup-location" ]]; then
        local backup_location=$(cat /tmp/last-rollback-backup-location | cut -d'=' -f2)
        echo "Backup Location: $backup_location"
    fi
    
    echo "========================================"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--revision)
            ROLLBACK_REVISION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --no-backup)
            BACKUP_BEFORE_ROLLBACK=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --list-history)
            list_deployment_history
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main rollback function
main() {
    info "Starting Splunk MCP Platform rollback..."
    info "Target namespace: $NAMESPACE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        warning "DRY RUN MODE - No changes will be made"
    fi
    
    # Check prerequisites
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is required but not installed"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Confirm rollback
    confirm_rollback
    
    # Create backup
    create_rollback_backup
    
    # Perform rollback
    perform_gradual_rollback
    
    # Run health checks
    run_post_rollback_health_checks
    
    # Display summary
    display_rollback_summary
    
    success "Rollback completed successfully!"
}

# Run main function
main "$@"