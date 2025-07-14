"""
Demo endpoints for testing and demonstrating the exception handling system.

These endpoints showcase different types of exceptions and error responses.
"""

from typing import Optional
from fastapi import APIRouter, Query, Path, Depends
from pydantic import BaseModel

from ....core.exceptions import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ExternalServiceError,
    SPLTranslationError,
    QueryTimeoutError,
    RateLimitExceededError,
    validation_error,
    not_found_error,
    unauthorized_error,
    forbidden_error,
    service_unavailable_error,
    rate_limit_error
)

router = APIRouter()


class DemoRequest(BaseModel):
    """Demo request model for validation testing"""
    name: str
    email: str
    age: int


@router.get("/exceptions/validation")
async def demo_validation_error():
    """Demonstrate validation error with field-specific details"""
    raise validation_error(
        message="Demo validation failed",
        field="demo_field",
        value="invalid_value",
        field_errors=[
            {"field": "email", "message": "Invalid email format"},
            {"field": "age", "message": "Must be between 18 and 120"}
        ]
    )


@router.get("/exceptions/authentication")
async def demo_authentication_error():
    """Demonstrate authentication error"""
    raise unauthorized_error("Demo: Authentication required for this endpoint")


@router.get("/exceptions/authorization")
async def demo_authorization_error():
    """Demonstrate authorization error"""
    raise forbidden_error(
        message="Demo: You need admin privileges",
        required_permission="admin:read"
    )


@router.get("/exceptions/not-found/{resource_id}")
async def demo_not_found_error(resource_id: str = Path(..., description="Resource ID")):
    """Demonstrate resource not found error"""
    raise not_found_error("dashboard", resource_id)


@router.get("/exceptions/external-service")
async def demo_external_service_error():
    """Demonstrate external service error"""
    raise service_unavailable_error(
        service_name="splunk",
        operation="search",
        retry_after=30
    )


@router.get("/exceptions/spl-translation")
async def demo_spl_translation_error():
    """Demonstrate SPL translation error"""
    raise SPLTranslationError(
        query="show me all the things from yesterday",
        reason="Ambiguous time reference and unclear data source"
    )


@router.get("/exceptions/query-timeout")
async def demo_query_timeout_error():
    """Demonstrate query timeout error"""
    raise QueryTimeoutError(
        timeout_seconds=30,
        query="search * | stats count by sourcetype"
    )


@router.get("/exceptions/rate-limit")
async def demo_rate_limit_error():
    """Demonstrate rate limit exceeded error"""
    raise rate_limit_error(
        limit=100,
        window_seconds=3600,
        retry_after=60
    )


@router.get("/exceptions/unexpected")
async def demo_unexpected_error():
    """Demonstrate unexpected error (will be caught by general handler)"""
    # This will trigger the general exception handler
    raise ValueError("This is an unexpected error for testing")


@router.post("/exceptions/pydantic-validation")
async def demo_pydantic_validation_error(request: DemoRequest):
    """Demonstrate Pydantic validation error (built-in FastAPI validation)"""
    # This endpoint will never be reached if validation fails
    # Try calling with invalid data to see Pydantic validation errors
    return {"message": f"Hello {request.name}, validation passed!"}


@router.get("/exceptions/custom-context")
async def demo_custom_context_error():
    """Demonstrate exception with custom context and suggestions"""
    exc = ExternalServiceError(
        service_name="nlp-engine",
        operation="translate_query",
        status_code=503
    )
    
    # Add custom suggestions
    exc.add_suggestion("Check if the NLP service is running")
    exc.add_suggestion("Verify network connectivity")
    exc.add_suggestion("Try a simpler query")
    
    raise exc


@router.get("/exceptions/chained")
async def demo_chained_error():
    """Demonstrate exception with cause chain"""
    try:
        # Simulate a database error
        raise ConnectionError("Failed to connect to database")
    except ConnectionError as e:
        # Wrap it in our custom exception
        raise ExternalServiceError(
            service_name="database",
            operation="connect",
            status_code=503,
            cause=e
        )


@router.get("/exceptions/conditional/{error_type}")
async def demo_conditional_error(
    error_type: str = Path(..., description="Type of error to generate"),
    severity: Optional[str] = Query(None, description="Error severity level")
):
    """Demonstrate different types of errors based on parameters"""
    
    if error_type == "auth":
        raise AuthenticationError("Conditional authentication error")
    elif error_type == "authz":
        raise AuthorizationError("Conditional authorization error")
    elif error_type == "validation":
        raise ValidationError("Conditional validation error")
    elif error_type == "service":
        raise ExternalServiceError("test-service", "test-operation")
    elif error_type == "timeout":
        raise QueryTimeoutError(timeout_seconds=60)
    elif error_type == "rate-limit":
        raise RateLimitExceededError(limit=50, window_seconds=3600, retry_after=30)
    else:
        raise not_found_error("error_type", error_type)


@router.get("/exceptions/success")
async def demo_success_response():
    """Demonstrate a successful response (no exceptions)"""
    return {
        "message": "This endpoint demonstrates a successful response",
        "status": "success",
        "data": {
            "demo": True,
            "exceptions_tested": [
                "validation",
                "authentication", 
                "authorization",
                "not_found",
                "external_service",
                "spl_translation",
                "query_timeout",
                "rate_limit",
                "unexpected"
            ]
        }
    }