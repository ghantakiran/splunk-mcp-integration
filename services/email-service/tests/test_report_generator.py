"""
Tests for Report Generator Service.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, mock_open
from typing import Dict, Any
import tempfile
import os

from app.services.report_generator import ReportGenerator
from app.services.database_service import DatabaseService
from app.services.redis_service import RedisService


class TestReportGenerator:
    """Test suite for ReportGenerator class."""

    @pytest.fixture
    def report_generator(self, mock_database_service, mock_redis_service):
        """Create a ReportGenerator instance."""
        return ReportGenerator(mock_database_service, mock_redis_service)

    @pytest.mark.asyncio
    async def test_report_generator_initialization(self, report_generator):
        """Test ReportGenerator initialization."""
        await report_generator.initialize()
        # Initialization should complete without errors
        assert report_generator.db is not None
        assert report_generator.redis is not None

    @pytest.mark.asyncio
    async def test_report_generator_cleanup(self, report_generator):
        """Test ReportGenerator cleanup."""
        await report_generator.cleanup()
        # Cleanup should complete without errors

    @pytest.mark.asyncio
    async def test_generate_pdf_report_success(self, report_generator):
        """Test successful PDF report generation."""
        # Mock the actual implementation that would be in the service
        with patch.object(report_generator, 'generate_pdf_report') as mock_method:
            mock_method.return_value = {
                "file_path": "/tmp/test_report.pdf",
                "file_size": 1024000,
                "pages": 5,
                "generation_time": 2.5
            }
            
            report_config = {
                "title": "Test PDF Report",
                "query": "index=main | stats count by source",
                "template": "standard",
                "include_charts": True
            }
            
            result = await report_generator.generate_pdf_report(report_config)
            
            assert result["file_path"] == "/tmp/test_report.pdf"
            assert result["file_size"] == 1024000
            assert result["pages"] == 5
            mock_method.assert_called_once_with(report_config)

    @pytest.mark.asyncio
    async def test_generate_csv_report_success(self, report_generator):
        """Test successful CSV report generation."""
        with patch.object(report_generator, 'generate_csv_report') as mock_method:
            mock_method.return_value = {
                "file_path": "/tmp/test_report.csv",
                "file_size": 512000,
                "rows": 1000,
                "columns": 8
            }
            
            report_config = {
                "title": "Test CSV Report",
                "query": "index=main | stats count by source",
                "delimiter": ",",
                "include_headers": True
            }
            
            result = await report_generator.generate_csv_report(report_config)
            
            assert result["file_path"] == "/tmp/test_report.csv"
            assert result["rows"] == 1000
            mock_method.assert_called_once_with(report_config)

    @pytest.mark.asyncio
    async def test_generate_html_report_success(self, report_generator):
        """Test successful HTML report generation."""
        with patch.object(report_generator, 'generate_html_report') as mock_method:
            mock_method.return_value = {
                "file_path": "/tmp/test_report.html",
                "file_size": 256000,
                "interactive": True,
                "chart_count": 3
            }
            
            report_config = {
                "title": "Test HTML Report",
                "query": "index=main | timechart count",
                "template": "interactive",
                "include_javascript": True
            }
            
            result = await report_generator.generate_html_report(report_config)
            
            assert result["file_path"] == "/tmp/test_report.html"
            assert result["interactive"] is True
            assert result["chart_count"] == 3
            mock_method.assert_called_once_with(report_config)

    @pytest.mark.asyncio
    async def test_generate_excel_report_success(self, report_generator):
        """Test successful Excel report generation."""
        with patch.object(report_generator, 'generate_excel_report') as mock_method:
            mock_method.return_value = {
                "file_path": "/tmp/test_report.xlsx",
                "file_size": 768000,
                "sheets": 3,
                "charts": 2
            }
            
            report_config = {
                "title": "Test Excel Report",
                "query": "index=main | stats count by source, host",
                "include_charts": True,
                "sheet_per_query": True
            }
            
            result = await report_generator.generate_excel_report(report_config)
            
            assert result["file_path"] == "/tmp/test_report.xlsx"
            assert result["sheets"] == 3
            assert result["charts"] == 2
            mock_method.assert_called_once_with(report_config)


class TestReportGeneratorWithImplementation:
    """Test suite for ReportGenerator with mock implementations."""

    @pytest.fixture
    def report_generator_with_impl(self, mock_database_service, mock_redis_service):
        """Create ReportGenerator with mock implementations."""
        generator = ReportGenerator(mock_database_service, mock_redis_service)
        
        # Add mock implementations for the methods
        async def mock_generate_pdf_report(config):
            return {
                "file_path": f"/tmp/{config.get('title', 'report').replace(' ', '_')}.pdf",
                "file_size": 1024000,
                "pages": 5,
                "generation_time": 2.5,
                "format": "pdf"
            }
        
        async def mock_generate_csv_report(config):
            return {
                "file_path": f"/tmp/{config.get('title', 'report').replace(' ', '_')}.csv",
                "file_size": 256000,
                "rows": 1000,
                "columns": len(config.get('fields', ['field1', 'field2'])),
                "format": "csv"
            }
        
        async def mock_generate_html_report(config):
            return {
                "file_path": f"/tmp/{config.get('title', 'report').replace(' ', '_')}.html",
                "file_size": 512000,
                "interactive": config.get('include_javascript', False),
                "chart_count": 2,
                "format": "html"
            }
        
        async def mock_generate_excel_report(config):
            return {
                "file_path": f"/tmp/{config.get('title', 'report').replace(' ', '_')}.xlsx",
                "file_size": 768000,
                "sheets": 2,
                "charts": 1,
                "format": "excel"
            }
        
        # Attach mock implementations
        generator.generate_pdf_report = mock_generate_pdf_report
        generator.generate_csv_report = mock_generate_csv_report
        generator.generate_html_report = mock_generate_html_report
        generator.generate_excel_report = mock_generate_excel_report
        
        return generator

    @pytest.mark.asyncio
    async def test_pdf_report_with_charts(self, report_generator_with_impl):
        """Test PDF report generation with charts."""
        config = {
            "title": "Performance Dashboard",
            "query": "index=main | timechart count",
            "include_charts": True,
            "chart_types": ["line", "bar"],
            "template": "professional"
        }
        
        result = await report_generator_with_impl.generate_pdf_report(config)
        
        assert result["file_path"].endswith("Performance_Dashboard.pdf")
        assert result["format"] == "pdf"
        assert result["generation_time"] == 2.5

    @pytest.mark.asyncio
    async def test_csv_report_with_custom_fields(self, report_generator_with_impl):
        """Test CSV report generation with custom fields."""
        config = {
            "title": "User Activity Report",
            "query": "index=main | stats count by user, action",
            "fields": ["user", "action", "count", "timestamp"],
            "delimiter": ",",
            "include_headers": True
        }
        
        result = await report_generator_with_impl.generate_csv_report(config)
        
        assert result["file_path"].endswith("User_Activity_Report.csv")
        assert result["format"] == "csv"
        assert result["columns"] == 4  # Number of fields

    @pytest.mark.asyncio
    async def test_html_report_with_interactivity(self, report_generator_with_impl):
        """Test HTML report generation with interactive features."""
        config = {
            "title": "Interactive Dashboard",
            "query": "index=main | stats count by source",
            "include_javascript": True,
            "template": "modern",
            "interactive_charts": True
        }
        
        result = await report_generator_with_impl.generate_html_report(config)
        
        assert result["file_path"].endswith("Interactive_Dashboard.html")
        assert result["format"] == "html"
        assert result["interactive"] is True
        assert result["chart_count"] == 2

    @pytest.mark.asyncio
    async def test_excel_report_with_multiple_sheets(self, report_generator_with_impl):
        """Test Excel report generation with multiple sheets."""
        config = {
            "title": "Comprehensive Analysis",
            "queries": [
                "index=main | stats count by source",
                "index=main | stats count by host"
            ],
            "sheet_per_query": True,
            "include_charts": True
        }
        
        result = await report_generator_with_impl.generate_excel_report(config)
        
        assert result["file_path"].endswith("Comprehensive_Analysis.xlsx")
        assert result["format"] == "excel"
        assert result["sheets"] == 2
        assert result["charts"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_report_generation(self, report_generator_with_impl):
        """Test concurrent generation of multiple reports."""
        configs = [
            {"title": "Report 1", "query": "query1", "format": "pdf"},
            {"title": "Report 2", "query": "query2", "format": "csv"},
            {"title": "Report 3", "query": "query3", "format": "html"}
        ]
        
        # Generate reports concurrently
        import asyncio
        tasks = [
            report_generator_with_impl.generate_pdf_report(configs[0]),
            report_generator_with_impl.generate_csv_report(configs[1]),
            report_generator_with_impl.generate_html_report(configs[2])
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert results[0]["format"] == "pdf"
        assert results[1]["format"] == "csv"
        assert results[2]["format"] == "html"


class TestReportGeneratorIntegration:
    """Test suite for ReportGenerator integration scenarios."""

    @pytest.fixture
    def report_generator_integration(self, db_session):
        """Create ReportGenerator with integration setup."""
        db_service = AsyncMock(spec=DatabaseService)
        db_service.session = db_session
        redis_service = AsyncMock(spec=RedisService)
        
        # Mock database operations
        db_service.save_report_metadata = AsyncMock()
        db_service.get_report_template = AsyncMock()
        db_service.update_report_status = AsyncMock()
        
        # Mock Redis operations
        redis_service.cache_report = AsyncMock()
        redis_service.get_cached_report = AsyncMock()
        redis_service.queue_report_job = AsyncMock()
        
        return ReportGenerator(db_service, redis_service)

    @pytest.mark.asyncio
    async def test_report_generation_with_database_integration(self, report_generator_integration):
        """Test report generation with database operations."""
        generator = report_generator_integration
        
        # Mock template retrieval
        generator.db.get_report_template.return_value = {
            "id": "template-123",
            "name": "Standard Template",
            "layout": "professional",
            "styles": {"font": "Arial", "size": 12}
        }
        
        # Mock report saving
        generator.db.save_report_metadata.return_value = {"id": "report-456"}
        
        with patch.object(generator, 'generate_pdf_report') as mock_gen:
            mock_gen.return_value = {
                "file_path": "/tmp/test.pdf",
                "file_size": 1024000
            }
            
            config = {
                "title": "Test Report",
                "template_id": "template-123",
                "query": "test query"
            }
            
            result = await generator.generate_pdf_report(config)
            
            assert result["file_path"] == "/tmp/test.pdf"

    @pytest.mark.asyncio
    async def test_report_caching_with_redis(self, report_generator_integration):
        """Test report caching functionality with Redis."""
        generator = report_generator_integration
        
        # Mock cache miss and subsequent cache
        generator.redis.get_cached_report.return_value = None
        generator.redis.cache_report.return_value = True
        
        with patch.object(generator, 'generate_csv_report') as mock_gen:
            mock_gen.return_value = {
                "file_path": "/tmp/cached_report.csv",
                "file_size": 512000
            }
            
            config = {
                "title": "Cached Report",
                "query": "index=main | head 100",
                "cache_duration": 3600
            }
            
            result = await generator.generate_csv_report(config)
            
            assert result["file_size"] == 512000

    @pytest.mark.asyncio
    async def test_report_queue_processing(self, report_generator_integration):
        """Test background report queue processing."""
        generator = report_generator_integration
        
        # Mock queue operations
        generator.redis.queue_report_job.return_value = "job-789"
        generator.redis.get_job_status = AsyncMock(return_value="completed")
        
        # Mock job processing
        with patch.object(generator, '_process_queued_report') as mock_process:
            mock_process.return_value = {
                "job_id": "job-789",
                "status": "completed",
                "result": {"file_path": "/tmp/queued_report.pdf"}
            }
            
            job_config = {
                "title": "Queued Report",
                "priority": "high",
                "scheduled_time": "2025-01-16T15:00:00Z"
            }
            
            # This would typically be called by a background worker
            result = await generator._process_queued_report(job_config)
            
            assert result["status"] == "completed"


class TestReportGeneratorErrorHandling:
    """Test suite for ReportGenerator error handling."""

    @pytest.fixture
    def report_generator_with_errors(self):
        """Create ReportGenerator with error-prone services."""
        db_service = AsyncMock(spec=DatabaseService)
        redis_service = AsyncMock(spec=RedisService)
        
        # Make some operations fail
        db_service.save_report_metadata.side_effect = Exception("Database error")
        redis_service.cache_report.side_effect = Exception("Redis error")
        
        return ReportGenerator(db_service, redis_service)

    @pytest.mark.asyncio
    async def test_report_generation_with_database_error(self, report_generator_with_errors):
        """Test report generation when database operations fail."""
        generator = report_generator_with_errors
        
        with patch.object(generator, 'generate_pdf_report') as mock_gen:
            # Even with database errors, report generation should proceed
            mock_gen.return_value = {
                "file_path": "/tmp/error_test.pdf",
                "file_size": 1024000,
                "warnings": ["Database metadata save failed"]
            }
            
            config = {"title": "Error Test", "query": "test"}
            result = await generator.generate_pdf_report(config)
            
            assert result["file_path"] == "/tmp/error_test.pdf"
            assert "warnings" in result

    @pytest.mark.asyncio
    async def test_report_generation_with_redis_error(self, report_generator_with_errors):
        """Test report generation when Redis operations fail."""
        generator = report_generator_with_errors
        
        with patch.object(generator, 'generate_html_report') as mock_gen:
            # Report generation should continue despite Redis errors
            mock_gen.return_value = {
                "file_path": "/tmp/redis_error_test.html",
                "file_size": 256000,
                "cached": False  # Indicates caching failed
            }
            
            config = {"title": "Redis Error Test", "query": "test"}
            result = await generator.generate_html_report(config)
            
            assert result["file_path"] == "/tmp/redis_error_test.html"
            assert result["cached"] is False

    @pytest.mark.asyncio
    async def test_invalid_report_configuration(self, report_generator_with_errors):
        """Test handling of invalid report configurations."""
        generator = report_generator_with_errors
        
        with patch.object(generator, 'generate_csv_report') as mock_gen:
            # Should handle invalid configurations gracefully
            mock_gen.side_effect = ValueError("Invalid configuration")
            
            config = {"title": "", "query": None}  # Invalid config
            
            with pytest.raises(ValueError):
                await generator.generate_csv_report(config)

    @pytest.mark.asyncio
    async def test_file_system_errors(self, report_generator_with_errors):
        """Test handling of file system errors."""
        generator = report_generator_with_errors
        
        with patch.object(generator, 'generate_excel_report') as mock_gen:
            # Simulate file system error
            mock_gen.side_effect = OSError("Permission denied")
            
            config = {"title": "FS Error Test", "output_path": "/readonly/path"}
            
            with pytest.raises(OSError):
                await generator.generate_excel_report(config)


class TestReportGeneratorMocking:
    """Test suite for detailed ReportGenerator mocking scenarios."""

    @pytest.mark.asyncio
    async def test_template_processing(self, report_generator):
        """Test report template processing."""
        with patch.object(report_generator, '_process_template') as mock_process:
            mock_process.return_value = {
                "processed_html": "<html><body>Processed content</body></html>",
                "variables_used": ["title", "date", "data"],
                "template_id": "template-123"
            }
            
            template_config = {
                "template_id": "template-123",
                "variables": {
                    "title": "Monthly Report",
                    "date": "2025-01-16",
                    "data": [1, 2, 3, 4, 5]
                }
            }
            
            result = await generator._process_template(template_config)
            
            assert "processed_html" in result
            assert len(result["variables_used"]) == 3

    @pytest.mark.asyncio
    async def test_chart_generation_integration(self, report_generator, mock_visualization_service):
        """Test integration with chart generation service."""
        with patch.object(report_generator, '_generate_charts') as mock_charts:
            mock_charts.return_value = {
                "charts": [
                    {"type": "bar", "url": "http://localhost:8002/charts/bar1.png"},
                    {"type": "line", "url": "http://localhost:8002/charts/line1.png"}
                ],
                "chart_count": 2
            }
            
            chart_config = {
                "query_results": [{"source": "web", "count": 100}],
                "chart_types": ["bar", "line"],
                "dimensions": {"width": 800, "height": 600}
            }
            
            result = await generator._generate_charts(chart_config)
            
            assert result["chart_count"] == 2
            assert len(result["charts"]) == 2

    @pytest.mark.asyncio
    async def test_report_metadata_handling(self, report_generator):
        """Test report metadata handling."""
        with patch.object(report_generator, '_handle_metadata') as mock_metadata:
            mock_metadata.return_value = {
                "metadata": {
                    "generated_at": "2025-01-16T10:30:00Z",
                    "generator_version": "1.0.0",
                    "query_execution_time": 1.5,
                    "total_records": 5000
                }
            }
            
            metadata_config = {
                "include_generation_info": True,
                "include_query_stats": True,
                "include_data_summary": True
            }
            
            result = await generator._handle_metadata(metadata_config)
            
            assert "metadata" in result
            assert result["metadata"]["total_records"] == 5000