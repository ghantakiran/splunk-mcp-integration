"""
Data models for Email Service.
"""

from .email_models import (
    EmailMessage,
    EmailRecipient,
    EmailAttachment,
    EmailTemplate,
    EmailQueue,
    EmailLog,
    EmailThread,
    ScheduledEmail,
    EmailSubscription,
    EmailPreference,
    EmailMetrics,
    EmailStatus,
    EmailPriority,
    EmailType,
    AttachmentType,
)

from .user_models import (
    EmailUser,
    UserEmailSettings,
    UserSubscription,
)

from .report_models import (
    EmailReport,
    ReportSchedule,
    ReportFormat,
    ReportStatus,
)

__all__ = [
    # Email models
    "EmailMessage",
    "EmailRecipient", 
    "EmailAttachment",
    "EmailTemplate",
    "EmailQueue",
    "EmailLog",
    "EmailThread",
    "ScheduledEmail",
    "EmailSubscription",
    "EmailPreference",
    "EmailMetrics",
    "EmailStatus",
    "EmailPriority",
    "EmailType",
    "AttachmentType",
    
    # User models
    "EmailUser",
    "UserEmailSettings",
    "UserSubscription",
    
    # Report models
    "EmailReport",
    "ReportSchedule",
    "ReportFormat",
    "ReportStatus",
]