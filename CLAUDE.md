# CLAUDE.md - Splunk MCP Integration Project Guide
Always read PLANNING.md at the start of every new conversation, check TASKS.md before starting your work, mark completed tasks to TASKS.md immediately, and add newly discovered tasks to TASKS.md when found.

## Session Summary

### Session 1 - Project Foundation Setup (2025-07-13)

**Completed Tasks:**
- ✅ Set up version control repository with proper branching strategy (TASKS.md - First task)
  - Initialized Git repository
  - Created comprehensive README.md with project overview, architecture, and setup instructions
  - Set up .gitignore for Python/Node.js hybrid project
  - Created complete directory structure following planned architecture
  - Made initial commit with all project documentation
  - Created and switched to `develop` branch for GitFlow workflow

**Repository Status:**
- **Current Branch**: `develop` (ready for active development)
- **Main Branch**: Contains stable project foundation
- **Directory Structure**: Complete architecture with services/, frontend/, shared/, tests/, docs/, infrastructure/
- **Documentation**: All planning documents (PLANNING.md, TASKS.md, README.md) in place

**Next Steps:**
- Begin Phase 1, Milestone 1.1: Development Environment Setup
- Configure Docker development environment with multi-service setup
- Set up PostgreSQL database with initial schema
- Configure Redis for caching and session management

**Project Status:** Foundation complete, Docker development environment configured

### Session 2 - Docker Development Environment (2025-07-13)

**Completed Tasks:**
- ✅ Configure Docker development environment with multi-service setup (TASKS.md - Second task)
  - Created comprehensive docker-compose.yml with all 6 microservices
  - Set up PostgreSQL database with complete schema and initial data
  - Configured Redis for caching and session management with optimized settings
  - Added Dockerfiles for API Gateway and Frontend services
  - Created development dependencies and package configurations
  - Added .env.example with all required environment variables
  - Created Makefile with development workflow commands
  - Added basic FastAPI and React application entry points
  - Included development tools (pgAdmin, Redis Commander) for easier debugging

**Docker Environment:**
- **Services**: 8 containers (6 microservices + PostgreSQL + Redis + dev tools)
- **Database**: PostgreSQL 15 with complete schema (auth, chat, spl, viz, alerts, audit)
- **Cache**: Redis 7 with optimized configuration for session management
- **Frontend**: React 18 with TypeScript and Material-UI
- **Backend**: FastAPI with async support and comprehensive dependencies
- **Development Tools**: pgAdmin for database management, Redis Commander for cache inspection

**Next Steps:**
- Begin Phase 1, Milestone 1.2: Core Backend Foundation
- Initialize FastAPI project with proper structure
- Set up async database connections with SQLAlchemy
- Create base models for User, Query, and Session
- Implement database migrations with Alembic

**Project Status:** Docker development environment ready, FastAPI foundation complete

### Session 3 - FastAPI Backend Foundation (2025-07-13)

**Completed Tasks:**
- ✅ Initialize FastAPI project with proper structure (TASKS.md - Third task)
  - Created comprehensive application structure following FastAPI best practices
  - Added configuration management with Pydantic settings and environment variables
  - Implemented security utilities for JWT authentication and password hashing
  - Created custom exception handling with proper HTTP status mapping
  - Set up structured logging with request/response middleware
  - Added dependency injection system for database, Redis, and authentication
  - Created API v1 router structure with endpoint placeholders
  - Implemented health check endpoints with dependency status monitoring
  - Added proper error handling and exception mappers
  - Set up CORS middleware and request logging

**FastAPI Application Structure:**
- **Core Components**: Configuration, security, exceptions, logging modules
- **API Architecture**: RESTful API v1 with proper routing and dependency injection
- **Security Features**: JWT tokens, password hashing, rate limiting, session management
- **Monitoring**: Health checks, structured logging, security event tracking
- **Error Handling**: Custom exceptions with proper HTTP status code mapping
- **Middleware**: CORS, request logging, authentication validation

**Technical Implementation:**
- Pydantic-based configuration with environment variable support
- Async/await throughout for optimal performance
- Enterprise-grade security with JWT access/refresh tokens
- Structured logging with security and query event tracking
- Comprehensive exception handling with detailed error responses
- Dependency injection for database, Redis, and authentication

**Next Steps:**
- Set up async database connections with SQLAlchemy
- Create base models for User, Query, and Session
- Implement database migrations with Alembic
- Add JWT token validation and user authentication endpoints

**Project Status:** FastAPI foundation complete, async database layer implemented

### Session 4 - Async Database Integration (2025-07-13)

**Completed Tasks:**
- ✅ Set up async database connections with SQLAlchemy (TASKS.md - Fourth task)
  - Created comprehensive async database session management with connection pooling
  - Implemented base model classes with common functionality and mixins
  - Added complete data models for all core entities (User, Conversation, Query, Dashboard, Alert, Audit)
  - Set up proper database configuration with PostgreSQL and SQLite support
  - Created database manager for advanced operations and health monitoring
  - Added relationship mapping between all models following schema design
  - Implemented model utilities for serialization, context management, and validation
  - Set up database initialization and connection health checking
  - Added proper naming conventions and metadata configuration
  - Fixed dependency injection imports for seamless integration

**Database Architecture:**
- **Session Management**: Async SQLAlchemy with connection pooling and health monitoring
- **Model Structure**: Base classes with TimestampMixin, SoftDeleteMixin, AuditMixin
- **Entity Models**: User, Conversation, Message, Query, QueryResult, Dashboard, Chart, AlertRule, AlertIncident, ActivityLog, SecurityEvent
- **Relationships**: Comprehensive foreign key relationships matching PostgreSQL schema
- **Configuration**: Environment-based config supporting PostgreSQL (production) and SQLite (development)

**Technical Implementation:**
- Async/await throughout database layer for optimal performance
- Connection pooling with different strategies for PostgreSQL vs SQLite
- Health check system for database monitoring
- Model utilities for serialization, context management, and validation
- JSONB fields for flexible metadata and configuration storage
- Enum types for status management and type safety
- Proper constraint naming conventions and metadata configuration

**Data Models Created:**
- **User**: Authentication, RBAC, Splunk integration, preferences
- **Conversation/Message**: Chat functionality with threading and context
- **Query/QueryResult**: SPL translation, execution tracking, caching
- **Dashboard/Chart**: Visualization management with layouts and permissions
- **Alert**: Rule definitions and incident management
- **Audit**: Activity logs and security event tracking

**Next Steps:**
- Create base models for User, Query, and Session (completed as part of database setup)
- Implement database migrations with Alembic
- Set up API versioning and documentation
- Implement JWT token generation and validation

**Project Status:** Database layer complete, ready for migrations and authentication implementation

## Project Overview

This project implements a Model Context Protocol (MCP) integration for Splunk Enterprise that enables natural language interactions with Splunk data. Users can chat in natural language to query data, create dashboards, generate reports, and manage alerts while respecting existing security and access controls.

## Architecture

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
│  Access Control Service (Python)                              │
│  ├── RBAC Integration                                          │
│  ├── Permission Checker                                        │
│  ├── Data Filtering                                            │
│  └── Audit Logger                                              │
├─────────────────────────────────────────────────────────────────┤
│  Visualization Engine (Python/JavaScript)                     │
│  ├── Chart Generator                                           │
│  ├── Dashboard Builder                                         │
│  ├── Export Service                                            │
│  └── Template Manager                                          │
├─────────────────────────────────────────────────────────────────┤
│  Alert Management System (Python)                             │
│  ├── Alert Creator                                             │
│  ├── Notification Service                                      │
│  ├── Escalation Manager                                        │
│  └── Historical Analyzer                                       │
└─────────────────────────────────────────────────────────────────┘
│
│  External Integrations
├── Splunk REST API (Primary Data Interface)
├── Authentication Services (LDAP/SAML/OAuth)
├── Notification Services (Email/Slack/Teams)
└── Export Services (PDF/Excel/PowerPoint)
```

### Technology Stack

#### Backend Services
- **Framework**: FastAPI (Python 3.9+)
- **NLP**: OpenAI GPT-4 or Claude-3 via API
- **Database**: PostgreSQL for metadata, Redis for caching
- **Message Queue**: RabbitMQ or Apache Kafka
- **Authentication**: JWT tokens with refresh mechanism
- **API Gateway**: nginx or AWS API Gateway

#### Frontend
- **Framework**: React 18 with TypeScript
- **State Management**: Redux Toolkit or Zustand
- **UI Components**: Material-UI or Ant Design
- **Charts**: D3.js or Chart.js for visualizations
- **Real-time**: WebSocket for live updates

#### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Kubernetes or Docker Compose
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack integration
- **Security**: Vault for secrets, SSL/TLS everywhere

## Development Guidelines

### Code Organization

```
splunk-mcp-integration/
├── services/
│   ├── nlp-engine/                 # Natural Language Processing
│   ├── spl-translator/             # SPL Translation Service
│   ├── access-control/             # Authentication & Authorization
│   ├── visualization/              # Chart & Dashboard Generation
│   ├── alert-manager/              # Alert Management
│   └── api-gateway/                # API Gateway & Routing
├── frontend/
│   ├── src/
│   │   ├── components/             # React Components
│   │   ├── services/               # API Services
│   │   ├── hooks/                  # Custom React Hooks
│   │   ├── store/                  # State Management
│   │   └── utils/                  # Utility Functions
│   └── public/
├── shared/
│   ├── models/                     # Data Models (Pydantic)
│   ├── utils/                      # Shared Utilities
│   └── constants/                  # Constants & Configurations
├── tests/
│   ├── unit/                       # Unit Tests
│   ├── integration/                # Integration Tests
│   └── e2e/                        # End-to-End Tests
├── docs/
│   ├── api/                        # API Documentation
│   ├── deployment/                 # Deployment Guides
│   └── user/                       # User Documentation
└── infrastructure/
    ├── docker/                     # Docker Configurations
    ├── kubernetes/                 # K8s Manifests
    └── terraform/                  # Infrastructure as Code
```

### Core Data Models

```python
# User Context
class UserContext:
    user_id: str
    roles: List[str]
    permissions: Dict[str, Any]
    accessible_indexes: List[str]
    session_id: str
    preferences: Dict[str, Any]

# Query Models
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
    
class QueryResult:
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    execution_time: float
    visualization_hint: str

# Visualization Models
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

### API Endpoints

#### Core Chat API
```python
POST /api/v1/chat/query
# Natural language query processing
{
    "query": "Show me failed login attempts in the last 24 hours",
    "conversation_id": "uuid",
    "user_context": {...}
}

GET /api/v1/chat/conversations/{conversation_id}
# Retrieve conversation history

POST /api/v1/chat/clarify
# Handle clarification requests
```

#### SPL Translation API
```python
POST /api/v1/spl/translate
# Convert natural language to SPL
{
    "natural_query": "...",
    "user_context": {...},
    "optimization_level": "standard"
}

POST /api/v1/spl/validate
# Validate SPL syntax and permissions

GET /api/v1/spl/suggestions
# Get query suggestions based on user history
```

#### Access Control API
```python
GET /api/v1/access/permissions
# Get user permissions and accessible data

POST /api/v1/access/check
# Check access to specific resources
{
    "resource_type": "index",
    "resource_name": "security_logs",
    "action": "read"
}

GET /api/v1/access/audit/{user_id}
# Retrieve audit logs for user
```

#### Visualization API
```python
POST /api/v1/viz/generate
# Generate visualization from data
{
    "data": [...],
    "chart_type": "auto",
    "preferences": {...}
}

POST /api/v1/dashboards/create
# Create new dashboard

GET /api/v1/dashboards/{dashboard_id}/export
# Export dashboard in various formats
```

### Development Practices

#### Security Requirements
- **Input Validation**: Sanitize all user inputs
- **SQL Injection Prevention**: Use parameterized queries
- **XSS Protection**: Escape all user-generated content
- **CSRF Protection**: Implement CSRF tokens
- **Rate Limiting**: Prevent abuse with rate limiting
- **Audit Logging**: Log all security-relevant events

#### Performance Considerations
- **Query Optimization**: Implement query caching and optimization
- **Connection Pooling**: Use connection pools for database access
- **Async Processing**: Use async/await for I/O operations
- **Resource Limits**: Implement timeouts and resource limits
- **Caching Strategy**: Cache frequently accessed data

#### Error Handling
```python
class SPLTranslationError(Exception):
    """Raised when SPL translation fails"""
    pass

class AccessDeniedError(Exception):
    """Raised when user lacks required permissions"""
    pass

class QueryTimeoutError(Exception):
    """Raised when query execution times out"""
    pass
```

### Testing Strategy

#### Unit Tests
- Test individual components in isolation
- Mock external dependencies (Splunk API, NLP services)
- Achieve >90% code coverage
- Use pytest for Python, Jest for JavaScript

#### Integration Tests
- Test service-to-service communication
- Test database interactions
- Test API endpoint functionality
- Use test containers for external dependencies

#### End-to-End Tests
- Test complete user workflows
- Test security scenarios
- Test performance under load
- Use Playwright or Cypress for frontend testing

### Deployment Configuration

#### Environment Variables
```bash
# Application Settings
APP_NAME=splunk-mcp-integration
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/splunk_mcp
REDIS_URL=redis://localhost:6379

# Splunk Configuration
SPLUNK_HOST=https://splunk.company.com:8089
SPLUNK_TOKEN=your_splunk_token

# NLP Service Configuration
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4

# Security Settings
SECRET_KEY=your_secret_key
JWT_EXPIRE_MINUTES=30
CORS_ORIGINS=https://your-frontend.com

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

#### Docker Configuration
```dockerfile
# Multi-stage build example
FROM python:3.9-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Development Workflow

### Phase 1: Foundation (Months 1-3)
1. **Setup Development Environment**
   - Configure Docker development environment
   - Set up CI/CD pipeline
   - Implement basic authentication

2. **Core NLP Engine**
   - Implement natural language processing
   - Create intent classification system
   - Build entity extraction capabilities

3. **Basic SPL Translation**
   - Develop simple NL → SPL converter
   - Implement query validation
   - Create basic test suite

### Phase 2: Advanced Features (Months 4-6)
1. **Enhanced Query Processing**
   - Implement complex SPL translation
   - Add query optimization
   - Create conversation context management

2. **Visualization Generation**
   - Build chart generation engine
   - Implement dashboard creation
   - Add export capabilities

3. **Access Control Integration**
   - Integrate with Splunk RBAC
   - Implement permission checking
   - Add audit logging

### Phase 3: Production Ready (Months 7-9)
1. **Alert Management**
   - Build alert creation system
   - Implement notification service
   - Add escalation management

2. **Performance Optimization**
   - Implement caching strategies
   - Add query optimization
   - Optimize database queries

3. **Security Hardening**
   - Conduct security audit
   - Implement additional security measures
   - Add penetration testing

### Phase 4: Enterprise Features (Months 10-12)
1. **Scalability Improvements**
   - Implement horizontal scaling
   - Add load balancing
   - Optimize for high concurrency

2. **Advanced Analytics**
   - Add machine learning capabilities
   - Implement predictive analytics
   - Create anomaly detection

3. **Integration Enhancements**
   - Add third-party integrations
   - Implement SSO solutions
   - Create API documentation

## Key Implementation Notes

### Natural Language Processing
- Use few-shot learning for SPL translation
- Implement context-aware query understanding
- Handle ambiguous queries with clarification prompts
- Support multiple languages if required

### Splunk Integration
- Use Splunk REST API for all data operations
- Implement connection pooling for API calls
- Handle Splunk API rate limiting gracefully
- Cache frequently accessed metadata

### Security Considerations
- Never store Splunk credentials in plaintext
- Implement proper session management
- Use HTTPS for all communications
- Validate all user inputs thoroughly

### Performance Optimization
- Implement query result caching
- Use async processing for long-running queries
- Optimize database queries with proper indexing
- Monitor performance metrics continuously

## Troubleshooting Guide

### Common Issues
1. **SPL Translation Errors**: Check NLP model configuration and training data
2. **Access Denied Errors**: Verify user permissions and RBAC configuration
3. **Performance Issues**: Check query optimization and caching
4. **Authentication Failures**: Verify JWT token configuration and expiration

### Debugging Tools
- Use structured logging for all services
- Implement health checks for all endpoints
- Add performance monitoring and alerting
- Create comprehensive error tracking

## Resources

### Documentation
- [Splunk REST API Reference](https://docs.splunk.com/Documentation/Splunk/latest/RESTREF)
- [SPL Reference](https://docs.splunk.com/Documentation/Splunk/latest/SearchReference)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/docs)

### Development Tools
- **Code Quality**: Black, isort, flake8 for Python
- **Testing**: pytest, coverage.py, Jest
- **API Testing**: Postman, HTTPie
- **Performance**: py-spy, memory_profiler

---

*This guide should be updated as the project evolves and new requirements emerge.*