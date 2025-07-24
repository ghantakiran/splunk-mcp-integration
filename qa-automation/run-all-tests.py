#!/usr/bin/env python3
"""
Comprehensive test execution framework for Splunk MCP Integration project.

This script orchestrates the execution of all testing phases including:
- Unit tests (backend and frontend)
- Integration tests
- Performance tests
- Security tests
- End-to-end tests

Usage:
    python run-all-tests.py [--phase=all|unit|integration|performance|security|e2e]
    python run-all-tests.py --coverage --report
    python run-all-tests.py --service=nlp-engine --test-type=unit
"""

import os
import sys
import subprocess
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import concurrent.futures
from dataclasses import dataclass
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test-execution.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test execution result container."""
    service: str
    test_type: str
    status: str
    duration: float
    coverage: float
    details: Dict
    errors: List[str]

@dataclass
class TestSuite:
    """Test suite configuration."""
    name: str
    path: str
    command: str
    timeout: int
    required_coverage: float
    critical: bool

class TestExecutionFramework:
    """Comprehensive test execution framework."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results: List[TestResult] = []
        self.start_time = datetime.now()
        self.config = self.load_test_config()
        
    def load_test_config(self) -> Dict:
        """Load test configuration from YAML file."""
        config_path = self.project_root / "qa-automation" / "test-config.yml"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Default configuration if file doesn't exist
        return {
            "services": [
                "api-gateway", "nlp-engine", "visualization-service",
                "alert-manager", "frontend", "webhook-service",
                "email-service", "pdf-export-service", "powerpoint-export-service",
                "word-export-service", "csv-export-service", "itsm-service",
                "bi-integration-service", "html-report-service"
            ],
            "test_types": ["unit", "integration", "performance", "security", "e2e"],
            "coverage_thresholds": {
                "unit": 90.0,
                "integration": 80.0,
                "overall": 85.0
            },
            "timeouts": {
                "unit": 300,
                "integration": 600,
                "performance": 1800,
                "security": 3600,
                "e2e": 1200
            }
        }
    
    def get_test_suites(self) -> List[TestSuite]:
        """Get all configured test suites."""
        suites = []
        
        # Backend service unit tests
        for service in self.config["services"]:
            if service == "frontend":
                continue
                
            service_path = self.project_root / "services" / service
            if service_path.exists() and (service_path / "tests").exists():
                suites.append(TestSuite(
                    name=f"{service}-unit",
                    path=str(service_path),
                    command="pytest tests/ -v --cov=app --cov-report=json --cov-report=term",
                    timeout=self.config["timeouts"]["unit"],
                    required_coverage=self.config["coverage_thresholds"]["unit"],
                    critical=True
                ))
        
        # Frontend tests
        frontend_path = self.project_root / "frontend"
        if frontend_path.exists():
            suites.append(TestSuite(
                name="frontend-unit",
                path=str(frontend_path),
                command="npm test -- --coverage --watchAll=false --testResultsProcessor=jest-sonar-reporter",
                timeout=self.config["timeouts"]["unit"],
                required_coverage=85.0,
                critical=True
            ))
        
        # Integration tests
        suites.append(TestSuite(
            name="integration-tests",
            path=str(self.project_root / "tests" / "integration"),
            command="pytest -v --tb=short",
            timeout=self.config["timeouts"]["integration"],
            required_coverage=self.config["coverage_thresholds"]["integration"],
            critical=True
        ))
        
        # Performance tests
        suites.append(TestSuite(
            name="performance-tests",
            path=str(self.project_root / "tests" / "performance"),
            command="locust --headless --users 100 --spawn-rate 10 --run-time 300s --html=performance-report.html",
            timeout=self.config["timeouts"]["performance"],
            required_coverage=0.0,
            critical=False
        ))
        
        # Security tests
        suites.append(TestSuite(
            name="security-tests",
            path=str(self.project_root / "tests" / "security"),
            command="python security_test_suite.py",
            timeout=self.config["timeouts"]["security"],
            required_coverage=0.0,
            critical=True
        ))
        
        # End-to-end tests
        suites.append(TestSuite(
            name="e2e-tests",
            path=str(self.project_root / "tests" / "e2e"),
            command="cypress run --headless --browser chrome",
            timeout=self.config["timeouts"]["e2e"],
            required_coverage=0.0,
            critical=True
        ))
        
        return suites
    
    def execute_test_suite(self, suite: TestSuite) -> TestResult:
        """Execute a single test suite."""
        logger.info(f"Starting test suite: {suite.name}")
        
        start_time = time.time()
        
        try:
            # Change to test directory
            original_cwd = os.getcwd()
            os.chdir(suite.path)
            
            # Execute test command
            result = subprocess.run(
                suite.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=suite.timeout
            )
            
            duration = time.time() - start_time
            
            # Parse test results
            coverage = self.extract_coverage(result.stdout, result.stderr)
            status = "PASSED" if result.returncode == 0 else "FAILED"
            
            # Extract additional details
            details = {
                "return_code": result.returncode,
                "stdout": result.stdout[-1000:],  # Last 1000 chars
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "command": suite.command
            }
            
            errors = []
            if result.returncode != 0:
                errors.append(f"Test execution failed with return code {result.returncode}")
            
            if coverage < suite.required_coverage and suite.required_coverage > 0:
                errors.append(f"Coverage {coverage:.1f}% below required {suite.required_coverage}%")
            
            return TestResult(
                service=suite.name.split('-')[0],
                test_type=suite.name.split('-')[-1],
                status=status,
                duration=duration,
                coverage=coverage,
                details=details,
                errors=errors
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                service=suite.name.split('-')[0],
                test_type=suite.name.split('-')[-1],
                status="TIMEOUT",
                duration=suite.timeout,
                coverage=0.0,
                details={"error": "Test execution timed out"},
                errors=[f"Test suite timed out after {suite.timeout} seconds"]
            )
        
        except Exception as e:
            return TestResult(
                service=suite.name.split('-')[0],
                test_type=suite.name.split('-')[-1],
                status="ERROR",
                duration=time.time() - start_time,
                coverage=0.0,
                details={"error": str(e)},
                errors=[f"Test execution error: {str(e)}"]
            )
        
        finally:
            os.chdir(original_cwd)
    
    def extract_coverage(self, stdout: str, stderr: str) -> float:
        """Extract coverage percentage from test output."""
        # Try to find coverage in stdout first
        for line in stdout.split('\n'):
            if 'TOTAL' in line and '%' in line:
                try:
                    # Extract percentage from pytest coverage report
                    parts = line.split()
                    for part in parts:
                        if part.endswith('%'):
                            return float(part.rstrip('%'))
                except ValueError:
                    continue
        
        # Try Jest coverage format
        for line in stdout.split('\n'):
            if 'All files' in line and '%' in line:
                try:
                    # Extract percentage from Jest coverage report
                    parts = line.split('|')
                    if len(parts) >= 2:
                        coverage_part = parts[1].strip()
                        if coverage_part.endswith('%'):
                            return float(coverage_part.rstrip('%'))
                except ValueError:
                    continue
        
        return 0.0
    
    def run_parallel_tests(self, suites: List[TestSuite], max_workers: int = 4) -> List[TestResult]:
        """Run test suites in parallel."""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all test suites
            future_to_suite = {
                executor.submit(self.execute_test_suite, suite): suite 
                for suite in suites
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_suite):
                suite = future_to_suite[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed {suite.name}: {result.status} ({result.duration:.1f}s)")
                except Exception as e:
                    logger.error(f"Error executing {suite.name}: {e}")
                    results.append(TestResult(
                        service=suite.name.split('-')[0],
                        test_type=suite.name.split('-')[-1],
                        status="ERROR",
                        duration=0.0,
                        coverage=0.0,
                        details={"error": str(e)},
                        errors=[f"Parallel execution error: {str(e)}"]
                    ))
        
        return results
    
    def generate_test_report(self, results: List[TestResult]) -> Dict:
        """Generate comprehensive test report."""
        total_duration = sum(r.duration for r in results)
        passed_tests = [r for r in results if r.status == "PASSED"]
        failed_tests = [r for r in results if r.status == "FAILED"]
        error_tests = [r for r in results if r.status == "ERROR"]
        
        # Calculate overall coverage
        coverage_results = [r for r in results if r.coverage > 0]
        overall_coverage = (
            sum(r.coverage for r in coverage_results) / len(coverage_results)
            if coverage_results else 0.0
        )
        
        report = {
            "summary": {
                "total_tests": len(results),
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "errors": len(error_tests),
                "success_rate": len(passed_tests) / len(results) * 100,
                "total_duration": total_duration,
                "overall_coverage": overall_coverage
            },
            "results_by_service": {},
            "results_by_type": {},
            "critical_failures": [],
            "coverage_summary": {},
            "recommendations": []
        }
        
        # Group results by service and type
        for result in results:
            # By service
            if result.service not in report["results_by_service"]:
                report["results_by_service"][result.service] = []
            report["results_by_service"][result.service].append({
                "test_type": result.test_type,
                "status": result.status,
                "duration": result.duration,
                "coverage": result.coverage,
                "errors": result.errors
            })
            
            # By type
            if result.test_type not in report["results_by_type"]:
                report["results_by_type"][result.test_type] = []
            report["results_by_type"][result.test_type].append({
                "service": result.service,
                "status": result.status,
                "duration": result.duration,
                "coverage": result.coverage,
                "errors": result.errors
            })
            
            # Critical failures
            if result.status in ["FAILED", "ERROR"] and result.errors:
                report["critical_failures"].append({
                    "service": result.service,
                    "test_type": result.test_type,
                    "status": result.status,
                    "errors": result.errors
                })
            
            # Coverage summary
            if result.coverage > 0:
                report["coverage_summary"][f"{result.service}-{result.test_type}"] = result.coverage
        
        # Generate recommendations
        if overall_coverage < 85:
            report["recommendations"].append("Overall test coverage is below 85%. Focus on improving unit test coverage.")
        
        if len(failed_tests) > 0:
            report["recommendations"].append(f"{len(failed_tests)} test suites failed. Review and fix failing tests before deployment.")
        
        if total_duration > 1800:  # 30 minutes
            report["recommendations"].append("Test execution time is high. Consider optimizing test performance and parallelization.")
        
        return report
    
    def export_results(self, results: List[TestResult], report: Dict, format: str = "json"):
        """Export test results in various formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            # Export detailed JSON report
            output_file = self.project_root / "qa-automation" / f"test-results-{timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump({
                    "timestamp": timestamp,
                    "execution_time": str(datetime.now() - self.start_time),
                    "report": report,
                    "detailed_results": [
                        {
                            "service": r.service,
                            "test_type": r.test_type,
                            "status": r.status,
                            "duration": r.duration,
                            "coverage": r.coverage,
                            "errors": r.errors,
                            "details": r.details
                        }
                        for r in results
                    ]
                }, f, indent=2)
            
            logger.info(f"JSON report exported to: {output_file}")
        
        elif format == "html":
            # Export HTML report
            html_content = self.generate_html_report(report, results)
            output_file = self.project_root / "qa-automation" / f"test-report-{timestamp}.html"
            with open(output_file, 'w') as f:
                f.write(html_content)
            
            logger.info(f"HTML report exported to: {output_file}")
        
        elif format == "junit":
            # Export JUnit XML for CI/CD integration
            junit_content = self.generate_junit_xml(results)
            output_file = self.project_root / "qa-automation" / f"junit-results-{timestamp}.xml"
            with open(output_file, 'w') as f:
                f.write(junit_content)
            
            logger.info(f"JUnit XML exported to: {output_file}")
    
    def generate_html_report(self, report: Dict, results: List[TestResult]) -> str:
        """Generate HTML test report."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Splunk MCP Integration - Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .metric {{ text-align: center; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
                .passed {{ color: green; }}
                .failed {{ color: red; }}
                .error {{ color: orange; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .coverage-bar {{ width: 100px; height: 20px; background-color: #f0f0f0; border-radius: 10px; }}
                .coverage-fill {{ height: 100%; background-color: #4CAF50; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Splunk MCP Integration - Test Report</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Total Execution Time: {str(datetime.now() - self.start_time)}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>Total Tests</h3>
                    <p>{report['summary']['total_tests']}</p>
                </div>
                <div class="metric passed">
                    <h3>Passed</h3>
                    <p>{report['summary']['passed']}</p>
                </div>
                <div class="metric failed">
                    <h3>Failed</h3>
                    <p>{report['summary']['failed']}</p>
                </div>
                <div class="metric">
                    <h3>Success Rate</h3>
                    <p>{report['summary']['success_rate']:.1f}%</p>
                </div>
                <div class="metric">
                    <h3>Coverage</h3>
                    <p>{report['summary']['overall_coverage']:.1f}%</p>
                </div>
            </div>
            
            <h2>Test Results by Service</h2>
            <table>
                <tr>
                    <th>Service</th>
                    <th>Test Type</th>
                    <th>Status</th>
                    <th>Duration (s)</th>
                    <th>Coverage</th>
                    <th>Errors</th>
                </tr>
        """
        
        for result in results:
            status_class = result.status.lower()
            coverage_width = min(result.coverage, 100)
            
            html += f"""
                <tr>
                    <td>{result.service}</td>
                    <td>{result.test_type}</td>
                    <td class="{status_class}">{result.status}</td>
                    <td>{result.duration:.1f}</td>
                    <td>
                        <div class="coverage-bar">
                            <div class="coverage-fill" style="width: {coverage_width}%"></div>
                        </div>
                        {result.coverage:.1f}%
                    </td>
                    <td>{'; '.join(result.errors) if result.errors else '-'}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>Recommendations</h2>
            <ul>
        """
        
        for recommendation in report['recommendations']:
            html += f"<li>{recommendation}</li>"
        
        html += """
            </ul>
        </body>
        </html>
        """
        
        return html
    
    def generate_junit_xml(self, results: List[TestResult]) -> str:
        """Generate JUnit XML format for CI/CD integration."""
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<testsuites>\n'
        
        for result in results:
            xml += f'  <testsuite name="{result.service}-{result.test_type}" tests="1" '
            xml += f'failures="{1 if result.status == "FAILED" else 0}" '
            xml += f'errors="{1 if result.status == "ERROR" else 0}" '
            xml += f'time="{result.duration}">\n'
            
            xml += f'    <testcase name="{result.service}-{result.test_type}" '
            xml += f'classname="{result.service}" time="{result.duration}">\n'
            
            if result.status == "FAILED":
                xml += '      <failure message="Test failed">\n'
                xml += f'        {"; ".join(result.errors)}\n'
                xml += '      </failure>\n'
            elif result.status == "ERROR":
                xml += '      <error message="Test error">\n'
                xml += f'        {"; ".join(result.errors)}\n'
                xml += '      </error>\n'
            
            xml += '    </testcase>\n'
            xml += '  </testsuite>\n'
        
        xml += '</testsuites>\n'
        return xml
    
    def run_tests(self, phase: str = "all", service: str = None, test_type: str = None, 
                  parallel: bool = True, export_format: str = "json"):
        """Main test execution method."""
        logger.info(f"Starting test execution - Phase: {phase}")
        
        # Get test suites based on filters
        all_suites = self.get_test_suites()
        
        # Filter suites based on parameters
        filtered_suites = []
        for suite in all_suites:
            # Filter by service
            if service and not suite.name.startswith(service):
                continue
            
            # Filter by test type
            if test_type and not suite.name.endswith(test_type):
                continue
            
            # Filter by phase
            if phase != "all":
                if phase == "unit" and not suite.name.endswith("unit"):
                    continue
                elif phase == "integration" and "integration" not in suite.name:
                    continue
                elif phase == "performance" and "performance" not in suite.name:
                    continue
                elif phase == "security" and "security" not in suite.name:
                    continue
                elif phase == "e2e" and "e2e" not in suite.name:
                    continue
            
            filtered_suites.append(suite)
        
        if not filtered_suites:
            logger.warning("No test suites found matching the specified criteria")
            return
        
        logger.info(f"Executing {len(filtered_suites)} test suites")
        
        # Execute tests
        if parallel and len(filtered_suites) > 1:
            results = self.run_parallel_tests(filtered_suites)
        else:
            results = [self.execute_test_suite(suite) for suite in filtered_suites]
        
        # Generate report
        report = self.generate_test_report(results)
        
        # Print summary
        print("\n" + "="*80)
        print("TEST EXECUTION SUMMARY")
        print("="*80)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Errors: {report['summary']['errors']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Overall Coverage: {report['summary']['overall_coverage']:.1f}%")
        print(f"Total Duration: {report['summary']['total_duration']:.1f}s")
        print("="*80)
        
        if report['critical_failures']:
            print("\nCRITICAL FAILURES:")
            for failure in report['critical_failures']:
                print(f"- {failure['service']}-{failure['test_type']}: {'; '.join(failure['errors'])}")
        
        if report['recommendations']:
            print("\nRECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"- {rec}")
        
        # Export results
        self.export_results(results, report, export_format)
        
        # Store results for further analysis
        self.results = results
        
        # Return success/failure for CI/CD
        return all(r.status == "PASSED" for r in results if r.test_type in ["unit", "integration"])

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Splunk MCP Integration Test Framework")
    parser.add_argument("--phase", choices=["all", "unit", "integration", "performance", "security", "e2e"], 
                       default="all", help="Test phase to execute")
    parser.add_argument("--service", help="Specific service to test")
    parser.add_argument("--test-type", help="Specific test type to run")
    parser.add_argument("--parallel", action="store_true", default=True, help="Run tests in parallel")
    parser.add_argument("--no-parallel", action="store_false", dest="parallel", help="Run tests sequentially")
    parser.add_argument("--format", choices=["json", "html", "junit"], default="json", help="Export format")
    parser.add_argument("--coverage", action="store_true", help="Focus on coverage analysis")
    parser.add_argument("--report", action="store_true", help="Generate comprehensive report")
    
    args = parser.parse_args()
    
    # Initialize test framework
    framework = TestExecutionFramework()
    
    # Run tests
    success = framework.run_tests(
        phase=args.phase,
        service=args.service,
        test_type=args.test_type,
        parallel=args.parallel,
        export_format=args.format
    )
    
    # Exit with appropriate code for CI/CD
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()