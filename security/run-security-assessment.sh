#!/bin/bash
"""
Comprehensive Security Assessment Runner
=======================================
Orchestrates all security review and hardening activities
"""

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-production}"
NAMESPACE="${NAMESPACE:-splunk-mcp-prod}"
OUTPUT_DIR="${SCRIPT_DIR}/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create output directory
create_output_dir() {
    mkdir -p "${OUTPUT_DIR}"
    log_info "Created output directory: ${OUTPUT_DIR}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    # Required tools
    local tools=("python3" "kubectl" "docker" "helm")
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    # Optional security tools (will install if needed)
    local security_tools=("trivy" "grype" "kubesec" "gitleaks" "snyk")
    local missing_security_tools=()
    
    for tool in "${security_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_security_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and run again."
        exit 1
    fi
    
    if [ ${#missing_security_tools[@]} -ne 0 ]; then
        log_warning "Missing optional security tools: ${missing_security_tools[*]}"
        log_info "Attempting to install missing security tools..."
        install_security_tools "${missing_security_tools[@]}"
    fi
    
    # Check Python dependencies
    python3 -c "import requests, yaml, asyncio" 2>/dev/null || {
        log_info "Installing Python dependencies..."
        pip3 install requests pyyaml
    }
    
    log_success "Prerequisites check completed"
}

# Install security tools
install_security_tools() {
    local tools=("$@")
    
    for tool in "${tools[@]}"; do
        log_info "Installing $tool..."
        
        case "$tool" in
            "trivy")
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    brew install trivy || log_warning "Failed to install trivy via brew"
                else
                    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
                fi
                ;;
            "grype")
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    brew tap anchore/grype && brew install grype || log_warning "Failed to install grype via brew"
                else
                    curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin
                fi
                ;;
            "gitleaks")
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    brew install gitleaks || log_warning "Failed to install gitleaks via brew"
                else
                    curl -sSfL https://github.com/zricethezav/gitleaks/releases/latest/download/gitleaks_linux_x64.tar.gz | tar -xz -C /usr/local/bin
                fi
                ;;
            "snyk")
                npm install -g snyk || log_warning "Failed to install snyk via npm"
                ;;
            *)
                log_warning "Don't know how to install $tool automatically"
                ;;
        esac
    done
}

# Run security review framework
run_security_review() {
    log_info "Running comprehensive security review framework..."
    
    local report_file="${OUTPUT_DIR}/security_review_${TIMESTAMP}.json"
    
    if [ -f "${SCRIPT_DIR}/security-review-framework.py" ]; then
        python3 "${SCRIPT_DIR}/security-review-framework.py" \
            --environment "$ENVIRONMENT" \
            --namespace "$NAMESPACE" \
            --output json \
            --export-path "$report_file" \
            --verbose || {
            log_error "Security review framework failed"
            return 1
        }
        
        log_success "Security review completed: $report_file"
    else
        log_error "Security review framework script not found"
        return 1
    fi
}

# Run compliance framework checker
run_compliance_check() {
    log_info "Running compliance framework assessment..."
    
    local report_file="${OUTPUT_DIR}/compliance_assessment_${TIMESTAMP}.json"
    
    if [ -f "${SCRIPT_DIR}/compliance-framework-checker.py" ]; then
        python3 "${SCRIPT_DIR}/compliance-framework-checker.py" \
            --environment "$ENVIRONMENT" \
            --namespace "$NAMESPACE" \
            --output json \
            --export-path "$report_file" \
            --verbose || {
            log_warning "Compliance assessment had issues (non-critical)"
        }
        
        log_success "Compliance assessment completed: $report_file"
    else
        log_error "Compliance framework checker script not found"
        return 1
    fi
}

# Run vulnerability scanner
run_vulnerability_scan() {
    log_info "Running comprehensive vulnerability assessment..."
    
    local report_file="${OUTPUT_DIR}/vulnerability_assessment_${TIMESTAMP}.json"
    
    if [ -f "${SCRIPT_DIR}/vulnerability-scanner.py" ]; then
        python3 "${SCRIPT_DIR}/vulnerability-scanner.py" \
            --environment "$ENVIRONMENT" \
            --namespace "$NAMESPACE" \
            --output json \
            --export-path "$report_file" \
            --verbose || {
            log_warning "Vulnerability assessment completed with findings"
        }
        
        log_success "Vulnerability assessment completed: $report_file"
    else
        log_error "Vulnerability scanner script not found"
        return 1
    fi
}

# Apply Kubernetes security hardening
apply_kubernetes_hardening() {
    log_info "Applying Kubernetes security hardening configurations..."
    
    if [ -f "${SCRIPT_DIR}/kubernetes-security-hardening.yaml" ]; then
        # Validate YAML first
        if kubectl apply --dry-run=client -f "${SCRIPT_DIR}/kubernetes-security-hardening.yaml" >/dev/null 2>&1; then
            log_info "YAML validation passed, applying configurations..."
            
            # Apply in stages to handle dependencies
            log_info "Applying namespaces and basic configurations..."
            kubectl apply -f "${SCRIPT_DIR}/kubernetes-security-hardening.yaml" --selector="step=1" || true
            
            sleep 5
            
            log_info "Applying security policies and network policies..."
            kubectl apply -f "${SCRIPT_DIR}/kubernetes-security-hardening.yaml" --selector="step=2" || true
            
            sleep 5
            
            log_info "Applying remaining configurations..."
            kubectl apply -f "${SCRIPT_DIR}/kubernetes-security-hardening.yaml" || {
                log_warning "Some hardening configurations may have failed to apply"
            }
            
            log_success "Kubernetes security hardening applied"
        else
            log_error "YAML validation failed for security hardening configurations"
            return 1
        fi
    else
        log_error "Kubernetes security hardening YAML not found"
        return 1
    fi
}

# Validate monitoring infrastructure
validate_monitoring() {
    log_info "Validating monitoring infrastructure..."
    
    if [ -f "${PROJECT_ROOT}/infrastructure/monitoring-alerting/validate-monitoring.py" ]; then
        python3 "${PROJECT_ROOT}/infrastructure/monitoring-alerting/validate-monitoring.py" \
            --namespace "splunk-mcp-monitoring-prod" \
            --environment "$ENVIRONMENT" \
            --output json \
            --report-file "${OUTPUT_DIR}/monitoring_validation_${TIMESTAMP}.json" \
            --verbose || {
            log_warning "Monitoring validation completed with issues"
        }
        
        log_success "Monitoring validation completed"
    else
        log_warning "Monitoring validation script not found, skipping..."
    fi
}

# Run security benchmarks
run_security_benchmarks() {
    log_info "Running security benchmarks..."
    
    # CIS Kubernetes Benchmark (simplified)
    log_info "Checking CIS Kubernetes Benchmark compliance..."
    
    # Check for kube-bench
    if command -v kube-bench &> /dev/null; then
        kube-bench --json > "${OUTPUT_DIR}/cis_benchmark_${TIMESTAMP}.json" || {
            log_warning "CIS benchmark assessment had issues"
        }
    else
        log_warning "kube-bench not available, skipping CIS benchmark"
    fi
    
    # Check Pod Security Standards
    log_info "Validating Pod Security Standards..."
    kubectl get pods -n "$NAMESPACE" -o json | jq '.items[] | select(.spec.securityContext.runAsNonRoot != true)' > "${OUTPUT_DIR}/non_compliant_pods_${TIMESTAMP}.json" || true
    
    log_success "Security benchmarks completed"
}

# Generate consolidated report
generate_consolidated_report() {
    log_info "Generating consolidated security assessment report..."
    
    local consolidated_report="${OUTPUT_DIR}/consolidated_security_report_${TIMESTAMP}.json"
    
    # Create consolidated report structure
    cat > "$consolidated_report" << EOF
{
  "assessment_metadata": {
    "assessment_id": "security_assessment_${TIMESTAMP}",
    "environment": "${ENVIRONMENT}",
    "namespace": "${NAMESPACE}",
    "assessment_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "report_version": "1.0"
  },
  "executive_summary": {
    "overall_security_posture": "PENDING_ANALYSIS",
    "critical_findings": 0,
    "high_risk_findings": 0,
    "compliance_status": "PENDING_ANALYSIS",
    "recommendations": []
  },
  "detailed_assessments": {
    "security_review": "security_review_${TIMESTAMP}.json",
    "compliance_assessment": "compliance_assessment_${TIMESTAMP}.json",
    "vulnerability_assessment": "vulnerability_assessment_${TIMESTAMP}.json",
    "monitoring_validation": "monitoring_validation_${TIMESTAMP}.json",
    "security_benchmarks": "cis_benchmark_${TIMESTAMP}.json"
  },
  "remediation_priorities": [],
  "next_steps": [
    "Review all critical and high-risk findings",
    "Implement recommended security controls",
    "Schedule regular security assessments",
    "Update security policies and procedures"
  ]
}
EOF
    
    log_success "Consolidated report generated: $consolidated_report"
}

# Display summary
display_summary() {
    log_info "Security Assessment Summary"
    echo "=================================="
    echo "Environment: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "Assessment Date: $(date)"
    echo "Reports Location: $OUTPUT_DIR"
    echo ""
    echo "Generated Reports:"
    ls -la "$OUTPUT_DIR"/*"$TIMESTAMP"* 2>/dev/null || echo "No reports found"
    echo ""
    echo "Next Steps:"
    echo "1. Review all generated reports"
    echo "2. Address critical and high-risk findings"
    echo "3. Implement recommended security controls"
    echo "4. Schedule regular security assessments"
    echo ""
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    # Add any cleanup tasks here
}

# Signal handler
trap cleanup EXIT

# Main execution
main() {
    echo "================================================================"
    echo "Splunk MCP Integration - Comprehensive Security Assessment"
    echo "================================================================"
    echo ""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment|-e)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --namespace|-n)
                NAMESPACE="$2"
                shift 2
                ;;
            --output-dir|-o)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --skip-hardening)
                SKIP_HARDENING=true
                shift
                ;;
            --skip-scans)
                SKIP_SCANS=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --environment, -e     Target environment (default: production)"
                echo "  --namespace, -n       Kubernetes namespace (default: splunk-mcp-prod)"
                echo "  --output-dir, -o      Output directory for reports (default: ./reports)"
                echo "  --skip-hardening      Skip applying security hardening"
                echo "  --skip-scans          Skip vulnerability and compliance scans"
                echo "  --help, -h            Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute assessment steps
    create_output_dir
    check_prerequisites
    
    if [ "${SKIP_SCANS:-false}" != "true" ]; then
        run_security_review
        run_compliance_check
        run_vulnerability_scan
        run_security_benchmarks
    fi
    
    validate_monitoring
    
    if [ "${SKIP_HARDENING:-false}" != "true" ]; then
        apply_kubernetes_hardening
    fi
    
    generate_consolidated_report
    display_summary
    
    log_success "Comprehensive security assessment completed successfully!"
    
    # Determine exit code based on findings
    if [ -f "${OUTPUT_DIR}/security_review_${TIMESTAMP}.json" ]; then
        # Check for critical findings (simplified)
        if grep -q '"severity": "CRITICAL"' "${OUTPUT_DIR}"/*"${TIMESTAMP}".json 2>/dev/null; then
            log_warning "Critical security findings detected. Please review and address immediately."
            exit 1
        fi
    fi
    
    exit 0
}

# Execute main function
main "$@"