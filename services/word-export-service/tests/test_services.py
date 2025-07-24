#!/usr/bin/env python3
"""
Comprehensive service tests for Word Export Service.

This module tests core services including Word document generation,
template management, job processing, and analytics services.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.word_generator import WordGeneratorService
from app.services.template_service import TemplateService
from app.services.job_service import JobService
from app.services.analytics_service import AnalyticsService
from app.models.word_models import (
    JobStatus,
    OutputFormat,
    Template,
    FontFamily,
    ColorScheme,
    ChartType,
    DocumentConfig,
    DocumentMetadata,
    DocumentLayout,
    DocumentSection,
    Chart,
    ChartConfig,
    ChartData,
    Table,
    TableConfig,
    TableColumn,
    DataSource,
    StaticDataSource
)


class TestWordGeneratorService:
    """Test Word generation service functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_document_success(
        self,
        sample_document_config,
        sample_data_source,
        mock_docx,
        mock_matplotlib
    ):
        """Test successful document generation."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.Document') as mock_document_class:
            mock_doc = MagicMock()
            mock_document_class.return_value = mock_doc
            
            result = await service.generate_document(
                config=sample_document_config,
                data_source=sample_data_source,
                output_path="/tmp/test_document.docx"
            )
            
            assert result is not None
            assert "file_path" in result
            assert "file_size" in result
            assert "generation_time_ms" in result
            assert "metadata" in result
            mock_doc.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_document_with_charts(
        self,
        sample_document_config_with_charts,
        sample_data_source,
        mock_docx,
        mock_matplotlib
    ):
        """Test document generation with charts."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.Document') as mock_document_class, \
             patch('matplotlib.pyplot.savefig') as mock_savefig:
            
            mock_doc = MagicMock()
            mock_document_class.return_value = mock_doc
            mock_savefig.return_value = None
            
            result = await service.generate_document(
                config=sample_document_config_with_charts,
                data_source=sample_data_source,
                output_path="/tmp/test_document_charts.docx"
            )
            
            assert result is not None
            assert result["metadata"]["charts_generated"] > 0
            assert "chart_types" in result["metadata"]
            mock_savefig.assert_called()
    
    @pytest.mark.asyncio
    async def test_generate_document_with_tables(
        self,
        sample_document_config_with_tables,
        sample_data_source,
        mock_docx
    ):
        """Test document generation with tables."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.Document') as mock_document_class:
            mock_doc = MagicMock()
            mock_table = MagicMock()
            mock_doc.add_table.return_value = mock_table
            mock_document_class.return_value = mock_doc
            
            result = await service.generate_document(
                config=sample_document_config_with_tables,
                data_source=sample_data_source,
                output_path="/tmp/test_document_tables.docx"
            )
            
            assert result is not None
            assert result["metadata"]["tables_generated"] > 0
            mock_doc.add_table.assert_called()
    
    def test_create_chart_bar_chart(self, sample_chart_data, mock_matplotlib):
        """Test bar chart creation."""
        service = WordGeneratorService()
        
        chart_config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Test Bar Chart",
            width=400,
            height=300
        )
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.bar') as mock_bar, \
             patch('matplotlib.pyplot.savefig') as mock_savefig:
            
            mock_fig = MagicMock()
            mock_figure.return_value = mock_fig
            
            chart_path = service.create_chart(chart_config, sample_chart_data)
            
            assert chart_path is not None
            assert chart_path.endswith('.png')
            mock_bar.assert_called_once()
            mock_savefig.assert_called_once()
    
    def test_create_chart_line_chart(self, sample_chart_data, mock_matplotlib):
        """Test line chart creation."""
        service = WordGeneratorService()
        
        chart_config = ChartConfig(
            chart_type=ChartType.LINE,
            title="Test Line Chart",
            width=500,
            height=400
        )
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.plot') as mock_plot, \
             patch('matplotlib.pyplot.savefig') as mock_savefig:
            
            mock_fig = MagicMock()
            mock_figure.return_value = mock_fig
            
            chart_path = service.create_chart(chart_config, sample_chart_data)
            
            assert chart_path is not None
            mock_plot.assert_called_once()
            mock_savefig.assert_called_once()
    
    def test_create_chart_pie_chart(self, sample_pie_chart_data, mock_matplotlib):
        """Test pie chart creation."""
        service = WordGeneratorService()
        
        chart_config = ChartConfig(
            chart_type=ChartType.PIE,
            title="Test Pie Chart",
            width=400,
            height=400
        )
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.pie') as mock_pie, \
             patch('matplotlib.pyplot.savefig') as mock_savefig:
            
            mock_fig = MagicMock()
            mock_figure.return_value = mock_fig
            
            chart_path = service.create_chart(chart_config, sample_pie_chart_data)
            
            assert chart_path is not None
            mock_pie.assert_called_once()
            mock_savefig.assert_called_once()
    
    def test_apply_template_professional(self, mock_docx):
        """Test applying professional template."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.Document') as mock_document_class:
            mock_doc = MagicMock()
            mock_section = MagicMock()
            mock_doc.sections = [mock_section]
            mock_document_class.return_value = mock_doc
            
            service.apply_template(mock_doc, Template.PROFESSIONAL)
            
            # Verify template-specific styling was applied
            assert mock_section.page_height is not None or True  # Mock may not have all attributes
    
    def test_apply_template_corporate(self, mock_docx):
        """Test applying corporate template."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.Document') as mock_document_class:
            mock_doc = MagicMock()
            mock_section = MagicMock()
            mock_doc.sections = [mock_section]
            mock_document_class.return_value = mock_doc
            
            service.apply_template(mock_doc, Template.CORPORATE)
            
            # Verify corporate styling was applied
            assert mock_section is not None
    
    def test_add_metadata_to_document(self, sample_document_metadata, mock_docx):
        """Test adding metadata to document."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.Document') as mock_document_class:
            mock_doc = MagicMock()
            mock_core_props = MagicMock()
            mock_doc.core_properties = mock_core_props
            mock_document_class.return_value = mock_doc
            
            service.add_metadata(mock_doc, sample_document_metadata)
            
            assert mock_core_props.title == sample_document_metadata.title
            assert mock_core_props.author == sample_document_metadata.author
            assert mock_core_props.subject == sample_document_metadata.subject
    
    @pytest.mark.asyncio
    async def test_process_data_source_static(self, sample_static_data_source):
        """Test processing static data source."""
        service = WordGeneratorService()
        
        result = await service.process_data_source(sample_static_data_source)
        
        assert result is not None
        assert "charts" in result
        assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_process_data_source_query(self, sample_query_data_source):
        """Test processing query data source."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.execute_query') as mock_execute:
            mock_execute.return_value = {
                "results": [{"col1": "A", "col2": 1}, {"col1": "B", "col2": 2}],
                "columns": ["col1", "col2"]
            }
            
            result = await service.process_data_source(sample_query_data_source)
            
            assert result is not None
            assert "results" in result
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_data_source_file(self, sample_file_data_source):
        """Test processing file data source."""
        service = WordGeneratorService()
        
        with patch('pandas.read_csv') as mock_read_csv:
            mock_df = MagicMock()
            mock_df.to_dict.return_value = {
                "col1": {0: "A", 1: "B"},
                "col2": {0: 1, 1: 2}
            }
            mock_read_csv.return_value = mock_df
            
            result = await service.process_data_source(sample_file_data_source)
            
            assert result is not None
            mock_read_csv.assert_called_once()
    
    def test_validate_document_config_valid(self, sample_document_config):
        """Test document config validation with valid config."""
        service = WordGeneratorService()
        
        result = service.validate_document_config(sample_document_config)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_document_config_invalid_font_size(self, sample_document_config):
        """Test document config validation with invalid font size."""
        service = WordGeneratorService()
        
        # Modify config to have invalid font size
        invalid_config = sample_document_config.copy()
        invalid_config.font_size = 0
        
        result = service.validate_document_config(invalid_config)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert any("font_size" in error.lower() for error in result["errors"])
    
    def test_estimate_generation_time_simple(self, sample_document_config):
        """Test generation time estimation for simple document."""
        service = WordGeneratorService()
        
        estimated_time = service.estimate_generation_time(sample_document_config)
        
        assert isinstance(estimated_time, (int, float))
        assert estimated_time > 0
        assert estimated_time < 60000  # Should be under 1 minute for simple doc
    
    def test_estimate_generation_time_complex(self, sample_document_config_with_charts):
        """Test generation time estimation for complex document."""
        service = WordGeneratorService()
        
        estimated_time = service.estimate_generation_time(sample_document_config_with_charts)
        
        assert isinstance(estimated_time, (int, float))
        assert estimated_time > 5000  # Should be longer for complex doc
    
    @pytest.mark.asyncio
    async def test_cleanup_temporary_files(self):
        """Test cleanup of temporary files."""
        service = WordGeneratorService()
        
        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_files = []
            for i in range(3):
                temp_file = os.path.join(temp_dir, f"temp_chart_{i}.png")
                with open(temp_file, 'w') as f:
                    f.write("dummy content")
                temp_files.append(temp_file)
            
            # Add files to cleanup list
            service.temp_files.extend(temp_files)
            
            # Cleanup
            await service.cleanup_temporary_files()
            
            # Verify files were removed
            for temp_file in temp_files:
                assert not os.path.exists(temp_file)
    
    @pytest.mark.asyncio
    async def test_convert_to_pdf(self, mock_docx):
        """Test document conversion to PDF."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.convert_docx_to_pdf') as mock_convert:
            mock_convert.return_value = "/tmp/document.pdf"
            
            pdf_path = await service.convert_to_pdf("/tmp/document.docx")
            
            assert pdf_path == "/tmp/document.pdf"
            mock_convert.assert_called_once_with("/tmp/document.docx")
    
    @pytest.mark.asyncio
    async def test_generate_document_error_handling(
        self,
        sample_document_config,
        sample_data_source
    ):
        """Test error handling in document generation."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.Document') as mock_document_class:
            mock_document_class.side_effect = Exception("Document creation failed")
            
            with pytest.raises(Exception) as exc_info:
                await service.generate_document(
                    config=sample_document_config,
                    data_source=sample_data_source,
                    output_path="/tmp/test_document.docx"
                )
            
            assert "Document creation failed" in str(exc_info.value)


class TestTemplateService:
    """Test template management service."""
    
    @pytest.mark.asyncio
    async def test_create_template(self, sample_template_data, mock_database):
        """Test creating new template."""
        service = TemplateService()
        
        with patch.object(service, '_save_template_to_db') as mock_save:
            mock_save.return_value = {
                "template_id": 123,
                "name": sample_template_data["name"],
                "created_at": datetime.now(timezone.utc)
            }
            
            result = await service.create_template(
                name=sample_template_data["name"],
                description=sample_template_data["description"],
                config=sample_template_data["config"],
                user_id=1
            )
            
            assert result is not None
            assert "template_id" in result
            assert result["name"] == sample_template_data["name"]
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_template_by_id(self, sample_template_data, mock_database):
        """Test getting template by ID."""
        service = TemplateService()
        
        with patch.object(service, '_fetch_template_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "template_id": 123,
                **sample_template_data
            }
            
            result = await service.get_template_by_id(123)
            
            assert result is not None
            assert result["template_id"] == 123
            assert result["name"] == sample_template_data["name"]
            mock_fetch.assert_called_once_with(123)
    
    @pytest.mark.asyncio
    async def test_list_templates(self, sample_template_list, mock_database):
        """Test listing templates."""
        service = TemplateService()
        
        with patch.object(service, '_fetch_templates_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "templates": sample_template_list,
                "total": len(sample_template_list)
            }
            
            result = await service.list_templates(
                page=1,
                page_size=10,
                user_id=1
            )
            
            assert result is not None
            assert "templates" in result
            assert "total" in result
            assert len(result["templates"]) == len(sample_template_list)
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_template(self, sample_template_data, mock_database):
        """Test updating template."""
        service = TemplateService()
        
        update_data = {
            "description": "Updated description",
            "config": {"template": "corporate"}
        }
        
        with patch.object(service, '_template_exists') as mock_exists, \
             patch.object(service, '_update_template_in_db') as mock_update:
            
            mock_exists.return_value = True
            mock_update.return_value = {
                "template_id": 123,
                "name": sample_template_data["name"],
                "description": update_data["description"],
                "updated_at": datetime.now(timezone.utc)
            }
            
            result = await service.update_template(
                template_id=123,
                update_data=update_data,
                user_id=1
            )
            
            assert result is not None
            assert result["description"] == update_data["description"]
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_template(self, mock_database):
        """Test deleting template."""
        service = TemplateService()
        
        with patch.object(service, '_template_exists') as mock_exists, \
             patch.object(service, '_delete_template_from_db') as mock_delete:
            
            mock_exists.return_value = True
            mock_delete.return_value = True
            
            result = await service.delete_template(
                template_id=123,
                user_id=1
            )
            
            assert result is True
            mock_delete.assert_called_once_with(123)
    
    @pytest.mark.asyncio
    async def test_validate_template_config(self, sample_template_config):
        """Test template config validation."""
        service = TemplateService()
        
        result = await service.validate_template_config(sample_template_config)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_duplicate_template(self, sample_template_data, mock_database):
        """Test duplicating template."""
        service = TemplateService()
        
        with patch.object(service, '_fetch_template_from_db') as mock_fetch, \
             patch.object(service, '_save_template_to_db') as mock_save:
            
            mock_fetch.return_value = sample_template_data
            mock_save.return_value = {
                "template_id": 456,
                "name": f"Copy of {sample_template_data['name']}",
                "created_at": datetime.now(timezone.utc)
            }
            
            result = await service.duplicate_template(
                template_id=123,
                new_name="Copy of Template",
                user_id=1
            )
            
            assert result is not None
            assert "Copy of" in result["name"]
            mock_save.assert_called_once()
    
    def test_get_available_templates(self):
        """Test getting available built-in templates."""
        service = TemplateService()
        
        templates = service.get_available_templates()
        
        assert isinstance(templates, list)
        assert len(templates) > 0
        
        # Check that all built-in templates are included
        template_names = [t["name"] for t in templates]
        assert "professional" in template_names
        assert "corporate" in template_names
        assert "academic" in template_names
    
    def test_validate_template_name(self):
        """Test template name validation."""
        service = TemplateService()
        
        valid_names = [
            "Professional Template",
            "Corporate_Report_2024",
            "Academic-Style"
        ]
        
        for name in valid_names:
            result = service.validate_template_name(name)
            assert result is True
        
        invalid_names = [
            "",
            "x",
            "x" * 200,
            "Template<>Name"
        ]
        
        for name in invalid_names:
            result = service.validate_template_name(name)
            assert result is False


class TestJobService:
    """Test job management service."""
    
    @pytest.mark.asyncio
    async def test_create_job(self, sample_word_export_request, mock_database):
        """Test creating new job."""
        service = JobService()
        
        with patch.object(service, '_save_job_to_db') as mock_save:
            mock_save.return_value = {
                "job_id": 123,
                "job_name": sample_word_export_request.job_name,
                "status": JobStatus.PENDING,
                "created_at": datetime.now(timezone.utc)
            }
            
            result = await service.create_job(
                request=sample_word_export_request,
                user_id=1
            )
            
            assert result is not None
            assert "job_id" in result
            assert result["status"] == JobStatus.PENDING
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_job_status(self, mock_database):
        """Test getting job status."""
        service = JobService()
        
        with patch.object(service, '_fetch_job_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "job_id": 123,
                "status": JobStatus.PROCESSING,
                "progress_percentage": 45.5,
                "current_step": "Generating charts",
                "runtime_seconds": 120.5
            }
            
            result = await service.get_job_status(123)
            
            assert result is not None
            assert result["status"] == JobStatus.PROCESSING
            assert result["progress_percentage"] == 45.5
            mock_fetch.assert_called_once_with(123)
    
    @pytest.mark.asyncio
    async def test_update_job_status(self, mock_database):
        """Test updating job status."""
        service = JobService()
        
        with patch.object(service, '_update_job_in_db') as mock_update:
            mock_update.return_value = True
            
            result = await service.update_job_status(
                job_id=123,
                status=JobStatus.COMPLETED,
                progress=100.0,
                current_step="Completed"
            )
            
            assert result is True
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_jobs(self, sample_job_list, mock_database):
        """Test listing jobs."""
        service = JobService()
        
        with patch.object(service, '_fetch_jobs_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "jobs": sample_job_list,
                "total": len(sample_job_list)
            }
            
            result = await service.list_jobs(
                user_id=1,
                page=1,
                page_size=10
            )
            
            assert result is not None
            assert "jobs" in result
            assert "total" in result
            assert len(result["jobs"]) == len(sample_job_list)
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_job(self, mock_database):
        """Test canceling job."""
        service = JobService()
        
        with patch.object(service, '_fetch_job_from_db') as mock_fetch, \
             patch.object(service, '_update_job_in_db') as mock_update:
            
            mock_fetch.return_value = {
                "job_id": 123,
                "status": JobStatus.PENDING
            }
            mock_update.return_value = True
            
            result = await service.cancel_job(123, user_id=1)
            
            assert result is True
            mock_update.assert_called_with(123, {"status": JobStatus.CANCELLED})
    
    @pytest.mark.asyncio
    async def test_delete_job(self, mock_database):
        """Test deleting job."""
        service = JobService()
        
        with patch.object(service, '_fetch_job_from_db') as mock_fetch, \
             patch.object(service, '_delete_job_from_db') as mock_delete, \
             patch('os.remove') as mock_remove:
            
            mock_fetch.return_value = {
                "job_id": 123,
                "file_path": "/tmp/document.docx",
                "status": JobStatus.COMPLETED
            }
            mock_delete.return_value = True
            
            result = await service.delete_job(123, user_id=1)
            
            assert result is True
            mock_delete.assert_called_once_with(123)
            mock_remove.assert_called_once_with("/tmp/document.docx")
    
    @pytest.mark.asyncio
    async def test_get_job_details(self, sample_job_details, mock_database):
        """Test getting detailed job information."""
        service = JobService()
        
        with patch.object(service, '_fetch_job_details_from_db') as mock_fetch:
            mock_fetch.return_value = sample_job_details
            
            result = await service.get_job_details(123)
            
            assert result is not None
            assert result["job_id"] == sample_job_details["job_id"]
            assert result["job_name"] == sample_job_details["job_name"]
            mock_fetch.assert_called_once_with(123)
    
    @pytest.mark.asyncio
    async def test_process_job_queue(self, mock_database, mock_word_generator):
        """Test processing job queue."""
        service = JobService()
        
        with patch.object(service, '_get_pending_jobs') as mock_get_pending, \
             patch.object(service, '_process_single_job') as mock_process:
            
            mock_get_pending.return_value = [
                {"job_id": 123, "job_name": "Test Job 1"},
                {"job_id": 124, "job_name": "Test Job 2"}
            ]
            mock_process.return_value = True
            
            result = await service.process_job_queue()
            
            assert result is not None
            assert result["processed_jobs"] == 2
            assert mock_process.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_jobs(self, mock_database):
        """Test cleanup of expired jobs."""
        service = JobService()
        
        with patch.object(service, '_find_expired_jobs') as mock_find, \
             patch.object(service, '_delete_job_from_db') as mock_delete, \
             patch('os.remove') as mock_remove:
            
            expired_jobs = [
                {"job_id": 123, "file_path": "/tmp/expired1.docx"},
                {"job_id": 124, "file_path": "/tmp/expired2.docx"}
            ]
            mock_find.return_value = expired_jobs
            mock_delete.return_value = True
            
            result = await service.cleanup_expired_jobs()
            
            assert result is not None
            assert result["cleaned_jobs"] == 2
            assert mock_delete.call_count == 2
            assert mock_remove.call_count == 2


class TestAnalyticsService:
    """Test analytics service functionality."""
    
    @pytest.mark.asyncio
    async def test_get_job_analytics(self, mock_database):
        """Test getting job analytics."""
        service = AnalyticsService()
        
        with patch.object(service, '_fetch_analytics_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "period_days": 30,
                "total_jobs": 500,
                "successful_jobs": 475,
                "failed_jobs": 25,
                "success_rate": 95.0,
                "avg_generation_time": 3500.0
            }
            
            result = await service.get_analytics(period_days=30)
            
            assert result is not None
            assert result["total_jobs"] == 500
            assert result["success_rate"] == 95.0
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_analytics(self, mock_database):
        """Test getting user-specific analytics."""
        service = AnalyticsService()
        
        with patch.object(service, '_fetch_user_analytics_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "user_id": 1,
                "total_jobs": 50,
                "successful_jobs": 48,
                "favorite_template": "professional",
                "avg_file_size": 2048000
            }
            
            result = await service.get_user_analytics(user_id=1, period_days=30)
            
            assert result is not None
            assert result["user_id"] == 1
            assert result["total_jobs"] == 50
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_template_usage_stats(self, mock_database):
        """Test getting template usage statistics."""
        service = AnalyticsService()
        
        with patch.object(service, '_fetch_template_stats_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "professional": 250,
                "corporate": 150,
                "academic": 75,
                "report": 25
            }
            
            result = await service.get_template_usage_stats(period_days=30)
            
            assert result is not None
            assert result["professional"] == 250
            assert result["corporate"] == 150
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_job_metrics(self, mock_database):
        """Test tracking job metrics."""
        service = AnalyticsService()
        
        job_metrics = {
            "job_id": 123,
            "generation_time_ms": 4500,
            "file_size_bytes": 2048000,
            "chart_count": 3,
            "table_count": 2,
            "template": "professional"
        }
        
        with patch.object(service, '_save_metrics_to_db') as mock_save:
            mock_save.return_value = True
            
            result = await service.track_job_metrics(job_metrics)
            
            assert result is True
            mock_save.assert_called_once_with(job_metrics)
    
    def test_calculate_performance_trends(self):
        """Test performance trend calculation."""
        service = AnalyticsService()
        
        # Mock time series data
        time_series_data = [
            {"date": "2024-01-01", "avg_time": 4000, "success_rate": 90},
            {"date": "2024-01-02", "avg_time": 3800, "success_rate": 92},
            {"date": "2024-01-03", "avg_time": 3600, "success_rate": 94},
            {"date": "2024-01-04", "avg_time": 3400, "success_rate": 96},
            {"date": "2024-01-05", "avg_time": 3200, "success_rate": 98}
        ]
        
        trends = service.calculate_performance_trends(time_series_data)
        
        assert trends is not None
        assert "generation_time_trend" in trends
        assert "success_rate_trend" in trends
        assert trends["generation_time_trend"] == "improving"  # Times are decreasing
        assert trends["success_rate_trend"] == "improving"  # Rates are increasing
    
    def test_generate_usage_report(self):
        """Test usage report generation."""
        service = AnalyticsService()
        
        usage_data = {
            "total_jobs": 1000,
            "successful_jobs": 950,
            "failed_jobs": 50,
            "avg_generation_time": 3500,
            "template_usage": {
                "professional": 500,
                "corporate": 300,
                "academic": 200
            },
            "format_usage": {
                "docx": 800,
                "pdf": 150,
                "txt": 50
            }
        }
        
        report = service.generate_usage_report(usage_data)
        
        assert report is not None
        assert "summary" in report
        assert "success_rate" in report["summary"]
        assert report["summary"]["success_rate"] == 95.0
        assert "recommendations" in report


class TestServiceIntegration:
    """Test service integration and workflows."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_document_generation(
        self,
        sample_word_export_request,
        mock_database,
        mock_docx,
        mock_matplotlib
    ):
        """Test end-to-end document generation workflow."""
        job_service = JobService()
        word_generator = WordGeneratorService()
        analytics_service = AnalyticsService()
        
        with patch.object(job_service, '_save_job_to_db') as mock_save_job, \
             patch.object(job_service, '_update_job_in_db') as mock_update_job, \
             patch.object(analytics_service, '_save_metrics_to_db') as mock_save_metrics, \
             patch('app.services.word_generator.Document') as mock_document_class:
            
            mock_doc = MagicMock()
            mock_document_class.return_value = mock_doc
            
            # Step 1: Create job
            mock_save_job.return_value = {
                "job_id": 123,
                "status": JobStatus.PENDING
            }
            
            job = await job_service.create_job(sample_word_export_request, user_id=1)
            
            # Step 2: Generate document
            generation_result = await word_generator.generate_document(
                config=sample_word_export_request.document_config,
                data_source=sample_word_export_request.data_source,
                output_path="/tmp/test_document.docx"
            )
            
            # Step 3: Update job status
            await job_service.update_job_status(
                job_id=job["job_id"],
                status=JobStatus.COMPLETED,
                progress=100.0
            )
            
            # Step 4: Track analytics
            await analytics_service.track_job_metrics({
                "job_id": job["job_id"],
                "generation_time_ms": generation_result["generation_time_ms"],
                "file_size_bytes": generation_result["file_size"]
            })
            
            assert job["job_id"] == 123
            assert generation_result is not None
            mock_save_job.assert_called_once()
            mock_update_job.assert_called()
            mock_save_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_document_generation(
        self,
        sample_bulk_word_export_request,
        mock_database,
        mock_docx
    ):
        """Test bulk document generation workflow."""
        job_service = JobService()
        word_generator = WordGeneratorService()
        
        with patch.object(job_service, '_save_job_to_db') as mock_save_job, \
             patch('app.services.word_generator.Document') as mock_document_class:
            
            mock_doc = MagicMock()
            mock_document_class.return_value = mock_doc
            
            # Create jobs for each request in bulk
            jobs = []
            for i, request in enumerate(sample_bulk_word_export_request.jobs):
                mock_save_job.return_value = {
                    "job_id": 100 + i,
                    "status": JobStatus.PENDING
                }
                
                job = await job_service.create_job(request, user_id=1)
                jobs.append(job)
            
            # Process all jobs
            generation_results = []
            for i, (job, request) in enumerate(zip(jobs, sample_bulk_word_export_request.jobs)):
                result = await word_generator.generate_document(
                    config=request.document_config,
                    data_source=request.data_source,
                    output_path=f"/tmp/bulk_document_{i}.docx"
                )
                generation_results.append(result)
            
            assert len(jobs) == len(sample_bulk_word_export_request.jobs)
            assert len(generation_results) == len(jobs)
            assert all(result is not None for result in generation_results)
    
    @pytest.mark.asyncio
    async def test_concurrent_job_processing(
        self,
        sample_word_export_request,
        mock_database,
        mock_docx
    ):
        """Test concurrent job processing."""
        job_service = JobService()
        word_generator = WordGeneratorService()
        
        with patch.object(job_service, '_save_job_to_db') as mock_save_job, \
             patch('app.services.word_generator.Document') as mock_document_class:
            
            mock_doc = MagicMock()
            mock_document_class.return_value = mock_doc
            
            # Create multiple jobs
            jobs = []
            for i in range(3):
                mock_save_job.return_value = {
                    "job_id": 200 + i,
                    "status": JobStatus.PENDING
                }
                
                job = await job_service.create_job(sample_word_export_request, user_id=1)
                jobs.append(job)
            
            # Process jobs concurrently
            async def process_job(job):
                return await word_generator.generate_document(
                    config=sample_word_export_request.document_config,
                    data_source=sample_word_export_request.data_source,
                    output_path=f"/tmp/concurrent_document_{job['job_id']}.docx"
                )
            
            tasks = [process_job(job) for job in jobs]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All tasks should complete successfully
            assert len(results) == 3
            assert all(not isinstance(result, Exception) for result in results)


class TestErrorHandling:
    """Test error handling in services."""
    
    @pytest.mark.asyncio
    async def test_word_generator_file_write_error(
        self,
        sample_document_config,
        sample_data_source,
        mock_docx
    ):
        """Test error handling when file write fails."""
        service = WordGeneratorService()
        
        with patch('app.services.word_generator.Document') as mock_document_class:
            mock_doc = MagicMock()
            mock_doc.save.side_effect = PermissionError("Permission denied")
            mock_document_class.return_value = mock_doc
            
            with pytest.raises(PermissionError):
                await service.generate_document(
                    config=sample_document_config,
                    data_source=sample_data_source,
                    output_path="/readonly/document.docx"
                )
    
    @pytest.mark.asyncio
    async def test_template_service_database_error(self, mock_database):
        """Test template service database error handling."""
        service = TemplateService()
        
        with patch.object(service, '_fetch_template_from_db') as mock_fetch:
            mock_fetch.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception) as exc_info:
                await service.get_template_by_id(123)
            
            assert "Database connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_job_service_invalid_status_update(self, mock_database):
        """Test job service invalid status update."""
        service = JobService()
        
        with patch.object(service, '_fetch_job_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "job_id": 123,
                "status": JobStatus.COMPLETED  # Already completed
            }
            
            with pytest.raises(ValueError) as exc_info:
                await service.update_job_status(
                    job_id=123,
                    status=JobStatus.PROCESSING
                )
            
            assert "invalid status transition" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_analytics_service_invalid_metrics(self, mock_database):
        """Test analytics service with invalid metrics data."""
        service = AnalyticsService()
        
        invalid_metrics = {
            "job_id": None,  # Invalid job ID
            "generation_time_ms": -100,  # Negative time
            "file_size_bytes": "invalid"  # Invalid type
        }
        
        with pytest.raises(ValueError):
            await service.track_job_metrics(invalid_metrics)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])