#!/usr/bin/env python3
"""
Comprehensive model tests for PowerPoint Export Service.

This module tests all Pydantic models including validation, serialization,
and data transformation logic for presentations, templates, jobs, and configurations.
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pydantic import ValidationError
import json


class TestPresentationModels:
    """Test presentation-related models."""
    
    def test_presentation_request_model_valid(self):
        """Test valid presentation request model."""
        from app.models.powerpoint_models import PresentationRequest
        
        valid_data = {
            "title": "Quarterly Business Review",
            "subtitle": "Q4 2024 Analysis",
            "author": "Analytics Team",
            "company": "Acme Corp",
            "slides": [
                {
                    "title": "Executive Summary",
                    "content": ["Point 1", "Point 2"],
                    "layout": "title_and_content"
                },
                {
                    "title": "Chart Slide",
                    "content": [],
                    "layout": "title_only",
                    "chart": {
                        "type": "bar",
                        "data": [{"category": "A", "value": 100}],
                        "title": "Sample Chart"
                    }
                }
            ],
            "configuration": {
                "theme": "office",
                "animation": "fade",
                "transition": "slide",
                "output_format": "pptx"
            }
        }
        
        presentation = PresentationRequest(**valid_data)
        
        assert presentation.title == "Quarterly Business Review"
        assert presentation.subtitle == "Q4 2024 Analysis"
        assert len(presentation.slides) == 2
        assert presentation.configuration.theme == "office"
        assert presentation.configuration.output_format == "pptx"
    
    def test_presentation_request_minimal_data(self):
        """Test presentation request with minimal required data."""
        from app.models.powerpoint_models import PresentationRequest
        
        minimal_data = {
            "title": "Test Presentation",
            "slides": [
                {
                    "title": "Slide 1",
                    "content": ["Content line 1"],
                    "layout": "title_and_content"
                }
            ]
        }
        
        presentation = PresentationRequest(**minimal_data)
        
        assert presentation.title == "Test Presentation"
        assert len(presentation.slides) == 1
        # Optional fields should have defaults
        assert presentation.author is None or isinstance(presentation.author, str)
        assert presentation.configuration is None or hasattr(presentation.configuration, 'theme')
    
    def test_presentation_request_invalid_empty_title(self):
        """Test presentation request with empty title."""
        from app.models.powerpoint_models import PresentationRequest
        
        invalid_data = {
            "title": "",  # Empty title
            "slides": [{"title": "Slide 1", "content": [], "layout": "title_only"}]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PresentationRequest(**invalid_data)
        
        assert "title" in str(exc_info.value)
    
    def test_presentation_request_invalid_no_slides(self):
        """Test presentation request with no slides."""
        from app.models.powerpoint_models import PresentationRequest
        
        invalid_data = {
            "title": "Test Presentation",
            "slides": []  # No slides
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PresentationRequest(**invalid_data)
        
        assert "slides" in str(exc_info.value)
    
    def test_slide_model_valid(self):
        """Test valid slide model."""
        from app.models.powerpoint_models import Slide
        
        valid_data = {
            "title": "Sample Slide",
            "content": ["Bullet point 1", "Bullet point 2"],
            "layout": "title_and_content",
            "notes": "Speaker notes for this slide"
        }
        
        slide = Slide(**valid_data)
        
        assert slide.title == "Sample Slide"
        assert len(slide.content) == 2
        assert slide.layout == "title_and_content"
        assert slide.notes == "Speaker notes for this slide"
    
    def test_slide_model_with_chart(self):
        """Test slide model with embedded chart."""
        from app.models.powerpoint_models import Slide
        
        valid_data = {
            "title": "Chart Slide",
            "content": [],
            "layout": "chart_slide",
            "chart": {
                "type": "line",
                "data": [
                    {"x": "Jan", "y": 100},
                    {"x": "Feb", "y": 150}
                ],
                "title": "Monthly Trends",
                "x_label": "Month",
                "y_label": "Value"
            }
        }
        
        slide = Slide(**valid_data)
        
        assert slide.chart is not None
        assert slide.chart.type == "line"
        assert slide.chart.title == "Monthly Trends"
        assert len(slide.chart.data) == 2
    
    def test_slide_model_with_multiple_charts(self):
        """Test slide model with multiple charts."""
        from app.models.powerpoint_models import Slide
        
        valid_data = {
            "title": "Comparison Slide",
            "content": [],
            "layout": "comparison",
            "charts": [
                {
                    "type": "bar",
                    "data": [{"category": "A", "value": 50}],
                    "title": "Chart 1"
                },
                {
                    "type": "pie", 
                    "data": [{"label": "X", "value": 30}],
                    "title": "Chart 2"
                }
            ]
        }
        
        slide = Slide(**valid_data)
        
        assert slide.charts is not None
        assert len(slide.charts) == 2
        assert slide.charts[0].type == "bar"
        assert slide.charts[1].type == "pie"


class TestChartModels:
    """Test chart-related models."""
    
    def test_chart_model_valid(self):
        """Test valid chart model."""
        from app.models.powerpoint_models import Chart
        
        valid_data = {
            "type": "bar",
            "data": [
                {"category": "Q1", "value": 100},
                {"category": "Q2", "value": 150},
                {"category": "Q3", "value": 120}
            ],
            "title": "Quarterly Revenue",
            "x_label": "Quarter",
            "y_label": "Revenue (K)",
            "color_scheme": "blue"
        }
        
        chart = Chart(**valid_data)
        
        assert chart.type == "bar"
        assert len(chart.data) == 3
        assert chart.title == "Quarterly Revenue"
        assert chart.x_label == "Quarter"
        assert chart.color_scheme == "blue"
    
    def test_chart_model_line_chart(self):
        """Test line chart model."""
        from app.models.powerpoint_models import Chart
        
        valid_data = {
            "type": "line",
            "data": [
                {"x": "Jan", "y": 85},
                {"x": "Feb", "y": 90},
                {"x": "Mar", "y": 88}
            ],
            "title": "Monthly Performance"
        }
        
        chart = Chart(**valid_data)
        
        assert chart.type == "line"
        assert len(chart.data) == 3
        assert chart.data[0]["x"] == "Jan"
        assert chart.data[0]["y"] == 85
    
    def test_chart_model_pie_chart(self):
        """Test pie chart model."""
        from app.models.powerpoint_models import Chart
        
        valid_data = {
            "type": "pie",
            "data": [
                {"label": "Product A", "value": 45},
                {"label": "Product B", "value": 30},
                {"label": "Product C", "value": 25}
            ],
            "title": "Market Share",
            "show_percentages": True
        }
        
        chart = Chart(**valid_data)
        
        assert chart.type == "pie"
        assert len(chart.data) == 3
        assert chart.show_percentages is True
        assert chart.data[0]["label"] == "Product A"
    
    def test_chart_model_invalid_type(self):
        """Test chart model with invalid chart type."""
        from app.models.powerpoint_models import Chart
        
        invalid_data = {
            "type": "invalid_chart_type",
            "data": [{"x": 1, "y": 2}],
            "title": "Invalid Chart"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Chart(**invalid_data)
        
        assert "type" in str(exc_info.value)
    
    def test_chart_model_empty_data(self):
        """Test chart model with empty data."""
        from app.models.powerpoint_models import Chart
        
        invalid_data = {
            "type": "bar",
            "data": [],  # Empty data
            "title": "Empty Chart"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Chart(**invalid_data)
        
        assert "data" in str(exc_info.value)


class TestConfigurationModels:
    """Test configuration-related models."""
    
    def test_presentation_configuration_model(self):
        """Test presentation configuration model."""
        from app.models.powerpoint_models import PresentationConfiguration
        
        valid_data = {
            "theme": "modern",
            "animation": "zoom",
            "transition": "push",
            "output_format": "pdf",
            "include_charts": True,
            "chart_style": "minimal",
            "font_family": "Arial",
            "font_size": 16,
            "color_scheme": "green"
        }
        
        config = PresentationConfiguration(**valid_data)
        
        assert config.theme == "modern"
        assert config.animation == "zoom"
        assert config.transition == "push"
        assert config.output_format == "pdf"
        assert config.include_charts is True
        assert config.font_size == 16
    
    def test_configuration_default_values(self):
        """Test configuration model with default values."""
        from app.models.powerpoint_models import PresentationConfiguration
        
        minimal_data = {
            "theme": "office"
        }
        
        config = PresentationConfiguration(**minimal_data)
        
        assert config.theme == "office"
        # Check that defaults are applied
        assert config.output_format is not None
        assert config.include_charts is not None
        assert config.font_size is None or isinstance(config.font_size, int)
    
    def test_configuration_invalid_theme(self):
        """Test configuration with invalid theme."""
        from app.models.powerpoint_models import PresentationConfiguration
        
        invalid_data = {
            "theme": "invalid_theme"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PresentationConfiguration(**invalid_data)
        
        assert "theme" in str(exc_info.value)
    
    def test_configuration_invalid_output_format(self):
        """Test configuration with invalid output format."""
        from app.models.powerpoint_models import PresentationConfiguration
        
        invalid_data = {
            "theme": "office",
            "output_format": "invalid_format"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PresentationConfiguration(**invalid_data)
        
        assert "output_format" in str(exc_info.value)
    
    def test_configuration_invalid_font_size(self):
        """Test configuration with invalid font size."""
        from app.models.powerpoint_models import PresentationConfiguration
        
        invalid_data = {
            "theme": "office",
            "font_size": -5  # Negative font size
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PresentationConfiguration(**invalid_data)
        
        assert "font_size" in str(exc_info.value)


class TestJobModels:
    """Test job-related models."""
    
    def test_job_model_valid(self):
        """Test valid job model."""
        from app.models.powerpoint_models import Job
        
        valid_data = {
            "job_id": "job-123",
            "user_id": "user-456",
            "status": "completed",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "file_path": "/tmp/presentation.pptx",
            "file_size": 2048576,
            "metadata": {
                "slides_count": 15,
                "charts_count": 8,
                "processing_time_ms": 45000,
                "theme": "office"
            }
        }
        
        job = Job(**valid_data)
        
        assert job.job_id == "job-123"
        assert job.user_id == "user-456"
        assert job.status == "completed"
        assert job.file_size == 2048576
        assert job.metadata["slides_count"] == 15
    
    def test_job_model_pending_status(self):
        """Test job model with pending status."""
        from app.models.powerpoint_models import Job
        
        valid_data = {
            "job_id": "job-pending-123",
            "user_id": "user-456",
            "status": "pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "file_path": None,
            "file_size": None,
            "metadata": {
                "estimated_processing_time_ms": 30000
            }
        }
        
        job = Job(**valid_data)
        
        assert job.job_id == "job-pending-123"
        assert job.status == "pending"
        assert job.file_path is None
        assert job.file_size is None
    
    def test_job_model_failed_status(self):
        """Test job model with failed status."""
        from app.models.powerpoint_models import Job
        
        valid_data = {
            "job_id": "job-failed-123",
            "user_id": "user-456",
            "status": "failed",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "file_path": None,
            "file_size": None,
            "metadata": {
                "error": "Invalid chart data format",
                "error_details": "Chart data must contain 'data' field"
            }
        }
        
        job = Job(**valid_data)
        
        assert job.job_id == "job-failed-123"
        assert job.status == "failed"
        assert job.metadata["error"] == "Invalid chart data format"
    
    def test_job_model_invalid_status(self):
        """Test job model with invalid status."""
        from app.models.powerpoint_models import Job
        
        invalid_data = {
            "job_id": "job-123",
            "user_id": "user-456",
            "status": "invalid_status",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Job(**invalid_data)
        
        assert "status" in str(exc_info.value)
    
    def test_job_response_model(self):
        """Test job response model."""
        from app.models.powerpoint_models import JobResponse
        
        valid_data = {
            "job_id": "job-123",
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "file_url": "https://example.com/files/job-123.pptx",
            "metadata": {
                "slides_count": 10,
                "file_size": 1024000,
                "processing_time_ms": 25000
            }
        }
        
        response = JobResponse(**valid_data)
        
        assert response.job_id == "job-123"
        assert response.status == "completed"
        assert response.file_url == "https://example.com/files/job-123.pptx"
        assert response.metadata["slides_count"] == 10


class TestTemplateModels:
    """Test template-related models."""
    
    def test_template_model_valid(self):
        """Test valid template model."""
        from app.models.powerpoint_models import Template
        
        valid_data = {
            "template_id": "template-123",
            "name": "Business Report Template",
            "description": "Professional business presentation template",
            "theme": "office",
            "slides": [
                {
                    "layout": "title_slide",
                    "elements": [
                        {"type": "title", "placeholder": "{{title}}"},
                        {"type": "subtitle", "placeholder": "{{subtitle}}"}
                    ]
                },
                {
                    "layout": "title_and_content", 
                    "elements": [
                        {"type": "title", "placeholder": "{{slide_title}}"},
                        {"type": "content", "placeholder": "{{content}}"}
                    ]
                }
            ],
            "variables": ["title", "subtitle", "slide_title", "content"],
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        template = Template(**valid_data)
        
        assert template.template_id == "template-123"
        assert template.name == "Business Report Template"
        assert template.theme == "office"
        assert len(template.slides) == 2
        assert len(template.variables) == 4
        assert template.is_active is True
    
    def test_template_request_model(self):
        """Test template request model."""
        from app.models.powerpoint_models import TemplateRequest
        
        valid_data = {
            "name": "New Template",
            "description": "A new custom template",
            "theme": "modern",
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
        
        template_request = TemplateRequest(**valid_data)
        
        assert template_request.name == "New Template"
        assert template_request.theme == "modern"
        assert len(template_request.slides) == 1
    
    def test_template_invalid_empty_name(self):
        """Test template with empty name."""
        from app.models.powerpoint_models import TemplateRequest
        
        invalid_data = {
            "name": "",  # Empty name
            "theme": "office",
            "slides": [{"layout": "title_slide", "elements": []}],
            "variables": []
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TemplateRequest(**invalid_data)
        
        assert "name" in str(exc_info.value)
    
    def test_template_slide_element_model(self):
        """Test template slide element model."""
        from app.models.powerpoint_models import TemplateSlideElement
        
        valid_data = {
            "type": "title",
            "placeholder": "{{presentation_title}}",
            "position": {"x": 100, "y": 50},
            "size": {"width": 800, "height": 100},
            "formatting": {
                "font_family": "Arial",
                "font_size": 24,
                "color": "#000000",
                "bold": True
            }
        }
        
        element = TemplateSlideElement(**valid_data)
        
        assert element.type == "title"
        assert element.placeholder == "{{presentation_title}}"
        assert element.position["x"] == 100
        assert element.size["width"] == 800
        assert element.formatting["font_size"] == 24


class TestValidationAndSerialization:
    """Test data validation and serialization."""
    
    def test_presentation_json_serialization(self):
        """Test presentation model JSON serialization."""
        from app.models.powerpoint_models import PresentationRequest
        
        data = {
            "title": "Test Presentation",
            "slides": [
                {
                    "title": "Slide 1",
                    "content": ["Content line"],
                    "layout": "title_and_content"
                }
            ],
            "configuration": {
                "theme": "office",
                "output_format": "pptx"
            }
        }
        
        presentation = PresentationRequest(**data)
        json_str = presentation.model_dump_json()
        parsed = json.loads(json_str)
        
        assert parsed["title"] == "Test Presentation"
        assert len(parsed["slides"]) == 1
        assert parsed["configuration"]["theme"] == "office"
    
    def test_nested_model_validation(self):
        """Test nested model validation."""
        from app.models.powerpoint_models import PresentationRequest
        
        # Invalid nested configuration
        invalid_data = {
            "title": "Test Presentation",
            "slides": [
                {
                    "title": "Slide 1",
                    "content": ["Content"],
                    "layout": "title_and_content"
                }
            ],
            "configuration": {
                "theme": "invalid_theme",  # Invalid theme
                "output_format": "pptx"
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PresentationRequest(**invalid_data)
        
        # Should indicate the nested validation error
        error_str = str(exc_info.value)
        assert "configuration" in error_str or "theme" in error_str
    
    def test_optional_field_handling(self):
        """Test optional field handling."""
        from app.models.powerpoint_models import PresentationRequest
        
        # Only required fields
        minimal_data = {
            "title": "Minimal Presentation",
            "slides": [
                {
                    "title": "Slide 1",
                    "content": [],
                    "layout": "title_only"
                }
            ]
        }
        
        presentation = PresentationRequest(**minimal_data)
        
        # Optional fields should be None or have defaults
        assert presentation.subtitle is None
        assert presentation.author is None
        assert presentation.company is None
        # Configuration should be None or have defaults
        assert presentation.configuration is None or hasattr(presentation.configuration, 'theme')
    
    def test_list_field_validation(self):
        """Test list field validation."""
        from app.models.powerpoint_models import Slide
        
        # Valid list content
        valid_data = {
            "title": "List Slide",
            "content": ["Point 1", "Point 2", "Point 3"],
            "layout": "title_and_content"
        }
        
        slide = Slide(**valid_data)
        
        assert len(slide.content) == 3
        assert all(isinstance(item, str) for item in slide.content)
    
    def test_datetime_field_handling(self):
        """Test datetime field handling."""
        from app.models.powerpoint_models import Job
        
        now = datetime.now()
        
        valid_data = {
            "job_id": "job-123",
            "user_id": "user-456", 
            "status": "pending",
            "created_at": now,
            "updated_at": now
        }
        
        job = Job(**valid_data)
        
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)
        assert job.created_at == now
        assert job.updated_at == now


class TestEnumValidation:
    """Test enum validation."""
    
    def test_job_status_enum(self):
        """Test JobStatus enum validation."""
        from app.models.powerpoint_models import JobStatus
        
        # Valid statuses
        valid_statuses = ["pending", "processing", "completed", "failed", "cancelled"]
        
        for status in valid_statuses:
            assert hasattr(JobStatus, status.upper())
            assert getattr(JobStatus, status.upper()) == status
    
    def test_output_format_enum(self):
        """Test OutputFormat enum validation."""
        from app.models.powerpoint_models import OutputFormat
        
        # Valid formats
        valid_formats = ["pptx", "pdf", "png", "jpg"]
        
        for format_val in valid_formats:
            assert hasattr(OutputFormat, format_val.upper())
            assert getattr(OutputFormat, format_val.upper()) == format_val
    
    def test_theme_enum(self):
        """Test Theme enum validation."""
        from app.models.powerpoint_models import Theme
        
        # Valid themes
        valid_themes = ["office", "modern", "colorful", "dark", "minimal"]
        
        for theme in valid_themes:
            assert hasattr(Theme, theme.upper())
            assert getattr(Theme, theme.upper()) == theme
    
    def test_chart_type_enum(self):
        """Test ChartType enum validation."""
        from app.models.powerpoint_models import ChartType
        
        # Valid chart types
        valid_types = ["bar", "column", "line", "pie", "area", "scatter", "doughnut", "radar"]
        
        for chart_type in valid_types:
            assert hasattr(ChartType, chart_type.upper())
            assert getattr(ChartType, chart_type.upper()) == chart_type


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])