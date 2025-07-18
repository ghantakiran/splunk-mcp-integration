#!/usr/bin/env python3
"""
HTML Report Generator Service.

This service handles the generation of interactive HTML reports with embedded charts,
tables, and visualizations with advanced interactive features.
"""

import asyncio
import base64
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiofiles
import aiohttp
from jinja2 import Environment, FileSystemLoader, Template as Jinja2Template

from app.core.config import settings
from app.models.html_models import (
    Chart,
    ChartType,
    ColorScheme,
    InteractiveFeature,
    JobStatus,
    Layout,
    LayoutSection,
    OutputFormat,
    ReportConfig,
    Table,
    Template
)

logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """HTML report generator with interactive features."""
    
    def __init__(self):
        """Initialize the HTML report generator."""
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(settings.HTML_TEMPLATE_DIR),
            autoescape=True
        )
        
        # Chart type mappings for different JS libraries
        self.plotly_chart_types = {
            ChartType.BAR: "bar",
            ChartType.COLUMN: "bar",
            ChartType.LINE: "scatter",
            ChartType.PIE: "pie",
            ChartType.AREA: "scatter",
            ChartType.SCATTER: "scatter",
            ChartType.HEATMAP: "heatmap",
            ChartType.TREEMAP: "treemap",
            ChartType.SUNBURST: "sunburst",
            ChartType.HISTOGRAM: "histogram"
        }
        
        self.color_schemes = {
            ColorScheme.BLUE: ["#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c"],
            ColorScheme.RED: ["#d62728", "#ff9896", "#ff7f0e", "#ffbb78", "#2ca02c"],
            ColorScheme.GREEN: ["#2ca02c", "#98df8a", "#d62728", "#ff9896", "#ff7f0e"],
            ColorScheme.ORANGE: ["#ff7f0e", "#ffbb78", "#2ca02c", "#98df8a", "#d62728"],
            ColorScheme.PURPLE: ["#9467bd", "#c5b0d5", "#8c564b", "#c49c94", "#e377c2"],
            ColorScheme.TEAL: ["#17becf", "#9edae5", "#bcbd22", "#dbdb8d", "#7f7f7f"],
            ColorScheme.RAINBOW: ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2"],
            ColorScheme.MONOCHROME: ["#000000", "#404040", "#808080", "#c0c0c0", "#ffffff"]
        }
    
    async def generate_report(
        self,
        job_id: int,
        user_id: int,
        report_config: ReportConfig,
        data_source: Dict[str, Any],
        output_format: OutputFormat = OutputFormat.HTML
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate an HTML report from configuration and data.
        
        Args:
            job_id: Job identifier
            user_id: User identifier
            report_config: Report configuration
            data_source: Data source configuration
            output_format: Output format
            
        Returns:
            Tuple of (success, file_path, error_message)
        """
        start_time = time.time()
        
        try:
            # Update job status to processing
            await self._update_job_status(job_id, JobStatus.PROCESSING, started_at=datetime.utcnow())
            
            logger.info(f"Starting HTML report generation for job {job_id}")
            
            # Fetch data from data source
            data = await self._fetch_data(data_source)
            
            # Generate HTML content
            html_content = await self._create_html_report(report_config, data, job_id)
            
            # Generate file path
            file_name = f"report_{job_id}_{int(time.time())}.{output_format.value}"
            file_path = os.path.join(settings.HTML_OUTPUT_DIR, file_name)
            
            # Save report
            if output_format == OutputFormat.HTML:
                await self._save_html_file(html_content, file_path)
            else:
                # Convert to other formats
                file_path = await self._convert_html(html_content, file_path, output_format)
            
            # Calculate metadata
            file_size = os.path.getsize(file_path)
            chart_count = len(report_config.charts)
            table_count = len(report_config.tables)
            section_count = len(report_config.layout.sections)
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Update job with success
            await self._update_job_completion(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                file_path=file_path,
                file_size=file_size,
                chart_count=chart_count,
                table_count=table_count,
                section_count=section_count,
                generation_time_ms=generation_time_ms
            )
            
            logger.info(f"HTML report generation completed for job {job_id}")
            return True, file_path, None
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"HTML report generation failed for job {job_id}: {error_message}")
            
            # Update job with failure
            await self._update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=error_message,
                completed_at=datetime.utcnow()
            )
            
            return False, None, error_message
    
    async def _create_html_report(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        job_id: int
    ) -> str:
        """Create HTML report from configuration and data."""
        # Load template
        template = await self._load_template(config.template)
        
        # Prepare charts
        charts_html = []
        for chart in config.charts:
            chart_html = await self._create_chart_html(chart, data)
            charts_html.append(chart_html)
        
        # Prepare tables
        tables_html = []
        for table in config.tables:
            table_html = await self._create_table_html(table)
            tables_html.append(table_html)
        
        # Create layout sections
        sections_html = []
        for section in config.layout.sections:
            section_html = await self._create_section_html(section, charts_html, tables_html)
            sections_html.append(section_html)
        
        # Prepare template context
        context = {
            "metadata": config.metadata,
            "sections": sections_html,
            "layout": config.layout,
            "enable_print_css": config.enable_print_css,
            "enable_dark_mode": config.enable_dark_mode,
            "custom_branding": config.custom_branding,
            "charts": config.charts,
            "tables": config.tables,
            "generated_at": datetime.utcnow().isoformat(),
            "job_id": job_id,
            "cdn_base_url": settings.CDN_BASE_URL if settings.USE_CDN else "/static",
            "enable_plotly": settings.ENABLE_PLOTLY,
            "enable_d3": settings.ENABLE_D3,
            "enable_chartjs": settings.ENABLE_CHARTJS,
            "enable_datatables": settings.ENABLE_DATATABLES,
            "enable_bootstrap": settings.ENABLE_BOOTSTRAP
        }
        
        # Render template
        html_content = template.render(**context)
        
        return html_content
    
    async def _create_chart_html(self, chart: Chart, data: Dict[str, Any]) -> str:
        """Create HTML for a chart with interactive features."""
        # Get chart data
        chart_data = chart.data
        
        # Apply color scheme
        colors = self.color_schemes.get(chart.config.color_scheme, self.color_schemes[ColorScheme.BLUE])
        
        # Create Plotly configuration
        plotly_data = []
        for i, dataset in enumerate(chart_data.datasets):
            trace = {
                "x": chart_data.labels,
                "y": dataset["data"],
                "name": dataset["label"],
                "type": self.plotly_chart_types.get(chart.config.chart_type, "scatter"),
                "marker": {"color": colors[i % len(colors)]}
            }
            
            # Add chart-specific configurations
            if chart.config.chart_type == ChartType.LINE:
                trace["mode"] = "lines+markers"
            elif chart.config.chart_type == ChartType.AREA:
                trace["fill"] = "tonexty" if i > 0 else "tozeroy"
            elif chart.config.chart_type == ChartType.COLUMN:
                trace["orientation"] = "v"
            elif chart.config.chart_type == ChartType.BAR:
                trace["orientation"] = "h"
            
            plotly_data.append(trace)
        
        # Create layout configuration
        layout = {
            "title": chart.config.title,
            "width": chart.config.width,
            "height": chart.config.height,
            "showlegend": chart.config.show_legend,
            "responsive": chart.config.responsive,
            "autosize": chart.config.responsive
        }
        
        # Add grid configuration
        if chart.config.show_grid:
            layout["xaxis"] = {"showgrid": True}
            layout["yaxis"] = {"showgrid": True}
        
        # Add interactive features
        config_plotly = {
            "displayModeBar": True,
            "responsive": chart.config.responsive
        }
        
        if InteractiveFeature.ZOOM in chart.config.interactive_features:
            config_plotly["scrollZoom"] = True
        
        if InteractiveFeature.PAN in chart.config.interactive_features:
            config_plotly["dragmode"] = "pan"
        
        # Generate chart HTML
        chart_html = f"""
        <div id="chart-{chart.id}" class="chart-container">
            <script>
                (function() {{
                    var data = {json.dumps(plotly_data)};
                    var layout = {json.dumps(layout)};
                    var config = {json.dumps(config_plotly)};
                    
                    Plotly.newPlot('chart-{chart.id}', data, layout, config);
                    
                    // Add interactive features
                    {await self._generate_chart_interactions(chart)}
                }})();
            </script>
        </div>
        """
        
        return chart_html
    
    async def _create_table_html(self, table: Table) -> str:
        """Create HTML for an interactive table."""
        # Prepare table columns
        columns = []
        for col in table.config.columns:
            column_def = {
                "data": col.name,
                "title": col.label,
                "type": col.data_type,
                "orderable": col.sortable,
                "searchable": col.filterable
            }
            
            if col.width:
                column_def["width"] = f"{col.width}px"
            
            columns.append(column_def)
        
        # DataTables configuration
        datatable_config = {
            "paging": table.config.pagination,
            "pageLength": table.config.page_size,
            "searching": table.config.search,
            "ordering": table.config.sorting,
            "responsive": table.config.responsive,
            "stripe": table.config.striped,
            "columns": columns
        }
        
        # Add export buttons
        if table.config.export_buttons:
            datatable_config["dom"] = "Bfrtip"
            datatable_config["buttons"] = [
                {"extend": btn, "className": "btn btn-sm"} 
                for btn in table.config.export_buttons
            ]
        
        # Generate table HTML
        table_html = f"""
        <div id="table-{table.id}" class="table-container">
            <table id="datatable-{table.id}" class="table table-striped table-bordered">
                <thead>
                    <tr>
                        {' '.join([f'<th>{col.label}</th>' for col in table.config.columns])}
                    </tr>
                </thead>
                <tbody>
                    {await self._generate_table_rows(table)}
                </tbody>
            </table>
            <script>
                (function() {{
                    var config = {json.dumps(datatable_config)};
                    $('#datatable-{table.id}').DataTable(config);
                }})();
            </script>
        </div>
        """
        
        return table_html
    
    async def _create_section_html(
        self,
        section: LayoutSection,
        charts_html: List[str],
        tables_html: List[str]
    ) -> str:
        """Create HTML for a layout section."""
        # Get content based on type
        content = ""
        if section.content_type == "chart" and section.content_id:
            # Find chart HTML by ID
            for i, chart_html in enumerate(charts_html):
                if f"chart-{section.content_id}" in chart_html:
                    content = chart_html
                    break
        elif section.content_type == "table" and section.content_id:
            # Find table HTML by ID
            for i, table_html in enumerate(tables_html):
                if f"table-{section.content_id}" in table_html:
                    content = table_html
                    break
        elif section.content_type == "html" and section.html_content:
            content = section.html_content
        elif section.content_type == "text" and section.html_content:
            content = f"<p>{section.html_content}</p>"
        
        # Build CSS classes
        css_classes = ["col-md-" + str(section.width)] + section.css_classes
        
        # Build inline styles
        inline_styles = []
        if section.height:
            inline_styles.append(f"height: {section.height}px")
        
        for prop, value in section.custom_styles.items():
            inline_styles.append(f"{prop}: {value}")
        
        style_attr = f'style="{"; ".join(inline_styles)}"' if inline_styles else ""
        
        # Generate section HTML
        section_html = f"""
        <div id="section-{section.id}" class="{' '.join(css_classes)}" {style_attr}>
            {f'<h3>{section.title}</h3>' if section.title else ''}
            {content}
        </div>
        """
        
        return section_html
    
    async def _generate_chart_interactions(self, chart: Chart) -> str:
        """Generate JavaScript for chart interactions."""
        interactions = []
        
        # Add click interactions
        if InteractiveFeature.CLICK in chart.config.interactive_features:
            interactions.append(f"""
                document.getElementById('chart-{chart.id}').on('plotly_click', function(data) {{
                    console.log('Chart clicked:', data);
                    // Add custom click handling here
                }});
            """)
        
        # Add hover interactions
        if InteractiveFeature.HOVER in chart.config.interactive_features:
            interactions.append(f"""
                document.getElementById('chart-{chart.id}').on('plotly_hover', function(data) {{
                    console.log('Chart hovered:', data);
                    // Add custom hover handling here
                }});
            """)
        
        # Add brush/selection interactions
        if InteractiveFeature.BRUSH in chart.config.interactive_features:
            interactions.append(f"""
                document.getElementById('chart-{chart.id}').on('plotly_selected', function(data) {{
                    console.log('Chart selection:', data);
                    // Add custom selection handling here
                }});
            """)
        
        return "\n".join(interactions)
    
    async def _generate_table_rows(self, table: Table) -> str:
        """Generate HTML table rows from data."""
        rows = []
        for row_data in table.data:
            cells = []
            for col in table.config.columns:
                cell_value = row_data.get(col.name, "")
                cells.append(f"<td>{cell_value}</td>")
            rows.append(f"<tr>{''.join(cells)}</tr>")
        
        return "\n".join(rows)
    
    async def _load_template(self, template_type: Template) -> Jinja2Template:
        """Load Jinja2 template by type."""
        template_file = f"{template_type.value}.html"
        
        try:
            return self.jinja_env.get_template(template_file)
        except Exception:
            # Fall back to default template
            logger.warning(f"Template {template_file} not found, using default")
            return self.jinja_env.get_template("modern.html")
    
    async def _fetch_data(self, data_source: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from data source."""
        if "static_source" in data_source:
            return data_source["static_source"].get("data", {})
        elif "query_source" in data_source:
            # In a real implementation, this would execute the query
            return {"query_result": "mock_data"}
        elif "file_source" in data_source:
            # In a real implementation, this would load from file
            return {"file_data": "mock_data"}
        else:
            return {}
    
    async def _save_html_file(self, html_content: str, file_path: str) -> None:
        """Save HTML content to file."""
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(html_content)
    
    async def _convert_html(self, html_content: str, output_path: str, output_format: OutputFormat) -> str:
        """Convert HTML to other formats."""
        if output_format == OutputFormat.PDF:
            # In a real implementation, this would use a library like WeasyPrint or Playwright
            logger.warning("PDF conversion not implemented - saving as HTML")
            html_path = output_path.replace('.pdf', '.html')
            await self._save_html_file(html_content, html_path)
            return html_path
        elif output_format == OutputFormat.PNG:
            # In a real implementation, this would use a screenshot library
            logger.warning("PNG conversion not implemented - saving as HTML")
            html_path = output_path.replace('.png', '.html')
            await self._save_html_file(html_content, html_path)
            return html_path
        else:
            await self._save_html_file(html_content, output_path)
            return output_path
    
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
        chart_count: int,
        table_count: int,
        section_count: int,
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
                    chart_count,
                    table_count,
                    section_count,
                    generation_time_ms
                )
            logger.info(f"Job {job_id} completed with {chart_count} charts, {table_count} tables, {section_count} sections")
        except Exception as e:
            logger.error(f"Failed to update job completion: {e}")


# Global generator instance
html_report_generator = HTMLReportGenerator()


# Export commonly used functions
__all__ = ["html_report_generator", "HTMLReportGenerator"]