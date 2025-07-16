# Alert Management Service

Comprehensive alerting system for the Splunk MCP integration, providing natural language alert creation, multi-channel notifications, and intelligent alert correlation.

## Features

### 🤖 Natural Language Alert Creation
- Convert natural language descriptions to alert rules
- Support for threshold, statistical, pattern, and anomaly detection
- Automatic SPL query generation via NLP service integration
- Intelligent field mapping and operator extraction

### 📢 Multi-Channel Notifications
- **Email**: Rich HTML notifications with SMTP support
- **Slack**: Interactive messages with severity-based colors
- **Microsoft Teams**: Adaptive cards with contextual information
- **Webhooks**: Custom integrations with external systems
- **SMS**: Critical alert notifications (Twilio integration)

### 🔗 Alert Correlation & Intelligence
- Automatic grouping of related alerts
- Noise reduction through intelligent suppression
- Root cause analysis suggestions
- Time-based and pattern-based correlation

### 📈 Escalation Management
- Multi-level escalation workflows
- Time-based and condition-based triggers
- Automatic reassignment and severity adjustment
- Integration with external ticketing systems

### 📊 Alert Dashboard
- Real-time alert monitoring
- Historical analytics and metrics
- Alert effectiveness reporting
- Management interface for rules and channels

## Quick Start

### Prerequisites
- Python 3.11+
- Redis server
- PostgreSQL database
- Docker (optional)

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/splunk_mcp"
   export REDIS_URL="redis://localhost:6379"
   export NLP_SERVICE_URL="http://localhost:8001"
   ```

3. **Start the service:**
   ```bash
   python -m app.main
   ```

4. **Access the API:**
   - Service: http://localhost:8003
   - Documentation: http://localhost:8003/docs
   - Health check: http://localhost:8003/health

### Docker Deployment

1. **Build the image:**
   ```bash
   docker build -t alert-manager .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8003:8003 \
     -e DATABASE_URL="postgresql+asyncpg://user:pass@db:5432/splunk_mcp" \
     -e REDIS_URL="redis://redis:6379" \
     alert-manager
   ```

## API Endpoints

### Alert Rules
- `POST /api/v1/alerts/rules` - Create alert rule
- `POST /api/v1/alerts/from-natural-language` - Create from natural language
- `GET /api/v1/alerts/rules` - List alert rules
- `GET /api/v1/alerts/rules/{rule_id}` - Get alert rule
- `PUT /api/v1/alerts/rules/{rule_id}` - Update alert rule
- `DELETE /api/v1/alerts/rules/{rule_id}` - Delete alert rule
- `POST /api/v1/alerts/rules/{rule_id}/test` - Test alert rule

### Alert Incidents
- `GET /api/v1/alerts/incidents` - List incidents
- `GET /api/v1/alerts/incidents/{incident_id}` - Get incident
- `POST /api/v1/alerts/incidents/{incident_id}/acknowledge` - Acknowledge
- `POST /api/v1/alerts/incidents/{incident_id}/resolve` - Resolve

### Notification Channels
- `POST /api/v1/notifications/channels` - Create channel
- `GET /api/v1/notifications/channels` - List channels
- `POST /api/v1/notifications/test` - Test notification

### System
- `GET /health` - Health check
- `GET /docs` - API documentation

## Configuration

### Environment Variables

```bash
# Service Configuration
ALERT_SERVICE_PORT=8003
LOG_LEVEL=INFO
DEBUG=false

# Database & Cache
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/splunk_mcp
REDIS_URL=redis://localhost:6379

# External Services
NLP_SERVICE_URL=http://localhost:8001
API_GATEWAY_URL=http://localhost:8000

# Email Configuration
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=alerts@example.com
SMTP_PASSWORD=password
SMTP_FROM_EMAIL=alerts@example.com

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Teams Configuration
TEAMS_WEBHOOK_URL=https://outlook.office.com/...

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
```

### Alert Processing
```bash
ALERT_EVALUATION_INTERVAL=60  # seconds
MAX_ALERTS_PER_RULE=100
CORRELATION_WINDOW=300  # seconds
ALERT_RETENTION_DAYS=90
```

### Notification Settings
```bash
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_RETRY_DELAY=5  # seconds
NOTIFICATION_BATCH_SIZE=50
NOTIFICATION_RATE_LIMIT=100  # per minute
```

## Usage Examples

### Create Alert from Natural Language

```bash
curl -X POST "http://localhost:8003/api/v1/alerts/from-natural-language" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Alert me when CPU usage exceeds 80% for 5 minutes",
    "severity": "high",
    "tags": ["performance", "cpu"],
    "additional_context": {
      "environment": "production"
    }
  }'
```

### Create Notification Channel

```bash
curl -X POST "http://localhost:8003/api/v1/notifications/channels" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Alerts",
    "channel_type": "email",
    "config": {
      "smtp_host": "smtp.company.com",
      "from_email": "alerts@company.com",
      "default_recipients": ["admin@company.com"]
    }
  }'
```

### Test Notification

```bash
curl -X POST "http://localhost:8003/api/v1/notifications/test" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "channel_123",
    "test_recipient": "test@company.com",
    "test_data": {"severity": "high"}
  }'
```

## Natural Language Examples

The service supports various natural language patterns for alert creation:

### Threshold Alerts
- "Alert me when CPU usage exceeds 80%"
- "Notify when disk space falls below 10GB"
- "Alert when response time is greater than 2 seconds"

### Statistical Alerts
- "Alert when average memory usage exceeds 75%"
- "Notify when count of errors is more than 50"
- "Alert when sum of failed requests exceeds 100"

### Pattern Alerts
- "Alert when log level contains 'ERROR'"
- "Notify when message matches pattern 'timeout'"
- "Alert when status code equals 500"

### Anomaly Alerts
- "Alert when there is an anomaly in network traffic"
- "Notify when CPU usage is unusual"
- "Alert when there's a spike in error rates"

## Testing

### Run Tests
```bash
# Unit tests
pytest tests/

# Specific test file
pytest tests/test_alert_engine.py

# With coverage
pytest --cov=app tests/
```

### Test Coverage
- Alert engine functionality
- Notification service delivery
- Correlation engine logic
- API endpoint validation
- Error handling scenarios

## Architecture

### Core Components

1. **Alert Engine** (`app/services/alert_engine.py`)
   - Natural language processing
   - SPL query generation
   - Alert rule evaluation
   - Incident creation

2. **Notification Service** (`app/services/notification_service.py`)
   - Multi-channel delivery
   - Template rendering
   - Delivery tracking
   - Retry logic

3. **Correlation Engine** (`app/services/correlation_engine.py`)
   - Alert grouping
   - Pattern recognition
   - Noise reduction
   - Root cause analysis

4. **Escalation Service** (`app/services/escalation_service.py`)
   - Multi-level workflows
   - Condition evaluation
   - Action execution
   - History tracking

### Data Models

- **Alert Rules**: Configuration and conditions
- **Alert Incidents**: Active alert instances
- **Notification Channels**: Delivery endpoints
- **Escalation Rules**: Workflow definitions
- **Correlation Groups**: Related alert groupings

### Dependencies

- **NLP Engine Service**: Natural language processing
- **API Gateway**: Authentication and authorization
- **Visualization Service**: Dashboard rendering
- **PostgreSQL**: Data persistence
- **Redis**: Caching and queuing

## Development

### Adding New Notification Channels

1. Create channel configuration model in `models/notification.py`
2. Add handler function in `NotificationService`
3. Update channel handlers mapping
4. Add tests for new channel type

### Adding New Alert Patterns

1. Update `alert_patterns` in `AlertEngine`
2. Add pattern recognition logic
3. Update natural language parsing
4. Add test cases for new patterns

## Monitoring

### Health Checks
- Service health: `GET /health`
- Component health: Individual service checks
- Dependency health: Database and Redis connectivity

### Metrics
- Alert creation rates
- Notification delivery success/failure
- Escalation frequency
- Correlation effectiveness

### Logging
- Structured logging with correlation IDs
- Alert lifecycle events
- Notification delivery tracking
- Error and exception logging

## Troubleshooting

### Common Issues

1. **Alert Not Triggering**
   - Check SPL query syntax
   - Verify threshold conditions
   - Review alert rule status

2. **Notification Failures**
   - Verify channel configuration
   - Check network connectivity
   - Review SMTP/webhook settings

3. **Performance Issues**
   - Monitor database queries
   - Check Redis connectivity
   - Review alert evaluation frequency

### Debug Mode
Set `DEBUG=true` for detailed logging and error information.

## Contributing

1. Follow existing code structure and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Use structured logging for all operations
5. Follow security best practices

## Security

- Input validation and sanitization
- Encrypted credential storage
- Rate limiting for API endpoints
- Audit logging for security events
- Secure notification delivery

## License

Part of the Splunk MCP Integration project.