# Email Integration Service API

## Overview
The Email Integration Service enables natural language Splunk queries via email, automated report generation, and delivery system with comprehensive subscription management.

**Base URL**: `/api/v1/email`
**Port**: 8006 (Development)

## Authentication
All endpoints require JWT authentication:
```bash
Authorization: Bearer YOUR_JWT_TOKEN
```

## Core Endpoints

### Email Processing

#### Process Email Query
Process a natural language query received via email.

```http
POST /api/v1/email/process
```

**Request Body:**
```json
{
  "from": "user@company.com",
  "subject": "Query: Show me errors from last hour",
  "body": "Please show me all errors from the last hour with severity high",
  "message_id": "msg_12345",
  "received_at": "2025-01-22T10:30:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query_id": "q_789",
    "processed_at": "2025-01-22T10:30:15Z",
    "spl_query": "search earliest=-1h severity=high",
    "email_sent": true,
    "response_message_id": "msg_67890"
  }
}
```

#### Send Query Response
Send query results via email response.

```http
POST /api/v1/email/send-response
```

**Request Body:**
```json
{
  "to": "user@company.com",
  "query_id": "q_789",
  "results": {...},
  "format": "html",
  "include_attachments": true
}
```

### Report Management

#### Create Report Subscription
Set up automated report delivery via email.

```http
POST /api/v1/email/reports/subscribe
```

**Request Body:**
```json
{
  "user_email": "user@company.com",
  "report_name": "Daily Error Summary",
  "query": "search earliest=-24h severity=error | stats count by source",
  "schedule": {
    "frequency": "daily",
    "time": "09:00",
    "timezone": "UTC",
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
  },
  "format": "pdf",
  "template": "executive_summary"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "subscription_id": "sub_456",
    "status": "active",
    "next_delivery": "2025-01-23T09:00:00Z",
    "created_at": "2025-01-22T10:30:00Z"
  }
}
```

#### List Report Subscriptions
Get all report subscriptions for a user.

```http
GET /api/v1/email/reports/subscriptions
```

**Query Parameters:**
- `user_email` (string): Filter by user email
- `status` (string): Filter by status (active, paused, disabled)
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)

#### Update Report Subscription
Modify an existing report subscription.

```http
PUT /api/v1/email/reports/subscriptions/{subscription_id}
```

#### Delete Report Subscription
Remove a report subscription.

```http
DELETE /api/v1/email/reports/subscriptions/{subscription_id}
```

### Template Management

#### List Email Templates
Get available email templates.

```http
GET /api/v1/email/templates
```

**Response:**
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "id": "executive_summary",
        "name": "Executive Summary",
        "description": "Professional report template for executives",
        "format": "html",
        "variables": ["report_title", "date_range", "key_metrics"]
      }
    ]
  }
}
```

#### Create Custom Template
Create a new email template.

```http
POST /api/v1/email/templates
```

**Request Body:**
```json
{
  "name": "Custom Alert Template",
  "description": "Custom template for security alerts",
  "format": "html",
  "content": "<html>...",
  "variables": ["alert_name", "severity", "description"],
  "category": "alerts"
}
```

### User Management

#### Get User Preferences
Retrieve user email preferences.

```http
GET /api/v1/email/users/{user_id}/preferences
```

#### Update User Preferences
Update user email preferences.

```http
PUT /api/v1/email/users/{user_id}/preferences
```

**Request Body:**
```json
{
  "email_notifications": true,
  "digest_frequency": "daily",
  "preferred_format": "html",
  "max_attachment_size": "10MB",
  "timezone": "America/New_York"
}
```

### Analytics

#### Email Analytics
Get email service analytics.

```http
GET /api/v1/email/analytics
```

**Query Parameters:**
- `start_date` (string): Start date (ISO format)
- `end_date` (string): End date (ISO format)
- `user_email` (string): Filter by user email
- `report_type` (string): Filter by report type

**Response:**
```json
{
  "success": true,
  "data": {
    "total_emails_sent": 1250,
    "queries_processed": 456,
    "reports_delivered": 89,
    "delivery_rate": 0.95,
    "top_queries": [...],
    "user_activity": {...}
  }
}
```

## Configuration

### Environment Variables
```bash
# Email Server Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true

# IMAP Configuration (for receiving emails)
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=your_email@gmail.com
IMAP_PASSWORD=your_app_password
IMAP_USE_SSL=true

# Service Configuration
EMAIL_SERVICE_PORT=8006
METRICS_PORT=9006
REDIS_URL=redis://localhost:6379/6
DATABASE_URL=postgresql://user:pass@localhost:5432/email_db

# Rate Limiting
RATE_LIMIT_PER_HOUR=100
RATE_LIMIT_PER_DOMAIN=500
```

## Error Codes

| Code | Description |
|------|-------------|
| `EMAIL_001` | Invalid email format |
| `EMAIL_002` | SMTP connection failed |
| `EMAIL_003` | Template not found |
| `EMAIL_004` | Subscription limit exceeded |
| `EMAIL_005` | Report generation failed |
| `EMAIL_006` | Authentication failed |
| `EMAIL_007` | Rate limit exceeded |

## Usage Examples

### Python SDK
```python
from splunk_mcp import EmailService

email_service = EmailService(api_key="your_api_key")

# Process email query
result = email_service.process_query(
    from_email="user@company.com",
    query="show me errors from last hour"
)

# Create report subscription
subscription = email_service.create_subscription(
    user_email="user@company.com",
    report_name="Daily Summary",
    schedule={"frequency": "daily", "time": "09:00"}
)
```

### cURL Examples
```bash
# Process email query
curl -X POST /api/v1/email/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"from": "user@company.com", "body": "show errors"}'

# Create subscription
curl -X POST /api/v1/email/reports/subscribe \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_email": "user@company.com", "report_name": "Daily Report"}'
```

## WebSocket Integration

For real-time email processing updates:

```javascript
const ws = new WebSocket('ws://localhost:8006/ws');

ws.on('message', (data) => {
  const message = JSON.parse(data);
  if (message.type === 'email_processed') {
    console.log('Email processed:', message.data);
  }
});
```

## Security Considerations

### Email Security
- All email content is sanitized to prevent XSS
- SMTP connections use TLS encryption
- Email addresses are validated against whitelist/blacklist
- Attachment scanning for malicious content

### Authentication
- JWT tokens required for all operations
- Service-to-service authentication for email processing
- Rate limiting to prevent abuse
- Audit logging for all email operations

### Data Privacy
- Email content is not stored permanently
- Personal data handling complies with GDPR
- Encryption for sensitive email metadata
- Automatic cleanup of processed emails

## Monitoring

### Health Checks
```bash
# Service health
curl /api/v1/email/health

# Email server connectivity
curl /api/v1/email/health/smtp

# Database connectivity
curl /api/v1/email/health/database
```

### Metrics
Available at `/api/v1/email/metrics`:
- `email_service_requests_total`
- `email_service_processing_duration`
- `email_service_emails_sent_total`
- `email_service_delivery_success_rate`

## Integration Examples

### Slack Integration
```python
# Forward Slack queries via email
@slack_app.event("message")
def handle_message(event):
    if "@email-query" in event["text"]:
        email_service.process_query(
            from_email=f"{event['user']}@slack.local",
            query=event["text"].replace("@email-query", "")
        )
```

### Teams Integration
```python
# Process Teams queries via email
async def handle_teams_query(activity):
    result = await email_service.process_query(
        from_email=f"{activity.from_property.id}@teams.local",
        query=activity.text
    )
```

---

*Last Updated: January 22, 2025*
*API Version: 1.0*