#!/usr/bin/env python3
"""
Comprehensive service tests for Visualization Service.

This module tests core services including chart generation, dashboard
management, export functionality, and interactive features.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List
import json
import base64


class TestChartGeneratorService:
    """Test chart generation service."""
    
    @pytest.mark.asyncio
    async def test_generate_line_chart(
        self, 
        mock_plotly,
        sample_chart_data,
        sample_chart_configurations
    ):
        """Test line chart generation."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        chart_config = sample_chart_configurations[0]  # Line chart
        
        result = await generator.generate_chart(
            data=sample_chart_data,
            chart_type=chart_config["chart_type"],
            title=chart_config["title"],
            x_field=chart_config["x_field"],
            y_field=chart_config["y_field"]
        )
        
        assert result is not None
        assert "chart_html" in result
        assert "metadata" in result
        assert result["metadata"]["chart_type"] == "line"
        
        # Verify Plotly was called correctly
        mock_plotly["px"].line.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_bar_chart(
        self, 
        mock_plotly,
        sample_chart_data,
        sample_chart_configurations
    ):
        """Test bar chart generation."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        chart_config = sample_chart_configurations[1]  # Bar chart
        
        result = await generator.generate_chart(
            data=sample_chart_data,
            chart_type=chart_config["chart_type"],
            title=chart_config["title"],
            x_field=chart_config["x_field"],
            y_field=chart_config["y_field"]
        )
        
        assert result["metadata"]["chart_type"] == "bar"
        mock_plotly["px"].bar.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_pie_chart(
        self, 
        mock_plotly,
        sample_chart_data,
        sample_chart_configurations
    ):
        """Test pie chart generation."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        chart_config = sample_chart_configurations[2]  # Pie chart
        
        result = await generator.generate_chart(
            data=sample_chart_data,
            chart_type=chart_config["chart_type"],
            title=chart_config["title"],
            value_field=chart_config["value_field"],
            label_field=chart_config["label_field"]
        )
        
        assert result["metadata"]["chart_type"] == "pie"
        mock_plotly["px"].pie.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_scatter_chart(
        self, 
        mock_plotly,
        sample_chart_configurations
    ):
        """Test scatter chart generation."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        chart_config = sample_chart_configurations[4]  # Scatter chart
        
        # Create scatter data with required fields
        scatter_data = [
            {"load": 10, "response_time": 100, "count": 5, "source": "app1"},
            {"load": 20, "response_time": 150, "count": 8, "source": "app2"}
        ]
        
        result = await generator.generate_chart(
            data=scatter_data,
            chart_type=chart_config["chart_type"],
            title=chart_config["title"],
            x_field=chart_config["x_field"],
            y_field=chart_config["y_field"]
        )
        
        assert result["metadata"]["chart_type"] == "scatter"
        mock_plotly["px"].scatter.assert_called_once()
    
    def test_validate_chart_data_valid(self):
        """Test chart data validation with valid data."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        valid_data = [
            {"x": 1, "y": 10},
            {"x": 2, "y": 20},
            {"x": 3, "y": 15}
        ]
        
        result = generator.validate_data(valid_data)
        assert result is True
    
    def test_validate_chart_data_empty(self):
        """Test chart data validation with empty data."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        
        result = generator.validate_data([])
        assert result is False
    
    def test_select_optimal_chart_type(self):
        """Test automatic chart type selection."""
        from app.services.chart_selector import ChartSelector
        
        selector = ChartSelector()
        
        # Time series data should suggest line chart
        time_series_data = [
            {"_time": "2024-01-01T10:00:00", "count": 100},
            {"_time": "2024-01-01T11:00:00", "count": 120}
        ]
        
        suggested_type = selector.select_optimal_type(time_series_data)
        assert suggested_type in ["line", "timechart"]
        
        # Categorical data should suggest bar chart
        categorical_data = [
            {"category": "A", "value": 100},
            {"category": "B", "value": 150}
        ]
        
        suggested_type = selector.select_optimal_type(categorical_data)
        assert suggested_type in ["bar", "column"]
    
    @pytest.mark.asyncio
    async def test_chart_generation_with_customization(
        self,
        mock_plotly,
        sample_chart_data,
        sample_customization_options
    ):
        """Test chart generation with customization options."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        
        result = await generator.generate_chart(
            data=sample_chart_data,
            chart_type="line",
            title="Custom Chart",
            x_field="_time",
            y_field="count",
            customization=sample_customization_options
        )
        
        assert result is not None
        # Should apply customization
        mock_plotly["figure"].update_layout.assert_called()


class TestChartExportService:
    """Test chart export service."""
    
    @pytest.mark.asyncio
    async def test_export_chart_png(
        self,
        mock_plotly,
        mock_file_operations
    ):
        """Test PNG chart export."""
        from app.services.chart_export import ChartExportService
        
        export_service = ChartExportService()
        
        # Mock chart figure
        mock_figure = mock_plotly["figure"]
        
        export_config = {
            "format": "png",
            "width": 800,
            "height": 600,
            "dpi": 150
        }
        
        result = await export_service.export_chart(
            chart_figure=mock_figure,
            export_config=export_config
        )
        
        assert result is not None
        assert result["format"] == "png"
        assert "file_path" in result
        mock_figure.to_image.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_chart_svg(
        self,
        mock_plotly,
        mock_file_operations
    ):
        """Test SVG chart export."""
        from app.services.chart_export import ChartExportService
        
        export_service = ChartExportService()
        mock_figure = mock_plotly["figure"]
        
        export_config = {
            "format": "svg",
            "width": 800,
            "height": 600
        }
        
        result = await export_service.export_chart(
            chart_figure=mock_figure,
            export_config=export_config
        )
        
        assert result["format"] == "svg"
        mock_figure.to_image.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_chart_html(
        self,
        mock_plotly,
        mock_file_operations
    ):
        """Test HTML chart export."""
        from app.services.chart_export import ChartExportService
        
        export_service = ChartExportService()
        mock_figure = mock_plotly["figure"]
        
        export_config = {
            "format": "html",
            "interactive": True,
            "include_plotly": True
        }
        
        result = await export_service.export_chart(
            chart_figure=mock_figure,
            export_config=export_config
        )
        
        assert result["format"] == "html"
        mock_figure.to_html.assert_called_once()
    
    def test_get_supported_formats(self):
        """Test getting supported export formats."""
        from app.services.chart_export import ChartExportService
        
        export_service = ChartExportService()
        formats = export_service.get_supported_formats()
        
        expected_formats = ["png", "pdf", "svg", "html"]
        for fmt in expected_formats:
            assert fmt in formats


class TestDashboardBuilderService:
    """Test dashboard builder service."""
    
    @pytest.mark.asyncio
    async def test_create_dashboard(
        self,
        sample_dashboard_configurations,
        mock_chart_generator
    ):
        """Test dashboard creation."""
        from app.services.dashboard_builder import DashboardBuilder
        
        builder = DashboardBuilder()
        dashboard_config = sample_dashboard_configurations[0]
        
        result = await builder.create_dashboard(dashboard_config)
        
        assert result is not None
        assert result["title"] == dashboard_config["title"]
        assert "layout_html" in result
        assert "panels" in result
        assert len(result["panels"]) == len(dashboard_config["panels"])
    
    @pytest.mark.asyncio
    async def test_add_panel_to_dashboard(
        self,
        mock_chart_generator
    ):
        """Test adding panel to existing dashboard."""
        from app.services.dashboard_builder import DashboardBuilder
        
        builder = DashboardBuilder()
        dashboard_id = "dashboard-123"
        
        panel_config = {
            "id": "new_panel",
            "title": "New Panel",
            "chart_config": {
                "chart_type": "bar",
                "x_field": "source",
                "y_field": "count"
            },
            "position": {"x": 1, "y": 1, "w": 1, "h": 1}
        }
        
        with patch.object(builder, 'get_dashboard') as mock_get:
            mock_get.return_value = {
                "dashboard_id": dashboard_id,
                "panels": []
            }
            
            result = await builder.add_panel(dashboard_id, panel_config)
            
            assert result is not None
            assert result["panel_id"] == "new_panel"
    
    def test_validate_dashboard_layout(self):
        """Test dashboard layout validation."""
        from app.services.dashboard_layout import DashboardLayoutValidator
        
        validator = DashboardLayoutValidator()
        
        valid_layout = {
            "type": "grid",
            "columns": 2,
            "rows": 2
        }
        
        result = validator.validate_layout(valid_layout)
        assert result["is_valid"] is True
        
        # Test invalid layout
        invalid_layout = {
            "type": "invalid_type"
        }
        
        result = validator.validate_layout(invalid_layout)
        assert result["is_valid"] is False
    
    @pytest.mark.asyncio
    async def test_optimize_dashboard_layout(self):
        """Test dashboard layout optimization."""
        from app.services.dashboard_layout import DashboardLayoutOptimizer
        
        optimizer = DashboardLayoutOptimizer()
        
        panels = [
            {"id": "panel1", "position": {"x": 0, "y": 0, "w": 1, "h": 1}},
            {"id": "panel2", "position": {"x": 1, "y": 0, "w": 1, "h": 1}},
            {"id": "panel3", "position": {"x": 0, "y": 1, "w": 2, "h": 1}}
        ]
        
        result = await optimizer.optimize_layout(panels)
        
        assert result is not None
        assert "optimized_panels" in result
        assert len(result["optimized_panels"]) == len(panels)


class TestInteractiveChartService:
    """Test interactive chart service."""
    
    @pytest.mark.asyncio
    async def test_add_chart_interactions(
        self,
        mock_plotly,
        sample_interactive_features
    ):
        """Test adding interactions to chart."""
        from app.services.interactive_charts import InteractiveChartService
        
        service = InteractiveChartService()
        mock_figure = mock_plotly["figure"]
        
        result = await service.add_interactions(
            chart_figure=mock_figure,
            interaction_config=sample_interactive_features
        )
        
        assert result is not None
        assert "interactive_html" in result
        assert "enabled_features" in result
        
        # Should have updated the figure with interactions
        mock_figure.update_layout.assert_called()
    
    def test_validate_interaction_config(self):
        """Test interaction configuration validation."""
        from app.services.interactive_charts import InteractiveChartService
        
        service = InteractiveChartService()
        
        valid_config = {
            "zoom": {"enabled": True, "type": "xy"},
            "hover": {"enabled": True}
        }
        
        result = service.validate_interaction_config(valid_config)
        assert result["is_valid"] is True
        
        # Test invalid config
        invalid_config = {
            "zoom": {"enabled": "invalid"}  # Should be boolean
        }
        
        result = service.validate_interaction_config(invalid_config)
        assert result["is_valid"] is False
    
    @pytest.mark.asyncio
    async def test_enable_crossfilter(
        self,
        mock_plotly
    ):
        """Test enabling crossfilter interactions."""
        from app.services.interactive_charts import InteractiveChartService
        
        service = InteractiveChartService()
        mock_figures = [mock_plotly["figure"], mock_plotly["figure"]]
        
        result = await service.enable_crossfilter(mock_figures)
        
        assert result is not None
        assert "crossfilter_enabled" in result
        assert result["crossfilter_enabled"] is True


class TestChartCustomizationService:
    """Test chart customization service."""
    
    @pytest.mark.asyncio
    async def test_apply_color_customization(
        self,
        mock_plotly
    ):
        """Test applying color customization."""
        from app.services.chart_customization import ChartCustomizationService
        
        service = ChartCustomizationService()
        mock_figure = mock_plotly["figure"]
        
        color_config = {
            "colors": {
                "primary": "#1f77b4",
                "secondary": "#ff7f0e",
                "background": "#ffffff"
            }
        }
        
        result = await service.apply_customization(
            chart_figure=mock_figure,
            customization_config=color_config
        )
        
        assert result is not None
        assert "customized_html" in result
        mock_figure.update_layout.assert_called()
    
    @pytest.mark.asyncio
    async def test_apply_font_customization(
        self,
        mock_plotly
    ):
        """Test applying font customization."""
        from app.services.chart_customization import ChartCustomizationService
        
        service = ChartCustomizationService()
        mock_figure = mock_plotly["figure"]
        
        font_config = {
            "fonts": {
                "title": {"family": "Arial", "size": 18, "color": "#333333"},
                "axes": {"family": "Arial", "size": 12, "color": "#666666"}
            }
        }
        
        result = await service.apply_customization(
            chart_figure=mock_figure,
            customization_config=font_config
        )
        
        assert result is not None
        mock_figure.update_layout.assert_called()
    
    def test_validate_customization_config(self):
        """Test customization configuration validation."""
        from app.services.chart_customization import ChartCustomizationService
        
        service = ChartCustomizationService()
        
        valid_config = {
            "colors": {"primary": "#1f77b4"},
            "fonts": {"title": {"family": "Arial", "size": 16}}
        }
        
        result = service.validate_customization_config(valid_config)
        assert result["is_valid"] is True


class TestCachingService:
    """Test caching functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_chart_result(
        self,
        mock_redis
    ):
        """Test caching chart generation results."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        
        chart_data = {
            "chart_id": "chart-123",
            "chart_html": "<div>Chart</div>",
            "metadata": {"chart_type": "line"}
        }
        
        cache_key = "chart_cache:chart-123"
        
        # Test cache miss
        mock_redis.get.return_value = None
        
        with patch.object(generator, '_generate_chart_internal') as mock_internal:
            mock_internal.return_value = chart_data
            
            result = await generator.generate_chart(
                data=[{"x": 1, "y": 2}],
                chart_type="line",
                title="Test Chart"
            )
            
            assert result == chart_data
            mock_redis.set.assert_called()  # Should cache result
    
    @pytest.mark.asyncio
    async def test_cache_hit_scenario(
        self,
        mock_redis
    ):
        """Test cache hit scenario."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        
        cached_data = {
            "chart_id": "chart-123",
            "chart_html": "<div>Cached Chart</div>",
            "metadata": {"chart_type": "line", "cached": True}
        }
        
        # Mock cache hit
        mock_redis.get.return_value = json.dumps(cached_data).encode()
        
        with patch.object(generator, '_generate_chart_internal') as mock_internal:
            result = await generator.generate_chart(
                data=[{"x": 1, "y": 2}],
                chart_type="line",
                title="Test Chart"
            )
            
            # Should return cached result without calling internal generation
            mock_internal.assert_not_called()
            assert result["metadata"]["cached"] is True


class TestErrorHandling:
    """Test error handling in services."""
    
    @pytest.mark.asyncio
    async def test_chart_generation_invalid_data_error(
        self,
        mock_plotly
    ):
        """Test error handling for invalid chart data."""
        from app.services.chart_generator import ChartGenerator
        
        generator = ChartGenerator()
        
        # Mock Plotly to raise an error
        mock_plotly["px"].line.side_effect = Exception("Invalid data format")
        
        with pytest.raises(Exception) as exc_info:
            await generator.generate_chart(
                data=[{"invalid": "data"}],
                chart_type="line",
                title="Test Chart"
            )
        
        assert "Invalid data format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_export_service_file_write_error(
        self,
        mock_plotly,
        mock_file_operations
    ):
        """Test error handling for file write errors during export."""
        from app.services.chart_export import ChartExportService
        
        export_service = ChartExportService()
        
        # Mock file write to fail
        def failing_write(path, content):
            raise PermissionError("Cannot write file")
        
        mock_file_operations["write_file"] = failing_write
        
        export_config = {"format": "png", "width": 800, "height": 600}
        
        with pytest.raises(Exception):
            await export_service.export_chart(
                chart_figure=mock_plotly["figure"],
                export_config=export_config
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])