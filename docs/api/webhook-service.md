# Webhook Service API

## Overview
The Webhook Service provides comprehensive webhook management and delivery capabilities, enabling external tools to receive real-time notifications and data from the Splunk MCP platform.

**Base URL**: `/api/v1/webhooks`
**Port**: 8007 (Development)

## Authentication
All endpoints require JWT authentication:
```bash
Authorization: Bearer YOUR_JWT_TOKEN
```

## Core Endpoints

### Webhook Management

#### Create Webhook
Register a new webhook endpoint.

```http
POST /api/v1/webhooks
```

**Request Body:**
```json
{
  "name": "Security Alerts Webhook",
  "url": "https://external-service.com/webhooks/security",
  "method": "POST",
  "headers": {
    "X-API-Key": "external_api_key",
    "Content-Type": "application/json"
  },
  "events": ["alert.triggered", "security.violation"],
  "filters": {
    "severity": ["high", "critical"],
    "source": ["security_logs"]
  },
  "active": true,
  "retry_policy": {
    "max_attempts": 3,
    "initial_delay": 1000,
    "backoff_multiplier": 2.0,
    "max_delay": 60000
  },
  "timeout": 30000
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "webhook_id": "wh_abc123",
    "name": "Security Alerts Webhook",
    "url": "https://external-service.com/webhooks/security",
    "status": "active",
    "created_at": "2025-01-22T10:30:00Z",
    "signature_secret": "wh_secret_xyz789"
  }
}
```

#### List Webhooks
Get all webhooks for the authenticated user.

```http
GET /api/v1/webhooks
```

**Query Parameters:**
- `status` (string): Filter by status (active, paused, disabled)
- `event` (string): Filter by event type
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "webhooks": [
      {
        "webhook_id": "wh_abc123",
        "name": "Security Alerts Webhook",
        "url": "https://external-service.com/webhooks/security",
        "events": ["alert.triggered"],
        "status": "active",
        "last_delivery": "2025-01-22T09:45:00Z",
        "success_rate": 0.95
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 5,
      "pages": 1
    }
  }
}
```

#### Get Webhook Details
Retrieve detailed information about a specific webhook.

```http
GET /api/v1/webhooks/{webhook_id}
```

#### Update Webhook
Modify an existing webhook configuration.

```http
PUT /api/v1/webhooks/{webhook_id}
```

#### Delete Webhook
Remove a webhook endpoint.

```http
DELETE /api/v1/webhooks/{webhook_id}
```

#### Test Webhook
Send a test payload to verify webhook configuration.

```http
POST /api/v1/webhooks/{webhook_id}/test
```

**Request Body:**
```json
{
  "test_payload": {
    "type": "test",
    "message": "This is a test webhook delivery",
    "timestamp": "2025-01-22T10:30:00Z"
  }
}
```

### Event Processing

#### Trigger Event
Manually trigger a webhook event (for testing/development).

```http
POST /api/v1/webhooks/events/trigger
```

**Request Body:**
```json
{
  "event_type": "alert.triggered",
  "data": {
    "alert_id": "alert_456",
    "name": "High CPU Usage",
    "severity": "high",
    "timestamp": "2025-01-22T10:30:00Z",
    "description": "CPU usage exceeded 90% for 5 minutes",
    "source": "server-monitoring"
  },
  "metadata": {
    "user_id": "user_123",
    "correlation_id": "corr_789"
  }
}
```

#### List Event Types
Get available webhook event types.

```http
GET /api/v1/webhooks/events/types
```

**Response:**
```json
{
  "success": true,
  "data": {
    "event_types": [
      {
        "type": "alert.triggered",
        "description": "Triggered when an alert condition is met",
        "payload_schema": {...}
      },
      {
        "type": "query.completed",
        "description": "Triggered when a query execution completes",
        "payload_schema": {...}
      },
      {
        "type": "dashboard.created",
        "description": "Triggered when a new dashboard is created",
        "payload_schema": {...}
      }
    ]
  }
}
```

### Delivery Management

#### List Delivery Attempts
Get delivery history for a webhook.

```http
GET /api/v1/webhooks/{webhook_id}/deliveries
```

**Query Parameters:**
- `status` (string): Filter by delivery status (success, failed, pending)
- `start_date` (string): Filter from date (ISO format)
- `end_date` (string): Filter to date (ISO format)
- `page` (int): Page number
- `limit` (int): Items per page

**Response:**
```json
{
  "success": true,
  "data": {
    "deliveries": [
      {
        "delivery_id": "del_123",
        "webhook_id": "wh_abc123",
        "event_type": "alert.triggered",
        "status": "success",
        "http_status": 200,
        "response_time": 245,
        "attempted_at": "2025-01-22T10:30:00Z",
        "attempts": 1,
        "response_headers": {...},
        "error_message": null
      }
    ]
  }
}
```

#### Retry Failed Delivery
Retry a failed webhook delivery.

```http
POST /api/v1/webhooks/deliveries/{delivery_id}/retry
```

#### Get Delivery Details
Get detailed information about a specific delivery.

```http
GET /api/v1/webhooks/deliveries/{delivery_id}
```

### Analytics

#### Webhook Statistics
Get comprehensive webhook analytics.

```http
GET /api/v1/webhooks/analytics
```

**Query Parameters:**
- `webhook_id` (string): Filter by specific webhook
- `start_date` (string): Start date for analytics
- `end_date` (string): End date for analytics
- `granularity` (string): Data granularity (hour, day, week, month)

**Response:**
```json
{
  "success": true,
  "data": {
    "total_webhooks": 15,
    "active_webhooks": 12,
    "total_deliveries": 1250,
    "successful_deliveries": 1188,
    "failed_deliveries": 62,
    "success_rate": 0.95,
    "average_response_time": 285,
    "popular_events": [
      {"event": "alert.triggered", "count": 456},
      {"event": "query.completed", "count": 389}
    ],
    "delivery_trends": [...]
  }
}
```

#### User Quota Status
Check current webhook usage against quota limits.

```http
GET /api/v1/webhooks/quota
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_role": "premium",
    "quota_limits": {
      "max_webhooks": 25,
      "max_deliveries_per_hour": 1000
    },
    "current_usage": {
      "active_webhooks": 12,
      "deliveries_this_hour": 156
    },
    "remaining": {
      "webhooks": 13,
      "deliveries_this_hour": 844
    }
  }
}
```

## Configuration

### Environment Variables
```bash
# Service Configuration
WEBHOOK_SERVICE_PORT=8007
REDIS_URL=redis://localhost:6379/7
DATABASE_URL=postgresql://user:pass@localhost:5432/webhook_db

# Delivery Configuration
MAX_CONCURRENT_DELIVERIES=50
DEFAULT_TIMEOUT=30000
MAX_RETRY_ATTEMPTS=3
QUEUE_MAX_SIZE=10000

# Rate Limiting
RATE_LIMIT_PER_USER=1000
RATE_LIMIT_PER_ENDPOINT=500
RATE_LIMIT_BURST=10

# Security
SIGNATURE_ALGORITHM=sha256
JWT_SECRET_KEY=your_secret_key
```

## Event Types

### Available Event Types

| Event Type | Description | Payload |
|------------|-------------|---------|
| `query.completed` | Query execution finished | Query results, execution time |
| `alert.triggered` | Alert condition met | Alert details, severity, timestamp |
| `dashboard.created` | New dashboard created | Dashboard metadata, creator |
| `dashboard.updated` | Dashboard modified | Changes, updated fields |
| `report.generated` | Report generation complete | Report metadata, download URL |
| `error.occurred` | System error detected | Error details, stack trace |
| `user.action` | User performed action | Action type, user context |
| `system.status_changed` | System status update | Old status, new status |

### Payload Structure
All webhook payloads follow this structure:

```json
{
  "id": "event_12345",
  "type": "alert.triggered",
  "timestamp": "2025-01-22T10:30:00Z",
  "data": {
    // Event-specific data
  },
  "metadata": {
    "source": "splunk-mcp",
    "version": "1.0",
    "correlation_id": "corr_789",
    "user_id": "user_123"
  }
}
```

## Security

### Signature Verification
All webhook deliveries include an HMAC-SHA256 signature:

```http
X-Webhook-Signature-256: sha256=1234567890abcdef...
```

**Verification Example (Node.js):**
```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload, 'utf8')
    .digest('hex');
  
  return `sha256=${expectedSignature}` === signature;
}
```

**Verification Example (Python):**
```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={expected_signature}" == signature
```

### Rate Limiting
Rate limits are enforced per user and webhook:
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **User Limits**: 1000 requests/hour
- **Endpoint Limits**: 500 deliveries/hour per webhook
- **Burst Protection**: 10 requests/second maximum

### IP Filtering
Configure allowed IP ranges for webhook deliveries:

```json
{
  "allowed_ips": ["192.168.1.0/24", "10.0.0.0/8"],
  "blocked_ips": ["192.168.1.100"]
}
```

## Error Handling

### Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `WEBHOOK_001` | Invalid webhook URL | Check URL format and accessibility |
| `WEBHOOK_002` | Delivery timeout | Increase timeout or check endpoint |
| `WEBHOOK_003` | Maximum retries exceeded | Check endpoint health and logs |
| `WEBHOOK_004` | Invalid signature secret | Regenerate webhook secret |
| `WEBHOOK_005` | Quota limit exceeded | Upgrade plan or reduce usage |
| `WEBHOOK_006` | Invalid event type | Check available event types |
| `WEBHOOK_007` | Delivery queue full | Retry later or increase limits |

### Retry Logic
Failed deliveries are retried with exponential backoff:

1. **Initial Delay**: 1 second
2. **Backoff Multiplier**: 2.0
3. **Maximum Delay**: 60 seconds
4. **Maximum Attempts**: 3 (configurable)

## Usage Examples

### Python SDK
```python
from splunk_mcp import WebhookService

webhook_service = WebhookService(api_key="your_api_key")

# Create webhook
webhook = webhook_service.create_webhook(
    name="My Webhook",
    url="https://myapp.com/webhook",
    events=["alert.triggered"]
)

# List deliveries
deliveries = webhook_service.get_deliveries(webhook.id)
```

### cURL Examples
```bash
# Create webhook
curl -X POST /api/v1/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Webhook",
    "url": "https://example.com/webhook",
    "events": ["alert.triggered"]
  }'

# Test webhook
curl -X POST /api/v1/webhooks/wh_123/test \
  -H "Authorization: Bearer $TOKEN"
```

### JavaScript Integration
```javascript
// Handle webhook in Express.js
const express = require('express');
const crypto = require('crypto');

app.post('/webhook', (req, res) => {
  const signature = req.headers['x-webhook-signature-256'];
  const payload = JSON.stringify(req.body);
  
  if (!verifyWebhookSignature(payload, signature, 'your_secret')) {
    return res.status(401).send('Invalid signature');
  }
  
  // Process webhook payload
  console.log('Received webhook:', req.body);
  res.status(200).send('OK');
});
```

## Monitoring

### Health Checks
```bash
# Service health
curl /api/v1/webhooks/health

# Delivery queue status
curl /api/v1/webhooks/health/queue

# Database connectivity
curl /api/v1/webhooks/health/database
```

### Metrics
Available at `/api/v1/webhooks/metrics`:
- `webhook_service_requests_total`
- `webhook_service_deliveries_total`
- `webhook_service_delivery_duration`
- `webhook_service_delivery_success_rate`
- `webhook_service_queue_size`

## Integration Examples

### Slack Integration
```python
# Send Slack notifications via webhook
webhook_payload = {
    "text": f"Alert triggered: {alert_name}",
    "attachments": [{
        "color": "danger" if severity == "high" else "warning",
        "fields": [
            {"title": "Severity", "value": severity},
            {"title": "Time", "value": timestamp}
        ]
    }]
}
```

### PagerDuty Integration
```json
{
  "routing_key": "your_integration_key",
  "event_action": "trigger",
  "payload": {
    "summary": "Alert from Splunk MCP",
    "severity": "error",
    "source": "splunk-mcp-webhook"
  }
}
```

---

*Last Updated: January 22, 2025*
*API Version: 1.0*