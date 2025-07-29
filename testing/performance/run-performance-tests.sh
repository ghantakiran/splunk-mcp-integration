#!/bin/bash
# Performance Testing Automation Runner for Splunk MCP Platform
# =============================================================
# Orchestrates comprehensive performance testing suite

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Default values
ENVIRONMENT="staging"
TEST_SUITE="all"
CONFIG_FILE="$SCRIPT_DIR/performance-test-config.yaml"
OUTPUT_DIR="$SCRIPT_DIR/reports"
PARALLEL_EXECUTION=true
VERBOSE=false
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message"
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

Performance testing automation runner for Splunk MCP Integration Platform

OPTIONS:
    -h, --help                  Show this help message
    -e, --environment ENV       Test environment (development|staging|production) [default: staging]
    -s, --suite SUITE          Test suite to run (all|load|database|nlp|frontend) [default: all]
    -c, --config FILE          Configuration file path [default: performance-test-config.yaml]
    -o, --output-dir DIR        Output directory for reports [default: ./reports]
    --parallel                  Run tests in parallel (default)
    --sequential                Run tests sequentially
    --dry-run                   Show what would be executed without running
    -v, --verbose               Enable verbose logging

TEST SUITES:
    all                         Run all performance tests
    load                        Load testing and API stress tests
    database                    Database performance testing (PostgreSQL and Redis)
    nlp                         NLP engine performance testing
    frontend                    Frontend performance testing
    integration                 End-to-end integration performance testing

EXAMPLES:
    # Run all tests in staging environment
    $0 --environment staging

    # Run only database tests with verbose output
    $0 --suite database --verbose

    # Run production tests with custom config
    $0 --environment production --config custom-config.yaml

    # Dry run to see what would be executed
    $0 --dry-run --suite all

PREREQUISITES:
    - Python 3.8+ with required packages (asyncio, aiohttp, asyncpg, aioredis)
    - Access to target environment (API, database, Redis)
    - Sufficient system resources for load generation

EOF
}

# Function to check prerequisites
check_prerequisites() {
    info "Checking performance testing prerequisites..."
    
    local errors=0
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
        ((errors++))
    else
        debug "Python 3 found: $(python3 --version)"
    fi
    
    # Check required Python packages
    local required_packages=("aiohttp" "asyncpg" "aioredis" "psutil" "pyyaml")
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" &> /dev/null; then
            error "Required Python package '$package' not found"
            ((errors++))
        else
            debug "Python package '$package' is available"
        fi
    done
    
    # Check configuration file
    if [[ ! -f "$CONFIG_FILE" ]]; then
        error "Configuration file not found: $CONFIG_FILE"
        ((errors++))
    else
        debug "Configuration file found: $CONFIG_FILE"
    fi
    
    # Check test scripts
    local test_scripts=("load-test-suite.py" "database-performance-test.py")
    for script in "${test_scripts[@]}"; do
        local script_path="$SCRIPT_DIR/$script"
        if [[ ! -f "$script_path" ]]; then
            error "Test script not found: $script_path"
            ((errors++))
        else
            debug "Test script found: $script_path"
        fi
    done
    
    if [[ $errors -gt 0 ]]; then
        error "Prerequisites check failed with $errors errors"
        return 1
    fi
    
    success "Prerequisites check passed"
    return 0
}

# Function to create output directory
setup_output_directory() {
    local test_run_dir="$OUTPUT_DIR/performance-test-$TIMESTAMP"
    
    mkdir -p "$test_run_dir"
    
    # Create subdirectories for different test types
    mkdir -p "$test_run_dir/load-testing"
    mkdir -p "$test_run_dir/database-testing"
    mkdir -p "$test_run_dir/nlp-testing"
    mkdir -p "$test_run_dir/frontend-testing"
    mkdir -p "$test_run_dir/system-metrics"
    
    echo "$test_run_dir"
}

# Function to extract configuration for specific test type
extract_test_config() {
    local test_type="$1"
    local output_file="$2"
    
    python3 -c "
import yaml
import json

with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

# Extract environment-specific config
env_config = config.get('environments', {}).get('$ENVIRONMENT', {})
global_config = config.get('global', {})
test_config = config.get('${test_type}_testing', {})

# Merge configurations (environment overrides default)
merged_config = {**test_config, **env_config.get('${test_type}_testing', {})}
merged_config.update(global_config)

with open('$output_file', 'w') as f:
    json.dump(merged_config, f, indent=2)
"
}

# Function to run load testing
run_load_testing() {
    local output_dir="$1"
    
    info "Running load testing suite..."
    
    local config_file="$output_dir/load-test-config.json"
    extract_test_config "load" "$config_file"
    
    local test_script="$SCRIPT_DIR/load-test-suite.py"
    local report_file="$output_dir/load-testing/load-test-report-$TIMESTAMP.json"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        debug "DRY RUN: Would execute load testing with config: $config_file"
        return 0
    fi
    
    # Run load testing
    local cmd="python3 $test_script --config $config_file --output $report_file"
    
    if [[ "$VERBOSE" == "true" ]]; then
        cmd="$cmd --verbose"
    fi
    
    debug "Executing: $cmd"
    
    if eval "$cmd"; then
        success "Load testing completed successfully"
        echo "$report_file"
    else
        error "Load testing failed"
        return 1
    fi
}

# Function to run database performance testing
run_database_testing() {
    local output_dir="$1"
    
    info "Running database performance testing..."
    
    local config_file="$output_dir/database-test-config.json"
    extract_test_config "database" "$config_file"
    
    local test_script="$SCRIPT_DIR/database-performance-test.py"
    local report_file="$output_dir/database-testing/database-test-report-$TIMESTAMP.json"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        debug "DRY RUN: Would execute database testing with config: $config_file"
        return 0
    fi
    
    # Extract database connection details from config
    local postgres_url=$(python3 -c "
import json
with open('$config_file', 'r') as f:
    config = json.load(f)
print(config.get('postgresql', {}).get('connection_url', 'postgresql://user:pass@localhost:5432/splunk_mcp'))
")
    
    local redis_url=$(python3 -c "
import json
with open('$config_file', 'r') as f:
    config = json.load(f)
print(config.get('redis', {}).get('connection_url', 'redis://localhost:6379'))
")
    
    local cmd="python3 $test_script --postgres-url '$postgres_url' --redis-url '$redis_url' --output $report_file"
    
    if [[ "$VERBOSE" == "true" ]]; then
        cmd="$cmd --verbose"
    fi
    
    debug "Executing: $cmd"
    
    if eval "$cmd"; then
        success "Database performance testing completed successfully"
        echo "$report_file"
    else
        error "Database performance testing failed"
        return 1
    fi
}

# Function to run NLP performance testing
run_nlp_testing() {
    local output_dir="$1"
    
    info "Running NLP engine performance testing..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        debug "DRY RUN: Would execute NLP performance testing"
        return 0
    fi
    
    # Create NLP-specific test script
    local nlp_test_script="$output_dir/nlp-performance-test.py"
    
    cat > "$nlp_test_script" << 'EOF'
#!/usr/bin/env python3
import asyncio
import aiohttp
import json
import time
import statistics
from datetime import datetime

async def run_nlp_performance_test():
    """Run NLP engine performance test"""
    
    # Test queries of varying complexity
    test_queries = [
        "show me errors",
        "what are the top 10 errors in the last hour?",
        "find all authentication failures from users in the last 24 hours",
        "create a dashboard showing error trends over time with alerts",
        "analyze user activity patterns and identify anomalies"
    ]
    
    base_url = "http://localhost:8000"
    results = []
    
    async with aiohttp.ClientSession() as session:
        # Authenticate first
        auth_data = {"username": "test_user", "password": "test_password"}
        async with session.post(f"{base_url}/api/v1/auth/login", json=auth_data) as response:
            if response.status == 200:
                data = await response.json()
                token = data.get('access_token')
            else:
                token = None
        
        if not token:
            print("Authentication failed")
            return
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test each query multiple times
        for i, query in enumerate(test_queries):
            query_times = []
            success_count = 0
            
            for _ in range(10):  # 10 iterations per query
                start_time = time.time()
                
                try:
                    async with session.post(
                        f"{base_url}/api/v1/queries/nlp",
                        json={"query": query},
                        headers=headers
                    ) as response:
                        await response.text()
                        end_time = time.time()
                        
                        if response.status < 400:
                            success_count += 1
                            query_times.append(end_time - start_time)
                            
                except Exception as e:
                    print(f"Query failed: {e}")
            
            if query_times:
                results.append({
                    "query_complexity": i + 1,
                    "query": query,
                    "avg_response_time": statistics.mean(query_times),
                    "min_response_time": min(query_times),
                    "max_response_time": max(query_times),
                    "success_rate": success_count / 10 * 100,
                    "iterations": len(query_times)
                })
    
    # Save results
    report = {
        "test_type": "nlp_performance",
        "timestamp": datetime.now().isoformat(),
        "results": results
    }
    
    with open("nlp-performance-report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("NLP Performance Test Results:")
    for result in results:
        print(f"  Complexity {result['query_complexity']}: {result['avg_response_time']:.3f}s avg")

if __name__ == "__main__":
    asyncio.run(run_nlp_performance_test())
EOF
    
    # Run NLP performance test
    local report_file="$output_dir/nlp-testing/nlp-performance-report-$TIMESTAMP.json"
    
    cd "$output_dir/nlp-testing"
    
    if python3 "$nlp_test_script"; then
        mv nlp-performance-report.json "$report_file"
        success "NLP performance testing completed successfully"
        echo "$report_file"
    else
        error "NLP performance testing failed"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
}

# Function to run system monitoring during tests
start_system_monitoring() {
    local output_dir="$1"
    local monitoring_file="$output_dir/system-metrics/system-metrics-$TIMESTAMP.json"
    
    info "Starting system resource monitoring..."
    
    # Create system monitoring script
    local monitor_script="$output_dir/system-monitor.py"
    
    cat > "$monitor_script" << 'EOF'
#!/usr/bin/env python3
import psutil
import json
import time
import signal
import sys
from datetime import datetime

monitoring = True
metrics = []

def signal_handler(sig, frame):
    global monitoring
    monitoring = False
    
    # Save metrics
    with open("system-metrics.json", "w") as f:
        json.dump({
            "monitoring_start": metrics[0]["timestamp"] if metrics else None,
            "monitoring_end": datetime.now().isoformat(),
            "total_samples": len(metrics),
            "metrics": metrics
        }, f, indent=2)
    
    print(f"\nSystem monitoring stopped. Collected {len(metrics)} samples.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print("Starting system monitoring... Press Ctrl+C to stop.")

while monitoring:
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        metrics.append({
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available": memory.available,
            "disk_usage": disk.percent,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        })
        
        time.sleep(5)  # Collect metrics every 5 seconds
        
    except Exception as e:
        print(f"Monitoring error: {e}")
        time.sleep(5)
EOF
    
    # Start monitoring in background
    cd "$output_dir/system-metrics"
    python3 "$monitor_script" &
    local monitor_pid=$!
    cd "$SCRIPT_DIR"
    
    echo "$monitor_pid"
}

# Function to stop system monitoring
stop_system_monitoring() {
    local monitor_pid="$1"
    local output_dir="$2"
    
    info "Stopping system resource monitoring..."
    
    if kill -TERM "$monitor_pid" 2>/dev/null; then
        sleep 2
        success "System monitoring stopped"
        
        # Move metrics file to final location
        local final_metrics="$output_dir/system-metrics/system-metrics-$TIMESTAMP.json"
        if [[ -f "$output_dir/system-metrics/system-metrics.json" ]]; then
            mv "$output_dir/system-metrics/system-metrics.json" "$final_metrics"
            echo "$final_metrics"
        fi
    else
        warning "Could not stop system monitoring (PID: $monitor_pid)"
    fi
}

# Function to generate comprehensive report
generate_comprehensive_report() {
    local output_dir="$1"
    shift
    local report_files=("$@")
    
    info "Generating comprehensive performance report..."
    
    local summary_file="$output_dir/performance-test-summary-$TIMESTAMP.json"
    
    # Create comprehensive report
    python3 -c "
import json
import os
from datetime import datetime

report_files = '$( IFS=$'\n'; echo "${report_files[*]}" )'.split('\n')
report_files = [f.strip() for f in report_files if f.strip()]

comprehensive_report = {
    'test_run_summary': {
        'environment': '$ENVIRONMENT',
        'test_suite': '$TEST_SUITE',
        'timestamp': datetime.now().isoformat(),
        'total_test_files': len(report_files)
    },
    'individual_reports': {}
}

for report_file in report_files:
    if os.path.exists(report_file):
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
            
            # Extract key metrics
            report_name = os.path.basename(report_file).replace('-$TIMESTAMP.json', '')
            comprehensive_report['individual_reports'][report_name] = {
                'file_path': report_file,
                'summary': data.get('performance_analysis', data.get('summary', {}))
            }
        except Exception as e:
            print(f'Error processing {report_file}: {e}')

with open('$summary_file', 'w') as f:
    json.dump(comprehensive_report, f, indent=2)

print('Comprehensive report generated: $summary_file')
"
    
    success "Comprehensive report generated: $summary_file"
    echo "$summary_file"
}

# Function to display test results summary
display_summary() {
    local output_dir="$1"
    local summary_file="$2"
    
    echo ""
    echo "========================================"
    echo "PERFORMANCE TEST SUMMARY"
    echo "========================================"
    echo "Environment: $ENVIRONMENT"
    echo "Test Suite: $TEST_SUITE"
    echo "Timestamp: $TIMESTAMP"
    echo "Output Directory: $output_dir"
    echo ""
    
    if [[ -f "$summary_file" ]]; then
        python3 -c "
import json

try:
    with open('$summary_file', 'r') as f:
        data = json.load(f)
    
    print('Test Results:')
    for test_name, test_data in data.get('individual_reports', {}).items():
        print(f'  {test_name}: {test_data.get(\"file_path\", \"N/A\")}')
    
    print('')
    print('Individual report files:')
    for test_name in data.get('individual_reports', {}):
        print(f'  - {test_name}')
        
except Exception as e:
    print(f'Error displaying summary: {e}')
"
    else
        echo "Summary file not found: $summary_file"
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
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -s|--suite)
            TEST_SUITE="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --parallel)
            PARALLEL_EXECUTION=true
            shift
            ;;
        --sequential)
            PARALLEL_EXECUTION=false
            shift
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

# Main execution function
main() {
    info "Starting Splunk MCP Performance Testing Suite..."
    info "Environment: $ENVIRONMENT"
    info "Test Suite: $TEST_SUITE"
    info "Configuration: $CONFIG_FILE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        warning "DRY RUN MODE - No tests will be executed"
    fi
    
    # Check prerequisites
    check_prerequisites || exit 1
    
    # Setup output directory
    local output_dir
    output_dir=$(setup_output_directory)
    info "Output directory: $output_dir"
    
    # Start system monitoring
    local monitor_pid=""
    if [[ "$DRY_RUN" == "false" ]]; then
        monitor_pid=$(start_system_monitoring "$output_dir")
        debug "System monitoring started (PID: $monitor_pid)"
    fi
    
    # Run tests based on suite selection
    local report_files=()
    local test_failures=0
    
    case "$TEST_SUITE" in
        "load"|"all")
            if run_load_testing "$output_dir"; then
                report_files+=("$output_dir/load-testing/load-test-report-$TIMESTAMP.json")
            else
                ((test_failures++))
            fi
            ;;& # Continue to next pattern
        "database"|"all")
            if run_database_testing "$output_dir"; then
                report_files+=("$output_dir/database-testing/database-test-report-$TIMESTAMP.json")
            else
                ((test_failures++))
            fi
            ;;& # Continue to next pattern
        "nlp"|"all")
            if run_nlp_testing "$output_dir"; then
                report_files+=("$output_dir/nlp-testing/nlp-performance-report-$TIMESTAMP.json")
            else
                ((test_failures++))
            fi
            ;;
    esac
    
    # Stop system monitoring
    local metrics_file=""
    if [[ -n "$monitor_pid" && "$DRY_RUN" == "false" ]]; then
        metrics_file=$(stop_system_monitoring "$monitor_pid" "$output_dir")
        if [[ -n "$metrics_file" ]]; then
            report_files+=("$metrics_file")
        fi
    fi
    
    # Generate comprehensive report
    local summary_file=""
    if [[ ${#report_files[@]} -gt 0 ]]; then
        summary_file=$(generate_comprehensive_report "$output_dir" "${report_files[@]}")
    fi
    
    # Display summary
    display_summary "$output_dir" "$summary_file"
    
    # Exit with appropriate code
    if [[ $test_failures -eq 0 ]]; then
        success "All performance tests completed successfully!"
        exit 0
    else
        error "$test_failures test(s) failed"
        exit 1
    fi
}

# Handle script interruption
trap 'error "Performance testing interrupted"; exit 130' INT TERM

# Run main function
main "$@"