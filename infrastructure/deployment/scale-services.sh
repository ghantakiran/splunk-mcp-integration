#!/bin/bash
# Service Scaling Script for Splunk MCP Platform
# ==============================================
# Automated scaling for production deployments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
NAMESPACE="splunk-mcp-prod"
DRY_RUN=false
VERBOSE=false
WAIT_FOR_READY=true
SCALE_MODE="manual"

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
Usage: $0 [OPTIONS] [SERVICE] [REPLICAS]

Service scaling script for Splunk MCP Integration Platform

ARGUMENTS:
    SERVICE                     Service name to scale (optional if using --all or --preset)
    REPLICAS                    Number of replicas to scale to

OPTIONS:
    -h, --help                  Show this help message
    -n, --namespace NAME        Kubernetes namespace [default: splunk-mcp-prod]
    --dry-run                   Show what would be scaled without executing
    --no-wait                   Don't wait for scaling to complete
    -v, --verbose               Enable verbose logging
    --all REPLICAS              Scale all services to specified replica count
    --preset PRESET             Use predefined scaling preset
    --list-services             List all available services
    --show-current              Show current replica counts

SCALING PRESETS:
    minimal                     Minimal resource usage (1 replica each)
    development                 Development environment (1-2 replicas)
    staging                     Staging environment (2-3 replicas)
    production                  Production environment (3-5 replicas)
    high-load                   High load environment (5-10 replicas)

EXAMPLES:
    # Scale specific service
    $0 api-gateway 3

    # Scale all services to 2 replicas
    $0 --all 2

    # Use production preset
    $0 --preset production

    # Show current scaling status
    $0 --show-current

    # Dry run with staging preset
    $0 --dry-run --preset staging

SERVICES:
    Core: api-gateway, nlp-engine, visualization, alert-manager
    Integration: slack-bot, teams-bot, email-service, webhook-service, bi-integration
    Export: pdf-export, powerpoint-export, html-report, word-export, csv-export, json-xml-export
    Platform: secure-sharing, report-scheduling, frontend

EOF
}

# Function to list all services
list_services() {
    info "Available services in namespace: $NAMESPACE"
    
    local deployments=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [[ -z "$deployments" ]]; then
        warning "No deployments found in namespace $NAMESPACE"
        return 1
    fi
    
    echo ""
    echo "Core Services:"
    for service in api-gateway nlp-engine visualization alert-manager; do
        if echo "$deployments" | tr ' ' '\n' | grep -q "^$service$"; then
            echo "  - $service"
        fi
    done
    
    echo ""
    echo "Integration Services:"
    for service in slack-bot teams-bot email-service webhook-service bi-integration; do
        if echo "$deployments" | tr ' ' '\n' | grep -q "^$service$"; then
            echo "  - $service"
        fi
    done
    
    echo ""
    echo "Export Services:"
    for service in pdf-export powerpoint-export html-report word-export csv-export json-xml-export; do
        if echo "$deployments" | tr ' ' '\n' | grep -q "^$service$"; then
            echo "  - $service"
        fi
    done
    
    echo ""
    echo "Platform Services:"
    for service in secure-sharing report-scheduling frontend; do
        if echo "$deployments" | tr ' ' '\n' | grep -q "^$service$"; then
            echo "  - $service"
        fi
    done
}

# Function to show current replica counts
show_current_scaling() {
    info "Current replica counts in namespace: $NAMESPACE"
    
    echo ""
    printf "%-25s %-10s %-10s %-10s\n" "SERVICE" "DESIRED" "CURRENT" "READY"
    printf "%-25s %-10s %-10s %-10s\n" "-------" "-------" "-------" "-----"
    
    local deployments=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    for deployment in $deployments; do
        local desired=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
        local current=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.replicas}')
        local ready=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
        
        # Handle empty values
        desired=${desired:-0}
        current=${current:-0}
        ready=${ready:-0}
        
        printf "%-25s %-10s %-10s %-10s\n" "$deployment" "$desired" "$current" "$ready"
    done
}

# Function to get preset scaling configuration
get_preset_config() {
    local preset="$1"
    
    case "$preset" in
        minimal)
            cat << EOF
api-gateway:1
nlp-engine:1
visualization:1
alert-manager:1
slack-bot:1
teams-bot:1
email-service:1
webhook-service:1
bi-integration:1
pdf-export:1
powerpoint-export:1
html-report:1
word-export:1
csv-export:1
json-xml-export:1
secure-sharing:1
report-scheduling:1
frontend:1
EOF
            ;;
        development)
            cat << EOF
api-gateway:2
nlp-engine:1
visualization:1
alert-manager:1
slack-bot:1
teams-bot:1
email-service:1
webhook-service:1
bi-integration:1
pdf-export:1
powerpoint-export:1
html-report:1
word-export:1
csv-export:1
json-xml-export:1
secure-sharing:1
report-scheduling:1
frontend:2
EOF
            ;;
        staging)
            cat << EOF
api-gateway:3
nlp-engine:2
visualization:2
alert-manager:2
slack-bot:1
teams-bot:1
email-service:2
webhook-service:2
bi-integration:1
pdf-export:2
powerpoint-export:2
html-report:2
word-export:2
csv-export:2
json-xml-export:2
secure-sharing:2
report-scheduling:1
frontend:3
EOF
            ;;
        production)
            cat << EOF
api-gateway:5
nlp-engine:3
visualization:3
alert-manager:3
slack-bot:2
teams-bot:2
email-service:3
webhook-service:3
bi-integration:2
pdf-export:3
powerpoint-export:3
html-report:3
word-export:3
csv-export:3
json-xml-export:3
secure-sharing:3
report-scheduling:2
frontend:5
EOF
            ;;
        high-load)
            cat << EOF
api-gateway:10
nlp-engine:5
visualization:5
alert-manager:5
slack-bot:3
teams-bot:3
email-service:5
webhook-service:5
bi-integration:3
pdf-export:5
powerpoint-export:5
html-report:5
word-export:5
csv-export:5
json-xml-export:5
secure-sharing:5
report-scheduling:3
frontend:10
EOF
            ;;
        *)
            error "Unknown preset: $preset"
            return 1
            ;;
    esac
}

# Function to scale a single service
scale_service() {
    local service="$1"
    local replicas="$2"
    
    info "Scaling service '$service' to $replicas replicas..."
    
    # Check if deployment exists
    if ! kubectl get deployment "$service" -n "$NAMESPACE" &>/dev/null; then
        warning "Deployment '$service' not found in namespace $NAMESPACE"
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        debug "DRY RUN: Would scale $service to $replicas replicas"
        return 0
    fi
    
    # Perform scaling
    kubectl scale deployment "$service" --replicas="$replicas" -n "$NAMESPACE"
    
    if [[ "$WAIT_FOR_READY" == "true" ]]; then
        info "Waiting for scaling to complete..."
        kubectl rollout status deployment/"$service" -n "$NAMESPACE" --timeout=300s
        success "Service '$service' scaled successfully to $replicas replicas"
    else
        success "Scaling initiated for service '$service'"
    fi
}

# Function to scale all services
scale_all_services() {
    local replicas="$1"
    
    info "Scaling all services to $replicas replicas..."
    
    local deployments=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [[ -z "$deployments" ]]; then
        error "No deployments found in namespace $NAMESPACE"
        return 1
    fi
    
    local scaling_failures=0
    
    for deployment in $deployments; do
        if scale_service "$deployment" "$replicas"; then
            debug "Successfully scaled $deployment"
        else
            error "Failed to scale $deployment"
            ((scaling_failures++))
        fi
    done
    
    if [[ $scaling_failures -eq 0 ]]; then
        success "All services scaled successfully"
    else
        error "$scaling_failures services failed to scale"
        return 1
    fi
}

# Function to apply preset scaling
apply_preset() {
    local preset="$1"
    
    info "Applying scaling preset: $preset"
    
    local preset_config
    if ! preset_config=$(get_preset_config "$preset"); then
        return 1
    fi
    
    local scaling_failures=0
    
    while IFS=':' read -r service replicas; do
        if [[ -n "$service" && -n "$replicas" ]]; then
            if scale_service "$service" "$replicas"; then
                debug "Successfully applied preset scaling for $service"
            else
                warning "Failed to apply preset scaling for $service"
                ((scaling_failures++))
            fi
        fi
    done <<< "$preset_config"
    
    if [[ $scaling_failures -eq 0 ]]; then
        success "Preset '$preset' applied successfully"
    else
        warning "Preset '$preset' applied with $scaling_failures failures"
    fi
}

# Function to validate scaling parameters
validate_scaling_params() {
    local service="$1"
    local replicas="$2"
    
    # Validate replica count
    if ! [[ "$replicas" =~ ^[0-9]+$ ]] || [[ "$replicas" -lt 0 ]]; then
        error "Invalid replica count: $replicas (must be a non-negative integer)"
        return 1
    fi
    
    # Validate replica count limits
    if [[ "$replicas" -gt 50 ]]; then
        warning "High replica count detected: $replicas"
        warning "This may consume significant cluster resources"
        
        read -p "Continue with scaling to $replicas replicas? (yes/no): " confirmation
        if [[ "$confirmation" != "yes" ]]; then
            info "Scaling cancelled by user"
            return 1
        fi
    fi
    
    # Check if service exists
    if ! kubectl get deployment "$service" -n "$NAMESPACE" &>/dev/null; then
        error "Service '$service' not found in namespace $NAMESPACE"
        return 1
    fi
    
    return 0
}

# Function to display scaling summary
display_scaling_summary() {
    echo ""
    echo "========================================"
    echo "Scaling Summary"
    echo "========================================"
    echo "Namespace: $NAMESPACE"
    echo "Timestamp: $(date)"
    echo ""
    
    # Show current status
    show_current_scaling
    echo ""
    
    echo "Scaling operation completed."
    echo "========================================"
}

# Parse command line arguments
SCALE_ALL=false
PRESET=""
LIST_SERVICES=false
SHOW_CURRENT=false

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
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-wait)
            WAIT_FOR_READY=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --all)
            SCALE_ALL=true
            ALL_REPLICAS="$2"
            shift 2
            ;;
        --preset)
            PRESET="$2"
            shift 2
            ;;
        --list-services)
            LIST_SERVICES=true
            shift
            ;;
        --show-current)
            SHOW_CURRENT=true
            shift
            ;;
        -*)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            # Positional arguments
            if [[ -z "${SERVICE:-}" ]]; then
                SERVICE="$1"
            elif [[ -z "${REPLICAS:-}" ]]; then
                REPLICAS="$1"
            else
                error "Too many arguments"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Main scaling function
main() {
    # Check prerequisites
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is required but not installed"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Handle special operations
    if [[ "$LIST_SERVICES" == "true" ]]; then
        list_services
        exit 0
    fi
    
    if [[ "$SHOW_CURRENT" == "true" ]]; then
        show_current_scaling
        exit 0
    fi
    
    info "Starting service scaling operation..."
    info "Target namespace: $NAMESPACE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        warning "DRY RUN MODE - No changes will be made"
    fi
    
    # Determine scaling operation
    if [[ "$SCALE_ALL" == "true" ]]; then
        if [[ -z "$ALL_REPLICAS" ]]; then
            error "Replica count required for --all option"
            exit 1
        fi
        scale_all_services "$ALL_REPLICAS"
    elif [[ -n "$PRESET" ]]; then
        apply_preset "$PRESET"
    elif [[ -n "${SERVICE:-}" ]] && [[ -n "${REPLICAS:-}" ]]; then
        validate_scaling_params "$SERVICE" "$REPLICAS"
        scale_service "$SERVICE" "$REPLICAS"
    else
        error "No scaling operation specified"
        echo ""
        usage
        exit 1
    fi
    
    # Display summary
    display_scaling_summary
    
    success "Service scaling completed successfully!"
}

# Run main function
main "$@"