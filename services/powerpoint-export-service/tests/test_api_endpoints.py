#!/usr/bin/env python3
"""
Comprehensive API endpoint tests for PowerPoint Export Service.

This module tests all API endpoints including presentation generation, template
management, job handling, and export functionality.
"""

import pytest
import json
from typing import Dict, Any
from unittest.mock import AsyncMock, patch, Mock
from fastapi import status
import os

from .conftest import (
    assert_job_structure, 
    assert_template_structure,
    assert_presentation_structure,
    generate_mock_pptx_data,
    create_mock_presentation_html
)


class TestPresentationGenerationEndpoints:
    """Test presentation generation API endpoints."""
    
    def test_generate_presentation_success(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_data,
        sample_presentation_configurations,
        mock_powerpoint_generator
    ):
        """Test successful presentation generation."""
        request_data = {
            **sample_presentation_data,
            "configuration": sample_presentation_configurations[0]
        }
        
        response = test_client.post(
            "/api/v1/powerpoint-exports/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        assert assert_job_structure(data)
        assert data["job_id"] is not None
        assert data["status"] == "pending"
        assert "estimated_completion_time" in data
        mock_powerpoint_generator.generate_presentation.assert_called_once()
    
    def test_generate_presentation_with_charts(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_data,
        sample_presentation_configurations,
        sample_chart_data,
        mock_powerpoint_generator
    ):
        """Test presentation generation with embedded charts."""
        # Add charts to presentation data
        enhanced_data = sample_presentation_data.copy()
        enhanced_data["slides"][1]["chart"] = sample_chart_data[0]
        enhanced_data["slides"][2]["charts"] = sample_chart_data[1:3]
        
        request_data = {
            **enhanced_data,
            "configuration": sample_presentation_configurations[0]
        }
        
        response = test_client.post(
            "/api/v1/powerpoint-exports/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        assert data["status"] == "pending"
        assert "charts_count" in data.get("metadata", {})
    
    def test_generate_presentation_different_formats(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_data,
        sample_presentation_configurations,
        mock_powerpoint_generator
    ):
        """Test presentation generation in different output formats."""
        formats = ["pptx", "pdf", "png"]
        
        for format_type in formats:
            config = sample_presentation_configurations[0].copy()
            config["output_format"] = format_type
            
            request_data = {
                **sample_presentation_data,
                "configuration": config
            }
            
            response = test_client.post(
                "/api/v1/powerpoint-exports/generate",
                headers=auth_headers,
                json=request_data
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            data = response.json()
            assert data["metadata"]["output_format"] == format_type
    
    def test_generate_presentation_different_themes(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_data,
        sample_presentation_configurations,
        mock_powerpoint_generator
    ):
        """Test presentation generation with different themes."""
        themes = ["office", "modern", "colorful", "dark", "minimal"]
        
        for theme in themes:
            config = sample_presentation_configurations[0].copy()
            config["theme"] = theme
            
            request_data = {
                **sample_presentation_data,
                "configuration": config
            }
            
            response = test_client.post(
                "/api/v1/powerpoint-exports/generate",
                headers=auth_headers,
                json=request_data
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            data = response.json()
            assert data["metadata"]["theme"] == theme
    
    def test_generate_presentation_invalid_data(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_configurations
    ):
        """Test presentation generation with invalid data."""
        invalid_data = {
            "title": "",  # Empty title
            "slides": [],  # No slides
            "configuration": sample_presentation_configurations[0]
        }
        
        response = test_client.post(
            "/api/v1/powerpoint-exports/generate",
            headers=auth_headers,
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_generate_presentation_missing_configuration(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_data
    ):
        """Test presentation generation with missing configuration."""
        request_data = {
            **sample_presentation_data
            # Missing configuration
        }
        
        response = test_client.post(
            "/api/v1/powerpoint-exports/generate",
            headers=auth_headers,
            json=request_data
        )
        
        # Should use default configuration or return validation error
        assert response.status_code in [
            status.HTTP_202_ACCEPTED, 
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_generate_presentation_unauthorized(
        self, 
        test_client,
        sample_presentation_data,
        sample_presentation_configurations
    ):
        """Test presentation generation without authentication."""
        request_data = {
            **sample_presentation_data,
            "configuration": sample_presentation_configurations[0]
        }
        
        response = test_client.post(
            "/api/v1/powerpoint-exports/generate",
            json=request_data
            # No auth headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestBulkGenerationEndpoints:
    """Test bulk presentation generation endpoints."""
    
    def test_bulk_generate_presentations(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_data,
        sample_presentation_configurations,
        mock_powerpoint_generator
    ):
        """Test bulk presentation generation."""
        bulk_data = {
            "presentations": [
                {
                    **sample_presentation_data,
                    "title": "Presentation 1",
                    "configuration": sample_presentation_configurations[0]
                },
                {
                    **sample_presentation_data,
                    "title": "Presentation 2", 
                    "configuration": sample_presentation_configurations[1]
                }
            ],
            "shared_settings": {
                "author": "Bulk Generator",
                "company": "Test Corp"
            }
        }
        
        response = test_client.post(
            "/api/v1/powerpoint-exports/bulk-generate",
            headers=auth_headers,
            json=bulk_data
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        assert "batch_id" in data
        assert "jobs" in data
        assert len(data["jobs"]) == 2
        
        for job in data["jobs"]:
            assert assert_job_structure(job)
            assert job["status"] == "pending"
    
    def test_bulk_generate_with_template(
        self, 
        test_client, 
        auth_headers,
        sample_template_data,
        mock_powerpoint_generator
    ):
        """Test bulk generation using template."""
        bulk_data = {
            "template_id": "template-123",
            "presentations": [
                {
                    "title": "Report 1",
                    "variables": {
                        "section_title": "Sales Performance",
                        "content": "Strong quarter results"
                    }
                },
                {
                    "title": "Report 2",
                    "variables": {
                        "section_title": "Marketing Metrics",
                        "content": "Campaign effectiveness analysis"
                    }
                }
            ]
        }
        
        response = test_client.post(
            "/api/v1/powerpoint-exports/bulk-generate",
            headers=auth_headers,
            json=bulk_data
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        assert "batch_id" in data
        assert len(data["jobs"]) == 2


class TestJobManagementEndpoints:
    """Test job management API endpoints."""
    
    def test_get_job_status(
        self, 
        test_client, 
        auth_headers,
        sample_job_data
    ):
        """Test getting job status."""
        job_id = sample_job_data[0]["job_id"]
        
        with patch('app.api.v1.endpoints.powerpoint_exports.get_job_by_id') as mock_get_job:
            mock_get_job.return_value = sample_job_data[0]
            
            response = test_client.get(
                f"/api/v1/powerpoint-exports/jobs/{job_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert "metadata" in data
    
    def test_get_job_not_found(
        self, 
        test_client, 
        auth_headers
    ):
        """Test getting non-existent job."""
        non_existent_id = "non-existent-job"
        
        with patch('app.api.v1.endpoints.powerpoint_exports.get_job_by_id') as mock_get_job:
            mock_get_job.return_value = None
            
            response = test_client.get(
                f"/api/v1/powerpoint-exports/jobs/{non_existent_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_list_user_jobs(
        self, 
        test_client, 
        auth_headers,
        sample_job_data
    ):
        """Test listing user jobs."""
        with patch('app.api.v1.endpoints.powerpoint_exports.get_user_jobs') as mock_get_jobs:
            mock_get_jobs.return_value = {
                "jobs": sample_job_data,
                "total": len(sample_job_data),
                "page": 1,
                "per_page": 10
            }
            
            response = test_client.get(
                "/api/v1/powerpoint-exports/jobs",
                headers=auth_headers,
                params={"page": 1, "per_page": 10}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["jobs"]) == len(sample_job_data)
        assert data["total"] == len(sample_job_data)
        
        for job in data["jobs"]:
            assert assert_job_structure(job)
    
    def test_cancel_job(
        self, 
        test_client, 
        auth_headers,
        sample_job_data
    ):
        """Test canceling a job."""
        job_id = sample_job_data[1]["job_id"]  # Processing job
        
        with patch('app.api.v1.endpoints.powerpoint_exports.cancel_job') as mock_cancel:
            mock_cancel.return_value = {
                "job_id": job_id,
                "status": "cancelled",
                "cancelled_at": "2024-01-16T10:30:00Z"
            }
            
            response = test_client.post(
                f"/api/v1/powerpoint-exports/jobs/{job_id}/cancel",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["job_id"] == job_id
        assert data["status"] == "cancelled"
    
    def test_delete_job(
        self, 
        test_client, 
        auth_headers,
        sample_job_data
    ):
        """Test deleting a completed job."""
        job_id = sample_job_data[0]["job_id"]  # Completed job
        
        with patch('app.api.v1.endpoints.powerpoint_exports.delete_job') as mock_delete:
            mock_delete.return_value = {"deleted": True}
            
            response = test_client.delete(
                f"/api/v1/powerpoint-exports/jobs/{job_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["deleted"] is True
    
    def test_download_job_file(
        self, 
        test_client, 
        auth_headers,
        sample_job_data,
        mock_file_operations
    ):
        """Test downloading completed job file."""
        job_id = sample_job_data[0]["job_id"]
        file_name = f"{job_id}.pptx"
        
        # Create mock file
        mock_content = generate_mock_pptx_data()
        mock_file_operations["create_pptx_file"](file_name, mock_content)
        
        with patch('app.api.v1.endpoints.powerpoint_exports.get_job_file_path') as mock_get_path:
            mock_get_path.return_value = os.path.join(mock_file_operations["temp_dir"], file_name)
            
            response = test_client.get(
                f"/api/v1/powerpoint-exports/jobs/{job_id}/download",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class TestTemplateEndpoints:
    """Test template management API endpoints."""
    
    def test_create_template(
        self, 
        test_client, 
        auth_headers,
        sample_template_data
    ):
        """Test creating a new template."""
        template_data = sample_template_data[0]
        
        response = test_client.post(
            "/api/v1/templates/",
            headers=auth_headers,
            json=template_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert assert_template_structure(data)
        assert data["name"] == template_data["name"]
        assert data["theme"] == template_data["theme"]
    
    def test_get_template(
        self, 
        test_client, 
        auth_headers,
        sample_template_data
    ):
        """Test getting template by ID."""
        template_id = "template-123"
        
        with patch('app.api.v1.endpoints.templates.get_template_by_id') as mock_get:
            mock_get.return_value = {
                "template_id": template_id,
                **sample_template_data[0]
            }
            
            response = test_client.get(
                f"/api/v1/templates/{template_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["template_id"] == template_id
        assert data["name"] == sample_template_data[0]["name"]
    
    def test_update_template(
        self, 
        test_client, 
        auth_headers,
        sample_template_data
    ):
        """Test updating template."""
        template_id = "template-123"
        update_data = {
            "name": "Updated Template Name",
            "description": "Updated description"
        }
        
        with patch('app.api.v1.endpoints.templates.update_template') as mock_update:
            mock_update.return_value = {
                "template_id": template_id,
                **sample_template_data[0],
                **update_data
            }
            
            response = test_client.put(
                f"/api/v1/templates/{template_id}",
                headers=auth_headers,
                json=update_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_delete_template(
        self, 
        test_client, 
        auth_headers
    ):
        """Test deleting template."""
        template_id = "template-123"
        
        with patch('app.api.v1.endpoints.templates.delete_template') as mock_delete:
            mock_delete.return_value = {"deleted": True}
            
            response = test_client.delete(
                f"/api/v1/templates/{template_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["deleted"] is True
    
    def test_list_templates(
        self, 
        test_client, 
        auth_headers,
        sample_template_data
    ):
        """Test listing all templates."""
        with patch('app.api.v1.endpoints.templates.get_templates') as mock_get_all:
            templates_with_ids = [
                {"template_id": f"template-{i}", **template}
                for i, template in enumerate(sample_template_data)
            ]
            mock_get_all.return_value = {
                "templates": templates_with_ids,
                "total": len(templates_with_ids)
            }
            
            response = test_client.get(
                "/api/v1/templates/",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["templates"]) == len(sample_template_data)
        for template in data["templates"]:
            assert assert_template_structure(template)
    
    def test_duplicate_template(
        self, 
        test_client, 
        auth_headers,
        sample_template_data
    ):
        """Test duplicating a template."""
        source_template_id = "template-123"
        
        with patch('app.api.v1.endpoints.templates.duplicate_template') as mock_duplicate:
            mock_duplicate.return_value = {
                "template_id": "template-456",
                **sample_template_data[0],
                "name": f"Copy of {sample_template_data[0]['name']}"
            }
            
            response = test_client.post(
                f"/api/v1/templates/{source_template_id}/duplicate",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["template_id"] != source_template_id
        assert "Copy of" in data["name"]


class TestCapabilityEndpoints:
    """Test service capability endpoints."""
    
    def test_get_capabilities(self, test_client):
        """Test getting service capabilities."""
        response = test_client.get("/api/v1/powerpoint-exports/capabilities")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "supported_formats" in data
        assert "supported_themes" in data
        assert "supported_chart_types" in data
        assert "max_file_size_mb" in data
        assert "max_slides_per_presentation" in data
    
    def test_get_supported_formats(self, test_client):
        """Test getting supported export formats."""
        response = test_client.get("/api/v1/powerpoint-exports/formats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "formats" in data
        assert len(data["formats"]) > 0
        
        # Check required formats
        format_values = [fmt["format"] for fmt in data["formats"]]
        required_formats = ["pptx", "pdf", "png"]
        for fmt in required_formats:
            assert fmt in format_values
    
    def test_get_supported_themes(self, test_client):
        """Test getting supported themes."""
        response = test_client.get("/api/v1/powerpoint-exports/themes")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "themes" in data
        assert len(data["themes"]) > 0
        
        # Check required themes
        theme_values = [theme["name"] for theme in data["themes"]]
        required_themes = ["office", "modern", "colorful", "dark", "minimal"]
        for theme in required_themes:
            assert theme in theme_values
    
    def test_get_chart_types(self, test_client):
        """Test getting supported chart types."""
        response = test_client.get("/api/v1/powerpoint-exports/chart-types")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "chart_types" in data
        assert len(data["chart_types"]) > 0
        
        # Check required chart types
        chart_type_values = [ct["type"] for ct in data["chart_types"]]
        required_types = ["bar", "column", "line", "pie", "area", "scatter"]
        for chart_type in required_types:
            assert chart_type in chart_type_values


class TestAnalyticsEndpoints:
    """Test analytics and metrics endpoints."""
    
    def test_get_user_analytics(
        self, 
        test_client, 
        auth_headers
    ):
        """Test getting user analytics."""
        with patch('app.api.v1.endpoints.powerpoint_exports.get_user_analytics') as mock_analytics:
            mock_analytics.return_value = {
                "user_id": "test-user-123",
                "total_presentations": 45,
                "total_slides": 320,
                "favorite_theme": "office",
                "most_used_format": "pptx",
                "average_processing_time_ms": 35000,
                "success_rate": 0.96,
                "last_30_days": {
                    "presentations_created": 12,
                    "total_file_size_mb": 156.7,
                    "themes_used": ["office", "modern", "colorful"]
                }
            }
            
            response = test_client.get(
                "/api/v1/powerpoint-exports/analytics/user",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "total_presentations" in data
        assert "success_rate" in data
        assert "last_30_days" in data
    
    def test_get_performance_metrics(
        self, 
        test_client, 
        auth_headers
    ):
        """Test getting performance metrics."""
        with patch('app.api.v1.endpoints.powerpoint_exports.get_performance_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "average_generation_time_ms": 42000,
                "success_rate": 0.97,
                "concurrent_jobs": 8,
                "queue_length": 15,
                "most_popular_theme": "modern",
                "most_popular_format": "pptx",
                "resource_usage": {
                    "cpu_percent": 65.2,
                    "memory_percent": 42.1,
                    "disk_usage_gb": 12.8
                }
            }
            
            response = test_client.get(
                "/api/v1/powerpoint-exports/analytics/performance",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "average_generation_time_ms" in data
        assert "success_rate" in data
        assert "resource_usage" in data


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    def test_invalid_presentation_data(
        self, 
        test_client, 
        auth_headers
    ):
        """Test handling of invalid presentation data."""
        invalid_data = {
            "title": None,  # Invalid title
            "slides": "not_a_list",  # Invalid slides format
            "author": 123  # Invalid author type
        }
        
        response = test_client.post(
            "/api/v1/powerpoint-exports/generate",
            headers=auth_headers,
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_too_many_slides(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_configurations
    ):
        """Test handling of presentations with too many slides."""
        large_presentation = {
            "title": "Large Presentation",
            "slides": [{"title": f"Slide {i}", "content": []} for i in range(150)],  # Too many slides
            "configuration": sample_presentation_configurations[0]
        }
        
        response = test_client.post(
            "/api/v1/powerpoint-exports/generate",
            headers=auth_headers,
            json=large_presentation
        )
        
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        ]
    
    def test_rate_limiting(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_data,
        sample_presentation_configurations
    ):
        """Test rate limiting enforcement."""
        request_data = {
            **sample_presentation_data,
            "configuration": sample_presentation_configurations[0]
        }
        
        with patch('app.utils.rate_limiter.check_rate_limit') as mock_limiter:
            mock_limiter.return_value = False  # Rate limit exceeded
            
            response = test_client.post(
                "/api/v1/powerpoint-exports/generate",
                headers=auth_headers,
                json=request_data
            )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    def test_service_unavailable(
        self, 
        test_client, 
        auth_headers,
        sample_presentation_data,
        sample_presentation_configurations
    ):
        """Test handling of service unavailability."""
        request_data = {
            **sample_presentation_data,
            "configuration": sample_presentation_configurations[0]
        }
        
        with patch('app.services.powerpoint_generator.PowerPointGenerator.generate_presentation') as mock_gen:
            mock_gen.side_effect = Exception("Service temporarily unavailable")
            
            response = test_client.post(
                "/api/v1/powerpoint-exports/generate",
                headers=auth_headers,
                json=request_data
            )
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


class TestConcurrency:
    """Test concurrent request handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_presentation_generation(
        self, 
        async_client, 
        auth_headers,
        sample_presentation_data,
        sample_presentation_configurations,
        mock_powerpoint_generator
    ):
        """Test handling of concurrent presentation generation requests."""
        import asyncio
        
        request_data = {
            **sample_presentation_data,
            "configuration": sample_presentation_configurations[0]
        }
        
        # Send multiple concurrent requests
        tasks = []
        for i in range(5):
            task = async_client.post(
                "/api/v1/powerpoint-exports/generate",
                headers=auth_headers,
                json={**request_data, "title": f"Presentation {i}"}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed or fail gracefully
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [
                    status.HTTP_202_ACCEPTED, 
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    status.HTTP_503_SERVICE_UNAVAILABLE
                ]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])