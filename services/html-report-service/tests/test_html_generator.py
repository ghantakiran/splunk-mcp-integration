#!/usr/bin/env python3
"""
Tests for HTML Generator Service.

This module contains comprehensive tests for the HTML report generator,
including report generation, template rendering, and format conversion.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

from app.models.html_models import (
    JobStatus,
    OutputFormat,
    Template,
    ChartType,
    ColorScheme,
    InteractiveFeature
)


class TestHTMLReportGenerator:
    """Test cases for HTML report generator initialization and configuration."""
    
    @pytest.fixture
    def generator(self, mock_settings, mock_jinja_env):
        """Create HTML report generator instance."""
        with patch('app.services.html_generator.Environment') as mock_env_class:
            mock_env_class.return_value = mock_jinja_env
            
            from app.services.html_generator import HTMLReportGenerator
            return HTMLReportGenerator()
    
    def test_generator_initialization(self, generator):
        """Test generator initialization."""
        assert generator is not None
        assert hasattr(generator, 'jinja_env')
        assert hasattr(generator, 'plotly_chart_types')
        assert hasattr(generator, 'color_schemes')
    
    def test_chart_type_mappings(self, generator):
        """Test chart type mappings."""
        assert ChartType.BAR in generator.plotly_chart_types
        assert ChartType.LINE in generator.plotly_chart_types
        assert ChartType.PIE in generator.plotly_chart_types
        assert generator.plotly_chart_types[ChartType.BAR] == "bar"
        assert generator.plotly_chart_types[ChartType.LINE] == "scatter"
        assert generator.plotly_chart_types[ChartType.PIE] == "pie"
    
    def test_color_schemes(self, generator):
        """Test color scheme configurations."""
        assert ColorScheme.BLUE in generator.color_schemes
        assert ColorScheme.RED in generator.color_schemes
        assert isinstance(generator.color_schemes[ColorScheme.BLUE], list)
        assert len(generator.color_schemes[ColorScheme.BLUE]) > 0


class TestReportGeneration:
    """Test cases for main report generation functionality."""
    
    @pytest.fixture
    def generator(self, mock_settings, mock_jinja_env):
        """Create HTML report generator instance."""
        with patch('app.services.html_generator.Environment') as mock_env_class:
            mock_env_class.return_value = mock_jinja_env
            
            from app.services.html_generator import HTMLReportGenerator
            return HTMLReportGenerator()
    
    @pytest.mark.asyncio
    async def test_generate_report_success(
        self,
        generator,
        sample_report_config,
        sample_data_source,
        mock_file_operations,
        mock_database
    ):
        """Test successful report generation."""
        job_id = 123
        user_id = 456
        
        with patch.object(generator, '_update_job_status', new_callable=AsyncMock) as mock_update_status, \
             patch.object(generator, '_update_job_completion', new_callable=AsyncMock) as mock_update_completion, \
             patch.object(generator, '_fetch_data', new_callable=AsyncMock) as mock_fetch_data, \
             patch.object(generator, '_create_html_report', new_callable=AsyncMock) as mock_create_html, \
             patch.object(generator, '_save_html_file', new_callable=AsyncMock) as mock_save_file:
            
            # Setup mocks
            mock_fetch_data.return_value = {"test": "data"}
            mock_create_html.return_value = "<html><body>Test Report</body></html>"
            
            # Execute
            success, file_path, error = await generator.generate_report(
                job_id=job_id,
                user_id=user_id,
                report_config=sample_report_config,
                data_source=sample_data_source.dict(),
                output_format=OutputFormat.HTML
            )
            
            # Verify
            assert success is True
            assert file_path is not None
            assert error is None
            
            # Verify status updates
            mock_update_status.assert_called_once()
            mock_update_completion.assert_called_once()
            
            # Verify data processing
            mock_fetch_data.assert_called_once_with(sample_data_source.dict())
            mock_create_html.assert_called_once()
            mock_save_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_report_failure(
        self,
        generator,
        sample_report_config,
        sample_data_source
    ):
        """Test report generation failure handling."""
        job_id = 123
        user_id = 456
        
        with patch.object(generator, '_update_job_status', new_callable=AsyncMock) as mock_update_status, \
             patch.object(generator, '_fetch_data', new_callable=AsyncMock) as mock_fetch_data:
            
            # Setup failure
            mock_fetch_data.side_effect = Exception("Test error")
            
            # Execute
            success, file_path, error = await generator.generate_report(
                job_id=job_id,
                user_id=user_id,
                report_config=sample_report_config,
                data_source=sample_data_source.dict(),
                output_format=OutputFormat.HTML
            )
            
            # Verify
            assert success is False
            assert file_path is None
            assert error == "Test error"
            
            # Verify error status update
            assert mock_update_status.call_count == 2  # Processing + Failed


class TestChartGeneration:
    """Test cases for chart generation functionality."""
    
    @pytest.fixture
    def generator(self, mock_settings, mock_jinja_env):
        """Create HTML report generator instance."""
        with patch('app.services.html_generator.Environment') as mock_env_class:
            mock_env_class.return_value = mock_jinja_env
            
            from app.services.html_generator import HTMLReportGenerator
            return HTMLReportGenerator()
    
    @pytest.mark.asyncio
    async def test_create_chart_html_bar_chart(self, generator, sample_chart):
        """Test bar chart HTML generation."""
        # Update chart type to bar
        sample_chart.config.chart_type = ChartType.BAR
        sample_chart.config.interactive_features = [InteractiveFeature.ZOOM, InteractiveFeature.HOVER]
        
        with patch.object(generator, '_generate_chart_interactions', new_callable=AsyncMock) as mock_interactions:
            mock_interactions.return_value = "// Test interactions"
            
            result = await generator._create_chart_html(sample_chart, {"test": "data"})
            
            assert isinstance(result, str)
            assert f"chart-{sample_chart.id}" in result
            assert "Plotly.newPlot" in result
            assert "var data" in result
            assert "var layout" in result
            assert "var config" in result
    
    @pytest.mark.asyncio
    async def test_create_chart_html_line_chart(self, generator, sample_chart):
        """Test line chart HTML generation."""
        sample_chart.config.chart_type = ChartType.LINE
        
        with patch.object(generator, '_generate_chart_interactions', new_callable=AsyncMock) as mock_interactions:
            mock_interactions.return_value = ""
            
            result = await generator._create_chart_html(sample_chart, {"test": "data"})
            
            assert isinstance(result, str)
            assert "mode" in result  # Line charts should have mode configuration
    
    @pytest.mark.asyncio
    async def test_create_chart_html_pie_chart(self, generator, sample_chart):
        """Test pie chart HTML generation."""
        sample_chart.config.chart_type = ChartType.PIE
        
        with patch.object(generator, '_generate_chart_interactions', new_callable=AsyncMock) as mock_interactions:
            mock_interactions.return_value = ""
            
            result = await generator._create_chart_html(sample_chart, {"test": "data"})
            
            assert isinstance(result, str)
            assert "pie" in result.lower()
    
    @pytest.mark.asyncio
    async def test_generate_chart_interactions(self, generator, sample_chart):
        """Test chart interaction generation."""
        sample_chart.config.interactive_features = [
            InteractiveFeature.CLICK,
            InteractiveFeature.HOVER,
            InteractiveFeature.BRUSH
        ]
        
        result = await generator._generate_chart_interactions(sample_chart)
        
        assert isinstance(result, str)
        assert "plotly_click" in result
        assert "plotly_hover" in result
        assert "plotly_selected" in result


class TestTableGeneration:
    """Test cases for table generation functionality."""
    
    @pytest.fixture
    def generator(self, mock_settings, mock_jinja_env):
        """Create HTML report generator instance."""
        with patch('app.services.html_generator.Environment') as mock_env_class:
            mock_env_class.return_value = mock_jinja_env
            
            from app.services.html_generator import HTMLReportGenerator
            return HTMLReportGenerator()
    
    @pytest.mark.asyncio
    async def test_create_table_html(self, generator, sample_table):
        """Test table HTML generation."""
        with patch.object(generator, '_generate_table_rows', new_callable=AsyncMock) as mock_rows:
            mock_rows.return_value = "<tr><td>Test</td><td>Data</td></tr>"
            
            result = await generator._create_table_html(sample_table)
            
            assert isinstance(result, str)
            assert f"table-{sample_table.id}" in result
            assert "DataTable" in result
            assert "thead" in result
            assert "tbody" in result
            assert sample_table.config.title in result or "table" in result.lower()
    
    @pytest.mark.asyncio
    async def test_generate_table_rows(self, generator, sample_table):
        """Test table row generation."""
        result = await generator._generate_table_rows(sample_table)
        
        assert isinstance(result, str)
        assert "<tr>" in result
        assert "<td>" in result
        assert str(sample_table.data[0]["sales"]) in result
        assert sample_table.data[0]["region"] in result
    
    @pytest.mark.asyncio
    async def test_table_with_export_buttons(self, generator, sample_table):
        """Test table with export buttons."""
        sample_table.config.export_buttons = ["copy", "csv", "excel", "pdf"]
        
        with patch.object(generator, '_generate_table_rows', new_callable=AsyncMock) as mock_rows:
            mock_rows.return_value = "<tr><td>Test</td></tr>"
            
            result = await generator._create_table_html(sample_table)
            
            assert "buttons" in result
            assert "copy" in result
            assert "csv" in result


class TestTemplateHandling:
    """Test cases for template loading and rendering."""
    
    @pytest.fixture
    def generator(self, mock_settings, mock_jinja_env):
        """Create HTML report generator instance."""
        with patch('app.services.html_generator.Environment') as mock_env_class:
            mock_env_class.return_value = mock_jinja_env
            
            from app.services.html_generator import HTMLReportGenerator
            return HTMLReportGenerator()
    
    @pytest.mark.asyncio
    async def test_load_template_success(self, generator, mock_jinja_template):
        """Test successful template loading."""
        generator.jinja_env.get_template.return_value = mock_jinja_template
        
        template = await generator._load_template(Template.MODERN)
        
        assert template == mock_jinja_template
        generator.jinja_env.get_template.assert_called_with("modern.html")
    
    @pytest.mark.asyncio
    async def test_load_template_fallback(self, generator, mock_jinja_template):
        """Test template loading with fallback."""
        # First call fails, second succeeds (fallback)
        generator.jinja_env.get_template.side_effect = [Exception("Template not found"), mock_jinja_template]
        
        template = await generator._load_template(Template.CORPORATE)
        
        assert template == mock_jinja_template
        assert generator.jinja_env.get_template.call_count == 2
    
    @pytest.mark.asyncio
    async def test_create_html_report(
        self,
        generator,
        sample_report_config,
        sample_chart,
        sample_table,
        mock_jinja_template
    ):
        """Test complete HTML report creation."""
        # Add chart and table to config
        sample_report_config.charts = [sample_chart]
        sample_report_config.tables = [sample_table]
        
        data = {"test": "data"}
        job_id = 123
        
        with patch.object(generator, '_load_template', new_callable=AsyncMock) as mock_load_template, \
             patch.object(generator, '_create_chart_html', new_callable=AsyncMock) as mock_create_chart, \
             patch.object(generator, '_create_table_html', new_callable=AsyncMock) as mock_create_table, \
             patch.object(generator, '_create_section_html', new_callable=AsyncMock) as mock_create_section:
            
            # Setup mocks
            mock_load_template.return_value = mock_jinja_template
            mock_create_chart.return_value = "<div>Chart HTML</div>"
            mock_create_table.return_value = "<div>Table HTML</div>"
            mock_create_section.return_value = "<div>Section HTML</div>"
            
            result = await generator._create_html_report(sample_report_config, data, job_id)
            
            assert isinstance(result, str)
            mock_jinja_template.render.assert_called_once()
            
            # Verify context passed to template
            render_args = mock_jinja_template.render.call_args[1]
            assert "metadata" in render_args
            assert "sections" in render_args
            assert "job_id" in render_args
            assert render_args["job_id"] == job_id


class TestDataSourceHandling:
    """Test cases for data source processing."""
    
    @pytest.fixture
    def generator(self, mock_settings, mock_jinja_env):
        """Create HTML report generator instance."""
        with patch('app.services.html_generator.Environment') as mock_env_class:
            mock_env_class.return_value = mock_jinja_env
            
            from app.services.html_generator import HTMLReportGenerator
            return HTMLReportGenerator()
    
    @pytest.mark.asyncio
    async def test_fetch_data_static_source(self, generator):
        """Test fetching data from static source."""
        data_source = {
            "static_source": {
                "data": {"key": "value", "numbers": [1, 2, 3]}
            }
        }
        
        result = await generator._fetch_data(data_source)
        
        assert result == {"key": "value", "numbers": [1, 2, 3]}
    
    @pytest.mark.asyncio
    async def test_fetch_data_query_source(self, generator):
        """Test fetching data from query source."""
        data_source = {
            "query_source": {
                "query": "SELECT * FROM table",
                "parameters": {"limit": 100}
            }
        }
        
        result = await generator._fetch_data(data_source)
        
        assert "query_result" in result
    
    @pytest.mark.asyncio
    async def test_fetch_data_file_source(self, generator):
        """Test fetching data from file source."""
        data_source = {
            "file_source": {
                "file_path": "/tmp/data.csv",
                "file_format": "csv"
            }
        }
        
        result = await generator._fetch_data(data_source)
        
        assert "file_data" in result
    
    @pytest.mark.asyncio
    async def test_fetch_data_empty_source(self, generator):
        """Test fetching data from empty source."""
        data_source = {}
        
        result = await generator._fetch_data(data_source)
        
        assert result == {}


class TestFileOperations:
    """Test cases for file operations and format conversion."""
    
    @pytest.fixture
    def generator(self, mock_settings, mock_jinja_env):
        """Create HTML report generator instance."""
        with patch('app.services.html_generator.Environment') as mock_env_class:
            mock_env_class.return_value = mock_jinja_env
            
            from app.services.html_generator import HTMLReportGenerator
            return HTMLReportGenerator()
    
    @pytest.mark.asyncio
    async def test_save_html_file(self, generator):
        """Test saving HTML file."""
        content = "<html><body>Test</body></html>"
        file_path = "/tmp/test.html"
        
        with patch('aiofiles.open', mock_open()) as mock_file:
            mock_file.return_value.__aenter__.return_value = AsyncMock()
            mock_file.return_value.__aexit__.return_value = None
            
            await generator._save_html_file(content, file_path)
            
            mock_file.assert_called_once_with(file_path, 'w', encoding='utf-8')
    
    @pytest.mark.asyncio
    async def test_convert_html_to_pdf(self, generator):
        """Test HTML to PDF conversion."""
        content = "<html><body>Test</body></html>"
        output_path = "/tmp/test.pdf"
        
        with patch.object(generator, '_save_html_file', new_callable=AsyncMock) as mock_save:
            result = await generator._convert_html(content, output_path, OutputFormat.PDF)
            
            # Should fall back to HTML for now (PDF not implemented)
            assert result.endswith('.html')
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_convert_html_to_png(self, generator):
        """Test HTML to PNG conversion."""
        content = "<html><body>Test</body></html>"
        output_path = "/tmp/test.png"
        
        with patch.object(generator, '_save_html_file', new_callable=AsyncMock) as mock_save:
            result = await generator._convert_html(content, output_path, OutputFormat.PNG)
            
            # Should fall back to HTML for now (PNG not implemented)
            assert result.endswith('.html')
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_convert_html_to_html(self, generator):
        """Test HTML to HTML conversion (no conversion)."""
        content = "<html><body>Test</body></html>"
        output_path = "/tmp/test.html"
        
        with patch.object(generator, '_save_html_file', new_callable=AsyncMock) as mock_save:
            result = await generator._convert_html(content, output_path, OutputFormat.HTML)
            
            assert result == output_path
            mock_save.assert_called_once()


class TestDatabaseOperations:
    """Test cases for database operations."""
    
    @pytest.fixture
    def generator(self, mock_settings, mock_jinja_env):
        """Create HTML report generator instance."""
        with patch('app.services.html_generator.Environment') as mock_env_class:
            mock_env_class.return_value = mock_jinja_env
            
            from app.services.html_generator import HTMLReportGenerator
            return HTMLReportGenerator()
    
    @pytest.mark.asyncio
    async def test_update_job_status(self, generator, mock_database):
        """Test job status update."""
        job_id = 123
        status = JobStatus.PROCESSING
        error_message = "Test error"
        started_at = datetime.utcnow()
        
        await generator._update_job_status(
            job_id=job_id,
            status=status,
            error_message=error_message,
            started_at=started_at
        )
        
        # Verify database function was called
        mock_database['update_status'].assert_called_once_with(
            mock_database['get_session'].return_value.__aenter__.return_value,
            job_id,
            status.value,
            error_message,
            started_at,
            None
        )
    
    @pytest.mark.asyncio
    async def test_update_job_completion(self, generator, mock_database):
        """Test job completion update."""
        job_id = 123
        status = JobStatus.COMPLETED
        file_path = "/tmp/report.html"
        file_size = 1024
        chart_count = 2
        table_count = 1
        section_count = 3
        generation_time_ms = 5000
        
        await generator._update_job_completion(
            job_id=job_id,
            status=status,
            file_path=file_path,
            file_size=file_size,
            chart_count=chart_count,
            table_count=table_count,
            section_count=section_count,
            generation_time_ms=generation_time_ms
        )
        
        # Verify database function was called
        mock_database['update_completion'].assert_called_once_with(
            mock_database['get_session'].return_value.__aenter__.return_value,
            job_id,
            status.value,
            file_path,
            file_size,
            chart_count,
            table_count,
            section_count,
            generation_time_ms
        )
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, generator, mock_database):
        """Test database error handling."""
        # Simulate database error
        mock_database['update_status'].side_effect = Exception("Database error")
        
        # Should not raise exception, just log error
        await generator._update_job_status(123, JobStatus.FAILED)
        
        # Verify the function was called despite the error
        mock_database['update_status'].assert_called_once()


class TestSectionGeneration:
    """Test cases for layout section generation."""
    
    @pytest.fixture
    def generator(self, mock_settings, mock_jinja_env):
        """Create HTML report generator instance."""
        with patch('app.services.html_generator.Environment') as mock_env_class:
            mock_env_class.return_value = mock_jinja_env
            
            from app.services.html_generator import HTMLReportGenerator
            return HTMLReportGenerator()
    
    @pytest.mark.asyncio
    async def test_create_section_html_chart(self, generator, sample_layout_sections):
        """Test creating section HTML for chart content."""
        section = sample_layout_sections[0]  # Chart section
        charts_html = [f'<div id="chart-{section.content_id}">Chart Content</div>']
        tables_html = []
        
        result = await generator._create_section_html(section, charts_html, tables_html)
        
        assert isinstance(result, str)
        assert f"section-{section.id}" in result
        assert section.title in result
        assert "Chart Content" in result
        assert f"col-md-{section.width}" in result
    
    @pytest.mark.asyncio
    async def test_create_section_html_table(self, generator, sample_layout_sections):
        """Test creating section HTML for table content."""
        section = sample_layout_sections[1]  # Table section
        charts_html = []
        tables_html = [f'<div id="table-{section.content_id}">Table Content</div>']
        
        result = await generator._create_section_html(section, charts_html, tables_html)
        
        assert isinstance(result, str)
        assert f"section-{section.id}" in result
        assert section.title in result
        assert "Table Content" in result
    
    @pytest.mark.asyncio
    async def test_create_section_html_with_styles(self, generator, sample_layout_sections):
        """Test creating section HTML with custom styles."""
        section = sample_layout_sections[0]
        section.custom_styles = {"background-color": "red", "padding": "10px"}
        section.height = 500
        
        charts_html = [f'<div id="chart-{section.content_id}">Chart</div>']
        tables_html = []
        
        result = await generator._create_section_html(section, charts_html, tables_html)
        
        assert "style=" in result
        assert "background-color: red" in result
        assert "padding: 10px" in result
        assert "height: 500px" in result