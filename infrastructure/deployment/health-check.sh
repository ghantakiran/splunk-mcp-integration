#!/bin/bash
# Health Check and Validation Script for Splunk MCP Platform
# ==========================================================
# Comprehensive health monitoring for deployed platform

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
NAMESPACE="splunk-mcp-prod"
MONITORING_NAMESPACE="monitoring"
CHECK_EXTERNAL=false
CONTINUOUS_MODE=false
INTERVAL=30
OUTPUT_FORMAT="text"
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Status tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Logging functions
info() { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[PASS]${NC} $*"; ((PASSED_CHECKS++)); }
warning() { echo -e "${YELLOW}[WARN]${NC} $*"; ((WARNING_CHECKS++)); }
failure() { echo -e "${RED}[FAIL]${NC} $*"; ((FAILED_CHECKS++)); }
debug() { [[ "$VERBOSE" == "true" ]] && echo -e "${PURPLE}[DEBUG]${NC} $*"; }

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Health check and validation script for Splunk MCP Integration Platform

OPTIONS:
    -h, --help                  Show this help message
    -n, --namespace NAME        Application namespace [default: splunk-mcp-prod]
    -m, --monitoring-ns NAME    Monitoring namespace [default: monitoring]
    -e, --check-external        Include external service health checks
    -c, --continuous            Run continuously with interval
    -i, --interval SECONDS      Interval for continuous mode [default: 30]
    -f, --format FORMAT         Output format (text|json|prometheus) [default: text]
    -v, --verbose               Enable verbose logging

EXAMPLES:
    # Basic health check
    $0

    # Check with external services
    $0 --check-external

    # Continuous monitoring
    $0 --continuous --interval 60

    # JSON output for automation
    $0 --format json

HEALTH CHECKS:
    - Kubernetes cluster connectivity
    - Pod status and readiness
    - Service endpoints availability
    - ConfigMap and Secret presence
    - Database connectivity
    - Redis connectivity
    - External service health (optional)
    - Monitoring stack health

EOF
}

# Function to initialize check tracking
init_checks() {
    TOTAL_CHECKS=0
    PASSED_CHECKS=0
    FAILED_CHECKS=0
    WARNING_CHECKS=0
}

# Function to perform a check and track results
perform_check() {
    local check_name="$1"
    local check_command="$2"
    
    ((TOTAL_CHECKS++))
    debug "Running check: $check_name"
    
    if eval "$check_command" &>/dev/null; then
        success "$check_name"
        return 0
    else
        failure "$check_name"
        return 1
    fi
}

# Function to check Kubernetes cluster connectivity
check_cluster_connectivity() {
    info "Checking Kubernetes cluster connectivity..."
    
    perform_check "Cluster API access" "kubectl cluster-info"
    perform_check "Namespace '$NAMESPACE' exists" "kubectl get namespace $NAMESPACE"
    perform_check "Monitoring namespace '$MONITORING_NAMESPACE' exists" "kubectl get namespace $MONITORING_NAMESPACE"
    
    # Check cluster node health
    local node_count=$(kubectl get nodes --no-headers | wc -l)
    local ready_nodes=$(kubectl get nodes --no-headers | grep -c " Ready " || echo 0)
    
    if [[ $ready_nodes -eq $node_count ]]; then
        success "All $node_count cluster nodes are ready"
    else
        failure "Only $ready_nodes of $node_count nodes are ready"
    fi
}

# Function to check pod health
check_pod_health() {
    info "Checking pod health..."
    
    # Get pod status
    local total_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    local running_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
    local ready_pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[?(@.status.conditions[?(@.type=="Ready" && @.status=="True")])].metadata.name}' 2>/dev/null | wc -w)
    
    if [[ $total_pods -eq 0 ]]; then
        failure "No pods found in namespace $NAMESPACE"
        return 1
    fi
    
    if [[ $running_pods -eq $total_pods ]]; then
        success "All $total_pods pods are running"
    else
        failure "Only $running_pods of $total_pods pods are running"
    fi
    
    if [[ $ready_pods -eq $total_pods ]]; then
        success "All $total_pods pods are ready"
    else
        failure "Only $ready_pods of $total_pods pods are ready"
    fi
    
    # Check for pod restarts
    local restart_count=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].status.containerStatuses[*].restartCount}' 2>/dev/null | tr ' ' '\n' | awk '{sum += $1} END {print sum+0}')
    
    if [[ $restart_count -eq 0 ]]; then
        success "No pod restarts detected"
    elif [[ $restart_count -lt 5 ]]; then
        warning "Low restart count detected: $restart_count"
    else
        failure "High restart count detected: $restart_count"
    fi
}

# Function to check service endpoints
check_service_endpoints() {
    info "Checking service endpoints..."
    
    local services=$(kubectl get services -n "$NAMESPACE" --no-headers -o custom-columns=":metadata.name" 2>/dev/null)
    
    if [[ -z "$services" ]]; then
        failure "No services found in namespace $NAMESPACE"
        return 1
    fi
    
    for service in $services; do
        local endpoints=$(kubectl get endpoints "$service" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null | wc -w)
        
        if [[ $endpoints -gt 0 ]]; then
            success "Service '$service' has $endpoints endpoints"
        else
            failure "Service '$service' has no endpoints"
        fi
    done
}

# Function to check configuration resources
check_configuration() {
    info "Checking configuration resources..."
    
    perform_check "ConfigMap 'splunk-mcp-config' exists" "kubectl get configmap splunk-mcp-config -n $NAMESPACE"
    perform_check "Secret 'splunk-mcp-secrets' exists" "kubectl get secret splunk-mcp-secrets -n $NAMESPACE"
    
    # Check if configuration has required keys
    local config_keys=$(kubectl get configmap splunk-mcp-config -n "$NAMESPACE" -o jsonpath='{.data}' 2>/dev/null | jq -r 'keys[]' 2>/dev/null || echo "")
    
    if echo "$config_keys" | grep -q "ENVIRONMENT"; then
        success "ConfigMap contains required configuration"
    else
        warning "ConfigMap may be missing required configuration"
    fi
}

# Function to check application health endpoints
check_application_health() {
    info "Checking application health endpoints..."
    
    # Core services with their ports
    local services=(
        "api-gateway:8000"
        "nlp-engine:8001"
        "visualization:8002"
        "alert-manager:8003"
    )
    
    for service_port in "${services[@]}"; do
        local service="${service_port%:*}"
        local port="${service_port#*:}"
        
        # Check if service exists
        if kubectl get service "$service" -n "$NAMESPACE" &>/dev/null; then
            # Try to access health endpoint
            local health_check="kubectl exec -n $NAMESPACE deployment/$service -- curl -f http://localhost:$port/health --max-time 5"
            
            if perform_check "$service health endpoint" "$health_check"; then
                debug "$service health endpoint is responding"
            else
                debug "$service health endpoint check failed"
            fi
        else
            warning "Service '$service' not found"
            ((WARNING_CHECKS++))
        fi
    done
}

# Function to check database connectivity
check_database_connectivity() {
    info "Checking database connectivity..."
    
    # Check if we can connect to PostgreSQL from api-gateway
    local db_check="kubectl exec -n $NAMESPACE deployment/api-gateway -- python -c \"import psycopg2, os; psycopg2.connect(os.environ['DATABASE_URL']).close(); print('OK')\""
    
    if perform_check "PostgreSQL connectivity" "$db_check"; then
        debug "PostgreSQL connection successful"
    else
        debug "PostgreSQL connection failed"
    fi
}

# Function to check Redis connectivity
check_redis_connectivity() {
    info "Checking Redis connectivity..."
    
    # Check if we can connect to Redis from api-gateway
    local redis_check="kubectl exec -n $NAMESPACE deployment/api-gateway -- python -c \"import redis, os; redis.from_url(os.environ['REDIS_URL']).ping(); print('OK')\""
    
    if perform_check "Redis connectivity" "$redis_check"; then
        debug "Redis connection successful"
    else
        debug "Redis connection failed"
    fi
}

# Function to check external services
check_external_services() {
    if [[ "$CHECK_EXTERNAL" != "true" ]]; then
        return 0
    fi
    
    info "Checking external service connectivity..."
    
    # Check OpenAI API
    local openai_check="kubectl exec -n $NAMESPACE deployment/nlp-engine -- python -c \"import openai, os; openai.api_key=os.environ.get('OPENAI_API_KEY'); print('OK')\""
    perform_check "OpenAI API configuration" "$openai_check" || warning "OpenAI API may not be configured"
    
    # Check Anthropic API
    local anthropic_check="kubectl exec -n $NAMESPACE deployment/nlp-engine -- python -c \"import anthropic, os; anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY')); print('OK')\""
    perform_check "Anthropic API configuration" "$anthropic_check" || warning "Anthropic API may not be configured"
}

# Function to check monitoring stack
check_monitoring_stack() {
    info "Checking monitoring stack..."
    
    # Check if monitoring pods are running
    local prometheus_pods=$(kubectl get pods -n "$MONITORING_NAMESPACE" -l app.kubernetes.io/name=prometheus --no-headers 2>/dev/null | wc -l)
    local grafana_pods=$(kubectl get pods -n "$MONITORING_NAMESPACE" -l app.kubernetes.io/name=grafana --no-headers 2>/dev/null | wc -l)
    
    if [[ $prometheus_pods -gt 0 ]]; then
        success "Prometheus is deployed ($prometheus_pods pods)"
    else
        warning "Prometheus not found in monitoring namespace"
    fi
    
    if [[ $grafana_pods -gt 0 ]]; then
        success "Grafana is deployed ($grafana_pods pods)"
    else
        warning "Grafana not found in monitoring namespace"
    fi
}

# Function to check ingress and networking
check_networking() {
    info "Checking networking configuration..."
    
    # Check ingress resources
    local ingress_count=$(kubectl get ingress -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    
    if [[ $ingress_count -gt 0 ]]; then
        success "Ingress resources configured ($ingress_count found)"
    else
        warning "No ingress resources found"
    fi
    
    # Check network policies
    local netpol_count=$(kubectl get networkpolicy -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    
    if [[ $netpol_count -gt 0 ]]; then
        success "Network policies configured ($netpol_count found)"
    else
        warning "No network policies found"
    fi
}

# Function to generate JSON output
generate_json_output() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local status="healthy"
    
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        status="unhealthy"
    elif [[ $WARNING_CHECKS -gt 0 ]]; then
        status="degraded"
    fi
    
    cat << EOF
{
  "timestamp": "$timestamp",
  "namespace": "$NAMESPACE",
  "status": "$status",
  "summary": {
    "total_checks": $TOTAL_CHECKS,
    "passed": $PASSED_CHECKS,
    "failed": $FAILED_CHECKS,
    "warnings": $WARNING_CHECKS,
    "success_rate": $(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))
  },
  "health_score": $(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
}
EOF
}

# Function to generate Prometheus metrics
generate_prometheus_output() {
    cat << EOF
# HELP splunk_mcp_health_checks_total Total number of health checks performed
# TYPE splunk_mcp_health_checks_total counter
splunk_mcp_health_checks_total{namespace="$NAMESPACE"} $TOTAL_CHECKS

# HELP splunk_mcp_health_checks_passed Number of health checks that passed
# TYPE splunk_mcp_health_checks_passed counter
splunk_mcp_health_checks_passed{namespace="$NAMESPACE"} $PASSED_CHECKS

# HELP splunk_mcp_health_checks_failed Number of health checks that failed
# TYPE splunk_mcp_health_checks_failed counter
splunk_mcp_health_checks_failed{namespace="$NAMESPACE"} $FAILED_CHECKS

# HELP splunk_mcp_health_checks_warnings Number of health checks with warnings
# TYPE splunk_mcp_health_checks_warnings counter
splunk_mcp_health_checks_warnings{namespace="$NAMESPACE"} $WARNING_CHECKS

# HELP splunk_mcp_health_score Overall health score (0-100)
# TYPE splunk_mcp_health_score gauge
splunk_mcp_health_score{namespace="$NAMESPACE"} $(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
EOF
}

# Function to display summary
display_summary() {
    echo ""
    echo "==============================================="
    echo "Health Check Summary"
    echo "==============================================="
    echo "Namespace: $NAMESPACE"
    echo "Timestamp: $(date)"
    echo ""
    echo "Results:"
    echo "  Total Checks: $TOTAL_CHECKS"
    echo "  Passed: $PASSED_CHECKS"
    echo "  Failed: $FAILED_CHECKS"
    echo "  Warnings: $WARNING_CHECKS"
    echo "  Success Rate: $(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))%"
    echo ""
    
    if [[ $FAILED_CHECKS -eq 0 && $WARNING_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}✅ SYSTEM HEALTHY${NC}"
    elif [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${YELLOW}⚠️ SYSTEM HEALTHY WITH WARNINGS${NC}"
    else
        echo -e "${RED}❌ SYSTEM UNHEALTHY${NC}"
    fi
    
    echo "==============================================="
}

# Function to run all health checks
run_health_checks() {
    init_checks
    
    check_cluster_connectivity
    check_pod_health
    check_service_endpoints
    check_configuration
    check_application_health
    check_database_connectivity
    check_redis_connectivity
    check_external_services
    check_monitoring_stack
    check_networking
    
    case "$OUTPUT_FORMAT" in
        json)
            generate_json_output
            ;;
        prometheus)
            generate_prometheus_output
            ;;
        text|*)
            display_summary
            ;;
    esac
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
        -m|--monitoring-ns)
            MONITORING_NAMESPACE="$2"
            shift 2
            ;;
        -e|--check-external)
            CHECK_EXTERNAL=true
            shift
            ;;
        -c|--continuous)
            CONTINUOUS_MODE=true
            shift
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main function
main() {
    # Check prerequisites
    if ! command -v kubectl &> /dev/null; then
        echo "Error: kubectl is required but not installed"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        echo "Error: Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Run health checks
    if [[ "$CONTINUOUS_MODE" == "true" ]]; then
        info "Starting continuous health monitoring (interval: ${INTERVAL}s)"
        while true; do
            run_health_checks
            sleep "$INTERVAL"
            echo ""
        done
    else
        run_health_checks
    fi
    
    # Exit with appropriate code
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        exit 1
    elif [[ $WARNING_CHECKS -gt 0 ]]; then
        exit 2
    else
        exit 0
    fi
}

# Run main function
main "$@"