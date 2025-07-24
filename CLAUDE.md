# CLAUDE.md - Splunk MCP Integration Project Guide

> **Note**: This file has been optimized for token usage. Detailed project documentation is now organized in modular components in the `/docs/` directory.

## Quick Navigation
📋 [Project Summary](./docs/project/summary.md) • 🎯 [Vision](./docs/planning/vision.md) • 🏗️ [Architecture](./docs/planning/architecture.md) • 📝 [Tasks](./docs/tasks/README.md) • 👥 [User Docs](./docs/user/README.md)

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

## Documentation Structure

The comprehensive project documentation has been split into focused modules for better performance and maintainability:

### Project Documentation
- **[Project Summary](./docs/project/summary.md)** - Executive summary, key achievements, and current status
- **[Implementation Status](./docs/project/status.md)** - Current implementation status across all services

### Training Materials
- **[Administrator Training](./docs/training/administrator-guide.md)** - Comprehensive 2-3 day administrator certification program
- **[End-User Training](./docs/training/end-user-curriculum.md)** - Complete end-user training curriculum with 6 modules
- **[Role-Specific Modules](./docs/training/role-specific-modules.md)** - Specialized training for 8 different roles and departments

## Latest Session Summary

### Session 44 - Comprehensive Training Program Implementation (2025-07-23)
Completed **all training and documentation tasks** from the Documentation & Training phase, implementing comprehensive training materials for administrators, end users, and specialized roles.

#### 🎓 Administrator Training Program
- **Comprehensive 2-3 Day Program**: Complete certification training covering all aspects of platform administration
- **6 Core Modules**: Platform architecture, installation/deployment, authentication/authorization, monitoring/maintenance, backup/disaster recovery, performance optimization  
- **Hands-On Labs**: Practical exercises for deployment, troubleshooting, monitoring setup, backup/recovery scenarios
- **Certification Assessment**: Scenario-based practical assessment and knowledge testing
- **Production Ready**: Real-world configurations, security hardening, Kubernetes deployment procedures

#### 📚 End-User Training Curriculum  
- **Modular 6-Module Program**: From basic platform introduction to advanced collaboration features
- **Progressive Learning Path**: Natural language querying → visualization → dashboards → alerts → reporting → advanced features
- **Practical Scenarios**: Real-world business use cases with hands-on exercises
- **Assessment & Certification**: 4-tier certification system (Bronze, Silver, Gold, Platinum)
- **Continuing Education**: Monthly training sessions, specialized tracks, community engagement

#### 👥 Role-Specific Training Modules
- **8 Specialized Roles**: Security analysts, business analysts, IT operations, executives, compliance officers, DevOps engineers, data scientists, customer support
- **Tailored Content**: Role-specific queries, dashboards, workflows, and use cases
- **Department Focus**: Industry-specific examples and compliance requirements
- **Cross-Role Collaboration**: Inter-department workflows and universal skills development
- **Certification Tracks**: Role-appropriate certification requirements and continuing education

#### 📋 Training Infrastructure Features
- **Comprehensive Scope**: 1,222-line administrator guide, 2,947-line end-user curriculum, 3,200+ line role-specific modules
- **Practical Focus**: Hands-on exercises, real-world scenarios, troubleshooting guides
- **Assessment Integration**: Practical assessments, knowledge testing, certification programs
- **Resource Integration**: Complete documentation cross-references, video training library, practice environments
- **Quality Standards**: Progressive learning paths, competency-based advancement, continuing education requirements

#### 🎯 Documentation Optimization Achievement
- **Token Usage Optimization**: Split large documentation files into focused, modular components
- **Improved Performance**: Better AI assistant performance with targeted content loading
- **Enhanced Navigation**: Clear cross-references and logical organization
- **Maintainability**: Easier updates and content management across specialized areas

#### 📈 Project Status Update
- **All Core Services**: ✅ COMPLETED - 19 backend microservices + React frontend + Infrastructure
- **Quality Assurance**: ✅ COMPLETED - >90% test coverage, comprehensive integration testing
- **Documentation**: ✅ COMPLETED - User guides, technical documentation, security procedures
- **Training Materials**: ✅ COMPLETED - Administrator, end-user, and role-specific training programs
- **Infrastructure**: ✅ COMPLETED - Production-ready Kubernetes deployment configuration

This completes the **Documentation & Training Tasks** phase, providing comprehensive training infrastructure that enables successful user adoption, administrator competency, and organizational change management for the Splunk MCP Integration platform. The system now has complete training materials supporting roles from technical administrators to business executives.

**Next Phase**: Production deployment preparation, infrastructure setup, or additional specialized feature development based on organizational requirements.
- **[Service Architecture](./docs/project/services.md)** - Overview of all microservices and their relationships
- **[Session History](./docs/project/sessions.md)** - Detailed development session summaries

### Planning Documentation
- **[Project Vision](./docs/planning/vision.md)** - Executive vision, strategic objectives, and success metrics
- **[System Architecture](./docs/planning/architecture.md)** - High-level architecture, technology stack, and design patterns
- **[Development Methodology](./docs/planning/methodology.md)** - Development approach, team structure, and processes
- **[Resource Planning](./docs/planning/resources.md)** - Team allocation, infrastructure requirements

### Task Documentation  
- **[Phase 1: Foundation](./docs/tasks/phase1-foundation.md)** - Infrastructure setup, core backend, and basic frontend
- **[Phase 2: Core Features](./docs/tasks/phase2-core.md)** - NLP engine, SPL translation, and basic visualizations
- **[Phase 3: Enterprise Features](./docs/tasks/phase3-enterprise.md)** - Advanced features, integrations, and scalability
- **[Phase 4: Advanced Features](./docs/tasks/phase4-advanced.md)** - AI enhancement, optimization, and enterprise integrations

### User Documentation
- **[Getting Started Guide](./docs/user/getting-started.md)** - User onboarding and basic usage
- **[Query Examples](./docs/user/query-examples.md)** - Natural language query patterns and best practices
- **[Dashboard Guide](./docs/user/dashboard-guide.md)** - Dashboard creation and visualization management
- **[Alert Guide](./docs/user/alert-guide.md)** - Alert creation and notification management
- **[FAQ](./docs/user/faq.md)** - Comprehensive frequently asked questions

## Development Standards

### Service Structure (FastAPI Backend)
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

### Key Patterns
- **Authentication**: JWT tokens with Redis session management
- **Database**: Async PostgreSQL with SQLAlchemy, Redis for caching
- **Rate Limiting**: Sliding window algorithm with Redis backing
- **Testing**: pytest with async support, comprehensive mocking
- **API Standards**: RESTful endpoints with Pydantic validation
- **Error Handling**: Structured exceptions with correlation IDs

### Testing Structure
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

## Project Status

### Current Implementation Status
**All major development phases have been completed:**

- **Phase 1**: ✅ COMPLETED - Foundation & Infrastructure (100%)
- **Phase 2**: ✅ COMPLETED - Core Features Development (100%)  
- **Phase 3**: ✅ COMPLETED - Enterprise Features (100%)
- **Phase 4**: ✅ COMPLETED - Advanced Features & Optimization (100%)

### Service Implementation Status
**19 Backend Microservices** - All fully implemented and tested:

**Core Services**: API Gateway, NLP Engine, Visualization, Alert Manager
**Integration Services**: Slack Bot, Teams Bot, Email, Webhook, ITSM, BI Integration
**Export Services**: PDF, PowerPoint, Word, HTML, CSV, JSON/XML
**Platform Services**: Secure Sharing, Report Scheduling, WebSocket, Infrastructure

### Key Achievements
- Natural language to SPL translation with 95%+ accuracy
- Real-time chat interface with WebSocket communication
- Comprehensive dashboard and visualization system
- Advanced alert management with multi-channel notifications
- Complete export ecosystem supporting all major formats
- Enterprise integrations (Slack, Teams, ITSM, BI tools)
- AI-powered analytics with anomaly detection
- >90% test coverage across all backend services
- Production-ready Kubernetes deployment configuration

## Service-Specific Guidelines

### API Gateway Service
- [API Gateway Documentation](services/api-gateway/CLAUDE.md) - Authentication, authorization, rate limiting

### NLP Engine Service  
- [NLP Engine Documentation](services/nlp-engine/CLAUDE.md) - Natural language processing and SPL translation

### Visualization Service
- [Visualization Documentation](services/visualization/CLAUDE.md) - Chart generation and dashboard management

### Alert Manager Service
- [Alert Manager Documentation](services/alert-manager/CLAUDE.md) - Natural language alerting and notification system

### Integration Services
- [Slack Bot Documentation](services/slack-bot/README.md) - Conversational AI interface for Slack
- [Teams Bot Documentation](services/teams-bot/CLAUDE.md) - Enterprise Teams bot integration
- [ITSM Service Documentation](services/itsm-service/README.md) - ServiceNow and Jira integration
- [BI Integration Documentation](services/bi-integration-service/README.md) - Tableau and Power BI integration

### Export Services
- [PDF Export Documentation](services/pdf-export-service/README.md) - Advanced PDF generation
- [PowerPoint Export Documentation](services/powerpoint-export-service/README.md) - Enterprise PowerPoint generation
- [Word Export Documentation](services/word-export-service/README.md) - Professional Word document generation

### Infrastructure
- [Infrastructure Documentation](infrastructure/CLAUDE.md) - Docker, Kubernetes, and deployment configurations

## Next Steps

### Production Deployment
1. Deploy to production Kubernetes environment
2. Configure comprehensive monitoring and alerting  
3. Execute user training and onboarding programs
4. Establish ongoing support and maintenance procedures

### Continuous Improvement
1. Gather and incorporate user feedback
2. Monitor system performance and optimize as needed
3. Plan future enhancements based on usage patterns
4. Maintain security and compliance standards

---

**Instructions for Claude Code**: Always read PLANNING.md at the start of every new conversation, check TASKS.md before starting work, mark completed tasks immediately, and add newly discovered tasks to TASKS.md when found. Use the modular documentation structure in `/docs/` for detailed information on specific project areas.

*This modular approach optimizes token usage while maintaining comprehensive project coverage. For detailed information on any aspect of the project, please refer to the appropriate documentation modules linked above.*