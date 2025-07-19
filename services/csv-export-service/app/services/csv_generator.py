#!/usr/bin/env python3
"""
CSV Generator Service.

This service handles the generation of CSV files with advanced formatting,
customization options, and performance optimizations.
"""

import asyncio
import csv
import gzip
import io
import json
import logging
import os
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Generator
import tempfile

import aiofiles
import pandas as pd
from decimal import Decimal

from app.core.config import settings
from app.models.csv_models import (
    CSVExportConfig,
    ColumnMapping,
    DataType,
    Encoding,
    ExportFormat,
    JobStatus,
    NullHandling,
    QuoteStyle,
    CompressionType
)

logger = logging.getLogger(__name__)


class CSVGenerator:
    """Advanced CSV generator with customizable formatting and optimization."""
    
    def __init__(self):
        """Initialize the CSV generator."""
        self.quote_style_mapping = {
            QuoteStyle.MINIMAL: csv.QUOTE_MINIMAL,
            QuoteStyle.ALL: csv.QUOTE_ALL,
            QuoteStyle.NON_NUMERIC: csv.QUOTE_NONNUMERIC,
            QuoteStyle.NONE: csv.QUOTE_NONE
        }
        
        self.null_value_mapping = {
            NullHandling.EMPTY_STRING: "",
            NullHandling.NULL: "NULL",
            NullHandling.NA: "N/A",
            NullHandling.NONE: "None"
        }
    
    async def generate_csv(
        self,
        job_id: int,
        user_id: int,
        data_source: Dict[str, Any],
        export_config: CSVExportConfig,
        job_name: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate a CSV file from data source and configuration.
        
        Args:
            job_id: Job identifier
            user_id: User identifier
            data_source: Data source configuration
            export_config: Export configuration
            job_name: Job name for file naming
            
        Returns:
            Tuple of (success, file_path, error_message)
        """
        start_time = time.time()
        
        try:
            # Update job status to processing
            await self._update_job_status(job_id, JobStatus.PROCESSING, started_at=datetime.utcnow())
            
            logger.info(f"Starting CSV generation for job {job_id}")
            
            # Fetch data from data source
            data = await self._fetch_data(data_source)
            
            # Process and validate data
            processed_data = await self._process_data(data, export_config)
            
            # Generate file path
            file_extension = self._get_file_extension(export_config.export_format, export_config.compression.compression_type)
            file_name = f"{job_name.replace(' ', '_')}_{job_id}_{int(time.time())}.{file_extension}"
            file_path = os.path.join(settings.CSV_OUTPUT_DIR, file_name)
            
            # Generate CSV content
            csv_content = await self._generate_csv_content(processed_data, export_config)
            
            # Write file with compression if specified
            await self._write_file(csv_content, file_path, export_config.compression)
            
            # Calculate metadata
            file_size = os.path.getsize(file_path)
            row_count = len(processed_data) if processed_data else 0
            column_count = len(processed_data[0]) if processed_data and len(processed_data) > 0 else 0
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Update job with success
            await self._update_job_completion(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                file_path=file_path,
                file_size=file_size,
                row_count=row_count,
                column_count=column_count,
                generation_time_ms=generation_time_ms
            )
            
            logger.info(f"CSV generation completed for job {job_id}")
            return True, file_path, None
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"CSV generation failed for job {job_id}: {error_message}")
            
            # Update job with failure
            await self._update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=error_message,
                completed_at=datetime.utcnow()
            )
            
            return False, None, error_message
    
    async def _fetch_data(self, data_source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch data from data source."""
        if "static_source" in data_source:
            static_data = data_source["static_source"]
            return static_data.get("data", [])
        elif "query_source" in data_source:
            # In a real implementation, this would execute the query
            return await self._execute_query(data_source["query_source"])
        elif "file_source" in data_source:
            # In a real implementation, this would load from file
            return await self._load_from_file(data_source["file_source"])
        else:
            return []
    
    async def _execute_query(self, query_source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute query against data source."""
        # Mock implementation - in real scenario, would connect to actual data source
        logger.info(f"Executing query: {query_source.get('query', '')}")
        
        # Return mock data for demonstration
        return [
            {"id": 1, "name": "Sample Record 1", "value": 100.5, "date": "2024-01-01"},
            {"id": 2, "name": "Sample Record 2", "value": 200.75, "date": "2024-01-02"},
            {"id": 3, "name": "Sample Record 3", "value": 300.25, "date": "2024-01-03"}
        ]
    
    async def _load_from_file(self, file_source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Load data from file source."""
        file_path = file_source.get("file_path", "")
        file_format = file_source.get("file_format", "csv")
        
        logger.info(f"Loading data from file: {file_path}")
        
        try:
            if file_format == "csv":
                # Mock CSV loading
                return [
                    {"column1": "value1", "column2": "value2"},
                    {"column1": "value3", "column2": "value4"}
                ]
            elif file_format == "json":
                # Mock JSON loading
                return [{"data": "mock_json_data"}]
            else:
                logger.warning(f"Unsupported file format: {file_format}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            return []
    
    async def _process_data(
        self,
        data: List[Dict[str, Any]],
        config: CSVExportConfig
    ) -> List[Dict[str, Any]]:
        """Process data according to configuration."""
        if not data:
            return []
        
        processed_data = data.copy()
        
        # Apply column mappings
        if config.column_mappings:
            processed_data = await self._apply_column_mappings(processed_data, config.column_mappings)
        
        # Apply data processing options
        if config.data_processing.remove_empty_rows:
            processed_data = self._remove_empty_rows(processed_data)
        
        if config.data_processing.remove_duplicate_rows:
            processed_data = self._remove_duplicate_rows(processed_data)
        
        if config.data_processing.max_rows:
            processed_data = processed_data[:config.data_processing.max_rows]
        
        if config.data_processing.skip_rows > 0:
            processed_data = processed_data[config.data_processing.skip_rows:]
        
        # Handle null values
        processed_data = self._handle_null_values(processed_data, config.data_processing)
        
        # Trim whitespace if requested
        if config.data_processing.trim_whitespace:
            processed_data = self._trim_whitespace(processed_data)
        
        return processed_data
    
    async def _apply_column_mappings(
        self,
        data: List[Dict[str, Any]],
        mappings: List[ColumnMapping]
    ) -> List[Dict[str, Any]]:
        """Apply column mappings to data."""
        if not mappings:
            return data
        
        # Create mapping dictionaries
        source_to_target = {m.source_name: m.target_name for m in mappings if m.include}
        column_types = {m.source_name: m.data_type for m in mappings}
        format_strings = {m.source_name: m.format_string for m in mappings if m.format_string}
        
        processed_data = []
        
        for row in data:
            new_row = {}
            for mapping in mappings:
                if not mapping.include:
                    continue
                
                source_value = row.get(mapping.source_name)
                
                # Apply data type conversion
                converted_value = self._convert_data_type(source_value, mapping.data_type, format_strings.get(mapping.source_name))
                
                # Use target name
                new_row[mapping.target_name] = converted_value
            
            processed_data.append(new_row)
        
        return processed_data
    
    def _convert_data_type(self, value: Any, data_type: DataType, format_string: Optional[str] = None) -> Any:
        """Convert value to specified data type."""
        if value is None:
            return None
        
        try:
            if data_type == DataType.STRING:
                return str(value)
            elif data_type == DataType.INTEGER:
                return int(float(value))  # Handle string numbers
            elif data_type == DataType.FLOAT:
                return float(value)
            elif data_type == DataType.DECIMAL:
                return Decimal(str(value))
            elif data_type == DataType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1', 'yes', 'on')
            elif data_type == DataType.DATE:
                if format_string:
                    return datetime.strptime(str(value), format_string).date()
                return pd.to_datetime(value).date()
            elif data_type == DataType.DATETIME:
                if format_string:
                    return datetime.strptime(str(value), format_string)
                return pd.to_datetime(value)
            elif data_type == DataType.TIME:
                if format_string:
                    return datetime.strptime(str(value), format_string).time()
                return pd.to_datetime(value).time()
            else:
                return str(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert value {value} to {data_type}: {e}")
            return str(value)  # Fallback to string
    
    def _remove_empty_rows(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove rows that are completely empty."""
        return [row for row in data if any(v is not None and str(v).strip() for v in row.values())]
    
    def _remove_duplicate_rows(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate rows."""
        seen = set()
        unique_data = []
        
        for row in data:
            # Create a hashable representation of the row
            row_tuple = tuple(sorted(row.items()))
            if row_tuple not in seen:
                seen.add(row_tuple)
                unique_data.append(row)
        
        return unique_data
    
    def _handle_null_values(self, data: List[Dict[str, Any]], processing_config) -> List[Dict[str, Any]]:
        """Handle null values according to configuration."""
        null_replacement = self._get_null_replacement(processing_config)
        
        processed_data = []
        for row in data:
            new_row = {}
            for key, value in row.items():
                if value is None or value == "" or pd.isna(value):
                    new_row[key] = null_replacement
                else:
                    new_row[key] = value
            processed_data.append(new_row)
        
        return processed_data
    
    def _get_null_replacement(self, processing_config) -> str:
        """Get null value replacement based on configuration."""
        if processing_config.null_handling == NullHandling.CUSTOM:
            return processing_config.custom_null_value or ""
        else:
            return self.null_value_mapping.get(processing_config.null_handling, "")
    
    def _trim_whitespace(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Trim whitespace from string values."""
        processed_data = []
        for row in data:
            new_row = {}
            for key, value in row.items():
                if isinstance(value, str):
                    new_row[key] = value.strip()
                else:
                    new_row[key] = value
            processed_data.append(new_row)
        
        return processed_data
    
    async def _generate_csv_content(
        self,
        data: List[Dict[str, Any]],
        config: CSVExportConfig
    ) -> str:
        """Generate CSV content from processed data."""
        if not data:
            return ""
        
        output = io.StringIO()
        
        # Determine field names
        fieldnames = list(data[0].keys()) if data else []
        
        # Apply header configuration
        if config.header_config.custom_headers:
            display_headers = config.header_config.custom_headers[:len(fieldnames)]
        else:
            display_headers = self._transform_headers(fieldnames, config.header_config)
        
        # Configure CSV writer
        writer_config = {
            'delimiter': config.formatting.delimiter,
            'quotechar': config.formatting.quote_char,
            'escapechar': config.formatting.escape_char,
            'lineterminator': config.formatting.line_terminator,
            'quoting': self.quote_style_mapping.get(config.formatting.quote_style, csv.QUOTE_MINIMAL)
        }
        
        writer = csv.DictWriter(output, fieldnames=fieldnames, **writer_config)
        
        # Write header if requested
        if config.header_config.include_header:
            # Create header row mapping
            header_row = dict(zip(fieldnames, display_headers))
            writer.writerow(header_row)
        
        # Write data rows
        for row in data:
            writer.writerow(row)
        
        return output.getvalue()
    
    def _transform_headers(self, headers: List[str], header_config) -> List[str]:
        """Transform headers according to configuration."""
        transformed = headers.copy()
        
        # Apply case transformation
        if header_config.header_case == "lower":
            transformed = [h.lower() for h in transformed]
        elif header_config.header_case == "upper":
            transformed = [h.upper() for h in transformed]
        elif header_config.header_case == "title":
            transformed = [h.title() for h in transformed]
        
        # Apply prefix and suffix
        if header_config.header_prefix:
            transformed = [f"{header_config.header_prefix}{h}" for h in transformed]
        
        if header_config.header_suffix:
            transformed = [f"{h}{header_config.header_suffix}" for h in transformed]
        
        return transformed
    
    def _get_file_extension(self, export_format: ExportFormat, compression_type: CompressionType) -> str:
        """Get file extension based on format and compression."""
        base_extension = {
            ExportFormat.CSV: "csv",
            ExportFormat.TSV: "tsv",
            ExportFormat.PIPE: "txt",
            ExportFormat.CUSTOM: "csv"
        }.get(export_format, "csv")
        
        if compression_type == CompressionType.GZIP:
            return f"{base_extension}.gz"
        elif compression_type == CompressionType.ZIP:
            return "zip"
        elif compression_type == CompressionType.BZIP2:
            return f"{base_extension}.bz2"
        else:
            return base_extension
    
    async def _write_file(self, content: str, file_path: str, compression_config) -> None:
        """Write content to file with optional compression."""
        if compression_config.compression_type == CompressionType.NONE:
            # Write uncompressed file
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
        
        elif compression_config.compression_type == CompressionType.GZIP:
            # Write gzip compressed file
            with gzip.open(file_path, 'wt', encoding='utf-8', compresslevel=compression_config.compression_level) as f:
                f.write(content)
        
        elif compression_config.compression_type == CompressionType.ZIP:
            # Write zip compressed file
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compression_config.compression_level) as zipf:
                # Extract base name for the file inside the zip
                base_name = Path(file_path).stem + ".csv"
                zipf.writestr(base_name, content.encode('utf-8'))
        
        else:
            # Fallback to uncompressed
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
    
    async def validate_data(self, data_source: Dict[str, Any], config: CSVExportConfig) -> Dict[str, Any]:
        """Validate data source and return statistics."""
        try:
            # Fetch a sample of data for validation
            data = await self._fetch_data(data_source)
            
            if not data:
                return {
                    "is_valid": False,
                    "row_count": 0,
                    "column_count": 0,
                    "issues": [{"type": "error", "message": "No data found"}],
                    "warnings": [],
                    "estimated_file_size_mb": 0.0
                }
            
            # Basic validation
            row_count = len(data)
            column_count = len(data[0]) if data else 0
            issues = []
            warnings = []
            
            # Check data limits
            if row_count > settings.CSV_MAX_ROWS_PER_FILE:
                issues.append({
                    "type": "error",
                    "message": f"Row count ({row_count}) exceeds maximum ({settings.CSV_MAX_ROWS_PER_FILE})"
                })
            
            if column_count > settings.CSV_MAX_COLUMNS:
                issues.append({
                    "type": "error",
                    "message": f"Column count ({column_count}) exceeds maximum ({settings.CSV_MAX_COLUMNS})"
                })
            
            # Estimate file size
            sample_row = data[0] if data else {}
            avg_field_length = sum(len(str(v)) for v in sample_row.values()) / len(sample_row) if sample_row else 0
            estimated_size_bytes = row_count * column_count * avg_field_length * 1.2  # Add overhead
            estimated_size_mb = estimated_size_bytes / (1024 * 1024)
            
            if estimated_size_mb > settings.CSV_MAX_FILE_SIZE_MB:
                warnings.append(f"Estimated file size ({estimated_size_mb:.1f}MB) may exceed limit ({settings.CSV_MAX_FILE_SIZE_MB}MB)")
            
            return {
                "is_valid": len(issues) == 0,
                "row_count": row_count,
                "column_count": column_count,
                "issues": issues,
                "warnings": warnings,
                "estimated_file_size_mb": estimated_size_mb
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "row_count": 0,
                "column_count": 0,
                "issues": [{"type": "error", "message": f"Validation failed: {str(e)}"}],
                "warnings": [],
                "estimated_file_size_mb": 0.0
            }
    
    async def _update_job_status(
        self,
        job_id: int,
        status: JobStatus,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> None:
        """Update job status in database."""
        try:
            from app.core.database import get_db_session, update_job_status
            
            async with get_db_session() as session:
                await update_job_status(
                    session,
                    job_id,
                    status.value,
                    error_message,
                    started_at,
                    completed_at
                )
            logger.info(f"Job {job_id} status updated to {status.value}")
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
    
    async def _update_job_completion(
        self,
        job_id: int,
        status: JobStatus,
        file_path: str,
        file_size: int,
        row_count: int,
        column_count: int,
        generation_time_ms: int
    ) -> None:
        """Update job with completion details."""
        try:
            from app.core.database import get_db_session, update_job_completion
            
            async with get_db_session() as session:
                await update_job_completion(
                    session,
                    job_id,
                    status.value,
                    file_path,
                    file_size,
                    row_count,
                    column_count,
                    generation_time_ms
                )
            logger.info(f"Job {job_id} completed with {row_count} rows, {column_count} columns")
        except Exception as e:
            logger.error(f"Failed to update job completion: {e}")


# Global generator instance
csv_generator = CSVGenerator()


# Export commonly used functions
__all__ = ["csv_generator", "CSVGenerator"]