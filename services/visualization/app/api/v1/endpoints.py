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
    ChartConfig, ChartType, Dashboard, DashboardPanel, ExportFormat
)
from ...services.chart_selector import ChartTypeSelector
from ...services.chart_generator import ChartGenerator
from ...core.logging import get_logger, log_chart_generation
from ...core.config import settings

logger = get_logger(__name__)
router = APIRouter()

# Initialize services
chart_selector = ChartTypeSelector()
chart_generator = ChartGenerator()


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
            "export_formats": ["png", "pdf", "svg", "html"]
        },
        "timestamp": time.time()
    }