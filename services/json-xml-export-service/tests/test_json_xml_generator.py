"""
Tests for JSON/XML export generator.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from lxml import etree

from app.models.json_xml_models import ExportConfiguration, ExportFormat, JsonFormatting, XmlFormatting, FieldMapping
from app.services.json_xml_generator import JsonXmlExportGenerator


class TestJsonXmlExportGenerator:
    """Test cases for JSON/XML export generator."""
    
    @pytest.fixture
    def generator(self, temp_dir):
        """Create generator instance with temporary directory."""
        generator = JsonXmlExportGenerator()
        generator.export_path = Path(temp_dir)
        return generator
    
    @pytest.mark.asyncio
    async def test_generate_json_export(self, generator, sample_data, json_export_config):
        """Test JSON export generation."""
        job_id = "test-job-001"
        
        result = await generator.generate_export(
            data=sample_data,
            config=json_export_config,
            job_id=job_id,
            filename="test_export.json"
        )
        
        assert result["filename"] == "test_export.json"
        assert result["records_processed"] == len(sample_data)
        assert result["file_size"] > 0
        assert result["processing_time"] > 0
        
        # Verify file exists and contains valid JSON
        file_path = Path(result["file_path"])
        assert file_path.exists()
        
        with open(file_path, 'r') as f:
            exported_data = json.load(f)
        
        assert isinstance(exported_data, list)
        assert len(exported_data) == len(sample_data)
        
        # Check if metadata was added
        if json_export_config.include_metadata:
            for record in exported_data:
                assert "_export_timestamp" in record
                assert "_export_source" in record
                assert "_record_index" in record
    
    @pytest.mark.asyncio
    async def test_generate_xml_export(self, generator, sample_data, xml_export_config):
        """Test XML export generation."""
        job_id = "test-job-002"
        
        result = await generator.generate_export(
            data=sample_data,
            config=xml_export_config,
            job_id=job_id,
            filename="test_export.xml"
        )
        
        assert result["filename"] == "test_export.xml"
        assert result["records_processed"] == len(sample_data)
        assert result["file_size"] > 0
        
        # Verify file exists and contains valid XML
        file_path = Path(result["file_path"])
        assert file_path.exists()
        
        tree = etree.parse(str(file_path))
        root = tree.getroot()
        
        assert root.tag == xml_export_config.xml_config.root_tag
        
        # Check number of records
        records = root.findall(xml_export_config.xml_config.item_tag)
        assert len(records) == len(sample_data)
        
        # Verify some data
        first_record = records[0]
        assert first_record.find("id") is not None
        assert first_record.find("name") is not None
    
    @pytest.mark.asyncio
    async def test_generate_jsonl_export(self, generator, sample_data, jsonl_export_config):
        """Test JSON Lines export generation."""
        job_id = "test-job-003"
        
        result = await generator.generate_export(
            data=sample_data,
            config=jsonl_export_config,
            job_id=job_id,
            filename="test_export.jsonl"
        )
        
        assert result["filename"] == "test_export.jsonl"
        assert result["records_processed"] == len(sample_data)
        
        # Verify file exists and contains valid JSON Lines
        file_path = Path(result["file_path"])
        assert file_path.exists()
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == len(sample_data)
        
        # Each line should be valid JSON
        for line in lines:
            record = json.loads(line.strip())
            assert isinstance(record, dict)
    
    @pytest.mark.asyncio
    async def test_field_mapping(self, generator, sample_data):
        """Test field mapping functionality."""
        mappings = [
            FieldMapping(
                source_field="name",
                target_field="record_name",
                transform="upper"
            ),
            FieldMapping(
                source_field="value",
                target_field="amount",
                data_type="string"
            ),
            FieldMapping(
                source_field="nonexistent",
                target_field="default_field",
                default_value="default_value"
            )
        ]
        
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            field_mappings=mappings,
            include_metadata=False
        )
        
        result = await generator.generate_export(
            data=sample_data,
            config=config,
            job_id="mapping-test"
        )
        
        # Verify mapping results
        file_path = Path(result["file_path"])
        with open(file_path, 'r') as f:
            exported_data = json.load(f)
        
        first_record = exported_data[0]
        assert first_record["record_name"] == "TEST RECORD 1"  # Uppercase transformation
        assert first_record["amount"] == "100"  # String conversion
        assert first_record["default_field"] == "default_value"  # Default value
    
    @pytest.mark.asyncio
    async def test_data_flattening(self, generator, nested_sample_data):
        """Test data flattening functionality."""
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            flatten_nested=True,
            include_metadata=False
        )
        
        result = await generator.generate_export(
            data=nested_sample_data,
            config=config,
            job_id="flatten-test"
        )
        
        # Verify flattening results
        file_path = Path(result["file_path"])
        with open(file_path, 'r') as f:
            exported_data = json.load(f)
        
        first_record = exported_data[0]
        
        # Check flattened fields
        assert "user.id" in first_record
        assert "user.profile.name" in first_record
        assert "user.profile.contact.email" in first_record
        assert "activity.login_count" in first_record
        assert "activity.sessions[0].id" in first_record
    
    @pytest.mark.asyncio
    async def test_compression_gzip(self, generator, sample_data):
        """Test GZIP compression."""
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            compression="gzip",
            include_metadata=False
        )
        
        result = await generator.generate_export(
            data=sample_data,
            config=config,
            job_id="gzip-test"
        )
        
        assert result["filename"].endswith(".gz")
        
        # Verify compressed file exists
        file_path = Path(result["file_path"])
        assert file_path.exists()
        
        # Verify it's actually compressed
        import gzip
        with gzip.open(file_path, 'rt') as f:
            decompressed_data = json.load(f)
        
        assert len(decompressed_data) == len(sample_data)
    
    @pytest.mark.asyncio
    async def test_compression_zip(self, generator, sample_data):
        """Test ZIP compression."""
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            compression="zip",
            include_metadata=False
        )
        
        result = await generator.generate_export(
            data=sample_data,
            config=config,
            job_id="zip-test"
        )
        
        assert result["filename"].endswith(".zip")
        
        # Verify compressed file exists
        file_path = Path(result["file_path"])
        assert file_path.exists()
        
        # Verify it's actually compressed
        import zipfile
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            assert len(zip_file.namelist()) == 1
    
    @pytest.mark.asyncio
    async def test_validate_export_size(self, generator, large_sample_data):
        """Test export size validation."""
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            max_records=500
        )
        
        validation_result = await generator.validate_export_size(
            large_sample_data,
            config
        )
        
        assert validation_result["record_count"] == len(large_sample_data)
        assert validation_result["estimated_size_mb"] > 0
        assert len(validation_result["warnings"]) > 0  # Should warn about record limit
        assert not validation_result["valid"]  # Should be invalid due to record limit
    
    @pytest.mark.asyncio
    async def test_max_records_limit(self, generator, large_sample_data):
        """Test maximum records limitation."""
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            max_records=100,
            include_metadata=False
        )
        
        result = await generator.generate_export(
            data=large_sample_data,
            config=config,
            job_id="limit-test"
        )
        
        # Should process only max_records
        assert result["records_processed"] == 100
        
        # Verify actual file content
        file_path = Path(result["file_path"])
        with open(file_path, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 100
    
    @pytest.mark.asyncio
    async def test_custom_json_formatting(self, generator, sample_data):
        """Test custom JSON formatting options."""
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            json_config=JsonFormatting(
                indent=None,  # Compact
                sort_keys=False,
                ensure_ascii=True,
                compact=True
            ),
            include_metadata=False
        )
        
        result = await generator.generate_export(
            data=sample_data,
            config=config,
            job_id="custom-json-test"
        )
        
        # Verify file is compact (no indentation)
        file_path = Path(result["file_path"])
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Compact JSON should not have newlines within the structure
        assert content.count('\n') == 0 or content.count('\n') == 1  # Only final newline
    
    @pytest.mark.asyncio
    async def test_custom_xml_formatting(self, generator, sample_data):
        """Test custom XML formatting options."""
        config = ExportConfiguration(
            format=ExportFormat.XML,
            xml_config=XmlFormatting(
                pretty_print=False,
                root_tag="custom_root",
                item_tag="custom_item",
                xml_declaration=False,
                namespace="http://example.com/ns"
            ),
            include_metadata=False
        )
        
        result = await generator.generate_export(
            data=sample_data,
            config=config,
            job_id="custom-xml-test"
        )
        
        # Verify XML structure
        file_path = Path(result["file_path"])
        tree = etree.parse(str(file_path))
        root = tree.getroot()
        
        assert root.tag == "custom_root"
        assert root.nsmap[None] == "http://example.com/ns"
        
        items = root.findall("custom_item")
        assert len(items) == len(sample_data)
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_format(self, generator, sample_data):
        """Test error handling for invalid export format."""
        # This would normally be caught by Pydantic validation,
        # but we can test the generator's handling of edge cases
        with pytest.raises(ValueError):
            config = ExportConfiguration(format="invalid_format")  # This should fail validation
    
    @pytest.mark.asyncio
    async def test_filename_generation(self, generator, sample_data, json_export_config):
        """Test automatic filename generation."""
        job_id = "filename-test"
        
        result = await generator.generate_export(
            data=sample_data,
            config=json_export_config,
            job_id=job_id
            # No filename provided
        )
        
        # Should generate filename with job_id and timestamp
        assert job_id in result["filename"]
        assert result["filename"].endswith(".json")
    
    def test_get_file_extension(self, generator):
        """Test file extension determination."""
        assert generator._get_file_extension(ExportFormat.JSON) == "json"
        assert generator._get_file_extension(ExportFormat.XML) == "xml"
        assert generator._get_file_extension(ExportFormat.JSONL) == "jsonl"
        assert generator._get_file_extension(ExportFormat.CUSTOM_JSON) == "json"
        assert generator._get_file_extension(ExportFormat.CUSTOM_XML) == "xml"
    
    def test_sanitize_xml_tag(self, generator):
        """Test XML tag sanitization."""
        assert generator._sanitize_xml_tag("valid_tag") == "valid_tag"
        assert generator._sanitize_xml_tag("123invalid") == "field_123invalid"
        assert generator._sanitize_xml_tag("invalid-chars!@#") == "invalid-chars___"
        assert generator._sanitize_xml_tag("") == "field"
    
    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, generator, temp_dir):
        """Test cleanup of old export files."""
        # Create some test files
        test_files = []
        for i in range(3):
            test_file = Path(temp_dir) / f"test_file_{i}.json"
            test_file.write_text('{"test": "data"}')
            test_files.append(test_file)
        
        # All files should exist
        for file_path in test_files:
            assert file_path.exists()
        
        # Cleanup with 0 hour retention (should delete all)
        cleaned_count = await generator.cleanup_old_files(max_age_hours=0)
        
        assert cleaned_count == len(test_files)
        
        # Files should no longer exist
        for file_path in test_files:
            assert not file_path.exists()