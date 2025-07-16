"""
Chart Customization Service

This service handles advanced chart customization including:
- Theme management and application
- Font and color customization
- Axis, legend, and grid configuration
- Custom styling and CSS/JavaScript injection
- Chart templates and presets
"""
import json
import time
from typing import Dict, Any, List, Optional, Union
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from ..models.chart import (
    ChartConfig, ChartCustomization, ChartTemplate, ChartTheme, 
    FontFamily, ColorScheme, ChartFont, ChartAxis, ChartLegend, 
    ChartGrid, ChartMargin, ChartTitle, ChartAnnotation, LegendPosition,
    AxisType, GridStyle
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class ChartCustomizationService:
    """Service for handling chart customization and styling"""
    
    def __init__(self):
        self.templates = {}
        self.theme_configs = self._initialize_theme_configs()
        self.color_schemes = self._initialize_color_schemes()
        self.default_templates = self._create_default_templates()
        
    def _initialize_theme_configs(self) -> Dict[str, Dict[str, Any]]:
        """Initialize theme configurations"""
        return {
            ChartTheme.DEFAULT: {
                "template": "plotly_white",
                "background_color": "#FFFFFF",
                "plot_background_color": "#FFFFFF",
                "grid_color": "#E0E0E0",
                "text_color": "#000000"
            },
            ChartTheme.DARK: {
                "template": "plotly_dark",
                "background_color": "#2F2F2F",
                "plot_background_color": "#3F3F3F",
                "grid_color": "#4F4F4F",
                "text_color": "#FFFFFF"
            },
            ChartTheme.MINIMAL: {
                "template": "simple_white",
                "background_color": "#FFFFFF",
                "plot_background_color": "#FFFFFF",
                "grid_color": "#F0F0F0",
                "text_color": "#333333"
            },
            ChartTheme.PRESENTATION: {
                "template": "presentation",
                "background_color": "#FFFFFF",
                "plot_background_color": "#FAFAFA",
                "grid_color": "#DDDDDD",
                "text_color": "#2E2E2E"
            },
            ChartTheme.SEABORN: {
                "template": "seaborn",
                "background_color": "#F8F9FA",
                "plot_background_color": "#FFFFFF",
                "grid_color": "#D9D9D9",
                "text_color": "#333333"
            }
        }
    
    def _initialize_color_schemes(self) -> Dict[str, List[str]]:
        """Initialize color scheme palettes"""
        return {
            ColorScheme.DEFAULT: px.colors.qualitative.Plotly,
            ColorScheme.VIRIDIS: px.colors.sequential.Viridis,
            ColorScheme.PLASMA: px.colors.sequential.Plasma,
            ColorScheme.INFERNO: px.colors.sequential.Inferno,
            ColorScheme.MAGMA: px.colors.sequential.Magma,
            ColorScheme.BLUES: px.colors.sequential.Blues,
            ColorScheme.REDS: px.colors.sequential.Reds,
            ColorScheme.GREENS: px.colors.sequential.Greens,
            ColorScheme.CATEGORICAL: px.colors.qualitative.Set1,
            ColorScheme.PASTEL: px.colors.qualitative.Pastel1,
            ColorScheme.DARK: px.colors.qualitative.Dark2,
            ColorScheme.COLORBLIND: px.colors.qualitative.Safe
        }
    
    def _create_default_templates(self) -> Dict[str, ChartTemplate]:
        """Create default chart templates"""
        templates = {}
        
        # Corporate template
        corporate_customization = ChartCustomization(
            theme=ChartTheme.DEFAULT,
            font_family=FontFamily.ARIAL,
            font_size=12,
            background_color="#FFFFFF",
            plot_background_color="#FAFAFA",
            title=ChartTitle(
                font=ChartFont(size=16, bold=True, color="#1F4E79"),
                position="center",
                pad=30
            ),
            legend=ChartLegend(
                position=LegendPosition.RIGHT,
                font=ChartFont(size=11),
                background_color="rgba(255,255,255,0.9)"
            ),
            grid=ChartGrid(
                show_x=True,
                show_y=True,
                color="#E5E5E5",
                style=GridStyle.DOT
            )
        )
        templates["corporate"] = ChartTemplate(
            name="Corporate",
            description="Professional corporate styling with clean design",
            customization=corporate_customization,
            tags=["professional", "corporate", "clean"]
        )
        
        # Dark theme template
        dark_customization = ChartCustomization(
            theme=ChartTheme.DARK,
            font_family=FontFamily.ROBOTO,
            font_size=12,
            background_color="#2F2F2F",
            plot_background_color="#3F3F3F",
            title=ChartTitle(
                font=ChartFont(size=18, bold=True, color="#FFFFFF"),
                position="center",
                pad=25
            ),
            legend=ChartLegend(
                position=LegendPosition.TOP,
                font=ChartFont(size=11, color="#FFFFFF"),
                background_color="rgba(0,0,0,0.3)"
            ),
            grid=ChartGrid(
                show_x=True,
                show_y=True,
                color="#555555",
                style=GridStyle.SOLID
            )
        )
        templates["dark"] = ChartTemplate(
            name="Dark",
            description="Dark theme with high contrast for presentations",
            customization=dark_customization,
            tags=["dark", "presentation", "contrast"]
        )
        
        # Minimal template
        minimal_customization = ChartCustomization(
            theme=ChartTheme.MINIMAL,
            font_family=FontFamily.HELVETICA,
            font_size=11,
            background_color="#FFFFFF",
            plot_background_color="#FFFFFF",
            title=ChartTitle(
                font=ChartFont(size=14, bold=False, color="#333333"),
                position="left",
                pad=20
            ),
            legend=ChartLegend(
                position=LegendPosition.BOTTOM,
                font=ChartFont(size=10),
                background_color="rgba(255,255,255,0)"
            ),
            grid=ChartGrid(
                show_x=False,
                show_y=True,
                color="#F0F0F0",
                style=GridStyle.SOLID
            )
        )
        templates["minimal"] = ChartTemplate(
            name="Minimal",
            description="Clean minimal design with focus on data",
            customization=minimal_customization,
            tags=["minimal", "clean", "simple"]
        )
        
        return templates
    
    def apply_customization(
        self,
        fig: go.Figure,
        config: ChartConfig,
        customization: Optional[ChartCustomization] = None
    ) -> go.Figure:
        """
        Apply comprehensive customization to a chart
        
        Args:
            fig: Plotly figure to customize
            config: Chart configuration
            customization: Customization settings
            
        Returns:
            Customized Plotly figure
        """
        if not customization:
            customization = config.customization
            
        if not customization:
            return fig
            
        logger.info("Applying chart customization",
                   theme=customization.theme,
                   font_family=customization.font_family)
        
        try:
            # Apply theme
            fig = self._apply_theme(fig, customization.theme)
            
            # Apply font styling
            fig = self._apply_font_styling(fig, customization)
            
            # Apply colors and backgrounds
            fig = self._apply_color_styling(fig, customization)
            
            # Apply title customization
            if customization.title:
                fig = self._apply_title_styling(fig, customization.title)
            
            # Apply axis customization
            if customization.x_axis:
                fig = self._apply_axis_styling(fig, customization.x_axis, "x")
            if customization.y_axis:
                fig = self._apply_axis_styling(fig, customization.y_axis, "y")
            
            # Apply legend customization
            if customization.legend:
                fig = self._apply_legend_styling(fig, customization.legend)
            
            # Apply grid customization
            if customization.grid:
                fig = self._apply_grid_styling(fig, customization.grid)
            
            # Apply margin customization
            if customization.margin:
                fig = self._apply_margin_styling(fig, customization.margin)
            
            # Apply annotations
            if customization.annotations:
                fig = self._apply_annotations(fig, customization.annotations)
            
            # Apply toolbar and tips configuration
            fig = self._apply_interaction_config(fig, customization)
            
            logger.info("Chart customization applied successfully")
            return fig
            
        except Exception as e:
            logger.error("Error applying chart customization",
                        error=str(e),
                        exc_info=True)
            return fig
    
    def _apply_theme(self, fig: go.Figure, theme: ChartTheme) -> go.Figure:
        """Apply theme to the figure"""
        theme_config = self.theme_configs.get(theme, self.theme_configs[ChartTheme.DEFAULT])
        
        if theme_config["template"] != "none":
            fig.update_layout(template=theme_config["template"])
        
        return fig
    
    def _apply_font_styling(self, fig: go.Figure, customization: ChartCustomization) -> go.Figure:
        """Apply font styling to the figure"""
        font_config = {
            "family": customization.font_family,
            "size": customization.font_size
        }
        
        fig.update_layout(font=font_config)
        return fig
    
    def _apply_color_styling(self, fig: go.Figure, customization: ChartCustomization) -> go.Figure:
        """Apply color styling to the figure"""
        fig.update_layout(
            paper_bgcolor=customization.background_color,
            plot_bgcolor=customization.plot_background_color
        )
        return fig
    
    def _apply_title_styling(self, fig: go.Figure, title_config: ChartTitle) -> go.Figure:
        """Apply title styling to the figure"""
        if not title_config.show:
            fig.update_layout(title=None)
            return fig
        
        title_font = {}
        if title_config.font:
            title_font = {
                "family": title_config.font.family,
                "size": title_config.font.size,
                "color": title_config.font.color
            }
        
        fig.update_layout(
            title={
                "text": title_config.text,
                "font": title_font,
                "x": 0.5 if title_config.position == "center" else (0.0 if title_config.position == "left" else 1.0),
                "xanchor": title_config.position,
                "pad": {"t": title_config.pad}
            }
        )
        return fig
    
    def _apply_axis_styling(self, fig: go.Figure, axis_config: ChartAxis, axis: str) -> go.Figure:
        """Apply axis styling to the figure"""
        axis_updates = {}
        
        if axis_config.title:
            title_font = {}
            if axis_config.title_font:
                title_font = {
                    "family": axis_config.title_font.family,
                    "size": axis_config.title_font.size,
                    "color": axis_config.title_font.color
                }
            axis_updates["title"] = {
                "text": axis_config.title,
                "font": title_font
            }
        
        if axis_config.label_font:
            axis_updates["tickfont"] = {
                "family": axis_config.label_font.family,
                "size": axis_config.label_font.size,
                "color": axis_config.label_font.color
            }
        
        # Axis line and ticks
        axis_updates.update({
            "showline": axis_config.show_line,
            "linecolor": axis_config.line_color,
            "linewidth": axis_config.line_width,
            "showticklabels": axis_config.show_labels,
            "ticks": "outside" if axis_config.show_ticks else "",
            "tickcolor": axis_config.tick_color,
            "ticklen": axis_config.tick_length,
            "tickangle": axis_config.tick_angle
        })
        
        # Axis type
        if axis_config.type != AxisType.AUTO:
            axis_updates["type"] = axis_config.type
        
        # Axis range
        if axis_config.range_min is not None and axis_config.range_max is not None:
            axis_updates["range"] = [axis_config.range_min, axis_config.range_max]
        
        # Tick format
        if axis_config.tick_format:
            axis_updates["tickformat"] = axis_config.tick_format
        
        if axis == "x":
            fig.update_xaxes(**axis_updates)
        else:
            fig.update_yaxes(**axis_updates)
        
        return fig
    
    def _apply_legend_styling(self, fig: go.Figure, legend_config: ChartLegend) -> go.Figure:
        """Apply legend styling to the figure"""
        if not legend_config.show:
            fig.update_layout(showlegend=False)
            return fig
        
        legend_updates = {
            "orientation": legend_config.orientation,
            "bgcolor": legend_config.background_color,
            "bordercolor": legend_config.border_color,
            "borderwidth": legend_config.border_width,
            "itemsizing": "constant",
            "itemclick": "toggle",
            "itemdoubleclick": "toggleothers"
        }
        
        if legend_config.font:
            legend_updates["font"] = {
                "family": legend_config.font.family,
                "size": legend_config.font.size,
                "color": legend_config.font.color
            }
        
        # Position legend
        position_map = {
            LegendPosition.RIGHT: {"x": 1.02, "y": 0.5, "xanchor": "left", "yanchor": "middle"},
            LegendPosition.LEFT: {"x": -0.02, "y": 0.5, "xanchor": "right", "yanchor": "middle"},
            LegendPosition.TOP: {"x": 0.5, "y": 1.02, "xanchor": "center", "yanchor": "bottom"},
            LegendPosition.BOTTOM: {"x": 0.5, "y": -0.02, "xanchor": "center", "yanchor": "top"},
            LegendPosition.TOP_RIGHT: {"x": 1, "y": 1, "xanchor": "right", "yanchor": "top"},
            LegendPosition.TOP_LEFT: {"x": 0, "y": 1, "xanchor": "left", "yanchor": "top"},
            LegendPosition.BOTTOM_RIGHT: {"x": 1, "y": 0, "xanchor": "right", "yanchor": "bottom"},
            LegendPosition.BOTTOM_LEFT: {"x": 0, "y": 0, "xanchor": "left", "yanchor": "bottom"}
        }
        
        if legend_config.position in position_map:
            legend_updates.update(position_map[legend_config.position])
        
        fig.update_layout(legend=legend_updates)
        return fig
    
    def _apply_grid_styling(self, fig: go.Figure, grid_config: ChartGrid) -> go.Figure:
        """Apply grid styling to the figure"""
        grid_updates = {
            "showgrid": grid_config.show_x,
            "gridcolor": grid_config.color,
            "gridwidth": grid_config.width
        }
        
        if grid_config.style != GridStyle.SOLID:
            dash_map = {
                GridStyle.DASH: "dash",
                GridStyle.DOT: "dot",
                GridStyle.DASHDOT: "dashdot"
            }
            if grid_config.style in dash_map:
                grid_updates["griddash"] = dash_map[grid_config.style]
        
        fig.update_xaxes(**grid_updates)
        
        grid_updates["showgrid"] = grid_config.show_y
        fig.update_yaxes(**grid_updates)
        
        return fig
    
    def _apply_margin_styling(self, fig: go.Figure, margin_config: ChartMargin) -> go.Figure:
        """Apply margin styling to the figure"""
        fig.update_layout(
            margin=dict(
                l=margin_config.left,
                r=margin_config.right,
                t=margin_config.top,
                b=margin_config.bottom
            )
        )
        return fig
    
    def _apply_annotations(self, fig: go.Figure, annotations: List[ChartAnnotation]) -> go.Figure:
        """Apply annotations to the figure"""
        plotly_annotations = []
        
        for annotation in annotations:
            annotation_config = {
                "text": annotation.text,
                "x": annotation.x,
                "y": annotation.y,
                "bgcolor": annotation.background_color,
                "bordercolor": annotation.border_color,
                "borderwidth": annotation.border_width,
                "showarrow": annotation.arrow_show
            }
            
            if annotation.font:
                annotation_config["font"] = {
                    "family": annotation.font.family,
                    "size": annotation.font.size,
                    "color": annotation.font.color
                }
            
            if annotation.arrow_show:
                annotation_config["arrowcolor"] = annotation.arrow_color
            
            plotly_annotations.append(annotation_config)
        
        fig.update_layout(annotations=plotly_annotations)
        return fig
    
    def _apply_interaction_config(self, fig: go.Figure, customization: ChartCustomization) -> go.Figure:
        """Apply interaction configuration"""
        config = {}
        
        if not customization.show_toolbar:
            config["displayModeBar"] = False
        
        if not customization.show_tips:
            fig.update_layout(hovermode=False)
        
        # Note: Custom CSS/JS would need to be handled at the application level
        return fig
    
    def get_template(self, template_name: str) -> Optional[ChartTemplate]:
        """Get a chart template by name"""
        return self.default_templates.get(template_name) or self.templates.get(template_name)
    
    def list_templates(self) -> List[ChartTemplate]:
        """List all available templates"""
        all_templates = {**self.default_templates, **self.templates}
        return list(all_templates.values())
    
    def create_template(self, template: ChartTemplate) -> ChartTemplate:
        """Create a new chart template"""
        self.templates[template.name] = template
        logger.info("Created new chart template", template_name=template.name)
        return template
    
    def get_color_palette(self, scheme: ColorScheme, count: int) -> List[str]:
        """Get color palette for the specified scheme"""
        colors = self.color_schemes.get(scheme, self.color_schemes[ColorScheme.DEFAULT])
        
        # Repeat colors if we need more than available
        while len(colors) < count:
            colors.extend(colors)
        
        return colors[:count]
    
    def get_theme_config(self, theme: ChartTheme) -> Dict[str, Any]:
        """Get theme configuration"""
        return self.theme_configs.get(theme, self.theme_configs[ChartTheme.DEFAULT])
    
    def validate_customization(self, customization: ChartCustomization) -> List[str]:
        """Validate customization configuration and return warnings"""
        warnings = []
        
        # Validate color formats
        if customization.background_color and not self._is_valid_color(customization.background_color):
            warnings.append("Invalid background color format")
        
        if customization.plot_background_color and not self._is_valid_color(customization.plot_background_color):
            warnings.append("Invalid plot background color format")
        
        # Validate font sizes
        if customization.font_size < 8 or customization.font_size > 72:
            warnings.append("Font size should be between 8 and 72")
        
        # Validate annotations
        for i, annotation in enumerate(customization.annotations):
            if not self._is_valid_color(annotation.background_color):
                warnings.append(f"Invalid annotation {i+1} background color")
            if not self._is_valid_color(annotation.border_color):
                warnings.append(f"Invalid annotation {i+1} border color")
        
        return warnings
    
    def _is_valid_color(self, color: str) -> bool:
        """Validate color format (hex, rgb, rgba, named)"""
        import re
        
        # Hex colors
        if re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', color):
            return True
        
        # RGB/RGBA colors
        if re.match(r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*[\d.]+\s*)?\)$', color):
            return True
        
        # Named colors (basic validation)
        named_colors = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'black', 'white', 'gray', 'grey']
        if color.lower() in named_colors:
            return True
        
        return False