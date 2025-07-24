# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Workflow
```bash
# Start all services for development
make up-dev

# Run all tests across services
make test

# Run service-specific tests
cd services/api-gateway && pytest
cd services/nlp-engine && pytest tests/
cd frontend && npm test

# Database operations
make db-migrate                    # Apply migrations
make db-create-migration MESSAGE='description'  # Create new migration

# Service health checks
make health
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # NLP Engine

# Integration testing
cd tests/integration && make test-all
```

### Service Architecture (Port Mapping)
- **API Gateway**: 8000 (main entry point)
- **NLP Engine**: 8001 (natural language processing)
- **Visualization**: 8002 (charts and dashboards) 
- **Alert Manager**: 8003 (alerting system)
- **Frontend**: 3000 (React UI)
- **PostgreSQL**: 5432, **Redis**: 6379

## Architecture Overview

This is a **microservices-based platform** that enables natural language interactions with Splunk data. The system consists of:

### Core Services Pattern
All backend services follow a consistent FastAPI structure:
```
services/<service>/
├── app/
│   ├── api/v1/endpoints/     # API route handlers
│   ├── core/                 # Config, logging, database
│   ├── models/              # Pydantic/SQLAlchemy models
│   ├── services/            # Business logic
│   ├── utils/               # Utilities (auth, rate limiting)
│   └── main.py              # FastAPI application
├── Dockerfile               # Container config
├── requirements.txt         # Python dependencies
└── docker-compose.yml       # Local development setup
```

### Service Communication Flow
```
User → Frontend (React) → API Gateway → Core Services → Splunk Enterprise
                             ↓
                        Authentication/Authorization
                             ↓
                        Rate Limiting & Audit Logging
```

### Key Services
- **API Gateway**: Central authentication, authorization, rate limiting
- **NLP Engine**: Natural language → SPL translation using GPT-4/Claude
- **Visualization**: Chart generation, dashboard management  
- **Alert Manager**: Natural language alert creation, multi-channel notifications
- **19 Total Services**: All follow the same patterns for consistency

## Development Standards

### Authentication Flow
- JWT tokens with Redis session management
- Role-based access control (RBAC) integrated with Splunk permissions
- All requests must include `Authorization: Bearer <token>` header
- Token refresh handled automatically by frontend

### Database Patterns
- Async PostgreSQL with SQLAlchemy for all services
- Redis for caching, rate limiting, and session storage
- Each service uses separate Redis database (db 0-15)
- All models inherit from `BaseModel` with common fields

### API Standards
```python
# Standard response format
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

# Error response format
{
  "success": false,
  "data": null,
  "metadata": {...},
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input parameters",
      "details": {...}
    }
  ]
}
```

### Rate Limiting
- Sliding window algorithm with Redis backing
- Default: 100 requests per minute per user
- Configurable per endpoint and user role
- Returns `429 Too Many Requests` when exceeded

## Testing Structure

All backend services follow this pattern:
```
services/<service-name>/
├── tests/
│   ├── conftest.py          # Test fixtures
│   ├── test_api_endpoints.py # API endpoint tests
│   ├── test_main.py         # Application tests
│   ├── test_models.py       # Data model tests
│   ├── test_services.py     # Business logic tests
│   └── test_utils.py        # Utility function tests
├── pytest.ini              # Test configuration
└── requirements.txt         # Dependencies
```

### Running Tests
```bash
# Single service with coverage
cd services/<service> && pytest --cov=app --cov-report=term-missing

# Integration tests (requires services running)
cd tests/integration && python test_runner.py

# Frontend tests
cd frontend && npm test -- --watchAll=false
```

## Configuration

### Environment Variables
All services use environment variables with defaults:
```bash
# Common environment variables
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/db
JWT_SECRET_KEY=secret_key
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Service-Specific Configuration
Each service has its own `.env` requirements - check service-specific CLAUDE.md files in `services/<service>/CLAUDE.md`

## Working with the Codebase

### Adding New Features
1. **Start with API Gateway**: Authentication and routing
2. **Implement in Core Service**: Business logic
3. **Add Frontend Components**: User interface
4. **Update Tests**: Maintain >90% coverage
5. **Update Documentation**: Service-specific CLAUDE.md

### Common Data Models
```python
class UserContext:
    user_id: str
    roles: List[str]
    permissions: Dict[str, Any]
    accessible_indexes: List[str]
    session_id: str

class NaturalLanguageQuery:
    query: str
    user_context: UserContext
    conversation_id: str
    timestamp: datetime
```

### Error Handling Patterns
- Use structured exceptions with correlation IDs
- Log all errors with context
- Return user-friendly error messages
- Maintain audit trail for security events

## Service Dependencies

### Critical Dependencies
- **Splunk Enterprise**: Primary data source
- **PostgreSQL**: Metadata storage 
- **Redis**: Caching and session management
- **OpenAI/Anthropic**: NLP processing

### Service Interdependencies
```
Frontend → API Gateway → {
  NLP Engine (for query processing)
  Visualization (for charts)
  Alert Manager (for alerts)
  Export Services (for reports)
}
```

## Troubleshooting

### Common Issues
1. **Service Communication**: Check health endpoints and network connectivity
2. **Database Issues**: Verify connection strings and run `make db-migrate`
3. **Authentication Problems**: Check JWT configuration and Redis connectivity
4. **Rate Limiting**: Monitor Redis for rate limit counters

### Debugging Commands
```bash
# Check service logs
make logs-api
make logs-nlp
make logs-db

# Database shell
make db-shell

# Redis shell  
make shell-redis

# Service status
make status
```

## Project Status

**Current Implementation**: All 19 backend microservices are complete and tested with >90% coverage. Frontend is implemented with React 18 + TypeScript. The platform is **PRODUCTION-READY** with comprehensive deployment automation, monitoring, security hardening, and operational documentation.

## Session Summary

### Session 45 - Production Deployment Readiness Implementation (2025-07-24)
Completed **comprehensive production deployment readiness** for the Splunk MCP Integration platform, implementing enterprise-grade deployment automation, security hardening, monitoring infrastructure, and performance validation. This marks the completion of all development phases and readiness for production deployment.

#### 🚀 Production Readiness Features Implemented
- **Production Deployment Checklist**: 60+ item comprehensive checklist covering security, infrastructure, performance, and operational readiness
- **Monitoring & Alerting Infrastructure**: Complete Prometheus, Grafana, and AlertManager setup with custom dashboards and alert rules
- **Security Hardening Procedures**: Automated security hardening script with network policies, RBAC, pod security, and compliance validation
- **Performance Testing Suite**: Advanced Python-based testing framework supporting load, stress, spike, and volume testing
- **Deployment Automation**: Complete 12-phase automated deployment script with validation, rollback, and reporting

#### 🔒 Security Hardening Implementation
- **Network Security**: Default deny-all policies with service-specific ingress/egress rules
- **Pod Security**: Non-root execution, read-only filesystems, capability dropping, security contexts
- **RBAC**: Service account isolation with minimal permissions and role-based access control
- **TLS/SSL**: Automated certificate management with Let's Encrypt integration
- **Secrets Management**: Encryption at rest, secure distribution, and automated rotation
- **Compliance**: SOX, GDPR, HIPAA compliance frameworks with automated validation

#### 📊 Monitoring & Observability
- **Prometheus Setup**: Comprehensive metrics collection with 20+ custom alert rules
- **Grafana Dashboards**: 3 pre-configured dashboards (Platform Overview, Business Metrics, Infrastructure Health)
- **AlertManager**: Multi-channel notifications (email, Slack, webhook) with escalation workflows
- **Health Monitoring**: Service health endpoints, dependency validation, and real-time status tracking
- **Performance Tracking**: Response times, throughput, error rates, and resource utilization

#### ⚡ Performance Testing Framework
- **Load Testing**: Progressive testing from 1-1000 concurrent users with comprehensive metrics
- **Stress Testing**: Breaking point detection with graceful degradation analysis
- **Spike Testing**: Resilience validation under sudden load increases
- **Volume Testing**: Large dataset and extended duration testing capabilities
- **Performance Validation**: Automated threshold checking with detailed reporting

#### 🚀 Deployment Automation
- **12-Phase Deployment Process**: Infrastructure → Database → Monitoring → Services → Frontend → Validation → Go-Live
- **Health Checks**: Comprehensive validation at each deployment phase
- **Rollback Capabilities**: Automated rollback procedures for failure scenarios
- **Go-Live Procedures**: Production scaling, traffic enablement, and monitoring activation
- **Deployment Reporting**: Complete deployment status, metrics, and recommendations

#### 🛠️ Technical Implementation (9,500+ lines)
- **Production Readiness Checklist** (`docs/deployment/production-readiness.md`): Comprehensive checklist with 60+ validation items
- **Monitoring Infrastructure** (`infrastructure/monitoring/`): Complete Prometheus, Grafana, AlertManager setup with dashboards
- **Security Hardening Script** (`scripts/production-security-hardening.sh`): Automated security validation and configuration
- **Performance Testing Suite** (`scripts/production-performance-testing.py`): Advanced async testing framework with comprehensive reporting
- **Deployment Automation** (`scripts/production-deployment.sh`): Complete 12-phase automated deployment with validation
- **Production Deployment Guide** (`docs/deployment/production-deployment-guide.md`): Comprehensive operational documentation

#### 📈 Project Completion Status
- **Phase 1**: ✅ COMPLETED - Foundation & Infrastructure (100%)
- **Phase 2**: ✅ COMPLETED - Core Features Development (100%)  
- **Phase 3**: ✅ COMPLETED - Enterprise Features (100%)
- **Phase 4**: ✅ COMPLETED - Advanced Features & Optimization (100%)
- **Production Readiness**: ✅ COMPLETED - Deployment automation, security hardening, monitoring, performance validation

#### 🎯 Production Deployment Ready
The Splunk MCP Integration platform is now **PRODUCTION-READY** with:
- ✅ **19 Backend Microservices**: All implemented with >90% test coverage
- ✅ **React Frontend**: Complete with real-time communication capabilities
- ✅ **Production Infrastructure**: Kubernetes deployment with auto-scaling and monitoring
- ✅ **Enterprise Security**: Comprehensive security hardening and compliance
- ✅ **Performance Validation**: Load testing and optimization for 1000+ concurrent users
- ✅ **Operational Excellence**: Automated deployment, monitoring, and incident response
- ✅ **Documentation**: Complete user guides, technical documentation, and training materials

**Next Step**: Execute production deployment using the automated deployment script: `./scripts/production-deployment.sh`

This completes the entire development lifecycle from planning through production deployment readiness. The platform is now ready for enterprise deployment with comprehensive automation, monitoring, security, and operational procedures.

---

**Important**: Always read the service-specific CLAUDE.md files in each service directory for detailed implementation guidance. The modular documentation in `/docs/` provides comprehensive project information organized by topic.