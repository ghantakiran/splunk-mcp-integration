"""
Excel Export Service Data Models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid


# SQLAlchemy Base
Base = declarative_base()


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExcelFormat(str, Enum):
    """Excel format enumeration."""
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    ODS = "ods"


class ChartType(str, Enum):
    """Chart type enumeration."""
    LINE = "line"
    BAR = "bar"
    COLUMN = "column"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    RADAR = "radar"
    BUBBLE = "bubble"


class CellDataType(str, Enum):
    """Cell data type enumeration."""
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    FORMULA = "formula"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"


class Theme(str, Enum):
    """Theme enumeration."""
    OFFICE = "office"
    MODERN = "modern"
    COLORFUL = "colorful"
    DARK = "dark"
    LIGHT = "light"


# SQLAlchemy Models
class ExcelJob(Base):
    """Excel export job model."""
    __tablename__ = "excel_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    job_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default=JobStatus.PENDING.value)
    workbook_config = Column(JSON, nullable=False)
    data_source = Column(JSON, nullable=False)
    output_format = Column(String(10), nullable=False, default=ExcelFormat.XLSX.value)
    theme = Column(String(50), nullable=False, default=Theme.OFFICE.value)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)
    worksheet_count = Column(Integer, nullable=True)
    chart_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class ExcelTemplate(Base):
    """Excel template model."""
    __tablename__ = "excel_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    workbook_config = Column(JSON, nullable=False)
    default_theme = Column(String(50), nullable=False, default=Theme.OFFICE.value)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExcelUser(Base):
    """Excel service user model."""
    __tablename__ = "excel_users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    preferences = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models
class CellStyle(BaseModel):
    """Cell style configuration."""
    font_name: Optional[str] = Field(default="Arial", description="Font name")
    font_size: Optional[int] = Field(default=11, description="Font size")
    font_bold: Optional[bool] = Field(default=False, description="Bold text")
    font_italic: Optional[bool] = Field(default=False, description="Italic text")
    font_color: Optional[str] = Field(default="000000", description="Font color (hex)")
    background_color: Optional[str] = Field(default=None, description="Background color (hex)")
    border_style: Optional[str] = Field(default=None, description="Border style")
    border_color: Optional[str] = Field(default="000000", description="Border color (hex)")
    text_align: Optional[str] = Field(default="left", description="Text alignment")
    vertical_align: Optional[str] = Field(default="top", description="Vertical alignment")
    number_format: Optional[str] = Field(default=None, description="Number format")
    text_wrap: Optional[bool] = Field(default=False, description="Text wrap")


class CellData(BaseModel):
    """Cell data configuration."""
    value: Union[str, int, float, bool, None] = Field(description="Cell value")
    data_type: CellDataType = Field(default=CellDataType.STRING, description="Data type")
    style: Optional[CellStyle] = Field(default=None, description="Cell style")
    formula: Optional[str] = Field(default=None, description="Excel formula")
    comment: Optional[str] = Field(default=None, description="Cell comment")


class ChartConfig(BaseModel):
    """Chart configuration."""
    chart_id: str = Field(description="Unique chart identifier")
    chart_type: ChartType = Field(description="Chart type")
    title: str = Field(description="Chart title")
    width: int = Field(default=600, description="Chart width")
    height: int = Field(default=400, description="Chart height")
    position: Dict[str, int] = Field(
        default={"row": 1, "col": 1},
        description="Chart position"
    )
    data_range: Optional[str] = Field(default=None, description="Data range for chart")
    series_config: Optional[Dict[str, Any]] = Field(default=None, description="Series configuration")
    style_config: Optional[Dict[str, Any]] = Field(default=None, description="Style configuration")


class WorksheetConfig(BaseModel):
    """Worksheet configuration."""
    name: str = Field(description="Worksheet name")
    data: List[List[CellData]] = Field(description="Worksheet data")
    headers: Optional[List[str]] = Field(default=None, description="Column headers")
    header_style: Optional[CellStyle] = Field(default=None, description="Header style")
    auto_filter: Optional[bool] = Field(default=False, description="Enable auto filter")
    freeze_panes: Optional[Dict[str, int]] = Field(default=None, description="Freeze panes")
    column_widths: Optional[Dict[str, float]] = Field(default=None, description="Column widths")
    row_heights: Optional[Dict[str, float]] = Field(default=None, description="Row heights")
    charts: Optional[List[ChartConfig]] = Field(default=[], description="Charts")
    protection: Optional[Dict[str, Any]] = Field(default=None, description="Worksheet protection")


class WorkbookConfig(BaseModel):
    """Workbook configuration."""
    name: str = Field(description="Workbook name")
    worksheets: List[WorksheetConfig] = Field(description="Worksheets")
    theme: Theme = Field(default=Theme.OFFICE, description="Workbook theme")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Workbook properties")
    protection: Optional[Dict[str, Any]] = Field(default=None, description="Workbook protection")


class DataValidationRule(BaseModel):
    """Data validation rule."""
    cell_range: str = Field(description="Cell range for validation")
    validation_type: str = Field(description="Validation type")
    formula1: str = Field(description="First formula")
    formula2: Optional[str] = Field(default=None, description="Second formula")
    input_title: Optional[str] = Field(default=None, description="Input title")
    input_message: Optional[str] = Field(default=None, description="Input message")
    error_title: Optional[str] = Field(default=None, description="Error title")
    error_message: Optional[str] = Field(default=None, description="Error message")
    show_dropdown: Optional[bool] = Field(default=True, description="Show dropdown")


class ExcelExportRequest(BaseModel):
    """Excel export request."""
    job_name: str = Field(description="Job name")
    workbook_config: WorkbookConfig = Field(description="Workbook configuration")
    data_source: Dict[str, Any] = Field(description="Data source configuration")
    output_format: ExcelFormat = Field(default=ExcelFormat.XLSX, description="Output format")
    theme: Theme = Field(default=Theme.OFFICE, description="Theme")
    validation_rules: Optional[List[DataValidationRule]] = Field(default=[], description="Validation rules")
    
    @validator('job_name')
    def validate_job_name(cls, v):
        if not v.strip():
            raise ValueError('Job name cannot be empty')
        return v.strip()


class BulkExcelExportRequest(BaseModel):
    """Bulk Excel export request."""
    template_id: Optional[int] = Field(default=None, description="Template ID")
    output_format: ExcelFormat = Field(default=ExcelFormat.XLSX, description="Output format")
    theme: Theme = Field(default=Theme.OFFICE, description="Theme")
    jobs: List[Dict[str, Any]] = Field(description="List of export jobs")
    
    @validator('jobs')
    def validate_jobs(cls, v):
        if not v:
            raise ValueError('At least one job must be provided')
        if len(v) > 100:
            raise ValueError('Maximum 100 jobs allowed per batch')
        return v


class ExcelJobResponse(BaseModel):
    """Excel job response."""
    job_id: int = Field(description="Job ID")
    status: JobStatus = Field(description="Job status")
    message: str = Field(description="Response message")
    file_path: Optional[str] = Field(default=None, description="File path")
    file_size: Optional[int] = Field(default=None, description="File size")
    row_count: Optional[int] = Field(default=None, description="Row count")
    worksheet_count: Optional[int] = Field(default=None, description="Worksheet count")
    chart_count: Optional[int] = Field(default=None, description="Chart count")
    generation_time_ms: Optional[int] = Field(default=None, description="Generation time")
    created_at: datetime = Field(description="Creation time")
    completed_at: Optional[datetime] = Field(default=None, description="Completion time")


class ExcelJobStatusResponse(BaseModel):
    """Excel job status response."""
    job_id: int = Field(description="Job ID")
    status: JobStatus = Field(description="Job status")
    progress: Optional[float] = Field(default=None, description="Progress percentage")
    runtime_seconds: Optional[float] = Field(default=None, description="Runtime in seconds")
    error_message: Optional[str] = Field(default=None, description="Error message")


class ExcelTemplateCreate(BaseModel):
    """Excel template creation request."""
    name: str = Field(description="Template name")
    description: Optional[str] = Field(default=None, description="Template description")
    workbook_config: WorkbookConfig = Field(description="Workbook configuration")
    default_theme: Theme = Field(default=Theme.OFFICE, description="Default theme")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Template name cannot be empty')
        return v.strip()


class ExcelTemplateResponse(BaseModel):
    """Excel template response."""
    id: int = Field(description="Template ID")
    name: str = Field(description="Template name")
    description: Optional[str] = Field(description="Template description")
    workbook_config: WorkbookConfig = Field(description="Workbook configuration")
    default_theme: Theme = Field(description="Default theme")
    is_active: bool = Field(description="Is active")
    is_default: bool = Field(description="Is default")
    created_by: int = Field(description="Created by user ID")
    created_at: datetime = Field(description="Creation time")
    updated_at: datetime = Field(description="Update time")


class ExcelCapabilities(BaseModel):
    """Excel service capabilities."""
    supported_formats: List[str] = Field(description="Supported formats")
    supported_themes: List[str] = Field(description="Supported themes")
    supported_chart_types: List[str] = Field(description="Supported chart types")
    max_file_size_mb: int = Field(description="Maximum file size")
    max_rows: int = Field(description="Maximum rows")
    max_columns: int = Field(description="Maximum columns")
    max_concurrent_jobs: int = Field(description="Maximum concurrent jobs")
    max_worksheets: int = Field(description="Maximum worksheets")
    max_charts_per_worksheet: int = Field(description="Maximum charts per worksheet")
    features: Dict[str, bool] = Field(description="Available features")


class ExcelAnalytics(BaseModel):
    """Excel analytics response."""
    period_days: int = Field(description="Period in days")
    total_jobs: int = Field(description="Total jobs")
    successful_jobs: int = Field(description="Successful jobs")
    failed_jobs: int = Field(description="Failed jobs")
    success_rate: float = Field(description="Success rate percentage")
    avg_generation_time: float = Field(description="Average generation time")
    avg_file_size: float = Field(description="Average file size")
    avg_row_count: float = Field(description="Average row count")
    usage_by_format: Dict[str, int] = Field(description="Usage by format")
    usage_by_theme: Dict[str, int] = Field(description="Usage by theme")
    top_templates: List[Dict[str, Any]] = Field(description="Top used templates")
    daily_usage: List[Dict[str, Any]] = Field(description="Daily usage statistics")