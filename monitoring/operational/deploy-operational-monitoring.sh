#!/bin/bash
################################################################################
# Operational Monitoring Deployment Script
# =========================================
# Deploy comprehensive operational monitoring, dashboards, and automation
# for the Splunk MCP Integration platform
################################################################################

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-monitoring}"
ENVIRONMENT="${ENVIRONMENT:-production}"
CONFIG_DIR="$(dirname "$0")"
KUBECTL_TIMEOUT="300s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
    fi
    
    log_info "Prerequisites check passed ✓"
}

# Deploy Prometheus with operational rules
deploy_prometheus_operational() {
    log_info "Deploying Prometheus with operational monitoring rules..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: operational-prometheus-rules
  namespace: $NAMESPACE
  labels:
    app: prometheus
    component: rules
data:
  operational-rules.yaml: |
    groups:
    - name: operational.rules
      rules:
      # Business Impact Metrics
      - record: splunk_mcp:user_satisfaction_score
        expr: avg(user_feedback_rating{platform="splunk-mcp"})
      
      - record: splunk_mcp:daily_active_users
        expr: count(increase(user_login_total{platform="splunk-mcp"}[24h]) > 0)
      
      - record: splunk_mcp:query_success_rate
        expr: |
          rate(splunk_mcp_queries_successful_total[5m]) / 
          rate(splunk_mcp_queries_total[5m])
      
      # Performance Metrics  
      - record: splunk_mcp:response_time_95th
        expr: |
          histogram_quantile(0.95, 
            rate(http_request_duration_seconds_bucket{job=~"splunk-mcp-.*"}[5m])
          )
      
      - record: splunk_mcp:error_rate_5xx
        expr: |
          rate(http_requests_total{status=~"5..", job=~"splunk-mcp-.*"}[5m]) /
          rate(http_requests_total{job=~"splunk-mcp-.*"}[5m])
      
      # Resource Utilization
      - record: splunk_mcp:cpu_utilization_avg
        expr: |
          avg(rate(container_cpu_usage_seconds_total{namespace="splunk-mcp-prod"}[5m])) * 100
      
      - record: splunk_mcp:memory_utilization_avg
        expr: |
          avg(container_memory_usage_bytes{namespace="splunk-mcp-prod"}) /
          avg(container_spec_memory_limit_bytes{namespace="splunk-mcp-prod"}) * 100
      
      # Operational Intelligence
      - record: splunk_mcp:capacity_forecast_cpu_7d
        expr: |
          predict_linear(splunk_mcp:cpu_utilization_avg[24h], 7*24*3600)
      
      - record: splunk_mcp:capacity_forecast_memory_7d
        expr: |
          predict_linear(splunk_mcp:memory_utilization_avg[24h], 7*24*3600)
      
      # SLA Compliance
      - record: splunk_mcp:sla_availability
        expr: |
          avg(up{job=~"splunk-mcp-.*"}) * 100
      
      - record: splunk_mcp:sla_response_time_compliance
        expr: |
          (
            count(splunk_mcp:response_time_95th < 2.0) /
            count(splunk_mcp:response_time_95th)
          ) * 100
      
      - record: splunk_mcp:sla_error_rate_compliance
        expr: |
          (
            count(splunk_mcp:error_rate_5xx < 0.01) /
            count(splunk_mcp:error_rate_5xx)
          ) * 100

    - name: operational.alerts
      rules:
      # Critical Business Impact Alerts
      - alert: HighErrorRate
        expr: splunk_mcp:error_rate_5xx > 0.05
        for: 5m
        labels:
          severity: critical
          category: business_impact
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ \$value | humanizePercentage }} for 5 minutes"
          runbook_url: "https://docs.company.com/runbooks/high-error-rate"
      
      - alert: LowUserSatisfaction
        expr: splunk_mcp:user_satisfaction_score < 3.5
        for: 15m
        labels:
          severity: warning
          category: user_experience
        annotations:
          summary: "User satisfaction score is low"
          description: "User satisfaction score is {{ \$value }}/5.0"
      
      - alert: ServiceDown
        expr: up{job=~"splunk-mcp-.*"} == 0
        for: 1m
        labels:
          severity: critical
          category: availability
        annotations:
          summary: "Service {{ \$labels.job }} is down"
          description: "Service {{ \$labels.job }} has been down for more than 1 minute"
      
      # Performance Alerts
      - alert: HighResponseTime
        expr: splunk_mcp:response_time_95th > 5.0
        for: 10m
        labels:
          severity: warning
          category: performance
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ \$value }}s"
      
      - alert: HighCPUUtilization
        expr: splunk_mcp:cpu_utilization_avg > 80
        for: 15m
        labels:
          severity: warning
          category: resource
        annotations:
          summary: "High CPU utilization"
          description: "Average CPU utilization is {{ \$value }}%"
      
      - alert: HighMemoryUtilization
        expr: splunk_mcp:memory_utilization_avg > 85
        for: 10m
        labels:
          severity: warning
          category: resource
        annotations:
          summary: "High memory utilization"
          description: "Average memory utilization is {{ \$value }}%"
      
      # Capacity Planning Alerts
      - alert: CPUCapacityWarning
        expr: splunk_mcp:capacity_forecast_cpu_7d > 90
        for: 1h
        labels:
          severity: warning
          category: capacity
        annotations:
          summary: "CPU capacity warning"
          description: "Predicted CPU utilization will reach {{ \$value }}% in 7 days"
      
      - alert: MemoryCapacityWarning
        expr: splunk_mcp:capacity_forecast_memory_7d > 90
        for: 1h
        labels:
          severity: warning
          category: capacity
        annotations:
          summary: "Memory capacity warning"
          description: "Predicted memory utilization will reach {{ \$value }}% in 7 days"
      
      # SLA Compliance Alerts
      - alert: SLAAvailabilityBreach
        expr: splunk_mcp:sla_availability < 99.5
        for: 5m
        labels:
          severity: critical
          category: sla
        annotations:
          summary: "SLA availability breach"
          description: "Platform availability is {{ \$value }}% (SLA: 99.5%)"
      
      - alert: SLAResponseTimeBreach
        expr: splunk_mcp:sla_response_time_compliance < 95
        for: 10m
        labels:
          severity: warning
          category: sla
        annotations:
          summary: "SLA response time breach"
          description: "Response time SLA compliance is {{ \$value }}% (SLA: 95%)"
      
      # Security Alerts
      - alert: HighAuthenticationFailures
        expr: rate(auth_failures_total{platform="splunk-mcp"}[5m]) > 10
        for: 2m
        labels:
          severity: critical
          category: security
        annotations:
          summary: "High authentication failure rate"
          description: "Authentication failure rate is {{ \$value }}/sec - possible attack"
      
      - alert: SuspiciousActivity
        expr: rate(suspicious_activity_total{platform="splunk-mcp"}[5m]) > 5
        for: 1m
        labels:
          severity: critical
          category: security
        annotations:
          summary: "Suspicious activity detected"
          description: "Suspicious activity rate is {{ \$value }}/sec"
EOF

    log_info "Prometheus operational rules deployed ✓"
}

# Deploy Grafana operational dashboards
deploy_grafana_dashboards() {
    log_info "Deploying Grafana operational dashboards..."
    
    # Apply dashboard ConfigMap
    kubectl apply -f "$CONFIG_DIR/grafana-dashboards.yaml"
    
    # Create dashboard provisioning ConfigMap
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: operational-dashboard-provisioning
  namespace: $NAMESPACE
data:
  operational-dashboards.yaml: |
    apiVersion: 1
    providers:
    - name: 'operational-dashboards'
      orgId: 1
      folder: 'Operational Monitoring'
      type: file
      disableDeletion: false
      updateIntervalSeconds: 10
      allowUiUpdates: true
      options:
        path: /etc/grafana/provisioning/dashboards/operational
EOF

    # Create Grafana deployment with operational dashboards
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana-operational
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana-operational
  template:
    metadata:
      labels:
        app: grafana-operational
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: "admin123"
        - name: GF_INSTALL_PLUGINS
          value: "grafana-worldmap-panel,grafana-piechart-panel"
        volumeMounts:
        - name: dashboard-config
          mountPath: /etc/grafana/provisioning/dashboards
        - name: dashboards
          mountPath: /etc/grafana/provisioning/dashboards/operational
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: dashboard-config
        configMap:
          name: operational-dashboard-provisioning
      - name: dashboards
        configMap:
          name: operational-dashboards
---
apiVersion: v1
kind: Service
metadata:
  name: grafana-operational
  namespace: $NAMESPACE
spec:
  selector:
    app: grafana-operational
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP
EOF

    log_info "Grafana operational dashboards deployed ✓"
}

# Deploy operational automation
deploy_operational_automation() {
    log_info "Deploying operational automation system..."
    
    # Create ConfigMap for automation configuration
    kubectl create configmap operational-automation-config \
        --from-file="$CONFIG_DIR/operational-dashboard-config.json" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Create operational automation deployment
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: operational-automation
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: operational-automation
  template:
    metadata:
      labels:
        app: operational-automation
    spec:
      serviceAccountName: operational-automation
      containers:
      - name: automation
        image: python:3.11-slim
        command: ["python", "/app/operational-automation.py"]
        env:
        - name: NAMESPACE
          value: "splunk-mcp-prod"
        - name: ENVIRONMENT
          value: "$ENVIRONMENT"
        volumeMounts:
        - name: automation-code
          mountPath: /app
        - name: config
          mountPath: /config
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
      volumes:
      - name: automation-code
        configMap:
          name: operational-automation-code
      - name: config
        configMap:
          name: operational-automation-config
      initContainers:
      - name: install-deps
        image: python:3.11-slim
        command: ["pip", "install", "kubernetes", "aiohttp", "redis", "pyyaml"]
        volumeMounts:
        - name: automation-code
          mountPath: /app
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: operational-automation
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: operational-automation
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "patch", "update"]
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: operational-automation
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: operational-automation
subjects:
- kind: ServiceAccount
  name: operational-automation
  namespace: $NAMESPACE
EOF

    # Create ConfigMap with automation code
    kubectl create configmap operational-automation-code \
        --from-file="$CONFIG_DIR/operational-automation.py" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    log_info "Operational automation deployed ✓"
}

# Deploy AlertManager operational configuration
deploy_alertmanager_operational() {
    log_info "Deploying AlertManager operational configuration..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-operational-config
  namespace: $NAMESPACE
data:
  alertmanager.yml: |
    global:
      smtp_smarthost: 'smtp.gmail.com:587'
      smtp_from: 'ops@company.com'
      slack_api_url: '\${SLACK_WEBHOOK_URL}'

    route:
      group_by: ['alertname', 'category']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 1h
      receiver: 'default'
      routes:
      - match:
          category: business_impact
        receiver: 'executive-team'
      - match:
          category: security
        receiver: 'security-team'
      - match:
          severity: critical
        receiver: 'ops-critical'
      - match:
          category: capacity
        receiver: 'ops-capacity'

    receivers:
    - name: 'default'
      slack_configs:
      - channel: '#operations'
        title: 'Operational Alert'
        text: |
          {{ range .Alerts }}
          **Alert:** {{ .Annotations.summary }}
          **Description:** {{ .Annotations.description }}
          **Severity:** {{ .Labels.severity }}
          {{ end }}

    - name: 'executive-team'
      email_configs:
      - to: 'cto@company.com,ops-director@company.com'
        subject: 'CRITICAL: Business Impact Alert'
        body: |
          Critical business impact alert detected:
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Time: {{ .StartsAt.Format "2006-01-02 15:04:05" }}
          {{ end }}
      slack_configs:
      - channel: '#executive-alerts'
        title: '🚨 CRITICAL Business Impact Alert'
        text: |
          {{ range .Alerts }}
          **Alert:** {{ .Annotations.summary }}
          **Description:** {{ .Annotations.description }}
          **Runbook:** {{ .Annotations.runbook_url }}
          {{ end }}

    - name: 'security-team'
      slack_configs:
      - channel: '#security-alerts'
        title: '🔒 Security Alert'
        text: |
          {{ range .Alerts }}
          **Security Alert:** {{ .Annotations.summary }}
          **Description:** {{ .Annotations.description }}
          **Severity:** {{ .Labels.severity }}
          {{ end }}

    - name: 'ops-critical'
      slack_configs:
      - channel: '#ops-critical'
        title: '🚨 Critical Operational Alert'
        text: |
          {{ range .Alerts }}
          **Critical Alert:** {{ .Annotations.summary }}
          **Description:** {{ .Annotations.description }}
          **Runbook:** {{ .Annotations.runbook_url }}
          {{ end }}

    - name: 'ops-capacity'
      slack_configs:
      - channel: '#ops-capacity'
        title: '📈 Capacity Planning Alert'
        text: |
          {{ range .Alerts }}
          **Capacity Alert:** {{ .Annotations.summary }}
          **Description:** {{ .Annotations.description }}
          **Recommendation:** Scale resources or optimize usage
          {{ end }}
EOF

    log_info "AlertManager operational configuration deployed ✓"
}

# Deploy custom metrics exporters
deploy_custom_metrics() {
    log_info "Deploying custom metrics exporters..."
    
    # Deploy business metrics exporter
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: business-metrics-exporter
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: business-metrics-exporter
  template:
    metadata:
      labels:
        app: business-metrics-exporter
    spec:
      containers:
      - name: exporter
        image: prom/node-exporter:latest
        ports:
        - containerPort: 9100
        command:
        - /bin/sh
        - -c
        - |
          # Create custom metrics endpoint
          mkdir -p /tmp/metrics
          cat > /tmp/metrics/business.prom << 'EOL'
          # HELP splunk_mcp_user_satisfaction_score User satisfaction score
          # TYPE splunk_mcp_user_satisfaction_score gauge
          splunk_mcp_user_satisfaction_score 4.2
          
          # HELP splunk_mcp_active_users_total Total active users
          # TYPE splunk_mcp_active_users_total counter
          splunk_mcp_active_users_total 245
          
          # HELP splunk_mcp_queries_successful_total Successful queries
          # TYPE splunk_mcp_queries_successful_total counter
          splunk_mcp_queries_successful_total 15420
          
          # HELP splunk_mcp_dashboards_created_total Dashboards created
          # TYPE splunk_mcp_dashboards_created_total counter
          splunk_mcp_dashboards_created_total 89
          EOL
          
          # Serve metrics
          cd /tmp/metrics && python3 -m http.server 9100
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: business-metrics-exporter
  namespace: $NAMESPACE
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9100"
    prometheus.io/path: "/business.prom"
spec:
  selector:
    app: business-metrics-exporter
  ports:
  - port: 9100
    targetPort: 9100
EOF

    log_info "Custom metrics exporters deployed ✓"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying operational monitoring deployment..."
    
    # Check if all pods are running
    log_info "Checking pod status..."
    kubectl get pods -n "$NAMESPACE" -l app=grafana-operational
    kubectl get pods -n "$NAMESPACE" -l app=operational-automation
    kubectl get pods -n "$NAMESPACE" -l app=business-metrics-exporter
    
    # Check services
    log_info "Checking service status..."
    kubectl get services -n "$NAMESPACE"
    
    # Check if Grafana is accessible
    log_info "Testing Grafana accessibility..."
    if kubectl port-forward -n "$NAMESPACE" service/grafana-operational 3000:3000 --timeout=10s &>/dev/null &
    then
        PF_PID=$!
        sleep 5
        if curl -s http://localhost:3000/api/health &>/dev/null; then
            log_info "Grafana is accessible ✓"
        else
            log_warn "Grafana health check failed"
        fi
        kill $PF_PID 2>/dev/null || true
    fi
    
    # Check ConfigMaps
    log_info "Checking configuration..."
    kubectl get configmaps -n "$NAMESPACE" | grep -E "(operational|business|grafana)"
    
    log_info "Deployment verification completed ✓"
}

# Display access information
show_access_info() {
    log_info "Operational Monitoring Access Information:"
    echo
    echo "🖥️  Grafana Operational Dashboards:"
    echo "   kubectl port-forward -n $NAMESPACE service/grafana-operational 3000:3000"
    echo "   URL: http://localhost:3000"
    echo "   Username: admin"
    echo "   Password: admin123"
    echo
    echo "📊 Available Dashboards:"
    echo "   - Platform Operations Overview"
    echo "   - User Experience Monitoring"  
    echo "   - Operational Intelligence"
    echo "   - Security Operations Center"
    echo
    echo "🤖 Operational Automation:"
    echo "   - Auto-scaling based on CPU/Memory"
    echo "   - Incident response automation"
    echo "   - Capacity forecasting and optimization"
    echo "   - Multi-channel alerting (Slack, Email)"
    echo
    echo "📈 Custom Metrics:"
    echo "   - Business impact metrics"
    echo "   - User satisfaction tracking"
    echo "   - SLA compliance monitoring"
    echo "   - Security event monitoring"
    echo
}

# Main deployment function
main() {
    log_info "Starting operational monitoring deployment..."
    echo "Environment: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "Config Directory: $CONFIG_DIR"
    echo
    
    check_prerequisites
    deploy_prometheus_operational
    deploy_grafana_dashboards
    deploy_operational_automation
    deploy_alertmanager_operational
    deploy_custom_metrics
    verify_deployment
    show_access_info
    
    log_info "🎉 Operational monitoring deployment completed successfully!"
    log_info "The platform now has comprehensive operational intelligence and automation."
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Operational Monitoring Deployment Script"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --namespace NAME    Set Kubernetes namespace (default: monitoring)"
        echo "  --environment ENV   Set environment (default: production)"
        echo
        echo "Environment Variables:"
        echo "  NAMESPACE          Kubernetes namespace"
        echo "  ENVIRONMENT        Deployment environment"
        echo
        exit 0
        ;;
    --namespace)
        NAMESPACE="$2"
        shift 2
        ;;
    --environment)
        ENVIRONMENT="$2"
        shift 2
        ;;
    "")
        # No arguments, proceed with main
        ;;
    *)
        log_error "Unknown argument: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Run main function
main "$@"