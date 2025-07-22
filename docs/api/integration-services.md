# Integration Services API

## Overview
The Integration Services provide seamless connectivity between Splunk MCP and external systems including ITSM tools, BI platforms, chat applications, and third-party services.

## Services Included

1. **[ITSM Service](#itsm-service)** - ServiceNow and Jira integration
2. **[BI Integration Service](#bi-integration-service)** - Tableau and Power BI integration
3. **[Slack Bot Service](#slack-bot-service)** - Slack conversational interface
4. **[Microsoft Teams Bot Service](#teams-bot-service)** - Teams conversational interface

---

## ITSM Service

**Base URL**: `/api/v1/itsm`
**Port**: 8008 (Development)

### Authentication
```bash
Authorization: Bearer YOUR_JWT_TOKEN
```

### ServiceNow Integration

#### Create ServiceNow Incident
```http
POST /api/v1/itsm/servicenow/incidents
```

**Request Body:**
```json
{
  "instance_url": "https://company.service-now.com",
  "credentials": {
    "username": "service_account",
    "password": "password"
  },
  "incident": {
    "short_description": "High CPU usage detected",
    "description": "Splunk alert: CPU usage exceeded 90% threshold",
    "priority": "2",
    "urgency": "2",
    "category": "software",
    "assignment_group": "IT Operations"
  }
}
```

#### Sync ServiceNow Records
```http
POST /api/v1/itsm/servicenow/sync
```

### Jira Integration

#### Create Jira Issue
```http
POST /api/v1/itsm/jira/issues
```

**Request Body:**
```json
{
  "server_url": "https://company.atlassian.net",
  "credentials": {
    "email": "user@company.com",
    "api_token": "jira_api_token"
  },
  "issue": {
    "project": {"key": "OPS"},
    "issuetype": {"name": "Task"},
    "summary": "Investigate security alert",
    "description": "Security alert from Splunk requires investigation",
    "priority": {"name": "High"},
    "labels": ["splunk", "security"]
  }
}
```

#### Search Jira Issues
```http
GET /api/v1/itsm/jira/issues/search?jql=project=OPS AND status=Open
```

### Workflow Automation

#### Create Workflow
```http
POST /api/v1/itsm/workflows
```

**Request Body:**
```json
{
  "name": "Security Alert Workflow",
  "trigger": {
    "type": "alert",
    "conditions": {
      "severity": ["high", "critical"],
      "category": "security"
    }
  },
  "steps": [
    {
      "type": "create_ticket",
      "provider": "servicenow",
      "config": {
        "table": "incident",
        "priority": "2"
      }
    },
    {
      "type": "notify",
      "channels": ["email", "slack"],
      "message": "Security incident created: {{ticket_number}}"
    }
  ]
}
```

---

## BI Integration Service

**Base URL**: `/api/v1/bi`
**Port**: 8010 (Development)

### Tableau Integration

#### Publish Workbook
```http
POST /api/v1/bi/tableau/workbooks
```

**Request Body:**
```json
{
  "server_url": "https://tableau.company.com",
  "credentials": {
    "token_name": "api_token",
    "token_value": "tableau_token",
    "site_id": "default"
  },
  "workbook": {
    "name": "Splunk Security Dashboard",
    "project_id": "project_123",
    "file_path": "/path/to/workbook.twbx",
    "show_tabs": true,
    "overwrite": true
  }
}
```

#### Refresh Data Source
```http
POST /api/v1/bi/tableau/datasources/{datasource_id}/refresh
```

### Power BI Integration

#### Publish Report
```http
POST /api/v1/bi/powerbi/reports
```

**Request Body:**
```json
{
  "tenant_id": "company_tenant_id",
  "credentials": {
    "client_id": "powerbi_client_id",
    "client_secret": "powerbi_secret"
  },
  "workspace_id": "workspace_123",
  "report": {
    "name": "Splunk Analytics Report",
    "file_path": "/path/to/report.pbix",
    "conflict_action": "CreateOrOverwrite"
  }
}
```

#### Get Datasets
```http
GET /api/v1/bi/powerbi/workspaces/{workspace_id}/datasets
```

### Data Source Management

#### Create Connection
```http
POST /api/v1/bi/connections
```

**Request Body:**
```json
{
  "name": "Splunk Production",
  "type": "splunk",
  "config": {
    "host": "splunk.company.com",
    "port": 8089,
    "username": "service_account",
    "password": "password",
    "default_index": "main"
  },
  "bi_platforms": ["tableau", "powerbi"]
}
```

---

## Slack Bot Service

**Base URL**: `/api/v1/slack`
**Port**: 8004 (Development)

### Bot Management

#### Configure Bot
```http
POST /api/v1/slack/bot/configure
```

**Request Body:**
```json
{
  "bot_token": "xoxb-slack-bot-token",
  "signing_secret": "slack_signing_secret",
  "app_id": "A1234567890",
  "team_id": "T1234567890",
  "features": {
    "slash_commands": true,
    "event_subscriptions": true,
    "interactive_components": true
  }
}
```

### Message Processing

#### Process Slack Query
```http
POST /api/v1/slack/process-query
```

**Request Body:**
```json
{
  "user_id": "U1234567890",
  "channel_id": "C1234567890",
  "text": "show me errors from the last hour",
  "timestamp": "1642857600.123456"
}
```

### Slash Commands

Available slash commands:
- `/splunk query` - Execute natural language query
- `/splunk status` - Get system status
- `/splunk help` - Show help information
- `/splunk alerts` - List active alerts

### Interactive Features

#### Block Kit Components
```json
{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Query Results: 42 errors found"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "Create Alert"},
          "action_id": "create_alert"
        }
      ]
    }
  ]
}
```

---

## Microsoft Teams Bot Service

**Base URL**: `/api/v1/teams`
**Port**: 8005 (Development)

### Bot Framework Integration

#### Configure Bot
```http
POST /api/v1/teams/bot/configure
```

**Request Body:**
```json
{
  "app_id": "teams_app_id",
  "app_password": "teams_app_password",
  "bot_name": "SplunkBot",
  "supported_scopes": ["personal", "team", "groupchat"]
}
```

### Adaptive Cards

#### Send Adaptive Card
```http
POST /api/v1/teams/cards/send
```

**Request Body:**
```json
{
  "user_id": "user@company.com",
  "card": {
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": [
      {
        "type": "TextBlock",
        "text": "Security Alert",
        "weight": "bolder",
        "size": "medium"
      },
      {
        "type": "TextBlock",
        "text": "High CPU usage detected on server-01"
      }
    ],
    "actions": [
      {
        "type": "Action.Submit",
        "title": "Investigate",
        "data": {"action": "investigate", "alert_id": "alert_123"}
      }
    ]
  }
}
```

### Proactive Messaging

#### Send Proactive Message
```http
POST /api/v1/teams/messages/proactive
```

**Request Body:**
```json
{
  "recipients": ["user@company.com", "team_123"],
  "message": {
    "type": "message",
    "text": "Alert: Critical system error detected",
    "attachments": [...]
  }
}
```

## Common Integration Patterns

### Event-Driven Integration

#### Subscribe to Events
```http
POST /api/v1/integrations/events/subscribe
```

**Request Body:**
```json
{
  "service": "itsm",
  "event_types": ["alert.triggered", "incident.created"],
  "callback_url": "https://external-system.com/webhook",
  "filters": {
    "severity": ["high", "critical"]
  }
}
```

### Data Synchronization

#### Sync Configuration
```http
POST /api/v1/integrations/sync/configure
```

**Request Body:**
```json
{
  "source": "splunk",
  "target": "servicenow",
  "mapping": {
    "alert_id": "external_id",
    "severity": "priority",
    "description": "short_description"
  },
  "sync_frequency": "realtime",
  "conflict_resolution": "source_wins"
}
```

## Security Considerations

### Authentication Methods
1. **Service Accounts** - Dedicated service credentials
2. **OAuth 2.0** - For third-party integrations
3. **API Keys** - For simple integrations
4. **Certificate-based** - For high-security environments

### Data Protection
- All credentials encrypted at rest
- TLS encryption for all communications
- Regular credential rotation
- Audit logging for all integrations

### Rate Limiting
- Service-specific rate limits
- Burst protection mechanisms
- Queue management for high-volume integrations

## Monitoring and Troubleshooting

### Health Checks
```bash
# Check all integration services
curl /api/v1/integrations/health

# Service-specific health
curl /api/v1/itsm/health
curl /api/v1/bi/health
curl /api/v1/slack/health
curl /api/v1/teams/health
```

### Metrics
Common metrics across all integration services:
- `integration_requests_total`
- `integration_request_duration`
- `integration_success_rate`
- `integration_connection_pool_active`

### Error Handling
Standard error codes across integration services:
- `INT_001` - Authentication failed
- `INT_002` - Connection timeout
- `INT_003` - Rate limit exceeded
- `INT_004` - Invalid configuration
- `INT_005` - Service unavailable

## Usage Examples

### Python SDK
```python
from splunk_mcp import IntegrationService

# ITSM Integration
itsm = IntegrationService.itsm(api_key="your_key")
incident = itsm.servicenow.create_incident(
    description="High CPU usage",
    priority="high"
)

# BI Integration  
bi = IntegrationService.bi(api_key="your_key")
workbook = bi.tableau.publish_workbook(
    name="Security Dashboard",
    file_path="dashboard.twbx"
)

# Slack Integration
slack = IntegrationService.slack(api_key="your_key")
response = slack.send_message(
    channel="#security",
    text="Alert: Security event detected"
)
```

### Webhook Integration
```javascript
// Handle integration webhooks
app.post('/webhook/integration', (req, res) => {
  const event = req.body;
  
  switch (event.type) {
    case 'ticket.created':
      handleTicketCreated(event.data);
      break;
    case 'report.published':
      handleReportPublished(event.data);
      break;
  }
  
  res.status(200).send('OK');
});
```

---

*Last Updated: January 22, 2025*
*API Version: 1.0*