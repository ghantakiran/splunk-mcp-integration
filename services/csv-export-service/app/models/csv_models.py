#!/usr/bin/env python3
"""
Pydantic models for CSV Export Service.

This module contains all data models used for API requests, responses,
and internal data structures for the CSV export service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


# Enums
class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormat(str, Enum):
    """Export format enumeration."""
    CSV = "csv"
    TSV = "tsv"
    PIPE = "pipe"
    CUSTOM = "custom"


class Encoding(str, Enum):
    """Encoding enumeration."""
    UTF8 = "utf-8"
    UTF16 = "utf-16"
    UTF16LE = "utf-16-le"
    UTF16BE = "utf-16-be"
    UTF32 = "utf-32"
    LATIN1 = "latin-1"
    ASCII = "ascii"
    CP1252 = "cp1252"
    ISO88591 = "iso-8859-1"


class Delimiter(str, Enum):
    """Delimiter enumeration."""
    COMMA = ","
    SEMICOLON = ";"
    TAB = "\t"
    PIPE = "|"
    COLON = ":"
    CARET = "^"
    TILDE = "~"


class QuoteStyle(str, Enum):
    """Quote style enumeration."""
    MINIMAL = "minimal"
    ALL = "all"
    NON_NUMERIC = "non_numeric"
    NONE = "none"


class NullHandling(str, Enum):
    """Null value handling enumeration."""
    EMPTY_STRING = "empty_string"
    NULL = "null"
    NA = "na"
    NONE = "none"
    CUSTOM = "custom"


class DataType(str, Enum):
    """Data type enumeration."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"


class CompressionType(str, Enum):
    """Compression type enumeration."""
    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"
    BZIP2 = "bzip2"


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
    file_format: str = Field(..., pattern="^(csv|json|xlsx|xml|parquet)$", description="File format")
    sheet_name: Optional[str] = Field(default=None, description="Sheet name for Excel files")
    has_header: bool = Field(default=True, description="File has header row")


class StaticDataSource(BaseModel):
    """Static data source model."""
    data: List[Dict[str, Any]] = Field(..., description="Static data")
    columns: Optional[List[str]] = Field(default=None, description="Column names")


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


# Column configuration models
class ColumnMapping(BaseModel):
    """Column mapping configuration."""
    source_name: str = Field(..., description="Source column name")
    target_name: str = Field(..., description="Target column name")
    data_type: DataType = Field(default=DataType.STRING, description="Data type")
    format_string: Optional[str] = Field(default=None, description="Format string for dates/numbers")
    transform_function: Optional[str] = Field(default=None, description="Transform function name")
    include: bool = Field(default=True, description="Include column in export")


class HeaderConfig(BaseModel):
    """Header configuration."""
    include_header: bool = Field(default=True, description="Include header row")
    custom_headers: Optional[List[str]] = Field(default=None, description="Custom header names")
    header_case: str = Field(default="original", pattern="^(original|lower|upper|title)$", description="Header case transformation")
    header_prefix: Optional[str] = Field(default=None, description="Header prefix")
    header_suffix: Optional[str] = Field(default=None, description="Header suffix")


class FormattingConfig(BaseModel):
    """Formatting configuration."""
    encoding: Encoding = Field(default=Encoding.UTF8, description="File encoding")
    delimiter: str = Field(default=",", description="Field delimiter")
    quote_char: str = Field(default='"', description="Quote character")
    escape_char: str = Field(default="\\", description="Escape character")
    line_terminator: str = Field(default="\n", description="Line terminator")
    quote_style: QuoteStyle = Field(default=QuoteStyle.MINIMAL, description="Quote style")
    
    @field_validator("delimiter")
    @classmethod
    def validate_delimiter(cls, v):
        """Validate delimiter is not empty."""
        if not v:
            raise ValueError("Delimiter cannot be empty")
        return v
    
    @field_validator("quote_char")
    @classmethod
    def validate_quote_char(cls, v):
        """Validate quote character is single character."""
        if len(v) != 1:
            raise ValueError("Quote character must be single character")
        return v


class DataProcessingConfig(BaseModel):
    """Data processing configuration."""
    null_handling: NullHandling = Field(default=NullHandling.EMPTY_STRING, description="Null value handling")
    custom_null_value: Optional[str] = Field(default=None, description="Custom null value replacement")
    trim_whitespace: bool = Field(default=True, description="Trim whitespace from values")
    remove_empty_rows: bool = Field(default=False, description="Remove empty rows")
    remove_duplicate_rows: bool = Field(default=False, description="Remove duplicate rows")
    max_rows: Optional[int] = Field(default=None, ge=1, description="Maximum rows to export")
    skip_rows: int = Field(default=0, ge=0, description="Number of rows to skip")
    
    @model_validator(mode='after')
    def validate_custom_null_value(self):
        """Validate custom null value when null_handling is CUSTOM."""
        if self.null_handling == NullHandling.CUSTOM and self.custom_null_value is None:
            raise ValueError("custom_null_value is required when null_handling is CUSTOM")
        return self


class CompressionConfig(BaseModel):
    """Compression configuration."""
    compression_type: CompressionType = Field(default=CompressionType.NONE, description="Compression type")
    compression_level: int = Field(default=6, ge=1, le=9, description="Compression level")
    include_source_filename: bool = Field(default=True, description="Include source filename in archive")


class CSVExportConfig(BaseModel):
    """CSV export configuration."""
    export_format: ExportFormat = Field(default=ExportFormat.CSV, description="Export format")
    formatting: FormattingConfig = Field(default_factory=FormattingConfig, description="Formatting options")
    header_config: HeaderConfig = Field(default_factory=HeaderConfig, description="Header configuration")
    data_processing: DataProcessingConfig = Field(default_factory=DataProcessingConfig, description="Data processing options")
    compression: CompressionConfig = Field(default_factory=CompressionConfig, description="Compression options")
    column_mappings: List[ColumnMapping] = Field(default_factory=list, description="Column mappings")
    
    @model_validator(mode='after')
    def validate_format_consistency(self):
        """Validate format consistency."""
        if self.export_format == ExportFormat.TSV:
            self.formatting.delimiter = "\t"
        elif self.export_format == ExportFormat.PIPE:
            self.formatting.delimiter = "|"
        
        return self


# Request models
class CSVExportRequest(BaseModel):
    """CSV export request model."""
    job_name: str = Field(..., min_length=1, max_length=255, description="Job name")
    data_source: DataSource = Field(..., description="Data source")
    export_config: CSVExportConfig = Field(default_factory=CSVExportConfig, description="Export configuration")
    expires_in_hours: int = Field(default=24, ge=1, le=168, description="Expiration time in hours")
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1=highest, 10=lowest)")


class BulkCSVExportRequest(BaseModel):
    """Bulk CSV export request model."""
    jobs: List[CSVExportRequest] = Field(..., min_items=1, max_items=20, description="Export jobs")
    archive_name: Optional[str] = Field(default=None, description="Archive name for bulk export")
    compression: CompressionConfig = Field(default_factory=CompressionConfig, description="Archive compression")


class TemplateRequest(BaseModel):
    """Template request model."""
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str = Field(default="", max_length=1000, description="Template description")
    export_config: CSVExportConfig = Field(..., description="Template configuration")
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
    rows_processed: Optional[int] = Field(default=None, description="Rows processed")
    total_rows: Optional[int] = Field(default=None, description="Total rows")
    current_operation: Optional[str] = Field(default=None, description="Current operation")
    runtime_seconds: Optional[float] = Field(default=None, description="Runtime in seconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class JobDetailsResponse(BaseModel):
    """Job details response model."""
    job_id: int = Field(..., description="Job identifier")
    job_name: str = Field(..., description="Job name")
    status: JobStatus = Field(..., description="Job status")
    export_format: ExportFormat = Field(..., description="Export format")
    file_path: Optional[str] = Field(default=None, description="Generated file path")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    row_count: Optional[int] = Field(default=None, description="Number of rows exported")
    column_count: Optional[int] = Field(default=None, description="Number of columns exported")
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
    avg_row_count: float = Field(..., description="Average row count")
    total_data_exported_gb: float = Field(..., description="Total data exported in GB")
    usage_by_format: Dict[str, int] = Field(..., description="Usage statistics by format")
    daily_usage: List[Dict[str, Any]] = Field(..., description="Daily usage statistics")


class CapabilitiesResponse(BaseModel):
    """Service capabilities response model."""
    supported_formats: List[str] = Field(..., description="Supported export formats")
    supported_encodings: List[str] = Field(..., description="Supported encodings")
    supported_delimiters: List[str] = Field(..., description="Supported delimiters")
    max_file_size_mb: int = Field(..., description="Maximum file size in MB")
    max_concurrent_jobs: int = Field(..., description="Maximum concurrent jobs")
    max_rows_per_file: int = Field(..., description="Maximum rows per file")
    features: List[str] = Field(..., description="Available features")


class TemplateResponse(BaseModel):
    """Template response model."""
    template_id: int = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    is_default: bool = Field(..., description="Is default template")
    is_active: bool = Field(..., description="Is template active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TemplateListResponse(BaseModel):
    """Template list response model."""
    total: int = Field(..., description="Total number of templates")
    templates: List[TemplateResponse] = Field(..., description="List of templates")


class ValidationResponse(BaseModel):
    """Data validation response model."""
    is_valid: bool = Field(..., description="Is data valid")
    row_count: int = Field(..., description="Total row count")
    column_count: int = Field(..., description="Total column count")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="Validation issues")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    estimated_file_size_mb: float = Field(..., description="Estimated file size in MB")


# Export commonly used models
__all__ = [
    # Enums
    "JobStatus",
    "ExportFormat",
    "Encoding",
    "Delimiter",
    "QuoteStyle",
    "NullHandling",
    "DataType",
    "CompressionType",
    
    # Base models
    "BaseResponse",
    "ErrorResponse",
    
    # Data models
    "DataSource",
    "QueryDataSource",
    "FileDataSource",
    "StaticDataSource",
    
    # Configuration models
    "ColumnMapping",
    "HeaderConfig",
    "FormattingConfig",
    "DataProcessingConfig",
    "CompressionConfig",
    "CSVExportConfig",
    
    # Request models
    "CSVExportRequest",
    "BulkCSVExportRequest",
    "TemplateRequest",
    
    # Response models
    "JobResponse",
    "JobStatusResponse",
    "JobDetailsResponse",
    "JobListResponse",
    "AnalyticsResponse",
    "CapabilitiesResponse",
    "TemplateResponse",
    "TemplateListResponse",
    "ValidationResponse"
]