# Microsoft Teams Bot Service

A comprehensive Microsoft Teams bot integration for the Splunk MCP platform that enables natural language interactions with Splunk data directly within Microsoft Teams.

## Features

🤖 **Microsoft Teams Integration**
- Full Bot Framework support with ActivityHandler
- Personal conversations, team channels, and group chats
- @mention handling in channels
- Proactive messaging for alerts and notifications

💬 **Natural Language Processing**
- Convert plain English to SPL queries
- Context-aware conversation management
- Built-in commands (help, status, alerts)
- Query history and session persistence

📊 **Rich Interactions**
- Adaptive Cards for interactive experiences
- Visualization embedding in Teams
- One-click query execution
- Result sharing and collaboration

🔒 **Enterprise Security**
- Microsoft Bot Framework authentication
- JWT token validation
- Role-based access control
- Comprehensive audit logging

## Quick Start

### Prerequisites

1. **Microsoft Teams App Registration**
   - Register bot in Azure Bot Service
   - Get App ID, Password, and Tenant ID
   - Configure Teams app manifest

2. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your Teams app credentials
   ```

3. **Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Development

```bash
# Start database services
docker-compose up -d postgres redis

# Run the bot service
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload

# For local testing with Teams
ngrok http 8005
# Update Teams app manifest with ngrok URL
```

### Production

```bash
# Start all services
docker-compose up -d

# Check health
curl http://localhost:8005/teams/health
```

## Usage Examples

### Personal Chat
```
User: "show me errors from last hour"
Bot: [Adaptive card with SPL query and results]
```

### Channel Mention
```
User: "@Splunk MCP Assistant what's the server status?"
Bot: [System status card with metrics]
```

### Interactive Cards
```
[User clicks "Run Query" button on card]
Bot: [Executes query and shows results inline]
```

## Configuration

Key environment variables:

```bash
# Microsoft Teams
MICROSOFT_APP_ID=your-app-id
MICROSOFT_APP_PASSWORD=your-app-password
MICROSOFT_APP_TENANT_ID=your-tenant-id

# Backend Services
API_GATEWAY_URL=http://api-gateway:8000
NLP_ENGINE_URL=http://nlp-engine:8001
VISUALIZATION_URL=http://visualization:8002

# Database
DATABASE_URL=postgresql://teams_user:teams_pass@postgres:5432/teams_bot
REDIS_URL=redis://redis:6379/4
```

## API Endpoints

- `POST /teams/messages` - Handle Teams activities
- `POST /teams/commands` - Process slash commands  
- `GET /teams/health` - Health check
- `GET /teams/metrics` - Service metrics

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific tests
pytest tests/test_teams_handler.py -v
```

## Architecture

The service follows a layered architecture:

- **FastAPI Application**: HTTP endpoints and middleware
- **Teams Handler**: Bot Framework ActivityHandler implementation
- **Service Layer**: Business logic and backend integration
- **Data Layer**: PostgreSQL and Redis for persistence

## Security

- **Bot Framework Verification**: Validates Microsoft signatures
- **JWT Authentication**: Secure API token validation
- **Rate Limiting**: Prevents abuse with sliding window limits
- **Input Validation**: Comprehensive sanitization

## Monitoring

- **Health Checks**: Database, Redis, and service connectivity
- **Metrics**: Response times, success rates, user engagement
- **Logging**: Structured logs with correlation IDs
- **Audit Trail**: Complete activity and query logging

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check Bot Framework credentials
2. **Authentication failures**: Verify JWT configuration
3. **Database errors**: Check connection string and migrations
4. **Rate limiting**: Monitor Redis connectivity

### Debug Commands

```bash
# Check service status
curl http://localhost:8005/teams/health

# View logs
docker-compose logs teams-bot

# Database queries
psql $DATABASE_URL -c "SELECT * FROM teams_sessions LIMIT 10;"
```

## Development

### Code Standards
- Follow PEP 8 style guidelines
- Use type hints and docstrings
- Maintain >90% test coverage
- Async/await for I/O operations

### File Structure
```
app/
├── main.py              # FastAPI application
├── bot/
│   ├── teams_handler.py # Bot Framework handler
│   └── auth.py          # Authentication logic
├── services/            # Business logic layer
├── models/              # Data models
├── utils/               # Utilities and helpers
└── api/                 # API endpoints
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines.

## License

This project is part of the Splunk MCP Integration platform.