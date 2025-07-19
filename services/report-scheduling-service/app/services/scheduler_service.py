"""
Scheduler service for managing report schedules and executions.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from croniter import croniter
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import (
    ReportSchedule, ScheduleExecution, ReportSubscription,
    ScheduleAnalytics, get_database
)
from app.models.schedule_models import (
    ScheduleStatus, ExecutionStatus, Priority,
    ScheduleResponse, ExecutionResponse, CreateScheduleRequest,
    UpdateScheduleRequest
)
from app.services.report_generator import ReportGeneratorService
from app.services.delivery_service import DeliveryService
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing report schedules."""
    
    def __init__(self):
        self.report_generator = ReportGeneratorService()
        self.delivery_service = DeliveryService()
    
    async def create_schedule(
        self,
        request: CreateScheduleRequest,
        user_id: str
    ) -> ScheduleResponse:
        """Create a new report schedule."""
        db = await get_database()
        
        try:
            # Calculate next execution time
            next_execution = self._calculate_next_execution(
                request.schedule_config.cron_expression,
                request.schedule_config.timezone,
                request.schedule_config.start_date
            )
            
            # Create schedule record
            schedule = ReportSchedule(
                user_id=user_id,
                name=request.name,
                description=request.description,
                status=ScheduleStatus.ACTIVE,
                cron_expression=request.schedule_config.cron_expression,
                timezone=request.schedule_config.timezone,
                start_date=request.schedule_config.start_date,
                end_date=request.schedule_config.end_date,
                max_executions=request.schedule_config.max_executions,
                allow_overlap=request.schedule_config.allow_overlap,
                priority=request.schedule_config.priority,
                query=request.report_config.query,
                query_type=request.report_config.query_type,
                time_range=request.report_config.time_range,
                report_format=request.report_config.format,
                format_options=request.report_config.format_options,
                visualization_config=request.report_config.visualization_config,
                data_filters=request.report_config.data_filters,
                parameters=request.report_config.parameters,
                delivery_configs=[config.dict() for config in request.delivery_configs],
                next_execution=next_execution,
                tags=request.tags,
                metadata=request.metadata
            )
            
            db.add(schedule)
            await db.commit()
            await db.refresh(schedule)
            
            # Schedule the first execution
            await self._schedule_execution(schedule)
            
            logger.info(f"Created schedule {schedule.schedule_id} for user {user_id}")
            
            return await self._schedule_to_response(schedule)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create schedule: {e}")
            raise
        finally:
            await db.close()
    
    async def update_schedule(
        self,
        schedule_id: UUID,
        request: UpdateScheduleRequest,
        user_id: str
    ) -> ScheduleResponse:
        """Update an existing schedule."""
        db = await get_database()
        
        try:
            # Get existing schedule
            result = await db.execute(
                select(ReportSchedule).where(
                    and_(
                        ReportSchedule.schedule_id == schedule_id,
                        ReportSchedule.user_id == user_id
                    )
                )
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                raise ValueError(f"Schedule {schedule_id} not found")
            
            # Update fields
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.description is not None:
                update_data["description"] = request.description
            if request.status is not None:
                update_data["status"] = request.status
            if request.tags is not None:
                update_data["tags"] = request.tags
            if request.metadata is not None:
                update_data["metadata"] = request.metadata
            
            # Update schedule configuration
            if request.schedule_config is not None:
                config = request.schedule_config
                update_data.update({
                    "cron_expression": config.cron_expression,
                    "timezone": config.timezone,
                    "start_date": config.start_date,
                    "end_date": config.end_date,
                    "max_executions": config.max_executions,
                    "allow_overlap": config.allow_overlap,
                    "priority": config.priority
                })
                
                # Recalculate next execution
                next_execution = self._calculate_next_execution(
                    config.cron_expression,
                    config.timezone,
                    config.start_date
                )
                update_data["next_execution"] = next_execution
            
            # Update report configuration
            if request.report_config is not None:
                config = request.report_config
                update_data.update({
                    "query": config.query,
                    "query_type": config.query_type,
                    "time_range": config.time_range,
                    "report_format": config.format,
                    "format_options": config.format_options,
                    "visualization_config": config.visualization_config,
                    "data_filters": config.data_filters,
                    "parameters": config.parameters
                })
            
            # Update delivery configurations
            if request.delivery_configs is not None:
                update_data["delivery_configs"] = [
                    config.dict() for config in request.delivery_configs
                ]
            
            # Apply updates
            if update_data:
                await db.execute(
                    update(ReportSchedule)
                    .where(ReportSchedule.schedule_id == schedule_id)
                    .values(**update_data)
                )
                await db.commit()
                
                # Refresh schedule
                await db.refresh(schedule)
            
            logger.info(f"Updated schedule {schedule_id}")
            
            return await self._schedule_to_response(schedule)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update schedule {schedule_id}: {e}")
            raise
        finally:
            await db.close()
    
    async def get_schedule(self, schedule_id: UUID, user_id: str) -> Optional[ScheduleResponse]:
        """Get a schedule by ID."""
        db = await get_database()
        
        try:
            result = await db.execute(
                select(ReportSchedule).where(
                    and_(
                        ReportSchedule.schedule_id == schedule_id,
                        ReportSchedule.user_id == user_id
                    )
                )
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                return None
            
            return await self._schedule_to_response(schedule)
            
        finally:
            await db.close()
    
    async def list_schedules(
        self,
        user_id: str,
        status: Optional[ScheduleStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List schedules for a user."""
        db = await get_database()
        
        try:
            # Build query
            query = select(ReportSchedule).where(ReportSchedule.user_id == user_id)
            
            if status:
                query = query.where(ReportSchedule.status == status)
            
            # Get total count
            count_result = await db.execute(
                select(db.func.count(ReportSchedule.schedule_id)).where(
                    ReportSchedule.user_id == user_id
                )
            )
            total = count_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * page_size
            query = query.order_by(ReportSchedule.created_at.desc())
            query = query.offset(offset).limit(page_size)
            
            result = await db.execute(query)
            schedules = result.scalars().all()
            
            schedule_responses = []
            for schedule in schedules:
                schedule_responses.append(await self._schedule_to_response(schedule))
            
            return {
                "schedules": schedule_responses,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
            
        finally:
            await db.close()
    
    async def delete_schedule(self, schedule_id: UUID, user_id: str) -> bool:
        """Delete a schedule."""
        db = await get_database()
        
        try:
            result = await db.execute(
                select(ReportSchedule).where(
                    and_(
                        ReportSchedule.schedule_id == schedule_id,
                        ReportSchedule.user_id == user_id
                    )
                )
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                return False
            
            await db.delete(schedule)
            await db.commit()
            
            # Cancel any pending executions
            await self._cancel_pending_executions(schedule_id)
            
            logger.info(f"Deleted schedule {schedule_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete schedule {schedule_id}: {e}")
            raise
        finally:
            await db.close()
    
    async def execute_schedule(self, schedule_id: UUID) -> ExecutionResponse:
        """Execute a schedule immediately."""
        db = await get_database()
        
        try:
            # Get schedule
            result = await db.execute(
                select(ReportSchedule).where(ReportSchedule.schedule_id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                raise ValueError(f"Schedule {schedule_id} not found")
            
            if schedule.status != ScheduleStatus.ACTIVE:
                raise ValueError(f"Schedule {schedule_id} is not active")
            
            # Create execution record
            execution = ScheduleExecution(
                schedule_id=schedule_id,
                scheduled_at=datetime.now(timezone.utc),
                status=ExecutionStatus.PENDING
            )
            
            db.add(execution)
            await db.commit()
            await db.refresh(execution)
            
            # Queue execution
            await self._queue_execution(execution.execution_id)
            
            logger.info(f"Queued execution {execution.execution_id} for schedule {schedule_id}")
            
            return await self._execution_to_response(execution)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to execute schedule {schedule_id}: {e}")
            raise
        finally:
            await db.close()
    
    async def process_scheduled_executions(self):
        """Process due scheduled executions."""
        db = await get_database()
        
        try:
            # Find schedules due for execution
            now = datetime.now(timezone.utc)
            
            result = await db.execute(
                select(ReportSchedule).where(
                    and_(
                        ReportSchedule.status == ScheduleStatus.ACTIVE,
                        ReportSchedule.next_execution <= now
                    )
                )
            )
            schedules = result.scalars().all()
            
            for schedule in schedules:
                try:
                    await self._process_schedule_execution(schedule)
                except Exception as e:
                    logger.error(f"Failed to process schedule {schedule.schedule_id}: {e}")
            
        finally:
            await db.close()
    
    async def _process_schedule_execution(self, schedule: ReportSchedule):
        """Process a single schedule execution."""
        db = await get_database()
        
        try:
            # Check if overlap is allowed
            if not schedule.allow_overlap:
                # Check for running executions
                result = await db.execute(
                    select(ScheduleExecution).where(
                        and_(
                            ScheduleExecution.schedule_id == schedule.schedule_id,
                            ScheduleExecution.status.in_([
                                ExecutionStatus.PENDING,
                                ExecutionStatus.RUNNING,
                                ExecutionStatus.RETRYING
                            ])
                        )
                    )
                )
                running_executions = result.scalars().all()
                
                if running_executions:
                    logger.warning(
                        f"Skipping execution for schedule {schedule.schedule_id} "
                        f"due to overlap prevention"
                    )
                    return
            
            # Check execution limits
            if schedule.max_executions and schedule.execution_count >= schedule.max_executions:
                # Disable schedule
                await db.execute(
                    update(ReportSchedule)
                    .where(ReportSchedule.schedule_id == schedule.schedule_id)
                    .values(status=ScheduleStatus.DISABLED)
                )
                await db.commit()
                
                logger.info(
                    f"Disabled schedule {schedule.schedule_id} - "
                    f"max executions ({schedule.max_executions}) reached"
                )
                return
            
            # Create execution record
            execution = ScheduleExecution(
                schedule_id=schedule.schedule_id,
                scheduled_at=datetime.now(timezone.utc),
                status=ExecutionStatus.PENDING
            )
            
            db.add(execution)
            
            # Update schedule next execution time
            next_execution = self._calculate_next_execution(
                schedule.cron_expression,
                schedule.timezone
            )
            
            await db.execute(
                update(ReportSchedule)
                .where(ReportSchedule.schedule_id == schedule.schedule_id)
                .values(
                    next_execution=next_execution,
                    execution_count=schedule.execution_count + 1
                )
            )
            
            await db.commit()
            await db.refresh(execution)
            
            # Queue execution
            await self._queue_execution(execution.execution_id)
            
            logger.info(
                f"Queued execution {execution.execution_id} "
                f"for schedule {schedule.schedule_id}"
            )
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to process schedule execution: {e}")
            raise
        finally:
            await db.close()
    
    async def _schedule_execution(self, schedule: ReportSchedule):
        """Schedule the first execution for a new schedule."""
        # Implementation would queue the schedule for processing
        redis_client = await get_redis_client()
        await redis_client.sadd("active_schedules", str(schedule.schedule_id))
    
    async def _queue_execution(self, execution_id: UUID):
        """Queue an execution for processing."""
        redis_client = await get_redis_client()
        await redis_client.lpush("report_execution_queue", str(execution_id))
    
    async def _cancel_pending_executions(self, schedule_id: UUID):
        """Cancel pending executions for a schedule."""
        db = await get_database()
        
        try:
            await db.execute(
                update(ScheduleExecution)
                .where(
                    and_(
                        ScheduleExecution.schedule_id == schedule_id,
                        ScheduleExecution.status == ExecutionStatus.PENDING
                    )
                )
                .values(status=ExecutionStatus.CANCELLED)
            )
            await db.commit()
            
        finally:
            await db.close()
    
    def _calculate_next_execution(
        self,
        cron_expression: str,
        timezone_str: str,
        start_date: Optional[datetime] = None
    ) -> datetime:
        """Calculate next execution time for a cron expression."""
        try:
            # Use start_date as base time if provided, otherwise use current time
            base_time = start_date or datetime.now(timezone.utc)
            
            # Create croniter instance
            cron = croniter(cron_expression, base_time)
            
            # Get next execution time
            next_time = cron.get_next(datetime)
            
            return next_time
            
        except Exception as e:
            logger.error(f"Failed to calculate next execution: {e}")
            # Fallback to 1 hour from now
            return datetime.now(timezone.utc) + timedelta(hours=1)
    
    async def _schedule_to_response(self, schedule: ReportSchedule) -> ScheduleResponse:
        """Convert database schedule to response model."""
        from app.models.schedule_models import (
            ScheduleConfiguration, ReportConfiguration, DeliveryConfiguration
        )
        
        # Build schedule configuration
        schedule_config = ScheduleConfiguration(
            cron_expression=schedule.cron_expression,
            timezone=schedule.timezone,
            start_date=schedule.start_date,
            end_date=schedule.end_date,
            max_executions=schedule.max_executions,
            allow_overlap=schedule.allow_overlap,
            priority=schedule.priority
        )
        
        # Build report configuration
        report_config = ReportConfiguration(
            query=schedule.query,
            query_type=schedule.query_type,
            time_range=schedule.time_range,
            format=schedule.report_format,
            format_options=schedule.format_options,
            visualization_config=schedule.visualization_config,
            data_filters=schedule.data_filters,
            parameters=schedule.parameters
        )
        
        # Build delivery configurations
        delivery_configs = []
        for config_data in schedule.delivery_configs:
            delivery_configs.append(DeliveryConfiguration.parse_obj(config_data))
        
        return ScheduleResponse(
            schedule_id=schedule.schedule_id,
            user_id=schedule.user_id,
            name=schedule.name,
            description=schedule.description,
            status=schedule.status,
            schedule_config=schedule_config,
            report_config=report_config,
            delivery_configs=delivery_configs,
            next_execution=schedule.next_execution,
            last_execution=schedule.last_execution,
            execution_count=schedule.execution_count,
            success_count=schedule.success_count,
            failure_count=schedule.failure_count,
            tags=schedule.tags,
            metadata=schedule.metadata,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at
        )
    
    async def _execution_to_response(self, execution: ScheduleExecution) -> ExecutionResponse:
        """Convert database execution to response model."""
        return ExecutionResponse(
            execution_id=execution.execution_id,
            schedule_id=execution.schedule_id,
            status=execution.status,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            duration_seconds=execution.duration_seconds,
            report_file_path=execution.report_file_path,
            delivery_results=execution.delivery_results,
            error_message=execution.error_message,
            retry_count=execution.retry_count,
            metadata=execution.metadata,
            created_at=execution.created_at,
            updated_at=execution.updated_at
        )