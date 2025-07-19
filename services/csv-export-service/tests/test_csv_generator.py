#!/usr/bin/env python3
"""
Tests for CSV Generator Service.
"""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, patch
import pytest

from app.services.csv_generator import CSVGenerator
from app.models.csv_models import (
    CSVExportConfig, 
    ExportFormat, 
    Encoding, 
    QuoteStyle,
    NullHandling,
    DataType,
    CompressionType
)


class TestCSVGenerator:
    """Tests for CSV Generator."""
    
    @pytest.fixture
    def csv_generator(self):
        """Create CSV generator instance."""
        return CSVGenerator()
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return [
            {"id": 1, "name": "Alice", "value": 100.5, "date": "2024-01-01"},
            {"id": 2, "name": "Bob", "value": 200.0, "date": "2024-01-02"},
            {"id": 3, "name": "Charlie", "value": 150.75, "date": "2024-01-03"}
        ]
    
    @pytest.fixture
    def default_config(self):
        """Default export configuration."""
        return CSVExportConfig()
    
    @pytest.fixture
    def data_source_static(self, sample_data):
        """Static data source."""
        return {
            "static_source": {
                "data": sample_data
            }
        }
    
    @pytest.mark.asyncio
    async def test_fetch_data_static_source(self, csv_generator, data_source_static, sample_data):
        """Test fetching data from static source."""
        result = await csv_generator._fetch_data(data_source_static)
        
        assert result == sample_data
        assert len(result) == 3
        assert result[0]["name"] == "Alice"
    
    @pytest.mark.asyncio
    async def test_fetch_data_query_source(self, csv_generator):
        """Test fetching data from query source."""
        data_source = {
            "query_source": {
                "query": "SELECT * FROM test_table",
                "parameters": {}
            }
        }
        
        result = await csv_generator._fetch_data(data_source)
        
        # Should return mock data from _execute_query
        assert len(result) == 3
        assert result[0]["name"] == "Sample Record 1"
    
    @pytest.mark.asyncio
    async def test_fetch_data_file_source(self, csv_generator):
        """Test fetching data from file source."""
        data_source = {
            "file_source": {
                "file_path": "/path/to/test.csv",
                "file_format": "csv"
            }
        }
        
        result = await csv_generator._fetch_data(data_source)
        
        # Should return mock data from _load_from_file
        assert len(result) == 2
        assert result[0]["column1"] == "value1"
    
    @pytest.mark.asyncio
    async def test_process_data_basic(self, csv_generator, sample_data, default_config):
        """Test basic data processing."""
        result = await csv_generator._process_data(sample_data, default_config)
        
        assert len(result) == 3
        assert result == sample_data  # No processing applied with default config
    
    @pytest.mark.asyncio
    async def test_process_data_with_limits(self, csv_generator, sample_data):
        """Test data processing with row limits."""
        config = CSVExportConfig()
        config.data_processing.max_rows = 2
        config.data_processing.skip_rows = 1
        
        result = await csv_generator._process_data(sample_data, config)
        
        # Should skip 1 row and limit to 2 rows
        assert len(result) == 2
        assert result[0]["name"] == "Bob"  # First row after skipping Alice
        assert result[1]["name"] == "Charlie"
    
    @pytest.mark.asyncio
    async def test_process_data_remove_duplicates(self, csv_generator):
        """Test removing duplicate rows."""
        data_with_duplicates = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 1, "name": "Alice"},  # Duplicate
            {"id": 3, "name": "Charlie"}
        ]
        
        config = CSVExportConfig()
        config.data_processing.remove_duplicate_rows = True
        
        result = await csv_generator._process_data(data_with_duplicates, config)
        
        assert len(result) == 3  # One duplicate removed
        names = [row["name"] for row in result]
        assert names.count("Alice") == 1
    
    @pytest.mark.asyncio
    async def test_process_data_null_handling(self, csv_generator):
        """Test null value handling."""
        data_with_nulls = [
            {"id": 1, "name": "Alice", "value": None},
            {"id": 2, "name": None, "value": 100},
            {"id": 3, "name": "Charlie", "value": ""}
        ]
        
        config = CSVExportConfig()
        config.data_processing.null_handling = NullHandling.NULL
        
        result = await csv_generator._process_data(data_with_nulls, config)
        
        assert result[0]["value"] == "NULL"
        assert result[1]["name"] == "NULL"
        assert result[2]["value"] == "NULL"  # Empty string treated as null
    
    def test_convert_data_type(self, csv_generator):
        """Test data type conversion."""
        # Test string conversion
        assert csv_generator._convert_data_type("123", DataType.STRING) == "123"
        
        # Test integer conversion
        assert csv_generator._convert_data_type("123", DataType.INTEGER) == 123
        assert csv_generator._convert_data_type("123.7", DataType.INTEGER) == 123
        
        # Test float conversion
        assert csv_generator._convert_data_type("123.45", DataType.FLOAT) == 123.45
        
        # Test boolean conversion
        assert csv_generator._convert_data_type("true", DataType.BOOLEAN) is True
        assert csv_generator._convert_data_type("false", DataType.BOOLEAN) is False
        assert csv_generator._convert_data_type("1", DataType.BOOLEAN) is True
        assert csv_generator._convert_data_type("0", DataType.BOOLEAN) is False
    
    def test_remove_empty_rows(self, csv_generator):
        """Test removing empty rows."""
        data_with_empty = [
            {"id": 1, "name": "Alice"},
            {"id": None, "name": None},  # Empty row
            {"id": "", "name": ""},      # Empty row
            {"id": 2, "name": "Bob"}
        ]
        
        result = csv_generator._remove_empty_rows(data_with_empty)
        
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"
    
    def test_trim_whitespace(self, csv_generator):
        """Test trimming whitespace."""
        data_with_whitespace = [
            {"id": 1, "name": "  Alice  "},
            {"id": 2, "name": "\tBob\n"},
            {"id": 3, "name": 123}  # Non-string value
        ]
        
        result = csv_generator._trim_whitespace(data_with_whitespace)
        
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"
        assert result[2]["name"] == 123  # Unchanged
    
    @pytest.mark.asyncio
    async def test_generate_csv_content_basic(self, csv_generator, sample_data, default_config):
        """Test basic CSV content generation."""
        content = await csv_generator._generate_csv_content(sample_data, default_config)
        
        lines = content.strip().split('\n')
        assert len(lines) == 4  # 1 header + 3 data rows
        
        # Check header
        assert lines[0] == 'id,name,value,date'
        
        # Check first data row
        assert 'Alice' in lines[1]
        assert '100.5' in lines[1]
    
    @pytest.mark.asyncio
    async def test_generate_csv_content_custom_delimiter(self, csv_generator, sample_data):
        """Test CSV generation with custom delimiter."""
        config = CSVExportConfig()
        config.formatting.delimiter = ";"
        
        content = await csv_generator._generate_csv_content(sample_data, config)
        
        lines = content.strip().split('\n')
        # Should use semicolon delimiter
        assert lines[0] == 'id;name;value;date'
        assert 'Alice' in lines[1] and ';' in lines[1]
    
    @pytest.mark.asyncio
    async def test_generate_csv_content_no_header(self, csv_generator, sample_data):
        """Test CSV generation without header."""
        config = CSVExportConfig()
        config.header_config.include_header = False
        
        content = await csv_generator._generate_csv_content(sample_data, config)
        
        lines = content.strip().split('\n')
        assert len(lines) == 3  # Only data rows, no header
        assert 'Alice' in lines[0]  # First line is data
    
    @pytest.mark.asyncio
    async def test_generate_csv_content_custom_headers(self, csv_generator, sample_data):
        """Test CSV generation with custom headers."""
        config = CSVExportConfig()
        config.header_config.custom_headers = ["ID", "Full Name", "Amount", "Date"]
        
        content = await csv_generator._generate_csv_content(sample_data, config)
        
        lines = content.strip().split('\n')
        assert lines[0] == 'ID,Full Name,Amount,Date'
    
    def test_transform_headers(self, csv_generator):
        """Test header transformation."""
        headers = ["first_name", "last_name", "email_address"]
        
        # Test uppercase transformation
        header_config = type('obj', (object,), {
            'header_case': 'upper',
            'header_prefix': None,
            'header_suffix': None
        })
        
        result = csv_generator._transform_headers(headers, header_config)
        assert result == ["FIRST_NAME", "LAST_NAME", "EMAIL_ADDRESS"]
        
        # Test with prefix and suffix
        header_config.header_prefix = "col_"
        header_config.header_suffix = "_field"
        header_config.header_case = "lower"
        
        result = csv_generator._transform_headers(headers, header_config)
        assert result == ["col_first_name_field", "col_last_name_field", "col_email_address_field"]
    
    def test_get_file_extension(self, csv_generator):
        """Test file extension generation."""
        # Test basic CSV
        ext = csv_generator._get_file_extension(ExportFormat.CSV, CompressionType.NONE)
        assert ext == "csv"
        
        # Test TSV
        ext = csv_generator._get_file_extension(ExportFormat.TSV, CompressionType.NONE)
        assert ext == "tsv"
        
        # Test with GZIP compression
        ext = csv_generator._get_file_extension(ExportFormat.CSV, CompressionType.GZIP)
        assert ext == "csv.gz"
        
        # Test with ZIP compression
        ext = csv_generator._get_file_extension(ExportFormat.CSV, CompressionType.ZIP)
        assert ext == "zip"
    
    @pytest.mark.asyncio
    async def test_write_file_uncompressed(self, csv_generator):
        """Test writing uncompressed file."""
        content = "id,name,value\n1,Alice,100"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            compression_config = type('obj', (object,), {
                'compression_type': CompressionType.NONE
            })
            
            await csv_generator._write_file(content, tmp_path, compression_config)
            
            # Read and verify content
            with open(tmp_path, 'r') as f:
                written_content = f.read()
            
            assert written_content == content
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    @pytest.mark.asyncio
    async def test_validate_data_success(self, csv_generator, data_source_static):
        """Test successful data validation."""
        config = CSVExportConfig()
        
        result = await csv_generator.validate_data(data_source_static, config)
        
        assert result["is_valid"] is True
        assert result["row_count"] == 3
        assert result["column_count"] == 4
        assert len(result["issues"]) == 0
        assert result["estimated_file_size_mb"] > 0
    
    @pytest.mark.asyncio
    async def test_validate_data_empty_source(self, csv_generator):
        """Test validation with empty data source."""
        empty_source = {"static_source": {"data": []}}
        config = CSVExportConfig()
        
        result = await csv_generator.validate_data(empty_source, config)
        
        assert result["is_valid"] is False
        assert result["row_count"] == 0
        assert len(result["issues"]) > 0
        assert result["issues"][0]["type"] == "error"
        assert result["issues"][0]["message"] == "No data found"
    
    @pytest.mark.asyncio
    async def test_validate_data_too_many_rows(self, csv_generator, data_source_static):
        """Test validation with too many rows."""
        # Create data source with many rows
        large_data = [{"id": i, "value": i} for i in range(2000000)]  # Exceeds limit
        large_source = {"static_source": {"data": large_data}}
        config = CSVExportConfig()
        
        with patch.object(csv_generator, '_fetch_data', return_value=large_data):
            result = await csv_generator.validate_data(large_source, config)
        
        assert result["is_valid"] is False
        assert any("exceeds maximum" in issue["message"] for issue in result["issues"])
    
    @pytest.mark.asyncio
    async def test_generate_csv_full_process_mock(self, csv_generator, data_source_static, default_config):
        """Test full CSV generation process with mocked database operations."""
        with patch.object(csv_generator, '_update_job_status') as mock_update_status, \
             patch.object(csv_generator, '_update_job_completion') as mock_update_completion, \
             patch('tempfile.mkdtemp', return_value='/tmp/test'), \
             patch('os.path.join', return_value='/tmp/test/output.csv'), \
             patch('os.path.getsize', return_value=1024):
            
            mock_update_status.return_value = None
            mock_update_completion.return_value = None
            
            success, file_path, error = await csv_generator.generate_csv(
                job_id=123,
                user_id=1,
                data_source=data_source_static,
                export_config=default_config,
                job_name="Test Export"
            )
            
            assert success is True
            assert file_path is not None
            assert error is None
            
            # Verify database updates were called
            mock_update_status.assert_called()
            mock_update_completion.assert_called()