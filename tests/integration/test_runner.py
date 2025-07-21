#!/usr/bin/env python3
"""
Integration test runner and reporting system.

This module provides a comprehensive test runner for integration tests,
generates detailed reports, and manages test execution across environments.
"""

import os
import sys
import time
import json
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

import pytest
import aiohttp
from dataclasses import dataclass, asdict


@dataclass
class TestResult:
    """Test result data structure."""
    test_name: str
    status: str  # passed, failed, skipped, error
    duration: float
    error_message: Optional[str] = None
    service: Optional[str] = None
    category: Optional[str] = None


@dataclass
class ServiceHealthStatus:
    """Service health status data structure."""
    service_name: str
    status: str  # healthy, unhealthy, unknown
    response_time: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class TestSuiteReport:
    """Complete test suite report."""
    start_time: datetime
    end_time: datetime
    total_duration: float
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    success_rate: float
    service_health: List[ServiceHealthStatus]
    test_results: List[TestResult]
    environment_info: Dict[str, Any]


class IntegrationTestRunner:
    """Comprehensive integration test runner."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results: List[TestResult] = []
        self.service_health: List[ServiceHealthStatus] = []
        self.start_time = None
        self.end_time = None
    
    async def check_service_health(self) -> Dict[str, ServiceHealthStatus]:
        """Check health of all services before running tests."""
        services = [
            ("api_gateway", self.config["api_gateway"]),
            ("nlp_engine", self.config["nlp_engine"]),
            ("visualization", self.config["visualization"]),
            ("alert_manager", self.config["alert_manager"]),
            ("email_service", self.config["email_service"]),
            ("webhook_service", self.config["webhook_service"]),
            ("slack_bot", self.config["slack_bot"]),
            ("teams_bot", self.config["teams_bot"])
        ]
        
        health_results = {}
        
        async with aiohttp.ClientSession() as session:
            for service_name, service_config in services:
                health_url = f"http://{service_config['host']}:{service_config['port']}/health"
                
                try:
                    start_time = time.time()
                    async with session.get(health_url, timeout=10) as response:
                        end_time = time.time()
                        response_time = end_time - start_time
                        
                        if response.status == 200:
                            status = ServiceHealthStatus(
                                service_name=service_name,
                                status="healthy",
                                response_time=response_time
                            )
                        else:
                            status = ServiceHealthStatus(
                                service_name=service_name,
                                status="unhealthy",
                                response_time=response_time,
                                error_message=f"HTTP {response.status}"
                            )
                except Exception as e:
                    status = ServiceHealthStatus(
                        service_name=service_name,
                        status="unhealthy",
                        error_message=str(e)
                    )
                
                health_results[service_name] = status
                self.service_health.append(status)
        
        return health_results
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Gather environment information."""
        return {
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": os.getcwd(),
            "environment_variables": {
                key: value for key, value in os.environ.items()
                if key.startswith(('SPLUNK_', 'TEST_', 'API_', 'NLP_', 'REDIS_', 'POSTGRES_'))
            },
            "test_config": self.config
        }
    
    def run_pytest_with_reporting(self, test_paths: List[str], markers: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run pytest with custom reporting."""
        pytest_args = [
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_results.json",
            "--html=test_report.html",
            "--self-contained-html"
        ]
        
        # Add markers if specified
        if markers:
            for marker in markers:
                pytest_args.extend(["-m", marker])
        
        # Add test paths
        pytest_args.extend(test_paths)
        
        # Run pytest
        exit_code = pytest.main(pytest_args)
        
        # Parse results
        results = {"exit_code": exit_code}
        
        # Read JSON report if available
        if os.path.exists("test_results.json"):
            with open("test_results.json", "r") as f:
                results["json_report"] = json.load(f)
        
        return results
    
    def parse_test_results(self, pytest_results: Dict[str, Any]) -> List[TestResult]:
        """Parse pytest results into TestResult objects."""
        test_results = []
        
        if "json_report" in pytest_results:
            json_data = pytest_results["json_report"]
            
            for test in json_data.get("tests", []):
                # Extract service name from test path
                service = "unknown"
                if "test_e2e_conversation_flow" in test["nodeid"]:
                    service = "cross_service"
                elif "test_performance_integration" in test["nodeid"]:
                    service = "performance"
                elif "test_security_integration" in test["nodeid"]:
                    service = "security"
                
                # Extract category from test name
                category = "integration"
                if "performance" in test["nodeid"].lower():
                    category = "performance"
                elif "security" in test["nodeid"].lower():
                    category = "security"
                elif "e2e" in test["nodeid"].lower():
                    category = "end_to_end"
                
                result = TestResult(
                    test_name=test["nodeid"],
                    status=test["outcome"],
                    duration=test.get("duration", 0),
                    error_message=test.get("call", {}).get("longrepr") if test["outcome"] in ["failed", "error"] else None,
                    service=service,
                    category=category
                )
                
                test_results.append(result)
        
        return test_results
    
    def generate_summary_report(self) -> TestSuiteReport:
        """Generate comprehensive test suite report."""
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        errors = sum(1 for r in self.results if r.status == "error")
        
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        return TestSuiteReport(
            start_time=self.start_time,
            end_time=self.end_time,
            total_duration=(self.end_time - self.start_time).total_seconds(),
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            success_rate=success_rate,
            service_health=self.service_health,
            test_results=self.results,
            environment_info=self.get_environment_info()
        )
    
    def generate_detailed_report(self, report: TestSuiteReport, output_file: str = "integration_test_report.json"):
        """Generate detailed JSON report."""
        report_data = asdict(report)
        
        # Convert datetime objects to strings
        report_data["start_time"] = report.start_time.isoformat()
        report_data["end_time"] = report.end_time.isoformat()
        
        with open(output_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"Detailed report saved to: {output_file}")
    
    def generate_html_summary(self, report: TestSuiteReport, output_file: str = "integration_summary.html"):
        """Generate HTML summary report."""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integration Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; text-align: center; }}
        .success {{ background-color: #d4edda; }}
        .warning {{ background-color: #fff3cd; }}
        .danger {{ background-color: #f8d7da; }}
        .service-health {{ margin-bottom: 30px; }}
        .service {{ display: inline-block; margin: 5px; padding: 10px; border-radius: 5px; }}
        .service.healthy {{ background-color: #d4edda; }}
        .service.unhealthy {{ background-color: #f8d7da; }}
        .test-results {{ margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .skipped {{ color: orange; }}
        .error {{ color: darkred; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Integration Test Report</h1>
        <p><strong>Test Run:</strong> {report.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {report.end_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Duration:</strong> {report.total_duration:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <div class="summary-card {'success' if report.success_rate >= 95 else 'warning' if report.success_rate >= 80 else 'danger'}">
            <h3>Success Rate</h3>
            <p>{report.success_rate:.1f}%</p>
        </div>
        <div class="summary-card">
            <h3>Total Tests</h3>
            <p>{report.total_tests}</p>
        </div>
        <div class="summary-card success">
            <h3>Passed</h3>
            <p>{report.passed}</p>
        </div>
        <div class="summary-card danger">
            <h3>Failed</h3>
            <p>{report.failed}</p>
        </div>
        <div class="summary-card warning">
            <h3>Skipped</h3>
            <p>{report.skipped}</p>
        </div>
        <div class="summary-card danger">
            <h3>Errors</h3>
            <p>{report.errors}</p>
        </div>
    </div>
    
    <div class="service-health">
        <h2>Service Health Status</h2>
        {"".join([f'<div class="service {health.status}"><strong>{health.service_name}</strong><br>Status: {health.status}<br>{"Response: " + str(health.response_time) + "ms" if health.response_time else ""}</div>' for health in report.service_health])}
    </div>
    
    <div class="test-results">
        <h2>Test Results by Category</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Category</th>
                    <th>Service</th>
                    <th>Status</th>
                    <th>Duration (s)</th>
                    <th>Error</th>
                </tr>
            </thead>
            <tbody>
                {"".join([f'<tr><td>{result.test_name}</td><td>{result.category}</td><td>{result.service}</td><td class="{result.status}">{result.status}</td><td>{result.duration:.3f}</td><td>{result.error_message[:100] + "..." if result.error_message and len(result.error_message) > 100 else result.error_message or ""}</td></tr>' for result in report.test_results])}
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        
        with open(output_file, "w") as f:
            f.write(html_content)
        
        print(f"HTML summary saved to: {output_file}")
    
    def print_console_summary(self, report: TestSuiteReport):
        """Print summary to console."""
        print("\n" + "="*80)
        print("INTEGRATION TEST SUMMARY")
        print("="*80)
        print(f"Test Run: {report.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {report.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {report.total_duration:.2f} seconds")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed}")
        print(f"Failed: {report.failed}")
        print(f"Skipped: {report.skipped}")
        print(f"Errors: {report.errors}")
        print(f"Success Rate: {report.success_rate:.1f}%")
        
        print("\nService Health:")
        for health in report.service_health:
            status_indicator = "✓" if health.status == "healthy" else "✗"
            response_info = f" ({health.response_time:.3f}s)" if health.response_time else ""
            print(f"  {status_indicator} {health.service_name}: {health.status}{response_info}")
        
        if report.failed > 0 or report.errors > 0:
            print("\nFailed/Error Tests:")
            for result in report.test_results:
                if result.status in ["failed", "error"]:
                    print(f"  ✗ {result.test_name} ({result.status})")
                    if result.error_message:
                        print(f"    Error: {result.error_message[:200]}...")
        
        print("="*80)
    
    async def run_integration_tests(
        self,
        test_paths: List[str],
        markers: Optional[List[str]] = None,
        skip_health_check: bool = False
    ) -> TestSuiteReport:
        """Run complete integration test suite."""
        print("Starting integration test suite...")
        self.start_time = datetime.utcnow()
        
        # Check service health
        if not skip_health_check:
            print("Checking service health...")
            health_results = await self.check_service_health()
            
            healthy_services = [name for name, status in health_results.items() if status.status == "healthy"]
            unhealthy_services = [name for name, status in health_results.items() if status.status != "healthy"]
            
            print(f"Healthy services: {', '.join(healthy_services)}")
            if unhealthy_services:
                print(f"Unhealthy services: {', '.join(unhealthy_services)}")
                print("Warning: Some services are unhealthy. Tests may fail or be skipped.")
        
        # Run tests
        print("Running integration tests...")
        pytest_results = self.run_pytest_with_reporting(test_paths, markers)
        
        # Parse results
        self.results = self.parse_test_results(pytest_results)
        self.end_time = datetime.utcnow()
        
        # Generate report
        report = self.generate_summary_report()
        
        return report


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Integration Test Runner")
    parser.add_argument("--config", default="test_config.json", help="Test configuration file")
    parser.add_argument("--paths", nargs="+", default=["tests/integration/"], help="Test paths to run")
    parser.add_argument("--markers", nargs="+", help="Pytest markers to filter tests")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip service health check")
    parser.add_argument("--output-dir", default=".", help="Output directory for reports")
    
    args = parser.parse_args()
    
    # Load configuration
    config_file = args.config
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
    else:
        # Default configuration
        config = {
            "api_gateway": {"host": "localhost", "port": 8000},
            "nlp_engine": {"host": "localhost", "port": 8001},
            "visualization": {"host": "localhost", "port": 8002},
            "alert_manager": {"host": "localhost", "port": 8003},
            "email_service": {"host": "localhost", "port": 8006},
            "webhook_service": {"host": "localhost", "port": 8007},
            "slack_bot": {"host": "localhost", "port": 8004},
            "teams_bot": {"host": "localhost", "port": 8005}
        }
    
    # Run tests
    async def run_tests():
        runner = IntegrationTestRunner(config)
        report = await runner.run_integration_tests(
            test_paths=args.paths,
            markers=args.markers,
            skip_health_check=args.skip_health_check
        )
        
        # Generate reports
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        runner.generate_detailed_report(report, str(output_dir / "integration_test_report.json"))
        runner.generate_html_summary(report, str(output_dir / "integration_summary.html"))
        runner.print_console_summary(report)
        
        # Exit with appropriate code
        if report.failed > 0 or report.errors > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    # Run async main
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()