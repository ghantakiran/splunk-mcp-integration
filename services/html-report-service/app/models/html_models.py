#!/usr/bin/env python3
"""
Pydantic models for HTML Report Service.

This module contains all data models used for API requests, responses,
and internal data structures for the HTML report service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# Enums
class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutputFormat(str, Enum):
    """Output format enumeration."""
    HTML = "html"
    PDF = "pdf"
    PNG = "png"


class Template(str, Enum):
    """Template enumeration."""
    MODERN = "modern"
    CLASSIC = "classic"
    MINIMAL = "minimal"
    DARK = "dark"
    CORPORATE = "corporate"


class ChartType(str, Enum):
    """Chart type enumeration."""
    BAR = "bar"
    COLUMN = "column"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    SUNBURST = "sunburst"
    HISTOGRAM = "histogram"


class InteractiveFeature(str, Enum):
    """Interactive feature enumeration."""
    ZOOM = "zoom"
    PAN = "pan"
    FILTER = "filter"
    DRILL_DOWN = "drill_down"
    HOVER = "hover"
    CLICK = "click"
    BRUSH = "brush"
    CROSSFILTER = "crossfilter"


class ColorScheme(str, Enum):
    """Color scheme enumeration."""
    BLUE = "blue"
    RED = "red"
    GREEN = "green"
    ORANGE = "orange"
    PURPLE = "purple"
    TEAL = "teal"
    RAINBOW = "rainbow"
    MONOCHROME = "monochrome"


# Base models
class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = True
    message: str = "Operation completed successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = False
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


# Data source models
class QueryDataSource(BaseModel):
    """Query-based data source model."""
    query: str = Field(..., description="Data query")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    connection_id: Optional[str] = Field(default=None, description="Connection identifier")


class FileDataSource(BaseModel):
    """File-based data source model."""
    file_path: str = Field(..., description="File path or URL")
    file_format: str = Field(..., pattern="^(csv|json|xlsx|xml)$", description="File format")
    sheet_name: Optional[str] = Field(default=None, description="Sheet name for Excel files")


class StaticDataSource(BaseModel):
    """Static data source model."""
    data: List[Dict[str, Any]] = Field(..., description="Static data")


class DataSource(BaseModel):
    """Data source model."""
    source_type: str = Field(..., pattern="^(query|file|static)$", description="Data source type")
    query_source: Optional[QueryDataSource] = Field(default=None, description="Query data source")
    file_source: Optional[FileDataSource] = Field(default=None, description="File data source")
    static_source: Optional[StaticDataSource] = Field(default=None, description="Static data source")
    
    @model_validator(mode='after')
    def validate_source_consistency(self):
        """Validate that the correct source is provided based on source_type."""
        source_type = self.source_type
        sources = {
            "query": self.query_source,
            "file": self.file_source,
            "static": self.static_source
        }
        
        # Check that exactly one source is provided based on source_type
        if source_type == "query" and self.query_source is None:
            raise ValueError("query_source is required when source_type is query")
        elif source_type == "file" and self.file_source is None:
            raise ValueError("file_source is required when source_type is file")
        elif source_type == "static" and self.static_source is None:
            raise ValueError("static_source is required when source_type is static")
        
        # Check that other sources are None
        for src_type, src_value in sources.items():
            if src_type != source_type and src_value is not None:
                raise ValueError(f"{src_type}_source should be None when source_type is {source_type}")
        
        return self


# Chart models
class ChartData(BaseModel):
    """Chart data model."""
    labels: List[str] = Field(..., description="Chart labels")
    datasets: List[Dict[str, Any]] = Field(..., description="Chart datasets")
    
    @field_validator("datasets")
    @classmethod
    def validate_datasets(cls, v):
        """Validate datasets structure."""
        if not v:
            raise ValueError("At least one dataset is required")
        
        for dataset in v:
            if "data" not in dataset:
                raise ValueError("Each dataset must have a 'data' field")
            if "label" not in dataset:
                raise ValueError("Each dataset must have a 'label' field")
        
        return v


class ChartConfig(BaseModel):
    """Chart configuration model."""
    chart_type: ChartType = Field(..., description="Type of chart")
    title: str = Field(default="", description="Chart title")
    width: int = Field(default=800, ge=100, le=2000, description="Chart width in pixels")
    height: int = Field(default=600, ge=100, le=1500, description="Chart height in pixels")
    color_scheme: ColorScheme = Field(default=ColorScheme.BLUE, description="Color scheme")
    interactive_features: List[InteractiveFeature] = Field(default_factory=list, description="Interactive features")
    show_legend: bool = Field(default=True, description="Show chart legend")
    show_grid: bool = Field(default=True, description="Show grid lines")
    animation_duration: int = Field(default=1000, ge=0, le=5000, description="Animation duration in ms")
    responsive: bool = Field(default=True, description="Enable responsive design")
    custom_options: Dict[str, Any] = Field(default_factory=dict, description="Custom chart options")


class Chart(BaseModel):
    """Chart model."""
    id: str = Field(..., description="Chart identifier")
    data: ChartData = Field(..., description="Chart data")
    config: ChartConfig = Field(..., description="Chart configuration")


# Table models
class TableColumn(BaseModel):
    """Table column model."""
    name: str = Field(..., description="Column name")
    label: str = Field(..., description="Column display label")
    data_type: str = Field(default="string", pattern="^(string|number|date|boolean)$", description="Data type")
    sortable: bool = Field(default=True, description="Allow sorting")
    filterable: bool = Field(default=True, description="Allow filtering")
    width: Optional[int] = Field(default=None, ge=50, le=500, description="Column width in pixels")


class TableConfig(BaseModel):
    """Table configuration model."""
    columns: List[TableColumn] = Field(..., description="Table columns")
    pagination: bool = Field(default=True, description="Enable pagination")
    page_size: int = Field(default=25, ge=5, le=100, description="Page size")
    search: bool = Field(default=True, description="Enable search")
    sorting: bool = Field(default=True, description="Enable sorting")
    filtering: bool = Field(default=True, description="Enable filtering")
    export_buttons: List[str] = Field(default=["csv", "excel", "pdf"], description="Export button types")
    responsive: bool = Field(default=True, description="Enable responsive design")
    striped: bool = Field(default=True, description="Striped rows")


class Table(BaseModel):
    """Table model."""
    id: str = Field(..., description="Table identifier")
    data: List[Dict[str, Any]] = Field(..., description="Table data")
    config: TableConfig = Field(..., description="Table configuration")


# Layout models
class LayoutSection(BaseModel):
    """Layout section model."""
    id: str = Field(..., description="Section identifier")
    title: str = Field(default="", description="Section title")
    width: int = Field(default=12, ge=1, le=12, description="Section width (1-12 columns)")
    height: Optional[int] = Field(default=None, ge=100, description="Section height in pixels")
    content_type: str = Field(..., pattern="^(chart|table|text|html)$", description="Content type")
    content_id: Optional[str] = Field(default=None, description="Content identifier")
    html_content: Optional[str] = Field(default=None, description="HTML content")
    css_classes: List[str] = Field(default_factory=list, description="CSS classes")
    custom_styles: Dict[str, str] = Field(default_factory=dict, description="Custom CSS styles")


class Layout(BaseModel):
    """Layout model."""
    sections: List[LayoutSection] = Field(..., description="Layout sections")
    container_fluid: bool = Field(default=False, description="Use fluid container")
    background_color: str = Field(default="#ffffff", description="Background color")
    custom_css: str = Field(default="", description="Custom CSS")


# Report models
class ReportMetadata(BaseModel):
    """Report metadata model."""
    title: str = Field(..., description="Report title")
    description: str = Field(default="", description="Report description")
    author: str = Field(default="", description="Report author")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    category: str = Field(default="", description="Report category")


class ReportConfig(BaseModel):
    """Report configuration model."""
    metadata: ReportMetadata = Field(..., description="Report metadata")
    template: Template = Field(default=Template.MODERN, description="Report template")
    layout: Layout = Field(..., description="Report layout")
    charts: List[Chart] = Field(default_factory=list, description="Charts")
    tables: List[Table] = Field(default_factory=list, description="Tables")
    enable_print_css: bool = Field(default=True, description="Enable print-friendly CSS")
    enable_dark_mode: bool = Field(default=False, description="Enable dark mode support")
    custom_branding: Dict[str, str] = Field(default_factory=dict, description="Custom branding")


# Request models
class HTMLReportRequest(BaseModel):
    """HTML report generation request model."""
    job_name: str = Field(..., min_length=1, max_length=255, description="Job name")
    report_config: ReportConfig = Field(..., description="Report configuration")
    data_source: DataSource = Field(..., description="Data source")
    output_format: OutputFormat = Field(default=OutputFormat.HTML, description="Output format")
    expires_in_hours: int = Field(default=24, ge=1, le=168, description="Expiration time in hours")


class BulkHTMLReportRequest(BaseModel):
    """Bulk HTML report generation request model."""
    output_format: OutputFormat = Field(default=OutputFormat.HTML, description="Output format")
    template: Template = Field(default=Template.MODERN, description="Template")
    jobs: List[HTMLReportRequest] = Field(..., min_items=1, max_items=10, description="Report jobs")


class TemplateRequest(BaseModel):
    """Template request model."""
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str = Field(default="", max_length=1000, description="Template description")
    template_type: Template = Field(..., description="Template type")
    template_data: ReportConfig = Field(..., description="Template data")
    is_default: bool = Field(default=False, description="Is default template")


# Response models
class JobResponse(BaseModel):
    """Job response model."""
    job_id: int = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Job status")
    message: str = Field(..., description="Response message")
    created_at: datetime = Field(..., description="Creation timestamp")


class JobStatusResponse(BaseModel):
    """Job status response model."""
    job_id: int = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Job status")
    progress_percentage: Optional[float] = Field(default=None, description="Progress percentage")
    current_section: Optional[str] = Field(default=None, description="Current section being processed")
    total_sections: Optional[int] = Field(default=None, description="Total number of sections")
    runtime_seconds: Optional[float] = Field(default=None, description="Runtime in seconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class JobDetailsResponse(BaseModel):
    """Job details response model."""
    job_id: int = Field(..., description="Job identifier")
    job_name: str = Field(..., description="Job name")
    status: JobStatus = Field(..., description="Job status")
    output_format: OutputFormat = Field(..., description="Output format")
    template: Template = Field(..., description="Template")
    file_path: Optional[str] = Field(default=None, description="Generated file path")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    chart_count: Optional[int] = Field(default=None, description="Number of charts")
    table_count: Optional[int] = Field(default=None, description="Number of tables")
    section_count: Optional[int] = Field(default=None, description="Number of sections")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    generation_time_ms: Optional[int] = Field(default=None, description="Generation time in milliseconds")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")


class JobListResponse(BaseModel):
    """Job list response model."""
    total: int = Field(..., description="Total number of jobs")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    jobs: List[JobDetailsResponse] = Field(..., description="List of jobs")


class AnalyticsResponse(BaseModel):
    """Analytics response model."""
    period_days: int = Field(..., description="Analysis period in days")
    total_jobs: int = Field(..., description="Total number of jobs")
    successful_jobs: int = Field(..., description="Number of successful jobs")
    failed_jobs: int = Field(..., description="Number of failed jobs")
    success_rate: float = Field(..., description="Success rate percentage")
    avg_generation_time: float = Field(..., description="Average generation time in milliseconds")
    avg_file_size: float = Field(..., description="Average file size in bytes")
    avg_chart_count: float = Field(..., description="Average chart count")
    avg_table_count: float = Field(..., description="Average table count")
    usage_by_format: Dict[str, int] = Field(..., description="Usage statistics by format")
    usage_by_template: Dict[str, int] = Field(..., description="Usage statistics by template")
    daily_usage: List[Dict[str, Any]] = Field(..., description="Daily usage statistics")


class CapabilitiesResponse(BaseModel):
    """Service capabilities response model."""
    supported_formats: List[str] = Field(..., description="Supported output formats")
    supported_templates: List[str] = Field(..., description="Supported templates")
    supported_chart_types: List[str] = Field(..., description="Supported chart types")
    supported_interactive_features: List[str] = Field(..., description="Supported interactive features")
    max_file_size_mb: int = Field(..., description="Maximum file size in MB")
    max_concurrent_jobs: int = Field(..., description="Maximum concurrent jobs")
    features: List[str] = Field(..., description="Available features")


class TemplateResponse(BaseModel):
    """Template response model."""
    template_id: int = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    template_type: Template = Field(..., description="Template type")
    is_default: bool = Field(..., description="Is default template")
    is_active: bool = Field(..., description="Is template active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TemplateListResponse(BaseModel):
    """Template list response model."""
    total: int = Field(..., description="Total number of templates")
    templates: List[TemplateResponse] = Field(..., description="List of templates")


# Export commonly used models
__all__ = [
    # Enums
    "JobStatus",
    "OutputFormat",
    "Template",
    "ChartType",
    "InteractiveFeature",
    "ColorScheme",
    
    # Base models
    "BaseResponse",
    "ErrorResponse",
    
    # Data models
    "DataSource",
    "QueryDataSource",
    "FileDataSource",
    "StaticDataSource",
    
    # Chart models
    "Chart",
    "ChartData",
    "ChartConfig",
    
    # Table models
    "Table",
    "TableColumn",
    "TableConfig",
    
    # Layout models
    "Layout",
    "LayoutSection",
    
    # Report models
    "ReportConfig",
    "ReportMetadata",
    
    # Request models
    "HTMLReportRequest",
    "BulkHTMLReportRequest",
    "TemplateRequest",
    
    # Response models
    "JobResponse",
    "JobStatusResponse",
    "JobDetailsResponse",
    "JobListResponse",
    "AnalyticsResponse",
    "CapabilitiesResponse",
    "TemplateResponse",
    "TemplateListResponse"
]