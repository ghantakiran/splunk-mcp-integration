#!/usr/bin/env python3
"""
Test runner script for rate limiting system

Provides convenient test execution with different test suites and reporting options.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List


def run_command(command: List[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {command[0]}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run rate limiting tests")
    parser.add_argument(
        "--suite", 
        choices=["unit", "integration", "performance", "all"],
        default="unit",
        help="Test suite to run"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests"
    )
    parser.add_argument(
        "--redis-required",
        action="store_true",
        help="Include tests that require Redis"
    )
    parser.add_argument(
        "--output-format",
        choices=["default", "junit", "json"],
        default="default",
        help="Test output format"
    )
    parser.add_argument(
        "--parallel", "-n",
        type=int,
        help="Number of parallel workers"
    )
    
    args = parser.parse_args()
    
    # Set up base command
    base_cmd = ["python", "-m", "pytest"]
    
    # Add test paths based on suite
    if args.suite == "unit":
        test_paths = [
            "tests/test_rate_limiting.py::TestRateLimitPolicy",
            "tests/test_rate_limiting.py::TestRateLimitStatus",
            "tests/test_rate_limiting.py::TestFixedWindowRateLimiter",
            "tests/test_rate_limiting.py::TestSlidingWindowRateLimiter",
            "tests/test_rate_limiting.py::TestTokenBucketRateLimiter",
            "tests/test_rate_limiting.py::TestRateLimitManager",
            "tests/test_rate_limiting.py::TestRateLimitUtilities"
        ]
        markers = ["-m", "unit"]
    elif args.suite == "integration":
        test_paths = [
            "tests/test_rate_limiting.py::TestRateLimitingIntegration",
            "tests/test_rate_limiting_middleware.py::TestRateLimitingMiddlewareIntegration"
        ]
        markers = ["-m", "integration"]
    elif args.suite == "performance":
        test_paths = ["tests/test_rate_limiting_performance.py"]
        markers = ["-m", "performance"]
    else:  # all
        test_paths = ["tests/"]
        markers = []
    
    # Build command
    cmd = base_cmd + test_paths
    
    # Add markers
    if markers:
        cmd.extend(markers)
    
    # Add Redis marker if not required
    if not args.redis_required:
        if markers:
            cmd.extend(["and", "not", "redis"])
        else:
            cmd.extend(["-m", "not redis"])
    
    # Add fast filter
    if args.fast:
        if "not" in cmd:
            cmd.extend(["and", "not", "slow"])
        else:
            cmd.extend(["-m", "not slow"])
    
    # Add verbosity
    if args.verbose:
        cmd.extend(["-v", "-s"])
    
    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])
    
    # Add coverage
    if args.coverage:
        cmd.extend([
            "--cov=app/core/rate_limiting",
            "--cov=app/middleware/rate_limiting",
            "--cov=app/api/v1/endpoints/rate_limits",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-fail-under=85"
        ])
    
    # Add output format
    if args.output_format == "junit":
        cmd.extend(["--junit-xml=test-results.xml"])
    elif args.output_format == "json":
        cmd.extend(["--json-report", "--json-report-file=test-results.json"])
    
    # Add other useful options
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--strict-config"
    ])
    
    # Change to project directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print(f"🚀 Running test suite: {args.suite}")
    print(f"📁 Working directory: {project_root}")
    print(f"🔧 Python path: {sys.executable}")
    
    # Check if Redis is available if needed
    if args.redis_required or args.suite in ["integration", "performance", "all"]:
        redis_check = ["redis-cli", "ping"]
        try:
            result = subprocess.run(redis_check, capture_output=True, text=True, timeout=5)
            if result.returncode != 0 or "PONG" not in result.stdout:
                print("⚠️  Redis is not available. Some tests may be skipped.")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠️  Could not check Redis availability. Some tests may fail.")
    
    # Run the tests
    success = run_command(cmd, f"Test suite: {args.suite}")
    
    if success:
        print(f"\n🎉 All tests passed!")
        
        # Additional reporting
        if args.coverage:
            print(f"\n📊 Coverage report generated: htmlcov/index.html")
        
        if args.output_format == "junit":
            print(f"📄 JUnit XML report: test-results.xml")
        elif args.output_format == "json":
            print(f"📄 JSON report: test-results.json")
    else:
        print(f"\n💥 Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()