"""
API endpoints for visualization service

Provides endpoints for chart generation, automatic chart type selection,
and dashboard management.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse, Response
import asyncio
import time
import uuid
import plotly.graph_objects as go

from ...models.chart import (
    ChartRequest, ChartResponse, ChartRecommendation, ChartData, 
    ChartConfig, ChartType, Dashboard, DashboardPanel, ExportFormat,
    ChartFilter, ChartSelection, DrillDownConfig, InteractionEvent,
    ChartInteractiveConfig, InteractiveChartResponse, InteractionType,
    FilterOperation, SelectionMode, ChartCustomization, ChartTemplate,
    ChartTheme, FontFamily, ColorScheme, LegendPosition
)
from ...services.chart_selector import ChartTypeSelector
from ...services.chart_generator import ChartGenerator
from ...services.interactive_charts import InteractiveChartService
from ...core.logging import get_logger, log_chart_generation
from ...core.config import settings

logger = get_logger(__name__)
router = APIRouter()

# Initialize services
chart_selector = ChartTypeSelector()
chart_generator = ChartGenerator()
interactive_service = InteractiveChartService()


# Chart Type Selection Endpoints

@router.post("/charts/recommend", response_model=ChartRecommendation)
async def recommend_chart_type(
    chart_data: ChartData,
    user_preferences: Optional[Dict[str, Any]] = None
) -> ChartRecommendation:
    """
    Recommend the best chart type for given data
    
    Analyzes data characteristics and recommends the most appropriate
    chart type along with optimal configuration settings.
    """
    start_time = time.time()
    
    try:
        logger.info("Chart recommendation request received", 
                   data_rows=chart_data.total_rows,
                   data_fields=len(chart_data.fields))
        
        # Get recommendation from chart selector
        recommendation = chart_selector.recommend_chart_type(
            data=chart_data,
            user_preferences=user_preferences
        )
        
        generation_time = time.time() - start_time
        
        logger.info("Chart recommendation completed",
                   recommended_type=recommendation.chart_type,
                   confidence=recommendation.confidence,
                   generation_time=generation_time)
        
        return recommendation
        
    except Exception as e:
        logger.error("Chart recommendation failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chart recommendation failed: {str(e)}")


@router.post("/charts/analyze", response_model=Dict[str, Any])
async def analyze_data_for_charts(chart_data: ChartData) -> Dict[str, Any]:
    """
    Analyze data characteristics for chart selection
    
    Provides detailed analysis of data properties that influence
    chart type selection without making specific recommendations.
    """
    try:
        logger.info("Data analysis request received",
                   data_rows=chart_data.total_rows,
                   data_fields=len(chart_data.fields))
        
        # Analyze data using chart selector's internal methods
        analysis = chart_selector._analyze_data(chart_data)
        
        # Add additional insights
        insights = {
            'data_summary': {
                'total_rows': chart_data.total_rows,
                'total_fields': len(chart_data.fields),
                'has_temporal_data': len(analysis.get('temporal_fields', [])) > 0,
                'has_numerical_data': len(analysis.get('numerical_fields', [])) > 0,
                'has_categorical_data': len(analysis.get('categorical_fields', [])) > 0,
                'data_density': analysis.get('data_density', 'unknown'),
                'data_pattern': analysis.get('data_pattern', 'unknown')
            },
            'field_analysis': analysis.get('field_types', {}),
            'suitable_chart_types': [],
            'recommendations': {
                'primary_use_cases': [],
                'visualization_goals': [],
                'interaction_features': []
            }
        }
        
        # Determine suitable chart types based on analysis
        pattern = analysis.get('data_pattern', 'general')
        if pattern == 'time_series':
            insights['suitable_chart_types'] = ['line', 'bar', 'area']
            insights['recommendations']['primary_use_cases'] = ['trend_analysis', 'time_comparison']
        elif pattern == 'correlation':
            insights['suitable_chart_types'] = ['scatter', 'heatmap', 'bubble']
            insights['recommendations']['primary_use_cases'] = ['correlation_analysis', 'relationship_exploration']
        elif pattern == 'distribution':
            insights['suitable_chart_types'] = ['histogram', 'box_plot', 'violin']
            insights['recommendations']['primary_use_cases'] = ['distribution_analysis', 'statistical_summary']
        elif pattern == 'categorical_comparison':
            insights['suitable_chart_types'] = ['bar', 'column', 'pie']
            insights['recommendations']['primary_use_cases'] = ['category_comparison', 'ranking']
        elif pattern == 'part_to_whole':
            insights['suitable_chart_types'] = ['pie', 'treemap', 'stacked_bar']
            insights['recommendations']['primary_use_cases'] = ['composition_analysis', 'market_share']
        else:
            insights['suitable_chart_types'] = ['table', 'bar', 'line']
            insights['recommendations']['primary_use_cases'] = ['data_exploration', 'general_analysis']
        
        logger.info("Data analysis completed", 
                   pattern=pattern,
                   suitable_types=len(insights['suitable_chart_types']))
        
        return insights
        
    except Exception as e:
        logger.error("Data analysis failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Data analysis failed: {str(e)}")


@router.get("/charts/types", response_model=Dict[str, Any])
async def get_supported_chart_types() -> Dict[str, Any]:
    """
    Get information about supported chart types
    
    Returns metadata about all supported chart types including
    their use cases, data requirements, and configuration options.
    """
    chart_types_info = {
        ChartType.LINE: {
            "name": "Line Chart",
            "description": "Shows trends and changes over time",
            "best_for": ["time_series", "trend_analysis", "continuous_data"],
            "data_requirements": {
                "min_fields": 2,
                "required_types": ["temporal", "numerical"],
                "max_categories": None
            },
            "features": ["zoom", "pan", "hover", "multi_series"],
            "export_formats": ["png", "pdf", "svg", "html"]
        },
        ChartType.BAR: {
            "name": "Bar Chart",
            "description": "Compares values across categories",
            "best_for": ["categorical_comparison", "ranking", "discrete_data"],
            "data_requirements": {
                "min_fields": 2,
                "required_types": ["categorical", "numerical"],
                "max_categories": 50
            },
            "features": ["sorting", "grouping", "stacking", "hover"],
            "export_formats": ["png", "pdf", "svg", "html"]
        },
        ChartType.PIE: {
            "name": "Pie Chart",
            "description": "Shows part-to-whole relationships",
            "best_for": ["composition", "market_share", "proportions"],
            "data_requirements": {
                "min_fields": 2,
                "required_types": ["categorical", "numerical"],
                "max_categories": 10
            },
            "features": ["explode", "labels", "hover", "rotation"],
            "export_formats": ["png", "pdf", "svg", "html"]
        },
        ChartType.SCATTER: {
            "name": "Scatter Plot",
            "description": "Shows relationships between numerical variables",
            "best_for": ["correlation", "clustering", "outlier_detection"],
            "data_requirements": {
                "min_fields": 2,
                "required_types": ["numerical", "numerical"],
                "max_categories": None
            },
            "features": ["zoom", "pan", "color_grouping", "size_mapping"],
            "export_formats": ["png", "pdf", "svg", "html"]
        },
        ChartType.HISTOGRAM: {
            "name": "Histogram",
            "description": "Shows distribution of numerical data",
            "best_for": ["distribution", "frequency_analysis", "statistical_summary"],
            "data_requirements": {
                "min_fields": 1,
                "required_types": ["numerical"],
                "max_categories": None
            },
            "features": ["bin_adjustment", "overlay", "statistics"],
            "export_formats": ["png", "pdf", "svg", "html"]
        },
        ChartType.HEATMAP: {
            "name": "Heatmap",
            "description": "Shows patterns in multi-dimensional data",
            "best_for": ["correlation_matrix", "intensity_mapping", "pattern_detection"],
            "data_requirements": {
                "min_fields": 3,
                "required_types": ["categorical", "categorical", "numerical"],
                "max_categories": 100
            },
            "features": ["color_scales", "clustering", "annotations"],
            "export_formats": ["png", "pdf", "svg", "html"]
        },
        ChartType.TREEMAP: {
            "name": "Treemap",
            "description": "Shows hierarchical data with nested rectangles",
            "best_for": ["hierarchical_data", "space_efficient", "proportional_comparison"],
            "data_requirements": {
                "min_fields": 2,
                "required_types": ["categorical", "numerical"],
                "max_categories": 1000
            },
            "features": ["drill_down", "color_coding", "hierarchical_navigation"],
            "export_formats": ["png", "pdf", "svg", "html"]
        },
        ChartType.TABLE: {
            "name": "Data Table",
            "description": "Shows raw data in tabular format",
            "best_for": ["detailed_view", "precise_values", "data_exploration"],
            "data_requirements": {
                "min_fields": 1,
                "required_types": ["any"],
                "max_categories": None
            },
            "features": ["sorting", "filtering", "pagination", "search"],
            "export_formats": ["csv", "excel", "pdf", "html"]
        }
    }
    
    return {
        "supported_types": list(ChartType),
        "total_types": len(chart_types_info),
        "chart_types": chart_types_info,
        "selection_algorithm": {
            "version": "1.0",
            "factors": [
                "data_types",
                "field_count",
                "row_count",
                "data_pattern",
                "user_preferences"
            ],
            "confidence_scoring": "Pattern matching with statistical analysis"
        }
    }


# Chart Generation Endpoints (Placeholder for future implementation)

@router.post("/charts/generate", response_model=ChartResponse)
async def generate_chart(
    request: ChartRequest,
    background_tasks: BackgroundTasks
) -> ChartResponse:
    """
    Generate a chart based on data and configuration
    
    Creates an actual chart visualization using the provided data
    and configuration. If no configuration is provided, automatically
    selects the best chart type.
    """
    chart_id = str(uuid.uuid4())
    
    try:
        logger.info("Chart generation request received",
                   chart_id=chart_id,
                   auto_select=request.auto_select,
                   requested_type=request.config.chart_type if request.config else None,
                   data_rows=request.data.total_rows)
        
        # Auto-select chart type if not specified
        if request.auto_select and (not request.config or request.config.chart_type == ChartType.AUTO):
            recommendation = chart_selector.recommend_chart_type(
                data=request.data,
                user_preferences=request.user_preferences
            )
            config = recommendation.config
            logger.info("Auto-selected chart type",
                       chart_id=chart_id,
                       selected_type=config.chart_type,
                       confidence=recommendation.confidence)
        else:
            config = request.config or ChartConfig(chart_type=ChartType.TABLE)
        
        # Generate the actual chart using ChartGenerator
        response = chart_generator.generate_chart(
            data=request.data,
            config=config,
            chart_id=chart_id
        )
        
        logger.info("Chart generation completed",
                   chart_id=chart_id,
                   chart_type=config.chart_type,
                   generation_time=response.generation_time,
                   data_points=request.data.total_rows)
        
        return response
        
    except Exception as e:
        logger.error("Chart generation failed", 
                    chart_id=chart_id, 
                    error=str(e), 
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {str(e)}")


@router.post("/charts/{chart_id}/export")
async def export_chart(
    chart_id: str,
    format: ExportFormat,
    plotly_json: str,
    filename: Optional[str] = None
) -> Response:
    """
    Export a generated chart to specified format
    
    Takes the Plotly JSON representation of a chart and exports it
    to the requested format (PNG, PDF, SVG, HTML, JSON).
    """
    try:
        logger.info("Chart export request received",
                   chart_id=chart_id,
                   export_format=format,
                   filename=filename)
        
        # Reconstruct the Plotly figure from JSON
        fig = go.Figure.from_json(plotly_json)
        
        # Export the chart
        file_bytes, content_type = chart_generator.export_chart(
            fig=fig,
            format=format,
            filename=filename
        )
        
        # Set filename for download
        if not filename:
            extension = format.value
            filename = f"chart_{chart_id}.{extension}"
        
        logger.info("Chart export completed",
                   chart_id=chart_id,
                   export_format=format,
                   file_size=len(file_bytes))
        
        return Response(
            content=file_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_bytes))
            }
        )
        
    except Exception as e:
        logger.error("Chart export failed",
                    chart_id=chart_id,
                    export_format=format,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chart export failed: {str(e)}")


# Dashboard Management Endpoints (Placeholder)

@router.get("/dashboards", response_model=List[Dict[str, Any]])
async def list_dashboards(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of dashboards to return"),
    offset: int = Query(0, ge=0, description="Number of dashboards to skip")
) -> List[Dict[str, Any]]:
    """
    List available dashboards
    
    Returns a list of dashboards accessible to the user with
    pagination support.
    """
    # TODO: Implement actual dashboard listing logic
    # For now, return mock data
    mock_dashboards = [
        {
            "dashboard_id": "dash-001",
            "title": "Security Overview",
            "description": "Security events and trends",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T15:30:00Z",
            "created_by": "user-001",
            "panel_count": 4
        },
        {
            "dashboard_id": "dash-002", 
            "title": "Application Performance",
            "description": "Application metrics and performance",
            "created_at": "2024-01-14T09:00:00Z",
            "updated_at": "2024-01-15T14:20:00Z",
            "created_by": "user-002",
            "panel_count": 6
        }
    ]
    
    # Apply pagination
    start_idx = offset
    end_idx = offset + limit
    
    logger.info("Dashboard list request",
               user_id=user_id,
               limit=limit,
               offset=offset,
               total_available=len(mock_dashboards))
    
    return mock_dashboards[start_idx:end_idx]


# Interactive Chart Endpoints

@router.post("/charts/interactive", response_model=InteractiveChartResponse)
async def create_interactive_chart(
    chart_data: ChartData,
    config: ChartConfig,
    interactive_config: Optional[ChartInteractiveConfig] = None,
    chart_id: Optional[str] = Query(None, description="Chart identifier")
) -> InteractiveChartResponse:
    """
    Create an interactive chart with advanced features
    
    Creates a chart with interactive capabilities including:
    - Data filtering and crossfilter
    - Drill-down functionality
    - Advanced selection modes (brush, lasso)
    - Zoom and pan controls
    """
    try:
        logger.info("Interactive chart creation request",
                   chart_type=config.chart_type,
                   data_rows=chart_data.total_rows,
                   interactive_features=bool(interactive_config))
        
        response = interactive_service.create_interactive_chart(
            data=chart_data,
            config=config,
            interactive_config=interactive_config,
            chart_id=chart_id
        )
        
        logger.info("Interactive chart created successfully",
                   chart_id=response.chart_id,
                   generation_time=response.generation_time)
        
        return response
        
    except Exception as e:
        logger.error("Interactive chart creation failed",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Interactive chart creation failed: {str(e)}")


@router.post("/charts/{chart_id}/interactions")
async def handle_chart_interaction(
    chart_id: str,
    event_type: InteractionType,
    event_data: Dict[str, Any],
    user_id: Optional[str] = Query(None, description="User ID")
) -> Dict[str, Any]:
    """
    Handle chart interaction events
    
    Processes various types of chart interactions including:
    - Click events for drill-down
    - Selection events (brush, lasso)
    - Filter events for data manipulation
    - Zoom and pan events
    """
    try:
        logger.info("Chart interaction event",
                   chart_id=chart_id,
                   event_type=event_type,
                   user_id=user_id)
        
        response = interactive_service.handle_interaction_event(
            chart_id=chart_id,
            event_type=event_type,
            event_data=event_data,
            user_id=user_id
        )
        
        logger.info("Interaction event processed",
                   chart_id=chart_id,
                   event_type=event_type,
                   status=response.get('status'))
        
        return response
        
    except Exception as e:
        logger.error("Interaction event handling failed",
                    chart_id=chart_id,
                    event_type=event_type,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Interaction handling failed: {str(e)}")


@router.post("/charts/linked", response_model=List[InteractiveChartResponse])
async def create_linked_charts(
    chart_configs: List[Dict[str, Any]],
    crossfilter_enabled: bool = Query(True, description="Enable crossfilter linking")
) -> List[InteractiveChartResponse]:
    """
    Create multiple linked charts with crossfilter capabilities
    
    Creates a set of charts that are linked together for crossfilter
    interactions, allowing selections in one chart to filter others.
    """
    try:
        logger.info("Linked charts creation request",
                   chart_count=len(chart_configs),
                   crossfilter_enabled=crossfilter_enabled)
        
        # Parse chart configurations
        parsed_configs = []
        for config_data in chart_configs:
            chart_data = ChartData(**config_data['data'])
            chart_config = ChartConfig(**config_data['config'])
            parsed_configs.append((chart_data, chart_config))
        
        charts = interactive_service.create_linked_charts(
            chart_configs=parsed_configs,
            crossfilter_enabled=crossfilter_enabled
        )
        
        logger.info("Linked charts created successfully",
                   chart_count=len(charts))
        
        return charts
        
    except Exception as e:
        logger.error("Linked charts creation failed",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Linked charts creation failed: {str(e)}")


@router.get("/charts/{chart_id}/state")
async def get_chart_state(chart_id: str) -> Dict[str, Any]:
    """
    Get current state of an interactive chart
    
    Returns the current interaction state including:
    - Active selections
    - Applied filters
    - Zoom/pan state
    - Linked chart information
    """
    try:
        state = interactive_service.get_chart_state(chart_id)
        
        logger.info("Chart state retrieved",
                   chart_id=chart_id,
                   has_selection=state.get('has_selection', False))
        
        return state
        
    except Exception as e:
        logger.error("Chart state retrieval failed",
                    chart_id=chart_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chart state retrieval failed: {str(e)}")


@router.delete("/charts/{chart_id}/state")
async def clear_chart_state(chart_id: str) -> Dict[str, str]:
    """
    Clear stored state for an interactive chart
    
    Removes all stored interaction state including selections,
    filters, and cached data for the specified chart.
    """
    try:
        interactive_service.clear_chart_state(chart_id)
        
        logger.info("Chart state cleared", chart_id=chart_id)
        
        return {
            "status": "success",
            "message": f"State cleared for chart {chart_id}",
            "chart_id": chart_id
        }
        
    except Exception as e:
        logger.error("Chart state clearing failed",
                    chart_id=chart_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chart state clearing failed: {str(e)}")


@router.post("/charts/{chart_id}/filters")
async def apply_chart_filters(
    chart_id: str,
    filters: List[ChartFilter],
    chart_data: ChartData,
    config: ChartConfig
) -> InteractiveChartResponse:
    """
    Apply filters to a chart and regenerate
    
    Applies the specified filters to the chart data and
    returns an updated interactive chart with filtered data.
    """
    try:
        logger.info("Applying chart filters",
                   chart_id=chart_id,
                   filter_count=len(filters))
        
        # Create interactive config with filters
        interactive_config = ChartInteractiveConfig(filters=filters)
        
        response = interactive_service.create_interactive_chart(
            data=chart_data,
            config=config,
            interactive_config=interactive_config,
            chart_id=chart_id
        )
        
        logger.info("Chart filters applied successfully",
                   chart_id=chart_id,
                   filter_count=len(filters))
        
        return response
        
    except Exception as e:
        logger.error("Chart filter application failed",
                    chart_id=chart_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chart filter application failed: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for visualization service"""
    return {
        "status": "healthy",
        "service": "visualization",
        "version": settings.app_version,
        "capabilities": {
            "chart_types": len(ChartType),
            "auto_selection": True,
            "dashboard_management": True,
            "export_formats": ["png", "pdf", "svg", "html"],
            "interactive_features": {
                "filtering": True,
                "drill_down": True,
                "crossfilter": True,
                "brush_selection": True,
                "lasso_selection": True,
                "zoom_pan": True,
                "linked_charts": True
            },
            "customization_features": {
                "themes": True,
                "fonts": True,
                "colors": True,
                "templates": True,
                "annotations": True,
                "axis_customization": True,
                "legend_customization": True
            }
        },
        "timestamp": time.time()
    }


# Chart Customization Endpoints

@router.post("/charts/customize", response_model=ChartResponse)
async def customize_chart(
    chart_data: ChartData,
    config: ChartConfig,
    customization: ChartCustomization,
    chart_id: Optional[str] = Query(None, description="Chart identifier")
) -> ChartResponse:
    """
    Generate a chart with advanced customization options
    
    Creates a chart with comprehensive customization including:
    - Theme and color scheme configuration
    - Font and typography customization
    - Axis, legend, and grid styling
    - Custom annotations and styling
    """
    try:
        logger.info("Customized chart generation request",
                   chart_type=config.chart_type,
                   theme=customization.theme,
                   font_family=customization.font_family)
        
        # Apply customization to config
        config.customization = customization
        
        # Generate the chart
        response = chart_generator.generate_chart(
            data=chart_data,
            config=config,
            chart_id=chart_id
        )
        
        logger.info("Customized chart created successfully",
                   chart_id=response.chart_id,
                   generation_time=response.generation_time)
        
        return response
        
    except Exception as e:
        logger.error("Customized chart generation failed",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Customized chart generation failed: {str(e)}")


@router.get("/charts/templates", response_model=List[ChartTemplate])
async def get_chart_templates() -> List[ChartTemplate]:
    """
    Get available chart templates
    
    Returns a list of predefined chart templates with their
    customization settings and metadata.
    """
    try:
        customization_service = chart_generator.get_customization_service()
        templates = customization_service.list_templates()
        
        logger.info("Chart templates retrieved",
                   template_count=len(templates))
        
        return templates
        
    except Exception as e:
        logger.error("Failed to retrieve chart templates",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve templates: {str(e)}")


@router.get("/charts/templates/{template_name}", response_model=ChartTemplate)
async def get_chart_template(template_name: str) -> ChartTemplate:
    """
    Get a specific chart template by name
    
    Returns the template configuration and metadata
    for the specified template name.
    """
    try:
        customization_service = chart_generator.get_customization_service()
        template = customization_service.get_template(template_name)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        logger.info("Chart template retrieved",
                   template_name=template_name)
        
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve chart template",
                    template_name=template_name,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve template: {str(e)}")


@router.post("/charts/templates", response_model=ChartTemplate)
async def create_chart_template(template: ChartTemplate) -> ChartTemplate:
    """
    Create a new chart template
    
    Creates a new chart template with the specified
    customization settings and metadata.
    """
    try:
        customization_service = chart_generator.get_customization_service()
        
        # Validate customization
        warnings = customization_service.validate_customization(template.customization)
        if warnings:
            logger.warning("Template validation warnings",
                          template_name=template.name,
                          warnings=warnings)
        
        created_template = customization_service.create_template(template)
        
        logger.info("Chart template created",
                   template_name=template.name,
                   template_description=template.description)
        
        return created_template
        
    except Exception as e:
        logger.error("Failed to create chart template",
                    template_name=template.name,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.post("/charts/from-template", response_model=ChartResponse)
async def create_chart_from_template(
    chart_data: ChartData,
    config: ChartConfig,
    template_name: str,
    chart_id: Optional[str] = Query(None, description="Chart identifier")
) -> ChartResponse:
    """
    Create a chart using a predefined template
    
    Generates a chart using the specified template's
    customization settings applied to the given data and config.
    """
    try:
        customization_service = chart_generator.get_customization_service()
        template = customization_service.get_template(template_name)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        logger.info("Chart generation from template",
                   template_name=template_name,
                   chart_type=config.chart_type)
        
        # Apply template to config
        config.template = template_name
        
        # Generate the chart
        response = chart_generator.generate_chart(
            data=chart_data,
            config=config,
            chart_id=chart_id
        )
        
        logger.info("Chart created from template successfully",
                   chart_id=response.chart_id,
                   template_name=template_name,
                   generation_time=response.generation_time)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create chart from template",
                    template_name=template_name,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create chart from template: {str(e)}")


@router.post("/charts/customization/validate")
async def validate_chart_customization(customization: ChartCustomization) -> Dict[str, Any]:
    """
    Validate chart customization configuration
    
    Validates the provided customization configuration and
    returns any warnings or validation errors.
    """
    try:
        customization_service = chart_generator.get_customization_service()
        warnings = customization_service.validate_customization(customization)
        
        return {
            "valid": len(warnings) == 0,
            "warnings": warnings,
            "customization_summary": {
                "theme": customization.theme,
                "font_family": customization.font_family,
                "font_size": customization.font_size,
                "has_title": customization.title is not None,
                "has_legend": customization.legend is not None,
                "has_grid": customization.grid is not None,
                "has_annotations": len(customization.annotations) > 0,
                "has_custom_axes": customization.x_axis is not None or customization.y_axis is not None
            }
        }
        
    except Exception as e:
        logger.error("Failed to validate customization",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate customization: {str(e)}")


@router.get("/charts/customization/options")
async def get_customization_options() -> Dict[str, Any]:
    """
    Get available customization options
    
    Returns comprehensive information about available
    customization options including themes, fonts, colors, etc.
    """
    try:
        customization_service = chart_generator.get_customization_service()
        
        return {
            "themes": [theme.value for theme in ChartTheme],
            "font_families": [font.value for font in FontFamily],
            "color_schemes": [scheme.value for scheme in ColorScheme],
            "legend_positions": [pos.value for pos in LegendPosition],
            "theme_configs": customization_service.theme_configs,
            "color_palettes": {
                scheme.value: customization_service.get_color_palette(scheme, 10)
                for scheme in ColorScheme
            },
            "default_templates": [template.name for template in customization_service.list_templates()]
        }
        
    except Exception as e:
        logger.error("Failed to get customization options",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get customization options: {str(e)}")