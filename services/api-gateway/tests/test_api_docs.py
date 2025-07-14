"""
Tests for API versioning and documentation
"""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from fastapi import FastAPI


class TestAPIVersioning:
    """Test API versioning functionality"""
    
    def test_version_extraction_from_path(self):
        """Test version extraction from URL path"""
        from app.core.versioning import APIVersionMiddleware
        
        middleware = APIVersionMiddleware(Mock())
        
        # Test valid version paths
        assert middleware.extract_version_from_path("/api/v1/auth/login") == ("1.0.0", "/api/auth/login")
        assert middleware.extract_version_from_path("/api/v1.0/auth/login") == ("1.0.0", "/api/auth/login")
        assert middleware.extract_version_from_path("/api/v1.0.0/auth/login") == ("1.0.0", "/api/auth/login")
        
        # Test invalid paths
        assert middleware.extract_version_from_path("/auth/login") is None
        assert middleware.extract_version_from_path("/api/auth/login") is None
    
    def test_version_normalization(self):
        """Test version normalization"""
        from app.core.versioning import APIVersionMiddleware
        
        middleware = APIVersionMiddleware(Mock())
        
        assert middleware.normalize_version("1") == "1.0.0"
        assert middleware.normalize_version("1.0") == "1.0.0"
        assert middleware.normalize_version("1.0.0") == "1.0.0"
        assert middleware.normalize_version("2.1") == "2.1.0"
    
    def test_version_support_checking(self):
        """Test version support validation"""
        from app.core.versioning import APIVersionMiddleware
        
        middleware = APIVersionMiddleware(Mock(), supported_versions=["1.0.0", "1.1.0"])
        
        assert middleware.is_version_supported("1.0.0") is True
        assert middleware.is_version_supported("1.1.0") is True
        assert middleware.is_version_supported("2.0.0") is False
    
    def test_version_comparison(self):
        """Test version comparison functionality"""
        from app.core.versioning import VersionValidator
        
        assert VersionValidator.compare_versions("1.0.0", "1.0.0") == 0
        assert VersionValidator.compare_versions("1.0.0", "1.0.1") == -1
        assert VersionValidator.compare_versions("1.0.1", "1.0.0") == 1
        assert VersionValidator.compare_versions("1.0.0", "2.0.0") == -1
        assert VersionValidator.compare_versions("2.0.0", "1.0.0") == 1
    
    def test_version_format_validation(self):
        """Test version format validation"""
        from app.core.versioning import VersionValidator
        
        # Valid versions
        assert VersionValidator.validate_version_format("1.0.0") is True
        assert VersionValidator.validate_version_format("1.0.0-alpha") is True
        assert VersionValidator.validate_version_format("1.0.0+build.1") is True
        
        # Invalid versions
        assert VersionValidator.validate_version_format("1.0") is False
        assert VersionValidator.validate_version_format("v1.0.0") is False
        assert VersionValidator.validate_version_format("1") is False
    
    def test_deprecation_detection(self):
        """Test version deprecation detection"""
        from app.core.versioning import VersionValidator
        
        assert VersionValidator.is_version_deprecated("1.0.0", "3.0.0") is True
        assert VersionValidator.is_version_deprecated("2.0.0", "3.0.0") is False
        assert VersionValidator.is_version_deprecated("1.5.0", "2.0.0") is False


class TestAPIDocumentation:
    """Test API documentation functionality"""
    
    def test_api_metadata_structure(self):
        """Test API metadata structure"""
        from app.core.docs import get_api_metadata
        
        metadata = get_api_metadata()
        
        assert "title" in metadata
        assert "description" in metadata
        assert "version" in metadata
        assert "contact" in metadata
        assert "license" in metadata
        assert "servers" in metadata
        assert "externalDocs" in metadata
        
        # Check contact information
        assert "name" in metadata["contact"]
        assert "email" in metadata["contact"]
        assert "url" in metadata["contact"]
        
        # Check license information
        assert "name" in metadata["license"]
        assert "url" in metadata["license"]
    
    def test_api_tags_structure(self):
        """Test API tags structure"""
        from app.core.docs import get_api_tags
        
        tags = get_api_tags()
        
        assert isinstance(tags, list)
        assert len(tags) > 0
        
        for tag in tags:
            assert "name" in tag
            assert "description" in tag
        
        # Check for expected tags
        tag_names = [tag["name"] for tag in tags]
        expected_tags = ["Health", "Authentication", "Users", "Chat", "Queries", "Dashboards", "Alerts", "System"]
        
        for expected_tag in expected_tags:
            assert expected_tag in tag_names
    
    def test_security_schemes_structure(self):
        """Test security schemes structure"""
        from app.core.docs import get_security_schemes
        
        schemes = get_security_schemes()
        
        assert "bearerAuth" in schemes
        assert "refreshAuth" in schemes
        
        # Check bearer auth structure
        bearer_auth = schemes["bearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"
        assert "description" in bearer_auth
    
    def test_response_examples_structure(self):
        """Test response examples structure"""
        from app.core.docs import get_response_examples
        
        examples = get_response_examples()
        
        expected_examples = [
            "ValidationError",
            "AuthenticationError", 
            "AuthorizationError",
            "NotFoundError",
            "RateLimitError",
            "InternalServerError"
        ]
        
        for example in expected_examples:
            assert example in examples
            assert "description" in examples[example]
            assert "content" in examples[example]
            assert "application/json" in examples[example]["content"]
    
    def test_version_config_structure(self):
        """Test API version configuration"""
        from app.core.docs import APIVersionConfig
        
        version_info = APIVersionConfig.get_version_info()
        
        assert "current_version" in version_info
        assert "supported_versions" in version_info
        assert "prefix" in version_info
        assert "deprecation_policy" in version_info
        assert "migration_guide" in version_info
        
        assert APIVersionConfig.is_version_supported("1.0.0") is True
        assert APIVersionConfig.is_version_supported("2.0.0") is False


class TestResponseModels:
    """Test response models structure and validation"""
    
    def test_error_response_model(self):
        """Test error response model"""
        from app.models.responses import ErrorResponse, ErrorDetail
        
        error_detail = ErrorDetail(
            message="Test error",
            code="test_error",
            details={"field": "value"}
        )
        
        error_response = ErrorResponse(error=error_detail)
        
        assert error_response.error.message == "Test error"
        assert error_response.error.code == "test_error"
        assert error_response.error.details == {"field": "value"}
    
    def test_health_check_response_model(self):
        """Test health check response model"""
        from app.models.responses import HealthCheckResponse
        from datetime import datetime
        
        health_response = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            environment="test",
            timestamp=datetime.utcnow(),
            services={"database": "healthy"},
            uptime_seconds=3600.0
        )
        
        assert health_response.status == "healthy"
        assert health_response.version == "1.0.0"
        assert health_response.environment == "test"
        assert health_response.services == {"database": "healthy"}
        assert health_response.uptime_seconds == 3600.0
    
    def test_api_version_response_model(self):
        """Test API version response model"""
        from app.models.responses import APIVersionResponse
        
        version_response = APIVersionResponse(
            current_version="1.0.0",
            supported_versions=["1.0.0"],
            prefix="/api/v1",
            deprecation_policy="12 months support",
            migration_guide="https://example.com/migration"
        )
        
        assert version_response.current_version == "1.0.0"
        assert version_response.supported_versions == ["1.0.0"]
        assert version_response.prefix == "/api/v1"
    
    def test_pagination_meta_model(self):
        """Test pagination metadata model"""
        from app.models.responses import PaginationMeta
        
        pagination = PaginationMeta(
            page=1,
            page_size=10,
            total_items=100,
            total_pages=10,
            has_next=True,
            has_previous=False
        )
        
        assert pagination.page == 1
        assert pagination.page_size == 10
        assert pagination.total_items == 100
        assert pagination.total_pages == 10
        assert pagination.has_next is True
        assert pagination.has_previous is False
    
    def test_success_response_model(self):
        """Test generic success response model"""
        from app.models.responses import SuccessResponse
        from pydantic import BaseModel
        
        class TestData(BaseModel):
            id: int
            name: str
        
        test_data = TestData(id=1, name="test")
        success_response = SuccessResponse[TestData](
            data=test_data,
            message="Success"
        )
        
        assert success_response.data.id == 1
        assert success_response.data.name == "test"
        assert success_response.message == "Success"
        assert success_response.timestamp is not None


class TestCommonResponses:
    """Test common HTTP response definitions"""
    
    def test_common_responses_structure(self):
        """Test common responses structure"""
        from app.models.responses import COMMON_RESPONSES
        
        expected_status_codes = [400, 401, 403, 404, 409, 429, 500, 503]
        
        for status_code in expected_status_codes:
            assert status_code in COMMON_RESPONSES
            
            response_def = COMMON_RESPONSES[status_code]
            assert "model" in response_def
            assert "description" in response_def
    
    def test_validation_error_response(self):
        """Test validation error response structure"""
        from app.models.responses import ValidationErrorResponse, ErrorDetail
        
        error_detail = ErrorDetail(
            message="Validation failed",
            code="validation_error",
            details={
                "errors": [
                    {
                        "loc": ["body", "email"],
                        "msg": "field required",
                        "type": "value_error.missing"
                    }
                ]
            }
        )
        
        validation_response = ValidationErrorResponse(error=error_detail)
        
        assert validation_response.error.code == "validation_error"
        assert "errors" in validation_response.error.details
    
    def test_rate_limit_response(self):
        """Test rate limit response structure"""
        from app.models.responses import RateLimitResponse, RateLimitInfo, ErrorDetail
        from datetime import datetime
        
        rate_limit_info = RateLimitInfo(
            limit=100,
            remaining=0,
            reset=datetime.utcnow(),
            retry_after=60
        )
        
        error_detail = ErrorDetail(
            message="Rate limit exceeded",
            code="rate_limit_error"
        )
        
        rate_limit_response = RateLimitResponse(
            error=error_detail,
            rate_limit=rate_limit_info
        )
        
        assert rate_limit_response.error.code == "rate_limit_error"
        assert rate_limit_response.rate_limit.limit == 100
        assert rate_limit_response.rate_limit.remaining == 0
        assert rate_limit_response.rate_limit.retry_after == 60


if __name__ == "__main__":
    # Run basic structural tests
    test_versioning = TestAPIVersioning()
    test_versioning.test_version_extraction_from_path()
    test_versioning.test_version_normalization()
    test_versioning.test_version_support_checking()
    test_versioning.test_version_comparison()
    test_versioning.test_version_format_validation()
    test_versioning.test_deprecation_detection()
    
    test_docs = TestAPIDocumentation()
    test_docs.test_api_metadata_structure()
    test_docs.test_api_tags_structure()
    test_docs.test_security_schemes_structure()
    test_docs.test_response_examples_structure()
    test_docs.test_version_config_structure()
    
    test_responses = TestResponseModels()
    test_responses.test_error_response_model()
    test_responses.test_health_check_response_model()
    test_responses.test_api_version_response_model()
    test_responses.test_pagination_meta_model()
    test_responses.test_success_response_model()
    
    test_common = TestCommonResponses()
    test_common.test_common_responses_structure()
    test_common.test_validation_error_response()
    test_common.test_rate_limit_response()
    
    print("✅ All API versioning and documentation tests passed!")
    print("📝 To run full tests with dependencies:")
    print("   pytest tests/test_api_docs.py -v")