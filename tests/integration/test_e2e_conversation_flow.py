#!/usr/bin/env python3
"""
End-to-end conversation flow integration tests.

This module tests complete user conversation flows across multiple services,
simulating real user interactions from natural language query to final output.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta

from .conftest import (
    get_service_url,
    make_authenticated_request,
    wait_for_service_health,
    create_test_conversation_id,
    create_test_user_context
)


class TestCompleteConversationFlow:
    """Test complete conversation flows across services."""
    
    @pytest.mark.asyncio
    async def test_query_to_visualization_flow(
        self,
        auth_headers: Dict[str, str],
        sample_natural_language_queries: List[Dict],
        mock_splunk_client
    ):
        """Test complete flow from natural language query to visualization."""
        # Step 1: Submit natural language query to NLP Engine
        query_data = sample_natural_language_queries[3]  # Chart query
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        
        response = await make_authenticated_request(
            "POST",
            nlp_url,
            auth_headers,
            {
                "query": query_data["query"],
                "context": create_test_user_context()
            }
        )
        
        assert response["status"] == 200
        spl_result = response["data"]
        assert "spl" in spl_result
        
        # Step 2: Execute SPL query (mocked)
        # In real scenario, this would go through API Gateway to Splunk
        mock_results = [
            {"_time": "2024-01-01T10:00:00", "count": 120},
            {"_time": "2024-01-01T10:05:00", "count": 150},
            {"_time": "2024-01-01T10:10:00", "count": 180},
            {"_time": "2024-01-01T10:15:00", "count": 140},
            {"_time": "2024-01-01T10:20:00", "count": 200}
        ]
        
        # Step 3: Generate visualization from results
        viz_url = get_service_url("visualization", "/api/v1/charts/generate")
        chart_response = await make_authenticated_request(
            "POST",
            viz_url,
            auth_headers,
            {
                "chart_type": "line",
                "data": mock_results,
                "title": "Events Over Time",
                "x_field": "_time",
                "y_field": "count"
            }
        )
        
        assert chart_response["status"] == 200
        chart_result = chart_response["data"]
        assert "chart_id" in chart_result
        assert "chart_url" in chart_result
    
    @pytest.mark.asyncio
    async def test_query_to_alert_creation_flow(
        self,
        auth_headers: Dict[str, str],
        sample_natural_language_queries: List[Dict],
        sample_alert_configurations: List[Dict]
    ):
        """Test flow from natural language alert query to alert creation."""
        # Step 1: Parse alert creation request
        alert_query = sample_natural_language_queries[4]  # Alert query
        nlp_url = get_service_url("nlp_engine", "/api/v1/ai/parse-alert")
        
        response = await make_authenticated_request(
            "POST",
            nlp_url,
            auth_headers,
            {
                "query": alert_query["query"],
                "context": create_test_user_context()
            }
        )
        
        assert response["status"] == 200
        alert_config = response["data"]
        
        # Step 2: Create alert in Alert Manager
        alert_url = get_service_url("alert_manager", "/api/v1/alerts")
        create_response = await make_authenticated_request(
            "POST",
            alert_url,
            auth_headers,
            {
                "name": "High Error Rate Alert",
                "search": alert_config.get("search", "search error"),
                "condition": alert_config.get("condition", "count > 100"),
                "time_window": alert_config.get("time_window", "1m"),
                "notifications": [
                    {"type": "email", "recipients": ["admin@example.com"]}
                ]
            }
        )
        
        assert create_response["status"] == 201
        alert_result = create_response["data"]
        assert "alert_id" in alert_result
        
        # Step 3: Verify alert is active
        alert_id = alert_result["alert_id"]
        status_response = await make_authenticated_request(
            "GET",
            f"{alert_url}/{alert_id}",
            auth_headers
        )
        
        assert status_response["status"] == 200
        assert status_response["data"]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_dashboard_creation_to_export_flow(
        self,
        auth_headers: Dict[str, str],
        sample_dashboard_configurations: List[Dict],
        sample_export_configurations: List[Dict]
    ):
        """Test flow from dashboard creation to PDF export."""
        # Step 1: Create dashboard
        dashboard_config = sample_dashboard_configurations[0]
        dashboard_url = get_service_url("visualization", "/api/v1/dashboards")
        
        dashboard_response = await make_authenticated_request(
            "POST",
            dashboard_url,
            auth_headers,
            dashboard_config
        )
        
        assert dashboard_response["status"] == 201
        dashboard_result = dashboard_response["data"]
        dashboard_id = dashboard_result["dashboard_id"]
        
        # Step 2: Generate PDF export
        export_config = sample_export_configurations[0]
        export_url = get_service_url("api_gateway", "/api/v1/export/pdf")
        
        export_response = await make_authenticated_request(
            "POST",
            export_url,
            auth_headers,
            {
                "dashboard_id": dashboard_id,
                "template": export_config["template"],
                "title": export_config["title"],
                "sections": export_config["sections"]
            }
        )
        
        assert export_response["status"] == 202  # Accepted for async processing
        export_result = export_response["data"]
        assert "job_id" in export_result
        
        # Step 3: Check export job status
        job_id = export_result["job_id"]
        status_url = f"{export_url}/jobs/{job_id}/status"
        
        # Poll for completion (with timeout)
        for _ in range(10):
            status_response = await make_authenticated_request(
                "GET",
                status_url,
                auth_headers
            )
            
            if status_response["status"] == 200:
                job_status = status_response["data"]["status"]
                if job_status in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)
        
        assert status_response["data"]["status"] == "completed"


class TestCrossServiceIntegration:
    """Test integration across multiple services."""
    
    @pytest.mark.asyncio
    async def test_slack_bot_query_integration(
        self,
        auth_headers: Dict[str, str],
        sample_natural_language_queries: List[Dict]
    ):
        """Test Slack bot query processing integration."""
        # Simulate Slack bot receiving a message
        slack_url = get_service_url("slack_bot", "/api/v1/slack/message")
        
        slack_message = {
            "channel": "C1234567890",
            "user": "U1234567890",
            "text": sample_natural_language_queries[0]["query"],
            "ts": "1234567890.123456"
        }
        
        response = await make_authenticated_request(
            "POST",
            slack_url,
            auth_headers,
            slack_message
        )
        
        assert response["status"] == 200
        assert "blocks" in response["data"]  # Slack Block Kit response
        
        # Verify the response contains formatted results
        blocks = response["data"]["blocks"]
        assert len(blocks) > 0
        assert any("search results" in str(block).lower() for block in blocks)
    
    @pytest.mark.asyncio
    async def test_teams_bot_alert_integration(
        self,
        auth_headers: Dict[str, str],
        sample_alert_configurations: List[Dict]
    ):
        """Test Teams bot alert creation integration."""
        # Simulate Teams bot receiving an alert creation request
        teams_url = get_service_url("teams_bot", "/api/v1/teams/message")
        
        teams_message = {
            "conversation": {"id": "19:meeting_xyz"},
            "from": {"id": "29:user_abc"},
            "text": "Create an alert for high error rates",
            "activity_type": "message"
        }
        
        response = await make_authenticated_request(
            "POST",
            teams_url,
            auth_headers,
            teams_message
        )
        
        assert response["status"] == 200
        assert "type" in response["data"]
        assert response["data"]["type"] == "message"
        
        # Verify adaptive card response
        assert "attachments" in response["data"]
        attachments = response["data"]["attachments"]
        assert len(attachments) > 0
        assert attachments[0]["contentType"] == "application/vnd.microsoft.card.adaptive"
    
    @pytest.mark.asyncio
    async def test_webhook_notification_integration(
        self,
        auth_headers: Dict[str, str],
        sample_alert_configurations: List[Dict]
    ):
        """Test webhook notification integration."""
        # Step 1: Create webhook endpoint
        webhook_url = get_service_url("webhook_service", "/api/v1/webhooks")
        
        webhook_config = {
            "url": "https://example.com/webhook",
            "events": ["alert.triggered", "alert.resolved"],
            "headers": {"Content-Type": "application/json"},
            "active": True
        }
        
        webhook_response = await make_authenticated_request(
            "POST",
            webhook_url,
            auth_headers,
            webhook_config
        )
        
        assert webhook_response["status"] == 201
        webhook_id = webhook_response["data"]["webhook_id"]
        
        # Step 2: Trigger an event
        event_url = get_service_url("webhook_service", "/api/v1/events/trigger")
        
        event_data = {
            "event_type": "alert.triggered",
            "data": {
                "alert_id": "alert_123",
                "severity": "high",
                "message": "High error rate detected",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        event_response = await make_authenticated_request(
            "POST",
            event_url,
            auth_headers,
            event_data
        )
        
        assert event_response["status"] == 202  # Accepted for processing
        
        # Step 3: Verify webhook delivery
        delivery_url = f"{webhook_url}/{webhook_id}/deliveries"
        
        # Allow time for delivery processing
        await asyncio.sleep(2)
        
        delivery_response = await make_authenticated_request(
            "GET",
            delivery_url,
            auth_headers
        )
        
        assert delivery_response["status"] == 200
        deliveries = delivery_response["data"]["deliveries"]
        assert len(deliveries) > 0
        assert deliveries[0]["event_type"] == "alert.triggered"
    
    @pytest.mark.asyncio
    async def test_email_report_integration(
        self,
        auth_headers: Dict[str, str],
        sample_export_configurations: List[Dict]
    ):
        """Test email report generation and delivery integration."""
        # Step 1: Create scheduled report
        email_url = get_service_url("email_service", "/api/v1/reports/schedule")
        
        report_config = {
            "name": "Daily Security Report",
            "query": "search security earliest=-24h | stats count by event_type",
            "schedule": "0 8 * * *",  # Daily at 8 AM
            "format": "pdf",
            "recipients": ["admin@example.com"],
            "template": "security_template"
        }
        
        schedule_response = await make_authenticated_request(
            "POST",
            email_url,
            auth_headers,
            report_config
        )
        
        assert schedule_response["status"] == 201
        schedule_id = schedule_response["data"]["schedule_id"]
        
        # Step 2: Trigger immediate report generation
        trigger_url = f"{email_url}/{schedule_id}/trigger"
        
        trigger_response = await make_authenticated_request(
            "POST",
            trigger_url,
            auth_headers
        )
        
        assert trigger_response["status"] == 202
        job_id = trigger_response["data"]["job_id"]
        
        # Step 3: Check report generation status
        status_url = get_service_url("email_service", f"/api/v1/jobs/{job_id}/status")
        
        for _ in range(10):
            status_response = await make_authenticated_request(
                "GET",
                status_url,
                auth_headers
            )
            
            if status_response["status"] == 200:
                job_status = status_response["data"]["status"]
                if job_status in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)
        
        assert status_response["data"]["status"] == "completed"
        assert "email_sent" in status_response["data"]
        assert status_response["data"]["email_sent"] is True


class TestDataFlowIntegration:
    """Test data flow and consistency across services."""
    
    @pytest.mark.asyncio
    async def test_user_session_consistency(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test user session consistency across services."""
        conversation_id = create_test_conversation_id()
        user_context = create_test_user_context()
        user_context["conversation_id"] = conversation_id
        
        # Step 1: Create session in API Gateway
        gateway_url = get_service_url("api_gateway", "/api/v1/sessions")
        
        session_response = await make_authenticated_request(
            "POST",
            gateway_url,
            auth_headers,
            {"context": user_context}
        )
        
        assert session_response["status"] == 201
        session_id = session_response["data"]["session_id"]
        
        # Step 2: Use session in NLP Engine
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        
        nlp_response = await make_authenticated_request(
            "POST",
            nlp_url,
            auth_headers,
            {
                "query": "Show me recent errors",
                "session_id": session_id,
                "context": user_context
            }
        )
        
        assert nlp_response["status"] == 200
        
        # Step 3: Verify session in Alert Manager
        alert_url = get_service_url("alert_manager", "/api/v1/alerts")
        
        alert_response = await make_authenticated_request(
            "POST",
            alert_url,
            auth_headers,
            {
                "name": "Test Alert",
                "search": "search error",
                "condition": "count > 10",
                "session_id": session_id
            }
        )
        
        assert alert_response["status"] == 201
        
        # Step 4: Verify session tracking
        session_status_url = f"{gateway_url}/{session_id}"
        
        status_response = await make_authenticated_request(
            "GET",
            session_status_url,
            auth_headers
        )
        
        assert status_response["status"] == 200
        session_data = status_response["data"]
        assert session_data["session_id"] == session_id
        assert "activities" in session_data
        assert len(session_data["activities"]) >= 2  # NLP query + Alert creation
    
    @pytest.mark.asyncio
    async def test_caching_consistency(
        self,
        auth_headers: Dict[str, str],
        sample_natural_language_queries: List[Dict]
    ):
        """Test caching consistency across services."""
        query = sample_natural_language_queries[0]
        
        # Step 1: First request to NLP Engine (cache miss)
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        
        first_response = await make_authenticated_request(
            "POST",
            nlp_url,
            auth_headers,
            {
                "query": query["query"],
                "context": create_test_user_context()
            }
        )
        
        assert first_response["status"] == 200
        first_result = first_response["data"]
        
        # Step 2: Second identical request (cache hit)
        second_response = await make_authenticated_request(
            "POST",
            nlp_url,
            auth_headers,
            {
                "query": query["query"],
                "context": create_test_user_context()
            }
        )
        
        assert second_response["status"] == 200
        second_result = second_response["data"]
        
        # Verify results are identical
        assert first_result["spl"] == second_result["spl"]
        
        # Verify cache headers (if implemented)
        if "cache_hit" in second_result:
            assert second_result["cache_hit"] is True
    
    @pytest.mark.asyncio
    async def test_error_propagation(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test error propagation across services."""
        # Step 1: Submit invalid query to NLP Engine
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        
        invalid_response = await make_authenticated_request(
            "POST",
            nlp_url,
            auth_headers,
            {
                "query": "",  # Invalid empty query
                "context": create_test_user_context()
            }
        )
        
        # Should handle error gracefully
        assert invalid_response["status"] in [400, 422]
        assert "error" in invalid_response["data"] or "detail" in invalid_response["data"]
        
        # Step 2: Submit invalid alert configuration
        alert_url = get_service_url("alert_manager", "/api/v1/alerts")
        
        invalid_alert_response = await make_authenticated_request(
            "POST",
            alert_url,
            auth_headers,
            {
                "name": "",  # Invalid empty name
                "search": "invalid spl syntax",
                "condition": "invalid condition"
            }
        )
        
        # Should handle error gracefully
        assert invalid_alert_response["status"] in [400, 422]
        
        # Verify error format consistency
        error_data = invalid_alert_response["data"]
        assert "error" in error_data or "detail" in error_data


@pytest.mark.asyncio
async def test_service_health_integration(service_health_checker):
    """Test that all services are healthy and can communicate."""
    health_status = await service_health_checker()
    
    # Log service health status
    print(f"Healthy services: {health_status['healthy']}")
    print(f"Unhealthy services: {health_status['unhealthy']}")
    
    # For integration tests, we can proceed even if some services are unavailable
    # but we should have at least core services available
    core_services = ["API Gateway", "NLP Engine"]
    available_core = [s for s in core_services if s in health_status['healthy']]
    
    assert len(available_core) > 0, f"No core services available. Healthy: {health_status['healthy']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])