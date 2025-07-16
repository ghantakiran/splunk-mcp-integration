# API Gateway Service - CLAUDE.md

## Inherits From
- [Main Project Guidelines](../../CLAUDE.md)
- [Shared Standards](../../CLAUDE.md#core-data-models)

## Service Overview
The API Gateway service serves as the central entry point for all client requests, providing authentication, authorization, rate limiting, and request routing to appropriate microservices. It includes comprehensive user management, session handling, and security features.

## Architecture
- **Authentication System**: JWT-based authentication with refresh tokens
- **Authorization**: Role-based access control (RBAC) with granular permissions
- **Rate Limiting**: Comprehensive rate limiting with multiple algorithms
- **Request Routing**: Intelligent routing to microservices
- **Security**: Exception handling, audit logging, and security middleware

## Development Guidelines

### Code Structure
```
services/api-gateway/
├── app/
│   ├── api/v1/                # API endpoints
│   │   ├── endpoints/         # Individual endpoint modules
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   ├── users.py       # User management
│   │   │   ├── profile.py     # User profile management
│   │   │   ├── rate_limits.py # Rate limiting management
│   │   │   ├── health.py      # Health check endpoints
│   │   │   └── [others]       # Other endpoint modules
│   │   ├── api.py             # Main API router
│   │   └── deps.py            # Dependencies and middleware
│   ├── core/                  # Core functionality
│   │   ├── config.py          # Configuration management
│   │   ├── security.py        # Security utilities
│   │   ├── exceptions.py      # Custom exceptions
│   │   ├── logging.py         # Structured logging
│   │   ├── rate_limiting.py   # Rate limiting core
│   │   └── docs.py            # API documentation
│   ├── db/                    # Database management
│   │   ├── session.py         # Database sessions
│   │   ├── base.py            # Base models
│   │   └── migrations.py      # Database migrations
│   ├── models/                # Data models
│   │   ├── user.py            # User models
│   │   ├── auth.py            # Authentication models
│   │   ├── profile.py         # Profile models
│   │   └── responses.py       # API response models
│   ├── services/              # Business logic
│   │   ├── auth_service.py    # Authentication service
│   │   └── profile_service.py # Profile service
│   ├── middleware/            # Custom middleware
│   │   └── rate_limiting.py   # Rate limiting middleware
│   └── main.py                # FastAPI application
├── alembic/                   # Database migrations
├── tests/                     # Test suites
└── requirements.txt
```

### Key Components

#### Authentication System
- **JWT Tokens**: Access and refresh token management
- **Password Security**: Bcrypt hashing with strength validation
- **Session Management**: Redis-based session storage
- **Multi-factor Authentication**: Support for MFA (planned)

#### Authorization (RBAC)
- **Role Management**: User roles and permissions
- **Permission Checking**: Granular permission validation
- **Resource Access**: Fine-grained resource access control
- **Audit Logging**: Complete audit trail for security events

#### Rate Limiting
- **3 Algorithms**: Fixed Window, Sliding Window, Token Bucket
- **Flexible Scoping**: Global, per-user, per-IP, per-endpoint
- **Policy Management**: Dynamic policy creation and modification
- **Performance**: >1000 req/s throughput with <10ms latency

#### User Management
- **User Profiles**: Comprehensive user profile management
- **Preferences**: User settings and preferences system
- **Activity Tracking**: User activity analytics
- **Onboarding**: Step-by-step onboarding process

## API Endpoints

### Authentication
- `POST /auth/login` - User authentication
- `POST /auth/logout` - Session termination
- `POST /auth/refresh` - Token refresh
- `POST /auth/register` - User registration (configurable)
- `GET /auth/me` - Current user profile
- `GET /auth/status` - Authentication status

### User Management
- `GET /users` - List users (admin)
- `GET /users/{user_id}` - Get user details
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user (admin)

### Profile Management
- `GET /profile` - Get user profile
- `PUT /profile` - Update profile
- `GET /profile/activity` - User activity analytics
- `POST /profile/export` - Export user data (GDPR)

### Rate Limiting
- `GET /rate-limits/status` - Current rate limit status
- `GET /rate-limits/policies` - List policies (admin)
- `POST /rate-limits/policies` - Create policy (admin)
- `PUT /rate-limits/policies/{name}` - Update policy (admin)
- `DELETE /rate-limits/policies/{name}` - Delete policy (admin)

### System
- `GET /health` - Service health check
- `GET /docs` - API documentation
- `GET /openapi.json` - OpenAPI specification

## Testing Guidelines

### Test Structure
```
tests/
├── test_auth.py               # Authentication tests
├── test_rate_limiting.py      # Rate limiting tests
├── test_profile.py            # Profile management tests
├── test_exceptions.py         # Exception handling tests
├── test_api_docs.py           # API documentation tests
├── conftest.py                # Test configuration
└── performance/               # Performance tests
```

### Testing Patterns
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end API testing
- **Performance Tests**: Rate limiting and load testing
- **Security Tests**: Authentication and authorization testing

## Configuration

### Environment Variables
```bash
# Service Configuration
API_GATEWAY_PORT=8000
LOG_LEVEL=INFO
DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/splunk_mcp
REDIS_URL=redis://localhost:6379

# Authentication
SECRET_KEY=your_secret_key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_MIN_LENGTH=8

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REDIS_URL=redis://localhost:6379

# Security
CORS_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["*"]
```

### Dependencies
- FastAPI for API framework
- SQLAlchemy for ORM
- Alembic for database migrations
- Redis for caching and sessions
- Pydantic for data validation
- PassLib for password hashing

## Security Features

### Authentication Security
- **Password Hashing**: Bcrypt with configurable rounds
- **Token Security**: JWT with proper expiration
- **Session Management**: Secure session handling
- **Brute Force Protection**: Rate limiting on auth endpoints

### Authorization Features
- **Role-Based Access**: User roles and permissions
- **Resource Protection**: Endpoint-level permissions
- **Audit Logging**: Complete security event tracking
- **Data Privacy**: GDPR-compliant data handling

### Rate Limiting Security
- **DDoS Protection**: Multi-layer rate limiting
- **API Abuse Prevention**: Per-endpoint rate limits
- **Graceful Degradation**: Fallback on Redis failure
- **Policy Management**: Dynamic policy updates

## Performance Considerations

### Optimization Strategies
- **Database Optimization**: Connection pooling and query optimization
- **Redis Caching**: Efficient session and rate limit storage
- **Async Processing**: Non-blocking request handling
- **Connection Management**: Proper connection lifecycle

### Monitoring
- **Request Metrics**: Response times and throughput
- **Error Tracking**: Exception monitoring and alerting
- **Security Metrics**: Authentication and authorization events
- **Performance Metrics**: Database and Redis performance

## Troubleshooting

### Common Issues
1. **Authentication Failures**: Check JWT configuration and Redis connection
2. **Rate Limiting Issues**: Verify Redis connectivity and policy configuration
3. **Database Errors**: Check connection string and migration status
4. **Performance Issues**: Monitor database queries and Redis operations

### Debugging Tools
- Structured logging with correlation IDs
- Health check endpoints
- Performance monitoring
- Security event tracking

## Development Workflow

### Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables
3. Start PostgreSQL and Redis
4. Run migrations: `python manage_db.py upgrade`
5. Start FastAPI: `uvicorn main:app --reload`

### Database Management
```bash
# Create migration
python manage_db.py create "migration_name"

# Apply migrations
python manage_db.py upgrade

# Reset database (development only)
python manage_db.py reset
```

### Testing
1. Unit tests: `pytest tests/`
2. Integration tests: `pytest tests/integration/`
3. Performance tests: `python scripts/run_tests.py --performance`

## Recent Implementations

### Session 3 - FastAPI Backend Foundation (2025-07-13)
- FastAPI application structure
- Configuration management
- Security utilities and JWT authentication
- Exception handling and logging

### Session 4 - Async Database Integration (2025-07-13)
- SQLAlchemy async setup
- Base models and relationships
- Database session management
- Model utilities and validation

### Session 5 - Database Migrations (2025-07-13)
- Alembic configuration
- Migration manager
- Database CLI tools
- Initial schema migration

### Session 6 - JWT Authentication (2025-07-13)
- JWT token generation and validation
- Password hashing and strength validation
- Session management with Redis
- Authentication endpoints

### Session 7 - API Versioning and Documentation (2025-07-13)
- API versioning middleware
- OpenAPI documentation
- Response models and standards
- Custom Swagger UI

### Session 8 - Exception Handling (2025-07-13)
- Hierarchical exception system
- Error context management
- Exception handling middleware
- Comprehensive error responses

### Session 9 - User Profile Management (2025-07-13)
- Profile service implementation
- User preferences system
- Activity analytics
- GDPR-compliant data export

### Session 10 - Rate Limiting System (2025-07-14)
- Three rate limiting algorithms
- Policy management system
- Performance optimization
- Comprehensive test suite

## Next Steps
- Multi-factor authentication implementation
- Advanced security features (OAuth2, SAML)
- Service mesh integration
- Advanced monitoring and alerting