"""
Comprehensive test suite for dashboard layout functionality
Tests dashboard layout engine, panel management, and responsive design features.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

from app.services.dashboard_layout import (
    DashboardLayoutEngine, LayoutType, PanelType, BreakpointSize,
    GridPosition, Panel, LayoutConfig, Dashboard, CollisionDetector,
    ResponsiveOptimizer, LayoutTemplateManager
)


class TestGridPosition:
    """Test grid position functionality"""
    
    def test_grid_position_creation(self):
        """Test creating grid position with default values"""
        position = GridPosition()
        assert position.x == 0
        assert position.y == 0
        assert position.width == 1
        assert position.height == 1
        assert position.min_width == 1
        assert position.min_height == 1
        assert position.max_width is None
        assert position.max_height is None
    
    def test_grid_position_with_values(self):
        """Test creating grid position with custom values"""
        position = GridPosition(x=2, y=3, width=4, height=5, min_width=2, min_height=2)
        assert position.x == 2
        assert position.y == 3
        assert position.width == 4
        assert position.height == 5
        assert position.min_width == 2
        assert position.min_height == 2
    
    def test_grid_position_serialization(self):
        """Test grid position to_dict and from_dict methods"""
        position = GridPosition(x=1, y=2, width=3, height=4, min_width=1, min_height=1)
        position_dict = position.to_dict()
        
        assert position_dict['x'] == 1
        assert position_dict['y'] == 2
        assert position_dict['width'] == 3
        assert position_dict['height'] == 4
        
        # Test deserialization
        restored_position = GridPosition.from_dict(position_dict)
        assert restored_position.x == position.x
        assert restored_position.y == position.y
        assert restored_position.width == position.width
        assert restored_position.height == position.height


class TestPanel:
    """Test panel functionality"""
    
    def test_panel_creation(self):
        """Test creating panel with required fields"""
        panel_id = str(uuid.uuid4())
        position = GridPosition(x=0, y=0, width=6, height=4)
        
        panel = Panel(
            id=panel_id,
            panel_type=PanelType.CHART,
            title="Test Chart Panel",
            position=position
        )
        
        assert panel.id == panel_id
        assert panel.panel_type == PanelType.CHART
        assert panel.title == "Test Chart Panel"
        assert panel.position == position
        assert panel.content == {}
        assert panel.style == {}
        assert panel.responsive_positions == {}
    
    def test_panel_with_content_and_style(self):
        """Test creating panel with content and style"""
        panel_id = str(uuid.uuid4())
        position = GridPosition(x=0, y=0, width=6, height=4)
        content = {"chart_type": "line", "data_source": "test"}
        style = {"background_color": "#ffffff", "border": "1px solid #ccc"}
        
        panel = Panel(
            id=panel_id,
            panel_type=PanelType.CHART,
            title="Test Chart Panel",
            position=position,
            content=content,
            style=style
        )
        
        assert panel.content == content
        assert panel.style == style
    
    def test_panel_serialization(self):
        """Test panel to_dict and from_dict methods"""
        panel_id = str(uuid.uuid4())
        position = GridPosition(x=1, y=2, width=6, height=4)
        
        panel = Panel(
            id=panel_id,
            panel_type=PanelType.CHART,
            title="Test Panel",
            position=position,
            content={"test": "data"},
            style={"color": "red"}
        )
        
        panel_dict = panel.to_dict()
        
        assert panel_dict['id'] == panel_id
        assert panel_dict['panel_type'] == 'chart'
        assert panel_dict['title'] == "Test Panel"
        assert panel_dict['position']['x'] == 1
        assert panel_dict['position']['y'] == 2
        assert panel_dict['content'] == {"test": "data"}
        assert panel_dict['style'] == {"color": "red"}
        
        # Test deserialization
        restored_panel = Panel.from_dict(panel_dict)
        assert restored_panel.id == panel.id
        assert restored_panel.panel_type == panel.panel_type
        assert restored_panel.title == panel.title
        assert restored_panel.position.x == panel.position.x
        assert restored_panel.position.y == panel.position.y


class TestLayoutConfig:
    """Test layout configuration functionality"""
    
    def test_layout_config_defaults(self):
        """Test layout config with default values"""
        config = LayoutConfig(layout_type=LayoutType.GRID)
        
        assert config.layout_type == LayoutType.GRID
        assert config.columns == 12
        assert config.row_height == 30
        assert config.margin == (10, 10)
        assert config.padding == (5, 5)
        assert config.auto_size is True
        assert config.compact_type == "vertical"
        assert config.prevent_collision is True
        assert config.use_css_transforms is True
        
        # Test breakpoints
        assert BreakpointSize.XL in config.breakpoints
        assert BreakpointSize.LG in config.breakpoints
        assert config.breakpoints[BreakpointSize.XL] == 1200
        assert config.breakpoints[BreakpointSize.LG] == 996
    
    def test_layout_config_custom_values(self):
        """Test layout config with custom values"""
        config = LayoutConfig(
            layout_type=LayoutType.FLUID,
            columns=8,
            row_height=40,
            margin=(15, 15),
            padding=(10, 10),
            auto_size=False,
            compact_type="horizontal",
            prevent_collision=False
        )
        
        assert config.layout_type == LayoutType.FLUID
        assert config.columns == 8
        assert config.row_height == 40
        assert config.margin == (15, 15)
        assert config.padding == (10, 10)
        assert config.auto_size is False
        assert config.compact_type == "horizontal"
        assert config.prevent_collision is False
    
    def test_layout_config_serialization(self):
        """Test layout config serialization"""
        config = LayoutConfig(
            layout_type=LayoutType.GRID,
            columns=10,
            row_height=35
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['layout_type'] == 'grid'
        assert config_dict['columns'] == 10
        assert config_dict['row_height'] == 35
        assert 'breakpoints' in config_dict
        assert 'breakpoint_columns' in config_dict
        
        # Test deserialization
        restored_config = LayoutConfig.from_dict(config_dict)
        assert restored_config.layout_type == config.layout_type
        assert restored_config.columns == config.columns
        assert restored_config.row_height == config.row_height


class TestDashboard:
    """Test dashboard functionality"""
    
    def test_dashboard_creation(self):
        """Test creating dashboard with required fields"""
        dashboard_id = str(uuid.uuid4())
        layout_config = LayoutConfig(layout_type=LayoutType.GRID)
        
        dashboard = Dashboard(
            id=dashboard_id,
            title="Test Dashboard",
            description="Test dashboard description",
            layout_config=layout_config
        )
        
        assert dashboard.id == dashboard_id
        assert dashboard.title == "Test Dashboard"
        assert dashboard.description == "Test dashboard description"
        assert dashboard.layout_config == layout_config
        assert dashboard.panels == []
        assert dashboard.global_filters == {}
        assert dashboard.theme == "default"
        assert dashboard.auto_refresh is False
        assert dashboard.refresh_interval == 300
    
    def test_dashboard_with_panels(self):
        """Test dashboard with panels"""
        dashboard_id = str(uuid.uuid4())
        layout_config = LayoutConfig(layout_type=LayoutType.GRID)
        
        panel1 = Panel(
            id=str(uuid.uuid4()),
            panel_type=PanelType.CHART,
            title="Chart Panel",
            position=GridPosition(x=0, y=0, width=6, height=4)
        )
        
        panel2 = Panel(
            id=str(uuid.uuid4()),
            panel_type=PanelType.TABLE,
            title="Table Panel",
            position=GridPosition(x=6, y=0, width=6, height=4)
        )
        
        dashboard = Dashboard(
            id=dashboard_id,
            title="Test Dashboard",
            description="Test dashboard with panels",
            layout_config=layout_config,
            panels=[panel1, panel2]
        )
        
        assert len(dashboard.panels) == 2
        assert dashboard.panels[0].panel_type == PanelType.CHART
        assert dashboard.panels[1].panel_type == PanelType.TABLE
    
    def test_dashboard_serialization(self):
        """Test dashboard serialization"""
        dashboard_id = str(uuid.uuid4())
        layout_config = LayoutConfig(layout_type=LayoutType.GRID)
        
        dashboard = Dashboard(
            id=dashboard_id,
            title="Test Dashboard",
            description="Test description",
            layout_config=layout_config,
            theme="dark",
            auto_refresh=True,
            refresh_interval=60
        )
        
        dashboard_dict = dashboard.to_dict()
        
        assert dashboard_dict['id'] == dashboard_id
        assert dashboard_dict['title'] == "Test Dashboard"
        assert dashboard_dict['description'] == "Test description"
        assert dashboard_dict['theme'] == "dark"
        assert dashboard_dict['auto_refresh'] is True
        assert dashboard_dict['refresh_interval'] == 60
        assert 'layout_config' in dashboard_dict
        assert 'panels' in dashboard_dict
        
        # Test deserialization
        restored_dashboard = Dashboard.from_dict(dashboard_dict)
        assert restored_dashboard.id == dashboard.id
        assert restored_dashboard.title == dashboard.title
        assert restored_dashboard.description == dashboard.description
        assert restored_dashboard.theme == dashboard.theme
        assert restored_dashboard.auto_refresh == dashboard.auto_refresh
        assert restored_dashboard.refresh_interval == dashboard.refresh_interval


class TestDashboardLayoutEngine:
    """Test dashboard layout engine functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = DashboardLayoutEngine()
    
    def test_engine_initialization(self):
        """Test engine initialization"""
        assert self.engine is not None
        assert self.engine.templates is not None
        assert self.engine.collision_detector is not None
        assert self.engine.responsive_optimizer is not None
    
    def test_create_dashboard_basic(self):
        """Test creating basic dashboard"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            description="Test description",
            layout_type=LayoutType.GRID
        )
        
        assert dashboard.title == "Test Dashboard"
        assert dashboard.description == "Test description"
        assert dashboard.layout_config.layout_type == LayoutType.GRID
        assert len(dashboard.panels) == 0
        assert dashboard.id is not None
    
    def test_create_dashboard_with_template(self):
        """Test creating dashboard with template"""
        dashboard = self.engine.create_dashboard(
            title="Executive Dashboard",
            description="Executive dashboard from template",
            layout_type=LayoutType.GRID,
            template_name="executive_dashboard"
        )
        
        assert dashboard.title == "Executive Dashboard"
        assert dashboard.description == "Executive dashboard from template"
        assert len(dashboard.panels) > 0  # Template should have panels
    
    def test_add_panel_to_dashboard(self):
        """Test adding panel to dashboard"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Test Chart Panel"
        )
        
        assert panel.panel_type == PanelType.CHART
        assert panel.title == "Test Chart Panel"
        assert panel.position.width == 6
        assert panel.position.height == 4
        assert len(dashboard.panels) == 1
        assert dashboard.panels[0].id == panel.id
    
    def test_add_panel_with_custom_position(self):
        """Test adding panel with custom position"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        position = GridPosition(x=2, y=3, width=8, height=6)
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.TABLE,
            title="Test Table Panel",
            position=position
        )
        
        assert panel.position.x == 2
        assert panel.position.y == 3
        assert panel.position.width == 8
        assert panel.position.height == 6
    
    def test_add_multiple_panels(self):
        """Test adding multiple panels to dashboard"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        panel1 = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Chart Panel 1"
        )
        
        panel2 = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.TABLE,
            title="Table Panel 2"
        )
        
        assert len(dashboard.panels) == 2
        assert panel1.position.y == 0
        assert panel2.position.y > panel1.position.y  # Should be placed below
    
    def test_update_panel(self):
        """Test updating panel"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Original Title"
        )
        
        updated_panel = self.engine.update_panel(
            dashboard=dashboard,
            panel_id=panel.id,
            title="Updated Title",
            content={"chart_type": "bar"}
        )
        
        assert updated_panel.title == "Updated Title"
        assert updated_panel.content == {"chart_type": "bar"}
        assert updated_panel.id == panel.id
    
    def test_remove_panel(self):
        """Test removing panel from dashboard"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Test Panel"
        )
        
        assert len(dashboard.panels) == 1
        
        success = self.engine.remove_panel(dashboard, panel.id)
        assert success is True
        assert len(dashboard.panels) == 0
    
    def test_remove_nonexistent_panel(self):
        """Test removing non-existent panel"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        success = self.engine.remove_panel(dashboard, "non-existent-id")
        assert success is False
    
    def test_get_panel(self):
        """Test getting panel by ID"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Test Panel"
        )
        
        retrieved_panel = self.engine.get_panel(dashboard, panel.id)
        assert retrieved_panel.id == panel.id
        assert retrieved_panel.title == panel.title
    
    def test_get_nonexistent_panel(self):
        """Test getting non-existent panel"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        with pytest.raises(ValueError, match="Panel not found"):
            self.engine.get_panel(dashboard, "non-existent-id")
    
    def test_move_panel(self):
        """Test moving panel to new position"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Test Panel"
        )
        
        new_position = GridPosition(x=3, y=4, width=8, height=6)
        moved_panel = self.engine.move_panel(
            dashboard=dashboard,
            panel_id=panel.id,
            new_position=new_position
        )
        
        assert moved_panel.position.x == 3
        assert moved_panel.position.y == 4
        assert moved_panel.position.width == 8
        assert moved_panel.position.height == 6
    
    def test_resize_panel(self):
        """Test resizing panel"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Test Panel"
        )
        
        resized_panel = self.engine.resize_panel(
            dashboard=dashboard,
            panel_id=panel.id,
            new_width=10,
            new_height=8
        )
        
        assert resized_panel.position.width == 10
        assert resized_panel.position.height == 8
        assert resized_panel.position.x == panel.position.x
        assert resized_panel.position.y == panel.position.y
    
    def test_optimize_layout(self):
        """Test layout optimization"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        # Add some panels
        panel1 = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Panel 1",
            position=GridPosition(x=0, y=5, width=6, height=4)
        )
        
        panel2 = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.TABLE,
            title="Panel 2",
            position=GridPosition(x=6, y=5, width=6, height=4)
        )
        
        # Optimize layout
        optimized_dashboard = self.engine.optimize_layout(dashboard)
        
        assert optimized_dashboard.id == dashboard.id
        assert len(optimized_dashboard.panels) == 2
        
        # Check that panels have been compacted vertically
        optimized_panel1 = optimized_dashboard.panels[0]
        optimized_panel2 = optimized_dashboard.panels[1]
        
        # Panel positions should be optimized
        assert optimized_panel1.position.y <= 5
        assert optimized_panel2.position.y <= 5
    
    def test_get_layout_for_breakpoint(self):
        """Test getting layout for specific breakpoint"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Test Panel"
        )
        
        layout = self.engine.get_layout_for_breakpoint(
            dashboard=dashboard,
            breakpoint=BreakpointSize.MD
        )
        
        assert len(layout) == 1
        assert layout[0]['i'] == panel.id
        assert 'x' in layout[0]
        assert 'y' in layout[0]
        assert 'w' in layout[0]
        assert 'h' in layout[0]


class TestCollisionDetector:
    """Test collision detection functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.detector = CollisionDetector()
        self.layout_config = LayoutConfig(layout_type=LayoutType.GRID)
        self.dashboard = Dashboard(
            id=str(uuid.uuid4()),
            title="Test Dashboard",
            description="Test",
            layout_config=self.layout_config
        )
    
    def test_no_collision_empty_dashboard(self):
        """Test no collision on empty dashboard"""
        position = GridPosition(x=0, y=0, width=6, height=4)
        resolved_position = self.detector.resolve_collision(
            dashboard=self.dashboard,
            position=position
        )
        
        assert resolved_position.x == position.x
        assert resolved_position.y == position.y
        assert resolved_position.width == position.width
        assert resolved_position.height == position.height
    
    def test_collision_detection(self):
        """Test collision detection with existing panels"""
        # Add existing panel
        existing_panel = Panel(
            id=str(uuid.uuid4()),
            panel_type=PanelType.CHART,
            title="Existing Panel",
            position=GridPosition(x=0, y=0, width=6, height=4)
        )
        self.dashboard.panels.append(existing_panel)
        
        # Try to place new panel at same position
        position = GridPosition(x=0, y=0, width=6, height=4)
        resolved_position = self.detector.resolve_collision(
            dashboard=self.dashboard,
            position=position
        )
        
        # Should be moved to avoid collision
        assert resolved_position.x != position.x or resolved_position.y != position.y
    
    def test_collision_resolution_with_exclusion(self):
        """Test collision resolution excluding specific panel"""
        # Add two panels
        panel1 = Panel(
            id="panel1",
            panel_type=PanelType.CHART,
            title="Panel 1",
            position=GridPosition(x=0, y=0, width=6, height=4)
        )
        panel2 = Panel(
            id="panel2",
            panel_type=PanelType.TABLE,
            title="Panel 2",
            position=GridPosition(x=6, y=0, width=6, height=4)
        )
        self.dashboard.panels.extend([panel1, panel2])
        
        # Try to move panel1 to panel2's position
        position = GridPosition(x=6, y=0, width=6, height=4)
        resolved_position = self.detector.resolve_collision(
            dashboard=self.dashboard,
            position=position,
            exclude_panel_id="panel1"
        )
        
        # Should still detect collision with panel2
        assert resolved_position.x != position.x or resolved_position.y != position.y


class TestResponsiveOptimizer:
    """Test responsive optimization functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.optimizer = ResponsiveOptimizer()
        self.layout_config = LayoutConfig(layout_type=LayoutType.GRID)
        self.dashboard = Dashboard(
            id=str(uuid.uuid4()),
            title="Test Dashboard",
            description="Test",
            layout_config=self.layout_config
        )
    
    def test_optimize_responsive_layout(self):
        """Test responsive layout optimization"""
        # Add panel
        panel = Panel(
            id=str(uuid.uuid4()),
            panel_type=PanelType.CHART,
            title="Test Panel",
            position=GridPosition(x=0, y=0, width=6, height=4)
        )
        self.dashboard.panels.append(panel)
        
        # Optimize
        optimized_dashboard = self.optimizer.optimize_responsive_layout(self.dashboard)
        
        assert optimized_dashboard.id == self.dashboard.id
        
        # Check that responsive positions were created
        optimized_panel = optimized_dashboard.panels[0]
        assert len(optimized_panel.responsive_positions) > 0
        assert BreakpointSize.XS in optimized_panel.responsive_positions
        assert BreakpointSize.SM in optimized_panel.responsive_positions
        assert BreakpointSize.MD in optimized_panel.responsive_positions
    
    def test_responsive_position_scaling(self):
        """Test responsive position scaling for different breakpoints"""
        # Add wide panel
        panel = Panel(
            id=str(uuid.uuid4()),
            panel_type=PanelType.CHART,
            title="Wide Panel",
            position=GridPosition(x=0, y=0, width=12, height=4)
        )
        self.dashboard.panels.append(panel)
        
        # Optimize
        optimized_dashboard = self.optimizer.optimize_responsive_layout(self.dashboard)
        optimized_panel = optimized_dashboard.panels[0]
        
        # Check that small breakpoints have narrower widths
        xs_position = optimized_panel.responsive_positions[BreakpointSize.XS]
        xl_position = optimized_panel.responsive_positions[BreakpointSize.XL]
        
        assert xs_position.width <= xl_position.width
        assert xs_position.width <= 4  # XS has 4 columns max


class TestLayoutTemplateManager:
    """Test layout template management"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.template_manager = LayoutTemplateManager()
        self.layout_config = LayoutConfig(layout_type=LayoutType.GRID)
        self.dashboard = Dashboard(
            id=str(uuid.uuid4()),
            title="Test Dashboard",
            description="Test",
            layout_config=self.layout_config
        )
    
    def test_save_template(self):
        """Test saving dashboard as template"""
        # Add panel to dashboard
        panel = Panel(
            id=str(uuid.uuid4()),
            panel_type=PanelType.CHART,
            title="Test Panel",
            position=GridPosition(x=0, y=0, width=6, height=4)
        )
        self.dashboard.panels.append(panel)
        
        # Save as template
        success = self.template_manager.save_template(
            template_name="test_template",
            dashboard=self.dashboard,
            description="Test template"
        )
        
        assert success is True
        assert "test_template" in self.template_manager.custom_templates
    
    def test_get_template(self):
        """Test getting saved template"""
        # Save template first
        self.template_manager.save_template(
            template_name="test_template",
            dashboard=self.dashboard,
            description="Test template"
        )
        
        # Get template
        template = self.template_manager.get_template("test_template")
        
        assert template is not None
        assert template['name'] == "test_template"
        assert template['description'] == "Test template"
        assert 'layout_config' in template
        assert 'panels' in template
    
    def test_get_nonexistent_template(self):
        """Test getting non-existent template"""
        template = self.template_manager.get_template("nonexistent")
        assert template is None
    
    def test_list_templates(self):
        """Test listing all templates"""
        # Save multiple templates
        self.template_manager.save_template(
            template_name="template1",
            dashboard=self.dashboard
        )
        self.template_manager.save_template(
            template_name="template2",
            dashboard=self.dashboard
        )
        
        templates = self.template_manager.list_templates()
        assert len(templates) == 2
        assert "template1" in templates
        assert "template2" in templates
    
    def test_delete_template(self):
        """Test deleting template"""
        # Save template
        self.template_manager.save_template(
            template_name="test_template",
            dashboard=self.dashboard
        )
        
        # Delete template
        success = self.template_manager.delete_template("test_template")
        assert success is True
        assert "test_template" not in self.template_manager.custom_templates
    
    def test_delete_nonexistent_template(self):
        """Test deleting non-existent template"""
        success = self.template_manager.delete_template("nonexistent")
        assert success is False


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = DashboardLayoutEngine()
    
    def test_dashboard_with_no_panels(self):
        """Test dashboard operations with no panels"""
        dashboard = self.engine.create_dashboard(
            title="Empty Dashboard",
            layout_type=LayoutType.GRID
        )
        
        # Test optimize with no panels
        optimized = self.engine.optimize_layout(dashboard)
        assert len(optimized.panels) == 0
        
        # Test get layout with no panels
        layout = self.engine.get_layout_for_breakpoint(dashboard, BreakpointSize.MD)
        assert len(layout) == 0
    
    def test_panel_with_extreme_dimensions(self):
        """Test panel with extreme dimensions"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        # Add panel with very large dimensions
        large_position = GridPosition(x=0, y=0, width=20, height=20)
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Large Panel",
            position=large_position
        )
        
        assert panel.position.width == 20
        assert panel.position.height == 20
    
    def test_collision_with_overlapping_panels(self):
        """Test collision detection with overlapping panels"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        # Add overlapping panels
        panel1 = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.CHART,
            title="Panel 1",
            position=GridPosition(x=0, y=0, width=8, height=6)
        )
        
        panel2 = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.TABLE,
            title="Panel 2",
            position=GridPosition(x=4, y=3, width=8, height=6)
        )
        
        # Panels should not overlap due to collision detection
        assert not self._panels_overlap(panel1, panel2)
    
    def _panels_overlap(self, panel1, panel2):
        """Helper method to check if two panels overlap"""
        pos1 = panel1.position
        pos2 = panel2.position
        
        return not (
            pos1.x + pos1.width <= pos2.x or
            pos2.x + pos2.width <= pos1.x or
            pos1.y + pos1.height <= pos2.y or
            pos2.y + pos2.height <= pos1.y
        )
    
    def test_responsive_optimization_with_small_panels(self):
        """Test responsive optimization with very small panels"""
        dashboard = self.engine.create_dashboard(
            title="Test Dashboard",
            layout_type=LayoutType.GRID
        )
        
        # Add very small panel
        panel = self.engine.add_panel(
            dashboard=dashboard,
            panel_type=PanelType.METRIC,
            title="Small Panel",
            position=GridPosition(x=0, y=0, width=1, height=1)
        )
        
        # Optimize for responsive
        optimized = self.engine.optimize_layout(dashboard)
        
        # Panel should still exist and be valid
        assert len(optimized.panels) == 1
        assert optimized.panels[0].position.width >= 1
        assert optimized.panels[0].position.height >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])