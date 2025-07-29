#!/usr/bin/env python3
"""
Performance Testing Automation Framework for Splunk MCP Platform
================================================================
Comprehensive load testing suite with distributed testing capabilities
"""

import asyncio
import aiohttp
import json
import time
import statistics
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import logging
import yaml
import psutil
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'performance-test-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestConfiguration:
    """Performance test configuration"""
    base_url: str = "http://localhost:8000"
    concurrent_users: int = 10
    test_duration: int = 60
    ramp_up_time: int = 10
    think_time: float = 1.0
    timeout: int = 30
    max_requests_per_second: int = 100
    
@dataclass
class TestMetrics:
    """Performance test metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = None
    error_rates: Dict[str, int] = None
    throughput: float = 0.0
    start_time: datetime = None
    end_time: datetime = None
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
        if self.error_rates is None:
            self.error_rates = {}

@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_usage: List[float] = None
    memory_usage: List[float] = None
    disk_io: List[Dict] = None
    network_io: List[Dict] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.cpu_usage is None:
            self.cpu_usage = []
        if self.memory_usage is None:
            self.memory_usage = []
        if self.disk_io is None:
            self.disk_io = []
        if self.network_io is None:
            self.network_io = []

class PerformanceTestSuite:
    """Main performance testing suite"""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.metrics = TestMetrics()
        self.system_metrics = SystemMetrics()
        self.session = None
        self.test_scenarios = []
        self.monitoring_task = None
        
    async def setup_session(self):
        """Setup HTTP session with connection pooling"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=50,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Splunk-MCP-Performance-Test/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )
        
    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
            
    async def authenticate_user(self, username: str = "test_user", password: str = "test_password") -> Optional[str]:
        """Authenticate and get JWT token"""
        try:
            auth_data = {
                "username": username,
                "password": password
            }
            
            async with self.session.post(
                f"{self.config.base_url}/api/v1/auth/login",
                json=auth_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('access_token')
                else:
                    logger.error(f"Authentication failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
            
    async def make_request(self, method: str, endpoint: str, data: Dict = None, 
                          headers: Dict = None, token: str = None) -> Tuple[int, float, Dict]:
        """Make HTTP request and measure response time"""
        url = f"{self.config.base_url}{endpoint}"
        
        # Prepare headers
        request_headers = headers or {}
        if token:
            request_headers['Authorization'] = f'Bearer {token}'
            
        start_time = time.time()
        
        try:
            async with self.session.request(
                method,
                url,
                json=data,
                headers=request_headers
            ) as response:
                response_data = await response.text()
                end_time = time.time()
                
                response_time = end_time - start_time
                
                # Try to parse JSON response
                try:
                    parsed_data = json.loads(response_data)
                except:
                    parsed_data = {"raw_response": response_data}
                
                return response.status, response_time, parsed_data
                
        except asyncio.TimeoutError:
            end_time = time.time()
            return 408, end_time - start_time, {"error": "timeout"}
        except Exception as e:
            end_time = time.time()
            return 500, end_time - start_time, {"error": str(e)}
            
    async def health_check_test(self, token: str = None) -> Dict:
        """Test health endpoints"""
        logger.info("Running health check performance test...")
        
        endpoints = [
            "/health",
            "/api/v1/health",
            "/api/v1/status"
        ]
        
        results = {}
        
        for endpoint in endpoints:
            response_times = []
            success_count = 0
            
            for _ in range(self.config.concurrent_users):
                status, response_time, data = await self.make_request("GET", endpoint, token=token)
                response_times.append(response_time)
                
                if status == 200:
                    success_count += 1
                    
            results[endpoint] = {
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "success_rate": success_count / len(response_times) * 100,
                "total_requests": len(response_times)
            }
            
        return results
        
    async def api_stress_test(self, token: str) -> Dict:
        """Stress test API endpoints"""
        logger.info("Running API stress test...")
        
        # Define test scenarios
        scenarios = [
            ("GET", "/api/v1/user/profile", None),
            ("GET", "/api/v1/queries/history", None),
            ("POST", "/api/v1/queries/nlp", {"query": "show me error logs from last hour"}),
            ("POST", "/api/v1/chat/message", {"message": "What are the top errors today?"}),
            ("GET", "/api/v1/dashboards", None),
        ]
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.config.concurrent_users)
        
        async def execute_scenario(scenario):
            async with semaphore:
                method, endpoint, data = scenario
                status, response_time, response_data = await self.make_request(
                    method, endpoint, data, token=token
                )
                
                return {
                    "endpoint": endpoint,
                    "method": method,
                    "status": status,
                    "response_time": response_time,
                    "success": status < 400
                }
        
        # Run scenarios multiple times
        tasks = []
        for _ in range(self.config.concurrent_users * 2):
            for scenario in scenarios:
                tasks.append(execute_scenario(scenario))
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        endpoint_metrics = {}
        for result in results:
            if isinstance(result, dict):
                endpoint = result["endpoint"]
                if endpoint not in endpoint_metrics:
                    endpoint_metrics[endpoint] = {
                        "response_times": [],
                        "success_count": 0,
                        "total_count": 0
                    }
                
                endpoint_metrics[endpoint]["response_times"].append(result["response_time"])
                endpoint_metrics[endpoint]["total_count"] += 1
                
                if result["success"]:
                    endpoint_metrics[endpoint]["success_count"] += 1
                    
        # Calculate statistics
        for endpoint, metrics in endpoint_metrics.items():
            response_times = metrics["response_times"]
            metrics.update({
                "avg_response_time": statistics.mean(response_times),
                "median_response_time": statistics.median(response_times),
                "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "success_rate": metrics["success_count"] / metrics["total_count"] * 100
            })
            del metrics["response_times"]  # Remove raw data for cleaner output
            
        return endpoint_metrics
        
    async def nlp_performance_test(self, token: str) -> Dict:
        """Test NLP engine performance with various query types"""
        logger.info("Running NLP engine performance test...")
        
        # Test queries of varying complexity
        test_queries = [
            "show me errors",
            "what are the top 10 errors in the last hour?",
            "find all authentication failures from users in the last 24 hours and group by source IP",
            "create a dashboard showing error trends over time with alerts for spikes above 100 errors per minute",
            "analyze user activity patterns and identify anomalies in login behavior across different time zones",
        ]
        
        results = {}
        
        for i, query in enumerate(test_queries):
            query_type = f"query_complexity_{i+1}"
            response_times = []
            success_count = 0
            processing_times = []
            
            # Run each query multiple times
            for _ in range(5):
                start_time = time.time()
                
                status, response_time, data = await self.make_request(
                    "POST",
                    "/api/v1/queries/nlp",
                    {"query": query},
                    token=token
                )
                
                response_times.append(response_time)
                
                if status == 200:
                    success_count += 1
                    # Extract processing time if available
                    if isinstance(data, dict) and "processing_time" in data:
                        processing_times.append(data["processing_time"])
                        
            results[query_type] = {
                "query": query,
                "avg_response_time": statistics.mean(response_times),
                "max_response_time": max(response_times),
                "success_rate": success_count / len(response_times) * 100,
                "avg_processing_time": statistics.mean(processing_times) if processing_times else None,
                "query_length": len(query)
            }
            
        return results
        
    async def concurrent_user_simulation(self, token: str) -> Dict:
        """Simulate concurrent user behavior"""
        logger.info(f"Simulating {self.config.concurrent_users} concurrent users...")
        
        async def user_session():
            """Simulate a single user session"""
            session_metrics = {
                "requests": 0,
                "successful_requests": 0,
                "total_response_time": 0,
                "errors": []
            }
            
            # Simulate user workflow
            user_actions = [
                ("GET", "/api/v1/user/profile"),
                ("GET", "/api/v1/dashboards"),
                ("POST", "/api/v1/chat/message", {"message": "Show me system health"}),
                ("POST", "/api/v1/queries/nlp", {"query": "errors in last hour"}),
                ("GET", "/api/v1/queries/history"),
            ]
            
            for action in user_actions:
                method, endpoint = action[:2]
                data = action[2] if len(action) > 2 else None
                
                status, response_time, response_data = await self.make_request(
                    method, endpoint, data, token=token
                )
                
                session_metrics["requests"] += 1
                session_metrics["total_response_time"] += response_time
                
                if status < 400:
                    session_metrics["successful_requests"] += 1
                else:
                    session_metrics["errors"].append({
                        "endpoint": endpoint,
                        "status": status,
                        "response_time": response_time
                    })
                
                # Simulate think time
                await asyncio.sleep(self.config.think_time)
                
            return session_metrics
            
        # Run concurrent user sessions
        tasks = [user_session() for _ in range(self.config.concurrent_users)]
        session_results = await asyncio.gather(*tasks)
        
        # Aggregate results
        total_requests = sum(r["requests"] for r in session_results)
        total_successful = sum(r["successful_requests"] for r in session_results)
        total_response_time = sum(r["total_response_time"] for r in session_results)
        all_errors = [error for r in session_results for error in r["errors"]]
        
        return {
            "concurrent_users": self.config.concurrent_users,
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_requests - total_successful,
            "success_rate": (total_successful / total_requests * 100) if total_requests > 0 else 0,
            "avg_response_time": (total_response_time / total_requests) if total_requests > 0 else 0,
            "total_errors": len(all_errors),
            "error_distribution": self._analyze_errors(all_errors)
        }
        
    def _analyze_errors(self, errors: List[Dict]) -> Dict:
        """Analyze error distribution"""
        error_counts = {}
        for error in errors:
            status = error.get("status", "unknown")
            error_counts[status] = error_counts.get(status, 0) + 1
        return error_counts
        
    async def database_performance_test(self) -> Dict:
        """Test database performance"""
        logger.info("Running database performance test...")
        
        try:
            # Test database connection and query performance
            db_test_script = """
import asyncio
import asyncpg
import time
import os

async def test_db_performance():
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/splunk_mcp')
    
    # Connection test
    start_time = time.time()
    conn = await asyncpg.connect(DATABASE_URL)
    connection_time = time.time() - start_time
    
    # Simple query test
    start_time = time.time()
    result = await conn.fetch('SELECT 1')
    simple_query_time = time.time() - start_time
    
    # Complex query test (if tables exist)
    try:
        start_time = time.time()
        result = await conn.fetch('SELECT COUNT(*) FROM users')
        complex_query_time = time.time() - start_time
    except:
        complex_query_time = None
    
    await conn.close()
    
    return {
        'connection_time': connection_time,
        'simple_query_time': simple_query_time,
        'complex_query_time': complex_query_time
    }

print(asyncio.run(test_db_performance()))
"""
            
            # Execute database test
            result = subprocess.run(
                ["python", "-c", db_test_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return eval(result.stdout.strip())
            else:
                return {"error": f"Database test failed: {result.stderr}"}
                
        except Exception as e:
            return {"error": f"Database performance test error: {str(e)}"}
            
    def start_system_monitoring(self):
        """Start system resource monitoring"""
        async def monitor_resources():
            while True:
                try:
                    # CPU usage
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.system_metrics.cpu_usage.append(cpu_percent)
                    
                    # Memory usage
                    memory = psutil.virtual_memory()
                    self.system_metrics.memory_usage.append(memory.percent)
                    
                    # Disk I/O
                    disk_io = psutil.disk_io_counters()
                    if disk_io:
                        self.system_metrics.disk_io.append({
                            'read_bytes': disk_io.read_bytes,
                            'write_bytes': disk_io.write_bytes,
                            'timestamp': time.time()
                        })
                    
                    # Network I/O
                    network_io = psutil.net_io_counters()
                    if network_io:
                        self.system_metrics.network_io.append({
                            'bytes_sent': network_io.bytes_sent,
                            'bytes_recv': network_io.bytes_recv,
                            'timestamp': time.time()
                        })
                    
                    await asyncio.sleep(5)  # Monitor every 5 seconds
                    
                except Exception as e:
                    logger.error(f"System monitoring error: {e}")
                    await asyncio.sleep(5)
        
        self.monitoring_task = asyncio.create_task(monitor_resources())
        
    def stop_system_monitoring(self):
        """Stop system resource monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            
    async def run_performance_tests(self) -> Dict:
        """Run complete performance test suite"""
        logger.info("Starting comprehensive performance test suite...")
        
        self.metrics.start_time = datetime.now()
        
        # Setup
        await self.setup_session()
        self.start_system_monitoring()
        
        try:
            # Authenticate
            token = await self.authenticate_user()
            if not token:
                raise Exception("Authentication failed - cannot proceed with tests")
            
            # Run test suite
            results = {
                "test_configuration": asdict(self.config),
                "test_start_time": self.metrics.start_time.isoformat(),
            }
            
            # Health check tests
            results["health_check_results"] = await self.health_check_test(token)
            
            # API stress tests
            results["api_stress_results"] = await self.api_stress_test(token)
            
            # NLP performance tests
            results["nlp_performance_results"] = await self.nlp_performance_test(token)
            
            # Concurrent user simulation
            results["concurrent_user_results"] = await self.concurrent_user_simulation(token)
            
            # Database performance tests
            results["database_performance_results"] = await self.database_performance_test()
            
            self.metrics.end_time = datetime.now()
            results["test_end_time"] = self.metrics.end_time.isoformat()
            results["total_test_duration"] = (self.metrics.end_time - self.metrics.start_time).total_seconds()
            
            # System metrics summary
            if self.system_metrics.cpu_usage:
                results["system_metrics"] = {
                    "avg_cpu_usage": statistics.mean(self.system_metrics.cpu_usage),
                    "max_cpu_usage": max(self.system_metrics.cpu_usage),
                    "avg_memory_usage": statistics.mean(self.system_metrics.memory_usage),
                    "max_memory_usage": max(self.system_metrics.memory_usage),
                    "monitoring_samples": len(self.system_metrics.cpu_usage)
                }
            
            return results
            
        finally:
            # Cleanup
            self.stop_system_monitoring()
            await self.cleanup_session()
            
    def generate_performance_report(self, results: Dict, output_file: str = None) -> str:
        """Generate performance test report"""
        if not output_file:
            output_file = f"performance-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        
        # Add performance analysis
        analysis = self._analyze_performance_results(results)
        results["performance_analysis"] = analysis
        
        # Save results
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Performance report saved to: {output_file}")
        return output_file
        
    def _analyze_performance_results(self, results: Dict) -> Dict:
        """Analyze performance test results and provide recommendations"""
        analysis = {
            "overall_performance": "unknown",
            "bottlenecks": [],
            "recommendations": [],
            "performance_score": 0
        }
        
        score = 100
        
        # Analyze API response times
        api_results = results.get("api_stress_results", {})
        slow_endpoints = []
        
        for endpoint, metrics in api_results.items():
            avg_time = metrics.get("avg_response_time", 0)
            if avg_time > 3.0:  # Slow response
                slow_endpoints.append(f"{endpoint}: {avg_time:.2f}s")
                score -= 10
            elif avg_time > 1.0:
                score -= 5
                
        if slow_endpoints:
            analysis["bottlenecks"].append("Slow API endpoints detected")
            analysis["recommendations"].append(f"Optimize slow endpoints: {', '.join(slow_endpoints)}")
        
        # Analyze success rates
        concurrent_results = results.get("concurrent_user_results", {})
        success_rate = concurrent_results.get("success_rate", 100)
        
        if success_rate < 95:
            analysis["bottlenecks"].append("Low success rate under load")
            analysis["recommendations"].append("Investigate error causes and improve error handling")
            score -= 20
        elif success_rate < 99:
            score -= 10
            
        # Analyze system resources
        system_metrics = results.get("system_metrics", {})
        max_cpu = system_metrics.get("max_cpu_usage", 0)
        max_memory = system_metrics.get("max_memory_usage", 0)
        
        if max_cpu > 90:
            analysis["bottlenecks"].append("High CPU usage detected")
            analysis["recommendations"].append("Consider CPU optimization or scaling")
            score -= 15
        
        if max_memory > 90:
            analysis["bottlenecks"].append("High memory usage detected")
            analysis["recommendations"].append("Investigate memory leaks or increase memory allocation")
            score -= 15
            
        # Determine overall performance
        analysis["performance_score"] = max(0, score)
        
        if score >= 90:
            analysis["overall_performance"] = "excellent"
        elif score >= 80:
            analysis["overall_performance"] = "good"
        elif score >= 70:
            analysis["overall_performance"] = "fair"
        else:
            analysis["overall_performance"] = "poor"
            
        return analysis
        
    def print_summary(self, results: Dict):
        """Print performance test summary"""
        print("\n" + "="*60)
        print("PERFORMANCE TEST SUMMARY")
        print("="*60)
        
        config = results.get("test_configuration", {})
        print(f"Test Duration: {results.get('total_test_duration', 0):.1f} seconds")
        print(f"Concurrent Users: {config.get('concurrent_users', 0)}")
        print(f"Base URL: {config.get('base_url', 'N/A')}")
        
        # API Performance
        api_results = results.get("api_stress_results", {})
        if api_results:
            print(f"\nAPI Performance:")
            for endpoint, metrics in api_results.items():
                print(f"  {endpoint}:")
                print(f"    Avg Response: {metrics.get('avg_response_time', 0):.3f}s")
                print(f"    Success Rate: {metrics.get('success_rate', 0):.1f}%")
        
        # Concurrent User Results
        concurrent_results = results.get("concurrent_user_results", {})
        if concurrent_results:
            print(f"\nConcurrent User Test:")
            print(f"  Total Requests: {concurrent_results.get('total_requests', 0)}")
            print(f"  Success Rate: {concurrent_results.get('success_rate', 0):.1f}%")
            print(f"  Avg Response Time: {concurrent_results.get('avg_response_time', 0):.3f}s")
        
        # System Metrics
        system_metrics = results.get("system_metrics", {})
        if system_metrics:
            print(f"\nSystem Resource Usage:")
            print(f"  Max CPU: {system_metrics.get('max_cpu_usage', 0):.1f}%")
            print(f"  Max Memory: {system_metrics.get('max_memory_usage', 0):.1f}%")
        
        # Performance Analysis
        analysis = results.get("performance_analysis", {})
        if analysis:
            print(f"\nPerformance Analysis:")
            print(f"  Overall Performance: {analysis.get('overall_performance', 'unknown').upper()}")
            print(f"  Performance Score: {analysis.get('performance_score', 0)}/100")
            
            if analysis.get("bottlenecks"):
                print(f"  Bottlenecks: {', '.join(analysis['bottlenecks'])}")
                
        print("="*60)

def load_config_from_file(config_file: str) -> TestConfiguration:
    """Load test configuration from YAML file"""
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        return TestConfiguration(**config_data)
    except Exception as e:
        logger.error(f"Failed to load config from {config_file}: {e}")
        return TestConfiguration()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Splunk MCP Performance Testing Suite')
    parser.add_argument('--base-url', default='http://localhost:8000', help='Base URL of the API')
    parser.add_argument('--users', type=int, default=10, help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--ramp-up', type=int, default=10, help='Ramp up time in seconds')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--output', help='Output report file')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    if args.config:
        config = load_config_from_file(args.config)
    else:
        config = TestConfiguration(
            base_url=args.base_url,
            concurrent_users=args.users,
            test_duration=args.duration,
            ramp_up_time=args.ramp_up
        )
    
    # Override with command line args
    if args.base_url != 'http://localhost:8000':
        config.base_url = args.base_url
    if args.users != 10:
        config.concurrent_users = args.users
    if args.duration != 60:
        config.test_duration = args.duration
    if args.ramp_up != 10:
        config.ramp_up_time = args.ramp_up
    
    # Run performance tests
    async def run_tests():
        test_suite = PerformanceTestSuite(config)
        
        try:
            results = await test_suite.run_performance_tests()
            
            # Generate report
            report_file = test_suite.generate_performance_report(results, args.output)
            
            # Print summary
            test_suite.print_summary(results)
            
            # Exit with appropriate code based on performance
            analysis = results.get("performance_analysis", {})
            performance = analysis.get("overall_performance", "unknown")
            
            if performance in ["excellent", "good"]:
                sys.exit(0)
            elif performance == "fair":
                sys.exit(1)
            else:
                sys.exit(2)
                
        except KeyboardInterrupt:
            logger.info("Performance test interrupted by user")
            sys.exit(130)
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            sys.exit(1)
    
    # Run the test suite
    asyncio.run(run_tests())

if __name__ == '__main__':
    main()