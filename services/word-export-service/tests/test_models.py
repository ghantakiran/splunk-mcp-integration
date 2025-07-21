#!/usr/bin/env python3
"""
Tests for Word Export Service models.

This module contains tests for all Pydantic models used in the Word export service,
including validation, serialization, and model relationships.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from pydantic import ValidationError

from app.models.word_models import (
    JobStatus,
    OutputFormat,
    Template,
    FontFamily,
    ColorScheme,
    ChartType,
    BaseResponse,
    ErrorResponse,
    DocumentMetadata,
    DocumentSection,
    DocumentLayout,
    ChartConfig,
    ChartData,
    Chart,
    TableColumn,
    TableConfig,
    Table,
    DocumentConfig,
    StaticDataSource,
    QueryDataSource,
    FileDataSource,
    DataSource,
    WordExportRequest,
    BulkWordExportRequest,
    JobResponse,
    JobStatusResponse,
    JobDetailsResponse,
    JobListResponse,
    AnalyticsResponse,
    CapabilitiesResponse
)


class TestEnumModels:
    """Test cases for enum models."""
    
    def test_job_status_enum_values(self):
        """Test JobStatus enum values."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"
    
    def test_output_format_enum_values(self):
        """Test OutputFormat enum values."""
        assert OutputFormat.DOCX == "docx"
        assert OutputFormat.PDF == "pdf"
        assert OutputFormat.TXT == "txt"
    
    def test_template_enum_values(self):
        """Test Template enum values."""
        assert Template.PROFESSIONAL == "professional"
        assert Template.CORPORATE == "corporate"
        assert Template.ACADEMIC == "academic"
        assert Template.REPORT == "report"
        assert Template.MINIMAL == "minimal"
    
    def test_font_family_enum_values(self):
        """Test FontFamily enum values."""
        assert FontFamily.CALIBRI == "calibri"
        assert FontFamily.ARIAL == "arial"
        assert FontFamily.TIMES_NEW_ROMAN == "times_new_roman"
        assert FontFamily.HELVETICA == "helvetica"
    
    def test_color_scheme_enum_values(self):
        """Test ColorScheme enum values."""
        assert ColorScheme.BLUE == "blue"
        assert ColorScheme.RED == "red"
        assert ColorScheme.GREEN == "green"
        assert ColorScheme.ORANGE == "orange"
        assert ColorScheme.PURPLE == "purple"
        assert ColorScheme.MONOCHROME == "monochrome"
    
    def test_chart_type_enum_values(self):
        """Test ChartType enum values."""
        assert ChartType.BAR == "bar"
        assert ChartType.LINE == "line"
        assert ChartType.PIE == "pie"
        assert ChartType.AREA == "area"
        assert ChartType.SCATTER == "scatter"
        assert ChartType.TABLE == "table"


class TestBaseModels:
    """Test cases for base models."""
    
    def test_base_response_creation(self):
        """Test BaseResponse model creation."""
        response = BaseResponse()
        
        assert response.success is True
        assert response.message == "Operation completed successfully"
        assert isinstance(response.timestamp, datetime)
    
    def test_base_response_custom_values(self):
        """Test BaseResponse with custom values."""
        custom_time = datetime.utcnow()
        response = BaseResponse(
            success=False,
            message="Custom message",
            timestamp=custom_time
        )
        
        assert response.success is False
        assert response.message == "Custom message"
        assert response.timestamp == custom_time
    
    def test_error_response_creation(self):
        """Test ErrorResponse model creation."""
        error = ErrorResponse(
            error_code="TEST_ERROR",
            error_details={"field": "value"}
        )
        
        assert error.success is False
        assert error.error_code == "TEST_ERROR"
        assert error.error_details == {"field": "value"}
    
    def test_error_response_serialization(self):
        """Test ErrorResponse serialization."""
        error = ErrorResponse(error_code="VALIDATION_ERROR")
        data = error.dict()
        
        assert data["success"] is False
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "timestamp" in data


class TestDocumentModels:
    """Test cases for document-related models."""
    
    def test_document_metadata_creation(self):
        """Test DocumentMetadata model creation."""
        metadata = DocumentMetadata(
            title="Test Document",
            subject="Test Subject",
            author="Test Author",
            company="Test Company",
            keywords=["test", "sample"],
            created_date=datetime.utcnow(),
            version="1.0"
        )
        
        assert metadata.title == "Test Document"
        assert metadata.subject == "Test Subject"
        assert metadata.author == "Test Author"
        assert metadata.company == "Test Company"
        assert metadata.keywords == ["test", "sample"]
        assert metadata.version == "1.0"
    
    def test_document_metadata_validation(self):
        """Test DocumentMetadata validation."""
        # Test empty title validation
        with pytest.raises(ValidationError):
            DocumentMetadata(
                title="",  # Empty title should be invalid
                subject="Test",
                author="Test Author"
            )
    
    def test_document_section_creation(self):
        """Test DocumentSection model creation."""
        section = DocumentSection(
            id="intro",
            title="Introduction",
            content_type="text",
            text_content="This is the introduction.",
            order=1
        )
        
        assert section.id == "intro"
        assert section.title == "Introduction"
        assert section.content_type == "text"
        assert section.text_content == "This is the introduction."
        assert section.order == 1
    
    def test_document_section_validation(self):
        """Test DocumentSection validation."""
        # Test invalid content type
        with pytest.raises(ValidationError):
            DocumentSection(
                id="section-1",
                content_type="invalid_type",
                order=1
            )
        
        # Test invalid order
        with pytest.raises(ValidationError):
            DocumentSection(
                id="section-1",
                content_type="text",
                order=0  # Order should be >= 1
            )
    
    def test_document_layout_creation(self):
        """Test DocumentLayout model creation."""
        sections = [
            DocumentSection(
                id="section-1",
                content_type="text",
                order=1
            )
        ]
        
        layout = DocumentLayout(
            sections=sections,
            page_size="A4",
            page_orientation="portrait",
            margins={"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0}
        )
        
        assert len(layout.sections) == 1
        assert layout.page_size == "A4"
        assert layout.page_orientation == "portrait"
        assert layout.margins["top"] == 1.0
    
    def test_document_layout_validation(self):
        """Test DocumentLayout validation."""
        # Test invalid page size
        with pytest.raises(ValidationError):
            DocumentLayout(
                sections=[],
                page_size="invalid_size"
            )
        
        # Test invalid page orientation
        with pytest.raises(ValidationError):
            DocumentLayout(
                sections=[],
                page_orientation="invalid_orientation"
            )


class TestChartModels:
    """Test cases for chart-related models."""
    
    def test_chart_config_creation(self):
        """Test ChartConfig model creation."""
        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Test Chart",
            width=400,
            height=300,
            show_legend=True,
            show_grid=True
        )
        
        assert config.chart_type == ChartType.BAR
        assert config.title == "Test Chart"
        assert config.width == 400
        assert config.height == 300
        assert config.show_legend is True
        assert config.show_grid is True
    
    def test_chart_config_validation(self):
        """Test ChartConfig validation."""
        # Test invalid dimensions
        with pytest.raises(ValidationError):
            ChartConfig(
                chart_type=ChartType.BAR,
                width=-100,  # Negative width should be invalid
                height=300
            )
        
        with pytest.raises(ValidationError):
            ChartConfig(
                chart_type=ChartType.BAR,
                width=400,
                height=0  # Zero height should be invalid
            )
    
    def test_chart_data_creation(self):
        """Test ChartData model creation."""
        chart_data = ChartData(
            labels=["Q1", "Q2", "Q3", "Q4"],
            datasets=[
                {
                    "label": "Sales",
                    "data": [100, 150, 120, 200],
                    "backgroundColor": "#007bff"
                }
            ]
        )
        
        assert chart_data.labels == ["Q1", "Q2", "Q3", "Q4"]
        assert len(chart_data.datasets) == 1
        assert chart_data.datasets[0]["label"] == "Sales"
        assert chart_data.datasets[0]["data"] == [100, 150, 120, 200]
    
    def test_chart_creation(self):
        """Test Chart model creation."""
        chart_config = ChartConfig(
            chart_type=ChartType.LINE,
            title="Test Chart"
        )
        
        chart_data = ChartData(
            labels=["A", "B", "C"],
            datasets=[{"label": "Test", "data": [1, 2, 3]}]
        )
        
        chart = Chart(
            id="chart-1",
            config=chart_config,
            data=chart_data
        )
        
        assert chart.id == "chart-1"
        assert chart.config.chart_type == ChartType.LINE
        assert chart.data.labels == ["A", "B", "C"]


class TestTableModels:
    """Test cases for table-related models."""
    
    def test_table_column_creation(self):
        """Test TableColumn model creation."""
        column = TableColumn(
            name="sales",
            label="Sales Amount",
            data_type="number",
            width=120
        )
        
        assert column.name == "sales"
        assert column.label == "Sales Amount"
        assert column.data_type == "number"
        assert column.width == 120
    
    def test_table_column_validation(self):
        """Test TableColumn validation."""
        # Test invalid data type
        with pytest.raises(ValidationError):
            TableColumn(
                name="test",
                label="Test",
                data_type="invalid_type"
            )
        
        # Test invalid width
        with pytest.raises(ValidationError):
            TableColumn(
                name="test",
                label="Test",
                width=-50
            )
    
    def test_table_config_creation(self):
        """Test TableConfig model creation."""
        columns = [
            TableColumn(name="id", label="ID", data_type="number"),
            TableColumn(name="name", label="Name", data_type="string")
        ]
        
        config = TableConfig(
            title="Test Table",
            columns=columns,
            show_header=True,
            stripe_rows=True
        )
        
        assert config.title == "Test Table"
        assert len(config.columns) == 2
        assert config.show_header is True
        assert config.stripe_rows is True
    
    def test_table_creation(self):
        """Test Table model creation."""
        columns = [TableColumn(name="id", label="ID", data_type="number")]
        config = TableConfig(title="Test", columns=columns)
        data = [{"id": 1}, {"id": 2}]
        
        table = Table(
            id="table-1",
            config=config,
            data=data
        )
        
        assert table.id == "table-1"
        assert table.config.title == "Test"
        assert len(table.data) == 2


class TestDataSourceModels:
    """Test cases for data source models."""
    
    def test_static_data_source_creation(self):
        """Test StaticDataSource model creation."""
        data_source = StaticDataSource(
            data={
                "charts": [{"name": "Sales", "values": [100, 200]}],
                "metadata": {"created": "2024-01-01"}
            }
        )
        
        assert "charts" in data_source.data
        assert "metadata" in data_source.data
    
    def test_query_data_source_creation(self):
        """Test QueryDataSource model creation."""
        data_source = QueryDataSource(
            query="SELECT * FROM sales WHERE date >= ?",
            parameters={"start_date": "2024-01-01"},
            connection_id="db-1"
        )
        
        assert "SELECT" in data_source.query
        assert data_source.parameters["start_date"] == "2024-01-01"
        assert data_source.connection_id == "db-1"
    
    def test_query_data_source_validation(self):
        """Test QueryDataSource validation."""
        # Test empty query
        with pytest.raises(ValidationError):
            QueryDataSource(query="")
    
    def test_file_data_source_creation(self):
        """Test FileDataSource model creation."""
        data_source = FileDataSource(
            file_path="/tmp/data.csv",
            file_format="csv",
            has_header=True,
            delimiter=",",
            encoding="utf-8"
        )
        
        assert data_source.file_path == "/tmp/data.csv"
        assert data_source.file_format == "csv"
        assert data_source.has_header is True
        assert data_source.delimiter == ","
        assert data_source.encoding == "utf-8"
    
    def test_data_source_union_model(self):
        """Test DataSource union model."""
        # Test with static source
        static_source = StaticDataSource(data={"test": "data"})
        data_source = DataSource(static_source=static_source)
        
        assert data_source.static_source is not None
        assert data_source.query_source is None
        assert data_source.file_source is None
        
        # Test with query source
        query_source = QueryDataSource(query="SELECT 1")
        data_source = DataSource(query_source=query_source)
        
        assert data_source.static_source is None
        assert data_source.query_source is not None
        assert data_source.file_source is None


class TestRequestModels:
    """Test cases for request models."""
    
    def test_word_export_request_creation(self, sample_document_config, sample_data_source):
        """Test WordExportRequest model creation."""
        request = WordExportRequest(
            job_name="Test Document Job",
            document_config=sample_document_config,
            data_source=sample_data_source,
            output_format=OutputFormat.DOCX,
            expires_in_hours=24
        )
        
        assert request.job_name == "Test Document Job"
        assert request.output_format == OutputFormat.DOCX
        assert request.expires_in_hours == 24
        assert request.document_config is not None
        assert request.data_source is not None
    
    def test_word_export_request_validation(self, sample_document_config, sample_data_source):
        """Test WordExportRequest validation."""
        # Test invalid expiration time
        with pytest.raises(ValidationError):
            WordExportRequest(
                job_name="Test",
                document_config=sample_document_config,
                data_source=sample_data_source,
                expires_in_hours=0  # Should be > 0
            )
        
        # Test very long expiration time
        with pytest.raises(ValidationError):
            WordExportRequest(
                job_name="Test",
                document_config=sample_document_config,
                data_source=sample_data_source,
                expires_in_hours=8760 + 1  # > 1 year should be invalid
            )
    
    def test_bulk_word_export_request_creation(self, sample_word_export_request):
        """Test BulkWordExportRequest model creation."""
        bulk_request = BulkWordExportRequest(
            jobs=[sample_word_export_request, sample_word_export_request],
            output_format=OutputFormat.PDF,
            template=Template.CORPORATE
        )
        
        assert len(bulk_request.jobs) == 2
        assert bulk_request.output_format == OutputFormat.PDF
        assert bulk_request.template == Template.CORPORATE
    
    def test_bulk_word_export_request_validation(self):
        """Test BulkWordExportRequest validation."""
        # Test empty jobs list
        with pytest.raises(ValidationError):
            BulkWordExportRequest(
                jobs=[],  # Empty list should be invalid
                output_format=OutputFormat.DOCX,
                template=Template.PROFESSIONAL
            )


class TestResponseModels:
    """Test cases for response models."""
    
    def test_job_response_creation(self):
        """Test JobResponse model creation."""
        response = JobResponse(
            job_id=123,
            status=JobStatus.PENDING,
            message="Job created successfully",
            created_at=datetime.utcnow()
        )
        
        assert response.job_id == 123
        assert response.status == JobStatus.PENDING
        assert response.message == "Job created successfully"
        assert isinstance(response.created_at, datetime)
    
    def test_job_status_response_creation(self):
        """Test JobStatusResponse model creation."""
        response = JobStatusResponse(
            job_id=123,
            status=JobStatus.PROCESSING,
            progress_percentage=45.5,
            current_step="Generating charts",
            total_steps=5,
            runtime_seconds=120.5
        )
        
        assert response.job_id == 123
        assert response.status == JobStatus.PROCESSING
        assert response.progress_percentage == 45.5
        assert response.current_step == "Generating charts"
        assert response.total_steps == 5
        assert response.runtime_seconds == 120.5
    
    def test_job_details_response_creation(self):
        """Test JobDetailsResponse model creation."""
        now = datetime.utcnow()
        response = JobDetailsResponse(
            job_id=123,
            job_name="Test Document",
            status=JobStatus.COMPLETED,
            output_format=OutputFormat.DOCX,
            template=Template.PROFESSIONAL,
            file_path="/tmp/document.docx",
            file_size=1024000,
            page_count=5,
            chart_count=2,
            table_count=1,
            generation_time_ms=4500,
            created_at=now,
            started_at=now,
            completed_at=now + timedelta(minutes=5),
            expires_at=now + timedelta(hours=24)
        )
        
        assert response.job_id == 123
        assert response.job_name == "Test Document"
        assert response.status == JobStatus.COMPLETED
        assert response.file_size == 1024000
        assert response.page_count == 5
        assert response.chart_count == 2
        assert response.table_count == 1
    
    def test_job_list_response_creation(self):
        """Test JobListResponse model creation."""
        job = JobDetailsResponse(
            job_id=1,
            job_name="Test",
            status=JobStatus.COMPLETED,
            output_format=OutputFormat.DOCX,
            template=Template.PROFESSIONAL,
            created_at=datetime.utcnow()
        )
        
        response = JobListResponse(
            total=100,
            page=1,
            page_size=20,
            jobs=[job]
        )
        
        assert response.total == 100
        assert response.page == 1
        assert response.page_size == 20
        assert len(response.jobs) == 1
    
    def test_analytics_response_creation(self):
        """Test AnalyticsResponse model creation."""
        response = AnalyticsResponse(
            period_days=30,
            total_jobs=500,
            successful_jobs=475,
            failed_jobs=25,
            success_rate=95.0,
            avg_generation_time=3500.0,
            avg_file_size=2048000.0,
            avg_page_count=5.2,
            avg_chart_count=1.8,
            avg_table_count=1.2,
            usage_by_format={"docx": 400, "pdf": 80, "txt": 20},
            usage_by_template={"professional": 300, "corporate": 150, "academic": 50},
            daily_usage=[
                {"date": "2024-01-01", "count": 15},
                {"date": "2024-01-02", "count": 20}
            ]
        )
        
        assert response.period_days == 30
        assert response.total_jobs == 500
        assert response.success_rate == 95.0
        assert response.usage_by_format["docx"] == 400
        assert len(response.daily_usage) == 2
    
    def test_capabilities_response_creation(self):
        """Test CapabilitiesResponse model creation."""
        response = CapabilitiesResponse(
            supported_formats=["docx", "pdf", "txt"],
            supported_templates=["professional", "corporate", "academic"],
            supported_chart_types=["bar", "line", "pie"],
            max_file_size_mb=50,
            max_concurrent_jobs=10,
            supported_fonts=["Calibri", "Arial", "Times New Roman"],
            features=[
                "Chart embedding",
                "Table formatting",
                "Custom templates"
            ]
        )
        
        assert "docx" in response.supported_formats
        assert "professional" in response.supported_templates
        assert "bar" in response.supported_chart_types
        assert "Calibri" in response.supported_fonts
        assert response.max_file_size_mb == 50
        assert response.max_concurrent_jobs == 10
        assert len(response.features) == 3


class TestDocumentConfigModel:
    """Test cases for DocumentConfig model."""
    
    def test_document_config_creation(
        self,
        sample_document_metadata,
        sample_document_layout
    ):
        """Test DocumentConfig model creation."""
        config = DocumentConfig(
            metadata=sample_document_metadata,
            template=Template.PROFESSIONAL,
            layout=sample_document_layout,
            font_family=FontFamily.CALIBRI,
            font_size=12,
            color_scheme=ColorScheme.BLUE,
            charts=[],
            tables=[]
        )
        
        assert config.metadata.title == "Test Document"
        assert config.template == Template.PROFESSIONAL
        assert config.font_family == FontFamily.CALIBRI
        assert config.font_size == 12
        assert config.color_scheme == ColorScheme.BLUE
        assert isinstance(config.charts, list)
        assert isinstance(config.tables, list)
    
    def test_document_config_validation(
        self,
        sample_document_metadata,
        sample_document_layout
    ):
        """Test DocumentConfig validation."""
        # Test invalid font size
        with pytest.raises(ValidationError):
            DocumentConfig(
                metadata=sample_document_metadata,
                template=Template.PROFESSIONAL,
                layout=sample_document_layout,
                font_size=0  # Font size should be > 0
            )
        
        # Test very large font size
        with pytest.raises(ValidationError):
            DocumentConfig(
                metadata=sample_document_metadata,
                template=Template.PROFESSIONAL,
                layout=sample_document_layout,
                font_size=100  # Font size should be reasonable
            )
    
    def test_document_config_with_charts_and_tables(
        self,
        sample_document_metadata,
        sample_document_layout,
        sample_chart,
        sample_table
    ):
        """Test DocumentConfig with charts and tables."""
        config = DocumentConfig(
            metadata=sample_document_metadata,
            template=Template.PROFESSIONAL,
            layout=sample_document_layout,
            charts=[sample_chart],
            tables=[sample_table]
        )
        
        assert len(config.charts) == 1
        assert len(config.tables) == 1
        assert config.charts[0].id == "chart-1"
        assert config.tables[0].id == "table-1"


class TestModelSerialization:
    """Test cases for model serialization and deserialization."""
    
    def test_chart_config_serialization(self):
        """Test ChartConfig serialization."""
        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Test Chart",
            width=400,
            height=300
        )
        
        data = config.dict()
        assert data["chart_type"] == "bar"
        assert data["title"] == "Test Chart"
        assert data["width"] == 400
        assert data["height"] == 300
    
    def test_request_deserialization(self, sample_document_config, sample_data_source):
        """Test request model deserialization."""
        request_data = {
            "job_name": "Test Document",
            "document_config": sample_document_config.dict(),
            "data_source": sample_data_source.dict(),
            "output_format": "docx",
            "expires_in_hours": 24
        }
        
        request = WordExportRequest(**request_data)
        assert request.job_name == "Test Document"
        assert request.output_format == OutputFormat.DOCX
    
    def test_json_serialization(self, sample_word_export_request):
        """Test JSON serialization."""
        json_str = sample_word_export_request.json()
        assert isinstance(json_str, str)
        assert "job_name" in json_str
        assert "document_config" in json_str
    
    def test_dict_conversion(self, sample_word_export_request):
        """Test dictionary conversion."""
        data = sample_word_export_request.dict()
        assert isinstance(data, dict)
        assert "job_name" in data
        assert isinstance(data["document_config"], dict)


class TestModelDefaults:
    """Test cases for model default values."""
    
    def test_document_section_defaults(self):
        """Test DocumentSection default values."""
        section = DocumentSection(
            id="test",
            content_type="text",
            order=1
        )
        
        assert section.title is None
        assert section.text_content is None
        assert section.chart_id is None
        assert section.table_id is None
    
    def test_chart_config_defaults(self):
        """Test ChartConfig default values."""
        config = ChartConfig(chart_type=ChartType.BAR)
        
        assert config.title is None
        assert config.width == 400  # Default width
        assert config.height == 300  # Default height
        assert config.show_legend is True
        assert config.show_grid is True
    
    def test_table_column_defaults(self):
        """Test TableColumn default values."""
        column = TableColumn(
            name="test",
            label="Test",
            data_type="string"
        )
        
        assert column.width is None
    
    def test_document_layout_defaults(self):
        """Test DocumentLayout default values."""
        layout = DocumentLayout(sections=[])
        
        assert layout.page_size == "A4"
        assert layout.page_orientation == "portrait"
        assert layout.margins == {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0}
    
    def test_document_config_defaults(self, sample_document_metadata):
        """Test DocumentConfig default values."""
        config = DocumentConfig(
            metadata=sample_document_metadata,
            layout=DocumentLayout(sections=[])
        )
        
        assert config.template == Template.PROFESSIONAL
        assert config.font_family == FontFamily.CALIBRI
        assert config.font_size == 11
        assert config.color_scheme == ColorScheme.BLUE
        assert config.charts == []
        assert config.tables == []