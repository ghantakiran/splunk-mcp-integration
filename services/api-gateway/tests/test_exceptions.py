"""
Comprehensive tests for the exception handling system.

This module tests all aspects of the enhanced exception handling including:
- Custom exception creation and behavior
- Exception to HTTP mapping
- Error context and tracking
- Exception handlers and middleware
- Error metrics and monitoring
"""

import pytest
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI, Request, status
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from unittest.mock import Mock, patch

from app.core.exceptions import (
    BaseCustomException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ResourceExistsError,
    ExternalServiceError,
    DatabaseError,
    SPLTranslationError,
    QueryTimeoutError,
    RateLimitExceededError,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    ErrorTracker,
    ErrorMetrics,
    map_exception_to_http,
    create_detailed_http_exception,
    validation_error,
    not_found_error,
    unauthorized_error,
    forbidden_error,
    service_unavailable_error,
    rate_limit_error
)
from app.core.exception_handlers import (
    ExceptionHandlingMiddleware,
    custom_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)


class TestBaseCustomException:
    """Test the base exception class functionality"""
    
    def test_basic_exception_creation(self):
        """Test basic exception creation with default values"""
        exc = BaseCustomException("Test error")
        
        assert exc.message == "Test error"
        assert exc.user_message == "Test error"
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.category == ErrorCategory.SYSTEM_ERROR
        assert exc.error_code == "basecustomexception_error"
        assert exc.details == {}
        assert exc.suggestions == []
        assert exc.retry_after is None
        assert exc.context is None
        assert exc.cause is None
        assert exc.error_id is not None
        assert isinstance(exc.created_at, datetime)
    
    def test_exception_with_all_parameters(self):
        """Test exception creation with all parameters"""
        details = {"field": "test", "value": 123}
        suggestions = ["Try again", "Check input"]
        context = ErrorContext(
            correlation_id="test-id",
            timestamp=datetime.utcnow(),
            user_id="user123"
        )
        
        exc = BaseCustomException(
            message="Detailed error",
            details=details,
            error_code="custom_error",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION,
            context=context,
            user_message="User-friendly message",
            suggestions=suggestions,
            retry_after=60
        )
        
        assert exc.message == "Detailed error"
        assert exc.user_message == "User-friendly message"
        assert exc.details == details
        assert exc.error_code == "custom_error"
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.VALIDATION
        assert exc.context == context
        assert exc.suggestions == suggestions
        assert exc.retry_after == 60
    
    def test_exception_to_dict(self):
        """Test exception conversion to dictionary"""
        exc = BaseCustomException(
            "Test error",
            details={"key": "value"},
            error_code="test_error"
        )
        
        exc_dict = exc.to_dict()
        
        assert exc_dict["message"] == "Test error"
        assert exc_dict["error_code"] == "test_error"
        assert exc_dict["details"] == {"key": "value"}
        assert exc_dict["severity"] == "medium"
        assert exc_dict["category"] == "system_error"
        assert "error_id" in exc_dict
        assert "created_at" in exc_dict
    
    def test_with_context(self):
        """Test adding context to exception"""
        exc = BaseCustomException("Test error")
        context = ErrorContext(
            correlation_id="test-id",
            timestamp=datetime.utcnow()
        )
        
        result = exc.with_context(context)
        
        assert result is exc  # Should return self
        assert exc.context == context
    
    def test_add_suggestion(self):
        """Test adding suggestions to exception"""
        exc = BaseCustomException("Test error")
        
        result = exc.add_suggestion("Try this")
        
        assert result is exc  # Should return self
        assert "Try this" in exc.suggestions


class TestSpecificExceptions:
    """Test specific exception types"""
    
    def test_validation_error(self):
        """Test validation error creation"""
        field_errors = [{"field": "email", "message": "Invalid format"}]
        exc = ValidationError("Validation failed", field_errors=field_errors)
        
        assert exc.severity == ErrorSeverity.LOW
        assert exc.category == ErrorCategory.VALIDATION
        assert exc.details["field_errors"] == field_errors
        assert "check your input" in exc.user_message.lower()
    
    def test_authentication_error(self):
        """Test authentication error creation"""
        exc = AuthenticationError()
        
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.category == ErrorCategory.AUTHENTICATION
        assert "authentication failed" in exc.message.lower()
        assert "credentials" in exc.user_message.lower()
    
    def test_authorization_error(self):
        """Test authorization error creation"""
        exc = AuthorizationError(required_permission="read:users")
        
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.category == ErrorCategory.AUTHORIZATION
        assert exc.details["required_permission"] == "read:users"
        assert "permission" in exc.user_message.lower()
    
    def test_resource_not_found_error(self):
        """Test resource not found error creation"""
        exc = ResourceNotFoundError("user", "123")
        
        assert exc.severity == ErrorSeverity.LOW
        assert exc.category == ErrorCategory.USER_ERROR
        assert exc.details["resource_type"] == "user"
        assert exc.details["resource_id"] == "123"
        assert "User not found (ID: 123)" == exc.message
    
    def test_external_service_error(self):
        """Test external service error creation"""
        exc = ExternalServiceError("splunk", "search", 503)
        
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.EXTERNAL_SERVICE
        assert exc.details["service_name"] == "splunk"
        assert exc.details["operation"] == "search"
        assert exc.details["status_code"] == 503
        assert exc.retry_after == 60
    
    def test_spl_translation_error(self):
        """Test SPL translation error creation"""
        query = "show me errors"
        exc = SPLTranslationError(query, "Unsupported operation")
        
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.category == ErrorCategory.BUSINESS_LOGIC
        assert exc.details["original_query"] == query
        assert exc.details["translation_failure_reason"] == "Unsupported operation"
        assert "rephrase" in exc.user_message.lower()
    
    def test_query_timeout_error(self):
        """Test query timeout error creation"""
        exc = QueryTimeoutError(30, "search * | head 1000")
        
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.category == ErrorCategory.PERFORMANCE
        assert exc.details["timeout_seconds"] == 30
        assert exc.details["query"] == "search * | head 1000"
        assert "time range" in exc.suggestions[0].lower()
    
    def test_rate_limit_exceeded_error(self):
        """Test rate limit exceeded error creation"""
        exc = RateLimitExceededError(100, 3600, 60)
        
        assert exc.severity == ErrorSeverity.LOW
        assert exc.category == ErrorCategory.BUSINESS_LOGIC
        assert exc.details["limit"] == 100
        assert exc.details["window_seconds"] == 3600
        assert exc.retry_after == 60


class TestErrorFactoryFunctions:
    """Test convenience factory functions for creating errors"""
    
    def test_validation_error_factory(self):
        """Test validation error factory function"""
        exc = validation_error("Invalid email", field="email", value="invalid")
        
        assert isinstance(exc, ValidationError)
        assert exc.message == "Invalid email"
        assert exc.details["field"] == "email"
        assert exc.details["value"] == "invalid"
    
    def test_not_found_error_factory(self):
        """Test not found error factory function"""
        exc = not_found_error("dashboard", "dash123")
        
        assert isinstance(exc, ResourceNotFoundError)
        assert exc.details["resource_type"] == "dashboard"
        assert exc.details["resource_id"] == "dash123"
    
    def test_unauthorized_error_factory(self):
        """Test unauthorized error factory function"""
        exc = unauthorized_error("Token expired")
        
        assert isinstance(exc, AuthenticationError)
        assert exc.message == "Token expired"
    
    def test_forbidden_error_factory(self):
        """Test forbidden error factory function"""
        exc = forbidden_error("Need admin role", "admin")
        
        assert isinstance(exc, AuthorizationError)
        assert exc.message == "Need admin role"
        assert exc.details["required_permission"] == "admin"
    
    def test_service_unavailable_error_factory(self):
        """Test service unavailable error factory function"""
        exc = service_unavailable_error("nlp-service", "translate", 120)
        
        assert isinstance(exc, ExternalServiceError)
        assert exc.details["service_name"] == "nlp-service"
        assert exc.details["operation"] == "translate"
        assert exc.retry_after == 120
    
    def test_rate_limit_error_factory(self):
        """Test rate limit error factory function"""
        exc = rate_limit_error(50, 1800, 30)
        
        assert isinstance(exc, RateLimitExceededError)
        assert exc.details["limit"] == 50
        assert exc.details["window_seconds"] == 1800
        assert exc.retry_after == 30


class TestErrorContext:
    """Test error context functionality"""
    
    def test_error_tracker_create_context(self):
        """Test error context creation from request info"""
        context = ErrorTracker.create_context(
            correlation_id="test-123",
            user_id="user456",
            session_id="session789",
            request_path="/api/v1/test",
            request_method="POST",
            user_agent="TestAgent/1.0",
            ip_address="192.168.1.1",
            custom_field="custom_value"
        )
        
        assert context.correlation_id == "test-123"
        assert context.user_id == "user456"
        assert context.session_id == "session789"
        assert context.request_path == "/api/v1/test"
        assert context.request_method == "POST"
        assert context.user_agent == "TestAgent/1.0"
        assert context.ip_address == "192.168.1.1"
        assert context.additional_context["custom_field"] == "custom_value"
        assert isinstance(context.timestamp, datetime)


class TestErrorMetrics:
    """Test error metrics and monitoring utilities"""
    
    def test_should_alert(self):
        """Test alert determination logic"""
        low_error = BaseCustomException("Low", severity=ErrorSeverity.LOW)
        medium_error = BaseCustomException("Medium", severity=ErrorSeverity.MEDIUM)
        high_error = BaseCustomException("High", severity=ErrorSeverity.HIGH)
        critical_error = BaseCustomException("Critical", severity=ErrorSeverity.CRITICAL)
        
        assert not ErrorMetrics.should_alert(low_error)
        assert not ErrorMetrics.should_alert(medium_error)
        assert ErrorMetrics.should_alert(high_error)
        assert ErrorMetrics.should_alert(critical_error)
    
    def test_get_metric_tags(self):
        """Test metric tags generation"""
        exc = ValidationError("Test error")
        tags = ErrorMetrics.get_metric_tags(exc)
        
        assert tags["error_code"] == exc.error_code
        assert tags["severity"] == exc.severity.value
        assert tags["category"] == exc.category.value
        assert tags["exception_type"] == "ValidationError"
    
    def test_is_retryable(self):
        """Test retry determination logic"""
        # Retryable exceptions
        service_error = ExternalServiceError("test-service")
        timeout_error = QueryTimeoutError(30)
        database_error = DatabaseError("insert")
        
        # Non-retryable exceptions
        validation_error = ValidationError("Invalid input")
        auth_error = AuthenticationError()
        
        assert ErrorMetrics.is_retryable(service_error)
        assert ErrorMetrics.is_retryable(timeout_error)
        assert ErrorMetrics.is_retryable(database_error)
        assert not ErrorMetrics.is_retryable(validation_error)
        assert not ErrorMetrics.is_retryable(auth_error)


class TestExceptionToHttpMapping:
    """Test exception to HTTP response mapping"""
    
    def test_map_exception_to_http(self):
        """Test mapping custom exception to HTTP exception"""
        exc = ValidationError(
            "Invalid input",
            field_errors=[{"field": "email", "message": "Required"}]
        )
        
        http_exc = map_exception_to_http(exc)
        
        assert http_exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "error" in http_exc.detail
        error_detail = http_exc.detail["error"]
        assert error_detail["message"] == exc.message
        assert error_detail["user_message"] == exc.user_message
        assert error_detail["code"] == exc.error_code
        assert error_detail["severity"] == exc.severity.value
        assert error_detail["category"] == exc.category.value
        assert error_detail["error_id"] == exc.error_id
    
    def test_create_detailed_http_exception(self):
        """Test creating detailed HTTP exception"""
        http_exc = create_detailed_http_exception(
            status_code=400,
            message="Bad request",
            user_message="Please fix your input",
            error_code="bad_request",
            details={"field": "email"},
            suggestions=["Check email format"],
            retry_after=30,
            severity="high",
            category="validation"
        )
        
        assert http_exc.status_code == 400
        error = http_exc.detail["error"]
        assert error["message"] == "Bad request"
        assert error["user_message"] == "Please fix your input"
        assert error["code"] == "bad_request"
        assert error["details"] == {"field": "email"}
        assert error["suggestions"] == ["Check email format"]
        assert error["retry_after"] == 30
        assert error["severity"] == "high"
        assert error["category"] == "validation"
        assert "error_id" in error
        assert "timestamp" in error


class TestExceptionHandlers:
    """Test exception handlers functionality"""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object"""
        request = Mock(spec=Request)
        request.url.path = "/api/v1/test"
        request.method = "POST"
        request.headers = {"user-agent": "TestAgent/1.0"}
        request.state = Mock()
        request.state.correlation_id = "test-123"
        request.state.user_id = "user456"
        request.state.session_id = "session789"
        return request
    
    @pytest.mark.asyncio
    async def test_custom_exception_handler(self, mock_request):
        """Test custom exception handler"""
        exc = ValidationError("Test validation error")
        
        response = await custom_exception_handler(mock_request, exc)
        
        assert response.status_code == 422
        content = response.body.decode()
        assert "Test validation error" in content
        assert "validation_error" in content
    
    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, mock_request):
        """Test validation exception handler"""
        # Create a mock RequestValidationError
        errors = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error.missing"
            }
        ]
        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = errors
        
        response = await validation_exception_handler(mock_request, exc)
        
        assert response.status_code == 422
        content = response.body.decode()
        assert "validation" in content.lower()
    
    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """Test HTTP exception handler"""
        from fastapi import HTTPException
        
        exc = HTTPException(status_code=404, detail="Not found")
        
        response = await http_exception_handler(mock_request, exc)
        
        assert response.status_code == 404
        content = response.body.decode()
        assert "Not found" in content
    
    @pytest.mark.asyncio
    async def test_general_exception_handler(self, mock_request):
        """Test general exception handler"""
        exc = ValueError("Unexpected error")
        
        response = await general_exception_handler(mock_request, exc)
        
        assert response.status_code == 500
        content = response.body.decode()
        assert "internal_server_error" in content.lower()


class TestExceptionHandlingMiddleware:
    """Test exception handling middleware"""
    
    def test_middleware_integration(self):
        """Test middleware integration with FastAPI application"""
        app = FastAPI()
        app.add_middleware(ExceptionHandlingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise ValidationError("Test error")
        
        @app.get("/crash")
        async def crash_endpoint():
            raise ValueError("Unexpected error")
        
        client = TestClient(app)
        
        # Test custom exception handling
        response = client.get("/test")
        assert response.status_code == 422
        assert "Test error" in response.text
        
        # Test unexpected exception handling
        response = client.get("/crash")
        assert response.status_code == 500
        assert "internal_server_error" in response.text.lower()


class TestIntegrationTests:
    """Integration tests for the complete exception handling system"""
    
    def test_complete_error_flow(self):
        """Test complete error handling flow from exception to response"""
        # Create an exception with full context
        context = ErrorTracker.create_context(
            correlation_id="integration-test",
            user_id="test-user",
            request_path="/api/v1/test"
        )
        
        exc = ExternalServiceError(
            service_name="splunk",
            operation="search",
            status_code=503
        ).with_context(context).add_suggestion("Check Splunk status")
        
        # Map to HTTP exception
        http_exc = map_exception_to_http(exc)
        
        # Verify complete error structure
        assert http_exc.status_code == 502  # Bad Gateway
        error = http_exc.detail["error"]
        assert error["message"] == exc.message
        assert error["user_message"] == exc.user_message
        assert error["code"] == exc.error_code
        assert error["severity"] == "high"
        assert error["category"] == "external_service"
        assert "Check Splunk status" in error["suggestions"]
        assert error["retry_after"] == 60
        assert "error_id" in error
        
        # Verify metrics
        assert ErrorMetrics.should_alert(exc)
        assert ErrorMetrics.is_retryable(exc)
        
        tags = ErrorMetrics.get_metric_tags(exc)
        assert tags["exception_type"] == "ExternalServiceError"
        assert tags["severity"] == "high"