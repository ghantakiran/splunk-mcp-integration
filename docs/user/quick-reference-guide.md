# Quick Reference Guide - Splunk MCP Integration Platform

A comprehensive quick reference for daily use of the Splunk MCP Integration Platform.

## Common Query Patterns

### Basic Search Patterns
```
Show me events from [time period]
Find [condition] in [time period]
Count [field] by [grouping] in [time period]
Top [N] [field] by [metric]
```

### Time Range Examples
```
"last hour" → earliest=-1h
"yesterday" → earliest=-1d@d latest=@d
"business hours today" → earliest=@d+9h latest=@d+17h
"last Monday to Friday" → earliest=-1w@w1 latest=@w1
"this month" → earliest=@mon
```

### Filter Patterns
```
AND logic: "errors AND critical"
OR logic: "errors OR warnings"
NOT logic: "events NOT from test"
Field comparison: "status_code=500"
Range: "response_time > 1000"
Contains: "message contains 'database'"
```

## Dashboard Quick Actions

### Chart Types Selection Guide
| Data Type | Recommended Chart | Use Case |
|-----------|------------------|----------|
| Time series | Line chart | Trends over time |
| Categories | Bar chart | Comparisons |
| Proportions | Pie chart | Distribution |
| Correlations | Scatter plot | Relationships |
| Geographic | Map | Location data |
| Status | Gauge | KPI monitoring |

### Dashboard Layout Best Practices
```
Executive Dashboard (2x3):
┌─────────┬─────────┬─────────┐
│ KPI 1   │ KPI 2   │ KPI 3   │
├─────────┴─────────┴─────────┤
│      Main Trend Chart       │
└─────────────────────────────┘

Operations Dashboard (3x3):
┌─────────┬─────────┬─────────┐
│ Status  │ Alerts  │ Health  │
├─────────┼─────────┼─────────┤
│   Performance Trends        │
├─────────┼─────────┼─────────┤
│ Issues  │ Activity│ Actions │
└─────────┴─────────┴─────────┘
```

## Alert Configuration Cheat Sheet

### Alert Types Quick Setup
```
Threshold Alert:
"Alert when [metric] [operator] [value] for [duration]"
Example: "Alert when CPU > 80% for 10 minutes"

Absence Alert:
"Alert if no [events] in [time period]"
Example: "Alert if no heartbeat in 5 minutes"

Correlation Alert:
"Alert when [condition1] AND [condition2]"
Example: "Alert when high CPU AND high memory"

Trend Alert:
"Alert when [metric] increases/decreases by [%] compared to [baseline]"
Example: "Alert when response time increases by 50% vs yesterday"
```

### Notification Channels
```
Email: Standard notifications, reports
Slack: Team collaboration, real-time alerts
SMS: Critical alerts, escalations
Webhook: Integration with external systems
```

## Report Generation Quick Reference

### Report Types and Formats
| Report Type | Best Format | Audience | Frequency |
|-------------|-------------|----------|-----------|
| Executive Summary | PDF/PowerPoint | Leadership | Weekly/Monthly |
| Operational Report | HTML/Excel | Operations | Daily |
| Technical Analysis | Excel/CSV | Analysts | As needed |
| Compliance Report | PDF | Auditors | Monthly/Quarterly |

### Scheduling Syntax
```
Daily: "Every day at [time]"
Weekly: "Every [day] at [time]"
Monthly: "First/Last [day] of month at [time]"
Business days: "Every weekday at [time]"
```

## Keyboard Shortcuts

### Navigation
| Shortcut | Action |
|----------|--------|
| Ctrl+/ | Open search bar |
| Ctrl+D | Create new dashboard |
| Ctrl+S | Save current view |
| Ctrl+R | Refresh data |
| Ctrl+F | Find in results |
| Esc | Close modal/cancel |

### Search and Query
| Shortcut | Action |
|----------|--------|
| Enter | Execute query |
| Ctrl+Enter | Execute and create chart |
| ↑/↓ | Query history |
| Tab | Auto-complete |
| Ctrl+L | Clear search |

## Troubleshooting Quick Fixes

### Common Issues and Solutions
```
❌ "No results found"
✅ Check time range, data permissions, spelling

❌ "Query too slow"
✅ Narrow time range, add specific filters, use indexed fields

❌ "Chart not loading"
✅ Check data format, try different chart type, refresh page

❌ "Alert not triggering"
✅ Verify query logic, check thresholds, test with sample data

❌ "Dashboard not refreshing"
✅ Check auto-refresh settings, verify data source connectivity
```

### Performance Optimization Tips
```
🚀 Faster Queries:
- Start with time range
- Use specific field names
- Limit result sets
- Avoid wildcards in large datasets

🚀 Efficient Dashboards:
- Limit panels per dashboard (max 12)
- Use appropriate refresh intervals
- Cache frequently used queries
- Optimize chart complexity
```

## Data Source Reference

### Common Field Names
```
Time Fields:
_time, timestamp, event_time, log_time

Source Fields:
source, sourcetype, host, index

Status Fields:
status, level, severity, priority

Performance Fields:
response_time, duration, latency, throughput

User Fields:
user, username, userid, client_ip

Error Fields:
error, exception, failure, message
```

### Index Patterns
```
Web Logs: web*, apache*, nginx*
Security: security*, auth*, firewall*
Applications: app*, application*
Infrastructure: infra*, system*, server*
Network: network*, cisco*, switch*
```

## Integration Quick Setup

### Slack Bot Commands
```
/splunk search [query] - Execute search
/splunk dashboard [name] - Share dashboard
/splunk alert [name] - Check alert status
/splunk help - Show available commands
```

### API Endpoints
```
Search: POST /api/v1/search
Dashboards: GET /api/v1/dashboards
Alerts: POST /api/v1/alerts
Reports: GET /api/v1/reports
Health: GET /health
```

## Security and Permissions

### Permission Levels
```
Viewer: Read-only access to shared content
User: Create personal dashboards and alerts
Power User: Share content, manage team resources
Admin: Full system administration
```

### Data Access Control
```
Index-based: Access to specific data indexes
Time-based: Historical data access limits
Field-based: Sensitive field masking
Export-based: Report download permissions
```

## Getting Help

### Support Channels
```
🆘 Immediate Help:
- In-platform help (? icon)
- Interactive tutorials
- Quick start guide

📚 Documentation:
- User manual
- API documentation
- Video tutorials

👥 Community:
- User forums
- Best practices wiki
- Expert chat support

🎓 Training:
- Interactive tutorials
- Live training sessions
- Certification programs
```

### Emergency Contacts
```
Technical Issues: support@company.com
Security Incidents: security@company.com
Access Requests: admin@company.com
Training Questions: training@company.com
```

---

*Keep this guide bookmarked for quick reference during daily platform use. Updated monthly with new features and best practices.*