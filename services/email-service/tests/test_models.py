"""
Tests for Email Service data models.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from app.models.email_models import (
    EmailStatus, EmailPriority, EmailType, AttachmentType,
    EmailMessage, EmailRecipient, EmailAttachment, EmailTemplate,
    EmailQueue, EmailLog, EmailThread, ScheduledEmail,
    EmailSubscription, EmailPreference, EmailMetrics,
    EmailMessageCreate, EmailMessageResponse,
    EmailTemplateCreate, EmailTemplateResponse,
    EmailStatsResponse, EmailQueueStatus
)


class TestEnums:
    """Test suite for enum classes."""

    def test_email_status_enum(self):
        """Test EmailStatus enum values."""
        assert EmailStatus.PENDING == "pending"
        assert EmailStatus.QUEUED == "queued"
        assert EmailStatus.SENDING == "sending"
        assert EmailStatus.SENT == "sent"
        assert EmailStatus.DELIVERED == "delivered"
        assert EmailStatus.FAILED == "failed"
        assert EmailStatus.BOUNCED == "bounced"
        assert EmailStatus.REJECTED == "rejected"
        
        # Test enum iteration
        statuses = list(EmailStatus)
        assert len(statuses) == 8

    def test_email_priority_enum(self):
        """Test EmailPriority enum values."""
        assert EmailPriority.LOW == "low"
        assert EmailPriority.NORMAL == "normal"
        assert EmailPriority.HIGH == "high"
        assert EmailPriority.URGENT == "urgent"
        
        # Test enum iteration
        priorities = list(EmailPriority)
        assert len(priorities) == 4

    def test_email_type_enum(self):
        """Test EmailType enum values."""
        assert EmailType.QUERY_REQUEST == "query_request"
        assert EmailType.QUERY_RESPONSE == "query_response"
        assert EmailType.REPORT == "report"
        assert EmailType.ALERT == "alert"
        assert EmailType.NOTIFICATION == "notification"
        assert EmailType.AUTO_RESPONSE == "auto_response"
        assert EmailType.SUBSCRIPTION == "subscription"
        
        # Test enum iteration
        types = list(EmailType)
        assert len(types) == 7

    def test_attachment_type_enum(self):
        """Test AttachmentType enum values."""
        assert AttachmentType.PDF == "pdf"
        assert AttachmentType.CSV == "csv"
        assert AttachmentType.XLSX == "xlsx"
        assert AttachmentType.HTML == "html"
        assert AttachmentType.PNG == "png"
        assert AttachmentType.JPG == "jpg"
        assert AttachmentType.TXT == "txt"
        assert AttachmentType.ZIP == "zip"
        
        # Test enum iteration
        types = list(AttachmentType)
        assert len(types) == 8


class TestEmailMessageCreate:
    """Test suite for EmailMessageCreate model."""

    def test_valid_email_message_create(self):
        """Test valid email message creation."""
        data = {
            "recipient_email": "user@example.com",
            "recipient_name": "Test User",
            "subject": "Test Email Subject",
            "body_text": "This is a test email body.",
            "body_html": "<p>This is a test email body.</p>",
            "email_type": EmailType.NOTIFICATION,
            "priority": EmailPriority.HIGH,
            "reply_to": "noreply@example.com",
            "cc": ["cc@example.com"],
            "bcc": ["bcc@example.com"],
            "metadata": {"test": True}
        }
        
        email = EmailMessageCreate(**data)
        
        assert email.recipient_email == "user@example.com"
        assert email.recipient_name == "Test User"
        assert email.subject == "Test Email Subject"
        assert email.email_type == EmailType.NOTIFICATION
        assert email.priority == EmailPriority.HIGH
        assert email.cc == ["cc@example.com"]
        assert email.metadata == {"test": True}

    def test_email_message_create_minimal_data(self):
        """Test email message creation with minimal required data."""
        data = {
            "recipient_email": "user@example.com",
            "subject": "Test Subject"
        }
        
        email = EmailMessageCreate(**data)
        
        assert email.recipient_email == "user@example.com"
        assert email.subject == "Test Subject"
        assert email.recipient_name is None
        assert email.body_text is None
        assert email.body_html is None
        assert email.email_type == EmailType.NOTIFICATION  # Default
        assert email.priority == EmailPriority.NORMAL  # Default
        assert email.cc is None
        assert email.bcc is None
        assert email.metadata is None

    def test_invalid_email_address(self):
        """Test validation failure for invalid email address."""
        data = {
            "recipient_email": "invalid-email",
            "subject": "Test Subject"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailMessageCreate(**data)
        
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if e["loc"] == ("recipient_email",)]
        assert len(email_errors) > 0

    def test_empty_subject(self):
        """Test validation failure for empty subject."""
        data = {
            "recipient_email": "user@example.com",
            "subject": ""
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailMessageCreate(**data)
        
        errors = exc_info.value.errors()
        subject_errors = [e for e in errors if e["loc"] == ("subject",)]
        assert len(subject_errors) > 0

    def test_subject_too_long(self):
        """Test validation failure for subject too long."""
        data = {
            "recipient_email": "user@example.com",
            "subject": "x" * 501  # Exceeds max length of 500
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailMessageCreate(**data)
        
        errors = exc_info.value.errors()
        subject_errors = [e for e in errors if e["loc"] == ("subject",)]
        assert len(subject_errors) > 0

    def test_invalid_cc_email(self):
        """Test validation failure for invalid CC email."""
        data = {
            "recipient_email": "user@example.com",
            "subject": "Test Subject",
            "cc": ["invalid-email"]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailMessageCreate(**data)
        
        errors = exc_info.value.errors()
        cc_errors = [e for e in errors if "cc" in e["loc"]]
        assert len(cc_errors) > 0

    def test_invalid_bcc_email(self):
        """Test validation failure for invalid BCC email."""
        data = {
            "recipient_email": "user@example.com",
            "subject": "Test Subject",
            "bcc": ["invalid-email"]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailMessageCreate(**data)
        
        errors = exc_info.value.errors()
        bcc_errors = [e for e in errors if "bcc" in e["loc"]]
        assert len(bcc_errors) > 0

    def test_invalid_reply_to_email(self):
        """Test validation failure for invalid reply-to email."""
        data = {
            "recipient_email": "user@example.com",
            "subject": "Test Subject",
            "reply_to": "invalid-email"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailMessageCreate(**data)
        
        errors = exc_info.value.errors()
        reply_to_errors = [e for e in errors if e["loc"] == ("reply_to",)]
        assert len(reply_to_errors) > 0

    def test_invalid_email_type(self):
        """Test validation failure for invalid email type."""
        data = {
            "recipient_email": "user@example.com",
            "subject": "Test Subject",
            "email_type": "invalid_type"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailMessageCreate(**data)
        
        errors = exc_info.value.errors()
        type_errors = [e for e in errors if e["loc"] == ("email_type",)]
        assert len(type_errors) > 0

    def test_invalid_priority(self):
        """Test validation failure for invalid priority."""
        data = {
            "recipient_email": "user@example.com",
            "subject": "Test Subject",
            "priority": "invalid_priority"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailMessageCreate(**data)
        
        errors = exc_info.value.errors()
        priority_errors = [e for e in errors if e["loc"] == ("priority",)]
        assert len(priority_errors) > 0


class TestEmailMessageResponse:
    """Test suite for EmailMessageResponse model."""

    def test_valid_email_message_response(self):
        """Test valid email message response."""
        email_id = uuid4()
        created_at = datetime.utcnow()
        sent_at = datetime.utcnow()
        
        data = {
            "id": email_id,
            "message_id": "test-message-123@example.com",
            "status": EmailStatus.SENT,
            "recipient_email": "user@example.com",
            "subject": "Test Subject",
            "email_type": EmailType.NOTIFICATION,
            "priority": EmailPriority.HIGH,
            "created_at": created_at,
            "sent_at": sent_at
        }
        
        response = EmailMessageResponse(**data)
        
        assert response.id == email_id
        assert response.message_id == "test-message-123@example.com"
        assert response.status == EmailStatus.SENT
        assert response.recipient_email == "user@example.com"
        assert response.subject == "Test Subject"
        assert response.email_type == EmailType.NOTIFICATION
        assert response.priority == EmailPriority.HIGH
        assert response.created_at == created_at
        assert response.sent_at == sent_at

    def test_email_message_response_minimal_data(self):
        """Test email message response with minimal data."""
        email_id = uuid4()
        created_at = datetime.utcnow()
        
        data = {
            "id": email_id,
            "message_id": "test-message-123@example.com",
            "status": EmailStatus.PENDING,
            "recipient_email": "user@example.com",
            "subject": "Test Subject",
            "email_type": EmailType.NOTIFICATION,
            "priority": EmailPriority.NORMAL,
            "created_at": created_at
        }
        
        response = EmailMessageResponse(**data)
        
        assert response.id == email_id
        assert response.sent_at is None


class TestEmailTemplateCreate:
    """Test suite for EmailTemplateCreate model."""

    def test_valid_email_template_create(self):
        """Test valid email template creation."""
        data = {
            "name": "test-template",
            "description": "A test email template",
            "subject_template": "Test Subject: {{variable1}}",
            "body_text_template": "Hello {{name}}, this is a test.",
            "body_html_template": "<p>Hello <strong>{{name}}</strong>, this is a test.</p>",
            "email_type": EmailType.NOTIFICATION,
            "variables": ["name", "variable1"],
            "default_values": {"variable1": "default"}
        }
        
        template = EmailTemplateCreate(**data)
        
        assert template.name == "test-template"
        assert template.description == "A test email template"
        assert template.subject_template == "Test Subject: {{variable1}}"
        assert template.email_type == EmailType.NOTIFICATION
        assert template.variables == ["name", "variable1"]
        assert template.default_values == {"variable1": "default"}

    def test_email_template_create_minimal_data(self):
        """Test email template creation with minimal data."""
        data = {
            "name": "minimal-template",
            "subject_template": "Test Subject",
            "email_type": EmailType.NOTIFICATION
        }
        
        template = EmailTemplateCreate(**data)
        
        assert template.name == "minimal-template"
        assert template.description is None
        assert template.body_text_template is None
        assert template.body_html_template is None
        assert template.variables is None
        assert template.default_values is None

    def test_invalid_template_name_empty(self):
        """Test validation failure for empty template name."""
        data = {
            "name": "",
            "subject_template": "Test Subject",
            "email_type": EmailType.NOTIFICATION
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailTemplateCreate(**data)
        
        errors = exc_info.value.errors()
        name_errors = [e for e in errors if e["loc"] == ("name",)]
        assert len(name_errors) > 0

    def test_invalid_template_name_too_long(self):
        """Test validation failure for template name too long."""
        data = {
            "name": "x" * 256,  # Exceeds max length of 255
            "subject_template": "Test Subject",
            "email_type": EmailType.NOTIFICATION
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailTemplateCreate(**data)
        
        errors = exc_info.value.errors()
        name_errors = [e for e in errors if e["loc"] == ("name",)]
        assert len(name_errors) > 0

    def test_invalid_subject_template_empty(self):
        """Test validation failure for empty subject template."""
        data = {
            "name": "test-template",
            "subject_template": "",
            "email_type": EmailType.NOTIFICATION
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailTemplateCreate(**data)
        
        errors = exc_info.value.errors()
        subject_errors = [e for e in errors if e["loc"] == ("subject_template",)]
        assert len(subject_errors) > 0

    def test_invalid_subject_template_too_long(self):
        """Test validation failure for subject template too long."""
        data = {
            "name": "test-template",
            "subject_template": "x" * 501,  # Exceeds max length of 500
            "email_type": EmailType.NOTIFICATION
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EmailTemplateCreate(**data)
        
        errors = exc_info.value.errors()
        subject_errors = [e for e in errors if e["loc"] == ("subject_template",)]
        assert len(subject_errors) > 0


class TestEmailTemplateResponse:
    """Test suite for EmailTemplateResponse model."""

    def test_valid_email_template_response(self):
        """Test valid email template response."""
        template_id = uuid4()
        created_at = datetime.utcnow()
        
        data = {
            "id": template_id,
            "name": "test-template",
            "description": "A test template",
            "email_type": EmailType.NOTIFICATION,
            "is_active": True,
            "version": 2,
            "created_at": created_at
        }
        
        response = EmailTemplateResponse(**data)
        
        assert response.id == template_id
        assert response.name == "test-template"
        assert response.description == "A test template"
        assert response.email_type == EmailType.NOTIFICATION
        assert response.is_active is True
        assert response.version == 2
        assert response.created_at == created_at

    def test_email_template_response_minimal_data(self):
        """Test email template response with minimal data."""
        template_id = uuid4()
        created_at = datetime.utcnow()
        
        data = {
            "id": template_id,
            "name": "minimal-template",
            "email_type": EmailType.NOTIFICATION,
            "is_active": True,
            "version": 1,
            "created_at": created_at
        }
        
        response = EmailTemplateResponse(**data)
        
        assert response.id == template_id
        assert response.description is None


class TestEmailStatsResponse:
    """Test suite for EmailStatsResponse model."""

    def test_valid_email_stats_response(self):
        """Test valid email stats response."""
        data = {
            "total_sent": 1000,
            "total_delivered": 950,
            "total_failed": 30,
            "total_bounced": 20,
            "delivery_rate": 95.0,
            "bounce_rate": 2.0,
            "recent_activity": [
                {"timestamp": "2025-01-16T10:00:00Z", "event": "sent", "count": 10},
                {"timestamp": "2025-01-16T11:00:00Z", "event": "delivered", "count": 9}
            ]
        }
        
        stats = EmailStatsResponse(**data)
        
        assert stats.total_sent == 1000
        assert stats.total_delivered == 950
        assert stats.total_failed == 30
        assert stats.total_bounced == 20
        assert stats.delivery_rate == 95.0
        assert stats.bounce_rate == 2.0
        assert len(stats.recent_activity) == 2
        assert stats.recent_activity[0]["event"] == "sent"

    def test_email_stats_response_zero_values(self):
        """Test email stats response with zero values."""
        data = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "total_bounced": 0,
            "delivery_rate": 0.0,
            "bounce_rate": 0.0,
            "recent_activity": []
        }
        
        stats = EmailStatsResponse(**data)
        
        assert stats.total_sent == 0
        assert stats.delivery_rate == 0.0
        assert len(stats.recent_activity) == 0


class TestEmailQueueStatus:
    """Test suite for EmailQueueStatus model."""

    def test_valid_email_queue_status(self):
        """Test valid email queue status."""
        oldest_pending = datetime.utcnow()
        
        data = {
            "queue_name": "default",
            "pending_count": 25,
            "processing_count": 5,
            "failed_count": 2,
            "average_processing_time": 1.5,
            "oldest_pending": oldest_pending
        }
        
        status = EmailQueueStatus(**data)
        
        assert status.queue_name == "default"
        assert status.pending_count == 25
        assert status.processing_count == 5
        assert status.failed_count == 2
        assert status.average_processing_time == 1.5
        assert status.oldest_pending == oldest_pending

    def test_email_queue_status_minimal_data(self):
        """Test email queue status with minimal data."""
        data = {
            "queue_name": "high-priority",
            "pending_count": 0,
            "processing_count": 0,
            "failed_count": 0,
            "average_processing_time": 0.0
        }
        
        status = EmailQueueStatus(**data)
        
        assert status.queue_name == "high-priority"
        assert status.oldest_pending is None


class TestDatabaseModels:
    """Test suite for SQLAlchemy database models."""

    def test_email_message_model_structure(self):
        """Test EmailMessage model structure."""
        # Test that the model has expected columns
        assert hasattr(EmailMessage, 'id')
        assert hasattr(EmailMessage, 'message_id')
        assert hasattr(EmailMessage, 'sender_email')
        assert hasattr(EmailMessage, 'recipient_email')
        assert hasattr(EmailMessage, 'subject')
        assert hasattr(EmailMessage, 'body_text')
        assert hasattr(EmailMessage, 'body_html')
        assert hasattr(EmailMessage, 'email_type')
        assert hasattr(EmailMessage, 'priority')
        assert hasattr(EmailMessage, 'status')
        assert hasattr(EmailMessage, 'created_at')
        
        # Test table name
        assert EmailMessage.__tablename__ == "email_messages"

    def test_email_template_model_structure(self):
        """Test EmailTemplate model structure."""
        assert hasattr(EmailTemplate, 'id')
        assert hasattr(EmailTemplate, 'name')
        assert hasattr(EmailTemplate, 'subject_template')
        assert hasattr(EmailTemplate, 'body_text_template')
        assert hasattr(EmailTemplate, 'body_html_template')
        assert hasattr(EmailTemplate, 'email_type')
        assert hasattr(EmailTemplate, 'is_active')
        assert hasattr(EmailTemplate, 'version')
        assert hasattr(EmailTemplate, 'created_at')
        
        # Test table name
        assert EmailTemplate.__tablename__ == "email_templates"

    def test_email_recipient_model_structure(self):
        """Test EmailRecipient model structure."""
        assert hasattr(EmailRecipient, 'id')
        assert hasattr(EmailRecipient, 'message_id')
        assert hasattr(EmailRecipient, 'email_address')
        assert hasattr(EmailRecipient, 'name')
        assert hasattr(EmailRecipient, 'recipient_type')
        assert hasattr(EmailRecipient, 'status')
        assert hasattr(EmailRecipient, 'sent_at')
        assert hasattr(EmailRecipient, 'delivered_at')
        
        # Test table name
        assert EmailRecipient.__tablename__ == "email_recipients"

    def test_email_attachment_model_structure(self):
        """Test EmailAttachment model structure."""
        assert hasattr(EmailAttachment, 'id')
        assert hasattr(EmailAttachment, 'message_id')
        assert hasattr(EmailAttachment, 'filename')
        assert hasattr(EmailAttachment, 'content_type')
        assert hasattr(EmailAttachment, 'file_size')
        assert hasattr(EmailAttachment, 'attachment_type')
        assert hasattr(EmailAttachment, 'file_path')
        assert hasattr(EmailAttachment, 'created_at')
        
        # Test table name
        assert EmailAttachment.__tablename__ == "email_attachments"

    def test_email_queue_model_structure(self):
        """Test EmailQueue model structure."""
        assert hasattr(EmailQueue, 'id')
        assert hasattr(EmailQueue, 'message_id')
        assert hasattr(EmailQueue, 'priority')
        assert hasattr(EmailQueue, 'scheduled_at')
        assert hasattr(EmailQueue, 'processed_at')
        assert hasattr(EmailQueue, 'queue_name')
        assert hasattr(EmailQueue, 'status')
        
        # Test table name
        assert EmailQueue.__tablename__ == "email_queue"

    def test_scheduled_email_model_structure(self):
        """Test ScheduledEmail model structure."""
        assert hasattr(ScheduledEmail, 'id')
        assert hasattr(ScheduledEmail, 'name')
        assert hasattr(ScheduledEmail, 'cron_expression')
        assert hasattr(ScheduledEmail, 'timezone')
        assert hasattr(ScheduledEmail, 'next_run_at')
        assert hasattr(ScheduledEmail, 'template_id')
        assert hasattr(ScheduledEmail, 'recipients')
        assert hasattr(ScheduledEmail, 'is_active')
        
        # Test table name
        assert ScheduledEmail.__tablename__ == "scheduled_emails"

    def test_email_subscription_model_structure(self):
        """Test EmailSubscription model structure."""
        assert hasattr(EmailSubscription, 'id')
        assert hasattr(EmailSubscription, 'user_id')
        assert hasattr(EmailSubscription, 'email_address')
        assert hasattr(EmailSubscription, 'subscription_type')
        assert hasattr(EmailSubscription, 'frequency')
        assert hasattr(EmailSubscription, 'is_active')
        assert hasattr(EmailSubscription, 'created_at')
        
        # Test table name
        assert EmailSubscription.__tablename__ == "email_subscriptions"


class TestModelValidation:
    """Test suite for model validation and edge cases."""

    def test_email_message_create_with_template_variables(self):
        """Test email message creation with template variables."""
        data = {
            "recipient_email": "user@example.com",
            "subject": "Test Subject",
            "template_id": uuid4(),
            "template_variables": {
                "name": "John Doe",
                "company": "Example Corp",
                "date": "2025-01-16"
            }
        }
        
        email = EmailMessageCreate(**data)
        
        assert email.template_id is not None
        assert email.template_variables == {
            "name": "John Doe",
            "company": "Example Corp",
            "date": "2025-01-16"
        }

    def test_email_message_create_with_attachments(self):
        """Test email message creation with attachments."""
        data = {
            "recipient_email": "user@example.com",
            "subject": "Test Subject",
            "attachments": [
                "/path/to/file1.pdf",
                "/path/to/file2.csv",
                "https://example.com/file3.png"
            ]
        }
        
        email = EmailMessageCreate(**data)
        
        assert len(email.attachments) == 3
        assert "/path/to/file1.pdf" in email.attachments
        assert "https://example.com/file3.png" in email.attachments

    def test_email_template_create_with_complex_variables(self):
        """Test email template creation with complex variables."""
        data = {
            "name": "complex-template",
            "subject_template": "{{subject_prefix}}: {{title}}",
            "body_html_template": """
            <h1>Hello {{user.name}}</h1>
            <p>Your {{report.type}} report is ready.</p>
            <ul>
            {{#each items}}
                <li>{{this.name}}: {{this.value}}</li>
            {{/each}}
            </ul>
            """,
            "email_type": EmailType.REPORT,
            "variables": ["user.name", "report.type", "items", "subject_prefix", "title"],
            "default_values": {
                "subject_prefix": "Report",
                "items": []
            }
        }
        
        template = EmailTemplateCreate(**data)
        
        assert len(template.variables) == 5
        assert "user.name" in template.variables
        assert template.default_values["subject_prefix"] == "Report"