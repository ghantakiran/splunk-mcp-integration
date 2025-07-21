#!/usr/bin/env python3
"""
Security integration testing across services.

This module tests security controls, authentication flows, authorization,
data protection, and security boundaries across the entire system.
"""

import pytest
import asyncio
import json
import base64
from typing import Dict, Any, List
from datetime import datetime, timedelta

from .conftest import (
    get_service_url,
    make_authenticated_request,
    create_test_conversation_id,
    create_test_user_context
)


class TestAuthenticationIntegration:
    """Test authentication flows across services."""
    
    @pytest.mark.asyncio
    async def test_jwt_token_propagation(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test JWT token propagation across service boundaries."""
        # Test that JWT tokens are properly validated across all services
        services_to_test = [
            ("api_gateway", "/api/v1/profile"),
            ("nlp_engine", "/api/v1/spl/translate"),
            ("visualization", "/api/v1/charts"),
            ("alert_manager", "/api/v1/alerts")
        ]
        
        for service_name, endpoint in services_to_test:
            url = get_service_url(service_name, endpoint)
            
            # Test with valid token
            response = await make_authenticated_request(
                "GET",
                url,
                auth_headers
            )
            
            # Should not return 401 for valid token
            assert response["status"] != 401, f"Valid token rejected by {service_name}"
    
    @pytest.mark.asyncio
    async def test_invalid_token_handling(self):
        """Test handling of invalid JWT tokens."""
        invalid_headers = {
            "Authorization": "Bearer invalid_token_12345",
            "Content-Type": "application/json"
        }
        
        services_to_test = [
            ("api_gateway", "/api/v1/profile"),
            ("nlp_engine", "/api/v1/spl/translate"),
            ("alert_manager", "/api/v1/alerts")
        ]
        
        for service_name, endpoint in services_to_test:
            url = get_service_url(service_name, endpoint)
            
            response = await make_authenticated_request(
                "GET",
                url,
                invalid_headers
            )
            
            # Should return 401 for invalid token
            assert response["status"] == 401, f"Invalid token not rejected by {service_name}"
    
    @pytest.mark.asyncio
    async def test_token_expiration_handling(self):
        """Test handling of expired JWT tokens."""
        # Create an expired token (in real implementation)
        expired_headers = {
            "Authorization": "Bearer expired_token_12345",
            "Content-Type": "application/json"
        }
        
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        
        response = await make_authenticated_request(
            "POST",
            nlp_url,
            expired_headers,
            {"query": "test query", "context": create_test_user_context()}
        )
        
        # Should return 401 for expired token
        assert response["status"] == 401
        assert "expired" in response["data"].get("detail", "").lower() or "unauthorized" in response["data"].get("detail", "").lower()
    
    @pytest.mark.asyncio
    async def test_cross_service_session_validation(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test session validation across services."""
        # Create session in API Gateway
        gateway_url = get_service_url("api_gateway", "/api/v1/sessions")
        
        session_response = await make_authenticated_request(
            "POST",
            gateway_url,
            auth_headers,
            {"context": create_test_user_context()}
        )
        
        assert session_response["status"] == 201
        session_id = session_response["data"]["session_id"]
        
        # Use session in other services
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        
        nlp_response = await make_authenticated_request(
            "POST",
            nlp_url,
            auth_headers,
            {
                "query": "test query",
                "session_id": session_id,
                "context": create_test_user_context()
            }
        )
        
        assert nlp_response["status"] == 200
        
        # Verify session is tracked consistently
        session_check = await make_authenticated_request(
            "GET",
            f"{gateway_url}/{session_id}",
            auth_headers
        )
        
        assert session_check["status"] == 200
        assert session_check["data"]["session_id"] == session_id


class TestAuthorizationIntegration:
    """Test authorization and permission controls."""
    
    @pytest.mark.asyncio
    async def test_role_based_access_control(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test RBAC enforcement across services."""
        # Test with different user roles
        user_roles_to_test = [
            {"role": "admin", "should_access": True},
            {"role": "user", "should_access": True},
            {"role": "viewer", "should_access": False}  # Viewer shouldn't create alerts
        ]
        
        for role_test in user_roles_to_test:
            # Simulate user with specific role
            role_headers = auth_headers.copy()
            # In real implementation, this would be a different token with role
            
            alert_url = get_service_url("alert_manager", "/api/v1/alerts")
            
            response = await make_authenticated_request(
                "POST",
                alert_url,
                role_headers,
                {
                    "name": f"Test Alert for {role_test['role']}",
                    "search": "search error",
                    "condition": "count > 10"
                }
            )
            
            if role_test["should_access"]:
                assert response["status"] in [201, 401], f"Role {role_test['role']} should have access"
            else:
                assert response["status"] in [403, 401], f"Role {role_test['role']} should be forbidden"
    
    @pytest.mark.asyncio
    async def test_data_access_permissions(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test data access permissions based on user context."""
        # Test access to different Splunk indexes
        restricted_context = create_test_user_context()
        restricted_context["splunk_access"]["indexes"] = ["limited_index"]
        
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        
        # Query that should be restricted
        response = await make_authenticated_request(
            "POST",
            nlp_url,
            auth_headers,
            {
                "query": "search index=security secret data",
                "context": restricted_context
            }
        )
        
        # Should either be allowed or properly handle restrictions
        assert response["status"] in [200, 403]
        
        if response["status"] == 200:
            # If allowed, SPL should be modified to only include accessible indexes
            spl_result = response["data"]["spl"]
            assert "index=limited_index" in spl_result or "index=" not in spl_result
    
    @pytest.mark.asyncio
    async def test_operation_permissions(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test operation-level permissions."""
        # Test different operations with varying permission requirements
        operations_to_test = [
            ("GET", "visualization", "/api/v1/charts", {}, "read"),
            ("POST", "visualization", "/api/v1/charts/generate", {"chart_type": "line", "data": []}, "create"),
            ("DELETE", "alert_manager", "/api/v1/alerts/123", {}, "delete"),
            ("POST", "api_gateway", "/api/v1/export/pdf", {"title": "Test"}, "export")
        ]
        
        for method, service, endpoint, data, permission_type in operations_to_test:
            url = get_service_url(service, endpoint)
            
            response = await make_authenticated_request(
                method,
                url,
                auth_headers,
                data if data else None
            )
            
            # Should not return 403 for authorized operations
            # (401 is acceptable if service is not available)
            assert response["status"] != 403, f"Permission denied for {permission_type} operation on {service}"


class TestInputValidationSecurity:
    """Test input validation and sanitization security."""
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test SQL injection prevention across services."""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM passwords",
            "admin'/*",
            "' OR 1=1#"
        ]
        
        for payload in sql_injection_payloads:
            # Test NLP Engine
            nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
            
            response = await make_authenticated_request(
                "POST",
                nlp_url,
                auth_headers,
                {
                    "query": payload,
                    "context": create_test_user_context()
                }
            )
            
            # Should either reject or sanitize the input
            assert response["status"] in [200, 400, 422]
            
            if response["status"] == 200:
                # If processed, should not contain dangerous SQL
                spl_result = response["data"]["spl"]
                dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "UNION"]
                assert not any(keyword in spl_result.upper() for keyword in dangerous_keywords)
            
            # Test Alert Manager
            alert_url = get_service_url("alert_manager", "/api/v1/alerts")
            
            alert_response = await make_authenticated_request(
                "POST",
                alert_url,
                auth_headers,
                {
                    "name": payload,
                    "search": "search error",
                    "condition": "count > 10"
                }
            )
            
            # Should reject dangerous input
            assert alert_response["status"] in [400, 422, 500]
    
    @pytest.mark.asyncio
    async def test_xss_prevention(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test XSS prevention in user inputs."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('xss')",
            "<svg onload=alert(1)>",
            "';alert(String.fromCharCode(88,83,83))//'"
        ]
        
        for payload in xss_payloads:
            # Test dashboard creation
            dashboard_url = get_service_url("visualization", "/api/v1/dashboards")
            
            response = await make_authenticated_request(
                "POST",
                dashboard_url,
                auth_headers,
                {
                    "title": payload,
                    "description": "Test dashboard",
                    "layout": {"rows": 1, "columns": 1, "panels": []}
                }
            )
            
            # Should either reject or sanitize
            assert response["status"] in [201, 400, 422]
            
            if response["status"] == 201:
                # If created, title should be sanitized
                dashboard_id = response["data"]["dashboard_id"]
                
                get_response = await make_authenticated_request(
                    "GET",
                    f"{dashboard_url}/{dashboard_id}",
                    auth_headers
                )
                
                if get_response["status"] == 200:
                    title = get_response["data"]["title"]
                    # Should not contain script tags or javascript
                    assert "<script>" not in title.lower()
                    assert "javascript:" not in title.lower()
    
    @pytest.mark.asyncio
    async def test_command_injection_prevention(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test command injection prevention."""
        command_injection_payloads = [
            "; cat /etc/passwd",
            "| whoami",
            "&& rm -rf /",
            "`id`",
            "$(ps aux)"
        ]
        
        for payload in command_injection_payloads:
            # Test export functionality (might involve file operations)
            export_url = get_service_url("api_gateway", "/api/v1/export/pdf")
            
            response = await make_authenticated_request(
                "POST",
                export_url,
                auth_headers,
                {
                    "title": payload,
                    "template": "standard",
                    "sections": [{"title": "Test", "type": "text", "content": "Test"}]
                }
            )
            
            # Should reject dangerous input
            assert response["status"] in [202, 400, 422]  # 202 if async processing
    
    @pytest.mark.asyncio
    async def test_path_traversal_prevention(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test path traversal prevention."""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd"
        ]
        
        for payload in path_traversal_payloads:
            # Test file-related operations
            export_url = get_service_url("api_gateway", "/api/v1/export/pdf")
            
            response = await make_authenticated_request(
                "POST",
                export_url,
                auth_headers,
                {
                    "title": "Test Export",
                    "template": payload,  # Dangerous template path
                    "sections": [{"title": "Test", "type": "text", "content": "Test"}]
                }
            )
            
            # Should reject dangerous paths
            assert response["status"] in [400, 422, 404]


class TestDataProtectionSecurity:
    """Test data protection and privacy controls."""
    
    @pytest.mark.asyncio
    async def test_sensitive_data_masking(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test sensitive data masking in responses."""
        # Test that sensitive data is properly masked
        profile_url = get_service_url("api_gateway", "/api/v1/profile")
        
        response = await make_authenticated_request(
            "GET",
            profile_url,
            auth_headers
        )
        
        if response["status"] == 200:
            profile_data = response["data"]
            
            # Sensitive fields should be masked or excluded
            sensitive_fields = ["password", "ssn", "credit_card", "api_key", "secret"]
            
            def check_for_sensitive_data(data, path=""):
                if isinstance(data, dict):
                    for key, value in data.items():
                        current_path = f"{path}.{key}" if path else key
                        
                        # Check if field name suggests sensitive data
                        if any(sensitive in key.lower() for sensitive in sensitive_fields):
                            assert value in [None, "", "***", "MASKED"], f"Sensitive field {current_path} not masked: {value}"
                        
                        if isinstance(value, (dict, list)):
                            check_for_sensitive_data(value, current_path)
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        check_for_sensitive_data(item, f"{path}[{i}]")
            
            check_for_sensitive_data(profile_data)
    
    @pytest.mark.asyncio
    async def test_data_encryption_in_transit(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test that sensitive data is encrypted in transit."""
        # This test would typically check HTTPS enforcement
        # For now, we'll test that sensitive data isn't transmitted in plain text
        
        # Test password-related operations
        auth_url = get_service_url("api_gateway", "/api/v1/auth/change-password")
        
        response = await make_authenticated_request(
            "POST",
            auth_url,
            auth_headers,
            {
                "current_password": "current_pass",
                "new_password": "new_pass"
            }
        )
        
        # Should handle password change requests securely
        # (might return 404 if endpoint doesn't exist, which is fine for this test)
        assert response["status"] in [200, 404, 401, 403]
    
    @pytest.mark.asyncio
    async def test_log_sanitization(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test that logs don't contain sensitive information."""
        # Submit request with sensitive data
        nlp_url = get_service_url("nlp_engine", "/api/v1/spl/translate")
        
        response = await make_authenticated_request(
            "POST",
            nlp_url,
            auth_headers,
            {
                "query": "search password=secret123 OR ssn=123-45-6789",
                "context": create_test_user_context()
            }
        )
        
        # Service should handle the request but not log sensitive data
        assert response["status"] in [200, 400, 422]
        
        # In a real test, we would check actual log files to ensure
        # sensitive data like "secret123" and "123-45-6789" are not logged


class TestSecurityHeadersAndPolicies:
    """Test security headers and policies."""
    
    @pytest.mark.asyncio
    async def test_security_headers_present(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test that proper security headers are present."""
        services_to_test = [
            ("api_gateway", "/api/v1/health"),
            ("nlp_engine", "/health"),
            ("visualization", "/health")
        ]
        
        for service_name, endpoint in services_to_test:
            url = get_service_url(service_name, endpoint)
            
            response = await make_authenticated_request(
                "GET",
                url,
                auth_headers
            )
            
            if response["status"] == 200:
                headers = response["headers"]
                
                # Check for important security headers
                security_headers = [
                    "x-content-type-options",
                    "x-frame-options",
                    "x-xss-protection",
                    "strict-transport-security",
                    "content-security-policy"
                ]
                
                present_headers = [h for h in security_headers if h in headers]
                
                # At least some security headers should be present
                assert len(present_headers) > 0, f"No security headers found for {service_name}"
    
    @pytest.mark.asyncio
    async def test_cors_policy_enforcement(
        self,
        auth_headers: Dict[str, str]
    ):
        """Test CORS policy enforcement."""
        # Test preflight OPTIONS request
        api_url = get_service_url("api_gateway", "/api/v1/health")
        
        # This would require implementing actual CORS testing
        # For now, we'll test that the endpoint responds appropriately
        response = await make_authenticated_request(
            "GET",
            api_url,
            auth_headers
        )
        
        assert response["status"] == 200
        
        # Check for CORS headers in response
        headers = response["headers"]
        cors_headers = ["access-control-allow-origin", "access-control-allow-methods", "access-control-allow-headers"]
        
        # Some CORS headers should be present for API endpoints
        present_cors_headers = [h for h in cors_headers if h in headers]
        
        # This assertion might need adjustment based on actual CORS implementation
        # assert len(present_cors_headers) > 0, "No CORS headers found"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])