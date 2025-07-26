# Splunk Cloud Authentication Service - CLAUDE.md

## Inherits From
- [Main Project Guidelines](../../CLAUDE.md)
- [Shared Standards](../../CLAUDE.md#core-data-models)

## Service Overview
The Splunk Cloud Authentication Service provides secure authentication and authorization for Splunk Cloud instances, supporting OAuth 2.0, SAML 2.0, and token-based authentication. It enables multi-tenant support and seamless integration with various Splunk Cloud deployments.

## Architecture
- **OAuth 2.0 Integration**: Standard OAuth flows for Splunk Cloud authentication
- **SAML 2.0 Support**: Enterprise SSO integration with identity providers
- **Token Management**: JWT-based token generation, validation, and refresh
- **Multi-Tenant Support**: Isolated authentication for different cloud instances
- **Cloud Instance Management**: Dynamic registration and configuration of cloud endpoints

## Development Guidelines

### Code Structure
```
services/splunk-cloud-auth-service/
├── app/
│   ├── api/v1/                    # API endpoints
│   │   ├── endpoints/             # Individual endpoint modules
│   │   │   ├── auth.py            # Authentication endpoints
│   │   │   ├── oauth.py           # OAuth 2.0 flows
│   │   │   ├── saml.py            # SAML 2.0 integration
│   │   │   ├── tokens.py          # Token management
│   │   │   ├── tenants.py         # Tenant management
│   │   │   └── health.py          # Health check endpoints
│   │   └── router.py              # Main API router
│   ├── core/                      # Core functionality
│   │   ├── config.py              # Configuration management
│   │   ├── security.py            # Security utilities
│   │   ├── logging.py             # Structured logging
│   │   └── database.py            # Database configuration
│   ├── models/                    # Data models
│   │   ├── auth_models.py         # Authentication models
│   │   ├── tenant_models.py       # Multi-tenant models
│   │   ├── token_models.py        # Token models
│   │   └── cloud_models.py        # Cloud instance models
│   ├── services/                  # Business logic
│   │   ├── oauth_service.py       # OAuth 2.0 service
│   │   ├── saml_service.py        # SAML 2.0 service
│   │   ├── token_service.py       # Token management service
│   │   ├── tenant_service.py      # Multi-tenant service
│   │   └── cloud_instance_service.py # Cloud instance management
│   ├── utils/                     # Utilities
│   │   ├── auth_utils.py          # Authentication utilities
│   │   ├── encryption.py          # Encryption utilities
│   │   ├── validators.py          # Input validation
│   │   └── rate_limiter.py        # Rate limiting
│   └── main.py                    # FastAPI application
├── tests/                         # Test suites
│   ├── conftest.py                # Test fixtures
│   ├── test_oauth_service.py      # OAuth service tests
│   ├── test_saml_service.py       # SAML service tests
│   ├── test_token_service.py      # Token service tests
│   ├── test_tenant_service.py     # Tenant service tests
│   └── test_api_endpoints.py      # API endpoint tests
├── Dockerfile                     # Container configuration
├── requirements.txt               # Python dependencies
├── docker-compose.yml             # Local development setup
└── README.md                      # Service documentation
```

## Key Features

### OAuth 2.0 Integration
- **Authorization Code Flow**: Standard OAuth flow for web applications
- **Client Credentials Flow**: Service-to-service authentication
- **Refresh Token Support**: Automatic token refresh and rotation
- **Scope Management**: Fine-grained permission control
- **PKCE Support**: Enhanced security for public clients

### SAML 2.0 Support
- **Identity Provider Integration**: Support for major IdPs (Azure AD, Okta, OneLogin)
- **Service Provider Configuration**: Flexible SP metadata configuration
- **Assertion Processing**: Secure SAML assertion validation
- **Attribute Mapping**: Flexible user attribute mapping
- **Single Sign-On (SSO)**: Seamless SSO experience

### Multi-Tenant Architecture
- **Tenant Isolation**: Complete data and configuration isolation
- **Dynamic Tenant Provisioning**: Automated tenant setup and configuration
- **Tenant-Specific Authentication**: Per-tenant auth configurations
- **Resource Management**: Tenant-specific resource allocation
- **Billing Integration**: Usage tracking and billing support

### Cloud Instance Management
- **Dynamic Registration**: Automatic cloud instance discovery
- **Health Monitoring**: Continuous health checks for cloud endpoints
- **Load Balancing**: Intelligent routing to healthy instances
- **Failover Support**: Automatic failover to backup instances
- **Configuration Management**: Centralized cloud instance configuration

## API Endpoints

### Authentication Endpoints
- `POST /api/v1/auth/login` - Standard login authentication
- `POST /api/v1/auth/logout` - Logout and token invalidation
- `POST /api/v1/auth/refresh` - Token refresh
- `GET /api/v1/auth/me` - Current user information

### OAuth 2.0 Endpoints
- `GET /api/v1/oauth/authorize` - OAuth authorization endpoint
- `POST /api/v1/oauth/token` - OAuth token endpoint
- `POST /api/v1/oauth/introspect` - Token introspection
- `POST /api/v1/oauth/revoke` - Token revocation

### SAML 2.0 Endpoints
- `GET /api/v1/saml/metadata` - Service provider metadata
- `POST /api/v1/saml/acs` - Assertion consumer service
- `GET /api/v1/saml/sso` - Single sign-on initiation
- `POST /api/v1/saml/slo` - Single logout

### Tenant Management Endpoints
- `POST /api/v1/tenants` - Create new tenant
- `GET /api/v1/tenants` - List tenants
- `GET /api/v1/tenants/{id}` - Get tenant details
- `PUT /api/v1/tenants/{id}` - Update tenant configuration
- `DELETE /api/v1/tenants/{id}` - Delete tenant

### Cloud Instance Endpoints
- `POST /api/v1/cloud/instances` - Register cloud instance
- `GET /api/v1/cloud/instances` - List cloud instances
- `GET /api/v1/cloud/instances/{id}` - Get instance details
- `PUT /api/v1/cloud/instances/{id}` - Update instance configuration
- `DELETE /api/v1/cloud/instances/{id}` - Deregister instance

## Configuration

### Environment Variables
```bash
# Service Configuration
CLOUD_AUTH_SERVICE_PORT=8017
LOG_LEVEL=INFO
ENVIRONMENT=development

# Database Configuration
DATABASE_URL=postgresql://user:pass@host:5432/cloud_auth_db
REDIS_URL=redis://host:6379/7

# OAuth Configuration
OAUTH_CLIENT_ID=your_oauth_client_id
OAUTH_CLIENT_SECRET=your_oauth_client_secret
OAUTH_AUTHORIZATION_URL=https://oauth.provider.com/auth
OAUTH_TOKEN_URL=https://oauth.provider.com/token

# SAML Configuration
SAML_SP_ENTITY_ID=https://your-app.com/saml/metadata
SAML_SP_ASSERTION_CONSUMER_SERVICE_URL=https://your-app.com/saml/acs
SAML_IDP_METADATA_URL=https://idp.provider.com/metadata

# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Encryption Configuration
ENCRYPTION_KEY=your_encryption_key
ENCRYPTION_ALGORITHM=AES-256-GCM

# Rate Limiting Configuration
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST=20
```

## Security Features

### Token Security
- **JWT with Claims**: Rich token payload with user and tenant information
- **Token Rotation**: Automatic token rotation and refresh
- **Secure Storage**: Encrypted token storage in Redis
- **Expiration Management**: Configurable token expiration policies
- **Revocation Support**: Immediate token revocation capabilities

### Multi-Tenant Security
- **Tenant Isolation**: Complete data isolation between tenants
- **Resource Quotas**: Per-tenant resource limits and quotas
- **Access Control**: Tenant-specific role and permission management
- **Audit Logging**: Comprehensive audit trails per tenant
- **Data Encryption**: Tenant-specific data encryption keys

### Cloud Security
- **TLS 1.3**: Encrypted communication with cloud instances
- **Certificate Validation**: Strict certificate validation
- **API Rate Limiting**: Protection against abuse and DoS attacks
- **Input Validation**: Comprehensive input sanitization
- **CORS Protection**: Proper cross-origin resource sharing controls

## Performance Considerations

### Caching Strategy
- **Token Caching**: Redis-based token caching for performance
- **Tenant Configuration Caching**: Cached tenant configurations
- **Cloud Instance Caching**: Cached cloud instance metadata
- **User Session Caching**: Efficient session management
- **SAML Metadata Caching**: Cached IdP metadata for performance

### Scalability Features
- **Horizontal Scaling**: Stateless service design for easy scaling
- **Connection Pooling**: Efficient database and Redis connections
- **Async Processing**: Non-blocking I/O operations
- **Load Balancing**: Support for multiple service instances
- **Health Checks**: Kubernetes-ready health check endpoints

## Testing Guidelines

### Test Coverage Requirements
- **Unit Tests**: >95% code coverage for all services
- **Integration Tests**: End-to-end authentication flows
- **Security Tests**: Authentication bypass and token security tests
- **Performance Tests**: Load testing for high-throughput scenarios
- **Multi-Tenant Tests**: Tenant isolation and security validation

### Test Patterns
- **Mock OAuth Providers**: Test without external OAuth dependencies
- **SAML Assertion Testing**: Comprehensive SAML flow testing
- **Token Lifecycle Testing**: Complete token management testing
- **Tenant Isolation Testing**: Verify complete tenant separation
- **Error Handling Testing**: Robust error scenario coverage

## Monitoring and Observability

### Metrics Collection
- **Authentication Metrics**: Login success/failure rates, token usage
- **Performance Metrics**: Response times, throughput, error rates
- **Tenant Metrics**: Per-tenant usage statistics and performance
- **Cloud Instance Metrics**: Instance health and connectivity
- **Security Metrics**: Failed authentication attempts, security events

### Logging Strategy
- **Structured Logging**: JSON-based logs with correlation IDs
- **Security Logging**: Comprehensive security event logging
- **Audit Logging**: Complete audit trails for compliance
- **Performance Logging**: Detailed performance tracking
- **Error Logging**: Rich error context and stack traces

## Integration Points

### API Gateway Integration
- **Token Validation**: Seamless token validation for all services
- **User Context**: Rich user context propagation
- **Rate Limiting**: Integrated rate limiting and throttling
- **Audit Logging**: Centralized audit log collection

### Other Service Integration
- **NLP Engine**: Cloud-specific user context and permissions
- **Visualization**: Cloud dashboard authentication and authorization
- **Alert Manager**: Cloud alert configuration and delivery
- **Export Services**: Cloud-specific export permissions and configurations

## Development Workflow

### Local Development
1. Clone repository and navigate to service directory
2. Install dependencies: `pip install -r requirements.txt`
3. Set up local database and Redis
4. Configure environment variables
5. Run service: `uvicorn main:app --reload --port 8017`

### Testing
1. Unit tests: `pytest tests/ --cov=app`
2. Integration tests: `pytest tests/integration/`
3. Security tests: `pytest tests/security/`
4. Performance tests: `pytest tests/performance/`

### Deployment
- Docker containerization with multi-stage builds
- Kubernetes deployment with health checks
- Environment-specific configuration management
- Comprehensive monitoring and alerting

## Recent Implementations

### Session 46 - Cloud Auth Service Foundation (2025-01-24)
- Created service architecture and documentation
- Designed OAuth 2.0 and SAML 2.0 integration patterns
- Established multi-tenant architecture foundation
- Planned cloud instance management capabilities

## Next Steps
1. Implement OAuth 2.0 service with Splunk Cloud integration
2. Add SAML 2.0 support for enterprise identity providers
3. Build multi-tenant management and isolation
4. Create cloud instance discovery and health monitoring
5. Integrate with API Gateway for unified authentication