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


# Update forward references
ChartRecommendation.model_rebuild()