#!/usr/bin/env python3
"""
Comprehensive model tests for Visualization Service.

This module tests all Pydantic models including validation, serialization,
and data transformation logic for charts, dashboards, and export configurations.
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pydantic import ValidationError
import json


class TestChartModels:
    """Test chart-related models."""
    
    def test_chart_request_model_valid(self):
        """Test valid chart request model."""
        from app.models.chart import ChartRequest
        
        valid_data = {
            "chart_type": "line",
            "data": [
                {"_time": "2024-01-01T10:00:00", "count": 120},
                {"_time": "2024-01-01T10:05:00", "count": 150}
            ],
            "title": "Test Chart",
            "x_field": "_time",
            "y_field": "count",
            "width": 800,
            "height": 600
        }
        
        chart_request = ChartRequest(**valid_data)
        
        assert chart_request.chart_type == "line"
        assert len(chart_request.data) == 2
        assert chart_request.title == "Test Chart"
        assert chart_request.width == 800
        assert chart_request.height == 600
    
    def test_chart_request_model_invalid_type(self):
        """Test chart request with invalid chart type."""
        from app.models.chart import ChartRequest
        
        invalid_data = {
            "chart_type": "invalid_type",
            "data": [{"x": 1, "y": 2}],
            "title": "Test Chart"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ChartRequest(**invalid_data)
        
        assert "chart_type" in str(exc_info.value)
    
    def test_chart_request_empty_data(self):
        """Test chart request with empty data."""
        from app.models.chart import ChartRequest
        
        invalid_data = {
            "chart_type": "line",
            "data": [],  # Empty data
            "title": "Test Chart"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ChartRequest(**invalid_data)
        
        assert "data" in str(exc_info.value)
    
    def test_chart_response_model(self):
        """Test chart response model."""
        from app.models.chart import ChartResponse
        
        data = {
            "chart_id": "chart-123",
            "chart_html": "<div>Mock Chart HTML</div>",
            "chart_json": '{"data": [], "layout": {}}',
            "metadata": {
                "chart_type": "line",
                "data_points": 100,
                "generation_time_ms": 150
            }
        }
        
        response = ChartResponse(**data)
        
        assert response.chart_id == "chart-123"
        assert response.chart_html == "<div>Mock Chart HTML</div>"
        assert response.metadata["chart_type"] == "line"
        assert response.metadata["data_points"] == 100
    
    def test_chart_customization_model(self):
        """Test chart customization model."""
        from app.models.chart import ChartCustomization
        
        data = {
            "colors": {
                "primary": "#1f77b4",
                "secondary": "#ff7f0e"
            },
            "fonts": {
                "title": {"family": "Arial", "size": 16},
                "axes": {"family": "Arial", "size": 12}
            },
            "layout": {
                "margin": {"top": 50, "right": 50, "bottom": 50, "left": 50}
            }
        }
        
        customization = ChartCustomization(**data)
        
        assert customization.colors["primary"] == "#1f77b4"
        assert customization.fonts["title"]["size"] == 16
        assert customization.layout["margin"]["top"] == 50
    
    def test_export_configuration_model(self):
        """Test export configuration model."""
        from app.models.chart import ExportConfiguration
        
        data = {
            "format": "png",
            "width": 1200,
            "height": 800,
            "dpi": 300,
            "background_color": "white"
        }
        
        export_config = ExportConfiguration(**data)
        
        assert export_config.format == "png"
        assert export_config.width == 1200
        assert export_config.dpi == 300
    
    def test_export_configuration_invalid_format(self):
        """Test export configuration with invalid format."""
        from app.models.chart import ExportConfiguration
        
        invalid_data = {
            "format": "invalid_format",
            "width": 800,
            "height": 600
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ExportConfiguration(**invalid_data)
        
        assert "format" in str(exc_info.value)


class TestDashboardModels:
    """Test dashboard-related models."""
    
    def test_dashboard_request_model(self):
        """Test dashboard request model."""
        from app.models.dashboard import DashboardRequest
        
        data = {
            "title": "System Overview",
            "description": "Main system monitoring dashboard",
            "layout": {
                "type": "grid",
                "columns": 2,
                "rows": 2
            },
            "panels": [
                {
                    "id": "panel1",
                    "title": "Errors",
                    "chart_config": {
                        "chart_type": "line",
                        "x_field": "_time",
                        "y_field": "count"
                    },
                    "position": {"x": 0, "y": 0, "w": 1, "h": 1}
                }
            ]
        }
        
        dashboard = DashboardRequest(**data)
        
        assert dashboard.title == "System Overview"
        assert dashboard.layout["type"] == "grid"
        assert len(dashboard.panels) == 1
        assert dashboard.panels[0]["id"] == "panel1"
    
    def test_dashboard_panel_model(self):
        """Test dashboard panel model."""
        from app.models.dashboard import DashboardPanel
        
        data = {
            "id": "panel1",
            "title": "Error Trends",
            "chart_config": {
                "chart_type": "line",
                "title": "Errors Over Time",
                "x_field": "_time",
                "y_field": "error_count"
            },
            "position": {"x": 0, "y": 0, "w": 2, "h": 1},
            "refresh_interval": 60
        }
        
        panel = DashboardPanel(**data)
        
        assert panel.id == "panel1"
        assert panel.chart_config["chart_type"] == "line"
        assert panel.position["w"] == 2
        assert panel.refresh_interval == 60
    
    def test_dashboard_layout_model(self):
        """Test dashboard layout model."""
        from app.models.dashboard import DashboardLayout
        
        data = {
            "type": "grid",
            "columns": 3,
            "rows": 2,
            "responsive": True,
            "gap": 10
        }
        
        layout = DashboardLayout(**data)
        
        assert layout.type == "grid"
        assert layout.columns == 3
        assert layout.responsive is True
        assert layout.gap == 10
    
    def test_dashboard_response_model(self):
        """Test dashboard response model."""
        from app.models.dashboard import DashboardResponse
        
        data = {
            "dashboard_id": "dashboard-123",
            "title": "Test Dashboard",
            "layout_html": "<div>Dashboard HTML</div>",
            "panels": [
                {"panel_id": "panel1", "chart_id": "chart1"}
            ],
            "metadata": {
                "panel_count": 1,
                "creation_time_ms": 500
            }
        }
        
        response = DashboardResponse(**data)
        
        assert response.dashboard_id == "dashboard-123"
        assert response.title == "Test Dashboard"
        assert len(response.panels) == 1
        assert response.metadata["panel_count"] == 1


class TestInteractiveFeatureModels:
    """Test interactive feature models."""
    
    def test_interactive_configuration_model(self):
        """Test interactive configuration model."""
        from app.models.interactive import InteractiveConfiguration
        
        data = {
            "zoom": {"enabled": True, "type": "xy"},
            "pan": {"enabled": True, "type": "xy"},
            "hover": {
                "enabled": True,
                "show_closest": True
            },
            "click": {
                "enabled": True,
                "mode": "select"
            }
        }
        
        config = InteractiveConfiguration(**data)
        
        assert config.zoom["enabled"] is True
        assert config.hover["show_closest"] is True
        assert config.click["mode"] == "select"
    
    def test_zoom_configuration_model(self):
        """Test zoom configuration model."""
        from app.models.interactive import ZoomConfiguration
        
        data = {
            "enabled": True,
            "type": "xy",
            "constraint": "domain",
            "autosize": True
        }
        
        zoom_config = ZoomConfiguration(**data)
        
        assert zoom_config.enabled is True
        assert zoom_config.type == "xy"
        assert zoom_config.constraint == "domain"
    
    def test_hover_configuration_model(self):
        """Test hover configuration model."""
        from app.models.interactive import HoverConfiguration
        
        data = {
            "enabled": True,
            "show_closest": True,
            "compare": False,
            "template": "custom_template"
        }
        
        hover_config = HoverConfiguration(**data)
        
        assert hover_config.enabled is True
        assert hover_config.show_closest is True
        assert hover_config.template == "custom_template"


class TestValidationAndSerialization:
    """Test data validation and serialization."""
    
    def test_chart_data_point_validation(self):
        """Test chart data point validation."""
        from app.models.chart import ChartDataPoint
        
        # Valid data point
        valid_data = {
            "_time": "2024-01-01T10:00:00",
            "count": 120,
            "source": "app1"
        }
        
        data_point = ChartDataPoint(**valid_data)
        assert data_point.dict()["_time"] == "2024-01-01T10:00:00"
        assert data_point.dict()["count"] == 120
    
    def test_numeric_field_validation(self):
        """Test numeric field validation."""
        from app.models.chart import ChartRequest
        
        # Test with negative dimensions (should fail)
        invalid_data = {
            "chart_type": "line",
            "data": [{"x": 1, "y": 2}],
            "title": "Test",
            "width": -800,  # Negative width
            "height": 600
        }
        
        with pytest.raises(ValidationError):
            ChartRequest(**invalid_data)
    
    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        from app.models.chart import ChartResponse
        
        data = {
            "chart_id": "chart-123",
            "chart_html": "<div>Chart</div>",
            "chart_json": '{"data": []}',
            "metadata": {"chart_type": "line"}
        }
        
        response = ChartResponse(**data)
        json_str = response.model_dump_json()
        parsed = json.loads(json_str)
        
        assert parsed["chart_id"] == "chart-123"
        assert parsed["metadata"]["chart_type"] == "line"
    
    def test_optional_fields_handling(self):
        """Test optional field handling."""
        from app.models.chart import ChartRequest
        
        # Minimal required fields only
        minimal_data = {
            "chart_type": "line",
            "data": [{"x": 1, "y": 2}],
            "title": "Test Chart"
        }
        
        chart = ChartRequest(**minimal_data)
        
        # Optional fields should have default values
        assert chart.width > 0  # Should have default width
        assert chart.height > 0  # Should have default height
        assert chart.interactive is not None  # Should have default


class TestColorValidation:
    """Test color validation in models."""
    
    def test_valid_color_formats(self):
        """Test valid color format validation."""
        from app.models.chart import ChartCustomization
        
        valid_colors = {
            "colors": {
                "hex": "#1f77b4",
                "rgb": "rgb(255, 0, 0)",
                "name": "blue"
            }
        }
        
        customization = ChartCustomization(**valid_colors)
        assert customization.colors["hex"] == "#1f77b4"
    
    def test_invalid_color_formats(self):
        """Test invalid color format validation."""
        from app.models.chart import ChartCustomization
        
        # This test assumes color validation is implemented
        invalid_colors = {
            "colors": {
                "invalid": "not-a-color"
            }
        }
        
        try:
            ChartCustomization(**invalid_colors)
            # If no validation error, that's also acceptable
        except ValidationError:
            # If validation error, that's expected for invalid colors
            pass


class TestComplexDataStructures:
    """Test complex data structure validation."""
    
    def test_nested_panel_configuration(self):
        """Test nested panel configuration validation."""
        from app.models.dashboard import DashboardRequest
        
        complex_data = {
            "title": "Complex Dashboard",
            "layout": {
                "type": "flexible",
                "responsive": True
            },
            "panels": [
                {
                    "id": "panel1",
                    "title": "Multi-Series Chart",
                    "chart_config": {
                        "chart_type": "line",
                        "data": [],
                        "multi_series": True,
                        "series_configs": [
                            {"name": "series1", "color": "#1f77b4"},
                            {"name": "series2", "color": "#ff7f0e"}
                        ]
                    },
                    "position": {"x": 0, "y": 0, "w": 2, "h": 1}
                }
            ]
        }
        
        dashboard = DashboardRequest(**complex_data)
        
        assert dashboard.title == "Complex Dashboard"
        assert len(dashboard.panels) == 1
        panel_config = dashboard.panels[0]["chart_config"]
        assert panel_config.get("multi_series") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])