#!/usr/bin/env python3
"""
Comprehensive test configuration for NLP Engine Service.

This module provides fixtures, mocks, and test utilities for comprehensive
testing of the NLP Engine Service components including AI features,
SPL translation, query processing, and API endpoints.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch
import tempfile
import os
from datetime import datetime, timedelta

# Test client imports
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Mock settings for testing
@pytest.fixture
def mock_settings():
    """Mock NLP Engine settings configuration."""
    with patch('app.core.config.settings') as mock:
        mock.OPENAI_API_KEY = "test-openai-key"
        mock.ANTHROPIC_API_KEY = "test-anthropic-key"
        mock.DATABASE_URL = "postgresql://test:test@localhost/test_nlp"
        mock.REDIS_URL = "redis://localhost:6379/1"
        mock.JWT_SECRET_KEY = "test-secret-key"
        mock.JWT_ALGORITHM = "HS256"
        mock.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock.API_HOST = "0.0.0.0"
        mock.API_PORT = 8001
        mock.DEBUG = True
        mock.LOG_LEVEL = "DEBUG"
        mock.MAX_TOKENS = 4000
        mock.TEMPERATURE = 0.1
        mock.MODEL_NAME = "gpt-4"
        mock.DEFAULT_INDEX = "main"
        mock.MAX_QUERY_TIME_SECONDS = 300
        mock.CACHE_TTL = 3600
        yield mock

@pytest.fixture
def mock_database():
    """Mock database operations."""
    with patch('app.core.database.get_db_session') as mock:
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar.return_value = None
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_session

@pytest.fixture
def mock_redis():
    """Mock Redis operations."""
    with patch('app.core.redis_client.get_redis_client') as mock:
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_client.set = AsyncMock()
        mock_client.delete = AsyncMock()
        mock_client.exists.return_value = False
        mock_client.expire = AsyncMock()
        mock_client.close = AsyncMock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_auth():
    """Mock authentication utilities."""
    with patch('app.utils.auth.get_current_user') as mock:
        mock_user = {
            "user_id": "test-user-123",
            "username": "test_user",
            "email": "test@example.com",
            "roles": ["user"],
            "permissions": ["nlp:read", "nlp:write"],
            "is_active": True
        }
        mock.return_value = mock_user
        yield mock_user

@pytest.fixture
def auth_headers():
    """Authentication headers for API requests."""
    return {
        "Authorization": "Bearer test-jwt-token",
        "Content-Type": "application/json"
    }

@pytest.fixture
def sample_user_context():
    """Sample user context for testing."""
    return {
        "user_id": "test-user-123",
        "username": "test_user",
        "roles": ["user"],
        "permissions": ["splunk:search", "splunk:read"],
        "accessible_indexes": ["main", "security", "web"],
        "session_id": "session-123",
        "preferences": {
            "timezone": "UTC",
            "date_format": "%Y-%m-%d %H:%M:%S"
        }
    }

@pytest.fixture
def sample_natural_language_queries():
    """Sample natural language queries for testing."""
    return [
        {
            "query": "show me errors from the last hour",
            "expected_search": "search error earliest=-1h",
            "expected_intent": "search",
            "complexity": "simple"
        },
        {
            "query": "count events by source type in the last 24 hours",
            "expected_search": "search earliest=-24h | stats count by sourcetype",
            "expected_intent": "aggregation",
            "complexity": "medium"
        },
        {
            "query": "find failed login attempts with source IP addresses",
            "expected_search": 'search "failed login" OR "login failed" | eval src_ip=coalesce(src, clientip, source_ip)',
            "expected_intent": "security_analysis",
            "complexity": "medium"
        },
        {
            "query": "show top 10 users by event count in security index",
            "expected_search": "search index=security | top 10 user",
            "expected_intent": "ranking",
            "complexity": "medium"
        },
        {
            "query": "create a chart showing error trends over time for the last 7 days",
            "expected_search": "search error earliest=-7d | timechart span=1h count",
            "expected_intent": "visualization",
            "complexity": "complex"
        }
    ]

@pytest.fixture
def sample_spl_queries():
    """Sample SPL queries for validation testing."""
    return [
        {
            "spl": "search error earliest=-1h",
            "is_valid": True,
            "estimated_time": 5.2,
            "result_count": 150
        },
        {
            "spl": "search earliest=-24h | stats count by sourcetype",
            "is_valid": True,
            "estimated_time": 12.5,
            "result_count": 25
        },
        {
            "spl": "search index=security | top 10 user",
            "is_valid": True,
            "estimated_time": 8.1,
            "result_count": 10
        },
        {
            "spl": "invalid spl syntax here",
            "is_valid": False,
            "error": "Syntax error in search command"
        }
    ]

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for AI provider testing."""
    with patch('app.ai.providers.openai') as mock:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '{"spl": "search error earliest=-1h", "confidence": 0.95, "explanation": "Search for errors in the last hour"}'
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock.OpenAI.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for AI provider testing."""
    with patch('app.ai.providers.anthropic') as mock:
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [Mock()]
        mock_message.content[0].text = '{"spl": "search error earliest=-1h", "confidence": 0.92, "explanation": "Search for errors in the last hour"}'
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock.Anthropic.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_query_performance():
    """Mock query performance analysis."""
    with patch('app.ai.query_performance_analysis.QueryPerformanceAnalyzer') as mock:
        mock_analyzer = Mock()
        mock_analyzer.analyze_performance = AsyncMock(return_value={
            "estimated_time_seconds": 10.5,
            "complexity_score": 0.7,
            "resource_usage": "medium",
            "optimization_suggestions": [
                "Consider adding time range filters",
                "Use more specific search terms"
            ],
            "risk_level": "low"
        })
        mock_analyzer.estimate_result_count = AsyncMock(return_value=250)
        mock.return_value = mock_analyzer
        yield mock_analyzer

@pytest.fixture
def mock_index_optimization():
    """Mock index selection optimization."""
    with patch('app.ai.index_selection_optimization.IndexOptimizer') as mock:
        mock_optimizer = Mock()
        mock_optimizer.optimize_indexes = AsyncMock(return_value={
            "recommended_indexes": ["main", "security"],
            "confidence": 0.85,
            "reasoning": "Based on query content and user permissions",
            "estimated_performance_gain": 0.3
        })
        mock.return_value = mock_optimizer
        yield mock_optimizer

@pytest.fixture
def mock_time_range_optimizer():
    """Mock time range optimization."""
    with patch('app.ai.time_range_optimization.TimeRangeOptimizer') as mock:
        mock_optimizer = Mock()
        mock_optimizer.optimize_time_range = AsyncMock(return_value={
            "optimized_earliest": "-1h",
            "optimized_latest": "now",
            "optimization_strategy": "relative_time",
            "estimated_performance_gain": 0.25
        })
        mock.return_value = mock_optimizer
        yield mock_optimizer

@pytest.fixture
def sample_ai_features_data():
    """Sample data for AI features testing."""
    return {
        "predictive_analytics": {
            "time_series_data": [
                {"_time": "2024-01-01T10:00:00", "count": 120, "trend": "increasing"},
                {"_time": "2024-01-01T11:00:00", "count": 150, "trend": "increasing"},
                {"_time": "2024-01-01T12:00:00", "count": 180, "trend": "stable"}
            ],
            "forecast_horizon": "24h",
            "confidence_level": 0.85
        },
        "anomaly_detection": {
            "baseline_data": [100, 105, 98, 102, 99, 104, 101],
            "current_value": 250,
            "threshold": 3.0,
            "is_anomaly": True,
            "severity": "high"
        },
        "intelligent_suggestions": {
            "query_history": [
                "search error earliest=-1h",
                "search failed_login earliest=-4h",
                "search index=security | top user"
            ],
            "context": "security_analysis",
            "suggestions": [
                "search error earliest=-1h | stats count by source",
                "search failed_login earliest=-1h | stats count by user"
            ]
        }
    }

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_client(mock_settings, mock_database, mock_redis):
    """FastAPI test client with mocked dependencies."""
    from app.main import app
    
    # Override dependencies with mocks
    with patch('app.core.config.settings', mock_settings):
        client = TestClient(app)
        yield client

@pytest.fixture
async def async_client(mock_settings, mock_database, mock_redis):
    """Async HTTP client for testing."""
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mock_data = {
            "temp_dir": temp_dir,
            "created_files": [],
            "read_files": {}
        }
        
        def mock_write_file(file_path: str, content: str):
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
            mock_data["created_files"].append(file_path)
            return full_path
        
        def mock_read_file(file_path: str):
            full_path = os.path.join(temp_dir, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()
                mock_data["read_files"][file_path] = content
                return content
            return None
        
        mock_data["write_file"] = mock_write_file
        mock_data["read_file"] = mock_read_file
        yield mock_data

# Utility functions for tests
def create_mock_response(status_code: int, json_data: Dict[str, Any]) -> Mock:
    """Create a mock HTTP response."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    return mock_response

def assert_spl_query_valid(spl_query: str) -> bool:
    """Assert that an SPL query has valid basic syntax."""
    if not spl_query or not isinstance(spl_query, str):
        return False
    
    # Basic SPL syntax validation
    spl_query = spl_query.strip()
    
    # Must start with search or other valid command
    valid_starts = ['search', 'eval', 'stats', 'sort', 'head', 'tail', 'fields', 'table', 'timechart']
    starts_correctly = any(spl_query.lower().startswith(cmd) for cmd in valid_starts)
    
    # Check for basic structure
    has_reasonable_length = len(spl_query) > 3
    
    return starts_correctly and has_reasonable_length

def assert_response_structure(response_data: Dict[str, Any], required_fields: List[str]) -> bool:
    """Assert that a response has the required structure."""
    if not isinstance(response_data, dict):
        return False
    
    for field in required_fields:
        if field not in response_data:
            return False
    
    return True

# Test configuration
pytest_plugins = []

# Configure async testing
@pytest.fixture(autouse=True)
def configure_async_testing():
    """Configure async testing environment."""
    # Set async test timeout
    import asyncio
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())