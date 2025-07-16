"""
Test suite for chart export API endpoints

This module tests the FastAPI endpoints for chart export functionality,
including advanced export, batch export, and export information endpoints.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from ..app.main import app
from ..app.models.chart import (
    ExportFormat, ExportQuality, ExportTemplate, ExportConfig,
    ExportResult, BatchExportRequest, BatchExportResult
)


class TestExportEndpoints:
    """Test suite for export API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_plotly_json(self):
        """Sample Plotly JSON for testing"""
        return json.dumps({
            "data": [
                {
                    "x": [1, 2, 3, 4],
                    "y": [10, 11, 12, 13],
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "Sample Data"
                }
            ],
            "layout": {
                "title": "Test Chart",
                "width": 800,
                "height": 600
            }
        })
    
    @pytest.fixture
    def sample_export_config(self):
        """Sample export configuration"""
        return {
            "format": "png",
            "quality": "high",
            "width": 800,
            "height": 600,
            "template": "web",
            "include_metadata": True,
            "transparent_background": False,
            "optimize": True
        }
    
    @pytest.fixture
    def sample_export_result(self):
        """Sample export result"""
        return ExportResult(
            export_id="test_export_123",
            chart_id="test_chart_123",
            format=ExportFormat.PNG,
            filename="test_chart.png",
            file_size=1024,
            content_type="image/png",
            export_time=0.5,
            config=ExportConfig(format=ExportFormat.PNG),
            metadata={"test": "metadata"}
        )
    
    # Legacy Export Endpoint Tests
    
    @patch('plotly.graph_objects.Figure.from_json')
    def test_export_chart_legacy_success(self, mock_from_json, client, sample_plotly_json):
        """Test successful legacy chart export"""
        mock_fig = Mock()
        mock_from_json.return_value = mock_fig
        
        with patch('app.services.chart_generator.ChartGenerator.export_chart') as mock_export:
            mock_export.return_value = (b'fake_png_data', 'image/png')
            
            response = client.post(
                "/charts/test_chart_123/export",
                params={
                    "format": "png",
                    "plotly_json": sample_plotly_json
                }
            )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert "attachment" in response.headers["content-disposition"]
        assert "chart_test_chart_123.png" in response.headers["content-disposition"]
    
    @patch('plotly.graph_objects.Figure.from_json')
    def test_export_chart_legacy_with_filename(self, mock_from_json, client, sample_plotly_json):
        """Test legacy chart export with custom filename"""
        mock_fig = Mock()
        mock_from_json.return_value = mock_fig
        
        with patch('app.services.chart_generator.ChartGenerator.export_chart') as mock_export:
            mock_export.return_value = (b'fake_png_data', 'image/png')
            
            response = client.post(
                "/charts/test_chart_123/export",
                params={
                    "format": "png",
                    "plotly_json": sample_plotly_json,
                    "filename": "custom_chart.png"
                }
            )
        
        assert response.status_code == 200
        assert "custom_chart.png" in response.headers["content-disposition"]
    
    @patch('plotly.graph_objects.Figure.from_json')
    def test_export_chart_legacy_error(self, mock_from_json, client, sample_plotly_json):
        """Test legacy chart export with error"""
        mock_from_json.side_effect = Exception("Invalid JSON")
        
        response = client.post(
            "/charts/test_chart_123/export",
            params={
                "format": "png",
                "plotly_json": sample_plotly_json
            }
        )
        
        assert response.status_code == 500
        assert "Chart export failed" in response.json()["detail"]
    
    # Advanced Export Endpoint Tests
    
    @patch('plotly.graph_objects.Figure.from_json')
    def test_export_chart_advanced_success(self, mock_from_json, client, sample_plotly_json, sample_export_config, sample_export_result):
        """Test successful advanced chart export"""
        mock_fig = Mock()
        mock_from_json.return_value = mock_fig
        
        with patch('app.services.chart_generator.ChartGenerator.export_chart_advanced') as mock_export:
            mock_export.return_value = sample_export_result
            
            response = client.post(
                "/charts/test_chart_123/export-advanced",
                json={
                    "plotly_json": sample_plotly_json,
                    "config": sample_export_config
                }
            )
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["export_id"] == "test_export_123"
        assert result["chart_id"] == "test_chart_123"
        assert result["format"] == "png"
        assert result["filename"] == "test_chart.png"
        assert result["file_size"] == 1024
        assert result["content_type"] == "image/png"
        assert result["export_time"] == 0.5
    
    @patch('plotly.graph_objects.Figure.from_json')
    def test_export_chart_advanced_with_filename(self, mock_from_json, client, sample_plotly_json, sample_export_config):
        """Test advanced chart export with custom filename"""
        mock_fig = Mock()
        mock_from_json.return_value = mock_fig
        
        custom_result = ExportResult(
            export_id="test_export_123",
            chart_id="test_chart_123",
            format=ExportFormat.PNG,
            filename="custom_chart.png",
            file_size=1024,
            content_type="image/png",
            export_time=0.5,
            config=ExportConfig(format=ExportFormat.PNG),
            metadata={}
        )
        
        with patch('app.services.chart_generator.ChartGenerator.export_chart_advanced') as mock_export:
            mock_export.return_value = custom_result
            
            response = client.post(
                "/charts/test_chart_123/export-advanced",
                json={
                    "plotly_json": sample_plotly_json,
                    "config": sample_export_config,
                    "filename": "custom_chart.png"
                }
            )
        
        assert response.status_code == 200
        result = response.json()
        assert result["filename"] == "custom_chart.png"
    
    @patch('plotly.graph_objects.Figure.from_json')
    def test_export_chart_advanced_error(self, mock_from_json, client, sample_plotly_json, sample_export_config):
        """Test advanced chart export with error"""
        mock_from_json.side_effect = Exception("Invalid JSON")
        
        response = client.post(
            "/charts/test_chart_123/export-advanced",
            json={
                "plotly_json": sample_plotly_json,
                "config": sample_export_config
            }
        )
        
        assert response.status_code == 500
        assert "Advanced chart export failed" in response.json()["detail"]
    
    # Advanced Export Download Endpoint Tests
    
    @patch('plotly.graph_objects.Figure.from_json')
    def test_download_advanced_export_success(self, mock_from_json, client, sample_plotly_json, sample_export_config, sample_export_result):
        """Test successful advanced export download"""
        mock_fig = Mock()
        mock_from_json.return_value = mock_fig
        
        with patch('app.services.chart_generator.ChartGenerator.export_chart_advanced') as mock_export_advanced:
            mock_export_advanced.return_value = sample_export_result
            
            with patch('app.services.chart_generator.ChartGenerator.export_chart') as mock_export:
                mock_export.return_value = (b'fake_png_data', 'image/png')
                
                response = client.post(
                    "/charts/test_chart_123/export-advanced/download",
                    json={
                        "plotly_json": sample_plotly_json,
                        "config": sample_export_config
                    }
                )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert "test_chart.png" in response.headers["content-disposition"]
        assert response.headers["x-export-id"] == "test_export_123"
        assert response.headers["x-export-time"] == "0.5"
    
    # Batch Export Endpoint Tests
    
    def test_batch_export_success(self, client):
        """Test successful batch export"""
        batch_request = {
            "charts": ["chart_123", "chart_456"],
            "format": "png",
            "config": {
                "format": "png",
                "quality": "high",
                "width": 800,
                "height": 600
            },
            "archive_format": "zip"
        }
        
        batch_result = BatchExportResult(
            batch_id="batch_123",
            total_charts=2,
            successful_exports=2,
            failed_exports=0,
            results=[],
            archive_size=2048,
            archive_filename="charts_export.zip",
            processing_time=1.5
        )
        
        with patch('app.services.chart_generator.ChartGenerator.batch_export_charts') as mock_batch_export:
            mock_batch_export.return_value = batch_result
            
            response = client.post(
                "/charts/batch-export",
                json=batch_request
            )
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["batch_id"] == "batch_123"
        assert result["total_charts"] == 2
        assert result["successful_exports"] == 2
        assert result["failed_exports"] == 0
        assert result["archive_size"] == 2048
        assert result["processing_time"] == 1.5
    
    def test_batch_export_with_failures(self, client):
        """Test batch export with some failures"""
        batch_request = {
            "charts": ["chart_123", "chart_456", "chart_789"],
            "format": "png",
            "config": {
                "format": "png",
                "quality": "high"
            },
            "archive_format": "zip"
        }
        
        batch_result = BatchExportResult(
            batch_id="batch_123",
            total_charts=3,
            successful_exports=2,
            failed_exports=1,
            results=[],
            archive_size=1024,
            archive_filename="charts_export.zip",
            processing_time=2.0
        )
        
        with patch('app.services.chart_generator.ChartGenerator.batch_export_charts') as mock_batch_export:
            mock_batch_export.return_value = batch_result
            
            response = client.post(
                "/charts/batch-export",
                json=batch_request
            )
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["failed_exports"] == 1
        assert result["successful_exports"] == 2
    
    def test_batch_export_error(self, client):
        """Test batch export with error"""
        batch_request = {
            "charts": ["chart_123"],
            "format": "png",
            "config": {
                "format": "png",
                "quality": "high"
            }
        }
        
        with patch('app.services.chart_generator.ChartGenerator.batch_export_charts') as mock_batch_export:
            mock_batch_export.side_effect = Exception("Batch export failed")
            
            response = client.post(
                "/charts/batch-export",
                json=batch_request
            )
        
        assert response.status_code == 500
        assert "Batch export failed" in response.json()["detail"]
    
    # Export Information Endpoint Tests
    
    def test_get_export_formats(self, client):
        """Test getting available export formats"""
        mock_formats = [
            {
                "format": "png",
                "name": "PNG",
                "description": "High-quality raster image format",
                "supports_transparency": True,
                "supports_animation": False,
                "best_for": ["web", "presentations"]
            },
            {
                "format": "pdf",
                "name": "PDF",
                "description": "Vector-based document format",
                "supports_transparency": False,
                "supports_animation": False,
                "best_for": ["printing", "documents"]
            }
        ]
        
        with patch('app.services.chart_generator.ChartGenerator.get_export_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_export_formats.return_value = mock_formats
            mock_get_service.return_value = mock_service
            
            response = client.get("/charts/export/formats")
        
        assert response.status_code == 200
        
        formats = response.json()
        assert len(formats) == 2
        assert formats[0]["format"] == "png"
        assert formats[0]["supports_transparency"] is True
        assert formats[1]["format"] == "pdf"
        assert formats[1]["supports_transparency"] is False
    
    def test_get_export_quality_options(self, client):
        """Test getting available export quality options"""
        mock_quality_options = [
            {
                "quality": "low",
                "name": "Low",
                "description": "Smallest file size",
                "scale": 1.0,
                "dpi": 150
            },
            {
                "quality": "high",
                "name": "High",
                "description": "High quality for most uses",
                "scale": 2.0,
                "dpi": 300
            }
        ]
        
        with patch('app.services.chart_generator.ChartGenerator.get_export_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_quality_options.return_value = mock_quality_options
            mock_get_service.return_value = mock_service
            
            response = client.get("/charts/export/quality-options")
        
        assert response.status_code == 200
        
        quality_options = response.json()
        assert len(quality_options) == 2
        assert quality_options[0]["quality"] == "low"
        assert quality_options[0]["scale"] == 1.0
        assert quality_options[1]["quality"] == "high"
        assert quality_options[1]["scale"] == 2.0
    
    def test_get_export_templates(self, client):
        """Test getting available export templates"""
        mock_templates = [
            {
                "template": "web",
                "name": "Web",
                "description": "Optimized for web display",
                "dimensions": "800x600",
                "dpi": 96
            },
            {
                "template": "print",
                "name": "Print",
                "description": "High-resolution for printing",
                "dimensions": "2480x3508",
                "dpi": 300
            }
        ]
        
        with patch('app.services.chart_generator.ChartGenerator.get_export_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_template_options.return_value = mock_templates
            mock_get_service.return_value = mock_service
            
            response = client.get("/charts/export/templates")
        
        assert response.status_code == 200
        
        templates = response.json()
        assert len(templates) == 2
        assert templates[0]["template"] == "web"
        assert templates[0]["dimensions"] == "800x600"
        assert templates[1]["template"] == "print"
        assert templates[1]["dimensions"] == "2480x3508"
    
    # Error Handling Tests
    
    def test_get_export_formats_error(self, client):
        """Test error handling for get export formats"""
        with patch('app.services.chart_generator.ChartGenerator.get_export_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_export_formats.side_effect = Exception("Service error")
            mock_get_service.return_value = mock_service
            
            response = client.get("/charts/export/formats")
        
        assert response.status_code == 500
        assert "Failed to retrieve export formats" in response.json()["detail"]
    
    def test_get_export_quality_options_error(self, client):
        """Test error handling for get quality options"""
        with patch('app.services.chart_generator.ChartGenerator.get_export_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_quality_options.side_effect = Exception("Service error")
            mock_get_service.return_value = mock_service
            
            response = client.get("/charts/export/quality-options")
        
        assert response.status_code == 500
        assert "Failed to retrieve quality options" in response.json()["detail"]
    
    def test_get_export_templates_error(self, client):
        """Test error handling for get templates"""
        with patch('app.services.chart_generator.ChartGenerator.get_export_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_template_options.side_effect = Exception("Service error")
            mock_get_service.return_value = mock_service
            
            response = client.get("/charts/export/templates")
        
        assert response.status_code == 500
        assert "Failed to retrieve export templates" in response.json()["detail"]
    
    # Validation Tests
    
    def test_advanced_export_invalid_config(self, client, sample_plotly_json):
        """Test advanced export with invalid configuration"""
        invalid_config = {
            "format": "invalid_format",
            "quality": "high"
        }
        
        response = client.post(
            "/charts/test_chart_123/export-advanced",
            json={
                "plotly_json": sample_plotly_json,
                "config": invalid_config
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_batch_export_empty_charts(self, client):
        """Test batch export with empty charts list"""
        batch_request = {
            "charts": [],
            "format": "png",
            "config": {
                "format": "png",
                "quality": "high"
            }
        }
        
        response = client.post(
            "/charts/batch-export",
            json=batch_request
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_legacy_export_missing_parameters(self, client):
        """Test legacy export with missing parameters"""
        response = client.post(
            "/charts/test_chart_123/export",
            params={}
        )
        
        assert response.status_code == 422  # Validation error
    
    # Health Check Test
    
    def test_health_check_includes_export_features(self, client):
        """Test that health check includes export features"""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        health_data = response.json()
        assert "capabilities" in health_data
        assert "export_features" in health_data["capabilities"]
        
        export_features = health_data["capabilities"]["export_features"]
        assert export_features["advanced_export"] is True
        assert export_features["batch_export"] is True
        assert "quality_levels" in export_features
        assert "export_templates" in export_features
        assert "format_specific_features" in export_features
        
        # Check specific format features
        format_features = export_features["format_specific_features"]
        assert "png" in format_features
        assert "transparency" in format_features["png"]
        assert "jpeg" in format_features
        assert "quality" in format_features["jpeg"]