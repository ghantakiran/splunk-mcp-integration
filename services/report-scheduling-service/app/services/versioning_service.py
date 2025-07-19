"""
Version management service for report schedules.
"""

import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import (
    ReportSchedule, ScheduleVersion, ScheduleHistory, VersionMetrics
)
from app.models.versioning_models import (
    CreateVersionRequest, RestoreVersionRequest, CompareVersionsRequest,
    HistoryFilterRequest, VersionResponse, VersionListResponse,
    VersionComparisonResponse, HistoryEventResponse, HistoryResponse,
    VersionStatsResponse, HistoryStatsResponse, RestoreResult,
    VersionAction, ChangeType, HistoryEventType, VersionDiff
)

logger = logging.getLogger(__name__)


class VersioningService:
    """Service for managing schedule versions and history."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_version(
        self,
        request: CreateVersionRequest,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> VersionResponse:
        """
        Create a new version of a schedule.
        
        Args:
            request: Version creation request
            user_id: ID of user creating the version
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Created version response
            
        Raises:
            ValueError: If schedule not found or invalid request
        """
        try:
            # Get the current schedule
            schedule = await self.db.get(ReportSchedule, request.schedule_id)
            if not schedule:
                raise ValueError(f"Schedule {request.schedule_id} not found")
            
            # Get current version number
            current_version_number = await self._get_next_version_number(request.schedule_id)
            
            # Create configuration snapshot
            config_snapshot = await self._create_config_snapshot(schedule)
            
            # Calculate checksum
            config_json = json.dumps(config_snapshot, sort_keys=True)
            checksum = hashlib.sha256(config_json.encode()).hexdigest()
            
            # Mark previous current version as not current
            await self._mark_previous_versions_not_current(request.schedule_id)
            
            # Create new version
            version = ScheduleVersion(
                schedule_id=request.schedule_id,
                version_number=current_version_number,
                version_name=request.version_name,
                description=request.description,
                action=VersionAction.CREATED,
                changes=[change.value for change in request.changes],
                change_notes=request.change_notes,
                tags=request.tags,
                schedule_config=config_snapshot,
                is_current=True,
                checksum=checksum,
                size_bytes=len(config_json),
                created_by=user_id
            )
            
            self.db.add(version)
            await self.db.flush()
            
            # Create history event
            await self._create_history_event(
                schedule_id=request.schedule_id,
                event_type=HistoryEventType.VERSION_CHANGE,
                event_title=f"Version {current_version_number} created",
                event_description=request.description,
                user_id=user_id,
                correlation_id=correlation_id,
                version_id=version.version_id,
                event_data={
                    "action": VersionAction.CREATED.value,
                    "version_number": current_version_number,
                    "changes": [change.value for change in request.changes],
                    "change_notes": request.change_notes,
                    "tags": request.tags
                }
            )
            
            await self.db.commit()
            
            logger.info(f"Created version {current_version_number} for schedule {request.schedule_id}")
            
            return await self._version_to_response(version)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating version: {e}")
            raise
    
    async def get_versions(
        self,
        schedule_id: UUID,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False
    ) -> VersionListResponse:
        """
        Get versions for a schedule.
        
        Args:
            schedule_id: Schedule ID
            limit: Maximum number of results
            offset: Result offset
            include_archived: Whether to include archived versions
            
        Returns:
            Version list response
        """
        try:
            # Build query
            query = self.db.query(ScheduleVersion).filter(
                ScheduleVersion.schedule_id == schedule_id
            )
            
            if not include_archived:
                query = query.filter(ScheduleVersion.action != VersionAction.ARCHIVED)
            
            # Get total count
            total = await self.db.scalar(
                query.with_only_columns(func.count(ScheduleVersion.version_id))
            )
            
            # Get versions
            versions = await self.db.execute(
                query.order_by(desc(ScheduleVersion.version_number))
                .limit(limit)
                .offset(offset)
            )
            
            version_responses = []
            for version in versions.scalars():
                version_responses.append(await self._version_to_response(version))
            
            return VersionListResponse(
                items=version_responses,
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + len(version_responses) < total
            )
            
        except Exception as e:
            logger.error(f"Error getting versions: {e}")
            raise
    
    async def get_version(self, version_id: UUID) -> Optional[VersionResponse]:
        """
        Get a specific version.
        
        Args:
            version_id: Version ID
            
        Returns:
            Version response or None if not found
        """
        try:
            version = await self.db.get(ScheduleVersion, version_id)
            if not version:
                return None
            
            return await self._version_to_response(version)
            
        except Exception as e:
            logger.error(f"Error getting version {version_id}: {e}")
            raise
    
    async def compare_versions(
        self,
        request: CompareVersionsRequest
    ) -> VersionComparisonResponse:
        """
        Compare two versions.
        
        Args:
            request: Comparison request
            
        Returns:
            Version comparison response
            
        Raises:
            ValueError: If versions not found
        """
        try:
            # Get both versions
            version_1 = await self.db.get(ScheduleVersion, request.version_id_1)
            version_2 = await self.db.get(ScheduleVersion, request.version_id_2)
            
            if not version_1:
                raise ValueError(f"Version {request.version_id_1} not found")
            if not version_2:
                raise ValueError(f"Version {request.version_id_2} not found")
            
            # Convert to responses
            version_1_response = await self._version_to_response(version_1)
            version_2_response = await self._version_to_response(version_2)
            
            # Compare configurations
            differences = self._compare_configurations(
                version_1.schedule_config,
                version_2.schedule_config,
                include_metadata=request.include_metadata
            )
            
            # Generate summary
            summary = self._generate_comparison_summary(differences)
            
            return VersionComparisonResponse(
                version_1=version_1_response,
                version_2=version_2_response,
                differences=differences,
                summary=summary,
                is_identical=len(differences) == 0
            )
            
        except Exception as e:
            logger.error(f"Error comparing versions: {e}")
            raise
    
    async def restore_version(
        self,
        request: RestoreVersionRequest,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> RestoreResult:
        """
        Restore a schedule to a previous version.
        
        Args:
            request: Restore request
            user_id: ID of user performing restore
            correlation_id: Optional correlation ID
            
        Returns:
            Restore result
            
        Raises:
            ValueError: If version not found or invalid
        """
        try:
            # Get the version to restore
            version_to_restore = await self.db.get(ScheduleVersion, request.version_id)
            if not version_to_restore:
                raise ValueError(f"Version {request.version_id} not found")
            
            # Get the current schedule
            schedule = await self.db.get(ReportSchedule, version_to_restore.schedule_id)
            if not schedule:
                raise ValueError(f"Schedule {version_to_restore.schedule_id} not found")
            
            # Create backup version of current state
            backup_request = CreateVersionRequest(
                schedule_id=version_to_restore.schedule_id,
                version_name=f"Pre-restore backup",
                description=f"Automatic backup before restoring to version {version_to_restore.version_number}",
                changes=[ChangeType.METADATA],
                change_notes=f"Backup created before restore operation",
                tags=["backup", "pre-restore"]
            )
            
            backup_version = await self.create_version(backup_request, user_id, correlation_id)
            
            # Apply the restored configuration
            config = version_to_restore.schedule_config
            changes_applied = await self._apply_configuration_to_schedule(schedule, config)
            
            # Create new version for the restore
            restore_version_request = CreateVersionRequest(
                schedule_id=version_to_restore.schedule_id,
                version_name=f"Restored to v{version_to_restore.version_number}",
                description=request.restore_notes or f"Restored to version {version_to_restore.version_number}",
                changes=[ChangeType.SCHEDULE_CONFIG],  # Will be updated based on actual changes
                change_notes=request.restore_notes,
                tags=["restore"]
            )
            
            new_version = await self.create_version(restore_version_request, user_id, correlation_id)
            
            # Create history event
            await self._create_history_event(
                schedule_id=version_to_restore.schedule_id,
                event_type=HistoryEventType.VERSION_CHANGE,
                event_title=f"Restored to version {version_to_restore.version_number}",
                event_description=request.restore_notes,
                user_id=user_id,
                correlation_id=correlation_id,
                version_id=new_version.version_id,
                event_data={
                    "action": VersionAction.RESTORED.value,
                    "restored_from_version": version_to_restore.version_number,
                    "backup_version_id": str(backup_version.version_id),
                    "changes_applied": changes_applied
                }
            )
            
            await self.db.commit()
            
            logger.info(
                f"Restored schedule {version_to_restore.schedule_id} to version {version_to_restore.version_number}"
            )
            
            return RestoreResult(
                success=True,
                restored_version_id=request.version_id,
                new_version_id=new_version.version_id,
                message=f"Successfully restored to version {version_to_restore.version_number}",
                warnings=[],
                changes_applied=changes_applied
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error restoring version: {e}")
            raise
    
    async def get_history(
        self,
        request: HistoryFilterRequest
    ) -> HistoryResponse:
        """
        Get history events with filtering.
        
        Args:
            request: History filter request
            
        Returns:
            History response
        """
        try:
            # Build query
            query = self.db.query(ScheduleHistory)
            
            if request.schedule_id:
                query = query.filter(ScheduleHistory.schedule_id == request.schedule_id)
            
            if request.event_types:
                query = query.filter(
                    ScheduleHistory.event_type.in_([et.value for et in request.event_types])
                )
            
            if request.start_date:
                query = query.filter(ScheduleHistory.occurred_at >= request.start_date)
            
            if request.end_date:
                query = query.filter(ScheduleHistory.occurred_at <= request.end_date)
            
            if request.user_id:
                query = query.filter(ScheduleHistory.user_id == request.user_id)
            
            # Get total count
            total = await self.db.scalar(
                query.with_only_columns(func.count(ScheduleHistory.event_id))
            )
            
            # Get history events
            history_events = await self.db.execute(
                query.order_by(desc(ScheduleHistory.occurred_at))
                .limit(request.limit)
                .offset(request.offset)
            )
            
            event_responses = []
            for event in history_events.scalars():
                event_responses.append(self._history_to_response(event))
            
            return HistoryResponse(
                items=event_responses,
                total=total,
                limit=request.limit,
                offset=request.offset,
                has_more=request.offset + len(event_responses) < total
            )
            
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            raise
    
    async def get_version_stats(self, schedule_id: UUID) -> VersionStatsResponse:
        """
        Get version statistics for a schedule.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Version statistics
        """
        try:
            # Get version data
            versions = await self.db.execute(
                self.db.query(ScheduleVersion)
                .filter(ScheduleVersion.schedule_id == schedule_id)
                .order_by(ScheduleVersion.version_number)
            )
            versions_list = list(versions.scalars())
            
            if not versions_list:
                raise ValueError(f"No versions found for schedule {schedule_id}")
            
            # Calculate statistics
            total_versions = len(versions_list)
            current_version = next(
                (v for v in versions_list if v.is_current),
                versions_list[-1]
            )
            
            # Version breakdown by action
            versions_by_action = {}
            for action in VersionAction:
                count = sum(1 for v in versions_list if v.action == action)
                if count > 0:
                    versions_by_action[action.value] = count
            
            # Version breakdown by change type
            versions_by_change_type = {}
            for version in versions_list:
                for change in version.changes:
                    versions_by_change_type[change] = versions_by_change_type.get(change, 0) + 1
            
            # User activity
            user_activity = {}
            for version in versions_list:
                user_activity[version.created_by] = user_activity.get(version.created_by, 0) + 1
            
            most_active_user = max(user_activity.items(), key=lambda x: x[1])[0] if user_activity else None
            
            # Size statistics
            total_size = sum(v.size_bytes for v in versions_list)
            average_size = total_size / total_versions if total_versions > 0 else 0
            largest_size = max(v.size_bytes for v in versions_list) if versions_list else 0
            
            return VersionStatsResponse(
                schedule_id=schedule_id,
                total_versions=total_versions,
                current_version_number=current_version.version_number,
                versions_by_action=versions_by_action,
                versions_by_change_type=versions_by_change_type,
                first_version_created=versions_list[0].created_at,
                last_version_created=versions_list[-1].created_at,
                most_active_user=most_active_user,
                total_size_bytes=total_size,
                average_size_bytes=average_size,
                largest_version_size=largest_size
            )
            
        except Exception as e:
            logger.error(f"Error getting version stats: {e}")
            raise
    
    # Private helper methods
    
    async def _get_next_version_number(self, schedule_id: UUID) -> int:
        """Get the next version number for a schedule."""
        max_version = await self.db.scalar(
            self.db.query(func.max(ScheduleVersion.version_number))
            .filter(ScheduleVersion.schedule_id == schedule_id)
        )
        return (max_version or 0) + 1
    
    async def _create_config_snapshot(self, schedule: ReportSchedule) -> Dict[str, Any]:
        """Create a configuration snapshot of a schedule."""
        return {
            "name": schedule.name,
            "description": schedule.description,
            "status": schedule.status.value,
            "cron_expression": schedule.cron_expression,
            "timezone": schedule.timezone,
            "start_date": schedule.start_date.isoformat() if schedule.start_date else None,
            "end_date": schedule.end_date.isoformat() if schedule.end_date else None,
            "max_executions": schedule.max_executions,
            "allow_overlap": schedule.allow_overlap,
            "priority": schedule.priority.value,
            "query": schedule.query,
            "query_type": schedule.query_type,
            "time_range": schedule.time_range,
            "report_format": schedule.report_format.value,
            "format_options": schedule.format_options,
            "visualization_config": schedule.visualization_config,
            "data_filters": schedule.data_filters,
            "parameters": schedule.parameters,
            "delivery_configs": schedule.delivery_configs,
            "tags": schedule.tags,
            "metadata": schedule.metadata
        }
    
    async def _mark_previous_versions_not_current(self, schedule_id: UUID):
        """Mark all previous versions of a schedule as not current."""
        await self.db.execute(
            self.db.query(ScheduleVersion)
            .filter(ScheduleVersion.schedule_id == schedule_id)
            .update({"is_current": False})
        )
    
    async def _create_history_event(
        self,
        schedule_id: UUID,
        event_type: HistoryEventType,
        event_title: str,
        event_description: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        version_id: Optional[UUID] = None,
        execution_id: Optional[UUID] = None,
        event_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a history event."""
        event = ScheduleHistory(
            schedule_id=schedule_id,
            event_type=event_type,
            event_title=event_title,
            event_description=event_description,
            user_id=user_id,
            correlation_id=correlation_id,
            version_id=version_id,
            execution_id=execution_id,
            event_data=event_data or {},
            metadata=metadata
        )
        
        self.db.add(event)
        await self.db.flush()
    
    async def _version_to_response(self, version: ScheduleVersion) -> VersionResponse:
        """Convert a version model to a response."""
        return VersionResponse(
            version_id=version.version_id,
            schedule_id=version.schedule_id,
            version_number=version.version_number,
            version_name=version.version_name,
            description=version.description,
            action=version.action,
            changes=[ChangeType(change) for change in version.changes],
            change_notes=version.change_notes,
            tags=version.tags,
            schedule_config=version.schedule_config,
            created_by=version.created_by,
            created_at=version.created_at,
            is_current=version.is_current,
            parent_version_id=version.parent_version_id,
            checksum=version.checksum,
            size_bytes=version.size_bytes
        )
    
    def _history_to_response(self, event: ScheduleHistory) -> HistoryEventResponse:
        """Convert a history model to a response."""
        return HistoryEventResponse(
            event_id=event.event_id,
            schedule_id=event.schedule_id,
            event_type=event.event_type,
            event_title=event.event_title,
            event_description=event.event_description,
            user_id=event.user_id,
            session_id=event.session_id,
            correlation_id=event.correlation_id,
            event_data=event.event_data,
            metadata=event.metadata,
            version_id=event.version_id,
            execution_id=event.execution_id,
            occurred_at=event.occurred_at,
            created_at=event.created_at
        )
    
    def _compare_configurations(
        self,
        config_1: Dict[str, Any],
        config_2: Dict[str, Any],
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Compare two configuration dictionaries."""
        differences = {}
        
        # Get all keys from both configurations
        all_keys = set(config_1.keys()) | set(config_2.keys())
        
        if not include_metadata:
            # Exclude metadata-related keys
            all_keys = {k for k in all_keys if k not in ["metadata", "tags", "updated_at"]}
        
        for key in all_keys:
            value_1 = config_1.get(key)
            value_2 = config_2.get(key)
            
            if value_1 != value_2:
                differences[key] = {
                    "old_value": value_1,
                    "new_value": value_2,
                    "change_type": self._get_change_type(value_1, value_2)
                }
        
        return differences
    
    def _get_change_type(self, old_value: Any, new_value: Any) -> str:
        """Determine the type of change between two values."""
        if old_value is None and new_value is not None:
            return "added"
        elif old_value is not None and new_value is None:
            return "removed"
        else:
            return "modified"
    
    def _generate_comparison_summary(self, differences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of differences."""
        if not differences:
            return {"message": "No differences found", "change_count": 0}
        
        change_types = {}
        for key, diff in differences.items():
            change_type = diff["change_type"]
            change_types[change_type] = change_types.get(change_type, 0) + 1
        
        return {
            "change_count": len(differences),
            "changes_by_type": change_types,
            "changed_fields": list(differences.keys()),
            "message": f"Found {len(differences)} differences"
        }
    
    async def _apply_configuration_to_schedule(
        self,
        schedule: ReportSchedule,
        config: Dict[str, Any]
    ) -> List[str]:
        """Apply configuration to a schedule and return list of changes."""
        changes_applied = []
        
        # Map configuration fields to schedule attributes
        field_mapping = {
            "name": "name",
            "description": "description",
            "cron_expression": "cron_expression",
            "timezone": "timezone",
            "start_date": "start_date",
            "end_date": "end_date",
            "max_executions": "max_executions",
            "allow_overlap": "allow_overlap",
            "query": "query",
            "query_type": "query_type",
            "time_range": "time_range",
            "format_options": "format_options",
            "visualization_config": "visualization_config",
            "data_filters": "data_filters",
            "parameters": "parameters",
            "delivery_configs": "delivery_configs",
            "tags": "tags",
            "metadata": "metadata"
        }
        
        for config_key, schedule_attr in field_mapping.items():
            if config_key in config:
                old_value = getattr(schedule, schedule_attr)
                new_value = config[config_key]
                
                if old_value != new_value:
                    setattr(schedule, schedule_attr, new_value)
                    changes_applied.append(f"Updated {config_key}")
        
        # Handle enum fields
        if "status" in config:
            from app.models.schedule_models import ScheduleStatus
            new_status = ScheduleStatus(config["status"])
            if schedule.status != new_status:
                schedule.status = new_status
                changes_applied.append("Updated status")
        
        if "priority" in config:
            from app.models.schedule_models import Priority
            new_priority = Priority(config["priority"])
            if schedule.priority != new_priority:
                schedule.priority = new_priority
                changes_applied.append("Updated priority")
        
        if "report_format" in config:
            from app.models.schedule_models import ReportFormat
            new_format = ReportFormat(config["report_format"])
            if schedule.report_format != new_format:
                schedule.report_format = new_format
                changes_applied.append("Updated report format")
        
        # Handle datetime fields
        if "start_date" in config and config["start_date"]:
            from datetime import datetime
            new_start_date = datetime.fromisoformat(config["start_date"])
            if schedule.start_date != new_start_date:
                schedule.start_date = new_start_date
                changes_applied.append("Updated start date")
        
        if "end_date" in config and config["end_date"]:
            from datetime import datetime
            new_end_date = datetime.fromisoformat(config["end_date"])
            if schedule.end_date != new_end_date:
                schedule.end_date = new_end_date
                changes_applied.append("Updated end date")
        
        return changes_applied