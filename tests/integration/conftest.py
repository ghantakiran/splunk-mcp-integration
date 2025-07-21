#!/usr/bin/env python3
"""
Integration test configuration for Splunk MCP Integration.

This module provides pytest fixtures and configuration for integration testing
across service boundaries, testing the complete system workflow.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp
import requests
from fastapi.testclient import TestClient

# Test configuration
TEST_CONFIG = {
    "api_gateway": {
        "host": os.getenv("API_GATEWAY_HOST", "localhost"),
        "port": int(os.getenv("API_GATEWAY_PORT", 8000)),
        "timeout": 30
    },
    "nlp_engine": {
        "host": os.getenv("NLP_ENGINE_HOST", "localhost"),
        "port": int(os.getenv("NLP_ENGINE_PORT", 8001)),
        "timeout": 30
    },
    "visualization": {
        "host": os.getenv("VISUALIZATION_HOST", "localhost"),
        "port": int(os.getenv("VISUALIZATION_PORT", 8002)),
        "timeout": 30
    },
    "alert_manager": {
        "host": os.getenv("ALERT_MANAGER_HOST", "localhost"),
        "port": int(os.getenv("ALERT_MANAGER_PORT", 8003)),
        "timeout": 30
    },
    "email_service": {
        "host": os.getenv("EMAIL_SERVICE_HOST", "localhost"),
        "port": int(os.getenv("EMAIL_SERVICE_PORT", 8006)),
        "timeout": 30
    },
    "webhook_service": {
        "host": os.getenv("WEBHOOK_SERVICE_HOST", "localhost"),
        "port": int(os.getenv("WEBHOOK_SERVICE_PORT", 8007)),
        "timeout": 30
    },
    "slack_bot": {
        "host": os.getenv("SLACK_BOT_HOST", "localhost"),
        "port": int(os.getenv("SLACK_BOT_PORT", 8004)),
        "timeout": 30
    },
    "teams_bot": {
        "host": os.getenv("TEAMS_BOT_HOST", "localhost"),
        "port": int(os.getenv("TEAMS_BOT_PORT", 8005)),
        "timeout": 30
    },
    "redis": {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", 6379)),
        "db": int(os.getenv("REDIS_TEST_DB", 15))
    },
    "postgres": {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_TEST_DB", "test_splunk_mcp"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "password")
    }
}


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration."""
    return TEST_CONFIG


@pytest.fixture
def temp_directory():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_splunk_client():
    """Mock Splunk client for testing."""
    with patch('splunklib.client.connect') as mock_connect:
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        # Mock search functionality
        mock_job = MagicMock()
        mock_job.is_done.return_value = True
        mock_job.results.return_value = [
            {"_time": "2024-01-01T10:00:00", "source": "app.log", "level": "INFO", "message": "Test message 1"},
            {"_time": "2024-01-01T10:01:00", "source": "app.log", "level": "ERROR", "message": "Test error 1"},
            {"_time": "2024-01-01T10:02:00", "source": "app.log", "level": "INFO", "message": "Test message 2"}
        ]
        mock_client.jobs.create.return_value = mock_job
        
        # Mock indexes
        mock_index = MagicMock()
        mock_index.name = "main"
        mock_client.indexes = {"main": mock_index}
        
        yield mock_client


@pytest.fixture
async def authenticated_user():
    """Create an authenticated user for testing."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "permissions": [
            "query:read",
            "dashboard:create",
            "alert:create",
            "export:create"
        ],
        "splunk_access": {
            "indexes": ["main", "security"],
            "search_capabilities": ["search", "rtsearch"],
            "role": "power"
        }
    }


@pytest.fixture
async def auth_headers(authenticated_user):
    """Generate authentication headers for API requests."""
    # In a real implementation, this would generate a valid JWT token
    # For testing, we'll use a mock token
    mock_token = "mock_jwt_token_for_testing"
    return {
        "Authorization": f"Bearer {mock_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
async def service_health_checker():
    """Check if all services are healthy before running tests."""
    async def check_health():
        services = [
            ("API Gateway", f"http://{TEST_CONFIG['api_gateway']['host']}:{TEST_CONFIG['api_gateway']['port']}/health"),
            ("NLP Engine", f"http://{TEST_CONFIG['nlp_engine']['host']}:{TEST_CONFIG['nlp_engine']['port']}/health"),
            ("Visualization", f"http://{TEST_CONFIG['visualization']['host']}:{TEST_CONFIG['visualization']['port']}/health"),
            ("Alert Manager", f"http://{TEST_CONFIG['alert_manager']['host']}:{TEST_CONFIG['alert_manager']['port']}/health"),
        ]
        
        healthy_services = []
        unhealthy_services = []
        
        async with aiohttp.ClientSession() as session:
            for service_name, health_url in services:
                try:
                    async with session.get(health_url, timeout=5) as response:
                        if response.status == 200:
                            healthy_services.append(service_name)
                        else:
                            unhealthy_services.append(f"{service_name} (HTTP {response.status})")
                except Exception as e:
                    unhealthy_services.append(f"{service_name} ({str(e)})")
        
        return {
            "healthy": healthy_services,
            "unhealthy": unhealthy_services,
            "all_healthy": len(unhealthy_services) == 0
        }
    
    return check_health


@pytest.fixture
def sample_natural_language_queries():
    """Sample natural language queries for testing."""
    return [
        {
            "query": "Show me errors from the last hour",
            "expected_spl": 'search error earliest=-1h',
            "expected_fields": ["_time", "source", "level", "message"],
            "category": "simple_search"
        },
        {
            "query": "Count events by source in the last 24 hours",
            "expected_spl": 'search * earliest=-24h | stats count by source',
            "expected_fields": ["source", "count"],
            "category": "aggregation"
        },
        {
            "query": "Show top 10 error sources with failure rates",
            "expected_spl": 'search error | stats count as failures by source | sort -failures | head 10',
            "expected_fields": ["source", "failures"],
            "category": "top_values"
        },
        {
            "query": "Create a chart showing events over time for the last 4 hours",
            "expected_spl": 'search * earliest=-4h | timechart count',
            "expected_fields": ["_time", "count"],
            "category": "timechart",
            "visualization": "line"
        },
        {
            "query": "Alert me when error rate exceeds 100 per minute",
            "expected_alert": {
                "condition": "count > 100",
                "time_window": "1m",
                "search": "search error"
            },
            "category": "alert"
        }
    ]


@pytest.fixture
def sample_chart_configurations():
    """Sample chart configurations for testing visualization."""
    return [
        {
            "type": "line",
            "title": "Events Over Time",
            "data": {
                "labels": ["10:00", "10:05", "10:10", "10:15", "10:20"],
                "datasets": [{
                    "label": "Event Count",
                    "data": [120, 150, 180, 140, 200],
                    "borderColor": "#1f77b4"
                }]
            },
            "options": {
                "responsive": True,
                "interaction": {"intersect": False}
            }
        },
        {
            "type": "bar",
            "title": "Top Error Sources",
            "data": {
                "labels": ["app.log", "error.log", "system.log", "security.log"],
                "datasets": [{
                    "label": "Error Count",
                    "data": [45, 32, 28, 15],
                    "backgroundColor": ["#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {"legend": {"display": True}}
            }
        },
        {
            "type": "pie",
            "title": "Log Level Distribution",
            "data": {
                "labels": ["INFO", "WARN", "ERROR", "DEBUG"],
                "datasets": [{
                    "data": [60, 25, 10, 5],
                    "backgroundColor": ["#1f77b4", "#ff7f0e", "#d62728", "#2ca02c"]
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {"tooltip": {"enabled": True}}
            }
        }
    ]


@pytest.fixture
def sample_alert_configurations():
    """Sample alert configurations for testing."""
    return [
        {
            "name": "High Error Rate Alert",
            "description": "Alert when error rate exceeds threshold",
            "search": "search error | stats count as error_count",
            "condition": "error_count > 100",
            "time_window": "5m",
            "severity": "high",
            "notifications": [
                {"type": "email", "recipients": ["admin@example.com"]},
                {"type": "slack", "channel": "#alerts"}
            ]
        },
        {
            "name": "Server Down Alert",
            "description": "Alert when server stops responding",
            "search": "search source=server.log | stats count",
            "condition": "count = 0",
            "time_window": "2m",
            "severity": "critical",
            "notifications": [
                {"type": "email", "recipients": ["oncall@example.com"]},
                {"type": "teams", "channel": "Operations Team"}
            ]
        },
        {
            "name": "Unusual Activity Alert",
            "description": "Alert on anomalous patterns",
            "search": "search * | stats count by source | where count > 1000",
            "condition": "count > 0",
            "time_window": "15m",
            "severity": "medium",
            "notifications": [
                {"type": "webhook", "url": "https://monitoring.example.com/webhook"}
            ]
        }
    ]


@pytest.fixture
def sample_dashboard_configurations():
    """Sample dashboard configurations for testing."""
    return [
        {
            "title": "System Overview Dashboard",
            "description": "High-level system health and performance metrics",
            "layout": {
                "rows": 3,
                "columns": 2,
                "panels": [
                    {
                        "id": "panel_1",
                        "title": "Event Volume",
                        "type": "line_chart",
                        "position": {"row": 1, "col": 1},
                        "size": {"width": 1, "height": 1},
                        "query": "search * | timechart count"
                    },
                    {
                        "id": "panel_2",
                        "title": "Error Rate",
                        "type": "single_value",
                        "position": {"row": 1, "col": 2},
                        "size": {"width": 1, "height": 1},
                        "query": "search error | stats count"
                    },
                    {
                        "id": "panel_3",
                        "title": "Top Sources",
                        "type": "table",
                        "position": {"row": 2, "col": 1},
                        "size": {"width": 2, "height": 1},
                        "query": "search * | stats count by source | sort -count | head 10"
                    }
                ]
            },
            "refresh_interval": "30s",
            "time_range": "-1h"
        }
    ]


@pytest.fixture
def sample_export_configurations():
    """Sample export configurations for testing."""
    return [
        {
            "format": "pdf",
            "template": "standard",
            "title": "Security Report",
            "description": "Weekly security analysis report",
            "sections": [
                {
                    "title": "Executive Summary",
                    "type": "text",
                    "content": "This report provides an overview of security events for the past week."
                },
                {
                    "title": "Error Trends",
                    "type": "chart",
                    "chart_config": {
                        "type": "line",
                        "query": "search error earliest=-7d | timechart count"
                    }
                },
                {
                    "title": "Top Security Events",
                    "type": "table",
                    "query": "search security earliest=-7d | stats count by event_type | sort -count"
                }
            ]
        },
        {
            "format": "excel",
            "template": "detailed",
            "title": "Performance Analysis",
            "worksheets": [
                {
                    "name": "Raw Data",
                    "query": "search performance earliest=-24h",
                    "format": "table"
                },
                {
                    "name": "Summary",
                    "charts": [
                        {
                            "type": "bar",
                            "query": "search performance earliest=-24h | stats avg(response_time) by server"
                        }
                    ]
                }
            ]
        }
    ]


@pytest.fixture
async def integration_test_data():
    """Comprehensive test data for integration testing."""
    return {
        "conversation_flow": [
            {
                "step": 1,
                "user_input": "Show me errors from the last hour",
                "expected_response_type": "search_results",
                "expected_spl": "search error earliest=-1h"
            },
            {
                "step": 2,
                "user_input": "Create a chart for this data",
                "expected_response_type": "visualization",
                "expected_chart_type": "line"
            },
            {
                "step": 3,
                "user_input": "Add this to a dashboard",
                "expected_response_type": "dashboard_update",
                "expected_action": "panel_added"
            },
            {
                "step": 4,
                "user_input": "Export this dashboard as PDF",
                "expected_response_type": "export_job",
                "expected_format": "pdf"
            }
        ],
        "cross_service_scenarios": [
            {
                "name": "Query to Alert Pipeline",
                "steps": [
                    {"service": "nlp_engine", "action": "parse_query", "input": "Alert when errors exceed 50 per minute"},
                    {"service": "alert_manager", "action": "create_alert", "input": "parsed_alert_config"},
                    {"service": "email_service", "action": "send_notification", "input": "alert_created"}
                ]
            },
            {
                "name": "Dashboard to Export Pipeline",
                "steps": [
                    {"service": "visualization", "action": "create_dashboard", "input": "dashboard_config"},
                    {"service": "pdf_export", "action": "generate_report", "input": "dashboard_data"},
                    {"service": "email_service", "action": "send_report", "input": "pdf_file"}
                ]
            }
        ]
    }


@pytest.fixture
def mock_service_responses():
    """Mock responses for cross-service communication."""
    return {
        "nlp_engine": {
            "/api/v1/spl/translate": {
                "success": True,
                "spl": "search error earliest=-1h",
                "confidence": 0.95,
                "metadata": {
                    "time_range": "-1h",
                    "search_terms": ["error"],
                    "commands": ["search"]
                }
            },
            "/api/v1/ai/suggestions": {
                "success": True,
                "suggestions": [
                    {"text": "Add | stats count by source", "confidence": 0.9},
                    {"text": "Include time range filter", "confidence": 0.8}
                ]
            }
        },
        "visualization": {
            "/api/v1/charts/generate": {
                "success": True,
                "chart_id": "chart_12345",
                "chart_url": "/charts/chart_12345.png",
                "chart_data": {
                    "type": "line",
                    "labels": ["10:00", "10:05", "10:10"],
                    "datasets": [{"data": [10, 15, 8]}]
                }
            },
            "/api/v1/dashboards": {
                "success": True,
                "dashboard_id": "dash_67890",
                "dashboard_url": "/dashboards/dash_67890"
            }
        },
        "alert_manager": {
            "/api/v1/alerts": {
                "success": True,
                "alert_id": "alert_54321",
                "status": "active",
                "next_check": "2024-01-01T10:05:00Z"
            }
        }
    }


# Helper functions for integration tests

def get_service_url(service_name: str, endpoint: str = "") -> str:
    """Get full URL for a service endpoint."""
    config = TEST_CONFIG.get(service_name)
    if not config:
        raise ValueError(f"Unknown service: {service_name}")
    
    base_url = f"http://{config['host']}:{config['port']}"
    return f"{base_url}{endpoint}" if endpoint else base_url


async def wait_for_service_health(service_name: str, timeout: int = 30) -> bool:
    """Wait for a service to become healthy."""
    health_url = get_service_url(service_name, "/health")
    
    async with aiohttp.ClientSession() as session:
        for _ in range(timeout):
            try:
                async with session.get(health_url, timeout=1) as response:
                    if response.status == 200:
                        return True
            except:
                pass
            await asyncio.sleep(1)
    
    return False


async def make_authenticated_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    data: Optional[Dict] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """Make an authenticated request to a service."""
    async with aiohttp.ClientSession() as session:
        kwargs = {
            "headers": headers,
            "timeout": aiohttp.ClientTimeout(total=timeout)
        }
        
        if data:
            kwargs["json"] = data
        
        async with session.request(method, url, **kwargs) as response:
            response_data = await response.json()
            return {
                "status": response.status,
                "data": response_data,
                "headers": dict(response.headers)
            }


def create_test_conversation_id() -> str:
    """Create a unique conversation ID for testing."""
    import uuid
    return f"test_conv_{uuid.uuid4().hex[:8]}"


def create_test_user_context() -> Dict[str, Any]:
    """Create a test user context."""
    return {
        "user_id": "test_user_123",
        "session_id": create_test_conversation_id(),
        "preferences": {
            "timezone": "UTC",
            "default_time_range": "-1h",
            "chart_theme": "default"
        },
        "splunk_context": {
            "default_index": "main",
            "search_role": "power",
            "app_context": "search"
        }
    }