"""
Comprehensive Test Suite for Dashboard Builder Service

This test suite provides complete coverage for the drag-and-drop dashboard builder
functionality including:
- Drag-and-drop operations
- Panel resize and move operations
- Panel configuration management
- Template-based dashboard creation
- Collaboration features
- Undo/redo functionality
"""

import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch

from app.services.dashboard_builder import (
    DashboardBuilderService,
    DragOperation,
    ResizeOperation,
    PanelConfiguration,
    CollaborationEvent
)
from app.models.chart import (
    DashboardGridPosition,
    PanelType,
    ChartType,
    LayoutType
)


class TestDashboardBuilderService:
    """Test cases for DashboardBuilderService"""
    
    def setup_method(self):
        """Setup test environment before each test"""
        self.builder_service = DashboardBuilderService()
        self.test_dashboard_id = str(uuid4())
        self.test_user_id = "test_user_123"
        self.test_panel_id = str(uuid4())
    
    def test_create_builder_session_success(self):
        """Test successful builder session creation"""
        result = self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Verify session structure
        assert "session" in result
        assert "grid_config" in result
        assert "panel_types" in result
        assert "chart_types" in result
        
        # Verify session configuration
        session = result["session"]
        assert session["dashboard_id"] == self.test_dashboard_id
        assert session["user_id"] == self.test_user_id
        assert session["is_active"] is True
        assert session["collaboration_enabled"] is True
        assert session["auto_save_enabled"] is True
        
        # Verify permissions
        permissions = session["permissions"]
        assert permissions["can_edit"] is True
        assert permissions["can_add_panels"] is True
        assert permissions["can_remove_panels"] is True
        assert permissions["can_modify_layout"] is True
        assert permissions["can_share"] is True
        
        # Verify grid configuration
        grid_config = result["grid_config"]
        assert grid_config["columns"] == 12
        assert grid_config["row_height"] == 60
        assert "breakpoints" in grid_config
        assert "cols" in grid_config
        
        # Verify panel and chart types
        assert len(result["panel_types"]) > 0
        assert len(result["chart_types"]) > 0
        
        # Verify internal state
        assert self.test_dashboard_id in self.builder_service.collaboration_state
        assert self.test_dashboard_id in self.builder_service.undo_stack
        assert self.test_dashboard_id in self.builder_service.redo_stack
    
    def test_handle_drag_operation_move_success(self):
        """Test successful drag operation for moving panels"""
        # Create builder session first
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Create drag operation
        drag_operation = DragOperation(
            panel_id=self.test_panel_id,
            source_position=DashboardGridPosition(x=0, y=0, width=4, height=3),
            target_position=DashboardGridPosition(x=2, y=1, width=4, height=3),
            dashboard_id=self.test_dashboard_id,
            operation_type="move"
        )
        
        result = self.builder_service.handle_drag_operation(drag_operation)
        
        # Verify successful operation
        assert result["success"] is True
        assert result["layout_valid"] is True
        assert "operation" in result
        assert "result" in result
        assert "timestamp" in result
        
        # Verify operation details
        operation_data = result["operation"]
        assert operation_data["panel_id"] == self.test_panel_id
        assert operation_data["operation_type"] == "move"
        
        # Verify result details
        operation_result = result["result"]
        assert operation_result["panel_id"] == self.test_panel_id
        assert operation_result["layout_updated"] is True
    
    def test_handle_drag_operation_invalid_position(self):
        """Test drag operation with invalid target position"""
        # Create builder session first
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Create invalid drag operation (x position out of bounds)
        drag_operation = DragOperation(
            panel_id=self.test_panel_id,
            source_position=DashboardGridPosition(x=0, y=0, width=4, height=3),
            target_position=DashboardGridPosition(x=15, y=1, width=4, height=3),  # x=15 > 12 columns
            dashboard_id=self.test_dashboard_id,
            operation_type="move"
        )
        
        result = self.builder_service.handle_drag_operation(drag_operation)
        
        # Verify failed operation
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Invalid drag operation"
    
    def test_handle_resize_operation_success(self):
        """Test successful panel resize operation"""
        # Create builder session first
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Create resize operation
        resize_operation = ResizeOperation(
            panel_id=self.test_panel_id,
            dashboard_id=self.test_dashboard_id,
            new_width=8,
            new_height=6,
            maintain_aspect_ratio=True
        )
        
        result = self.builder_service.handle_resize_operation(resize_operation)
        
        # Verify successful operation
        assert result["success"] is True
        assert "new_dimensions" in result
        assert "collisions_detected" in result
        assert "collision_resolution" in result
        assert "result" in result
        assert "timestamp" in result
        
        # Verify new dimensions
        new_dimensions = result["new_dimensions"]
        assert new_dimensions["width"] == 8
        assert new_dimensions["height"] == 6
        
        # Verify operation details
        operation_data = result["operation"]
        assert operation_data["panel_id"] == self.test_panel_id
        assert operation_data["new_width"] == 8
        assert operation_data["new_height"] == 6
        assert operation_data["maintain_aspect_ratio"] is True
    
    def test_handle_resize_operation_invalid_dimensions(self):
        """Test resize operation with invalid dimensions"""
        # Create builder session first
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Create invalid resize operation (width > 12)
        resize_operation = ResizeOperation(
            panel_id=self.test_panel_id,
            dashboard_id=self.test_dashboard_id,
            new_width=15,  # Invalid: > 12
            new_height=6,
            maintain_aspect_ratio=True
        )
        
        result = self.builder_service.handle_resize_operation(resize_operation)
        
        # Verify failed operation
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Invalid resize operation"
    
    def test_add_panel_to_dashboard_success(self):
        """Test successful panel addition to dashboard"""
        # Create builder session first
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Create panel configuration
        panel_config = PanelConfiguration(
            panel_id=self.test_panel_id,
            panel_type=PanelType.CHART,
            title="Test Chart Panel",
            chart_type=ChartType.LINE,
            data_source="test_index",
            query="search index=test_index | stats count by host",
            refresh_interval=300,
            styling={"background": "white", "border": "1px solid #ccc"},
            interactions={"zoom": True, "drill_down": True}
        )
        
        result = self.builder_service.add_panel_to_dashboard(
            self.test_dashboard_id,
            panel_config
        )
        
        # Verify successful addition
        assert result["success"] is True
        assert result["layout_valid"] is True
        assert "panel" in result
        assert "position" in result
        assert "timestamp" in result
        
        # Verify panel details
        panel_data = result["panel"]
        assert panel_data["id"] == self.test_panel_id
        assert panel_data["type"] == PanelType.CHART.value
        assert panel_data["title"] == "Test Chart Panel"
        assert panel_data["chart_type"] == ChartType.LINE.value
        assert panel_data["data_source"] == "test_index"
        assert panel_data["refresh_interval"] == 300
        
        # Verify position details
        position_data = result["position"]
        assert "x" in position_data
        assert "y" in position_data
        assert "width" in position_data
        assert "height" in position_data
    
    def test_add_panel_auto_id_generation(self):
        """Test panel addition with automatic ID generation"""
        # Create builder session first
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Create panel configuration without panel_id
        panel_config = PanelConfiguration(
            panel_id="",  # Empty ID for auto-generation
            panel_type=PanelType.METRIC,
            title="Test Metric Panel",
            styling={"fontSize": "24px"},
            interactions={}
        )
        
        result = self.builder_service.add_panel_to_dashboard(
            self.test_dashboard_id,
            panel_config
        )
        
        # Verify successful addition with auto-generated ID
        assert result["success"] is True
        panel_data = result["panel"]
        assert len(panel_data["id"]) > 0  # ID should be generated
        assert panel_data["type"] == PanelType.METRIC.value
        assert panel_data["title"] == "Test Metric Panel"
    
    def test_remove_panel_from_dashboard_success(self):
        """Test successful panel removal from dashboard"""
        # Create builder session first
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        result = self.builder_service.remove_panel_from_dashboard(
            self.test_dashboard_id,
            self.test_panel_id,
            optimize_layout=True
        )
        
        # Verify successful removal
        assert result["success"] is True
        assert result["removed_panel_id"] == self.test_panel_id
        assert result["layout_optimized"] is True
        assert "optimization_result" in result
        assert "timestamp" in result
        
        # Verify optimization result
        optimization_result = result["optimization_result"]
        assert "layout_optimized" in optimization_result
        assert "panels_moved" in optimization_result
        assert "space_recovered" in optimization_result
    
    def test_remove_panel_without_optimization(self):
        """Test panel removal without layout optimization"""
        # Create builder session first
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        result = self.builder_service.remove_panel_from_dashboard(
            self.test_dashboard_id,
            self.test_panel_id,
            optimize_layout=False
        )
        
        # Verify successful removal without optimization
        assert result["success"] is True
        assert result["removed_panel_id"] == self.test_panel_id
        assert result["layout_optimized"] is False
        assert result["optimization_result"] == {}
    
    def test_update_panel_configuration_success(self):
        """Test successful panel configuration update"""
        # Create builder session first
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Define configuration updates
        config_updates = {
            "title": "Updated Panel Title",
            "refresh_interval": 600,
            "styling": {"background": "lightblue", "fontSize": "16px"},
            "interactions": {"zoom": False, "filter": True}
        }
        
        result = self.builder_service.update_panel_configuration(
            self.test_dashboard_id,
            self.test_panel_id,
            config_updates
        )
        
        # Verify successful update
        assert result["success"] is True
        assert result["panel_id"] == self.test_panel_id
        assert result["updates_applied"] == config_updates
        assert "result" in result
        assert "timestamp" in result
        
        # Verify update result
        update_result = result["result"]
        assert update_result["updates_applied"] is True
        assert update_result["panel_id"] == self.test_panel_id
        assert update_result["updated_fields"] == list(config_updates.keys())
    
    def test_create_dashboard_from_template_template_not_found(self):
        """Test dashboard creation with non-existent template"""
        dashboard_config = {
            "title": "Test Dashboard",
            "description": "Dashboard from template",
            "user_id": self.test_user_id
        }
        
        result = self.builder_service.create_dashboard_from_template(
            "non_existent_template",
            dashboard_config
        )
        
        # Verify failure due to missing template
        assert result["success"] is False
        assert "error" in result
        assert "Template 'non_existent_template' not found" in result["error"]
    
    def test_get_collaboration_state_no_active_users(self):
        """Test getting collaboration state with no active users"""
        result = self.builder_service.get_collaboration_state(self.test_dashboard_id)
        
        # Verify collaboration state structure
        assert result["dashboard_id"] == self.test_dashboard_id
        assert result["active_users"] == []
        assert result["recent_events"] == []
        assert result["collaboration_enabled"] is False
        assert "timestamp" in result
    
    def test_get_collaboration_state_with_active_users(self):
        """Test getting collaboration state with active users"""
        # Create multiple builder sessions
        session1 = self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            "user1"
        )
        session2 = self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            "user2"
        )
        
        result = self.builder_service.get_collaboration_state(self.test_dashboard_id)
        
        # Verify collaboration state with active users
        assert result["dashboard_id"] == self.test_dashboard_id
        assert len(result["active_users"]) == 2
        assert result["collaboration_enabled"] is True
        
        # Verify active user details
        active_users = result["active_users"]
        user_ids = [user["user_id"] for user in active_users]
        assert "user1" in user_ids
        assert "user2" in user_ids
        
        # Verify user permissions
        for user in active_users:
            assert "session_id" in user
            assert "last_activity" in user
            assert "permissions" in user
            permissions = user["permissions"]
            assert permissions["can_edit"] is True
            assert permissions["can_add_panels"] is True
    
    def test_undo_last_operation_no_operations(self):
        """Test undo operation with no previous operations"""
        result = self.builder_service.undo_last_operation(self.test_dashboard_id)
        
        # Verify failure due to no operations
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "No operations to undo"
    
    def test_undo_last_operation_success(self):
        """Test successful undo operation"""
        # Create builder session and perform an operation
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Simulate saving state for undo
        self.builder_service._save_state_for_undo(self.test_dashboard_id)
        
        result = self.builder_service.undo_last_operation(self.test_dashboard_id)
        
        # Verify successful undo
        assert result["success"] is True
        assert result["can_redo"] is True
        assert "restored_state" in result
        assert "timestamp" in result
        
        # Verify restored state structure
        restored_state = result["restored_state"]
        assert restored_state["dashboard_id"] == self.test_dashboard_id
        assert "state_timestamp" in restored_state
        assert "layout" in restored_state
        assert "panels" in restored_state
    
    def test_redo_last_operation_no_operations(self):
        """Test redo operation with no operations to redo"""
        result = self.builder_service.redo_last_operation(self.test_dashboard_id)
        
        # Verify failure due to no operations to redo
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "No operations to redo"
    
    def test_undo_redo_cycle(self):
        """Test complete undo/redo cycle"""
        # Create builder session
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Simulate multiple operations
        self.builder_service._save_state_for_undo(self.test_dashboard_id)
        self.builder_service._save_state_for_undo(self.test_dashboard_id)
        
        # Test undo
        undo_result = self.builder_service.undo_last_operation(self.test_dashboard_id)
        assert undo_result["success"] is True
        assert undo_result["can_redo"] is True
        
        # Test redo
        redo_result = self.builder_service.redo_last_operation(self.test_dashboard_id)
        assert redo_result["success"] is True
        assert redo_result["can_undo"] is True
    
    def test_drag_operation_validation(self):
        """Test drag operation validation logic"""
        # Test valid operation
        valid_operation = DragOperation(
            panel_id=self.test_panel_id,
            source_position=DashboardGridPosition(x=0, y=0, width=4, height=3),
            target_position=DashboardGridPosition(x=2, y=1, width=4, height=3),
            dashboard_id=self.test_dashboard_id,
            operation_type="move"
        )
        assert self.builder_service._validate_drag_operation(valid_operation) is True
        
        # Test invalid operation (x position out of bounds)
        invalid_operation_x = DragOperation(
            panel_id=self.test_panel_id,
            source_position=DashboardGridPosition(x=0, y=0, width=4, height=3),
            target_position=DashboardGridPosition(x=15, y=1, width=4, height=3),
            dashboard_id=self.test_dashboard_id,
            operation_type="move"
        )
        assert self.builder_service._validate_drag_operation(invalid_operation_x) is False
        
        # Test invalid operation (negative y position)
        invalid_operation_y = DragOperation(
            panel_id=self.test_panel_id,
            source_position=DashboardGridPosition(x=0, y=0, width=4, height=3),
            target_position=DashboardGridPosition(x=2, y=-1, width=4, height=3),
            dashboard_id=self.test_dashboard_id,
            operation_type="move"
        )
        assert self.builder_service._validate_drag_operation(invalid_operation_y) is False
        
        # Test invalid operation type
        invalid_operation_type = DragOperation(
            panel_id=self.test_panel_id,
            source_position=DashboardGridPosition(x=0, y=0, width=4, height=3),
            target_position=DashboardGridPosition(x=2, y=1, width=4, height=3),
            dashboard_id=self.test_dashboard_id,
            operation_type="invalid_type"
        )
        assert self.builder_service._validate_drag_operation(invalid_operation_type) is False
    
    def test_resize_operation_validation(self):
        """Test resize operation validation logic"""
        # Test valid resize operation
        valid_resize = ResizeOperation(
            panel_id=self.test_panel_id,
            dashboard_id=self.test_dashboard_id,
            new_width=8,
            new_height=6
        )
        assert self.builder_service._validate_resize_operation(valid_resize) is True
        
        # Test invalid width (too large)
        invalid_width = ResizeOperation(
            panel_id=self.test_panel_id,
            dashboard_id=self.test_dashboard_id,
            new_width=15,
            new_height=6
        )
        assert self.builder_service._validate_resize_operation(invalid_width) is False
        
        # Test invalid height (zero)
        invalid_height = ResizeOperation(
            panel_id=self.test_panel_id,
            dashboard_id=self.test_dashboard_id,
            new_width=8,
            new_height=0
        )
        assert self.builder_service._validate_resize_operation(invalid_height) is False
    
    def test_optimal_position_calculation(self):
        """Test optimal position calculation for new panels"""
        position = self.builder_service._calculate_optimal_position(
            self.test_dashboard_id, 
            PanelType.CHART
        )
        
        # Verify position structure
        assert hasattr(position, 'x')
        assert hasattr(position, 'y')
        assert hasattr(position, 'width')
        assert hasattr(position, 'height')
        assert hasattr(position, 'breakpoint')
        
        # Verify position values are within valid ranges
        assert 0 <= position.x < 12
        assert position.y >= 0
        assert 1 <= position.width <= 12
        assert position.height >= 1
        assert position.breakpoint in ["xs", "sm", "md", "lg", "xl"]
    
    def test_collaboration_event_tracking(self):
        """Test collaboration event tracking functionality"""
        # Create builder session
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Create and execute drag operation
        drag_operation = DragOperation(
            panel_id=self.test_panel_id,
            source_position=DashboardGridPosition(x=0, y=0, width=4, height=3),
            target_position=DashboardGridPosition(x=2, y=1, width=4, height=3),
            dashboard_id=self.test_dashboard_id,
            operation_type="move"
        )
        
        # Execute operation (this should trigger collaboration state update)
        result = self.builder_service.handle_drag_operation(drag_operation)
        assert result["success"] is True
        
        # Verify collaboration state was updated
        collaboration_state = self.builder_service.get_collaboration_state(self.test_dashboard_id)
        assert len(collaboration_state["recent_events"]) > 0
        
        # Verify event structure
        recent_event = collaboration_state["recent_events"][0]
        assert recent_event["dashboard_id"] == self.test_dashboard_id
        assert recent_event["event_type"] == "layout_change"
        assert "event_data" in recent_event
        assert "timestamp" in recent_event
    
    def test_undo_stack_size_limit(self):
        """Test undo stack size limiting functionality"""
        # Create builder session
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Add many states to exceed limit
        for i in range(55):  # Exceed the 50 limit
            self.builder_service._save_state_for_undo(self.test_dashboard_id)
        
        # Verify stack size is limited
        undo_stack = self.builder_service.undo_stack[self.test_dashboard_id]
        assert len(undo_stack) == 50  # Should be limited to 50
    
    def test_collaboration_history_limit(self):
        """Test collaboration history size limiting"""
        # Create builder session
        self.builder_service.create_builder_session(
            self.test_dashboard_id, 
            self.test_user_id
        )
        
        # Add many collaboration events to exceed limit
        for i in range(105):  # Exceed the 100 limit
            drag_operation = DragOperation(
                panel_id=f"panel_{i}",
                source_position=DashboardGridPosition(x=0, y=i, width=4, height=3),
                target_position=DashboardGridPosition(x=1, y=i, width=4, height=3),
                dashboard_id=self.test_dashboard_id,
                operation_type="move"
            )
            self.builder_service._update_collaboration_state(drag_operation)
        
        # Verify collaboration history is limited
        collaboration_events = self.builder_service.collaboration_state[self.test_dashboard_id]
        assert len(collaboration_events) == 100  # Should be limited to 100


class TestDragOperation:
    """Test cases for DragOperation model"""
    
    def test_drag_operation_creation(self):
        """Test DragOperation model creation"""
        source_pos = DashboardGridPosition(x=0, y=0, width=4, height=3)
        target_pos = DashboardGridPosition(x=2, y=1, width=4, height=3)
        
        operation = DragOperation(
            panel_id="test_panel",
            source_position=source_pos,
            target_position=target_pos,
            dashboard_id="test_dashboard",
            operation_type="move"
        )
        
        assert operation.panel_id == "test_panel"
        assert operation.source_position == source_pos
        assert operation.target_position == target_pos
        assert operation.dashboard_id == "test_dashboard"
        assert operation.operation_type == "move"
        assert isinstance(operation.timestamp, datetime)
    
    def test_drag_operation_default_values(self):
        """Test DragOperation model default values"""
        source_pos = DashboardGridPosition(x=0, y=0, width=4, height=3)
        target_pos = DashboardGridPosition(x=2, y=1, width=4, height=3)
        
        operation = DragOperation(
            panel_id="test_panel",
            source_position=source_pos,
            target_position=target_pos,
            dashboard_id="test_dashboard"
            # operation_type not specified - should default to "move"
        )
        
        assert operation.operation_type == "move"
        assert isinstance(operation.timestamp, datetime)


class TestResizeOperation:
    """Test cases for ResizeOperation model"""
    
    def test_resize_operation_creation(self):
        """Test ResizeOperation model creation"""
        operation = ResizeOperation(
            panel_id="test_panel",
            dashboard_id="test_dashboard",
            new_width=8,
            new_height=6,
            maintain_aspect_ratio=False
        )
        
        assert operation.panel_id == "test_panel"
        assert operation.dashboard_id == "test_dashboard"
        assert operation.new_width == 8
        assert operation.new_height == 6
        assert operation.maintain_aspect_ratio is False
        assert isinstance(operation.timestamp, datetime)
    
    def test_resize_operation_validation(self):
        """Test ResizeOperation model validation"""
        # Test valid dimensions
        operation = ResizeOperation(
            panel_id="test_panel",
            dashboard_id="test_dashboard",
            new_width=12,  # Maximum valid width
            new_height=20  # Maximum valid height
        )
        assert operation.new_width == 12
        assert operation.new_height == 20
        
        # Test that invalid dimensions would be caught by Pydantic validation
        with pytest.raises(ValueError):
            ResizeOperation(
                panel_id="test_panel",
                dashboard_id="test_dashboard",
                new_width=0,  # Invalid: less than minimum
                new_height=6
            )
        
        with pytest.raises(ValueError):
            ResizeOperation(
                panel_id="test_panel",
                dashboard_id="test_dashboard",
                new_width=8,
                new_height=25  # Invalid: greater than maximum
            )


class TestPanelConfiguration:
    """Test cases for PanelConfiguration model"""
    
    def test_panel_configuration_creation(self):
        """Test PanelConfiguration model creation"""
        config = PanelConfiguration(
            panel_id="test_panel",
            panel_type=PanelType.CHART,
            title="Test Chart Panel",
            chart_type=ChartType.LINE,
            data_source="test_index",
            query="search index=test_index | stats count by host",
            refresh_interval=600,
            styling={"background": "white"},
            interactions={"zoom": True}
        )
        
        assert config.panel_id == "test_panel"
        assert config.panel_type == PanelType.CHART
        assert config.title == "Test Chart Panel"
        assert config.chart_type == ChartType.LINE
        assert config.data_source == "test_index"
        assert config.query == "search index=test_index | stats count by host"
        assert config.refresh_interval == 600
        assert config.styling == {"background": "white"}
        assert config.interactions == {"zoom": True}
    
    def test_panel_configuration_defaults(self):
        """Test PanelConfiguration model default values"""
        config = PanelConfiguration(
            panel_id="test_panel",
            panel_type=PanelType.TEXT,
            title="Test Text Panel"
        )
        
        assert config.refresh_interval == 300  # Default value
        assert config.styling == {}  # Default empty dict
        assert config.interactions == {}  # Default empty dict
        assert config.chart_type is None  # Default None
        assert config.data_source is None  # Default None
        assert config.query is None  # Default None
    
    def test_panel_configuration_refresh_interval_validation(self):
        """Test refresh interval validation"""
        # Test valid refresh interval
        config = PanelConfiguration(
            panel_id="test_panel",
            panel_type=PanelType.METRIC,
            title="Test Metric Panel",
            refresh_interval=60  # Valid: >= 30
        )
        assert config.refresh_interval == 60
        
        # Test that invalid refresh interval would be caught by Pydantic validation
        with pytest.raises(ValueError):
            PanelConfiguration(
                panel_id="test_panel",
                panel_type=PanelType.METRIC,
                title="Test Metric Panel",
                refresh_interval=15  # Invalid: < 30
            )


class TestCollaborationEvent:
    """Test cases for CollaborationEvent model"""
    
    def test_collaboration_event_creation(self):
        """Test CollaborationEvent model creation"""
        event = CollaborationEvent(
            user_id="test_user",
            dashboard_id="test_dashboard",
            event_type="panel_select",
            event_data={"panel_id": "test_panel", "selected": True}
        )
        
        assert event.user_id == "test_user"
        assert event.dashboard_id == "test_dashboard"
        assert event.event_type == "panel_select"
        assert event.event_data == {"panel_id": "test_panel", "selected": True}
        assert isinstance(event.timestamp, datetime)
    
    def test_collaboration_event_type_validation(self):
        """Test collaboration event type validation"""
        # Test valid event types
        valid_event_types = ["cursor_move", "panel_select", "panel_edit", "layout_change"]
        
        for event_type in valid_event_types:
            event = CollaborationEvent(
                user_id="test_user",
                dashboard_id="test_dashboard",
                event_type=event_type,
                event_data={}
            )
            assert event.event_type == event_type
        
        # Test that invalid event type would be caught by Pydantic validation
        with pytest.raises(ValueError):
            CollaborationEvent(
                user_id="test_user",
                dashboard_id="test_dashboard",
                event_type="invalid_event",  # Invalid event type
                event_data={}
            )


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main(["-v", __file__])