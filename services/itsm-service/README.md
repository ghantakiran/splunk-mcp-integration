# ITSM Service

A comprehensive ITSM (IT Service Management) tool integration service that provides natural language interfaces and bidirectional synchronization with ServiceNow, Jira, and other ITSM platforms.

## Features

- **Multi-Provider Support**: ServiceNow, Jira, BMC Remedy, Cherwell
- **Bidirectional Synchronization**: Real-time sync between systems
- **Natural Language Processing**: Convert plain English to ITSM operations
- **Workflow Automation**: Custom automation workflows with visual designer
- **Conflict Resolution**: Intelligent conflict detection and resolution
- **Role-Based Access Control**: Granular permissions and security
- **Comprehensive API**: RESTful API with OpenAPI documentation
- **Real-time Monitoring**: Metrics, health checks, and logging

## Quick Start

### Prerequisites

- Docker and Docker Compose
- PostgreSQL 13+
- Redis 6+
- Python 3.9+ (for development)

### Using Docker Compose

1. Clone the repository:
```bash
git clone <repository-url>
cd services/itsm-service
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Update environment variables in `.env` file with your configuration.

4. Start the services:
```bash
docker-compose up -d
```

5. Initialize the database:
```bash
docker-compose exec itsm-service python scripts/init_db.py
```

6. Access the API documentation at http://localhost:8003/docs

### Development Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export DATABASE_URL="postgresql+asyncpg://itsm_user:itsm_password@localhost:5435/itsm_db"
export REDIS_URL="redis://localhost:6382/3"
export JWT_SECRET_KEY="your-secret-key"
```

3. Initialize database:
```bash
python scripts/init_db.py
```

4. Run the development server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

## API Documentation

### Authentication

All API endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Core Endpoints

#### Integrations

- `GET /api/v1/integrations` - List user integrations
- `POST /api/v1/integrations` - Create new integration
- `GET /api/v1/integrations/{id}` - Get integration details
- `PUT /api/v1/integrations/{id}` - Update integration
- `DELETE /api/v1/integrations/{id}` - Delete integration
- `POST /api/v1/integrations/{id}/test` - Test integration connection

#### ServiceNow Operations

- `POST /api/v1/servicenow/{integration_id}/tickets` - Create ServiceNow ticket
- `PUT /api/v1/servicenow/{integration_id}/tickets/{ticket_id}` - Update ticket
- `GET /api/v1/servicenow/{integration_id}/tickets/{ticket_id}` - Get ticket
- `GET /api/v1/servicenow/{integration_id}/tickets` - Search tickets
- `GET /api/v1/servicenow/{integration_id}/tables` - Get available tables

#### Jira Operations

- `POST /api/v1/jira/{integration_id}/tickets` - Create Jira issue
- `PUT /api/v1/jira/{integration_id}/tickets/{ticket_id}` - Update issue
- `GET /api/v1/jira/{integration_id}/tickets/{ticket_id}` - Get issue
- `GET /api/v1/jira/{integration_id}/tickets` - Search issues
- `GET /api/v1/jira/{integration_id}/projects` - Get projects
- `GET /api/v1/jira/{integration_id}/issue-types` - Get issue types

#### Workflows

- `GET /api/v1/workflows` - List workflows
- `POST /api/v1/workflows` - Create workflow
- `GET /api/v1/workflows/{id}` - Get workflow details
- `PUT /api/v1/workflows/{id}` - Update workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow
- `POST /api/v1/workflows/{id}/execute` - Execute workflow
- `GET /api/v1/workflows/{id}/executions` - Get execution history

#### Synchronization

- `POST /api/v1/sync/{integration_id}` - Start synchronization
- `GET /api/v1/sync/{integration_id}/status` - Get sync status
- `GET /api/v1/sync/{integration_id}/conflicts` - Get unresolved conflicts
- `POST /api/v1/sync/{integration_id}/conflicts/{conflict_id}/resolve` - Resolve conflict

#### Analytics

- `GET /api/v1/analytics` - Get ITSM analytics
- `GET /api/v1/analytics/tickets` - Get ticket analytics
- `GET /api/v1/analytics/workflows` - Get workflow analytics
- `GET /api/v1/analytics/sync` - Get synchronization analytics

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_SECRET_KEY` | JWT signing secret | Required |
| `JWT_ALGORITHM` | JWT algorithm | HS256 |
| `JWT_EXPIRATION_SECONDS` | Token expiration time | 3600 |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FORMAT` | Log format (json/text) | json |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | true |
| `METRICS_ENABLED` | Enable metrics collection | true |
| `CORS_ORIGINS` | Allowed CORS origins | ["*"] |

### Database Configuration

The service uses PostgreSQL for persistent storage with the following tables:

- `itsm_integrations` - Integration configurations
- `itsm_tickets` - Synchronized ticket data
- `itsm_workflows` - Workflow definitions
- `itsm_sync_records` - Synchronization history
- `itsm_logs` - Activity logs
- `itsm_metrics` - Performance metrics
- `itsm_users` - User profiles
- `user_itsm_settings` - User preferences

### Redis Configuration

Redis is used for:
- Rate limiting
- Caching
- Session storage
- Background job queues
- Distributed locking

## Integration Setup

### ServiceNow Integration

1. Create a new integration:
```json
{
  "name": "Production ServiceNow",
  "provider": "servicenow",
  "endpoint_url": "https://yourinstance.service-now.com",
  "credentials": {
    "instance": "yourinstance",
    "username": "integration_user",
    "password": "secure_password"
  },
  "field_mappings": {
    "incident": {
      "title": "short_description",
      "description": "description",
      "priority": "priority",
      "status": "state"
    }
  }
}
```

2. Test the connection:
```bash
curl -X POST "http://localhost:8003/api/v1/integrations/{id}/test" \
  -H "Authorization: Bearer <token>"
```

### Jira Integration

1. Create a new integration:
```json
{
  "name": "Project Management Jira",
  "provider": "jira",
  "endpoint_url": "https://yourcompany.atlassian.net",
  "credentials": {
    "username": "user@yourcompany.com",
    "token": "your_api_token"
  }
}
```

2. Configure field mappings based on your Jira setup.

## Workflow Automation

### Workflow Definition

Create automated workflows using JSON configuration:

```json
{
  "name": "Incident Response Workflow",
  "description": "Automated incident response",
  "trigger_type": "event",
  "trigger_config": {
    "event_type": "ticket_created",
    "conditions": [
      {
        "field": "priority",
        "operator": "equals",
        "value": "critical"
      }
    ]
  },
  "steps": [
    {
      "id": "create_jira_issue",
      "type": "create_ticket",
      "config": {
        "provider": "jira",
        "project_key": "OPS",
        "issue_type": "Task",
        "ticket_data": {
          "summary": "Critical Incident: ${trigger.title}",
          "description": "Auto-created from ServiceNow: ${trigger.description}"
        }
      }
    },
    {
      "id": "send_notification",
      "type": "send_notification",
      "config": {
        "channels": ["email", "slack"],
        "recipients": ["ops-team@company.com"],
        "message": "Critical incident created: ${create_jira_issue.key}"
      }
    }
  ]
}
```

### Workflow Execution

Workflows can be triggered:
- Manually via API
- By events (ticket creation, updates)
- On schedule
- By external webhooks

## Synchronization

### Bidirectional Sync

The service supports real-time bidirectional synchronization:

1. **Incremental Sync**: Only syncs changed records
2. **Full Sync**: Complete data synchronization
3. **Conflict Resolution**: Handles concurrent modifications
4. **Field Mapping**: Custom field mapping between systems

### Conflict Resolution

When conflicts occur, the system provides several resolution strategies:

- **Manual Resolution**: User decides which version to keep
- **Automatic Local**: Local changes take precedence
- **Automatic Remote**: Remote changes take precedence
- **Timestamp Based**: Most recent change wins

## Security

### Authentication & Authorization

- JWT-based authentication
- Role-based access control (RBAC)
- Fine-grained permissions
- Session management

### Security Features

- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting
- Audit logging

### Roles and Permissions

| Role | Permissions |
|------|-------------|
| `itsm_admin` | Full access to all features |
| `itsm_manager` | Manage integrations, workflows, resolve conflicts |
| `itsm_analyst` | Create/update tickets, view analytics |
| `itsm_user` | Basic ticket operations |
| `itsm_viewer` | Read-only access |

## Monitoring & Observability

### Health Checks

- `/health` - Basic health check
- `/health/detailed` - Detailed component health
- Database connectivity
- Redis connectivity
- External service health

### Metrics

Prometheus-compatible metrics available at `/metrics`:

- Request counts and latencies
- Database connection pool metrics
- Cache hit/miss ratios
- Sync operation metrics
- Error rates by endpoint

### Logging

Structured JSON logging with:
- Request correlation IDs
- User context
- ITSM operation context
- Performance metrics
- Security events

## Testing

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_servicenow_manager.py
pytest tests/test_jira_manager.py
pytest tests/test_workflows.py
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Service interaction testing
- **API Tests**: Endpoint functionality testing
- **Performance Tests**: Load and stress testing

## Development

### Project Structure

```
app/
├── core/           # Core configuration and utilities
├── models/         # Database models
├── services/       # Business logic services
├── utils/          # Utility functions
└── main.py         # FastAPI application

tests/              # Test suite
scripts/            # Database and deployment scripts
```

### Adding New Providers

1. Create provider manager in `app/services/`
2. Implement required methods (test_connection, create_ticket, etc.)
3. Add provider enum to `ITSMProvider`
4. Update dependency injection in `utils/dependencies.py`
5. Add tests in `tests/`

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## Troubleshooting

### Common Issues

#### Connection Timeouts

```bash
# Check service health
curl http://localhost:8003/health/detailed

# Verify database connectivity
docker-compose exec itsm-service python -c "from app.core.database import check_database_connection; import asyncio; print(asyncio.run(check_database_connection()))"
```

#### Authentication Errors

- Verify JWT secret key configuration
- Check token expiration
- Validate user permissions

#### Sync Conflicts

- Review conflict resolution settings
- Check field mappings
- Verify data consistency

### Log Analysis

```bash
# View application logs
docker-compose logs itsm-service

# Filter for errors
docker-compose logs itsm-service | grep ERROR

# Search for specific operations
docker-compose logs itsm-service | grep "sync_id:"
```

## Performance Tuning

### Database Optimization

- Proper indexing on frequently queried fields
- Connection pooling configuration
- Query optimization

### Redis Configuration

- Memory allocation
- Persistence settings
- Connection pooling

### Application Tuning

- Async/await optimization
- Connection reuse
- Caching strategies

## License

[License information]

## Support

For support and questions:
- Documentation: [Link to docs]
- Issues: [Link to issue tracker]
- Email: [Support email]