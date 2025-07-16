"""
Dashboard Layout Engine for Splunk MCP Integration
Provides comprehensive layout management for dashboards with grid-based layouts,
responsive design, and panel management capabilities.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class LayoutType(Enum):
    """Supported dashboard layout types."""
    GRID = "grid"
    FLUID = "fluid"
    FIXED = "fixed"
    RESPONSIVE = "responsive"


class PanelType(Enum):
    """Supported panel types in dashboard."""
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    TEXT = "text"
    IMAGE = "image"
    IFRAME = "iframe"
    CUSTOM = "custom"


class BreakpointSize(Enum):
    """Responsive breakpoint sizes."""
    XS = "xs"  # Extra small devices (phones, 576px and down)
    SM = "sm"  # Small devices (tablets, 768px and down)
    MD = "md"  # Medium devices (desktops, 992px and down)
    LG = "lg"  # Large devices (large desktops, 1200px and down)
    XL = "xl"  # Extra large devices (1400px and up)


@dataclass
class GridPosition:
    """Grid position configuration for panels."""
    x: int = 0
    y: int = 0
    width: int = 1
    height: int = 1
    min_width: int = 1
    min_height: int = 1
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GridPosition':
        """Create from dictionary representation."""
        return cls(**data)


@dataclass
class Panel:
    """Dashboard panel configuration."""
    id: str
    panel_type: PanelType
    title: str
    position: GridPosition
    content: Dict[str, Any] = field(default_factory=dict)
    style: Dict[str, Any] = field(default_factory=dict)
    responsive_positions: Dict[BreakpointSize, GridPosition] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'panel_type': self.panel_type.value,
            'title': self.title,
            'position': self.position.to_dict(),
            'content': self.content,
            'style': self.style,
            'responsive_positions': {
                size.value: pos.to_dict() 
                for size, pos in self.responsive_positions.items()
            },
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Panel':
        """Create from dictionary representation."""
        responsive_positions = {}
        for size_str, pos_data in data.get('responsive_positions', {}).items():
            size = BreakpointSize(size_str)
            responsive_positions[size] = GridPosition.from_dict(pos_data)
        
        return cls(
            id=data['id'],
            panel_type=PanelType(data['panel_type']),
            title=data['title'],
            position=GridPosition.from_dict(data['position']),
            content=data.get('content', {}),
            style=data.get('style', {}),
            responsive_positions=responsive_positions,
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )


@dataclass
class LayoutConfig:
    """Dashboard layout configuration."""
    layout_type: LayoutType
    columns: int = 12
    row_height: int = 30
    margin: Tuple[int, int] = (10, 10)
    padding: Tuple[int, int] = (5, 5)
    auto_size: bool = True
    compact_type: str = "vertical"  # vertical, horizontal, none
    prevent_collision: bool = True
    use_css_transforms: bool = True
    
    # Responsive breakpoints
    breakpoints: Dict[BreakpointSize, int] = field(default_factory=lambda: {
        BreakpointSize.XL: 1200,
        BreakpointSize.LG: 996,
        BreakpointSize.MD: 768,
        BreakpointSize.SM: 576,
        BreakpointSize.XS: 0
    })
    
    # Columns for each breakpoint
    breakpoint_columns: Dict[BreakpointSize, int] = field(default_factory=lambda: {
        BreakpointSize.XL: 12,
        BreakpointSize.LG: 12,
        BreakpointSize.MD: 10,
        BreakpointSize.SM: 6,
        BreakpointSize.XS: 4
    })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'layout_type': self.layout_type.value,
            'columns': self.columns,
            'row_height': self.row_height,
            'margin': self.margin,
            'padding': self.padding,
            'auto_size': self.auto_size,
            'compact_type': self.compact_type,
            'prevent_collision': self.prevent_collision,
            'use_css_transforms': self.use_css_transforms,
            'breakpoints': {size.value: width for size, width in self.breakpoints.items()},
            'breakpoint_columns': {size.value: cols for size, cols in self.breakpoint_columns.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutConfig':
        """Create from dictionary representation."""
        breakpoints = {}
        for size_str, width in data.get('breakpoints', {}).items():
            breakpoints[BreakpointSize(size_str)] = width
        
        breakpoint_columns = {}
        for size_str, cols in data.get('breakpoint_columns', {}).items():
            breakpoint_columns[BreakpointSize(size_str)] = cols
        
        return cls(
            layout_type=LayoutType(data['layout_type']),
            columns=data.get('columns', 12),
            row_height=data.get('row_height', 30),
            margin=tuple(data.get('margin', [10, 10])),
            padding=tuple(data.get('padding', [5, 5])),
            auto_size=data.get('auto_size', True),
            compact_type=data.get('compact_type', 'vertical'),
            prevent_collision=data.get('prevent_collision', True),
            use_css_transforms=data.get('use_css_transforms', True),
            breakpoints=breakpoints,
            breakpoint_columns=breakpoint_columns
        )


@dataclass
class Dashboard:
    """Complete dashboard configuration."""
    id: str
    title: str
    description: str
    layout_config: LayoutConfig
    panels: List[Panel] = field(default_factory=list)
    global_filters: Dict[str, Any] = field(default_factory=dict)
    theme: str = "default"
    auto_refresh: bool = False
    refresh_interval: int = 300  # seconds
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'layout_config': self.layout_config.to_dict(),
            'panels': [panel.to_dict() for panel in self.panels],
            'global_filters': self.global_filters,
            'theme': self.theme,
            'auto_refresh': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dashboard':
        """Create from dictionary representation."""
        return cls(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            layout_config=LayoutConfig.from_dict(data['layout_config']),
            panels=[Panel.from_dict(panel_data) for panel_data in data.get('panels', [])],
            global_filters=data.get('global_filters', {}),
            theme=data.get('theme', 'default'),
            auto_refresh=data.get('auto_refresh', False),
            refresh_interval=data.get('refresh_interval', 300),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat())),
            created_by=data.get('created_by')
        )


class DashboardLayoutEngine:
    """
    Comprehensive dashboard layout engine with grid-based layouts,
    responsive design, and panel management capabilities.
    """
    
    def __init__(self):
        """Initialize the dashboard layout engine."""
        self.templates = self._load_layout_templates()
        self.collision_detector = CollisionDetector()
        self.responsive_optimizer = ResponsiveOptimizer()
        logger.info("Dashboard layout engine initialized")
    
    def create_dashboard(
        self,
        title: str,
        description: str = "",
        layout_type: LayoutType = LayoutType.GRID,
        template_name: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dashboard:
        """
        Create a new dashboard with specified configuration.
        
        Args:
            title: Dashboard title
            description: Dashboard description
            layout_type: Type of layout to use
            template_name: Optional template to use
            created_by: User who created the dashboard
            
        Returns:
            Dashboard: New dashboard instance
        """
        dashboard_id = str(uuid.uuid4())
        
        # Use template if specified
        if template_name and template_name in self.templates:
            template = self.templates[template_name]
            layout_config = LayoutConfig.from_dict(template['layout_config'])
            panels = [Panel.from_dict(panel_data) for panel_data in template.get('panels', [])]
        else:
            layout_config = LayoutConfig(layout_type=layout_type)
            panels = []
        
        dashboard = Dashboard(
            id=dashboard_id,
            title=title,
            description=description,
            layout_config=layout_config,
            panels=panels,
            created_by=created_by
        )
        
        logger.info(f"Created dashboard: {dashboard_id} with title: {title}")
        return dashboard
    
    def add_panel(
        self,
        dashboard: Dashboard,
        panel_type: PanelType,
        title: str,
        position: Optional[GridPosition] = None,
        content: Optional[Dict[str, Any]] = None,
        style: Optional[Dict[str, Any]] = None
    ) -> Panel:
        """
        Add a new panel to the dashboard.
        
        Args:
            dashboard: Dashboard to add panel to
            panel_type: Type of panel to add
            title: Panel title
            position: Panel position (auto-calculated if not provided)
            content: Panel content configuration
            style: Panel styling configuration
            
        Returns:
            Panel: New panel instance
        """
        panel_id = str(uuid.uuid4())
        
        # Auto-calculate position if not provided
        if position is None:
            position = self._calculate_optimal_position(dashboard)
        
        panel = Panel(
            id=panel_id,
            panel_type=panel_type,
            title=title,
            position=position,
            content=content or {},
            style=style or {}
        )
        
        # Check for collisions and adjust if necessary
        if dashboard.layout_config.prevent_collision:
            panel.position = self.collision_detector.resolve_collision(
                dashboard, panel.position
            )
        
        dashboard.panels.append(panel)
        dashboard.updated_at = datetime.now()
        
        logger.info(f"Added panel: {panel_id} to dashboard: {dashboard.id}")
        return panel
    
    def update_panel(
        self,
        dashboard: Dashboard,
        panel_id: str,
        **updates
    ) -> Panel:
        """
        Update an existing panel in the dashboard.
        
        Args:
            dashboard: Dashboard containing the panel
            panel_id: ID of panel to update
            **updates: Panel attributes to update
            
        Returns:
            Panel: Updated panel instance
            
        Raises:
            ValueError: If panel not found
        """
        panel = self.get_panel(dashboard, panel_id)
        
        # Update panel attributes
        for key, value in updates.items():
            if hasattr(panel, key):
                setattr(panel, key, value)
        
        # Handle position updates with collision detection
        if 'position' in updates and dashboard.layout_config.prevent_collision:
            panel.position = self.collision_detector.resolve_collision(
                dashboard, panel.position, exclude_panel_id=panel_id
            )
        
        panel.updated_at = datetime.now()
        dashboard.updated_at = datetime.now()
        
        logger.info(f"Updated panel: {panel_id} in dashboard: {dashboard.id}")
        return panel
    
    def remove_panel(self, dashboard: Dashboard, panel_id: str) -> bool:
        """
        Remove a panel from the dashboard.
        
        Args:
            dashboard: Dashboard to remove panel from
            panel_id: ID of panel to remove
            
        Returns:
            bool: True if panel was removed, False if not found
        """
        for i, panel in enumerate(dashboard.panels):
            if panel.id == panel_id:
                dashboard.panels.pop(i)
                dashboard.updated_at = datetime.now()
                logger.info(f"Removed panel: {panel_id} from dashboard: {dashboard.id}")
                return True
        return False
    
    def get_panel(self, dashboard: Dashboard, panel_id: str) -> Panel:
        """
        Get a specific panel from the dashboard.
        
        Args:
            dashboard: Dashboard to search
            panel_id: ID of panel to find
            
        Returns:
            Panel: Found panel instance
            
        Raises:
            ValueError: If panel not found
        """
        for panel in dashboard.panels:
            if panel.id == panel_id:
                return panel
        raise ValueError(f"Panel not found: {panel_id}")
    
    def move_panel(
        self,
        dashboard: Dashboard,
        panel_id: str,
        new_position: GridPosition
    ) -> Panel:
        """
        Move a panel to a new position.
        
        Args:
            dashboard: Dashboard containing the panel
            panel_id: ID of panel to move
            new_position: New position for the panel
            
        Returns:
            Panel: Moved panel instance
        """
        return self.update_panel(dashboard, panel_id, position=new_position)
    
    def resize_panel(
        self,
        dashboard: Dashboard,
        panel_id: str,
        new_width: int,
        new_height: int
    ) -> Panel:
        """
        Resize a panel to new dimensions.
        
        Args:
            dashboard: Dashboard containing the panel
            panel_id: ID of panel to resize
            new_width: New panel width
            new_height: New panel height
            
        Returns:
            Panel: Resized panel instance
        """
        panel = self.get_panel(dashboard, panel_id)
        new_position = GridPosition(
            x=panel.position.x,
            y=panel.position.y,
            width=new_width,
            height=new_height,
            min_width=panel.position.min_width,
            min_height=panel.position.min_height,
            max_width=panel.position.max_width,
            max_height=panel.position.max_height
        )
        return self.update_panel(dashboard, panel_id, position=new_position)
    
    def optimize_layout(self, dashboard: Dashboard) -> Dashboard:
        """
        Optimize the dashboard layout for better visual arrangement.
        
        Args:
            dashboard: Dashboard to optimize
            
        Returns:
            Dashboard: Optimized dashboard
        """
        if dashboard.layout_config.auto_size:
            # Auto-compact panels based on compact_type
            if dashboard.layout_config.compact_type == "vertical":
                self._compact_vertical(dashboard)
            elif dashboard.layout_config.compact_type == "horizontal":
                self._compact_horizontal(dashboard)
        
        # Optimize responsive positions
        dashboard = self.responsive_optimizer.optimize_responsive_layout(dashboard)
        
        dashboard.updated_at = datetime.now()
        logger.info(f"Optimized layout for dashboard: {dashboard.id}")
        return dashboard
    
    def get_layout_for_breakpoint(
        self,
        dashboard: Dashboard,
        breakpoint: BreakpointSize
    ) -> List[Dict[str, Any]]:
        """
        Get optimized layout for specific breakpoint.
        
        Args:
            dashboard: Dashboard to get layout for
            breakpoint: Target breakpoint size
            
        Returns:
            List[Dict[str, Any]]: Panel layout configurations
        """
        layout = []
        
        for panel in dashboard.panels:
            # Use responsive position if available, otherwise use default
            if breakpoint in panel.responsive_positions:
                position = panel.responsive_positions[breakpoint]
            else:
                position = panel.position
            
            layout.append({
                'i': panel.id,
                'x': position.x,
                'y': position.y,
                'w': position.width,
                'h': position.height,
                'minW': position.min_width,
                'minH': position.min_height,
                'maxW': position.max_width,
                'maxH': position.max_height
            })
        
        return layout
    
    def _calculate_optimal_position(self, dashboard: Dashboard) -> GridPosition:
        """Calculate optimal position for a new panel."""
        if not dashboard.panels:
            return GridPosition(x=0, y=0, width=6, height=4)
        
        # Find the lowest available position
        max_y = 0
        occupied_positions = set()
        
        for panel in dashboard.panels:
            pos = panel.position
            max_y = max(max_y, pos.y + pos.height)
            
            # Mark all occupied grid cells
            for x in range(pos.x, pos.x + pos.width):
                for y in range(pos.y, pos.y + pos.height):
                    occupied_positions.add((x, y))
        
        # Try to find a position in the current rows first
        for y in range(max_y + 1):
            for x in range(dashboard.layout_config.columns - 5):  # Leave space for width
                if (x, y) not in occupied_positions:
                    # Check if we can fit a 6x4 panel here
                    can_fit = True
                    for check_x in range(x, min(x + 6, dashboard.layout_config.columns)):
                        for check_y in range(y, y + 4):
                            if (check_x, check_y) in occupied_positions:
                                can_fit = False
                                break
                        if not can_fit:
                            break
                    
                    if can_fit:
                        return GridPosition(x=x, y=y, width=6, height=4)
        
        # If no space found, place at the bottom
        return GridPosition(x=0, y=max_y, width=6, height=4)
    
    def _compact_vertical(self, dashboard: Dashboard):
        """Compact panels vertically to minimize empty space."""
        # Sort panels by y position
        dashboard.panels.sort(key=lambda p: (p.position.y, p.position.x))
        
        # Track occupied positions
        occupied = {}
        
        for panel in dashboard.panels:
            pos = panel.position
            
            # Find the highest available y position
            best_y = 0
            for y in range(pos.y + 1):
                can_place = True
                for x in range(pos.x, pos.x + pos.width):
                    for check_y in range(y, y + pos.height):
                        if occupied.get((x, check_y), False):
                            can_place = False
                            break
                    if not can_place:
                        break
                
                if can_place:
                    best_y = y
                else:
                    break
            
            # Update panel position
            panel.position.y = best_y
            
            # Mark cells as occupied
            for x in range(pos.x, pos.x + pos.width):
                for y in range(best_y, best_y + pos.height):
                    occupied[(x, y)] = True
    
    def _compact_horizontal(self, dashboard: Dashboard):
        """Compact panels horizontally to minimize empty space."""
        # Sort panels by x position
        dashboard.panels.sort(key=lambda p: (p.position.x, p.position.y))
        
        # Track occupied positions
        occupied = {}
        
        for panel in dashboard.panels:
            pos = panel.position
            
            # Find the leftmost available x position
            best_x = 0
            for x in range(pos.x + 1):
                can_place = True
                for y in range(pos.y, pos.y + pos.height):
                    for check_x in range(x, x + pos.width):
                        if occupied.get((check_x, y), False):
                            can_place = False
                            break
                    if not can_place:
                        break
                
                if can_place:
                    best_x = x
                else:
                    break
            
            # Update panel position
            panel.position.x = best_x
            
            # Mark cells as occupied
            for x in range(best_x, best_x + pos.width):
                for y in range(pos.y, pos.y + pos.height):
                    occupied[(x, y)] = True
    
    def _load_layout_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined layout templates."""
        return {
            'executive_dashboard': {
                'layout_config': {
                    'layout_type': 'grid',
                    'columns': 12,
                    'row_height': 40,
                    'compact_type': 'vertical'
                },
                'panels': [
                    {
                        'id': 'kpi_row',
                        'panel_type': 'metric',
                        'title': 'Key Performance Indicators',
                        'position': {'x': 0, 'y': 0, 'width': 12, 'height': 2},
                        'content': {'metrics': ['revenue', 'users', 'conversion']}
                    },
                    {
                        'id': 'main_chart',
                        'panel_type': 'chart',
                        'title': 'Main Analytics Chart',
                        'position': {'x': 0, 'y': 2, 'width': 8, 'height': 6},
                        'content': {'chart_type': 'line'}
                    },
                    {
                        'id': 'secondary_chart',
                        'panel_type': 'chart',
                        'title': 'Secondary Chart',
                        'position': {'x': 8, 'y': 2, 'width': 4, 'height': 6},
                        'content': {'chart_type': 'pie'}
                    }
                ]
            },
            'operational_dashboard': {
                'layout_config': {
                    'layout_type': 'grid',
                    'columns': 12,
                    'row_height': 30,
                    'compact_type': 'vertical'
                },
                'panels': [
                    {
                        'id': 'system_status',
                        'panel_type': 'table',
                        'title': 'System Status',
                        'position': {'x': 0, 'y': 0, 'width': 6, 'height': 4},
                        'content': {'columns': ['service', 'status', 'uptime']}
                    },
                    {
                        'id': 'alerts',
                        'panel_type': 'table',
                        'title': 'Recent Alerts',
                        'position': {'x': 6, 'y': 0, 'width': 6, 'height': 4},
                        'content': {'columns': ['time', 'severity', 'message']}
                    },
                    {
                        'id': 'performance_chart',
                        'panel_type': 'chart',
                        'title': 'Performance Metrics',
                        'position': {'x': 0, 'y': 4, 'width': 12, 'height': 6},
                        'content': {'chart_type': 'line'}
                    }
                ]
            },
            'analytical_dashboard': {
                'layout_config': {
                    'layout_type': 'grid',
                    'columns': 12,
                    'row_height': 35,
                    'compact_type': 'vertical'
                },
                'panels': [
                    {
                        'id': 'filters',
                        'panel_type': 'text',
                        'title': 'Filters',
                        'position': {'x': 0, 'y': 0, 'width': 3, 'height': 8},
                        'content': {'type': 'filter_panel'}
                    },
                    {
                        'id': 'main_analysis',
                        'panel_type': 'chart',
                        'title': 'Main Analysis',
                        'position': {'x': 3, 'y': 0, 'width': 9, 'height': 5},
                        'content': {'chart_type': 'scatter'}
                    },
                    {
                        'id': 'data_table',
                        'panel_type': 'table',
                        'title': 'Data Table',
                        'position': {'x': 3, 'y': 5, 'width': 9, 'height': 3},
                        'content': {'columns': ['auto']}
                    }
                ]
            }
        }


class CollisionDetector:
    """Handles collision detection and resolution for dashboard panels."""
    
    def resolve_collision(
        self,
        dashboard: Dashboard,
        position: GridPosition,
        exclude_panel_id: Optional[str] = None
    ) -> GridPosition:
        """
        Resolve collision by finding the nearest available position.
        
        Args:
            dashboard: Dashboard to check for collisions
            position: Desired position
            exclude_panel_id: Panel ID to exclude from collision check
            
        Returns:
            GridPosition: Collision-free position
        """
        # Check if position is already free
        if not self._has_collision(dashboard, position, exclude_panel_id):
            return position
        
        # Try to find alternative positions
        for y_offset in range(20):  # Limit search to prevent infinite loops
            for x_offset in range(dashboard.layout_config.columns):
                test_position = GridPosition(
                    x=min(x_offset, dashboard.layout_config.columns - position.width),
                    y=position.y + y_offset,
                    width=position.width,
                    height=position.height,
                    min_width=position.min_width,
                    min_height=position.min_height,
                    max_width=position.max_width,
                    max_height=position.max_height
                )
                
                if not self._has_collision(dashboard, test_position, exclude_panel_id):
                    return test_position
        
        # Fallback: place at bottom
        max_y = max((p.position.y + p.position.height for p in dashboard.panels), default=0)
        return GridPosition(
            x=0,
            y=max_y,
            width=position.width,
            height=position.height,
            min_width=position.min_width,
            min_height=position.min_height,
            max_width=position.max_width,
            max_height=position.max_height
        )
    
    def _has_collision(
        self,
        dashboard: Dashboard,
        position: GridPosition,
        exclude_panel_id: Optional[str] = None
    ) -> bool:
        """Check if position collides with existing panels."""
        for panel in dashboard.panels:
            if exclude_panel_id and panel.id == exclude_panel_id:
                continue
            
            if self._positions_overlap(position, panel.position):
                return True
        
        return False
    
    def _positions_overlap(self, pos1: GridPosition, pos2: GridPosition) -> bool:
        """Check if two positions overlap."""
        return not (
            pos1.x + pos1.width <= pos2.x or
            pos2.x + pos2.width <= pos1.x or
            pos1.y + pos1.height <= pos2.y or
            pos2.y + pos2.height <= pos1.y
        )


class ResponsiveOptimizer:
    """Optimizes dashboard layouts for different screen sizes."""
    
    def optimize_responsive_layout(self, dashboard: Dashboard) -> Dashboard:
        """
        Optimize dashboard layout for all responsive breakpoints.
        
        Args:
            dashboard: Dashboard to optimize
            
        Returns:
            Dashboard: Dashboard with optimized responsive layouts
        """
        for breakpoint in BreakpointSize:
            self._optimize_for_breakpoint(dashboard, breakpoint)
        
        return dashboard
    
    def _optimize_for_breakpoint(self, dashboard: Dashboard, breakpoint: BreakpointSize):
        """Optimize layout for specific breakpoint."""
        target_columns = dashboard.layout_config.breakpoint_columns[breakpoint]
        
        for panel in dashboard.panels:
            # Create responsive position if doesn't exist
            if breakpoint not in panel.responsive_positions:
                panel.responsive_positions[breakpoint] = self._create_responsive_position(
                    panel.position, target_columns, breakpoint
                )
    
    def _create_responsive_position(
        self,
        original_position: GridPosition,
        target_columns: int,
        breakpoint: BreakpointSize
    ) -> GridPosition:
        """Create optimized position for specific breakpoint."""
        # Scale width proportionally
        width_ratio = original_position.width / 12  # Assuming 12 columns as base
        new_width = max(1, int(width_ratio * target_columns))
        
        # Adjust height based on breakpoint
        height_multiplier = self._get_height_multiplier(breakpoint)
        new_height = max(1, int(original_position.height * height_multiplier))
        
        # Ensure position fits within target columns
        new_x = min(original_position.x, target_columns - new_width)
        
        return GridPosition(
            x=new_x,
            y=original_position.y,
            width=new_width,
            height=new_height,
            min_width=1,
            min_height=1,
            max_width=target_columns,
            max_height=original_position.max_height
        )
    
    def _get_height_multiplier(self, breakpoint: BreakpointSize) -> float:
        """Get height multiplier for different breakpoints."""
        multipliers = {
            BreakpointSize.XL: 1.0,
            BreakpointSize.LG: 1.0,
            BreakpointSize.MD: 1.1,
            BreakpointSize.SM: 1.3,
            BreakpointSize.XS: 1.5
        }
        return multipliers.get(breakpoint, 1.0)


class LayoutTemplateManager:
    """Manages dashboard layout templates."""
    
    def __init__(self):
        """Initialize template manager."""
        self.custom_templates = {}
    
    def save_template(
        self,
        template_name: str,
        dashboard: Dashboard,
        description: str = ""
    ) -> bool:
        """
        Save dashboard as a template.
        
        Args:
            template_name: Name for the template
            dashboard: Dashboard to save as template
            description: Template description
            
        Returns:
            bool: True if saved successfully
        """
        try:
            template_data = {
                'name': template_name,
                'description': description,
                'layout_config': dashboard.layout_config.to_dict(),
                'panels': [panel.to_dict() for panel in dashboard.panels],
                'created_at': datetime.now().isoformat()
            }
            
            self.custom_templates[template_name] = template_data
            logger.info(f"Saved template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving template {template_name}: {str(e)}")
            return False
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get template by name."""
        return self.custom_templates.get(template_name)
    
    def list_templates(self) -> List[str]:
        """List all available templates."""
        return list(self.custom_templates.keys())
    
    def delete_template(self, template_name: str) -> bool:
        """Delete a template."""
        if template_name in self.custom_templates:
            del self.custom_templates[template_name]
            logger.info(f"Deleted template: {template_name}")
            return True
        return False