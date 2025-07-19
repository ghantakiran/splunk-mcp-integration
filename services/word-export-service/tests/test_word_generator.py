#!/usr/bin/env python3
"""
Test cases for Word document generator.

This module contains test cases for the WordDocumentGenerator class
and related functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.word_generator import WordDocumentGenerator
from app.models.word_models import (
    DocumentConfig,
    DocumentMetadata,
    DocumentLayout,
    DocumentSection,
    Template,
    OutputFormat,
    ColorScheme,
    JobStatus
)


class TestWordDocumentGenerator:
    """Test cases for WordDocumentGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create WordDocumentGenerator instance."""
        return WordDocumentGenerator()
    
    @pytest.fixture
    def sample_document_config(self):
        """Create sample document configuration."""
        return DocumentConfig(
            metadata=DocumentMetadata(
                title="Test Document",
                subject="Test Subject",
                author="Test Author",
                company="Test Company"
            ),
            template=Template.PROFESSIONAL,
            layout=DocumentLayout(
                sections=[
                    DocumentSection(
                        id="intro",
                        title="Introduction",
                        content_type="text",
                        text_content="This is a test document."
                    )
                ]
            ),
            color_scheme=ColorScheme.BLUE
        )
    
    @pytest.fixture
    def sample_data_source(self):
        """Create sample data source."""
        return {
            "static_source": {
                "data": {
                    "sample_data": [
                        {"name": "Item 1", "value": 100},
                        {"name": "Item 2", "value": 200}
                    ]
                }
            }
        }
    
    def test_initialization(self, generator):
        """Test generator initialization."""
        assert generator is not None
        assert hasattr(generator, 'color_schemes')
        assert hasattr(generator, 'font_mapping')
        assert ColorScheme.BLUE in generator.color_schemes
    
    def test_color_schemes(self, generator):
        """Test color scheme configuration."""
        blue_colors = generator.color_schemes[ColorScheme.BLUE]
        assert isinstance(blue_colors, list)
        assert len(blue_colors) > 0
        assert all(color.startswith('#') for color in blue_colors)
    
    def test_font_mapping(self, generator):
        """Test font mapping configuration."""
        from app.models.word_models import FontFamily
        
        assert FontFamily.CALIBRI in generator.font_mapping
        assert generator.font_mapping[FontFamily.CALIBRI] == "Calibri"
        assert FontFamily.ARIAL in generator.font_mapping
        assert generator.font_mapping[FontFamily.ARIAL] == "Arial"
    
    def test_hex_to_rgb_conversion(self, generator):
        """Test hex to RGB color conversion."""
        # Test black
        rgb = generator._hex_to_rgb("#000000")
        assert rgb == (0, 0, 0)
        
        # Test white
        rgb = generator._hex_to_rgb("#FFFFFF")
        assert rgb == (255, 255, 255)
        
        # Test red
        rgb = generator._hex_to_rgb("#FF0000")
        assert rgb == (255, 0, 0)
        
        # Test with lowercase
        rgb = generator._hex_to_rgb("#ff0000")
        assert rgb == (255, 0, 0)
        
        # Test without # prefix
        rgb = generator._hex_to_rgb("FF0000")
        assert rgb == (255, 0, 0)
    
    @pytest.mark.asyncio
    async def test_fetch_data_static_source(self, generator, sample_data_source):
        """Test fetching data from static source."""
        data = await generator._fetch_data(sample_data_source)
        
        assert "sample_data" in data
        assert len(data["sample_data"]) == 2
        assert data["sample_data"][0]["name"] == "Item 1"
    
    @pytest.mark.asyncio
    async def test_fetch_data_query_source(self, generator):
        """Test fetching data from query source."""
        query_source = {
            "query_source": {
                "query": "SELECT * FROM test_table",
                "parameters": {}
            }
        }
        
        data = await generator._fetch_data(query_source)
        assert "query_result" in data
    
    @pytest.mark.asyncio
    async def test_fetch_data_file_source(self, generator):
        """Test fetching data from file source."""
        file_source = {
            "file_source": {
                "file_path": "/path/to/file.csv",
                "file_format": "csv"
            }
        }
        
        data = await generator._fetch_data(file_source)
        assert "file_data" in data
    
    @pytest.mark.asyncio
    async def test_fetch_data_empty_source(self, generator):
        """Test fetching data from empty source."""
        data = await generator._fetch_data({})
        assert data == {}
    
    @pytest.mark.asyncio
    async def test_count_pages(self, generator):
        """Test page counting functionality."""
        # Test with non-existent file
        count = await generator._count_pages("/non/existent/file.docx")
        assert count == 1  # Default fallback
    
    @pytest.mark.asyncio
    @patch('app.services.word_generator.WordDocumentGenerator._update_job_status')
    @patch('app.services.word_generator.WordDocumentGenerator._update_job_completion')
    @patch('app.services.word_generator.WordDocumentGenerator._fetch_data')
    @patch('app.services.word_generator.WordDocumentGenerator._create_word_document')
    @patch('app.services.word_generator.WordDocumentGenerator._save_document')
    @patch('app.services.word_generator.WordDocumentGenerator._count_pages')
    @patch('os.path.getsize')
    async def test_generate_document_success(
        self,
        mock_getsize,
        mock_count_pages,
        mock_save_document,
        mock_create_document,
        mock_fetch_data,
        mock_update_completion,
        mock_update_status,
        generator,
        sample_document_config,
        sample_data_source
    ):
        """Test successful document generation."""
        # Setup mocks
        mock_fetch_data.return_value = sample_data_source
        mock_create_document.return_value = MagicMock()
        mock_save_document.return_value = None
        mock_count_pages.return_value = 5
        mock_getsize.return_value = 1024000  # 1MB
        mock_update_status.return_value = None
        mock_update_completion.return_value = None
        
        # Execute
        success, file_path, error_message = await generator.generate_document(
            job_id=123,
            user_id=456,
            document_config=sample_document_config,
            data_source=sample_data_source,
            output_format=OutputFormat.DOCX
        )
        
        # Verify
        assert success is True
        assert file_path is not None
        assert error_message is None
        assert file_path.endswith('.docx')
        
        # Verify calls
        mock_fetch_data.assert_called_once_with(sample_data_source)
        mock_create_document.assert_called_once()
        mock_save_document.assert_called_once()
        mock_count_pages.assert_called_once()
        mock_update_status.assert_called()
        mock_update_completion.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.word_generator.WordDocumentGenerator._update_job_status')
    @patch('app.services.word_generator.WordDocumentGenerator._fetch_data')
    async def test_generate_document_failure(
        self,
        mock_fetch_data,
        mock_update_status,
        generator,
        sample_document_config,
        sample_data_source
    ):
        """Test document generation failure."""
        # Setup mocks to raise exception
        mock_fetch_data.side_effect = Exception("Test error")
        mock_update_status.return_value = None
        
        # Execute
        success, file_path, error_message = await generator.generate_document(
            job_id=123,
            user_id=456,
            document_config=sample_document_config,
            data_source=sample_data_source,
            output_format=OutputFormat.DOCX
        )
        
        # Verify
        assert success is False
        assert file_path is None
        assert error_message == "Test error"
        
        # Verify status was updated to failed
        mock_update_status.assert_called()
        call_args = mock_update_status.call_args_list[-1]
        assert call_args[0][1] == JobStatus.FAILED
    
    def test_create_bar_chart(self, generator):
        """Test bar chart creation."""
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots()
        labels = ["A", "B", "C"]
        datasets = [{"label": "Series 1", "data": [1, 2, 3]}]
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
        config = MagicMock()
        
        # Should not raise an exception
        generator._create_bar_chart(ax, labels, datasets, colors, config)
        
        plt.close(fig)
    
    def test_create_line_chart(self, generator):
        """Test line chart creation."""
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots()
        labels = ["A", "B", "C"]
        datasets = [{"label": "Series 1", "data": [1, 2, 3]}]
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
        config = MagicMock()
        
        # Should not raise an exception
        generator._create_line_chart(ax, labels, datasets, colors, config)
        
        plt.close(fig)
    
    def test_create_pie_chart(self, generator):
        """Test pie chart creation."""
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots()
        labels = ["A", "B", "C"]
        dataset = {"label": "Series 1", "data": [1, 2, 3]}
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
        config = MagicMock()
        
        # Should not raise an exception
        generator._create_pie_chart(ax, labels, dataset, colors, config)
        
        plt.close(fig)
    
    @pytest.mark.asyncio
    async def test_generate_chart_image(self, generator):
        """Test chart image generation."""
        from app.models.word_models import Chart, ChartData, ChartConfig, ChartType
        
        chart = Chart(
            id="test_chart",
            data=ChartData(
                labels=["A", "B", "C"],
                datasets=[{"label": "Series 1", "data": [1, 2, 3]}]
            ),
            config=ChartConfig(
                chart_type=ChartType.BAR,
                title="Test Chart",
                width=400,
                height=300
            )
        )
        
        image_buffer = await generator._generate_chart_image(chart, ColorScheme.BLUE)
        
        # Should generate an image
        assert image_buffer is not None
        assert hasattr(image_buffer, 'read')
        
        # Image should have content
        image_content = image_buffer.read()
        assert len(image_content) > 0
        
        # Reset buffer position
        image_buffer.seek(0)


if __name__ == "__main__":
    pytest.main([__file__])