"""
Comprehensive audit trail service for secure sharing operations.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4
import time
import json

from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_database, ShareAuditTrail
from app.models.sharing_models import (
    AuditEventType, AuditEventSeverity, AuditEventCategory, ShareType, ShareOperation,
    PermissionScope, AuditTrailEvent, CreateAuditEventRequest, AuditTrailQuery,
    AuditTrailResponse, AuditTrailStatistics, AuditTrailExportRequest
)
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


class AuditTrailService:
    """Service for comprehensive audit trail management."""

    def __init__(self):
        self.service_version = getattr(settings, 'VERSION', '1.0.0')
        self.retention_days = getattr(settings, 'AUDIT_RETENTION_DAYS', 2555)  # 7 years default
        self.batch_size = getattr(settings, 'AUDIT_BATCH_SIZE', 1000)

    async def log_event(
        self,
        request: CreateAuditEventRequest,
        db: Optional[AsyncSession] = None
    ) -> AuditTrailEvent:
        """Log a single audit event."""
        if db is None:
            db = await get_database()

        try:
            start_time = time.time()
            
            # Calculate retention date
            retention_date = datetime.now(timezone.utc) + timedelta(days=self.retention_days)
            
            # Create audit trail record
            audit_record = ShareAuditTrail(
                event_id=uuid4(),
                event_type=request.event_type,
                category=request.category,
                severity=request.severity,
                title=request.title,
                description=request.description,
                timestamp=datetime.now(timezone.utc),
                user_id=request.user_id,
                session_id=request.session_id,
                ip_address=request.ip_address,
                user_agent=request.user_agent,
                share_id=request.share_id,
                resource_id=request.resource_id,
                resource_type=request.resource_type,
                operation=request.operation,
                scope=request.scope,
                scope_id=request.scope_id,
                before_state=request.before_state,
                after_state=request.after_state,
                context=request.context,
                metadata=request.metadata,
                correlation_id=request.correlation_id,
                request_id=request.request_id,
                authentication_method=request.authentication_method,
                authorization_granted=request.authorization_granted,
                service_name="secure-sharing-service",
                service_version=self.service_version,
                tags=request.tags,
                processing_time_ms=None,  # Will be set after processing
                retention_date=retention_date
            )

            db.add(audit_record)
            await db.commit()
            await db.refresh(audit_record)

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            audit_record.processing_time_ms = processing_time
            await db.commit()

            logger.info(
                "Audit event logged",
                event_id=str(audit_record.event_id),
                event_type=request.event_type.value,
                category=request.category.value,
                severity=request.severity.value,
                user_id=request.user_id,
                share_id=str(request.share_id) if request.share_id else None,
                processing_time_ms=processing_time
            )

            return self._convert_to_response_model(audit_record)

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to log audit event",
                event_type=request.event_type.value,
                error=str(e),
                user_id=request.user_id
            )
            raise

    async def log_share_event(
        self,
        event_type: AuditEventType,
        title: str,
        description: str,
        share_id: UUID,
        user_id: Optional[str] = None,
        operation: Optional[ShareOperation] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        severity: AuditEventSeverity = AuditEventSeverity.LOW,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> AuditTrailEvent:
        """Log a share-related audit event with simplified interface."""
        request = CreateAuditEventRequest(
            event_type=event_type,
            category=AuditEventCategory.SHARE_MANAGEMENT,
            severity=severity,
            title=title,
            description=description,
            user_id=user_id,
            share_id=share_id,
            operation=operation,
            before_state=before_state,
            after_state=after_state,
            context=context,
            correlation_id=correlation_id,
            ip_address=ip_address
        )
        return await self.log_event(request, db)

    async def log_permission_event(
        self,
        event_type: AuditEventType,
        title: str,
        description: str,
        user_id: str,
        operation: ShareOperation,
        scope: PermissionScope,
        scope_id: Optional[str] = None,
        authorization_granted: Optional[bool] = None,
        severity: AuditEventSeverity = AuditEventSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> AuditTrailEvent:
        """Log a permission-related audit event."""
        request = CreateAuditEventRequest(
            event_type=event_type,
            category=AuditEventCategory.PERMISSION_MANAGEMENT,
            severity=severity,
            title=title,
            description=description,
            user_id=user_id,
            operation=operation,
            scope=scope,
            scope_id=scope_id,
            authorization_granted=authorization_granted,
            context=context,
            correlation_id=correlation_id,
            ip_address=ip_address
        )
        return await self.log_event(request, db)

    async def log_security_event(
        self,
        event_type: AuditEventType,
        title: str,
        description: str,
        severity: AuditEventSeverity = AuditEventSeverity.HIGH,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> AuditTrailEvent:
        """Log a security-related audit event."""
        request = CreateAuditEventRequest(
            event_type=event_type,
            category=AuditEventCategory.SECURITY,
            severity=severity,
            title=title,
            description=description,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            context=context,
            correlation_id=correlation_id,
            authorization_granted=False  # Security events typically indicate denied access
        )
        return await self.log_event(request, db)

    async def query_events(
        self,
        query: AuditTrailQuery,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> AuditTrailResponse:
        """Query audit trail events with comprehensive filtering."""
        if db is None:
            db = await get_database()

        try:
            start_time = time.time()

            # Build the base query
            base_query = select(ShareAuditTrail)
            
            # Apply filters
            filters = []
            
            # Time range filters
            if query.start_time:
                filters.append(ShareAuditTrail.timestamp >= query.start_time)
            if query.end_time:
                filters.append(ShareAuditTrail.timestamp <= query.end_time)
            
            # Event filtering
            if query.event_types:
                filters.append(ShareAuditTrail.event_type.in_(query.event_types))
            if query.categories:
                filters.append(ShareAuditTrail.category.in_(query.categories))
            if query.severities:
                filters.append(ShareAuditTrail.severity.in_(query.severities))
            
            # User and resource filtering
            if query.user_ids:
                filters.append(ShareAuditTrail.user_id.in_(query.user_ids))
            if query.share_ids:
                filters.append(ShareAuditTrail.share_id.in_(query.share_ids))
            if query.resource_ids:
                filters.append(ShareAuditTrail.resource_id.in_(query.resource_ids))
            if query.resource_types:
                filters.append(ShareAuditTrail.resource_type.in_(query.resource_types))
            
            # Operation filtering
            if query.operations:
                filters.append(ShareAuditTrail.operation.in_(query.operations))
            if query.scopes:
                filters.append(ShareAuditTrail.scope.in_(query.scopes))
            
            # Security filtering
            if query.authorization_granted is not None:
                filters.append(ShareAuditTrail.authorization_granted == query.authorization_granted)
            if query.ip_addresses:
                filters.append(ShareAuditTrail.ip_address.in_(query.ip_addresses))
            
            # Text search (search in title, description)
            if query.search_query:
                search_term = f"%{query.search_query}%"
                filters.append(
                    or_(
                        ShareAuditTrail.title.ilike(search_term),
                        ShareAuditTrail.description.ilike(search_term)
                    )
                )
            
            # Tag filtering
            if query.tags:
                for tag in query.tags:
                    filters.append(ShareAuditTrail.tags.contains([tag]))

            # Check if user has permission to view audit events
            await self._check_audit_access_permission(user_id, filters, db)

            # Apply all filters
            if filters:
                base_query = base_query.where(and_(*filters))

            # Get total count (before pagination)
            count_query = select(func.count()).select_from(base_query.subquery())
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()

            # Apply sorting
            sort_column = getattr(ShareAuditTrail, query.sort_by, ShareAuditTrail.timestamp)
            if query.sort_order == "desc":
                base_query = base_query.order_by(desc(sort_column))
            else:
                base_query = base_query.order_by(asc(sort_column))

            # Apply pagination
            base_query = base_query.offset(query.offset).limit(query.limit)

            # Execute query
            result = await db.execute(base_query)
            audit_records = result.scalars().all()

            # Convert to response models
            events = [self._convert_to_response_model(record) for record in audit_records]

            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000

            # Build response
            response = AuditTrailResponse(
                events=events,
                total_count=total_count,
                filtered_count=len(events),
                limit=query.limit,
                offset=query.offset,
                has_more=query.offset + len(events) < total_count,
                query_metadata={
                    "filters_applied": len(filters),
                    "sort_by": query.sort_by,
                    "sort_order": query.sort_order,
                    "user_id": user_id
                },
                execution_time_ms=execution_time
            )

            logger.info(
                "Audit trail query completed",
                user_id=user_id,
                total_count=total_count,
                returned_count=len(events),
                execution_time_ms=execution_time,
                filters_applied=len(filters)
            )

            return response

        except Exception as e:
            logger.error(
                "Failed to query audit trail",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_event_by_id(
        self,
        event_id: UUID,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[AuditTrailEvent]:
        """Get a specific audit event by ID."""
        if db is None:
            db = await get_database()

        try:
            # Check permission to view audit events
            await self._check_audit_access_permission(user_id, [], db)

            result = await db.execute(
                select(ShareAuditTrail).where(ShareAuditTrail.event_id == event_id)
            )
            audit_record = result.scalar_one_or_none()

            if not audit_record:
                return None

            return self._convert_to_response_model(audit_record)

        except Exception as e:
            logger.error(
                "Failed to get audit event",
                event_id=str(event_id),
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> AuditTrailStatistics:
        """Get comprehensive audit trail statistics."""
        if db is None:
            db = await get_database()

        try:
            # Check permission to view audit statistics
            await self._check_audit_access_permission(user_id or "system", [], db)

            # Set default time range (last 30 days)
            if not start_time:
                start_time = datetime.now(timezone.utc) - timedelta(days=30)
            if not end_time:
                end_time = datetime.now(timezone.utc)

            # Base filters
            base_filters = [
                ShareAuditTrail.timestamp >= start_time,
                ShareAuditTrail.timestamp <= end_time
            ]

            # Total events
            total_result = await db.execute(
                select(func.count(ShareAuditTrail.event_id)).where(and_(*base_filters))
            )
            total_events = total_result.scalar() or 0

            # Event count by type
            type_result = await db.execute(
                select(ShareAuditTrail.event_type, func.count(ShareAuditTrail.event_id))
                .where(and_(*base_filters))
                .group_by(ShareAuditTrail.event_type)
            )
            event_count_by_type = {row[0]: row[1] for row in type_result.fetchall()}

            # Event count by category
            category_result = await db.execute(
                select(ShareAuditTrail.category, func.count(ShareAuditTrail.event_id))
                .where(and_(*base_filters))
                .group_by(ShareAuditTrail.category)
            )
            event_count_by_category = {row[0]: row[1] for row in category_result.fetchall()}

            # Event count by severity
            severity_result = await db.execute(
                select(ShareAuditTrail.severity, func.count(ShareAuditTrail.event_id))
                .where(and_(*base_filters))
                .group_by(ShareAuditTrail.severity)
            )
            event_count_by_severity = {row[0]: row[1] for row in severity_result.fetchall()}

            # Events by hour (last 24 hours)
            hourly_start = datetime.now(timezone.utc) - timedelta(hours=24)
            hourly_result = await db.execute(
                text("""
                    SELECT 
                        DATE_TRUNC('hour', timestamp) as hour,
                        COUNT(*) as count
                    FROM share_audit_trail 
                    WHERE timestamp >= :start_time AND timestamp <= :end_time
                    GROUP BY DATE_TRUNC('hour', timestamp)
                    ORDER BY hour
                """),
                {"start_time": hourly_start, "end_time": end_time}
            )
            events_by_hour = [
                {"hour": row[0].isoformat(), "count": row[1]} 
                for row in hourly_result.fetchall()
            ]

            # Events by day (last 30 days)
            daily_result = await db.execute(
                text("""
                    SELECT 
                        DATE_TRUNC('day', timestamp) as day,
                        COUNT(*) as count
                    FROM share_audit_trail 
                    WHERE timestamp >= :start_time AND timestamp <= :end_time
                    GROUP BY DATE_TRUNC('day', timestamp)
                    ORDER BY day
                """),
                {"start_time": start_time, "end_time": end_time}
            )
            events_by_day = [
                {"day": row[0].isoformat(), "count": row[1]} 
                for row in daily_result.fetchall()
            ]

            # Top active users
            user_result = await db.execute(
                select(ShareAuditTrail.user_id, func.count(ShareAuditTrail.event_id))
                .where(and_(*base_filters, ShareAuditTrail.user_id.is_not(None)))
                .group_by(ShareAuditTrail.user_id)
                .order_by(desc(func.count(ShareAuditTrail.event_id)))
                .limit(10)
            )
            top_active_users = [
                {"user_id": row[0], "event_count": row[1]} 
                for row in user_result.fetchall()
            ]

            # Unique users count
            unique_users_result = await db.execute(
                select(func.count(func.distinct(ShareAuditTrail.user_id)))
                .where(and_(*base_filters, ShareAuditTrail.user_id.is_not(None)))
            )
            unique_users_count = unique_users_result.scalar() or 0

            # Most accessed shares
            share_result = await db.execute(
                select(ShareAuditTrail.share_id, func.count(ShareAuditTrail.event_id))
                .where(and_(*base_filters, ShareAuditTrail.share_id.is_not(None)))
                .group_by(ShareAuditTrail.share_id)
                .order_by(desc(func.count(ShareAuditTrail.event_id)))
                .limit(10)
            )
            most_accessed_shares = [
                {"share_id": str(row[0]), "access_count": row[1]} 
                for row in share_result.fetchall()
            ]

            # Resource type activity
            resource_type_result = await db.execute(
                select(ShareAuditTrail.resource_type, func.count(ShareAuditTrail.event_id))
                .where(and_(*base_filters, ShareAuditTrail.resource_type.is_not(None)))
                .group_by(ShareAuditTrail.resource_type)
            )
            resource_type_activity = {row[0]: row[1] for row in resource_type_result.fetchall()}

            # Security events
            security_events_result = await db.execute(
                select(func.count(ShareAuditTrail.event_id))
                .where(and_(*base_filters, ShareAuditTrail.category == AuditEventCategory.SECURITY))
            )
            security_events_count = security_events_result.scalar() or 0

            # Failed authorization count
            failed_auth_result = await db.execute(
                select(func.count(ShareAuditTrail.event_id))
                .where(and_(*base_filters, ShareAuditTrail.authorization_granted == False))
            )
            failed_authorization_count = failed_auth_result.scalar() or 0

            # Suspicious activity indicators (high severity events, multiple failed auths from same IP)
            suspicious_activity = await self._detect_suspicious_activity(start_time, end_time, db)

            # Peak activity hours
            peak_hours_result = await db.execute(
                text("""
                    SELECT 
                        EXTRACT(hour FROM timestamp) as hour,
                        COUNT(*) as count
                    FROM share_audit_trail 
                    WHERE timestamp >= :start_time AND timestamp <= :end_time
                    GROUP BY EXTRACT(hour FROM timestamp)
                    ORDER BY count DESC
                    LIMIT 5
                """),
                {"start_time": start_time, "end_time": end_time}
            )
            peak_activity_hours = [int(row[0]) for row in peak_hours_result.fetchall()]

            # Average events per day
            days_in_range = (end_time - start_time).days or 1
            average_events_per_day = total_events / days_in_range

            # Retention policy compliance
            retention_compliance = await self._check_retention_compliance(db)

            return AuditTrailStatistics(
                total_events=total_events,
                event_count_by_type=event_count_by_type,
                event_count_by_category=event_count_by_category,
                event_count_by_severity=event_count_by_severity,
                events_by_hour=events_by_hour,
                events_by_day=events_by_day,
                top_active_users=top_active_users,
                unique_users_count=unique_users_count,
                most_accessed_shares=most_accessed_shares,
                resource_type_activity=resource_type_activity,
                security_events_count=security_events_count,
                failed_authorization_count=failed_authorization_count,
                suspicious_activity_indicators=suspicious_activity,
                peak_activity_hours=peak_activity_hours,
                average_events_per_day=average_events_per_day,
                retention_policy_compliance=retention_compliance
            )

        except Exception as e:
            logger.error(
                "Failed to get audit trail statistics",
                error=str(e)
            )
            raise

    async def cleanup_expired_events(
        self,
        batch_size: Optional[int] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Clean up expired audit events based on retention policy."""
        if db is None:
            db = await get_database()

        batch_size = batch_size or self.batch_size
        
        try:
            now = datetime.now(timezone.utc)
            
            # Find expired events
            expired_query = select(func.count(ShareAuditTrail.event_id)).where(
                ShareAuditTrail.retention_date <= now
            )
            count_result = await db.execute(expired_query)
            total_expired = count_result.scalar() or 0

            if total_expired == 0:
                return {
                    "total_expired": 0,
                    "deleted_count": 0,
                    "batches_processed": 0,
                    "cleanup_completed": True
                }

            # Delete in batches
            deleted_count = 0
            batches_processed = 0

            while True:
                # Get a batch of expired event IDs
                batch_query = select(ShareAuditTrail.event_id).where(
                    ShareAuditTrail.retention_date <= now
                ).limit(batch_size)
                
                batch_result = await db.execute(batch_query)
                batch_ids = [row[0] for row in batch_result.fetchall()]
                
                if not batch_ids:
                    break

                # Delete the batch
                from sqlalchemy import delete
                delete_result = await db.execute(
                    delete(ShareAuditTrail).where(
                        ShareAuditTrail.event_id.in_(batch_ids)
                    )
                )
                
                batch_deleted = delete_result.rowcount
                deleted_count += batch_deleted
                batches_processed += 1
                
                await db.commit()
                
                logger.info(
                    "Audit trail cleanup batch completed",
                    batch_size=len(batch_ids),
                    deleted_count=batch_deleted,
                    total_deleted=deleted_count,
                    batches_processed=batches_processed
                )

                # Small delay between batches to avoid overloading the database
                await asyncio.sleep(0.1)

            logger.info(
                "Audit trail cleanup completed",
                total_expired=total_expired,
                deleted_count=deleted_count,
                batches_processed=batches_processed
            )

            return {
                "total_expired": total_expired,
                "deleted_count": deleted_count,
                "batches_processed": batches_processed,
                "cleanup_completed": True
            }

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to cleanup expired audit events",
                error=str(e)
            )
            raise

    async def _check_audit_access_permission(
        self,
        user_id: str,
        additional_filters: List,
        db: AsyncSession
    ) -> None:
        """Check if user has permission to access audit trails."""
        # Check if user has audit access permissions
        from app.services.role_permission_service import role_permission_service
        
        permission_check = await role_permission_service.check_permission(
            user_id, ShareOperation.VIEW_ANALYTICS, PermissionScope.GLOBAL, db=db
        )
        
        if not permission_check.has_permission:
            # If no global permission, user can only see their own events
            additional_filters.append(ShareAuditTrail.user_id == user_id)
            
            logger.info(
                "Audit trail access restricted to user's own events",
                user_id=user_id
            )

    async def _detect_suspicious_activity(
        self,
        start_time: datetime,
        end_time: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Detect suspicious activity patterns."""
        suspicious_indicators = []

        try:
            # Multiple failed authentication attempts from same IP
            failed_auth_by_ip = await db.execute(
                text("""
                    SELECT 
                        ip_address,
                        COUNT(*) as failed_count,
                        COUNT(DISTINCT user_id) as affected_users
                    FROM share_audit_trail 
                    WHERE timestamp >= :start_time 
                        AND timestamp <= :end_time
                        AND authorization_granted = false
                        AND ip_address IS NOT NULL
                    GROUP BY ip_address
                    HAVING COUNT(*) >= 5
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """),
                {"start_time": start_time, "end_time": end_time}
            )
            
            for row in failed_auth_by_ip.fetchall():
                suspicious_indicators.append({
                    "type": "multiple_failed_auth",
                    "severity": "high",
                    "ip_address": row[0],
                    "failed_attempts": row[1],
                    "affected_users": row[2],
                    "description": f"Multiple failed authentication attempts ({row[1]}) from IP {row[0]}"
                })

            # High severity events
            high_severity_events = await db.execute(
                select(func.count(ShareAuditTrail.event_id))
                .where(
                    and_(
                        ShareAuditTrail.timestamp >= start_time,
                        ShareAuditTrail.timestamp <= end_time,
                        ShareAuditTrail.severity == AuditEventSeverity.CRITICAL
                    )
                )
            )
            critical_count = high_severity_events.scalar() or 0
            
            if critical_count > 0:
                suspicious_indicators.append({
                    "type": "critical_events",
                    "severity": "critical",
                    "count": critical_count,
                    "description": f"Found {critical_count} critical security events"
                })

        except Exception as e:
            logger.warning(
                "Failed to detect suspicious activity",
                error=str(e)
            )

        return suspicious_indicators

    async def _check_retention_compliance(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Check compliance with retention policies."""
        try:
            now = datetime.now(timezone.utc)
            
            # Events that should be expired but still exist
            overdue_result = await db.execute(
                select(func.count(ShareAuditTrail.event_id))
                .where(ShareAuditTrail.retention_date <= now)
            )
            overdue_count = overdue_result.scalar() or 0

            # Total events
            total_result = await db.execute(
                select(func.count(ShareAuditTrail.event_id))
            )
            total_count = total_result.scalar() or 0

            # Compliance percentage
            compliance_percentage = ((total_count - overdue_count) / total_count * 100) if total_count > 0 else 100

            return {
                "total_events": total_count,
                "overdue_events": overdue_count,
                "compliance_percentage": round(compliance_percentage, 2),
                "retention_days": self.retention_days,
                "next_cleanup_recommended": overdue_count > 0
            }

        except Exception as e:
            logger.warning(
                "Failed to check retention compliance",
                error=str(e)
            )
            return {
                "total_events": 0,
                "overdue_events": 0,
                "compliance_percentage": 100,
                "retention_days": self.retention_days,
                "next_cleanup_recommended": False
            }

    def _convert_to_response_model(self, audit_record: ShareAuditTrail) -> AuditTrailEvent:
        """Convert database model to response model."""
        return AuditTrailEvent(
            event_id=audit_record.event_id,
            event_type=audit_record.event_type,
            category=audit_record.category,
            severity=audit_record.severity,
            title=audit_record.title,
            description=audit_record.description,
            timestamp=audit_record.timestamp,
            user_id=audit_record.user_id,
            session_id=audit_record.session_id,
            ip_address=audit_record.ip_address,
            user_agent=audit_record.user_agent,
            share_id=audit_record.share_id,
            resource_id=audit_record.resource_id,
            resource_type=audit_record.resource_type,
            operation=audit_record.operation,
            scope=audit_record.scope,
            scope_id=audit_record.scope_id,
            before_state=audit_record.before_state,
            after_state=audit_record.after_state,
            context=audit_record.context,
            metadata=audit_record.metadata,
            correlation_id=audit_record.correlation_id,
            request_id=audit_record.request_id,
            authentication_method=audit_record.authentication_method,
            authorization_granted=audit_record.authorization_granted,
            service_name=audit_record.service_name,
            service_version=audit_record.service_version,
            tags=audit_record.tags
        )


# Service instance
audit_trail_service = AuditTrailService()