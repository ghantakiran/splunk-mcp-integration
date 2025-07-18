#!/usr/bin/env python3
"""
Pydantic models for PowerPoint Export Service.

This module contains all data models used for API requests, responses,
and internal data structures for the PowerPoint export service.
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
    PPTX = "pptx"
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"


class Theme(str, Enum):
    """Theme enumeration."""
    OFFICE = "office"
    MODERN = "modern"
    COLORFUL = "colorful"
    DARK = "dark"
    MINIMAL = "minimal"


class SlideType(str, Enum):
    """Slide type enumeration."""
    TITLE = "title"
    CONTENT = "content"
    TWO_CONTENT = "two_content"
    CHART = "chart"
    IMAGE = "image"
    TABLE = "table"
    BLANK = "blank"
    SECTION_HEADER = "section_header"


class LayoutType(str, Enum):
    """Layout type enumeration."""
    TITLE_SLIDE = "title_slide"
    TITLE_AND_CONTENT = "title_and_content"
    TWO_CONTENT = "two_content"
    COMPARISON = "comparison"
    TITLE_ONLY = "title_only"
    BLANK = "blank"
    CONTENT_WITH_CAPTION = "content_with_caption"
    PICTURE_WITH_CAPTION = "picture_with_caption"


class AnimationType(str, Enum):
    """Animation type enumeration."""
    FADE = "fade"
    SLIDE = "slide"
    ZOOM = "zoom"
    FLIP = "flip"
    NONE = "none"


class TransitionType(str, Enum):
    """Transition type enumeration."""
    FADE = "fade"
    SLIDE = "slide"
    PUSH = "push"
    COVER = "cover"
    UNCOVER = "uncover"
    NONE = "none"


class ChartType(str, Enum):
    """Chart type enumeration."""
    BAR = "bar"
    COLUMN = "column"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    DOUGHNUT = "doughnut"
    RADAR = "radar"


class ColorScheme(str, Enum):
    """Color scheme enumeration."""
    BLUE = "blue"
    RED = "red"
    GREEN = "green"
    ORANGE = "orange"
    PURPLE = "purple"
    TEAL = "teal"


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


# Position and size models
class Position(BaseModel):
    """Position model for slide elements."""
    x: float = Field(..., description="X coordinate in inches")
    y: float = Field(..., description="Y coordinate in inches")


class Size(BaseModel):
    """Size model for slide elements."""
    width: float = Field(..., description="Width in inches")
    height: float = Field(..., description="Height in inches")


class Rectangle(BaseModel):
    """Rectangle model combining position and size."""
    x: float = Field(..., description="X coordinate in inches")
    y: float = Field(..., description="Y coordinate in inches")
    width: float = Field(..., description="Width in inches")
    height: float = Field(..., description="Height in inches")


# Font and style models
class FontStyle(BaseModel):
    """Font style model."""
    family: str = Field(default="Calibri", description="Font family")
    size: int = Field(default=18, ge=8, le=72, description="Font size in points")
    bold: bool = Field(default=False, description="Bold font")
    italic: bool = Field(default=False, description="Italic font")
    underline: bool = Field(default=False, description="Underlined font")
    color: str = Field(default="#000000", description="Font color in hex format")


class TextStyle(BaseModel):
    """Text style model."""
    font: FontStyle = Field(default_factory=FontStyle)
    alignment: str = Field(default="left", pattern="^(left|center|right|justify)$")
    line_spacing: float = Field(default=1.0, ge=0.5, le=3.0)
    paragraph_spacing: float = Field(default=0.0, ge=0.0, le=72.0)


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
    show_legend: bool = Field(default=True, description="Show chart legend")
    show_data_labels: bool = Field(default=False, description="Show data labels")
    color_scheme: ColorScheme = Field(default=ColorScheme.BLUE, description="Color scheme")
    background_color: str = Field(default="#FFFFFF", description="Background color")
    border_color: str = Field(default="#CCCCCC", description="Border color")
    border_width: int = Field(default=1, ge=0, le=10, description="Border width")
    
    # Axis configuration
    x_axis_title: str = Field(default="", description="X-axis title")
    y_axis_title: str = Field(default="", description="Y-axis title")
    show_grid: bool = Field(default=True, description="Show grid lines")
    
    # Animation configuration
    animate: bool = Field(default=True, description="Enable chart animation")
    animation_duration: int = Field(default=1000, ge=0, le=5000, description="Animation duration in ms")


class Chart(BaseModel):
    """Chart model."""
    data: ChartData = Field(..., description="Chart data")
    config: ChartConfig = Field(..., description="Chart configuration")
    position: Rectangle = Field(..., description="Chart position and size")


# Text and content models
class TextContent(BaseModel):
    """Text content model."""
    text: str = Field(..., description="Text content")
    style: TextStyle = Field(default_factory=TextStyle, description="Text style")
    position: Rectangle = Field(..., description="Text position and size")


class ImageContent(BaseModel):
    """Image content model."""
    image_url: str = Field(..., description="Image URL or base64 data")
    alt_text: str = Field(default="", description="Alternative text")
    position: Rectangle = Field(..., description="Image position and size")
    maintain_aspect_ratio: bool = Field(default=True, description="Maintain aspect ratio")


class TableRow(BaseModel):
    """Table row model."""
    cells: List[str] = Field(..., description="Cell contents")
    style: Optional[TextStyle] = Field(default=None, description="Row style")


class TableContent(BaseModel):
    """Table content model."""
    headers: List[str] = Field(..., description="Table headers")
    rows: List[TableRow] = Field(..., description="Table rows")
    position: Rectangle = Field(..., description="Table position and size")
    header_style: TextStyle = Field(default_factory=TextStyle, description="Header style")
    row_style: TextStyle = Field(default_factory=TextStyle, description="Row style")
    show_grid: bool = Field(default=True, description="Show table grid")
    alternating_rows: bool = Field(default=True, description="Alternate row colors")


# Slide models
class SlideContent(BaseModel):
    """Slide content model."""
    texts: List[TextContent] = Field(default_factory=list, description="Text elements")
    images: List[ImageContent] = Field(default_factory=list, description="Image elements")
    charts: List[Chart] = Field(default_factory=list, description="Chart elements")
    tables: List[TableContent] = Field(default_factory=list, description="Table elements")


class Slide(BaseModel):
    """Slide model."""
    title: str = Field(default="", description="Slide title")
    slide_type: SlideType = Field(..., description="Type of slide")
    layout: LayoutType = Field(..., description="Slide layout")
    content: SlideContent = Field(default_factory=SlideContent, description="Slide content")
    animation: AnimationType = Field(default=AnimationType.FADE, description="Slide animation")
    transition: TransitionType = Field(default=TransitionType.FADE, description="Slide transition")
    notes: str = Field(default="", description="Speaker notes")
    background_color: str = Field(default="#FFFFFF", description="Background color")
    background_image: Optional[str] = Field(default=None, description="Background image URL")


# Presentation models
class PresentationMetadata(BaseModel):
    """Presentation metadata model."""
    title: str = Field(..., description="Presentation title")
    author: str = Field(default="", description="Presentation author")
    subject: str = Field(default="", description="Presentation subject")
    description: str = Field(default="", description="Presentation description")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    category: str = Field(default="", description="Presentation category")
    company: str = Field(default="", description="Company name")


class PresentationConfig(BaseModel):
    """Presentation configuration model."""
    metadata: PresentationMetadata = Field(..., description="Presentation metadata")
    slides: List[Slide] = Field(..., description="Presentation slides")
    theme: Theme = Field(default=Theme.OFFICE, description="Presentation theme")
    color_scheme: ColorScheme = Field(default=ColorScheme.BLUE, description="Color scheme")
    default_font: FontStyle = Field(default_factory=FontStyle, description="Default font")
    slide_size: Size = Field(default=Size(width=10, height=7.5), description="Slide size in inches")
    
    @field_validator("slides")
    @classmethod
    def validate_slides(cls, v):
        """Validate slides list."""
        if not v:
            raise ValueError("At least one slide is required")
        return v


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


# Request models
class PowerPointExportRequest(BaseModel):
    """PowerPoint export request model."""
    job_name: str = Field(..., min_length=1, max_length=255, description="Job name")
    presentation_config: PresentationConfig = Field(..., description="Presentation configuration")
    data_source: DataSource = Field(..., description="Data source")
    output_format: OutputFormat = Field(default=OutputFormat.PPTX, description="Output format")
    expires_in_hours: int = Field(default=24, ge=1, le=168, description="Expiration time in hours")


class BulkPowerPointExportRequest(BaseModel):
    """Bulk PowerPoint export request model."""
    output_format: OutputFormat = Field(default=OutputFormat.PPTX, description="Output format")
    theme: Theme = Field(default=Theme.OFFICE, description="Theme")
    jobs: List[PowerPointExportRequest] = Field(..., min_items=1, max_items=10, description="Export jobs")


class TemplateRequest(BaseModel):
    """Template request model."""
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str = Field(default="", max_length=1000, description="Template description")
    theme: Theme = Field(..., description="Template theme")
    template_data: PresentationConfig = Field(..., description="Template data")
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
    current_slide: Optional[int] = Field(default=None, description="Current slide being processed")
    total_slides: Optional[int] = Field(default=None, description="Total number of slides")
    runtime_seconds: Optional[float] = Field(default=None, description="Runtime in seconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class JobDetailsResponse(BaseModel):
    """Job details response model."""
    job_id: int = Field(..., description="Job identifier")
    job_name: str = Field(..., description="Job name")
    status: JobStatus = Field(..., description="Job status")
    output_format: OutputFormat = Field(..., description="Output format")
    theme: Theme = Field(..., description="Theme")
    file_path: Optional[str] = Field(default=None, description="Generated file path")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    slide_count: Optional[int] = Field(default=None, description="Number of slides")
    chart_count: Optional[int] = Field(default=None, description="Number of charts")
    animation_count: Optional[int] = Field(default=None, description="Number of animations")
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
    avg_slide_count: float = Field(..., description="Average slide count")
    usage_by_format: Dict[str, int] = Field(..., description="Usage statistics by format")
    usage_by_theme: Dict[str, int] = Field(..., description="Usage statistics by theme")
    daily_usage: List[Dict[str, Any]] = Field(..., description="Daily usage statistics")


class CapabilitiesResponse(BaseModel):
    """Service capabilities response model."""
    supported_formats: List[str] = Field(..., description="Supported output formats")
    supported_themes: List[str] = Field(..., description="Supported themes")
    supported_chart_types: List[str] = Field(..., description="Supported chart types")
    supported_animations: List[str] = Field(..., description="Supported animations")
    supported_transitions: List[str] = Field(..., description="Supported transitions")
    max_file_size_mb: int = Field(..., description="Maximum file size in MB")
    max_slides: int = Field(..., description="Maximum number of slides")
    max_concurrent_jobs: int = Field(..., description="Maximum concurrent jobs")
    features: List[str] = Field(..., description="Available features")


class TemplateResponse(BaseModel):
    """Template response model."""
    template_id: int = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    theme: Theme = Field(..., description="Template theme")
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
    "Theme",
    "SlideType",
    "LayoutType",
    "AnimationType",
    "TransitionType",
    "ChartType",
    "ColorScheme",
    
    # Base models
    "BaseResponse",
    "ErrorResponse",
    
    # Geometry models
    "Position",
    "Size",
    "Rectangle",
    
    # Style models
    "FontStyle",
    "TextStyle",
    
    # Content models
    "ChartData",
    "ChartConfig",
    "Chart",
    "TextContent",
    "ImageContent",
    "TableRow",
    "TableContent",
    
    # Slide models
    "SlideContent",
    "Slide",
    
    # Presentation models
    "PresentationMetadata",
    "PresentationConfig",
    
    # Data source models
    "QueryDataSource",
    "FileDataSource",
    "StaticDataSource",
    "DataSource",
    
    # Request models
    "PowerPointExportRequest",
    "BulkPowerPointExportRequest",
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
