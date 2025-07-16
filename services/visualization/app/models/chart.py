"""
Chart data models for visualization service
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class ChartType(str, Enum):
    """Supported chart types"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    SANKEY = "sankey"
    GAUGE = "gauge"
    TABLE = "table"
    AUTO = "auto"


class DataType(str, Enum):
    """Data types for automatic chart selection"""
    CATEGORICAL = "categorical"
    NUMERICAL = "numerical"
    TEMPORAL = "temporal"
    GEOSPATIAL = "geospatial"
    TEXT = "text"
    BOOLEAN = "boolean"


class AggregationType(str, Enum):
    """Aggregation types"""
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    DISTINCT = "distinct"


class ColorScheme(str, Enum):
    """Color schemes for charts"""
    DEFAULT = "default"
    VIRIDIS = "viridis"
    PLASMA = "plasma"
    INFERNO = "inferno"
    MAGMA = "magma"
    BLUES = "blues"
    REDS = "reds"
    GREENS = "greens"
    CATEGORICAL = "categorical"


class ExportFormat(str, Enum):
    """Export formats"""
    PNG = "png"
    PDF = "pdf"
    SVG = "svg"
    HTML = "html"
    JSON = "json"


class InteractionType(str, Enum):
    """Types of chart interactions"""
    CLICK = "click"
    HOVER = "hover"
    SELECT = "select"
    BRUSH = "brush"
    LASSO = "lasso"
    ZOOM = "zoom"
    PAN = "pan"
    DRILL_DOWN = "drill_down"
    FILTER = "filter"


class SelectionMode(str, Enum):
    """Selection modes for chart interactions"""
    SINGLE = "single"
    MULTIPLE = "multiple"
    RANGE = "range"


class FilterOperation(str, Enum):
    """Filter operations for data filtering"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class DataField(BaseModel):
    """Data field definition"""
    name: str = Field(..., description="Field name")
    data_type: DataType = Field(..., description="Data type")
    sample_values: List[Any] = Field(default=[], description="Sample values for analysis")
    unique_count: Optional[int] = Field(None, description="Number of unique values")
    null_count: Optional[int] = Field(None, description="Number of null values")
    min_value: Optional[Union[float, str, datetime]] = Field(None, description="Minimum value")
    max_value: Optional[Union[float, str, datetime]] = Field(None, description="Maximum value")


class ChartData(BaseModel):
    """Chart data structure"""
    fields: List[DataField] = Field(..., description="Data fields")
    rows: List[Dict[str, Any]] = Field(..., description="Data rows")
    total_rows: int = Field(..., description="Total number of rows")
    is_aggregated: bool = Field(default=False, description="Whether data is pre-aggregated")
    time_field: Optional[str] = Field(None, description="Time field name if temporal data")
    
    @validator('total_rows')
    def validate_total_rows(cls, v, values):
        if 'rows' in values and v != len(values['rows']):
            raise ValueError("total_rows must match the length of rows")
        return v


class ChartConfig(BaseModel):
    """Chart configuration"""
    chart_type: ChartType = Field(..., description="Chart type")
    title: Optional[str] = Field(None, description="Chart title")
    x_axis: Optional[str] = Field(None, description="X-axis field")
    y_axis: Optional[Union[str, List[str]]] = Field(None, description="Y-axis field(s)")
    color_field: Optional[str] = Field(None, description="Color grouping field")
    size_field: Optional[str] = Field(None, description="Size field for scatter plots")
    
    # Styling options
    width: int = Field(default=800, description="Chart width in pixels")
    height: int = Field(default=600, description="Chart height in pixels")
    color_scheme: ColorScheme = Field(default=ColorScheme.DEFAULT, description="Color scheme")
    
    # Interaction options
    interactive: bool = Field(default=True, description="Enable interactive features")
    zoom_enabled: bool = Field(default=True, description="Enable zoom")
    pan_enabled: bool = Field(default=True, description="Enable pan")
    hover_enabled: bool = Field(default=True, description="Enable hover tooltips")
    crossfilter_enabled: bool = Field(default=False, description="Enable crossfilter for data filtering")
    drill_down_enabled: bool = Field(default=False, description="Enable drill-down functionality")
    brush_enabled: bool = Field(default=False, description="Enable brush selection")
    lasso_enabled: bool = Field(default=False, description="Enable lasso selection")
    
    # Aggregation options
    aggregation: Optional[AggregationType] = Field(None, description="Aggregation type")
    group_by: Optional[List[str]] = Field(None, description="Group by fields")
    
    # Specific chart options
    chart_options: Dict[str, Any] = Field(default={}, description="Chart-specific options")


class ChartRecommendation(BaseModel):
    """Chart type recommendation"""
    chart_type: ChartType = Field(..., description="Recommended chart type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    reasoning: str = Field(..., description="Reasoning for recommendation")
    config: ChartConfig = Field(..., description="Recommended configuration")
    alternatives: List['ChartRecommendation'] = Field(default=[], description="Alternative recommendations")


class ChartResponse(BaseModel):
    """Chart generation response"""
    chart_id: str = Field(..., description="Unique chart identifier")
    chart_type: ChartType = Field(..., description="Generated chart type")
    config: ChartConfig = Field(..., description="Chart configuration used")
    data_summary: Dict[str, Any] = Field(..., description="Data summary statistics")
    generation_time: float = Field(..., description="Generation time in seconds")
    file_size: Optional[int] = Field(None, description="File size in bytes if exported")
    export_url: Optional[str] = Field(None, description="URL to exported chart")
    interactive_url: Optional[str] = Field(None, description="URL to interactive chart")
    plotly_json: Optional[str] = Field(None, description="Plotly JSON representation of the chart")


class ChartRequest(BaseModel):
    """Chart generation request"""
    data: ChartData = Field(..., description="Chart data")
    config: Optional[ChartConfig] = Field(None, description="Chart configuration")
    auto_select: bool = Field(default=True, description="Auto-select chart type if not specified")
    export_format: Optional[ExportFormat] = Field(None, description="Export format")
    user_preferences: Dict[str, Any] = Field(default={}, description="User preferences")


class DashboardPanel(BaseModel):
    """Dashboard panel definition"""
    panel_id: str = Field(..., description="Panel identifier")
    title: str = Field(..., description="Panel title")
    chart_config: ChartConfig = Field(..., description="Chart configuration")
    position: Dict[str, int] = Field(..., description="Panel position (x, y, width, height)")
    refresh_interval: Optional[int] = Field(None, description="Refresh interval in seconds")
    query: Optional[str] = Field(None, description="SPL query for data")


class Dashboard(BaseModel):
    """Dashboard definition"""
    dashboard_id: str = Field(..., description="Dashboard identifier")
    title: str = Field(..., description="Dashboard title")
    description: Optional[str] = Field(None, description="Dashboard description")
    panels: List[DashboardPanel] = Field(..., description="Dashboard panels")
    layout: Dict[str, Any] = Field(default={}, description="Layout configuration")
    filters: List[Dict[str, Any]] = Field(default=[], description="Global filters")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    permissions: Dict[str, List[str]] = Field(default={}, description="Access permissions")


class ChartFilter(BaseModel):
    """Chart data filter definition"""
    field: str = Field(..., description="Field to filter on")
    operation: FilterOperation = Field(..., description="Filter operation")
    value: Union[str, int, float, List[Any]] = Field(..., description="Filter value(s)")
    case_sensitive: bool = Field(default=True, description="Case sensitive filtering for string operations")


class ChartSelection(BaseModel):
    """Chart selection state"""
    selection_mode: SelectionMode = Field(..., description="Selection mode")
    selected_points: List[Dict[str, Any]] = Field(default=[], description="Selected data points")
    selection_bounds: Optional[Dict[str, Any]] = Field(None, description="Selection bounds (for brush/lasso)")
    active: bool = Field(default=False, description="Whether selection is active")


class DrillDownConfig(BaseModel):
    """Drill-down configuration"""
    enabled: bool = Field(default=False, description="Enable drill-down")
    target_field: Optional[str] = Field(None, description="Field to drill down on")
    aggregation_level: str = Field(default="next", description="Aggregation level for drill-down")
    breadcrumb_enabled: bool = Field(default=True, description="Show drill-down breadcrumb")
    max_levels: int = Field(default=5, description="Maximum drill-down levels")


class InteractionEvent(BaseModel):
    """Chart interaction event"""
    event_type: InteractionType = Field(..., description="Type of interaction")
    chart_id: str = Field(..., description="Chart identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data (selected points, bounds, etc.)")
    user_id: Optional[str] = Field(None, description="User who triggered the interaction")


class ChartInteractiveConfig(BaseModel):
    """Extended interactive configuration for charts"""
    filters: List[ChartFilter] = Field(default=[], description="Applied filters")
    selection: Optional[ChartSelection] = Field(None, description="Current selection state")
    drill_down: Optional[DrillDownConfig] = Field(None, description="Drill-down configuration")
    zoom_level: float = Field(default=1.0, description="Current zoom level")
    pan_offset: Dict[str, float] = Field(default={}, description="Pan offset (x, y)")
    crossfilter_enabled: bool = Field(default=False, description="Enable crossfilter mode")
    linked_charts: List[str] = Field(default=[], description="IDs of linked charts for crossfilter")


class InteractiveChartResponse(BaseModel):
    """Interactive chart response with state"""
    chart_id: str = Field(..., description="Chart identifier")
    chart_type: ChartType = Field(..., description="Chart type")
    config: ChartConfig = Field(..., description="Chart configuration")
    interactive_config: ChartInteractiveConfig = Field(..., description="Interactive configuration")
    data_summary: Dict[str, Any] = Field(..., description="Data summary")
    plotly_json: str = Field(..., description="Plotly JSON with interactive features")
    interaction_events: List[InteractionEvent] = Field(default=[], description="Recent interaction events")
    generation_time: float = Field(..., description="Generation time in seconds")


# Update forward references
ChartRecommendation.model_rebuild()