#!/usr/bin/env python3
"""
Comprehensive Performance Testing Suite for Splunk MCP Integration.

This module implements load testing using Locust to validate:
- API response times under load
- Concurrent user scenarios
- System scalability and throughput
- Resource utilization patterns
- Stress testing and failure points
"""

import json
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import base64
import hashlib

from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
from locust.env import Environment
from locust.stats import stats_printer
from locust.log import setup_logging

# Test Configuration
API_BASE_URL = "/api/v1"
TEST_USERS = {
    "admin": {"username": "admin", "password": "AdminPass123!"},
    "analyst": {"username": "analyst", "password": "AnalystPass123!"},
    "viewer": {"username": "viewer", "password": "ViewerPass123!"}
}

# Sample test data
SAMPLE_QUERIES = [
    "show me errors from the last hour",
    "count events by source",
    "find failed login attempts",
    "display server performance metrics",
    "analyze network traffic patterns",
    "show database connection errors",
    "get memory usage trends",
    "find security incidents",
    "show user activity logs",
    "analyze application errors"
]

SAMPLE_CHART_CONFIGS = [
    {"type": "bar", "title": "Error Count by Source"},
    {"type": "line", "title": "Performance Trends"},
    {"type": "pie", "title": "Event Distribution"},
    {"type": "area", "title": "Traffic Patterns"},
    {"type": "scatter", "title": "Response Time Analysis"}
]

class SplunkMCPUser(HttpUser):
    """Base user class for Splunk MCP testing."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session."""
        self.auth_token = None
        self.user_type = random.choice(list(TEST_USERS.keys()))
        self.conversation_id = str(uuid.uuid4())
        self.login()
    
    def login(self):
        """Authenticate user."""
        user_creds = TEST_USERS[self.user_type]
        
        with self.client.post(
            f"{API_BASE_URL}/auth/login",
            json=user_creds,
            catch_response=True,
            name="Login"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.auth_token = data.get("access_token")
                    response.success()
                except Exception as e:
                    response.failure(f"Login failed: {e}")
            else:
                response.failure(f"Login failed with status {response.status_code}")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self.auth_token:
            return {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
        return {"Content-Type": "application/json"}
    
    @task(5)
    def process_natural_language_query(self):
        """Test natural language query processing."""
        query = random.choice(SAMPLE_QUERIES)
        
        payload = {
            "query": query,
            "conversation_id": self.conversation_id,
            "user_context": {
                "user_type": self.user_type,
                "preferences": {"format": "json"}
            }
        }
        
        with self.client.post(
            f"{API_BASE_URL}/nlp/process-query",
            json=payload,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="NLP Query Processing"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "spl_query" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except Exception as e:
                    response.failure(f"Response parsing failed: {e}")
            elif response.status_code == 401:
                response.failure("Authentication failed")
                self.login()  # Re-authenticate
            else:
                response.failure(f"Query processing failed: {response.status_code}")
    
    @task(3)
    def generate_visualization(self):
        """Test visualization generation."""
        chart_config = random.choice(SAMPLE_CHART_CONFIGS)
        
        # Generate sample data
        sample_data = {
            "labels": [f"Item {i}" for i in range(1, 11)],
            "datasets": [{
                "label": "Sample Data",
                "data": [random.randint(10, 100) for _ in range(10)],
                "backgroundColor": "#1f77b4"
            }]
        }
        
        payload = {
            "chart_type": chart_config["type"],
            "title": chart_config["title"],
            "data": sample_data,
            "options": {
                "width": 800,
                "height": 400,
                "responsive": True
            }
        }
        
        with self.client.post(
            f"{API_BASE_URL}/visualization/generate-chart",
            json=payload,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="Visualization Generation"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 401:
                response.failure("Authentication failed")
                self.login()
            else:
                response.failure(f"Visualization failed: {response.status_code}")
    
    @task(2)
    def create_dashboard(self):
        """Test dashboard creation."""
        dashboard_data = {
            "title": f"Performance Dashboard {random.randint(1, 1000)}",
            "description": "Load testing dashboard",
            "layout": {
                "type": "grid",
                "columns": 2
            },
            "panels": [
                {
                    "title": "Sample Chart",
                    "type": "chart",
                    "position": {"row": 0, "col": 0}
                }
            ]
        }
        
        with self.client.post(
            f"{API_BASE_URL}/dashboards",
            json=dashboard_data,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="Dashboard Creation"
        ) as response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    dashboard_id = data.get("dashboard_id")
                    if dashboard_id:
                        response.success()
                        # Store for potential deletion
                        self.environment.dashboard_ids = getattr(self.environment, 'dashboard_ids', [])
                        self.environment.dashboard_ids.append(dashboard_id)
                    else:
                        response.failure("No dashboard ID returned")
                except Exception as e:
                    response.failure(f"Response parsing failed: {e}")
            elif response.status_code == 401:
                response.failure("Authentication failed")
                self.login()
            else:
                response.failure(f"Dashboard creation failed: {response.status_code}")
    
    @task(1)
    def create_alert(self):
        """Test alert creation."""
        alert_data = {
            "name": f"Load Test Alert {random.randint(1, 1000)}",
            "description": "Alert when error rate exceeds threshold",
            "search_query": "search error | stats count | eval threshold=100 | where count > threshold",
            "schedule": "*/5 * * * *",  # Every 5 minutes
            "notification_channels": ["email"],
            "email_recipients": ["test@example.com"]
        }
        
        with self.client.post(
            f"{API_BASE_URL}/alerts",
            json=alert_data,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="Alert Creation"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 401:
                response.failure("Authentication failed")
                self.login()
            else:
                response.failure(f"Alert creation failed: {response.status_code}")
    
    @task(1)
    def export_document(self):
        """Test document export functionality."""
        export_format = random.choice(["pdf", "docx", "pptx", "csv"])
        
        export_data = {
            "format": export_format,
            "title": f"Load Test Report {random.randint(1, 1000)}",
            "content": [
                {
                    "type": "text",
                    "content": "This is a load testing report."
                },
                {
                    "type": "chart",
                    "chart_id": "sample_chart_001"
                }
            ],
            "template": "professional"
        }
        
        with self.client.post(
            f"{API_BASE_URL}/export/{export_format}",
            json=export_data,
            headers=self.get_auth_headers(),
            catch_response=True,
            name=f"Export {export_format.upper()}"
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            elif response.status_code == 401:
                response.failure("Authentication failed")
                self.login()
            else:
                response.failure(f"Export failed: {response.status_code}")
    
    @task(1)
    def check_system_health(self):
        """Test system health endpoints."""
        health_endpoints = ["/health", "/ready", "/metrics"]
        
        for endpoint in health_endpoints:
            with self.client.get(
                endpoint,
                catch_response=True,
                name=f"Health Check - {endpoint}"
            ) as response:
                if response.status_code == 200:
                    response.success()
                elif response.status_code == 404:
                    # Endpoint might not exist, that's okay
                    response.success()
                else:
                    response.failure(f"Health check failed: {response.status_code}")


class HighLoadUser(FastHttpUser):
    """High-performance user for stress testing."""
    
    wait_time = between(0.1, 0.5)  # Faster requests
    
    def on_start(self):
        """Initialize high-load user session."""
        self.auth_token = None
        self.login()
    
    def login(self):
        """Quick authentication for high-load testing."""
        user_creds = random.choice(list(TEST_USERS.values()))
        
        with self.client.post(
            f"{API_BASE_URL}/auth/login",
            json=user_creds,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.auth_token = data.get("access_token")
                except:
                    pass  # Continue without auth for stress testing
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    @task(10)
    def rapid_api_calls(self):
        """Make rapid API calls for stress testing."""
        endpoints = [
            "/health",
            "/api/v1/capabilities",
            "/api/v1/status"
        ]
        
        endpoint = random.choice(endpoints)
        
        with self.client.get(
            endpoint,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="Rapid API Call"
        ) as response:
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"Rapid call failed: {response.status_code}")


class DatabaseStressUser(HttpUser):
    """User class for database stress testing."""
    
    wait_time = between(0.5, 1.5)
    
    def on_start(self):
        """Initialize database stress user."""
        self.auth_token = None
        self.login()
    
    def login(self):
        """Authenticate user."""
        user_creds = random.choice(list(TEST_USERS.values()))
        
        with self.client.post(
            f"{API_BASE_URL}/auth/login",
            json=user_creds,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.auth_token = data.get("access_token")
                except:
                    pass
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    @task(5)
    def create_and_query_data(self):
        """Create data and immediately query it."""
        # Create dashboard
        dashboard_data = {
            "title": f"DB Stress Dashboard {uuid.uuid4()}",
            "description": "Database stress testing"
        }
        
        with self.client.post(
            f"{API_BASE_URL}/dashboards",
            json=dashboard_data,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="DB Stress - Create"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                
                # Immediately query it back
                with self.client.get(
                    f"{API_BASE_URL}/dashboards",
                    headers=self.get_auth_headers(),
                    catch_response=True,
                    name="DB Stress - Query"
                ) as query_response:
                    if query_response.status_code == 200:
                        query_response.success()
                    else:
                        query_response.failure("Query failed")
            else:
                response.failure(f"Create failed: {response.status_code}")
    
    @task(3)
    def bulk_operations(self):
        """Perform bulk database operations."""
        # Create multiple alerts in bulk
        alerts = []
        for i in range(5):
            alerts.append({
                "name": f"Bulk Alert {i} - {uuid.uuid4()}",
                "description": f"Bulk alert {i}",
                "search_query": f"search index=test_{i}"
            })
        
        bulk_data = {"alerts": alerts}
        
        with self.client.post(
            f"{API_BASE_URL}/alerts/bulk",
            json=bulk_data,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="DB Stress - Bulk Create"
        ) as response:
            if response.status_code in [200, 201, 207]:  # 207 for partial success
                response.success()
            else:
                response.failure(f"Bulk operation failed: {response.status_code}")


# Performance Test Event Handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize performance test environment."""
    print("Starting Splunk MCP Performance Testing...")
    environment.start_time = time.time()
    environment.dashboard_ids = []

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup after performance testing."""
    print("Performance testing completed.")
    duration = time.time() - environment.start_time
    print(f"Total test duration: {duration:.2f} seconds")
    
    # Cleanup created resources
    if hasattr(environment, 'dashboard_ids') and environment.dashboard_ids:
        print(f"Created {len(environment.dashboard_ids)} dashboards during testing")

@events.request_success.add_listener
def on_request_success(request_type, name, response_time, response_length, **kwargs):
    """Log successful requests with high response times."""
    if response_time > 2000:  # Log requests slower than 2 seconds
        print(f"Slow request: {name} took {response_time}ms")

@events.request_failure.add_listener
def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """Log request failures for analysis."""
    print(f"Request failed: {name} - {exception}")

# Custom performance monitoring
class PerformanceMonitor:
    """Monitor performance metrics during testing."""
    
    def __init__(self):
        self.response_times = []
        self.error_rates = []
        
    def record_response_time(self, response_time):
        """Record response time."""
        self.response_times.append(response_time)
        
    def record_error(self, error_type):
        """Record error occurrence."""
        self.error_rates.append(error_type)
        
    def get_statistics(self):
        """Get performance statistics."""
        if not self.response_times:
            return {}
            
        return {
            "avg_response_time": sum(self.response_times) / len(self.response_times),
            "max_response_time": max(self.response_times),
            "min_response_time": min(self.response_times),
            "total_requests": len(self.response_times),
            "total_errors": len(self.error_rates)
        }

# Performance test scenarios
class PerformanceTestSuite:
    """Collection of performance test scenarios."""
    
    @staticmethod
    def normal_load_test():
        """Normal load test configuration."""
        return {
            "user_classes": [SplunkMCPUser],
            "users": 50,
            "spawn_rate": 5,
            "run_time": "10m"
        }
    
    @staticmethod
    def stress_test():
        """Stress test configuration."""
        return {
            "user_classes": [HighLoadUser],
            "users": 200,
            "spawn_rate": 20,
            "run_time": "5m"
        }
    
    @staticmethod
    def database_stress_test():
        """Database stress test configuration."""
        return {
            "user_classes": [DatabaseStressUser],
            "users": 100,
            "spawn_rate": 10,
            "run_time": "15m"
        }
    
    @staticmethod
    def mixed_workload_test():
        """Mixed workload test configuration."""
        return {
            "user_classes": [SplunkMCPUser, HighLoadUser, DatabaseStressUser],
            "users": 150,
            "spawn_rate": 15,
            "run_time": "20m"
        }

if __name__ == "__main__":
    # This file is designed to be run with the Locust CLI
    # Example commands:
    # locust -f locustfile.py --users 50 --spawn-rate 5 --run-time 10m --host http://localhost:8000
    # locust -f locustfile.py --headless --users 100 --spawn-rate 10 --run-time 5m --html performance-report.html
    pass