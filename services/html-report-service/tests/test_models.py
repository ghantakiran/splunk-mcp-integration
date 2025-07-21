#!/usr/bin/env python3
"""
Tests for HTML Report Service models.

This module contains tests for all Pydantic models used in the HTML report service,
including validation, serialization, and model relationships.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from pydantic import ValidationError

from app.models.html_models import (
    JobStatus,
    OutputFormat,
    Template,
    ChartType,
    InteractiveFeature,
    ColorScheme,
    BaseResponse,
    ErrorResponse,
    Metadata,
    CustomBranding,
    ChartConfig,
    ChartData,
    ChartDataset,
    Chart,
    TableColumn,
    TableConfig,
    Table,
    LayoutSection,
    Layout,
    ReportConfig,
    StaticDataSource,
    QueryDataSource,
    FileDataSource,
    DataSource,
    HTMLReportRequest,
    BulkHTMLReportRequest,
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
        assert OutputFormat.HTML == "html"
        assert OutputFormat.PDF == "pdf"
        assert OutputFormat.PNG == "png"
    
    def test_template_enum_values(self):
        """Test Template enum values."""
        assert Template.MODERN == "modern"
        assert Template.CLASSIC == "classic"
        assert Template.MINIMAL == "minimal"
        assert Template.DARK == "dark"
        assert Template.CORPORATE == "corporate"
    
    def test_chart_type_enum_values(self):
        """Test ChartType enum values."""
        assert ChartType.BAR == "bar"
        assert ChartType.COLUMN == "column"
        assert ChartType.LINE == "line"
        assert ChartType.PIE == "pie"
        assert ChartType.AREA == "area"
        assert ChartType.SCATTER == "scatter"
        assert ChartType.HEATMAP == "heatmap"
        assert ChartType.TREEMAP == "treemap"
        assert ChartType.SUNBURST == "sunburst"
        assert ChartType.HISTOGRAM == "histogram"
    
    def test_interactive_feature_enum_values(self):
        """Test InteractiveFeature enum values."""
        assert InteractiveFeature.ZOOM == "zoom"
        assert InteractiveFeature.PAN == "pan"
        assert InteractiveFeature.FILTER == "filter"
        assert InteractiveFeature.DRILL_DOWN == "drill_down"
        assert InteractiveFeature.HOVER == "hover"
        assert InteractiveFeature.CLICK == "click"
        assert InteractiveFeature.BRUSH == "brush"
        assert InteractiveFeature.CROSSFILTER == "crossfilter"
    
    def test_color_scheme_enum_values(self):
        """Test ColorScheme enum values."""
        assert ColorScheme.BLUE == "blue"
        assert ColorScheme.RED == "red"
        assert ColorScheme.GREEN == "green"
        assert ColorScheme.ORANGE == "orange"
        assert ColorScheme.PURPLE == "purple"
        assert ColorScheme.TEAL == "teal"
        assert ColorScheme.RAINBOW == "rainbow"
        assert ColorScheme.MONOCHROME == "monochrome"


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


class TestMetadataModels:
    """Test cases for metadata models."""
    
    def test_metadata_creation(self):
        """Test Metadata model creation."""
        metadata = Metadata(
            title="Test Report",
            description="A test report",
            author="Test Author",
            created_date=datetime.utcnow(),
            version="1.0",
            tags=["test", "sample"]
        )
        
        assert metadata.title == "Test Report"
        assert metadata.description == "A test report"
        assert metadata.author == "Test Author"
        assert metadata.version == "1.0"
        assert metadata.tags == ["test", "sample"]
    
    def test_metadata_validation(self):
        """Test Metadata validation."""
        # Test empty title validation
        with pytest.raises(ValidationError):
            Metadata(
                title="",  # Empty title should be invalid
                description="Test",
                author="Test Author"
            )
    
    def test_custom_branding_creation(self):
        """Test CustomBranding model creation."""
        branding = CustomBranding(
            logo_url="https://example.com/logo.png",
            primary_color="#007bff",
            secondary_color="#6c757d",
            accent_color="#28a745",
            font_family="Arial, sans-serif"
        )
        
        assert branding.logo_url == "https://example.com/logo.png"
        assert branding.primary_color == "#007bff"
        assert branding.font_family == "Arial, sans-serif"
    
    def test_custom_branding_validation(self):
        """Test CustomBranding validation."""
        # Test invalid URL
        with pytest.raises(ValidationError):
            CustomBranding(
                logo_url="invalid-url",
                primary_color="#007bff"
            )
        
        # Test invalid color format
        with pytest.raises(ValidationError):
            CustomBranding(
                primary_color="invalid-color"
            )


class TestChartModels:
    """Test cases for chart-related models."""
    
    def test_chart_dataset_creation(self):
        """Test ChartDataset model creation."""
        dataset = ChartDataset(
            label="Sales Data",
            data=[100, 150, 120, 200],
            backgroundColor="#007bff",
            borderColor="#0056b3",
            borderWidth=2
        )
        
        assert dataset.label == "Sales Data"
        assert dataset.data == [100, 150, 120, 200]
        assert dataset.backgroundColor == "#007bff"
        assert dataset.borderWidth == 2
    
    def test_chart_data_creation(self):
        """Test ChartData model creation."""
        chart_data = ChartData(
            labels=["Q1", "Q2", "Q3", "Q4"],
            datasets=[
                ChartDataset(
                    label="Sales",
                    data=[100, 150, 120, 200]
                )
            ]
        )
        
        assert chart_data.labels == ["Q1", "Q2", "Q3", "Q4"]
        assert len(chart_data.datasets) == 1
        assert chart_data.datasets[0].label == "Sales"
    
    def test_chart_config_creation(self):
        """Test ChartConfig model creation."""
        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Test Chart",
            color_scheme=ColorScheme.BLUE,
            width=800,
            height=400,
            show_legend=True,
            show_grid=True,
            responsive=True,
            interactive_features=[InteractiveFeature.ZOOM, InteractiveFeature.HOVER]
        )
        
        assert config.chart_type == ChartType.BAR
        assert config.title == "Test Chart"
        assert config.width == 800
        assert config.height == 400
        assert InteractiveFeature.ZOOM in config.interactive_features
    
    def test_chart_config_validation(self):
        """Test ChartConfig validation."""
        # Test invalid dimensions
        with pytest.raises(ValidationError):
            ChartConfig(
                chart_type=ChartType.BAR,
                width=-100,  # Negative width should be invalid
                height=400
            )
        
        with pytest.raises(ValidationError):
            ChartConfig(
                chart_type=ChartType.BAR,
                width=100,
                height=0  # Zero height should be invalid
            )
    
    def test_chart_creation(self):
        """Test Chart model creation."""
        chart_data = ChartData(
            labels=["A", "B", "C"],
            datasets=[ChartDataset(label="Test", data=[1, 2, 3])]
        )
        
        chart_config = ChartConfig(
            chart_type=ChartType.LINE,
            title="Test Chart"
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
            width=120,
            sortable=True,
            filterable=True
        )
        
        assert column.name == "sales"
        assert column.label == "Sales Amount"
        assert column.data_type == "number"
        assert column.width == 120
        assert column.sortable is True
        assert column.filterable is True
    
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
            pagination=True,
            page_size=25,
            search=True,
            sorting=True,
            responsive=True,
            striped=True,
            export_buttons=["copy", "csv", "excel"]
        )
        
        assert config.title == "Test Table"
        assert len(config.columns) == 2
        assert config.page_size == 25
        assert "csv" in config.export_buttons
    
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


class TestLayoutModels:
    """Test cases for layout-related models."""
    
    def test_layout_section_creation(self):
        """Test LayoutSection model creation."""
        section = LayoutSection(
            id="section-1",
            title="Chart Section",
            content_type="chart",
            content_id="chart-1",
            width=12,
            height=400,
            css_classes=["chart-container"],
            custom_styles={"margin": "10px"}
        )
        
        assert section.id == "section-1"
        assert section.title == "Chart Section"
        assert section.content_type == "chart"
        assert section.content_id == "chart-1"
        assert section.width == 12
        assert section.height == 400
        assert "chart-container" in section.css_classes
        assert section.custom_styles["margin"] == "10px"
    
    def test_layout_section_validation(self):
        """Test LayoutSection validation."""
        # Test invalid width
        with pytest.raises(ValidationError):
            LayoutSection(
                id="section-1",
                content_type="chart",
                width=13  # Width > 12 should be invalid for Bootstrap grid
            )
        
        # Test invalid content type
        with pytest.raises(ValidationError):
            LayoutSection(
                id="section-1",
                content_type="invalid_type",
                width=6
            )
    
    def test_layout_creation(self):
        """Test Layout model creation."""
        sections = [
            LayoutSection(
                id="section-1",
                content_type="chart",
                width=6
            ),
            LayoutSection(
                id="section-2",
                content_type="table",
                width=6
            )
        ]
        
        layout = Layout(
            title="Test Layout",
            sections=sections,
            grid_system="bootstrap",
            responsive=True
        )
        
        assert layout.title == "Test Layout"
        assert len(layout.sections) == 2
        assert layout.grid_system == "bootstrap"
        assert layout.responsive is True


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
    
    def test_html_report_request_creation(self, sample_report_config, sample_data_source):
        """Test HTMLReportRequest model creation."""
        request = HTMLReportRequest(
            job_name="Test Report Job",
            report_config=sample_report_config,
            data_source=sample_data_source,
            output_format=OutputFormat.HTML,
            expires_in_hours=24
        )
        
        assert request.job_name == "Test Report Job"
        assert request.output_format == OutputFormat.HTML
        assert request.expires_in_hours == 24
        assert request.report_config is not None
        assert request.data_source is not None
    
    def test_html_report_request_validation(self, sample_report_config, sample_data_source):
        """Test HTMLReportRequest validation."""
        # Test invalid expiration time
        with pytest.raises(ValidationError):
            HTMLReportRequest(
                job_name="Test",
                report_config=sample_report_config,
                data_source=sample_data_source,
                expires_in_hours=0  # Should be > 0
            )
        
        # Test very long expiration time
        with pytest.raises(ValidationError):
            HTMLReportRequest(
                job_name="Test",
                report_config=sample_report_config,
                data_source=sample_data_source,
                expires_in_hours=8760 + 1  # > 1 year should be invalid
            )
    
    def test_bulk_html_report_request_creation(self, sample_html_report_request):
        """Test BulkHTMLReportRequest model creation."""
        bulk_request = BulkHTMLReportRequest(
            jobs=[sample_html_report_request, sample_html_report_request],
            output_format=OutputFormat.PDF,
            template=Template.DARK
        )
        
        assert len(bulk_request.jobs) == 2
        assert bulk_request.output_format == OutputFormat.PDF
        assert bulk_request.template == Template.DARK
    
    def test_bulk_html_report_request_validation(self):
        """Test BulkHTMLReportRequest validation."""
        # Test empty jobs list
        with pytest.raises(ValidationError):
            BulkHTMLReportRequest(
                jobs=[],  # Empty list should be invalid
                output_format=OutputFormat.HTML,
                template=Template.MODERN
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
            current_section="Charts",
            total_sections=5,
            runtime_seconds=120.5
        )
        
        assert response.job_id == 123
        assert response.status == JobStatus.PROCESSING
        assert response.progress_percentage == 45.5
        assert response.current_section == "Charts"
        assert response.total_sections == 5
        assert response.runtime_seconds == 120.5
    
    def test_job_details_response_creation(self):
        """Test JobDetailsResponse model creation."""
        now = datetime.utcnow()
        response = JobDetailsResponse(
            job_id=123,
            job_name="Test Report",
            status=JobStatus.COMPLETED,
            output_format=OutputFormat.HTML,
            template=Template.MODERN,
            file_path="/tmp/report.html",
            file_size=1024000,
            chart_count=3,
            table_count=2,
            section_count=5,
            generation_time_ms=4500,
            created_at=now,
            started_at=now,
            completed_at=now + timedelta(minutes=5),
            expires_at=now + timedelta(hours=24)
        )
        
        assert response.job_id == 123
        assert response.job_name == "Test Report"
        assert response.status == JobStatus.COMPLETED
        assert response.file_size == 1024000
        assert response.chart_count == 3
        assert response.table_count == 2
    
    def test_job_list_response_creation(self):
        """Test JobListResponse model creation."""
        job = JobDetailsResponse(
            job_id=1,
            job_name="Test",
            status=JobStatus.COMPLETED,
            output_format=OutputFormat.HTML,
            template=Template.MODERN,
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
            avg_chart_count=2.5,
            avg_table_count=1.8,
            usage_by_format={"html": 400, "pdf": 80, "png": 20},
            usage_by_template={"modern": 300, "classic": 150, "minimal": 50},
            daily_usage=[
                {"date": "2024-01-01", "count": 15},
                {"date": "2024-01-02", "count": 20}
            ]
        )
        
        assert response.period_days == 30
        assert response.total_jobs == 500
        assert response.success_rate == 95.0
        assert response.usage_by_format["html"] == 400
        assert len(response.daily_usage) == 2
    
    def test_capabilities_response_creation(self):
        """Test CapabilitiesResponse model creation."""
        response = CapabilitiesResponse(
            supported_formats=["html", "pdf", "png"],
            supported_templates=["modern", "classic", "minimal"],
            supported_chart_types=["bar", "line", "pie"],
            supported_interactive_features=["zoom", "pan", "hover"],
            max_file_size_mb=50,
            max_concurrent_jobs=10,
            features=[
                "Interactive charts",
                "Responsive tables",
                "Custom templates"
            ]
        )
        
        assert "html" in response.supported_formats
        assert "modern" in response.supported_templates
        assert "bar" in response.supported_chart_types
        assert "zoom" in response.supported_interactive_features
        assert response.max_file_size_mb == 50
        assert response.max_concurrent_jobs == 10
        assert len(response.features) == 3


class TestModelSerialization:
    """Test cases for model serialization and deserialization."""
    
    def test_chart_config_serialization(self):
        """Test ChartConfig serialization."""
        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Test Chart",
            interactive_features=[InteractiveFeature.ZOOM]
        )
        
        data = config.dict()
        assert data["chart_type"] == "bar"
        assert data["title"] == "Test Chart"
        assert data["interactive_features"] == ["zoom"]
    
    def test_request_deserialization(self, sample_report_config, sample_data_source):
        """Test request model deserialization."""
        request_data = {
            "job_name": "Test Report",
            "report_config": sample_report_config.dict(),
            "data_source": sample_data_source.dict(),
            "output_format": "html",
            "expires_in_hours": 24
        }
        
        request = HTMLReportRequest(**request_data)
        assert request.job_name == "Test Report"
        assert request.output_format == OutputFormat.HTML
    
    def test_json_serialization(self, sample_html_report_request):
        """Test JSON serialization."""
        json_str = sample_html_report_request.json()
        assert isinstance(json_str, str)
        assert "job_name" in json_str
        assert "report_config" in json_str
    
    def test_dict_conversion(self, sample_html_report_request):
        """Test dictionary conversion."""
        data = sample_html_report_request.dict()
        assert isinstance(data, dict)
        assert "job_name" in data
        assert isinstance(data["report_config"], dict)