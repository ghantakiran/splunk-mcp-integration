"""
Tests for PDF generation service.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.pdf_generator import PDFGenerator, PDFGenerationError
from app.models.pdf_models import JobStatus, OutputFormat, LayoutConfig


@pytest.fixture
def pdf_generator():
    """Create PDF generator instance."""
    return PDFGenerator()


@pytest.fixture
def mock_template():
    """Mock template data."""
    return {
        "id": 1,
        "name": "Test Template",
        "template_type": "report",
        "template_content": "<html><body><h1>{{ title }}</h1><p>{{ content }}</p></body></html>",
        "css_content": "body { font-family: Arial; }",
        "variables": {"title": "Test", "content": "Test content"},
        "layout_config": {"page_size": "a4", "orientation": "portrait"}
    }


@pytest.fixture
def mock_job_parameters():
    """Mock job parameters."""
    return {
        "title": "Test PDF Report",
        "content": "This is test content for the PDF generation test."
    }


@pytest.fixture
def mock_data_source():
    """Mock data source."""
    return {
        "type": "test",
        "data": [],
        "charts": [
            {
                "chart_id": "test_chart_1",
                "title": "Test Chart",
                "chart_type": "bar",
                "width": 800,
                "height": 600,
                "data": {"labels": ["A", "B", "C"], "values": [10, 20, 30]},
                "options": {}
            }
        ]
    }


class TestPDFGenerator:
    """Test PDF generator functionality."""
    
    @pytest.mark.asyncio
    async def test_template_environment_setup(self, pdf_generator):
        """Test template environment is properly set up."""
        assert pdf_generator.template_env is not None
        assert 'format_date' in pdf_generator.template_env.filters
        assert 'format_number' in pdf_generator.template_env.filters
        assert 'now' in pdf_generator.template_env.globals
    
    @pytest.mark.asyncio
    async def test_format_date_filter(self, pdf_generator):
        """Test date formatting filter."""
        date_filter = pdf_generator.template_env.filters['format_date']
        test_date = datetime(2024, 1, 1, 10, 30, 0)
        result = date_filter(test_date)
        assert result == "2024-01-01 10:30:00"
    
    @pytest.mark.asyncio
    async def test_format_number_filter(self, pdf_generator):
        """Test number formatting filter."""
        number_filter = pdf_generator.template_env.filters['format_number']
        result = number_filter(1234.567, 2)
        assert result == "1,234.57"
    
    @pytest.mark.asyncio
    async def test_format_currency_filter(self, pdf_generator):
        """Test currency formatting filter."""
        currency_filter = pdf_generator.template_env.filters['format_currency']
        result = currency_filter(1234.56)
        assert result == "$1,234.56"
    
    @pytest.mark.asyncio
    async def test_truncate_text_filter(self, pdf_generator):
        """Test text truncation filter."""
        truncate_filter = pdf_generator.template_env.filters['truncate_text']
        result = truncate_filter("This is a very long text that should be truncated", 20)
        assert result == "This is a very long ..."
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.execute_query')
    async def test_get_template(self, mock_execute_query, pdf_generator, mock_template):
        """Test template retrieval."""
        mock_execute_query.return_value = mock_template
        
        template = await pdf_generator._get_template(1)
        
        assert template is not None
        assert template['id'] == 1
        assert template['name'] == "Test Template"
        mock_execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.execute_query')
    async def test_get_template_not_found(self, mock_execute_query, pdf_generator):
        """Test template retrieval when template not found."""
        mock_execute_query.return_value = None
        
        template = await pdf_generator._get_template(999)
        
        assert template is None
        mock_execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_prepare_template_data(self, pdf_generator, mock_template, 
                                       mock_job_parameters, mock_data_source):
        """Test template data preparation."""
        template_data = await pdf_generator._prepare_template_data(
            mock_template, mock_job_parameters, mock_data_source
        )
        
        assert 'template' in template_data
        assert 'parameters' in template_data
        assert 'data_source' in template_data
        assert 'generation_date' in template_data
        assert 'charts' in template_data
        assert template_data['parameters']['title'] == "Test PDF Report"
        assert len(template_data['charts']) == 1
    
    @pytest.mark.asyncio
    async def test_render_template(self, pdf_generator, mock_template):
        """Test template rendering."""
        template_data = {
            'title': 'Test Report',
            'content': 'Test content for rendering'
        }
        
        html_content = await pdf_generator._render_template(mock_template, template_data)
        
        assert html_content is not None
        assert 'Test Report' in html_content
        assert 'Test content for rendering' in html_content
    
    @pytest.mark.asyncio
    async def test_render_template_with_invalid_syntax(self, pdf_generator):
        """Test template rendering with invalid syntax."""
        invalid_template = {
            'id': 1,
            'template_content': '<html><body>{{ invalid_syntax }}</body></html>'
        }
        
        template_data = {}
        
        # Should not raise an error, just render without the variable
        html_content = await pdf_generator._render_template(invalid_template, template_data)
        assert html_content is not None
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.HTML')
    @patch('app.services.pdf_generator.CSS')
    async def test_generate_pdf_file(self, mock_css, mock_html, pdf_generator, temp_dir):
        """Test PDF file generation."""
        # Mock WeasyPrint
        mock_pdf_bytes = b"Mock PDF content"
        mock_html_instance = Mock()
        mock_html_instance.write_pdf.return_value = mock_pdf_bytes
        mock_html.return_value = mock_html_instance
        
        # Mock CSS
        mock_css_instance = Mock()
        mock_css.return_value = mock_css_instance
        
        # Set temp directory
        with patch('app.services.pdf_generator.settings.PDF_OUTPUT_DIR', temp_dir):
            result = await pdf_generator._generate_pdf_file(
                1, "<html><body>Test content</body></html>", 
                {"css_content": "body { font-family: Arial; }"}
            )
        
        assert result is not None
        assert 'file_path' in result
        assert 'file_size' in result
        assert 'page_count' in result
        assert 'filename' in result
        assert result['file_size'] == len(mock_pdf_bytes)
        assert os.path.exists(result['file_path'])
    
    @pytest.mark.asyncio
    async def test_generate_html_file(self, pdf_generator, temp_dir):
        """Test HTML file generation."""
        with patch('app.services.pdf_generator.settings.PDF_OUTPUT_DIR', temp_dir):
            result = await pdf_generator._generate_html(
                1, "<html><body>Test content</body></html>",
                {"css_content": "body { font-family: Arial; }"}
            )
        
        assert result is not None
        assert 'file_path' in result
        assert 'file_size' in result
        assert result['page_count'] == 1
        assert os.path.exists(result['file_path'])
        
        # Check file content
        with open(result['file_path'], 'r') as f:
            content = f.read()
            assert 'Test content' in content
            assert 'font-family: Arial' in content
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.httpx.AsyncClient')
    async def test_fetch_chart_image_success(self, mock_client, pdf_generator):
        """Test successful chart image fetching."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"Mock chart image data"
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        chart_config = Mock()
        chart_config.chart_id = "test_chart"
        chart_config.chart_type = "bar"
        chart_config.data = {}
        chart_config.options = {}
        chart_config.width = 800
        chart_config.height = 600
        
        result = await pdf_generator._fetch_chart_image(chart_config)
        
        assert result is not None
        assert result.startswith("data:image/png;base64,")
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.httpx.AsyncClient')
    async def test_fetch_chart_image_failure(self, mock_client, pdf_generator):
        """Test chart image fetching failure."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 500
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        chart_config = Mock()
        chart_config.chart_id = "test_chart"
        chart_config.chart_type = "bar"
        chart_config.data = {}
        chart_config.options = {}
        chart_config.width = 800
        chart_config.height = 600
        
        result = await pdf_generator._fetch_chart_image(chart_config)
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.execute_query')
    async def test_update_job_status(self, mock_execute_query, pdf_generator):
        """Test job status update."""
        await pdf_generator._update_job_status(1, JobStatus.PROCESSING)
        
        mock_execute_query.assert_called_once()
        args = mock_execute_query.call_args[0]
        assert JobStatus.PROCESSING.value in args
        assert 1 in args
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.execute_query')
    async def test_update_job_completion(self, mock_execute_query, pdf_generator):
        """Test job completion update."""
        result = {
            'file_path': '/tmp/test.pdf',
            'file_size': 1024,
            'page_count': 1
        }
        
        await pdf_generator._update_job_completion(1, result, 5000)
        
        mock_execute_query.assert_called_once()
        args = mock_execute_query.call_args[0]
        assert JobStatus.COMPLETED.value in args
        assert result['file_path'] in args
        assert result['file_size'] in args
        assert result['page_count'] in args
        assert 5000 in args
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.execute_query')
    async def test_update_job_error(self, mock_execute_query, pdf_generator):
        """Test job error update."""
        error_message = "Test error message"
        
        await pdf_generator._update_job_error(1, error_message, 3000)
        
        mock_execute_query.assert_called_once()
        args = mock_execute_query.call_args[0]
        assert JobStatus.FAILED.value in args
        assert error_message in args
        assert 3000 in args
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.execute_query')
    async def test_cancel_job(self, mock_execute_query, pdf_generator):
        """Test job cancellation."""
        # Add job to active jobs
        pdf_generator.active_jobs["job:1"] = {
            "job_id": 1,
            "start_time": 1234567890,
            "status": JobStatus.PROCESSING
        }
        
        result = await pdf_generator.cancel_job(1)
        
        assert result is True
        assert "job:1" not in pdf_generator.active_jobs
        mock_execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.execute_query')
    async def test_get_job_status_from_database(self, mock_execute_query, pdf_generator):
        """Test job status retrieval from database."""
        mock_job = {
            "id": 1,
            "status": "completed",
            "created_at": datetime.now(),
            "file_path": "/tmp/test.pdf"
        }
        mock_execute_query.return_value = mock_job
        
        status = await pdf_generator.get_job_status(1)
        
        assert status is not None
        assert status["id"] == 1
        assert status["status"] == "completed"
        mock_execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_job_status_from_active_jobs(self, pdf_generator):
        """Test job status retrieval from active jobs."""
        start_time = 1234567890
        pdf_generator.active_jobs["job:1"] = {
            "job_id": 1,
            "start_time": start_time,
            "status": JobStatus.PROCESSING
        }
        
        with patch('time.time', return_value=start_time + 10):
            status = await pdf_generator.get_job_status(1)
        
        assert status is not None
        assert status["job_id"] == 1
        assert status["status"] == JobStatus.PROCESSING
        assert status["runtime_seconds"] == 10
    
    @pytest.mark.asyncio
    async def test_count_pdf_pages(self, pdf_generator):
        """Test PDF page counting."""
        # Mock PDF content
        pdf_content = b"Mock PDF content with enough data to estimate pages"
        
        page_count = pdf_generator._count_pdf_pages(pdf_content)
        
        assert page_count >= 1
        assert isinstance(page_count, int)
    
    @pytest.mark.asyncio
    async def test_get_default_css(self, pdf_generator):
        """Test default CSS generation."""
        css = pdf_generator._get_default_css()
        
        assert css is not None
        assert "font-family" in css
        assert "body" in css
        assert ".header" in css
        assert ".footer" in css
    
    @pytest.mark.asyncio
    async def test_generate_layout_css(self, pdf_generator):
        """Test layout CSS generation."""
        layout_config = LayoutConfig(
            page_size="a4",
            orientation="portrait",
            margin_top=20,
            margin_bottom=20,
            margin_left=15,
            margin_right=15
        )
        
        css = pdf_generator._generate_layout_css(layout_config)
        
        assert css is not None
        assert "A4" in css
        assert "portrait" in css
        assert "20mm" in css
        assert "15mm" in css
    
    @pytest.mark.asyncio
    @patch('app.services.pdf_generator.execute_query')
    async def test_cleanup_old_files(self, mock_execute_query, pdf_generator, temp_dir):
        """Test cleanup of old files."""
        # Create test files
        test_file = os.path.join(temp_dir, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Mock database response
        mock_execute_query.return_value = [
            {"id": 1, "file_path": test_file}
        ]
        
        await pdf_generator.cleanup_old_files(1)
        
        # File should be deleted
        assert not os.path.exists(test_file)
        # Database should be updated
        assert mock_execute_query.call_count == 2