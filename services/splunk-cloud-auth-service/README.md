# Splunk Cloud Authentication Service

A comprehensive OAuth 2.0, SAML 2.0, and multi-tenant authentication service for Splunk Cloud integration. This service provides secure authentication and authorization for Splunk Cloud instances with support for multiple tenants and authentication providers.

## Features

### Authentication & Authorization
- **OAuth 2.0**: Full OAuth 2.0 implementation with authorization code flow
- **SAML 2.0**: Enterprise SSO integration with major identity providers
- **JWT Tokens**: Secure token-based authentication with refresh capabilities
- **Multi-Tenant**: Complete tenant isolation with per-tenant quotas and configurations
- **PKCE Support**: Enhanced security for public clients

### Cloud Integration
- **Splunk Cloud Support**: Native integration with Splunk Cloud instances
- **Dynamic Registration**: Automatic cloud instance discovery and registration
- **Health Monitoring**: Continuous health checks for cloud endpoints
- **Load Balancing**: Intelligent routing to healthy instances

### Security Features
- **Rate Limiting**: Configurable rate limiting with Redis backing
- **Account Security**: Failed login tracking and account lockout
- **Audit Logging**: Comprehensive security event logging
- **Encryption**: Data encryption at rest and in transit
- **Input Validation**: Comprehensive input sanitization and validation

### Enterprise Features
- **Multi-Tenant Architecture**: Complete tenant isolation and management
- **Resource Quotas**: Per-tenant resource limits and usage tracking
- **Subscription Management**: Flexible subscription plans and billing integration
- **Health Monitoring**: Kubernetes-ready health checks and monitoring

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd services/splunk-cloud-auth-service
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Verify Installation**
   ```bash
   curl http://localhost:8017/health
   ```

### Local Development

1. **Install Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Setup Database**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose up -d postgres redis
   
   # Run migrations (when available)
   alembic upgrade head
   ```

3. **Run Development Server**
   ```bash
   uvicorn app.main:app --reload --port 8017
   ```

## API Documentation

### Authentication Endpoints

#### Register User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "user@example.com",
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "tenant_id": "tenant-uuid"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "securepassword123",
  "tenant_id": "tenant-uuid"
}
```

#### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

### OAuth 2.0 Endpoints

#### Create OAuth Client
```http
POST /api/v1/oauth/clients
Content-Type: application/json

{
  "client_name": "My Application",
  "redirect_uris": ["https://myapp.com/callback"],
  "allowed_scopes": ["openid", "profile", "email"],
  "require_pkce": true
}
```

#### Authorization URL
```http
GET /api/v1/oauth/authorize?response_type=code&client_id=CLIENT_ID&redirect_uri=REDIRECT_URI&scope=openid%20profile&state=STATE&code_challenge=CHALLENGE&code_challenge_method=S256
```

#### Token Exchange
```http
POST /api/v1/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=AUTH_CODE&redirect_uri=REDIRECT_URI&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&code_verifier=VERIFIER
```

### Multi-Tenant Endpoints

#### Create Tenant
```http
POST /api/v1/tenants
Content-Type: application/json

{
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "admin_email": "admin@acme.com",
  "plan": "premium"
}
```

#### Create Cloud Instance
```http
POST /api/v1/tenants/{tenant_id}/cloud-instances
Content-Type: application/json

{
  "instance_name": "Production Splunk Cloud",
  "instance_url": "https://acme.splunkcloud.com",
  "instance_region": "us-east-1",
  "auth_method": "oauth2",
  "client_id": "splunk_client_id",
  "client_secret": "splunk_client_secret"
}
```

## Configuration

### Environment Variables

#### Application Settings
```bash
APP_NAME=splunk-cloud-auth-service
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8017
```

#### Database Configuration
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/7
```

#### JWT Configuration
```bash
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

#### OAuth 2.0 Configuration
```bash
OAUTH_CLIENT_ID=your_oauth_client_id
OAUTH_CLIENT_SECRET=your_oauth_client_secret
OAUTH_AUTHORIZATION_URL=https://auth.scp.splunk.com/oauth2/authorize
OAUTH_TOKEN_URL=https://auth.scp.splunk.com/oauth2/token
OAUTH_REDIRECT_URI=https://yourapp.com/callback
OAUTH_SCOPE=openid profile email
```

#### SAML 2.0 Configuration
```bash
SAML_SP_ENTITY_ID=https://yourapp.com/saml/metadata
SAML_SP_ACS_URL=https://yourapp.com/api/v1/saml/acs
SAML_SP_SLS_URL=https://yourapp.com/api/v1/saml/sls
SAML_IDP_METADATA_URL=https://idp.provider.com/metadata
```

## Security Considerations

### Production Security
- Change default JWT secret key
- Use strong passwords for database connections
- Enable TLS/SSL for all endpoints
- Configure proper CORS origins
- Implement rate limiting
- Regular security audits

### Token Security
- JWT tokens include user and tenant context
- Automatic token rotation and refresh
- Secure token storage in Redis
- Token revocation support

### Multi-Tenant Security
- Complete data isolation between tenants
- Per-tenant resource quotas
- Tenant-specific encryption keys
- Comprehensive audit logging

## Monitoring and Observability

### Health Checks
- `/health` - Basic health check
- `/health/detailed` - Comprehensive health check with dependencies
- `/health/ready` - Kubernetes readiness probe
- `/health/live` - Kubernetes liveness probe

### Metrics
- Prometheus metrics on port 9017
- Authentication success/failure rates
- Token usage statistics
- Tenant usage metrics
- API response times

### Logging
- Structured JSON logging
- Correlation IDs for request tracing
- Security event logging
- Performance metrics

## Development

### Running Tests
```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_oauth_service.py -v
```

### Code Quality
```bash
# Type checking
mypy app/

# Code formatting
black app/
isort app/

# Linting
flake8 app/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Deployment

### Docker Deployment
```bash
# Build image
docker build -t splunk-cloud-auth-service .

# Run container
docker run -p 8017:8017 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  splunk-cloud-auth-service
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloud-auth-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cloud-auth-service
  template:
    metadata:
      labels:
        app: cloud-auth-service
    spec:
      containers:
      - name: cloud-auth-service
        image: splunk-cloud-auth-service:latest
        ports:
        - containerPort: 8017
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: cloud-auth-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8017
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8017
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `/docs` folder
- Review the API documentation at `/api/v1/docs` when running

## Changelog

### Version 1.0.0
- Initial release
- OAuth 2.0 implementation
- SAML 2.0 support
- Multi-tenant architecture
- Splunk Cloud integration
- Comprehensive security features