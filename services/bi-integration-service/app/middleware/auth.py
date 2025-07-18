"""
Authentication middleware for BI Integration Service.
"""

import jwt
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""
    
    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        "/health",
        "/health/detailed",
        "/info",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/metrics"
    }
    
    async def dispatch(self, request: Request, call_next):
        """Validate JWT token for protected endpoints."""
        path = request.url.path
        
        # Skip authentication for public endpoints
        if path in self.PUBLIC_ENDPOINTS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization: Optional[str] = request.headers.get("Authorization")
        
        if not authorization:
            logger.warning(
                "Missing Authorization header",
                extra={
                    "path": path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else None
                }
            )
            
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": {
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": "Authentication required",
                        "details": "Missing Authorization header"
                    },
                    "metadata": {
                        "timestamp": "2025-01-18T10:30:00Z",
                        "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                        "version": settings.app_version
                    }
                }
            )
        
        # Parse Bearer token
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid scheme")
        except ValueError:
            logger.warning(
                "Invalid Authorization header format",
                extra={
                    "path": path,
                    "method": request.method,
                    "authorization": authorization[:20] + "..." if len(authorization) > 20 else authorization
                }
            )
            
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN_FORMAT",
                        "message": "Invalid token format",
                        "details": "Expected 'Bearer <token>'"
                    },
                    "metadata": {
                        "timestamp": "2025-01-18T10:30:00Z",
                        "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                        "version": settings.app_version
                    }
                }
            )
        
        # Validate JWT token
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            # Extract user information
            user_id = payload.get("sub")
            roles = payload.get("roles", [])
            permissions = payload.get("permissions", [])
            
            if not user_id:
                raise jwt.InvalidTokenError("Missing user ID in token")
            
            # Store user context in request state
            request.state.user_id = user_id
            request.state.roles = roles
            request.state.permissions = permissions
            request.state.token_payload = payload
            
            logger.debug(
                "Authentication successful",
                extra={
                    "user_id": user_id,
                    "roles": roles,
                    "path": path,
                    "method": request.method
                }
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning(
                "Expired JWT token",
                extra={
                    "path": path,
                    "method": request.method,
                    "token": token[:20] + "..." if len(token) > 20 else token
                }
            )
            
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": {
                        "code": "TOKEN_EXPIRED",
                        "message": "Token has expired",
                        "details": "Please obtain a new token"
                    },
                    "metadata": {
                        "timestamp": "2025-01-18T10:30:00Z",
                        "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                        "version": settings.app_version
                    }
                }
            )
            
        except jwt.InvalidTokenError as e:
            logger.warning(
                f"Invalid JWT token: {e}",
                extra={
                    "path": path,
                    "method": request.method,
                    "token": token[:20] + "..." if len(token) > 20 else token,
                    "error": str(e)
                }
            )
            
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Invalid token",
                        "details": str(e)
                    },
                    "metadata": {
                        "timestamp": "2025-01-18T10:30:00Z",
                        "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                        "version": settings.app_version
                    }
                }
            )
        
        except Exception as e:
            logger.error(
                f"Authentication error: {e}",
                extra={
                    "path": path,
                    "method": request.method,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": {
                        "code": "AUTHENTICATION_ERROR",
                        "message": "Authentication failed",
                        "details": "Internal authentication error"
                    },
                    "metadata": {
                        "timestamp": "2025-01-18T10:30:00Z",
                        "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                        "version": settings.app_version
                    }
                }
            )
        
        # Process request
        return await call_next(request)