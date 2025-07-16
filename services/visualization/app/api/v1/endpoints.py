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
from ...services.dashboard_builder import (
    DashboardBuilderService, DragOperation, ResizeOperation, 
    PanelConfiguration, CollaborationEvent
)
from ...core.logging import get_logger, log_chart_generation
from ...core.config import settings

logger = get_logger(__name__)
router = APIRouter()

# Initialize services
chart_selector = ChartTypeSelector()
chart_generator = ChartGenerator()
interactive_service = InteractiveChartService()
dashboard_engine = DashboardLayoutEngine()
dashboard_builder = DashboardBuilderService()


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


# Dashboard Builder Endpoints

@router.post("/builder/sessions", response_model=Dict[str, Any])
async def create_builder_session(
    dashboard_id: str = Query(..., description="Dashboard identifier"),
    user_id: str = Query(..., description="User identifier")
) -> Dict[str, Any]:
    """
    Create a new dashboard builder session for collaborative editing
    
    Creates a new session for the dashboard builder, enabling real-time
    collaboration and state management.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService
        builder_service = DashboardBuilderService()
        
        session = builder_service.create_builder_session(dashboard_id, user_id)
        
        logger.info("Builder session created",
                   session_id=session["session"]["session_id"],
                   dashboard_id=dashboard_id,
                   user_id=user_id)
        
        return session
        
    except Exception as e:
        logger.error("Builder session creation failed",
                    dashboard_id=dashboard_id,
                    user_id=user_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Builder session creation failed: {str(e)}")


@router.post("/builder/drag", response_model=Dict[str, Any])
async def handle_drag_operation(
    operation: "DragEvent"  # Forward reference to avoid circular import
) -> Dict[str, Any]:
    """
    Handle drag-and-drop operations for dashboard panels
    
    Processes drag events including move, resize, add, and remove operations
    with collision detection and layout validation.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService, DragOperation
        builder_service = DashboardBuilderService()
        
        # Convert DragEvent to DragOperation
        drag_op = DragOperation(
            panel_id=operation.panel_id,
            source_position=operation.source_position,
            target_position=operation.target_position,
            dashboard_id=operation.dashboard_id,
            operation_type=operation.operation.value
        )
        
        result = builder_service.handle_drag_operation(drag_op)
        
        logger.info("Drag operation processed",
                   operation_type=operation.operation.value,
                   panel_id=operation.panel_id,
                   success=result["success"])
        
        return result
        
    except Exception as e:
        logger.error("Drag operation failed",
                    operation=operation.dict(),
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Drag operation failed: {str(e)}")


@router.post("/builder/resize", response_model=Dict[str, Any])
async def handle_resize_operation(
    operation: "ResizeEvent"  # Forward reference
) -> Dict[str, Any]:
    """
    Handle panel resize operations with collision detection
    
    Processes panel resize events with automatic collision resolution
    and layout optimization.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService, ResizeOperation
        builder_service = DashboardBuilderService()
        
        # Convert ResizeEvent to ResizeOperation
        resize_op = ResizeOperation(
            panel_id=operation.panel_id,
            dashboard_id=operation.dashboard_id,
            new_width=operation.new_dimensions["width"],
            new_height=operation.new_dimensions["height"],
            maintain_aspect_ratio=operation.maintain_aspect_ratio
        )
        
        result = builder_service.handle_resize_operation(resize_op)
        
        logger.info("Resize operation processed",
                   panel_id=operation.panel_id,
                   new_dimensions=operation.new_dimensions,
                   success=result["success"])
        
        return result
        
    except Exception as e:
        logger.error("Resize operation failed",
                    operation=operation.dict(),
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resize operation failed: {str(e)}")


@router.post("/builder/panels/add", response_model=Dict[str, Any])
async def add_panel_to_dashboard(
    request: "AddPanelRequest"  # Forward reference
) -> Dict[str, Any]:
    """
    Add a new panel to the dashboard with automatic positioning
    
    Creates a new panel and adds it to the dashboard with optimal
    positioning and collision avoidance.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService, PanelConfiguration
        builder_service = DashboardBuilderService()
        
        # Create panel configuration
        panel_config = PanelConfiguration(
            panel_id=str(uuid.uuid4()),
            panel_type=request.panel_type,
            title=request.title,
            chart_type=None,  # Will be set based on configuration
            data_source=request.configuration.get("data_source"),
            query=request.configuration.get("query"),
            styling=request.configuration.get("styling", {}),
            interactions=request.configuration.get("interactions", {})
        )
        
        result = builder_service.add_panel_to_dashboard(
            request.dashboard_id,
            panel_config,
            request.position
        )
        
        logger.info("Panel added to dashboard",
                   dashboard_id=request.dashboard_id,
                   panel_id=panel_config.panel_id,
                   panel_type=request.panel_type.value,
                   success=result["success"])
        
        return result
        
    except Exception as e:
        logger.error("Add panel operation failed",
                    request=request.dict(),
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Add panel operation failed: {str(e)}")


@router.delete("/builder/panels/{panel_id}", response_model=Dict[str, Any])
async def remove_panel_from_dashboard(
    panel_id: str,
    dashboard_id: str = Query(..., description="Dashboard identifier"),
    optimize_layout: bool = Query(True, description="Optimize layout after removal")
) -> Dict[str, Any]:
    """
    Remove a panel from the dashboard and optionally optimize layout
    
    Removes the specified panel and can automatically optimize
    the remaining layout to close gaps.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService
        builder_service = DashboardBuilderService()
        
        result = builder_service.remove_panel_from_dashboard(
            dashboard_id,
            panel_id,
            optimize_layout
        )
        
        logger.info("Panel removed from dashboard",
                   dashboard_id=dashboard_id,
                   panel_id=panel_id,
                   layout_optimized=optimize_layout,
                   success=result["success"])
        
        return result
        
    except Exception as e:
        logger.error("Remove panel operation failed",
                    panel_id=panel_id,
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Remove panel operation failed: {str(e)}")


@router.put("/builder/panels/{panel_id}", response_model=Dict[str, Any])
async def update_panel_configuration(
    panel_id: str,
    request: "UpdatePanelRequest"  # Forward reference
) -> Dict[str, Any]:
    """
    Update panel configuration without changing layout
    
    Updates panel settings, styling, and behavior without
    affecting its position or size.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService
        builder_service = DashboardBuilderService()
        
        # Update title if provided
        config_updates = request.configuration.copy()
        if request.title:
            config_updates["title"] = request.title
        
        result = builder_service.update_panel_configuration(
            request.dashboard_id,
            panel_id,
            config_updates
        )
        
        logger.info("Panel configuration updated",
                   dashboard_id=request.dashboard_id,
                   panel_id=panel_id,
                   updates=list(config_updates.keys()),
                   success=result["success"])
        
        return result
        
    except Exception as e:
        logger.error("Update panel configuration failed",
                    panel_id=panel_id,
                    request=request.dict(),
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Update panel configuration failed: {str(e)}")


@router.post("/builder/templates/{template_name}/create", response_model=Dict[str, Any])
async def create_dashboard_from_template(
    template_name: str,
    dashboard_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new dashboard based on a predefined template
    
    Creates a complete dashboard from a template with automatic
    panel placement and configuration.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService
        builder_service = DashboardBuilderService()
        
        result = builder_service.create_dashboard_from_template(
            template_name,
            dashboard_config
        )
        
        logger.info("Dashboard created from template",
                   template_name=template_name,
                   dashboard_id=result.get("dashboard", {}).get("id"),
                   success=result["success"])
        
        return result
        
    except Exception as e:
        logger.error("Template dashboard creation failed",
                    template_name=template_name,
                    dashboard_config=dashboard_config,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Template dashboard creation failed: {str(e)}")


@router.get("/builder/collaboration/{dashboard_id}", response_model=Dict[str, Any])
async def get_collaboration_state(dashboard_id: str) -> Dict[str, Any]:
    """
    Get current collaboration state for a dashboard
    
    Returns information about active users, recent events,
    and collaboration status for the dashboard.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService
        builder_service = DashboardBuilderService()
        
        state = builder_service.get_collaboration_state(dashboard_id)
        
        logger.info("Collaboration state retrieved",
                   dashboard_id=dashboard_id,
                   active_users=len(state["active_users"]),
                   collaboration_enabled=state["collaboration_enabled"])
        
        return state
        
    except Exception as e:
        logger.error("Collaboration state retrieval failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Collaboration state retrieval failed: {str(e)}")


@router.post("/builder/undo/{dashboard_id}", response_model=Dict[str, Any])
async def undo_last_operation(dashboard_id: str) -> Dict[str, Any]:
    """
    Undo the last operation on a dashboard
    
    Reverts the most recent change to the dashboard layout
    or panel configuration.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService
        builder_service = DashboardBuilderService()
        
        result = builder_service.undo_last_operation(dashboard_id)
        
        logger.info("Undo operation processed",
                   dashboard_id=dashboard_id,
                   success=result["success"])
        
        return result
        
    except Exception as e:
        logger.error("Undo operation failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Undo operation failed: {str(e)}")


@router.post("/builder/redo/{dashboard_id}", response_model=Dict[str, Any])
async def redo_last_operation(dashboard_id: str) -> Dict[str, Any]:
    """
    Redo the last undone operation on a dashboard
    
    Re-applies the most recently undone change to the dashboard.
    """
    try:
        from ...services.dashboard_builder import DashboardBuilderService
        builder_service = DashboardBuilderService()
        
        result = builder_service.redo_last_operation(dashboard_id)
        
        logger.info("Redo operation processed",
                   dashboard_id=dashboard_id,
                   success=result["success"])
        
        return result
        
    except Exception as e:
        logger.error("Redo operation failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Redo operation failed: {str(e)}")


@router.get("/builder/templates", response_model=List[Dict[str, Any]])
async def get_panel_templates() -> List[Dict[str, Any]]:
    """
    Get available panel templates for the dashboard builder
    
    Returns a list of predefined panel templates that can be
    used to quickly create common panel types.
    """
    try:
        # Mock panel templates - in real implementation, this would be stored in database
        templates = [
            {
                "template_id": "chart_line",
                "name": "Line Chart",
                "description": "Time series line chart for trend analysis",
                "panel_type": "chart",
                "chart_type": "line",
                "default_dimensions": {"width": 6, "height": 4},
                "category": "charts",
                "tags": ["time_series", "trends", "analytics"]
            },
            {
                "template_id": "chart_bar",
                "name": "Bar Chart",
                "description": "Categorical comparison bar chart",
                "panel_type": "chart",
                "chart_type": "bar",
                "default_dimensions": {"width": 6, "height": 4},
                "category": "charts",
                "tags": ["comparison", "categorical", "analytics"]
            },
            {
                "template_id": "metric_kpi",
                "name": "KPI Metric",
                "description": "Single value KPI display with status indicator",
                "panel_type": "metric",
                "chart_type": "gauge",
                "default_dimensions": {"width": 3, "height": 2},
                "category": "metrics",
                "tags": ["kpi", "performance", "monitoring"]
            },
            {
                "template_id": "table_data",
                "name": "Data Table",
                "description": "Detailed data table with sorting and pagination",
                "panel_type": "table",
                "chart_type": "table",
                "default_dimensions": {"width": 12, "height": 6},
                "category": "data",
                "tags": ["table", "detailed", "raw_data"]
            },
            {
                "template_id": "text_markdown",
                "name": "Text Panel",
                "description": "Markdown text panel for documentation and notes",
                "panel_type": "text",
                "chart_type": None,
                "default_dimensions": {"width": 6, "height": 3},
                "category": "content",
                "tags": ["text", "documentation", "notes"]
            }
        ]
        
        logger.info("Panel templates retrieved", template_count=len(templates))
        
        return templates
        
    except Exception as e:
        logger.error("Panel templates retrieval failed",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel templates retrieval failed: {str(e)}")


# Dashboard Builder Endpoints

@router.post("/dashboard-builder/sessions")
async def create_builder_session(
    dashboard_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Create a new dashboard builder session for collaborative editing
    
    Creates a builder session that enables drag-and-drop functionality,
    collaborative editing, and real-time state management.
    """
    try:
        logger.info("Creating builder session",
                   dashboard_id=dashboard_id,
                   user_id=user_id)
        
        session = dashboard_builder.create_builder_session(dashboard_id, user_id)
        
        logger.info("Builder session created",
                   session_id=session["session"]["session_id"],
                   dashboard_id=dashboard_id)
        
        return session
        
    except Exception as e:
        logger.error("Builder session creation failed",
                    dashboard_id=dashboard_id,
                    user_id=user_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Builder session creation failed: {str(e)}")


@router.post("/dashboard-builder/drag-operation")
async def handle_drag_operation(operation: DragOperation) -> Dict[str, Any]:
    """
    Handle drag-and-drop operations for dashboard panels
    
    Processes panel move, resize, add, and remove operations with
    collision detection and layout validation.
    """
    try:
        logger.info("Processing drag operation",
                   panel_id=operation.panel_id,
                   operation_type=operation.operation_type,
                   dashboard_id=operation.dashboard_id)
        
        result = dashboard_builder.handle_drag_operation(operation)
        
        if result["success"]:
            logger.info("Drag operation completed successfully",
                       panel_id=operation.panel_id,
                       operation_type=operation.operation_type)
        else:
            logger.warning("Drag operation failed",
                          panel_id=operation.panel_id,
                          error=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error("Drag operation processing failed",
                    panel_id=operation.panel_id,
                    operation_type=operation.operation_type,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Drag operation failed: {str(e)}")


@router.post("/dashboard-builder/resize-operation")
async def handle_resize_operation(operation: ResizeOperation) -> Dict[str, Any]:
    """
    Handle panel resize operations with collision detection
    
    Processes panel resize operations with automatic collision
    detection and resolution for overlapping panels.
    """
    try:
        logger.info("Processing resize operation",
                   panel_id=operation.panel_id,
                   new_width=operation.new_width,
                   new_height=operation.new_height,
                   dashboard_id=operation.dashboard_id)
        
        result = dashboard_builder.handle_resize_operation(operation)
        
        if result["success"]:
            logger.info("Resize operation completed successfully",
                       panel_id=operation.panel_id,
                       collisions_detected=result.get("collisions_detected", False))
        else:
            logger.warning("Resize operation failed",
                          panel_id=operation.panel_id,
                          error=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error("Resize operation processing failed",
                    panel_id=operation.panel_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resize operation failed: {str(e)}")


@router.post("/dashboard-builder/panels/add")
async def add_panel_to_dashboard(
    dashboard_id: str,
    panel_config: PanelConfiguration,
    position: Optional[DashboardGridPosition] = None
) -> Dict[str, Any]:
    """
    Add a new panel to the dashboard with automatic positioning
    
    Creates a new panel with the specified configuration and either
    uses the provided position or calculates an optimal position.
    """
    try:
        logger.info("Adding panel to dashboard",
                   dashboard_id=dashboard_id,
                   panel_type=panel_config.panel_type,
                   panel_title=panel_config.title)
        
        result = dashboard_builder.add_panel_to_dashboard(
            dashboard_id, panel_config, position
        )
        
        if result["success"]:
            logger.info("Panel added successfully",
                       panel_id=result["panel"]["id"],
                       dashboard_id=dashboard_id)
        else:
            logger.warning("Panel addition failed",
                          dashboard_id=dashboard_id,
                          error=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error("Panel addition failed",
                    dashboard_id=dashboard_id,
                    panel_type=panel_config.panel_type,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel addition failed: {str(e)}")


@router.delete("/dashboard-builder/panels/{panel_id}")
async def remove_panel_from_dashboard(
    dashboard_id: str,
    panel_id: str,
    optimize_layout: bool = Query(True, description="Whether to optimize layout after removal")
) -> Dict[str, Any]:
    """
    Remove a panel from the dashboard and optionally optimize layout
    
    Removes the specified panel and can automatically optimize the
    remaining layout to fill empty spaces.
    """
    try:
        logger.info("Removing panel from dashboard",
                   dashboard_id=dashboard_id,
                   panel_id=panel_id,
                   optimize_layout=optimize_layout)
        
        result = dashboard_builder.remove_panel_from_dashboard(
            dashboard_id, panel_id, optimize_layout
        )
        
        if result["success"]:
            logger.info("Panel removed successfully",
                       panel_id=panel_id,
                       dashboard_id=dashboard_id,
                       layout_optimized=result.get("layout_optimized", False))
        else:
            logger.warning("Panel removal failed",
                          panel_id=panel_id,
                          error=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error("Panel removal failed",
                    dashboard_id=dashboard_id,
                    panel_id=panel_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel removal failed: {str(e)}")


@router.put("/dashboard-builder/panels/{panel_id}/config")
async def update_panel_configuration(
    dashboard_id: str,
    panel_id: str,
    config_updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update panel configuration without changing layout
    
    Updates panel properties like title, styling, interactions,
    and data sources without affecting the panel's position.
    """
    try:
        logger.info("Updating panel configuration",
                   dashboard_id=dashboard_id,
                   panel_id=panel_id,
                   update_fields=list(config_updates.keys()))
        
        result = dashboard_builder.update_panel_configuration(
            dashboard_id, panel_id, config_updates
        )
        
        if result["success"]:
            logger.info("Panel configuration updated successfully",
                       panel_id=panel_id,
                       updates_applied=len(config_updates))
        else:
            logger.warning("Panel configuration update failed",
                          panel_id=panel_id,
                          error=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error("Panel configuration update failed",
                    dashboard_id=dashboard_id,
                    panel_id=panel_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel configuration update failed: {str(e)}")


@router.post("/dashboard-builder/from-template")
async def create_dashboard_from_template(
    template_name: str,
    dashboard_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new dashboard based on a predefined template
    
    Creates a dashboard using a template with pre-configured
    panels, layout, and styling options.
    """
    try:
        logger.info("Creating dashboard from template",
                   template_name=template_name,
                   user_id=dashboard_config.get("user_id"))
        
        result = dashboard_builder.create_dashboard_from_template(
            template_name, dashboard_config
        )
        
        if result["success"]:
            logger.info("Dashboard created from template successfully",
                       dashboard_id=result["dashboard"]["id"],
                       template_name=template_name)
        else:
            logger.warning("Dashboard creation from template failed",
                          template_name=template_name,
                          error=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error("Dashboard creation from template failed",
                    template_name=template_name,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard creation from template failed: {str(e)}")


@router.get("/dashboard-builder/collaboration/{dashboard_id}")
async def get_collaboration_state(dashboard_id: str) -> Dict[str, Any]:
    """
    Get current collaboration state for a dashboard
    
    Returns information about active users, recent collaboration
    events, and real-time editing state.
    """
    try:
        logger.info("Retrieving collaboration state",
                   dashboard_id=dashboard_id)
        
        collaboration_state = dashboard_builder.get_collaboration_state(dashboard_id)
        
        logger.info("Collaboration state retrieved",
                   dashboard_id=dashboard_id,
                   active_users=len(collaboration_state["active_users"]),
                   recent_events=len(collaboration_state["recent_events"]))
        
        return collaboration_state
        
    except Exception as e:
        logger.error("Collaboration state retrieval failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Collaboration state retrieval failed: {str(e)}")


@router.post("/dashboard-builder/undo/{dashboard_id}")
async def undo_last_operation(dashboard_id: str) -> Dict[str, Any]:
    """
    Undo the last operation on a dashboard
    
    Reverts the dashboard to its previous state and moves
    the current state to the redo stack.
    """
    try:
        logger.info("Undoing last operation",
                   dashboard_id=dashboard_id)
        
        result = dashboard_builder.undo_last_operation(dashboard_id)
        
        if result["success"]:
            logger.info("Undo operation completed successfully",
                       dashboard_id=dashboard_id,
                       can_redo=result.get("can_redo", False))
        else:
            logger.warning("Undo operation failed",
                          dashboard_id=dashboard_id,
                          error=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error("Undo operation failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Undo operation failed: {str(e)}")


@router.post("/dashboard-builder/redo/{dashboard_id}")
async def redo_last_operation(dashboard_id: str) -> Dict[str, Any]:
    """
    Redo the last undone operation on a dashboard
    
    Restores a previously undone state and moves the current
    state back to the undo stack.
    """
    try:
        logger.info("Redoing last operation",
                   dashboard_id=dashboard_id)
        
        result = dashboard_builder.redo_last_operation(dashboard_id)
        
        if result["success"]:
            logger.info("Redo operation completed successfully",
                       dashboard_id=dashboard_id,
                       can_undo=result.get("can_undo", False))
        else:
            logger.warning("Redo operation failed",
                          dashboard_id=dashboard_id,
                          error=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error("Redo operation failed",
                    dashboard_id=dashboard_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Redo operation failed: {str(e)}")


@router.get("/dashboard-builder/templates")
async def get_dashboard_builder_templates() -> List[Dict[str, Any]]:
    """
    Get available dashboard builder templates
    
    Returns a list of predefined dashboard templates with
    their configurations, panel layouts, and metadata.
    """
    try:
        logger.info("Retrieving dashboard builder templates")
        
        # Mock templates - in production this would be loaded from storage
        templates = [
            {
                "template_id": "executive_dashboard",
                "name": "Executive Dashboard",
                "description": "High-level KPI dashboard for executives",
                "layout_type": "grid",
                "default_panels": [
                    {"type": "metric", "title": "Revenue", "position": {"x": 0, "y": 0, "width": 3, "height": 2}},
                    {"type": "metric", "title": "Users", "position": {"x": 3, "y": 0, "width": 3, "height": 2}},
                    {"type": "metric", "title": "Conversion", "position": {"x": 6, "y": 0, "width": 3, "height": 2}},
                    {"type": "metric", "title": "Growth", "position": {"x": 9, "y": 0, "width": 3, "height": 2}},
                    {"type": "chart", "title": "Revenue Trend", "chart_type": "line", "position": {"x": 0, "y": 2, "width": 8, "height": 4}},
                    {"type": "chart", "title": "Top Products", "chart_type": "bar", "position": {"x": 8, "y": 2, "width": 4, "height": 4}}
                ],
                "category": "business",
                "tags": ["executive", "kpi", "high-level"]
            },
            {
                "template_id": "operational_dashboard",
                "name": "Operational Dashboard",
                "description": "Detailed operational metrics and monitoring",
                "layout_type": "grid",
                "default_panels": [
                    {"type": "chart", "title": "System Load", "chart_type": "line", "position": {"x": 0, "y": 0, "width": 6, "height": 3}},
                    {"type": "chart", "title": "Error Rate", "chart_type": "line", "position": {"x": 6, "y": 0, "width": 6, "height": 3}},
                    {"type": "chart", "title": "Response Time", "chart_type": "histogram", "position": {"x": 0, "y": 3, "width": 4, "height": 3}},
                    {"type": "metric", "title": "Uptime", "position": {"x": 4, "y": 3, "width": 2, "height": 3}},
                    {"type": "metric", "title": "Alerts", "position": {"x": 6, "y": 3, "width": 2, "height": 3}},
                    {"type": "table", "title": "Recent Events", "position": {"x": 8, "y": 3, "width": 4, "height": 3}}
                ],
                "category": "operations",
                "tags": ["operational", "monitoring", "detailed"]
            },
            {
                "template_id": "analytical_dashboard",
                "name": "Analytical Dashboard",
                "description": "Data analysis and exploration dashboard",
                "layout_type": "grid",
                "default_panels": [
                    {"type": "chart", "title": "Correlation Matrix", "chart_type": "heatmap", "position": {"x": 0, "y": 0, "width": 6, "height": 4}},
                    {"type": "chart", "title": "Distribution", "chart_type": "histogram", "position": {"x": 6, "y": 0, "width": 6, "height": 4}},
                    {"type": "chart", "title": "Scatter Analysis", "chart_type": "scatter", "position": {"x": 0, "y": 4, "width": 8, "height": 4}},
                    {"type": "table", "title": "Statistical Summary", "position": {"x": 8, "y": 4, "width": 4, "height": 4}}
                ],
                "category": "analytics",
                "tags": ["analytical", "exploration", "statistical"]
            }
        ]
        
        logger.info("Dashboard builder templates retrieved",
                   template_count=len(templates))
        
        return templates
        
    except Exception as e:
        logger.error("Dashboard builder templates retrieval failed",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard builder templates retrieval failed: {str(e)}")


@router.get("/dashboard-builder/panel-templates")
async def get_panel_templates() -> List[Dict[str, Any]]:
    """
    Get available panel templates for dashboard builder
    
    Returns a list of predefined panel templates with their
    configurations, default dimensions, and styling options.
    """
    try:
        logger.info("Retrieving panel templates")
        
        # Panel templates with configurations
        panel_templates = [
            {
                "template_id": "chart_line",
                "name": "Line Chart",
                "description": "Time series line chart for trend analysis",
                "panel_type": "chart",
                "chart_type": "line",
                "default_dimensions": {"width": 8, "height": 4},
                "default_config": {
                    "styling": {"background": "white", "border": "1px solid #e0e0e0"},
                    "interactions": {"zoom": True, "pan": True, "hover": True},
                    "refresh_interval": 300
                },
                "category": "charts",
                "tags": ["time_series", "trend", "analytics"]
            },
            {
                "template_id": "chart_bar",
                "name": "Bar Chart",
                "description": "Categorical comparison bar chart",
                "panel_type": "chart",
                "chart_type": "bar",
                "default_dimensions": {"width": 6, "height": 4},
                "default_config": {
                    "styling": {"background": "white", "border": "1px solid #e0e0e0"},
                    "interactions": {"hover": True, "drill_down": True},
                    "refresh_interval": 300
                },
                "category": "charts",
                "tags": ["comparison", "categorical", "analytics"]
            },
            {
                "template_id": "metric_kpi",
                "name": "KPI Metric",
                "description": "Single value KPI display with status indicator",
                "panel_type": "metric",
                "chart_type": "gauge",
                "default_dimensions": {"width": 3, "height": 2},
                "default_config": {
                    "styling": {"background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "color": "white", "textAlign": "center"},
                    "interactions": {},
                    "refresh_interval": 60
                },
                "category": "metrics",
                "tags": ["kpi", "performance", "monitoring"]
            },
            {
                "template_id": "table_data",
                "name": "Data Table",
                "description": "Detailed data table with sorting and pagination",
                "panel_type": "table",
                "chart_type": "table",
                "default_dimensions": {"width": 12, "height": 6},
                "default_config": {
                    "styling": {"background": "white", "border": "1px solid #e0e0e0"},
                    "interactions": {"sort": True, "filter": True, "pagination": True},
                    "refresh_interval": 300
                },
                "category": "data",
                "tags": ["table", "detailed", "raw_data"]
            },
            {
                "template_id": "text_markdown",
                "name": "Text Panel",
                "description": "Markdown text panel for documentation and notes",
                "panel_type": "text",
                "chart_type": None,
                "default_dimensions": {"width": 6, "height": 3},
                "default_config": {
                    "styling": {"background": "#f8f9fa", "border": "1px solid #e0e0e0", "padding": "15px"},
                    "interactions": {},
                    "refresh_interval": None
                },
                "category": "content",
                "tags": ["text", "documentation", "notes"]
            }
        ]
        
        logger.info("Panel templates retrieved",
                   template_count=len(panel_templates))
        
        return panel_templates
        
    except Exception as e:
        logger.error("Panel templates retrieval failed",
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Panel templates retrieval failed: {str(e)}")