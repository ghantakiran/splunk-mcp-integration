"""
Multi-channel notification service for alert delivery.
"""
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Any, Dict, List, Optional
import httpx
import aiosmtplib
from jinja2 import Template, Environment, DictLoader

from ..core.config import settings
from ..core.logging import AlertLogger
from ..models.notification import (
    NotificationChannel, NotificationTemplate, NotificationHistory,
    NotificationSendRequest, NotificationStatus, ChannelType
)
from ..models.alert import AlertIncident


class NotificationService:
    """Multi-channel notification delivery service."""
    
    def __init__(self):
        self.logger = AlertLogger("notification_service")
        
        # Template environment for rendering
        self.jinja_env = Environment(
            loader=DictLoader({}),
            autoescape=True
        )
        
        # Default templates
        self.default_templates = {
            "alert_triggered": {
                "subject": "🚨 Alert Triggered: {{ incident.title }}",
                "body": """
Alert Details:
- Alert: {{ incident.title }}
- Severity: {{ incident.severity | upper }}
- Triggered at: {{ incident.triggered_at }}
- Trigger Value: {{ incident.trigger_value }}

Description:
{{ incident.description }}

{% if incident.trigger_data %}
Data:
{% for item in incident.trigger_data[:5] %}
- {{ item }}
{% endfor %}
{% endif %}

Alert Rule: {{ rule.name }}
Query: {{ rule.spl_query }}
                """.strip()
            },
            "alert_resolved": {
                "subject": "✅ Alert Resolved: {{ incident.title }}",
                "body": """
Alert Resolved:
- Alert: {{ incident.title }}
- Resolved at: {{ incident.resolved_at }}
- Resolution Time: {{ incident.resolution_time_minutes }} minutes
- Resolved by: {{ incident.resolved_by }}

{% if incident.resolution_notes %}
Resolution Notes:
{{ incident.resolution_notes }}
{% endif %}
                """.strip()
            }
        }
        
        # Channel handlers
        self.channel_handlers = {
            ChannelType.EMAIL: self._send_email,
            ChannelType.SLACK: self._send_slack,
            ChannelType.TEAMS: self._send_teams,
            ChannelType.SMS: self._send_sms,
            ChannelType.WEBHOOK: self._send_webhook
        }
    
    async def send_notification(
        self,
        request: NotificationSendRequest,
        incident: AlertIncident,
        rule: Any,
        channels: List[NotificationChannel],
        template: Optional[NotificationTemplate] = None
    ) -> List[NotificationHistory]:
        """Send notifications across multiple channels."""
        notifications = []
        
        for channel in channels:
            try:
                # Get or create template
                if template is None:
                    template_content = self._get_default_template(
                        "alert_triggered", 
                        channel.channel_type
                    )
                else:
                    template_content = {
                        "subject": template.subject_template,
                        "body": template.body_template
                    }
                
                # Render template
                rendered = await self._render_template(
                    template_content, 
                    incident, 
                    rule
                )
                
                # Send notification
                notification = await self._send_single_notification(
                    channel=channel,
                    incident=incident,
                    subject=rendered["subject"],
                    content=rendered["body"],
                    recipients=request.recipients,
                    priority=request.priority,
                    metadata=request.metadata
                )
                
                notifications.append(notification)
                
            except Exception as e:
                self.logger.log_error(
                    "send_notification",
                    str(e),
                    {
                        "channel_id": channel.id,
                        "incident_id": incident.id,
                        "channel_type": channel.channel_type
                    }
                )
                
                # Create failed notification record
                notification = NotificationHistory(
                    id=f"failed_{datetime.utcnow().timestamp()}",
                    incident_id=incident.id,
                    channel_id=channel.id,
                    channel_type=channel.channel_type,
                    recipient="failed",
                    subject=rendered.get("subject", "Alert Notification") if 'rendered' in locals() else "Alert Notification",
                    content="Failed to send",
                    status=NotificationStatus.FAILED.value,
                    error_message=str(e),
                    created_at=datetime.utcnow()
                )
                notifications.append(notification)
        
        return notifications
    
    async def _send_single_notification(
        self,
        channel: NotificationChannel,
        incident: AlertIncident,
        subject: str,
        content: str,
        recipients: Optional[List[str]] = None,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationHistory:
        """Send a single notification through a specific channel."""
        
        # Create notification record
        notification = NotificationHistory(
            id=f"notification_{datetime.utcnow().timestamp()}",
            incident_id=incident.id,
            channel_id=channel.id,
            channel_type=channel.channel_type,
            recipient=recipients[0] if recipients else "default",
            subject=subject,
            content=content,
            status=NotificationStatus.PENDING.value,
            priority=priority,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        
        try:
            # Get channel handler
            handler = self.channel_handlers.get(ChannelType(channel.channel_type))
            if not handler:
                raise ValueError(f"No handler for channel type: {channel.channel_type}")
            
            # Send notification
            result = await handler(
                channel=channel,
                subject=subject,
                content=content,
                recipients=recipients,
                metadata=metadata or {}
            )
            
            # Update notification record
            notification.status = NotificationStatus.SENT.value
            notification.sent_at = datetime.utcnow()
            notification.external_id = result.get("external_id")
            notification.response_data = result
            
            self.logger.log_notification_sent(
                notification_id=notification.id,
                incident_id=incident.id,
                channel=channel.channel_type,
                recipient=notification.recipient,
                status="sent"
            )
            
        except Exception as e:
            notification.status = NotificationStatus.FAILED.value
            notification.error_message = str(e)
            
            self.logger.log_notification_sent(
                notification_id=notification.id,
                incident_id=incident.id,
                channel=channel.channel_type,
                recipient=notification.recipient,
                status="failed",
                error=str(e)
            )
        
        return notification
    
    async def _render_template(
        self, 
        template_content: Dict[str, str], 
        incident: AlertIncident, 
        rule: Any
    ) -> Dict[str, str]:
        """Render notification template with incident data."""
        
        # Prepare template variables
        template_vars = {
            "incident": {
                "id": incident.id,
                "title": incident.title,
                "description": incident.description,
                "severity": incident.severity,
                "status": incident.status,
                "triggered_at": incident.triggered_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "trigger_value": incident.trigger_value,
                "trigger_data": incident.trigger_data,
                "assigned_to": incident.assigned_to,
                "acknowledged_by": incident.acknowledged_by,
                "resolved_by": incident.resolved_by,
                "resolved_at": incident.resolved_at.strftime("%Y-%m-%d %H:%M:%S UTC") if incident.resolved_at else None,
                "resolution_time_minutes": incident.resolution_time_minutes,
                "resolution_notes": incident.resolution_notes
            },
            "rule": {
                "id": rule.id if rule else "unknown",
                "name": rule.name if rule else "Unknown Rule",
                "description": rule.description if rule else "",
                "spl_query": rule.spl_query if rule else ""
            },
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
        # Render subject and body
        subject_template = Template(template_content.get("subject", "Alert Notification"))
        body_template = Template(template_content.get("body", "Alert triggered"))
        
        return {
            "subject": subject_template.render(**template_vars),
            "body": body_template.render(**template_vars)
        }
    
    def _get_default_template(self, template_type: str, channel_type: str) -> Dict[str, str]:
        """Get default template for channel type."""
        return self.default_templates.get(template_type, {
            "subject": "Alert Notification",
            "body": "An alert has been triggered."
        })
    
    async def _send_email(
        self,
        channel: NotificationChannel,
        subject: str,
        content: str,
        recipients: Optional[List[str]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send email notification."""
        config = channel.config
        
        # Determine recipients
        if not recipients:
            recipients = config.get("default_recipients", [])
        
        if not recipients:
            raise ValueError("No email recipients specified")
        
        # Create email message
        msg = MimeMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{config.get('from_name', 'Splunk MCP Alerts')} <{config.get('from_email', settings.smtp_from_email)}>"
        msg["To"] = ", ".join(recipients)
        
        # Add plain text content
        text_part = MimeText(content, "plain")
        msg.attach(text_part)
        
        # Send email
        smtp_config = {
            "hostname": config.get("smtp_host", settings.smtp_host),
            "port": config.get("smtp_port", settings.smtp_port),
            "use_tls": config.get("smtp_use_tls", settings.smtp_use_tls),
            "username": config.get("smtp_username", settings.smtp_username),
            "password": config.get("smtp_password", settings.smtp_password)
        }
        
        await aiosmtplib.send(
            msg,
            hostname=smtp_config["hostname"],
            port=smtp_config["port"],
            use_tls=smtp_config["use_tls"],
            username=smtp_config["username"],
            password=smtp_config["password"]
        )
        
        return {
            "external_id": f"email_{datetime.utcnow().timestamp()}",
            "recipients": recipients,
            "smtp_host": smtp_config["hostname"]
        }
    
    async def _send_slack(
        self,
        channel: NotificationChannel,
        subject: str,
        content: str,
        recipients: Optional[List[str]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send Slack notification."""
        config = channel.config
        webhook_url = config.get("webhook_url")
        
        if not webhook_url:
            raise ValueError("Slack webhook URL not configured")
        
        # Create Slack message
        slack_message = {
            "channel": config.get("channel", "#alerts"),
            "username": config.get("username", "Splunk MCP Alerts"),
            "icon_emoji": config.get("icon_emoji", ":warning:"),
            "text": subject,
            "attachments": [
                {
                    "color": self._get_slack_color(metadata.get("severity", "medium")),
                    "text": content,
                    "ts": datetime.utcnow().timestamp()
                }
            ]
        }
        
        # Send to Slack
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=slack_message,
                timeout=30.0
            )
            response.raise_for_status()
        
        return {
            "external_id": f"slack_{datetime.utcnow().timestamp()}",
            "channel": config.get("channel"),
            "webhook_response": response.text
        }
    
    async def _send_teams(
        self,
        channel: NotificationChannel,
        subject: str,
        content: str,
        recipients: Optional[List[str]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send Microsoft Teams notification."""
        config = channel.config
        webhook_url = config.get("webhook_url")
        
        if not webhook_url:
            raise ValueError("Teams webhook URL not configured")
        
        # Create Teams adaptive card
        teams_message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": self._get_teams_color(metadata.get("severity", "medium")),
            "summary": subject,
            "sections": [
                {
                    "activityTitle": subject,
                    "activitySubtitle": "Splunk MCP Alert",
                    "text": content,
                    "facts": [
                        {"name": "Timestamp", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")},
                        {"name": "Severity", "value": metadata.get("severity", "medium").upper()}
                    ]
                }
            ]
        }
        
        # Send to Teams
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=teams_message,
                timeout=30.0
            )
            response.raise_for_status()
        
        return {
            "external_id": f"teams_{datetime.utcnow().timestamp()}",
            "webhook_response": response.text
        }
    
    async def _send_sms(
        self,
        channel: NotificationChannel,
        subject: str,
        content: str,
        recipients: Optional[List[str]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send SMS notification (placeholder implementation)."""
        config = channel.config
        
        # For now, just return a mock response
        # TODO: Implement actual SMS sending with Twilio or AWS SNS
        return {
            "external_id": f"sms_{datetime.utcnow().timestamp()}",
            "provider": config.get("provider", "twilio"),
            "recipients": recipients or config.get("default_recipients", []),
            "message": f"{subject}\n\n{content}"
        }
    
    async def _send_webhook(
        self,
        channel: NotificationChannel,
        subject: str,
        content: str,
        recipients: Optional[List[str]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send webhook notification."""
        config = channel.config
        url = config.get("url")
        
        if not url:
            raise ValueError("Webhook URL not configured")
        
        # Prepare webhook payload
        payload = {
            "subject": subject,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "recipients": recipients,
            "metadata": metadata
        }
        
        # Send webhook
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        headers.setdefault("Content-Type", "application/json")
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=payload,
                headers=headers,
                timeout=config.get("timeout", 30)
            )
            response.raise_for_status()
        
        return {
            "external_id": f"webhook_{datetime.utcnow().timestamp()}",
            "url": url,
            "method": method,
            "status_code": response.status_code,
            "response": response.text
        }
    
    def _get_slack_color(self, severity: str) -> str:
        """Get Slack color based on severity."""
        colors = {
            "critical": "danger",
            "high": "warning", 
            "medium": "warning",
            "low": "good",
            "info": "#36a64f"
        }
        return colors.get(severity.lower(), "warning")
    
    def _get_teams_color(self, severity: str) -> str:
        """Get Teams color based on severity."""
        colors = {
            "critical": "ff0000",
            "high": "ff6600",
            "medium": "ffcc00",
            "low": "36a64f",
            "info": "0078d4"
        }
        return colors.get(severity.lower(), "ffcc00")
    
    async def test_notification_channel(
        self,
        channel: NotificationChannel,
        test_recipient: str,
        test_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Test a notification channel."""
        try:
            # Create test message
            test_subject = "🧪 Test Notification from Splunk MCP"
            test_content = f"""
This is a test notification sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}.

Channel: {channel.name}
Type: {channel.channel_type}

If you received this message, the notification channel is working correctly.
            """.strip()
            
            # Send test notification
            handler = self.channel_handlers.get(ChannelType(channel.channel_type))
            if not handler:
                raise ValueError(f"No handler for channel type: {channel.channel_type}")
            
            result = await handler(
                channel=channel,
                subject=test_subject,
                content=test_content,
                recipients=[test_recipient] if test_recipient else None,
                metadata=test_data or {}
            )
            
            return {
                "success": True,
                "message": "Test notification sent successfully",
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Test notification failed: {str(e)}",
                "error": str(e)
            }