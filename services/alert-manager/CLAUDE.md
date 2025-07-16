# Alert Management Service - CLAUDE.md

## Inherits From
- [Main Project Guidelines](../../CLAUDE.md)
- [Shared Standards](../../CLAUDE.md#core-data-models)

## Service Overview
The Alert Management service provides comprehensive alerting capabilities for the Splunk MCP integration. It enables users to create alerts using natural language, manage alert rules, handle notifications across multiple channels, and provide intelligent alert correlation and escalation.

## Architecture
- **Alert Creation Engine**: Natural language to alert rule conversion
- **Notification System**: Multi-channel notification delivery (email, Slack, Teams, webhooks)
- **Alert Correlation**: Intelligent grouping and correlation of related alerts
- **Escalation Engine**: Rule-based escalation workflows
- **Alert Dashboard**: Real-time alert monitoring and management

## Development Guidelines

### Code Structure
```
services/alert-manager/
├── app/
│   ├── services/              # Core services
│   │   ├── alert_engine.py         # Alert creation and processing
│   │   ├── notification_service.py # Notification delivery
│   │   ├── correlation_engine.py   # Alert correlation
│   │   ├── escalation_service.py   # Escalation workflows
│   │   └── alert_dashboard.py      # Dashboard management
│   ├── models/                # Data models
│   │   ├── alert.py           # Alert rule and incident models
│   │   ├── notification.py    # Notification models
│   │   └── escalation.py      # Escalation models
│   ├── api/v1/                # API endpoints
│   │   └── endpoints.py       # All alert management endpoints
│   ├── core/                  # Core configuration
│   │   ├── config.py          # Configuration management
│   │   └── logging.py         # Structured logging
│   └── main.py                # FastAPI application
├── tests/                     # Test suites
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container configuration
├── CLAUDE.md                  # This file
└── TASKS.md                   # Service-specific tasks
```

### Key Components

#### Alert Creation Engine
- **Natural Language Processing**: Convert natural language descriptions to alert rules
- **Condition Parsing**: Parse complex alerting conditions and thresholds
- **Schedule Management**: Handle time-based and continuous alerting
- **Template System**: Pre-built alert templates for common scenarios

#### Notification System
- **Multi-Channel Support**: Email, Slack, Teams, webhooks, SMS
- **Template Engine**: Customizable notification templates
- **Delivery Tracking**: Track notification delivery status and failures
- **Rate Limiting**: Prevent notification flooding

#### Alert Correlation
- **Pattern Recognition**: Identify related alerts and group them
- **Root Cause Analysis**: Suggest potential root causes
- **Noise Reduction**: Suppress duplicate and low-priority alerts
- **Intelligent Grouping**: Group alerts by time, source, or pattern

## API Endpoints

### Alert Management
- `POST /alerts/rules` - Create new alert rule
- `GET /alerts/rules` - List alert rules with filtering
- `GET /alerts/rules/{rule_id}` - Get alert rule details
- `PUT /alerts/rules/{rule_id}` - Update alert rule
- `DELETE /alerts/rules/{rule_id}` - Delete alert rule
- `POST /alerts/rules/{rule_id}/test` - Test alert rule

### Alert Incidents
- `GET /alerts/incidents` - List alert incidents
- `GET /alerts/incidents/{incident_id}` - Get incident details
- `POST /alerts/incidents/{incident_id}/acknowledge` - Acknowledge alert
- `POST /alerts/incidents/{incident_id}/resolve` - Resolve alert
- `POST /alerts/incidents/{incident_id}/escalate` - Escalate alert

### Notifications
- `POST /notifications/channels` - Configure notification channel
- `GET /notifications/channels` - List notification channels
- `POST /notifications/test` - Test notification delivery
- `GET /notifications/history` - Notification delivery history

### Alert Templates
- `GET /alerts/templates` - List available alert templates
- `POST /alerts/templates` - Create custom alert template
- `POST /alerts/from-template` - Create alert from template

## Testing Guidelines

### Test Structure
```
tests/
├── test_alert_engine.py        # Alert creation and processing tests
├── test_notification_service.py # Notification delivery tests
├── test_correlation_engine.py   # Alert correlation tests
├── test_escalation_service.py   # Escalation workflow tests
└── integration/                 # Integration tests
```

## Configuration

### Environment Variables
```bash
# Service Configuration
ALERT_SERVICE_PORT=8003
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost:5432/splunk_mcp

# Notification Configuration
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=alerts@example.com
SMTP_PASSWORD=password
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
TEAMS_WEBHOOK_URL=https://outlook.office.com/...

# Alert Processing
ALERT_EVALUATION_INTERVAL=60  # seconds
MAX_ALERTS_PER_RULE=100
CORRELATION_WINDOW=300  # seconds
```

### Dependencies
- FastAPI for API framework
- SQLAlchemy for database operations
- Redis for caching and queuing
- Celery for background tasks
- Jinja2 for template rendering
- Requests for webhook notifications

## Features

### Alert Creation
- **Natural Language Input**: "Alert me when CPU usage exceeds 80% for 5 minutes"
- **Condition Types**: Threshold, statistical, pattern-based, anomaly detection
- **Scheduling**: Real-time, scheduled, or event-driven alerts
- **Flexible Thresholds**: Static, dynamic, or ML-based thresholds

### Notification Channels
- **Email**: Rich HTML templates with charts and data
- **Slack**: Interactive messages with action buttons
- **Microsoft Teams**: Adaptive cards with contextual information
- **Webhooks**: Custom integrations with external systems
- **SMS**: Critical alert notifications via SMS

### Alert Intelligence
- **Correlation**: Group related alerts to reduce noise
- **Suppression**: Prevent alert storms and duplicates
- **Escalation**: Automatic escalation based on time or severity
- **Root Cause**: AI-powered root cause analysis suggestions

## Performance Considerations

### Optimization Strategies
- **Background Processing**: Celery for alert evaluation and notifications
- **Caching**: Redis for alert state and notification templates
- **Batch Processing**: Group notifications to reduce overhead
- **Rate Limiting**: Prevent notification flooding

### Monitoring
- **Alert Metrics**: Creation, firing, and resolution rates
- **Notification Metrics**: Delivery success and failure rates
- **Performance Metrics**: Alert evaluation and processing times
- **System Health**: Service availability and response times

## Security Considerations

### Data Protection
- **Sensitive Data**: Encrypt notification credentials and webhook URLs
- **Access Control**: Role-based access to alert management
- **Audit Logging**: Track all alert and notification activities
- **Input Validation**: Sanitize alert conditions and notification content

### Notification Security
- **Webhook Validation**: Verify webhook signatures and certificates
- **Channel Security**: Use secure connections for all notifications
- **Content Filtering**: Prevent sensitive data leakage in notifications
- **Rate Limiting**: Prevent abuse of notification channels

## Development Workflow

### Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables
3. Start Redis and PostgreSQL
4. Start Celery worker: `celery -A app.worker worker --loglevel=info`
5. Run FastAPI application: `uvicorn main:app --reload`

### Testing
1. Unit tests: `pytest tests/`
2. Integration tests: `pytest tests/integration/`
3. Load tests: `pytest tests/performance/`

## Recent Implementations

This service is being implemented as part of Phase 3 (Enterprise Features) - Milestone 3.3: Alert Management System.

## Next Steps
- Implement natural language alert creation
- Build multi-channel notification system
- Create alert correlation and escalation engines
- Develop alert dashboard and management interface
- Add comprehensive monitoring and analytics