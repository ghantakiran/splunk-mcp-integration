"""
JSON/XML export generator service.
"""

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles
import dicttoxml
import pandas as pd
from lxml import etree
from structlog import get_logger

from app.core.config import settings
from app.models.json_xml_models import (
    ExportConfiguration,
    ExportFormat,
    JsonFormatting,
    XmlFormatting,
    FieldMapping
)

logger = get_logger(__name__)


class JsonXmlExportGenerator:
    """JSON/XML export generator."""
    
    def __init__(self):
        self.export_path = Path(settings.EXPORT_STORAGE_PATH)
        self.export_path.mkdir(parents=True, exist_ok=True)
    
    async def generate_export(
        self,
        data: List[Dict[str, Any]],
        config: ExportConfiguration,
        job_id: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate export file from data."""
        start_time = time.time()
        
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                extension = self._get_file_extension(config.format)
                filename = f"export_{job_id}_{timestamp}.{extension}"
            
            file_path = self.export_path / filename
            
            # Process data based on configuration
            processed_data = await self._process_data(data, config)
            
            # Generate file based on format
            if config.format in [ExportFormat.JSON, ExportFormat.CUSTOM_JSON]:
                await self._generate_json_file(processed_data, file_path, config.json_config)
            elif config.format == ExportFormat.JSONL:
                await self._generate_jsonl_file(processed_data, file_path, config.json_config)
            elif config.format in [ExportFormat.XML, ExportFormat.CUSTOM_XML]:
                await self._generate_xml_file(processed_data, file_path, config.xml_config)
            else:
                raise ValueError(f"Unsupported export format: {config.format}")
            
            # Apply compression if requested
            if config.compression:
                file_path = await self._apply_compression(file_path, config.compression)
                filename = file_path.name
            
            processing_time = time.time() - start_time
            file_size = file_path.stat().st_size
            
            logger.info(
                "Export generated successfully",
                job_id=job_id,
                filename=filename,
                file_size=file_size,
                records=len(processed_data),
                processing_time=processing_time
            )
            
            return {
                "filename": filename,
                "file_path": str(file_path),
                "file_size": file_size,
                "records_processed": len(processed_data),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(
                "Export generation failed",
                job_id=job_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _process_data(
        self,
        data: List[Dict[str, Any]],
        config: ExportConfiguration
    ) -> List[Dict[str, Any]]:
        """Process data according to configuration."""
        processed_data = data.copy()
        
        # Apply field mappings
        if config.field_mappings:
            processed_data = await self._apply_field_mappings(processed_data, config.field_mappings)
        
        # Flatten nested objects if requested
        if config.flatten_nested:
            processed_data = await self._flatten_data(processed_data)
        
        # Add metadata if requested
        if config.include_metadata:
            processed_data = await self._add_metadata(processed_data)
        
        # Limit records if specified
        if config.max_records and len(processed_data) > config.max_records:
            processed_data = processed_data[:config.max_records]
        
        return processed_data
    
    async def _apply_field_mappings(
        self,
        data: List[Dict[str, Any]],
        mappings: List[FieldMapping]
    ) -> List[Dict[str, Any]]:
        """Apply field mappings to data."""
        mapping_dict = {m.source_field: m for m in mappings}
        
        processed_data = []
        for record in data:
            new_record = {}
            
            for source_field, value in record.items():
                if source_field in mapping_dict:
                    mapping = mapping_dict[source_field]
                    target_field = mapping.target_field
                    
                    # Apply transformation if specified
                    if mapping.transform:
                        value = await self._apply_transformation(value, mapping.transform)
                    
                    # Apply data type conversion
                    if mapping.data_type:
                        value = await self._convert_data_type(value, mapping.data_type)
                    
                    new_record[target_field] = value
                else:
                    new_record[source_field] = value
            
            # Add default values for missing fields
            for mapping in mappings:
                if mapping.target_field not in new_record and mapping.default_value is not None:
                    new_record[mapping.target_field] = mapping.default_value
            
            processed_data.append(new_record)
        
        return processed_data
    
    async def _apply_transformation(self, value: Any, transform: str) -> Any:
        """Apply transformation to value."""
        try:
            if transform == "upper":
                return str(value).upper() if value is not None else value
            elif transform == "lower":
                return str(value).lower() if value is not None else value
            elif transform == "trim":
                return str(value).strip() if value is not None else value
            elif transform == "string":
                return str(value) if value is not None else value
            elif transform == "int":
                return int(value) if value is not None else value
            elif transform == "float":
                return float(value) if value is not None else value
            else:
                return value
        except Exception as e:
            logger.warning(f"Transformation failed: {e}")
            return value
    
    async def _convert_data_type(self, value: Any, data_type: str) -> Any:
        """Convert value to specified data type."""
        try:
            if data_type == "string":
                return str(value) if value is not None else None
            elif data_type == "int":
                return int(value) if value is not None else None
            elif data_type == "float":
                return float(value) if value is not None else None
            elif data_type == "bool":
                return bool(value) if value is not None else None
            else:
                return value
        except Exception as e:
            logger.warning(f"Data type conversion failed: {e}")
            return value
    
    async def _flatten_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten nested objects in data."""
        flattened_data = []
        
        for record in data:
            flattened_record = {}
            self._flatten_dict(record, flattened_record)
            flattened_data.append(flattened_record)
        
        return flattened_data
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten a nested dictionary."""
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                for i, item in enumerate(v):
                    items.extend(self._flatten_dict(item, f"{new_key}[{i}]", sep=sep).items())
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    async def _add_metadata(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add metadata to data."""
        metadata = {
            "_export_timestamp": datetime.utcnow().isoformat(),
            "_export_source": "splunk-mcp-integration",
            "_record_count": len(data)
        }
        
        # Add metadata as first record or merge with existing records
        if data:
            enhanced_data = []
            for i, record in enumerate(data):
                enhanced_record = record.copy()
                enhanced_record.update({
                    "_record_index": i,
                    **metadata
                })
                enhanced_data.append(enhanced_record)
            return enhanced_data
        else:
            return [metadata]
    
    async def _generate_json_file(
        self,
        data: List[Dict[str, Any]],
        file_path: Path,
        json_config: Optional[JsonFormatting]
    ) -> None:
        """Generate JSON file."""
        config = json_config or JsonFormatting()
        
        json_kwargs = {
            "ensure_ascii": config.ensure_ascii,
            "sort_keys": config.sort_keys
        }
        
        if config.compact:
            json_kwargs["separators"] = (',', ':')
        else:
            json_kwargs["indent"] = config.indent
        
        if config.separators:
            json_kwargs["separators"] = config.separators
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            json_content = json.dumps(data, **json_kwargs)
            await f.write(json_content)
    
    async def _generate_jsonl_file(
        self,
        data: List[Dict[str, Any]],
        file_path: Path,
        json_config: Optional[JsonFormatting]
    ) -> None:
        """Generate JSON Lines file."""
        config = json_config or JsonFormatting()
        
        json_kwargs = {
            "ensure_ascii": config.ensure_ascii,
            "sort_keys": config.sort_keys,
            "separators": (',', ':')  # Always compact for JSONL
        }
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            for record in data:
                json_line = json.dumps(record, **json_kwargs)
                await f.write(json_line + '\n')
    
    async def _generate_xml_file(
        self,
        data: List[Dict[str, Any]],
        file_path: Path,
        xml_config: Optional[XmlFormatting]
    ) -> None:
        """Generate XML file."""
        config = xml_config or XmlFormatting()
        
        # Create root element
        root = etree.Element(config.root_tag)
        
        # Add namespace if specified
        if config.namespace:
            root.set("xmlns", config.namespace)
        
        if config.schema_location:
            root.set("xsi:schemaLocation", config.schema_location)
            root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        
        # Add data items
        for record in data:
            item_element = etree.SubElement(root, config.item_tag)
            self._dict_to_xml_element(record, item_element)
        
        # Create tree and write to file
        tree = etree.ElementTree(root)
        
        with open(file_path, 'wb') as f:
            tree.write(
                f,
                encoding=config.encoding,
                xml_declaration=config.xml_declaration,
                pretty_print=config.pretty_print
            )
    
    def _dict_to_xml_element(self, data: Dict[str, Any], parent: etree.Element) -> None:
        """Convert dictionary to XML element."""
        for key, value in data.items():
            # Sanitize key for XML
            clean_key = self._sanitize_xml_tag(key)
            
            if isinstance(value, dict):
                element = etree.SubElement(parent, clean_key)
                self._dict_to_xml_element(value, element)
            elif isinstance(value, list):
                for item in value:
                    element = etree.SubElement(parent, clean_key)
                    if isinstance(item, dict):
                        self._dict_to_xml_element(item, element)
                    else:
                        element.text = str(item) if item is not None else ""
            else:
                element = etree.SubElement(parent, clean_key)
                element.text = str(value) if value is not None else ""
    
    def _sanitize_xml_tag(self, tag: str) -> str:
        """Sanitize string for use as XML tag."""
        # Replace invalid characters with underscores
        sanitized = ''.join(c if c.isalnum() or c in ['_', '-'] else '_' for c in str(tag))
        
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"field_{sanitized}"
        
        return sanitized or "field"
    
    async def _apply_compression(self, file_path: Path, compression: str) -> Path:
        """Apply compression to file."""
        if compression.lower() == "gzip":
            import gzip
            compressed_path = file_path.with_suffix(f"{file_path.suffix}.gz")
            
            async with aiofiles.open(file_path, 'rb') as f_in:
                content = await f_in.read()
            
            with gzip.open(compressed_path, 'wb') as f_out:
                f_out.write(content)
            
            # Remove original file
            file_path.unlink()
            return compressed_path
        
        elif compression.lower() == "zip":
            import zipfile
            compressed_path = file_path.with_suffix(".zip")
            
            with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, file_path.name)
            
            # Remove original file
            file_path.unlink()
            return compressed_path
        
        else:
            raise ValueError(f"Unsupported compression format: {compression}")
    
    def _get_file_extension(self, format_type: ExportFormat) -> str:
        """Get file extension for format."""
        if format_type == ExportFormat.JSON:
            return "json"
        elif format_type == ExportFormat.XML:
            return "xml"
        elif format_type == ExportFormat.JSONL:
            return "jsonl"
        elif format_type == ExportFormat.CUSTOM_JSON:
            return "json"
        elif format_type == ExportFormat.CUSTOM_XML:
            return "xml"
        else:
            return "txt"
    
    async def validate_export_size(
        self,
        data: List[Dict[str, Any]],
        config: ExportConfiguration
    ) -> Dict[str, Any]:
        """Validate export size and estimate resource usage."""
        record_count = len(data)
        
        # Estimate file size based on format
        sample_data = data[:min(100, record_count)] if data else []
        
        if config.format in [ExportFormat.JSON, ExportFormat.CUSTOM_JSON]:
            sample_size = len(json.dumps(sample_data))
        elif config.format == ExportFormat.JSONL:
            sample_size = sum(len(json.dumps(record)) + 1 for record in sample_data)
        elif config.format in [ExportFormat.XML, ExportFormat.CUSTOM_XML]:
            # Rough XML size estimation
            sample_size = len(json.dumps(sample_data)) * 1.5  # XML is typically larger
        else:
            sample_size = len(str(sample_data))
        
        estimated_size_mb = (sample_size * record_count / len(sample_data) / 1024 / 1024) if sample_data else 0
        
        # Check limits
        warnings = []
        if estimated_size_mb > settings.MAX_FILE_SIZE_MB:
            warnings.append(f"Estimated file size ({estimated_size_mb:.1f}MB) exceeds limit ({settings.MAX_FILE_SIZE_MB}MB)")
        
        if config.max_records and record_count > config.max_records:
            warnings.append(f"Record count ({record_count}) exceeds specified limit ({config.max_records})")
        
        return {
            "record_count": record_count,
            "estimated_size_mb": estimated_size_mb,
            "warnings": warnings,
            "valid": len(warnings) == 0
        }
    
    async def cleanup_old_files(self, max_age_hours: int = None) -> int:
        """Clean up old export files."""
        max_age = max_age_hours or settings.FILE_RETENTION_HOURS
        cutoff_time = time.time() - (max_age * 3600)
        
        cleaned_count = 0
        
        try:
            for file_path in self.export_path.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
                    logger.info(f"Cleaned up old export file: {file_path.name}")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        return cleaned_count