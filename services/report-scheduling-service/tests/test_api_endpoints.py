#!/usr/bin/env python3
"""
Comprehensive API endpoint tests for Report Scheduling Service.

This module tests all API endpoints including schedules, executions, versions,
analytics, and error handling with comprehensive scenarios.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta, timezone
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestScheduleEndpoints:
    """Test schedule management endpoints."""
    
    def test_create_schedule_success(
        self,
        test_client,
        auth_headers,
        sample_schedule_data,
        mock_scheduler,
        mock_database,
        mock_redis
    ):
        """Test successful schedule creation."""
        schedule_data = sample_schedule_data[0]
        
        response = test_client.post(
            "/api/v1/schedules",
            headers=auth_headers,
            json=schedule_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "schedule_id" in data
        assert data["name"] == schedule_data["name"]
        assert data["cron_expression"] == schedule_data["cron_expression"]
        assert data["is_active"] == schedule_data["is_active"]
        assert "created_at" in data
    
    def test_create_schedule_with_all_fields(
        self,
        test_client,
        auth_headers,
        sample_schedule_data,
        mock_scheduler,
        mock_database
    ):
        """Test schedule creation with all optional fields."""
        schedule_data = sample_schedule_data[1]  # Weekly performance dashboard
        
        response = test_client.post(
            "/api/v1/schedules",
            headers=auth_headers,
            json=schedule_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["priority"] == schedule_data["priority"]
        assert data["timezone"] == schedule_data["timezone"]
        assert data["delivery_config"] == schedule_data["delivery_config"]
        assert data["retention_days"] == schedule_data["retention_days"]
    
    def test_create_schedule_invalid_cron(
        self,
        test_client,
        auth_headers,
        sample_schedule_data
    ):
        """Test schedule creation with invalid cron expression."""
        schedule_data = sample_schedule_data[0].copy()
        schedule_data["cron_expression"] = "invalid cron expression"
        
        response = test_client.post(
            "/api/v1/schedules",
            headers=auth_headers,
            json=schedule_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
    
    def test_create_schedule_missing_required_fields(
        self,
        test_client,
        auth_headers
    ):
        """Test schedule creation with missing required fields."""
        incomplete_data = {
            "name": "Incomplete Schedule"
            # Missing cron_expression and other required fields
        }
        
        response = test_client.post(
            "/api/v1/schedules",
            headers=auth_headers,
            json=incomplete_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_schedule_unauthorized(
        self,
        test_client,
        sample_schedule_data
    ):
        """Test schedule creation without authentication."""
        response = test_client.post(
            "/api/v1/schedules",
            json=sample_schedule_data[0]
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_schedule_by_id_success(
        self,
        test_client,
        auth_headers,
        sample_schedule_data,
        mock_database
    ):
        """Test successful schedule retrieval by ID."""
        schedule_id = "schedule-123"
        schedule_data = sample_schedule_data[0]
        
        with patch('app.services.schedule_service.ScheduleService.get_schedule') as mock_get:
            mock_get.return_value = {
                "schedule_id": schedule_id,
                **schedule_data,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            response = test_client.get(
                f"/api/v1/schedules/{schedule_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["schedule_id"] == schedule_id
        assert data["name"] == schedule_data["name"]
    
    def test_get_schedule_not_found(
        self,
        test_client,
        auth_headers,
        mock_database
    ):
        """Test schedule retrieval for non-existent schedule."""
        schedule_id = "non-existent-schedule"
        
        with patch('app.services.schedule_service.ScheduleService.get_schedule') as mock_get:
            mock_get.return_value = None
            
            response = test_client.get(
                f"/api/v1/schedules/{schedule_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_schedule_success(
        self,
        test_client,
        auth_headers,
        mock_database,
        mock_scheduler
    ):
        """Test successful schedule update."""
        schedule_id = "schedule-123"
        update_data = {
            "name": "Updated Schedule Name",
            "description": "Updated description",
            "is_active": False
        }
        
        with patch('app.services.schedule_service.ScheduleService.update_schedule') as mock_update:
            mock_update.return_value = {
                "schedule_id": schedule_id,
                **update_data,
                "updated_at": datetime.now(timezone.utc)
            }
            
            response = test_client.put(
                f"/api/v1/schedules/{schedule_id}",
                headers=auth_headers,
                json=update_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["is_active"] == update_data["is_active"]
    
    def test_delete_schedule_success(
        self,
        test_client,
        auth_headers,
        mock_database,
        mock_scheduler
    ):
        """Test successful schedule deletion."""
        schedule_id = "schedule-123"
        
        with patch('app.services.schedule_service.ScheduleService.delete_schedule') as mock_delete:
            mock_delete.return_value = True
            
            response = test_client.delete(
                f"/api/v1/schedules/{schedule_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Schedule deleted successfully"
    
    def test_list_schedules_with_filters(
        self,
        test_client,
        auth_headers,
        sample_schedule_data,
        mock_database
    ):
        """Test listing schedules with filters."""
        with patch('app.services.schedule_service.ScheduleService.list_schedules') as mock_list:
            mock_list.return_value = {
                "schedules": sample_schedule_data,
                "total": len(sample_schedule_data),
                "page": 1,
                "per_page": 10
            }
            
            response = test_client.get(
                "/api/v1/schedules",
                headers=auth_headers,
                params={
                    "is_active": "true",
                    "priority": "high",
                    "page": 1,
                    "per_page": 10
                }
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "schedules" in data
        assert "total" in data
        assert isinstance(data["schedules"], list)
    
    def test_pause_schedule_success(
        self,
        test_client,
        auth_headers,
        mock_scheduler
    ):
        """Test successful schedule pause."""
        schedule_id = "schedule-123"
        
        response = test_client.post(
            f"/api/v1/schedules/{schedule_id}/pause",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Schedule paused successfully"
        mock_scheduler.pause_job.assert_called_once()
    
    def test_resume_schedule_success(
        self,
        test_client,
        auth_headers,
        mock_scheduler
    ):
        """Test successful schedule resume."""
        schedule_id = "schedule-123"
        
        response = test_client.post(
            f"/api/v1/schedules/{schedule_id}/resume",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Schedule resumed successfully"
        mock_scheduler.resume_job.assert_called_once()
    
    def test_trigger_schedule_manually(
        self,
        test_client,
        auth_headers,
        mock_scheduler,
        mock_report_generator
    ):
        """Test manual schedule trigger."""
        schedule_id = "schedule-123"
        
        response = test_client.post(
            f"/api/v1/schedules/{schedule_id}/trigger",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "execution_id" in data
        assert data["status"] == "triggered"


class TestExecutionEndpoints:
    """Test execution management endpoints."""
    
    def test_get_execution_by_id(
        self,
        test_client,
        auth_headers,
        sample_execution_data,
        mock_database
    ):
        """Test getting execution by ID."""
        execution_id = "exec-123"
        execution_data = sample_execution_data[0]
        
        with patch('app.services.execution_service.ExecutionService.get_execution') as mock_get:
            mock_get.return_value = {
                "execution_id": execution_id,
                **execution_data
            }
            
            response = test_client.get(
                f"/api/v1/executions/{execution_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["execution_id"] == execution_id
        assert data["status"] == execution_data["status"]
    
    def test_list_executions_for_schedule(
        self,
        test_client,
        auth_headers,
        sample_execution_data,
        mock_database
    ):
        """Test listing executions for a specific schedule."""
        schedule_id = "schedule-456"
        
        with patch('app.services.execution_service.ExecutionService.list_executions') as mock_list:
            mock_list.return_value = {
                "executions": sample_execution_data,
                "total": len(sample_execution_data),
                "page": 1,
                "per_page": 10
            }
            
            response = test_client.get(
                f"/api/v1/schedules/{schedule_id}/executions",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "executions" in data
        assert "total" in data
    
    def test_cancel_execution(
        self,
        test_client,
        auth_headers,
        mock_database
    ):
        """Test execution cancellation."""
        execution_id = "exec-456"
        
        with patch('app.services.execution_service.ExecutionService.cancel_execution') as mock_cancel:
            mock_cancel.return_value = {
                "execution_id": execution_id,
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc)
            }
            
            response = test_client.post(
                f"/api/v1/executions/{execution_id}/cancel",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "cancelled"
    
    def test_retry_failed_execution(
        self,
        test_client,
        auth_headers,
        mock_database,
        mock_report_generator
    ):
        """Test retrying a failed execution."""
        execution_id = "exec-789"
        
        with patch('app.services.execution_service.ExecutionService.retry_execution') as mock_retry:
            mock_retry.return_value = {
                "execution_id": execution_id,
                "status": "pending",
                "retry_count": 1
            }
            
            response = test_client.post(
                f"/api/v1/executions/{execution_id}/retry",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "pending"
        assert data["retry_count"] == 1
    
    def test_download_execution_report(
        self,
        test_client,
        auth_headers,
        mock_file_operations,
        mock_database
    ):
        """Test downloading execution report."""
        execution_id = "exec-123"
        file_path = "test_report.pdf"
        
        # Create mock file
        mock_file_operations["create_report_file"](file_path, b"PDF content", "pdf")
        
        with patch('app.services.execution_service.ExecutionService.get_execution') as mock_get:
            mock_get.return_value = {
                "execution_id": execution_id,
                "status": "completed",
                "file_path": file_path
            }
            
            response = test_client.get(
                f"/api/v1/executions/{execution_id}/download",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"


class TestVersionEndpoints:
    """Test version management endpoints."""
    
    def test_list_schedule_versions(
        self,
        test_client,
        auth_headers,
        sample_version_data,
        mock_database
    ):
        """Test listing schedule versions."""
        schedule_id = "schedule-123"
        
        with patch('app.services.version_service.VersionService.list_versions') as mock_list:
            mock_list.return_value = {
                "versions": sample_version_data,
                "total": len(sample_version_data),
                "page": 1,
                "per_page": 10
            }
            
            response = test_client.get(
                f"/api/v1/schedules/{schedule_id}/versions",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "versions" in data
        assert "total" in data
    
    def test_get_version_by_id(
        self,
        test_client,
        auth_headers,
        sample_version_data,
        mock_database
    ):
        """Test getting specific version."""
        version_id = "v1.2.0"
        version_data = sample_version_data[2]  # Current version
        
        with patch('app.services.version_service.VersionService.get_version') as mock_get:
            mock_get.return_value = {
                "version_id": version_id,
                **version_data
            }
            
            response = test_client.get(
                f"/api/v1/versions/{version_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["version_id"] == version_id
        assert data["is_current"] == version_data["is_current"]
    
    def test_restore_schedule_version(
        self,
        test_client,
        auth_headers,
        mock_database,
        mock_scheduler
    ):
        """Test restoring schedule to previous version."""
        schedule_id = "schedule-123"
        version_id = "v1.1.0"
        
        with patch('app.services.version_service.VersionService.restore_version') as mock_restore:
            mock_restore.return_value = {
                "schedule_id": schedule_id,
                "version_id": version_id,
                "restored_at": datetime.now(timezone.utc)
            }
            
            response = test_client.post(
                f"/api/v1/schedules/{schedule_id}/versions/{version_id}/restore",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["version_id"] == version_id
        assert "restored_at" in data
    
    def test_compare_versions(
        self,
        test_client,
        auth_headers,
        mock_database
    ):
        """Test comparing two schedule versions."""
        version1_id = "v1.1.0"
        version2_id = "v1.2.0"
        
        with patch('app.services.version_service.VersionService.compare_versions') as mock_compare:
            mock_compare.return_value = {
                "version1": version1_id,
                "version2": version2_id,
                "differences": [
                    {
                        "field": "report_config.include_charts",
                        "old_value": False,
                        "new_value": True
                    }
                ],
                "summary": "Added chart support to report configuration"
            }
            
            response = test_client.get(
                f"/api/v1/versions/{version1_id}/compare/{version2_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "differences" in data
        assert "summary" in data


class TestAnalyticsEndpoints:
    """Test analytics and metrics endpoints."""
    
    def test_get_schedule_analytics(
        self,
        test_client,
        auth_headers,
        mock_analytics_service
    ):
        """Test getting schedule analytics."""
        schedule_id = "schedule-123"
        
        response = test_client.get(
            f"/api/v1/schedules/{schedule_id}/analytics",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_executions" in data
        assert "success_rate" in data
        assert "average_execution_time_ms" in data
        mock_analytics_service.get_schedule_analytics.assert_called_once()
    
    def test_get_system_analytics(
        self,
        test_client,
        auth_headers,
        mock_analytics_service
    ):
        """Test getting system-wide analytics."""
        response = test_client.get(
            "/api/v1/analytics/system",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_schedules" in data
        assert "active_schedules" in data
        assert "queue_length" in data
        mock_analytics_service.get_system_analytics.assert_called_once()
    
    def test_get_user_analytics(
        self,
        test_client,
        auth_headers,
        mock_analytics_service
    ):
        """Test getting user-specific analytics."""
        response = test_client.get(
            "/api/v1/analytics/user",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "schedules_created" in data
        assert "reports_generated" in data
        assert "data_consumed_mb" in data
        mock_analytics_service.get_user_analytics.assert_called_once()
    
    def test_get_performance_metrics(
        self,
        test_client,
        auth_headers,
        mock_analytics_service
    ):
        """Test getting performance metrics."""
        response = test_client.get(
            "/api/v1/analytics/performance",
            headers=auth_headers,
            params={
                "period": "7d",
                "granularity": "1h"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)  # Time series data


class TestSubscriptionEndpoints:
    """Test subscription management endpoints."""
    
    def test_create_subscription(
        self,
        test_client,
        auth_headers,
        sample_subscription_data,
        mock_database
    ):
        """Test creating schedule subscription."""
        subscription_data = sample_subscription_data[0]
        
        with patch('app.services.subscription_service.SubscriptionService.create_subscription') as mock_create:
            mock_create.return_value = {
                "subscription_id": "sub-123",
                **subscription_data,
                "created_at": datetime.now(timezone.utc)
            }
            
            response = test_client.post(
                "/api/v1/subscriptions",
                headers=auth_headers,
                json=subscription_data
            )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "subscription_id" in data
        assert data["subscription_type"] == subscription_data["subscription_type"]
    
    def test_list_user_subscriptions(
        self,
        test_client,
        auth_headers,
        sample_subscription_data,
        mock_database
    ):
        """Test listing user subscriptions."""
        with patch('app.services.subscription_service.SubscriptionService.list_subscriptions') as mock_list:
            mock_list.return_value = {
                "subscriptions": sample_subscription_data,
                "total": len(sample_subscription_data)
            }
            
            response = test_client.get(
                "/api/v1/subscriptions",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "subscriptions" in data
        assert "total" in data
    
    def test_update_subscription(
        self,
        test_client,
        auth_headers,
        mock_database
    ):
        """Test updating subscription preferences."""
        subscription_id = "sub-123"
        update_data = {
            "is_active": False,
            "frequency": "daily",
            "preferences": {
                "format": "xlsx",
                "include_attachments": False
            }
        }
        
        with patch('app.services.subscription_service.SubscriptionService.update_subscription') as mock_update:
            mock_update.return_value = {
                "subscription_id": subscription_id,
                **update_data,
                "updated_at": datetime.now(timezone.utc)
            }
            
            response = test_client.put(
                f"/api/v1/subscriptions/{subscription_id}",
                headers=auth_headers,
                json=update_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] == update_data["is_active"]
        assert data["frequency"] == update_data["frequency"]
    
    def test_delete_subscription(
        self,
        test_client,
        auth_headers,
        mock_database
    ):
        """Test deleting subscription."""
        subscription_id = "sub-123"
        
        with patch('app.services.subscription_service.SubscriptionService.delete_subscription') as mock_delete:
            mock_delete.return_value = True
            
            response = test_client.delete(
                f"/api/v1/subscriptions/{subscription_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Subscription deleted successfully"


class TestHealthAndStatusEndpoints:
    """Test health and status endpoints."""
    
    def test_health_check(
        self,
        test_client
    ):
        """Test health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_service_status(
        self,
        test_client,
        mock_redis,
        mock_database
    ):
        """Test service status endpoint."""
        response = test_client.get("/api/v1/status")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "dependencies" in data
        assert "uptime" in data
    
    def test_service_capabilities(
        self,
        test_client
    ):
        """Test service capabilities endpoint."""
        response = test_client.get("/api/v1/capabilities")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "supported_formats" in data
        assert "supported_delivery_methods" in data
        assert "features" in data
        assert "limits" in data


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_schedule_not_found_error(
        self,
        test_client,
        auth_headers,
        mock_database
    ):
        """Test error handling for non-existent schedule."""
        schedule_id = "non-existent-schedule"
        
        with patch('app.services.schedule_service.ScheduleService.get_schedule') as mock_get:
            mock_get.side_effect = ValueError("Schedule not found")
            
            response = test_client.get(
                f"/api/v1/schedules/{schedule_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_database_connection_error(
        self,
        test_client,
        auth_headers,
        sample_schedule_data
    ):
        """Test handling of database connection errors."""
        with patch('app.services.schedule_service.ScheduleService.create_schedule') as mock_create:
            mock_create.side_effect = Exception("Database connection failed")
            
            response = test_client.post(
                "/api/v1/schedules",
                headers=auth_headers,
                json=sample_schedule_data[0]
            )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_scheduler_unavailable_error(
        self,
        test_client,
        auth_headers,
        mock_scheduler
    ):
        """Test handling of scheduler service errors."""
        schedule_id = "schedule-123"
        mock_scheduler.pause_job.side_effect = Exception("Scheduler unavailable")
        
        response = test_client.post(
            f"/api/v1/schedules/{schedule_id}/pause",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    
    def test_validation_errors(
        self,
        test_client,
        auth_headers
    ):
        """Test various validation error scenarios."""
        # Test empty request body
        response = test_client.post(
            "/api/v1/schedules",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test invalid cron expression
        invalid_schedule = {
            "name": "Invalid Schedule",
            "cron_expression": "invalid cron",
            "report_config": {},
            "delivery_config": {}
        }
        response = test_client.post(
            "/api/v1/schedules",
            headers=auth_headers,
            json=invalid_schedule
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_rate_limiting(
        self,
        test_client,
        auth_headers,
        sample_schedule_data
    ):
        """Test rate limiting functionality."""
        with patch('app.utils.rate_limiter.check_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = False  # Rate limit exceeded
            
            response = test_client.post(
                "/api/v1/schedules",
                headers=auth_headers,
                json=sample_schedule_data[0]
            )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert "rate limit" in data["detail"].lower()


class TestAsyncEndpoints:
    """Test async endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_async_schedule_processing(
        self,
        async_client,
        auth_headers,
        sample_schedule_data,
        mock_scheduler,
        mock_report_generator
    ):
        """Test async schedule processing."""
        schedule_data = sample_schedule_data[0]
        
        response = await async_client.post(
            "/api/v1/schedules",
            headers=auth_headers,
            json=schedule_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "schedule_id" in data
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_requests(
        self,
        async_client,
        auth_headers,
        mock_scheduler,
        mock_report_generator
    ):
        """Test handling of concurrent execution requests."""
        import asyncio
        
        schedule_ids = ["schedule-1", "schedule-2", "schedule-3"]
        
        # Create concurrent trigger requests
        tasks = [
            async_client.post(
                f"/api/v1/schedules/{schedule_id}/trigger",
                headers=auth_headers
            )
            for schedule_id in schedule_ids
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed or handle gracefully
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [200, 202, 429]  # Success, Accepted, or Rate Limited


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
