"""
Template management service for PDF Export Service.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog
import uuid
from jinja2 import Environment, DictLoader, select_autoescape, TemplateSyntaxError

from app.core.config import settings
from app.core.database import execute_query
from app.core.redis_client import get_redis_connection
from app.models.pdf_models import TemplateType, PDFTemplate, LayoutConfig

logger = structlog.get_logger(__name__)


class TemplateError(Exception):
    """Template service error."""
    pass


class TemplateService:
    """Template management service."""
    
    def __init__(self):
        self.template_cache = {}
        self.template_env = Environment(
            loader=DictLoader({}),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    async def create_template(self, template_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create new template."""
        try:
            # Validate template content
            await self._validate_template_content(template_data['template_content'])
            
            # Insert template
            template_id = await execute_query(
                """
                INSERT INTO pdf_templates (name, template_type, description, template_content, 
                                         css_content, variables, layout_config, created_by, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                template_data['name'],
                template_data['template_type'],
                template_data.get('description'),
                template_data['template_content'],
                template_data.get('css_content'),
                template_data.get('variables', {}),
                template_data.get('layout_config', {}),
                user_id,
                True,
                fetchval=True
            )
            
            # Get created template
            template = await self.get_template(template_id)
            
            # Clear cache
            await self._clear_template_cache(template_id)
            
            logger.info("Template created", template_id=template_id, name=template_data['name'])
            return template
            
        except Exception as e:
            logger.error("Failed to create template", template_data=template_data, error=str(e))
            raise TemplateError(f"Failed to create template: {str(e)}")
    
    async def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Get template by ID."""
        try:
            # Check cache first
            cache_key = f"template:{template_id}"
            async with get_redis_connection() as redis_client:
                cached_template = await redis_client.get(cache_key)
                if cached_template:
                    import json
                    return json.loads(cached_template)
            
            # Get from database
            template = await execute_query(
                "SELECT * FROM pdf_templates WHERE id = $1",
                template_id,
                fetchrow=True
            )
            
            if template:
                template_dict = dict(template)
                
                # Cache template
                async with get_redis_connection() as redis_client:
                    await redis_client.setex(
                        cache_key,
                        settings.TEMPLATE_CACHE_TTL,
                        json.dumps(template_dict, default=str)
                    )
                
                return template_dict
            
            return None
            
        except Exception as e:
            logger.error("Failed to get template", template_id=template_id, error=str(e))
            return None
    
    async def update_template(self, template_id: int, template_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Update template."""
        try:
            # Validate template content if provided
            if 'template_content' in template_data:
                await self._validate_template_content(template_data['template_content'])
            
            # Build update query
            update_fields = []
            params = []
            param_count = 1
            
            for field, value in template_data.items():
                if field in ['name', 'description', 'template_content', 'css_content', 
                           'variables', 'layout_config', 'is_active']:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value)
                    param_count += 1
            
            if not update_fields:
                raise TemplateError("No valid fields to update")
            
            params.append(template_id)
            
            # Update template
            await execute_query(
                f"UPDATE pdf_templates SET {', '.join(update_fields)} WHERE id = ${param_count}",
                *params
            )
            
            # Clear cache
            await self._clear_template_cache(template_id)
            
            # Get updated template
            template = await self.get_template(template_id)
            
            logger.info("Template updated", template_id=template_id)
            return template
            
        except Exception as e:
            logger.error("Failed to update template", template_id=template_id, error=str(e))
            raise TemplateError(f"Failed to update template: {str(e)}")
    
    async def delete_template(self, template_id: int, user_id: int) -> bool:
        """Delete template (soft delete)."""
        try:
            # Check if template is used in any jobs
            job_count = await execute_query(
                "SELECT COUNT(*) FROM pdf_export_jobs WHERE template_id = $1",
                template_id,
                fetchval=True
            )
            
            if job_count > 0:
                # Soft delete - mark as inactive
                await execute_query(
                    "UPDATE pdf_templates SET is_active = FALSE WHERE id = $1",
                    template_id
                )
                logger.info("Template soft deleted", template_id=template_id, job_count=job_count)
            else:
                # Hard delete - remove from database
                await execute_query(
                    "DELETE FROM pdf_templates WHERE id = $1",
                    template_id
                )
                logger.info("Template hard deleted", template_id=template_id)
            
            # Clear cache
            await self._clear_template_cache(template_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to delete template", template_id=template_id, error=str(e))
            return False
    
    async def list_templates(self, user_id: int = None, template_type: TemplateType = None,
                           is_active: bool = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List templates with filtering."""
        try:
            # Build query conditions
            conditions = []
            params = []
            param_count = 1
            
            if user_id:
                conditions.append(f"created_by = ${param_count}")
                params.append(user_id)
                param_count += 1
            
            if template_type:
                conditions.append(f"template_type = ${param_count}")
                params.append(template_type.value)
                param_count += 1
            
            if is_active is not None:
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)
                param_count += 1
            
            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            
            # Get total count
            total_count = await execute_query(
                f"SELECT COUNT(*) FROM pdf_templates{where_clause}",
                *params,
                fetchval=True
            )
            
            # Get templates
            offset = (page - 1) * page_size
            templates = await execute_query(
                f"""
                SELECT * FROM pdf_templates{where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
                """,
                *params,
                page_size,
                offset,
                fetch=True
            )
            
            return {
                "templates": [dict(template) for template in templates],
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error("Failed to list templates", error=str(e))
            raise TemplateError(f"Failed to list templates: {str(e)}")
    
    async def preview_template(self, template_id: int, preview_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Preview template with sample data."""
        try:
            # Get template
            template = await self.get_template(template_id)
            if not template:
                raise TemplateError(f"Template {template_id} not found")
            
            # Prepare preview data
            preview_data = preview_data or {}
            template_data = {
                'title': 'Sample Report',
                'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'content': 'This is a sample content for template preview.',
                'charts': [
                    {
                        'title': 'Sample Chart',
                        'chart_type': 'bar',
                        'data': {'labels': ['A', 'B', 'C'], 'values': [10, 20, 30]},
                        'full_width': False
                    }
                ],
                'tables': [
                    {
                        'title': 'Sample Table',
                        'headers': ['Column 1', 'Column 2', 'Column 3'],
                        'data': [
                            ['Row 1, Col 1', 'Row 1, Col 2', 'Row 1, Col 3'],
                            ['Row 2, Col 1', 'Row 2, Col 2', 'Row 2, Col 3']
                        ]
                    }
                ],
                **preview_data
            }
            
            # Render template
            template_obj = self.template_env.from_string(template['template_content'])
            html_content = template_obj.render(**template_data)
            
            return {
                'template_id': template_id,
                'preview_html': html_content,
                'preview_css': template.get('css_content', ''),
                'variables': template.get('variables', {}),
                'layout_config': template.get('layout_config', {})
            }
            
        except Exception as e:
            logger.error("Failed to preview template", template_id=template_id, error=str(e))
            raise TemplateError(f"Failed to preview template: {str(e)}")
    
    async def duplicate_template(self, template_id: int, new_name: str, user_id: int) -> Dict[str, Any]:
        """Duplicate existing template."""
        try:
            # Get original template
            original_template = await self.get_template(template_id)
            if not original_template:
                raise TemplateError(f"Template {template_id} not found")
            
            # Create new template data
            new_template_data = {
                'name': new_name,
                'template_type': original_template['template_type'],
                'description': f"Copy of {original_template['name']}",
                'template_content': original_template['template_content'],
                'css_content': original_template['css_content'],
                'variables': original_template['variables'],
                'layout_config': original_template['layout_config']
            }
            
            # Create new template
            new_template = await self.create_template(new_template_data, user_id)
            
            logger.info("Template duplicated", original_id=template_id, new_id=new_template['id'])
            return new_template
            
        except Exception as e:
            logger.error("Failed to duplicate template", template_id=template_id, error=str(e))
            raise TemplateError(f"Failed to duplicate template: {str(e)}")
    
    async def get_template_analytics(self, template_id: int) -> Dict[str, Any]:
        """Get template usage analytics."""
        try:
            # Get usage statistics
            stats = await execute_query(
                """
                SELECT 
                    COUNT(*) as total_jobs,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_jobs,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
                    AVG(generation_time_ms) as avg_generation_time,
                    AVG(file_size) as avg_file_size,
                    AVG(page_count) as avg_page_count
                FROM pdf_export_jobs 
                WHERE template_id = $1
                """,
                template_id,
                fetchrow=True
            )
            
            # Get usage by format
            format_stats = await execute_query(
                """
                SELECT output_format, COUNT(*) as count
                FROM pdf_export_jobs 
                WHERE template_id = $1
                GROUP BY output_format
                """,
                template_id,
                fetch=True
            )
            
            # Get recent usage
            recent_jobs = await execute_query(
                """
                SELECT COUNT(*) as count
                FROM pdf_export_jobs 
                WHERE template_id = $1 
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                """,
                template_id,
                fetchval=True
            )
            
            return {
                'template_id': template_id,
                'total_jobs': stats['total_jobs'] or 0,
                'successful_jobs': stats['successful_jobs'] or 0,
                'failed_jobs': stats['failed_jobs'] or 0,
                'success_rate': (stats['successful_jobs'] / max(stats['total_jobs'], 1)) * 100 if stats['total_jobs'] else 0,
                'avg_generation_time_ms': float(stats['avg_generation_time']) if stats['avg_generation_time'] else 0,
                'avg_file_size_mb': float(stats['avg_file_size']) / (1024 * 1024) if stats['avg_file_size'] else 0,
                'avg_page_count': float(stats['avg_page_count']) if stats['avg_page_count'] else 0,
                'usage_by_format': {row['output_format']: row['count'] for row in format_stats},
                'recent_jobs_30_days': recent_jobs or 0
            }
            
        except Exception as e:
            logger.error("Failed to get template analytics", template_id=template_id, error=str(e))
            return {}
    
    async def export_template(self, template_id: int) -> Dict[str, Any]:
        """Export template as JSON."""
        try:
            template = await self.get_template(template_id)
            if not template:
                raise TemplateError(f"Template {template_id} not found")
            
            # Remove internal fields
            export_data = {
                'name': template['name'],
                'template_type': template['template_type'],
                'description': template['description'],
                'template_content': template['template_content'],
                'css_content': template['css_content'],
                'variables': template['variables'],
                'layout_config': template['layout_config'],
                'exported_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            return export_data
            
        except Exception as e:
            logger.error("Failed to export template", template_id=template_id, error=str(e))
            raise TemplateError(f"Failed to export template: {str(e)}")
    
    async def import_template(self, template_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Import template from JSON."""
        try:
            # Validate import data
            required_fields = ['name', 'template_type', 'template_content']
            for field in required_fields:
                if field not in template_data:
                    raise TemplateError(f"Missing required field: {field}")
            
            # Create template
            import_data = {
                'name': template_data['name'],
                'template_type': template_data['template_type'],
                'description': template_data.get('description', 'Imported template'),
                'template_content': template_data['template_content'],
                'css_content': template_data.get('css_content'),
                'variables': template_data.get('variables', {}),
                'layout_config': template_data.get('layout_config', {})
            }
            
            template = await self.create_template(import_data, user_id)
            
            logger.info("Template imported", template_id=template['id'], name=template_data['name'])
            return template
            
        except Exception as e:
            logger.error("Failed to import template", error=str(e))
            raise TemplateError(f"Failed to import template: {str(e)}")
    
    async def _validate_template_content(self, template_content: str):
        """Validate template content."""
        try:
            # Check for Jinja2 syntax errors
            self.template_env.from_string(template_content)
            
            # Check for potentially dangerous content
            dangerous_patterns = [
                '{{config',
                '{{lipsum',
                '{{joiner',
                '{{cycler',
                '{{namespace',
                '__import__',
                'eval(',
                'exec(',
                'open(',
                'file(',
                'input(',
                'raw_input('
            ]
            
            for pattern in dangerous_patterns:
                if pattern in template_content.lower():
                    raise TemplateError(f"Template contains potentially dangerous content: {pattern}")
            
        except TemplateSyntaxError as e:
            raise TemplateError(f"Template syntax error: {str(e)}")
        except Exception as e:
            raise TemplateError(f"Template validation failed: {str(e)}")
    
    async def _clear_template_cache(self, template_id: int):
        """Clear template cache."""
        try:
            cache_key = f"template:{template_id}"
            async with get_redis_connection() as redis_client:
                await redis_client.delete(cache_key)
        except Exception as e:
            logger.error("Failed to clear template cache", template_id=template_id, error=str(e))
    
    async def get_template_types(self) -> List[Dict[str, Any]]:
        """Get available template types."""
        return [
            {
                'type': TemplateType.REPORT.value,
                'name': 'Report Template',
                'description': 'Standard report template with header, content, and footer'
            },
            {
                'type': TemplateType.DASHBOARD.value,
                'name': 'Dashboard Template',
                'description': 'Template for dashboard exports with multiple charts'
            },
            {
                'type': TemplateType.CHART.value,
                'name': 'Chart Template',
                'description': 'Template optimized for single chart exports'
            },
            {
                'type': TemplateType.TABLE.value,
                'name': 'Table Template',
                'description': 'Template for tabular data exports'
            },
            {
                'type': TemplateType.CUSTOM.value,
                'name': 'Custom Template',
                'description': 'Custom template with flexible layout'
            }
        ]
    
    async def get_default_templates(self, template_type: TemplateType = None) -> List[Dict[str, Any]]:
        """Get default templates."""
        try:
            conditions = ["is_default = TRUE"]
            params = []
            
            if template_type:
                conditions.append("template_type = $1")
                params.append(template_type.value)
            
            templates = await execute_query(
                f"SELECT * FROM pdf_templates WHERE {' AND '.join(conditions)} ORDER BY name",
                *params,
                fetch=True
            )
            
            return [dict(template) for template in templates]
            
        except Exception as e:
            logger.error("Failed to get default templates", error=str(e))
            return []


# Global template service instance
template_service = TemplateService()