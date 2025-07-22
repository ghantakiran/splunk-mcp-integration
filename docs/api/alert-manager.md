# Alert Manager Service Documentation

## Overview

The Alert Manager Service provides comprehensive alerting capabilities with natural language alert creation, multi-channel notifications, escalation workflows, and intelligent alert correlation. It supports real-time monitoring and automated response systems.

**Base URL**: `/api/v1/alerts`  
**Service Port**: 8003  
**Version**: 1.0

## Alert Management

### POST /alerts
Create a new alert from natural language description.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "description": "Alert me when error rate exceeds 100 per minute in the last 5 minutes",
  "notification_channels": ["email", "slack"],
  "severity": "high",
  "settings": {
    "email_recipients": ["admin@company.com", "oncall@company.com"],
    "slack_channel": "#alerts",
    "check_interval": 300,
    "enabled": true
  },
  "metadata": {
    "tags": ["performance", "errors"],
    "owner": "devops-team",
    "environment": "production"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "alert_id": "alert_123",
    "name": "High Error Rate Alert",
    "description": "Alert me when error rate exceeds 100 per minute in the last 5 minutes",
    "search_query": "search earliest=-5m@m index=* error | stats count as error_count | eval error_rate=error_count/5 | where error_rate > 100",
    "trigger_condition": {
      "field": "error_rate",
      "operator": "greater_than",
      "threshold": 100,
      "time_window": "5m"
    },
    "severity": "high",
    "status": "active",
    "notification_channels": ["email", "slack"],
    "created_at": "2025-01-22T11:00:00Z",
    "next_check": "2025-01-22T11:05:00Z"
  }
}
```

---

### GET /alerts
List alerts with filtering and pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `status`: Filter by status (active, paused, disabled)
- `severity`: Filter by severity (low, medium, high, critical)
- `tag`: Filter by tag
- `owner`: Filter by owner
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `sort`: Sort field (name, created_at, severity, last_triggered)
- `order`: Sort order (asc, desc)

**Response:**
```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "alert_id": "alert_123",
        "name": "High Error Rate Alert",
        "description": "Alert when error rate exceeds threshold",
        "severity": "high",
        "status": "active",
        "last_triggered": "2025-01-22T10:45:00Z",
        "trigger_count": 3,
        "notification_channels": ["email", "slack"],
        "created_at": "2025-01-22T11:00:00Z",
        "tags": ["performance", "errors"]
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 15,
      "pages": 1
    },
    "summary": {
      "total_alerts": 15,
      "active": 12,
      "paused": 2,
      "disabled": 1,
      "triggered_last_24h": 8
    }
  }
}
```

---

### GET /alerts/{alert_id}
Get detailed alert configuration and history.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "alert_id": "alert_123",
    "name": "High Error Rate Alert",
    "description": "Alert me when error rate exceeds 100 per minute in the last 5 minutes",
    "search_query": "search earliest=-5m@m index=* error | stats count as error_count | eval error_rate=error_count/5 | where error_rate > 100",
    "trigger_condition": {
      "field": "error_rate",
      "operator": "greater_than",
      "threshold": 100,
      "time_window": "5m",
      "evaluation_delay": "1m"
    },
    "severity": "high",
    "status": "active",
    "notification_channels": ["email", "slack"],
    "settings": {
      "check_interval": 300,
      "max_frequency": "once_per_hour",
      "suppress_duration": 3600,
      "auto_resolve": true,
      "escalation_enabled": true
    },
    "escalation": {
      "levels": [
        {
          "level": 1,
          "delay": 0,
          "channels": ["slack"],
          "recipients": ["#alerts"]
        },
        {
          "level": 2,
          "delay": 1800,
          "channels": ["email", "slack"],
          "recipients": ["oncall@company.com", "#critical-alerts"]
        }
      ]
    },
    "statistics": {
      "total_triggers": 15,
      "last_triggered": "2025-01-22T10:45:00Z",
      "avg_trigger_frequency": "2.3/day",
      "false_positive_rate": 0.12,
      "resolution_time_avg": "25m"
    },
    "created_by": "user_123",
    "created_at": "2025-01-22T11:00:00Z",
    "updated_at": "2025-01-22T11:00:00Z"
  }
}
```

---

### PUT /alerts/{alert_id}
Update alert configuration.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Updated High Error Rate Alert",
  "description": "Enhanced alert for error monitoring",
  "trigger_condition": {
    "threshold": 150
  },
  "settings": {
    "check_interval": 600,
    "max_frequency": "once_per_30_minutes"
  },
  "notification_channels": ["email", "slack", "webhook"],
  "webhook_url": "https://api.company.com/alerts/webhook"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Alert updated successfully",
    "updated_fields": ["name", "description", "threshold", "check_interval", "notification_channels"],
    "updated_at": "2025-01-22T11:30:00Z"
  }
}
```

---

### DELETE /alerts/{alert_id}
Delete an alert.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Alert deleted successfully",
    "alert_id": "alert_123"
  }
}
```

---

### POST /alerts/{alert_id}/actions
Perform actions on an alert.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "action": "pause",
  "reason": "Maintenance window",
  "duration": 3600
}
```

**Available Actions:**
- `pause`: Temporarily disable alert
- `resume`: Re-enable paused alert
- `test`: Test alert trigger
- `silence`: Silence notifications for specified duration
- `acknowledge`: Acknowledge triggered alert

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Alert paused for 1 hour",
    "action": "pause",
    "expires_at": "2025-01-22T12:30:00Z"
  }
}
```

## Alert Triggers and History

### GET /alerts/{alert_id}/triggers
Get alert trigger history.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `start_time`: Start time for history (ISO 8601)
- `end_time`: End time for history (ISO 8601)
- `limit`: Maximum results (default: 50, max: 500)
- `include_resolved`: Include resolved triggers (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "triggers": [
      {
        "trigger_id": "trigger_456",
        "alert_id": "alert_123",
        "triggered_at": "2025-01-22T10:45:00Z",
        "resolved_at": "2025-01-22T11:15:00Z",
        "duration": "30m",
        "trigger_value": 125.7,
        "threshold": 100,
        "severity": "high",
        "status": "resolved",
        "notifications_sent": [
          {
            "channel": "slack",
            "recipient": "#alerts",
            "sent_at": "2025-01-22T10:45:30Z",
            "status": "delivered"
          },
          {
            "channel": "email",
            "recipient": "oncall@company.com",
            "sent_at": "2025-01-22T11:00:30Z",
            "status": "delivered"
          }
        ],
        "actions_taken": [
          {
            "action": "acknowledge",
            "user": "user_123",
            "timestamp": "2025-01-22T10:50:00Z"
          }
        ]
      }
    ],
    "summary": {
      "total_triggers": 15,
      "resolved": 13,
      "active": 2,
      "avg_duration": "25m",
      "time_range": {
        "start": "2025-01-15T00:00:00Z",
        "end": "2025-01-22T11:30:00Z"
      }
    }
  }
}
```

---

### POST /alerts/{alert_id}/test
Test alert trigger manually.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "test_data": {
    "error_rate": 150
  },
  "send_notifications": false,
  "dry_run": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "test_result": "triggered",
    "condition_met": true,
    "test_value": 150,
    "threshold": 100,
    "search_executed": true,
    "search_results": {
      "execution_time": "1.2s",
      "result_count": 1,
      "matching_events": 750
    },
    "notifications": {
      "would_send": ["slack", "email"],
      "recipients": ["#alerts", "oncall@company.com"],
      "sent": false
    }
  }
}
```

## Notification Management

### GET /notification-channels
Get available notification channels.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "channels": [
      {
        "type": "email",
        "name": "Email",
        "description": "Send alerts via email",
        "configuration": {
          "required_fields": ["recipients"],
          "optional_fields": ["subject_template", "body_template"]
        },
        "available": true
      },
      {
        "type": "slack",
        "name": "Slack",
        "description": "Send alerts to Slack channels",
        "configuration": {
          "required_fields": ["channel"],
          "optional_fields": ["username", "icon_emoji"]
        },
        "available": true,
        "connected": true
      },
      {
        "type": "teams",
        "name": "Microsoft Teams",
        "description": "Send alerts to Teams channels",
        "configuration": {
          "required_fields": ["webhook_url"],
          "optional_fields": ["card_template"]
        },
        "available": true,
        "connected": false
      },
      {
        "type": "webhook",
        "name": "Custom Webhook",
        "description": "Send alerts to custom HTTP endpoints",
        "configuration": {
          "required_fields": ["url"],
          "optional_fields": ["headers", "payload_template"]
        },
        "available": true
      }
    ]
  }
}
```

---

### POST /notification-channels/{channel_type}/test
Test notification channel configuration.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "configuration": {
    "channel": "#test-alerts",
    "message": "Test alert notification from Splunk MCP"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "test_result": "success",
    "message": "Test notification sent successfully",
    "delivery_time": "2.3s",
    "response": {
      "status": 200,
      "message": "Message delivered"
    }
  }
}
```

## Alert Templates

### GET /templates
Get available alert templates.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "template_id": "template_1",
        "name": "High Error Rate",
        "description": "Monitor error rate exceeding threshold",
        "category": "performance",
        "search_template": "search earliest=-{time_window} index=* error | stats count as error_count | eval error_rate=error_count/{minutes} | where error_rate > {threshold}",
        "variables": [
          {
            "name": "time_window",
            "type": "timespan",
            "default": "5m",
            "description": "Time window for monitoring"
          },
          {
            "name": "threshold",
            "type": "number",
            "default": 100,
            "description": "Error rate threshold per minute"
          }
        ],
        "suggested_severity": "high",
        "suggested_channels": ["email", "slack"]
      },
      {
        "template_id": "template_2",
        "name": "Failed Login Attempts",
        "description": "Detect potential brute force attacks",
        "category": "security",
        "search_template": "search earliest=-{time_window} index=security failed login | stats count by src_ip, user | where count > {threshold}",
        "variables": [
          {
            "name": "time_window",
            "type": "timespan",
            "default": "15m",
            "description": "Time window for monitoring"
          },
          {
            "name": "threshold", 
            "type": "number",
            "default": 5,
            "description": "Failed attempts threshold"
          }
        ],
        "suggested_severity": "critical",
        "suggested_channels": ["email", "slack", "teams"]
      }
    ]
  }
}
```

---

### POST /alerts/from-template
Create alert from template.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "template_id": "template_1",
  "name": "Production Error Rate Alert",
  "variables": {
    "time_window": "10m",
    "threshold": 150
  },
  "notification_channels": ["email", "slack"],
  "settings": {
    "email_recipients": ["devops@company.com"],
    "slack_channel": "#production-alerts"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "alert_id": "alert_124",
    "name": "Production Error Rate Alert",
    "search_query": "search earliest=-10m index=* error | stats count as error_count | eval error_rate=error_count/10 | where error_rate > 150",
    "created_from_template": "template_1",
    "status": "active"
  }
}
```

## Alert Analytics

### GET /analytics/summary
Get alert system analytics summary.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `time_range`: Time range for analytics (1h, 24h, 7d, 30d)
- `groupby`: Group by field (severity, channel, owner)

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "time_range": "24h",
      "total_alerts": 45,
      "active_alerts": 38,
      "triggered_alerts": 12,
      "resolved_alerts": 8,
      "avg_resolution_time": "32m",
      "false_positive_rate": 0.15
    },
    "by_severity": {
      "critical": {"count": 2, "triggered": 1},
      "high": {"count": 8, "triggered": 4},
      "medium": {"count": 15, "triggered": 5},
      "low": {"count": 20, "triggered": 2}
    },
    "by_channel": {
      "email": {"alerts": 35, "notifications_sent": 156},
      "slack": {"alerts": 28, "notifications_sent": 89},
      "teams": {"alerts": 12, "notifications_sent": 23},
      "webhook": {"alerts": 8, "notifications_sent": 15}
    },
    "top_triggered": [
      {
        "alert_id": "alert_123",
        "name": "High Error Rate Alert",
        "trigger_count": 8,
        "last_triggered": "2025-01-22T10:45:00Z"
      }
    ],
    "performance": {
      "avg_check_time": "1.2s",
      "avg_notification_time": "3.1s",
      "system_health": "good"
    }
  }
}
```

---

### GET /analytics/trends
Get alert trending data.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `metric`: Metric to analyze (trigger_count, resolution_time, false_positives)
- `time_range`: Time range (7d, 30d, 90d)
- `interval`: Data interval (1h, 1d, 1w)

**Response:**
```json
{
  "success": true,
  "data": {
    "metric": "trigger_count",
    "time_range": "7d",
    "interval": "1d",
    "data_points": [
      {
        "timestamp": "2025-01-16T00:00:00Z",
        "value": 23,
        "breakdown": {
          "critical": 1,
          "high": 5,
          "medium": 12,
          "low": 5
        }
      },
      {
        "timestamp": "2025-01-17T00:00:00Z",
        "value": 18,
        "breakdown": {
          "critical": 0,
          "high": 3,
          "medium": 10,
          "low": 5
        }
      }
    ],
    "insights": [
      {
        "type": "trend",
        "message": "Alert trigger rate decreased 22% this week",
        "confidence": 0.87
      },
      {
        "type": "anomaly",
        "message": "Spike in critical alerts on Jan 16th",
        "confidence": 0.92
      }
    ]
  }
}
```

## Service Configuration

### GET /capabilities
Get alert manager service capabilities.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "features": {
      "natural_language_alerts": true,
      "multi_channel_notifications": true,
      "escalation_workflows": true,
      "alert_correlation": true,
      "template_system": true,
      "real_time_monitoring": true
    },
    "supported_channels": ["email", "slack", "teams", "webhook", "sms"],
    "limits": {
      "max_alerts_per_user": 500,
      "max_notification_channels": 10,
      "min_check_interval": 60,
      "max_escalation_levels": 5
    },
    "search_capabilities": {
      "max_search_time_range": "30d",
      "max_search_complexity": "high",
      "supported_spl_commands": ["search", "stats", "eval", "where", "sort"]
    }
  }
}
```

---

### GET /health
Service health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-22T11:40:00Z",
  "dependencies": {
    "database": "healthy",
    "redis": "healthy",
    "splunk_api": "healthy",
    "notification_services": {
      "email": "healthy",
      "slack": "healthy",
      "teams": "healthy"
    }
  },
  "performance": {
    "active_alerts": 38,
    "checks_per_minute": 45,
    "avg_check_time": "1.2s",
    "notifications_sent_last_hour": 23,
    "queue_depth": 0
  }
}
```

## Error Handling

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_SEARCH_QUERY` | 400 | Generated SPL query is invalid |
| `UNSUPPORTED_CHANNEL` | 400 | Notification channel not supported |
| `ALERT_NOT_FOUND` | 404 | Alert ID does not exist |
| `NOTIFICATION_FAILED` | 500 | Failed to send notification |
| `ESCALATION_ERROR` | 500 | Error in escalation workflow |
| `TEMPLATE_NOT_FOUND` | 404 | Alert template not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many alert checks |
| `SEARCH_TIMEOUT` | 504 | Alert search query timed out |

---

*Last Updated: January 22, 2025*
*Service Version: 1.0*