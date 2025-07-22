# API Gateway Service Documentation

## Overview

The API Gateway serves as the central entry point for all client requests to the Splunk MCP Integration platform. It provides authentication, authorization, rate limiting, request routing, and monitoring capabilities.

**Base URL**: `/api/v1`  
**Service Port**: 8000  
**Version**: 1.0

## Authentication Endpoints

### POST /auth/login
Authenticate user and obtain JWT access token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "remember_me": "boolean (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "expires_in": 3600,
    "token_type": "Bearer",
    "user": {
      "id": "user_123",
      "username": "john.doe",
      "email": "john@example.com",
      "roles": ["analyst"],
      "permissions": ["read", "write"]
    }
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid credentials
- `401 Unauthorized`: Authentication failed
- `429 Too Many Requests`: Rate limit exceeded

---

### POST /auth/logout
Invalidate current session and tokens.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Successfully logged out"
  }
}
```

---

### POST /auth/refresh
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "expires_in": 3600,
    "token_type": "Bearer"
  }
}
```

---

### POST /auth/register
Register new user account.

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "first_name": "string",
  "last_name": "string",
  "organization": "string (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "user_456",
    "message": "User registered successfully",
    "email_verification_required": true
  }
}
```

---

### POST /auth/verify-email
Verify email address using verification token.

**Request Body:**
```json
{
  "token": "verification_token_here"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Email verified successfully"
  }
}
```

---

### POST /auth/forgot-password
Request password reset email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Password reset email sent"
  }
}
```

---

### POST /auth/reset-password
Reset password using reset token.

**Request Body:**
```json
{
  "token": "reset_token_here",
  "new_password": "new_secure_password"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Password reset successfully"
  }
}
```

## User Management Endpoints

### GET /users/profile
Get current user profile information.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "user_123",
    "username": "john.doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "organization": "Acme Corp",
    "roles": ["analyst"],
    "permissions": ["read", "write"],
    "preferences": {
      "theme": "dark",
      "language": "en",
      "timezone": "UTC"
    },
    "created_at": "2025-01-15T10:30:00Z",
    "last_login": "2025-01-22T08:15:00Z"
  }
}
```

---

### PUT /users/profile
Update current user profile.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "preferences": {
    "theme": "dark",
    "language": "en",
    "timezone": "America/New_York"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Profile updated successfully"
  }
}
```

---

### PUT /users/change-password
Change user password.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "current_password": "current_password",
  "new_password": "new_secure_password"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Password changed successfully"
  }
}
```

---

### GET /users/capabilities
Get current user capabilities and permissions.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "permissions": ["read", "write", "dashboard:create"],
    "splunk_indexes": ["main", "security", "web"],
    "rate_limits": {
      "queries_per_hour": 1000,
      "concurrent_queries": 10
    },
    "features": {
      "advanced_analytics": true,
      "export_pdf": true,
      "email_reports": true
    }
  }
}
```

## System Information Endpoints

### GET /system/info
Get system information and capabilities.

**Response:**
```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "build": "20250122.1",
    "environment": "production",
    "services": {
      "nlp_engine": "healthy",
      "visualization": "healthy",
      "alert_manager": "healthy",
      "email_service": "healthy"
    },
    "features": {
      "natural_language_queries": true,
      "real_time_charts": true,
      "multi_format_export": true,
      "slack_integration": true,
      "teams_integration": true
    },
    "limits": {
      "max_query_length": 1000,
      "max_dashboard_panels": 50,
      "max_concurrent_users": 10000
    }
  }
}
```

---

### GET /system/status
Get real-time system status.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "uptime": "72h 15m 30s",
    "services": {
      "api_gateway": {
        "status": "healthy",
        "response_time": "15ms",
        "requests_per_minute": 1250
      },
      "nlp_engine": {
        "status": "healthy",
        "response_time": "180ms",
        "queries_processed": 1500
      },
      "visualization": {
        "status": "healthy",
        "response_time": "95ms",
        "charts_generated": 890
      }
    },
    "database": {
      "status": "healthy",
      "connections": 45,
      "query_time": "12ms"
    },
    "cache": {
      "status": "healthy",
      "hit_rate": 0.87,
      "memory_usage": "65%"
    }
  }
}
```

## Health Check Endpoints

### GET /health
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-22T10:30:00Z"
}
```

---

### GET /health/detailed
Detailed health check with service dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-22T10:30:00Z",
  "services": {
    "database": {
      "status": "healthy",
      "response_time": "5ms"
    },
    "redis": {
      "status": "healthy",
      "response_time": "2ms"
    },
    "nlp_service": {
      "status": "healthy",
      "response_time": "180ms"
    },
    "splunk_api": {
      "status": "healthy",
      "response_time": "120ms"
    }
  }
}
```

---

### GET /ready
Kubernetes readiness probe endpoint.

**Response:**
```json
{
  "ready": true,
  "timestamp": "2025-01-22T10:30:00Z"
}
```

---

### GET /metrics
Prometheus metrics endpoint.

**Response:** Prometheus format metrics
```
# HELP api_requests_total Total number of API requests
# TYPE api_requests_total counter
api_requests_total{method="GET",endpoint="/users/profile",status="200"} 1500
api_requests_total{method="POST",endpoint="/auth/login",status="200"} 250

# HELP api_request_duration_seconds API request duration
# TYPE api_request_duration_seconds histogram
api_request_duration_seconds_bucket{method="GET",endpoint="/users/profile",le="0.1"} 1200
api_request_duration_seconds_bucket{method="GET",endpoint="/users/profile",le="0.5"} 1500
```

## Rate Limiting

The API Gateway implements rate limiting with the following default limits:

### Per-User Limits
- **Authenticated Users**: 1000 requests/hour
- **Unauthenticated Users**: 100 requests/hour
- **Burst Limit**: 10 requests/second

### Per-Endpoint Limits
- **Authentication**: 10 requests/minute
- **Query Processing**: 60 requests/minute
- **File Export**: 10 requests/hour

### Headers
Rate limit information is returned in response headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when rate limit resets

### Error Response
When rate limit is exceeded:
```json
{
  "success": false,
  "errors": [
    {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "Rate limit exceeded. Try again in 60 seconds.",
      "retry_after": 60
    }
  ]
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | Valid authentication token required |
| `INVALID_CREDENTIALS` | 401 | Username or password incorrect |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `USER_NOT_FOUND` | 404 | User account not found |
| `EMAIL_NOT_VERIFIED` | 403 | Email verification required |
| `WEAK_PASSWORD` | 400 | Password doesn't meet requirements |
| `SERVICE_UNAVAILABLE` | 503 | Backend service temporarily unavailable |

## WebSocket Endpoints

### /ws
WebSocket connection for real-time communication.

**Connection:** `ws://localhost:8000/ws?token=<jwt_token>`

**Message Format:**
```json
{
  "type": "ping|pong|typing|message|error",
  "conversation_id": "conv_123",
  "data": {}
}
```

**Example Messages:**
```json
// Incoming query
{
  "type": "message",
  "conversation_id": "conv_123",
  "data": {
    "query": "show me errors from last hour"
  }
}

// Typing indicator
{
  "type": "typing",
  "conversation_id": "conv_123",
  "data": {
    "user_id": "user_123",
    "typing": true
  }
}
```

## Security Considerations

### Authentication
- JWT tokens expire after 1 hour by default
- Refresh tokens expire after 30 days
- All passwords are hashed using bcrypt with 12 rounds

### Authorization
- Role-based access control (RBAC)
- Permission checks on every API call
- Splunk index-level access control

### Security Headers
All responses include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`  
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

### Input Validation
- All input is validated and sanitized
- SQL injection prevention
- XSS protection
- CSRF protection for state-changing operations

---

*Last Updated: January 22, 2025*
*Service Version: 1.0*