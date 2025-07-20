"""
Tests for BI Integration Service data models.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from app.models.bi_models import (
    BIProvider, IntegrationStatus, DataSourceType, RefreshStatus,
    CreateBIIntegrationRequest, UpdateBIIntegrationRequest,
    BIIntegrationResponse, BIWorkbookResponse, BIDataSourceResponse,
    BIAnalyticsResponse, ConnectionTestResponse
)


class TestEnums:
    """Test suite for enum classes."""

    def test_bi_provider_enum(self):
        """Test BIProvider enum values."""
        assert BIProvider.TABLEAU == "tableau"
        assert BIProvider.POWERBI == "powerbi"
        assert BIProvider.LOOKER == "looker"
        assert BIProvider.QLIK == "qlik"
        
        # Test enum iteration
        providers = list(BIProvider)
        assert len(providers) == 4

    def test_integration_status_enum(self):
        """Test IntegrationStatus enum values."""
        assert IntegrationStatus.ACTIVE == "active"
        assert IntegrationStatus.INACTIVE == "inactive"
        assert IntegrationStatus.ERROR == "error"
        assert IntegrationStatus.PENDING == "pending"
        assert IntegrationStatus.DISABLED == "disabled"

    def test_data_source_type_enum(self):
        """Test DataSourceType enum values."""
        assert DataSourceType.SPLUNK == "splunk"
        assert DataSourceType.DATABASE == "database"
        assert DataSourceType.FILE == "file"
        assert DataSourceType.CLOUD == "cloud"
        assert DataSourceType.API == "api"

    def test_refresh_status_enum(self):
        """Test RefreshStatus enum values."""
        assert RefreshStatus.PENDING == "pending"
        assert RefreshStatus.RUNNING == "running"
        assert RefreshStatus.COMPLETED == "completed"
        assert RefreshStatus.FAILED == "failed"
        assert RefreshStatus.CANCELLED == "cancelled"


class TestCreateBIIntegrationRequest:
    """Test suite for CreateBIIntegrationRequest model."""

    def test_valid_tableau_integration_request(self):
        """Test valid Tableau integration request."""
        data = {
            "name": "Test Tableau Integration",
            "provider": "tableau",
            "server_url": "https://tableau.example.com",
            "site_id": "test-site",
            "credentials": {
                "token_name": "test-token",
                "token_value": "test-token-value"
            },
            "configuration": {
                "auto_refresh": True,
                "refresh_interval": 3600,
                "timeout": 300
            }
        }
        
        request = CreateBIIntegrationRequest(**data)
        
        assert request.name == "Test Tableau Integration"
        assert request.provider == BIProvider.TABLEAU
        assert request.server_url == "https://tableau.example.com"
        assert request.site_id == "test-site"
        assert request.credentials["token_name"] == "test-token"
        assert request.configuration["auto_refresh"] is True

    def test_valid_powerbi_integration_request(self):
        """Test valid Power BI integration request."""
        data = {
            "name": "Test Power BI Integration",
            "provider": "powerbi",
            "server_url": "https://api.powerbi.com",
            "credentials": {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "tenant_id": "test-tenant-id"
            },
            "configuration": {
                "auto_refresh": False,
                "refresh_interval": 7200
            }
        }
        
        request = CreateBIIntegrationRequest(**data)
        
        assert request.name == "Test Power BI Integration"
        assert request.provider == BIProvider.POWERBI
        assert request.server_url == "https://api.powerbi.com"
        assert request.site_id is None  # Optional for Power BI
        assert request.credentials["client_id"] == "test-client-id"

    def test_invalid_name_empty(self):
        """Test validation failure for empty name."""
        data = {
            "name": "",  # Invalid: empty string
            "provider": "tableau",
            "server_url": "https://tableau.example.com",
            "credentials": {"token_name": "test", "token_value": "test"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateBIIntegrationRequest(**data)
        
        errors = exc_info.value.errors()
        name_errors = [e for e in errors if e["loc"] == ("name",)]
        assert len(name_errors) > 0

    def test_invalid_name_too_long(self):
        """Test validation failure for name too long."""
        data = {
            "name": "x" * 256,  # Invalid: exceeds max length
            "provider": "tableau",
            "server_url": "https://tableau.example.com",
            "credentials": {"token_name": "test", "token_value": "test"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateBIIntegrationRequest(**data)
        
        errors = exc_info.value.errors()
        name_errors = [e for e in errors if e["loc"] == ("name",)]
        assert len(name_errors) > 0

    def test_invalid_provider(self):
        """Test validation failure for invalid provider."""
        data = {
            "name": "Test Integration",
            "provider": "invalid_provider",  # Invalid provider
            "server_url": "https://example.com",
            "credentials": {"token_name": "test", "token_value": "test"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateBIIntegrationRequest(**data)
        
        errors = exc_info.value.errors()
        provider_errors = [e for e in errors if e["loc"] == ("provider",)]
        assert len(provider_errors) > 0

    def test_invalid_server_url(self):
        """Test validation failure for invalid server URL."""
        data = {
            "name": "Test Integration",
            "provider": "tableau",
            "server_url": "not-a-valid-url",  # Invalid URL
            "credentials": {"token_name": "test", "token_value": "test"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateBIIntegrationRequest(**data)
        
        errors = exc_info.value.errors()
        url_errors = [e for e in errors if e["loc"] == ("server_url",)]
        assert len(url_errors) > 0

    def test_missing_required_fields(self):
        """Test validation failure for missing required fields."""
        data = {
            "name": "Test Integration"
            # Missing provider, server_url, and credentials
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateBIIntegrationRequest(**data)
        
        errors = exc_info.value.errors()
        assert len(errors) >= 3  # At least provider, server_url, credentials

    def test_empty_credentials(self):
        """Test validation failure for empty credentials."""
        data = {
            "name": "Test Integration",
            "provider": "tableau",
            "server_url": "https://tableau.example.com",
            "credentials": {}  # Invalid: empty credentials
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateBIIntegrationRequest(**data)
        
        errors = exc_info.value.errors()
        creds_errors = [e for e in errors if e["loc"] == ("credentials",)]
        assert len(creds_errors) > 0

    def test_optional_fields_defaults(self):
        """Test default values for optional fields."""
        data = {
            "name": "Test Integration",
            "provider": "tableau",
            "server_url": "https://tableau.example.com",
            "credentials": {"token_name": "test", "token_value": "test"}
        }
        
        request = CreateBIIntegrationRequest(**data)
        
        assert request.site_id is None
        assert request.description is None
        assert request.configuration == {}
        assert request.tags == []
        assert request.metadata == {}


class TestUpdateBIIntegrationRequest:
    """Test suite for UpdateBIIntegrationRequest model."""

    def test_valid_update_request(self):
        """Test valid update request."""
        data = {
            "name": "Updated Integration Name",
            "description": "Updated description",
            "configuration": {
                "auto_refresh": False,
                "refresh_interval": 7200
            },
            "tags": ["updated", "test"]
        }
        
        request = UpdateBIIntegrationRequest(**data)
        
        assert request.name == "Updated Integration Name"
        assert request.description == "Updated description"
        assert request.configuration["auto_refresh"] is False
        assert request.tags == ["updated", "test"]

    def test_partial_update_request(self):
        """Test partial update request with only some fields."""
        data = {
            "name": "Updated Name Only"
        }
        
        request = UpdateBIIntegrationRequest(**data)
        
        assert request.name == "Updated Name Only"
        assert request.description is None
        assert request.configuration is None
        assert request.tags is None

    def test_empty_update_request(self):
        """Test empty update request."""
        request = UpdateBIIntegrationRequest()
        
        assert request.name is None
        assert request.description is None
        assert request.configuration is None
        assert request.tags is None
        assert request.metadata is None

    def test_invalid_name_update(self):
        """Test validation failure for invalid name in update."""
        data = {
            "name": "x" * 256  # Too long
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UpdateBIIntegrationRequest(**data)
        
        errors = exc_info.value.errors()
        name_errors = [e for e in errors if e["loc"] == ("name",)]
        assert len(name_errors) > 0


class TestBIIntegrationResponse:
    """Test suite for BIIntegrationResponse model."""

    def test_valid_integration_response(self):
        """Test valid integration response."""
        integration_id = str(uuid4())
        created_at = datetime.utcnow()
        updated_at = datetime.utcnow()
        
        data = {
            "id": integration_id,
            "name": "Test Integration",
            "provider": "tableau",
            "server_url": "https://tableau.example.com",
            "site_id": "test-site",
            "status": "active",
            "description": "Test description",
            "configuration": {"auto_refresh": True},
            "tags": ["test"],
            "metadata": {"key": "value"},
            "created_by": "test-user@example.com",
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat()
        }
        
        response = BIIntegrationResponse(**data)
        
        assert response.id == integration_id
        assert response.name == "Test Integration"
        assert response.provider == BIProvider.TABLEAU
        assert response.status == IntegrationStatus.ACTIVE
        assert response.created_by == "test-user@example.com"

    def test_response_serialization(self):
        """Test response model serialization."""
        integration_id = str(uuid4())
        
        data = {
            "id": integration_id,
            "name": "Test Integration",
            "provider": "tableau",
            "server_url": "https://tableau.example.com",
            "status": "active",
            "created_by": "test-user@example.com",
            "created_at": "2025-01-18T10:00:00Z",
            "updated_at": "2025-01-18T10:00:00Z"
        }
        
        response = BIIntegrationResponse(**data)
        
        # Test model_dump (Pydantic v2)
        serialized = response.model_dump()
        assert serialized["id"] == integration_id
        assert serialized["provider"] == "tableau"
        assert serialized["status"] == "active"
        
        # Test JSON serialization
        json_data = response.model_dump_json()
        assert isinstance(json_data, str)
        assert integration_id in json_data


class TestBIWorkbookResponse:
    """Test suite for BIWorkbookResponse model."""

    def test_valid_workbook_response(self):
        """Test valid workbook response."""
        workbook_id = str(uuid4())
        integration_id = str(uuid4())
        
        data = {
            "id": workbook_id,
            "integration_id": integration_id,
            "name": "Test Workbook",
            "project_name": "Test Project",
            "description": "Test workbook description",
            "url": "https://tableau.example.com/workbooks/test",
            "size": 1024000,
            "created_at": "2025-01-18T10:00:00Z",
            "updated_at": "2025-01-18T10:00:00Z",
            "tags": ["test", "sample"],
            "metadata": {"view_count": 10}
        }
        
        response = BIWorkbookResponse(**data)
        
        assert response.id == workbook_id
        assert response.integration_id == integration_id
        assert response.name == "Test Workbook"
        assert response.size == 1024000
        assert response.tags == ["test", "sample"]

    def test_workbook_response_optional_fields(self):
        """Test workbook response with optional fields as None."""
        workbook_id = str(uuid4())
        integration_id = str(uuid4())
        
        data = {
            "id": workbook_id,
            "integration_id": integration_id,
            "name": "Test Workbook",
            "created_at": "2025-01-18T10:00:00Z",
            "updated_at": "2025-01-18T10:00:00Z"
        }
        
        response = BIWorkbookResponse(**data)
        
        assert response.project_name is None
        assert response.description is None
        assert response.url is None
        assert response.size is None
        assert response.tags == []
        assert response.metadata == {}


class TestBIDataSourceResponse:
    """Test suite for BIDataSourceResponse model."""

    def test_valid_data_source_response(self):
        """Test valid data source response."""
        ds_id = str(uuid4())
        integration_id = str(uuid4())
        
        data = {
            "id": ds_id,
            "integration_id": integration_id,
            "name": "Test Data Source",
            "type": "splunk",
            "connection_info": {
                "host": "splunk.example.com",
                "port": 8089,
                "index": "main"
            },
            "refresh_status": "completed",
            "last_refresh": "2025-01-18T09:00:00Z",
            "created_at": "2025-01-18T10:00:00Z",
            "updated_at": "2025-01-18T10:00:00Z"
        }
        
        response = BIDataSourceResponse(**data)
        
        assert response.id == ds_id
        assert response.integration_id == integration_id
        assert response.name == "Test Data Source"
        assert response.type == DataSourceType.SPLUNK
        assert response.refresh_status == RefreshStatus.COMPLETED
        assert response.connection_info["host"] == "splunk.example.com"


class TestBIAnalyticsResponse:
    """Test suite for BIAnalyticsResponse model."""

    def test_valid_analytics_response(self):
        """Test valid analytics response."""
        integration_id = str(uuid4())
        
        data = {
            "integration": {
                "id": integration_id,
                "name": "Test Integration",
                "provider": "tableau",
                "status": "active"
            },
            "workbooks": {
                "total": 15,
                "active": 12,
                "last_updated": "2025-01-18T10:00:00Z"
            },
            "data_sources": {
                "total": 8,
                "healthy": 7,
                "failed": 1
            },
            "usage": {
                "daily_requests": 156,
                "weekly_requests": 1089,
                "monthly_requests": 4521
            }
        }
        
        response = BIAnalyticsResponse(**data)
        
        assert response.integration["id"] == integration_id
        assert response.workbooks["total"] == 15
        assert response.data_sources["total"] == 8
        assert response.usage["daily_requests"] == 156

    def test_analytics_response_optional_fields(self):
        """Test analytics response with minimal required fields."""
        integration_id = str(uuid4())
        
        data = {
            "integration": {
                "id": integration_id,
                "name": "Test Integration",
                "provider": "tableau",
                "status": "active"
            }
        }
        
        response = BIAnalyticsResponse(**data)
        
        assert response.workbooks is None
        assert response.data_sources is None
        assert response.usage is None


class TestConnectionTestResponse:
    """Test suite for ConnectionTestResponse model."""

    def test_successful_connection_test_response(self):
        """Test successful connection test response."""
        data = {
            "success": True,
            "server_info": {
                "version": "2023.3",
                "build": "20230918.23.0927.1526"
            },
            "response_time_ms": 245,
            "timestamp": "2025-01-18T10:00:00Z"
        }
        
        response = ConnectionTestResponse(**data)
        
        assert response.success is True
        assert response.server_info["version"] == "2023.3"
        assert response.response_time_ms == 245
        assert response.error is None

    def test_failed_connection_test_response(self):
        """Test failed connection test response."""
        data = {
            "success": False,
            "error": "Authentication failed",
            "error_code": "AUTH_FAILED",
            "timestamp": "2025-01-18T10:00:00Z"
        }
        
        response = ConnectionTestResponse(**data)
        
        assert response.success is False
        assert response.error == "Authentication failed"
        assert response.error_code == "AUTH_FAILED"
        assert response.server_info is None

    def test_connection_test_response_validation(self):
        """Test connection test response validation."""
        # Test missing required fields
        with pytest.raises(ValidationError):
            ConnectionTestResponse()
        
        # Test valid minimal response
        data = {
            "success": True,
            "timestamp": "2025-01-18T10:00:00Z"
        }
        
        response = ConnectionTestResponse(**data)
        assert response.success is True
        assert response.timestamp == "2025-01-18T10:00:00Z"


class TestModelValidators:
    """Test suite for custom model validators."""

    def test_url_validation(self):
        """Test URL validation in models."""
        # Valid URLs
        valid_urls = [
            "https://tableau.example.com",
            "https://api.powerbi.com",
            "http://localhost:8080",
            "https://test.com:8443/path"
        ]
        
        for url in valid_urls:
            data = {
                "name": "Test",
                "provider": "tableau",
                "server_url": url,
                "credentials": {"token_name": "test", "token_value": "test"}
            }
            request = CreateBIIntegrationRequest(**data)
            assert request.server_url == url

    def test_configuration_validation(self):
        """Test configuration field validation."""
        # Valid configurations
        valid_configs = [
            {"auto_refresh": True, "refresh_interval": 3600},
            {"timeout": 300, "max_retries": 3},
            {}  # Empty is valid
        ]
        
        for config in valid_configs:
            data = {
                "name": "Test",
                "provider": "tableau",
                "server_url": "https://example.com",
                "credentials": {"token_name": "test", "token_value": "test"},
                "configuration": config
            }
            request = CreateBIIntegrationRequest(**data)
            assert request.configuration == config

    def test_tags_validation(self):
        """Test tags field validation."""
        # Valid tags
        valid_tags = [
            ["tag1", "tag2"],
            ["production"],
            []  # Empty is valid
        ]
        
        for tags in valid_tags:
            data = {
                "name": "Test",
                "provider": "tableau",
                "server_url": "https://example.com",
                "credentials": {"token_name": "test", "token_value": "test"},
                "tags": tags
            }
            request = CreateBIIntegrationRequest(**data)
            assert request.tags == tags