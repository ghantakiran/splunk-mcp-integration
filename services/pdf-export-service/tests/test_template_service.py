"""
Tests for template service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from app.services.template_service import TemplateService, TemplateError
from app.models.pdf_models import TemplateType


@pytest.fixture
def template_service():
    """Create template service instance."""
    return TemplateService()


@pytest.fixture
def mock_template_data():
    """Mock template data."""
    return {
        "name": "Test Template",
        "template_type": "report",
        "description": "Test template description",
        "template_content": "<html><body><h1>{{ title }}</h1><p>{{ content }}</p></body></html>",
        "css_content": "body { font-family: Arial, sans-serif; }",
        "variables": {"title": "Default Title", "content": "Default Content"},
        "layout_config": {"page_size": "a4", "orientation": "portrait"}
    }


@pytest.fixture
def mock_template_response():
    """Mock template response from database."""
    return {
        "id": 1,
        "name": "Test Template",
        "template_type": "report",
        "description": "Test template description",
        "template_content": "<html><body><h1>{{ title }}</h1><p>{{ content }}</p></body></html>",
        "css_content": "body { font-family: Arial, sans-serif; }",
        "variables": {"title": "Default Title", "content": "Default Content"},
        "layout_config": {"page_size": "a4", "orientation": "portrait"},
        "created_by": 1,
        "is_active": True,
        "is_default": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


class TestTemplateService:
    """Test template service functionality."""
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_create_template_success(self, mock_execute_query, template_service, 
                                         mock_template_data, mock_template_response):
        """Test successful template creation."""
        mock_execute_query.side_effect = [1, mock_template_response]
        
        result = await template_service.create_template(mock_template_data, 1)
        
        assert result is not None
        assert result['id'] == 1
        assert result['name'] == "Test Template"
        assert mock_execute_query.call_count == 2
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_create_template_with_invalid_content(self, mock_execute_query, template_service):
        """Test template creation with invalid content."""
        invalid_template_data = {
            "name": "Invalid Template",
            "template_type": "report",
            "template_content": "<html><body>{{ invalid_syntax }",  # Invalid Jinja2
            "css_content": "",
            "variables": {},
            "layout_config": {}
        }
        
        with pytest.raises(TemplateError):
            await template_service.create_template(invalid_template_data, 1)
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    @patch('app.services.template_service.get_redis_connection')
    async def test_get_template_from_cache(self, mock_redis, mock_execute_query, 
                                         template_service, mock_template_response):
        """Test template retrieval from cache."""
        mock_redis_client = AsyncMock()
        mock_redis_client.get.return_value = json.dumps(mock_template_response, default=str)
        mock_redis.return_value.__aenter__.return_value = mock_redis_client
        
        result = await template_service.get_template(1)
        
        assert result is not None
        assert result['id'] == 1
        assert result['name'] == "Test Template"
        mock_execute_query.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    @patch('app.services.template_service.get_redis_connection')
    async def test_get_template_from_database(self, mock_redis, mock_execute_query, 
                                            template_service, mock_template_response):
        """Test template retrieval from database."""
        mock_redis_client = AsyncMock()
        mock_redis_client.get.return_value = None
        mock_redis_client.setex.return_value = True
        mock_redis.return_value.__aenter__.return_value = mock_redis_client
        
        mock_execute_query.return_value = mock_template_response
        
        result = await template_service.get_template(1)
        
        assert result is not None
        assert result['id'] == 1
        assert result['name'] == "Test Template"
        mock_execute_query.assert_called_once()
        mock_redis_client.setex.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    @patch('app.services.template_service.get_redis_connection')
    async def test_get_template_not_found(self, mock_redis, mock_execute_query, template_service):
        """Test template retrieval when template not found."""
        mock_redis_client = AsyncMock()
        mock_redis_client.get.return_value = None
        mock_redis.return_value.__aenter__.return_value = mock_redis_client
        
        mock_execute_query.return_value = None
        
        result = await template_service.get_template(999)
        
        assert result is None
        mock_execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_update_template_success(self, mock_execute_query, template_service, 
                                         mock_template_response):
        """Test successful template update."""
        update_data = {
            "name": "Updated Template",
            "description": "Updated description"
        }
        
        updated_template = mock_template_response.copy()
        updated_template.update(update_data)
        
        mock_execute_query.side_effect = [None, updated_template]
        
        with patch.object(template_service, '_clear_template_cache') as mock_clear_cache:
            result = await template_service.update_template(1, update_data, 1)
        
        assert result is not None
        assert result['name'] == "Updated Template"
        assert result['description'] == "Updated description"
        mock_clear_cache.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_update_template_with_invalid_content(self, mock_execute_query, template_service):
        """Test template update with invalid content."""
        update_data = {
            "template_content": "<html><body>{{ invalid_syntax }"  # Invalid Jinja2
        }
        
        with pytest.raises(TemplateError):
            await template_service.update_template(1, update_data, 1)
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_delete_template_with_jobs(self, mock_execute_query, template_service):
        """Test template deletion when template has associated jobs."""
        mock_execute_query.side_effect = [5, None]  # 5 jobs found, then soft delete
        
        with patch.object(template_service, '_clear_template_cache') as mock_clear_cache:
            result = await template_service.delete_template(1, 1)
        
        assert result is True
        mock_clear_cache.assert_called_once_with(1)
        
        # Should perform soft delete
        delete_call = mock_execute_query.call_args_list[1]
        assert "is_active = FALSE" in delete_call[0][0]
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_delete_template_without_jobs(self, mock_execute_query, template_service):
        """Test template deletion when template has no associated jobs."""
        mock_execute_query.side_effect = [0, None]  # 0 jobs found, then hard delete
        
        with patch.object(template_service, '_clear_template_cache') as mock_clear_cache:
            result = await template_service.delete_template(1, 1)
        
        assert result is True
        mock_clear_cache.assert_called_once_with(1)
        
        # Should perform hard delete
        delete_call = mock_execute_query.call_args_list[1]
        assert "DELETE FROM" in delete_call[0][0]
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_list_templates(self, mock_execute_query, template_service, mock_template_response):
        """Test template listing."""
        mock_execute_query.side_effect = [1, [mock_template_response]]
        
        result = await template_service.list_templates(
            user_id=1,
            template_type=TemplateType.REPORT,
            is_active=True,
            page=1,
            page_size=20
        )
        
        assert result is not None
        assert result['total'] == 1
        assert result['page'] == 1
        assert result['page_size'] == 20
        assert result['total_pages'] == 1
        assert len(result['templates']) == 1
        assert result['templates'][0]['id'] == 1
        assert mock_execute_query.call_count == 2
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_list_templates_with_filters(self, mock_execute_query, template_service):
        """Test template listing with filters."""
        mock_execute_query.side_effect = [0, []]
        
        result = await template_service.list_templates(
            user_id=1,
            template_type=TemplateType.DASHBOARD,
            is_active=False,
            page=1,
            page_size=10
        )
        
        assert result is not None
        assert result['total'] == 0
        assert len(result['templates']) == 0
        
        # Check that filters were applied
        count_call = mock_execute_query.call_args_list[0]
        assert "created_by = $1" in count_call[0][0]
        assert "template_type = $2" in count_call[0][0]
        assert "is_active = $3" in count_call[0][0]
    
    @pytest.mark.asyncio
    async def test_preview_template(self, template_service, mock_template_response):
        """Test template preview generation."""
        with patch.object(template_service, 'get_template', return_value=mock_template_response):
            result = await template_service.preview_template(1, {"title": "Preview Title"})
        
        assert result is not None
        assert result['template_id'] == 1
        assert 'preview_html' in result
        assert 'preview_css' in result
        assert 'variables' in result
        assert 'Preview Title' in result['preview_html']
    
    @pytest.mark.asyncio
    async def test_preview_template_not_found(self, template_service):
        """Test template preview when template not found."""
        with patch.object(template_service, 'get_template', return_value=None):
            with pytest.raises(TemplateError):
                await template_service.preview_template(999)
    
    @pytest.mark.asyncio
    async def test_duplicate_template(self, template_service, mock_template_response):
        """Test template duplication."""
        new_name = "Duplicated Template"
        
        with patch.object(template_service, 'get_template', return_value=mock_template_response):
            with patch.object(template_service, 'create_template', return_value=mock_template_response) as mock_create:
                result = await template_service.duplicate_template(1, new_name, 1)
        
        assert result is not None
        mock_create.assert_called_once()
        
        # Check that create was called with correct data
        create_args = mock_create.call_args[0]
        assert create_args[0]['name'] == new_name
        assert create_args[0]['template_content'] == mock_template_response['template_content']
    
    @pytest.mark.asyncio
    async def test_duplicate_template_not_found(self, template_service):
        """Test template duplication when original not found."""
        with patch.object(template_service, 'get_template', return_value=None):
            with pytest.raises(TemplateError):
                await template_service.duplicate_template(999, "New Name", 1)
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_get_template_analytics(self, mock_execute_query, template_service):
        """Test template analytics retrieval."""
        mock_stats = {
            'total_jobs': 10,
            'successful_jobs': 8,
            'failed_jobs': 2,
            'avg_generation_time': 5000.0,
            'avg_file_size': 1024.0,
            'avg_page_count': 3.0
        }
        
        mock_format_stats = [
            {'output_format': 'pdf', 'count': 8},
            {'output_format': 'html', 'count': 2}
        ]
        
        mock_recent_jobs = 5
        
        mock_execute_query.side_effect = [mock_stats, mock_format_stats, mock_recent_jobs]
        
        result = await template_service.get_template_analytics(1)
        
        assert result is not None
        assert result['template_id'] == 1
        assert result['total_jobs'] == 10
        assert result['successful_jobs'] == 8
        assert result['failed_jobs'] == 2
        assert result['success_rate'] == 80.0
        assert result['usage_by_format'] == {'pdf': 8, 'html': 2}
        assert result['recent_jobs_30_days'] == 5
        assert mock_execute_query.call_count == 3
    
    @pytest.mark.asyncio
    async def test_export_template(self, template_service, mock_template_response):
        """Test template export."""
        with patch.object(template_service, 'get_template', return_value=mock_template_response):
            result = await template_service.export_template(1)
        
        assert result is not None
        assert result['name'] == mock_template_response['name']
        assert result['template_type'] == mock_template_response['template_type']
        assert result['template_content'] == mock_template_response['template_content']
        assert 'exported_at' in result
        assert 'version' in result
        
        # Internal fields should be removed
        assert 'id' not in result
        assert 'created_by' not in result
        assert 'created_at' not in result
    
    @pytest.mark.asyncio
    async def test_export_template_not_found(self, template_service):
        """Test template export when template not found."""
        with patch.object(template_service, 'get_template', return_value=None):
            with pytest.raises(TemplateError):
                await template_service.export_template(999)
    
    @pytest.mark.asyncio
    async def test_import_template(self, template_service, mock_template_response):
        """Test template import."""
        import_data = {
            'name': 'Imported Template',
            'template_type': 'report',
            'template_content': '<html><body>{{ content }}</body></html>',
            'css_content': 'body { font-family: Arial; }',
            'variables': {},
            'layout_config': {}
        }
        
        with patch.object(template_service, 'create_template', return_value=mock_template_response) as mock_create:
            result = await template_service.import_template(import_data, 1)
        
        assert result is not None
        mock_create.assert_called_once()
        
        # Check that create was called with correct data
        create_args = mock_create.call_args[0]
        assert create_args[0]['name'] == 'Imported Template'
        assert create_args[0]['template_type'] == 'report'
    
    @pytest.mark.asyncio
    async def test_import_template_missing_required_fields(self, template_service):
        """Test template import with missing required fields."""
        import_data = {
            'name': 'Incomplete Template'
            # Missing template_type and template_content
        }
        
        with pytest.raises(TemplateError):
            await template_service.import_template(import_data, 1)
    
    @pytest.mark.asyncio
    async def test_validate_template_content_valid(self, template_service):
        """Test template content validation with valid content."""
        valid_content = "<html><body><h1>{{ title }}</h1></body></html>"
        
        # Should not raise an exception
        await template_service._validate_template_content(valid_content)
    
    @pytest.mark.asyncio
    async def test_validate_template_content_invalid_syntax(self, template_service):
        """Test template content validation with invalid syntax."""
        invalid_content = "<html><body>{{ invalid_syntax }</body></html>"
        
        with pytest.raises(TemplateError):
            await template_service._validate_template_content(invalid_content)
    
    @pytest.mark.asyncio
    async def test_validate_template_content_dangerous_content(self, template_service):
        """Test template content validation with dangerous content."""
        dangerous_content = "<html><body>{{ config.items() }}</body></html>"
        
        with pytest.raises(TemplateError):
            await template_service._validate_template_content(dangerous_content)
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.get_redis_connection')
    async def test_clear_template_cache(self, mock_redis, template_service):
        """Test template cache clearing."""
        mock_redis_client = AsyncMock()
        mock_redis_client.delete.return_value = True
        mock_redis.return_value.__aenter__.return_value = mock_redis_client
        
        await template_service._clear_template_cache(1)
        
        mock_redis_client.delete.assert_called_once_with("template:1")
    
    @pytest.mark.asyncio
    async def test_get_template_types(self, template_service):
        """Test template types retrieval."""
        types = await template_service.get_template_types()
        
        assert types is not None
        assert len(types) == 5
        assert any(t['type'] == 'report' for t in types)
        assert any(t['type'] == 'dashboard' for t in types)
        assert any(t['type'] == 'chart' for t in types)
        assert any(t['type'] == 'table' for t in types)
        assert any(t['type'] == 'custom' for t in types)
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_get_default_templates(self, mock_execute_query, template_service, mock_template_response):
        """Test default templates retrieval."""
        mock_execute_query.return_value = [mock_template_response]
        
        templates = await template_service.get_default_templates()
        
        assert templates is not None
        assert len(templates) == 1
        assert templates[0]['id'] == 1
        mock_execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.template_service.execute_query')
    async def test_get_default_templates_with_type_filter(self, mock_execute_query, template_service):
        """Test default templates retrieval with type filter."""
        mock_execute_query.return_value = []
        
        templates = await template_service.get_default_templates(TemplateType.DASHBOARD)
        
        assert templates is not None
        assert len(templates) == 0
        mock_execute_query.assert_called_once()
        
        # Check that type filter was applied
        call_args = mock_execute_query.call_args[0]
        assert "template_type = $1" in call_args[0]
        assert TemplateType.DASHBOARD.value in call_args[1:]