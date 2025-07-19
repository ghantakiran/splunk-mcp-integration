# Report Scheduling Service

A comprehensive microservice for automated report scheduling, generation, and delivery within the Splunk MCP Integration platform. This service enables users to create, manage, and automate Splunk report delivery across multiple channels.

## 🚀 Features

### Core Functionality
- **Flexible Scheduling**: Create report schedules using cron expressions with timezone support
- **Multi-Channel Delivery**: Email, Slack, Teams, webhooks, and file storage delivery options
- **Subscription Management**: User-based subscription system with preferences and notifications
- **Report Generation**: Integration with export services for PDF, Excel, PowerPoint, Word, CSV, JSON, XML, and HTML formats
- **Background Processing**: Asynchronous job processing with Redis-based queuing
- **Analytics & Insights**: Comprehensive analytics for usage patterns, performance metrics, and trends

### Enterprise Features
- **JWT Authentication**: Secure API access with role-based permissions
- **Role-Based Access Control**: Admin, manager, user, and viewer roles with granular permissions
- **Audit Logging**: Complete activity tracking with correlation IDs
- **Rate Limiting**: Configurable rate limiting with Redis-backed sliding window algorithm
- **Health Monitoring**: Kubernetes-ready health checks and Prometheus metrics
- **High Availability**: Production-ready architecture with database and Redis clustering

## 🏗️ Architecture

### Service Components
```
┌─────────────────────────────────────────┐
│         Report Scheduling Service        │
├─────────────────────────────────────────┤
│  API Layer (FastAPI)                   │
│  ├── Schedule Management                │
│  ├── Subscription Management            │
│  ├── Report Management                  │
│  └── Analytics & Metrics                │
├─────────────────────────────────────────┤
│  Service Layer                          │
│  ├── Scheduler Service                  │
│  ├── Subscription Service               │
│  ├── Delivery Service                   │
│  ├── Report Generator                   │
│  └── Analytics Service                  │
├─────────────────────────────────────────┤
│  Data Layer                             │
│  ├── PostgreSQL (Metadata)             │
│  ├── Redis (Caching & Queuing)         │
│  └── File Storage (Reports)             │
└─────────────────────────────────────────┘
```

### Database Schema
- **report_schedules**: Schedule configurations and metadata
- **schedule_executions**: Execution history and results
- **report_subscriptions**: User subscriptions and preferences
- **delivery_attempts**: Delivery tracking and retry logic
- **schedule_analytics**: Performance metrics and usage analytics
- **system_metrics**: System health and performance indicators

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
API_PORT=8015
DEBUG=false

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/report_scheduling
REDIS_URL=redis://localhost:6379/0

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# External Services
NLP_ENGINE_URL=http://localhost:8001
VISUALIZATION_SERVICE_URL=http://localhost:8002
EMAIL_SERVICE_URL=http://localhost:8006
SLACK_BOT_URL=http://localhost:8004
TEAMS_BOT_URL=http://localhost:8005
PDF_EXPORT_SERVICE_URL=http://localhost:8009
POWERPOINT_EXPORT_SERVICE_URL=http://localhost:8011
WORD_EXPORT_SERVICE_URL=http://localhost:8013
HTML_REPORT_SERVICE_URL=http://localhost:8012
CSV_EXPORT_SERVICE_URL=http://localhost:8014
JSON_XML_EXPORT_SERVICE_URL=http://localhost:8015

# Security
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
SERVICE_AUTH_TOKEN=your-service-token
```

### Local Development Setup

1. **Clone and Install Dependencies**
```bash
cd services/report-scheduling-service
pip install -r requirements.txt
```

2. **Database Setup**
```bash
# Initialize PostgreSQL database
psql -U postgres -c "CREATE DATABASE report_scheduling;"
psql -U postgres -d report_scheduling -f scripts/init-db.sql
```

3. **Start Redis**
```bash
redis-server
```

4. **Run the Service**
```bash
python main.py
```

### Docker Setup

1. **Build and Run with Docker Compose**
```bash
docker-compose up -d
```

2. **Initialize Database**
```bash
docker-compose exec postgres psql -U postgres -d report_scheduling -f /docker-entrypoint-initdb.d/init-db.sql
```

## 📡 API Endpoints

### Schedule Management
- `POST /api/v1/schedules/` - Create a new schedule
- `GET /api/v1/schedules/` - List schedules with filtering
- `GET /api/v1/schedules/{id}` - Get schedule by ID
- `PUT /api/v1/schedules/{id}` - Update schedule
- `DELETE /api/v1/schedules/{id}` - Delete schedule
- `POST /api/v1/schedules/{id}/execute` - Execute schedule manually
- `POST /api/v1/schedules/{id}/pause` - Pause schedule
- `POST /api/v1/schedules/{id}/resume` - Resume schedule

### Subscription Management
- `POST /api/v1/subscriptions/` - Create subscription
- `GET /api/v1/subscriptions/` - List subscriptions
- `GET /api/v1/subscriptions/{id}` - Get subscription by ID
- `PUT /api/v1/subscriptions/{id}` - Update subscription
- `DELETE /api/v1/subscriptions/{id}` - Delete subscription
- `POST /api/v1/subscriptions/{id}/test` - Test subscription delivery
- `POST /api/v1/subscriptions/{id}/activate` - Activate subscription
- `POST /api/v1/subscriptions/{id}/deactivate` - Deactivate subscription

### Report Management
- `GET /api/v1/reports/executions` - List report executions
- `GET /api/v1/reports/executions/{id}` - Get execution details
- `POST /api/v1/reports/executions/{id}/retry` - Retry failed execution
- `POST /api/v1/reports/executions/{id}/cancel` - Cancel running execution
- `GET /api/v1/reports/executions/{id}/download` - Download report file
- `DELETE /api/v1/reports/executions/{id}` - Delete execution
- `GET /api/v1/reports/executions/{id}/logs` - Get execution logs
- `GET /api/v1/reports/summary` - Get report summary statistics

### Analytics & Metrics
- `GET /api/v1/analytics/overview` - Get analytics overview
- `GET /api/v1/analytics/schedules` - Get schedule analytics
- `GET /api/v1/analytics/executions` - Get execution analytics
- `GET /api/v1/analytics/deliveries` - Get delivery analytics
- `GET /api/v1/analytics/performance` - Get performance analytics
- `GET /api/v1/analytics/usage` - Get usage analytics
- `GET /api/v1/analytics/trends` - Get trend analysis
- `GET /api/v1/analytics/health` - Get system health metrics
- `POST /api/v1/analytics/reports` - Generate analytics report

### Health & Monitoring
- `GET /health` - Basic health check
- `GET /ready` - Kubernetes readiness probe
- `GET /metrics` - Prometheus metrics endpoint

## 🔧 Configuration

### Schedule Configuration
```json
{
  "name": "Weekly Error Report",
  "description": "Weekly summary of application errors",
  "cron_expression": "0 9 * * 1",
  "timezone": "America/New_York",
  "query": "search index=main error | stats count by source | head 10",
  "query_type": "spl",
  "time_range": {
    "earliest": "-7d",
    "latest": "now"
  },
  "report_format": "pdf",
  "format_options": {
    "template": "professional",
    "include_charts": true
  },
  "visualization_config": {
    "chart_type": "bar",
    "title": "Error Count by Source"
  },
  "delivery_configs": [
    {
      "method": "email",
      "config": {
        "to": "team@company.com",
        "subject": "Weekly Error Report",
        "template": "default"
      }
    }
  ]
}
```

### Subscription Configuration
```json
{
  "schedule_id": "uuid-here",
  "delivery_method": "slack",
  "delivery_config": {
    "channel": "#alerts",
    "format": "summary",
    "include_chart": true
  },
  "active": true,
  "preferences": {
    "notification_on_success": true,
    "notification_on_failure": true,
    "max_file_size_mb": 25
  }
}
```

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/ -v
```

### Run Integration Tests
```bash
pytest tests/test_integration.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### API Testing with cURL
```bash
# Create a schedule
curl -X POST "http://localhost:8015/api/v1/schedules/" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d @examples/schedule.json

# List schedules
curl -X GET "http://localhost:8015/api/v1/schedules/" \
  -H "Authorization: Bearer your-jwt-token"

# Execute schedule manually
curl -X POST "http://localhost:8015/api/v1/schedules/{id}/execute" \
  -H "Authorization: Bearer your-jwt-token"
```

## 📊 Monitoring & Observability

### Health Checks
The service provides comprehensive health monitoring:
- Database connectivity verification
- Redis connectivity verification
- External service health checks
- Queue status monitoring
- Performance metrics tracking

### Metrics
Prometheus-compatible metrics include:
- Schedule execution counts and success rates
- Delivery attempt counts and success rates
- Queue lengths and processing times
- Database and Redis performance metrics
- API endpoint response times and error rates

### Logging
Structured JSON logging with:
- Correlation IDs for request tracking
- User context and security events
- Performance metrics and slow query detection
- Error tracking with stack traces
- Audit trail for all operations

## 🔒 Security

### Authentication & Authorization
- JWT-based authentication with configurable expiration
- Role-based access control (RBAC) with granular permissions
- Service-to-service authentication for internal API calls
- Request validation and input sanitization

### Data Protection
- SQL injection prevention with parameterized queries
- XSS protection with input validation
- CSRF protection for state-changing operations
- Secure file handling with size limits and type validation

### Network Security
- CORS configuration for cross-origin requests
- Security headers (HSTS, X-Frame-Options, etc.)
- Rate limiting to prevent abuse
- Request/response logging for audit trails

## 🚀 Deployment

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: report-scheduling-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: report-scheduling-service
  template:
    metadata:
      labels:
        app: report-scheduling-service
    spec:
      containers:
      - name: report-scheduling-service
        image: report-scheduling-service:latest
        ports:
        - containerPort: 8015
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
            port: 8015
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8015
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Production Considerations
- Use PostgreSQL with read replicas for high availability
- Deploy Redis in cluster mode for scalability
- Configure horizontal pod autoscaling based on CPU and queue length
- Set up monitoring and alerting for critical metrics
- Implement proper backup and disaster recovery procedures

## 🤝 Contributing

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Use type hints throughout the codebase
- Add logging for important operations

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
- [Export Services](../pdf-export-service/README.md) - Document generation services

## 📞 Support

For issues and questions:
1. Check the [troubleshooting guide](docs/troubleshooting.md)
2. Review the [API documentation](http://localhost:8015/docs)
3. Submit issues to the project repository
4. Contact the development team for urgent issues