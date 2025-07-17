# CLAUDE.md - Microsoft Teams Bot Service Guide

## Service Overview

This service implements a comprehensive Microsoft Teams bot integration for the Splunk MCP platform, enabling natural language interactions with Splunk data directly within Microsoft Teams. Users can chat with the bot in personal conversations or mention it in team channels to query data, create visualizations, and manage alerts.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Microsoft Teams Bot Service                  │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                                 │
│  ├── Teams Message Handling                                    │
│  ├── Bot Framework Integration                                 │
│  ├── JWT Authentication                                        │
│  └── Rate Limiting & Security                                  │
├─────────────────────────────────────────────────────────────────┤
│  Teams Handler (teams_handler.py)                              │
│  ├── ActivityHandler Implementation                            │
│  ├── Message Processing                                        │
│  ├── Adaptive Card Interactions                                │
│  └── Proactive Messaging                                       │
├─────────────────────────────────────────────────────────────────┤
│  Authentication & Security (auth.py)                           │
│  ├── Microsoft Bot Framework Verification                      │
│  ├── JWT Token Validation                                      │
│  ├── OpenID Metadata Fetching                                  │
│  └── Activity Signature Verification                           │
├─────────────────────────────────────────────────────────────────┤
│  Adaptive Cards Builder (adaptive_cards.py)                    │
│  ├── Rich Interactive Cards                                    │
│  ├── Query Result Cards                                        │
│  ├── Help & Status Cards                                       │
│  └── Action Button Handlers                                    │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer                                                 │
│  ├── User Management Service                                   │
│  ├── Session Management Service                                │
│  ├── Splunk Service Integration                                │
│  └── Rate Limiting Service                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

- **Framework**: FastAPI 0.104.1 with async/await patterns
- **Bot Framework**: Microsoft Bot Builder SDK (botbuilder-core, botbuilder-schema)
- **Database**: PostgreSQL with asyncpg for Teams-specific data
- **Caching**: Redis for session management and rate limiting
- **Authentication**: JWT tokens + Microsoft Bot Framework verification
- **Cards**: Adaptive Cards for rich interactive experiences
- **Logging**: Structured logging with structlog
- **Testing**: Pytest with comprehensive async test coverage

## Key Features

### 🤖 Microsoft Teams Integration
- **Bot Framework Integration**: Full Microsoft Bot Framework support with ActivityHandler
- **Adaptive Cards**: Rich interactive cards for queries, results, and help
- **Multi-Context Support**: Personal conversations, team channels, and group chats
- **Proactive Messaging**: Ability to send notifications and alerts
- **Mention Handling**: Smart @mention detection and response in channels

### 🔒 Security & Authentication
- **Bot Framework Verification**: Validates all incoming activities from Microsoft Teams
- **JWT Authentication**: Secure token-based authentication for API calls
- **OpenID Metadata**: Dynamic fetching of Microsoft's signing keys
- **Rate Limiting**: Sliding window rate limiting with Redis
- **Input Validation**: Comprehensive input sanitization and validation

### 💬 Natural Language Processing
- **Query Processing**: Natural language to SPL query translation
- **Context Management**: Conversation history and session management
- **Command Handling**: Built-in commands (help, status, alerts)
- **Error Handling**: Graceful error handling with user-friendly messages

### 📊 Rich Interactions
- **Interactive Cards**: Buttons, dropdowns, and form inputs
- **Visualization Embedding**: Chart and dashboard embedding in Teams
- **Quick Actions**: One-click query execution and result sharing
- **Help System**: Contextual help and usage guidance

## Database Schema

The service uses a comprehensive PostgreSQL schema with 8 main tables:

- **teams_users**: User profiles and metadata
- **user_contexts**: Splunk access control and permissions
- **teams_sessions**: Conversation sessions and history
- **teams_activities**: Activity logging and audit trail
- **teams_query_results**: Query execution history and results
- **teams_metrics**: Performance and usage metrics
- **teams_alert_definitions**: User-defined alerts and notifications
- **teams_bot_installations**: Bot installation tracking
- **teams_conversation_references**: Proactive messaging references

## Configuration

### Environment Variables

```bash
# Microsoft Teams Bot Configuration
MICROSOFT_APP_ID=your-app-id
MICROSOFT_APP_PASSWORD=your-app-password
MICROSOFT_APP_TENANT_ID=your-tenant-id

# Service URLs
API_GATEWAY_URL=http://api-gateway:8000
NLP_ENGINE_URL=http://nlp-engine:8001
VISUALIZATION_URL=http://visualization:8002
ALERT_MANAGER_URL=http://alert-manager:8003

# Database Configuration
DATABASE_URL=postgresql://teams_user:teams_pass@postgres:5432/teams_bot
REDIS_URL=redis://redis:6379/4

# Security
JWT_SECRET_KEY=your-secret-key

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Microsoft Teams App Manifest

The bot requires registration in Microsoft Teams with the following capabilities:
- **Bot**: Conversational bot with messaging
- **Scopes**: Personal, Team, GroupChat
- **Commands**: Predefined slash commands
- **Adaptive Cards**: Rich card interactions

## API Endpoints

### Core Endpoints

- `POST /teams/messages` - Handle Teams message activities
- `POST /teams/commands` - Handle slash commands
- `GET /teams/health` - Health check endpoint
- `GET /teams/metrics` - Service metrics

### Activity Types Handled

- **message**: Text messages and @mentions
- **invoke**: Adaptive card actions and submissions
- **memberAdded**: Welcome new users
- **memberRemoved**: Handle user departures
- **installationUpdate**: Bot installation/uninstallation

## Usage Examples

### Personal Chat
```
User: "show me errors from last hour"
Bot: [Sends adaptive card with SPL query, results, and actions]
```

### Channel Mention
```
User: "@Splunk MCP Assistant what's the server status?"
Bot: [Responds with system status card and metrics]
```

### Adaptive Card Actions
```
[User clicks "Run Query" button]
Bot: [Executes query and shows results inline]
```

## Development Setup

### Prerequisites
- Python 3.9+
- Docker and Docker Compose
- Microsoft Teams Bot registration
- PostgreSQL and Redis

### Local Development

1. **Clone and Navigate**
   ```bash
   cd services/teams-bot
   ```

2. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your Microsoft Teams app credentials
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Services**
   ```bash
   docker-compose up -d postgres redis
   ```

5. **Run Application**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
   ```

6. **ngrok for Local Testing**
   ```bash
   ngrok http 8005
   # Update Teams app manifest with ngrok URL
   ```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_teams_handler.py -v
pytest tests/test_auth.py -v
pytest tests/test_adaptive_cards.py -v
```

## Service Integration

### Backend Service Communication

The Teams bot integrates with all backend services:

```python
# Example: Query processing flow
async def process_query(self, activity: dict, query: str):
    # 1. Get user context
    user_context = await self.user_service.get_user_context(user_id)
    
    # 2. Process with NLP engine
    response = await self.splunk_service.process_query(
        query=query,
        user_context=user_context
    )
    
    # 3. Format and send results
    await self._send_query_results(activity, response)
```

### Rate Limiting

Implements sliding window rate limiting:
- **Personal chats**: 100 requests per hour
- **Channel mentions**: 50 requests per hour
- **Adaptive card actions**: 200 requests per hour

### Session Management

Maintains conversation context:
- **History**: Last 50 messages per session
- **Context**: User preferences and state
- **Persistence**: Sessions stored in PostgreSQL

## Monitoring & Metrics

### Performance Metrics
- Response times for different activity types
- Query execution success rates
- User engagement metrics
- Error rates and types

### Health Checks
- Database connectivity
- Redis availability
- Backend service health
- Bot Framework connectivity

### Logging

Structured logging with correlation IDs:
```json
{
  "timestamp": "2025-01-16T10:30:00Z",
  "level": "INFO",
  "correlation_id": "uuid",
  "user_id": "29:user123",
  "conversation_id": "19:conv123",
  "activity_type": "message",
  "message": "Query processed successfully"
}
```

## Security Considerations

### Authentication Flow
1. **Bot Framework Verification**: Validates Microsoft signature
2. **JWT Token Validation**: Verifies internal API tokens
3. **OpenID Metadata**: Dynamic key fetching for signature verification
4. **Activity Validation**: Ensures activities come from legitimate sources

### Data Protection
- **PII Handling**: Minimal storage of personal information
- **Query Sanitization**: Input validation and SQL injection prevention
- **Audit Logging**: Comprehensive activity logging
- **Encryption**: All sensitive data encrypted at rest

## Troubleshooting

### Common Issues

1. **Bot Not Responding**
   - Check Microsoft App credentials
   - Verify webhook URL configuration
   - Review Bot Framework activity validation

2. **Authentication Failures**
   - Validate JWT secret key
   - Check OpenID metadata connectivity
   - Review Bot Framework signature verification

3. **Database Connection Issues**
   - Verify PostgreSQL connection string
   - Check database migrations
   - Review connection pool settings

4. **Rate Limiting**
   - Check Redis connectivity
   - Review rate limit configurations
   - Monitor user activity patterns

### Debug Commands

```bash
# Check service health
curl http://localhost:8005/teams/health

# View metrics
curl http://localhost:8005/teams/metrics

# Check logs
docker-compose logs teams-bot

# Database queries
psql $DATABASE_URL -c "SELECT * FROM teams_sessions LIMIT 10;"
```

## Deployment

### Docker Deployment

```bash
# Build and start
docker-compose up -d

# Scale the service
docker-compose up -d --scale teams-bot=3

# Update configuration
docker-compose restart teams-bot
```

### Production Considerations

- **Load Balancing**: Use nginx or cloud load balancer
- **SSL/TLS**: Terminate SSL at load balancer
- **Secrets Management**: Use Azure Key Vault or similar
- **Monitoring**: Integrate with Prometheus and Grafana
- **Backup**: Regular database backups
- **High Availability**: Multi-region deployment

## Contributing

### Code Standards
- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Maintain >90% test coverage

### Pull Request Process
1. Create feature branch from `develop`
2. Implement changes with tests
3. Update documentation
4. Submit PR with detailed description
5. Address review feedback

## Future Enhancements

### Planned Features
- **Voice Commands**: Speech-to-text integration
- **Advanced Cards**: Dynamic form generation
- **Multi-Language**: International Teams support
- **AI Insights**: Proactive data insights
- **Integration Hub**: Third-party service connections

### Performance Optimizations
- **Caching**: Enhanced response caching
- **Connection Pooling**: Optimized database connections
- **Async Processing**: Background query processing
- **CDN Integration**: Asset delivery optimization

---

*For general project information, see the main CLAUDE.md file in the project root.*