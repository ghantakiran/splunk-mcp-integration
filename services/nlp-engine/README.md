# Splunk MCP NLP Engine Service

Advanced Natural Language Processing service for Splunk MCP integration, providing SPL translation, intent classification, and entity extraction capabilities.

## Features

- **SPL Translation**: Convert natural language queries to Splunk SPL commands
- **Intent Classification**: Classify user intents for optimized query processing
- **Entity Extraction**: Extract Splunk-specific entities from natural language
- **Context Management**: Conversation flow and context-aware query processing
- **Reference Resolution**: Automatic resolution of pronouns and references
- **Multi-Provider AI**: Support for OpenAI GPT-4 and Anthropic Claude-3
- **Fallback Support**: Automatic failover between AI providers
- **Memory Store**: Redis-based conversation and query history
- **Follow-up Suggestions**: Intelligent query suggestions based on context
- **Structured Logging**: Comprehensive logging with metrics
- **API Documentation**: Interactive OpenAPI/Swagger documentation

## Architecture

```
nlp-engine/
├── app/
│   ├── ai/                     # AI integration layer
│   │   ├── providers.py        # AI provider implementations
│   │   ├── nlp_service.py      # Core NLP processing
│   │   └── __init__.py
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints.py    # FastAPI endpoints
│   │       ├── context_endpoints.py # Context management endpoints
│   │       └── __init__.py
│   ├── context/                # Context management system
│   │   ├── conversation_manager.py # Conversation flow management
│   │   ├── context_service.py  # Context-aware query processing
│   │   ├── memory_store.py     # Redis memory store
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py           # Configuration management
│   │   ├── logging.py          # Structured logging
│   │   └── __init__.py
│   ├── main.py                 # FastAPI application
│   └── __init__.py
├── tests/
│   ├── test_context_management.py # Context system tests
│   └── ...
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Configure API keys
export OPENAI_API_KEY="your_openai_api_key"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export SECRET_KEY="your_secret_key"
export JWT_SECRET_KEY="your_jwt_secret_key"
```

### 2. Docker Deployment

```bash
# Start all services
docker-compose up -d

# Start with monitoring (Prometheus/Grafana)
docker-compose --profile monitoring up -d

# Check service health
curl http://localhost:8001/ping
```

### 3. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python -m app.main

# Or with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## API Endpoints

### Context Management Endpoints

#### Create Conversation
```bash
POST /api/v1/conversations
```

Create a new conversation for context tracking:
```json
{
  "user_id": "user123",
  "title": "Security Analysis",
  "session_id": "session456",
  "metadata": {
    "source": "web_app"
  }
}
```

#### Contextual Query Processing
```bash
POST /api/v1/conversations/{conversation_id}/query
```

Process query with conversation context:
```json
{
  "conversation_id": "conv-123",
  "query": "Show me the same data for yesterday",
  "preferences": {
    "include_history": true,
    "max_context_queries": 5,
    "suggest_follow_ups": true
  }
}
```

#### Get Conversation
```bash
GET /api/v1/conversations/{conversation_id}
```

#### Add Message
```bash
POST /api/v1/conversations/{conversation_id}/messages
```

#### Get Conversation History
```bash
GET /api/v1/conversations/{conversation_id}/history
```

#### Get User Conversations
```bash
GET /api/v1/conversations/user/{user_id}
```

### Core NLP Endpoints

#### Translate to SPL
```bash
POST /api/v1/translate
```

Convert natural language to SPL:
```json
{
  "query": "Show me all failed login attempts in the last 24 hours",
  "context": {
    "user_role": "admin",
    "available_indexes": ["security", "auth"]
  }
}
```

#### Intent Classification
```bash
POST /api/v1/intent
```

Classify query intent:
```json
{
  "query": "Count the number of errors by source in the last hour"
}
```

#### Entity Extraction
```bash
POST /api/v1/entities
```

Extract entities:
```json
{
  "query": "Show me errors from host web01 for user john.doe"
}
```

#### Query Enhancement
```bash
POST /api/v1/enhance
```

Comprehensive analysis:
```json
{
  "query": "Find security incidents from yesterday",
  "context": {
    "user_role": "security_analyst"
  }
}
```

### System Endpoints

- `GET /` - Service information
- `GET /ping` - Health check
- `GET /api/v1/health` - Detailed health status
- `GET /api/v1/providers` - AI provider information
- `GET /api/v1/metrics` - Service metrics
- `GET /docs` - Interactive API documentation

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `DEFAULT_AI_PROVIDER` | Primary AI provider | `openai` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENVIRONMENT` | Environment name | `development` |
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | - |

### AI Provider Configuration

```python
# OpenAI Settings
OPENAI_MODEL = "gpt-4-turbo-preview"
OPENAI_MAX_TOKENS = 4096
OPENAI_TEMPERATURE = 0.1

# Anthropic Settings  
ANTHROPIC_MODEL = "claude-3-sonnet-20240229"
ANTHROPIC_MAX_TOKENS = 4096
ANTHROPIC_TEMPERATURE = 0.1
```

## Usage Examples

### Python Client

```python
import httpx

async def translate_query():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/api/v1/translate",
            json={
                "query": "Find all errors in the last hour",
                "context": {"environment": "production"}
            }
        )
        result = response.json()
        print(f"SPL: {result['spl_query']}")
        print(f"Confidence: {result['confidence_score']}")
```

### cURL

```bash
# Translate natural language to SPL
curl -X POST "http://localhost:8001/api/v1/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all 404 errors from apache logs",
    "context": {"sourcetype": "apache_access"}
  }'

# Get service health
curl http://localhost:8001/api/v1/health
```

## Development

### Project Structure

- **AI Layer**: Provider-agnostic AI integrations with fallback support
- **NLP Service**: Core business logic for SPL translation and analysis
- **API Layer**: FastAPI endpoints with comprehensive validation
- **Configuration**: Centralized settings with environment variable support
- **Logging**: Structured logging with NLP-specific metrics

### Adding New Features

1. **New AI Provider**: Implement `BaseAIProvider` interface
2. **New NLP Task**: Extend `NLPService` with new methods
3. **New Endpoint**: Add to `endpoints.py` with proper models
4. **New Configuration**: Update `config.py` and environment template

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/

# Load testing
locust -f tests/load_test.py --host=http://localhost:8001
```

## Monitoring

### Metrics

- Request/response times
- AI provider performance
- Translation accuracy
- Error rates
- Token usage

### Logging

Structured JSON logging includes:
- Request tracing
- AI API calls
- NLP processing metrics
- Error tracking

### Health Checks

- Service availability
- AI provider connectivity
- Database connections
- Memory/CPU usage

## Security

- API key management through environment variables
- Input validation and sanitization
- Rate limiting (configurable)
- CORS protection
- Request/response logging
- Error handling without information leakage

## Performance

- Async/await throughout
- Connection pooling
- Caching strategies
- Provider fallback
- Timeout handling
- Resource monitoring

## Deployment

### Docker Production

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale NLP service
docker-compose up -d --scale nlp-engine=3
```

### Kubernetes

```yaml
# See k8s/ directory for Kubernetes manifests
kubectl apply -f k8s/
```

## Troubleshooting

### Common Issues

1. **AI Provider Errors**
   - Check API keys
   - Verify provider availability
   - Review rate limits

2. **Performance Issues**
   - Monitor token usage
   - Check provider latency
   - Review query complexity

3. **Translation Quality**
   - Provide better context
   - Use conversation history
   - Fine-tune prompts

### Logs

```bash
# View service logs
docker-compose logs nlp-engine

# Follow logs
docker-compose logs -f nlp-engine

# Filter by level
docker-compose logs nlp-engine | grep ERROR
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Update documentation
5. Submit pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: [Project Issues](https://github.com/your-org/splunk-mcp/issues)
- Documentation: [Full Docs](https://docs.your-org.com/splunk-mcp)
- Community: [Discord/Slack](https://your-org.com/community)