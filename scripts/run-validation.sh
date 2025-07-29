#!/bin/bash
# Production Readiness Validation Runner
# ======================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
VERBOSE=false
OUTPUT_DIR="validation-reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --env ENV          Environment to validate (development|staging|production)"
            echo "  --verbose          Enable verbose output"
            echo "  --output-dir DIR   Directory for validation reports"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Production Readiness Validation${NC}"
echo -e "${BLUE}======================================${NC}"
echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "Timestamp: ${YELLOW}$TIMESTAMP${NC}"
echo -e "Output Directory: ${YELLOW}$OUTPUT_DIR${NC}"
echo ""

# Check if Python requirements are installed
echo -e "${BLUE}Checking Python dependencies...${NC}"
if ! python3 -c "import aiohttp, asyncpg, aioredis, yaml" 2>/dev/null; then
    echo -e "${RED}Missing required Python packages. Installing...${NC}"
    pip3 install aiohttp asyncpg aioredis pyyaml
fi

# Check if services are running (for development environment)
if [ "$ENVIRONMENT" = "development" ]; then
    echo -e "${BLUE}Checking if development services are running...${NC}"
    
    # Check if docker-compose is running
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✓ Docker services are running${NC}"
    else
        echo -e "${YELLOW}⚠ Docker services not detected. Starting services...${NC}"
        make up-dev &
        DOCKER_PID=$!
        
        # Wait for services to start
        echo "Waiting for services to start..."
        sleep 30
        
        # Check if services are healthy
        timeout=60
        while [ $timeout -gt 0 ]; do
            if curl -f http://localhost:8000/health >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Services are ready${NC}"
                break
            fi
            echo "Waiting for services... ($timeout seconds remaining)"
            sleep 5
            timeout=$((timeout - 5))
        done
        
        if [ $timeout -le 0 ]; then
            echo -e "${RED}✗ Services failed to start within timeout${NC}"
            exit 1
        fi
    fi
fi

# Run the validation script
echo -e "${BLUE}Running production readiness validation...${NC}"

PYTHON_ARGS="--env $ENVIRONMENT"
if [ "$VERBOSE" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --verbose"
fi

REPORT_FILE="$OUTPUT_DIR/production-readiness-report-$ENVIRONMENT-$TIMESTAMP.json"
PYTHON_ARGS="$PYTHON_ARGS --output $REPORT_FILE"

if python3 scripts/production-readiness-validation.py $PYTHON_ARGS; then
    VALIDATION_STATUS="PASSED"
    STATUS_COLOR=$GREEN
else
    VALIDATION_STATUS="FAILED"
    STATUS_COLOR=$RED
fi

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${STATUS_COLOR}Validation Status: $VALIDATION_STATUS${NC}"
echo -e "${BLUE}======================================${NC}"

# Generate summary report
if [ -f "$REPORT_FILE" ]; then
    echo -e "${BLUE}Generating summary report...${NC}"
    
    # Extract key metrics from JSON report
    TOTAL_CHECKS=$(cat "$REPORT_FILE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['summary']['total'])")
    PASSED_CHECKS=$(cat "$REPORT_FILE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['summary']['passed'])")
    FAILED_CHECKS=$(cat "$REPORT_FILE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['summary']['failed'])")
    WARNING_CHECKS=$(cat "$REPORT_FILE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['summary']['warnings'])")
    SUCCESS_RATE=$(cat "$REPORT_FILE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(round((data['summary']['passed'] / data['summary']['total']) * 100, 1) if data['summary']['total'] > 0 else 0)")
    
    # Create summary text report
    SUMMARY_FILE="$OUTPUT_DIR/validation-summary-$ENVIRONMENT-$TIMESTAMP.txt"
    cat > "$SUMMARY_FILE" << EOF
Production Readiness Validation Summary
=======================================

Environment: $ENVIRONMENT
Timestamp: $TIMESTAMP
Overall Status: $VALIDATION_STATUS

Statistics:
-----------
Total Checks: $TOTAL_CHECKS
Passed: $PASSED_CHECKS
Failed: $FAILED_CHECKS
Warnings: $WARNING_CHECKS
Success Rate: $SUCCESS_RATE%

Report Files:
-------------
Detailed JSON Report: $REPORT_FILE
Summary Report: $SUMMARY_FILE

EOF
    
    echo -e "${GREEN}✓ Summary report generated: $SUMMARY_FILE${NC}"
    
    # Display quick summary
    echo ""
    echo -e "${BLUE}Quick Summary:${NC}"
    echo -e "  Total Checks: $TOTAL_CHECKS"
    echo -e "  ${GREEN}Passed: $PASSED_CHECKS${NC}"
    if [ "$FAILED_CHECKS" -gt 0 ]; then
        echo -e "  ${RED}Failed: $FAILED_CHECKS${NC}"
    fi
    if [ "$WARNING_CHECKS" -gt 0 ]; then
        echo -e "  ${YELLOW}Warnings: $WARNING_CHECKS${NC}"
    fi
    echo -e "  Success Rate: $SUCCESS_RATE%"
fi

# Cleanup if we started services
if [ -n "$DOCKER_PID" ]; then
    echo -e "${BLUE}Cleaning up started services...${NC}"
    kill $DOCKER_PID 2>/dev/null || true
    make down >/dev/null 2>&1 || true
fi

echo ""
echo -e "${BLUE}Validation complete. Reports saved to: $OUTPUT_DIR${NC}"

# Exit with appropriate status code
if [ "$VALIDATION_STATUS" = "PASSED" ]; then
    exit 0
else
    exit 1
fi