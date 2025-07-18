"""
Tests for API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from app.models.pdf_models import JobStatus, OutputFormat, TemplateType


class TestPDFExportEndpoints:
    """Test PDF export API endpoints."""
    
    @pytest.mark.asyncio
    async def test_generate_pdf_success(self, client, auth_headers, pdf_generation_request):
        """Test successful PDF generation request."""
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.check_rate_limit', return_value=True) as mock_rate_limit, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', return_value=1) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.post(
                "/api/v1/pdf-exports/generate",
                json=pdf_generation_request,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['job_id'] == 1
            assert data['status'] == JobStatus.PENDING.value
            assert data['message'] == "PDF generation started"
            
            mock_rate_limit.assert_called_once()
            mock_execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_pdf_rate_limit_exceeded(self, client, auth_headers, pdf_generation_request):
        """Test PDF generation with rate limit exceeded."""
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.check_rate_limit', return_value=False) as mock_rate_limit:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.post(
                "/api/v1/pdf-exports/generate",
                json=pdf_generation_request,
                headers=auth_headers
            )
            
            assert response.status_code == 429
            data = response.json()
            assert "Rate limit exceeded" in data['detail']
    
    @pytest.mark.asyncio
    async def test_generate_pdf_invalid_request(self, client, auth_headers):
        """Test PDF generation with invalid request data."""
        invalid_request = {
            "job_name": "",  # Empty job name
            "template_id": "invalid",  # Invalid type
            "output_format": "invalid_format"  # Invalid format
        }
        
        response = await client.post(
            "/api/v1/pdf-exports/generate",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_bulk_generate_pdf_success(self, client, auth_headers):
        """Test successful bulk PDF generation."""
        bulk_request = {
            "template_id": 1,
            "output_format": "pdf",
            "jobs": [
                {
                    "job_name": "Bulk Job 1",
                    "parameters": {"title": "Report 1"},
                    "data_source": {}
                },
                {
                    "job_name": "Bulk Job 2",
                    "parameters": {"title": "Report 2"},
                    "data_source": {}
                }
            ]
        }
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.check_rate_limit', return_value=True) as mock_rate_limit, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', side_effect=[1, 2]) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.post(
                "/api/v1/pdf-exports/bulk-generate",
                json=bulk_request,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]['job_id'] == 1
            assert data[1]['job_id'] == 2
            
            mock_rate_limit.assert_called_once()
            assert mock_execute_query.call_count == 2
    
    @pytest.mark.asyncio
    async def test_list_jobs_success(self, client, auth_headers):
        """Test successful job listing."""
        mock_jobs = [
            {
                "id": 1,
                "user_id": 1,
                "template_id": 1,
                "job_name": "Test Job",
                "status": "completed",
                "parameters": {},
                "data_source": {},
                "output_format": "pdf",
                "file_path": "/tmp/test.pdf",
                "file_size": 1024,
                "page_count": 1,
                "error_message": None,
                "generation_time_ms": 5000,
                "created_at": datetime.now(),
                "started_at": datetime.now(),
                "completed_at": datetime.now()
            }
        ]
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', side_effect=[1, mock_jobs]) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/pdf-exports/jobs",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 1
            assert len(data['jobs']) == 1
            assert data['jobs'][0]['id'] == 1
            assert data['jobs'][0]['job_name'] == "Test Job"
    
    @pytest.mark.asyncio
    async def test_list_jobs_with_filters(self, client, auth_headers):
        """Test job listing with filters."""
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', side_effect=[0, []]) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/pdf-exports/jobs?status=completed&template_id=1&page=1&page_size=10",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 0
            assert len(data['jobs']) == 0
    
    @pytest.mark.asyncio
    async def test_get_job_success(self, client, auth_headers):
        """Test successful job retrieval."""
        mock_job = {
            "id": 1,
            "user_id": 1,
            "template_id": 1,
            "job_name": "Test Job",
            "status": "completed",
            "parameters": {},
            "data_source": {},
            "output_format": "pdf",
            "file_path": "/tmp/test.pdf",
            "file_size": 1024,
            "page_count": 1,
            "error_message": None,
            "generation_time_ms": 5000,
            "created_at": datetime.now(),
            "started_at": datetime.now(),
            "completed_at": datetime.now()
        }
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', return_value=mock_job) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/pdf-exports/jobs/1",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['id'] == 1
            assert data['job_name'] == "Test Job"
            assert data['status'] == "completed"
    
    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client, auth_headers):
        """Test job retrieval when job not found."""
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', return_value=None) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/pdf-exports/jobs/999",
                headers=auth_headers
            )
            
            assert response.status_code == 404
            data = response.json()
            assert data['detail'] == "Job not found"
    
    @pytest.mark.asyncio
    async def test_get_job_status_success(self, client, auth_headers):
        """Test successful job status retrieval."""
        mock_job = {"id": 1, "user_id": 1}
        mock_status = {
            "job_id": 1,
            "status": "processing",
            "runtime_seconds": 10.5
        }
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', return_value=mock_job) as mock_execute_query, \
             patch('app.api.v1.endpoints.pdf_exports.pdf_generator.get_job_status', return_value=mock_status) as mock_generator:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/pdf-exports/jobs/1/status",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['job_id'] == 1
            assert data['status'] == "processing"
            assert data['runtime_seconds'] == 10.5
    
    @pytest.mark.asyncio
    async def test_cancel_job_success(self, client, auth_headers):
        """Test successful job cancellation."""
        mock_job = {"id": 1, "user_id": 1, "status": "processing"}
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', return_value=mock_job) as mock_execute_query, \
             patch('app.api.v1.endpoints.pdf_exports.pdf_generator.cancel_job', return_value=True) as mock_generator:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.post(
                "/api/v1/pdf-exports/jobs/1/cancel",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['message'] == "Job cancelled successfully"
            
            mock_generator.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_cancel_job_cannot_cancel(self, client, auth_headers):
        """Test job cancellation when job cannot be cancelled."""
        mock_job = {"id": 1, "user_id": 1, "status": "completed"}
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', return_value=mock_job) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.post(
                "/api/v1/pdf-exports/jobs/1/cancel",
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert data['detail'] == "Job cannot be cancelled"
    
    @pytest.mark.asyncio
    async def test_download_job_file_success(self, client, auth_headers, temp_dir):
        """Test successful job file download."""
        import os
        
        # Create test file
        test_file = os.path.join(temp_dir, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("Test PDF content")
        
        mock_job = {
            "id": 1,
            "user_id": 1,
            "job_name": "Test Job",
            "status": "completed",
            "file_path": test_file
        }
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', return_value=mock_job) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/pdf-exports/jobs/1/download",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.headers['content-type'] == 'application/pdf'
    
    @pytest.mark.asyncio
    async def test_download_job_file_not_completed(self, client, auth_headers):
        """Test job file download when job not completed."""
        mock_job = {
            "id": 1,
            "user_id": 1,
            "status": "processing",
            "file_path": None
        }
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', return_value=mock_job) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/pdf-exports/jobs/1/download",
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert data['detail'] == "Job not completed"
    
    @pytest.mark.asyncio
    async def test_delete_job_success(self, client, auth_headers):
        """Test successful job deletion."""
        mock_job = {
            "id": 1,
            "user_id": 1,
            "status": "completed",
            "file_path": "/tmp/test.pdf"
        }
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', side_effect=[mock_job, None]) as mock_execute_query, \
             patch('app.api.v1.endpoints.pdf_exports.pdf_generator.cancel_job') as mock_cancel, \
             patch('os.path.exists', return_value=False) as mock_exists:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.delete(
                "/api/v1/pdf-exports/jobs/1",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['message'] == "Job deleted successfully"
    
    @pytest.mark.asyncio
    async def test_get_analytics_success(self, client, auth_headers):
        """Test successful analytics retrieval."""
        mock_stats = {
            'total_jobs': 10,
            'successful_jobs': 8,
            'failed_jobs': 2,
            'avg_generation_time': 5000.0,
            'total_file_size': 1024000,
            'total_pages': 30
        }
        
        mock_format_stats = [
            {'output_format': 'pdf', 'count': 8},
            {'output_format': 'html', 'count': 2}
        ]
        
        mock_template_stats = [
            {'name': 'Template 1', 'count': 5},
            {'name': 'Template 2', 'count': 3}
        ]
        
        mock_daily_stats = [
            {'date': datetime.now().date(), 'count': 5}
        ]
        
        with patch('app.api.v1.endpoints.pdf_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.pdf_exports.execute_query', side_effect=[
                 mock_stats, mock_format_stats, mock_template_stats, mock_daily_stats
             ]) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/pdf-exports/analytics?days=30",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['period_days'] == 30
            assert data['total_jobs'] == 10
            assert data['successful_jobs'] == 8
            assert data['failed_jobs'] == 2
            assert data['success_rate'] == 80.0
            assert data['usage_by_format'] == {'pdf': 8, 'html': 2}
    
    @pytest.mark.asyncio
    async def test_get_supported_formats(self, client):
        """Test supported formats retrieval."""
        response = await client.get("/api/v1/pdf-exports/formats")
        
        assert response.status_code == 200
        data = response.json()
        assert 'formats' in data
        assert len(data['formats']) == 4
        
        format_values = [f['format'] for f in data['formats']]
        assert 'pdf' in format_values
        assert 'html' in format_values
        assert 'png' in format_values
        assert 'jpg' in format_values
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self, client):
        """Test service capabilities retrieval."""
        response = await client.get("/api/v1/pdf-exports/capabilities")
        
        assert response.status_code == 200
        data = response.json()
        assert 'supported_formats' in data
        assert 'max_file_size_mb' in data
        assert 'max_pages' in data
        assert 'max_concurrent_jobs' in data
        assert 'supported_page_sizes' in data
        assert 'supported_orientations' in data
        assert 'template_types' in data


class TestTemplateEndpoints:
    """Test template API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_template_success(self, client, auth_headers, template_create_request):
        """Test successful template creation."""
        mock_template = {
            "id": 1,
            "name": "Test Template",
            "template_type": "report",
            "description": "Test template",
            "template_content": template_create_request['template_content'],
            "css_content": template_create_request['css_content'],
            "variables": template_create_request['variables'],
            "layout_config": template_create_request['layout_config'],
            "created_by": 1,
            "is_active": True,
            "is_default": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        with patch('app.api.v1.endpoints.templates.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.templates.check_rate_limit', return_value=True) as mock_rate_limit, \
             patch('app.api.v1.endpoints.templates.template_service.create_template', return_value=mock_template) as mock_create:
            
            mock_user.return_value = Mock(id=1, email="test@example.com", permissions={"template:create": True})
            
            response = await client.post(
                "/api/v1/templates/",
                json=template_create_request,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['id'] == 1
            assert data['name'] == "Test Template"
            assert data['template_type'] == "report"
            
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_template_rate_limit_exceeded(self, client, auth_headers, template_create_request):
        """Test template creation with rate limit exceeded."""
        with patch('app.api.v1.endpoints.templates.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.templates.check_rate_limit', return_value=False) as mock_rate_limit:
            
            mock_user.return_value = Mock(id=1, email="test@example.com", permissions={"template:create": True})
            
            response = await client.post(
                "/api/v1/templates/",
                json=template_create_request,
                headers=auth_headers
            )
            
            assert response.status_code == 429
            data = response.json()
            assert "Rate limit exceeded" in data['detail']
    
    @pytest.mark.asyncio
    async def test_list_templates_success(self, client, auth_headers):
        """Test successful template listing."""
        mock_templates = [
            {
                "id": 1,
                "name": "Template 1",
                "template_type": "report",
                "description": "Test template 1",
                "template_content": "<html></html>",
                "css_content": "",
                "variables": {},
                "layout_config": {},
                "created_by": 1,
                "is_active": True,
                "is_default": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        
        mock_result = {
            "templates": mock_templates,
            "total": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1
        }
        
        with patch('app.api.v1.endpoints.templates.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.templates.template_service.list_templates', return_value=mock_result) as mock_list:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/templates/",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 1
            assert len(data['templates']) == 1
            assert data['templates'][0]['id'] == 1
    
    @pytest.mark.asyncio
    async def test_get_template_success(self, client, auth_headers):
        """Test successful template retrieval."""
        mock_template = {
            "id": 1,
            "name": "Test Template",
            "template_type": "report",
            "description": "Test template",
            "template_content": "<html></html>",
            "css_content": "",
            "variables": {},
            "layout_config": {},
            "created_by": 1,
            "is_active": True,
            "is_default": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        with patch('app.api.v1.endpoints.templates.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.templates.template_service.get_template', return_value=mock_template) as mock_get:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/templates/1",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['id'] == 1
            assert data['name'] == "Test Template"
    
    @pytest.mark.asyncio
    async def test_get_template_not_found(self, client, auth_headers):
        """Test template retrieval when template not found."""
        with patch('app.api.v1.endpoints.templates.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.templates.template_service.get_template', return_value=None) as mock_get:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await client.get(
                "/api/v1/templates/999",
                headers=auth_headers
            )
            
            assert response.status_code == 404
            data = response.json()
            assert data['detail'] == "Template not found"
    
    @pytest.mark.asyncio
    async def test_get_template_types(self, client):
        """Test template types retrieval."""
        mock_types = [
            {
                'type': 'report',
                'name': 'Report Template',
                'description': 'Standard report template'
            },
            {
                'type': 'dashboard',
                'name': 'Dashboard Template',
                'description': 'Dashboard template'
            }
        ]
        
        with patch('app.api.v1.endpoints.templates.template_service.get_template_types', return_value=mock_types) as mock_get_types:
            response = await client.get("/api/v1/templates/types")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]['type'] == 'report'
            assert data[1]['type'] == 'dashboard'
    
    @pytest.mark.asyncio
    async def test_get_default_templates(self, client):
        """Test default templates retrieval."""
        mock_templates = [
            {
                "id": 1,
                "name": "Default Template",
                "template_type": "report",
                "description": "Default template",
                "template_content": "<html></html>",
                "css_content": "",
                "variables": {},
                "layout_config": {},
                "created_by": 1,
                "is_active": True,
                "is_default": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        
        with patch('app.api.v1.endpoints.templates.template_service.get_default_templates', return_value=mock_templates) as mock_get_defaults:
            response = await client.get("/api/v1/templates/defaults")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]['id'] == 1
            assert data[0]['is_default'] is True