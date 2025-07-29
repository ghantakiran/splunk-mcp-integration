# Monitoring and Alerting Configuration
# =====================================

This directory contains comprehensive monitoring and alerting configuration for the Splunk MCP Integration Platform.

## Overview

The monitoring stack provides complete observability across all platform components:

- **Prometheus** - Metrics collection and storage
- **AlertManager** - Alert routing and notification management  
- **Grafana** - Visualization and dashboards
- **Custom Metrics** - Application-specific monitoring

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Applications  │───▶│   Prometheus    │───▶│     Grafana     │
│   (21 Services) │    │  (Metrics DB)   │    │  (Dashboards)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  AlertManager   │───▶│  Notifications  │
                       │ (Alert Routing) │    │ Email/Slack/PD  │
                       └─────────────────┘    └─────────────────┘
```

## Directory Structure

```
monitoring/
├── prometheus/
│   ├── prometheus-config.yaml      # Main Prometheus configuration
│   ├── alerting-rules.yaml         # Alert rule definitions
│   └── recording-rules.yaml        # Metric aggregation rules
├── alertmanager/
│   ├── alertmanager-config.yaml    # Alert routing configuration
│   └── templates/                  # Custom notification templates
├── grafana/
│   ├── dashboards/                 # Pre-built dashboards
│   │   ├── platform-overview.json # Main platform dashboard
│   │   ├── service-details.json   # Individual service metrics
│   │   └── infrastructure.json    # Infrastructure monitoring
│   └── datasources/               # Data source configurations
└── README.md                      # This file
```

## Quick Start

### 1. Deploy Monitoring Stack

```bash
# Deploy Prometheus
kubectl apply -f prometheus/

# Deploy AlertManager  
kubectl apply -f alertmanager/

# Deploy Grafana
kubectl apply -f grafana/
```

### 2. Configure Secrets

```bash
# Create AlertManager secrets
kubectl create secret generic alertmanager-secrets \
  --from-literal=smtp-password="your-smtp-password" \
  --from-literal=slack-webhook-url="your-slack-webhook" \
  --from-literal=pagerduty-service-key="your-pd-key" \
  -n monitoring

# Create Grafana admin password
kubectl create secret generic grafana-admin \
  --from-literal=admin-password="secure-password" \
  -n monitoring
```

### 3. Access Dashboards

```bash
# Port forward to Grafana
kubectl port-forward svc/grafana 3000:3000 -n monitoring

# Access at http://localhost:3000
# Default: admin / (password from secret)
```

## Monitoring Targets

### Core Services (Critical)
- **API Gateway** (Port 8000) - Main entry point
- **NLP Engine** (Port 8001) - Natural language processing  
- **Visualization** (Port 8002) - Chart generation
- **Alert Manager** (Port 8003) - Platform alerting

### Integration Services
- **Slack/Teams Bots** (Ports 8004/8005) - Messaging platforms
- **Email Service** (Port 8006) - Email notifications
- **Webhook Service** (Port 8007) - External integrations
- **BI Integration** (Port 8008) - Business intelligence

### Export Services  
- **PDF Export** (Port 8009) - Document generation
- **PowerPoint Export** (Port 8011) - Presentations
- **HTML Report** (Port 8012) - Web reports
- **Word Export** (Port 8013) - Document creation
- **CSV Export** (Port 8014) - Data extraction
- **JSON/XML Export** (Port 8015) - Structured data

### Platform Services
- **Secure Sharing** (Port 8016) - Content sharing
- **Report Scheduling** (Port 8015) - Automated reports
- **Frontend** (Port 3000) - React user interface

### Infrastructure
- **PostgreSQL** (Port 5432) - Primary database
- **Redis** (Port 6379) - Cache and sessions
- **Kubernetes** - Container orchestration

## Alert Categories

### Critical Alerts (Immediate Response)
- Service down conditions
- High error rates (>5%)
- Extreme response times (>3s)
- Database/Redis failures
- Node/pod failures

### Warning Alerts (Review Required)
- Elevated response times (>1s)
- Resource usage above 80%
- Authentication failures
- Queue backups
- SSL certificate expiration

### Info Alerts (Awareness)
- Low user activity
- High report generation
- Business metric anomalies

## Notification Channels

### Email Recipients
- **Critical**: platform-oncall@company.com
- **Infrastructure**: infrastructure-team@company.com  
- **Security**: security-team@company.com
- **General**: platform-team@company.com

### Slack Channels
- **#platform-alerts** - Critical platform issues
- **#platform-warnings** - Warning-level alerts
- **#infrastructure-alerts** - Infrastructure issues
- **#security-alerts** - Security incidents

### PagerDuty
- Critical alerts trigger PagerDuty incidents
- 24/7 on-call rotation for production issues

## Key Metrics

### Application Metrics
```promql
# Request rate
rate(http_requests_total[5m])

# Response time percentiles  
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Service availability
up{job="service-name"}
```

### Infrastructure Metrics
```promql
# CPU usage
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage  
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Database connections
postgresql_connections_active / postgresql_connections_max

# Redis memory
redis_memory_used_bytes / redis_memory_max_bytes
```

### Business Metrics
```promql
# User sessions
rate(user_sessions_total[1h])

# Query volume
rate(splunk_queries_total[5m])

# Report generation
rate(reports_generated_total[1h])

# Export job success rate
rate(export_jobs_success_total[5m]) / rate(export_jobs_total[5m])
```

## Grafana Dashboards

### 1. Platform Overview
- **URL**: `/d/splunk-mcp-overview`
- **Purpose**: High-level system health
- **Panels**: Service status, request rates, response times, infrastructure health

### 2. Service Details  
- **URL**: `/d/splunk-mcp-services`
- **Purpose**: Detailed service metrics
- **Panels**: Per-service metrics, logs, traces

### 3. Infrastructure
- **URL**: `/d/splunk-mcp-infrastructure`  
- **Purpose**: Infrastructure monitoring
- **Panels**: Node metrics, database, Redis, Kubernetes

### 4. Business Metrics
- **URL**: `/d/splunk-mcp-business`
- **Purpose**: Business KPIs and usage
- **Panels**: User activity, query patterns, report generation

## Alert Runbooks

Each alert includes a runbook URL with detailed troubleshooting steps:

- **Base URL**: `https://docs.splunk-mcp.com/runbooks/`
- **Format**: `{alert-name-lowercase}`
- **Example**: `https://docs.splunk-mcp.com/runbooks/service-down`

### Common Runbooks
- `service-down` - Service availability issues
- `high-response-time` - Performance degradation
- `high-error-rate` - Error rate spikes  
- `database-failure` - Database connectivity
- `pod-crash-loop` - Kubernetes pod issues
- `high-cpu` - CPU utilization problems
- `ssl-expiry` - Certificate renewal

## Maintenance

### Daily Tasks
- [ ] Review overnight alerts and incidents
- [ ] Check dashboard health indicators
- [ ] Validate monitoring data completeness

### Weekly Tasks  
- [ ] Review alert noise and false positives
- [ ] Update alert thresholds based on trends
- [ ] Test notification channels

### Monthly Tasks
- [ ] Review and optimize recording rules
- [ ] Update dashboard panels and queries
- [ ] Analyze monitoring cost and retention
- [ ] Update runbook documentation

## Configuration Management

### Environment Variables
```bash
# AlertManager Configuration
SMTP_SMARTHOST=smtp.company.com:587
SMTP_FROM=alerts@splunk-mcp.company.com  
SMTP_AUTH_USERNAME=alerts@splunk-mcp.company.com
SMTP_AUTH_PASSWORD=secret

# Notification Endpoints
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SLACK_SECURITY_WEBHOOK_URL=https://hooks.slack.com/...
PAGERDUTY_SERVICE_KEY=integration-key
```

### Secrets Management
```bash
# Create monitoring secrets
kubectl create secret generic monitoring-config \
  --from-literal=smtp-password="$SMTP_PASSWORD" \
  --from-literal=slack-webhook="$SLACK_WEBHOOK_URL" \
  --from-literal=pagerduty-key="$PAGERDUTY_SERVICE_KEY" \
  -n monitoring
```

## Troubleshooting

### Common Issues

#### No Metrics Data
```bash
# Check Prometheus targets
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
# Visit http://localhost:9090/targets

# Check service annotations
kubectl get pods -n splunk-mcp-prod -o yaml | grep prometheus
```

#### Alerts Not Firing
```bash
# Check AlertManager status
kubectl logs deployment/alertmanager -n monitoring

# Validate alert rules
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
# Visit http://localhost:9090/rules
```

#### Missing Notifications
```bash
# Check AlertManager config
kubectl logs deployment/alertmanager -n monitoring

# Test notification channels
curl -X POST "http://alertmanager:9093/api/v1/alerts" \
  -H "Content-Type: application/json" \
  -d '[{"labels":{"alertname":"test"}}]'
```

### Performance Optimization

#### High Cardinality Metrics
```bash
# Find high cardinality series
curl http://prometheus:9090/api/v1/label/__name__/values | jq '.data[]' | sort

# Check series count per metric
curl 'http://prometheus:9090/api/v1/query?query=topk(10,count%20by%20(__name__)({__name__=~".%2B"}))'
```

#### Storage Optimization  
```bash
# Check storage usage
kubectl exec prometheus-0 -n monitoring -- df -h /prometheus

# Compact blocks
kubectl exec prometheus-0 -n monitoring -- promtool tsdb analyze /prometheus
```

## Security Considerations

### Access Control
- Grafana authentication via LDAP/OIDC
- Prometheus data encryption at rest
- Network policies for monitoring namespace
- RBAC for monitoring components

### Data Privacy
- Metric scraping filtered by namespace
- Sensitive labels excluded from metrics
- Alert content sanitized
- Log data anonymization

## Support and Documentation

### Resources
- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Documentation**: https://grafana.com/docs/
- **AlertManager Guide**: https://prometheus.io/docs/alerting/
- **Platform Runbooks**: https://docs.splunk-mcp.com/runbooks/

### Contact Information
- **Platform Team**: platform-team@company.com
- **Infrastructure Team**: infrastructure-team@company.com  
- **On-Call**: platform-oncall@company.com

---

*Last Updated: December 2024*
*Version: 2.0.0*