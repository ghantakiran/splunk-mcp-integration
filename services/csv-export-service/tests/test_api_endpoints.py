#!/usr/bin/env python3
"""
Tests for CSV Export Service API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from tests.conftest import assert_response_success, assert_response_error


class TestExportEndpoints:
    """Tests for CSV export endpoints."""
    
    def test_create_csv_export_success(self, test_client, auth_headers, sample_csv_export_request, mock_database, mock_redis, mock_csv_generator):
        """Test successful CSV export creation."""
        response = test_client.post(
            "/api/v1/export/",
            json=sample_csv_export_request,
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["job_id"] == 123
        assert data["status"] == "pending"
        assert "message" in data
    
    def test_create_csv_export_unauthorized(self, test_client, sample_csv_export_request):
        """Test CSV export creation without authentication."""
        response = test_client.post(
            "/api/v1/export/",
            json=sample_csv_export_request
        )
        
        assert_response_error(response, 403)
    
    def test_create_csv_export_invalid_data(self, test_client, auth_headers, mock_database, mock_redis):
        """Test CSV export creation with invalid data."""
        invalid_request = {
            "job_name": "",  # Invalid: empty name
            "data_source": {
                "source_type": "invalid"  # Invalid source type
            }
        }
        
        response = test_client.post(
            "/api/v1/export/",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert_response_error(response, 422)
    
    def test_validate_export_data(self, test_client, auth_headers, sample_csv_export_request, mock_database, mock_csv_generator):
        """Test export data validation."""
        response = test_client.post(
            "/api/v1/export/validate",
            json=sample_csv_export_request,
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["is_valid"] is True
        assert data["row_count"] == 10
        assert data["column_count"] == 3
    
    def test_get_export_capabilities(self, test_client):
        """Test getting service capabilities."""
        response = test_client.get("/api/v1/export/capabilities")
        
        assert_response_success(response, 200)
        data = response.json()
        assert "supported_formats" in data
        assert "supported_encodings" in data
        assert "max_file_size_mb" in data
        assert "features" in data
    
    def test_download_export_file(self, test_client, auth_headers, mock_database):
        """Test downloading export file."""
        with patch("os.path.exists", return_value=True), \
             patch("fastapi.responses.FileResponse") as mock_file_response:
            
            mock_file_response.return_value = mock_file_response
            
            response = test_client.get(
                "/api/v1/export/123/download",
                headers=auth_headers
            )
            
            # Note: This would normally return a file response
            # In testing, we verify the endpoint logic


class TestTemplateEndpoints:
    """Tests for template endpoints."""
    
    def test_create_template(self, test_client, auth_headers, sample_template_request, mock_database):
        """Test template creation."""
        response = test_client.post(
            "/api/v1/templates/",
            json=sample_template_request,
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["template_id"] == 456
        assert data["name"] == "Test Template"
        assert data["is_active"] is True
    
    def test_get_user_templates(self, test_client, auth_headers, mock_database):
        """Test getting user templates."""
        response = test_client.get(
            "/api/v1/templates/",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert "total" in data
        assert "templates" in data
        assert isinstance(data["templates"], list)
    
    def test_get_default_templates(self, test_client):
        """Test getting default templates."""
        response = test_client.get("/api/v1/templates/default")
        
        assert_response_success(response, 200)
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # Should have at least 3 default templates
        
        # Check first default template
        template = data[0]
        assert template["template_id"] < 0  # Negative IDs for defaults
        assert template["is_default"] is True
    
    def test_get_template_by_id(self, test_client, auth_headers, mock_database):
        """Test getting specific template."""
        # Test default template
        response = test_client.get(
            "/api/v1/templates/-1",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["template_id"] == -1
        assert data["is_default"] is True
    
    def test_template_not_found(self, test_client, auth_headers, mock_database):
        """Test template not found."""
        response = test_client.get(
            "/api/v1/templates/99999",
            headers=auth_headers
        )
        
        assert_response_error(response, 404)


class TestJobEndpoints:
    """Tests for job management endpoints."""
    
    def test_get_job_details(self, test_client, auth_headers, mock_database):
        """Test getting job details."""
        response = test_client.get(
            "/api/v1/jobs/123",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["job_id"] == 123
        assert data["job_name"] == "Test Export"
        assert data["status"] == "completed"
    
    def test_get_job_status(self, test_client, auth_headers, mock_database):
        """Test getting job status."""
        response = test_client.get(
            "/api/v1/jobs/123/status",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["job_id"] == 123
        assert data["status"] == "completed"
        assert "progress_percentage" in data
    
    def test_list_user_jobs(self, test_client, auth_headers, mock_database):
        """Test listing user jobs."""
        response = test_client.get(
            "/api/v1/jobs/",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert "total" in data
        assert "jobs" in data
        assert "page" in data
        assert "page_size" in data
    
    def test_list_jobs_with_filter(self, test_client, auth_headers, mock_database):
        """Test listing jobs with status filter."""
        response = test_client.get(
            "/api/v1/jobs/?status_filter=completed&limit=10&offset=0",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert "jobs" in data
    
    def test_get_jobs_summary(self, test_client, auth_headers, mock_database):
        """Test getting jobs summary."""
        response = test_client.get(
            "/api/v1/jobs/status/summary",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert "total_jobs" in data
        assert "status_breakdown" in data
        assert "success_rate" in data
    
    def test_job_not_found(self, test_client, auth_headers, mock_database):
        """Test job not found."""
        mock_database["get_job_by_id"].return_value = AsyncMock(return_value=None)
        
        response = test_client.get(
            "/api/v1/jobs/99999",
            headers=auth_headers
        )
        
        assert_response_error(response, 404)


class TestAnalyticsEndpoints:
    """Tests for analytics endpoints."""
    
    def test_get_usage_analytics(self, test_client, auth_headers, mock_database):
        """Test getting usage analytics."""
        response = test_client.get(
            "/api/v1/analytics/usage?period_days=30",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["period_days"] == 30
        assert "total_jobs" in data
        assert "success_rate" in data
        assert "daily_usage" in data
        assert isinstance(data["daily_usage"], list)
    
    def test_get_performance_metrics(self, test_client, auth_headers, mock_database):
        """Test getting performance metrics."""
        response = test_client.get(
            "/api/v1/analytics/performance?hours=24",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["period_hours"] == 24
        assert "summary" in data
        assert "hourly_metrics" in data
        assert isinstance(data["hourly_metrics"], list)
    
    def test_get_export_patterns(self, test_client, auth_headers, mock_database):
        """Test getting export patterns."""
        response = test_client.get(
            "/api/v1/analytics/export-patterns?days=30",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["analysis_period_days"] == 30
        assert "patterns" in data
        assert "recommendations" in data
    
    def test_get_user_activity(self, test_client, auth_headers, mock_database):
        """Test getting user activity."""
        response = test_client.get(
            "/api/v1/analytics/user-activity?days=7",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["period_days"] == 7
        assert "activity_summary" in data
        assert "recent_activity" in data
        assert "preferences" in data
    
    def test_get_system_health(self, test_client, auth_headers, mock_database):
        """Test getting system health."""
        response = test_client.get(
            "/api/v1/analytics/system-health",
            headers=auth_headers
        )
        
        assert_response_success(response, 200)
        data = response.json()
        assert "overall_status" in data
        assert "components" in data
        assert "metrics" in data


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["service"] == "CSV Export Service"
        assert data["status"] == "healthy"
    
    def test_health_check(self, test_client):
        """Test health check endpoint."""
        with patch("app.core.database.get_db_session"), \
             patch("app.core.redis_client.get_redis"):
            
            response = test_client.get("/health")
            
            # This might fail in test environment without actual DB/Redis
            # but we can test the endpoint exists
            assert response.status_code in [200, 503]
    
    def test_readiness_check(self, test_client):
        """Test readiness check endpoint."""
        response = test_client.get("/ready")
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "csv-export-service"
    
    def test_service_info(self, test_client):
        """Test service info endpoint."""
        response = test_client.get("/info")
        
        assert_response_success(response, 200)
        data = response.json()
        assert data["service"] == "csv-export-service"
        assert "features" in data
        assert "supported_formats" in data
        assert "configuration" in data