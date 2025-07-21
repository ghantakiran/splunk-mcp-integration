#!/usr/bin/env python3
"""
Comprehensive API endpoint tests for Visualization Service.

This module tests all API endpoints including chart generation, dashboard
management, exports, customization, and error handling.
"""

import pytest
import json
from typing import Dict, Any
from unittest.mock import AsyncMock, patch, Mock
from fastapi import status
import base64

from .conftest import (
    assert_chart_structure, 
    assert_dashboard_structure,
    generate_mock_image_data,
    create_mock_chart_html
)


class TestChartGenerationEndpoints:
    """Test chart generation API endpoints."""
    
    def test_generate_chart_success(
        self, 
        test_client, 
        auth_headers,
        sample_chart_data,
        sample_chart_configurations,
        mock_chart_generator
    ):
        """Test successful chart generation."""
        request_data = {
            "data": sample_chart_data,
            **sample_chart_configurations[0]  # Line chart config
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert assert_chart_structure(data)
        assert data["chart_id"] is not None
        assert "chart_html" in data
        assert data["metadata"]["chart_type"] == "line"
    
    def test_generate_bar_chart(
        self, 
        test_client, 
        auth_headers,
        sample_chart_data,
        sample_chart_configurations,
        mock_chart_generator
    ):
        """Test bar chart generation."""
        request_data = {
            "data": sample_chart_data,
            **sample_chart_configurations[1]  # Bar chart config
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["metadata"]["chart_type"] == "bar"
        mock_chart_generator.generate_chart.assert_called_once()
    
    def test_generate_pie_chart(
        self, 
        test_client, 
        auth_headers,
        sample_chart_data,
        sample_chart_configurations,
        mock_chart_generator
    ):
        """Test pie chart generation."""
        request_data = {
            "data": sample_chart_data,
            **sample_chart_configurations[2]  # Pie chart config
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["metadata"]["chart_type"] == "pie"
        # Should have aggregated data for pie chart
        assert "value_field" in str(request_data)
    
    def test_generate_heatmap_chart(
        self, 
        test_client, 
        auth_headers,
        sample_chart_data,
        sample_chart_configurations,
        mock_chart_generator
    ):
        """Test heatmap chart generation."""
        request_data = {
            "data": sample_chart_data,
            **sample_chart_configurations[3]  # Heatmap config
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["metadata"]["chart_type"] == "heatmap"
    
    def test_generate_scatter_chart(
        self, 
        test_client, 
        auth_headers,
        sample_chart_data,
        sample_chart_configurations,
        mock_chart_generator
    ):
        """Test scatter chart generation."""
        # Add required fields for scatter plot
        scatter_data = []
        for item in sample_chart_data:
            scatter_data.append({
                **item,
                "load": item["count"] * 0.8,
                "response_time": item["count"] * 2.5
            })
        
        request_data = {
            "data": scatter_data,
            **sample_chart_configurations[4]  # Scatter config
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["metadata"]["chart_type"] == "scatter"
    
    def test_generate_chart_invalid_data(
        self, 
        test_client, 
        auth_headers,
        sample_chart_configurations
    ):
        """Test chart generation with invalid data."""
        request_data = {
            "data": [],  # Empty data
            **sample_chart_configurations[0]
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_generate_chart_missing_fields(
        self, 
        test_client, 
        auth_headers,
        sample_chart_data
    ):
        """Test chart generation with missing required fields."""
        request_data = {
            "data": sample_chart_data
            # Missing chart_type and other required fields
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_generate_chart_unauthorized(
        self, 
        test_client,
        sample_chart_data,
        sample_chart_configurations
    ):
        """Test chart generation without authentication."""
        request_data = {
            "data": sample_chart_data,
            **sample_chart_configurations[0]
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            json=request_data
            # No auth headers
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestChartCustomizationEndpoints:
    """Test chart customization API endpoints."""
    
    def test_customize_chart_colors(
        self, 
        test_client, 
        auth_headers,
        sample_customization_options
    ):
        """Test chart color customization."""
        chart_id = "test-chart-123"
        customization_data = {
            "colors": sample_customization_options["colors"]
        }
        
        with patch('app.services.chart_customization.ChartCustomizationService') as mock_service:
            mock_service.return_value.apply_customization.return_value = {
                "chart_id": chart_id,
                "customized_html": "<div>Customized Chart</div>",
                "applied_options": customization_data
            }
            
            response = test_client.post(
                f"/api/v1/charts/{chart_id}/customize",
                headers=auth_headers,
                json=customization_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["chart_id"] == chart_id
        assert "customized_html" in data
    
    def test_customize_chart_fonts(
        self, 
        test_client, 
        auth_headers,
        sample_customization_options
    ):
        """Test chart font customization."""
        chart_id = "test-chart-123"
        customization_data = {
            "fonts": sample_customization_options["fonts"]
        }
        
        with patch('app.services.chart_customization.ChartCustomizationService') as mock_service:
            mock_service.return_value.apply_customization.return_value = {
                "chart_id": chart_id,
                "customized_html": "<div>Font Customized Chart</div>",
                "applied_options": customization_data
            }
            
            response = test_client.post(
                f"/api/v1/charts/{chart_id}/customize",
                headers=auth_headers,
                json=customization_data
            )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_customize_chart_layout(
        self, 
        test_client, 
        auth_headers,
        sample_customization_options
    ):
        """Test chart layout customization."""
        chart_id = "test-chart-123"
        customization_data = {
            "layout": sample_customization_options["layout"],
            "axes": sample_customization_options["axes"]
        }
        
        with patch('app.services.chart_customization.ChartCustomizationService') as mock_service:
            mock_service.return_value.apply_customization.return_value = {
                "chart_id": chart_id,
                "customized_html": "<div>Layout Customized Chart</div>",
                "applied_options": customization_data
            }
            
            response = test_client.post(
                f"/api/v1/charts/{chart_id}/customize",
                headers=auth_headers,
                json=customization_data
            )
        
        assert response.status_code == status.HTTP_200_OK


class TestInteractiveChartEndpoints:
    """Test interactive chart feature endpoints."""
    
    def test_enable_chart_interactions(
        self, 
        test_client, 
        auth_headers,
        sample_interactive_features
    ):
        """Test enabling chart interactions."""
        chart_id = "test-chart-123"
        
        with patch('app.services.interactive_charts.InteractiveChartService') as mock_service:
            mock_service.return_value.add_interactions.return_value = {
                "chart_id": chart_id,
                "interactive_html": "<div>Interactive Chart</div>",
                "enabled_features": sample_interactive_features
            }
            
            response = test_client.post(
                f"/api/v1/charts/{chart_id}/interactions",
                headers=auth_headers,
                json=sample_interactive_features
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["chart_id"] == chart_id
        assert "interactive_html" in data
        assert "enabled_features" in data
    
    def test_get_chart_interactions(
        self, 
        test_client, 
        auth_headers,
        sample_interactive_features
    ):
        """Test getting chart interaction configuration."""
        chart_id = "test-chart-123"
        
        with patch('app.services.interactive_charts.InteractiveChartService') as mock_service:
            mock_service.return_value.get_interactions.return_value = {
                "chart_id": chart_id,
                "enabled_features": sample_interactive_features,
                "interaction_config": {
                    "zoom_enabled": True,
                    "pan_enabled": True,
                    "hover_enabled": True
                }
            }
            
            response = test_client.get(
                f"/api/v1/charts/{chart_id}/interactions",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["chart_id"] == chart_id
        assert "enabled_features" in data


class TestChartExportEndpoints:
    """Test chart export API endpoints."""
    
    def test_export_chart_png(
        self, 
        test_client, 
        auth_headers,
        sample_export_configurations,
        mock_chart_export
    ):
        """Test PNG chart export."""
        chart_id = "test-chart-123"
        export_config = sample_export_configurations[0]  # PNG config
        
        response = test_client.post(
            f"/api/v1/charts/{chart_id}/export",
            headers=auth_headers,
            json=export_config
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["format"] == "png"
        assert "export_id" in data
        assert "file_path" in data
        mock_chart_export.export_chart.assert_called_once()
    
    def test_export_chart_pdf(
        self, 
        test_client, 
        auth_headers,
        sample_export_configurations,
        mock_chart_export
    ):
        """Test PDF chart export."""
        chart_id = "test-chart-123"
        export_config = sample_export_configurations[1]  # PDF config
        
        response = test_client.post(
            f"/api/v1/charts/{chart_id}/export",
            headers=auth_headers,
            json=export_config
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["format"] == "pdf"
        assert "export_id" in data
    
    def test_export_chart_svg(
        self, 
        test_client, 
        auth_headers,
        sample_export_configurations,
        mock_chart_export
    ):
        """Test SVG chart export."""
        chart_id = "test-chart-123"
        export_config = sample_export_configurations[2]  # SVG config
        
        response = test_client.post(
            f"/api/v1/charts/{chart_id}/export",
            headers=auth_headers,
            json=export_config
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["format"] == "svg"
    
    def test_export_chart_html(
        self, 
        test_client, 
        auth_headers,
        sample_export_configurations,
        mock_chart_export
    ):
        """Test HTML chart export."""
        chart_id = "test-chart-123"
        export_config = sample_export_configurations[3]  # HTML config
        
        response = test_client.post(
            f"/api/v1/charts/{chart_id}/export",
            headers=auth_headers,
            json=export_config
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["format"] == "html"
        assert data["metadata"]["interactive"] is True
    
    def test_download_exported_chart(
        self, 
        test_client, 
        auth_headers,
        mock_file_operations
    ):
        """Test downloading exported chart file."""
        export_id = "export-123"
        
        # Create mock file
        mock_content = generate_mock_image_data("png")
        mock_file_operations["write_file"]("chart.png", mock_content)
        
        with patch('app.api.v1.endpoints.get_export_file_path') as mock_get_path:
            mock_get_path.return_value = os.path.join(mock_file_operations["temp_dir"], "chart.png")
            
            response = test_client.get(
                f"/api/v1/charts/exports/{export_id}/download",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("image/")
    
    def test_get_export_formats(
        self, 
        test_client, 
        auth_headers,
        mock_chart_export
    ):
        """Test getting supported export formats."""
        response = test_client.get(
            "/api/v1/charts/export/formats",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "formats" in data
        expected_formats = ["png", "pdf", "svg", "html"]
        for fmt in expected_formats:
            assert fmt in data["formats"]


class TestDashboardEndpoints:
    """Test dashboard management API endpoints."""
    
    def test_create_dashboard(
        self, 
        test_client, 
        auth_headers,
        sample_dashboard_configurations,
        mock_dashboard_builder
    ):
        """Test dashboard creation."""
        dashboard_config = sample_dashboard_configurations[0]
        
        response = test_client.post(
            "/api/v1/dashboards",
            headers=auth_headers,
            json=dashboard_config
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert assert_dashboard_structure(data)
        assert data["title"] == dashboard_config["title"]
        assert len(data["panels"]) == len(dashboard_config["panels"])
        mock_dashboard_builder.create_dashboard.assert_called_once()
    
    def test_get_dashboard(
        self, 
        test_client, 
        auth_headers,
        mock_dashboard_builder
    ):
        """Test getting dashboard by ID."""
        dashboard_id = "dashboard-123"
        
        mock_dashboard_builder.get_dashboard.return_value = {
            "dashboard_id": dashboard_id,
            "title": "Test Dashboard",
            "layout_html": "<div>Dashboard Content</div>",
            "panels": [{"panel_id": "panel1"}]
        }
        
        response = test_client.get(
            f"/api/v1/dashboards/{dashboard_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["dashboard_id"] == dashboard_id
        assert data["title"] == "Test Dashboard"
    
    def test_update_dashboard(
        self, 
        test_client, 
        auth_headers,
        mock_dashboard_builder
    ):
        """Test dashboard update."""
        dashboard_id = "dashboard-123"
        update_data = {
            "title": "Updated Dashboard Title",
            "refresh_interval": 600
        }
        
        mock_dashboard_builder.update_dashboard.return_value = {
            "dashboard_id": dashboard_id,
            "title": "Updated Dashboard Title",
            "updated_fields": ["title", "refresh_interval"]
        }
        
        response = test_client.put(
            f"/api/v1/dashboards/{dashboard_id}",
            headers=auth_headers,
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["title"] == update_data["title"]
    
    def test_delete_dashboard(
        self, 
        test_client, 
        auth_headers,
        mock_dashboard_builder
    ):
        """Test dashboard deletion."""
        dashboard_id = "dashboard-123"
        
        mock_dashboard_builder.delete_dashboard.return_value = {
            "dashboard_id": dashboard_id,
            "deleted": True
        }
        
        response = test_client.delete(
            f"/api/v1/dashboards/{dashboard_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["deleted"] is True
    
    def test_list_dashboards(
        self, 
        test_client, 
        auth_headers,
        mock_dashboard_builder
    ):
        """Test listing user dashboards."""
        mock_dashboard_builder.list_dashboards.return_value = {
            "dashboards": [
                {"dashboard_id": "dash1", "title": "Dashboard 1"},
                {"dashboard_id": "dash2", "title": "Dashboard 2"}
            ],
            "total": 2,
            "page": 1,
            "per_page": 10
        }
        
        response = test_client.get(
            "/api/v1/dashboards",
            headers=auth_headers,
            params={"page": 1, "per_page": 10}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["dashboards"]) == 2
        assert data["total"] == 2


class TestHealthEndpoints:
    """Test health and monitoring endpoints."""
    
    def test_health_check(self, test_client):
        """Test basic health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_ready_check(self, test_client):
        """Test readiness probe endpoint."""
        response = test_client.get("/ready")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["ready"] is True
        assert "dependencies" in data


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_chart_not_found(
        self, 
        test_client, 
        auth_headers
    ):
        """Test accessing non-existent chart."""
        non_existent_id = "non-existent-chart"
        
        response = test_client.get(
            f"/api/v1/charts/{non_existent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_dashboard_not_found(
        self, 
        test_client, 
        auth_headers
    ):
        """Test accessing non-existent dashboard."""
        non_existent_id = "non-existent-dashboard"
        
        response = test_client.get(
            f"/api/v1/dashboards/{non_existent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_invalid_chart_type(
        self, 
        test_client, 
        auth_headers,
        sample_chart_data
    ):
        """Test chart generation with invalid chart type."""
        request_data = {
            "data": sample_chart_data,
            "chart_type": "invalid_chart_type",
            "title": "Test Chart"
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json=request_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_rate_limiting(
        self, 
        test_client, 
        auth_headers,
        sample_chart_data,
        sample_chart_configurations
    ):
        """Test rate limiting enforcement."""
        request_data = {
            "data": sample_chart_data,
            **sample_chart_configurations[0]
        }
        
        # Mock rate limiting
        with patch('app.utils.rate_limiter.check_rate_limit') as mock_limiter:
            mock_limiter.return_value = False  # Rate limit exceeded
            
            response = test_client.post(
                "/api/v1/charts/generate",
                headers=auth_headers,
                json=request_data
            )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    def test_large_dataset_handling(
        self, 
        test_client, 
        auth_headers,
        sample_chart_configurations
    ):
        """Test handling of very large datasets."""
        # Create large dataset
        large_data = [
            {"_time": f"2024-01-01T{i:02d}:00:00", "count": i * 10}
            for i in range(10000)  # 10k data points
        ]
        
        request_data = {
            "data": large_data,
            **sample_chart_configurations[0]
        }
        
        response = test_client.post(
            "/api/v1/charts/generate",
            headers=auth_headers,
            json=request_data
        )
        
        # Should either handle gracefully or return appropriate error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


class TestConcurrency:
    """Test concurrent request handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_chart_generation(
        self, 
        async_client, 
        auth_headers,
        sample_chart_data,
        sample_chart_configurations,
        mock_chart_generator
    ):
        """Test handling of concurrent chart generation requests."""
        import asyncio
        
        request_data = {
            "data": sample_chart_data,
            **sample_chart_configurations[0]
        }
        
        # Send multiple concurrent requests
        tasks = []
        for _ in range(5):
            task = async_client.post(
                "/api/v1/charts/generate",
                headers=auth_headers,
                json=request_data
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed or fail gracefully
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [
                    status.HTTP_200_OK, 
                    status.HTTP_429_TOO_MANY_REQUESTS
                ]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])