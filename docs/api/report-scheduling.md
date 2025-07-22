# Report Scheduling Service API

## Overview
The Report Scheduling Service provides comprehensive automated report generation, scheduling, and delivery capabilities with version control, analytics, and multi-channel delivery support.

**Base URL**: `/api/v1/reports`
**Port**: 8015 (Development)

## Authentication
All endpoints require JWT authentication:
```bash
Authorization: Bearer YOUR_JWT_TOKEN
```

## Core Endpoints

### Schedule Management

#### Create Report Schedule
Create a new automated report schedule.

```http
POST /api/v1/reports/schedules
```

**Request Body:**
```json
{
  "name": "Daily Security Summary",
  "description": "Daily summary of security events and alerts",
  "query": "search earliest=-24h index=security | stats count by severity, source",
  "schedule": {
    "type": "cron",
    "expression": "0 9 * * 1-5",
    "timezone": "America/New_York"
  },
  "delivery": {
    "channels": [
      {
        "type": "email",
        "recipients": ["security-team@company.com"],
        "format": "pdf",
        "template": "executive_summary"
      },
      {
        "type": "slack",
        "channel": "#security-alerts",
        "format": "html"
      }
    ]
  },
  "parameters": {
    "include_charts": true,
    "chart_types": ["bar", "pie"],
    "theme": "corporate",
    "logo_url": "https://company.com/logo.png"
  },
  "active": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "schedule_id": "sched_abc123",
    "name": "Daily Security Summary",
    "status": "active",
    "created_at": "2025-01-22T10:30:00Z",
    "next_execution": "2025-01-23T14:00:00Z",
    "version": 1
  }
}
```

#### List Report Schedules
Get all report schedules for the authenticated user.

```http
GET /api/v1/reports/schedules
```

**Query Parameters:**
- `status` (string): Filter by status (active, paused, disabled)
- `user_id` (string): Filter by user (admin only)
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)
- `sort` (string): Sort field (created_at, name, next_execution)
- `order` (string): Sort order (asc, desc)

#### Get Schedule Details
Retrieve detailed information about a specific schedule.

```http
GET /api/v1/reports/schedules/{schedule_id}
```

#### Update Report Schedule
Modify an existing report schedule.

```http
PUT /api/v1/reports/schedules/{schedule_id}
```

#### Delete Report Schedule
Remove a report schedule.

```http
DELETE /api/v1/reports/schedules/{schedule_id}
```

#### Pause/Resume Schedule
Temporarily pause or resume a schedule.

```http
POST /api/v1/reports/schedules/{schedule_id}/pause
POST /api/v1/reports/schedules/{schedule_id}/resume
```

#### Execute Schedule Immediately
Trigger immediate execution of a schedule.

```http
POST /api/v1/reports/schedules/{schedule_id}/execute
```

### Execution Management

#### List Schedule Executions
Get execution history for a schedule.

```http
GET /api/v1/reports/schedules/{schedule_id}/executions
```

**Query Parameters:**
- `status` (string): Filter by execution status (success, failed, running)
- `start_date` (string): Filter from date (ISO format)
- `end_date` (string): Filter to date (ISO format)
- `page` (int): Page number
- `limit` (int): Items per page

**Response:**
```json
{
  "success": true,
  "data": {
    "executions": [
      {
        "execution_id": "exec_456",
        "schedule_id": "sched_abc123",
        "status": "success",
        "started_at": "2025-01-22T14:00:00Z",
        "completed_at": "2025-01-22T14:02:15Z",
        "duration": 135,
        "result_count": 1247,
        "deliveries": [
          {
            "channel": "email",
            "status": "delivered",
            "delivered_at": "2025-01-22T14:02:30Z"
          }
        ],
        "version": 1
      }
    ]
  }
}
```

#### Get Execution Details
Get detailed information about a specific execution.

```http
GET /api/v1/reports/executions/{execution_id}
```

#### Retry Failed Execution
Retry a failed report execution.

```http
POST /api/v1/reports/executions/{execution_id}/retry
```

#### Cancel Running Execution
Cancel a currently running execution.

```http
POST /api/v1/reports/executions/{execution_id}/cancel
```

#### Download Report Results
Download generated report files.

```http
GET /api/v1/reports/executions/{execution_id}/download
```

**Query Parameters:**
- `format` (string): File format (pdf, xlsx, html, csv)
- `attachment` (boolean): Force download as attachment

### Subscription Management

#### Create Subscription
Subscribe to report deliveries.

```http
POST /api/v1/reports/subscriptions
```

**Request Body:**
```json
{
  "schedule_id": "sched_abc123",
  "delivery_preferences": {
    "email": "user@company.com",
    "slack_user": "@john.doe",
    "format": "pdf",
    "frequency": "every_execution"
  },
  "notifications": {
    "execution_started": false,
    "execution_completed": true,
    "execution_failed": true
  }
}
```

#### List Subscriptions
Get all subscriptions for the authenticated user.

```http
GET /api/v1/reports/subscriptions
```

#### Update Subscription
Modify subscription preferences.

```http
PUT /api/v1/reports/subscriptions/{subscription_id}
```

#### Unsubscribe
Remove a subscription.

```http
DELETE /api/v1/reports/subscriptions/{subscription_id}
```

#### Test Subscription
Send a test delivery to verify subscription configuration.

```http
POST /api/v1/reports/subscriptions/{subscription_id}/test
```

### Version Control

#### List Schedule Versions
Get version history for a schedule.

```http
GET /api/v1/reports/schedules/{schedule_id}/versions
```

**Response:**
```json
{
  "success": true,
  "data": {
    "versions": [
      {
        "version": 2,
        "created_at": "2025-01-22T15:30:00Z",
        "created_by": "user_123",
        "changes": ["query updated", "delivery channels modified"],
        "change_summary": "Updated query to include error codes"
      },
      {
        "version": 1,
        "created_at": "2025-01-21T10:00:00Z",
        "created_by": "user_123",
        "changes": ["initial version"],
        "change_summary": "Initial schedule creation"
      }
    ]
  }
}
```

#### Get Version Details
Get detailed information about a specific version.

```http
GET /api/v1/reports/schedules/{schedule_id}/versions/{version}
```

#### Compare Versions
Compare two versions of a schedule.

```http
POST /api/v1/reports/versions/compare
```

**Request Body:**
```json
{
  "schedule_id": "sched_abc123",
  "version_a": 1,
  "version_b": 2
}
```

#### Restore Version
Restore a schedule to a previous version.

```http
POST /api/v1/reports/schedules/{schedule_id}/versions/{version}/restore
```

### Analytics

#### Schedule Analytics
Get comprehensive analytics for report schedules.

```http
GET /api/v1/reports/analytics
```

**Query Parameters:**
- `schedule_id` (string): Filter by specific schedule
- `start_date` (string): Start date for analytics
- `end_date` (string): End date for analytics
- `granularity` (string): Data granularity (hour, day, week, month)

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_schedules": 25,
      "active_schedules": 18,
      "total_executions": 1500,
      "successful_executions": 1425,
      "failed_executions": 75,
      "success_rate": 0.95,
      "average_execution_time": 145
    },
    "trends": {
      "execution_trend": [...],
      "success_rate_trend": [...],
      "delivery_performance": [...]
    },
    "top_schedules": [
      {
        "schedule_id": "sched_abc123",
        "name": "Daily Security Summary",
        "executions": 30,
        "success_rate": 0.97
      }
    ]
  }
}
```

#### User Analytics
Get analytics specific to the authenticated user.

```http
GET /api/v1/reports/analytics/user
```

#### Performance Metrics
Get detailed performance metrics.

```http
GET /api/v1/reports/analytics/performance
```

## Configuration

### Environment Variables
```bash
# Service Configuration
REPORT_SCHEDULING_PORT=8015
REDIS_URL=redis://localhost:6379/15
DATABASE_URL=postgresql://user:pass@localhost:5432/reports_db

# Report Generation
MAX_CONCURRENT_REPORTS=10
REPORT_TIMEOUT=300000
TEMP_STORAGE_PATH=/tmp/reports
CLEANUP_INTERVAL=3600

# Delivery Configuration
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
SLACK_BOT_TOKEN=xoxb-slack-token
TEAMS_APP_ID=teams-app-id

# Version Control
MAX_VERSIONS_PER_SCHEDULE=50
VERSION_RETENTION_DAYS=365
```

## Schedule Configuration

### Cron Expressions
Schedule executions using cron expressions:

```bash
# Every day at 9:00 AM
0 9 * * *

# Every weekday at 8:30 AM
30 8 * * 1-5

# Every hour on the half hour
30 * * * *

# First day of every month at midnight
0 0 1 * *

# Every Sunday at 6:00 PM
0 18 * * 0
```

### Timezone Support
Supported timezones:
- `UTC` (default)
- `America/New_York`
- `America/Los_Angeles`
- `Europe/London`
- `Asia/Tokyo`
- And all other IANA timezone identifiers

## Delivery Channels

### Email Delivery
```json
{
  "type": "email",
  "recipients": ["user@company.com", "team@company.com"],
  "cc": ["manager@company.com"],
  "bcc": ["archive@company.com"],
  "subject": "Daily Report: {{report_name}}",
  "format": "pdf",
  "template": "professional",
  "attach_raw_data": false
}
```

### Slack Delivery
```json
{
  "type": "slack",
  "channel": "#reports",
  "format": "html",
  "message": "Daily report is ready! {{download_link}}",
  "thread_replies": false
}
```

### Teams Delivery
```json
{
  "type": "teams",
  "channel": "reports",
  "format": "adaptive_card",
  "template": "report_summary"
}
```

### File Storage Delivery
```json
{
  "type": "file_storage",
  "path": "/shared/reports/{{date}}/",
  "formats": ["pdf", "xlsx"],
  "retention_days": 30
}
```

### Webhook Delivery
```json
{
  "type": "webhook",
  "url": "https://external-system.com/reports",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer token",
    "Content-Type": "application/json"
  },
  "include_metadata": true
}
```

## Error Handling

### Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `RPT_001` | Invalid cron expression | Check cron syntax |
| `RPT_002` | Query execution failed | Verify SPL query syntax |
| `RPT_003` | Delivery failed | Check delivery configuration |
| `RPT_004` | Template not found | Use valid template name |
| `RPT_005` | Schedule limit exceeded | Upgrade plan or reduce schedules |
| `RPT_006` | Execution timeout | Optimize query or increase timeout |
| `RPT_007` | Storage limit exceeded | Clean up old reports |

### Retry Logic
Failed executions and deliveries are retried:
- **Query Failures**: 3 attempts with 1-minute intervals
- **Delivery Failures**: 5 attempts with exponential backoff
- **Temporary Failures**: Automatic retry on next schedule

## Usage Examples

### Python SDK
```python
from splunk_mcp import ReportSchedulingService

reports = ReportSchedulingService(api_key="your_api_key")

# Create schedule
schedule = reports.create_schedule(
    name="Daily Error Report",
    query="search earliest=-24h error | stats count by source",
    cron="0 9 * * *",
    delivery_email="admin@company.com"
)

# Get analytics
analytics = reports.get_analytics(
    start_date="2025-01-01",
    end_date="2025-01-22"
)
```

### cURL Examples
```bash
# Create schedule
curl -X POST /api/v1/reports/schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hourly Status Check",
    "query": "search earliest=-1h | stats count",
    "schedule": {"type": "cron", "expression": "0 * * * *"},
    "delivery": {"channels": [{"type": "email", "recipients": ["admin@company.com"]}]}
  }'

# Execute immediately
curl -X POST /api/v1/reports/schedules/sched_123/execute \
  -H "Authorization: Bearer $TOKEN"
```

### JavaScript Integration
```javascript
// Handle report webhook
app.post('/webhook/reports', (req, res) => {
  const report = req.body;
  
  console.log(`Report ${report.name} completed:`, report.status);
  
  if (report.status === 'success') {
    // Process successful report
    processReport(report);
  } else {
    // Handle failure
    logError(report.error_message);
  }
  
  res.status(200).send('OK');
});
```

## Monitoring

### Health Checks
```bash
# Service health
curl /api/v1/reports/health

# Scheduler health
curl /api/v1/reports/health/scheduler

# Database connectivity
curl /api/v1/reports/health/database

# Delivery services health
curl /api/v1/reports/health/delivery
```

### Metrics
Available at `/api/v1/reports/metrics`:
- `report_scheduling_executions_total`
- `report_scheduling_execution_duration`
- `report_scheduling_success_rate`
- `report_scheduling_delivery_success_rate`
- `report_scheduling_active_schedules`

### Alerting
Set up alerts for:
- Failed executions exceeding threshold
- Delivery failures
- Long-running executions
- Storage usage exceeding limits

---

*Last Updated: January 22, 2025*
*API Version: 1.0*