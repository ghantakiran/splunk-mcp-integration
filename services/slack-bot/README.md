# Slack Bot Service

A comprehensive Slack integration for the Splunk MCP (Model Context Protocol) project that enables natural language interactions with Splunk data through Slack.

## Features

### Core Functionality
- **Natural Language Processing**: Convert plain English queries to SPL
- **Real-time Interaction**: Instant responses via mentions, DMs, and slash commands  
- **Visualization Support**: Automatic chart generation and sharing
- **Alert Management**: Create and manage Splunk alerts through natural language
- **Session Management**: Contextual conversations with history tracking
- **Multi-Channel Support**: Works in channels, groups, and direct messages

### Slack Integrations
- **App Mentions**: `@splunk-bot show me errors from last hour`
- **Direct Messages**: Private query execution and results
- **Slash Commands**: `/splunk`, `/splunk-help`, `/splunk-status`
- **Interactive Components**: Buttons and menus for enhanced UX
- **Rich Formatting**: Blocks, attachments, and formatted responses

### Enterprise Features
- **Authentication & Authorization**: Slack-based user authentication with Splunk RBAC
- **Rate Limiting**: Configurable per-user request limits
- **Session Management**: Conversation context and history tracking
- **Audit Logging**: Comprehensive logging of all interactions
- **Health Monitoring**: Service health checks and metrics

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Slack Bot Service                            │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Application (Port 8004)                               │
│  ├── Slack Event Handler                                       │
│  ├── Slash Command Processor                                   │
│  ├── Interactive Component Handler                             │
│  └── Health Check Endpoints                                    │
├─────────────────────────────────────────────────────────────────┤
│  Core Services                                                 │
│  ├── Splunk Service (Backend Communication)                    │
│  ├── User Service (Authentication & Context)                   │
│  ├── Session Service (Conversation Management)                 │
│  └── Rate Limiter (Request Throttling)                         │
├─────────────────────────────────────────────────────────────────┤
│  Utilities                                                     │
│  ├── Message Formatter (Slack Block Kit)                       │
│  ├── Authentication (Slack Signature Verification)             │
│  └── Logging (Structured Logging)                              │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                    │
│  ├── PostgreSQL (User Data, Sessions, Metrics)                 │
│  └── Redis (Caching, Rate Limiting)                            │
└─────────────────────────────────────────────────────────────────┘
```

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Slack App with Bot Token

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token

# Backend Services
API_GATEWAY_URL=http://localhost:8000
NLP_ENGINE_URL=http://localhost:8001
VISUALIZATION_URL=http://localhost:8002
ALERT_MANAGER_URL=http://localhost:8003

# Database
DATABASE_URL=postgresql://user:pass@localhost/slack_bot
REDIS_URL=redis://localhost:6379/3
```

### Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Database**:
   ```bash
   psql -d slack_bot -f init.sql
   ```

3. **Run Application**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
   ```

### Docker Deployment

1. **Build Image**:
   ```bash
   docker build -t slack-bot .
   ```

2. **Run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

## Slack App Configuration

### Required Scopes
- `app_mentions:read` - Read app mentions
- `channels:history` - Read channel messages
- `chat:write` - Send messages
- `commands` - Handle slash commands
- `im:history` - Read direct messages
- `im:write` - Send direct messages
- `users:read` - Read user information

### Event Subscriptions
Enable events and subscribe to:
- `app_mention` - When bot is mentioned
- `message.im` - Direct messages to bot

### Slash Commands
Create these slash commands:
- `/splunk` - Execute Splunk queries
- `/splunk-help` - Show help information
- `/splunk-status` - Check system status

### Interactive Components
Enable interactive components with Request URL pointing to:
`https://your-domain.com/slack/interactive`

## Usage Examples

### Basic Queries
```
@splunk-bot show me errors from the last hour
@splunk-bot count events by source
@splunk-bot find failed login attempts
```

### Advanced Queries
```
@splunk-bot show me top 10 error sources in the last 24 hours
@splunk-bot create a chart of response times by service
@splunk-bot alert me when error rate exceeds 5%
```

### Slash Commands
```
/splunk show me server performance
/splunk-help
/splunk-status
```

## API Endpoints

### Health Checks
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with dependencies
- `GET /metrics` - Service metrics

### Slack Integration
- `POST /slack/events` - Slack event handler
- `POST /slack/commands` - Slash command handler  
- `POST /slack/interactive` - Interactive component handler

## Database Schema

### Core Tables
- `slack_users` - Slack user information and metadata
- `user_contexts` - Splunk access control and permissions
- `user_sessions` - Conversation sessions and history
- `query_results` - Query execution results and analytics
- `bot_metrics` - Usage metrics and monitoring data
- `slack_alert_definitions` - Alerts created via Slack

### Indexes
Performance-optimized indexes on frequently queried columns:
- User ID lookups
- Session management
- Time-based queries
- Active session filtering

## Configuration

### Rate Limiting
```python
RATE_LIMIT_REQUESTS=100    # Requests per window
RATE_LIMIT_WINDOW=3600     # Window size in seconds
```

### Message Limits
```python
MAX_MESSAGE_LENGTH=3000    # Maximum Slack message length
MAX_QUERY_RESULTS=50       # Maximum results to display
```

### Feature Toggles
```python
ENABLE_DIRECT_MESSAGES=true      # Allow DMs
ENABLE_CHANNEL_MENTIONS=true     # Allow mentions
ENABLE_SLASH_COMMANDS=true       # Enable slash commands
```

## Testing

### Run Tests
```bash
pytest tests/ -v
```

### Test Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Integration Testing
```bash
pytest tests/integration/ -v
```

## Monitoring & Logging

### Structured Logging
All logs use structured JSON format with correlation IDs:
```json
{
  "timestamp": "2025-01-16T10:30:00Z",
  "level": "INFO",
  "service": "slack-bot",
  "user_id": "U123456789",
  "channel": "C123456789",
  "message": "Query processed successfully"
}
```

### Metrics Collection
- Request counts and success rates
- Response time distributions
- Active user and session counts
- Error rates by type
- Rate limiting statistics

### Health Monitoring
- Database connectivity
- Redis availability
- Backend service health
- Slack API connectivity

## Security

### Authentication
- Slack signature verification for all requests
- JWT tokens for backend service communication
- User context validation for Splunk access

### Authorization
- Role-based access control (RBAC)
- Index-level permissions
- Query execution limits
- Audit logging

### Data Protection
- Input sanitization and validation
- SQL injection prevention
- XSS protection for message formatting
- Secure credential management

## Troubleshooting

### Common Issues

1. **Bot Not Responding**
   - Check Slack app configuration
   - Verify event subscription URL
   - Check bot token permissions

2. **Database Connection Errors**
   - Verify PostgreSQL connection string
   - Check database initialization
   - Review connection pool settings

3. **Rate Limiting Issues**
   - Check Redis connectivity
   - Review rate limit configuration
   - Monitor user request patterns

4. **Backend Service Errors**
   - Verify service URLs and connectivity
   - Check authentication tokens
   - Review service health endpoints

### Debug Mode
Enable debug logging:
```bash
LOG_LEVEL=DEBUG
```

### Health Checks
Monitor service health:
```bash
curl http://localhost:8004/health/detailed
```

## Contributing

1. Follow the established code style (Black, isort)
2. Add tests for new functionality
3. Update documentation for API changes
4. Ensure security best practices

## License

This project is part of the Splunk MCP Integration suite.

---

For more information, see the main project documentation in the root `CLAUDE.md` file.