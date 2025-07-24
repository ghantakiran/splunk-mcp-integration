#!/usr/bin/env python3
"""
Comprehensive service tests for Report Scheduling Service.

This module tests core services including scheduler, report generation,
delivery, analytics, and background processing.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List
import json
import tempfile
import os
from datetime import datetime, timedelta, timezone


class TestSchedulerService:
    """Test scheduler service functionality."""
    
    @pytest.mark.asyncio
    async def test_schedule_job_success(
        self,
        mock_scheduler,
        mock_database,
        mock_redis,
        sample_schedule_data
    ):
        """Test successful job scheduling."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        schedule_data = sample_schedule_data[0]
        
        result = await service.schedule_job(
            schedule_id="schedule-123",
            cron_expression=schedule_data["cron_expression"],
            timezone=schedule_data["timezone"]
        )
        
        assert result is not None
        assert "job_id" in result
        assert "scheduled_at" in result
        assert "next_run" in result
        mock_scheduler.schedule_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_job_success(
        self,
        mock_scheduler,
        mock_database
    ):
        """Test successful job cancellation."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        job_id = "job-123"
        
        result = await service.cancel_job(job_id)
        
        assert result is True
        mock_scheduler.cancel_job.assert_called_once_with(job_id)
    
    @pytest.mark.asyncio
    async def test_get_job_status(
        self,
        mock_scheduler
    ):
        """Test getting job status."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        job_id = "job-123"
        
        result = await service.get_job_status(job_id)
        
        assert result is not None
        assert "job_id" in result
        assert "status" in result
        mock_scheduler.get_job_status.assert_called_once_with(job_id)
    
    @pytest.mark.asyncio
    async def test_list_active_jobs(
        self,
        mock_scheduler
    ):
        """Test listing active jobs."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        
        result = await service.list_active_jobs()
        
        assert result is not None
        assert isinstance(result, list)
        mock_scheduler.list_active_jobs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pause_resume_job(
        self,
        mock_scheduler
    ):
        """Test pausing and resuming jobs."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        job_id = "job-123"
        
        # Test pause
        pause_result = await service.pause_job(job_id)
        assert pause_result is True
        mock_scheduler.pause_job.assert_called_once_with(job_id)
        
        # Test resume
        resume_result = await service.resume_job(job_id)
        assert resume_result is True
        mock_scheduler.resume_job.assert_called_once_with(job_id)
    
    def test_validate_cron_expression_valid(self):
        """Test validation of valid cron expressions."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        
        valid_expressions = [
            "0 9 * * *",      # Daily at 9 AM
            "0 0 * * 0",      # Weekly on Sunday
            "0 0 1 * *",      # Monthly on 1st
            "0 */6 * * *",    # Every 6 hours
            "30 8 * * 1-5"    # Weekdays at 8:30 AM
        ]
        
        for expr in valid_expressions:
            result = service.validate_cron_expression(expr)
            assert result["is_valid"] is True
            assert "next_run" in result
    
    def test_validate_cron_expression_invalid(self):
        """Test validation of invalid cron expressions."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        
        invalid_expressions = [
            "invalid cron",
            "60 25 32 13 8",  # Invalid values
            "* * * *",        # Too few fields
            "0 0 0 0 0 0",    # Too many fields
            "",               # Empty string
        ]
        
        for expr in invalid_expressions:
            result = service.validate_cron_expression(expr)
            assert result["is_valid"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_trigger_manual_execution(
        self,
        mock_scheduler,
        mock_report_generator,
        mock_database
    ):
        """Test triggering manual schedule execution."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        schedule_id = "schedule-123"
        
        result = await service.trigger_manual_execution(
            schedule_id=schedule_id,
            user_id="user-123",
            parameters={"priority": "high"}
        )
        
        assert result is not None
        assert "execution_id" in result
        assert result["status"] == "triggered"


class TestReportGenerationService:
    """Test report generation service."""
    
    @pytest.mark.asyncio
    async def test_generate_report_success(
        self,
        mock_report_generator,
        sample_schedule_data,
        mock_file_operations
    ):
        """Test successful report generation."""
        from app.services.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        schedule_data = sample_schedule_data[0]
        
        result = await generator.generate_report(
            schedule_id="schedule-123",
            report_config=schedule_data["report_config"],
            execution_id="exec-456"
        )
        
        assert result is not None
        assert "report_id" in result
        assert "file_path" in result
        assert "file_size" in result
        assert result["format"] == schedule_data["report_config"]["format"]
        mock_report_generator.generate_report.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_report_with_charts(
        self,
        mock_report_generator,
        sample_schedule_data,
        mock_file_operations
    ):
        """Test report generation with charts."""
        from app.services.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        schedule_data = sample_schedule_data[1]  # Weekly performance with charts
        
        result = await generator.generate_report(
            schedule_id="schedule-456",
            report_config=schedule_data["report_config"],
            execution_id="exec-789"
        )
        
        assert result is not None
        assert result["metadata"]["charts_generated"] >= 1
        assert "chart_types" in result["metadata"]
    
    def test_validate_query_success(self, mock_report_generator):
        """Test successful query validation."""
        from app.services.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        query = "search error earliest=-24h | stats count by source"
        
        result = generator.validate_query(query)
        
        assert result is not None
        assert result["is_valid"] is True
        assert "estimated_rows" in result
        assert "estimated_time_ms" in result
        mock_report_generator.validate_query.assert_called_once()
    
    def test_validate_query_invalid(self, mock_report_generator):
        """Test invalid query validation."""
        from app.services.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        
        # Mock invalid query response
        mock_report_generator.validate_query.return_value = {
            "is_valid": False,
            "error": "Invalid SPL syntax",
            "line": 1,
            "column": 15
        }
        
        query = "search error | invalid_command"
        result = generator.validate_query(query)
        
        assert result["is_valid"] is False
        assert "error" in result
    
    def test_get_supported_formats(self, mock_report_generator):
        """Test getting supported report formats."""
        from app.services.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        formats = generator.get_supported_formats()
        
        expected_formats = ["pdf", "csv", "xlsx", "json"]
        for fmt in expected_formats:
            assert fmt in formats
        
        mock_report_generator.get_supported_formats.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_report_different_formats(
        self,
        mock_report_generator,
        sample_schedule_data,
        mock_file_operations
    ):
        """Test report generation in different formats."""
        from app.services.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        schedule_data = sample_schedule_data[0]
        formats = ["pdf", "csv", "xlsx", "json"]
        
        for fmt in formats:
            config = schedule_data["report_config"].copy()
            config["format"] = fmt
            
            result = await generator.generate_report(
                schedule_id="schedule-123",
                report_config=config,
                execution_id=f"exec-{fmt}"
            )
            
            assert result["format"] == fmt
            assert result["file_path"].endswith(f".{fmt}")
    
    @pytest.mark.asyncio
    async def test_report_generation_error_handling(
        self,
        mock_report_generator
    ):
        """Test error handling in report generation."""
        from app.services.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        
        # Mock generation failure
        mock_report_generator.generate_report.side_effect = Exception("Query timeout")
        
        with pytest.raises(Exception) as exc_info:
            await generator.generate_report(
                schedule_id="schedule-123",
                report_config={"query": "slow query", "format": "pdf"},
                execution_id="exec-error"
            )
        
        assert "Query timeout" in str(exc_info.value)


class TestDeliveryService:
    """Test delivery service functionality."""
    
    @pytest.mark.asyncio
    async def test_deliver_report_email(
        self,
        mock_delivery_service,
        sample_schedule_data,
        mock_file_operations
    ):
        """Test email delivery of reports."""
        from app.services.delivery_service import DeliveryService
        
        service = DeliveryService()
        schedule_data = sample_schedule_data[0]  # Email delivery
        file_path = "test_report.pdf"
        
        # Create mock report file
        mock_file_operations["create_report_file"](file_path, b"PDF content", "pdf")
        
        result = await service.deliver_report(
            report_path=file_path,
            delivery_config=schedule_data["delivery_config"],
            execution_id="exec-123"
        )
        
        assert result is not None
        assert "delivery_id" in result
        assert result["status"] == "delivered"
        assert result["delivery_time_ms"] > 0
        mock_delivery_service.deliver_report.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deliver_report_webhook(
        self,
        mock_delivery_service,
        sample_schedule_data,
        mock_file_operations
    ):
        """Test webhook delivery of reports."""
        from app.services.delivery_service import DeliveryService
        
        service = DeliveryService()
        schedule_data = sample_schedule_data[1]  # Webhook delivery
        file_path = "test_report.xlsx"
        
        # Create mock report file
        mock_file_operations["create_report_file"](file_path, b"Excel content", "xlsx")
        
        result = await service.deliver_report(
            report_path=file_path,
            delivery_config=schedule_data["delivery_config"],
            execution_id="exec-456"
        )
        
        assert result is not None
        assert result["status"] == "delivered"
        assert result["metadata"]["delivery_method"] == "webhook"
    
    @pytest.mark.asyncio
    async def test_deliver_report_sftp(
        self,
        mock_delivery_service,
        sample_schedule_data,
        mock_file_operations
    ):
        """Test SFTP delivery of reports."""
        from app.services.delivery_service import DeliveryService
        
        service = DeliveryService()
        schedule_data = sample_schedule_data[2]  # SFTP delivery
        file_path = "test_report.csv"
        
        # Create mock report file
        mock_file_operations["create_report_file"](file_path, b"CSV content", "csv")
        
        result = await service.deliver_report(
            report_path=file_path,
            delivery_config=schedule_data["delivery_config"],
            execution_id="exec-789"
        )
        
        assert result is not None
        assert result["status"] == "delivered"
    
    def test_validate_delivery_config_email(self, mock_delivery_service):
        """Test email delivery configuration validation."""
        from app.services.delivery_service import DeliveryService
        
        service = DeliveryService()
        
        valid_config = {
            "method": "email",
            "recipients": ["admin@example.com", "team@example.com"],
            "subject": "Daily Report"
        }
        
        result = service.validate_delivery_config(valid_config)
        
        assert result["is_valid"] is True
        assert "email" in result["supported_methods"]
        mock_delivery_service.validate_delivery_config.assert_called_once()
    
    def test_validate_delivery_config_invalid(self, mock_delivery_service):
        """Test invalid delivery configuration validation."""
        from app.services.delivery_service import DeliveryService
        
        service = DeliveryService()
        
        # Mock invalid config response
        mock_delivery_service.validate_delivery_config.return_value = {
            "is_valid": False,
            "errors": ["Invalid email address format"],
            "supported_methods": ["email", "webhook", "sftp"]
        }
        
        invalid_config = {
            "method": "email",
            "recipients": ["invalid-email"]  # Invalid email
        }
        
        result = service.validate_delivery_config(invalid_config)
        
        assert result["is_valid"] is False
        assert "errors" in result
    
    @pytest.mark.asyncio
    async def test_test_delivery_connection(
        self,
        mock_delivery_service
    ):
        """Test delivery connection testing."""
        from app.services.delivery_service import DeliveryService
        
        service = DeliveryService()
        
        config = {
            "method": "webhook",
            "webhook_url": "https://api.example.com/reports"
        }
        
        result = await service.test_delivery_connection(config)
        
        assert result is not None
        assert result["connection_ok"] is True
        assert "response_time_ms" in result
        mock_delivery_service.test_delivery_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delivery_retry_logic(
        self,
        mock_delivery_service,
        mock_file_operations
    ):
        """Test delivery retry logic on failure."""
        from app.services.delivery_service import DeliveryService
        
        service = DeliveryService()
        file_path = "test_report.pdf"
        
        # Create mock report file
        mock_file_operations["create_report_file"](file_path, b"PDF content", "pdf")
        
        # Mock delivery to fail first, then succeed
        delivery_responses = [
            Exception("Temporary failure"),
            {
                "delivery_id": "delivery-456",
                "status": "delivered",
                "delivered_at": datetime.now(timezone.utc),
                "attempts": 2
            }
        ]
        mock_delivery_service.deliver_report.side_effect = delivery_responses
        
        config = {
            "method": "email",
            "recipients": ["admin@example.com"],
            "retry_attempts": 3
        }
        
        result = await service.deliver_report(
            report_path=file_path,
            delivery_config=config,
            execution_id="exec-retry"
        )
        
        assert result["status"] == "delivered"
        assert result["attempts"] == 2


class TestAnalyticsService:
    """Test analytics service functionality."""
    
    @pytest.mark.asyncio
    async def test_get_schedule_analytics(
        self,
        mock_analytics_service
    ):
        """Test getting schedule analytics."""
        from app.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        schedule_id = "schedule-123"
        
        result = await service.get_schedule_analytics(
            schedule_id=schedule_id,
            period_days=30
        )
        
        assert result is not None
        assert result["schedule_id"] == schedule_id
        assert "total_executions" in result
        assert "success_rate" in result
        assert "average_execution_time_ms" in result
        mock_analytics_service.get_schedule_analytics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_system_analytics(
        self,
        mock_analytics_service
    ):
        """Test getting system analytics."""
        from app.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        
        result = await service.get_system_analytics()
        
        assert result is not None
        assert "total_schedules" in result
        assert "active_schedules" in result
        assert "queue_length" in result
        assert "success_rate_today" in result
        mock_analytics_service.get_system_analytics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_analytics(
        self,
        mock_analytics_service
    ):
        """Test getting user analytics."""
        from app.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        user_id = "user-123"
        
        result = await service.get_user_analytics(user_id=user_id)
        
        assert result is not None
        assert result["user_id"] == user_id
        assert "schedules_created" in result
        assert "reports_generated" in result
        assert "favorite_formats" in result
        mock_analytics_service.get_user_analytics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_performance_report(
        self,
        mock_analytics_service,
        mock_database
    ):
        """Test generating performance analytics report."""
        from app.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        
        with patch.object(service, '_calculate_performance_metrics') as mock_calc:
            mock_calc.return_value = {
                "avg_response_time": 2500,
                "throughput_per_hour": 45,
                "error_rate": 0.02,
                "resource_utilization": 0.65
            }
            
            result = await service.generate_performance_report(
                period_days=7,
                granularity="hour"
            )
        
        assert result is not None
        assert "avg_response_time" in result
        assert "throughput_per_hour" in result
        assert "time_series_data" in result
    
    @pytest.mark.asyncio
    async def test_track_execution_metrics(
        self,
        mock_database,
        mock_redis
    ):
        """Test tracking execution metrics."""
        from app.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        
        execution_data = {
            "execution_id": "exec-123",
            "schedule_id": "schedule-456",
            "execution_time_ms": 45000,
            "report_size_bytes": 2048576,
            "status": "completed",
            "format": "pdf"
        }
        
        result = await service.track_execution_metrics(execution_data)
        
        assert result is not None
        assert result["tracked"] is True
    
    def test_calculate_success_rate(self):
        """Test success rate calculation."""
        from app.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        
        # Test normal case
        rate = service.calculate_success_rate(
            successful_count=95,
            total_count=100
        )
        assert rate == 0.95
        
        # Test edge case - zero total
        rate = service.calculate_success_rate(
            successful_count=0,
            total_count=0
        )
        assert rate == 0.0
        
        # Test perfect success rate
        rate = service.calculate_success_rate(
            successful_count=50,
            total_count=50
        )
        assert rate == 1.0
    
    def test_analyze_performance_trends(self):
        """Test performance trend analysis."""
        from app.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        
        # Mock time series data
        time_series_data = [
            {"timestamp": datetime.now(timezone.utc) - timedelta(days=6), "avg_time": 3000},
            {"timestamp": datetime.now(timezone.utc) - timedelta(days=5), "avg_time": 3200},
            {"timestamp": datetime.now(timezone.utc) - timedelta(days=4), "avg_time": 3100},
            {"timestamp": datetime.now(timezone.utc) - timedelta(days=3), "avg_time": 2900},
            {"timestamp": datetime.now(timezone.utc) - timedelta(days=2), "avg_time": 2800},
            {"timestamp": datetime.now(timezone.utc) - timedelta(days=1), "avg_time": 2700},
            {"timestamp": datetime.now(timezone.utc), "avg_time": 2650}
        ]
        
        trend = service.analyze_performance_trends(time_series_data, "avg_time")
        
        assert trend in ["improving", "stable", "degrading"]
        # Based on the decreasing trend, should be "improving"
        assert trend == "improving"


class TestVersionService:
    """Test version management service."""
    
    @pytest.mark.asyncio
    async def test_create_version(
        self,
        sample_schedule_data,
        mock_database
    ):
        """Test creating new version."""
        from app.services.version_service import VersionService
        
        service = VersionService()
        schedule_data = sample_schedule_data[0]
        
        result = await service.create_version(
            schedule_id="schedule-123",
            configuration=schedule_data,
            action="create",
            change_summary="Initial version created",
            user_id="user-123"
        )
        
        assert result is not None
        assert "version_id" in result
        assert result["action"] == "create"
        assert result["change_summary"] == "Initial version created"
        assert result["is_current"] is True
    
    @pytest.mark.asyncio
    async def test_list_versions(
        self,
        sample_version_data,
        mock_database
    ):
        """Test listing schedule versions."""
        from app.services.version_service import VersionService
        
        service = VersionService()
        schedule_id = "schedule-123"
        
        with patch.object(service, '_fetch_versions_from_db') as mock_fetch:
            mock_fetch.return_value = sample_version_data
            
            result = await service.list_versions(
                schedule_id=schedule_id,
                page=1,
                per_page=10
            )
        
        assert result is not None
        assert "versions" in result
        assert "total" in result
        assert len(result["versions"]) == len(sample_version_data)
    
    @pytest.mark.asyncio
    async def test_get_version_by_id(
        self,
        sample_version_data,
        mock_database
    ):
        """Test getting specific version."""
        from app.services.version_service import VersionService
        
        service = VersionService()
        version_id = "v1.2.0"
        version_data = sample_version_data[2]  # Current version
        
        with patch.object(service, '_fetch_version_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "version_id": version_id,
                **version_data
            }
            
            result = await service.get_version_by_id(version_id)
        
        assert result is not None
        assert result["version_id"] == version_id
        assert result["is_current"] == version_data["is_current"]
    
    @pytest.mark.asyncio
    async def test_restore_version(
        self,
        sample_version_data,
        mock_database,
        mock_scheduler
    ):
        """Test restoring to previous version."""
        from app.services.version_service import VersionService
        
        service = VersionService()
        schedule_id = "schedule-123"
        version_id = "v1.1.0"
        
        with patch.object(service, '_fetch_version_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "version_id": version_id,
                **sample_version_data[1]
            }
            
            result = await service.restore_version(
                schedule_id=schedule_id,
                version_id=version_id,
                user_id="user-123"
            )
        
        assert result is not None
        assert result["schedule_id"] == schedule_id
        assert result["version_id"] == version_id
        assert "restored_at" in result
    
    @pytest.mark.asyncio
    async def test_compare_versions(
        self,
        sample_version_data,
        mock_database
    ):
        """Test comparing two versions."""
        from app.services.version_service import VersionService
        
        service = VersionService()
        version1_id = "v1.1.0"
        version2_id = "v1.2.0"
        
        with patch.object(service, '_fetch_version_from_db') as mock_fetch:
            def fetch_version(version_id):
                if version_id == version1_id:
                    return {"version_id": version1_id, **sample_version_data[1]}
                else:
                    return {"version_id": version2_id, **sample_version_data[2]}
            
            mock_fetch.side_effect = fetch_version
            
            result = await service.compare_versions(version1_id, version2_id)
        
        assert result is not None
        assert result["version1"] == version1_id
        assert result["version2"] == version2_id
        assert "differences" in result
        assert "summary" in result
    
    def test_detect_configuration_changes(self):
        """Test detecting changes between configurations."""
        from app.services.version_service import VersionService
        
        service = VersionService()
        
        old_config = {
            "name": "Daily Report",
            "cron_expression": "0 9 * * *",
            "report_config": {
                "format": "pdf",
                "include_charts": False
            },
            "delivery_config": {
                "recipients": ["admin@example.com"]
            }
        }
        
        new_config = {
            "name": "Daily Report",
            "cron_expression": "0 9 * * *",
            "report_config": {
                "format": "pdf",
                "include_charts": True  # Changed
            },
            "delivery_config": {
                "recipients": ["admin@example.com", "team@example.com"]  # Added recipient
            }
        }
        
        differences = service.detect_configuration_changes(old_config, new_config)
        
        assert len(differences) >= 2  # At least 2 changes detected
        
        # Check for specific changes
        change_fields = [diff["field"] for diff in differences]
        assert "report_config.include_charts" in change_fields
        assert "delivery_config.recipients" in change_fields


class TestSubscriptionService:
    """Test subscription management service."""
    
    @pytest.mark.asyncio
    async def test_create_subscription(
        self,
        sample_subscription_data,
        mock_database
    ):
        """Test creating subscription."""
        from app.services.subscription_service import SubscriptionService
        
        service = SubscriptionService()
        subscription_data = sample_subscription_data[0]
        
        result = await service.create_subscription(
            user_id="user-123",
            subscription_data=subscription_data
        )
        
        assert result is not None
        assert "subscription_id" in result
        assert result["schedule_id"] == subscription_data["schedule_id"]
        assert result["subscription_type"] == subscription_data["subscription_type"]
    
    @pytest.mark.asyncio
    async def test_list_user_subscriptions(
        self,
        sample_subscription_data,
        mock_database
    ):
        """Test listing user subscriptions."""
        from app.services.subscription_service import SubscriptionService
        
        service = SubscriptionService()
        user_id = "user-123"
        
        with patch.object(service, '_fetch_user_subscriptions') as mock_fetch:
            mock_fetch.return_value = sample_subscription_data
            
            result = await service.list_subscriptions(
                user_id=user_id,
                page=1,
                per_page=10
            )
        
        assert result is not None
        assert "subscriptions" in result
        assert "total" in result
    
    @pytest.mark.asyncio
    async def test_update_subscription(
        self,
        mock_database
    ):
        """Test updating subscription."""
        from app.services.subscription_service import SubscriptionService
        
        service = SubscriptionService()
        subscription_id = "sub-123"
        
        update_data = {
            "is_active": False,
            "frequency": "daily",
            "preferences": {
                "format": "xlsx",
                "include_attachments": False
            }
        }
        
        with patch.object(service, '_subscription_exists') as mock_exists:
            mock_exists.return_value = True
            
            result = await service.update_subscription(
                subscription_id=subscription_id,
                update_data=update_data,
                user_id="user-123"
            )
        
        assert result is not None
        assert result["is_active"] == update_data["is_active"]
        assert result["frequency"] == update_data["frequency"]
    
    @pytest.mark.asyncio
    async def test_delete_subscription(
        self,
        mock_database
    ):
        """Test deleting subscription."""
        from app.services.subscription_service import SubscriptionService
        
        service = SubscriptionService()
        subscription_id = "sub-123"
        
        with patch.object(service, '_subscription_exists') as mock_exists:
            mock_exists.return_value = True
            
            result = await service.delete_subscription(
                subscription_id=subscription_id,
                user_id="user-123"
            )
        
        assert result is not None
        assert result["deleted"] is True
    
    @pytest.mark.asyncio
    async def test_process_subscription_notifications(
        self,
        sample_subscription_data,
        mock_database,
        mock_delivery_service
    ):
        """Test processing subscription notifications."""
        from app.services.subscription_service import SubscriptionService
        
        service = SubscriptionService()
        
        execution_data = {
            "execution_id": "exec-123",
            "schedule_id": "schedule-456",
            "status": "completed",
            "report_path": "/tmp/report.pdf"
        }
        
        with patch.object(service, '_get_active_subscriptions') as mock_get_subs:
            mock_get_subs.return_value = [sample_subscription_data[0]]
            
            result = await service.process_subscription_notifications(execution_data)
        
        assert result is not None
        assert "notifications_sent" in result
        assert result["notifications_sent"] >= 0


class TestErrorHandling:
    """Test error handling in services."""
    
    @pytest.mark.asyncio
    async def test_scheduler_service_error_handling(
        self,
        mock_scheduler
    ):
        """Test scheduler service error handling."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        
        # Mock scheduler failure
        mock_scheduler.schedule_job.side_effect = Exception("Scheduler unavailable")
        
        with pytest.raises(Exception) as exc_info:
            await service.schedule_job(
                schedule_id="schedule-123",
                cron_expression="0 9 * * *",
                timezone="UTC"
            )
        
        assert "Scheduler unavailable" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_report_generation_timeout_error(
        self,
        mock_report_generator
    ):
        """Test report generation timeout error."""
        from app.services.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        
        # Mock timeout error
        mock_report_generator.generate_report.side_effect = TimeoutError("Query timeout")
        
        with pytest.raises(TimeoutError) as exc_info:
            await generator.generate_report(
                schedule_id="schedule-123",
                report_config={"query": "long running query", "format": "pdf"},
                execution_id="exec-timeout"
            )
        
        assert "Query timeout" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delivery_service_network_error(
        self,
        mock_delivery_service,
        mock_file_operations
    ):
        """Test delivery service network error handling."""
        from app.services.delivery_service import DeliveryService
        
        service = DeliveryService()
        file_path = "test_report.pdf"
        
        # Create mock report file
        mock_file_operations["create_report_file"](file_path, b"PDF content", "pdf")
        
        # Mock network error
        mock_delivery_service.deliver_report.side_effect = ConnectionError("Network unreachable")
        
        config = {
            "method": "webhook",
            "webhook_url": "https://unreachable.example.com/reports"
        }
        
        with pytest.raises(ConnectionError) as exc_info:
            await service.deliver_report(
                report_path=file_path,
                delivery_config=config,
                execution_id="exec-network-error"
            )
        
        assert "Network unreachable" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_database_connection_error(
        self,
        mock_database
    ):
        """Test database connection error handling."""
        from app.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        
        # Mock database connection error
        mock_database["get_session"].side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception) as exc_info:
            await service.get_schedule_analytics(
                schedule_id="schedule-123",
                period_days=30
            )
        
        assert "Database connection failed" in str(exc_info.value)


class TestAsyncPatterns:
    """Test async patterns and concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_report_generation(
        self,
        mock_report_generator,
        sample_schedule_data,
        mock_file_operations
    ):
        """Test concurrent report generation."""
        import asyncio
        from app.services.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        
        # Create multiple concurrent generation tasks
        tasks = []
        for i in range(3):
            config = sample_schedule_data[0]["report_config"].copy()
            config["title"] = f"Concurrent Report {i}"
            
            task = generator.generate_report(
                schedule_id=f"schedule-{i}",
                report_config=config,
                execution_id=f"exec-{i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All tasks should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert "report_id" in result
    
    @pytest.mark.asyncio
    async def test_background_job_processing(
        self,
        mock_scheduler,
        mock_report_generator,
        mock_delivery_service,
        mock_database
    ):
        """Test background job processing."""
        from app.services.scheduler_service import SchedulerService
        
        service = SchedulerService()
        
        # Simulate background processing
        with patch.object(service, '_process_scheduled_job') as mock_process:
            mock_process.return_value = {
                "execution_id": "exec-bg-123",
                "status": "completed"
            }
            
            result = await service.process_scheduled_job(
                schedule_id="schedule-123",
                triggered_at=datetime.now(timezone.utc)
            )
        
        assert result is not None
        assert result["status"] == "completed"
        mock_process.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
