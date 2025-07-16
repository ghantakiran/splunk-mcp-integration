"""
Chart Generation Service

This service handles the actual rendering of charts using Plotly.
It takes chart configurations and data to generate interactive charts
with proper styling, legends, and export capabilities.
"""
import io
import base64
import json
import time
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

from ..models.chart import (
    ChartType, ChartConfig, ChartData, ChartResponse, 
    ColorScheme, ExportFormat, DataType
)
from ..core.logging import get_logger, log_chart_generation
from ..core.config import settings

logger = get_logger(__name__)


class ChartGenerator:
    """Generates interactive charts using Plotly"""
    
    def __init__(self):
        # Configure Plotly defaults
        pio.templates.default = "plotly_white"
        
        # Color schemes mapping
        self.color_schemes = {
            ColorScheme.DEFAULT: px.colors.qualitative.Plotly,
            ColorScheme.VIRIDIS: px.colors.sequential.Viridis,
            ColorScheme.PLASMA: px.colors.sequential.Plasma,
            ColorScheme.INFERNO: px.colors.sequential.Inferno,
            ColorScheme.MAGMA: px.colors.sequential.Magma,
            ColorScheme.BLUES: px.colors.sequential.Blues,
            ColorScheme.REDS: px.colors.sequential.Reds,
            ColorScheme.GREENS: px.colors.sequential.Greens,
            ColorScheme.CATEGORICAL: px.colors.qualitative.Set1
        }
    
    def generate_chart(
        self, 
        data: ChartData, 
        config: ChartConfig,
        chart_id: Optional[str] = None
    ) -> ChartResponse:
        """
        Generate a chart based on data and configuration
        
        Args:
            data: Chart data
            config: Chart configuration
            chart_id: Optional chart identifier
            
        Returns:
            ChartResponse with generated chart information
        """
        start_time = time.time()
        
        try:
            logger.info("Starting chart generation",
                       chart_type=config.chart_type,
                       data_rows=data.total_rows,
                       chart_id=chart_id)
            
            # Convert data to DataFrame for easier manipulation
            df = self._prepare_dataframe(data)
            
            # Generate the chart based on type
            fig = self._generate_chart_by_type(df, config)
            
            # Apply styling and configuration
            fig = self._apply_styling(fig, config)
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Create response
            response = ChartResponse(
                chart_id=chart_id or f"chart_{int(time.time())}",
                chart_type=config.chart_type,
                config=config,
                data_summary=self._create_data_summary(data, df),
                generation_time=generation_time,
                file_size=None,  # Will be set during export
                export_url=None,  # Will be set during export
                interactive_url=f"/charts/{chart_id}/interactive" if chart_id else None
            )
            
            # Store the figure for later use (in a real implementation, this would be cached)
            response.plotly_json = fig.to_json()
            
            # Log successful generation
            log_chart_generation(
                chart_type=config.chart_type,
                data_points=data.total_rows,
                generation_time=generation_time,
                success=True
            )
            
            logger.info("Chart generation completed",
                       chart_type=config.chart_type,
                       generation_time=generation_time,
                       chart_id=response.chart_id)
            
            return response
            
        except Exception as e:
            generation_time = time.time() - start_time
            log_chart_generation(
                chart_type=config.chart_type,
                data_points=data.total_rows,
                generation_time=generation_time,
                success=False,
                error=str(e)
            )
            
            logger.error("Chart generation failed",
                        chart_type=config.chart_type,
                        error=str(e),
                        exc_info=True)
            raise
    
    def _prepare_dataframe(self, data: ChartData) -> pd.DataFrame:
        """Convert ChartData to pandas DataFrame"""
        try:
            df = pd.DataFrame(data.rows)
            
            # Apply data type conversions based on field definitions
            for field in data.fields:
                if field.name in df.columns:
                    if field.data_type == DataType.NUMERICAL:
                        df[field.name] = pd.to_numeric(df[field.name], errors='coerce')
                    elif field.data_type == DataType.TEMPORAL:
                        df[field.name] = pd.to_datetime(df[field.name], errors='coerce')
                    elif field.data_type == DataType.CATEGORICAL:
                        df[field.name] = df[field.name].astype('category')
            
            return df
            
        except Exception as e:
            logger.error("Failed to prepare DataFrame", error=str(e))
            raise ValueError(f"Data preparation failed: {str(e)}")
    
    def _generate_chart_by_type(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate chart based on chart type"""
        
        chart_generators = {
            ChartType.LINE: self._generate_line_chart,
            ChartType.BAR: self._generate_bar_chart,
            ChartType.PIE: self._generate_pie_chart,
            ChartType.SCATTER: self._generate_scatter_chart,
            ChartType.HISTOGRAM: self._generate_histogram,
            ChartType.HEATMAP: self._generate_heatmap,
            ChartType.TREEMAP: self._generate_treemap,
            ChartType.SANKEY: self._generate_sankey_chart,
            ChartType.GAUGE: self._generate_gauge_chart,
            ChartType.TABLE: self._generate_table
        }
        
        generator = chart_generators.get(config.chart_type)
        if not generator:
            raise ValueError(f"Unsupported chart type: {config.chart_type}")
        
        return generator(df, config)
    
    def _generate_line_chart(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate line chart"""
        fig = go.Figure()
        
        x_data = df[config.x_axis] if config.x_axis else df.index
        
        if isinstance(config.y_axis, list):
            # Multiple series
            colors = self._get_color_palette(config.color_scheme, len(config.y_axis))
            for i, y_col in enumerate(config.y_axis):
                fig.add_trace(go.Scatter(
                    x=x_data,
                    y=df[y_col],
                    mode='lines+markers',
                    name=y_col,
                    line=dict(color=colors[i % len(colors)]),
                    hovertemplate=f'<b>{y_col}</b><br>' +
                                 f'{config.x_axis}: %{{x}}<br>' +
                                 f'{y_col}: %{{y}}<br>' +
                                 '<extra></extra>'
                ))
        else:
            # Single series
            color_col = config.color_field
            if color_col and color_col in df.columns:
                # Colored by category
                for category in df[color_col].unique():
                    mask = df[color_col] == category
                    fig.add_trace(go.Scatter(
                        x=x_data[mask],
                        y=df[config.y_axis][mask],
                        mode='lines+markers',
                        name=str(category),
                        hovertemplate=f'<b>{category}</b><br>' +
                                     f'{config.x_axis}: %{{x}}<br>' +
                                     f'{config.y_axis}: %{{y}}<br>' +
                                     '<extra></extra>'
                    ))
            else:
                # Single colored line
                fig.add_trace(go.Scatter(
                    x=x_data,
                    y=df[config.y_axis],
                    mode='lines+markers',
                    name=config.y_axis,
                    hovertemplate=f'{config.x_axis}: %{{x}}<br>' +
                                 f'{config.y_axis}: %{{y}}<br>' +
                                 '<extra></extra>'
                ))
        
        return fig
    
    def _generate_bar_chart(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate bar chart"""
        fig = go.Figure()
        
        x_data = df[config.x_axis] if config.x_axis else df.index
        
        if isinstance(config.y_axis, list):
            # Multiple series (grouped bars)
            colors = self._get_color_palette(config.color_scheme, len(config.y_axis))
            for i, y_col in enumerate(config.y_axis):
                fig.add_trace(go.Bar(
                    x=x_data,
                    y=df[y_col],
                    name=y_col,
                    marker_color=colors[i % len(colors)],
                    hovertemplate=f'<b>{y_col}</b><br>' +
                                 f'{config.x_axis}: %{{x}}<br>' +
                                 f'{y_col}: %{{y}}<br>' +
                                 '<extra></extra>'
                ))
        else:
            # Single series
            color_col = config.color_field
            if color_col and color_col in df.columns:
                # Colored by category
                colors = self._get_color_palette(config.color_scheme, df[color_col].nunique())
                color_map = {cat: colors[i % len(colors)] 
                           for i, cat in enumerate(df[color_col].unique())}
                
                fig.add_trace(go.Bar(
                    x=x_data,
                    y=df[config.y_axis],
                    marker_color=[color_map[cat] for cat in df[color_col]],
                    text=df[config.y_axis],
                    textposition='auto',
                    hovertemplate=f'{config.x_axis}: %{{x}}<br>' +
                                 f'{config.y_axis}: %{{y}}<br>' +
                                 f'{color_col}: %{{text}}<br>' +
                                 '<extra></extra>'
                ))
            else:
                # Single colored bars
                fig.add_trace(go.Bar(
                    x=x_data,
                    y=df[config.y_axis],
                    marker_color=self._get_color_palette(config.color_scheme, 1)[0],
                    text=df[config.y_axis],
                    textposition='auto',
                    hovertemplate=f'{config.x_axis}: %{{x}}<br>' +
                                 f'{config.y_axis}: %{{y}}<br>' +
                                 '<extra></extra>'
                ))
        
        return fig
    
    def _generate_pie_chart(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate pie chart"""
        labels_col = config.color_field or config.x_axis
        values_col = config.y_axis
        
        if not labels_col or not values_col:
            raise ValueError("Pie chart requires both labels and values columns")
        
        # Aggregate data if needed
        if len(df) > df[labels_col].nunique():
            df_agg = df.groupby(labels_col)[values_col].sum().reset_index()
        else:
            df_agg = df
        
        colors = self._get_color_palette(config.color_scheme, len(df_agg))
        
        fig = go.Figure(data=[go.Pie(
            labels=df_agg[labels_col],
            values=df_agg[values_col],
            hole=0.3 if config.chart_options.get('donut', False) else 0,
            marker_colors=colors,
            textinfo='label+percent+value',
            textposition='auto',
            hovertemplate='<b>%{label}</b><br>' +
                         'Value: %{value}<br>' +
                         'Percentage: %{percent}<br>' +
                         '<extra></extra>'
        )])
        
        return fig
    
    def _generate_scatter_chart(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate scatter plot"""
        fig = go.Figure()
        
        x_data = df[config.x_axis]
        y_data = df[config.y_axis] if isinstance(config.y_axis, str) else df[config.y_axis[0]]
        
        color_col = config.color_field
        size_col = config.size_field
        
        if color_col and color_col in df.columns:
            # Colored by category
            for category in df[color_col].unique():
                mask = df[color_col] == category
                size_data = df[size_col][mask] if size_col and size_col in df.columns else 8
                
                fig.add_trace(go.Scatter(
                    x=x_data[mask],
                    y=y_data[mask],
                    mode='markers',
                    name=str(category),
                    marker=dict(
                        size=size_data,
                        sizemode='diameter',
                        sizeref=2. * max(size_data) / (40.**2) if hasattr(size_data, '__iter__') else 1,
                        sizemin=4
                    ),
                    hovertemplate=f'<b>{category}</b><br>' +
                                 f'{config.x_axis}: %{{x}}<br>' +
                                 f'{config.y_axis}: %{{y}}<br>' +
                                 (f'{size_col}: %{{marker.size}}<br>' if size_col else '') +
                                 '<extra></extra>'
                ))
        else:
            # Single series
            size_data = df[size_col] if size_col and size_col in df.columns else 8
            
            fig.add_trace(go.Scatter(
                x=x_data,
                y=y_data,
                mode='markers',
                marker=dict(
                    size=size_data,
                    color=self._get_color_palette(config.color_scheme, 1)[0],
                    sizemode='diameter',
                    sizeref=2. * max(size_data) / (40.**2) if hasattr(size_data, '__iter__') else 1,
                    sizemin=4
                ),
                hovertemplate=f'{config.x_axis}: %{{x}}<br>' +
                             f'{config.y_axis}: %{{y}}<br>' +
                             (f'{size_col}: %{{marker.size}}<br>' if size_col else '') +
                             '<extra></extra>'
            ))
        
        return fig
    
    def _generate_histogram(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate histogram"""
        data_col = config.x_axis or config.y_axis
        
        if not data_col:
            raise ValueError("Histogram requires a data column")
        
        fig = go.Figure()
        
        color_col = config.color_field
        if color_col and color_col in df.columns:
            # Multiple histograms by category
            for category in df[color_col].unique():
                mask = df[color_col] == category
                fig.add_trace(go.Histogram(
                    x=df[data_col][mask],
                    name=str(category),
                    opacity=0.7,
                    nbinsx=config.chart_options.get('bins', 30),
                    hovertemplate=f'<b>{category}</b><br>' +
                                 f'{data_col}: %{{x}}<br>' +
                                 'Count: %{y}<br>' +
                                 '<extra></extra>'
                ))
        else:
            # Single histogram
            fig.add_trace(go.Histogram(
                x=df[data_col],
                marker_color=self._get_color_palette(config.color_scheme, 1)[0],
                opacity=0.8,
                nbinsx=config.chart_options.get('bins', 30),
                hovertemplate=f'{data_col}: %{{x}}<br>' +
                             'Count: %{y}<br>' +
                             '<extra></extra>'
            ))
        
        return fig
    
    def _generate_heatmap(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate heatmap"""
        x_col = config.x_axis
        y_col = config.y_axis if isinstance(config.y_axis, str) else config.y_axis[0]
        z_col = config.color_field
        
        if not all([x_col, y_col, z_col]):
            raise ValueError("Heatmap requires x, y, and z columns")
        
        # Create pivot table for heatmap
        pivot_df = df.pivot_table(
            index=y_col, 
            columns=x_col, 
            values=z_col, 
            aggfunc='mean'
        )
        
        colorscale = self._get_colorscale(config.color_scheme)
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_df.values,
            x=pivot_df.columns,
            y=pivot_df.index,
            colorscale=colorscale,
            hovertemplate=f'{x_col}: %{{x}}<br>' +
                         f'{y_col}: %{{y}}<br>' +
                         f'{z_col}: %{{z}}<br>' +
                         '<extra></extra>'
        ))
        
        return fig
    
    def _generate_treemap(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate treemap"""
        labels_col = config.color_field or config.x_axis
        values_col = config.y_axis
        
        if not labels_col or not values_col:
            raise ValueError("Treemap requires both labels and values columns")
        
        # Aggregate data if needed
        if len(df) > df[labels_col].nunique():
            df_agg = df.groupby(labels_col)[values_col].sum().reset_index()
        else:
            df_agg = df
        
        fig = go.Figure(go.Treemap(
            labels=df_agg[labels_col],
            values=df_agg[values_col],
            parents=[""] * len(df_agg),  # All at root level
            hovertemplate='<b>%{label}</b><br>' +
                         'Value: %{value}<br>' +
                         'Percentage: %{percentParent}<br>' +
                         '<extra></extra>'
        ))
        
        return fig
    
    def _generate_sankey_chart(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate sankey diagram for flow visualization"""
        source_col = config.x_axis
        target_col = config.y_axis if isinstance(config.y_axis, str) else config.y_axis[0]
        value_col = config.color_field
        
        if not all([source_col, target_col, value_col]):
            raise ValueError("Sankey diagram requires source, target, and value columns")
        
        # Prepare data for Sankey
        # Get unique nodes (sources and targets)
        sources = df[source_col].unique().tolist()
        targets = df[target_col].unique().tolist()
        all_nodes = list(set(sources + targets))
        
        # Create node mappings
        node_map = {node: i for i, node in enumerate(all_nodes)}
        
        # Prepare Sankey data
        source_indices = [node_map[source] for source in df[source_col]]
        target_indices = [node_map[target] for target in df[target_col]]
        values = df[value_col].tolist()
        
        # Generate colors for nodes and links
        colors = self._get_color_palette(config.color_scheme, len(all_nodes))
        node_colors = colors[:len(all_nodes)]
        link_colors = [f"rgba({int(colors[i % len(colors)][1:3], 16)}, "
                      f"{int(colors[i % len(colors)][3:5], 16)}, "
                      f"{int(colors[i % len(colors)][5:7], 16)}, 0.4)" 
                      for i in source_indices]
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                color=node_colors
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=values,
                color=link_colors,
                hovertemplate='%{source.label} → %{target.label}<br>' +
                             'Value: %{value}<br>' +
                             '<extra></extra>'
            )
        )])
        
        return fig
    
    def _generate_gauge_chart(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate gauge chart for KPI visualization"""
        value_col = config.y_axis if isinstance(config.y_axis, str) else config.y_axis[0]
        
        if not value_col:
            raise ValueError("Gauge chart requires a value column")
        
        # Get the value (use first row or aggregate if multiple)
        if len(df) > 1:
            # Use mean for multiple values
            value = df[value_col].mean()
        else:
            value = df[value_col].iloc[0]
        
        # Get gauge configuration from chart options
        gauge_options = config.chart_options
        min_value = gauge_options.get('min', 0)
        max_value = gauge_options.get('max', 100)
        threshold_1 = gauge_options.get('threshold_1', max_value * 0.6)
        threshold_2 = gauge_options.get('threshold_2', max_value * 0.8)
        
        # Determine gauge color based on value
        if value <= threshold_1:
            gauge_color = "green"
        elif value <= threshold_2:
            gauge_color = "yellow"
        else:
            gauge_color = "red"
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': config.title or value_col},
            delta={'reference': gauge_options.get('reference', threshold_1)},
            gauge={
                'axis': {'range': [None, max_value]},
                'bar': {'color': gauge_color},
                'steps': [
                    {'range': [min_value, threshold_1], 'color': "lightgray"},
                    {'range': [threshold_1, threshold_2], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': threshold_2
                }
            }
        ))
        
        return fig
    
    def _generate_table(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> go.Figure:
        """Generate table"""
        # Limit rows for performance
        max_rows = config.chart_options.get('max_rows', 100)
        df_display = df.head(max_rows)
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df_display.columns),
                fill_color='lightblue',
                align='left',
                font=dict(size=12, color='darkblue')
            ),
            cells=dict(
                values=[df_display[col] for col in df_display.columns],
                fill_color='white',
                align='left',
                font=dict(size=11)
            )
        )])
        
        return fig
    
    def _apply_styling(self, fig: go.Figure, config: ChartConfig) -> go.Figure:
        """Apply styling and configuration to the chart"""
        
        # Update layout
        layout_updates = {
            'title': config.title or '',
            'width': config.width,
            'height': config.height,
            'showlegend': True,
            'hovermode': 'closest' if config.hover_enabled else False,
            'template': 'plotly_white'
        }
        
        # Add axis labels
        if config.x_axis and config.chart_type != ChartType.PIE:
            layout_updates['xaxis_title'] = config.x_axis
        if config.y_axis and config.chart_type not in [ChartType.PIE, ChartType.TABLE]:
            y_title = config.y_axis if isinstance(config.y_axis, str) else ', '.join(config.y_axis)
            layout_updates['yaxis_title'] = y_title
        
        # Configure zoom and pan
        if config.zoom_enabled and config.chart_type not in [ChartType.PIE, ChartType.TABLE]:
            layout_updates['xaxis'] = dict(fixedrange=False)
            layout_updates['yaxis'] = dict(fixedrange=False)
        
        if not config.pan_enabled:
            layout_updates.setdefault('xaxis', {})['fixedrange'] = True
            layout_updates.setdefault('yaxis', {})['fixedrange'] = True
        
        fig.update_layout(**layout_updates)
        
        # Configure interactivity
        if not config.interactive:
            fig.update_layout(
                xaxis=dict(fixedrange=True),
                yaxis=dict(fixedrange=True),
                showlegend=False
            )
        
        return fig
    
    def _get_color_palette(self, scheme: ColorScheme, count: int) -> List[str]:
        """Get color palette for the specified scheme"""
        colors = self.color_schemes.get(scheme, self.color_schemes[ColorScheme.DEFAULT])
        
        # Repeat colors if we need more than available
        while len(colors) < count:
            colors.extend(colors)
        
        return colors[:count]
    
    def _get_colorscale(self, scheme: ColorScheme) -> str:
        """Get Plotly colorscale name for the specified scheme"""
        colorscale_map = {
            ColorScheme.VIRIDIS: 'Viridis',
            ColorScheme.PLASMA: 'Plasma',
            ColorScheme.INFERNO: 'Inferno',
            ColorScheme.MAGMA: 'Magma',
            ColorScheme.BLUES: 'Blues',
            ColorScheme.REDS: 'Reds',
            ColorScheme.GREENS: 'Greens',
            ColorScheme.DEFAULT: 'RdYlBu',
            ColorScheme.CATEGORICAL: 'Set1'
        }
        
        return colorscale_map.get(scheme, 'RdYlBu')
    
    def _create_data_summary(
        self, 
        data: ChartData, 
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Create data summary for the response"""
        return {
            "total_rows": data.total_rows,
            "total_fields": len(data.fields),
            "processed_rows": len(df),
            "field_types": {field.name: field.data_type for field in data.fields},
            "data_shape": df.shape,
            "memory_usage": df.memory_usage(deep=True).sum(),
            "has_null_values": df.isnull().any().any(),
            "categorical_fields": [f.name for f in data.fields if f.data_type == DataType.CATEGORICAL],
            "numerical_fields": [f.name for f in data.fields if f.data_type == DataType.NUMERICAL],
            "temporal_fields": [f.name for f in data.fields if f.data_type == DataType.TEMPORAL]
        }
    
    def export_chart(
        self, 
        fig: go.Figure, 
        format: ExportFormat,
        filename: Optional[str] = None
    ) -> Tuple[bytes, str]:
        """
        Export chart to specified format
        
        Args:
            fig: Plotly figure
            format: Export format
            filename: Optional filename
            
        Returns:
            Tuple of (file_bytes, content_type)
        """
        try:
            if format == ExportFormat.PNG:
                img_bytes = fig.to_image(format="png")
                return img_bytes, "image/png"
            
            elif format == ExportFormat.PDF:
                img_bytes = fig.to_image(format="pdf")
                return img_bytes, "application/pdf"
            
            elif format == ExportFormat.SVG:
                img_bytes = fig.to_image(format="svg")
                return img_bytes, "image/svg+xml"
            
            elif format == ExportFormat.HTML:
                html_str = fig.to_html(include_plotlyjs=True)
                return html_str.encode('utf-8'), "text/html"
            
            elif format == ExportFormat.JSON:
                json_str = fig.to_json()
                return json_str.encode('utf-8'), "application/json"
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error("Chart export failed", format=format, error=str(e))
            raise ValueError(f"Export failed: {str(e)}")