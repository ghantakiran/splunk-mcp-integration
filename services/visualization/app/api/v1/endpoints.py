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
    ChartTheme, FontFamily, ColorScheme, LegendPosition, ExportConfig,
    ExportResult, ExportQuality, ExportOrientation, ExportTemplate,
    BatchExportRequest, BatchExportResult, DashboardCreateRequest,
    DashboardUpdateRequest, PanelCreateRequest, PanelUpdateRequest,
    DashboardResponse, DashboardListResponse, LayoutType, PanelType,
    DashboardGridPosition, DashboardLayoutConfig, DashboardTemplate,
    BreakpointSize
)
from ...services.chart_selector import ChartTypeSelector
from ...services.chart_generator import ChartGenerator
from ...services.interactive_charts import InteractiveChartService
from ...services.dashboard_layout import DashboardLayoutEngine
from ...core.logging import get_logger, log_chart_generation
from ...core.config import settings

logger = get_logger(__name__)
router = APIRouter()

# Initialize services
chart_selector = ChartTypeSelector()
chart_generator = ChartGenerator()
interactive_service = InteractiveChartService()
dashboard_engine = DashboardLayoutEngine()


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
    Export a generated chart to specified format (legacy endpoint)
    
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
        
        # Export the chart using legacy method
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


@router.post("/charts/{chart_id}/export-advanced", response_model=ExportResult)
async def export_chart_advanced(
    chart_id: str,
    plotly_json: str,
    config: ExportConfig,
    filename: Optional[str] = None
) -> ExportResult:
    """
    Export a generated chart with advanced configuration options
    
    Takes the Plotly JSON representation of a chart and exports it
    with comprehensive configuration options including quality settings,
    templates, optimization, and format-specific features.
    """
    try:
        logger.info("Advanced chart export request received",
                   chart_id=chart_id,
                   export_format=config.format,
                   quality=config.quality,
                   template=config.template,
                   filename=filename)
        
        # Reconstruct the Plotly figure from JSON
        fig = go.Figure.from_json(plotly_json)
        
        # Export the chart using advanced method
        result = chart_generator.export_chart_advanced(
            fig=fig,
            config=config,
            chart_id=chart_id,
            filename=filename
        )
        
        logger.info("Advanced chart export completed",
                   chart_id=chart_id,
                   export_id=result.export_id,
                   export_format=config.format,
                   file_size=result.file_size,
                   export_time=result.export_time)
        
        return result
        
    except Exception as e:
        logger.error("Advanced chart export failed",
                    chart_id=chart_id,
                    export_format=config.format,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Advanced chart export failed: {str(e)}")


@router.post("/charts/{chart_id}/export-advanced/download")
async def download_advanced_export(
    chart_id: str,
    plotly_json: str,
    config: ExportConfig,
    filename: Optional[str] = None
) -> Response:
    """
    Export and download a chart with advanced configuration options
    
    Similar to export_chart_advanced but returns the file directly
    for download instead of metadata.
    """
    try:
        logger.info("Advanced chart export download request received",
                   chart_id=chart_id,
                   export_format=config.format,
                   quality=config.quality,
                   template=config.template)
        
        # Reconstruct the Plotly figure from JSON
        fig = go.Figure.from_json(plotly_json)
        
        # Export the chart using advanced method
        result = chart_generator.export_chart_advanced(
            fig=fig,
            config=config,
            chart_id=chart_id,
            filename=filename
        )
        
        # Get the file bytes (this would be implemented in the service)
        # For now, we'll use the legacy method to get the actual bytes
        file_bytes, content_type = chart_generator.export_chart(
            fig=fig,
            format=config.format,
            filename=result.filename
        )
        
        logger.info("Advanced chart export download completed",
                   chart_id=chart_id,
                   export_id=result.export_id,
                   file_size=len(file_bytes))
        
        return Response(
            content=file_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={result.filename}",
                "Content-Length": str(len(file_bytes)),
                "X-Export-ID": result.export_id,
                "X-Export-Time": str(result.export_time)
            }
        )
        
    except Exception as e:
        logger.error("Advanced chart export download failed",
                    chart_id=chart_id,
                    export_format=config.format,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Advanced chart export download failed: {str(e)}")


@router.post("/charts/batch-export", response_model=BatchExportResult)
async def batch_export_charts(
    request: BatchExportRequest,
    background_tasks: BackgroundTasks
) -> BatchExportResult:
    """
    Export multiple charts in batch with archiving
    
    Processes multiple charts for export using the same configuration
    and creates an archive file containing all exported charts.
    """
    try:
        logger.info("Batch export request received",
                   chart_count=len(request.charts),
                   export_format=request.format,
                   archive_format=request.archive_format)
        
        # Process batch export using the export service
        # This would be implemented in the chart generator's export service
        result = chart_generator.batch_export_charts(request)
        
        logger.info("Batch export completed",
                   batch_id=result.batch_id,
                   successful_exports=result.successful_exports,
                   failed_exports=result.failed_exports,
                   processing_time=result.processing_time)
        
        return result
        
    except Exception as e:
        logger.error("Batch export failed",
                    chart_count=len(request.charts),
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch export failed: {str(e)}")


@router.get("/charts/export/formats", response_model=List[Dict[str, Any]])
async def get_export_formats() -> List[Dict[str, Any]]:
    """
    Get available export formats with their capabilities
    
    Returns comprehensive information about supported export formats
    including their features, use cases, and technical specifications.
    """
    try:
        export_service = chart_generator.get_export_service()
        formats = export_service.get_export_formats()
        
        logger.info("Export formats retrieved",
                   format_count=len(formats))
        
        return formats
        
    except Exception as e:
        logger.error("Failed to retrieve export formats",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve export formats: {str(e)}")


@router.get("/charts/export/quality-options", response_model=List[Dict[str, Any]])
async def get_export_quality_options() -> List[Dict[str, Any]]:
    """
    Get available export quality options
    
    Returns information about quality levels including their
    performance characteristics and use cases.
    """
    try:
        export_service = chart_generator.get_export_service()
        quality_options = export_service.get_quality_options()
        
        logger.info("Export quality options retrieved",
                   option_count=len(quality_options))
        
        return quality_options
        
    except Exception as e:
        logger.error("Failed to retrieve export quality options",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve quality options: {str(e)}")


@router.get("/charts/export/templates", response_model=List[Dict[str, Any]])
async def get_export_templates() -> List[Dict[str, Any]]:
    """
    Get available export templates
    
    Returns information about export templates including their
    dimensions, DPI settings, and intended use cases.
    """
    try:
        export_service = chart_generator.get_export_service()
        templates = export_service.get_template_options()
        
        logger.info("Export templates retrieved",
                   template_count=len(templates))
        
        return templates
        
    except Exception as e:
        logger.error("Failed to retrieve export templates",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve export templates: {str(e)}")


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
            "export_formats": ["png", "pdf", "svg", "html", "json", "jpeg", "webp"],
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
            },
            "export_features": {
                "advanced_export": True,
                "batch_export": True,
                "quality_levels": ["low", "medium", "high", "ultra"],
                "export_templates": ["presentation", "print", "web", "social", "report"],
                "optimization": True,
                "format_specific_features": {
                    "png": ["transparency", "compression"],
                    "jpeg": ["quality", "progressive"],
                    "webp": ["quality", "compression"],
                    "pdf": ["vector_graphics", "high_dpi"],
                    "svg": ["scalable", "embed_fonts"],
                    "html": ["interactive", "responsive"],
                    "json": ["metadata", "programmatic_access"]
                }
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


# Dashboard Layout Endpoints

@router.post("/dashboards", response_model=DashboardResponse)
async def create_dashboard(request: DashboardCreateRequest) -> DashboardResponse:
    """
    Create a new dashboard with optional template
    
    Creates a new dashboard with the specified layout type and
    optionally applies a predefined template for initial configuration.
    """
    try:
        logger.info("Creating dashboard",
                   title=request.title,
                   layout_type=request.layout_type,
                   template_name=request.template_name)
        
        # Convert Pydantic enum to dashboard engine enum
        from ...services.dashboard_layout import LayoutType as DashboardLayoutType
        layout_type = DashboardLayoutType(request.layout_type.value)
        
        dashboard = dashboard_engine.create_dashboard(
            title=request.title,
            description=request.description or "",
            layout_type=layout_type,
            template_name=request.template_name,
            created_by=request.created_by
        )
        
        # Convert to Pydantic model
        dashboard_dict = dashboard.to_dict()
        
        # Convert back to Pydantic models
        from ...services.dashboard_layout import LayoutType as DashboardLayoutType
        pydantic_dashboard = Dashboard(
            dashboard_id=dashboard_dict['id'],
            title=dashboard_dict['title'],
            description=dashboard_dict['description'],
            layout_config=DashboardLayoutConfig(
                layout_type=LayoutType(dashboard_dict['layout_config']['layout_type']),
                columns=dashboard_dict['layout_config']['columns'],
                row_height=dashboard_dict['layout_config']['row_height'],
                margin=dashboard_dict['layout_config']['margin'],
                padding=dashboard_dict['layout_config']['padding'],
                auto_size=dashboard_dict['layout_config']['auto_size'],
                compact_type=dashboard_dict['layout_config']['compact_type'],
                prevent_collision=dashboard_dict['layout_config']['prevent_collision'],
                use_css_transforms=dashboard_dict['layout_config']['use_css_transforms'],
                breakpoints=dashboard_dict['layout_config']['breakpoints'],
                breakpoint_columns=dashboard_dict['layout_config']['breakpoint_columns']
            ),
            panels=[],
            global_filters=dashboard_dict['global_filters'],
            theme=dashboard_dict['theme'],
            auto_refresh=dashboard_dict['auto_refresh'],
            refresh_interval=dashboard_dict['refresh_interval'],
            created_at=dashboard_dict['created_at'],
            updated_at=dashboard_dict['updated_at'],
            created_by=dashboard_dict['created_by']
        )
        
        response = DashboardResponse(
            dashboard=pydantic_dashboard,
            panel_count=len(dashboard.panels),
            total_size=len(str(dashboard_dict)),
            last_modified=dashboard.updated_at,
            can_edit=True,
            can_share=True
        )
        
        logger.info("Dashboard created successfully",
                   dashboard_id=dashboard.id,
                   panel_count=len(dashboard.panels))
        
        return response
        
    except Exception as e:
        logger.error("Dashboard creation failed",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard creation failed: {str(e)}")


@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(dashboard_id: str) -> DashboardResponse:
    """
    Get a specific dashboard by ID
    
    Returns the complete dashboard configuration including
    layout, panels, and metadata.
    """
    try:
        # In a real implementation, this would retrieve from storage
        # For now, we'll return a mock response
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Dashboard retrieval failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard retrieval failed: {str(e)}")


@router.put("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(dashboard_id: str, request: DashboardUpdateRequest) -> DashboardResponse:
    """
    Update an existing dashboard
    
    Updates the dashboard configuration with the provided changes.
    Only specified fields will be updated.
    """
    try:
        # In a real implementation, this would update the dashboard in storage
        # For now, we'll return a mock response
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Dashboard update failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard update failed: {str(e)}")


@router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(dashboard_id: str) -> Dict[str, str]:
    """
    Delete a dashboard
    
    Permanently deletes the dashboard and all its panels.
    """
    try:
        # In a real implementation, this would delete from storage
        logger.info("Dashboard deleted", dashboard_id=dashboard_id)
        
        return {
            "status": "success",
            "message": f"Dashboard {dashboard_id} deleted successfully",
            "dashboard_id": dashboard_id
        }
        
    except Exception as e:
        logger.error("Dashboard deletion failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard deletion failed: {str(e)}")


@router.post("/dashboards/{dashboard_id}/panels", response_model=DashboardPanel)
async def add_panel(dashboard_id: str, request: PanelCreateRequest) -> DashboardPanel:
    """
    Add a new panel to a dashboard
    
    Creates a new panel and adds it to the specified dashboard.
    Panel position is auto-calculated if not provided.
    """
    try:
        logger.info("Adding panel to dashboard",
                   dashboard_id=dashboard_id,
                   panel_type=request.panel_type,
                   title=request.title)
        
        # In a real implementation, this would:
        # 1. Retrieve the dashboard
        # 2. Create the panel using dashboard_engine.add_panel()
        # 3. Save the updated dashboard
        # 4. Return the created panel
        
        # For now, create a mock panel
        panel_id = str(uuid.uuid4())
        position = request.position or DashboardGridPosition(x=0, y=0, width=6, height=4)
        
        panel = DashboardPanel(
            panel_id=panel_id,
            panel_type=request.panel_type,
            title=request.title,
            position=position,
            content=request.content or {},
            style=request.style or {},
            chart_config=request.chart_config,
            query=request.query
        )
        
        logger.info("Panel added successfully",
                   dashboard_id=dashboard_id,
                   panel_id=panel_id)
        
        return panel
        
    except Exception as e:
        logger.error("Panel addition failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel addition failed: {str(e)}")


@router.put("/dashboards/{dashboard_id}/panels/{panel_id}", response_model=DashboardPanel)
async def update_panel(
    dashboard_id: str,
    panel_id: str,
    request: PanelUpdateRequest
) -> DashboardPanel:
    """
    Update an existing panel
    
    Updates the panel configuration with the provided changes.
    Only specified fields will be updated.
    """
    try:
        logger.info("Updating panel",
                   dashboard_id=dashboard_id,
                   panel_id=panel_id)
        
        # In a real implementation, this would:
        # 1. Retrieve the dashboard
        # 2. Update the panel using dashboard_engine.update_panel()
        # 3. Save the updated dashboard
        # 4. Return the updated panel
        
        raise HTTPException(status_code=404, detail="Panel not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Panel update failed",
                    dashboard_id=dashboard_id,
                    panel_id=panel_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel update failed: {str(e)}")


@router.delete("/dashboards/{dashboard_id}/panels/{panel_id}")
async def remove_panel(dashboard_id: str, panel_id: str) -> Dict[str, str]:
    """
    Remove a panel from a dashboard
    
    Removes the specified panel from the dashboard.
    """
    try:
        logger.info("Removing panel from dashboard",
                   dashboard_id=dashboard_id,
                   panel_id=panel_id)
        
        # In a real implementation, this would:
        # 1. Retrieve the dashboard
        # 2. Remove the panel using dashboard_engine.remove_panel()
        # 3. Save the updated dashboard
        
        return {
            "status": "success",
            "message": f"Panel {panel_id} removed from dashboard {dashboard_id}",
            "dashboard_id": dashboard_id,
            "panel_id": panel_id
        }
        
    except Exception as e:
        logger.error("Panel removal failed",
                    dashboard_id=dashboard_id,
                    panel_id=panel_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel removal failed: {str(e)}")


@router.post("/dashboards/{dashboard_id}/panels/{panel_id}/move")
async def move_panel(
    dashboard_id: str,
    panel_id: str,
    new_position: DashboardGridPosition
) -> DashboardPanel:
    """
    Move a panel to a new position
    
    Moves the specified panel to a new position within the dashboard grid.
    """
    try:
        logger.info("Moving panel",
                   dashboard_id=dashboard_id,
                   panel_id=panel_id,
                   new_position=new_position.dict())
        
        # In a real implementation, this would:
        # 1. Retrieve the dashboard
        # 2. Move the panel using dashboard_engine.move_panel()
        # 3. Save the updated dashboard
        # 4. Return the updated panel
        
        raise HTTPException(status_code=404, detail="Panel not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Panel move failed",
                    dashboard_id=dashboard_id,
                    panel_id=panel_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel move failed: {str(e)}")


@router.post("/dashboards/{dashboard_id}/panels/{panel_id}/resize")
async def resize_panel(
    dashboard_id: str,
    panel_id: str,
    new_width: int,
    new_height: int
) -> DashboardPanel:
    """
    Resize a panel
    
    Changes the size of the specified panel within the dashboard grid.
    """
    try:
        logger.info("Resizing panel",
                   dashboard_id=dashboard_id,
                   panel_id=panel_id,
                   new_width=new_width,
                   new_height=new_height)
        
        # In a real implementation, this would:
        # 1. Retrieve the dashboard
        # 2. Resize the panel using dashboard_engine.resize_panel()
        # 3. Save the updated dashboard
        # 4. Return the updated panel
        
        raise HTTPException(status_code=404, detail="Panel not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Panel resize failed",
                    dashboard_id=dashboard_id,
                    panel_id=panel_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel resize failed: {str(e)}")


@router.post("/dashboards/{dashboard_id}/optimize")
async def optimize_dashboard_layout(dashboard_id: str) -> DashboardResponse:
    """
    Optimize dashboard layout
    
    Optimizes the dashboard layout for better visual arrangement,
    including auto-compacting panels and responsive optimization.
    """
    try:
        logger.info("Optimizing dashboard layout", dashboard_id=dashboard_id)
        
        # In a real implementation, this would:
        # 1. Retrieve the dashboard
        # 2. Optimize using dashboard_engine.optimize_layout()
        # 3. Save the optimized dashboard
        # 4. Return the updated dashboard
        
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Dashboard layout optimization failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard layout optimization failed: {str(e)}")


@router.get("/dashboards/{dashboard_id}/layout/{breakpoint}")
async def get_dashboard_layout_for_breakpoint(
    dashboard_id: str,
    breakpoint: BreakpointSize
) -> List[Dict[str, Any]]:
    """
    Get dashboard layout for specific breakpoint
    
    Returns the optimized layout configuration for the specified
    responsive breakpoint size.
    """
    try:
        logger.info("Getting dashboard layout for breakpoint",
                   dashboard_id=dashboard_id,
                   breakpoint=breakpoint)
        
        # In a real implementation, this would:
        # 1. Retrieve the dashboard
        # 2. Get layout using dashboard_engine.get_layout_for_breakpoint()
        # 3. Return the layout configuration
        
        # For now, return empty layout
        return []
        
    except Exception as e:
        logger.error("Dashboard layout retrieval failed",
                    dashboard_id=dashboard_id,
                    breakpoint=breakpoint,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard layout retrieval failed: {str(e)}")


@router.get("/dashboard-templates", response_model=List[DashboardTemplate])
async def get_dashboard_templates() -> List[DashboardTemplate]:
    """
    Get available dashboard templates
    
    Returns a list of predefined dashboard templates with their
    layout configurations and sample panels.
    """
    try:
        logger.info("Getting dashboard templates")
        
        # For now, return empty list
        # In a real implementation, this would return available templates
        return []
        
    except Exception as e:
        logger.error("Dashboard template retrieval failed",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard template retrieval failed: {str(e)}")


@router.post("/dashboard-templates", response_model=DashboardTemplate)
async def create_dashboard_template(template: DashboardTemplate) -> DashboardTemplate:
    """
    Create a new dashboard template
    
    Creates a new dashboard template that can be used to
    quickly create dashboards with predefined layouts.
    """
    try:
        logger.info("Creating dashboard template",
                   template_name=template.name,
                   category=template.category)
        
        # In a real implementation, this would:
        # 1. Validate the template
        # 2. Save to template storage
        # 3. Return the created template
        
        return template
        
    except Exception as e:
        logger.error("Dashboard template creation failed",
                    template_name=template.name,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard template creation failed: {str(e)}")


@router.get("/layout/types")
async def get_layout_types() -> Dict[str, Any]:
    """
    Get available layout types and their configurations
    
    Returns information about supported layout types and
    their default configurations.
    """
    try:
        return {
            "layout_types": [layout_type.value for layout_type in LayoutType],
            "panel_types": [panel_type.value for panel_type in PanelType],
            "breakpoint_sizes": [size.value for size in BreakpointSize],
            "default_configurations": {
                "grid": {
                    "columns": 12,
                    "row_height": 30,
                    "margin": [10, 10],
                    "padding": [5, 5],
                    "auto_size": True,
                    "compact_type": "vertical",
                    "prevent_collision": True
                },
                "responsive": {
                    "breakpoints": {
                        "xl": 1200,
                        "lg": 996,
                        "md": 768,
                        "sm": 576,
                        "xs": 0
                    },
                    "breakpoint_columns": {
                        "xl": 12,
                        "lg": 12,
                        "md": 10,
                        "sm": 6,
                        "xs": 4
                    }
                }
            }
        }
        
    except Exception as e:
        logger.error("Layout types retrieval failed",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Layout types retrieval failed: {str(e)}")