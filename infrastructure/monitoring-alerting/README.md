# Comprehensive Monitoring and Alerting Infrastructure

## Overview

This directory contains a complete enterprise-grade monitoring and alerting infrastructure for the Splunk MCP Integration platform. The system provides comprehensive observability through Prometheus, Grafana, and AlertManager with custom dashboards, alerting rules, and notification channels.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Monitoring & Alerting Stack                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ Prometheus  │  │   Grafana   │  │AlertManager │  │ServiceMon│ │
│  │ (Metrics)   │  │(Dashboard)  │  │(Alerts)     │  │ (Config) │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                    Application Services                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ API Gateway │  │ NLP Engine  │  │Visualization│  │21+ More  │ │
│  │   :8000     │  │   :8001     │  │   :8002     │  │ Services │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     Infrastructure                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ Kubernetes  │  │ PostgreSQL  │  │    Redis    │  │  Ingress │ │
│  │  Cluster    │  │ Database    │  │   Cache     │  │   NGINX  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Core Monitoring Stack
- **Prometheus**: Metrics collection, storage, and alerting engine
- **Grafana**: Visualization, dashboards, and analytics
- **AlertManager**: Alert routing, grouping, and notification management
- **Prometheus Operator**: Kubernetes-native Prometheus management

### Supporting Components
- **Node Exporter**: System-level metrics collection
- **Kube State Metrics**: Kubernetes object metrics
- **ServiceMonitors**: Custom service discovery for application metrics
- **PrometheusRules**: Custom alerting and recording rules

### Custom Features
- **Multi-environment support**: Production, staging, and development configurations
- **Advanced alerting**: Business metrics, security, and infrastructure alerts
- **Comprehensive dashboards**: System overview, performance, business KPIs, security
- **Enterprise integrations**: Slack, email, PagerDuty notifications

## Quick Start

### Prerequisites

1. **Kubernetes Cluster** (v1.20+)
   ```bash
   kubectl version --client
   ```

2. **Helm** (v3+)
   ```bash
   helm version
   ```

3. **Required CLI Tools**
   ```bash
   # Install yq for YAML processing
   sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
   sudo chmod +x /usr/local/bin/yq
   ```

4. **Environment Variables** (Optional)
   ```bash
   export SLACK_CRITICAL_WEBHOOK_URL="https://hooks.slack.com/..."
   export SLACK_WARNING_WEBHOOK_URL="https://hooks.slack.com/..."
   export PAGERDUTY_API_KEY="your-pagerduty-key"
   ```

### Deploy Monitoring Stack

1. **Clone and Navigate**
   ```bash
   cd infrastructure/monitoring-alerting
   ```

2. **Deploy to Production**
   ```bash
   ./deploy-monitoring-stack.sh --environment production
   ```

3. **Deploy to Staging**
   ```bash
   ./deploy-monitoring-stack.sh --environment staging
   ```

4. **Deploy to Development**
   ```bash
   ./deploy-monitoring-stack.sh --environment development
   ```

### Access Dashboards

1. **Prometheus**
   ```bash
   kubectl port-forward -n splunk-mcp-monitoring-prod svc/prometheus-operator-kube-p-prometheus 9090:9090
   # Access: http://localhost:9090
   ```

2. **Grafana**
   ```bash
   kubectl port-forward -n splunk-mcp-monitoring-prod svc/prometheus-operator-grafana 3000:80
   # Access: http://localhost:3000 (admin/admin123)
   ```

3. **AlertManager**
   ```bash
   kubectl port-forward -n splunk-mcp-monitoring-prod svc/prometheus-operator-kube-p-alertmanager 9093:9093
   # Access: http://localhost:9093
   ```

## Configuration

### Environment-Specific Settings

The system supports multiple environments with different resource allocations:

- **Production**: High availability, large storage, multiple replicas
- **Staging**: Medium resources, moderate availability
- **Development**: Minimal resources, single replicas

### Notification Channels

Configure notification channels in `monitoring-config.yaml`:

```yaml
notification_channels:
  email:
    smtp_host: "smtp.company.com"
    recipients:
      critical: "ops-team@company.com"
  slack:
    channels:
      critical: "#platform-alerts-critical"
  pagerduty:
    api_key: "${PAGERDUTY_API_KEY}"
```

### Custom Metrics

The system automatically discovers services with Prometheus annotations:

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
spec:
  # ... service definition
```

## Dashboards

### System Overview Dashboard
- **Purpose**: High-level system health and performance
- **Metrics**: CPU, memory, disk usage, pod status
- **Refresh**: 30 seconds
- **Audience**: Operations team, executives

### Application Performance Dashboard
- **Purpose**: Application-specific performance metrics
- **Metrics**: Request rate, error rate, response time, database connections
- **Refresh**: 15 seconds
- **Audience**: Development team, SRE

### Business KPIs Dashboard
- **Purpose**: Business metrics and key performance indicators
- **Metrics**: Active users, query volume, user satisfaction, feature adoption
- **Refresh**: 1 minute
- **Audience**: Product managers, executives

### Security Monitoring Dashboard
- **Purpose**: Security events and compliance metrics
- **Metrics**: Failed logins, suspicious activity, SSL certificate status
- **Refresh**: 30 seconds
- **Audience**: Security team, compliance officers

## Alert Rules

### Infrastructure Alerts

- **NodeDown**: Node unavailable (Critical)
- **HighCPUUsage**: CPU > 85% for 10m (Warning)
- **HighMemoryUsage**: Memory > 90% for 5m (Critical)
- **DiskSpaceLow**: Disk < 15% (Warning)
- **DiskSpaceCritical**: Disk < 5% (Critical)

### Kubernetes Alerts

- **PodCrashLooping**: Pod restart rate > 0 (Critical)
- **PodNotReady**: Pod not ready for 10m (Warning)
- **DeploymentReplicasMismatch**: Replica count mismatch (Warning)

### Application Alerts

- **HighErrorRate**: Error rate > 5% (Warning)
- **HighResponseTime**: 95th percentile > 2s (Warning)
- **ServiceDown**: Service unavailable (Critical)

### Database Alerts

- **PostgreSQLDown**: Database unavailable (Critical)
- **HighDatabaseConnections**: Connections > 80% (Warning)
- **RedisDown**: Cache unavailable (Critical)
- **HighRedisMemoryUsage**: Memory > 90% (Warning)

### Security Alerts

- **HighFailedLoginAttempts**: Failed logins > 5/5m (Warning)
- **SuspiciousActivity**: Security events > 2/1m (Critical)
- **SSLCertificateExpiring**: Certificate expires < 30 days (Warning)

## Advanced Features

### Multi-Environment Support

```bash
# Deploy to different environments
./deploy-monitoring-stack.sh --environment production
./deploy-monitoring-stack.sh --environment staging
./deploy-monitoring-stack.sh --environment development
```

### Dry Run Mode

```bash
# Test deployment without making changes
./deploy-monitoring-stack.sh --dry-run
```

### Custom Configuration

```bash
# Use custom configuration file
./deploy-monitoring-stack.sh --config custom-config.yaml
```

### Verbose Output

```bash
# Enable detailed logging
./deploy-monitoring-stack.sh --verbose
```

## Monitoring Validation

### Health Checks

1. **Check Pod Status**
   ```bash
   kubectl get pods -n splunk-mcp-monitoring-prod
   ```

2. **Verify Services**
   ```bash
   kubectl get svc -n splunk-mcp-monitoring-prod
   ```

3. **Check Prometheus Targets**
   ```bash
   # Port-forward to Prometheus
   kubectl port-forward -n splunk-mcp-monitoring-prod svc/prometheus-operator-kube-p-prometheus 9090:9090
   # Visit http://localhost:9090/targets
   ```

4. **Validate Alert Rules**
   ```bash
   kubectl get prometheusrules -n splunk-mcp-monitoring-prod
   ```

### Test Alerting

1. **Simulate High CPU**
   ```bash
   kubectl run cpu-test --image=busybox --restart=Never -- /bin/sh -c "while true; do true; done"
   ```

2. **Check Alert Status**
   ```bash
   # Access AlertManager
   kubectl port-forward -n splunk-mcp-monitoring-prod svc/prometheus-operator-kube-p-alertmanager 9093:9093
   # Visit http://localhost:9093/#/alerts
   ```

3. **Cleanup Test**
   ```bash
   kubectl delete pod cpu-test
   ```

## Production Considerations

### Resource Requirements

| Environment | Prometheus Storage | Grafana Storage | CPU Limit | Memory Limit |
|-------------|-------------------|----------------|-----------|-------------|
| Production  | 500Gi             | 50Gi           | 4 cores   | 16Gi        |
| Staging     | 200Gi             | 20Gi           | 2 cores   | 8Gi         |
| Development | 50Gi              | 10Gi           | 1 core    | 4Gi         |

### Security

1. **RBAC**: Least-privilege access controls
2. **Network Policies**: Traffic segmentation
3. **Encryption**: Data encryption at rest and in transit
4. **Secrets Management**: Kubernetes secrets for sensitive data

### High Availability

- **Prometheus**: Multiple replicas with persistent storage
- **Grafana**: Load-balanced instances
- **AlertManager**: Clustered configuration
- **Data Persistence**: Persistent volumes for all components

### Backup and Recovery

1. **Prometheus Data**
   ```bash
   # Backup Prometheus data
   kubectl exec -n splunk-mcp-monitoring-prod prometheus-0 -- tar czf /tmp/prometheus-backup.tar.gz /prometheus
   ```

2. **Grafana Dashboards**
   ```bash
   # Export dashboards
   kubectl get configmap grafana-dashboards -n splunk-mcp-monitoring-prod -o yaml > dashboards-backup.yaml
   ```

3. **Configuration Backup**
   ```bash
   # Backup all monitoring configurations
   kubectl get all,configmaps,secrets,prometheusrules,servicemonitors -n splunk-mcp-monitoring-prod -o yaml > monitoring-backup.yaml
   ```

## Troubleshooting

### Common Issues

1. **Pods Not Starting**
   ```bash
   kubectl describe pod <pod-name> -n splunk-mcp-monitoring-prod
   kubectl logs <pod-name> -n splunk-mcp-monitoring-prod
   ```

2. **No Metrics Data**
   ```bash
   # Check ServiceMonitor configuration
   kubectl get servicemonitors -n splunk-mcp-monitoring-prod
   
   # Verify service annotations
   kubectl get svc -n splunk-mcp-prod -o yaml | grep prometheus
   ```

3. **Alerts Not Firing**
   ```bash
   # Check PrometheusRule status
   kubectl describe prometheusrules -n splunk-mcp-monitoring-prod
   
   # Verify AlertManager configuration
   kubectl logs deployment/prometheus-operator-kube-p-alertmanager -n splunk-mcp-monitoring-prod
   ```

4. **Storage Issues**
   ```bash
   # Check PVC status
   kubectl get pvc -n splunk-mcp-monitoring-prod
   
   # Check storage usage
   kubectl exec -n splunk-mcp-monitoring-prod prometheus-0 -- df -h
   ```

### Performance Tuning

1. **Prometheus Configuration**
   - Adjust scrape intervals based on requirements
   - Use recording rules for expensive queries
   - Configure appropriate retention periods

2. **Grafana Optimization**
   - Use template variables for dynamic dashboards
   - Implement proper caching strategies
   - Optimize query patterns

3. **Storage Optimization**
   - Use appropriate storage classes
   - Configure data lifecycle policies
   - Monitor storage usage trends

## Integration with Splunk MCP Services

### Service Annotations

Add these annotations to your services:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
```

### Custom Metrics

Implement these metrics in your services:

```python
# Example Python metrics
from prometheus_client import Counter, Histogram, Gauge

# Request counter
requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])

# Response time histogram
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

# Active users gauge
active_users = Gauge('active_users_total', 'Number of active users')
```

### Business Metrics

Implement business-specific metrics:

```python
# User satisfaction
user_satisfaction = Gauge('user_satisfaction_score', 'User satisfaction score (1-5)')

# Query success rate
query_success = Counter('splunk_queries_success_total', 'Successful Splunk queries')
query_failure = Counter('splunk_queries_failed_total', 'Failed Splunk queries')

# Feature usage
feature_usage = Counter('feature_usage_total', 'Feature usage count', ['feature', 'user_type'])
```

## Maintenance

### Regular Tasks

1. **Daily**
   - Review overnight alerts
   - Check dashboard health
   - Monitor resource usage

2. **Weekly**
   - Update alert thresholds
   - Review metric retention
   - Test backup procedures

3. **Monthly**
   - Update dashboard panels
   - Review notification channels
   - Analyze performance trends

4. **Quarterly**
   - Review and update alert rules
   - Capacity planning assessment
   - Security review

### Upgrade Procedures

1. **Backup Current State**
   ```bash
   kubectl get all,configmaps,secrets -n splunk-mcp-monitoring-prod -o yaml > backup.yaml
   ```

2. **Update Helm Chart**
   ```bash
   helm repo update
   helm upgrade prometheus-operator prometheus-community/kube-prometheus-stack -n splunk-mcp-monitoring-prod
   ```

3. **Validate Upgrade**
   ```bash
   ./deploy-monitoring-stack.sh --environment production --dry-run
   ```

## Support and Documentation

### Resources

- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Documentation**: https://grafana.com/docs/
- **Kubernetes Monitoring**: https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/

### Contact Information

- **Platform Team**: platform-team@company.com
- **Operations Team**: ops-team@company.com
- **On-Call Support**: platform-oncall@company.com

### Runbooks

- **High CPU Usage**: https://docs.company.com/runbooks/high-cpu
- **Database Issues**: https://docs.company.com/runbooks/database-down
- **Service Outages**: https://docs.company.com/runbooks/service-down
- **Security Incidents**: https://docs.company.com/runbooks/security-incident

---

## Files in This Directory

- `monitoring-stack-deployment.py`: Python-based monitoring deployment system
- `monitoring-config.yaml`: Comprehensive configuration for all environments
- `deploy-monitoring-stack.sh`: Shell script for easy deployment
- `README.md`: This documentation file

## Deployment Summary

The monitoring infrastructure provides:

- **Complete Observability**: Metrics, logs, and traces for all services
- **Proactive Alerting**: Business, infrastructure, and security alerts
- **Executive Dashboards**: High-level KPIs and health indicators
- **Enterprise Integration**: Slack, email, PagerDuty notifications
- **Multi-Environment Support**: Production, staging, development configurations
- **High Availability**: Clustered, persistent, and scalable architecture

This monitoring system ensures comprehensive visibility into the Splunk MCP Integration platform with enterprise-grade reliability, security, and performance.

---

*Last Updated: July 28, 2025*  
*Version: 1.0.0*  
*Status: Production Ready*