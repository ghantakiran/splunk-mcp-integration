"""
PDF Export Service data models.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
import uuid


class JobStatus(str, Enum):
    """PDF export job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TemplateType(str, Enum):
    """PDF template type."""
    REPORT = "report"
    DASHBOARD = "dashboard"
    CHART = "chart"
    TABLE = "table"
    CUSTOM = "custom"


class OutputFormat(str, Enum):
    """PDF output format."""
    PDF = "pdf"
    HTML = "html"
    PNG = "png"
    JPG = "jpg"


class PageSize(str, Enum):
    """PDF page size."""
    A4 = "a4"
    LETTER = "letter"
    LEGAL = "legal"
    A3 = "a3"
    TABLOID = "tabloid"


class PageOrientation(str, Enum):
    """PDF page orientation."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class PDFQuality(str, Enum):
    """PDF quality setting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


# Request Models
class PDFGenerationRequest(BaseModel):
    """Request model for PDF generation."""
    template_id: Optional[int] = None
    template_type: TemplateType = TemplateType.REPORT
    job_name: str = Field(..., min_length=1, max_length=255)
    output_format: OutputFormat = OutputFormat.PDF
    parameters: Dict[str, Any] = Field(default_factory=dict)
    data_source: Dict[str, Any] = Field(default_factory=dict)
    layout_config: Optional[Dict[str, Any]] = None
    
    @validator('job_name')
    def validate_job_name(cls, v):
        """Validate job name."""
        if not v.strip():
            raise ValueError('Job name cannot be empty')
        return v.strip()
    
    @validator('parameters')
    def validate_parameters(cls, v):
        """Validate parameters."""
        if not isinstance(v, dict):
            raise ValueError('Parameters must be a dictionary')
        return v


class TemplateCreateRequest(BaseModel):
    """Request model for template creation."""
    name: str = Field(..., min_length=1, max_length=255)
    template_type: TemplateType
    description: Optional[str] = None
    template_content: str = Field(..., min_length=1)
    css_content: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    layout_config: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('name')
    def validate_name(cls, v):
        """Validate template name."""
        if not v.strip():
            raise ValueError('Template name cannot be empty')
        return v.strip()
    
    @validator('template_content')
    def validate_template_content(cls, v):
        """Validate template content."""
        if not v.strip():
            raise ValueError('Template content cannot be empty')
        return v.strip()


class TemplateUpdateRequest(BaseModel):
    """Request model for template update."""
    name: Optional[str] = None
    description: Optional[str] = None
    template_content: Optional[str] = None
    css_content: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    layout_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class LayoutConfig(BaseModel):
    """PDF layout configuration."""
    page_size: PageSize = PageSize.A4
    orientation: PageOrientation = PageOrientation.PORTRAIT
    margin_top: float = Field(default=20.0, ge=0, le=100)
    margin_bottom: float = Field(default=20.0, ge=0, le=100)
    margin_left: float = Field(default=20.0, ge=0, le=100)
    margin_right: float = Field(default=20.0, ge=0, le=100)
    header_height: float = Field(default=0.0, ge=0, le=100)
    footer_height: float = Field(default=0.0, ge=0, le=100)
    dpi: int = Field(default=300, ge=72, le=600)
    quality: PDFQuality = PDFQuality.HIGH
    
    @validator('dpi')
    def validate_dpi(cls, v):
        """Validate DPI."""
        if v < 72 or v > 600:
            raise ValueError('DPI must be between 72 and 600')
        return v


class ChartConfig(BaseModel):
    """Chart configuration for PDF embedding."""
    chart_id: str
    title: str
    chart_type: str
    width: int = Field(default=800, ge=100, le=2000)
    height: int = Field(default=600, ge=100, le=1500)
    data: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)
    full_width: bool = False


class TableConfig(BaseModel):
    """Table configuration for PDF embedding."""
    title: str
    headers: List[str]
    data: List[List[str]]
    style: Dict[str, Any] = Field(default_factory=dict)
    full_width: bool = True


# Response Models
class PDFJob(BaseModel):
    """PDF export job response model."""
    id: int
    user_id: int
    template_id: Optional[int]
    job_name: str
    status: JobStatus
    parameters: Dict[str, Any]
    data_source: Dict[str, Any]
    output_format: OutputFormat
    file_path: Optional[str]
    file_size: Optional[int]
    page_count: Optional[int]
    error_message: Optional[str]
    generation_time_ms: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class PDFTemplate(BaseModel):
    """PDF template response model."""
    id: int
    name: str
    template_type: TemplateType
    description: Optional[str]
    template_content: str
    css_content: Optional[str]
    variables: Dict[str, Any]
    layout_config: Dict[str, Any]
    created_by: Optional[int]
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class PDFUser(BaseModel):
    """PDF user response model."""
    id: int
    external_id: str
    email: str
    name: str
    role: str
    permissions: Dict[str, Any]
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class PDFExportPreferences(BaseModel):
    """PDF export preferences response model."""
    id: int
    user_id: int
    default_template_id: Optional[int]
    default_format: OutputFormat
    default_page_size: PageSize
    default_orientation: PageOrientation
    default_dpi: int
    custom_css: Optional[str]
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class PDFAnalytics(BaseModel):
    """PDF analytics response model."""
    id: int
    user_id: int
    job_id: int
    template_type: TemplateType
    output_format: OutputFormat
    generation_time_ms: int
    file_size: int
    page_count: int
    success: bool
    error_code: Optional[str]
    created_at: datetime
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class PDFGenerationResponse(BaseModel):
    """PDF generation response model."""
    job_id: int
    status: JobStatus
    message: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    generation_time_ms: Optional[int] = None
    created_at: datetime


class PDFTemplateList(BaseModel):
    """PDF template list response model."""
    templates: List[PDFTemplate]
    total: int
    page: int
    page_size: int


class PDFJobList(BaseModel):
    """PDF job list response model."""
    jobs: List[PDFJob]
    total: int
    page: int
    page_size: int


class PDFPreview(BaseModel):
    """PDF preview response model."""
    template_id: int
    preview_html: str
    preview_css: str
    variables: Dict[str, Any]


class PDFCapabilities(BaseModel):
    """PDF service capabilities response model."""
    supported_formats: List[OutputFormat]
    supported_page_sizes: List[PageSize]
    supported_orientations: List[PageOrientation]
    supported_qualities: List[PDFQuality]
    template_types: List[TemplateType]
    max_file_size_mb: int
    max_pages: int
    max_concurrent_jobs: int


class PDFUsageAnalytics(BaseModel):
    """PDF usage analytics response model."""
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    avg_generation_time_ms: float
    avg_file_size_mb: float
    avg_page_count: float
    jobs_by_format: Dict[str, int]
    jobs_by_template_type: Dict[str, int]
    jobs_by_date: Dict[str, int]
    top_templates: List[Dict[str, Any]]
    performance_metrics: Dict[str, float]


# Validation Models
class PDFJobUpdate(BaseModel):
    """PDF job update model."""
    status: Optional[JobStatus] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    generation_time_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PDFError(BaseModel):
    """PDF error model."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PDFHealthCheck(BaseModel):
    """PDF health check model."""
    status: str
    version: str
    uptime: float
    database: Dict[str, Any]
    redis: Dict[str, Any]
    dependencies: Dict[str, Any]
    performance: Dict[str, Any]


# Request validation models
class PDFBulkGenerationRequest(BaseModel):
    """Bulk PDF generation request model."""
    template_id: int
    jobs: List[Dict[str, Any]]
    output_format: OutputFormat = OutputFormat.PDF
    
    @validator('jobs')
    def validate_jobs(cls, v):
        """Validate jobs list."""
        if not v:
            raise ValueError('Jobs list cannot be empty')
        if len(v) > 50:
            raise ValueError('Maximum 50 jobs allowed per bulk request')
        return v


class PDFPreviewRequest(BaseModel):
    """PDF preview request model."""
    template_id: int
    parameters: Dict[str, Any] = Field(default_factory=dict)
    sample_data: Dict[str, Any] = Field(default_factory=dict)