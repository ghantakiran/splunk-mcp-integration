# Splunk MCP Integration - API Documentation

## Overview

The Splunk MCP Integration platform provides a comprehensive REST API that enables natural language interactions with Splunk data through multiple microservices. This documentation covers all API endpoints, authentication methods, and integration patterns.

## Quick Start

### Base URLs
- **API Gateway**: `http://localhost:8000` (Development) / `https://api.splunk-mcp.com` (Production)
- **Services** are accessed through the API Gateway with service-specific prefixes

### Authentication
All API requests require JWT authentication:

```bash
# Obtain access token
curl -X POST /auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" /api/v1/nlp/process-query
```

### Quick Example
```bash
# Process a natural language query
curl -X POST /api/v1/nlp/process-query \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show me errors from the last hour",
    "conversation_id": "conv_123"
  }'
```

## Service APIs

### 1. [API Gateway Service](./api-gateway.md)
- Authentication & Authorization
- Rate Limiting
- Request Routing
- Health Monitoring

### 2. [NLP Engine Service](./nlp-engine.md)
- Natural Language Processing
- SPL Translation
- Intent Classification
- Context Management

### 3. [Visualization Service](./visualization.md)
- Chart Generation
- Dashboard Management
- Interactive Visualizations
- Export Capabilities

### 4. [Alert Manager Service](./alert-manager.md)
- Alert Creation & Management
- Multi-Channel Notifications
- Escalation Workflows
- Alert Analytics

### 5. [Email Integration Service](./email-service.md)
- Email Query Processing
- Report Delivery
- Subscription Management
- Template System

### 6. [Webhook Service](./webhook-service.md)
- Webhook Management
- Event Processing
- Delivery Tracking
- Security & Authentication

### 7. [Export Services](./export-services.md)
- PDF Export Service
- PowerPoint Export Service
- Word Export Service
- CSV Export Service
- HTML Report Service

### 8. [Integration Services](./integration-services.md)
- ITSM Service (ServiceNow, Jira)
- BI Integration Service (Tableau, Power BI)
- Slack Bot Service
- Microsoft Teams Bot Service

### 9. [Report Scheduling Service](./report-scheduling.md)
- Automated Report Generation
- Schedule Management
- Delivery System
- Version Control

## Common Patterns

### Response Format
All API responses follow a consistent format:

```json
{
  "success": true,
  "data": {},
  "metadata": {
    "timestamp": "2025-01-22T10:30:00Z",
    "correlation_id": "uuid",
    "version": "1.0"
  },
  "errors": []
}
```

### Error Handling
Error responses include detailed information:

```json
{
  "success": false,
  "data": null,
  "metadata": {
    "timestamp": "2025-01-22T10:30:00Z",
    "correlation_id": "uuid",
    "version": "1.0"
  },
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input parameters",
      "field": "query",
      "details": {}
    }
  ]
}
```

### Pagination
List endpoints support pagination:

```bash
GET /api/v1/resource?page=1&limit=50&sort=created_at&order=desc
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 500,
    "pages": 10,
    "has_next": true,
    "has_prev": false
  }
}
```

### Rate Limiting
Rate limits are enforced per user and endpoint:
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Default Limits**: 1000 requests/hour for authenticated users
- **Burst Protection**: 10 requests/second maximum

## Security

### Authentication Methods
1. **JWT Bearer Tokens** (Primary)
2. **API Keys** (Service-to-service)
3. **OAuth 2.0** (Third-party integrations)

### Authorization
Role-based access control (RBAC) with permissions:
- `read`: View resources
- `write`: Create/update resources
- `delete`: Delete resources
- `admin`: Administrative operations

### Security Headers
All responses include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

## SDKs and Libraries

### Python SDK
```python
from splunk_mcp import SplunkMCPClient

client = SplunkMCPClient(
    base_url="https://api.splunk-mcp.com",
    api_key="your_api_key"
)

result = client.nlp.process_query("show me errors from last hour")
```

### JavaScript SDK
```javascript
import { SplunkMCPClient } from '@splunk-mcp/sdk';

const client = new SplunkMCPClient({
  baseUrl: 'https://api.splunk-mcp.com',
  apiKey: 'your_api_key'
});

const result = await client.nlp.processQuery('show me errors from last hour');
```

## WebSocket API

Real-time communication is available via WebSocket connections:

```javascript
const ws = new WebSocket('wss://api.splunk-mcp.com/ws');
ws.send(JSON.stringify({
  type: 'query',
  data: { query: 'show me real-time errors' }
}));
```

## Monitoring and Health

### Health Endpoints
- `GET /health` - Overall system health
- `GET /health/detailed` - Detailed service health
- `GET /ready` - Readiness check
- `GET /metrics` - Prometheus metrics

### System Status
Check real-time system status:
```bash
curl /api/v1/system/status
```

## Migration Guide

### API Versioning
- Current version: `v1`
- Backward compatibility maintained for 12 months
- Deprecation notices provided 6 months in advance

### Breaking Changes
See [CHANGELOG.md](../CHANGELOG.md) for version-specific changes.

## Support and Resources

### Documentation
- [Getting Started Guide](../getting-started.md)
- [Developer Guide](../developer-guide.md)
- [Deployment Guide](../deployment.md)
- [Troubleshooting Guide](../troubleshooting.md)

### Community
- **GitHub**: [Issues and Discussions](https://github.com/splunk-mcp/issues)
- **Stack Overflow**: Tag `splunk-mcp`
- **Documentation**: [Official Docs](https://docs.splunk-mcp.com)

### Contact
- **Technical Support**: support@splunk-mcp.com
- **Sales/Business**: sales@splunk-mcp.com
- **Security Issues**: security@splunk-mcp.com

---

*Last Updated: January 22, 2025*
*API Version: 1.0*