"""
Tests for JSON/XML export API endpoints.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status


class TestJsonXmlExportEndpoints:
    """Test cases for JSON/XML export API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_export_success(self, async_client, auth_headers):
        """Test successful export creation."""
        export_request = {
            "data_source": {
                "type": "static",
                "config": {"data": [{"id": 1, "name": "test"}]}
            },
            "export_config": {
                "format": "json",
                "encoding": "utf-8",
                "json_config": {
                    "indent": 2,
                    "sort_keys": True
                },
                "include_metadata": True
            },
            "filename": "test_export.json"
        }
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:create"]
            }
            
            with patch('app.utils.rate_limiter.check_rate_limit') as mock_rate_limit:
                mock_rate_limit.return_value = None
                
                response = await async_client.post(
                    "/api/v1/json-xml-exports/generate",
                    headers=auth_headers,
                    json=export_request
                )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert data["success"] is True
        assert "job" in data
        assert data["job"]["status"] == "completed"
        assert data["job"]["format"] == "json"
        assert "download_url" in data
    
    @pytest.mark.asyncio
    async def test_create_export_unauthorized(self, async_client):
        """Test export creation without authentication."""
        export_request = {
            "data_source": {
                "type": "static",
                "config": {"data": [{"id": 1, "name": "test"}]}
            },
            "export_config": {
                "format": "json"
            }
        }
        
        response = await async_client.post(
            "/api/v1/json-xml-exports/generate",
            json=export_request
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_create_export_permission_denied(self, async_client, auth_headers):
        """Test export creation with insufficient permissions."""
        export_request = {
            "data_source": {
                "type": "static",
                "config": {"data": [{"id": 1, "name": "test"}]}
            },
            "export_config": {
                "format": "json"
            }
        }
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:read"]  # Missing create permission
            }
            
            response = await async_client.post(
                "/api/v1/json-xml-exports/generate",
                headers=auth_headers,
                json=export_request
            )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_create_bulk_exports(self, async_client, auth_headers):
        """Test bulk export creation."""
        bulk_request = {
            "exports": [
                {
                    "data_source": {
                        "type": "static",
                        "config": {"data": [{"id": 1, "name": "test1"}]}
                    },
                    "export_config": {
                        "format": "json"
                    }
                },
                {
                    "data_source": {
                        "type": "static",
                        "config": {"data": [{"id": 2, "name": "test2"}]}
                    },
                    "export_config": {
                        "format": "xml"
                    }
                }
            ],
            "parallel": True
        }
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:create"]
            }
            
            with patch('app.utils.rate_limiter.check_rate_limit') as mock_rate_limit:
                mock_rate_limit.return_value = None
                
                response = await async_client.post(
                    "/api/v1/json-xml-exports/bulk-generate",
                    headers=auth_headers,
                    json=bulk_request
                )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check both exports
        for export_result in data:
            assert "success" in export_result
            assert "job" in export_result
    
    @pytest.mark.asyncio
    async def test_get_export_job(self, async_client, auth_headers):
        """Test getting export job details."""
        job_id = "test-job-123"
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:read"]
            }
            
            response = await async_client.get(
                f"/api/v1/json-xml-exports/jobs/{job_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert data["job"]["job_id"] == job_id
        assert "download_url" in data
    
    @pytest.mark.asyncio
    async def test_list_export_jobs(self, async_client, auth_headers):
        """Test listing export jobs."""
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:read"]
            }
            
            response = await async_client.get(
                "/api/v1/json-xml-exports/jobs",
                headers=auth_headers,
                params={"page": 1, "page_size": 10}
            )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
    
    @pytest.mark.asyncio
    async def test_list_export_jobs_with_filters(self, async_client, auth_headers):
        """Test listing export jobs with filters."""
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:read"]
            }
            
            response = await async_client.get(
                "/api/v1/json-xml-exports/jobs",
                headers=auth_headers,
                params={
                    "page": 1,
                    "page_size": 20,
                    "status_filter": "completed",
                    "format_filter": "json"
                }
            )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_download_export_file(self, async_client, auth_headers):
        """Test downloading export file."""
        job_id = "test-job-123"
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:read"]
            }
            
            with patch('app.utils.rate_limiter.check_rate_limit') as mock_rate_limit:
                mock_rate_limit.return_value = None
                
                response = await async_client.get(
                    f"/api/v1/json-xml-exports/jobs/{job_id}/download",
                    headers=auth_headers
                )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_delete_export_job(self, async_client, auth_headers):
        """Test deleting export job."""
        job_id = "test-job-123"
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:delete"]
            }
            
            response = await async_client.delete(
                f"/api/v1/json-xml-exports/jobs/{job_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    @pytest.mark.asyncio
    async def test_get_export_capabilities(self, async_client):
        """Test getting export capabilities."""
        response = await async_client.get("/api/v1/json-xml-exports/capabilities")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "supported_formats" in data
        assert "supported_encodings" in data
        assert "supported_compressions" in data
        assert "max_file_size_mb" in data
        assert "features" in data
        
        # Check specific capabilities
        assert "json" in data["supported_formats"]
        assert "xml" in data["supported_formats"]
        assert "jsonl" in data["supported_formats"]
        assert "utf-8" in data["supported_encodings"]
        assert "gzip" in data["supported_compressions"]
    
    @pytest.mark.asyncio
    async def test_validate_export_config(self, async_client, auth_headers):
        """Test export configuration validation."""
        export_request = {
            "data_source": {
                "type": "static",
                "config": {"data": [{"id": 1, "name": "test"}]}
            },
            "export_config": {
                "format": "json",
                "max_records": 100000
            }
        }
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:read"]
            }
            
            response = await async_client.post(
                "/api/v1/json-xml-exports/validate",
                headers=auth_headers,
                json=export_request
            )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert "valid" in data
        assert "estimated_size_mb" in data
        assert "record_count" in data
        assert "warnings" in data
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, async_client, auth_headers):
        """Test rate limiting functionality."""
        export_request = {
            "data_source": {
                "type": "static",
                "config": {"data": [{"id": 1, "name": "test"}]}
            },
            "export_config": {
                "format": "json"
            }
        }
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:create"]
            }
            
            # Mock rate limit exceeded
            with patch('app.utils.rate_limiter.check_rate_limit') as mock_rate_limit:
                from app.utils.rate_limiter import RateLimitExceeded
                mock_rate_limit.side_effect = RateLimitExceeded(retry_after=60)
                
                response = await async_client.post(
                    "/api/v1/json-xml-exports/generate",
                    headers=auth_headers,
                    json=export_request
                )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in response.headers
    
    @pytest.mark.asyncio
    async def test_invalid_export_format(self, async_client, auth_headers):
        """Test handling of invalid export format."""
        export_request = {
            "data_source": {
                "type": "static",
                "config": {"data": [{"id": 1, "name": "test"}]}
            },
            "export_config": {
                "format": "invalid_format"
            }
        }
        
        response = await async_client.post(
            "/api/v1/json-xml-exports/generate",
            headers=auth_headers,
            json=export_request
        )
        
        # Should fail validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, async_client, auth_headers):
        """Test handling of missing required fields."""
        export_request = {
            "export_config": {
                "format": "json"
            }
            # Missing data_source
        }
        
        response = await async_client.post(
            "/api/v1/json-xml-exports/generate",
            headers=auth_headers,
            json=export_request
        )
        
        # Should fail validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_empty_bulk_export_request(self, async_client, auth_headers):
        """Test handling of empty bulk export request."""
        bulk_request = {
            "exports": [],  # Empty list
            "parallel": True
        }
        
        response = await async_client.post(
            "/api/v1/json-xml-exports/bulk-generate",
            headers=auth_headers,
            json=bulk_request
        )
        
        # Should fail validation due to min_items=1
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_export_with_compression(self, async_client, auth_headers):
        """Test export with compression options."""
        export_request = {
            "data_source": {
                "type": "static",
                "config": {"data": [{"id": 1, "name": "test"}]}
            },
            "export_config": {
                "format": "json",
                "compression": "gzip",
                "json_config": {
                    "indent": 2
                }
            }
        }
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:create"]
            }
            
            with patch('app.utils.rate_limiter.check_rate_limit') as mock_rate_limit:
                mock_rate_limit.return_value = None
                
                response = await async_client.post(
                    "/api/v1/json-xml-exports/generate",
                    headers=auth_headers,
                    json=export_request
                )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert data["success"] is True
        # Filename should indicate compression
        assert data["job"]["filename"].endswith(".gz")
    
    @pytest.mark.asyncio
    async def test_xml_export_with_custom_config(self, async_client, auth_headers):
        """Test XML export with custom configuration."""
        export_request = {
            "data_source": {
                "type": "static",
                "config": {"data": [{"id": 1, "name": "test"}]}
            },
            "export_config": {
                "format": "xml",
                "xml_config": {
                    "pretty_print": True,
                    "root_tag": "records",
                    "item_tag": "record",
                    "xml_declaration": True,
                    "namespace": "http://example.com/ns"
                }
            }
        }
        
        with patch('app.utils.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "permissions": ["json_xml_export:create"]
            }
            
            with patch('app.utils.rate_limiter.check_rate_limit') as mock_rate_limit:
                mock_rate_limit.return_value = None
                
                response = await async_client.post(
                    "/api/v1/json-xml-exports/generate",
                    headers=auth_headers,
                    json=export_request
                )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert data["success"] is True
        assert data["job"]["format"] == "xml"