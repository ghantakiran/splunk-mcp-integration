#!/usr/bin/env python3
"""
Comprehensive service tests for PowerPoint Export Service.

This module tests core services including PowerPoint generation, template
management, job processing, and chart integration.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List
import json
import tempfile
import os
from datetime import datetime, timedelta


class TestPowerPointGeneratorService:
    """Test PowerPoint generation service."""
    
    @pytest.mark.asyncio
    async def test_generate_presentation_success(
        self,
        sample_presentation_data,
        sample_presentation_configurations,
        mock_python_pptx,
        mock_matplotlib,
        mock_database,
        mock_redis
    ):
        """Test successful presentation generation."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        request_data = {
            **sample_presentation_data,
            "configuration": sample_presentation_configurations[0]
        }
        
        result = await generator.generate_presentation(
            presentation_data=request_data,
            user_id="test-user-123"
        )
        
        assert result is not None
        assert "job_id" in result
        assert result["status"] == "completed"
        assert "file_path" in result
        assert "metadata" in result
        
        # Verify python-pptx was used
        mock_python_pptx["presentation_class"].assert_called()
        mock_python_pptx["presentation"].save.assert_called()
    
    @pytest.mark.asyncio
    async def test_generate_presentation_with_charts(
        self,
        sample_presentation_data,
        sample_presentation_configurations,
        sample_chart_data,
        mock_python_pptx,
        mock_matplotlib,
        mock_database,
        mock_redis
    ):
        """Test presentation generation with embedded charts."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        
        # Add charts to presentation data
        enhanced_data = sample_presentation_data.copy()
        enhanced_data["slides"][1]["chart"] = sample_chart_data[0]
        enhanced_data["slides"][2]["charts"] = sample_chart_data[1:3]
        
        request_data = {
            **enhanced_data,
            "configuration": sample_presentation_configurations[0]
        }
        
        result = await generator.generate_presentation(
            presentation_data=request_data,
            user_id="test-user-123"
        )
        
        assert result["status"] == "completed"
        assert result["metadata"]["charts_count"] >= 3
        
        # Verify matplotlib was used for chart generation
        assert mock_matplotlib["plt"].figure.called or mock_matplotlib["plt"].subplots.called
        mock_matplotlib["plt"].savefig.assert_called()
    
    @pytest.mark.asyncio
    async def test_generate_presentation_different_themes(
        self,
        sample_presentation_data,
        sample_presentation_configurations,
        mock_python_pptx,
        mock_database,
        mock_redis
    ):
        """Test presentation generation with different themes."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        themes = ["office", "modern", "colorful", "dark", "minimal"]
        
        for theme in themes:
            config = sample_presentation_configurations[0].copy()
            config["theme"] = theme
            
            request_data = {
                **sample_presentation_data,
                "configuration": config
            }
            
            result = await generator.generate_presentation(
                presentation_data=request_data,
                user_id="test-user-123"
            )
            
            assert result["status"] == "completed"
            assert result["metadata"]["theme"] == theme
    
    @pytest.mark.asyncio
    async def test_generate_presentation_different_formats(
        self,
        sample_presentation_data,
        sample_presentation_configurations,
        mock_python_pptx,
        mock_database,
        mock_redis
    ):
        """Test presentation generation in different output formats."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        formats = ["pptx", "pdf", "png"]
        
        for format_type in formats:
            config = sample_presentation_configurations[0].copy()
            config["output_format"] = format_type
            
            request_data = {
                **sample_presentation_data,
                "configuration": config
            }
            
            result = await generator.generate_presentation(
                presentation_data=request_data,
                user_id="test-user-123"
            )
            
            assert result["status"] == "completed"
            assert result["metadata"]["output_format"] == format_type
    
    def test_validate_presentation_data_valid(self):
        """Test presentation data validation with valid data."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        valid_data = {
            "title": "Test Presentation",
            "slides": [
                {
                    "title": "Slide 1",
                    "content": ["Content line 1"],
                    "layout": "title_and_content"
                }
            ]
        }
        
        result = generator.validate_presentation_data(valid_data)
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_presentation_data_invalid(self):
        """Test presentation data validation with invalid data."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        invalid_data = {
            "title": "",  # Empty title
            "slides": []   # No slides
        }
        
        result = generator.validate_presentation_data(invalid_data)
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
    
    def test_get_supported_themes(self):
        """Test getting supported themes."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        themes = generator.get_supported_themes()
        
        expected_themes = ["office", "modern", "colorful", "dark", "minimal"]
        for theme in expected_themes:
            assert theme in themes
    
    def test_get_supported_formats(self):
        """Test getting supported export formats."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        formats = generator.get_supported_formats()
        
        expected_formats = ["pptx", "pdf", "png", "jpg"]
        for format_type in expected_formats:
            assert format_type in formats
    
    @pytest.mark.asyncio
    async def test_create_from_template(
        self,
        sample_template_data,
        mock_python_pptx,
        mock_database,
        mock_redis
    ):
        """Test creating presentation from template."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        template_data = sample_template_data[0]
        
        variables = {
            "title": "Generated from Template",
            "subtitle": "Test Presentation",
            "author": "Template User",
            "section_title": "Section 1",
            "slide_title": "Slide from Template",
            "content": "This is template-generated content"
        }
        
        with patch.object(generator, '_get_template_by_id') as mock_get_template:
            mock_get_template.return_value = template_data
            
            result = await generator.create_from_template(
                template_id="template-123",
                variables=variables,
                user_id="test-user-123"
            )
        
        assert result is not None
        assert result["status"] == "completed"
        assert "template_id" in result
        assert result["template_id"] == "template-123"


class TestChartGenerationService:
    """Test chart generation service."""
    
    def test_create_bar_chart(self, mock_matplotlib):
        """Test bar chart generation."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        chart_data = {
            "type": "bar",
            "data": [
                {"category": "A", "value": 100},
                {"category": "B", "value": 150},
                {"category": "C", "value": 120}
            ],
            "title": "Sample Bar Chart",
            "x_label": "Categories",
            "y_label": "Values"
        }
        
        chart_image = generator._create_chart(chart_data)
        
        assert chart_image is not None
        # Verify matplotlib was called for bar chart
        mock_matplotlib["ax"].bar.assert_called()
        mock_matplotlib["ax"].set_title.assert_called_with("Sample Bar Chart")
        mock_matplotlib["ax"].set_xlabel.assert_called_with("Categories")
        mock_matplotlib["ax"].set_ylabel.assert_called_with("Values")
    
    def test_create_line_chart(self, mock_matplotlib):
        """Test line chart generation."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        chart_data = {
            "type": "line",
            "data": [
                {"x": "Jan", "y": 85},
                {"x": "Feb", "y": 90},
                {"x": "Mar", "y": 88}
            ],
            "title": "Monthly Trends",
            "x_label": "Month",
            "y_label": "Score"
        }
        
        chart_image = generator._create_chart(chart_data)
        
        assert chart_image is not None
        # Verify matplotlib was called for line chart
        mock_matplotlib["ax"].plot.assert_called()
        mock_matplotlib["ax"].set_title.assert_called_with("Monthly Trends")
    
    def test_create_pie_chart(self, mock_matplotlib):
        """Test pie chart generation."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        chart_data = {
            "type": "pie",
            "data": [
                {"label": "A", "value": 30},
                {"label": "B", "value": 45},
                {"label": "C", "value": 25}
            ],
            "title": "Distribution Chart",
            "show_percentages": True
        }
        
        chart_image = generator._create_chart(chart_data)
        
        assert chart_image is not None
        # Verify matplotlib was called for pie chart
        mock_matplotlib["ax"].pie.assert_called()
    
    def test_create_scatter_chart(self, mock_matplotlib):
        """Test scatter chart generation."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        chart_data = {
            "type": "scatter",
            "data": [
                {"x": 10, "y": 20},
                {"x": 15, "y": 25},
                {"x": 20, "y": 30}
            ],
            "title": "Correlation Analysis",
            "x_label": "Variable X",
            "y_label": "Variable Y"
        }
        
        chart_image = generator._create_chart(chart_data)
        
        assert chart_image is not None
        # Verify matplotlib was called for scatter chart
        mock_matplotlib["ax"].scatter.assert_called()
    
    def test_create_chart_invalid_type(self):
        """Test chart generation with invalid chart type."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        chart_data = {
            "type": "invalid_chart_type",
            "data": [{"x": 1, "y": 2}],
            "title": "Invalid Chart"
        }
        
        with pytest.raises(ValueError):
            generator._create_chart(chart_data)
    
    def test_create_chart_empty_data(self):
        """Test chart generation with empty data."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        chart_data = {
            "type": "bar",
            "data": [],  # Empty data
            "title": "Empty Chart"
        }
        
        with pytest.raises(ValueError):
            generator._create_chart(chart_data)


class TestTemplateService:
    """Test template management service."""
    
    @pytest.mark.asyncio
    async def test_create_template(
        self,
        sample_template_data,
        mock_database,
        mock_redis
    ):
        """Test template creation."""
        from app.services.template_service import TemplateService
        
        service = TemplateService()
        template_data = sample_template_data[0]
        
        result = await service.create_template(
            template_data=template_data,
            user_id="test-user-123"
        )
        
        assert result is not None
        assert "template_id" in result
        assert result["name"] == template_data["name"]
        assert result["theme"] == template_data["theme"]
        mock_database.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_template_by_id(
        self,
        sample_template_data,
        mock_database
    ):
        """Test getting template by ID."""
        from app.services.template_service import TemplateService
        
        service = TemplateService()
        template_id = "template-123"
        template_data = sample_template_data[0]
        
        with patch.object(service, '_fetch_template_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "template_id": template_id,
                **template_data
            }
            
            result = await service.get_template_by_id(template_id)
        
        assert result is not None
        assert result["template_id"] == template_id
        assert result["name"] == template_data["name"]
    
    @pytest.mark.asyncio
    async def test_update_template(
        self,
        sample_template_data,
        mock_database
    ):
        """Test template update."""
        from app.services.template_service import TemplateService
        
        service = TemplateService()
        template_id = "template-123"
        update_data = {
            "name": "Updated Template Name",
            "description": "Updated description"
        }
        
        with patch.object(service, '_fetch_template_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "template_id": template_id,
                **sample_template_data[0]
            }
            
            result = await service.update_template(
                template_id=template_id,
                update_data=update_data,
                user_id="test-user-123"
            )
        
        assert result is not None
        assert result["name"] == update_data["name"]
        assert result["description"] == update_data["description"]
        mock_database.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_template(
        self,
        mock_database
    ):
        """Test template deletion."""
        from app.services.template_service import TemplateService
        
        service = TemplateService()
        template_id = "template-123"
        
        with patch.object(service, '_template_exists') as mock_exists:
            mock_exists.return_value = True
            
            result = await service.delete_template(
                template_id=template_id,
                user_id="test-user-123"
            )
        
        assert result is not None
        assert result["deleted"] is True
        mock_database.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_list_templates(
        self,
        sample_template_data,
        mock_database
    ):
        """Test listing all templates."""
        from app.services.template_service import TemplateService
        
        service = TemplateService()
        
        with patch.object(service, '_fetch_templates_from_db') as mock_fetch:
            templates_with_ids = [
                {"template_id": f"template-{i}", **template}
                for i, template in enumerate(sample_template_data)
            ]
            mock_fetch.return_value = templates_with_ids
            
            result = await service.list_templates(
                user_id="test-user-123",
                page=1,
                per_page=10
            )
        
        assert result is not None
        assert "templates" in result
        assert len(result["templates"]) == len(sample_template_data)
        assert "total" in result
    
    def test_validate_template_data_valid(self):
        """Test template data validation with valid data."""
        from app.services.template_service import TemplateService
        
        service = TemplateService()
        valid_data = {
            "name": "Valid Template",
            "theme": "office",
            "slides": [
                {
                    "layout": "title_slide",
                    "elements": [
                        {"type": "title", "placeholder": "{{title}}"}
                    ]
                }
            ],
            "variables": ["title"]
        }
        
        result = service.validate_template_data(valid_data)
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_template_data_invalid(self):
        """Test template data validation with invalid data."""
        from app.services.template_service import TemplateService
        
        service = TemplateService()
        invalid_data = {
            "name": "",  # Empty name
            "theme": "invalid_theme",
            "slides": [],  # No slides
            "variables": []
        }
        
        result = service.validate_template_data(invalid_data)
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_duplicate_template(
        self,
        sample_template_data,
        mock_database
    ):
        """Test duplicating a template."""
        from app.services.template_service import TemplateService
        
        service = TemplateService()
        source_template_id = "template-123"
        template_data = sample_template_data[0]
        
        with patch.object(service, '_fetch_template_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "template_id": source_template_id,
                **template_data
            }
            
            result = await service.duplicate_template(
                source_template_id=source_template_id,
                user_id="test-user-123"
            )
        
        assert result is not None
        assert result["template_id"] != source_template_id
        assert "Copy of" in result["name"]
        mock_database.commit.assert_called()


class TestJobManagementService:
    """Test job management service."""
    
    @pytest.mark.asyncio
    async def test_create_job(
        self,
        mock_database,
        mock_redis
    ):
        """Test job creation."""
        from app.services.job_service import JobService
        
        service = JobService()
        job_data = {
            "user_id": "test-user-123",
            "presentation_data": {
                "title": "Test Presentation",
                "slides": [{"title": "Slide 1", "content": []}]
            },
            "configuration": {
                "theme": "office",
                "output_format": "pptx"
            }
        }
        
        result = await service.create_job(job_data)
        
        assert result is not None
        assert "job_id" in result
        assert result["status"] == "pending"
        assert result["user_id"] == "test-user-123"
        mock_database.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_job_by_id(
        self,
        sample_job_data,
        mock_database
    ):
        """Test getting job by ID."""
        from app.services.job_service import JobService
        
        service = JobService()
        job_id = sample_job_data[0]["job_id"]
        
        with patch.object(service, '_fetch_job_from_db') as mock_fetch:
            mock_fetch.return_value = sample_job_data[0]
            
            result = await service.get_job_by_id(job_id)
        
        assert result is not None
        assert result["job_id"] == job_id
        assert result["status"] == sample_job_data[0]["status"]
    
    @pytest.mark.asyncio
    async def test_update_job_status(
        self,
        mock_database
    ):
        """Test updating job status."""
        from app.services.job_service import JobService
        
        service = JobService()
        job_id = "job-123"
        new_status = "processing"
        
        with patch.object(service, '_job_exists') as mock_exists:
            mock_exists.return_value = True
            
            result = await service.update_job_status(
                job_id=job_id,
                status=new_status,
                metadata={"processing_started_at": datetime.now()}
            )
        
        assert result is not None
        assert result["status"] == new_status
        mock_database.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_cancel_job(
        self,
        mock_database
    ):
        """Test canceling a job."""
        from app.services.job_service import JobService
        
        service = JobService()
        job_id = "job-123"
        
        with patch.object(service, '_fetch_job_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "job_id": job_id,
                "status": "processing",
                "user_id": "test-user-123"
            }
            
            result = await service.cancel_job(
                job_id=job_id,
                user_id="test-user-123"
            )
        
        assert result is not None
        assert result["status"] == "cancelled"
        assert "cancelled_at" in result
        mock_database.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_job(
        self,
        mock_database,
        mock_file_operations
    ):
        """Test deleting a completed job."""
        from app.services.job_service import JobService
        
        service = JobService()
        job_id = "job-123"
        file_path = "test_presentation.pptx"
        
        # Create mock file
        mock_file_operations["create_pptx_file"](file_path, b"mock_content")
        
        with patch.object(service, '_fetch_job_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "job_id": job_id,
                "status": "completed",
                "user_id": "test-user-123",
                "file_path": os.path.join(mock_file_operations["temp_dir"], file_path)
            }
            
            result = await service.delete_job(
                job_id=job_id,
                user_id="test-user-123"
            )
        
        assert result is not None
        assert result["deleted"] is True
        mock_database.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_user_jobs(
        self,
        sample_job_data,
        mock_database
    ):
        """Test getting user jobs."""
        from app.services.job_service import JobService
        
        service = JobService()
        user_id = "test-user-123"
        
        with patch.object(service, '_fetch_user_jobs_from_db') as mock_fetch:
            mock_fetch.return_value = sample_job_data
            
            result = await service.get_user_jobs(
                user_id=user_id,
                page=1,
                per_page=10
            )
        
        assert result is not None
        assert "jobs" in result
        assert len(result["jobs"]) == len(sample_job_data)
        assert "total" in result
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_jobs(
        self,
        mock_database
    ):
        """Test cleaning up expired jobs."""
        from app.services.job_service import JobService
        
        service = JobService()
        
        with patch.object(service, '_fetch_expired_jobs') as mock_fetch:
            expired_jobs = [
                {
                    "job_id": "expired-job-1",
                    "file_path": "/tmp/expired1.pptx",
                    "created_at": datetime.now() - timedelta(days=8)
                },
                {
                    "job_id": "expired-job-2", 
                    "file_path": "/tmp/expired2.pptx",
                    "created_at": datetime.now() - timedelta(days=10)
                }
            ]
            mock_fetch.return_value = expired_jobs
            
            result = await service.cleanup_expired_jobs()
        
        assert result is not None
        assert "cleaned_count" in result
        assert result["cleaned_count"] == len(expired_jobs)
        mock_database.commit.assert_called()


class TestCachingService:
    """Test caching functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_job_result(
        self,
        mock_redis
    ):
        """Test caching job generation results."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        job_data = {
            "job_id": "job-123",
            "file_path": "/tmp/presentation.pptx",
            "metadata": {"slides_count": 10}
        }
        
        cache_key = "job_cache:job-123"
        
        # Test cache miss
        mock_redis.get.return_value = None
        
        with patch.object(generator, '_generate_presentation_internal') as mock_internal:
            mock_internal.return_value = job_data
            
            result = await generator.generate_presentation(
                presentation_data={"title": "Test", "slides": []},
                user_id="test-user-123"
            )
            
            assert result == job_data
            mock_redis.set.assert_called()  # Should cache result
    
    @pytest.mark.asyncio
    async def test_cache_hit_scenario(
        self,
        mock_redis
    ):
        """Test cache hit scenario."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        cached_data = {
            "job_id": "job-123",
            "file_path": "/tmp/cached_presentation.pptx",
            "metadata": {"slides_count": 8, "cached": True}
        }
        
        # Mock cache hit
        mock_redis.get.return_value = json.dumps(cached_data).encode()
        
        with patch.object(generator, '_generate_presentation_internal') as mock_internal:
            result = await generator.generate_presentation(
                presentation_data={"title": "Test", "slides": []},
                user_id="test-user-123"
            )
            
            # Should return cached result without calling internal generation
            mock_internal.assert_not_called()
            assert result["metadata"]["cached"] is True


class TestErrorHandling:
    """Test error handling in services."""
    
    @pytest.mark.asyncio
    async def test_presentation_generation_invalid_data_error(
        self,
        mock_python_pptx
    ):
        """Test error handling for invalid presentation data."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        
        # Mock python-pptx to raise an error
        mock_python_pptx["presentation_class"].side_effect = Exception("Invalid presentation format")
        
        with pytest.raises(Exception) as exc_info:
            await generator.generate_presentation(
                presentation_data={"title": "Test", "slides": []},
                user_id="test-user-123"
            )
        
        assert "Invalid presentation format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_file_write_error_during_generation(
        self,
        mock_python_pptx,
        mock_file_operations
    ):
        """Test error handling for file write errors during generation."""
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        
        # Mock file write to fail
        def failing_save(path):
            raise PermissionError("Cannot write file")
        
        mock_python_pptx["presentation"].save.side_effect = failing_save
        
        with pytest.raises(PermissionError):
            await generator.generate_presentation(
                presentation_data={"title": "Test", "slides": []},
                user_id="test-user-123"
            )
    
    @pytest.mark.asyncio
    async def test_template_not_found_error(
        self,
        mock_database
    ):
        """Test error handling for non-existent template."""
        from app.services.template_service import TemplateService
        
        service = TemplateService()
        template_id = "non-existent-template"
        
        with patch.object(service, '_fetch_template_from_db') as mock_fetch:
            mock_fetch.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await service.get_template_by_id(template_id)
        
        assert "Template not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_job_not_found_error(
        self,
        mock_database
    ):
        """Test error handling for non-existent job."""
        from app.services.job_service import JobService
        
        service = JobService()
        job_id = "non-existent-job"
        
        with patch.object(service, '_fetch_job_from_db') as mock_fetch:
            mock_fetch.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await service.get_job_by_id(job_id)
        
        assert "Job not found" in str(exc_info.value)


class TestAsyncPatterns:
    """Test async patterns and concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_presentation_generation(
        self,
        sample_presentation_data,
        sample_presentation_configurations,
        mock_python_pptx,
        mock_database,
        mock_redis
    ):
        """Test concurrent presentation generation."""
        import asyncio
        from app.services.powerpoint_generator import PowerPointGenerator
        
        generator = PowerPointGenerator()
        
        # Create multiple concurrent generation tasks
        tasks = []
        for i in range(3):
            request_data = {
                **sample_presentation_data,
                "title": f"Concurrent Presentation {i}",
                "configuration": sample_presentation_configurations[0]
            }
            
            task = generator.generate_presentation(
                presentation_data=request_data,
                user_id=f"test-user-{i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All tasks should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_background_job_processing(
        self,
        mock_database,
        mock_redis
    ):
        """Test background job processing."""
        from app.services.job_service import JobService
        
        service = JobService()
        
        # Create a job
        job_data = {
            "user_id": "test-user-123",
            "presentation_data": {"title": "Background Job", "slides": []},
            "configuration": {"theme": "office"}
        }
        
        job = await service.create_job(job_data)
        
        # Simulate background processing
        with patch.object(service, '_process_job_async') as mock_process:
            mock_process.return_value = {"status": "completed"}
            
            result = await service.process_job_in_background(job["job_id"])
        
        assert result is not None
        mock_process.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])