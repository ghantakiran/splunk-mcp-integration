"""
Tests for API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from app.models.excel_models import JobStatus, ExcelFormat, Theme


class TestExcelExportEndpoints:
    """Test Excel export API endpoints."""
    
    @pytest.mark.asyncio
    async def test_generate_excel_success(self, async_client, auth_headers, sample_export_request):
        """Test successful Excel generation request."""
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.check_rate_limit', return_value=True) as mock_rate_limit, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', return_value=1) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.post(
                "/api/v1/excel-exports/generate",
                json=sample_export_request.dict(),
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['job_id'] == 1
            assert data['status'] == JobStatus.PENDING.value
            assert data['message'] == "Excel generation started"
            
            mock_rate_limit.assert_called_once()
            mock_execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_excel_rate_limit_exceeded(self, async_client, auth_headers, sample_export_request):
        """Test Excel generation with rate limit exceeded."""
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.check_rate_limit', return_value=False) as mock_rate_limit:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.post(
                "/api/v1/excel-exports/generate",
                json=sample_export_request.dict(),
                headers=auth_headers
            )
            
            assert response.status_code == 429
            data = response.json()
            assert "Rate limit exceeded" in data['detail']
    
    @pytest.mark.asyncio
    async def test_generate_excel_invalid_request(self, async_client, auth_headers):
        """Test Excel generation with invalid request data."""
        invalid_request = {
            "job_name": "",  # Empty job name
            "workbook_config": {},  # Invalid workbook config
            "data_source": {},
            "output_format": "invalid_format"  # Invalid format
        }
        
        response = await async_client.post(
            "/api/v1/excel-exports/generate",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_bulk_generate_excel_success(self, async_client, auth_headers):
        """Test successful bulk Excel generation."""
        bulk_request = {
            "output_format": "xlsx",
            "theme": "office",
            "jobs": [
                {
                    "job_name": "Bulk Job 1",
                    "workbook_config": {
                        "name": "Report 1",
                        "worksheets": [
                            {
                                "name": "Sheet1",
                                "data": [],
                                "headers": ["Col1", "Col2"]
                            }
                        ]
                    },
                    "data_source": {}
                },
                {
                    "job_name": "Bulk Job 2",
                    "workbook_config": {
                        "name": "Report 2",
                        "worksheets": [
                            {
                                "name": "Sheet1",
                                "data": [],
                                "headers": ["Col1", "Col2"]
                            }
                        ]
                    },
                    "data_source": {}
                }
            ]
        }
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.check_rate_limit', return_value=True) as mock_rate_limit, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', side_effect=[1, 2]) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.post(
                "/api/v1/excel-exports/bulk-generate",
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
    async def test_list_jobs_success(self, async_client, auth_headers):
        """Test successful job listing."""
        mock_jobs = [
            {
                "id": 1,
                "job_name": "Test Job",
                "status": "completed",
                "output_format": "xlsx",
                "theme": "office",
                "file_path": "/tmp/test.xlsx",
                "file_size": 1024,
                "row_count": 100,
                "worksheet_count": 1,
                "chart_count": 0,
                "error_message": None,
                "generation_time_ms": 5000,
                "created_at": datetime.now(),
                "started_at": datetime.now(),
                "completed_at": datetime.now()
            }
        ]
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', side_effect=[1, mock_jobs]) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.get(
                "/api/v1/excel-exports/jobs",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 1
            assert len(data['jobs']) == 1
            assert data['jobs'][0]['id'] == 1
            assert data['jobs'][0]['job_name'] == "Test Job"
    
    @pytest.mark.asyncio
    async def test_list_jobs_with_filters(self, async_client, auth_headers):
        """Test job listing with filters."""
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', side_effect=[0, []]) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.get(
                "/api/v1/excel-exports/jobs?status=completed&output_format=xlsx&page=1&page_size=10",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 0
            assert len(data['jobs']) == 0
    
    @pytest.mark.asyncio
    async def test_get_job_success(self, async_client, auth_headers):
        """Test successful job retrieval."""
        mock_job = {
            "id": 1,
            "job_name": "Test Job",
            "status": "completed",
            "output_format": "xlsx",
            "theme": "office",
            "file_path": "/tmp/test.xlsx",
            "file_size": 1024,
            "row_count": 100,
            "worksheet_count": 1,
            "chart_count": 0,
            "error_message": None,
            "generation_time_ms": 5000,
            "created_at": datetime.now(),
            "started_at": datetime.now(),
            "completed_at": datetime.now()
        }
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', return_value=mock_job) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.get(
                "/api/v1/excel-exports/jobs/1",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['job_id'] == 1
            assert data['status'] == "completed"
    
    @pytest.mark.asyncio
    async def test_get_job_not_found(self, async_client, auth_headers):
        """Test job retrieval when job not found."""
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', return_value=None) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.get(
                "/api/v1/excel-exports/jobs/999",
                headers=auth_headers
            )
            
            assert response.status_code == 404
            data = response.json()
            assert data['detail'] == "Job not found"
    
    @pytest.mark.asyncio
    async def test_get_job_status_success(self, async_client, auth_headers):
        """Test successful job status retrieval."""
        mock_job = {"id": 1, "user_id": 1}
        mock_status = {
            "job_id": 1,
            "status": "processing",
            "runtime_seconds": 10.5
        }
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', return_value=mock_job) as mock_execute_query, \
             patch('app.api.v1.endpoints.excel_exports.excel_generator.get_job_status', return_value=mock_status) as mock_generator:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.get(
                "/api/v1/excel-exports/jobs/1/status",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['job_id'] == 1
            assert data['status'] == "processing"
            assert data['runtime_seconds'] == 10.5
    
    @pytest.mark.asyncio
    async def test_cancel_job_success(self, async_client, auth_headers):
        """Test successful job cancellation."""
        mock_job = {"id": 1, "user_id": 1, "status": "processing"}
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', return_value=mock_job) as mock_execute_query, \
             patch('app.api.v1.endpoints.excel_exports.excel_generator.cancel_job', return_value=True) as mock_generator:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.post(
                "/api/v1/excel-exports/jobs/1/cancel",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['message'] == "Job cancelled successfully"
            
            mock_generator.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_cancel_job_cannot_cancel(self, async_client, auth_headers):
        """Test job cancellation when job cannot be cancelled."""
        mock_job = {"id": 1, "user_id": 1, "status": "completed"}
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', return_value=mock_job) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.post(
                "/api/v1/excel-exports/jobs/1/cancel",
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert data['detail'] == "Job cannot be cancelled"
    
    @pytest.mark.asyncio
    async def test_download_job_file_success(self, async_client, auth_headers, temp_dir):
        """Test successful job file download."""
        import os
        
        # Create test file
        test_file = os.path.join(temp_dir, "test.xlsx")
        with open(test_file, 'w') as f:
            f.write("Test Excel content")
        
        mock_job = {
            "id": 1,
            "user_id": 1,
            "job_name": "Test Job",
            "status": "completed",
            "file_path": test_file
        }
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', return_value=mock_job) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.get(
                "/api/v1/excel-exports/jobs/1/download",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.headers['content-type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    @pytest.mark.asyncio
    async def test_download_job_file_not_completed(self, async_client, auth_headers):
        """Test job file download when job not completed."""
        mock_job = {
            "id": 1,
            "user_id": 1,
            "status": "processing",
            "file_path": None
        }
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', return_value=mock_job) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.get(
                "/api/v1/excel-exports/jobs/1/download",
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert data['detail'] == "Job not completed"
    
    @pytest.mark.asyncio
    async def test_delete_job_success(self, async_client, auth_headers):
        """Test successful job deletion."""
        mock_job = {
            "id": 1,
            "user_id": 1,
            "status": "completed",
            "file_path": "/tmp/test.xlsx"
        }
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', side_effect=[mock_job, None]) as mock_execute_query, \
             patch('app.api.v1.endpoints.excel_exports.excel_generator.cancel_job') as mock_cancel, \
             patch('os.path.exists', return_value=False) as mock_exists:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.delete(
                "/api/v1/excel-exports/jobs/1",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['message'] == "Job deleted successfully"
    
    @pytest.mark.asyncio
    async def test_get_analytics_success(self, async_client, auth_headers):
        """Test successful analytics retrieval."""
        mock_stats = {
            'total_jobs': 10,
            'successful_jobs': 8,
            'failed_jobs': 2,
            'avg_generation_time': 5000.0,
            'avg_file_size': 1024.0,
            'avg_row_count': 100.0
        }
        
        mock_format_stats = [
            {'output_format': 'xlsx', 'count': 8},
            {'output_format': 'csv', 'count': 2}
        ]
        
        mock_theme_stats = [
            {'theme': 'office', 'count': 6},
            {'theme': 'modern', 'count': 4}
        ]
        
        mock_daily_stats = [
            {'date': datetime.now().date(), 'count': 5}
        ]
        
        with patch('app.api.v1.endpoints.excel_exports.get_current_user_full') as mock_user, \
             patch('app.api.v1.endpoints.excel_exports.execute_query', side_effect=[
                 mock_stats, mock_format_stats, mock_theme_stats, mock_daily_stats
             ]) as mock_execute_query:
            
            mock_user.return_value = Mock(id=1, email="test@example.com")
            
            response = await async_client.get(
                "/api/v1/excel-exports/analytics?days=30",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['period_days'] == 30
            assert data['total_jobs'] == 10
            assert data['successful_jobs'] == 8
            assert data['failed_jobs'] == 2
            assert data['success_rate'] == 80.0
            assert data['usage_by_format'] == {'xlsx': 8, 'csv': 2}
    
    @pytest.mark.asyncio
    async def test_get_supported_formats(self, async_client):
        """Test supported formats retrieval."""
        response = await async_client.get("/api/v1/excel-exports/formats")
        
        assert response.status_code == 200
        data = response.json()
        assert 'formats' in data
        assert len(data['formats']) == 4
        
        format_values = [f['format'] for f in data['formats']]
        assert 'xlsx' in format_values
        assert 'xls' in format_values
        assert 'csv' in format_values
        assert 'ods' in format_values
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self, async_client):
        """Test service capabilities retrieval."""
        response = await async_client.get("/api/v1/excel-exports/capabilities")
        
        assert response.status_code == 200
        data = response.json()
        assert 'supported_formats' in data
        assert 'supported_themes' in data
        assert 'supported_chart_types' in data
        assert 'max_file_size_mb' in data
        assert 'max_rows' in data
        assert 'max_columns' in data
        assert 'max_concurrent_jobs' in data
        assert 'features' in data