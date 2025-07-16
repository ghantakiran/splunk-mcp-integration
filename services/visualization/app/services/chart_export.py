"""
Advanced Chart Export Service

This service handles comprehensive chart export functionality including:
- Multiple export formats with quality settings
- Export configuration and optimization
- Batch export capabilities
- Export template management
- Format-specific enhancements
"""
import io
import time
import uuid
import zipfile
import tarfile
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.io as pio
from PIL import Image
import base64

from ..models.chart import (
    ExportFormat, ExportQuality, ExportOrientation, ExportTemplate,
    ExportConfig, ExportResult, BatchExportRequest, BatchExportResult,
    ChartConfig
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class ChartExportService:
    """Advanced chart export service with comprehensive features"""
    
    def __init__(self):
        self.quality_settings = self._initialize_quality_settings()
        self.template_configs = self._initialize_template_configs()
        self.export_cache = {}
        
    def _initialize_quality_settings(self) -> Dict[str, Dict[str, Any]]:
        """Initialize quality settings for different export formats"""
        return {
            ExportQuality.LOW: {
                "scale": 1.0,
                "jpeg_quality": 60,
                "png_compression": 9,
                "webp_quality": 60,
                "pdf_dpi": 150
            },
            ExportQuality.MEDIUM: {
                "scale": 1.5,
                "jpeg_quality": 80,
                "png_compression": 6,
                "webp_quality": 80,
                "pdf_dpi": 200
            },
            ExportQuality.HIGH: {
                "scale": 2.0,
                "jpeg_quality": 90,
                "png_compression": 3,
                "webp_quality": 90,
                "pdf_dpi": 300
            },
            ExportQuality.ULTRA: {
                "scale": 3.0,
                "jpeg_quality": 95,
                "png_compression": 1,
                "webp_quality": 95,
                "pdf_dpi": 600
            }
        }
    
    def _initialize_template_configs(self) -> Dict[str, Dict[str, Any]]:
        """Initialize export template configurations"""
        return {
            ExportTemplate.PRESENTATION: {
                "width": 1920,
                "height": 1080,
                "dpi": 300,
                "font_scale": 1.2,
                "margin_top": 80,
                "margin_bottom": 80,
                "margin_left": 80,
                "margin_right": 80,
                "background_color": "#FFFFFF",
                "include_title": True,
                "include_legend": True
            },
            ExportTemplate.PRINT: {
                "width": 2480,
                "height": 3508,  # A4 at 300 DPI
                "dpi": 300,
                "font_scale": 1.0,
                "margin_top": 100,
                "margin_bottom": 100,
                "margin_left": 100,
                "margin_right": 100,
                "background_color": "#FFFFFF",
                "include_title": True,
                "include_legend": True
            },
            ExportTemplate.WEB: {
                "width": 800,
                "height": 600,
                "dpi": 96,
                "font_scale": 1.0,
                "margin_top": 50,
                "margin_bottom": 50,
                "margin_left": 50,
                "margin_right": 50,
                "background_color": "#FFFFFF",
                "include_title": True,
                "include_legend": True
            },
            ExportTemplate.SOCIAL: {
                "width": 1200,
                "height": 628,  # Social media optimal
                "dpi": 150,
                "font_scale": 1.1,
                "margin_top": 40,
                "margin_bottom": 40,
                "margin_left": 40,
                "margin_right": 40,
                "background_color": "#FFFFFF",
                "include_title": True,
                "include_legend": False
            },
            ExportTemplate.REPORT: {
                "width": 1200,
                "height": 800,
                "dpi": 300,
                "font_scale": 1.0,
                "margin_top": 60,
                "margin_bottom": 60,
                "margin_left": 60,
                "margin_right": 60,
                "background_color": "#FFFFFF",
                "include_title": True,
                "include_legend": True
            }
        }
    
    def export_chart(
        self,
        fig: go.Figure,
        config: ExportConfig,
        chart_id: str,
        filename: Optional[str] = None
    ) -> ExportResult:
        """
        Export chart with advanced configuration options
        
        Args:
            fig: Plotly figure
            config: Export configuration
            chart_id: Chart identifier
            filename: Optional filename override
            
        Returns:
            ExportResult with export details
        """
        start_time = time.time()
        export_id = str(uuid.uuid4())
        
        try:
            logger.info("Starting chart export",
                       export_id=export_id,
                       chart_id=chart_id,
                       format=config.format,
                       quality=config.quality,
                       template=config.template)
            
            # Apply template configuration
            config = self._apply_template_config(config)
            
            # Prepare figure for export
            fig = self._prepare_figure_for_export(fig, config)
            
            # Export based on format
            file_bytes, content_type = self._export_by_format(fig, config)
            
            # Generate filename if not provided
            if not filename:
                filename = f"chart_{chart_id}_{export_id[:8]}.{config.format}"
            
            # Create metadata
            metadata = self._create_export_metadata(fig, config, chart_id)
            
            export_time = time.time() - start_time
            
            result = ExportResult(
                export_id=export_id,
                chart_id=chart_id,
                format=config.format,
                filename=filename,
                file_size=len(file_bytes),
                content_type=content_type,
                export_time=export_time,
                config=config,
                metadata=metadata
            )
            
            logger.info("Chart export completed",
                       export_id=export_id,
                       chart_id=chart_id,
                       format=config.format,
                       file_size=len(file_bytes),
                       export_time=export_time)
            
            return result
            
        except Exception as e:
            logger.error("Chart export failed",
                        export_id=export_id,
                        chart_id=chart_id,
                        error=str(e),
                        exc_info=True)
            raise ValueError(f"Export failed: {str(e)}")
    
    def _apply_template_config(self, config: ExportConfig) -> ExportConfig:
        """Apply template configuration to export config"""
        if config.template == ExportTemplate.CUSTOM:
            return config
        
        template_config = self.template_configs.get(config.template, {})
        
        # Create a copy of the config with template overrides
        config_dict = config.dict()
        
        # Apply template settings if not explicitly set
        for key, value in template_config.items():
            if key in config_dict and config_dict[key] is None:
                config_dict[key] = value
            elif key not in config_dict:
                config_dict[key] = value
        
        return ExportConfig(**config_dict)
    
    def _prepare_figure_for_export(self, fig: go.Figure, config: ExportConfig) -> go.Figure:
        """Prepare figure for export with configuration"""
        # Create a copy of the figure
        export_fig = go.Figure(fig)
        
        # Apply export-specific modifications
        layout_updates = {}
        
        # Set dimensions
        if config.width and config.height:
            layout_updates['width'] = config.width
            layout_updates['height'] = config.height
        
        # Set background color
        if not config.transparent_background:
            layout_updates['paper_bgcolor'] = config.background_color
            layout_updates['plot_bgcolor'] = config.background_color
        else:
            layout_updates['paper_bgcolor'] = 'rgba(0,0,0,0)'
            layout_updates['plot_bgcolor'] = 'rgba(0,0,0,0)'
        
        # Set margins
        layout_updates['margin'] = dict(
            l=config.margin_left,
            r=config.margin_right,
            t=config.margin_top,
            b=config.margin_bottom
        )
        
        # Apply font scaling
        if config.font_scale != 1.0:
            current_font = export_fig.layout.font or {}
            current_size = current_font.get('size', 12)
            layout_updates['font'] = dict(
                size=int(current_size * config.font_scale)
            )
        
        # Hide/show title and legend based on config
        if not config.include_title:
            layout_updates['title'] = None
        
        if not config.include_legend:
            layout_updates['showlegend'] = False
        
        # Apply all layout updates
        export_fig.update_layout(**layout_updates)
        
        return export_fig
    
    def _export_by_format(self, fig: go.Figure, config: ExportConfig) -> Tuple[bytes, str]:
        """Export figure in specified format"""
        quality_settings = self.quality_settings[config.quality]
        
        if config.format == ExportFormat.PNG:
            return self._export_png(fig, config, quality_settings)
        
        elif config.format == ExportFormat.JPEG:
            return self._export_jpeg(fig, config, quality_settings)
        
        elif config.format == ExportFormat.WEBP:
            return self._export_webp(fig, config, quality_settings)
        
        elif config.format == ExportFormat.PDF:
            return self._export_pdf(fig, config, quality_settings)
        
        elif config.format == ExportFormat.SVG:
            return self._export_svg(fig, config, quality_settings)
        
        elif config.format == ExportFormat.HTML:
            return self._export_html(fig, config, quality_settings)
        
        elif config.format == ExportFormat.JSON:
            return self._export_json(fig, config, quality_settings)
        
        else:
            raise ValueError(f"Unsupported export format: {config.format}")
    
    def _export_png(self, fig: go.Figure, config: ExportConfig, quality_settings: Dict) -> Tuple[bytes, str]:
        """Export as PNG with optimization"""
        scale = quality_settings['scale']
        
        # Create image bytes
        img_bytes = fig.to_image(
            format="png",
            width=config.width,
            height=config.height,
            scale=scale
        )
        
        # Optimize PNG if requested
        if config.optimize:
            img = Image.open(io.BytesIO(img_bytes))
            optimized_buffer = io.BytesIO()
            img.save(
                optimized_buffer,
                format='PNG',
                optimize=True,
                compress_level=quality_settings['png_compression']
            )
            img_bytes = optimized_buffer.getvalue()
        
        return img_bytes, "image/png"
    
    def _export_jpeg(self, fig: go.Figure, config: ExportConfig, quality_settings: Dict) -> Tuple[bytes, str]:
        """Export as JPEG with quality optimization"""
        scale = quality_settings['scale']
        
        # Create image bytes
        img_bytes = fig.to_image(
            format="png",  # Start with PNG for transparency handling
            width=config.width,
            height=config.height,
            scale=scale
        )
        
        # Convert to JPEG
        img = Image.open(io.BytesIO(img_bytes))
        
        # Handle transparency by adding white background
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, config.background_color)
            background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            img = background
        
        jpeg_buffer = io.BytesIO()
        img.save(
            jpeg_buffer,
            format='JPEG',
            quality=quality_settings['jpeg_quality'],
            optimize=config.optimize,
            progressive=config.progressive
        )
        
        return jpeg_buffer.getvalue(), "image/jpeg"
    
    def _export_webp(self, fig: go.Figure, config: ExportConfig, quality_settings: Dict) -> Tuple[bytes, str]:
        """Export as WebP with advanced compression"""
        scale = quality_settings['scale']
        
        # Create image bytes
        img_bytes = fig.to_image(
            format="png",
            width=config.width,
            height=config.height,
            scale=scale
        )
        
        # Convert to WebP
        img = Image.open(io.BytesIO(img_bytes))
        webp_buffer = io.BytesIO()
        img.save(
            webp_buffer,
            format='WEBP',
            quality=quality_settings['webp_quality'],
            method=6 if config.optimize else 4,  # Higher compression method
            lossless=False
        )
        
        return webp_buffer.getvalue(), "image/webp"
    
    def _export_pdf(self, fig: go.Figure, config: ExportConfig, quality_settings: Dict) -> Tuple[bytes, str]:
        """Export as PDF with high quality"""
        pdf_bytes = fig.to_image(
            format="pdf",
            width=config.width,
            height=config.height
        )
        
        return pdf_bytes, "application/pdf"
    
    def _export_svg(self, fig: go.Figure, config: ExportConfig, quality_settings: Dict) -> Tuple[bytes, str]:
        """Export as SVG with embedded fonts"""
        svg_str = fig.to_image(
            format="svg",
            width=config.width,
            height=config.height
        )
        
        # Embed fonts if requested
        if config.embed_fonts:
            # SVG font embedding would be implemented here
            pass
        
        return svg_str, "image/svg+xml"
    
    def _export_html(self, fig: go.Figure, config: ExportConfig, quality_settings: Dict) -> Tuple[bytes, str]:
        """Export as interactive HTML"""
        html_config = {
            'include_plotlyjs': True,
            'config': {
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                'responsive': True
            }
        }
        
        html_str = fig.to_html(**html_config)
        
        # Add custom CSS for better presentation
        if config.background_color != "#FFFFFF":
            html_str = html_str.replace(
                '<body>',
                f'<body style="background-color: {config.background_color};">'
            )
        
        return html_str.encode('utf-8'), "text/html"
    
    def _export_json(self, fig: go.Figure, config: ExportConfig, quality_settings: Dict) -> Tuple[bytes, str]:
        """Export as JSON with metadata"""
        json_data = {
            'figure': fig.to_dict(),
            'config': config.dict(),
            'metadata': {
                'export_timestamp': datetime.utcnow().isoformat(),
                'plotly_version': pio.__version__,
                'format': config.format
            }
        }
        
        json_str = json.dumps(json_data, indent=2 if config.optimize else None)
        
        return json_str.encode('utf-8'), "application/json"
    
    def _create_export_metadata(self, fig: go.Figure, config: ExportConfig, chart_id: str) -> Dict[str, Any]:
        """Create comprehensive export metadata"""
        return {
            'chart_id': chart_id,
            'export_timestamp': datetime.utcnow().isoformat(),
            'format': config.format,
            'quality': config.quality,
            'template': config.template,
            'dimensions': {
                'width': config.width,
                'height': config.height,
                'dpi': config.dpi
            },
            'figure_info': {
                'trace_count': len(fig.data),
                'trace_types': [trace.type for trace in fig.data],
                'has_title': bool(fig.layout.title),
                'has_legend': fig.layout.showlegend
            },
            'optimization': {
                'optimize': config.optimize,
                'compression_level': config.compression_level,
                'font_scale': config.font_scale
            }
        }
    
    def batch_export(self, request: BatchExportRequest) -> BatchExportResult:
        """Export multiple charts in batch"""
        start_time = time.time()
        batch_id = str(uuid.uuid4())
        
        logger.info("Starting batch export",
                   batch_id=batch_id,
                   chart_count=len(request.charts),
                   format=request.format)
        
        results = []
        successful_exports = 0
        failed_exports = 0
        
        # Process each chart
        for chart_id in request.charts:
            try:
                # This would integrate with the chart storage/retrieval system
                # For now, we'll simulate the export process
                fig = self._get_chart_figure(chart_id)  # Placeholder
                
                result = self.export_chart(fig, request.config, chart_id)
                results.append(result)
                successful_exports += 1
                
            except Exception as e:
                logger.error("Chart export failed in batch",
                            batch_id=batch_id,
                            chart_id=chart_id,
                            error=str(e))
                failed_exports += 1
        
        # Create archive
        archive_filename = request.archive_name or f"charts_export_{batch_id[:8]}.{request.archive_format}"
        archive_size = self._create_archive(results, request.archive_format, archive_filename)
        
        processing_time = time.time() - start_time
        
        batch_result = BatchExportResult(
            batch_id=batch_id,
            total_charts=len(request.charts),
            successful_exports=successful_exports,
            failed_exports=failed_exports,
            results=results,
            archive_size=archive_size,
            archive_filename=archive_filename,
            processing_time=processing_time
        )
        
        logger.info("Batch export completed",
                   batch_id=batch_id,
                   successful=successful_exports,
                   failed=failed_exports,
                   processing_time=processing_time)
        
        return batch_result
    
    def _get_chart_figure(self, chart_id: str) -> go.Figure:
        """Get chart figure by ID (placeholder)"""
        # This would be implemented to retrieve the chart from storage
        # For now, return a simple placeholder figure
        return go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[4, 5, 6])])
    
    def _create_archive(self, results: List[ExportResult], format: str, filename: str) -> int:
        """Create archive file with exported charts"""
        # This would create the actual archive file
        # For now, return a placeholder size
        return sum(result.file_size for result in results)
    
    def get_export_formats(self) -> List[Dict[str, Any]]:
        """Get available export formats with capabilities"""
        return [
            {
                "format": ExportFormat.PNG,
                "name": "PNG",
                "description": "High-quality raster image format with transparency support",
                "supports_transparency": True,
                "supports_animation": False,
                "best_for": ["web", "presentations", "high-quality prints"]
            },
            {
                "format": ExportFormat.JPEG,
                "name": "JPEG",
                "description": "Compressed raster image format for photographs",
                "supports_transparency": False,
                "supports_animation": False,
                "best_for": ["web", "email", "social media"]
            },
            {
                "format": ExportFormat.WEBP,
                "name": "WebP",
                "description": "Modern image format with superior compression",
                "supports_transparency": True,
                "supports_animation": True,
                "best_for": ["web", "mobile", "performance"]
            },
            {
                "format": ExportFormat.PDF,
                "name": "PDF",
                "description": "Vector-based document format for printing",
                "supports_transparency": False,
                "supports_animation": False,
                "best_for": ["printing", "documents", "reports"]
            },
            {
                "format": ExportFormat.SVG,
                "name": "SVG",
                "description": "Scalable vector graphics format",
                "supports_transparency": True,
                "supports_animation": True,
                "best_for": ["web", "scalable graphics", "illustrations"]
            },
            {
                "format": ExportFormat.HTML,
                "name": "HTML",
                "description": "Interactive web format with full functionality",
                "supports_transparency": False,
                "supports_animation": True,
                "best_for": ["web", "interactive", "embedding"]
            },
            {
                "format": ExportFormat.JSON,
                "name": "JSON",
                "description": "Data format for programmatic access",
                "supports_transparency": False,
                "supports_animation": False,
                "best_for": ["api", "data exchange", "programmatic"]
            }
        ]
    
    def get_quality_options(self) -> List[Dict[str, Any]]:
        """Get available quality options"""
        return [
            {
                "quality": ExportQuality.LOW,
                "name": "Low",
                "description": "Smallest file size, fastest export",
                "scale": 1.0,
                "dpi": 150
            },
            {
                "quality": ExportQuality.MEDIUM,
                "name": "Medium",
                "description": "Balanced quality and file size",
                "scale": 1.5,
                "dpi": 200
            },
            {
                "quality": ExportQuality.HIGH,
                "name": "High",
                "description": "High quality for most uses",
                "scale": 2.0,
                "dpi": 300
            },
            {
                "quality": ExportQuality.ULTRA,
                "name": "Ultra",
                "description": "Maximum quality for professional use",
                "scale": 3.0,
                "dpi": 600
            }
        ]
    
    def get_template_options(self) -> List[Dict[str, Any]]:
        """Get available template options"""
        return [
            {
                "template": ExportTemplate.WEB,
                "name": "Web",
                "description": "Optimized for web display",
                "dimensions": "800x600",
                "dpi": 96
            },
            {
                "template": ExportTemplate.PRINT,
                "name": "Print",
                "description": "High-resolution for printing",
                "dimensions": "2480x3508",
                "dpi": 300
            },
            {
                "template": ExportTemplate.PRESENTATION,
                "name": "Presentation",
                "description": "Optimized for presentations",
                "dimensions": "1920x1080",
                "dpi": 300
            },
            {
                "template": ExportTemplate.SOCIAL,
                "name": "Social Media",
                "description": "Optimized for social sharing",
                "dimensions": "1200x628",
                "dpi": 150
            },
            {
                "template": ExportTemplate.REPORT,
                "name": "Report",
                "description": "Optimized for reports",
                "dimensions": "1200x800",
                "dpi": 300
            }
        ]