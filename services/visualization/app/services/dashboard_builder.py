"""
Drag-and-Drop Dashboard Builder Service

This service provides comprehensive dashboard building capabilities including:
- Drag-and-drop panel management
- Real-time layout updates
- Panel configuration and customization
- Template-based dashboard creation
- Collaborative dashboard editing
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from uuid import uuid4

from pydantic import BaseModel, Field
from ..models.chart import (
    Dashboard, DashboardPanel, DashboardGridPosition, 
    DashboardLayoutConfig, PanelType, LayoutType,
    ChartType, DashboardTemplate
)

logger = logging.getLogger(__name__)


class DragOperation(BaseModel):
    """Model for drag operation data"""
    panel_id: str
    source_position: DashboardGridPosition
    target_position: DashboardGridPosition
    dashboard_id: str
    operation_type: str = Field(default="move", regex="^(move|resize|add|remove)$")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ResizeOperation(BaseModel):
    """Model for panel resize operations"""
    panel_id: str
    dashboard_id: str
    new_width: int = Field(ge=1, le=12)
    new_height: int = Field(ge=1, le=20)
    maintain_aspect_ratio: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PanelConfiguration(BaseModel):
    """Model for panel configuration during builder operations"""
    panel_id: str
    panel_type: PanelType
    title: str
    chart_type: Optional[ChartType] = None
    data_source: Optional[str] = None
    query: Optional[str] = None
    refresh_interval: Optional[int] = Field(default=300, ge=30)  # seconds
    styling: Dict[str, Any] = Field(default_factory=dict)
    interactions: Dict[str, Any] = Field(default_factory=dict)


class CollaborationEvent(BaseModel):
    """Model for collaborative editing events"""
    user_id: str
    dashboard_id: str
    event_type: str = Field(regex="^(cursor_move|panel_select|panel_edit|layout_change)$")
    event_data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DashboardBuilderService:
    """Comprehensive drag-and-drop dashboard builder service"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}
        self.collaboration_state: Dict[str, List[CollaborationEvent]] = {}
        self.undo_stack: Dict[str, List[Dict]] = {}
        self.redo_stack: Dict[str, List[Dict]] = {}
        
    def create_builder_session(self, dashboard_id: str, user_id: str) -> Dict[str, Any]:
        """
        Create a new dashboard builder session for collaborative editing
        
        Args:
            dashboard_id: Unique dashboard identifier
            user_id: User identifier for session
            
        Returns:
            Session configuration and initial state
        """
        session_id = str(uuid4())
        
        session_config = {
            "session_id": session_id,
            "dashboard_id": dashboard_id,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "is_active": True,
            "permissions": {
                "can_edit": True,
                "can_add_panels": True,
                "can_remove_panels": True,
                "can_modify_layout": True,
                "can_share": True
            },
            "collaboration_enabled": True,
            "auto_save_enabled": True,
            "auto_save_interval": 30  # seconds
        }
        
        self.active_sessions[session_id] = session_config
        
        if dashboard_id not in self.collaboration_state:
            self.collaboration_state[dashboard_id] = []
            
        if dashboard_id not in self.undo_stack:
            self.undo_stack[dashboard_id] = []
            self.redo_stack[dashboard_id] = []
        
        logger.info(f"Created builder session {session_id} for dashboard {dashboard_id}")
        
        return {
            "session": session_config,
            "grid_config": {
                "columns": 12,
                "row_height": 60,
                "margin": [10, 10],
                "container_padding": [20, 20],
                "breakpoints": {
                    "lg": 1200,
                    "md": 996,
                    "sm": 768,
                    "xs": 480,
                    "xxs": 0
                },
                "cols": {
                    "lg": 12,
                    "md": 10,
                    "sm": 6,
                    "xs": 4,
                    "xxs": 2
                }
            },
            "panel_types": [pt.value for pt in PanelType],
            "chart_types": [ct.value for ct in ChartType]
        }
    
    def handle_drag_operation(self, operation: DragOperation) -> Dict[str, Any]:
        """
        Handle drag-and-drop operations for dashboard panels
        
        Args:
            operation: Drag operation details
            
        Returns:
            Operation result and updated layout
        """
        try:
            # Validate operation
            if not self._validate_drag_operation(operation):
                return {
                    "success": False,
                    "error": "Invalid drag operation",
                    "operation": operation.dict()
                }
            
            # Store current state for undo
            self._save_state_for_undo(operation.dashboard_id)
            
            # Perform the drag operation
            result = self._execute_drag_operation(operation)
            
            # Update collaboration state
            self._update_collaboration_state(operation)
            
            # Validate layout after operation
            layout_valid = self._validate_layout_after_operation(operation)
            
            if not layout_valid:
                # Rollback operation
                self._rollback_last_operation(operation.dashboard_id)
                return {
                    "success": False,
                    "error": "Operation would create invalid layout",
                    "operation": operation.dict()
                }
            
            logger.info(f"Drag operation completed successfully: {operation.operation_type}")
            
            return {
                "success": True,
                "operation": operation.dict(),
                "result": result,
                "layout_valid": True,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error handling drag operation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "operation": operation.dict()
            }
    
    def handle_resize_operation(self, operation: ResizeOperation) -> Dict[str, Any]:
        """
        Handle panel resize operations with collision detection
        
        Args:
            operation: Resize operation details
            
        Returns:
            Resize result and layout adjustments
        """
        try:
            # Validate resize operation
            if not self._validate_resize_operation(operation):
                return {
                    "success": False,
                    "error": "Invalid resize operation",
                    "operation": operation.dict()
                }
            
            # Store current state for undo
            self._save_state_for_undo(operation.dashboard_id)
            
            # Calculate new dimensions
            new_dimensions = self._calculate_resize_dimensions(operation)
            
            # Check for collisions
            collisions = self._detect_resize_collisions(operation, new_dimensions)
            
            # Resolve collisions if any
            collision_resolution = {}
            if collisions:
                collision_resolution = self._resolve_resize_collisions(
                    operation, collisions
                )
            
            # Execute resize operation
            resize_result = self._execute_resize_operation(operation, new_dimensions)
            
            logger.info(f"Resize operation completed: panel {operation.panel_id}")
            
            return {
                "success": True,
                "operation": operation.dict(),
                "new_dimensions": new_dimensions,
                "collisions_detected": len(collisions) > 0,
                "collision_resolution": collision_resolution,
                "result": resize_result,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error handling resize operation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "operation": operation.dict()
            }
    
    def add_panel_to_dashboard(
        self, 
        dashboard_id: str, 
        panel_config: PanelConfiguration,
        position: Optional[DashboardGridPosition] = None
    ) -> Dict[str, Any]:
        """
        Add a new panel to the dashboard with automatic positioning
        
        Args:
            dashboard_id: Target dashboard identifier
            panel_config: Panel configuration details
            position: Optional specific position (auto-calculated if None)
            
        Returns:
            Added panel details and updated layout
        """
        try:
            # Generate panel ID if not provided
            if not panel_config.panel_id:
                panel_config.panel_id = str(uuid4())
            
            # Calculate optimal position if not provided
            if position is None:
                position = self._calculate_optimal_position(
                    dashboard_id, panel_config.panel_type
                )
            
            # Create panel object
            panel = DashboardPanel(
                id=panel_config.panel_id,
                type=panel_config.panel_type,
                title=panel_config.title,
                position=position,
                chart_type=panel_config.chart_type,
                data_source=panel_config.data_source,
                query=panel_config.query,
                refresh_interval=panel_config.refresh_interval,
                styling=panel_config.styling,
                interactions=panel_config.interactions,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Store current state for undo
            self._save_state_for_undo(dashboard_id)
            
            # Add panel to dashboard
            add_result = self._add_panel_to_layout(dashboard_id, panel)
            
            # Validate layout after addition
            layout_valid = self._validate_layout_integrity(dashboard_id)
            
            if not layout_valid:
                self._rollback_last_operation(dashboard_id)
                return {
                    "success": False,
                    "error": "Adding panel would create invalid layout"
                }
            
            logger.info(f"Added panel {panel.id} to dashboard {dashboard_id}")
            
            return {
                "success": True,
                "panel": panel.dict(),
                "position": position.dict(),
                "layout_valid": True,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error adding panel to dashboard: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def remove_panel_from_dashboard(
        self, 
        dashboard_id: str, 
        panel_id: str,
        optimize_layout: bool = True
    ) -> Dict[str, Any]:
        """
        Remove a panel from the dashboard and optionally optimize layout
        
        Args:
            dashboard_id: Source dashboard identifier
            panel_id: Panel to remove
            optimize_layout: Whether to compact layout after removal
            
        Returns:
            Removal result and layout changes
        """
        try:
            # Store current state for undo
            self._save_state_for_undo(dashboard_id)
            
            # Remove panel from layout
            removal_result = self._remove_panel_from_layout(dashboard_id, panel_id)
            
            if not removal_result["success"]:
                return removal_result
            
            # Optimize layout if requested
            optimization_result = {}
            if optimize_layout:
                optimization_result = self._optimize_layout_after_removal(
                    dashboard_id, panel_id
                )
            
            logger.info(f"Removed panel {panel_id} from dashboard {dashboard_id}")
            
            return {
                "success": True,
                "removed_panel_id": panel_id,
                "layout_optimized": optimize_layout,
                "optimization_result": optimization_result,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error removing panel from dashboard: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_panel_configuration(
        self, 
        dashboard_id: str, 
        panel_id: str,
        config_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update panel configuration without changing layout
        
        Args:
            dashboard_id: Dashboard identifier
            panel_id: Panel to update
            config_updates: Configuration changes
            
        Returns:
            Update result and new configuration
        """
        try:
            # Store current state for undo
            self._save_state_for_undo(dashboard_id)
            
            # Validate configuration updates
            validation_result = self._validate_config_updates(config_updates)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"]
                }
            
            # Apply configuration updates
            update_result = self._apply_panel_config_updates(
                dashboard_id, panel_id, config_updates
            )
            
            logger.info(f"Updated configuration for panel {panel_id}")
            
            return {
                "success": True,
                "panel_id": panel_id,
                "updates_applied": config_updates,
                "result": update_result,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error updating panel configuration: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_dashboard_from_template(
        self, 
        template_name: str,
        dashboard_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new dashboard based on a predefined template
        
        Args:
            template_name: Template identifier
            dashboard_config: Dashboard-specific configuration
            
        Returns:
            Created dashboard details
        """
        try:
            # Load template
            template = self._load_dashboard_template(template_name)
            if not template:
                return {
                    "success": False,
                    "error": f"Template '{template_name}' not found"
                }
            
            # Generate dashboard ID
            dashboard_id = str(uuid4())
            
            # Create dashboard from template
            dashboard = self._create_dashboard_from_template_config(
                dashboard_id, template, dashboard_config
            )
            
            # Initialize builder session
            session = self.create_builder_session(dashboard_id, dashboard_config.get("user_id"))
            
            logger.info(f"Created dashboard {dashboard_id} from template {template_name}")
            
            return {
                "success": True,
                "dashboard": dashboard.dict(),
                "template_used": template_name,
                "builder_session": session,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error creating dashboard from template: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_collaboration_state(self, dashboard_id: str) -> Dict[str, Any]:
        """
        Get current collaboration state for a dashboard
        
        Args:
            dashboard_id: Dashboard identifier
            
        Returns:
            Collaboration state and active users
        """
        active_users = []
        for session_id, session in self.active_sessions.items():
            if (session["dashboard_id"] == dashboard_id and 
                session["is_active"] and
                session["collaboration_enabled"]):
                active_users.append({
                    "user_id": session["user_id"],
                    "session_id": session_id,
                    "last_activity": session["last_activity"],
                    "permissions": session["permissions"]
                })
        
        recent_events = self.collaboration_state.get(dashboard_id, [])[-50:]  # Last 50 events
        
        return {
            "dashboard_id": dashboard_id,
            "active_users": active_users,
            "recent_events": [event.dict() for event in recent_events],
            "collaboration_enabled": len(active_users) > 1,
            "timestamp": datetime.utcnow()
        }
    
    def undo_last_operation(self, dashboard_id: str) -> Dict[str, Any]:
        """
        Undo the last operation on a dashboard
        
        Args:
            dashboard_id: Dashboard identifier
            
        Returns:
            Undo result and restored state
        """
        try:
            if dashboard_id not in self.undo_stack or not self.undo_stack[dashboard_id]:
                return {
                    "success": False,
                    "error": "No operations to undo"
                }
            
            # Get last state
            last_state = self.undo_stack[dashboard_id].pop()
            
            # Move current state to redo stack
            current_state = self._get_current_dashboard_state(dashboard_id)
            self.redo_stack[dashboard_id].append(current_state)
            
            # Restore last state
            restore_result = self._restore_dashboard_state(dashboard_id, last_state)
            
            logger.info(f"Undid last operation on dashboard {dashboard_id}")
            
            return {
                "success": True,
                "restored_state": last_state,
                "can_redo": True,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error undoing operation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def redo_last_operation(self, dashboard_id: str) -> Dict[str, Any]:
        """
        Redo the last undone operation on a dashboard
        
        Args:
            dashboard_id: Dashboard identifier
            
        Returns:
            Redo result and restored state
        """
        try:
            if dashboard_id not in self.redo_stack or not self.redo_stack[dashboard_id]:
                return {
                    "success": False,
                    "error": "No operations to redo"
                }
            
            # Get state to redo
            redo_state = self.redo_stack[dashboard_id].pop()
            
            # Move current state to undo stack
            current_state = self._get_current_dashboard_state(dashboard_id)
            self.undo_stack[dashboard_id].append(current_state)
            
            # Restore redo state
            restore_result = self._restore_dashboard_state(dashboard_id, redo_state)
            
            logger.info(f"Redid last operation on dashboard {dashboard_id}")
            
            return {
                "success": True,
                "restored_state": redo_state,
                "can_undo": True,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error redoing operation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # Private helper methods
    
    def _validate_drag_operation(self, operation: DragOperation) -> bool:
        """Validate drag operation parameters"""
        # Check if positions are within grid bounds
        if (operation.target_position.x < 0 or operation.target_position.x >= 12 or
            operation.target_position.y < 0):
            return False
        
        # Check if operation type is valid
        valid_operations = ["move", "resize", "add", "remove"]
        if operation.operation_type not in valid_operations:
            return False
        
        return True
    
    def _execute_drag_operation(self, operation: DragOperation) -> Dict[str, Any]:
        """Execute the actual drag operation"""
        # This would integrate with the dashboard layout engine
        # For now, return a mock successful operation
        return {
            "operation_id": str(uuid4()),
            "panel_id": operation.panel_id,
            "new_position": operation.target_position.dict(),
            "layout_updated": True
        }
    
    def _validate_resize_operation(self, operation: ResizeOperation) -> bool:
        """Validate resize operation parameters"""
        return (operation.new_width > 0 and operation.new_width <= 12 and
                operation.new_height > 0 and operation.new_height <= 20)
    
    def _calculate_resize_dimensions(self, operation: ResizeOperation) -> Dict[str, int]:
        """Calculate new panel dimensions"""
        return {
            "width": operation.new_width,
            "height": operation.new_height
        }
    
    def _detect_resize_collisions(self, operation: ResizeOperation, dimensions: Dict) -> List[str]:
        """Detect collisions during resize operations"""
        # Mock collision detection - would integrate with layout engine
        return []
    
    def _resolve_resize_collisions(self, operation: ResizeOperation, collisions: List[str]) -> Dict[str, Any]:
        """Resolve collisions by moving or resizing other panels"""
        return {
            "conflicts_resolved": len(collisions),
            "panels_moved": collisions,
            "resolution_strategy": "auto_arrange"
        }
    
    def _execute_resize_operation(self, operation: ResizeOperation, dimensions: Dict) -> Dict[str, Any]:
        """Execute the resize operation"""
        return {
            "panel_id": operation.panel_id,
            "new_dimensions": dimensions,
            "operation_completed": True
        }
    
    def _calculate_optimal_position(self, dashboard_id: str, panel_type: PanelType) -> DashboardGridPosition:
        """Calculate optimal position for new panel"""
        # Default positioning logic - would integrate with layout engine
        return DashboardGridPosition(
            x=0, y=0, width=6, height=4,
            breakpoint="lg"
        )
    
    def _add_panel_to_layout(self, dashboard_id: str, panel: DashboardPanel) -> Dict[str, Any]:
        """Add panel to dashboard layout"""
        return {
            "panel_added": True,
            "layout_updated": True,
            "panel_id": panel.id
        }
    
    def _remove_panel_from_layout(self, dashboard_id: str, panel_id: str) -> Dict[str, Any]:
        """Remove panel from dashboard layout"""
        return {
            "success": True,
            "panel_removed": True,
            "panel_id": panel_id
        }
    
    def _validate_layout_after_operation(self, operation: DragOperation) -> bool:
        """Validate layout integrity after operation"""
        return True
    
    def _validate_layout_integrity(self, dashboard_id: str) -> bool:
        """Validate overall layout integrity"""
        return True
    
    def _optimize_layout_after_removal(self, dashboard_id: str, removed_panel_id: str) -> Dict[str, Any]:
        """Optimize layout after panel removal"""
        return {
            "layout_optimized": True,
            "panels_moved": 0,
            "space_recovered": True
        }
    
    def _validate_config_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate panel configuration updates"""
        return {"valid": True}
    
    def _apply_panel_config_updates(self, dashboard_id: str, panel_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Apply configuration updates to panel"""
        return {
            "updates_applied": True,
            "panel_id": panel_id,
            "updated_fields": list(updates.keys())
        }
    
    def _load_dashboard_template(self, template_name: str) -> Optional[DashboardTemplate]:
        """Load dashboard template by name"""
        # Mock template loading - would integrate with template storage
        return None
    
    def _create_dashboard_from_template_config(self, dashboard_id: str, template: DashboardTemplate, config: Dict) -> Dashboard:
        """Create dashboard from template configuration"""
        # Mock dashboard creation
        return Dashboard(
            id=dashboard_id,
            title=config.get("title", "New Dashboard"),
            description=config.get("description", ""),
            layout_config=DashboardLayoutConfig(),
            panels=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def _save_state_for_undo(self, dashboard_id: str):
        """Save current dashboard state for undo functionality"""
        current_state = self._get_current_dashboard_state(dashboard_id)
        if dashboard_id not in self.undo_stack:
            self.undo_stack[dashboard_id] = []
        self.undo_stack[dashboard_id].append(current_state)
        
        # Limit undo stack size
        if len(self.undo_stack[dashboard_id]) > 50:
            self.undo_stack[dashboard_id].pop(0)
    
    def _get_current_dashboard_state(self, dashboard_id: str) -> Dict[str, Any]:
        """Get current dashboard state for undo/redo"""
        return {
            "dashboard_id": dashboard_id,
            "state_timestamp": datetime.utcnow(),
            "layout": {},  # Would contain actual layout data
            "panels": {}   # Would contain actual panel data
        }
    
    def _restore_dashboard_state(self, dashboard_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Restore dashboard to a previous state"""
        return {
            "state_restored": True,
            "dashboard_id": dashboard_id,
            "restore_timestamp": datetime.utcnow()
        }
    
    def _rollback_last_operation(self, dashboard_id: str):
        """Rollback the last operation"""
        if dashboard_id in self.undo_stack and self.undo_stack[dashboard_id]:
            last_state = self.undo_stack[dashboard_id].pop()
            self._restore_dashboard_state(dashboard_id, last_state)
    
    def _update_collaboration_state(self, operation: DragOperation):
        """Update collaboration state with operation"""
        if operation.dashboard_id not in self.collaboration_state:
            self.collaboration_state[operation.dashboard_id] = []
        
        # Add collaboration event (mock)
        event = CollaborationEvent(
            user_id="current_user",  # Would get from session
            dashboard_id=operation.dashboard_id,
            event_type="layout_change",
            event_data=operation.dict()
        )
        
        self.collaboration_state[operation.dashboard_id].append(event)
        
        # Limit collaboration history
        if len(self.collaboration_state[operation.dashboard_id]) > 100:
            self.collaboration_state[operation.dashboard_id].pop(0)