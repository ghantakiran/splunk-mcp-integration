# User Adoption and Feedback Collection Service

A comprehensive microservice for tracking user onboarding, adoption metrics, and feedback collection in the Splunk MCP Integration platform.

## Overview

This service provides sophisticated user adoption tracking, onboarding management, and feedback collection capabilities with automated analytics and notifications.

## Features

### 🎯 User Onboarding Management
- **8-Step Onboarding Process**: Welcome tour, first query, dashboard creation, visualizations, alerts, exports, sharing, and profile completion
- **Progress Tracking**: Real-time onboarding progress with completion time metrics
- **Bottleneck Identification**: Automated analysis of onboarding pain points
- **Personalized Recommendations**: AI-driven suggestions for improving user experience

### 📊 Adoption Analytics
- **Comprehensive Scoring**: Multi-factor adoption score calculation (login frequency, feature usage, engagement depth, content creation)
- **Engagement Levels**: Automatic classification (new, beginner, intermediate, advanced, expert)
- **Feature Adoption Tracking**: Detailed analysis of feature usage patterns
- **Cohort Analysis**: User retention and engagement trends over time

### 💬 Feedback Collection System
- **Multi-Type Feedback**: Bug reports, feature requests, general feedback, and suggestions
- **Automated Categorization**: AI-powered feedback classification using keyword analysis
- **Sentiment Analysis**: Automatic sentiment detection with confidence scoring
- **Survey Management**: Dynamic survey creation with targeting rules and automation

### 📈 Analytics and Insights
- **Funnel Analysis**: User journey progression tracking
- **Performance Metrics**: Response times, resolution rates, and satisfaction scores
- **Trend Analysis**: Daily, weekly, and monthly adoption trends
- **Actionable Insights**: Automated recommendations for improving user adoption

### 🔔 Notification System
- **Multi-Channel Alerts**: Email, Slack, and Teams notifications
- **Event-Based Triggers**: Feedback submissions, onboarding completion, low engagement alerts
- **Survey Invitations**: Automated survey distribution based on user behavior
- **Milestone Celebrations**: Achievement notifications and adoption milestones

## Architecture

### Service Structure
```
services/user-adoption-service/
├── app/
│   ├── api/v1/endpoints/     # REST API endpoints
│   │   ├── onboarding.py     # Onboarding management
│   │   ├── feedback.py       # Feedback collection
│   │   └── adoption.py       # Adoption metrics
│   ├── core/                 # Core configurations
│   │   ├── config.py         # Environment configuration
│   │   └── database.py       # Database connections
│   ├── models/               # Data models
│   │   └── adoption_models.py # SQLAlchemy models
│   ├── services/             # Business logic
│   │   ├── onboarding_service.py    # Onboarding logic
│   │   ├── feedback_service.py      # Feedback processing
│   │   ├── adoption_service.py      # Adoption calculations
│   │   └── notification_service.py  # Notifications
│   ├── utils/                # Utilities
│   │   └── auth.py           # Authentication
│   └── main.py               # FastAPI application
├── Dockerfile                # Container configuration
├── docker-compose.yml        # Local development setup
├── requirements.txt          # Python dependencies
└── README.md                 # Documentation
```

### Database Models
- **UserProfile**: Core user information and adoption metrics
- **OnboardingStep**: Individual onboarding step tracking
- **FeedbackSubmission**: User feedback and categorization
- **FeedbackFollowUp**: Response tracking and communication
- **AdoptionMetric**: Detailed usage and engagement metrics
- **SurveyTemplate**: Dynamic survey configuration
- **SurveyResponse**: Survey submission and analysis

## API Endpoints

### Onboarding Management
- `POST /api/v1/onboarding/users` - Create user profile
- `GET /api/v1/onboarding/users/{user_id}` - Get user profile
- `GET /api/v1/onboarding/users/{user_id}/steps` - Get onboarding steps
- `POST /api/v1/onboarding/users/{user_id}/steps/{step_id}/start` - Start step
- `POST /api/v1/onboarding/users/{user_id}/steps/{step_id}/complete` - Complete step
- `GET /api/v1/onboarding/users/{user_id}/progress` - Get progress details
- `GET /api/v1/onboarding/analytics/onboarding` - Onboarding analytics

### Feedback Collection
- `POST /api/v1/feedback/submit` - Submit feedback
- `GET /api/v1/feedback/submissions` - Get user submissions
- `GET /api/v1/feedback/submissions/{feedback_id}` - Get feedback details
- `POST /api/v1/feedback/submissions/{feedback_id}/follow-up` - Add response
- `GET /api/v1/feedback/analytics/feedback` - Feedback analytics
- `POST /api/v1/feedback/surveys/templates` - Create survey template
- `GET /api/v1/feedback/surveys/active` - Get active surveys
- `POST /api/v1/feedback/surveys/responses` - Submit survey response

### Adoption Analytics
- `POST /api/v1/adoption/metrics` - Track adoption metric
- `GET /api/v1/adoption/metrics/user/{user_id}` - Get user metrics
- `GET /api/v1/adoption/metrics/features` - Feature adoption metrics
- `GET /api/v1/adoption/metrics/engagement` - Engagement analytics
- `GET /api/v1/adoption/metrics/cohort-analysis` - Cohort analysis
- `GET /api/v1/adoption/metrics/funnel-analysis` - Funnel analysis
- `GET /api/v1/adoption/users/low-engagement` - Low engagement users

## Configuration

### Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://user:pass@host:5432/user_adoption_db
REDIS_URL=redis://host:6379/10

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=24

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@domain.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@yourcompany.com

# Notification Webhooks
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
ADMIN_EMAIL_ADDRESSES=admin1@company.com,admin2@company.com

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=production
DEBUG=false
```

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (optional)

### Local Development
```bash
# Clone and setup
cd services/user-adoption-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Database setup
createdb user_adoption_db
export DATABASE_URL="postgresql://user:pass@localhost:5432/user_adoption_db"
export REDIS_URL="redis://localhost:6379/10"

# Run the service
uvicorn app.main:app --reload --port 8020
```

### Docker Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f user-adoption-service

# Stop services
docker-compose down
```

## Testing

### Unit Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_onboarding.py -v
```

### API Testing
```bash
# Health check
curl http://localhost:8020/health

# API documentation
open http://localhost:8020/docs
```

## Monitoring and Observability

### Health Endpoints
- `/health` - Basic health check
- `/api/v1/health` - Detailed health status
- `/metrics` - Prometheus metrics

### Key Metrics
- **User Adoption Scores**: Individual and aggregate adoption metrics
- **Onboarding Performance**: Completion rates, bottleneck identification
- **Feedback Volume**: Submission rates, resolution times
- **System Performance**: Response times, error rates, resource usage

### Alerts and Notifications
- **Low Engagement**: Users below adoption thresholds
- **Onboarding Issues**: Steps with high abandonment rates
- **Feedback Volume**: High-priority feedback requiring attention
- **System Health**: Service availability and performance issues

## Integration

### Authentication
This service integrates with the platform's JWT-based authentication system. Users are authenticated via the API Gateway and user context is passed through JWT tokens.

### Database Integration
- **PostgreSQL**: Primary storage for user profiles, onboarding steps, feedback, and metrics
- **Redis**: Caching, session management, and real-time data storage

### External Services
- **Email**: SMTP integration for notifications and survey invitations
- **Slack/Teams**: Webhook integration for real-time alerts and celebrations
- **AI Services**: Integration with feedback categorization and sentiment analysis

## Security

### Data Protection
- **PII Handling**: Secure handling of personally identifiable information
- **Anonymous Feedback**: Support for anonymous feedback submission
- **Data Retention**: Configurable data retention policies
- **Access Control**: Role-based access to analytics and admin functions

### Authentication & Authorization
- **JWT Tokens**: Secure token-based authentication
- **Role-Based Access**: Admin and user role separation
- **Permission Checks**: Granular permission validation
- **Token Blacklisting**: Secure token revocation

## Deployment

### Production Deployment
```yaml
# Kubernetes deployment example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-adoption-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-adoption-service
  template:
    metadata:
      labels:
        app: user-adoption-service
    spec:
      containers:
      - name: user-adoption-service
        image: user-adoption-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secrets
              key: url
```

### Scaling Considerations
- **Horizontal Scaling**: Stateless design supports multiple replicas
- **Database Connections**: Connection pooling for optimal performance
- **Caching Strategy**: Redis-based caching for frequently accessed data
- **Async Operations**: Background task processing for notifications

## Contributing

### Development Guidelines
1. **Code Style**: Follow PEP 8 and use Black for formatting
2. **Testing**: Maintain >90% test coverage
3. **Documentation**: Update API documentation for new endpoints
4. **Logging**: Use structured logging for observability

### Commit Guidelines
- **Feature**: `feat: add user onboarding analytics`
- **Bug Fix**: `fix: resolve feedback categorization issue`
- **Documentation**: `docs: update API documentation`
- **Refactor**: `refactor: optimize adoption score calculation`

## License

This service is part of the Splunk MCP Integration platform and follows the project's licensing terms.

## Support

For issues, questions, or contributions:
- **Documentation**: [Platform Documentation](../../docs/README.md)
- **API Reference**: [OpenAPI Specification](http://localhost:8020/docs)
- **Monitoring**: [Service Dashboard](http://localhost:3000/dashboard/user-adoption)

---

**Service Status**: Production Ready ✅  
**Version**: 1.0.0  
**Last Updated**: 2025-01-27