"""
Test suite for chart export functionality

This module contains comprehensive tests for the chart export service,
including format-specific testing, quality settings, template configurations,
and batch export capabilities.
"""
import pytest
import io
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import plotly.graph_objects as go
from PIL import Image

from ..app.services.chart_export import ChartExportService
from ..app.models.chart import (
    ExportFormat, ExportQuality, ExportOrientation, ExportTemplate,
    ExportConfig, ExportResult, BatchExportRequest, BatchExportResult
)


class TestChartExportService:
    """Test suite for ChartExportService"""
    
    @pytest.fixture
    def export_service(self):
        """Create a ChartExportService instance for testing"""
        return ChartExportService()
    
    @pytest.fixture
    def sample_figure(self):
        """Create a sample Plotly figure for testing"""
        return go.Figure(data=[
            go.Scatter(x=[1, 2, 3, 4], y=[10, 11, 12, 13], name="Sample Data")
        ], layout=go.Layout(title="Test Chart", width=800, height=600))
    
    @pytest.fixture
    def basic_export_config(self):
        """Create a basic export configuration"""
        return ExportConfig(
            format=ExportFormat.PNG,
            quality=ExportQuality.HIGH,
            width=800,
            height=600,
            template=ExportTemplate.WEB
        )
    
    # Quality Settings Tests
    
    def test_quality_settings_initialization(self, export_service):
        """Test that quality settings are properly initialized"""
        assert ExportQuality.LOW in export_service.quality_settings
        assert ExportQuality.MEDIUM in export_service.quality_settings
        assert ExportQuality.HIGH in export_service.quality_settings
        assert ExportQuality.ULTRA in export_service.quality_settings
        
        # Test specific quality parameters
        low_quality = export_service.quality_settings[ExportQuality.LOW]
        assert low_quality['scale'] == 1.0
        assert low_quality['jpeg_quality'] == 60
        assert low_quality['png_compression'] == 9
        
        ultra_quality = export_service.quality_settings[ExportQuality.ULTRA]
        assert ultra_quality['scale'] == 3.0
        assert ultra_quality['jpeg_quality'] == 95
        assert ultra_quality['png_compression'] == 1
    
    def test_template_configs_initialization(self, export_service):
        """Test that template configurations are properly initialized"""
        assert ExportTemplate.PRESENTATION in export_service.template_configs
        assert ExportTemplate.PRINT in export_service.template_configs
        assert ExportTemplate.WEB in export_service.template_configs
        assert ExportTemplate.SOCIAL in export_service.template_configs
        assert ExportTemplate.REPORT in export_service.template_configs
        
        # Test specific template parameters
        presentation_template = export_service.template_configs[ExportTemplate.PRESENTATION]
        assert presentation_template['width'] == 1920
        assert presentation_template['height'] == 1080
        assert presentation_template['dpi'] == 300
        
        web_template = export_service.template_configs[ExportTemplate.WEB]
        assert web_template['width'] == 800
        assert web_template['height'] == 600
        assert web_template['dpi'] == 96
    
    # Template Configuration Tests
    
    def test_apply_template_config_web(self, export_service):
        """Test applying web template configuration"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            template=ExportTemplate.WEB
        )
        
        applied_config = export_service._apply_template_config(config)
        
        assert applied_config.width == 800
        assert applied_config.height == 600
        assert applied_config.dpi == 96
        assert applied_config.margin_top == 50
        assert applied_config.margin_bottom == 50
    
    def test_apply_template_config_presentation(self, export_service):
        """Test applying presentation template configuration"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            template=ExportTemplate.PRESENTATION
        )
        
        applied_config = export_service._apply_template_config(config)
        
        assert applied_config.width == 1920
        assert applied_config.height == 1080
        assert applied_config.dpi == 300
        assert applied_config.margin_top == 80
        assert applied_config.font_scale == 1.2
    
    def test_apply_template_config_custom_no_override(self, export_service):
        """Test that custom template doesn't override existing config"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            template=ExportTemplate.CUSTOM,
            width=1000,
            height=800
        )
        
        applied_config = export_service._apply_template_config(config)
        
        assert applied_config.width == 1000
        assert applied_config.height == 800
        assert applied_config.template == ExportTemplate.CUSTOM
    
    # Figure Preparation Tests
    
    def test_prepare_figure_for_export_dimensions(self, export_service, sample_figure):
        """Test figure preparation with custom dimensions"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            width=1200,
            height=900
        )
        
        prepared_fig = export_service._prepare_figure_for_export(sample_figure, config)
        
        assert prepared_fig.layout.width == 1200
        assert prepared_fig.layout.height == 900
    
    def test_prepare_figure_for_export_transparent_background(self, export_service, sample_figure):
        """Test figure preparation with transparent background"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            transparent_background=True
        )
        
        prepared_fig = export_service._prepare_figure_for_export(sample_figure, config)
        
        assert prepared_fig.layout.paper_bgcolor == 'rgba(0,0,0,0)'
        assert prepared_fig.layout.plot_bgcolor == 'rgba(0,0,0,0)'
    
    def test_prepare_figure_for_export_margins(self, export_service, sample_figure):
        """Test figure preparation with custom margins"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            margin_top=100,
            margin_bottom=80,
            margin_left=60,
            margin_right=60
        )
        
        prepared_fig = export_service._prepare_figure_for_export(sample_figure, config)
        
        assert prepared_fig.layout.margin.t == 100
        assert prepared_fig.layout.margin.b == 80
        assert prepared_fig.layout.margin.l == 60
        assert prepared_fig.layout.margin.r == 60
    
    def test_prepare_figure_for_export_font_scaling(self, export_service, sample_figure):
        """Test figure preparation with font scaling"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            font_scale=1.5
        )
        
        prepared_fig = export_service._prepare_figure_for_export(sample_figure, config)
        
        # Font size should be scaled from default 12 to 18
        assert prepared_fig.layout.font.size == 18
    
    def test_prepare_figure_for_export_hide_title_legend(self, export_service, sample_figure):
        """Test figure preparation with hidden title and legend"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            include_title=False,
            include_legend=False
        )
        
        prepared_fig = export_service._prepare_figure_for_export(sample_figure, config)
        
        assert prepared_fig.layout.title is None
        assert prepared_fig.layout.showlegend is False
    
    # Format-Specific Export Tests
    
    @patch('plotly.graph_objects.Figure.to_image')
    def test_export_png_basic(self, mock_to_image, export_service, sample_figure):
        """Test basic PNG export"""
        mock_to_image.return_value = b'fake_png_data'
        
        config = ExportConfig(format=ExportFormat.PNG, width=800, height=600)
        quality_settings = export_service.quality_settings[ExportQuality.HIGH]
        
        file_bytes, content_type = export_service._export_png(sample_figure, config, quality_settings)
        
        assert file_bytes == b'fake_png_data'
        assert content_type == "image/png"
        mock_to_image.assert_called_once_with(format="png", width=800, height=600, scale=2.0)
    
    @patch('plotly.graph_objects.Figure.to_image')
    @patch('PIL.Image.open')
    def test_export_png_with_optimization(self, mock_image_open, mock_to_image, export_service, sample_figure):
        """Test PNG export with optimization"""
        mock_to_image.return_value = b'fake_png_data'
        mock_image = Mock()
        mock_image_open.return_value = mock_image
        
        # Mock the save method to return optimized data
        def mock_save(buffer, format, **kwargs):
            buffer.write(b'optimized_png_data')
        
        mock_image.save = mock_save
        
        config = ExportConfig(format=ExportFormat.PNG, width=800, height=600, optimize=True)
        quality_settings = export_service.quality_settings[ExportQuality.HIGH]
        
        file_bytes, content_type = export_service._export_png(sample_figure, config, quality_settings)
        
        assert file_bytes == b'optimized_png_data'
        assert content_type == "image/png"
        mock_image.save.assert_called_once()
    
    @patch('plotly.graph_objects.Figure.to_image')
    @patch('PIL.Image.open')
    def test_export_jpeg_basic(self, mock_image_open, mock_to_image, export_service, sample_figure):
        """Test basic JPEG export"""
        mock_to_image.return_value = b'fake_png_data'
        mock_image = Mock()
        mock_image.mode = 'RGB'
        mock_image_open.return_value = mock_image
        
        # Mock the save method to return JPEG data
        def mock_save(buffer, format, **kwargs):
            buffer.write(b'fake_jpeg_data')
        
        mock_image.save = mock_save
        
        config = ExportConfig(format=ExportFormat.JPEG, width=800, height=600)
        quality_settings = export_service.quality_settings[ExportQuality.HIGH]
        
        file_bytes, content_type = export_service._export_jpeg(sample_figure, config, quality_settings)
        
        assert file_bytes == b'fake_jpeg_data'
        assert content_type == "image/jpeg"
    
    @patch('plotly.graph_objects.Figure.to_image')
    @patch('PIL.Image.open')
    def test_export_jpeg_with_transparency(self, mock_image_open, mock_to_image, export_service, sample_figure):
        """Test JPEG export with transparency handling"""
        mock_to_image.return_value = b'fake_png_data'
        
        # Mock RGBA image
        mock_image = Mock()
        mock_image.mode = 'RGBA'
        mock_image.size = (800, 600)
        mock_image.split.return_value = [Mock(), Mock(), Mock(), Mock()]  # R, G, B, A channels
        mock_image_open.return_value = mock_image
        
        # Mock background image creation
        mock_background = Mock()
        mock_background.paste = Mock()
        
        with patch('PIL.Image.new', return_value=mock_background):
            # Mock the save method
            def mock_save(buffer, format, **kwargs):
                buffer.write(b'fake_jpeg_data')
            
            mock_background.save = mock_save
            
            config = ExportConfig(format=ExportFormat.JPEG, width=800, height=600, background_color="#FFFFFF")
            quality_settings = export_service.quality_settings[ExportQuality.HIGH]
            
            file_bytes, content_type = export_service._export_jpeg(sample_figure, config, quality_settings)
            
            assert file_bytes == b'fake_jpeg_data'
            assert content_type == "image/jpeg"
            mock_background.paste.assert_called_once()
    
    @patch('plotly.graph_objects.Figure.to_image')
    @patch('PIL.Image.open')
    def test_export_webp_basic(self, mock_image_open, mock_to_image, export_service, sample_figure):
        """Test basic WebP export"""
        mock_to_image.return_value = b'fake_png_data'
        mock_image = Mock()
        mock_image_open.return_value = mock_image
        
        # Mock the save method to return WebP data
        def mock_save(buffer, format, **kwargs):
            buffer.write(b'fake_webp_data')
        
        mock_image.save = mock_save
        
        config = ExportConfig(format=ExportFormat.WEBP, width=800, height=600)
        quality_settings = export_service.quality_settings[ExportQuality.HIGH]
        
        file_bytes, content_type = export_service._export_webp(sample_figure, config, quality_settings)
        
        assert file_bytes == b'fake_webp_data'
        assert content_type == "image/webp"
    
    @patch('plotly.graph_objects.Figure.to_image')
    def test_export_pdf_basic(self, mock_to_image, export_service, sample_figure):
        """Test basic PDF export"""
        mock_to_image.return_value = b'fake_pdf_data'
        
        config = ExportConfig(format=ExportFormat.PDF, width=800, height=600)
        quality_settings = export_service.quality_settings[ExportQuality.HIGH]
        
        file_bytes, content_type = export_service._export_pdf(sample_figure, config, quality_settings)
        
        assert file_bytes == b'fake_pdf_data'
        assert content_type == "application/pdf"
        mock_to_image.assert_called_once_with(format="pdf", width=800, height=600)
    
    @patch('plotly.graph_objects.Figure.to_image')
    def test_export_svg_basic(self, mock_to_image, export_service, sample_figure):
        """Test basic SVG export"""
        mock_to_image.return_value = b'fake_svg_data'
        
        config = ExportConfig(format=ExportFormat.SVG, width=800, height=600)
        quality_settings = export_service.quality_settings[ExportQuality.HIGH]
        
        file_bytes, content_type = export_service._export_svg(sample_figure, config, quality_settings)
        
        assert file_bytes == b'fake_svg_data'
        assert content_type == "image/svg+xml"
    
    @patch('plotly.graph_objects.Figure.to_html')
    def test_export_html_basic(self, mock_to_html, export_service, sample_figure):
        """Test basic HTML export"""
        mock_to_html.return_value = '<html><body>Test Chart</body></html>'
        
        config = ExportConfig(format=ExportFormat.HTML, width=800, height=600)
        quality_settings = export_service.quality_settings[ExportQuality.HIGH]
        
        file_bytes, content_type = export_service._export_html(sample_figure, config, quality_settings)
        
        assert b'<html><body>Test Chart</body></html>' in file_bytes
        assert content_type == "text/html"
    
    @patch('plotly.graph_objects.Figure.to_html')
    def test_export_html_with_background_color(self, mock_to_html, export_service, sample_figure):
        """Test HTML export with custom background color"""
        mock_to_html.return_value = '<html><body>Test Chart</body></html>'
        
        config = ExportConfig(format=ExportFormat.HTML, width=800, height=600, background_color="#F0F0F0")
        quality_settings = export_service.quality_settings[ExportQuality.HIGH]
        
        file_bytes, content_type = export_service._export_html(sample_figure, config, quality_settings)
        
        html_content = file_bytes.decode('utf-8')
        assert 'background-color: #F0F0F0' in html_content
        assert content_type == "text/html"
    
    @patch('plotly.graph_objects.Figure.to_dict')
    def test_export_json_basic(self, mock_to_dict, export_service, sample_figure):
        """Test basic JSON export"""
        mock_to_dict.return_value = {'data': [{'x': [1, 2, 3], 'y': [4, 5, 6]}]}
        
        config = ExportConfig(format=ExportFormat.JSON, width=800, height=600)
        quality_settings = export_service.quality_settings[ExportQuality.HIGH]
        
        file_bytes, content_type = export_service._export_json(sample_figure, config, quality_settings)
        
        json_data = json.loads(file_bytes.decode('utf-8'))
        assert 'figure' in json_data
        assert 'config' in json_data
        assert 'metadata' in json_data
        assert content_type == "application/json"
    
    # Full Export Process Tests
    
    @patch('plotly.graph_objects.Figure.to_image')
    def test_export_chart_full_process(self, mock_to_image, export_service, sample_figure):
        """Test the full export chart process"""
        mock_to_image.return_value = b'fake_png_data'
        
        config = ExportConfig(
            format=ExportFormat.PNG,
            quality=ExportQuality.HIGH,
            width=800,
            height=600,
            template=ExportTemplate.WEB,
            include_metadata=True
        )
        
        result = export_service.export_chart(sample_figure, config, "test_chart_123")
        
        assert isinstance(result, ExportResult)
        assert result.chart_id == "test_chart_123"
        assert result.format == ExportFormat.PNG
        assert result.file_size > 0
        assert result.content_type == "image/png"
        assert result.export_time > 0
        assert result.config == config
        assert "chart_id" in result.metadata
        assert "export_timestamp" in result.metadata
    
    def test_export_chart_with_filename(self, export_service, sample_figure):
        """Test export chart with custom filename"""
        config = ExportConfig(format=ExportFormat.PNG, width=800, height=600)
        
        with patch('plotly.graph_objects.Figure.to_image', return_value=b'fake_png_data'):
            result = export_service.export_chart(sample_figure, config, "test_chart_123", "custom_chart.png")
        
        assert result.filename == "custom_chart.png"
    
    def test_export_chart_metadata_creation(self, export_service, sample_figure):
        """Test export chart metadata creation"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            quality=ExportQuality.HIGH,
            template=ExportTemplate.PRESENTATION,
            width=1920,
            height=1080,
            optimize=True,
            font_scale=1.2
        )
        
        metadata = export_service._create_export_metadata(sample_figure, config, "test_chart_123")
        
        assert metadata['chart_id'] == "test_chart_123"
        assert metadata['format'] == ExportFormat.PNG
        assert metadata['quality'] == ExportQuality.HIGH
        assert metadata['template'] == ExportTemplate.PRESENTATION
        assert metadata['dimensions']['width'] == 1920
        assert metadata['dimensions']['height'] == 1080
        assert metadata['figure_info']['trace_count'] == 1
        assert metadata['optimization']['optimize'] is True
        assert metadata['optimization']['font_scale'] == 1.2
    
    # Batch Export Tests
    
    @patch.object(ChartExportService, '_get_chart_figure')
    @patch.object(ChartExportService, 'export_chart')
    @patch.object(ChartExportService, '_create_archive')
    def test_batch_export_success(self, mock_create_archive, mock_export_chart, mock_get_chart_figure, export_service):
        """Test successful batch export"""
        # Mock dependencies
        mock_get_chart_figure.return_value = go.Figure()
        mock_export_result = ExportResult(
            export_id="export_123",
            chart_id="chart_123",
            format=ExportFormat.PNG,
            filename="chart_123.png",
            file_size=1024,
            content_type="image/png",
            export_time=0.5,
            config=ExportConfig(format=ExportFormat.PNG),
            metadata={}
        )
        mock_export_chart.return_value = mock_export_result
        mock_create_archive.return_value = 2048
        
        request = BatchExportRequest(
            charts=["chart_123", "chart_456"],
            format=ExportFormat.PNG,
            config=ExportConfig(format=ExportFormat.PNG),
            archive_format="zip"
        )
        
        result = export_service.batch_export(request)
        
        assert isinstance(result, BatchExportResult)
        assert result.total_charts == 2
        assert result.successful_exports == 2
        assert result.failed_exports == 0
        assert result.archive_size == 2048
        assert len(result.results) == 2
    
    @patch.object(ChartExportService, '_get_chart_figure')
    @patch.object(ChartExportService, 'export_chart')
    def test_batch_export_with_failures(self, mock_export_chart, mock_get_chart_figure, export_service):
        """Test batch export with some failures"""
        # Mock dependencies
        mock_get_chart_figure.return_value = go.Figure()
        
        # First export succeeds, second fails
        mock_export_result = ExportResult(
            export_id="export_123",
            chart_id="chart_123",
            format=ExportFormat.PNG,
            filename="chart_123.png",
            file_size=1024,
            content_type="image/png",
            export_time=0.5,
            config=ExportConfig(format=ExportFormat.PNG),
            metadata={}
        )
        mock_export_chart.side_effect = [mock_export_result, Exception("Export failed")]
        
        request = BatchExportRequest(
            charts=["chart_123", "chart_456"],
            format=ExportFormat.PNG,
            config=ExportConfig(format=ExportFormat.PNG),
            archive_format="zip"
        )
        
        with patch.object(export_service, '_create_archive', return_value=1024):
            result = export_service.batch_export(request)
        
        assert result.total_charts == 2
        assert result.successful_exports == 1
        assert result.failed_exports == 1
        assert len(result.results) == 1
    
    # Service Info Methods Tests
    
    def test_get_export_formats(self, export_service):
        """Test getting available export formats"""
        formats = export_service.get_export_formats()
        
        assert len(formats) == 7  # PNG, JPEG, WebP, PDF, SVG, HTML, JSON
        
        # Check PNG format info
        png_format = next((f for f in formats if f['format'] == ExportFormat.PNG), None)
        assert png_format is not None
        assert png_format['name'] == 'PNG'
        assert png_format['supports_transparency'] is True
        assert png_format['supports_animation'] is False
        assert 'web' in png_format['best_for']
    
    def test_get_quality_options(self, export_service):
        """Test getting available quality options"""
        quality_options = export_service.get_quality_options()
        
        assert len(quality_options) == 4  # LOW, MEDIUM, HIGH, ULTRA
        
        # Check high quality option
        high_quality = next((q for q in quality_options if q['quality'] == ExportQuality.HIGH), None)
        assert high_quality is not None
        assert high_quality['name'] == 'High'
        assert high_quality['scale'] == 2.0
        assert high_quality['dpi'] == 300
    
    def test_get_template_options(self, export_service):
        """Test getting available template options"""
        template_options = export_service.get_template_options()
        
        assert len(template_options) == 5  # WEB, PRINT, PRESENTATION, SOCIAL, REPORT
        
        # Check presentation template option
        presentation_template = next((t for t in template_options if t['template'] == ExportTemplate.PRESENTATION), None)
        assert presentation_template is not None
        assert presentation_template['name'] == 'Presentation'
        assert presentation_template['dimensions'] == '1920x1080'
        assert presentation_template['dpi'] == 300
    
    # Error Handling Tests
    
    def test_export_chart_invalid_format(self, export_service, sample_figure):
        """Test export chart with invalid format"""
        config = ExportConfig(format="invalid_format")
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            export_service.export_chart(sample_figure, config, "test_chart_123")
    
    @patch('plotly.graph_objects.Figure.to_image')
    def test_export_chart_plotly_error(self, mock_to_image, export_service, sample_figure):
        """Test export chart with Plotly error"""
        mock_to_image.side_effect = Exception("Plotly export failed")
        
        config = ExportConfig(format=ExportFormat.PNG, width=800, height=600)
        
        with pytest.raises(ValueError, match="Export failed"):
            export_service.export_chart(sample_figure, config, "test_chart_123")
    
    def test_export_chart_empty_figure(self, export_service):
        """Test export chart with empty figure"""
        empty_fig = go.Figure()
        config = ExportConfig(format=ExportFormat.PNG, width=800, height=600)
        
        with patch('plotly.graph_objects.Figure.to_image', return_value=b'empty_png_data'):
            result = export_service.export_chart(empty_fig, config, "test_chart_123")
        
        assert isinstance(result, ExportResult)
        assert result.chart_id == "test_chart_123"
        assert result.metadata['figure_info']['trace_count'] == 0