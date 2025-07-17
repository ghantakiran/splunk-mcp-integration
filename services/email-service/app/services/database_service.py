"""
Database service for Email Service.
"""

import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete, and_, or_, func, desc

from app.core.config import settings, get_database_config
from app.core.logging import get_logger
from app.models.email_models import (
    EmailMessage, EmailRecipient, EmailAttachment, EmailTemplate,
    EmailQueue, EmailLog, EmailThread, ScheduledEmail, EmailSubscription,
    EmailPreference, EmailMetrics, EmailStatus, EmailPriority, EmailType
)
from app.models.user_models import EmailUser, UserEmailSettings, UserSubscription
from app.models.report_models import EmailReport, ReportSchedule, ReportTemplate, ReportExecution

logger = get_logger(__name__)


class DatabaseService:
    """Database service for email operations."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._pool = None
    
    async def initialize(self):
        """Initialize database connection."""
        try:
            config = get_database_config()
            
            # Create async engine
            self.engine = create_async_engine(
                config["url"],
                pool_size=config["pool_size"],
                max_overflow=config["max_overflow"],
                pool_timeout=config["pool_timeout"],
                pool_recycle=config["pool_recycle"],
                echo=config["echo"],
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            # Test connection
            async with self.session_factory() as session:
                await session.execute(select(1))
            
            logger.info("Database service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize database service", error=str(e))
            raise
    
    async def cleanup(self):
        """Cleanup database connections."""
        try:
            if self.engine:
                await self.engine.dispose()
            logger.info("Database service cleanup completed")
        except Exception as e:
            logger.error("Error during database cleanup", error=str(e))
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if not self.session_factory:
            raise RuntimeError("Database service not initialized")
        return self.session_factory()
    
    # Email Message Operations
    
    async def create_email_message(self, message_data: Dict[str, Any]) -> EmailMessage:
        """Create a new email message."""
        async with self.get_session() as session:
            message = EmailMessage(**message_data)
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return message
    
    async def get_email_message(self, message_id: UUID) -> Optional[EmailMessage]:
        """Get email message by ID."""
        async with self.get_session() as session:
            result = await session.execute(
                select(EmailMessage).where(EmailMessage.id == message_id)
            )
            return result.scalar_one_or_none()
    
    async def get_email_messages_by_user(
        self, 
        user_id: str, 
        limit: int = 50,
        offset: int = 0,
        status: Optional[EmailStatus] = None,
        email_type: Optional[EmailType] = None,
    ) -> List[EmailMessage]:
        """Get email messages for a user."""
        async with self.get_session() as session:
            query = select(EmailMessage).where(EmailMessage.user_id == user_id)
            
            if status:
                query = query.where(EmailMessage.status == status)
            
            if email_type:
                query = query.where(EmailMessage.email_type == email_type)
            
            query = query.order_by(desc(EmailMessage.created_at)).limit(limit).offset(offset)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def update_email_message_status(
        self, 
        message_id: UUID, 
        status: EmailStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update email message status."""
        async with self.get_session() as session:
            update_data = {"status": status}
            
            if status == EmailStatus.SENT:
                update_data["sent_at"] = datetime.utcnow()
            elif status == EmailStatus.DELIVERED:
                update_data["delivered_at"] = datetime.utcnow()
            elif status == EmailStatus.FAILED:
                update_data["failed_at"] = datetime.utcnow()
                if error_message:
                    update_data["error_message"] = error_message
            
            result = await session.execute(
                update(EmailMessage)
                .where(EmailMessage.id == message_id)
                .values(**update_data)
            )
            await session.commit()
            return result.rowcount > 0
    
    async def get_pending_emails(self, limit: int = 100) -> List[EmailMessage]:
        """Get pending email messages."""
        async with self.get_session() as session:
            result = await session.execute(
                select(EmailMessage)
                .where(EmailMessage.status.in_([EmailStatus.PENDING, EmailStatus.QUEUED]))
                .order_by(EmailMessage.priority.desc(), EmailMessage.created_at)
                .limit(limit)
            )
            return result.scalars().all()
    
    # Email Template Operations
    
    async def create_email_template(self, template_data: Dict[str, Any]) -> EmailTemplate:
        """Create a new email template."""
        async with self.get_session() as session:
            template = EmailTemplate(**template_data)
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return template
    
    async def get_email_template(self, template_id: UUID) -> Optional[EmailTemplate]:
        """Get email template by ID."""
        async with self.get_session() as session:
            result = await session.execute(
                select(EmailTemplate).where(EmailTemplate.id == template_id)
            )
            return result.scalar_one_or_none()
    
    async def get_email_template_by_name(self, name: str) -> Optional[EmailTemplate]:
        """Get email template by name."""
        async with self.get_session() as session:
            result = await session.execute(
                select(EmailTemplate).where(EmailTemplate.name == name)
            )
            return result.scalar_one_or_none()
    
    async def get_email_templates_by_type(self, email_type: EmailType) -> List[EmailTemplate]:
        """Get email templates by type."""
        async with self.get_session() as session:
            result = await session.execute(
                select(EmailTemplate)
                .where(and_(
                    EmailTemplate.email_type == email_type,
                    EmailTemplate.is_active == True
                ))
                .order_by(EmailTemplate.name)
            )
            return result.scalars().all()
    
    # User Operations
    
    async def create_user(self, user_data: Dict[str, Any]) -> EmailUser:
        """Create a new email user."""
        async with self.get_session() as session:
            user = EmailUser(**user_data)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def get_user(self, user_id: str) -> Optional[EmailUser]:
        """Get user by ID."""
        async with self.get_session() as session:
            result = await session.execute(
                select(EmailUser).where(EmailUser.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[EmailUser]:
        """Get user by email address."""
        async with self.get_session() as session:
            result = await session.execute(
                select(EmailUser).where(EmailUser.email_address == email)
            )
            return result.scalar_one_or_none()
    
    async def update_user_activity(self, user_id: str) -> bool:
        """Update user last activity timestamp."""
        async with self.get_session() as session:
            result = await session.execute(
                update(EmailUser)
                .where(EmailUser.id == user_id)
                .values(last_activity_at=datetime.utcnow())
            )
            await session.commit()
            return result.rowcount > 0
    
    # User Settings Operations
    
    async def get_user_settings(self, user_id: str) -> Optional[UserEmailSettings]:
        """Get user email settings."""
        async with self.get_session() as session:
            result = await session.execute(
                select(UserEmailSettings).where(UserEmailSettings.user_id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def create_user_settings(self, settings_data: Dict[str, Any]) -> UserEmailSettings:
        """Create user email settings."""
        async with self.get_session() as session:
            settings = UserEmailSettings(**settings_data)
            session.add(settings)
            await session.commit()
            await session.refresh(settings)
            return settings
    
    async def update_user_settings(
        self, 
        user_id: str, 
        settings_data: Dict[str, Any]
    ) -> bool:
        """Update user email settings."""
        async with self.get_session() as session:
            settings_data["updated_at"] = datetime.utcnow()
            result = await session.execute(
                update(UserEmailSettings)
                .where(UserEmailSettings.user_id == user_id)
                .values(**settings_data)
            )
            await session.commit()
            return result.rowcount > 0
    
    # Report Operations
    
    async def create_report(self, report_data: Dict[str, Any]) -> EmailReport:
        """Create a new email report."""
        async with self.get_session() as session:
            report = EmailReport(**report_data)
            session.add(report)
            await session.commit()
            await session.refresh(report)
            return report
    
    async def get_report(self, report_id: UUID) -> Optional[EmailReport]:
        """Get report by ID."""
        async with self.get_session() as session:
            result = await session.execute(
                select(EmailReport).where(EmailReport.id == report_id)
            )
            return result.scalar_one_or_none()
    
    async def get_reports_by_user(
        self, 
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EmailReport]:
        """Get reports for a user."""
        async with self.get_session() as session:
            result = await session.execute(
                select(EmailReport)
                .where(EmailReport.requested_by == user_id)
                .order_by(desc(EmailReport.requested_at))
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()
    
    async def update_report_status(
        self, 
        report_id: UUID, 
        status_data: Dict[str, Any]
    ) -> bool:
        """Update report status and metadata."""
        async with self.get_session() as session:
            result = await session.execute(
                update(EmailReport)
                .where(EmailReport.id == report_id)
                .values(**status_data)
            )
            await session.commit()
            return result.rowcount > 0
    
    # Subscription Operations
    
    async def create_subscription(self, subscription_data: Dict[str, Any]) -> UserSubscription:
        """Create a new user subscription."""
        async with self.get_session() as session:
            subscription = UserSubscription(**subscription_data)
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            return subscription
    
    async def get_subscription(self, subscription_id: UUID) -> Optional[UserSubscription]:
        """Get subscription by ID."""
        async with self.get_session() as session:
            result = await session.execute(
                select(UserSubscription).where(UserSubscription.id == subscription_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_subscriptions(self, user_id: str) -> List[UserSubscription]:
        """Get all subscriptions for a user."""
        async with self.get_session() as session:
            result = await session.execute(
                select(UserSubscription)
                .where(UserSubscription.user_id == user_id)
                .order_by(desc(UserSubscription.created_at))
            )
            return result.scalars().all()
    
    async def get_active_subscriptions(self) -> List[UserSubscription]:
        """Get all active subscriptions."""
        async with self.get_session() as session:
            result = await session.execute(
                select(UserSubscription)
                .where(and_(
                    UserSubscription.is_active == True,
                    UserSubscription.next_execution_at <= datetime.utcnow()
                ))
                .order_by(UserSubscription.next_execution_at)
            )
            return result.scalars().all()
    
    async def update_subscription_execution(
        self, 
        subscription_id: UUID,
        execution_data: Dict[str, Any]
    ) -> bool:
        """Update subscription execution status."""
        async with self.get_session() as session:
            execution_data["updated_at"] = datetime.utcnow()
            result = await session.execute(
                update(UserSubscription)
                .where(UserSubscription.id == subscription_id)
                .values(**execution_data)
            )
            await session.commit()
            return result.rowcount > 0
    
    # Statistics and Analytics
    
    async def get_email_stats(
        self, 
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get email statistics."""
        async with self.get_session() as session:
            query = select(EmailMessage)
            
            if user_id:
                query = query.where(EmailMessage.user_id == user_id)
            
            if start_date:
                query = query.where(EmailMessage.created_at >= start_date)
            
            if end_date:
                query = query.where(EmailMessage.created_at <= end_date)
            
            # Get basic counts
            total_result = await session.execute(
                select(func.count(EmailMessage.id)).select_from(query.subquery())
            )
            total_count = total_result.scalar() or 0
            
            # Get status breakdown
            status_result = await session.execute(
                select(EmailMessage.status, func.count(EmailMessage.id))
                .select_from(query.subquery())
                .group_by(EmailMessage.status)
            )
            status_counts = dict(status_result.all())
            
            # Get type breakdown
            type_result = await session.execute(
                select(EmailMessage.email_type, func.count(EmailMessage.id))
                .select_from(query.subquery())
                .group_by(EmailMessage.email_type)
            )
            type_counts = dict(type_result.all())
            
            return {
                "total_emails": total_count,
                "by_status": status_counts,
                "by_type": type_counts,
                "delivery_rate": (
                    status_counts.get(EmailStatus.DELIVERED, 0) / max(total_count, 1) * 100
                ),
                "failure_rate": (
                    status_counts.get(EmailStatus.FAILED, 0) / max(total_count, 1) * 100
                ),
            }
    
    async def record_email_metric(self, metric_data: Dict[str, Any]) -> None:
        """Record email metric."""
        async with self.get_session() as session:
            metric = EmailMetrics(**metric_data)
            session.add(metric)
            await session.commit()
    
    async def cleanup_old_records(self, days: int = 90) -> Dict[str, int]:
        """Cleanup old records."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cleanup_counts = {}
        
        async with self.get_session() as session:
            # Cleanup old email logs
            result = await session.execute(
                delete(EmailLog).where(EmailLog.timestamp < cutoff_date)
            )
            cleanup_counts["email_logs"] = result.rowcount
            
            # Cleanup old metrics
            result = await session.execute(
                delete(EmailMetrics).where(EmailMetrics.timestamp < cutoff_date)
            )
            cleanup_counts["email_metrics"] = result.rowcount
            
            # Cleanup completed reports older than retention period
            result = await session.execute(
                delete(EmailReport).where(and_(
                    EmailReport.expires_at < datetime.utcnow(),
                    EmailReport.status == "completed"
                ))
            )
            cleanup_counts["expired_reports"] = result.rowcount
            
            await session.commit()
        
        logger.info("Database cleanup completed", cleanup_counts=cleanup_counts)
        return cleanup_counts