"""
PDF generation service using WeasyPrint and Jinja2.
"""

import os
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import uuid
import base64
import httpx
from jinja2 import Environment, FileSystemLoader, DictLoader, select_autoescape
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import structlog
from PIL import Image
import io

from app.core.config import settings
from app.core.database import execute_query
from app.core.redis_client import get_redis_connection
from app.models.pdf_models import (
    JobStatus, TemplateType, OutputFormat, PDFJob, PDFTemplate,
    LayoutConfig, ChartConfig, TableConfig
)
from app.utils.metrics import PDF_GENERATION_COUNT, PDF_GENERATION_DURATION

logger = structlog.get_logger(__name__)


class PDFGenerationError(Exception):
    """PDF generation error."""
    pass


class TemplateError(Exception):
    """Template error."""
    pass


class PDFGenerator:
    """PDF generation service."""
    
    def __init__(self):
        self.template_env = None
        self.font_config = FontConfiguration()
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self._setup_template_environment()
    
    def _setup_template_environment(self):
        """Setup Jinja2 template environment."""
        # Template loaders
        file_loader = FileSystemLoader(settings.PDF_TEMPLATE_DIR)
        
        # Create environment with both loaders
        self.template_env = Environment(
            loader=file_loader,
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            enable_async=True
        )
        
        # Add custom filters
        self.template_env.filters['format_date'] = self._format_date
        self.template_env.filters['format_number'] = self._format_number
        self.template_env.filters['format_currency'] = self._format_currency
        self.template_env.filters['truncate_text'] = self._truncate_text
        
        # Add custom functions
        self.template_env.globals['now'] = self._get_current_time
        self.template_env.globals['format_chart'] = self._format_chart
        self.template_env.globals['format_table'] = self._format_table
        
        logger.info("Template environment setup complete")
    
    def _format_date(self, value, format_string='%Y-%m-%d %H:%M:%S'):
        """Format date filter."""
        if value is None:
            return ''
        return value.strftime(format_string)
    
    def _format_number(self, value, decimals=2):
        """Format number filter."""
        if value is None:
            return ''
        return f"{value:,.{decimals}f}"
    
    def _format_currency(self, value, currency='$'):
        """Format currency filter."""
        if value is None:
            return ''
        return f"{currency}{value:,.2f}"
    
    def _truncate_text(self, value, length=100, suffix='...'):
        """Truncate text filter."""
        if value is None:
            return ''
        if len(value) <= length:
            return value
        return value[:length] + suffix
    
    def _get_current_time(self):
        """Get current time function."""
        from datetime import datetime
        return datetime.now()
    
    def _format_chart(self, chart_config: ChartConfig) -> str:
        """Format chart for HTML embedding."""
        try:
            # Generate chart HTML
            chart_html = f"""
            <div class="chart-container" style="width: {chart_config.width}px; height: {chart_config.height}px;">
                <h3>{chart_config.title}</h3>
                <div id="chart-{chart_config.chart_id}" class="chart-content">
                    {chart_config.data.get('html', 'Chart placeholder')}
                </div>
            </div>
            """
            return chart_html
        except Exception as e:
            logger.error("Failed to format chart", chart_id=chart_config.chart_id, error=str(e))
            return f"<div class='chart-error'>Error loading chart: {chart_config.title}</div>"
    
    def _format_table(self, table_config: TableConfig) -> str:
        """Format table for HTML embedding."""
        try:
            # Generate table HTML
            table_html = f"<h3>{table_config.title}</h3><table class='data-table'>"
            
            # Headers
            table_html += "<thead><tr>"
            for header in table_config.headers:
                table_html += f"<th>{header}</th>"
            table_html += "</tr></thead>"
            
            # Data rows
            table_html += "<tbody>"
            for row in table_config.data:
                table_html += "<tr>"
                for cell in row:
                    table_html += f"<td>{cell}</td>"
                table_html += "</tr>"
            table_html += "</tbody></table>"
            
            return table_html
        except Exception as e:
            logger.error("Failed to format table", table_title=table_config.title, error=str(e))
            return f"<div class='table-error'>Error loading table: {table_config.title}</div>"
    
    async def generate_pdf(self, job_id: int, template_id: int, parameters: Dict[str, Any],
                          data_source: Dict[str, Any], output_format: OutputFormat = OutputFormat.PDF,
                          layout_config: Optional[LayoutConfig] = None) -> Dict[str, Any]:
        """Generate PDF from template and data."""
        start_time = time.time()
        job_key = f"job:{job_id}"
        
        try:
            # Mark job as processing
            await self._update_job_status(job_id, JobStatus.PROCESSING)
            
            # Track active job
            self.active_jobs[job_key] = {
                "job_id": job_id,
                "start_time": start_time,
                "status": JobStatus.PROCESSING
            }
            
            # Get template
            template = await self._get_template(template_id)
            if not template:
                raise PDFGenerationError(f"Template {template_id} not found")
            
            # Load template data
            template_data = await self._prepare_template_data(template, parameters, data_source)
            
            # Render template
            html_content = await self._render_template(template, template_data)
            
            # Generate output based on format
            if output_format == OutputFormat.HTML:
                result = await self._generate_html(job_id, html_content, template)
            elif output_format == OutputFormat.PNG:
                result = await self._generate_image(job_id, html_content, template, 'png')
            elif output_format == OutputFormat.JPG:
                result = await self._generate_image(job_id, html_content, template, 'jpg')
            else:
                result = await self._generate_pdf_file(job_id, html_content, template, layout_config)
            
            # Update job with results
            generation_time = int((time.time() - start_time) * 1000)
            await self._update_job_completion(job_id, result, generation_time)
            
            # Update metrics
            PDF_GENERATION_COUNT.labels(
                template_type=template.get('template_type', 'unknown'),
                status='success'
            ).inc()
            
            PDF_GENERATION_DURATION.labels(
                template_type=template.get('template_type', 'unknown')
            ).observe(time.time() - start_time)
            
            logger.info(
                "PDF generation completed",
                job_id=job_id,
                template_id=template_id,
                format=output_format,
                generation_time_ms=generation_time,
                file_size=result.get('file_size', 0)
            )
            
            return result
            
        except Exception as e:
            generation_time = int((time.time() - start_time) * 1000)
            await self._update_job_error(job_id, str(e), generation_time)
            
            # Update metrics
            PDF_GENERATION_COUNT.labels(
                template_type='unknown',
                status='error'
            ).inc()
            
            logger.error(
                "PDF generation failed",
                job_id=job_id,
                template_id=template_id,
                error=str(e),
                generation_time_ms=generation_time
            )
            
            raise PDFGenerationError(f"PDF generation failed: {str(e)}")
        
        finally:
            # Remove from active jobs
            if job_key in self.active_jobs:
                del self.active_jobs[job_key]
    
    async def _get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Get template from database."""
        try:
            template = await execute_query(
                "SELECT * FROM pdf_templates WHERE id = $1 AND is_active = TRUE",
                template_id,
                fetchrow=True
            )
            return dict(template) if template else None
        except Exception as e:
            logger.error("Failed to get template", template_id=template_id, error=str(e))
            return None
    
    async def _prepare_template_data(self, template: Dict[str, Any], parameters: Dict[str, Any],
                                   data_source: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for template rendering."""
        template_data = {
            'template': template,
            'parameters': parameters,
            'data_source': data_source,
            'generation_date': self._get_current_time().isoformat(),
            'generation_timestamp': int(time.time())
        }
        
        # Merge template variables
        template_variables = template.get('variables', {})
        for key, value in template_variables.items():
            if key not in template_data:
                template_data[key] = value
        
        # Process data source
        if data_source:
            # Handle charts
            if 'charts' in data_source:
                charts = []
                for chart_data in data_source['charts']:
                    chart_config = ChartConfig(**chart_data)
                    # Fetch chart image if needed
                    chart_image = await self._fetch_chart_image(chart_config)
                    chart_data['image'] = chart_image
                    charts.append(chart_data)
                template_data['charts'] = charts
            
            # Handle tables
            if 'tables' in data_source:
                tables = []
                for table_data in data_source['tables']:
                    table_config = TableConfig(**table_data)
                    tables.append(table_config.dict())
                template_data['tables'] = tables
            
            # Handle raw data
            if 'data' in data_source:
                template_data['data'] = data_source['data']
        
        return template_data
    
    async def _render_template(self, template: Dict[str, Any], template_data: Dict[str, Any]) -> str:
        """Render template with data."""
        try:
            # Create template from string
            template_obj = self.template_env.from_string(template['template_content'])
            
            # Render template
            html_content = await template_obj.render_async(**template_data)
            
            return html_content
            
        except Exception as e:
            logger.error("Template rendering failed", template_id=template['id'], error=str(e))
            raise TemplateError(f"Template rendering failed: {str(e)}")
    
    async def _generate_pdf_file(self, job_id: int, html_content: str, template: Dict[str, Any],
                               layout_config: Optional[LayoutConfig] = None) -> Dict[str, Any]:
        """Generate PDF file from HTML content."""
        try:
            # Prepare CSS
            css_content = template.get('css_content', '') or self._get_default_css()
            
            # Apply layout configuration
            if layout_config:
                css_content += self._generate_layout_css(layout_config)
            
            # Generate unique filename
            filename = f"pdf_export_{job_id}_{uuid.uuid4().hex[:8]}.pdf"
            file_path = os.path.join(settings.PDF_OUTPUT_DIR, filename)
            
            # Convert HTML to PDF
            html_doc = HTML(string=html_content, base_url=settings.WEASYPRINT_BASE_URL)
            css_doc = CSS(string=css_content) if css_content else None
            
            # Generate PDF
            if css_doc:
                pdf_bytes = html_doc.write_pdf(
                    stylesheets=[css_doc],
                    font_config=self.font_config,
                    presentational_hints=settings.WEASYPRINT_PRESENTATIONAL_HINTS,
                    optimize_images=settings.WEASYPRINT_OPTIMIZE_IMAGES
                )
            else:
                pdf_bytes = html_doc.write_pdf(
                    font_config=self.font_config,
                    presentational_hints=settings.WEASYPRINT_PRESENTATIONAL_HINTS,
                    optimize_images=settings.WEASYPRINT_OPTIMIZE_IMAGES
                )
            
            # Save to file
            with open(file_path, 'wb') as f:
                f.write(pdf_bytes)
            
            # Get file info
            file_size = len(pdf_bytes)
            page_count = self._count_pdf_pages(pdf_bytes)
            
            return {
                'file_path': file_path,
                'file_size': file_size,
                'page_count': page_count,
                'filename': filename
            }
            
        except Exception as e:
            logger.error("PDF file generation failed", job_id=job_id, error=str(e))
            raise PDFGenerationError(f"PDF file generation failed: {str(e)}")
    
    async def _generate_html(self, job_id: int, html_content: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """Generate HTML file from content."""
        try:
            # Generate unique filename
            filename = f"html_export_{job_id}_{uuid.uuid4().hex[:8]}.html"
            file_path = os.path.join(settings.PDF_OUTPUT_DIR, filename)
            
            # Add CSS styling
            css_content = template.get('css_content', '') or self._get_default_css()
            
            # Create complete HTML document
            complete_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    {css_content}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(complete_html)
            
            # Get file info
            file_size = len(complete_html.encode('utf-8'))
            
            return {
                'file_path': file_path,
                'file_size': file_size,
                'page_count': 1,
                'filename': filename
            }
            
        except Exception as e:
            logger.error("HTML file generation failed", job_id=job_id, error=str(e))
            raise PDFGenerationError(f"HTML file generation failed: {str(e)}")
    
    async def _generate_image(self, job_id: int, html_content: str, template: Dict[str, Any],
                            format: str) -> Dict[str, Any]:
        """Generate image file from HTML content."""
        try:
            # Generate unique filename
            filename = f"image_export_{job_id}_{uuid.uuid4().hex[:8]}.{format}"
            file_path = os.path.join(settings.PDF_OUTPUT_DIR, filename)
            
            # Prepare CSS
            css_content = template.get('css_content', '') or self._get_default_css()
            
            # Convert HTML to image via PDF
            html_doc = HTML(string=html_content, base_url=settings.WEASYPRINT_BASE_URL)
            css_doc = CSS(string=css_content) if css_content else None
            
            # Generate PDF first
            if css_doc:
                pdf_bytes = html_doc.write_pdf(
                    stylesheets=[css_doc],
                    font_config=self.font_config
                )
            else:
                pdf_bytes = html_doc.write_pdf(font_config=self.font_config)
            
            # Convert PDF to image using PIL
            from pdf2image import convert_from_bytes
            
            images = convert_from_bytes(pdf_bytes, dpi=settings.PDF_DPI)
            
            if images:
                # Save first page as image
                if format.lower() == 'jpg':
                    images[0].save(file_path, 'JPEG', quality=95)
                else:
                    images[0].save(file_path, 'PNG')
                
                # Get file info
                file_size = os.path.getsize(file_path)
                
                return {
                    'file_path': file_path,
                    'file_size': file_size,
                    'page_count': len(images),
                    'filename': filename
                }
            else:
                raise PDFGenerationError("No images generated from PDF")
                
        except Exception as e:
            logger.error("Image generation failed", job_id=job_id, format=format, error=str(e))
            raise PDFGenerationError(f"Image generation failed: {str(e)}")
    
    async def _fetch_chart_image(self, chart_config: ChartConfig) -> Optional[str]:
        """Fetch chart image from visualization service."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.CHART_SERVICE_URL}/api/v1/charts/render",
                    json={
                        "chart_id": chart_config.chart_id,
                        "chart_type": chart_config.chart_type,
                        "data": chart_config.data,
                        "options": chart_config.options,
                        "width": chart_config.width,
                        "height": chart_config.height,
                        "format": settings.CHART_FORMAT
                    },
                    timeout=settings.CHART_TIMEOUT_SECONDS
                )
                
                if response.status_code == 200:
                    image_data = response.content
                    # Convert to base64 for embedding
                    image_b64 = base64.b64encode(image_data).decode('utf-8')
                    return f"data:image/{settings.CHART_FORMAT};base64,{image_b64}"
                else:
                    logger.error(
                        "Chart service error",
                        chart_id=chart_config.chart_id,
                        status_code=response.status_code
                    )
                    return None
                    
        except Exception as e:
            logger.error("Failed to fetch chart image", chart_id=chart_config.chart_id, error=str(e))
            return None
    
    def _get_default_css(self) -> str:
        """Get default CSS for PDF generation."""
        return """
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 0;
        }
        
        .header {
            text-align: center;
            border-bottom: 2px solid #3498db;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .content {
            margin: 20px 0;
        }
        
        .footer {
            text-align: center;
            border-top: 1px solid #bdc3c7;
            padding-top: 20px;
            margin-top: 30px;
            font-size: 12px;
            color: #7f8c8d;
        }
        
        .chart-container {
            margin: 20px 0;
            text-align: center;
            page-break-inside: avoid;
        }
        
        .chart-container img {
            max-width: 100%;
            height: auto;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .data-table th,
        .data-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        .data-table th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        
        .data-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        @page {
            margin: 2cm;
            size: A4;
        }
        
        @media print {
            .page-break {
                page-break-before: always;
            }
        }
        """
    
    def _generate_layout_css(self, layout_config: LayoutConfig) -> str:
        """Generate CSS from layout configuration."""
        css = f"""
        @page {{
            size: {layout_config.page_size.upper()} {layout_config.orientation};
            margin-top: {layout_config.margin_top}mm;
            margin-bottom: {layout_config.margin_bottom}mm;
            margin-left: {layout_config.margin_left}mm;
            margin-right: {layout_config.margin_right}mm;
        }}
        """
        
        return css
    
    def _count_pdf_pages(self, pdf_bytes: bytes) -> int:
        """Count pages in PDF."""
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            return len(pdf_reader.pages)
        except Exception:
            # Fallback estimation
            return max(1, len(pdf_bytes) // 50000)
    
    async def _update_job_status(self, job_id: int, status: JobStatus):
        """Update job status."""
        try:
            await execute_query(
                "UPDATE pdf_export_jobs SET status = $1, started_at = CURRENT_TIMESTAMP WHERE id = $2",
                status.value,
                job_id
            )
        except Exception as e:
            logger.error("Failed to update job status", job_id=job_id, status=status, error=str(e))
    
    async def _update_job_completion(self, job_id: int, result: Dict[str, Any], generation_time: int):
        """Update job completion."""
        try:
            await execute_query(
                """
                UPDATE pdf_export_jobs 
                SET status = $1, file_path = $2, file_size = $3, page_count = $4, 
                    generation_time_ms = $5, completed_at = CURRENT_TIMESTAMP
                WHERE id = $6
                """,
                JobStatus.COMPLETED.value,
                result['file_path'],
                result['file_size'],
                result['page_count'],
                generation_time,
                job_id
            )
        except Exception as e:
            logger.error("Failed to update job completion", job_id=job_id, error=str(e))
    
    async def _update_job_error(self, job_id: int, error_message: str, generation_time: int):
        """Update job error."""
        try:
            await execute_query(
                """
                UPDATE pdf_export_jobs 
                SET status = $1, error_message = $2, generation_time_ms = $3, completed_at = CURRENT_TIMESTAMP
                WHERE id = $4
                """,
                JobStatus.FAILED.value,
                error_message,
                generation_time,
                job_id
            )
        except Exception as e:
            logger.error("Failed to update job error", job_id=job_id, error=str(e))
    
    async def cancel_job(self, job_id: int) -> bool:
        """Cancel running job."""
        job_key = f"job:{job_id}"
        
        if job_key in self.active_jobs:
            try:
                await execute_query(
                    "UPDATE pdf_export_jobs SET status = $1, completed_at = CURRENT_TIMESTAMP WHERE id = $2",
                    JobStatus.CANCELLED.value,
                    job_id
                )
                
                del self.active_jobs[job_key]
                logger.info("Job cancelled", job_id=job_id)
                return True
            except Exception as e:
                logger.error("Failed to cancel job", job_id=job_id, error=str(e))
                return False
        
        return False
    
    async def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get job status."""
        job_key = f"job:{job_id}"
        
        # Check if job is actively running
        if job_key in self.active_jobs:
            active_job = self.active_jobs[job_key]
            return {
                "job_id": job_id,
                "status": active_job["status"],
                "started_at": active_job["start_time"],
                "runtime_seconds": time.time() - active_job["start_time"]
            }
        
        # Get from database
        try:
            job = await execute_query(
                "SELECT * FROM pdf_export_jobs WHERE id = $1",
                job_id,
                fetchrow=True
            )
            return dict(job) if job else None
        except Exception as e:
            logger.error("Failed to get job status", job_id=job_id, error=str(e))
            return None
    
    async def cleanup_old_files(self, retention_days: int = None):
        """Clean up old generated files."""
        retention_days = retention_days or settings.STORAGE_RETENTION_DAYS
        
        try:
            # Get old jobs
            old_jobs = await execute_query(
                """
                SELECT id, file_path FROM pdf_export_jobs 
                WHERE completed_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                AND file_path IS NOT NULL
                """,
                retention_days,
                fetch=True
            )
            
            cleaned_count = 0
            for job in old_jobs:
                file_path = job['file_path']
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except Exception as e:
                        logger.error("Failed to delete file", file_path=file_path, error=str(e))
            
            # Update database
            await execute_query(
                """
                UPDATE pdf_export_jobs 
                SET file_path = NULL 
                WHERE completed_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """,
                retention_days
            )
            
            logger.info("File cleanup completed", files_cleaned=cleaned_count, retention_days=retention_days)
            
        except Exception as e:
            logger.error("File cleanup failed", error=str(e))


# Global PDF generator instance
pdf_generator = PDFGenerator()