#!/usr/bin/env python3
"""
Performance and load testing for cross-service integration.

This module tests system performance under load, concurrent user scenarios,
and service bottleneck identification across the entire system.
"""

import pytest
import asyncio
import time
import statistics
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp

from .conftest import (
    get_service_url,
    make_authenticated_request,
    create_test_conversation_id,
    create_test_user_context
)


class TestPerformanceIntegration:
    """Test performance characteristics across services."""
    
    @pytest.mark.asyncio
    async def test_nlp_engine_response_time(
        self,
        auth_headers: Dict[str, str],
        sample_natural_language_queries: List[Dict]
    ):
        """Test NLP Engine response time under various loads."""
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        response_times = []
        
        # Test with different query complexities
        for query_data in sample_natural_language_queries[:3]:
            start_time = time.time()
            
            response = await make_authenticated_request(
                "POST",
                nlp_url,
                auth_headers,
                {
                    "query": query_data["query"],
                    "context": create_test_user_context()
                }
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert response["status"] == 200
            assert response_time < 5.0, f"Response time {response_time}s exceeds 5s threshold"
        
        # Analyze response time statistics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        print(f"NLP Engine Response Times - Avg: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s")
        
        assert avg_response_time < 2.0, f"Average response time {avg_response_time}s exceeds 2s threshold"
    
    @pytest.mark.asyncio
    async def test_concurrent_user_simulation(
        self,
        auth_headers: Dict[str, str],
        sample_natural_language_queries: List[Dict]
    ):
        """Test system performance with concurrent users."""
        concurrent_users = 10
        requests_per_user = 5
        
        async def simulate_user_session():
            """Simulate a single user session."""
            session_times = []
            user_context = create_test_user_context()
            
            for query_data in sample_natural_language_queries[:requests_per_user]:
                start_time = time.time()
                
                # Step 1: NLP translation
                nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
                nlp_response = await make_authenticated_request(
                    "POST",
                    nlp_url,
                    auth_headers,
                    {
                        "query": query_data["query"],
                        "context": user_context
                    }
                )
                
                # Step 2: Visualization (if applicable)
                if query_data.get("visualization"):
                    viz_url = get_service_url("visualization", "/api/v1/charts/generate")
                    viz_response = await make_authenticated_request(
                        "POST",
                        viz_url,
                        auth_headers,
                        {
                            "chart_type": query_data["visualization"],
                            "data": [{"_time": "2024-01-01T10:00:00", "count": 100}],
                            "title": "Test Chart"
                        }
                    )
                
                end_time = time.time()
                session_times.append(end_time - start_time)
            
            return session_times
        
        # Run concurrent user sessions
        tasks = [simulate_user_session() for _ in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_sessions = [r for r in results if not isinstance(r, Exception)]
        all_response_times = [time for session in successful_sessions for time in session]
        
        success_rate = len(successful_sessions) / len(tasks)
        avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
        p95_response_time = statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) > 20 else 0
        
        print(f"Concurrent Users Test - Success Rate: {success_rate:.2%}")
        print(f"Average Response Time: {avg_response_time:.3f}s")
        print(f"P95 Response Time: {p95_response_time:.3f}s")
        
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95% threshold"
        assert avg_response_time < 3.0, f"Average response time {avg_response_time:.3f}s exceeds 3s threshold"
    
    @pytest.mark.asyncio
    async def test_database_performance_under_load(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test database performance under concurrent load."""
        concurrent_operations = 20
        
        async def database_operation():
            """Perform a database-intensive operation."""
            start_time = time.time()
            
            # Create alert (database write)
            alert_url = get_service_url("alert_manager", "/api/v1/alerts")
            create_response = await make_authenticated_request(
                "POST",
                alert_url,
                auth_headers,
                {
                    "name": f"Load Test Alert {time.time()}",
                    "search": "search error",
                    "condition": "count > 10",
                    "time_window": "5m"
                }
            )
            
            if create_response["status"] != 201:
                return None
            
            alert_id = create_response["data"]["alert_id"]
            
            # Read alert (database read)
            read_response = await make_authenticated_request(
                "GET",
                f"{alert_url}/{alert_id}",
                auth_headers
            )
            
            # Delete alert (database delete)
            delete_response = await make_authenticated_request(
                "DELETE",
                f"{alert_url}/{alert_id}",
                auth_headers
            )
            
            end_time = time.time()
            
            return {
                "operation_time": end_time - start_time,
                "create_status": create_response["status"],
                "read_status": read_response["status"],
                "delete_status": delete_response["status"]
            }
        
        # Run concurrent database operations
        tasks = [database_operation() for _ in range(concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_operations = [r for r in results if r is not None and not isinstance(r, Exception)]
        operation_times = [op["operation_time"] for op in successful_operations]
        
        success_rate = len(successful_operations) / len(tasks)
        avg_operation_time = statistics.mean(operation_times) if operation_times else 0
        
        print(f"Database Load Test - Success Rate: {success_rate:.2%}")
        print(f"Average Operation Time: {avg_operation_time:.3f}s")
        
        assert success_rate >= 0.90, f"Database operation success rate {success_rate:.2%} below 90%"
        assert avg_operation_time < 2.0, f"Average operation time {avg_operation_time:.3f}s exceeds 2s"
    
    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(
        self,
        auth_headers: Dict[str, str],
        sample_natural_language_queries: List[Dict]
    ):
        """Test memory usage patterns during operations."""
        # This would typically require additional monitoring setup
        # For now, we'll test that services don't crash under load
        
        operations_count = 50
        
        async def memory_intensive_operation():
            """Perform memory-intensive operations."""
            # Large visualization generation
            viz_url = get_service_url("visualization", "/api/v1/charts/generate")
            
            # Generate large dataset
            large_dataset = [
                {"_time": f"2024-01-01T{i:02d}:00:00", "count": i * 10}
                for i in range(1000)  # Large dataset
            ]
            
            response = await make_authenticated_request(
                "POST",
                viz_url,
                auth_headers,
                {
                    "chart_type": "line",
                    "data": large_dataset,
                    "title": "Large Dataset Chart"
                }
            )
            
            return response["status"] == 200
        
        # Run memory-intensive operations
        tasks = [memory_intensive_operation() for _ in range(operations_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_operations = sum(1 for r in results if r is True)
        success_rate = successful_operations / len(tasks)
        
        print(f"Memory Usage Test - Success Rate: {success_rate:.2%}")
        
        assert success_rate >= 0.85, f"Memory test success rate {success_rate:.2%} below 85%"


class TestLoadTesting:
    """Load testing for system limits and bottlenecks."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test rate limiting enforcement across services."""
        # Test rate limiting on NLP Engine
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        
        # Send requests rapidly to trigger rate limiting
        rapid_requests = 100
        successful_requests = 0
        rate_limited_requests = 0
        
        async def make_rapid_request():
            try:
                response = await make_authenticated_request(
                    "POST",
                    nlp_url,
                    auth_headers,
                    {
                        "query": "test query",
                        "context": create_test_user_context()
                    },
                    timeout=5
                )
                
                if response["status"] == 200:
                    return "success"
                elif response["status"] == 429:  # Too Many Requests
                    return "rate_limited"
                else:
                    return "error"
            except Exception:
                return "error"
        
        # Make rapid requests
        tasks = [make_rapid_request() for _ in range(rapid_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_requests = sum(1 for r in results if r == "success")
        rate_limited_requests = sum(1 for r in results if r == "rate_limited")
        
        print(f"Rate Limiting Test - Successful: {successful_requests}, Rate Limited: {rate_limited_requests}")
        
        # Rate limiting should kick in for excessive requests
        assert rate_limited_requests > 0, "Rate limiting not enforced"
        assert successful_requests > 0, "No successful requests (rate limiting too aggressive)"
    
    @pytest.mark.asyncio
    async def test_service_circuit_breaker(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test circuit breaker pattern for service failures."""
        # This test would require implementing circuit breaker patterns
        # For now, we'll test basic error handling
        
        # Test with non-existent service endpoint
        invalid_url = get_service_url("nlp_engine", "/api/v1/invalid/endpoint")
        
        error_responses = 0
        for _ in range(10):
            try:
                response = await make_authenticated_request(
                    "POST",
                    invalid_url,
                    auth_headers,
                    {"test": "data"},
                    timeout=5
                )
                
                if response["status"] == 404:
                    error_responses += 1
            except Exception:
                error_responses += 1
        
        # All requests should properly handle the invalid endpoint
        assert error_responses == 10, "Circuit breaker or error handling not working properly"
    
    @pytest.mark.asyncio
    async def test_dashboard_load_performance(
        self,
        auth_headers: Dict[str, str],
        sample_dashboard_configurations: List[Dict]
    ):
        """Test dashboard loading performance with multiple panels."""
        dashboard_config = sample_dashboard_configurations[0]
        
        # Create dashboard with multiple panels
        dashboard_url = get_service_url("visualization", "/api/v1/dashboards")
        
        start_time = time.time()
        
        dashboard_response = await make_authenticated_request(
            "POST",
            dashboard_url,
            auth_headers,
            dashboard_config
        )
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        assert dashboard_response["status"] == 201
        dashboard_id = dashboard_response["data"]["dashboard_id"]
        
        # Test dashboard loading performance
        load_times = []
        
        for _ in range(10):
            start_time = time.time()
            
            load_response = await make_authenticated_request(
                "GET",
                f"{dashboard_url}/{dashboard_id}",
                auth_headers
            )
            
            end_time = time.time()
            load_time = end_time - start_time
            load_times.append(load_time)
            
            assert load_response["status"] == 200
        
        avg_load_time = statistics.mean(load_times)
        max_load_time = max(load_times)
        
        print(f"Dashboard Performance - Creation: {creation_time:.3f}s")
        print(f"Average Load Time: {avg_load_time:.3f}s, Max Load Time: {max_load_time:.3f}s")
        
        assert creation_time < 5.0, f"Dashboard creation time {creation_time:.3f}s exceeds 5s"
        assert avg_load_time < 1.0, f"Average load time {avg_load_time:.3f}s exceeds 1s"


class TestScalabilityTesting:
    """Test system scalability characteristics."""
    
    @pytest.mark.asyncio
    async def test_export_job_queue_performance(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test export job queue performance under load."""
        # Submit multiple export jobs simultaneously
        export_jobs = 20
        job_ids = []
        
        export_url = get_service_url("api_gateway", "/api/v1/export/pdf")
        
        # Submit all jobs rapidly
        async def submit_export_job():
            response = await make_authenticated_request(
                "POST",
                export_url,
                auth_headers,
                {
                    "title": f"Load Test Report {time.time()}",
                    "template": "standard",
                    "sections": [
                        {
                            "title": "Test Section",
                            "type": "text",
                            "content": "Test content for load testing"
                        }
                    ]
                }
            )
            
            if response["status"] == 202:
                return response["data"]["job_id"]
            return None
        
        tasks = [submit_export_job() for _ in range(export_jobs)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        submitted_jobs = [job_id for job_id in results if job_id is not None]
        submission_success_rate = len(submitted_jobs) / export_jobs
        
        print(f"Export Queue Test - Submitted: {len(submitted_jobs)}/{export_jobs}")
        print(f"Submission Success Rate: {submission_success_rate:.2%}")
        
        assert submission_success_rate >= 0.80, f"Job submission rate {submission_success_rate:.2%} below 80%"
        
        # Monitor job processing
        completed_jobs = 0
        failed_jobs = 0
        
        # Check job status periodically
        for _ in range(30):  # Check for up to 30 seconds
            for job_id in submitted_jobs:
                status_response = await make_authenticated_request(
                    "GET",
                    f"{export_url}/jobs/{job_id}/status",
                    auth_headers
                )
                
                if status_response["status"] == 200:
                    job_status = status_response["data"]["status"]
                    if job_status == "completed":
                        completed_jobs += 1
                    elif job_status == "failed":
                        failed_jobs += 1
            
            if completed_jobs + failed_jobs >= len(submitted_jobs):
                break
            
            await asyncio.sleep(1)
        
        completion_rate = completed_jobs / len(submitted_jobs) if submitted_jobs else 0
        
        print(f"Job Processing - Completed: {completed_jobs}, Failed: {failed_jobs}")
        print(f"Completion Rate: {completion_rate:.2%}")
        
        assert completion_rate >= 0.70, f"Job completion rate {completion_rate:.2%} below 70%"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_scaling(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test WebSocket connection scaling."""
        # This test would require WebSocket implementation
        # For now, we'll test the REST API endpoints that support chat
        
        concurrent_sessions = 25
        messages_per_session = 5
        
        async def simulate_chat_session():
            """Simulate a chat session with multiple messages."""
            session_id = create_test_conversation_id()
            chat_url = get_service_url("api_gateway", "/api/v1/chat/message")
            
            successful_messages = 0
            
            for i in range(messages_per_session):
                response = await make_authenticated_request(
                    "POST",
                    chat_url,
                    auth_headers,
                    {
                        "message": f"Test message {i+1}",
                        "conversation_id": session_id,
                        "context": create_test_user_context()
                    }
                )
                
                if response["status"] == 200:
                    successful_messages += 1
                
                # Small delay between messages
                await asyncio.sleep(0.1)
            
            return successful_messages
        
        # Run concurrent chat sessions
        tasks = [simulate_chat_session() for _ in range(concurrent_sessions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = [r for r in results if isinstance(r, int)]
        total_messages = sum(successful_results)
        expected_messages = concurrent_sessions * messages_per_session
        
        success_rate = total_messages / expected_messages if expected_messages > 0 else 0
        
        print(f"Chat Scaling Test - Successful Messages: {total_messages}/{expected_messages}")
        print(f"Message Success Rate: {success_rate:.2%}")
        
        assert success_rate >= 0.85, f"Chat message success rate {success_rate:.2%} below 85%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])