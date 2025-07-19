"""
Pydantic models for JSON/XML export service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict, validator


class ExportFormat(str, Enum):
    """Export format types."""
    JSON = "json"
    XML = "xml"
    JSONL = "jsonl"  # JSON Lines
    CUSTOM_JSON = "custom-json"
    CUSTOM_XML = "custom-xml"


class ExportStatus(str, Enum):
    """Export job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JsonFormatting(BaseModel):
    """JSON formatting configuration."""
    model_config = ConfigDict(extra="forbid")
    
    indent: Optional[int] = Field(default=2, ge=0, le=8, description="JSON indentation")
    sort_keys: bool = Field(default=True, description="Sort object keys")
    ensure_ascii: bool = Field(default=False, description="Ensure ASCII characters only")
    separators: Optional[tuple] = Field(default=None, description="Item and key separators")
    compact: bool = Field(default=False, description="Compact output (overrides indent)")


class XmlFormatting(BaseModel):
    """XML formatting configuration."""
    model_config = ConfigDict(extra="forbid")
    
    pretty_print: bool = Field(default=True, description="Pretty print XML")
    encoding: str = Field(default="utf-8", description="XML encoding")
    xml_declaration: bool = Field(default=True, description="Include XML declaration")
    root_tag: str = Field(default="root", min_length=1, description="Root element tag")
    item_tag: str = Field(default="item", min_length=1, description="Item element tag")
    namespace: Optional[str] = Field(default=None, description="XML namespace")
    schema_location: Optional[str] = Field(default=None, description="Schema location")


class DataSource(BaseModel):
    """Data source configuration."""
    model_config = ConfigDict(extra="forbid")
    
    type: str = Field(description="Data source type")
    config: Dict[str, Any] = Field(description="Source-specific configuration")
    query: Optional[str] = Field(default=None, description="Query string")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Data filters")


class FieldMapping(BaseModel):
    """Field mapping configuration."""
    model_config = ConfigDict(extra="forbid")
    
    source_field: str = Field(description="Source field name")
    target_field: str = Field(description="Target field name")
    data_type: Optional[str] = Field(default=None, description="Target data type")
    transform: Optional[str] = Field(default=None, description="Transformation function")
    default_value: Optional[Any] = Field(default=None, description="Default value")


class ExportConfiguration(BaseModel):
    """Export configuration."""
    model_config = ConfigDict(extra="forbid")
    
    format: ExportFormat = Field(description="Export format")
    encoding: str = Field(default="utf-8", description="File encoding")
    compression: Optional[str] = Field(default=None, description="Compression type")
    
    # Format-specific configurations
    json_config: Optional[JsonFormatting] = Field(default=None, description="JSON formatting")
    xml_config: Optional[XmlFormatting] = Field(default=None, description="XML formatting")
    
    # Data processing
    field_mappings: Optional[List[FieldMapping]] = Field(default=None, description="Field mappings")
    include_metadata: bool = Field(default=True, description="Include metadata")
    flatten_nested: bool = Field(default=False, description="Flatten nested objects")
    max_records: Optional[int] = Field(default=None, ge=1, description="Maximum records")
    
    @validator('json_config')
    def validate_json_config(cls, v, values):
        """Validate JSON config when format is JSON."""
        format_type = values.get('format')
        if format_type in [ExportFormat.JSON, ExportFormat.JSONL, ExportFormat.CUSTOM_JSON]:
            return v or JsonFormatting()
        return v
    
    @validator('xml_config')
    def validate_xml_config(cls, v, values):
        """Validate XML config when format is XML."""
        format_type = values.get('format')
        if format_type in [ExportFormat.XML, ExportFormat.CUSTOM_XML]:
            return v or XmlFormatting()
        return v


class ExportRequest(BaseModel):
    """Export request model."""
    model_config = ConfigDict(extra="forbid")
    
    data_source: DataSource = Field(description="Data source configuration")
    export_config: ExportConfiguration = Field(description="Export configuration")
    filename: Optional[str] = Field(default=None, description="Output filename")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class BulkExportRequest(BaseModel):
    """Bulk export request model."""
    model_config = ConfigDict(extra="forbid")
    
    exports: List[ExportRequest] = Field(min_items=1, max_items=10, description="Export requests")
    parallel: bool = Field(default=True, description="Process exports in parallel")
    shared_config: Optional[ExportConfiguration] = Field(default=None, description="Shared configuration")


class ExportJob(BaseModel):
    """Export job model."""
    model_config = ConfigDict(extra="forbid")
    
    job_id: str = Field(description="Job identifier")
    user_id: str = Field(description="User identifier")
    status: ExportStatus = Field(description="Job status")
    format: ExportFormat = Field(description="Export format")
    filename: Optional[str] = Field(default=None, description="Output filename")
    file_path: Optional[str] = Field(default=None, description="File path")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    records_processed: Optional[int] = Field(default=None, description="Records processed")
    error_message: Optional[str] = Field(default=None, description="Error message")
    
    created_at: datetime = Field(description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Job metadata")


class ExportJobCreate(BaseModel):
    """Export job creation model."""
    model_config = ConfigDict(extra="forbid")
    
    export_request: ExportRequest = Field(description="Export request")
    priority: int = Field(default=0, ge=0, le=10, description="Job priority")


class ExportJobUpdate(BaseModel):
    """Export job update model."""
    model_config = ConfigDict(extra="forbid")
    
    status: Optional[ExportStatus] = Field(default=None, description="Job status")
    error_message: Optional[str] = Field(default=None, description="Error message")
    file_path: Optional[str] = Field(default=None, description="File path")
    file_size: Optional[int] = Field(default=None, description="File size")
    records_processed: Optional[int] = Field(default=None, description="Records processed")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata updates")


class ExportJobResponse(BaseModel):
    """Export job response model."""
    model_config = ConfigDict(extra="forbid")
    
    success: bool = Field(description="Request success")
    job: ExportJob = Field(description="Export job")
    download_url: Optional[str] = Field(default=None, description="Download URL")


class ExportJobList(BaseModel):
    """Export job list response."""
    model_config = ConfigDict(extra="forbid")
    
    success: bool = Field(description="Request success")
    jobs: List[ExportJob] = Field(description="Export jobs")
    total: int = Field(description="Total job count")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")


class ExportCapabilities(BaseModel):
    """Export capabilities response."""
    model_config = ConfigDict(extra="forbid")
    
    supported_formats: List[str] = Field(description="Supported export formats")
    supported_encodings: List[str] = Field(description="Supported encodings")
    supported_compressions: List[str] = Field(description="Supported compression types")
    max_file_size_mb: int = Field(description="Maximum file size in MB")
    max_records: int = Field(description="Maximum records per export")
    features: List[str] = Field(description="Available features")


class ExportAnalytics(BaseModel):
    """Export analytics model."""
    model_config = ConfigDict(extra="forbid")
    
    total_exports: int = Field(description="Total exports")
    successful_exports: int = Field(description="Successful exports")
    failed_exports: int = Field(description="Failed exports")
    avg_processing_time: float = Field(description="Average processing time in seconds")
    total_data_exported: int = Field(description="Total data exported in bytes")
    format_distribution: Dict[str, int] = Field(description="Export format distribution")
    user_activity: Dict[str, int] = Field(description="User activity statistics")


class HealthCheck(BaseModel):
    """Health check response."""
    model_config = ConfigDict(extra="forbid")
    
    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    database: str = Field(description="Database status")
    redis: str = Field(description="Redis status")
    timestamp: datetime = Field(description="Check timestamp")


class ErrorResponse(BaseModel):
    """Error response model."""
    model_config = ConfigDict(extra="forbid")
    
    success: bool = Field(default=False, description="Request success")
    error: str = Field(description="Error message")
    code: str = Field(description="Error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    timestamp: datetime = Field(description="Error timestamp")