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
    PASTEL = "pastel"
    DARK = "dark"
    COLORBLIND = "colorblind"


class ChartTheme(str, Enum):
    """Chart themes"""
    DEFAULT = "plotly_white"
    DARK = "plotly_dark"
    MINIMAL = "simple_white"
    PRESENTATION = "presentation"
    SEABORN = "seaborn"
    GGPLOT2 = "ggplot2"
    NONE = "none"


class FontFamily(str, Enum):
    """Font families for charts"""
    DEFAULT = "Arial"
    ARIAL = "Arial"
    HELVETICA = "Helvetica"
    TIMES = "Times New Roman"
    COURIER = "Courier New"
    VERDANA = "Verdana"
    CALIBRI = "Calibri"
    OPEN_SANS = "Open Sans"
    ROBOTO = "Roboto"


class LegendPosition(str, Enum):
    """Legend position options"""
    RIGHT = "right"
    LEFT = "left"
    TOP = "top"
    BOTTOM = "bottom"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    NONE = "none"


class AxisType(str, Enum):
    """Axis type options"""
    AUTO = "auto"
    LINEAR = "linear"
    LOG = "log"
    DATE = "date"
    CATEGORY = "category"


class GridStyle(str, Enum):
    """Grid style options"""
    SOLID = "solid"
    DASH = "dash"
    DOT = "dot"
    DASHDOT = "dashdot"
    NONE = "none"


class ExportFormat(str, Enum):
    """Export formats"""
    PNG = "png"
    PDF = "pdf"
    SVG = "svg"
    HTML = "html"
    JSON = "json"
    JPEG = "jpeg"
    WEBP = "webp"


class ExportQuality(str, Enum):
    """Export quality levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class ExportOrientation(str, Enum):
    """Export orientation options"""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    AUTO = "auto"


class ExportTemplate(str, Enum):
    """Export template presets"""
    PRESENTATION = "presentation"
    PRINT = "print"
    WEB = "web"
    SOCIAL = "social"
    REPORT = "report"
    CUSTOM = "custom"


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


class ChartFont(BaseModel):
    """Font configuration for charts"""
    family: FontFamily = Field(default=FontFamily.DEFAULT, description="Font family")
    size: int = Field(default=12, ge=8, le=72, description="Font size")
    color: str = Field(default="#000000", description="Font color (hex)")
    bold: bool = Field(default=False, description="Bold text")
    italic: bool = Field(default=False, description="Italic text")


class ChartMargin(BaseModel):
    """Chart margin configuration"""
    top: int = Field(default=60, ge=0, description="Top margin")
    bottom: int = Field(default=60, ge=0, description="Bottom margin")
    left: int = Field(default=60, ge=0, description="Left margin")
    right: int = Field(default=60, ge=0, description="Right margin")


class ChartGrid(BaseModel):
    """Grid configuration for charts"""
    show_x: bool = Field(default=True, description="Show X-axis grid")
    show_y: bool = Field(default=True, description="Show Y-axis grid")
    color: str = Field(default="#E0E0E0", description="Grid color (hex)")
    width: int = Field(default=1, ge=1, le=5, description="Grid line width")
    style: GridStyle = Field(default=GridStyle.SOLID, description="Grid line style")


class ChartAxis(BaseModel):
    """Axis configuration for charts"""
    title: Optional[str] = Field(None, description="Axis title")
    title_font: Optional[ChartFont] = Field(None, description="Title font configuration")
    label_font: Optional[ChartFont] = Field(None, description="Label font configuration")
    type: AxisType = Field(default=AxisType.AUTO, description="Axis type")
    show_line: bool = Field(default=True, description="Show axis line")
    show_ticks: bool = Field(default=True, description="Show tick marks")
    show_labels: bool = Field(default=True, description="Show axis labels")
    line_color: str = Field(default="#000000", description="Axis line color")
    line_width: int = Field(default=1, ge=1, le=5, description="Axis line width")
    tick_color: str = Field(default="#000000", description="Tick mark color")
    tick_length: int = Field(default=5, ge=1, le=20, description="Tick mark length")
    range_min: Optional[Union[float, str]] = Field(None, description="Minimum axis range")
    range_max: Optional[Union[float, str]] = Field(None, description="Maximum axis range")
    tick_format: Optional[str] = Field(None, description="Tick format string")
    tick_angle: int = Field(default=0, ge=-90, le=90, description="Tick label angle")


class ChartLegend(BaseModel):
    """Legend configuration for charts"""
    show: bool = Field(default=True, description="Show legend")
    position: LegendPosition = Field(default=LegendPosition.RIGHT, description="Legend position")
    font: Optional[ChartFont] = Field(None, description="Legend font configuration")
    background_color: str = Field(default="rgba(255,255,255,0.8)", description="Legend background color")
    border_color: str = Field(default="#000000", description="Legend border color")
    border_width: int = Field(default=0, ge=0, le=5, description="Legend border width")
    item_spacing: int = Field(default=5, ge=0, le=20, description="Spacing between legend items")
    orientation: str = Field(default="vertical", description="Legend orientation")


class ChartTitle(BaseModel):
    """Title configuration for charts"""
    text: Optional[str] = Field(None, description="Title text")
    font: Optional[ChartFont] = Field(None, description="Title font configuration")
    position: str = Field(default="center", description="Title position")
    show: bool = Field(default=True, description="Show title")
    pad: int = Field(default=20, ge=0, le=100, description="Title padding")


class ChartAnnotation(BaseModel):
    """Annotation configuration for charts"""
    text: str = Field(..., description="Annotation text")
    x: Union[float, str] = Field(..., description="X position")
    y: Union[float, str] = Field(..., description="Y position")
    font: Optional[ChartFont] = Field(None, description="Annotation font")
    background_color: str = Field(default="rgba(255,255,255,0.8)", description="Background color")
    border_color: str = Field(default="#000000", description="Border color")
    border_width: int = Field(default=1, ge=0, le=5, description="Border width")
    arrow_show: bool = Field(default=False, description="Show arrow")
    arrow_color: str = Field(default="#000000", description="Arrow color")


class ChartCustomization(BaseModel):
    """Comprehensive chart customization configuration"""
    theme: ChartTheme = Field(default=ChartTheme.DEFAULT, description="Chart theme")
    title: Optional[ChartTitle] = Field(None, description="Title configuration")
    font_family: FontFamily = Field(default=FontFamily.DEFAULT, description="Default font family")
    font_size: int = Field(default=12, ge=8, le=72, description="Default font size")
    background_color: str = Field(default="#FFFFFF", description="Chart background color")
    plot_background_color: str = Field(default="#FFFFFF", description="Plot area background color")
    margin: Optional[ChartMargin] = Field(None, description="Chart margins")
    grid: Optional[ChartGrid] = Field(None, description="Grid configuration")
    x_axis: Optional[ChartAxis] = Field(None, description="X-axis configuration")
    y_axis: Optional[ChartAxis] = Field(None, description="Y-axis configuration")
    legend: Optional[ChartLegend] = Field(None, description="Legend configuration")
    annotations: List[ChartAnnotation] = Field(default=[], description="Chart annotations")
    show_toolbar: bool = Field(default=True, description="Show Plotly toolbar")
    show_tips: bool = Field(default=True, description="Show hover tips")
    custom_css: Optional[str] = Field(None, description="Custom CSS styling")
    custom_js: Optional[str] = Field(None, description="Custom JavaScript")


class ChartTemplate(BaseModel):
    """Chart template configuration"""
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    chart_type: Optional[ChartType] = Field(None, description="Applicable chart type")
    customization: ChartCustomization = Field(..., description="Customization settings")
    preview_url: Optional[str] = Field(None, description="Template preview image URL")
    created_by: Optional[str] = Field(None, description="Template creator")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    tags: List[str] = Field(default=[], description="Template tags")
    is_public: bool = Field(default=True, description="Public template")


class ExportConfig(BaseModel):
    """Export configuration for charts"""
    format: ExportFormat = Field(..., description="Export format")
    quality: ExportQuality = Field(default=ExportQuality.HIGH, description="Export quality")
    width: Optional[int] = Field(None, ge=100, le=8000, description="Export width in pixels")
    height: Optional[int] = Field(None, ge=100, le=8000, description="Export height in pixels")
    dpi: int = Field(default=300, ge=72, le=600, description="Export DPI (dots per inch)")
    orientation: ExportOrientation = Field(default=ExportOrientation.AUTO, description="Export orientation")
    template: ExportTemplate = Field(default=ExportTemplate.WEB, description="Export template preset")
    include_metadata: bool = Field(default=True, description="Include chart metadata in export")
    include_title: bool = Field(default=True, description="Include chart title in export")
    include_legend: bool = Field(default=True, description="Include legend in export")
    background_color: str = Field(default="#FFFFFF", description="Background color for export")
    transparent_background: bool = Field(default=False, description="Use transparent background")
    font_scale: float = Field(default=1.0, ge=0.5, le=3.0, description="Font scale multiplier")
    margin_top: int = Field(default=50, ge=0, le=200, description="Top margin in pixels")
    margin_bottom: int = Field(default=50, ge=0, le=200, description="Bottom margin in pixels")
    margin_left: int = Field(default=50, ge=0, le=200, description="Left margin in pixels")
    margin_right: int = Field(default=50, ge=0, le=200, description="Right margin in pixels")
    compression_level: int = Field(default=6, ge=1, le=9, description="Compression level for applicable formats")
    optimize: bool = Field(default=True, description="Optimize file size")
    progressive: bool = Field(default=False, description="Use progressive encoding (JPEG)")
    embed_fonts: bool = Field(default=True, description="Embed fonts in export")
    
    @validator('background_color')
    def validate_background_color(cls, v):
        """Validate background color format"""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Background color must be in hex format (#RRGGBB)')
        return v


class ExportResult(BaseModel):
    """Export result information"""
    export_id: str = Field(..., description="Unique export identifier")
    chart_id: str = Field(..., description="Source chart identifier")
    format: ExportFormat = Field(..., description="Export format")
    filename: str = Field(..., description="Export filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME content type")
    export_time: float = Field(..., description="Export processing time in seconds")
    config: ExportConfig = Field(..., description="Export configuration used")
    metadata: Dict[str, Any] = Field(default={}, description="Additional export metadata")
    url: Optional[str] = Field(None, description="Download URL if available")
    expires_at: Optional[datetime] = Field(None, description="URL expiration time")


class BatchExportRequest(BaseModel):
    """Batch export request for multiple charts"""
    charts: List[str] = Field(..., description="List of chart IDs to export")
    format: ExportFormat = Field(..., description="Export format for all charts")
    config: ExportConfig = Field(..., description="Export configuration")
    archive_format: str = Field(default="zip", description="Archive format (zip, tar)")
    archive_name: Optional[str] = Field(None, description="Archive filename")
    include_manifest: bool = Field(default=True, description="Include export manifest")


class BatchExportResult(BaseModel):
    """Batch export result"""
    batch_id: str = Field(..., description="Batch export identifier")
    total_charts: int = Field(..., description="Total number of charts")
    successful_exports: int = Field(..., description="Number of successful exports")
    failed_exports: int = Field(..., description="Number of failed exports")
    results: List[ExportResult] = Field(..., description="Individual export results")
    archive_size: int = Field(..., description="Archive file size in bytes")
    archive_filename: str = Field(..., description="Archive filename")
    processing_time: float = Field(..., description="Total processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


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
    
    # Basic styling options
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
    
    # Advanced customization options
    customization: Optional[ChartCustomization] = Field(None, description="Advanced chart customization")
    template: Optional[str] = Field(None, description="Chart template name")
    
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


class LayoutType(str, Enum):
    """Dashboard layout types"""
    GRID = "grid"
    FLUID = "fluid"
    FIXED = "fixed"
    RESPONSIVE = "responsive"


class PanelType(str, Enum):
    """Dashboard panel types"""
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    TEXT = "text"
    IMAGE = "image"
    IFRAME = "iframe"
    CUSTOM = "custom"


class BreakpointSize(str, Enum):
    """Responsive breakpoint sizes"""
    XS = "xs"
    SM = "sm"
    MD = "md"
    LG = "lg"
    XL = "xl"


class DashboardGridPosition(BaseModel):
    """Dashboard panel grid position"""
    x: int = Field(default=0, description="Grid X position")
    y: int = Field(default=0, description="Grid Y position")
    width: int = Field(default=1, description="Grid width")
    height: int = Field(default=1, description="Grid height")
    min_width: int = Field(default=1, description="Minimum width")
    min_height: int = Field(default=1, description="Minimum height")
    max_width: Optional[int] = Field(None, description="Maximum width")
    max_height: Optional[int] = Field(None, description="Maximum height")


class DashboardLayoutConfig(BaseModel):
    """Dashboard layout configuration"""
    layout_type: LayoutType = Field(default=LayoutType.GRID, description="Layout type")
    columns: int = Field(default=12, description="Number of columns")
    row_height: int = Field(default=30, description="Row height in pixels")
    margin: List[int] = Field(default=[10, 10], description="Margin [x, y]")
    padding: List[int] = Field(default=[5, 5], description="Padding [x, y]")
    auto_size: bool = Field(default=True, description="Auto-size panels")
    compact_type: str = Field(default="vertical", description="Compact type")
    prevent_collision: bool = Field(default=True, description="Prevent panel collision")
    use_css_transforms: bool = Field(default=True, description="Use CSS transforms")
    breakpoints: Dict[str, int] = Field(default={
        "xl": 1200, "lg": 996, "md": 768, "sm": 576, "xs": 0
    }, description="Responsive breakpoints")
    breakpoint_columns: Dict[str, int] = Field(default={
        "xl": 12, "lg": 12, "md": 10, "sm": 6, "xs": 4
    }, description="Columns per breakpoint")


class DashboardPanel(BaseModel):
    """Enhanced dashboard panel definition"""
    panel_id: str = Field(..., description="Panel identifier")
    panel_type: PanelType = Field(..., description="Panel type")
    title: str = Field(..., description="Panel title")
    position: DashboardGridPosition = Field(..., description="Panel grid position")
    content: Dict[str, Any] = Field(default={}, description="Panel content configuration")
    style: Dict[str, Any] = Field(default={}, description="Panel styling")
    responsive_positions: Dict[str, DashboardGridPosition] = Field(default={}, description="Responsive positions")
    chart_config: Optional[ChartConfig] = Field(None, description="Chart configuration if panel is chart")
    refresh_interval: Optional[int] = Field(None, description="Refresh interval in seconds")
    query: Optional[str] = Field(None, description="SPL query for data")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")


class Dashboard(BaseModel):
    """Enhanced dashboard definition"""
    dashboard_id: str = Field(..., description="Dashboard identifier")
    title: str = Field(..., description="Dashboard title")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout_config: DashboardLayoutConfig = Field(..., description="Layout configuration")
    panels: List[DashboardPanel] = Field(default=[], description="Dashboard panels")
    global_filters: Dict[str, Any] = Field(default={}, description="Global filters")
    theme: str = Field(default="default", description="Dashboard theme")
    auto_refresh: bool = Field(default=False, description="Auto-refresh dashboard")
    refresh_interval: int = Field(default=300, description="Refresh interval in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    created_by: Optional[str] = Field(None, description="Creator user ID")
    permissions: Dict[str, List[str]] = Field(default={}, description="Access permissions")


class DashboardTemplate(BaseModel):
    """Dashboard template configuration"""
    template_id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    layout_config: DashboardLayoutConfig = Field(..., description="Layout configuration")
    panels: List[DashboardPanel] = Field(default=[], description="Template panels")
    preview_url: Optional[str] = Field(None, description="Preview image URL")
    category: str = Field(default="general", description="Template category")
    tags: List[str] = Field(default=[], description="Template tags")
    created_by: Optional[str] = Field(None, description="Template creator")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    is_public: bool = Field(default=True, description="Public template")
    use_count: int = Field(default=0, description="Usage count")


class DashboardCreateRequest(BaseModel):
    """Dashboard creation request"""
    title: str = Field(..., description="Dashboard title")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout_type: LayoutType = Field(default=LayoutType.GRID, description="Layout type")
    template_name: Optional[str] = Field(None, description="Template to use")
    created_by: Optional[str] = Field(None, description="Creator user ID")


class DashboardUpdateRequest(BaseModel):
    """Dashboard update request"""
    title: Optional[str] = Field(None, description="Dashboard title")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout_config: Optional[DashboardLayoutConfig] = Field(None, description="Layout configuration")
    global_filters: Optional[Dict[str, Any]] = Field(None, description="Global filters")
    theme: Optional[str] = Field(None, description="Dashboard theme")
    auto_refresh: Optional[bool] = Field(None, description="Auto-refresh setting")
    refresh_interval: Optional[int] = Field(None, description="Refresh interval")


class PanelCreateRequest(BaseModel):
    """Panel creation request"""
    panel_type: PanelType = Field(..., description="Panel type")
    title: str = Field(..., description="Panel title")
    position: Optional[DashboardGridPosition] = Field(None, description="Panel position")
    content: Optional[Dict[str, Any]] = Field(None, description="Panel content")
    style: Optional[Dict[str, Any]] = Field(None, description="Panel style")
    chart_config: Optional[ChartConfig] = Field(None, description="Chart configuration")
    query: Optional[str] = Field(None, description="SPL query")


class PanelUpdateRequest(BaseModel):
    """Panel update request"""
    title: Optional[str] = Field(None, description="Panel title")
    position: Optional[DashboardGridPosition] = Field(None, description="Panel position")
    content: Optional[Dict[str, Any]] = Field(None, description="Panel content")
    style: Optional[Dict[str, Any]] = Field(None, description="Panel style")
    chart_config: Optional[ChartConfig] = Field(None, description="Chart configuration")
    query: Optional[str] = Field(None, description="SPL query")


class DashboardResponse(BaseModel):
    """Dashboard response"""
    dashboard: Dashboard = Field(..., description="Dashboard configuration")
    panel_count: int = Field(..., description="Number of panels")
    total_size: int = Field(..., description="Total dashboard size in bytes")
    last_modified: datetime = Field(..., description="Last modification time")
    can_edit: bool = Field(default=False, description="User can edit dashboard")
    can_share: bool = Field(default=False, description="User can share dashboard")


class DashboardListResponse(BaseModel):
    """Dashboard list response"""
    dashboards: List[Dashboard] = Field(..., description="List of dashboards")
    total_count: int = Field(..., description="Total number of dashboards")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Page size")
    has_next: bool = Field(default=False, description="Has next page")
    has_previous: bool = Field(default=False, description="Has previous page")


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


# Drag-and-Drop Dashboard Builder Models

class DragDropOperation(str, Enum):
    """Drag-and-drop operation types"""
    MOVE = "move"
    RESIZE = "resize"
    ADD = "add"
    REMOVE = "remove"
    COPY = "copy"


class BuilderPermission(str, Enum):
    """Dashboard builder permissions"""
    READ = "read"
    EDIT = "edit"
    ADD_PANELS = "add_panels"
    REMOVE_PANELS = "remove_panels"
    MODIFY_LAYOUT = "modify_layout"
    SHARE = "share"
    ADMIN = "admin"


class DragEvent(BaseModel):
    """Drag event for dashboard builder"""
    operation: DragDropOperation = Field(..., description="Type of drag operation")
    panel_id: str = Field(..., description="Panel being dragged")
    source_position: DashboardGridPosition = Field(..., description="Original position")
    target_position: DashboardGridPosition = Field(..., description="Target position")
    dashboard_id: str = Field(..., description="Dashboard identifier")
    user_id: str = Field(..., description="User performing the operation")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    metadata: Dict[str, Any] = Field(default={}, description="Additional event metadata")


class ResizeEvent(BaseModel):
    """Panel resize event for dashboard builder"""
    panel_id: str = Field(..., description="Panel being resized")
    dashboard_id: str = Field(..., description="Dashboard identifier")
    old_dimensions: Dict[str, int] = Field(..., description="Previous dimensions")
    new_dimensions: Dict[str, int] = Field(..., description="New dimensions")
    maintain_aspect_ratio: bool = Field(default=True, description="Maintain aspect ratio during resize")
    user_id: str = Field(..., description="User performing the resize")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class PanelTemplate(BaseModel):
    """Template for creating new panels"""
    template_id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    panel_type: PanelType = Field(..., description="Panel type")
    chart_type: Optional[ChartType] = Field(None, description="Default chart type")
    default_dimensions: Dict[str, int] = Field(..., description="Default panel dimensions")
    configuration: Dict[str, Any] = Field(default={}, description="Default panel configuration")
    preview_url: Optional[str] = Field(None, description="Template preview image URL")
    category: str = Field(default="general", description="Template category")
    tags: List[str] = Field(default=[], description="Template tags")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Template creation time")


class BuilderSession(BaseModel):
    """Dashboard builder session"""
    session_id: str = Field(..., description="Session identifier")
    dashboard_id: str = Field(..., description="Dashboard being edited")
    user_id: str = Field(..., description="User identifier")
    permissions: List[BuilderPermission] = Field(..., description="User permissions for this session")
    is_active: bool = Field(default=True, description="Session active status")
    collaboration_enabled: bool = Field(default=True, description="Collaboration mode enabled")
    auto_save_enabled: bool = Field(default=True, description="Auto-save enabled")
    auto_save_interval: int = Field(default=30, description="Auto-save interval in seconds")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")


class CollaborationCursor(BaseModel):
    """Collaboration cursor position"""
    user_id: str = Field(..., description="User identifier")
    user_name: str = Field(..., description="User display name")
    position: Dict[str, float] = Field(..., description="Cursor position (x, y)")
    color: str = Field(..., description="User cursor color")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class BuilderState(BaseModel):
    """Dashboard builder state"""
    dashboard_id: str = Field(..., description="Dashboard identifier")
    active_sessions: List[BuilderSession] = Field(default=[], description="Active editing sessions")
    collaboration_cursors: List[CollaborationCursor] = Field(default=[], description="User cursor positions")
    undo_available: bool = Field(default=False, description="Undo operation available")
    redo_available: bool = Field(default=False, description="Redo operation available")
    pending_changes: bool = Field(default=False, description="Unsaved changes exist")
    last_saved: Optional[datetime] = Field(None, description="Last save timestamp")
    lock_status: Optional[Dict[str, Any]] = Field(None, description="Panel lock status")


class DragDropResult(BaseModel):
    """Result of drag-and-drop operation"""
    success: bool = Field(..., description="Operation success status")
    operation: DragDropOperation = Field(..., description="Operation type")
    panel_id: str = Field(..., description="Affected panel ID")
    old_position: Optional[DashboardGridPosition] = Field(None, description="Previous position")
    new_position: Optional[DashboardGridPosition] = Field(None, description="New position")
    conflicts_resolved: List[str] = Field(default=[], description="IDs of panels that were moved to resolve conflicts")
    layout_optimized: bool = Field(default=False, description="Whether layout was optimized")
    validation_errors: List[str] = Field(default=[], description="Validation errors")
    warnings: List[str] = Field(default=[], description="Operation warnings")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Operation timestamp")


class BuilderRequest(BaseModel):
    """Base request for builder operations"""
    dashboard_id: str = Field(..., description="Dashboard identifier")
    session_id: str = Field(..., description="Builder session ID")
    user_id: str = Field(..., description="User identifier")


class AddPanelRequest(BuilderRequest):
    """Request to add a new panel to dashboard"""
    panel_type: PanelType = Field(..., description="Type of panel to add")
    template_id: Optional[str] = Field(None, description="Panel template to use")
    position: Optional[DashboardGridPosition] = Field(None, description="Specific position (auto if None)")
    configuration: Dict[str, Any] = Field(default={}, description="Panel configuration")
    title: str = Field(default="New Panel", description="Panel title")


class MovePanelRequest(BuilderRequest):
    """Request to move a panel"""
    panel_id: str = Field(..., description="Panel to move")
    target_position: DashboardGridPosition = Field(..., description="Target position")
    copy_mode: bool = Field(default=False, description="Copy instead of move")


class ResizePanelRequest(BuilderRequest):
    """Request to resize a panel"""
    panel_id: str = Field(..., description="Panel to resize")
    new_width: int = Field(..., ge=1, le=12, description="New panel width")
    new_height: int = Field(..., ge=1, le=20, description="New panel height")
    maintain_aspect_ratio: bool = Field(default=True, description="Maintain aspect ratio")


class RemovePanelRequest(BuilderRequest):
    """Request to remove a panel"""
    panel_id: str = Field(..., description="Panel to remove")
    optimize_layout: bool = Field(default=True, description="Optimize layout after removal")


class UpdatePanelRequest(BuilderRequest):
    """Request to update panel configuration"""
    panel_id: str = Field(..., description="Panel to update")
    configuration: Dict[str, Any] = Field(..., description="Configuration updates")
    title: Optional[str] = Field(None, description="New panel title")


class UndoRedoRequest(BuilderRequest):
    """Request for undo/redo operations"""
    operation: str = Field(..., regex="^(undo|redo)$", description="Operation type")


class SaveDashboardRequest(BuilderRequest):
    """Request to save dashboard"""
    auto_save: bool = Field(default=False, description="Whether this is an auto-save")
    commit_message: Optional[str] = Field(None, description="Optional commit message")


class DashboardBuilderResponse(BaseModel):
    """Response from dashboard builder operations"""
    success: bool = Field(..., description="Operation success status")
    dashboard_id: str = Field(..., description="Dashboard identifier")
    operation_type: str = Field(..., description="Type of operation performed")
    result: Dict[str, Any] = Field(default={}, description="Operation result data")
    builder_state: BuilderState = Field(..., description="Current builder state")
    errors: List[str] = Field(default=[], description="Operation errors")
    warnings: List[str] = Field(default=[], description="Operation warnings")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# Update forward references
ChartRecommendation.model_rebuild()
DragEvent.model_rebuild()
ResizeEvent.model_rebuild()
BuilderSession.model_rebuild()
BuilderState.model_rebuild()
DragDropResult.model_rebuild()