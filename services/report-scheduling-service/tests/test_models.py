#!/usr/bin/env python3
"""
Comprehensive model tests for Report Scheduling Service.

This module tests all Pydantic models including validation, serialization,
and relationship handling.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
import json
from pydantic import ValidationError


class TestScheduleModels:
    """Test schedule data models."""
    
    def test_create_schedule_request_valid(self):
        """Test creating valid schedule request."""
        from app.models.schedule_models import CreateScheduleRequest
        
        valid_data = {
            "name": "Daily Error Report",
            "description": "Daily report of system errors",
            "cron_expression": "0 9 * * *",
            "timezone": "UTC",
            "is_active": True,
            "priority": "medium",
            "report_config": {
                "query": "search error earliest=-24h",
                "format": "pdf",
                "title": "Daily Error Summary"
            },
            "delivery_config": {
                "method": "email",
                "recipients": ["admin@example.com"]
            },
            "retention_days": 30,
            "max_retries": 3
        }
        
        schedule_request = CreateScheduleRequest(**valid_data)
        
        assert schedule_request.name == valid_data["name"]
        assert schedule_request.cron_expression == valid_data["cron_expression"]
        assert schedule_request.is_active == valid_data["is_active"]
        assert schedule_request.priority == valid_data["priority"]
        assert schedule_request.retention_days == valid_data["retention_days"]
    
    def test_create_schedule_request_minimal_fields(self):
        """Test creating schedule request with minimal required fields."""
        from app.models.schedule_models import CreateScheduleRequest
        
        minimal_data = {
            "name": "Minimal Schedule",
            "cron_expression": "0 12 * * *",
            "report_config": {
                "query": "search *",
                "format": "csv"
            },
            "delivery_config": {
                "method": "email",
                "recipients": ["user@example.com"]
            }
        }
        
        schedule_request = CreateScheduleRequest(**minimal_data)
        
        assert schedule_request.name == minimal_data["name"]
        assert schedule_request.is_active is True  # Default value
        assert schedule_request.priority == "medium"  # Default value
        assert schedule_request.timezone == "UTC"  # Default value
    
    def test_create_schedule_request_invalid_cron(self):
        """Test validation of invalid cron expression."""
        from app.models.schedule_models import CreateScheduleRequest
        
        invalid_data = {
            "name": "Invalid Schedule",
            "cron_expression": "invalid cron expression",
            "report_config": {
                "query": "search *",
                "format": "pdf"
            },
            "delivery_config": {
                "method": "email",
                "recipients": ["user@example.com"]
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateScheduleRequest(**invalid_data)
        
        assert "cron_expression" in str(exc_info.value)
    
    def test_create_schedule_request_invalid_email(self):
        """Test validation of invalid email in recipients."""
        from app.models.schedule_models import CreateScheduleRequest
        
        invalid_data = {
            "name": "Invalid Email Schedule",
            "cron_expression": "0 9 * * *",
            "report_config": {
                "query": "search *",
                "format": "pdf"
            },
            "delivery_config": {
                "method": "email",
                "recipients": ["invalid-email"]  # Invalid email format
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateScheduleRequest(**invalid_data)
        
        assert "email" in str(exc_info.value).lower()
    
    def test_update_schedule_request_partial(self):
        """Test updating schedule with partial data."""
        from app.models.schedule_models import UpdateScheduleRequest
        
        update_data = {
            "name": "Updated Schedule Name",
            "is_active": False,
            "description": "Updated description"
        }
        
        update_request = UpdateScheduleRequest(**update_data)
        
        assert update_request.name == update_data["name"]
        assert update_request.is_active == update_data["is_active"]
        assert update_request.description == update_data["description"]
        assert update_request.cron_expression is None  # Not updated
    
    def test_schedule_response_serialization(self):
        """Test schedule response serialization."""
        from app.models.schedule_models import ScheduleResponse
        
        schedule_data = {
            "schedule_id": "schedule-123",
            "name": "Test Schedule",
            "description": "Test description",
            "cron_expression": "0 9 * * *",
            "timezone": "UTC",
            "is_active": True,
            "priority": "high",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "created_by": "user-123",
            "next_run": datetime.now(timezone.utc) + timedelta(hours=24),
            "last_run": datetime.now(timezone.utc) - timedelta(hours=24),
            "execution_count": 45,
            "success_count": 43,
            "failure_count": 2
        }
        
        response = ScheduleResponse(**schedule_data)
        json_data = response.json()
        
        # Verify JSON serialization
        parsed_data = json.loads(json_data)
        assert parsed_data["schedule_id"] == schedule_data["schedule_id"]
        assert parsed_data["name"] == schedule_data["name"]
        assert "created_at" in parsed_data


class TestExecutionModels:
    """Test execution data models."""
    
    def test_execution_response_complete(self):
        """Test complete execution response model."""
        from app.models.execution_models import ExecutionResponse
        
        execution_data = {
            "execution_id": "exec-123",
            "schedule_id": "schedule-456",
            "triggered_at": datetime.now(timezone.utc),
            "started_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "status": "completed",
            "report_size_bytes": 2048576,
            "delivery_status": "delivered",
            "execution_time_seconds": 300,
            "retry_count": 0,
            "error_message": None,
            "metadata": {
                "rows_processed": 15000,
                "charts_generated": 3
            }
        }
        
        response = ExecutionResponse(**execution_data)
        
        assert response.execution_id == execution_data["execution_id"]
        assert response.status == execution_data["status"]
        assert response.execution_time_seconds == execution_data["execution_time_seconds"]
        assert response.metadata == execution_data["metadata"]
    
    def test_execution_response_failed(self):
        """Test failed execution response model."""
        from app.models.execution_models import ExecutionResponse
        
        execution_data = {
            "execution_id": "exec-456",
            "schedule_id": "schedule-789",
            "triggered_at": datetime.now(timezone.utc),
            "started_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            "status": "failed",
            "report_size_bytes": None,
            "delivery_status": "failed",
            "execution_time_seconds": 600,
            "retry_count": 3,
            "error_message": "Query timeout exceeded",
            "metadata": {
                "error_type": "timeout",
                "last_retry_at": datetime.now(timezone.utc)
            }
        }
        
        response = ExecutionResponse(**execution_data)
        
        assert response.status == "failed"
        assert response.error_message == "Query timeout exceeded"
        assert response.retry_count == 3
    
    def test_execution_status_enum(self):
        """Test execution status enumeration."""
        from app.models.execution_models import ExecutionStatus
        
        # Test all valid status values
        valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        
        for status in valid_statuses:
            assert hasattr(ExecutionStatus, status.upper())
            assert getattr(ExecutionStatus, status.upper()) == status
    
    def test_execution_trigger_request(self):
        """Test manual execution trigger request."""
        from app.models.execution_models import TriggerExecutionRequest
        
        trigger_data = {
            "parameters": {
                "override_query": "search error earliest=-1h",
                "custom_title": "Emergency Report"
            },
            "priority": "high",
            "notify_on_completion": True
        }
        
        request = TriggerExecutionRequest(**trigger_data)
        
        assert request.parameters == trigger_data["parameters"]
        assert request.priority == trigger_data["priority"]
        assert request.notify_on_completion is True
    
    def test_execution_metrics(self):
        """Test execution metrics model."""
        from app.models.execution_models import ExecutionMetrics
        
        metrics_data = {
            "total_executions": 150,
            "successful_executions": 145,
            "failed_executions": 5,
            "success_rate": 0.967,
            "average_execution_time_ms": 45000,
            "average_report_size_mb": 2.5,
            "total_data_processed_gb": 125.8,
            "period_start": datetime.now(timezone.utc) - timedelta(days=30),
            "period_end": datetime.now(timezone.utc)
        }
        
        metrics = ExecutionMetrics(**metrics_data)
        
        assert metrics.total_executions == 150
        assert metrics.success_rate == 0.967
        assert metrics.average_execution_time_ms == 45000


class TestVersionModels:
    """Test version management models."""
    
    def test_version_response_model(self):
        """Test version response model."""
        from app.models.version_models import VersionResponse
        
        version_data = {
            "version_id": "v1.2.0",
            "schedule_id": "schedule-123",
            "version_number": "1.2.0",
            "created_at": datetime.now(timezone.utc),
            "created_by": "user-123",
            "action": "update",
            "change_summary": "Added chart support",
            "configuration": {
                "name": "Daily Report",
                "cron_expression": "0 9 * * *",
                "report_config": {
                    "format": "pdf",
                    "include_charts": True
                }
            },
            "is_current": True
        }
        
        response = VersionResponse(**version_data)
        
        assert response.version_id == version_data["version_id"]
        assert response.version_number == version_data["version_number"]
        assert response.action == version_data["action"]
        assert response.is_current is True
    
    def test_version_comparison_model(self):
        """Test version comparison model."""
        from app.models.version_models import VersionComparison
        
        comparison_data = {
            "version1": "v1.1.0",
            "version2": "v1.2.0",
            "differences": [
                {
                    "field": "report_config.include_charts",
                    "old_value": False,
                    "new_value": True,
                    "change_type": "modified"
                },
                {
                    "field": "delivery_config.recipients",
                    "old_value": ["admin@example.com"],
                    "new_value": ["admin@example.com", "team@example.com"],
                    "change_type": "modified"
                }
            ],
            "summary": "Added chart support and additional recipient",
            "has_breaking_changes": False
        }
        
        comparison = VersionComparison(**comparison_data)
        
        assert comparison.version1 == "v1.1.0"
        assert comparison.version2 == "v1.2.0"
        assert len(comparison.differences) == 2
        assert comparison.has_breaking_changes is False
    
    def test_version_restore_request(self):
        """Test version restore request model."""
        from app.models.version_models import RestoreVersionRequest
        
        restore_data = {
            "create_backup": True,
            "force_restore": False,
            "notes": "Restoring due to configuration issue"
        }
        
        request = RestoreVersionRequest(**restore_data)
        
        assert request.create_backup is True
        assert request.force_restore is False
        assert request.notes == restore_data["notes"]


class TestConfigurationModels:
    """Test configuration-related models."""
    
    def test_report_config_model(self):
        """Test report configuration model."""
        from app.models.config_models import ReportConfig
        
        config_data = {
            "query": "search error earliest=-24h | stats count by source",
            "format": "pdf",
            "title": "Daily Error Report",
            "include_charts": True,
            "chart_types": ["bar", "pie"],
            "include_summary": True,
            "template": "professional",
            "page_size": "A4",
            "orientation": "portrait",
            "custom_css": ".header { color: blue; }"
        }
        
        config = ReportConfig(**config_data)
        
        assert config.query == config_data["query"]
        assert config.format == config_data["format"]
        assert config.include_charts is True
        assert config.chart_types == config_data["chart_types"]
        assert config.template == config_data["template"]
    
    def test_delivery_config_email(self):
        """Test email delivery configuration model."""
        from app.models.config_models import EmailDeliveryConfig
        
        email_config_data = {
            "method": "email",
            "recipients": ["admin@example.com", "team@example.com"],
            "cc_recipients": ["manager@example.com"],
            "bcc_recipients": ["archive@example.com"],
            "subject": "Daily Report - {{date}}",
            "body_template": "Please find attached the daily report.",
            "include_attachments": True,
            "smtp_config": {
                "host": "smtp.example.com",
                "port": 587,
                "use_tls": True,
                "username": "reports@example.com"
            }
        }
        
        config = EmailDeliveryConfig(**email_config_data)
        
        assert config.method == "email"
        assert len(config.recipients) == 2
        assert config.subject == email_config_data["subject"]
        assert config.include_attachments is True
    
    def test_delivery_config_webhook(self):
        """Test webhook delivery configuration model."""
        from app.models.config_models import WebhookDeliveryConfig
        
        webhook_config_data = {
            "method": "webhook",
            "webhook_url": "https://api.example.com/reports",
            "headers": {
                "Authorization": "Bearer token123",
                "Content-Type": "application/json"
            },
            "timeout_seconds": 30,
            "retry_attempts": 3,
            "include_metadata": True,
            "verify_ssl": True
        }
        
        config = WebhookDeliveryConfig(**webhook_config_data)
        
        assert config.method == "webhook"
        assert config.webhook_url == webhook_config_data["webhook_url"]
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3
    
    def test_delivery_config_sftp(self):
        """Test SFTP delivery configuration model."""
        from app.models.config_models import SftpDeliveryConfig
        
        sftp_config_data = {
            "method": "sftp",
            "sftp_config": {
                "host": "sftp.example.com",
                "port": 22,
                "username": "reports",
                "path": "/reports/daily/",
                "use_key_auth": True,
                "verify_host_key": True
            },
            "filename_pattern": "report_{{date}}_{{time}}.{{format}}",
            "create_directories": True,
            "overwrite_existing": False
        }
        
        config = SftpDeliveryConfig(**sftp_config_data)
        
        assert config.method == "sftp"
        assert config.sftp_config["host"] == "sftp.example.com"
        assert config.filename_pattern == sftp_config_data["filename_pattern"]
        assert config.create_directories is True


class TestSubscriptionModels:
    """Test subscription-related models."""
    
    def test_subscription_request_model(self):
        """Test subscription request model."""
        from app.models.subscription_models import CreateSubscriptionRequest
        
        subscription_data = {
            "schedule_id": "schedule-123",
            "subscription_type": "email",
            "frequency": "immediate",
            "is_active": True,
            "preferences": {
                "format": "pdf",
                "include_attachments": True,
                "notification_email": "user@example.com"
            }
        }
        
        request = CreateSubscriptionRequest(**subscription_data)
        
        assert request.schedule_id == subscription_data["schedule_id"]
        assert request.subscription_type == subscription_data["subscription_type"]
        assert request.frequency == subscription_data["frequency"]
        assert request.preferences == subscription_data["preferences"]
    
    def test_subscription_response_model(self):
        """Test subscription response model."""
        from app.models.subscription_models import SubscriptionResponse
        
        subscription_data = {
            "subscription_id": "sub-123",
            "schedule_id": "schedule-456",
            "user_id": "user-123",
            "subscription_type": "webhook",
            "frequency": "digest",
            "is_active": True,
            "preferences": {
                "webhook_url": "https://api.user.com/reports",
                "digest_interval": "daily"
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_notification_at": datetime.now(timezone.utc) - timedelta(hours=12)
        }
        
        response = SubscriptionResponse(**subscription_data)
        
        assert response.subscription_id == subscription_data["subscription_id"]
        assert response.subscription_type == subscription_data["subscription_type"]
        assert response.frequency == subscription_data["frequency"]
    
    def test_subscription_update_request(self):
        """Test subscription update request model."""
        from app.models.subscription_models import UpdateSubscriptionRequest
        
        update_data = {
            "is_active": False,
            "frequency": "weekly",
            "preferences": {
                "format": "xlsx",
                "include_attachments": False
            }
        }
        
        request = UpdateSubscriptionRequest(**update_data)
        
        assert request.is_active is False
        assert request.frequency == "weekly"
        assert request.preferences == update_data["preferences"]


class TestAnalyticsModels:
    """Test analytics and metrics models."""
    
    def test_analytics_response_model(self):
        """Test analytics response model."""
        from app.models.analytics_models import AnalyticsResponse
        
        analytics_data = {
            "schedule_id": "schedule-123",
            "period_days": 30,
            "total_executions": 150,
            "successful_executions": 145,
            "failed_executions": 5,
            "success_rate": 0.967,
            "average_execution_time_ms": 45000,
            "average_report_size_mb": 2.5,
            "total_data_processed_gb": 125.8,
            "performance_trend": "stable",
            "top_error_types": [
                {"error_type": "timeout", "count": 3},
                {"error_type": "connection", "count": 2}
            ],
            "usage_by_format": {
                "pdf": 80,
                "csv": 50,
                "xlsx": 20
            }
        }
        
        response = AnalyticsResponse(**analytics_data)
        
        assert response.schedule_id == analytics_data["schedule_id"]
        assert response.success_rate == analytics_data["success_rate"]
        assert response.performance_trend == analytics_data["performance_trend"]
        assert len(response.top_error_types) == 2
    
    def test_system_analytics_model(self):
        """Test system analytics model."""
        from app.models.analytics_models import SystemAnalyticsResponse
        
        system_data = {
            "total_schedules": 25,
            "active_schedules": 20,
            "paused_schedules": 5,
            "total_executions_today": 35,
            "successful_executions_today": 33,
            "failed_executions_today": 2,
            "success_rate_today": 0.943,
            "queue_length": 8,
            "average_processing_time_ms": 42000,
            "system_load": 0.65,
            "storage_used_gb": 245.8,
            "storage_available_gb": 754.2
        }
        
        response = SystemAnalyticsResponse(**system_data)
        
        assert response.total_schedules == 25
        assert response.active_schedules == 20
        assert response.success_rate_today == 0.943
        assert response.queue_length == 8
    
    def test_user_analytics_model(self):
        """Test user analytics model."""
        from app.models.analytics_models import UserAnalyticsResponse
        
        user_data = {
            "user_id": "user-123",
            "schedules_created": 8,
            "active_schedules": 6,
            "reports_generated": 120,
            "successful_reports": 116,
            "failed_reports": 4,
            "data_consumed_mb": 350.5,
            "favorite_formats": ["pdf", "xlsx"],
            "most_used_delivery_method": "email",
            "average_report_size_mb": 2.9,
            "total_execution_time_hours": 15.2
        }
        
        response = UserAnalyticsResponse(**user_data)
        
        assert response.user_id == user_data["user_id"]
        assert response.schedules_created == 8
        assert response.reports_generated == 120
        assert response.favorite_formats == ["pdf", "xlsx"]


class TestValidationAndSerialization:
    """Test model validation and serialization features."""
    
    def test_model_validation_errors(self):
        """Test various model validation error scenarios."""
        from app.models.schedule_models import CreateScheduleRequest
        
        # Test missing required fields
        with pytest.raises(ValidationError) as exc_info:
            CreateScheduleRequest(name="Test")
        
        errors = exc_info.value.errors()
        error_fields = [error["loc"][0] for error in errors]
        assert "cron_expression" in error_fields
        assert "report_config" in error_fields
        assert "delivery_config" in error_fields
    
    def test_model_serialization_with_dates(self):
        """Test model serialization with datetime fields."""
        from app.models.execution_models import ExecutionResponse
        
        execution_data = {
            "execution_id": "exec-123",
            "schedule_id": "schedule-456",
            "triggered_at": datetime.now(timezone.utc),
            "started_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "status": "completed"
        }
        
        response = ExecutionResponse(**execution_data)
        json_data = response.json()
        
        # Verify JSON contains ISO formatted dates
        parsed_data = json.loads(json_data)
        assert "T" in parsed_data["triggered_at"]  # ISO format indicator
        assert "Z" in parsed_data["triggered_at"] or "+" in parsed_data["triggered_at"]
    
    def test_model_with_optional_fields(self):
        """Test models with optional fields and default values."""
        from app.models.schedule_models import CreateScheduleRequest
        
        minimal_data = {
            "name": "Test Schedule",
            "cron_expression": "0 9 * * *",
            "report_config": {
                "query": "search *",
                "format": "pdf"
            },
            "delivery_config": {
                "method": "email",
                "recipients": ["test@example.com"]
            }
        }
        
        request = CreateScheduleRequest(**minimal_data)
        
        # Check default values are applied
        assert request.is_active is True
        assert request.priority == "medium"
        assert request.timezone == "UTC"
        assert request.retention_days == 30
        assert request.max_retries == 3
    
    def test_model_custom_validators(self):
        """Test custom validation logic in models."""
        from app.models.config_models import ReportConfig
        
        # Test valid chart types
        valid_config = {
            "query": "search *",
            "format": "pdf",
            "chart_types": ["bar", "line", "pie"]
        }
        
        config = ReportConfig(**valid_config)
        assert "bar" in config.chart_types
        
        # Test invalid chart types
        invalid_config = {
            "query": "search *",
            "format": "pdf",
            "chart_types": ["invalid_chart_type"]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ReportConfig(**invalid_config)
        
        assert "chart_types" in str(exc_info.value)
    
    def test_model_nested_validation(self):
        """Test validation of nested model structures."""
        from app.models.schedule_models import CreateScheduleRequest
        
        # Test with invalid nested delivery config
        invalid_nested_data = {
            "name": "Test Schedule",
            "cron_expression": "0 9 * * *",
            "report_config": {
                "query": "search *",
                "format": "pdf"
            },
            "delivery_config": {
                "method": "email",
                "recipients": []  # Empty recipients should be invalid
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateScheduleRequest(**invalid_nested_data)
        
        errors = exc_info.value.errors()
        # Check that validation error is from nested field
        assert any("delivery_config" in str(error["loc"]) for error in errors)
    
    def test_model_field_aliases(self):
        """Test model field aliases if any are defined."""
        from app.models.execution_models import ExecutionResponse
        
        # Test that models handle both original and alias field names
        execution_data = {
            "execution_id": "exec-123",
            "schedule_id": "schedule-456",
            "triggered_at": datetime.now(timezone.utc),
            "status": "completed"
        }
        
        response = ExecutionResponse(**execution_data)
        assert response.execution_id == "exec-123"
    
    def test_model_exclude_and_include(self):
        """Test model serialization with exclude and include options."""
        from app.models.schedule_models import ScheduleResponse
        
        schedule_data = {
            "schedule_id": "schedule-123",
            "name": "Test Schedule",
            "description": "Test description",
            "cron_expression": "0 9 * * *",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "created_by": "user-123"
        }
        
        response = ScheduleResponse(**schedule_data)
        
        # Test excluding sensitive fields
        public_data = response.dict(exclude={"created_by"})
        assert "created_by" not in public_data
        assert "schedule_id" in public_data
        
        # Test including only specific fields
        minimal_data = response.dict(include={"schedule_id", "name", "is_active"})
        assert len(minimal_data) == 3
        assert minimal_data["name"] == "Test Schedule"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
