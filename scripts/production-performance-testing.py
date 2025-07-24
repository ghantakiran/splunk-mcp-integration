#!/usr/bin/env python3
"""
Production Performance Testing Suite for Splunk MCP Integration
Comprehensive load testing, stress testing, and performance optimization for production deployment.
"""

import asyncio
import aiohttp
import time
import json
import sys
import argparse
import logging
import statistics
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import psutil
import yaml
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance-test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result data structure"""
    endpoint: str
    method: str
    response_time: float
    status_code: int
    success: bool
    error_message: str = ""
    timestamp: float = 0

@dataclass
class PerformanceMetrics:
    """Performance metrics aggregation"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    median_response_time: float
    percentile_95: float
    percentile_99: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    error_rate: float
    start_time: float
    end_time: float
    duration: float

class PerformanceTester:
    """Main performance testing class"""
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.results: List[TestResult] = []
        self.session: aiohttp.ClientSession = None
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        default_config = {
            'base_url': 'http://localhost:8000',
            'endpoints': [
                {'path': '/health', 'method': 'GET', 'weight': 10},
                {'path': '/api/v1/auth/login', 'method': 'POST', 'weight': 5, 'data': {'username': 'test', 'password': 'test'}},
                {'path': '/api/v1/nlp/query', 'method': 'POST', 'weight': 20, 'data': {'query': 'show me errors from last hour'}},
                {'path': '/api/v1/visualization/charts', 'method': 'GET', 'weight': 15},
                {'path': '/api/v1/dashboards', 'method': 'GET', 'weight': 10},
                {'path': '/api/v1/alerts', 'method': 'GET', 'weight': 8},
            ],
            'authentication': {
                'enabled': True,
                'token_endpoint': '/api/v1/auth/login',
                'username': 'testuser',
                'password': 'testpass123'
            },
            'load_test': {
                'concurrent_users': [1, 5, 10, 25, 50, 100],
                'duration_seconds': 60,
                'ramp_up_seconds': 10
            },
            'stress_test': {
                'max_concurrent_users': 500,
                'step_size': 25,
                'step_duration': 30
            },
            'spike_test': {
                'normal_load': 10,
                'spike_load': 100,
                'spike_duration': 30
            },
            'thresholds': {
                'max_response_time': 3.0,
                'max_error_rate': 0.05,
                'min_throughput': 100
            }
        }
        
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    file_config = yaml.safe_load(f)
                    default_config.update(file_config)
            except Exception as e:
                logger.warning(f"Could not load config file {config_file}: {e}")
                
        return default_config
    
    async def _authenticate(self) -> str:
        """Authenticate and get JWT token"""
        if not self.config['authentication']['enabled']:
            return None
            
        auth_url = f"{self.config['base_url']}{self.config['authentication']['token_endpoint']}"
        auth_data = {
            'username': self.config['authentication']['username'],
            'password': self.config['authentication']['password']
        }
        
        try:
            async with self.session.post(auth_url, json=auth_data) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('access_token')
                else:
                    logger.error(f"Authentication failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def _make_request(self, endpoint: Dict[str, Any], token: str = None) -> TestResult:
        """Make a single HTTP request and measure performance"""
        url = f"{self.config['base_url']}{endpoint['path']}"
        method = endpoint['method'].upper()
        data = endpoint.get('data', {})
        
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        start_time = time.time()
        
        try:
            if method == 'GET':
                async with self.session.get(url, headers=headers) as response:
                    await response.text()  # Consume response
                    response_time = time.time() - start_time
                    return TestResult(
                        endpoint=endpoint['path'],
                        method=method,
                        response_time=response_time,
                        status_code=response.status,
                        success=200 <= response.status < 300,
                        timestamp=start_time
                    )
            else:
                async with self.session.request(method, url, headers=headers, json=data) as response:
                    await response.text()  # Consume response
                    response_time = time.time() - start_time
                    return TestResult(
                        endpoint=endpoint['path'],
                        method=method,
                        response_time=response_time,
                        status_code=response.status,
                        success=200 <= response.status < 300,
                        timestamp=start_time
                    )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint=endpoint['path'],
                method=method,
                response_time=response_time,
                status_code=0,
                success=False,
                error_message=str(e),
                timestamp=start_time
            )
    
    async def _run_load_test_worker(self, user_id: int, duration: float, token: str = None):
        """Worker function for individual user load testing"""
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # Select endpoint based on weight
            endpoint = self._select_weighted_endpoint()
            result = await self._make_request(endpoint, token)
            self.results.append(result)
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)
    
    def _select_weighted_endpoint(self) -> Dict[str, Any]:
        """Select endpoint based on configured weights"""
        import random
        
        endpoints = self.config['endpoints']
        weights = [ep.get('weight', 1) for ep in endpoints]
        return random.choices(endpoints, weights=weights)[0]
    
    async def run_load_test(self, concurrent_users: int, duration: int) -> PerformanceMetrics:
        """Run load test with specified concurrent users"""
        logger.info(f"Starting load test: {concurrent_users} users for {duration}s")
        
        # Clear previous results
        self.results = []
        start_time = time.time()
        
        # Authenticate once
        token = await self._authenticate()
        
        # Create tasks for concurrent users
        tasks = []
        for user_id in range(concurrent_users):
            task = asyncio.create_task(
                self._run_load_test_worker(user_id, duration, token)
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Calculate metrics
        return self._calculate_metrics(start_time, end_time)
    
    async def run_stress_test(self) -> List[PerformanceMetrics]:
        """Run stress test with gradually increasing load"""
        logger.info("Starting stress test")
        
        stress_config = self.config['stress_test']
        max_users = stress_config['max_concurrent_users']
        step_size = stress_config['step_size']
        step_duration = stress_config['step_duration']
        
        results = []
        
        for users in range(step_size, max_users + 1, step_size):
            logger.info(f"Stress test step: {users} users")
            metrics = await self.run_load_test(users, step_duration)
            results.append(metrics)
            
            # Check if system is failing
            if metrics.error_rate > 0.5 or metrics.average_response_time > 10:
                logger.warning(f"System degradation detected at {users} users")
                break
                
            # Brief pause between steps
            await asyncio.sleep(5)
        
        return results
    
    async def run_spike_test(self) -> Tuple[PerformanceMetrics, PerformanceMetrics]:
        """Run spike test to test system resilience"""
        logger.info("Starting spike test")
        
        spike_config = self.config['spike_test']
        normal_load = spike_config['normal_load']
        spike_load = spike_config['spike_load']
        spike_duration = spike_config['spike_duration']
        
        # Normal load phase
        logger.info(f"Spike test: Normal load ({normal_load} users)")
        normal_metrics = await self.run_load_test(normal_load, 30)
        
        # Spike phase
        logger.info(f"Spike test: Spike load ({spike_load} users)")
        spike_metrics = await self.run_load_test(spike_load, spike_duration)
        
        return normal_metrics, spike_metrics
    
    def _calculate_metrics(self, start_time: float, end_time: float) -> PerformanceMetrics:
        """Calculate performance metrics from test results"""
        if not self.results:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, start_time, end_time, end_time - start_time)
        
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]
        
        response_times = [r.response_time for r in self.results]
        successful_response_times = [r.response_time for r in successful_results]
        
        total_requests = len(self.results)
        successful_requests = len(successful_results)
        failed_requests = len(failed_results)
        duration = end_time - start_time
        
        return PerformanceMetrics(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=statistics.mean(response_times) if response_times else 0,
            median_response_time=statistics.median(response_times) if response_times else 0,
            percentile_95=self._percentile(response_times, 95) if response_times else 0,
            percentile_99=self._percentile(response_times, 99) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            requests_per_second=total_requests / duration if duration > 0 else 0,
            error_rate=failed_requests / total_requests if total_requests > 0 else 0,
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _check_thresholds(self, metrics: PerformanceMetrics) -> Dict[str, bool]:
        """Check if metrics meet performance thresholds"""
        thresholds = self.config['thresholds']
        
        return {
            'response_time': metrics.average_response_time <= thresholds['max_response_time'],
            'error_rate': metrics.error_rate <= thresholds['max_error_rate'],
            'throughput': metrics.requests_per_second >= thresholds['min_throughput']
        }
    
    def generate_report(self, test_results: Dict[str, Any]) -> str:
        """Generate comprehensive performance test report"""
        report = []
        report.append("=" * 80)
        report.append("SPLUNK MCP INTEGRATION - PERFORMANCE TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # System information
        report.append("SYSTEM INFORMATION:")
        report.append("-" * 40)
        report.append(f"CPU Cores: {psutil.cpu_count()}")
        report.append(f"Memory: {psutil.virtual_memory().total // (1024**3)} GB")
        report.append(f"Base URL: {self.config['base_url']}")
        report.append("")
        
        # Test configuration
        report.append("TEST CONFIGURATION:")
        report.append("-" * 40)
        report.append(f"Endpoints tested: {len(self.config['endpoints'])}")
        report.append(f"Authentication: {'Enabled' if self.config['authentication']['enabled'] else 'Disabled'}")
        report.append("")
        
        # Load test results
        if 'load_test' in test_results:
            report.append("LOAD TEST RESULTS:")
            report.append("-" * 40)
            for users, metrics in test_results['load_test'].items():
                thresholds = self._check_thresholds(metrics)
                status = "✓" if all(thresholds.values()) else "✗"
                
                report.append(f"{status} {users} concurrent users:")
                report.append(f"    Requests: {metrics.total_requests} (Success: {metrics.successful_requests}, Failed: {metrics.failed_requests})")
                report.append(f"    Response Time: Avg={metrics.average_response_time:.3f}s, 95th={metrics.percentile_95:.3f}s, 99th={metrics.percentile_99:.3f}s")
                report.append(f"    Throughput: {metrics.requests_per_second:.1f} req/s")
                report.append(f"    Error Rate: {metrics.error_rate:.1%}")
                report.append("")
        
        # Stress test results
        if 'stress_test' in test_results:
            report.append("STRESS TEST RESULTS:")
            report.append("-" * 40)
            stress_results = test_results['stress_test']
            
            # Find breaking point
            breaking_point = None
            for i, metrics in enumerate(stress_results):
                if metrics.error_rate > 0.1 or metrics.average_response_time > 5.0:
                    breaking_point = (i + 1) * self.config['stress_test']['step_size']
                    break
            
            if breaking_point:
                report.append(f"Breaking point detected at: {breaking_point} concurrent users")
            else:
                report.append("No breaking point detected within test range")
            
            report.append(f"Maximum tested load: {len(stress_results) * self.config['stress_test']['step_size']} users")
            report.append("")
        
        # Spike test results
        if 'spike_test' in test_results:
            report.append("SPIKE TEST RESULTS:")
            report.append("-" * 40)
            normal, spike = test_results['spike_test']
            
            report.append("Normal Load:")
            report.append(f"    Response Time: {normal.average_response_time:.3f}s")
            report.append(f"    Error Rate: {normal.error_rate:.1%}")
            report.append("")
            
            report.append("Spike Load:")
            report.append(f"    Response Time: {spike.average_response_time:.3f}s")
            report.append(f"    Error Rate: {spike.error_rate:.1%}")
            
            # Calculate degradation
            response_degradation = (spike.average_response_time - normal.average_response_time) / normal.average_response_time * 100
            error_increase = spike.error_rate - normal.error_rate
            
            report.append("")
            report.append(f"Performance degradation: {response_degradation:.1f}%")
            report.append(f"Error rate increase: {error_increase:.1%}")
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 40)
        
        # Analyze load test results for recommendations
        if 'load_test' in test_results:
            max_successful_users = 0
            for users, metrics in test_results['load_test'].items():
                thresholds = self._check_thresholds(metrics)
                if all(thresholds.values()):
                    max_successful_users = users
            
            report.append(f"• Maximum recommended concurrent users: {max_successful_users}")
            report.append(f"• Current configuration can handle up to {max_successful_users} users with acceptable performance")
        
        # Performance optimization recommendations
        report.append("• Consider implementing connection pooling for database connections")
        report.append("• Enable response caching for frequently accessed endpoints")
        report.append("• Monitor memory usage and garbage collection performance")
        report.append("• Consider horizontal scaling for loads exceeding current capacity")
        report.append("")
        
        # Thresholds summary
        report.append("PERFORMANCE THRESHOLDS:")
        report.append("-" * 40)
        thresholds = self.config['thresholds']
        report.append(f"Maximum Response Time: {thresholds['max_response_time']}s")
        report.append(f"Maximum Error Rate: {thresholds['max_error_rate']:.1%}")
        report.append(f"Minimum Throughput: {thresholds['min_throughput']} req/s")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive performance testing suite"""
        logger.info("Starting comprehensive performance testing")
        
        # Initialize session
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            results = {}
            
            # Load testing
            logger.info("Running load tests...")
            load_test_results = {}
            for users in self.config['load_test']['concurrent_users']:
                metrics = await self.run_load_test(users, self.config['load_test']['duration_seconds'])
                load_test_results[users] = metrics
                
                # Log progress
                thresholds = self._check_thresholds(metrics)
                status = "PASS" if all(thresholds.values()) else "FAIL"
                logger.info(f"Load test {users} users: {status} (Avg: {metrics.average_response_time:.3f}s, Error: {metrics.error_rate:.1%})")
            
            results['load_test'] = load_test_results
            
            # Stress testing
            logger.info("Running stress test...")
            stress_results = await self.run_stress_test()
            results['stress_test'] = stress_results
            
            # Spike testing
            logger.info("Running spike test...")
            normal_metrics, spike_metrics = await self.run_spike_test()
            results['spike_test'] = (normal_metrics, spike_metrics)
            
            return results
            
        finally:
            await self.session.close()

def check_system_resources():
    """Check system resources before testing"""
    logger.info("Checking system resources...")
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    logger.info(f"CPU usage: {cpu_percent}%")
    
    # Memory usage
    memory = psutil.virtual_memory()
    logger.info(f"Memory usage: {memory.percent}% ({memory.used // (1024**3)}GB used / {memory.total // (1024**3)}GB total)")
    
    # Disk usage
    disk = psutil.disk_usage('/')
    logger.info(f"Disk usage: {disk.percent}% ({disk.used // (1024**3)}GB used / {disk.total // (1024**3)}GB total)")
    
    # Network connections
    connections = len(psutil.net_connections())
    logger.info(f"Network connections: {connections}")
    
    # Warnings
    if cpu_percent > 80:
        logger.warning("High CPU usage detected - may affect test results")
    if memory.percent > 80:
        logger.warning("High memory usage detected - may affect test results")
    if disk.percent > 90:
        logger.warning("High disk usage detected - may affect test results")

def check_service_health(base_url: str):
    """Check service health before testing"""
    import requests
    
    logger.info("Checking service health...")
    
    health_endpoints = [
        f"{base_url}/health",
        f"{base_url}/api/v1/nlp/health",
        f"{base_url}/api/v1/visualization/health",
        f"{base_url}/api/v1/alerts/health"
    ]
    
    for endpoint in health_endpoints:
        try:
            response = requests.get(endpoint, timeout=5)
            if response.status_code == 200:
                logger.info(f"✓ {endpoint} - Healthy")
            else:
                logger.warning(f"✗ {endpoint} - Status: {response.status_code}")
        except Exception as e:
            logger.error(f"✗ {endpoint} - Error: {e}")

async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Splunk MCP Performance Testing Suite")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--base-url", "-u", default="http://localhost:8000", help="Base URL for testing")
    parser.add_argument("--test-type", "-t", choices=["load", "stress", "spike", "all"], default="all", help="Test type to run")
    parser.add_argument("--users", "-n", type=int, help="Number of concurrent users (for load test)")
    parser.add_argument("--duration", "-d", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--output", "-o", help="Output file for results")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip health checks")
    
    args = parser.parse_args()
    
    # System checks
    if not args.skip_health_check:
        check_system_resources()
        check_service_health(args.base_url)
    
    # Initialize tester
    tester = PerformanceTester(args.config)
    if args.base_url:
        tester.config['base_url'] = args.base_url
    
    try:
        if args.test_type == "load" and args.users:
            # Single load test
            metrics = await tester.run_load_test(args.users, args.duration)
            results = {'load_test': {args.users: metrics}}
        elif args.test_type == "stress":
            # Stress test only
            stress_results = await tester.run_stress_test()
            results = {'stress_test': stress_results}
        elif args.test_type == "spike":
            # Spike test only
            normal, spike = await tester.run_spike_test()
            results = {'spike_test': (normal, spike)}
        else:
            # Comprehensive testing
            results = await tester.run_comprehensive_test()
        
        # Generate report
        report = tester.generate_report(results)
        print(report)
        
        # Save results
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            logger.info(f"Results saved to: {args.output}")
        
        # Save detailed results as JSON
        json_output = args.output.replace('.txt', '.json') if args.output else 'performance-results.json'
        with open(json_output, 'w') as f:
            # Convert dataclasses to dict for JSON serialization
            json_results = {}
            for test_type, test_data in results.items():
                if test_type == 'load_test':
                    json_results[test_type] = {str(k): asdict(v) for k, v in test_data.items()}
                elif test_type == 'stress_test':
                    json_results[test_type] = [asdict(m) for m in test_data]
                elif test_type == 'spike_test':
                    json_results[test_type] = [asdict(test_data[0]), asdict(test_data[1])]
            json.dump(json_results, f, indent=2)
        logger.info(f"Detailed results saved to: {json_output}")
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())