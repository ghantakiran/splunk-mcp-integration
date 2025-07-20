# Secure Sharing Service

A comprehensive microservice for secure resource sharing with expiration, access control, and analytics within the Splunk MCP Integration platform.

## 🚀 Features

### Core Functionality
- **Secure Share Creation**: Create secure shares for reports, dashboards, charts, and other resources
- **Multiple Access Methods**: Link-based, token-based, email invitations, and embedded access
- **Comprehensive Permissions**: Fine-grained permission control (view, download, interact, comment, edit)
- **Expiration Policies**: Time-based, view-based, download-based, and combined expiration strategies
- **Password Protection**: Optional password protection for sensitive shares
- **Domain & User Restrictions**: Restrict access to specific domains or user email addresses

### Security Features
- **JWT Authentication**: Secure API access with role-based permissions
- **Public & Authenticated Sharing**: Support for both public (anonymous) and authenticated access modes
- **Rate Limiting**: Redis-based sliding window rate limiting to prevent abuse
- **Access Logging**: Comprehensive audit trail for all share access attempts
- **Security Validation**: Multi-layer security checks including domain validation and user allowlists
- **Token Security**: Cryptographically secure share tokens with configurable length

### Enterprise Features
- **Role-Based Access Control**: Admin, manager, user, and viewer roles with granular permissions
- **Analytics & Metrics**: Detailed usage analytics and performance metrics
- **High Availability**: Production-ready architecture with Redis and PostgreSQL clustering
- **Health Monitoring**: Kubernetes-ready health checks and Prometheus metrics integration
- **Structured Logging**: JSON-based logging with correlation IDs for request tracing

## 🏗️ Architecture

### Service Components
```
┌─────────────────────────────────────────┐
│         Secure Sharing Service          │
├─────────────────────────────────────────┤
│  API Layer (FastAPI)                   │
│  ├── Share Management                  │
│  ├── Access Control                    │
│  ├── Security Validation               │
│  └── Analytics & Monitoring            │
├─────────────────────────────────────────┤
│  Service Layer                          │
│  ├── Sharing Service                   │
│  ├── Security Service                  │
│  ├── Token Management                  │
│  └── Analytics Service                 │
├─────────────────────────────────────────┤
│  Data Layer                             │
│  ├── PostgreSQL (Metadata)             │
│  ├── Redis (Caching & Rate Limiting)   │
│  └── File Storage (Optional)           │
└─────────────────────────────────────────┘
```

### Database Schema
- **shared_resources**: Core share configurations and metadata
- **share_access_logs**: Comprehensive access tracking and audit trail
- **share_invitations**: Email-based invitation management
- **share_metrics**: Analytics and performance metrics
- **share_configurations**: System-wide configuration settings

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

### Environment Variables
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8016
DEBUG=false

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/secure_sharing
REDIS_URL=redis://localhost:6379/0

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Security
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
SERVICE_AUTH_TOKEN=your-service-token

# Share Configuration
SHARE_BASE_URL=http://localhost:8016
MAX_SHARES_PER_USER=1000
DEFAULT_EXPIRATION_HOURS=168
```

### Local Development Setup

1. **Clone and Install Dependencies**
```bash
cd services/secure-sharing-service
pip install -r requirements.txt
```

2. **Database Setup**
```bash
# Initialize PostgreSQL database
psql -U postgres -c "CREATE DATABASE secure_sharing;"
```

3. **Start Redis**
```bash
redis-server
```

4. **Run the Service**
```bash
python app/main.py
```

The service will be available at:
- API: http://localhost:8016
- Documentation: http://localhost:8016/api/v1/docs
- Health Check: http://localhost:8016/health

### Docker Setup

1. **Build and Run with Docker Compose**
```bash
docker-compose up -d
```

## 📡 API Endpoints

### Share Management
- `POST /api/v1/shares/` - Create a new secure share
- `GET /api/v1/shares/` - List shares with filtering and pagination
- `GET /api/v1/shares/{id}` - Get share details by ID
- `PUT /api/v1/shares/{id}` - Update share configuration
- `DELETE /api/v1/shares/{id}` - Delete share
- `POST /api/v1/shares/{id}/revoke` - Revoke share access

### Share Access
- `POST /api/v1/shares/access` - Access shared resource (public endpoint)
- `POST /api/v1/shares/access/authenticated` - Access shared resource with authentication (enhanced tracking)
- `GET /api/v1/shares/{id}/expiration` - Check expiration status

### Health & Monitoring
- `GET /health` - Basic health check
- `GET /ready` - Kubernetes readiness probe
- `GET /metrics` - Prometheus metrics endpoint

## 🔧 Sharing Modes

### Public Sharing (requires_authentication: false)
- **Anonymous Access**: No user email or authentication required
- **Broader Reach**: Ideal for public dashboards, marketing reports, or external stakeholder access
- **Security Options**: Can still use password protection, domain restrictions, or expiration policies
- **Metrics**: Basic access tracking with IP addresses and user agents
- **Use Cases**: Public dashboards, external reports, marketing materials, customer-facing analytics

### Authenticated Sharing (requires_authentication: true)
- **Email Required**: User must provide a valid email address for access
- **Enhanced Security**: User identity verification and better audit trails
- **Advanced Features**: Domain allowlists, user-specific permissions, and detailed analytics
- **Comprehensive Tracking**: User-level access patterns and behavior analysis
- **Use Cases**: Internal reports, sensitive data, compliance-required sharing, team collaboration

### Hybrid Access Options
- **Public with Optional Auth**: Use `/access` endpoint for public access, `/access/authenticated` for enhanced tracking
- **Progressive Security**: Start with public access, upgrade to authenticated for sensitive features
- **Flexible Permissions**: Different permission levels for public vs authenticated users

## 🔧 Configuration

### Share Creation Examples

#### Authenticated Share (Default)
```json
{
  "resource_type": "report",
  "resource_id": "123e4567-e89b-12d3-a456-426614174000",
  "resource_name": "Weekly Sales Report",
  "permissions": ["view", "download"],
  "requires_authentication": true,
  "expiration_policy": "after_time",
  "expires_at": "2024-08-01T00:00:00Z",
  "password_protected": true,
  "password": "secure123!",
  "allowed_domains": ["company.com"],
  "description": "Weekly sales performance report for authenticated users",
  "notify_on_access": true
}
```

#### Public Share (No Authentication Required)
```json
{
  "resource_type": "dashboard",
  "resource_id": "456e7890-e12b-34d5-a678-901234567890",
  "resource_name": "Public Dashboard",
  "permissions": ["view"],
  "requires_authentication": false,
  "expiration_policy": "after_views",
  "max_views": 1000,
  "password_protected": false,
  "description": "Publicly accessible dashboard for external stakeholders",
  "branding_enabled": true
}
```

#### Public Share with Password Protection
```json
{
  "resource_type": "chart",
  "resource_id": "789e0123-e45b-67d8-a901-234567890123",
  "resource_name": "Public Chart with Password",
  "permissions": ["view", "download"],
  "requires_authentication": false,
  "expiration_policy": "after_time",
  "expires_at": "2024-12-31T23:59:59Z",
  "password_protected": true,
  "password": "public123!",
  "description": "Public chart protected by password only"
}
```

### Share Access Examples

#### Authenticated Share Access
```json
{
  "share_token": "abc123xyz789...",
  "password": "secure123!",
  "user_email": "user@company.com"
}
```

#### Public Share Access (No Authentication)
```json
{
  "share_token": "def456uvw012...",
  "user_email": null
}
```

#### Public Share with Password Access
```json
{
  "share_token": "ghi789rst345...",
  "password": "public123!",
  "user_email": null
}
```

## 🔒 Security

### Authentication & Authorization
- JWT-based authentication with configurable expiration
- Role-based access control (RBAC) with granular permissions
- Service-to-service authentication for internal API calls
- Comprehensive input validation and sanitization

### Data Protection
- Cryptographically secure token generation
- Password hashing using bcrypt
- SQL injection prevention with parameterized queries
- XSS protection with input validation and output encoding

### Access Control
- Domain-based access restrictions
- User email allowlists
- Password protection for sensitive shares
- Comprehensive audit logging for compliance

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### API Testing with cURL

#### Create Shares

```bash
# Create an authenticated share (default)
curl -X POST "http://localhost:8016/api/v1/shares/" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "report",
    "resource_id": "123e4567-e89b-12d3-a456-426614174000",
    "resource_name": "Authenticated Test Report",
    "permissions": ["view"],
    "requires_authentication": true,
    "expiration_policy": "after_time",
    "expires_at": "2024-12-31T23:59:59Z"
  }'

# Create a public share (no authentication required)
curl -X POST "http://localhost:8016/api/v1/shares/" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "dashboard",
    "resource_id": "456e7890-e12b-34d5-a678-901234567890",
    "resource_name": "Public Test Dashboard",
    "permissions": ["view"],
    "requires_authentication": false,
    "expiration_policy": "after_views",
    "max_views": 100
  }'
```

#### Access Shares

```bash
# Access an authenticated share
curl -X POST "http://localhost:8016/api/v1/shares/access" \
  -H "Content-Type: application/json" \
  -d '{
    "share_token": "your-auth-share-token",
    "user_email": "user@example.com"
  }'

# Access a public share (no email required)
curl -X POST "http://localhost:8016/api/v1/shares/access" \
  -H "Content-Type: application/json" \
  -d '{
    "share_token": "your-public-share-token"
  }'

# Access a share with full authentication (enhanced tracking)
curl -X POST "http://localhost:8016/api/v1/shares/access/authenticated" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "share_token": "your-share-token"
  }'
```

## 📊 Monitoring & Observability

### Health Checks
The service provides comprehensive health monitoring:
- Database connectivity verification
- Redis connectivity verification
- Rate limiter status
- Service dependencies health

### Metrics
Prometheus-compatible metrics include:
- Share creation and access counts
- Request duration and success rates
- Rate limiting statistics
- Database and Redis performance metrics

### Logging
Structured JSON logging with:
- Correlation IDs for request tracking
- User context and security events
- Performance metrics and error tracking
- Comprehensive audit trails

## 🚀 Deployment

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-sharing-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: secure-sharing-service
  template:
    metadata:
      labels:
        app: secure-sharing-service
    spec:
      containers:
      - name: secure-sharing-service
        image: secure-sharing-service:latest
        ports:
        - containerPort: 8016
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        livenessProbe:
          httpGet:
            path: /health
            port: 8016
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8016
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Production Considerations
- Use PostgreSQL with read replicas for high availability
- Deploy Redis in cluster mode for scalability
- Configure horizontal pod autoscaling based on CPU and request metrics
- Set up monitoring and alerting for critical metrics
- Implement proper backup and disaster recovery procedures

## 🤝 Contributing

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Use type hints throughout the codebase
- Add structured logging for important operations

### Code Structure
```
app/
├── api/v1/endpoints/     # API endpoint definitions
├── core/                 # Core configuration and database
├── models/              # Pydantic models for requests/responses
├── services/            # Business logic services
└── utils/               # Utility functions and helpers
```

## 📝 License

This project is part of the Splunk MCP Integration platform. Please refer to the main project license for usage terms.

## 🔗 Related Services

- [API Gateway Service](../api-gateway/README.md) - Authentication and routing
- [NLP Engine Service](../nlp-engine/README.md) - Natural language processing
- [Visualization Service](../visualization/README.md) - Chart and dashboard generation
- [Email Service](../email-service/README.md) - Email delivery integration

## 📞 Support

For issues and questions:
1. Check the [API documentation](http://localhost:8016/api/v1/docs)
2. Review the health endpoints for service status
3. Check logs for error details and correlation IDs
4. Contact the development team for urgent issues