# NLP Engine Service - CLAUDE.md

## Inherits From
- [Main Project Guidelines](../../CLAUDE.md)
- [Shared Standards](../../CLAUDE.md#core-data-models)

## Service Overview
The NLP Engine service is responsible for natural language processing, SPL translation, and intelligent query understanding. It provides the core AI capabilities for converting user intent into executable Splunk queries.

## Architecture
- **AI Provider Integration**: OpenAI GPT-4 and Anthropic Claude-3 support
- **Context Management**: Conversation flow tracking and session persistence
- **SPL Translation**: Advanced natural language to SPL conversion
- **Query Optimization**: Performance analysis and optimization suggestions
- **Pattern Recognition**: Intent classification and entity extraction

## Development Guidelines

### Code Structure
```
services/nlp-engine/
├── app/
│   ├── ai/                     # AI processing modules
│   │   ├── nlp_service.py      # Core NLP processing
│   │   ├── providers.py        # AI provider integrations
│   │   ├── spl_mapping.py      # SPL command mapping
│   │   ├── query_constructor.py # Complex query building
│   │   └── [other AI modules]
│   ├── api/v1/                 # API endpoints
│   │   ├── endpoints.py        # General endpoints
│   │   └── spl_endpoints.py    # SPL-specific endpoints
│   ├── core/                   # Core configuration
│   └── main.py                 # FastAPI application
├── tests/                      # Test suites
└── requirements.txt
```

### Key Components

#### AI Provider Integration
- **OpenAI Integration**: GPT-4 for natural language understanding
- **Anthropic Integration**: Claude-3 for backup and comparison
- **Provider Abstraction**: Unified interface for multiple AI providers
- **Failover Logic**: Automatic failover between providers

#### SPL Translation Features
- **Command Mapping**: 15+ SPL commands across 9 categories
- **Pattern Detection**: Time series, correlation, distribution patterns
- **Complex Queries**: Subqueries, joins, aggregations
- **Optimization**: Performance analysis and suggestions

#### Context Management
- **Conversation Tracking**: Multi-turn conversation support
- **Session Persistence**: Redis-based session storage
- **Reference Resolution**: Pronoun and contextual reference handling
- **Query Enhancement**: Context-aware query improvement

## API Endpoints

### Core NLP Endpoints
- `POST /api/v1/translate` - Natural language to SPL translation
- `POST /api/v1/intent` - Intent classification
- `POST /api/v1/entities` - Entity extraction
- `POST /api/v1/conversations` - Conversation management

### SPL-Specific Endpoints
- `POST /api/v1/spl/translate/enhanced` - Advanced SPL translation
- `POST /api/v1/spl/commands/suggest` - Command suggestions
- `POST /api/v1/spl/validate` - SPL validation
- `POST /api/v1/spl/performance/analyze` - Performance analysis

## Testing Guidelines

### Test Structure
```
tests/
├── test_spl_mapping.py         # SPL mapping tests
├── test_query_constructor.py   # Query construction tests
├── test_nlp_service.py         # Core NLP tests
└── integration/                # Integration tests
```

### Testing Patterns
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Query optimization validation
- **Mock AI Providers**: Test without external API calls

## Configuration

### Environment Variables
```bash
# AI Provider Configuration
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_MODEL=gpt-4
ANTHROPIC_MODEL=claude-3-opus

# Service Configuration
NLP_SERVICE_PORT=8001
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379

# Performance Settings
MAX_TOKENS=4000
TIMEOUT_SECONDS=30
```

### Dependencies
- FastAPI for API framework
- OpenAI Python client
- Anthropic Python client
- Redis for session management
- Pydantic for data validation

## Performance Considerations

### Optimization Strategies
- **Token Management**: Efficient token usage across AI providers
- **Caching**: Redis caching for repeated queries
- **Async Processing**: Non-blocking operations
- **Connection Pooling**: Efficient API connections

### Monitoring
- **AI API Metrics**: Token usage, response times
- **Query Performance**: SPL optimization success rates
- **Error Tracking**: Provider failures and fallbacks
- **Context Metrics**: Conversation flow effectiveness

## Troubleshooting

### Common Issues
1. **AI Provider Failures**: Check API keys and rate limits
2. **SPL Translation Errors**: Verify command mapping configurations
3. **Context Loss**: Check Redis connection and session TTL
4. **Performance Issues**: Monitor token usage and response times

### Debugging Tools
- Structured logging with correlation IDs
- Performance metrics collection
- AI provider response validation
- Context state inspection

## Development Workflow

### Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables
3. Start Redis server
4. Run FastAPI application: `uvicorn main:app --reload`

### Testing
1. Unit tests: `pytest tests/`
2. Integration tests: `pytest tests/integration/`
3. Performance tests: `pytest tests/performance/`

### Deployment
- Docker containerization
- Environment-based configuration
- Health check endpoints
- Monitoring integration

## Recent Implementations

### Session 11 - Advanced NLP Engine (2025-07-14)
- OpenAI GPT-4 and Anthropic Claude-3 integration
- Full context management system
- Redis-based session persistence
- Comprehensive test suite

### Session 12 - SPL Command Mapping (2025-07-14)
- 15+ SPL commands across 9 categories
- Natural language field translation
- Intent pattern recognition
- Real-time syntax validation

### Session 13 - Complex Query Construction (2025-07-15)
- Multi-step query pipelines
- Subquery and join support
- Performance analysis engine
- Logical structure handling

### Session 14 - Time Range Optimization (2025-07-15)
- 6 time range types support
- 6 optimization strategies
- Context-aware recommendations
- Performance impact analysis

### Session 15 - Advanced Aggregation (2025-07-15)
- Statistical functions support
- Conditional aggregations
- Temporal aggregations
- Multi-field operations

### Session 16 - Statistical Functions (2025-07-15)
- 30+ statistical functions
- 8 function categories
- Advanced pattern detection
- SPL generation for statistics

### Session 17 - Regex Pattern Matching (2025-07-15)
- 40+ common patterns
- 6 operation types
- Pattern optimization
- Validation system

### Session 18 - Lookup Table Integration (2025-07-15)
- 6 predefined lookup tables
- Multiple lookup types
- Performance optimization
- Validation system

### Session 19 - Eval and Calculated Fields (2025-07-15)
- 25+ eval functions
- 6 function categories
- Expression validation
- Template system

### Session 20 - Query Performance Analysis (2025-07-15)
- 5 performance levels
- 10 bottleneck types
- Resource estimation
- Optimization suggestions

### Session 21 - Index Selection Optimization (2025-07-15)
- 8 index categories
- 7 optimization strategies
- Cost-benefit analysis
- Multi-index support

### Session 22 - Enhanced Lookup Integration (2025-07-16)
- Fixed naming conflicts
- Comprehensive validation
- Performance testing
- API integration

## Next Steps
- Machine learning capabilities for improved pattern recognition
- Advanced aggregation handling for statistical functions
- Performance monitoring and optimization
- Enhanced visualization integration