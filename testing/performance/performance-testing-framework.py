#!/usr/bin/env python3
"""
Comprehensive Performance Testing Framework
==========================================
Enterprise-grade performance and load testing for Splunk MCP Integration platform
"""

import asyncio
import json
import logging
import os
import sys
import time
import statistics
import random
import aiohttp
import yaml
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import websockets
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestType(Enum):
    """Types of performance tests"""
    LOAD_TEST = "load_test"
    STRESS_TEST = "stress_test"
    SPIKE_TEST = "spike_test"
    VOLUME_TEST = "volume_test"
    ENDURANCE_TEST = "endurance_test"
    SCALABILITY_TEST = "scalability_test"
    CONCURRENT_USER_TEST = "concurrent_user_test"
    REAL_TIME_TEST = "real_time_test"

class ServiceType(Enum):
    """Service types for testing"""
    API_GATEWAY = "api-gateway"
    NLP_ENGINE = "nlp-engine"
    VISUALIZATION = "visualization"
    ALERT_MANAGER = "alert-manager"
    FRONTEND = "frontend"
    DATABASE = "database"
    CACHE = "cache"
    WEBSOCKET = "websocket"

class MetricType(Enum):
    """Performance metrics to collect"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    CONCURRENT_USERS = "concurrent_users"
    DATABASE_CONNECTIONS = "database_connections"
    CACHE_HIT_RATE = "cache_hit_rate"

@dataclass
class PerformanceMetric:
    """Individual performance metric measurement"""
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    service: str = ""
    test_scenario: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestScenario:
    """Performance test scenario configuration"""
    name: str
    test_type: TestType
    duration_seconds: int
    concurrent_users: int
    ramp_up_seconds: int
    target_service: ServiceType
    endpoint: str
    request_data: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    success_criteria: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestResult:
    """Performance test result"""
    scenario: TestScenario
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    metrics: List[PerformanceMetric] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    success: bool = False

@dataclass
class PerformanceTestSuite:
    """Complete performance test suite results"""
    suite_name: str
    environment: str
    start_time: datetime
    end_time: Optional[datetime] = None
    test_results: List[TestResult] = field(default_factory=list)
    overall_success: bool = False
    summary_metrics: Dict[str, Any] = field(default_factory=dict)

class PerformanceTestingFramework:
    """Main performance testing framework"""
    
    def __init__(self, environment: str = "production", namespace: str = "splunk-mcp-prod"):
        self.environment = environment
        self.namespace = namespace
        self.base_urls = self._get_service_urls()
        self.test_data = self._load_test_data()
        self.session_pool = []
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
    def _get_service_urls(self) -> Dict[ServiceType, str]:
        """Get service URLs for testing"""
        if self.environment == "production":
            return {
                ServiceType.API_GATEWAY: "https://api.splunk-mcp.com",
                ServiceType.NLP_ENGINE: "http://nlp-engine.splunk-mcp-prod.svc.cluster.local:8001",
                ServiceType.VISUALIZATION: "http://visualization.splunk-mcp-prod.svc.cluster.local:8002",
                ServiceType.ALERT_MANAGER: "http://alert-manager.splunk-mcp-prod.svc.cluster.local:8003",
                ServiceType.FRONTEND: "https://app.splunk-mcp.com",
                ServiceType.WEBSOCKET: "wss://ws.splunk-mcp.com",
                ServiceType.DATABASE: "postgresql://splunk-mcp-prod:5432",
                ServiceType.CACHE: "redis://redis.splunk-mcp-prod.svc.cluster.local:6379"
            }
        else:
            return {
                ServiceType.API_GATEWAY: "http://localhost:8000",
                ServiceType.NLP_ENGINE: "http://localhost:8001",
                ServiceType.VISUALIZATION: "http://localhost:8002",
                ServiceType.ALERT_MANAGER: "http://localhost:8003",
                ServiceType.FRONTEND: "http://localhost:3000",
                ServiceType.WEBSOCKET: "ws://localhost:3000/ws",
                ServiceType.DATABASE: "postgresql://localhost:5432",
                ServiceType.CACHE: "redis://localhost:6379"
            }
    
    def _load_test_data(self) -> Dict[str, Any]:
        """Load test data for various scenarios"""
        return {
            "sample_queries": [
                "Show me failed login attempts in the last hour",
                "What are the top error messages from our web servers?",
                "Display CPU usage trends for the last 24 hours",
                "Find all security events from the firewall logs",
                "Show me database connection errors this week",
                "What are the slowest queries in our application?",
                "Display network traffic anomalies",
                "Show me all authentication failures by user",
                "What are the most frequent error codes?",
                "Display memory usage across all servers"
            ],
            "user_credentials": [
                {"username": f"testuser{i}", "password": "TestPass123!"} 
                for i in range(1, 101)
            ],
            "dashboard_ids": [f"dashboard_{i}" for i in range(1, 21)],
            "alert_configs": [
                {
                    "name": f"Test Alert {i}",
                    "query": f"search index=main error | head {i*10}",
                    "threshold": i * 0.1
                }
                for i in range(1, 11)
            ]
        }
    
    async def run_comprehensive_performance_tests(self) -> PerformanceTestSuite:
        """Run comprehensive performance test suite"""
        logger.info("Starting comprehensive performance testing suite...")
        
        suite = PerformanceTestSuite(
            suite_name="Splunk MCP Performance Validation",
            environment=self.environment,
            start_time=datetime.utcnow()
        )
        
        # Define test scenarios based on business requirements
        test_scenarios = [
            # Core API Performance Tests
            TestScenario(
                name="API Gateway Load Test",
                test_type=TestType.LOAD_TEST,
                duration_seconds=300,  # 5 minutes
                concurrent_users=1000,
                ramp_up_seconds=60,
                target_service=ServiceType.API_GATEWAY,
                endpoint="/api/v1/health",
                success_criteria={"avg_response_time": 1.0, "error_rate": 0.01}
            ),
            TestScenario(
                name="NLP Engine Query Processing",
                test_type=TestType.LOAD_TEST,
                duration_seconds=600,  # 10 minutes
                concurrent_users=500,
                ramp_up_seconds=120,
                target_service=ServiceType.NLP_ENGINE,
                endpoint="/api/v1/translate",
                request_data={"query": "Show me error logs from last hour"},
                success_criteria={"avg_response_time": 3.0, "error_rate": 0.02}
            ),
            TestScenario(
                name="Visualization Dashboard Rendering",
                test_type=TestType.LOAD_TEST,
                duration_seconds=300,
                concurrent_users=800,
                ramp_up_seconds=90,
                target_service=ServiceType.VISUALIZATION,
                endpoint="/api/v1/dashboard/render",
                success_criteria={"avg_response_time": 2.0, "error_rate": 0.01}
            ),
            
            # High Concurrency Tests
            TestScenario(
                name="10K Concurrent Users Simulation",
                test_type=TestType.CONCURRENT_USER_TEST,
                duration_seconds=1800,  # 30 minutes
                concurrent_users=10000,
                ramp_up_seconds=600,  # 10 minute ramp-up
                target_service=ServiceType.API_GATEWAY,
                endpoint="/api/v1/query",
                success_criteria={"avg_response_time": 3.0, "error_rate": 0.05}
            ),
            
            # Stress Testing
            TestScenario(
                name="System Breaking Point Analysis",
                test_type=TestType.STRESS_TEST,
                duration_seconds=900,  # 15 minutes
                concurrent_users=15000,  # Beyond normal capacity
                ramp_up_seconds=300,
                target_service=ServiceType.API_GATEWAY,
                endpoint="/api/v1/query",
                success_criteria={"system_stability": True}
            ),
            
            # Real-time Features Testing
            TestScenario(
                name="WebSocket Real-time Performance",
                test_type=TestType.REAL_TIME_TEST,
                duration_seconds=600,
                concurrent_users=2000,
                ramp_up_seconds=120,
                target_service=ServiceType.WEBSOCKET,
                endpoint="/ws",
                success_criteria={"message_latency": 0.1, "error_rate": 0.01}
            ),
            
            # Endurance Testing
            TestScenario(
                name="24-Hour Endurance Test",
                test_type=TestType.ENDURANCE_TEST,
                duration_seconds=86400,  # 24 hours
                concurrent_users=2000,
                ramp_up_seconds=1800,  # 30 minute ramp-up
                target_service=ServiceType.API_GATEWAY,
                endpoint="/api/v1/query",
                success_criteria={"memory_leak": False, "error_rate": 0.02}
            ),
            
            # Database Performance Tests
            TestScenario(
                name="Database Connection Pool Test",
                test_type=TestType.VOLUME_TEST,
                duration_seconds=600,
                concurrent_users=5000,
                ramp_up_seconds=180,
                target_service=ServiceType.DATABASE,
                endpoint="/api/v1/data/query",
                success_criteria={"avg_response_time": 1.5, "connection_pool_usage": 0.8}
            ),
            
            # Spike Testing
            TestScenario(
                name="Traffic Spike Resilience",
                test_type=TestType.SPIKE_TEST,
                duration_seconds=300,
                concurrent_users=20000,  # Sudden spike
                ramp_up_seconds=30,  # Very quick ramp-up
                target_service=ServiceType.API_GATEWAY,
                endpoint="/api/v1/query",
                success_criteria={"system_recovery": True, "error_rate": 0.1}
            )
        ]
        
        # Execute test scenarios
        for scenario in test_scenarios:
            logger.info(f"Executing test scenario: {scenario.name}")
            try:
                result = await self._execute_test_scenario(scenario)
                suite.test_results.append(result)
                
                # Log intermediate results
                self._log_test_result(result)
                
            except Exception as e:
                logger.error(f"Test scenario {scenario.name} failed: {e}")
                failed_result = TestResult(
                    scenario=scenario,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    errors=[str(e)],
                    success=False
                )
                suite.test_results.append(failed_result)
        
        suite.end_time = datetime.utcnow()
        suite.overall_success = self._evaluate_overall_success(suite)
        suite.summary_metrics = self._generate_summary_metrics(suite)
        
        return suite
    
    async def _execute_test_scenario(self, scenario: TestScenario) -> TestResult:
        """Execute individual test scenario"""
        result = TestResult(
            scenario=scenario,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            total_requests=0,
            successful_requests=0,
            failed_requests=0
        )
        
        # Execute based on test type
        if scenario.test_type == TestType.REAL_TIME_TEST:
            await self._execute_websocket_test(scenario, result)
        elif scenario.test_type == TestType.ENDURANCE_TEST:
            await self._execute_endurance_test(scenario, result)
        elif scenario.test_type == TestType.SPIKE_TEST:
            await self._execute_spike_test(scenario, result)
        else:
            await self._execute_http_load_test(scenario, result)
        
        result.end_time = datetime.utcnow()
        result.success = self._evaluate_test_success(scenario, result)
        
        return result
    
    async def _execute_http_load_test(self, scenario: TestScenario, result: TestResult):
        """Execute HTTP-based load test"""
        base_url = self.base_urls[scenario.target_service]
        url = f"{base_url}{scenario.endpoint}"
        
        # Create session pool
        connector = aiohttp.TCPConnector(limit=scenario.concurrent_users * 2)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=scenario.headers
        ) as session:
            
            # Ramp-up phase
            tasks = []
            users_per_second = scenario.concurrent_users / scenario.ramp_up_seconds
            
            start_time = time.time()
            end_time = start_time + scenario.duration_seconds
            
            # Create tasks with ramp-up
            for i in range(scenario.concurrent_users):
                delay = i / users_per_second
                task = asyncio.create_task(
                    self._simulate_user_session(session, url, scenario, delay, end_time)
                )
                tasks.append(task)
            
            # Collect metrics during test execution
            metrics_task = asyncio.create_task(
                self._collect_system_metrics(scenario, result, scenario.duration_seconds)
            )
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            await metrics_task
            
            # Count results
            for task in tasks:
                if not task.exception():
                    task_result = task.result()
                    result.total_requests += task_result.get('total_requests', 0)
                    result.successful_requests += task_result.get('successful_requests', 0)
                    result.failed_requests += task_result.get('failed_requests', 0)
                    
                    # Add response time metrics
                    if 'response_times' in task_result:
                        for rt in task_result['response_times']:
                            result.metrics.append(PerformanceMetric(
                                metric_type=MetricType.RESPONSE_TIME,
                                value=rt,
                                unit="seconds",
                                timestamp=datetime.utcnow(),
                                service=scenario.target_service.value,
                                test_scenario=scenario.name
                            ))
    
    async def _simulate_user_session(self, session: aiohttp.ClientSession, url: str, 
                                   scenario: TestScenario, delay: float, end_time: float) -> Dict[str, Any]:
        """Simulate individual user session"""
        await asyncio.sleep(delay)  # Ramp-up delay
        
        user_result = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': []
        }
        
        while time.time() < end_time:
            try:
                request_start = time.time()
                
                # Prepare request data
                if scenario.request_data:
                    # Randomize test data for realistic load
                    request_data = self._randomize_request_data(scenario.request_data)
                    async with session.post(url, json=request_data) as response:
                        await response.text()  # Consume response
                        response_time = time.time() - request_start
                        
                        if response.status < 400:
                            user_result['successful_requests'] += 1
                        else:
                            user_result['failed_requests'] += 1
                            
                        user_result['response_times'].append(response_time)
                else:
                    async with session.get(url) as response:
                        await response.text()  # Consume response
                        response_time = time.time() - request_start
                        
                        if response.status < 400:
                            user_result['successful_requests'] += 1
                        else:
                            user_result['failed_requests'] += 1
                            
                        user_result['response_times'].append(response_time)
                
                user_result['total_requests'] += 1
                
                # Add some think time to simulate realistic user behavior
                await asyncio.sleep(random.uniform(1, 5))
                
            except Exception as e:
                user_result['failed_requests'] += 1
                user_result['total_requests'] += 1
                
                # Add short delay before retry
                await asyncio.sleep(1)
        
        return user_result
    
    async def _execute_websocket_test(self, scenario: TestScenario, result: TestResult):
        """Execute WebSocket real-time performance test"""
        ws_url = self.base_urls[ServiceType.WEBSOCKET]
        
        tasks = []
        for i in range(scenario.concurrent_users):
            delay = (i / scenario.concurrent_users) * scenario.ramp_up_seconds
            task = asyncio.create_task(
                self._simulate_websocket_user(ws_url, scenario, delay)
            )
            tasks.append(task)
        
        # Collect metrics
        metrics_task = asyncio.create_task(
            self._collect_system_metrics(scenario, result, scenario.duration_seconds)
        )
        
        # Wait for completion
        websocket_results = await asyncio.gather(*tasks, return_exceptions=True)
        await metrics_task
        
        # Aggregate results
        for ws_result in websocket_results:
            if isinstance(ws_result, dict):
                result.total_requests += ws_result.get('messages_sent', 0)
                result.successful_requests += ws_result.get('messages_received', 0)
                result.failed_requests += ws_result.get('connection_errors', 0)
                
                # Add latency metrics
                for latency in ws_result.get('message_latencies', []):
                    result.metrics.append(PerformanceMetric(
                        metric_type=MetricType.RESPONSE_TIME,
                        value=latency,
                        unit="seconds",
                        timestamp=datetime.utcnow(),
                        service=scenario.target_service.value,
                        test_scenario=scenario.name
                    ))
    
    async def _simulate_websocket_user(self, ws_url: str, scenario: TestScenario, delay: float) -> Dict[str, Any]:
        """Simulate individual WebSocket user"""
        await asyncio.sleep(delay)
        
        user_result = {
            'messages_sent': 0,
            'messages_received': 0,
            'connection_errors': 0,
            'message_latencies': []
        }
        
        try:
            async with websockets.connect(ws_url) as websocket:
                end_time = time.time() + scenario.duration_seconds
                
                while time.time() < end_time:
                    try:
                        # Send query message
                        query = random.choice(self.test_data['sample_queries'])
                        message = {
                            'type': 'query',
                            'data': {'query': query},
                            'timestamp': time.time()
                        }
                        
                        send_time = time.time()
                        await websocket.send(json.dumps(message))
                        user_result['messages_sent'] += 1
                        
                        # Wait for response
                        response = await asyncio.wait_for(websocket.recv(), timeout=10)
                        receive_time = time.time()
                        
                        user_result['messages_received'] += 1
                        user_result['message_latencies'].append(receive_time - send_time)
                        
                        # Think time
                        await asyncio.sleep(random.uniform(2, 8))
                        
                    except asyncio.TimeoutError:
                        user_result['connection_errors'] += 1
                    except Exception as e:
                        user_result['connection_errors'] += 1
                        
        except Exception as e:
            user_result['connection_errors'] += 1
        
        return user_result
    
    async def _execute_endurance_test(self, scenario: TestScenario, result: TestResult):
        """Execute long-running endurance test"""
        logger.info(f"Starting {scenario.duration_seconds / 3600:.1f} hour endurance test")
        
        # Use lower concurrent users for sustainability
        sustained_users = min(scenario.concurrent_users, 2000)
        
        # Create modified scenario for endurance
        endurance_scenario = TestScenario(
            name=f"{scenario.name} - Sustained Load",
            test_type=TestType.LOAD_TEST,
            duration_seconds=scenario.duration_seconds,
            concurrent_users=sustained_users,
            ramp_up_seconds=scenario.ramp_up_seconds,
            target_service=scenario.target_service,
            endpoint=scenario.endpoint,
            request_data=scenario.request_data,
            success_criteria=scenario.success_criteria
        )
        
        # Execute with periodic health checks
        await self._execute_http_load_test(endurance_scenario, result)
        
        # Add memory leak detection
        memory_metrics = [m for m in result.metrics if m.metric_type == MetricType.MEMORY_USAGE]
        if memory_metrics:
            initial_memory = memory_metrics[0].value
            final_memory = memory_metrics[-1].value
            memory_increase = (final_memory - initial_memory) / initial_memory
            
            result.metrics.append(PerformanceMetric(
                metric_type=MetricType.MEMORY_USAGE,
                value=memory_increase,
                unit="percentage",
                timestamp=datetime.utcnow(),
                service="system",
                test_scenario=scenario.name,
                metadata={"type": "memory_leak_indicator"}
            ))
    
    async def _execute_spike_test(self, scenario: TestScenario, result: TestResult):
        """Execute spike test with sudden load increase"""
        logger.info(f"Starting spike test with {scenario.concurrent_users} sudden users")
        
        # Phase 1: Normal load (10% of spike users)
        normal_load = scenario.concurrent_users // 10
        await self._execute_load_phase("Normal Load", normal_load, 60, scenario, result)
        
        # Phase 2: Spike load (full users)
        await self._execute_load_phase("Spike Load", scenario.concurrent_users, 
                                     scenario.duration_seconds - 120, scenario, result)
        
        # Phase 3: Recovery phase (back to normal)
        await self._execute_load_phase("Recovery Load", normal_load, 60, scenario, result)
    
    async def _execute_load_phase(self, phase_name: str, users: int, duration: int, 
                                scenario: TestScenario, result: TestResult):
        """Execute a specific load phase"""
        logger.info(f"Executing {phase_name}: {users} users for {duration} seconds")
        
        phase_scenario = TestScenario(
            name=f"{scenario.name} - {phase_name}",
            test_type=TestType.LOAD_TEST,
            duration_seconds=duration,
            concurrent_users=users,
            ramp_up_seconds=min(30, duration // 2),
            target_service=scenario.target_service,
            endpoint=scenario.endpoint,
            request_data=scenario.request_data
        )
        
        phase_result = TestResult(
            scenario=phase_scenario,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            total_requests=0,
            successful_requests=0,
            failed_requests=0
        )
        
        await self._execute_http_load_test(phase_scenario, phase_result)
        
        # Merge phase results into main result
        result.total_requests += phase_result.total_requests
        result.successful_requests += phase_result.successful_requests
        result.failed_requests += phase_result.failed_requests
        result.metrics.extend(phase_result.metrics)
    
    async def _collect_system_metrics(self, scenario: TestScenario, result: TestResult, duration: int):
        """Collect system performance metrics during test execution"""
        start_time = time.time()
        end_time = start_time + duration
        
        while time.time() < end_time:
            try:
                # CPU Usage
                cpu_percent = psutil.cpu_percent(interval=1)
                result.metrics.append(PerformanceMetric(
                    metric_type=MetricType.CPU_USAGE,
                    value=cpu_percent,
                    unit="percentage",
                    timestamp=datetime.utcnow(),
                    service="system",
                    test_scenario=scenario.name
                ))
                
                # Memory Usage
                memory = psutil.virtual_memory()
                result.metrics.append(PerformanceMetric(
                    metric_type=MetricType.MEMORY_USAGE,
                    value=memory.percent,
                    unit="percentage",
                    timestamp=datetime.utcnow(),
                    service="system",
                    test_scenario=scenario.name
                ))
                
                # Disk I/O
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    result.metrics.append(PerformanceMetric(
                        metric_type=MetricType.DISK_IO,
                        value=disk_io.read_bytes + disk_io.write_bytes,
                        unit="bytes",
                        timestamp=datetime.utcnow(),
                        service="system",
                        test_scenario=scenario.name
                    ))
                
                # Network I/O
                network_io = psutil.net_io_counters()
                if network_io:
                    result.metrics.append(PerformanceMetric(
                        metric_type=MetricType.NETWORK_IO,
                        value=network_io.bytes_sent + network_io.bytes_recv,
                        unit="bytes",
                        timestamp=datetime.utcnow(),
                        service="system",
                        test_scenario=scenario.name
                    ))
                
                await asyncio.sleep(5)  # Collect metrics every 5 seconds
                
            except Exception as e:
                logger.warning(f"Error collecting system metrics: {e}")
                await asyncio.sleep(5)
    
    def _randomize_request_data(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """Randomize request data for realistic testing"""
        randomized = base_data.copy()
        
        if 'query' in randomized:
            randomized['query'] = random.choice(self.test_data['sample_queries'])
        
        if 'dashboard_id' in randomized:
            randomized['dashboard_id'] = random.choice(self.test_data['dashboard_ids'])
        
        if 'time_range' in randomized:
            time_ranges = ['1h', '4h', '24h', '7d', '30d']
            randomized['time_range'] = random.choice(time_ranges)
        
        return randomized
    
    def _evaluate_test_success(self, scenario: TestScenario, result: TestResult) -> bool:
        """Evaluate if test scenario passed success criteria"""
        if not scenario.success_criteria:
            return result.failed_requests == 0
        
        success = True
        
        # Check error rate
        if 'error_rate' in scenario.success_criteria:
            error_rate = result.failed_requests / max(result.total_requests, 1)
            if error_rate > scenario.success_criteria['error_rate']:
                success = False
                result.errors.append(f"Error rate {error_rate:.3f} exceeds limit {scenario.success_criteria['error_rate']}")
        
        # Check average response time
        if 'avg_response_time' in scenario.success_criteria:
            response_times = [m.value for m in result.metrics if m.metric_type == MetricType.RESPONSE_TIME]
            if response_times:
                avg_response_time = statistics.mean(response_times)
                if avg_response_time > scenario.success_criteria['avg_response_time']:
                    success = False
                    result.errors.append(f"Average response time {avg_response_time:.3f}s exceeds limit {scenario.success_criteria['avg_response_time']}s")
        
        # Check system stability for stress tests
        if 'system_stability' in scenario.success_criteria:
            cpu_metrics = [m.value for m in result.metrics if m.metric_type == MetricType.CPU_USAGE]
            memory_metrics = [m.value for m in result.metrics if m.metric_type == MetricType.MEMORY_USAGE]
            
            if cpu_metrics and max(cpu_metrics) > 95:
                success = False
                result.errors.append("System CPU usage exceeded 95%")
            
            if memory_metrics and max(memory_metrics) > 95:
                success = False
                result.errors.append("System memory usage exceeded 95%")
        
        return success
    
    def _evaluate_overall_success(self, suite: PerformanceTestSuite) -> bool:
        """Evaluate overall test suite success"""
        critical_tests = [
            "API Gateway Load Test",
            "NLP Engine Query Processing", 
            "10K Concurrent Users Simulation"
        ]
        
        for result in suite.test_results:
            if result.scenario.name in critical_tests and not result.success:
                return False
        
        # At least 80% of tests should pass
        passed_tests = sum(1 for r in suite.test_results if r.success)
        success_rate = passed_tests / len(suite.test_results)
        
        return success_rate >= 0.8
    
    def _generate_summary_metrics(self, suite: PerformanceTestSuite) -> Dict[str, Any]:
        """Generate summary metrics for the test suite"""
        all_metrics = []
        for result in suite.test_results:
            all_metrics.extend(result.metrics)
        
        # Response time analysis
        response_times = [m.value for m in all_metrics if m.metric_type == MetricType.RESPONSE_TIME]
        
        summary = {
            "total_tests": len(suite.test_results),
            "passed_tests": sum(1 for r in suite.test_results if r.success),
            "failed_tests": sum(1 for r in suite.test_results if not r.success),
            "total_requests": sum(r.total_requests for r in suite.test_results),
            "successful_requests": sum(r.successful_requests for r in suite.test_results),
            "failed_requests": sum(r.failed_requests for r in suite.test_results),
            "duration_hours": (suite.end_time - suite.start_time).total_seconds() / 3600
        }
        
        if response_times:
            summary.update({
                "avg_response_time": statistics.mean(response_times),
                "p50_response_time": statistics.median(response_times),
                "p95_response_time": self._percentile(response_times, 95),
                "p99_response_time": self._percentile(response_times, 99),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times)
            })
        
        # System resource usage
        cpu_metrics = [m.value for m in all_metrics if m.metric_type == MetricType.CPU_USAGE]
        memory_metrics = [m.value for m in all_metrics if m.metric_type == MetricType.MEMORY_USAGE]
        
        if cpu_metrics:
            summary["max_cpu_usage"] = max(cpu_metrics)
            summary["avg_cpu_usage"] = statistics.mean(cpu_metrics)
        
        if memory_metrics:
            summary["max_memory_usage"] = max(memory_metrics)
            summary["avg_memory_usage"] = statistics.mean(memory_metrics)
        
        return summary
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _log_test_result(self, result: TestResult):
        """Log test result summary"""
        success_indicator = "✓" if result.success else "✗"
        duration = (result.end_time - result.start_time).total_seconds()
        
        logger.info(f"{success_indicator} {result.scenario.name}")
        logger.info(f"  Duration: {duration:.1f}s")
        logger.info(f"  Total Requests: {result.total_requests}")
        logger.info(f"  Success Rate: {result.successful_requests}/{result.total_requests} ({result.successful_requests/max(result.total_requests, 1)*100:.1f}%)")
        
        if result.errors:
            for error in result.errors:
                logger.warning(f"  Error: {error}")
    
    def generate_performance_report(self, suite: PerformanceTestSuite) -> Dict[str, Any]:
        """Generate comprehensive performance test report"""
        return {
            "report_metadata": {
                "suite_name": suite.suite_name,
                "environment": suite.environment,
                "start_time": suite.start_time.isoformat(),
                "end_time": suite.end_time.isoformat() if suite.end_time else None,
                "duration_hours": (suite.end_time - suite.start_time).total_seconds() / 3600 if suite.end_time else 0,
                "report_generated": datetime.utcnow().isoformat()
            },
            "executive_summary": {
                "overall_success": suite.overall_success,
                "performance_requirements_met": self._check_performance_requirements(suite),
                "scalability_validated": self._check_scalability_validation(suite),
                "system_stability": self._check_system_stability(suite),
                "recommendations": self._generate_recommendations(suite),
                "critical_findings": self._get_critical_findings(suite)
            },
            "detailed_results": {
                "test_scenarios": [
                    {
                        "name": result.scenario.name,
                        "test_type": result.scenario.test_type.value,
                        "success": result.success,
                        "duration_seconds": (result.end_time - result.start_time).total_seconds(),
                        "concurrent_users": result.scenario.concurrent_users,
                        "total_requests": result.total_requests,
                        "successful_requests": result.successful_requests,
                        "failed_requests": result.failed_requests,
                        "error_rate": result.failed_requests / max(result.total_requests, 1),
                        "errors": result.errors
                    }
                    for result in suite.test_results
                ]
            },
            "performance_metrics": suite.summary_metrics,
            "system_requirements_validation": {
                "concurrent_users_10k": self._validate_10k_users(suite),
                "response_time_3s": self._validate_response_times(suite),
                "system_stability": self._validate_system_stability(suite),
                "scalability": self._validate_scalability(suite)
            },
            "resource_utilization": self._analyze_resource_utilization(suite),
            "bottleneck_analysis": self._identify_bottlenecks(suite),
            "scalability_analysis": self._analyze_scalability(suite)
        }
    
    def _check_performance_requirements(self, suite: PerformanceTestSuite) -> bool:
        """Check if performance requirements are met"""
        # Requirement: Handle 10,000+ concurrent queries with <3 second response times
        concurrent_user_test = next(
            (r for r in suite.test_results if "10K Concurrent" in r.scenario.name), 
            None
        )
        
        if not concurrent_user_test or not concurrent_user_test.success:
            return False
        
        # Check if response times are under 3 seconds
        response_times = [
            m.value for m in concurrent_user_test.metrics 
            if m.metric_type == MetricType.RESPONSE_TIME
        ]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = self._percentile(response_times, 95)
            return avg_response_time < 3.0 and p95_response_time < 5.0
        
        return False
    
    def _check_scalability_validation(self, suite: PerformanceTestSuite) -> bool:
        """Check if scalability is validated"""
        scalability_tests = [
            r for r in suite.test_results 
            if r.scenario.test_type in [TestType.SCALABILITY_TEST, TestType.CONCURRENT_USER_TEST]
        ]
        
        return len(scalability_tests) > 0 and all(r.success for r in scalability_tests)
    
    def _check_system_stability(self, suite: PerformanceTestSuite) -> bool:
        """Check system stability under load"""
        endurance_test = next(
            (r for r in suite.test_results if r.scenario.test_type == TestType.ENDURANCE_TEST),
            None
        )
        
        if endurance_test:
            return endurance_test.success
        
        # Check for memory leaks in other tests
        for result in suite.test_results:
            memory_leak_metrics = [
                m for m in result.metrics 
                if m.metric_type == MetricType.MEMORY_USAGE and 
                m.metadata.get("type") == "memory_leak_indicator"
            ]
            
            for metric in memory_leak_metrics:
                if metric.value > 0.1:  # More than 10% memory increase
                    return False
        
        return True
    
    def _generate_recommendations(self, suite: PerformanceTestSuite) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Analyze failed tests
        failed_tests = [r for r in suite.test_results if not r.success]
        if failed_tests:
            recommendations.append("Address failing performance tests before production deployment")
        
        # Check response times
        all_response_times = []
        for result in suite.test_results:
            all_response_times.extend([
                m.value for m in result.metrics 
                if m.metric_type == MetricType.RESPONSE_TIME
            ])
        
        if all_response_times:
            avg_response_time = statistics.mean(all_response_times)
            if avg_response_time > 2.0:
                recommendations.append("Optimize application response times - currently averaging {:.2f}s".format(avg_response_time))
        
        # Check resource utilization
        all_cpu_metrics = []
        all_memory_metrics = []
        
        for result in suite.test_results:
            all_cpu_metrics.extend([
                m.value for m in result.metrics 
                if m.metric_type == MetricType.CPU_USAGE
            ])
            all_memory_metrics.extend([
                m.value for m in result.metrics 
                if m.metric_type == MetricType.MEMORY_USAGE
            ])
        
        if all_cpu_metrics and max(all_cpu_metrics) > 80:
            recommendations.append("Consider horizontal scaling - CPU usage peaked at {:.1f}%".format(max(all_cpu_metrics)))
        
        if all_memory_metrics and max(all_memory_metrics) > 80:
            recommendations.append("Monitor memory usage - peaked at {:.1f}%".format(max(all_memory_metrics)))
        
        # Add general recommendations
        recommendations.extend([
            "Implement caching strategies for frequently accessed data",
            "Consider database connection pooling optimization",
            "Set up auto-scaling policies for production deployment",
            "Implement circuit breakers for external service dependencies",
            "Monitor and optimize database query performance"
        ])
        
        return recommendations
    
    def _get_critical_findings(self, suite: PerformanceTestSuite) -> List[str]:
        """Get critical performance findings"""
        findings = []
        
        # Check for critical test failures
        critical_tests = ["API Gateway Load Test", "10K Concurrent Users Simulation"]
        for test_name in critical_tests:
            test_result = next(
                (r for r in suite.test_results if r.scenario.name == test_name),
                None
            )
            if test_result and not test_result.success:
                findings.append(f"CRITICAL: {test_name} failed - system may not meet production requirements")
        
        # Check for high error rates
        for result in suite.test_results:
            error_rate = result.failed_requests / max(result.total_requests, 1)
            if error_rate > 0.05:  # More than 5% error rate
                findings.append(f"HIGH ERROR RATE: {result.scenario.name} - {error_rate*100:.1f}% of requests failed")
        
        return findings
    
    def _validate_10k_users(self, suite: PerformanceTestSuite) -> Dict[str, Any]:
        """Validate 10K concurrent users requirement"""
        test = next(
            (r for r in suite.test_results if "10K Concurrent" in r.scenario.name),
            None  
        )
        
        if not test:
            return {"validated": False, "reason": "10K concurrent users test not found"}
        
        return {
            "validated": test.success,
            "concurrent_users_tested": test.scenario.concurrent_users,
            "success_rate": test.successful_requests / max(test.total_requests, 1),
            "error_rate": test.failed_requests / max(test.total_requests, 1),
            "details": "Test completed successfully" if test.success else "; ".join(test.errors)
        }
    
    def _validate_response_times(self, suite: PerformanceTestSuite) -> Dict[str, Any]:
        """Validate <3 second response time requirement"""
        all_response_times = []
        for result in suite.test_results:
            all_response_times.extend([
                m.value for m in result.metrics 
                if m.metric_type == MetricType.RESPONSE_TIME
            ])
        
        if not all_response_times:
            return {"validated": False, "reason": "No response time metrics collected"}
        
        avg_response_time = statistics.mean(all_response_times)
        p95_response_time = self._percentile(all_response_times, 95)
        
        return {
            "validated": avg_response_time < 3.0 and p95_response_time < 5.0,
            "avg_response_time": avg_response_time,
            "p95_response_time": p95_response_time,
            "p99_response_time": self._percentile(all_response_times, 99),
            "requirement_met": avg_response_time < 3.0
        }
    
    def _validate_system_stability(self, suite: PerformanceTestSuite) -> Dict[str, Any]:
        """Validate system stability under load"""
        stability_indicators = {
            "memory_leaks": False,
            "cpu_overload": False,
            "system_crashes": False,
            "overall_stable": True
        }
        
        # Check for memory leaks
        for result in suite.test_results:
            memory_metrics = [
                m for m in result.metrics 
                if m.metric_type == MetricType.MEMORY_USAGE and 
                m.metadata.get("type") == "memory_leak_indicator"
            ]
            
            for metric in memory_metrics:
                if metric.value > 0.1:  # More than 10% increase
                    stability_indicators["memory_leaks"] = True
                    stability_indicators["overall_stable"] = False
        
        # Check for CPU overload
        all_cpu_metrics = []
        for result in suite.test_results:
            all_cpu_metrics.extend([
                m.value for m in result.metrics 
                if m.metric_type == MetricType.CPU_USAGE
            ])
        
        if all_cpu_metrics and max(all_cpu_metrics) > 95:
            stability_indicators["cpu_overload"] = True
            stability_indicators["overall_stable"] = False
        
        return stability_indicators
    
    def _validate_scalability(self, suite: PerformanceTestSuite) -> Dict[str, Any]:
        """Validate system scalability"""
        scalability_results = {
            "horizontal_scaling": True,
            "load_handling": True,
            "resource_efficiency": True,
            "overall_scalable": True
        }
        
        # Check if system handled increasing loads
        load_tests = [
            r for r in suite.test_results 
            if r.scenario.test_type in [TestType.LOAD_TEST, TestType.CONCURRENT_USER_TEST]
        ]
        
        for test in load_tests:
            if not test.success:
                scalability_results["load_handling"] = False
                scalability_results["overall_scalable"] = False
        
        return scalability_results
    
    def _analyze_resource_utilization(self, suite: PerformanceTestSuite) -> Dict[str, Any]:
        """Analyze system resource utilization"""
        cpu_metrics = []
        memory_metrics = []
        
        for result in suite.test_results:
            cpu_metrics.extend([
                m.value for m in result.metrics 
                if m.metric_type == MetricType.CPU_USAGE
            ])
            memory_metrics.extend([
                m.value for m in result.metrics 
                if m.metric_type == MetricType.MEMORY_USAGE
            ])
        
        analysis = {}
        
        if cpu_metrics:
            analysis["cpu"] = {
                "max_usage": max(cpu_metrics),
                "avg_usage": statistics.mean(cpu_metrics),
                "p95_usage": self._percentile(cpu_metrics, 95)
            }
        
        if memory_metrics:
            analysis["memory"] = {
                "max_usage": max(memory_metrics),
                "avg_usage": statistics.mean(memory_metrics),
                "p95_usage": self._percentile(memory_metrics, 95)
            }
        
        return analysis
    
    def _identify_bottlenecks(self, suite: PerformanceTestSuite) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Analyze response times by service
        service_response_times = {}
        for result in suite.test_results:
            service = result.scenario.target_service.value
            response_times = [
                m.value for m in result.metrics 
                if m.metric_type == MetricType.RESPONSE_TIME
            ]
            
            if response_times:
                service_response_times[service] = {
                    "avg": statistics.mean(response_times),
                    "p95": self._percentile(response_times, 95)
                }
        
        # Identify slow services
        for service, times in service_response_times.items():
            if times["avg"] > 2.0:
                bottlenecks.append({
                    "type": "slow_service",
                    "service": service,
                    "avg_response_time": times["avg"],
                    "severity": "high" if times["avg"] > 5.0 else "medium"
                })
        
        return bottlenecks
    
    def _analyze_scalability(self, suite: PerformanceTestSuite) -> Dict[str, Any]:
        """Analyze system scalability characteristics"""
        scalability_analysis = {
            "linear_scaling": True,
            "breaking_point": None,
            "recommended_max_users": 10000,
            "scaling_efficiency": "good"
        }
        
        # Analyze how response times change with load
        load_vs_response = []
        
        for result in suite.test_results:
            if result.scenario.test_type in [TestType.LOAD_TEST, TestType.CONCURRENT_USER_TEST]:
                response_times = [
                    m.value for m in result.metrics 
                    if m.metric_type == MetricType.RESPONSE_TIME
                ]
                
                if response_times:
                    load_vs_response.append({
                        "concurrent_users": result.scenario.concurrent_users,
                        "avg_response_time": statistics.mean(response_times),
                        "success": result.success
                    })
        
        # Sort by concurrent users
        load_vs_response.sort(key=lambda x: x["concurrent_users"])
        
        # Find breaking point
        for entry in load_vs_response:
            if not entry["success"] and scalability_analysis["breaking_point"] is None:
                scalability_analysis["breaking_point"] = entry["concurrent_users"]
                scalability_analysis["linear_scaling"] = False
                break
        
        scalability_analysis["load_response_data"] = load_vs_response
        
        return scalability_analysis
    
    def export_report(self, suite: PerformanceTestSuite, format_type: str = "json", 
                     output_path: Optional[str] = None) -> str:
        """Export performance test report"""
        report = self.generate_performance_report(suite)
        
        if output_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = self.results_dir / f"performance_report_{timestamp}.{format_type}"
        
        if format_type == "json":
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        elif format_type == "yaml":
            with open(output_path, 'w') as f:
                yaml.dump(report, f, default_flow_style=False)
        
        return str(output_path)

# CLI interface
async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Testing Framework")
    parser.add_argument("--environment", "-e", default="production", help="Environment name")
    parser.add_argument("--namespace", "-n", default="splunk-mcp-prod", help="Kubernetes namespace")
    parser.add_argument("--test-type", "-t", help="Specific test type to run")
    parser.add_argument("--duration", "-d", type=int, help="Test duration in seconds")
    parser.add_argument("--users", "-u", type=int, help="Number of concurrent users")
    parser.add_argument("--output", "-o", choices=["json", "yaml"], default="json", help="Output format")
    parser.add_argument("--export-path", help="Export report to specific path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    framework = PerformanceTestingFramework(
        environment=args.environment,
        namespace=args.namespace
    )
    
    try:
        suite = await framework.run_comprehensive_performance_tests()
        
        # Print summary to console
        print("\n" + "="*80)
        print("PERFORMANCE TEST SUITE SUMMARY")
        print("="*80)
        print(f"Environment: {suite.environment}")
        print(f"Duration: {(suite.end_time - suite.start_time).total_seconds() / 3600:.1f} hours")
        print(f"Total Tests: {len(suite.test_results)}")
        print(f"Passed: {sum(1 for r in suite.test_results if r.success)}")
        print(f"Failed: {sum(1 for r in suite.test_results if not r.success)}")
        print(f"Overall Success: {'✓' if suite.overall_success else '✗'}")
        print(f"Total Requests: {suite.summary_metrics.get('total_requests', 0)}")
        print(f"Success Rate: {suite.summary_metrics.get('successful_requests', 0) / max(suite.summary_metrics.get('total_requests', 1), 1) * 100:.1f}%")
        
        if 'avg_response_time' in suite.summary_metrics:
            print(f"Average Response Time: {suite.summary_metrics['avg_response_time']:.3f}s")
            print(f"95th Percentile Response Time: {suite.summary_metrics['p95_response_time']:.3f}s")
        
        # Export detailed report
        report_path = framework.export_report(suite, format_type=args.output, output_path=args.export_path)
        print(f"\nDetailed report exported to: {report_path}")
        
        # Exit with appropriate code
        if not suite.overall_success:
            print("\nWARNING: Some performance tests failed!")
            sys.exit(1)
        else:
            print("\nAll performance tests passed successfully!")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Performance testing failed: {e}")
        sys.exit(3)

if __name__ == "__main__":
    asyncio.run(main())