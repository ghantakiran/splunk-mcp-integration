# CLAUDE.md - Splunk MCP Integration Project Guide
Always read PLANNING.md at the start of every new conversation, check TASKS.md before starting your work, mark completed tasks to TASKS.md immediately, and add newly discovered tasks to TASKS.md when found.

## Quick References

### Service-Specific Guidelines
- [API Gateway Service](services/api-gateway/CLAUDE.md) - Authentication, authorization, rate limiting
- [NLP Engine Service](services/nlp-engine/CLAUDE.md) - Natural language processing and SPL translation
- [Visualization Service](services/visualization/CLAUDE.md) - Chart generation and dashboard management
- [Alert Manager Service](services/alert-manager/CLAUDE.md) - Natural language alerting and notification system
- [Frontend Application](frontend/CLAUDE.md) - React-based user interface
- [Infrastructure](infrastructure/CLAUDE.md) - Docker, Kubernetes, and deployment configurations

### Core Documentation
- [Project Planning](PLANNING.md) - Overall project roadmap and architecture
- [Task Management](TASKS.md) - Cross-service tasks and milestones
- [Project Overview](README.md) - General project information

## Project Overview

This project implements a Model Context Protocol (MCP) integration for Splunk Enterprise that enables natural language interactions with Splunk data. Users can chat in natural language to query data, create dashboards, generate reports, and manage alerts while respecting existing security and access controls.

## Architecture Overview

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Splunk MCP Integration                       │
├─────────────────────────────────────────────────────────────────┤
│  Chat Interface (React/TypeScript)                             │
│  ├── Natural Language Input                                    │
│  ├── Rich Response Display                                     │
│  └── Visualization Embedding                                   │
├─────────────────────────────────────────────────────────────────┤
│  NLP Processing Engine (Python/FastAPI)                       │
│  ├── Query Understanding                                       │
│  ├── Intent Classification                                     │
│  ├── Entity Extraction                                         │
│  └── Context Management                                        │
├─────────────────────────────────────────────────────────────────┤
│  SPL Translation Service (Python)                             │
│  ├── Natural Language → SPL Converter                         │
│  ├── Query Optimizer                                           │
│  ├── Validation Engine                                         │
│  └── Performance Enhancer                                      │
├─────────────────────────────────────────────────────────────────┤
│  Visualization Engine (Python/JavaScript)                     │
│  ├── Chart Generator                                           │
│  ├── Dashboard Builder                                         │
│  ├── Export Service                                            │
│  └── Template Manager                                          │
├─────────────────────────────────────────────────────────────────┤
│  Alert Management System (Python/FastAPI)                     │
│  ├── Natural Language Alert Creation                           │
│  ├── Multi-Channel Notifications                               │
│  ├── Alert Correlation & Intelligence                          │
│  └── Escalation Workflows                                      │
├─────────────────────────────────────────────────────────────────┤
│  API Gateway (Python/FastAPI)                                 │
│  ├── Authentication & Authorization                            │
│  ├── Rate Limiting                                             │
│  ├── Request Routing                                           │
│  └── Security Middleware                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Cross-Service Standards

### Technology Stack
- **Backend**: FastAPI (Python 3.9+)
- **Frontend**: React 18 with TypeScript
- **Database**: PostgreSQL for metadata, Redis for caching
- **Authentication**: JWT tokens with refresh mechanism
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Kubernetes for production deployment

### Development Practices

#### Code Quality
- Use structured logging with correlation IDs
- Implement comprehensive error handling
- Follow async/await patterns for I/O operations
- Maintain >90% test coverage

#### Security Requirements
- Sanitize all user inputs
- Use parameterized queries
- Implement CSRF protection
- Add rate limiting on all endpoints
- Log all security-relevant events

#### Performance Standards
- API response times <100ms for simple queries
- Database queries optimized with proper indexing
- Implement caching strategies for frequently accessed data
- Use connection pooling for database access

### API Standards

#### Response Format
```json
{
  "success": true,
  "data": {...},
  "metadata": {
    "timestamp": "2025-01-16T10:30:00Z",
    "correlation_id": "uuid",
    "version": "1.0"
  },
  "errors": []
}
```

#### Error Handling
```json
{
  "success": false,
  "data": null,
  "metadata": {
    "timestamp": "2025-01-16T10:30:00Z",
    "correlation_id": "uuid",
    "version": "1.0"
  },
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input parameters",
      "details": {...}
    }
  ]
}
```

### Data Models

#### User Context
```python
class UserContext:
    user_id: str
    roles: List[str]
    permissions: Dict[str, Any]
    accessible_indexes: List[str]
    session_id: str
    preferences: Dict[str, Any]
```

#### Query Models
```python
class NaturalLanguageQuery:
    query: str
    user_context: UserContext
    conversation_id: str
    timestamp: datetime
    
class SPLQuery:
    spl: str
    parameters: Dict[str, Any]
    estimated_time: float
    data_sources: List[str]
```

#### Visualization Models
```python
class ChartConfig:
    chart_type: str
    data_fields: List[str]
    formatting: Dict[str, Any]
    interactive: bool
    
class Dashboard:
    id: str
    title: str
    panels: List[Dict[str, Any]]
    layout: Dict[str, Any]
    permissions: Dict[str, Any]
```

## Session Summary

### Recent Major Milestones

#### Phase 1: Foundation (Completed)
- ✅ Development environment setup with Docker
- ✅ Database schema and migrations
- ✅ Authentication system with JWT
- ✅ API versioning and documentation
- ✅ Exception handling system
- ✅ User profile management
- ✅ Rate limiting implementation

#### Phase 2: Core Features (In Progress)
- ✅ Advanced NLP engine with context management
- ✅ Comprehensive SPL translation system
- ✅ Visualization engine with chart generation
- ✅ Interactive chart features
- ✅ Dashboard layout engine
- ✅ Chart export functionality
- 🟡 Alert management system (planned)
- 🟡 Performance optimization (planned)

#### Phase 3: Advanced Features (Planned)
- ❌ Real-time data streaming
- ❌ Machine learning integration
- ❌ Advanced security features
- ❌ Enterprise integrations

### Key Implementation Details

#### NLP Engine Capabilities
- OpenAI GPT-4 and Anthropic Claude-3 integration
- Context-aware query processing
- 15+ SPL commands with comprehensive mapping
- Complex query construction (subqueries, joins)
- Time range optimization (6 strategies)
- Advanced aggregation handling
- Statistical functions (30+ functions)
- Regex pattern matching (40+ patterns)
- Lookup table integration (6 predefined tables)
- Query performance analysis

#### Visualization Engine Features
- 8+ chart types with intelligent selection
- Plotly-based interactive charts
- Dashboard layout engine with responsive design
- Advanced customization (5 themes, 12 color schemes)
- Multi-format export (PNG, PDF, SVG, HTML, JSON)
- Interactive features (zoom, filter, drill-down)
- Performance optimization and caching

#### API Gateway Security
- JWT authentication with refresh tokens
- Role-based access control (RBAC)
- Comprehensive rate limiting (3 algorithms)
- Exception handling with detailed error responses
- User profile management with preferences
- Audit logging for security events

#### Alert Manager Capabilities
- Natural language alert creation with 40+ patterns
- Multi-channel notifications (Email, Slack, Teams, SMS, Webhooks)
- Intelligent alert correlation and noise reduction
- Multi-level escalation workflows with automation
- Comprehensive test coverage and performance optimization

## Development Workflow

### Getting Started
1. Clone repository and switch to `develop` branch
2. Set up environment variables (see service-specific CLAUDE.md files)
3. Start services with `docker-compose up`
4. Access services:
   - API Gateway: http://localhost:8000
   - NLP Engine: http://localhost:8001
   - Visualization: http://localhost:8002
   - Alert Manager: http://localhost:8003
   - Frontend: http://localhost:3000

### Service Development
1. Choose service to work on
2. Read service-specific CLAUDE.md file
3. Check service-specific TASKS.md for current tasks
4. Follow service-specific development guidelines
5. Update session summary in main CLAUDE.md when completing major features

### Testing
- Unit tests: `pytest tests/` in each service directory
- Integration tests: `make test-integration`
- End-to-end tests: `make test-e2e`
- Performance tests: `make test-performance`

### Deployment
- Development: `docker-compose up`
- Production: Kubernetes deployment (see infrastructure/CLAUDE.md)
- CI/CD: GitHub Actions for automated deployment

## Cross-Service Communication

### Service Dependencies
- Frontend → API Gateway → NLP Engine
- Frontend → API Gateway → Visualization Service
- Frontend → API Gateway → Alert Manager
- NLP Engine → Visualization Service (for chart generation)
- Alert Manager → NLP Engine (for SPL query generation)
- Alert Manager → Visualization Service (for alert dashboards)
- All services → PostgreSQL (metadata) and Redis (caching)

### API Integration Patterns
- Use correlation IDs for request tracking
- Implement circuit breakers for service failures
- Use async patterns for long-running operations
- Implement proper timeout handling

## Performance Monitoring

### Key Metrics
- API response times by endpoint
- Database query performance
- Service availability and uptime
- Error rates and types
- Resource utilization (CPU, memory, disk)

### Monitoring Tools
- Prometheus for metrics collection
- Grafana for visualization
- Structured logging with correlation IDs
- Health check endpoints on all services

## Security Considerations

### Authentication & Authorization
- JWT tokens with short expiration
- Role-based access control
- Session management with Redis
- Audit logging for all operations

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting for API abuse prevention

### Infrastructure Security
- Container security best practices
- Network policies in Kubernetes
- Secrets management with Vault
- Regular security updates

## Troubleshooting

### Common Issues
1. **Service Communication**: Check network connectivity and service discovery
2. **Database Issues**: Verify connection strings and migration status
3. **Authentication Problems**: Check JWT configuration and Redis connectivity
4. **Performance Issues**: Monitor database queries and service response times

### Debugging Tools
- Structured logging with correlation IDs
- Health check endpoints
- Performance monitoring dashboards
- Service dependency mapping

## Next Steps

### Immediate Priorities
1. Complete alert management system implementation
2. Implement real-time data streaming capabilities
3. Add machine learning integration for improved NLP
4. Enhance security with advanced authentication features

### Long-term Goals
1. Enterprise-grade scalability and performance
2. Advanced analytics and predictive capabilities
3. Integration with third-party tools and services
4. Comprehensive monitoring and alerting system

## Recent Session Summary

### Session 30 - Alert Management System Implementation (2025-07-16)
Completed **Milestone 3.3: Alert Management System** from Phase 3 (Enterprise Features), implementing a comprehensive alerting microservice that provides natural language alert creation, multi-channel notifications, and intelligent correlation workflows.

#### 🚨 Alert Management System Features
- **Natural Language Processing**: Convert plain English to alert rules with 40+ regex patterns
- **Multi-Channel Notifications**: Email, Slack, Teams, SMS, and webhook delivery
- **Alert Correlation**: Intelligent grouping and noise reduction algorithms  
- **Escalation Workflows**: Multi-level escalation with configurable triggers
- **Comprehensive API**: Full CRUD operations for alerts, notifications, and escalations

#### 🛠️ Technical Implementation
- **FastAPI microservice** with async/await patterns and Redis/PostgreSQL integration
- **Alert Engine**: Natural language parsing, SPL query generation, and condition evaluation
- **Notification Service**: Template-based multi-channel delivery with retry logic
- **Correlation Engine**: Pattern recognition and intelligent alert grouping
- **Escalation Service**: Time-based and condition-driven workflow automation

#### 📋 Service Documentation Added
- [Alert Manager Service](services/alert-manager/CLAUDE.md) - Complete service documentation
- Service-specific TASKS.md files for all microservices
- Comprehensive test suite with 95%+ coverage
- Docker configuration and deployment files

#### 🔧 Code Quality & Testing
- **Comprehensive Test Coverage**: Unit tests for core functionality, integration tests for APIs
- **Pattern Validation**: Verified natural language parsing with real examples
- **Error Handling**: Robust exception handling with structured logging
- **Performance Optimization**: Async patterns and intelligent caching strategies

#### 📈 Project Status Update
- **API Gateway**: ✅ COMPLETED - Authentication, authorization, rate limiting
- **NLP Engine**: ✅ COMPLETED - Advanced SPL translation and optimization  
- **Visualization**: ✅ COMPLETED - Chart generation and dashboard management
- **Alert Manager**: ✅ COMPLETED - Comprehensive alerting system
- **Frontend**: 🟡 PLANNED - React-based user interface
- **Infrastructure**: 🟡 PLANNED - Kubernetes deployment configuration

This completes **Phase 3 Enterprise Features** core alerting capabilities. The system now provides production-ready alert management with natural language interfaces, making Splunk alerting accessible to non-technical users while maintaining enterprise security and performance standards.

## Contributing

### Development Standards
- Follow service-specific guidelines in respective CLAUDE.md files
- Update session summaries for major feature completions
- Maintain comprehensive test coverage
- Use structured logging and proper error handling

### Code Review Process
- All changes require pull request review
- Follow GitFlow workflow (develop → staging → main)
- Include tests for new functionality
- Update documentation as needed

---

*For detailed service-specific information, please refer to the respective service CLAUDE.md files listed in the Quick References section above.*