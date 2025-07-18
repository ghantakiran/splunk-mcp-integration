# BI Integration Service

A comprehensive Business Intelligence integration service for the Splunk MCP platform, providing seamless integration with popular BI tools including Tableau Server and Microsoft Power BI.

## Features

- **Multi-Provider Support**: Tableau Server, Microsoft Power BI, with extensible architecture for additional providers
- **Natural Language Integration**: Seamless integration with Splunk MCP's natural language processing capabilities
- **Real-time Data Synchronization**: Automated data refresh and synchronization across BI platforms
- **Enterprise Security**: JWT authentication, role-based access control, and comprehensive audit logging
- **Scalable Architecture**: Built with FastAPI, PostgreSQL, and Redis for high performance and scalability
- **Comprehensive API**: RESTful API with automatic OpenAPI documentation
- **Monitoring & Observability**: Prometheus metrics, structured logging, and health checks

## Architecture

The service is built with a microservices architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                    BI Integration Service                       │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                                 │
│  ├── Authentication & Authorization Middleware                 │
│  ├── Rate Limiting & Request Tracking                          │
│  ├── Comprehensive Error Handling                              │
│  └── Prometheus Metrics Collection                             │
├─────────────────────────────────────────────────────────────────┤
│  API Layer (app/api/v1/)                                       │
│  ├── Integration Management Endpoints                          │
│  ├── Data Source Management                                    │
│  ├── Workbook & Dashboard Operations                           │
│  ├── Provider-Specific Endpoints                               │
│  └── Analytics & Reporting                                     │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer (app/services/)                                 │
│  ├── Integration Service                                       │
│  ├── Tableau Manager                                           │
│  ├── Power BI Manager                                          │
│  └── Background Task Processing                                │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer (app/models/)                                      │
│  ├── BI Integration Models                                     │
│  ├── User Management Models                                    │
│  └── Pydantic Response Models                                  │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure (app/core/)                                    │
│  ├── PostgreSQL Database                                       │
│  ├── Redis Cache & Queue                                       │
│  ├── Structured Logging                                        │
│  └── Configuration Management                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd services/bi-integration-service
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   # Run database migrations
   alembic upgrade head
   ```

6. **Start the service**
   ```bash
   python main.py
   ```

### Docker Deployment

1. **Using Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **Access the service**
   - API: http://localhost:8008
   - Documentation: http://localhost:8008/docs
   - Metrics: http://localhost:9008/metrics
   - Redis Commander: http://localhost:8083

## Configuration

### Environment Variables

Key environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_SECRET_KEY` | JWT signing secret | Required |
| `TABLEAU_SERVER_URL` | Tableau Server URL | Optional |
| `POWERBI_TENANT_ID` | Power BI tenant ID | Optional |

See `.env.example` for complete configuration options.

### Provider Configuration

#### Tableau Server

```bash
TABLEAU_SERVER_URL=https://your-tableau-server.com
TABLEAU_SITE_ID=your-site-id
TABLEAU_USERNAME=your-username
TABLEAU_PASSWORD=your-password
# OR use Personal Access Token
TABLEAU_TOKEN_NAME=your-token-name
TABLEAU_TOKEN_VALUE=your-token-value
```

#### Microsoft Power BI

```bash
POWERBI_TENANT_ID=your-tenant-id
POWERBI_CLIENT_ID=your-client-id
POWERBI_CLIENT_SECRET=your-client-secret
```

## API Documentation

### Authentication

All API endpoints require JWT authentication. Include the token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

### Core Endpoints

#### Integrations

- `GET /api/v1/integrations` - List user integrations
- `POST /api/v1/integrations` - Create new integration
- `GET /api/v1/integrations/{id}` - Get integration details
- `PUT /api/v1/integrations/{id}` - Update integration
- `DELETE /api/v1/integrations/{id}` - Delete integration
- `POST /api/v1/integrations/{id}/test` - Test integration connection
- `POST /api/v1/integrations/{id}/sync` - Synchronize integration data

#### Tableau

- `GET /api/v1/tableau/projects` - List Tableau projects
- `GET /api/v1/tableau/workbooks` - List Tableau workbooks
- `GET /api/v1/tableau/data-sources` - List Tableau data sources
- `POST /api/v1/tableau/workbooks/{id}/publish` - Publish workbook
- `POST /api/v1/tableau/data-sources/{id}/refresh` - Refresh data source

#### Power BI

- `GET /api/v1/powerbi/workspaces` - List Power BI workspaces
- `GET /api/v1/powerbi/reports` - List Power BI reports
- `GET /api/v1/powerbi/datasets` - List Power BI datasets
- `POST /api/v1/powerbi/datasets/{id}/refresh` - Refresh dataset

### Example Usage

```bash
# Create a new Tableau integration
curl -X POST "http://localhost:8008/api/v1/integrations" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Tableau",
    "provider": "tableau",
    "server_url": "https://tableau.company.com",
    "site_id": "production",
    "credentials": {
      "username": "service_account",
      "password": "secure_password"
    }
  }'

# Test the integration
curl -X POST "http://localhost:8008/api/v1/integrations/{id}/test" \
  -H "Authorization: Bearer <token>"

# Synchronize integration data
curl -X POST "http://localhost:8008/api/v1/integrations/{id}/sync" \
  -H "Authorization: Bearer <token>"
```

## Development

### Project Structure

```
services/bi-integration-service/
├── app/
│   ├── api/v1/                 # API endpoints
│   ├── core/                   # Core infrastructure
│   ├── middleware/             # Custom middleware
│   ├── models/                 # Data models
│   ├── services/               # Business logic
│   └── utils/                  # Utilities
├── tests/                      # Test suite
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Multi-container setup
└── README.md                   # This file
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_integrations.py -v
```

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/
mypy app/
```

## Monitoring & Observability

### Metrics

The service exposes Prometheus metrics at `/metrics`:

- Request count and duration
- Active connections
- Integration status
- Provider-specific metrics

### Logging

Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2025-01-18T10:30:00Z",
  "level": "INFO",
  "message": "Integration created successfully",
  "correlation_id": "uuid",
  "user_id": "user123",
  "integration_id": "int456",
  "provider": "tableau"
}
```

### Health Checks

- `/health` - Basic health check
- `/health/detailed` - Detailed health with dependency status

## Security

### Authentication & Authorization

- JWT-based authentication
- Role-based access control
- Request rate limiting
- Comprehensive audit logging

### Data Protection

- Encrypted credential storage
- Input validation and sanitization
- SQL injection prevention
- XSS protection

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check PostgreSQL connection
   psql -h localhost -p 5432 -U biservice -d biservice
   ```

2. **Redis Connection Issues**
   ```bash
   # Check Redis connection
   redis-cli -h localhost -p 6379 ping
   ```

3. **Authentication Errors**
   - Verify JWT secret key configuration
   - Check token expiration
   - Validate user permissions

4. **Provider Connection Issues**
   - Verify provider credentials
   - Check network connectivity
   - Review provider-specific logs

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true python main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is part of the Splunk MCP Integration platform.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the API documentation
- Check application logs
- Contact the development team