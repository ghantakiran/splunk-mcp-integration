# API Design Patterns and Standards

## Overview

The Splunk MCP Integration platform follows REST architectural principles and modern API design patterns to ensure consistency, scalability, and developer experience across all microservices. This document outlines the API design standards, patterns, and best practices used throughout the system.

## API Design Principles

### 1. RESTful Design Principles

#### Resource-Oriented Architecture
- URLs represent resources, not actions
- Use HTTP methods to indicate operations
- Maintain stateless communications
- Leverage HTTP status codes appropriately

```http
# Good: Resource-based URLs
GET    /api/v1/users                    # Get all users
POST   /api/v1/users                    # Create new user
GET    /api/v1/users/{id}               # Get specific user
PUT    /api/v1/users/{id}               # Update user
DELETE /api/v1/users/{id}               # Delete user

# Good: Nested resources
GET    /api/v1/users/{id}/dashboards    # Get user's dashboards
POST   /api/v1/users/{id}/dashboards    # Create dashboard for user
GET    /api/v1/dashboards/{id}/panels   # Get dashboard panels

# Bad: Action-based URLs
POST   /api/v1/createUser               # Avoid action verbs
GET    /api/v1/getUserDashboards/{id}   # Avoid mixed patterns
```

#### HTTP Methods and Semantics
```http
# CRUD Operations
GET    /api/v1/resources        # READ (Safe, Idempotent)
POST   /api/v1/resources        # CREATE (Not idempotent)
PUT    /api/v1/resources/{id}   # UPDATE (Idempotent)
PATCH  /api/v1/resources/{id}   # PARTIAL UPDATE (Not idempotent)
DELETE /api/v1/resources/{id}   # DELETE (Idempotent)

# Additional Operations
HEAD   /api/v1/resources/{id}   # Check resource existence
OPTIONS /api/v1/resources       # Get allowed methods
```

### 2. URL Structure Standards

#### Base URL Pattern
```
https://{service-domain}/api/{version}/{resource}
```

#### URL Construction Rules
```http
# Service-specific base URLs
https://api-gateway.splunk-mcp.com/api/v1/
https://nlp-engine.splunk-mcp.com/api/v1/
https://visualization.splunk-mcp.com/api/v1/

# Resource naming conventions
/api/v1/users                    # Collection (plural noun)
/api/v1/users/123                # Individual resource
/api/v1/users/123/dashboards     # Sub-collection
/api/v1/users/123/dashboards/456 # Sub-resource

# Query parameters for filtering/pagination
GET /api/v1/users?role=admin&page=2&size=20
GET /api/v1/dashboards?created_after=2025-01-01&sort=title
```

### 3. API Versioning Strategy

#### URL Path Versioning
```python
from fastapi import FastAPI
from fastapi.routing import APIRouter

# Version 1 router
v1_router = APIRouter(prefix="/api/v1")

@v1_router.get("/users/{user_id}")
async def get_user_v1(user_id: str):
    """Version 1: Basic user information"""
    return await user_service.get_user_basic(user_id)

# Version 2 router
v2_router = APIRouter(prefix="/api/v2")

@v2_router.get("/users/{user_id}")
async def get_user_v2(user_id: str):
    """Version 2: Enhanced user information with preferences"""
    return await user_service.get_user_detailed(user_id)

# Register routers
app = FastAPI(title="Splunk MCP Integration API")
app.include_router(v1_router)
app.include_router(v2_router)
```

#### Header-Based Versioning (Alternative)
```python
from fastapi import Header, HTTPException

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, api_version: str = Header("v1", alias="API-Version")):
    """Handle multiple API versions via headers"""
    if api_version == "v2":
        return await user_service.get_user_detailed(user_id)
    elif api_version == "v1":
        return await user_service.get_user_basic(user_id)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported API version: {api_version}"
        )
```

## Request and Response Patterns

### 1. Standardized Response Format

#### Success Response Structure
```python
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from datetime import datetime

class APIResponse(BaseModel):
    """Standardized API response format"""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": true,
                "data": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "john.doe",
                    "email": "john.doe@company.com"
                },
                "metadata": {
                    "timestamp": "2025-01-22T10:30:00Z",
                    "version": "1.0",
                    "correlation_id": "abc-123-def"
                }
            }
        }

class PaginatedResponse(APIResponse):
    """Paginated response format"""
    data: List[Any]
    pagination: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "success": true,
                "data": [
                    {"id": "1", "name": "Item 1"},
                    {"id": "2", "name": "Item 2"}
                ],
                "pagination": {
                    "page": 1,
                    "size": 20,
                    "total_pages": 5,
                    "total_items": 100,
                    "has_next": true,
                    "has_previous": false
                },
                "metadata": {
                    "timestamp": "2025-01-22T10:30:00Z"
                }
            }
        }
```

#### Error Response Structure
```python
from typing import List

class ErrorDetail(BaseModel):
    """Individual error detail"""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    """Standardized error response format"""
    success: bool = False
    data: Optional[Any] = None
    message: str
    errors: List[ErrorDetail]
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": false,
                "data": null,
                "message": "Validation failed",
                "errors": [
                    {
                        "code": "REQUIRED_FIELD",
                        "message": "Email is required",
                        "field": "email"
                    },
                    {
                        "code": "INVALID_FORMAT",
                        "message": "Password must be at least 8 characters",
                        "field": "password"
                    }
                ],
                "metadata": {
                    "timestamp": "2025-01-22T10:30:00Z",
                    "correlation_id": "xyz-789-ghi"
                }
            }
        }
```

### 2. HTTP Status Code Standards

#### Standard Status Codes Usage
```python
from fastapi import HTTPException, status

# Success codes
status.HTTP_200_OK           # Successful GET, PUT, PATCH, DELETE
status.HTTP_201_CREATED      # Successful POST (resource created)
status.HTTP_202_ACCEPTED     # Async operation accepted
status.HTTP_204_NO_CONTENT   # Successful DELETE (no content)

# Client error codes
status.HTTP_400_BAD_REQUEST      # Invalid request data
status.HTTP_401_UNAUTHORIZED     # Authentication required
status.HTTP_403_FORBIDDEN        # Insufficient permissions
status.HTTP_404_NOT_FOUND        # Resource not found
status.HTTP_409_CONFLICT         # Resource conflict
status.HTTP_422_UNPROCESSABLE_ENTITY  # Validation errors
status.HTTP_429_TOO_MANY_REQUESTS     # Rate limit exceeded

# Server error codes
status.HTTP_500_INTERNAL_SERVER_ERROR  # Generic server error
status.HTTP_502_BAD_GATEWAY           # Upstream service error
status.HTTP_503_SERVICE_UNAVAILABLE   # Service temporarily unavailable
status.HTTP_504_GATEWAY_TIMEOUT       # Upstream timeout

# Custom error handling
class APIErrorHandler:
    @staticmethod
    def validation_error(errors: List[ErrorDetail]):
        """Handle validation errors"""
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse(
                message="Validation failed",
                errors=errors
            ).dict()
        )
    
    @staticmethod
    def not_found(resource_type: str, resource_id: str):
        """Handle resource not found"""
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                message=f"{resource_type} not found",
                errors=[ErrorDetail(
                    code="RESOURCE_NOT_FOUND",
                    message=f"{resource_type} with ID {resource_id} does not exist"
                )]
            ).dict()
        )
    
    @staticmethod
    def forbidden(action: str, resource_type: str):
        """Handle insufficient permissions"""
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse(
                message="Insufficient permissions",
                errors=[ErrorDetail(
                    code="PERMISSION_DENIED",
                    message=f"User lacks permission to {action} {resource_type}"
                )]
            ).dict()
        )
```

### 3. Request Validation Patterns

#### Input Validation with Pydantic
```python
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
import re

class UserCreateRequest(BaseModel):
    """User creation request validation"""
    username: str = Field(..., min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_]+$')
    email: str = Field(..., max_length=255)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    roles: List[str] = Field(default=[], max_items=10)
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password complexity"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('roles')
    def validate_roles(cls, v):
        """Validate role names"""
        valid_roles = {'admin', 'manager', 'analyst', 'viewer'}
        for role in v:
            if role not in valid_roles:
                raise ValueError(f'Invalid role: {role}')
        return v

class QueryCreateRequest(BaseModel):
    """Query creation request validation"""
    natural_language: str = Field(..., min_length=5, max_length=1000)
    auto_execute: bool = Field(default=False)
    save_results: bool = Field(default=True)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('natural_language')
    def validate_query_safety(cls, v):
        """Validate query for safety"""
        dangerous_patterns = [
            r'drop\s+table',
            r'delete\s+from',
            r'truncate\s+table',
            r'alter\s+table',
            r'create\s+table'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Query contains potentially dangerous operations')
        
        return v.strip()
    
    @root_validator
    def validate_auto_execute(cls, values):
        """Validate auto-execute constraints"""
        if values.get('auto_execute') and len(values.get('natural_language', '')) > 500:
            raise ValueError('Auto-execute not allowed for complex queries')
        return values

class PaginationParams(BaseModel):
    """Pagination parameters validation"""
    page: int = Field(default=1, ge=1, le=1000)
    size: int = Field(default=20, ge=1, le=100)
    sort: Optional[str] = Field(default=None, regex=r'^[a-zA-Z0-9_]+(:asc|:desc)?$')
    
    @validator('sort')
    def validate_sort_field(cls, v):
        """Validate sort field"""
        if v:
            field = v.split(':')[0]
            allowed_fields = {'created_at', 'updated_at', 'name', 'title', 'email'}
            if field not in allowed_fields:
                raise ValueError(f'Sorting by {field} is not allowed')
        return v

class FilterParams(BaseModel):
    """Generic filtering parameters"""
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    search: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = Field(default=None, max_items=10)
    
    @validator('search')
    def validate_search_term(cls, v):
        """Validate search term"""
        if v and len(v.strip()) < 2:
            raise ValueError('Search term must be at least 2 characters')
        return v.strip() if v else None
```

## Authentication and Authorization

### 1. JWT Authentication Implementation

#### JWT Token Structure
```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from passlib.context import CryptContext

class JWTManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 30
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        now = datetime.utcnow()
        payload = {
            "sub": user_data["user_id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "roles": user_data["roles"],
            "permissions": user_data["permissions"],
            "session_id": user_data["session_id"],
            "token_type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire_minutes),
            "iss": "splunk-mcp",
            "aud": "splunk-mcp-users"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str, session_id: str) -> str:
        """Create JWT refresh token"""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "session_id": session_id,
            "token_type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.refresh_token_expire_days),
            "iss": "splunk-mcp",
            "aud": "splunk-mcp-users"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="splunk-mcp-users",
                issuer="splunk-mcp"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

# Authentication dependency
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManager = Depends()
) -> Dict[str, Any]:
    """Get current authenticated user"""
    payload = jwt_manager.verify_token(credentials.credentials)
    
    if payload.get("token_type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # Verify session is still active
    session_valid = await verify_session(payload["session_id"])
    if not session_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session no longer valid"
        )
    
    return payload
```

### 2. Role-Based Access Control (RBAC)

#### Permission System Implementation
```python
from enum import Enum
from typing import Set, List

class Permission(Enum):
    # User management
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Dashboard permissions
    DASHBOARD_READ = "dashboard:read"
    DASHBOARD_CREATE = "dashboard:create"
    DASHBOARD_UPDATE = "dashboard:update"
    DASHBOARD_DELETE = "dashboard:delete"
    DASHBOARD_SHARE = "dashboard:share"
    
    # Query permissions
    QUERY_EXECUTE = "query:execute"
    QUERY_SAVE = "query:save"
    QUERY_SHARE = "query:share"
    
    # Alert permissions
    ALERT_READ = "alert:read"
    ALERT_CREATE = "alert:create"
    ALERT_UPDATE = "alert:update"
    ALERT_DELETE = "alert:delete"
    
    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"
    ADMIN_SETTINGS = "admin:settings"

class Role:
    def __init__(self, name: str, permissions: Set[Permission]):
        self.name = name
        self.permissions = permissions

# Predefined roles
ROLES = {
    "admin": Role("admin", {
        Permission.USER_READ, Permission.USER_CREATE, Permission.USER_UPDATE, Permission.USER_DELETE,
        Permission.DASHBOARD_READ, Permission.DASHBOARD_CREATE, Permission.DASHBOARD_UPDATE, 
        Permission.DASHBOARD_DELETE, Permission.DASHBOARD_SHARE,
        Permission.QUERY_EXECUTE, Permission.QUERY_SAVE, Permission.QUERY_SHARE,
        Permission.ALERT_READ, Permission.ALERT_CREATE, Permission.ALERT_UPDATE, Permission.ALERT_DELETE,
        Permission.ADMIN_USERS, Permission.ADMIN_SYSTEM, Permission.ADMIN_SETTINGS
    }),
    
    "manager": Role("manager", {
        Permission.USER_READ,
        Permission.DASHBOARD_READ, Permission.DASHBOARD_CREATE, Permission.DASHBOARD_UPDATE, 
        Permission.DASHBOARD_SHARE,
        Permission.QUERY_EXECUTE, Permission.QUERY_SAVE, Permission.QUERY_SHARE,
        Permission.ALERT_READ, Permission.ALERT_CREATE, Permission.ALERT_UPDATE
    }),
    
    "analyst": Role("analyst", {
        Permission.DASHBOARD_READ, Permission.DASHBOARD_CREATE, Permission.DASHBOARD_UPDATE,
        Permission.QUERY_EXECUTE, Permission.QUERY_SAVE,
        Permission.ALERT_READ, Permission.ALERT_CREATE
    }),
    
    "viewer": Role("viewer", {
        Permission.DASHBOARD_READ,
        Permission.QUERY_EXECUTE
    })
}

class PermissionChecker:
    @staticmethod
    def check_permission(user_roles: List[str], required_permission: Permission) -> bool:
        """Check if user has required permission"""
        user_permissions = set()
        
        for role_name in user_roles:
            role = ROLES.get(role_name)
            if role:
                user_permissions.update(role.permissions)
        
        return required_permission in user_permissions
    
    @staticmethod
    def check_multiple_permissions(user_roles: List[str], 
                                 required_permissions: List[Permission],
                                 require_all: bool = True) -> bool:
        """Check multiple permissions"""
        user_permissions = set()
        
        for role_name in user_roles:
            role = ROLES.get(role_name)
            if role:
                user_permissions.update(role.permissions)
        
        if require_all:
            return all(perm in user_permissions for perm in required_permissions)
        else:
            return any(perm in user_permissions for perm in required_permissions)

# Permission dependency factories
def require_permission(permission: Permission):
    """Dependency factory for permission checking"""
    def permission_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_roles = current_user.get("roles", [])
        
        if not PermissionChecker.check_permission(user_roles, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}"
            )
        
        return current_user
    
    return permission_dependency

def require_any_permission(*permissions: Permission):
    """Dependency factory for checking any of multiple permissions"""
    def permission_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_roles = current_user.get("roles", [])
        
        if not PermissionChecker.check_multiple_permissions(
            user_roles, list(permissions), require_all=False
        ):
            perm_names = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required any of: {perm_names}"
            )
        
        return current_user
    
    return permission_dependency

# Usage in endpoints
@app.get("/api/v1/users")
async def get_users(
    current_user: Dict[str, Any] = Depends(require_permission(Permission.USER_READ))
):
    """Get users - requires USER_READ permission"""
    return await user_service.get_users()

@app.post("/api/v1/dashboards")
async def create_dashboard(
    dashboard_data: DashboardCreateRequest,
    current_user: Dict[str, Any] = Depends(require_permission(Permission.DASHBOARD_CREATE))
):
    """Create dashboard - requires DASHBOARD_CREATE permission"""
    return await dashboard_service.create_dashboard(dashboard_data, current_user["sub"])
```

## Rate Limiting and Throttling

### 1. Rate Limiting Implementation

#### Redis-Based Rate Limiter
```python
import redis
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_window_seconds = 3600  # 1 hour
        self.default_max_requests = 1000
    
    async def check_rate_limit(self, identifier: str, 
                              max_requests: int = None,
                              window_seconds: int = None) -> Dict[str, Any]:
        """Check if request is within rate limit"""
        max_requests = max_requests or self.default_max_requests
        window_seconds = window_seconds or self.default_window_seconds
        
        key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiration
        pipe.expire(key, window_seconds)
        
        results = pipe.execute()
        current_requests = results[1]
        
        # Check if over limit
        if current_requests >= max_requests:
            # Remove the request we just added since it's over limit
            self.redis.zrem(key, str(current_time))
            
            # Calculate reset time
            oldest_request = self.redis.zrange(key, 0, 0, withscores=True)
            reset_time = int(oldest_request[0][1]) + window_seconds if oldest_request else current_time + window_seconds
            
            return {
                "allowed": False,
                "current_requests": current_requests,
                "max_requests": max_requests,
                "window_seconds": window_seconds,
                "reset_time": reset_time,
                "retry_after": reset_time - current_time
            }
        
        return {
            "allowed": True,
            "current_requests": current_requests + 1,
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "remaining_requests": max_requests - (current_requests + 1)
        }

class RateLimitConfig:
    """Rate limit configuration per endpoint"""
    
    ENDPOINTS = {
        # Authentication endpoints
        "/api/v1/auth/login": {"max_requests": 5, "window_seconds": 300},  # 5 per 5 minutes
        "/api/v1/auth/register": {"max_requests": 3, "window_seconds": 3600},  # 3 per hour
        
        # Query endpoints
        "/api/v1/queries": {"max_requests": 100, "window_seconds": 3600},  # 100 per hour
        "/api/v1/queries/execute": {"max_requests": 50, "window_seconds": 3600},  # 50 per hour
        
        # Dashboard endpoints
        "/api/v1/dashboards": {"max_requests": 200, "window_seconds": 3600},  # 200 per hour
        
        # Export endpoints
        "/api/v1/exports": {"max_requests": 20, "window_seconds": 3600},  # 20 per hour
        
        # Admin endpoints
        "/api/v1/admin": {"max_requests": 500, "window_seconds": 3600},  # 500 per hour
    }
    
    # User-based rate limits
    USER_LIMITS = {
        "free": {"max_requests": 100, "window_seconds": 3600},
        "premium": {"max_requests": 1000, "window_seconds": 3600},
        "enterprise": {"max_requests": 10000, "window_seconds": 3600}
    }

# Rate limiting middleware
from fastapi import Request, Response
from fastapi.responses import JSONResponse

class RateLimitMiddleware:
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
    
    async def __call__(self, request: Request, call_next):
        # Get rate limit configuration
        endpoint = request.url.path
        method = request.method
        
        # Skip rate limiting for certain endpoints
        if endpoint in ["/health", "/metrics", "/docs"]:
            return await call_next(request)
        
        # Get endpoint-specific limits
        endpoint_config = RateLimitConfig.ENDPOINTS.get(endpoint, {})
        
        # Get user-specific limits if authenticated
        user_config = {}
        if hasattr(request.state, "user"):
            user_tier = request.state.user.get("tier", "free")
            user_config = RateLimitConfig.USER_LIMITS.get(user_tier, {})
        
        # Use most restrictive limits
        max_requests = min(
            endpoint_config.get("max_requests", 1000),
            user_config.get("max_requests", 1000)
        )
        window_seconds = min(
            endpoint_config.get("window_seconds", 3600),
            user_config.get("window_seconds", 3600)
        )
        
        # Create identifier (IP + user ID if available)
        identifier_parts = [request.client.host]
        if hasattr(request.state, "user"):
            identifier_parts.append(request.state.user["sub"])
        identifier = ":".join(identifier_parts)
        
        # Check rate limit
        rate_limit_result = await self.rate_limiter.check_rate_limit(
            identifier, max_requests, window_seconds
        )
        
        if not rate_limit_result["allowed"]:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Rate limit exceeded",
                    "errors": [{
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Limit: {max_requests} per {window_seconds} seconds"
                    }]
                },
                headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_limit_result["reset_time"]),
                    "Retry-After": str(rate_limit_result["retry_after"])
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining_requests"])
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window_seconds)
        
        return response
```

## API Documentation Standards

### 1. OpenAPI Specification

#### FastAPI Documentation Configuration
```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def create_app() -> FastAPI:
    """Create FastAPI application with comprehensive documentation"""
    app = FastAPI(
        title="Splunk MCP Integration API",
        description="""
        Natural language interface for Splunk Enterprise that enables conversational 
        interactions with Splunk data through advanced NLP processing.
        
        ## Features
        
        * **Natural Language Queries**: Convert plain English to SPL
        * **Visualization Generation**: Create charts and dashboards automatically
        * **Alert Management**: Set up intelligent alerts through conversation
        * **Export Capabilities**: Generate reports in multiple formats
        * **Real-time Collaboration**: Share insights and collaborate on data analysis
        
        ## Authentication
        
        This API uses JWT Bearer token authentication. Include your token in the 
        Authorization header:
        
        ```
        Authorization: Bearer <your-jwt-token>
        ```
        
        ## Rate Limiting
        
        API requests are rate limited based on your subscription tier:
        
        - **Free**: 100 requests per hour
        - **Premium**: 1,000 requests per hour  
        - **Enterprise**: 10,000 requests per hour
        
        Rate limit information is included in response headers.
        """,
        version="1.0.0",
        contact={
            "name": "Splunk MCP Integration Team",
            "url": "https://docs.splunk-mcp.com",
            "email": "support@splunk-mcp.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        servers=[
            {
                "url": "https://api.splunk-mcp.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.splunk-mcp.com", 
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            }
        ]
    )
    
    return app

def custom_openapi_schema(app: FastAPI):
    """Generate custom OpenAPI schema with additional metadata"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://docs.splunk-mcp.com/logo.png"
    }
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /auth/login endpoint"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service authentication"
        }
    }
    
    # Add global security
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema
```

#### Endpoint Documentation Examples
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi import Query, Path, Body

class UserResponse(BaseModel):
    """User information response"""
    id: str = Field(..., description="Unique user identifier", example="123e4567-e89b-12d3-a456-426614174000")
    username: str = Field(..., description="Username", example="john.doe")
    email: str = Field(..., description="Email address", example="john.doe@company.com")
    first_name: str = Field(..., description="First name", example="John")
    last_name: str = Field(..., description="Last name", example="Doe")
    roles: List[str] = Field(..., description="User roles", example=["analyst", "dashboard_viewer"])
    is_active: bool = Field(..., description="Whether user account is active", example=True)
    created_at: str = Field(..., description="Account creation timestamp", example="2025-01-22T10:30:00Z")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john.doe",
                "email": "john.doe@company.com",
                "first_name": "John",
                "last_name": "Doe",
                "roles": ["analyst", "dashboard_viewer"],
                "is_active": True,
                "created_at": "2025-01-22T10:30:00Z"
            }
        }

@app.get(
    "/api/v1/users/{user_id}",
    response_model=APIResponse[UserResponse],
    status_code=200,
    summary="Get user by ID",
    description="""
    Retrieve detailed information about a specific user by their unique identifier.
    
    **Required Permissions:** `user:read`
    
    **Rate Limit:** 1000 requests per hour
    
    This endpoint returns comprehensive user information including profile data,
    roles, and account status. Only users with appropriate permissions can access
    this information.
    """,
    responses={
        200: {
            "description": "User information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "username": "john.doe",
                            "email": "john.doe@company.com",
                            "first_name": "John",
                            "last_name": "Doe",
                            "roles": ["analyst"],
                            "is_active": True,
                            "created_at": "2025-01-22T10:30:00Z"
                        },
                        "metadata": {
                            "timestamp": "2025-01-22T10:30:00Z",
                            "version": "1.0"
                        }
                    }
                }
            }
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "User not found",
                        "errors": [{
                            "code": "USER_NOT_FOUND",
                            "message": "User with ID 123 does not exist"
                        }]
                    }
                }
            }
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Insufficient permissions",
                        "errors": [{
                            "code": "PERMISSION_DENIED",
                            "message": "User lacks permission to read user information"
                        }]
                    }
                }
            }
        }
    },
    tags=["Users"]
)
async def get_user(
    user_id: str = Path(
        ...,
        description="Unique user identifier",
        example="123e4567-e89b-12d3-a456-426614174000",
        regex=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    ),
    include_preferences: bool = Query(
        False,
        description="Include user preferences in response",
        example=False
    ),
    current_user: Dict[str, Any] = Depends(require_permission(Permission.USER_READ))
):
    """Get user by ID with comprehensive documentation"""
    user = await user_service.get_user(user_id, include_preferences)
    
    if not user:
        raise APIErrorHandler.not_found("User", user_id)
    
    return APIResponse(
        data=UserResponse(**user),
        metadata={
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
    )
```

### 2. API Testing Standards

#### Automated API Testing
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

class TestUserAPI:
    """Comprehensive API testing for user endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for testing"""
        token = create_test_jwt_token({
            "sub": "test-user-id",
            "username": "test.user",
            "roles": ["admin"]
        })
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_user_success(self, client, auth_headers):
        """Test successful user retrieval"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        with patch('app.services.user_service.get_user') as mock_get_user:
            mock_get_user.return_value = {
                "id": user_id,
                "username": "john.doe",
                "email": "john.doe@company.com",
                "first_name": "John",
                "last_name": "Doe",
                "roles": ["analyst"],
                "is_active": True,
                "created_at": "2025-01-22T10:30:00Z"
            }
            
            response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["id"] == user_id
            assert data["data"]["username"] == "john.doe"
            assert "metadata" in data
    
    def test_get_user_not_found(self, client, auth_headers):
        """Test user not found scenario"""
        user_id = "nonexistent-user-id"
        
        with patch('app.services.user_service.get_user') as mock_get_user:
            mock_get_user.return_value = None
            
            response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
            
            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False
            assert "USER_NOT_FOUND" in data["errors"][0]["code"]
    
    def test_get_user_unauthorized(self, client):
        """Test unauthorized access"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        response = client.get(f"/api/v1/users/{user_id}")
        
        assert response.status_code == 401
    
    def test_get_user_forbidden(self, client):
        """Test insufficient permissions"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Create token with viewer role (insufficient permissions)
        token = create_test_jwt_token({
            "sub": "test-user-id",
            "username": "test.user", 
            "roles": ["viewer"]
        })
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get(f"/api/v1/users/{user_id}", headers=headers)
        
        assert response.status_code == 403
        data = response.json()
        assert "PERMISSION_DENIED" in data["errors"][0]["code"]
    
    def test_create_user_validation_error(self, client, auth_headers):
        """Test user creation with validation errors"""
        invalid_user_data = {
            "username": "ab",  # Too short
            "email": "invalid-email",  # Invalid format
            "password": "weak"  # Too weak
        }
        
        response = client.post(
            "/api/v1/users",
            json=invalid_user_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0
    
    @pytest.mark.parametrize("page,size,expected_items", [
        (1, 10, 10),
        (2, 10, 5),
        (1, 20, 15)
    ])
    def test_list_users_pagination(self, client, auth_headers, page, size, expected_items):
        """Test user listing with pagination"""
        with patch('app.services.user_service.list_users') as mock_list_users:
            mock_list_users.return_value = {
                "users": [{"id": f"user-{i}"} for i in range(expected_items)],
                "total": 15,
                "page": page,
                "size": size
            }
            
            response = client.get(
                f"/api/v1/users?page={page}&size={size}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == expected_items
            assert data["pagination"]["page"] == page
            assert data["pagination"]["size"] == size

# Performance testing
@pytest.mark.performance
class TestAPIPerformance:
    """Performance testing for API endpoints"""
    
    def test_user_endpoint_performance(self, client, auth_headers):
        """Test user endpoint response time"""
        import time
        
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        start_time = time.time()
        response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response_time < 0.5  # Should respond within 500ms
        assert response.status_code == 200

# Load testing with locust
from locust import HttpUser, task, between

class APILoadTest(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup authentication"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test.user",
            "password": "test.password"
        })
        
        if response.status_code == 200:
            token = response.json()["data"]["access_token"]
            self.headers = {"Authorization": f"Bearer {token}"}
    
    @task(3)
    def get_users(self):
        """Test user listing endpoint"""
        self.client.get("/api/v1/users", headers=self.headers)
    
    @task(2)
    def get_user(self):
        """Test single user endpoint"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        self.client.get(f"/api/v1/users/{user_id}", headers=self.headers)
    
    @task(1)
    def create_query(self):
        """Test query creation endpoint"""
        self.client.post("/api/v1/queries", 
                        json={"natural_language": "show me errors from the last hour"},
                        headers=self.headers)
```

---

*This API design documentation provides comprehensive standards and patterns for building consistent, secure, and well-documented REST APIs across all microservices in the Splunk MCP Integration platform.*

*Last Updated: January 22, 2025*  
*Version: 1.0*