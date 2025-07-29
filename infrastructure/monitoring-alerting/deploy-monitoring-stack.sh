#!/bin/bash

# Deploy Comprehensive Monitoring and Alerting Stack
# =================================================
# Enterprise monitoring deployment script for Splunk MCP Integration platform

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/monitoring-config.yaml"
ENVIRONMENT="${ENVIRONMENT:-production}"
NAMESPACE="splunk-mcp-monitoring-${ENVIRONMENT}"
DRY_RUN="${DRY_RUN:-false}"
VERBOSE="${VERBOSE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local required_tools=("kubectl" "helm" "python3" "yq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Check Kubernetes connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if Helm repos are available
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || true
    helm repo add grafana https://grafana.github.io/helm-charts || true
    helm repo update
    
    log_success "Prerequisites check passed"
}

# Load configuration
load_config() {
    log_info "Loading configuration for environment: $ENVIRONMENT"
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Extract environment-specific configuration using yq
    PROMETHEUS_STORAGE=$(yq eval ".environments.$ENVIRONMENT.prometheus.storage" "$CONFIG_FILE")
    PROMETHEUS_RETENTION=$(yq eval ".environments.$ENVIRONMENT.prometheus.retention" "$CONFIG_FILE")
    GRAFANA_STORAGE=$(yq eval ".environments.$ENVIRONMENT.grafana.storage" "$CONFIG_FILE")
    NAMESPACE=$(yq eval ".environments.$ENVIRONMENT.namespace" "$CONFIG_FILE")
    
    log_success "Configuration loaded successfully"
    log_info "Namespace: $NAMESPACE"
    log_info "Prometheus Storage: $PROMETHEUS_STORAGE"
    log_info "Prometheus Retention: $PROMETHEUS_RETENTION"
}

# Create namespace and RBAC
setup_namespace() {
    log_info "Setting up namespace and RBAC..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would create namespace $NAMESPACE"
        return
    fi
    
    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Label namespace for monitoring
    kubectl label namespace "$NAMESPACE" monitoring=enabled --overwrite
    
    # Create monitoring service account
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: monitoring-admin
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-admin
rules:
- apiGroups: [""]
  resources: ["nodes", "nodes/proxy", "services", "endpoints", "pods", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["extensions", "apps"]
  resources: ["deployments", "daemonsets", "replicasets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["monitoring.coreos.com"]
  resources: ["*"]
  verbs: ["*"]
- nonResourceURLs: ["/metrics"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: monitoring-admin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: monitoring-admin
subjects:
- kind: ServiceAccount
  name: monitoring-admin
  namespace: $NAMESPACE
EOF
    
    log_success "Namespace and RBAC setup completed"
}

# Deploy Prometheus Operator
deploy_prometheus_operator() {
    log_info "Deploying Prometheus Operator..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would deploy Prometheus Operator"
        return
    fi
    
    # Create values file for Prometheus Operator
    cat > "${SCRIPT_DIR}/prometheus-operator-values.yaml" <<EOF
prometheus:
  prometheusSpec:
    retention: ${PROMETHEUS_RETENTION}
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: ${PROMETHEUS_STORAGE}
    resources:
      limits:
        cpu: "4"
        memory: "16Gi"
      requests:
        cpu: "2"
        memory: "8Gi"
    serviceAccountName: monitoring-admin
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      fsGroup: 2000
    additionalScrapeConfigs:
      name: additional-scrape-configs
      key: prometheus-additional.yaml

alertmanager:
  alertmanagerSpec:
    storage:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: "20Gi"
    resources:
      limits:
        cpu: "1"
        memory: "2Gi"
      requests:
        cpu: "500m"
        memory: "1Gi"

grafana:
  enabled: true
  persistence:
    enabled: true
    size: ${GRAFANA_STORAGE}
  resources:
    limits:
      cpu: "2"
      memory: "4Gi"
    requests:
      cpu: "1"
      memory: "2Gi"
  adminPassword: "admin123"  # Should be changed in production
  plugins:
    - grafana-piechart-panel
    - grafana-worldmap-panel
    - grafana-clock-panel
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
      - name: 'default'
        orgId: 1
        folder: ''
        type: file
        disableDeletion: false
        editable: true
        options:
          path: /var/lib/grafana/dashboards/default
  dashboards:
    default:
      splunk-mcp-overview:
        url: https://raw.githubusercontent.com/your-org/splunk-mcp-dashboards/main/overview.json
      splunk-mcp-performance:
        url: https://raw.githubusercontent.com/your-org/splunk-mcp-dashboards/main/performance.json

nodeExporter:
  enabled: true
  
kubeStateMetrics:
  enabled: true

defaultRules:
  create: true
  rules:
    alertmanager: true
    etcd: true
    configReloaders: true
    general: true
    k8s: true
    kubeApiserver: true
    kubeApiserverAvailability: true
    kubeApiserverSlos: true
    kubelet: true
    kubeProxy: true
    kubePrometheusGeneral: true
    kubePrometheusNodeRecording: true
    kubernetesApps: true
    kubernetesResources: true
    kubernetesStorage: true
    kubernetesSystem: true
    node: true
    nodeExporterAlerting: true
    nodeExporterRecording: true
    prometheus: true
    prometheusOperator: true
EOF
    
    # Install Prometheus Operator
    helm upgrade --install prometheus-operator \
        prometheus-community/kube-prometheus-stack \
        --namespace "$NAMESPACE" \
        --values "${SCRIPT_DIR}/prometheus-operator-values.yaml" \
        --wait \
        --timeout 10m
    
    log_success "Prometheus Operator deployed successfully"
}

# Configure custom scrape configs
configure_scrape_configs() {
    log_info "Configuring custom scrape configurations..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would configure scrape configs"
        return
    fi
    
    # Create additional scrape config
    cat > "${SCRIPT_DIR}/additional-scrape-configs.yaml" <<EOF
- job_name: 'splunk-mcp-services'
  kubernetes_sd_configs:
  - role: endpoints
    namespaces:
      names:
      - splunk-mcp-prod
      - splunk-mcp-staging
      - splunk-mcp-dev
  relabel_configs:
  - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
    action: keep
    regex: true
  - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
    action: replace
    target_label: __metrics_path__
    regex: (.+)
  - source_labels: [__address__, __meta_kubernetes_service_annotation_prometheus_io_port]
    action: replace
    regex: ([^:]+)(?::\d+)?;(\d+)
    replacement: \${1}:\${2}
    target_label: __address__
  - action: labelmap
    regex: __meta_kubernetes_service_label_(.+)
  - source_labels: [__meta_kubernetes_namespace]
    action: replace
    target_label: kubernetes_namespace
  - source_labels: [__meta_kubernetes_service_name]
    action: replace
    target_label: kubernetes_name

- job_name: 'kubernetes-ingress'
  kubernetes_sd_configs:
  - role: pod
    namespaces:
      names:
      - ingress-nginx
  relabel_configs:
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
    action: keep
    regex: true
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scheme]
    action: replace
    target_label: __scheme__
    regex: (https?)
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
    action: replace
    target_label: __metrics_path__
    regex: (.+)
  - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
    action: replace
    regex: ([^:]+)(?::\d+)?;(\d+)
    replacement: \${1}:\${2}
    target_label: __address__
EOF
    
    # Create secret for additional scrape configs
    kubectl create secret generic additional-scrape-configs \
        --from-file=prometheus-additional.yaml="${SCRIPT_DIR}/additional-scrape-configs.yaml" \
        --namespace "$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Custom scrape configurations applied"
}

# Deploy custom alert rules
deploy_alert_rules() {
    log_info "Deploying custom alert rules..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would deploy alert rules"
        return
    fi
    
    # Extract alert rules from config and create PrometheusRule
    python3 -c "
import yaml
import sys

with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

alert_rules = config['alert_rules']

prometheus_rule = {
    'apiVersion': 'monitoring.coreos.com/v1',
    'kind': 'PrometheusRule',
    'metadata': {
        'name': 'splunk-mcp-alerts',
        'namespace': '$NAMESPACE',
        'labels': {
            'app': 'splunk-mcp-monitoring',
            'prometheus': 'kube-prometheus'
        }
    },
    'spec': alert_rules
}

with open('${SCRIPT_DIR}/splunk-mcp-alerts.yaml', 'w') as f:
    yaml.dump(prometheus_rule, f, default_flow_style=False)
"
    
    kubectl apply -f "${SCRIPT_DIR}/splunk-mcp-alerts.yaml"
    
    log_success "Custom alert rules deployed"
}

# Configure AlertManager
configure_alertmanager() {
    log_info "Configuring AlertManager..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would configure AlertManager"
        return
    fi
    
    # Extract notification configuration and create AlertManager config
    python3 -c "
import yaml
import os

with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

notification_channels = config['notification_channels']

# Create AlertManager configuration
alertmanager_config = {
    'global': {
        'smtp_smarthost': f\"{notification_channels['email']['smtp_host']}:{notification_channels['email']['smtp_port']}\",
        'smtp_from': notification_channels['email']['smtp_from']
    },
    'route': {
        'group_by': ['alertname', 'cluster', 'service'],
        'group_wait': '30s',
        'group_interval': '5m',
        'repeat_interval': '12h',
        'receiver': 'default',
        'routes': [
            {
                'match': {'severity': 'critical'},
                'receiver': 'critical-alerts',
                'group_wait': '10s',
                'repeat_interval': '1h'
            },
            {
                'match': {'severity': 'warning'},
                'receiver': 'warning-alerts',
                'repeat_interval': '4h'
            },
            {
                'match': {'category': 'security'},
                'receiver': 'security-alerts',
                'group_wait': '0s',
                'repeat_interval': '30m'
            }
        ]
    },
    'receivers': [
        {
            'name': 'default',
            'email_configs': [
                {
                    'to': notification_channels['email']['recipients']['info'],
                    'subject': '[INFO] Splunk MCP Alert: {{ .GroupLabels.alertname }}',
                    'body': 'Alert details:\\n{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
                }
            ]
        },
        {
            'name': 'critical-alerts',
            'email_configs': [
                {
                    'to': notification_channels['email']['recipients']['critical'],
                    'subject': '🚨 [CRITICAL] Splunk MCP Alert: {{ .GroupLabels.alertname }}',
                    'body': 'CRITICAL ALERT:\\n{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
                }
            ],
            'slack_configs': [
                {
                    'api_url': os.environ.get('SLACK_CRITICAL_WEBHOOK_URL', ''),
                    'channel': notification_channels['slack']['channels']['critical'],
                    'title': '🚨 Critical Alert: {{ .GroupLabels.alertname }}',
                    'text': '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
                }
            ] if os.environ.get('SLACK_CRITICAL_WEBHOOK_URL') else []
        },
        {
            'name': 'warning-alerts',
            'email_configs': [
                {
                    'to': notification_channels['email']['recipients']['warning'],
                    'subject': '⚠️ [WARNING] Splunk MCP Alert: {{ .GroupLabels.alertname }}',
                    'body': 'Warning Alert:\\n{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
                }
            ]
        },
        {
            'name': 'security-alerts',
            'email_configs': [
                {
                    'to': notification_channels['email']['recipients']['critical'],
                    'subject': '🛡️ [SECURITY] Splunk MCP Alert: {{ .GroupLabels.alertname }}',
                    'body': 'SECURITY ALERT:\\n{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
                }
            ]
        }
    ]
}

with open('${SCRIPT_DIR}/alertmanager-config.yaml', 'w') as f:
    yaml.dump(alertmanager_config, f, default_flow_style=False)
"
    
    # Create AlertManager configuration secret
    kubectl create secret generic alertmanager-main \
        --from-file=alertmanager.yaml="${SCRIPT_DIR}/alertmanager-config.yaml" \
        --namespace "$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "AlertManager configured"
}

# Deploy ServiceMonitors for application monitoring
deploy_service_monitors() {
    log_info "Deploying ServiceMonitors for application services..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would deploy ServiceMonitors"
        return
    fi
    
    # Create ServiceMonitor for Splunk MCP services
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: splunk-mcp-services
  namespace: $NAMESPACE
  labels:
    app: splunk-mcp-monitoring
spec:
  selector:
    matchLabels:
      prometheus.io/scrape: "true"
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
  namespaceSelector:
    matchNames:
    - splunk-mcp-prod
    - splunk-mcp-staging
    - splunk-mcp-dev
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: splunk-mcp-ingress
  namespace: $NAMESPACE
  labels:
    app: splunk-mcp-monitoring
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: ingress-nginx
  endpoints:
  - port: prometheus
    interval: 30s
    path: /metrics
  namespaceSelector:
    matchNames:
    - ingress-nginx
EOF
    
    log_success "ServiceMonitors deployed"
}

# Validate deployment
validate_deployment() {
    log_info "Validating monitoring stack deployment..."
    
    # Check if all pods are running
    local timeout=300
    local elapsed=0
    
    while [[ $elapsed -lt $timeout ]]; do
        local not_ready=$(kubectl get pods -n "$NAMESPACE" --no-headers | grep -v Running | grep -v Completed | wc -l)
        
        if [[ $not_ready -eq 0 ]]; then
            log_success "All monitoring pods are running"
            break
        fi
        
        log_info "Waiting for $not_ready pods to be ready... ($elapsed/${timeout}s)"
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    if [[ $elapsed -ge $timeout ]]; then
        log_warning "Some pods may not be ready, but continuing..."
    fi
    
    # Check service endpoints
    log_info "Checking service endpoints..."
    
    # Port-forward and test Prometheus
    kubectl port-forward -n "$NAMESPACE" svc/prometheus-operator-kube-p-prometheus 9090:9090 &
    local pf_pid=$!
    sleep 5
    
    if curl -s http://localhost:9090/-/healthy > /dev/null; then
        log_success "Prometheus is healthy"
    else
        log_warning "Prometheus health check failed"
    fi
    
    kill $pf_pid 2>/dev/null || true
    
    # Port-forward and test Grafana
    kubectl port-forward -n "$NAMESPACE" svc/prometheus-operator-grafana 3000:80 &
    pf_pid=$!
    sleep 5
    
    if curl -s http://localhost:3000/api/health > /dev/null; then
        log_success "Grafana is healthy"
    else
        log_warning "Grafana health check failed"
    fi
    
    kill $pf_pid 2>/dev/null || true
    
    # Check AlertManager
    kubectl port-forward -n "$NAMESPACE" svc/prometheus-operator-kube-p-alertmanager 9093:9093 &
    pf_pid=$!
    sleep 5
    
    if curl -s http://localhost:9093/-/healthy > /dev/null; then
        log_success "AlertManager is healthy"
    else
        log_warning "AlertManager health check failed"
    fi
    
    kill $pf_pid 2>/dev/null || true
}

# Show access information
show_access_info() {
    log_info "Monitoring Stack Access Information"
    echo "=================================="
    echo
    echo "Namespace: $NAMESPACE"
    echo
    echo "Access URLs (use kubectl port-forward):"
    echo "  Prometheus:  kubectl port-forward -n $NAMESPACE svc/prometheus-operator-kube-p-prometheus 9090:9090"
    echo "               Then access: http://localhost:9090"
    echo
    echo "  Grafana:     kubectl port-forward -n $NAMESPACE svc/prometheus-operator-grafana 3000:80"
    echo "               Then access: http://localhost:3000 (admin/admin123)"
    echo
    echo "  AlertManager: kubectl port-forward -n $NAMESPACE svc/prometheus-operator-kube-p-alertmanager 9093:9093"
    echo "               Then access: http://localhost:9093"
    echo
    echo "Useful Commands:"
    echo "  View pods:    kubectl get pods -n $NAMESPACE"
    echo "  View services: kubectl get svc -n $NAMESPACE"
    echo "  View alerts:  kubectl get prometheusrules -n $NAMESPACE"
    echo "  View metrics: kubectl get servicemonitors -n $NAMESPACE"
    echo
}

# Main deployment function
main() {
    log_info "Starting Splunk MCP Monitoring Stack Deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Namespace: $NAMESPACE"
    log_info "Dry Run: $DRY_RUN"
    echo
    
    check_prerequisites
    load_config
    setup_namespace
    deploy_prometheus_operator
    configure_scrape_configs
    deploy_alert_rules
    configure_alertmanager
    deploy_service_monitors
    
    if [[ "$DRY_RUN" != "true" ]]; then
        validate_deployment
        show_access_info
    fi
    
    log_success "Monitoring stack deployment completed!"
}

# Handle script arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --namespace|-n)
            NAMESPACE="$2"
            shift 2
            ;;
        --config|-c)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --verbose|-v)
            VERBOSE="true"
            set -x
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --environment, -e    Environment (production, staging, development)"
            echo "  --namespace, -n      Kubernetes namespace"
            echo "  --config, -c         Configuration file path"
            echo "  --dry-run           Perform dry run without making changes"
            echo "  --verbose, -v       Enable verbose output"
            echo "  --help, -h          Show this help message"
            echo
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"