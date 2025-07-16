"""
Interactive Chart Features Service

This service handles advanced interactive features for charts including:
- Data filtering and crossfilter capabilities
- Drill-down functionality for hierarchical exploration
- Advanced selection modes (brush, lasso)
- Chart linking and synchronized interactions
- Real-time data updates and streaming
"""
import json
import time
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from ..models.chart import (
    ChartConfig, ChartData, ChartFilter, ChartSelection, DrillDownConfig,
    InteractionEvent, ChartInteractiveConfig, InteractiveChartResponse,
    FilterOperation, SelectionMode, InteractionType, ChartType
)
from ..core.logging import get_logger
from .chart_generator import ChartGenerator

logger = get_logger(__name__)


class InteractiveChartService:
    """Service for managing interactive chart features"""
    
    def __init__(self):
        self.chart_generator = ChartGenerator()
        self.active_selections = {}  # Store active selections by chart_id
        self.filter_cache = {}  # Cache filtered data for performance
        
    def create_interactive_chart(
        self,
        data: ChartData,
        config: ChartConfig,
        interactive_config: Optional[ChartInteractiveConfig] = None,
        chart_id: Optional[str] = None
    ) -> InteractiveChartResponse:
        """
        Create an interactive chart with advanced features
        
        Args:
            data: Chart data
            config: Chart configuration
            interactive_config: Interactive feature configuration
            chart_id: Optional chart identifier
            
        Returns:
            InteractiveChartResponse with enhanced interactive features
        """
        start_time = time.time()
        chart_id = chart_id or f"interactive_chart_{int(time.time())}"
        
        logger.info("Creating interactive chart", 
                   chart_type=config.chart_type,
                   chart_id=chart_id,
                   filters_count=len(interactive_config.filters) if interactive_config else 0)
        
        try:
            # Apply filters if specified
            filtered_data = self._apply_filters(data, interactive_config.filters if interactive_config else [])
            
            # Generate base chart
            base_response = self.chart_generator.generate_chart(filtered_data, config, chart_id)
            
            # Enhance with interactive features
            enhanced_fig = self._enhance_chart_interactivity(
                go.Figure.from_json(base_response.plotly_json),
                config,
                interactive_config
            )
            
            # Create interactive response
            interactive_response = InteractiveChartResponse(
                chart_id=chart_id,
                chart_type=config.chart_type,
                config=config,
                interactive_config=interactive_config or ChartInteractiveConfig(),
                data_summary=base_response.data_summary,
                plotly_json=enhanced_fig.to_json(),
                interaction_events=[],
                generation_time=time.time() - start_time
            )
            
            logger.info("Interactive chart created successfully",
                       chart_id=chart_id,
                       generation_time=interactive_response.generation_time)
            
            return interactive_response
            
        except Exception as e:
            logger.error("Interactive chart creation failed",
                        chart_id=chart_id,
                        error=str(e),
                        exc_info=True)
            raise
    
    def _apply_filters(self, data: ChartData, filters: List[ChartFilter]) -> ChartData:
        """Apply filters to chart data"""
        if not filters:
            return data
            
        df = pd.DataFrame(data.rows)
        
        for filter_config in filters:
            df = self._apply_single_filter(df, filter_config)
        
        # Update data structure
        filtered_data = ChartData(
            fields=data.fields,
            rows=df.to_dict(orient='records'),
            total_rows=len(df),
            is_aggregated=data.is_aggregated,
            time_field=data.time_field
        )
        
        return filtered_data
    
    def _apply_single_filter(self, df: pd.DataFrame, filter_config: ChartFilter) -> pd.DataFrame:
        """Apply a single filter to the dataframe"""
        field = filter_config.field
        operation = filter_config.operation
        value = filter_config.value
        
        if field not in df.columns:
            logger.warning(f"Filter field '{field}' not found in data")
            return df
        
        try:
            if operation == FilterOperation.EQUALS:
                if isinstance(value, str) and not filter_config.case_sensitive:
                    return df[df[field].str.lower() == value.lower()]
                return df[df[field] == value]
                
            elif operation == FilterOperation.NOT_EQUALS:
                if isinstance(value, str) and not filter_config.case_sensitive:
                    return df[df[field].str.lower() != value.lower()]
                return df[df[field] != value]
                
            elif operation == FilterOperation.GREATER_THAN:
                return df[df[field] > value]
                
            elif operation == FilterOperation.LESS_THAN:
                return df[df[field] < value]
                
            elif operation == FilterOperation.GREATER_EQUAL:
                return df[df[field] >= value]
                
            elif operation == FilterOperation.LESS_EQUAL:
                return df[df[field] <= value]
                
            elif operation == FilterOperation.CONTAINS:
                if not filter_config.case_sensitive:
                    return df[df[field].str.lower().str.contains(str(value).lower(), na=False)]
                return df[df[field].str.contains(str(value), na=False)]
                
            elif operation == FilterOperation.NOT_CONTAINS:
                if not filter_config.case_sensitive:
                    return df[~df[field].str.lower().str.contains(str(value).lower(), na=False)]
                return df[~df[field].str.contains(str(value), na=False)]
                
            elif operation == FilterOperation.IN:
                return df[df[field].isin(value)]
                
            elif operation == FilterOperation.NOT_IN:
                return df[~df[field].isin(value)]
                
            elif operation == FilterOperation.BETWEEN:
                if isinstance(value, list) and len(value) == 2:
                    return df[(df[field] >= value[0]) & (df[field] <= value[1])]
                    
            elif operation == FilterOperation.IS_NULL:
                return df[df[field].isnull()]
                
            elif operation == FilterOperation.IS_NOT_NULL:
                return df[df[field].notnull()]
                
            else:
                logger.warning(f"Unsupported filter operation: {operation}")
                return df
                
        except Exception as e:
            logger.error(f"Error applying filter {operation} on field {field}: {str(e)}")
            return df
    
    def _enhance_chart_interactivity(
        self,
        fig: go.Figure,
        config: ChartConfig,
        interactive_config: Optional[ChartInteractiveConfig]
    ) -> go.Figure:
        """Enhance chart with interactive features"""
        
        if not interactive_config:
            return fig
        
        # Configure selection modes
        if config.brush_enabled or config.lasso_enabled:
            fig.update_layout(
                dragmode='select' if config.brush_enabled else 'lasso',
                selectdirection='diagonal',
                newselection=dict(
                    line=dict(color='rgba(0,0,255,0.5)', width=2),
                    fillcolor='rgba(0,0,255,0.1)'
                )
            )
        
        # Add crossfilter capabilities
        if interactive_config.crossfilter_enabled:
            self._add_crossfilter_features(fig, config)
        
        # Configure drill-down
        if config.drill_down_enabled and interactive_config.drill_down:
            self._add_drill_down_features(fig, config, interactive_config.drill_down)
        
        # Add custom interactions based on chart type
        if config.chart_type in [ChartType.BAR, ChartType.LINE, ChartType.SCATTER]:
            self._add_chart_specific_interactions(fig, config)
        
        return fig
    
    def _add_crossfilter_features(self, fig: go.Figure, config: ChartConfig):
        """Add crossfilter capabilities to the chart"""
        # Add custom data attributes for crossfilter
        for trace in fig.data:
            if hasattr(trace, 'customdata'):
                # Enhance customdata for crossfilter linking
                trace.update(
                    customdata=trace.customdata,
                    hovertemplate=trace.hovertemplate + "<br>Click to filter linked charts<extra></extra>"
                )
    
    def _add_drill_down_features(self, fig: go.Figure, config: ChartConfig, drill_config: DrillDownConfig):
        """Add drill-down functionality to the chart"""
        if not drill_config.enabled:
            return
            
        # Add click events for drill-down
        for trace in fig.data:
            if hasattr(trace, 'marker'):
                trace.update(
                    marker=dict(
                        **trace.marker,
                        line=dict(width=1, color='rgba(0,0,0,0.3)')
                    )
                )
            
            # Update hover template to indicate drill-down capability
            if hasattr(trace, 'hovertemplate'):
                trace.update(
                    hovertemplate=trace.hovertemplate + "<br><i>Click to drill down</i><extra></extra>"
                )
    
    def _add_chart_specific_interactions(self, fig: go.Figure, config: ChartConfig):
        """Add chart-type specific interactive features"""
        
        if config.chart_type == ChartType.SCATTER:
            # Add range selectors for scatter plots
            fig.update_layout(
                xaxis=dict(
                    rangeslider=dict(visible=False),
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="Reset", step="all"),
                            dict(count=100, label="Top 100", step="all", stepmode="backward"),
                            dict(count=500, label="Top 500", step="all", stepmode="backward"),
                        ])
                    )
                )
            )
        
        elif config.chart_type == ChartType.LINE:
            # Add time range selector for line charts
            fig.update_layout(
                xaxis=dict(
                    rangeslider=dict(visible=True),
                    type='date' if config.x_axis and 'time' in config.x_axis.lower() else 'linear'
                )
            )
        
        elif config.chart_type == ChartType.BAR:
            # Add sorting options for bar charts
            fig.update_layout(
                updatemenus=[
                    dict(
                        type="dropdown",
                        direction="down",
                        showactive=True,
                        x=0.1,
                        y=1.15,
                        buttons=list([
                            dict(label="Original Order", method="restyle", args=["transforms", []]),
                            dict(label="Sort Ascending", method="restyle", 
                                 args=["transforms[0].operation", "sort"]),
                            dict(label="Sort Descending", method="restyle", 
                                 args=["transforms[0].direction", "descending"])
                        ]),
                    )
                ]
            )
    
    def handle_interaction_event(
        self,
        chart_id: str,
        event_type: InteractionType,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle chart interaction events
        
        Args:
            chart_id: Chart identifier
            event_type: Type of interaction
            event_data: Event data
            user_id: User who triggered the event
            
        Returns:
            Response data based on interaction type
        """
        logger.info("Handling interaction event",
                   chart_id=chart_id,
                   event_type=event_type,
                   user_id=user_id)
        
        try:
            if event_type == InteractionType.DRILL_DOWN:
                return self._handle_drill_down(chart_id, event_data)
            elif event_type == InteractionType.FILTER:
                return self._handle_filter_event(chart_id, event_data)
            elif event_type == InteractionType.SELECT:
                return self._handle_selection_event(chart_id, event_data)
            elif event_type == InteractionType.BRUSH:
                return self._handle_brush_event(chart_id, event_data)
            elif event_type == InteractionType.ZOOM:
                return self._handle_zoom_event(chart_id, event_data)
            else:
                logger.warning(f"Unhandled interaction type: {event_type}")
                return {"status": "unhandled", "event_type": event_type}
                
        except Exception as e:
            logger.error("Error handling interaction event",
                        chart_id=chart_id,
                        event_type=event_type,
                        error=str(e),
                        exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def _handle_drill_down(self, chart_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle drill-down interaction"""
        # Extract drill-down parameters
        point_data = event_data.get('point', {})
        field = event_data.get('field')
        value = event_data.get('value')
        
        return {
            "status": "drill_down",
            "chart_id": chart_id,
            "field": field,
            "value": value,
            "point_data": point_data,
            "suggested_filters": [
                {
                    "field": field,
                    "operation": "equals",
                    "value": value
                }
            ]
        }
    
    def _handle_filter_event(self, chart_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle filter interaction"""
        filters = event_data.get('filters', [])
        
        return {
            "status": "filtered",
            "chart_id": chart_id,
            "applied_filters": filters,
            "filter_count": len(filters)
        }
    
    def _handle_selection_event(self, chart_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle selection interaction"""
        selected_points = event_data.get('points', [])
        selection_mode = event_data.get('mode', 'single')
        
        # Store selection state
        self.active_selections[chart_id] = {
            "points": selected_points,
            "mode": selection_mode,
            "timestamp": time.time()
        }
        
        return {
            "status": "selected",
            "chart_id": chart_id,
            "selected_count": len(selected_points),
            "selection_mode": selection_mode,
            "selected_data": selected_points
        }
    
    def _handle_brush_event(self, chart_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle brush selection interaction"""
        bounds = event_data.get('bounds', {})
        selected_points = event_data.get('points', [])
        
        return {
            "status": "brushed",
            "chart_id": chart_id,
            "bounds": bounds,
            "selected_count": len(selected_points),
            "crossfilter_ready": True
        }
    
    def _handle_zoom_event(self, chart_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle zoom interaction"""
        zoom_level = event_data.get('zoom_level', 1.0)
        viewport = event_data.get('viewport', {})
        
        return {
            "status": "zoomed",
            "chart_id": chart_id,
            "zoom_level": zoom_level,
            "viewport": viewport
        }
    
    def create_linked_charts(
        self,
        chart_configs: List[Tuple[ChartData, ChartConfig]],
        crossfilter_enabled: bool = True
    ) -> List[InteractiveChartResponse]:
        """
        Create multiple linked charts with crossfilter capabilities
        
        Args:
            chart_configs: List of (data, config) tuples
            crossfilter_enabled: Enable crossfilter linking
            
        Returns:
            List of interactive chart responses
        """
        logger.info("Creating linked charts", chart_count=len(chart_configs))
        
        charts = []
        chart_ids = []
        
        for i, (data, config) in enumerate(chart_configs):
            chart_id = f"linked_chart_{i}_{int(time.time())}"
            chart_ids.append(chart_id)
            
            # Configure interactive features
            interactive_config = ChartInteractiveConfig(
                crossfilter_enabled=crossfilter_enabled,
                linked_charts=[cid for cid in chart_ids if cid != chart_id]
            )
            
            chart = self.create_interactive_chart(data, config, interactive_config, chart_id)
            charts.append(chart)
        
        # Update linked chart references
        for chart in charts:
            chart.interactive_config.linked_charts = [c.chart_id for c in charts if c.chart_id != chart.chart_id]
        
        logger.info("Linked charts created successfully", chart_count=len(charts))
        return charts
    
    def get_chart_state(self, chart_id: str) -> Dict[str, Any]:
        """Get current state of an interactive chart"""
        selection = self.active_selections.get(chart_id, {})
        
        return {
            "chart_id": chart_id,
            "has_selection": bool(selection),
            "selection": selection,
            "cached_filters": list(self.filter_cache.keys()) if chart_id in self.filter_cache else []
        }
    
    def clear_chart_state(self, chart_id: str):
        """Clear stored state for a chart"""
        if chart_id in self.active_selections:
            del self.active_selections[chart_id]
        if chart_id in self.filter_cache:
            del self.filter_cache[chart_id]
        
        logger.info("Chart state cleared", chart_id=chart_id)