#!/usr/bin/env python3
"""
Notification Service
===================
Service for managing notifications and alerts for the user adoption system
"""

import uuid
import logging
import smtplib
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications and alerts"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        
        self.slack_webhook_url = settings.SLACK_WEBHOOK_URL
        self.teams_webhook_url = settings.TEAMS_WEBHOOK_URL
    
    async def send_feedback_notification(self, feedback_id: uuid.UUID, user_name: str):
        """Send notification when new feedback is submitted"""
        try:
            # Email notification to admin team
            await self._send_email_notification(
                subject=f"New Feedback Submitted - ID: {feedback_id}",
                message=f"New feedback has been submitted by {user_name}.\n\nFeedback ID: {feedback_id}\nSubmitted by: {user_name}\nTime: {datetime.utcnow()}\n\nPlease review the feedback in the admin dashboard.",
                recipients=settings.ADMIN_EMAIL_ADDRESSES or []
            )
            
            # Slack notification
            if self.slack_webhook_url:
                await self._send_slack_notification(
                    message=f"🗯️ *New Feedback Submitted*\n\n*User:* {user_name}\n*Feedback ID:* {feedback_id}\n*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\nPlease review in the admin dashboard.",
                    channel="#feedback"
                )
            
            logger.info(f"Feedback notification sent for feedback {feedback_id}")
            
        except Exception as e:
            logger.error(f"Failed to send feedback notification: {e}")
    
    async def send_onboarding_completion_notification(self, user_profile_id: uuid.UUID, user_name: str):
        """Send notification when user completes onboarding"""
        try:
            # Email notification to admin team
            await self._send_email_notification(
                subject=f"User Onboarding Completed - {user_name}",
                message=f"User {user_name} has successfully completed the onboarding process.\n\nUser Profile ID: {user_profile_id}\nCompleted at: {datetime.utcnow()}\n\nYou can view their progress in the adoption analytics dashboard.",
                recipients=settings.ADMIN_EMAIL_ADDRESSES or []
            )
            
            # Slack notification
            if self.slack_webhook_url:
                await self._send_slack_notification(
                    message=f"🎉 *Onboarding Completed!*\n\n*User:* {user_name}\n*Completed:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\nGreat progress on user adoption!",
                    channel="#onboarding"
                )
            
            logger.info(f"Onboarding completion notification sent for user {user_name}")
            
        except Exception as e:
            logger.error(f"Failed to send onboarding notification: {e}")
    
    async def send_low_engagement_alert(self, user_count: int, threshold: float):
        """Send alert for low engagement users"""
        try:
            # Email notification to admin team
            await self._send_email_notification(
                subject=f"Low Engagement Alert - {user_count} Users Below Threshold",
                message=f"Alert: {user_count} users have engagement scores below {threshold}.\n\nThis may indicate onboarding issues or lack of adoption.\n\nPlease review the low engagement users in the adoption analytics dashboard and consider intervention strategies.",
                recipients=settings.ADMIN_EMAIL_ADDRESSES or []
            )
            
            # Slack notification with urgency
            if self.slack_webhook_url:
                await self._send_slack_notification(
                    message=f"⚠️ *Low Engagement Alert*\n\n*Users affected:* {user_count}\n*Threshold:* {threshold}\n*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\nReview needed for user adoption strategy.",
                    channel="#alerts"
                )
            
            logger.warning(f"Low engagement alert sent: {user_count} users below threshold {threshold}")
            
        except Exception as e:
            logger.error(f"Failed to send low engagement alert: {e}")
    
    async def send_survey_invitation(self, user_email: str, user_name: str, survey_name: str, survey_url: str):
        """Send survey invitation to user"""
        try:
            # Email invitation
            await self._send_email_notification(
                subject=f"Your Feedback is Important - {survey_name}",
                message=f"Hi {user_name},\n\nWe'd love to hear your feedback! Please take a few minutes to complete our survey: {survey_name}\n\nSurvey Link: {survey_url}\n\nYour feedback helps us improve the platform for everyone.\n\nThank you!",
                recipients=[user_email]
            )
            
            logger.info(f"Survey invitation sent to {user_email} for survey {survey_name}")
            
        except Exception as e:
            logger.error(f"Failed to send survey invitation: {e}")
    
    async def send_adoption_milestone_notification(self, user_name: str, milestone: str, score: float):
        """Send notification when user reaches adoption milestone"""
        try:
            # Slack celebration
            if self.slack_webhook_url:
                await self._send_slack_notification(
                    message=f"🏆 *Adoption Milestone Reached!*\n\n*User:* {user_name}\n*Milestone:* {milestone}\n*Score:* {score:.2f}\n*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\nCelebrating user success! 🎉",
                    channel="#achievements"
                )
            
            logger.info(f"Adoption milestone notification sent for {user_name}: {milestone}")
            
        except Exception as e:
            logger.error(f"Failed to send adoption milestone notification: {e}")
    
    async def send_system_health_alert(self, alert_type: str, message: str, severity: str = "warning"):
        """Send system health alert"""
        try:
            # Determine emoji based on severity
            emoji_map = {
                "critical": "🚨",
                "warning": "⚠️",
                "info": "ℹ️",
                "success": "✅"
            }
            
            emoji = emoji_map.get(severity, "ℹ️")
            
            # Email notification for critical alerts
            if severity == "critical":
                await self._send_email_notification(
                    subject=f"CRITICAL ALERT - {alert_type}",
                    message=f"Critical system alert:\n\nAlert Type: {alert_type}\nMessage: {message}\nTime: {datetime.utcnow()}\n\nImmediate attention required!",
                    recipients=settings.ADMIN_EMAIL_ADDRESSES or []
                )
            
            # Slack notification
            if self.slack_webhook_url:
                await self._send_slack_notification(
                    message=f"{emoji} *System Alert: {alert_type}*\n\n*Severity:* {severity.upper()}\n*Message:* {message}\n*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
                    channel="#system-alerts"
                )
            
            logger.warning(f"System health alert sent: {alert_type} - {severity}")
            
        except Exception as e:
            logger.error(f"Failed to send system health alert: {e}")
    
    async def _send_email_notification(self, subject: str, message: str, recipients: List[str]):
        """Send email notification"""
        if not recipients or not self.smtp_host:
            return
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_FROM_EMAIL or self.smtp_username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent to {len(recipients)} recipients: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    async def _send_slack_notification(self, message: str, channel: str = "#general"):
        """Send Slack notification"""
        if not self.slack_webhook_url:
            return
        
        try:
            payload = {
                "channel": channel,
                "text": message,
                "username": "Adoption Bot",
                "icon_emoji": ":chart_with_upwards_trend:"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.slack_webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent to {channel}")
                    else:
                        logger.error(f"Failed to send Slack notification: {response.status}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    async def _send_teams_notification(self, title: str, message: str, color: str = "0078D4"):
        """Send Microsoft Teams notification"""
        if not self.teams_webhook_url:
            return
        
        try:
            payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": title,
                "themeColor": color,
                "sections": [{
                    "activityTitle": title,
                    "activitySubtitle": f"User Adoption Service - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
                    "text": message,
                    "markdown": True
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.teams_webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Teams notification sent")
                    else:
                        logger.error(f"Failed to send Teams notification: {response.status}")
            
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
    
    async def send_batch_notification(self, notifications: List[Dict[str, Any]]):
        """Send multiple notifications in batch"""
        for notification in notifications:
            try:
                notification_type = notification.get("type")
                
                if notification_type == "feedback":
                    await self.send_feedback_notification(
                        notification["feedback_id"],
                        notification["user_name"]
                    )
                elif notification_type == "onboarding_completion":
                    await self.send_onboarding_completion_notification(
                        notification["user_profile_id"],
                        notification["user_name"]
                    )
                elif notification_type == "low_engagement":
                    await self.send_low_engagement_alert(
                        notification["user_count"],
                        notification["threshold"]
                    )
                elif notification_type == "survey_invitation":
                    await self.send_survey_invitation(
                        notification["user_email"],
                        notification["user_name"],
                        notification["survey_name"],
                        notification["survey_url"]
                    )
                elif notification_type == "adoption_milestone":
                    await self.send_adoption_milestone_notification(
                        notification["user_name"],
                        notification["milestone"],
                        notification["score"]
                    )
                elif notification_type == "system_alert":
                    await self.send_system_health_alert(
                        notification["alert_type"],
                        notification["message"],
                        notification.get("severity", "warning")
                    )
                
            except Exception as e:
                logger.error(f"Failed to send batch notification: {e}")
    
    def format_adoption_score_message(self, score: float) -> str:
        """Format adoption score for notifications"""
        if score >= 0.8:
            return f"Excellent adoption score: {score:.2f} 🏆"
        elif score >= 0.6:
            return f"Good adoption score: {score:.2f} 📈"
        elif score >= 0.4:
            return f"Moderate adoption score: {score:.2f} 📊"
        elif score >= 0.2:
            return f"Low adoption score: {score:.2f} 📉"
        else:
            return f"Very low adoption score: {score:.2f} ⚠️"