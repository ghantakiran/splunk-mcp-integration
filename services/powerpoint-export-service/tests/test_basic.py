#!/usr/bin/env python3
"""
Basic tests for PowerPoint Export Service.

These tests verify core functionality and API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


class TestBasicEndpoints:
    """Test basic API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "PowerPoint Export Service"
        assert data["version"] == "1.0.0"
        assert data["status"] == "healthy"
    
    def test_health_endpoint(self):
        """Test basic health endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "powerpoint-export-service"
        assert data["version"] == "1.0.0"
    
    def test_api_health_endpoint(self):
        """Test API health endpoint."""
        response = self.client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_capabilities_endpoint(self):
        """Test capabilities endpoint (no auth required)."""
        response = self.client.get("/api/v1/powerpoint-exports/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "supported_formats" in data
        assert "supported_themes" in data
        assert "supported_chart_types" in data
        assert "max_file_size_mb" in data
    
    def test_supported_formats_endpoint(self):
        """Test supported formats endpoint."""
        response = self.client.get("/api/v1/powerpoint-exports/formats")
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        assert len(data["formats"]) > 0
        
        # Check that PPTX format is supported
        format_values = [fmt["format"] for fmt in data["formats"]]
        assert "pptx" in format_values
    
    def test_templates_list_requires_auth(self):
        """Test that templates endpoint requires authentication."""
        response = self.client.get("/api/v1/templates/")
        assert response.status_code == 403  # Forbidden without auth
    
    def test_generate_requires_auth(self):
        """Test that generate endpoint requires authentication."""
        response = self.client.post("/api/v1/powerpoint-exports/generate", json={})
        assert response.status_code == 403  # Forbidden without auth
    
    def test_jobs_list_requires_auth(self):
        """Test that jobs list endpoint requires authentication."""
        response = self.client.get("/api/v1/powerpoint-exports/jobs")
        assert response.status_code == 403  # Forbidden without auth


class TestModels:
    """Test data models."""
    
    def test_job_status_enum(self):
        """Test JobStatus enum values."""
        from app.models.powerpoint_models import JobStatus
        
        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"
    
    def test_output_format_enum(self):
        """Test OutputFormat enum values."""
        from app.models.powerpoint_models import OutputFormat
        
        assert OutputFormat.PPTX == "pptx"
        assert OutputFormat.PDF == "pdf"
        assert OutputFormat.PNG == "png"
        assert OutputFormat.JPG == "jpg"
    
    def test_theme_enum(self):
        """Test Theme enum values."""
        from app.models.powerpoint_models import Theme
        
        assert Theme.OFFICE == "office"
        assert Theme.MODERN == "modern"
        assert Theme.COLORFUL == "colorful"
        assert Theme.DARK == "dark"
        assert Theme.MINIMAL == "minimal"
    
    def test_chart_type_enum(self):
        """Test ChartType enum values."""
        from app.models.powerpoint_models import ChartType
        
        assert ChartType.BAR == "bar"
        assert ChartType.COLUMN == "column"
        assert ChartType.LINE == "line"
        assert ChartType.PIE == "pie"
        assert ChartType.AREA == "area"
        assert ChartType.SCATTER == "scatter"
        assert ChartType.DOUGHNUT == "doughnut"
        assert ChartType.RADAR == "radar"


class TestConfiguration:
    """Test configuration loading."""
    
    def test_settings_loading(self):
        """Test that settings load correctly."""
        from app.core.config import settings
        
        # Test default values
        assert settings.API_PORT == 8011
        assert settings.DEBUG is False
        assert settings.PPT_MAX_SLIDES == 100
        assert settings.DEFAULT_THEME == "office"
        assert "office" in settings.AVAILABLE_THEMES
    
    def test_theme_validation(self):
        """Test theme validation in settings."""
        from app.core.config import settings
        
        # Default theme should be in available themes
        assert settings.DEFAULT_THEME in settings.AVAILABLE_THEMES
    
    def test_animation_validation(self):
        """Test animation validation in settings."""
        from app.core.config import settings
        
        # Default animation should be in available animations
        assert settings.DEFAULT_ANIMATION in settings.AVAILABLE_ANIMATIONS
    
    def test_transition_validation(self):
        """Test transition validation in settings."""
        from app.core.config import settings
        
        # Default transition should be in available transitions
        assert settings.DEFAULT_TRANSITION in settings.AVAILABLE_TRANSITIONS


class TestUtilities:
    """Test utility functions."""
    
    def test_auth_module_imports(self):
        """Test that auth module imports correctly."""
        from app.utils.auth import create_access_token, verify_token
        
        # Should be able to import without errors
        assert callable(create_access_token)
        assert callable(verify_token)
    
    def test_rate_limiter_imports(self):
        """Test that rate limiter module imports correctly."""
        from app.utils.rate_limiter import check_rate_limit, RateLimitExceeded
        
        # Should be able to import without errors
        assert callable(check_rate_limit)
        assert issubclass(RateLimitExceeded, Exception)
    
    def test_powerpoint_generator_imports(self):
        """Test that PowerPoint generator imports correctly."""
        from app.services.powerpoint_generator import PowerPointGenerator, powerpoint_generator
        
        # Should be able to import without errors
        assert isinstance(powerpoint_generator, PowerPointGenerator)


if __name__ == "__main__":
    pytest.main([__file__])
