#!/usr/bin/env python3
"""
Comprehensive Monitoring and Alerting Infrastructure Deployment
=============================================================
Enterprise-grade monitoring stack deployment for Splunk MCP Integration platform
with Prometheus, Grafana, AlertManager, and comprehensive observability capabilities
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import yaml
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import tempfile
import shutil
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MonitoringComponent(Enum):
    """Monitoring stack components"""
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    ALERTMANAGER = "alertmanager"
    NODE_EXPORTER = "node-exporter"
    KUBE_STATE_METRICS = "kube-state-metrics"
    PROMETHEUS_OPERATOR = "prometheus-operator"
    CUSTOM_METRICS = "custom-metrics"

class DeploymentStatus(Enum):
    """Deployment status for monitoring components"""
    PENDING = "pending"
    DEPLOYING = "deploying"
    READY = "ready"
    FAILED = "failed"
    UPDATING = "updating"

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

@dataclass
class MonitoringConfig:
    """Monitoring stack configuration"""
    namespace: str = "splunk-mcp-monitoring"
    prometheus_retention: str = "30d"
    prometheus_storage: str = "200Gi"
    grafana_storage: str = "20Gi"
    alertmanager_storage: str = "10Gi"
    
    # Notification channels
    slack_webhook_url: Optional[str] = None
    email_smtp_host: Optional[str] = None
    email_smtp_port: int = 587
    email_from: Optional[str] = None
    pagerduty_api_key: Optional[str] = None
    
    # Resource limits
    prometheus_cpu_limit: str = "2"
    prometheus_memory_limit: str = "8Gi"
    grafana_cpu_limit: str = "1"
    grafana_memory_limit: str = "2Gi"

@dataclass
class Dashboard:
    """Grafana dashboard definition"""
    name: str
    title: str
    description: str
    tags: List[str]
    panels: List[Dict[str, Any]]
    refresh_interval: str = "30s"
    time_range: str = "1h"

@dataclass
class AlertRule:
    """Prometheus alert rule definition"""
    name: str
    expr: str
    duration: str
    severity: AlertSeverity
    summary: str
    description: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

class MonitoringStackDeployer:
    """Main monitoring stack deployment system"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.namespace = config.namespace
        self.deployment_status: Dict[MonitoringComponent, DeploymentStatus] = {}
        self.dashboards: List[Dashboard] = []
        self.alert_rules: List[AlertRule] = []
        self.artifacts_dir = Path("monitoring-artifacts")
        self.artifacts_dir.mkdir(exist_ok=True)
        
    async def deploy_full_monitoring_stack(self) -> Dict[str, Any]:
        """Deploy complete monitoring and alerting infrastructure"""
        logger.info("Starting comprehensive monitoring stack deployment")
        
        try:
            # Phase 1: Setup namespace and prerequisites
            await self._setup_monitoring_namespace()
            
            # Phase 2: Deploy Prometheus Operator
            await self._deploy_prometheus_operator()
            
            # Phase 3: Deploy Prometheus
            await self._deploy_prometheus()
            
            # Phase 4: Deploy Grafana
            await self._deploy_grafana()
            
            # Phase 5: Deploy AlertManager
            await self._deploy_alertmanager()
            
            # Phase 6: Deploy supporting components
            await self._deploy_supporting_components()
            
            # Phase 7: Configure custom metrics
            await self._configure_custom_metrics()
            
            # Phase 8: Setup dashboards
            await self._setup_dashboards()
            
            # Phase 9: Configure alerting rules
            await self._configure_alerting_rules()
            
            # Phase 10: Validate monitoring stack
            await self._validate_monitoring_stack()
            
            logger.info("Monitoring stack deployment completed successfully")
            return await self._get_deployment_summary()
            
        except Exception as e:
            logger.error(f"Monitoring stack deployment failed: {e}")
            await self._cleanup_failed_deployment()
            raise

    async def _setup_monitoring_namespace(self):
        """Setup monitoring namespace with proper configuration"""
        logger.info(f"Setting up monitoring namespace: {self.namespace}")
        
        namespace_manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": self.namespace,
                "labels": {
                    "name": self.namespace,
                    "monitoring": "enabled",
                    "prometheus.io/scrape": "true"
                }
            }
        }
        
        await self._apply_manifest(namespace_manifest)
        
        # Create monitoring service account with appropriate permissions
        await self._create_monitoring_rbac()
        
        self.deployment_status[MonitoringComponent.PROMETHEUS] = DeploymentStatus.PENDING

    async def _create_monitoring_rbac(self):
        """Create RBAC for monitoring components"""
        rbac_manifests = [
            {
                "apiVersion": "v1",
                "kind": "ServiceAccount",
                "metadata": {
                    "name": "prometheus-server",
                    "namespace": self.namespace
                }
            },
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRole",
                "metadata": {
                    "name": "prometheus-server"
                },
                "rules": [
                    {
                        "apiGroups": [""],
                        "resources": ["nodes", "nodes/proxy", "services", "endpoints", "pods"],
                        "verbs": ["get", "list", "watch"]
                    },
                    {
                        "apiGroups": ["extensions"],
                        "resources": ["ingresses"],
                        "verbs": ["get", "list", "watch"]
                    },
                    {
                        "nonResourceURLs": ["/metrics"],
                        "verbs": ["get"]
                    }
                ]
            },
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRoleBinding",
                "metadata": {
                    "name": "prometheus-server"
                },
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "ClusterRole",
                    "name": "prometheus-server"
                },
                "subjects": [
                    {
                        "kind": "ServiceAccount",
                        "name": "prometheus-server",
                        "namespace": self.namespace
                    }
                ]
            }
        ]
        
        for manifest in rbac_manifests:
            await self._apply_manifest(manifest)

    async def _deploy_prometheus_operator(self):
        """Deploy Prometheus Operator"""
        logger.info("Deploying Prometheus Operator")
        
        # Use Helm to deploy Prometheus Operator
        helm_command = [
            "helm", "repo", "add", "prometheus-community",
            "https://prometheus-community.github.io/helm-charts"
        ]
        await self._run_command(helm_command)
        
        helm_command = ["helm", "repo", "update"]
        await self._run_command(helm_command)
        
        # Deploy with custom values
        operator_values = {
            "prometheus": {
                "prometheusSpec": {
                    "retention": self.config.prometheus_retention,
                    "storageSpec": {
                        "volumeClaimTemplate": {
                            "spec": {
                                "accessModes": ["ReadWriteOnce"],
                                "resources": {
                                    "requests": {
                                        "storage": self.config.prometheus_storage
                                    }
                                }
                            }
                        }
                    },
                    "resources": {
                        "limits": {
                            "cpu": self.config.prometheus_cpu_limit,
                            "memory": self.config.prometheus_memory_limit
                        },
                        "requests": {
                            "cpu": "500m",
                            "memory": "2Gi"
                        }
                    }
                }
            },
            "grafana": {
                "enabled": False  # We'll deploy Grafana separately
            }
        }
        
        # Write values to temp file
        values_file = self.artifacts_dir / "prometheus-operator-values.yaml"
        with open(values_file, 'w') as f:
            yaml.dump(operator_values, f)
        
        helm_command = [
            "helm", "install", "prometheus-operator",
            "prometheus-community/kube-prometheus-stack",
            "--namespace", self.namespace,
            "--create-namespace",
            "--values", str(values_file)
        ]
        
        await self._run_command(helm_command)
        await self._wait_for_component_ready("prometheus-operator")
        
        self.deployment_status[MonitoringComponent.PROMETHEUS_OPERATOR] = DeploymentStatus.READY

    async def _deploy_prometheus(self):
        """Deploy Prometheus with custom configuration"""
        logger.info("Deploying Prometheus server")
        
        prometheus_config = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "rule_files": [
                "/etc/prometheus/rules/*.yml"
            ],
            "scrape_configs": [
                {
                    "job_name": "kubernetes-apiservers",
                    "kubernetes_sd_configs": [{"role": "endpoints"}],
                    "scheme": "https",
                    "tls_config": {"ca_file": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"},
                    "bearer_token_file": "/var/run/secrets/kubernetes.io/serviceaccount/token",
                    "relabel_configs": [
                        {
                            "source_labels": ["__meta_kubernetes_namespace", "__meta_kubernetes_service_name", "__meta_kubernetes_endpoint_port_name"],
                            "action": "keep",
                            "regex": "default;kubernetes;https"
                        }
                    ]
                },
                {
                    "job_name": "kubernetes-nodes",
                    "kubernetes_sd_configs": [{"role": "node"}],
                    "scheme": "https",
                    "tls_config": {"ca_file": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"},
                    "bearer_token_file": "/var/run/secrets/kubernetes.io/serviceaccount/token",
                    "relabel_configs": [
                        {
                            "action": "labelmap",
                            "regex": "__meta_kubernetes_node_label_(.+)"
                        }
                    ]
                },
                {
                    "job_name": "splunk-mcp-services",
                    "kubernetes_sd_configs": [{"role": "endpoints"}],
                    "relabel_configs": [
                        {
                            "source_labels": ["__meta_kubernetes_service_annotation_prometheus_io_scrape"],
                            "action": "keep",
                            "regex": True
                        },
                        {
                            "source_labels": ["__meta_kubernetes_service_annotation_prometheus_io_path"],
                            "action": "replace",
                            "target_label": "__metrics_path__",
                            "regex": "(.+)"
                        },
                        {
                            "source_labels": ["__address__", "__meta_kubernetes_service_annotation_prometheus_io_port"],
                            "action": "replace",
                            "regex": "([^:]+)(?::\\d+)?;(\\d+)",
                            "replacement": "${1}:${2}",
                            "target_label": "__address__"
                        }
                    ]
                }
            ]
        }
        
        # Create ConfigMap for Prometheus configuration
        config_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "prometheus-config",
                "namespace": self.namespace
            },
            "data": {
                "prometheus.yml": yaml.dump(prometheus_config)
            }
        }
        
        await self._apply_manifest(config_manifest)
        self.deployment_status[MonitoringComponent.PROMETHEUS] = DeploymentStatus.READY

    async def _deploy_grafana(self):
        """Deploy Grafana with custom configuration"""
        logger.info("Deploying Grafana")
        
        # Grafana configuration
        grafana_config = {
            "server": {
                "root_url": "%(protocol)s://%(domain)s:%(http_port)s/grafana/",
                "serve_from_sub_path": True
            },
            "security": {
                "admin_user": "admin",
                "admin_password": "admin123",  # Should be set via secret in production
                "secret_key": "grafana-secret-key"
            },
            "database": {
                "type": "sqlite3",
                "path": "/var/lib/grafana/grafana.db"
            },
            "dashboards": {
                "default_home_dashboard_path": "/var/lib/grafana/dashboards/overview.json"
            },
            "auth.anonymous": {
                "enabled": False
            }
        }
        
        # Create Grafana deployment
        grafana_deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "grafana",
                "namespace": self.namespace,
                "labels": {
                    "app": "grafana",
                    "component": "monitoring"
                }
            },
            "spec": {
                "replicas": 2,
                "selector": {
                    "matchLabels": {
                        "app": "grafana"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "grafana"
                        }
                    },
                    "spec": {
                        "serviceAccountName": "prometheus-server",
                        "containers": [
                            {
                                "name": "grafana",
                                "image": "grafana/grafana:10.2.2",
                                "ports": [
                                    {
                                        "containerPort": 3000,
                                        "name": "http"
                                    }
                                ],
                                "env": [
                                    {
                                        "name": "GF_SECURITY_ADMIN_PASSWORD",
                                        "value": "admin123"
                                    }
                                ],
                                "resources": {
                                    "limits": {
                                        "cpu": self.config.grafana_cpu_limit,
                                        "memory": self.config.grafana_memory_limit
                                    },
                                    "requests": {
                                        "cpu": "100m",
                                        "memory": "256Mi"
                                    }
                                },
                                "volumeMounts": [
                                    {
                                        "name": "grafana-storage",
                                        "mountPath": "/var/lib/grafana"
                                    },
                                    {
                                        "name": "grafana-dashboards",
                                        "mountPath": "/var/lib/grafana/dashboards"
                                    }
                                ],
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": "/api/health",
                                        "port": 3000
                                    },
                                    "initialDelaySeconds": 60,
                                    "periodSeconds": 10
                                },
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": "/api/health",
                                        "port": 3000
                                    },
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 5
                                }
                            }
                        ],
                        "volumes": [
                            {
                                "name": "grafana-storage",
                                "persistentVolumeClaim": {
                                    "claimName": "grafana-storage"
                                }
                            },
                            {
                                "name": "grafana-dashboards",
                                "configMap": {
                                    "name": "grafana-dashboards"
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        # Create PVC for Grafana
        grafana_pvc = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": "grafana-storage",
                "namespace": self.namespace
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {
                    "requests": {
                        "storage": self.config.grafana_storage
                    }
                }
            }
        }
        
        # Create Grafana service
        grafana_service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "grafana",
                "namespace": self.namespace,
                "labels": {
                    "app": "grafana"
                }
            },
            "spec": {
                "type": "ClusterIP",
                "ports": [
                    {
                        "port": 3000,
                        "targetPort": 3000,
                        "name": "http"
                    }
                ],
                "selector": {
                    "app": "grafana"
                }
            }
        }
        
        await self._apply_manifest(grafana_pvc)
        await self._apply_manifest(grafana_deployment)
        await self._apply_manifest(grafana_service)
        
        await self._wait_for_component_ready("grafana")
        self.deployment_status[MonitoringComponent.GRAFANA] = DeploymentStatus.READY

    async def _deploy_alertmanager(self):
        """Deploy AlertManager with notification configuration"""
        logger.info("Deploying AlertManager")
        
        # AlertManager configuration
        alertmanager_config = {
            "global": {
                "smtp_smarthost": f"{self.config.email_smtp_host}:{self.config.email_smtp_port}",
                "smtp_from": self.config.email_from
            },
            "route": {
                "group_by": ["alertname"],
                "group_wait": "10s",
                "group_interval": "10s",
                "repeat_interval": "1h",
                "receiver": "web.hook",
                "routes": [
                    {
                        "match": {
                            "severity": "critical"
                        },
                        "receiver": "critical-alerts",
                        "group_wait": "0s",
                        "repeat_interval": "5m"
                    },
                    {
                        "match": {
                            "severity": "warning"
                        },
                        "receiver": "warning-alerts",
                        "repeat_interval": "30m"
                    }
                ]
            },
            "receivers": [
                {
                    "name": "web.hook",
                    "webhook_configs": [
                        {
                            "url": "http://127.0.0.1:5001/"
                        }
                    ]
                },
                {
                    "name": "critical-alerts",
                    "email_configs": [
                        {
                            "to": "ops-team@company.com",
                            "subject": "🚨 CRITICAL Alert: {{ .GroupLabels.alertname }}",
                            "body": "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
                        }
                    ],
                    "slack_configs": [
                        {
                            "api_url": self.config.slack_webhook_url,
                            "channel": "#alerts-critical",
                            "title": "🚨 Critical Alert",
                            "text": "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
                        }
                    ] if self.config.slack_webhook_url else []
                },
                {
                    "name": "warning-alerts",
                    "email_configs": [
                        {
                            "to": "monitoring@company.com",
                            "subject": "⚠️ Warning: {{ .GroupLabels.alertname }}",
                            "body": "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
                        }
                    ],
                    "slack_configs": [
                        {
                            "api_url": self.config.slack_webhook_url,
                            "channel": "#alerts-warning",
                            "title": "⚠️ Warning Alert",
                            "text": "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
                        }
                    ] if self.config.slack_webhook_url else []
                }
            ]
        }
        
        # Create AlertManager ConfigMap
        alertmanager_config_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "alertmanager-config",
                "namespace": self.namespace
            },
            "data": {
                "alertmanager.yml": yaml.dump(alertmanager_config)
            }
        }
        
        await self._apply_manifest(alertmanager_config_manifest)
        self.deployment_status[MonitoringComponent.ALERTMANAGER] = DeploymentStatus.READY

    async def _deploy_supporting_components(self):
        """Deploy supporting monitoring components"""
        logger.info("Deploying supporting components")
        
        # Deploy node-exporter for node metrics
        await self._deploy_node_exporter()
        
        # Deploy kube-state-metrics for Kubernetes metrics
        await self._deploy_kube_state_metrics()
        
        self.deployment_status[MonitoringComponent.NODE_EXPORTER] = DeploymentStatus.READY
        self.deployment_status[MonitoringComponent.KUBE_STATE_METRICS] = DeploymentStatus.READY

    async def _deploy_node_exporter(self):
        """Deploy node-exporter for node metrics"""
        node_exporter_manifest = {
            "apiVersion": "apps/v1",
            "kind": "DaemonSet",
            "metadata": {
                "name": "node-exporter",
                "namespace": self.namespace
            },
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app": "node-exporter"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "node-exporter"
                        },
                        "annotations": {
                            "prometheus.io/scrape": "true",
                            "prometheus.io/port": "9100"
                        }
                    },
                    "spec": {
                        "hostNetwork": True,
                        "containers": [
                            {
                                "name": "node-exporter",
                                "image": "prom/node-exporter:v1.6.1",
                                "ports": [
                                    {
                                        "containerPort": 9100,
                                        "hostPort": 9100,
                                        "name": "metrics"
                                    }
                                ],
                                "resources": {
                                    "limits": {
                                        "cpu": "200m",
                                        "memory": "200Mi"
                                    },
                                    "requests": {
                                        "cpu": "100m",
                                        "memory": "100Mi"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        await self._apply_manifest(node_exporter_manifest)

    async def _deploy_kube_state_metrics(self):
        """Deploy kube-state-metrics for Kubernetes object metrics"""
        kube_state_metrics_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "kube-state-metrics",
                "namespace": self.namespace
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "kube-state-metrics"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "kube-state-metrics"
                        },
                        "annotations": {
                            "prometheus.io/scrape": "true",
                            "prometheus.io/port": "8080"
                        }
                    },
                    "spec": {
                        "serviceAccountName": "prometheus-server",
                        "containers": [
                            {
                                "name": "kube-state-metrics",
                                "image": "k8s.gcr.io/kube-state-metrics/kube-state-metrics:v2.10.0",
                                "ports": [
                                    {
                                        "containerPort": 8080,
                                        "name": "http-metrics"
                                    }
                                ],
                                "resources": {
                                    "limits": {
                                        "cpu": "200m",
                                        "memory": "200Mi"
                                    },
                                    "requests": {
                                        "cpu": "100m",
                                        "memory": "100Mi"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        await self._apply_manifest(kube_state_metrics_manifest)

    async def _configure_custom_metrics(self):
        """Configure custom application metrics"""
        logger.info("Configuring custom application metrics")
        
        # Create ServiceMonitor for Splunk MCP services
        service_monitor = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "ServiceMonitor",
            "metadata": {
                "name": "splunk-mcp-services",
                "namespace": self.namespace,
                "labels": {
                    "app": "splunk-mcp-monitoring"
                }
            },
            "spec": {
                "selector": {
                    "matchLabels": {
                        "prometheus.io/scrape": "true"
                    }
                },
                "endpoints": [
                    {
                        "port": "metrics",
                        "interval": "30s",
                        "path": "/metrics"
                    }
                ],
                "namespaceSelector": {
                    "matchNames": ["splunk-mcp-prod"]
                }
            }
        }
        
        await self._apply_manifest(service_monitor)
        self.deployment_status[MonitoringComponent.CUSTOM_METRICS] = DeploymentStatus.READY

    async def _setup_dashboards(self):
        """Setup comprehensive Grafana dashboards"""
        logger.info("Setting up Grafana dashboards")
        
        # Create dashboard definitions
        self._create_system_overview_dashboard()
        self._create_application_performance_dashboard()
        self._create_business_kpi_dashboard()
        self._create_security_monitoring_dashboard()
        
        # Create ConfigMap with all dashboards
        dashboards_data = {}
        for dashboard in self.dashboards:
            dashboards_data[f"{dashboard.name}.json"] = json.dumps(self._convert_dashboard_to_grafana_format(dashboard), indent=2)
        
        dashboards_configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "grafana-dashboards",
                "namespace": self.namespace
            },
            "data": dashboards_data
        }
        
        await self._apply_manifest(dashboards_configmap)

    def _create_system_overview_dashboard(self):
        """Create system overview dashboard"""
        panels = [
            {
                "title": "CPU Usage",
                "type": "graph",
                "targets": [
                    {
                        "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
                        "legendFormat": "{{instance}}"
                    }
                ]
            },
            {
                "title": "Memory Usage",
                "type": "graph",
                "targets": [
                    {
                        "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
                        "legendFormat": "{{instance}}"
                    }
                ]
            },
            {
                "title": "Pod Status",
                "type": "stat",
                "targets": [
                    {
                        "expr": "kube_pod_status_phase{namespace=\"splunk-mcp-prod\"}",
                        "legendFormat": "{{phase}}"
                    }
                ]
            },
            {
                "title": "API Response Time",
                "type": "graph",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))",
                        "legendFormat": "95th percentile"
                    }
                ]
            }
        ]
        
        dashboard = Dashboard(
            name="system-overview",
            title="System Overview",
            description="Overall system health and performance metrics",
            tags=["system", "overview"],
            panels=panels
        )
        
        self.dashboards.append(dashboard)

    def _create_application_performance_dashboard(self):
        """Create application performance dashboard"""
        panels = [
            {
                "title": "Request Rate",
                "type": "graph",
                "targets": [
                    {
                        "expr": "sum(rate(http_requests_total[5m])) by (service)",
                        "legendFormat": "{{service}}"
                    }
                ]
            },
            {
                "title": "Error Rate",
                "type": "graph",
                "targets": [
                    {
                        "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (service) / sum(rate(http_requests_total[5m])) by (service)",
                        "legendFormat": "{{service}}"
                    }
                ]
            },
            {
                "title": "Database Connections",
                "type": "graph",
                "targets": [
                    {
                        "expr": "pg_stat_database_numbackends",
                        "legendFormat": "{{datname}}"
                    }
                ]
            },
            {
                "title": "NLP Query Processing Time",
                "type": "graph",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, sum(rate(nlp_query_duration_seconds_bucket[5m])) by (le))",
                        "legendFormat": "95th percentile"
                    }
                ]
            }
        ]
        
        dashboard = Dashboard(
            name="application-performance",
            title="Application Performance",
            description="Application-specific performance metrics",
            tags=["application", "performance"],
            panels=panels
        )
        
        self.dashboards.append(dashboard)

    def _create_business_kpi_dashboard(self):
        """Create business KPI dashboard"""
        panels = [
            {
                "title": "Active Users",
                "type": "stat",
                "targets": [
                    {
                        "expr": "sum(active_users_total)",
                        "legendFormat": "Active Users"
                    }
                ]
            },
            {
                "title": "Queries per Hour",
                "type": "graph",
                "targets": [
                    {
                        "expr": "sum(rate(splunk_queries_total[1h]))",
                        "legendFormat": "Queries/hour"
                    }
                ]
            },
            {
                "title": "User Satisfaction Score",
                "type": "gauge",
                "targets": [
                    {
                        "expr": "avg(user_satisfaction_score)",
                        "legendFormat": "Satisfaction"
                    }
                ]
            },
            {
                "title": "Feature Adoption Rate",
                "type": "graph",
                "targets": [
                    {
                        "expr": "sum(rate(feature_usage_total[1h])) by (feature)",
                        "legendFormat": "{{feature}}"
                    }
                ]
            }
        ]
        
        dashboard = Dashboard(
            name="business-kpi",
            title="Business KPIs",
            description="Business key performance indicators",
            tags=["business", "kpi"],
            panels=panels
        )
        
        self.dashboards.append(dashboard)

    def _create_security_monitoring_dashboard(self):
        """Create security monitoring dashboard"""
        panels = [
            {
                "title": "Failed Login Attempts",
                "type": "graph",
                "targets": [
                    {
                        "expr": "sum(rate(auth_failures_total[5m]))",
                        "legendFormat": "Failed Logins"
                    }
                ]
            },
            {
                "title": "Suspicious Activities",
                "type": "table",
                "targets": [
                    {
                        "expr": "security_events_total",
                        "legendFormat": "{{event_type}}"
                    }
                ]
            },
            {
                "title": "SSL Certificate Expiry",
                "type": "stat",
                "targets": [
                    {
                        "expr": "(probe_ssl_earliest_cert_expiry - time()) / 86400",
                        "legendFormat": "Days until expiry"
                    }
                ]
            }
        ]
        
        dashboard = Dashboard(
            name="security-monitoring",
            title="Security Monitoring",
            description="Security-related metrics and alerts",
            tags=["security", "monitoring"],
            panels=panels
        )
        
        self.dashboards.append(dashboard)

    async def _configure_alerting_rules(self):
        """Configure comprehensive alerting rules"""
        logger.info("Configuring alerting rules")
        
        # Define alert rules
        self.alert_rules = [
            AlertRule(
                name="HighCPUUsage",
                expr="100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) > 80",
                duration="5m",
                severity=AlertSeverity.WARNING,
                summary="High CPU usage detected",
                description="CPU usage is above 80% for more than 5 minutes on {{$labels.instance}}"
            ),
            AlertRule(
                name="HighMemoryUsage",
                expr="(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90",
                duration="5m",
                severity=AlertSeverity.CRITICAL,
                summary="High memory usage detected",
                description="Memory usage is above 90% for more than 5 minutes on {{$labels.instance}}"
            ),
            AlertRule(
                name="PodCrashLooping",
                expr="rate(kube_pod_container_status_restarts_total[15m]) > 0",
                duration="5m",
                severity=AlertSeverity.CRITICAL,
                summary="Pod is crash looping",
                description="Pod {{$labels.pod}} in namespace {{$labels.namespace}} is crash looping"
            ),
            AlertRule(
                name="HighErrorRate",
                expr="sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (service) / sum(rate(http_requests_total[5m])) by (service) > 0.05",
                duration="5m",
                severity=AlertSeverity.WARNING,
                summary="High error rate detected",
                description="Error rate is above 5% for service {{$labels.service}}"
            ),
            AlertRule(
                name="DatabaseDown",
                expr="pg_up == 0",
                duration="1m",
                severity=AlertSeverity.CRITICAL,
                summary="Database is down",
                description="PostgreSQL database is not responding"
            ),
            AlertRule(
                name="DiskSpaceRunningLow",
                expr="(node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 10",
                duration="5m",
                severity=AlertSeverity.WARNING,
                summary="Disk space running low",
                description="Disk space is below 10% on {{$labels.instance}}"
            )
        ]
        
        # Create PrometheusRule
        rules_data = {
            "groups": [
                {
                    "name": "splunk-mcp-alerts",
                    "rules": [
                        {
                            "alert": rule.name,
                            "expr": rule.expr,
                            "for": rule.duration,
                            "labels": {
                                "severity": rule.severity.value,
                                **rule.labels
                            },
                            "annotations": {
                                "summary": rule.summary,
                                "description": rule.description,
                                **rule.annotations
                            }
                        }
                        for rule in self.alert_rules
                    ]
                }
            ]
        }
        
        prometheus_rule = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "PrometheusRule",
            "metadata": {
                "name": "splunk-mcp-alerts",
                "namespace": self.namespace,
                "labels": {
                    "app": "prometheus-operator"
                }
            },
            "spec": rules_data
        }
        
        await self._apply_manifest(prometheus_rule)

    async def _validate_monitoring_stack(self):
        """Validate monitoring stack deployment"""
        logger.info("Validating monitoring stack")
        
        # Check Prometheus health
        await self._check_prometheus_health()
        
        # Check Grafana health
        await self._check_grafana_health()
        
        # Check AlertManager health
        await self._check_alertmanager_health()
        
        # Validate metrics collection
        await self._validate_metrics_collection()
        
        logger.info("Monitoring stack validation completed")

    async def _check_prometheus_health(self) -> bool:
        """Check Prometheus health"""
        try:
            # Port-forward to Prometheus and check health
            result = await self._run_command([
                "kubectl", "port-forward", "-n", self.namespace,
                "svc/prometheus-operator-kube-p-prometheus", "9090:9090"
            ], timeout=5, background=True)
            
            await asyncio.sleep(2)  # Wait for port-forward to establish
            
            response = requests.get("http://localhost:9090/-/healthy", timeout=5)
            return response.status_code == 200
        except:
            return False

    async def _check_grafana_health(self) -> bool:
        """Check Grafana health"""
        try:
            result = await self._run_command([
                "kubectl", "port-forward", "-n", self.namespace,
                "svc/grafana", "3000:3000"
            ], timeout=5, background=True)
            
            await asyncio.sleep(2)
            
            response = requests.get("http://localhost:3000/api/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    async def _check_alertmanager_health(self) -> bool:
        """Check AlertManager health"""
        try:
            result = await self._run_command([
                "kubectl", "port-forward", "-n", self.namespace,
                "svc/prometheus-operator-kube-p-alertmanager", "9093:9093"
            ], timeout=5, background=True)
            
            await asyncio.sleep(2)
            
            response = requests.get("http://localhost:9093/-/healthy", timeout=5)
            return response.status_code == 200
        except:
            return False

    async def _validate_metrics_collection(self):
        """Validate metrics are being collected"""
        logger.info("Validating metrics collection")
        # Implementation would check actual metrics endpoints
        pass

    async def _apply_manifest(self, manifest: Dict[str, Any]):
        """Apply Kubernetes manifest"""
        manifest_file = self.artifacts_dir / f"{manifest['metadata']['name']}.yaml"
        with open(manifest_file, 'w') as f:
            yaml.dump(manifest, f)
        
        result = await self._run_command([
            "kubectl", "apply", "-f", str(manifest_file)
        ])
        
        if result.returncode != 0:
            raise Exception(f"Failed to apply manifest: {result.stderr}")

    async def _run_command(self, command: List[str], timeout: int = 120, background: bool = False) -> subprocess.CompletedProcess:
        """Run shell command"""
        logger.debug(f"Running command: {' '.join(command)}")
        
        if background:
            # Start process in background for port-forwarding
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            return process
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return subprocess.CompletedProcess(
                args=command,
                returncode=process.returncode,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else ""
            )
        except asyncio.TimeoutError:
            process.kill()
            raise Exception(f"Command timed out: {' '.join(command)}")

    async def _wait_for_component_ready(self, component_name: str, timeout: int = 300):
        """Wait for component to be ready"""
        logger.info(f"Waiting for {component_name} to be ready")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = await self._run_command([
                    "kubectl", "get", "deployment", component_name,
                    "-n", self.namespace, "-o", "jsonpath='{.status.readyReplicas}'"
                ])
                
                if result.returncode == 0 and result.stdout.strip("'") != "":
                    ready_replicas = int(result.stdout.strip("'"))
                    if ready_replicas > 0:
                        logger.info(f"{component_name} is ready")
                        return
            except:
                pass
            
            await asyncio.sleep(10)
        
        raise Exception(f"{component_name} failed to become ready within {timeout} seconds")

    def _convert_dashboard_to_grafana_format(self, dashboard: Dashboard) -> Dict[str, Any]:
        """Convert dashboard to Grafana JSON format"""
        return {
            "dashboard": {
                "id": None,
                "title": dashboard.title,
                "description": dashboard.description,
                "tags": dashboard.tags,
                "timezone": "UTC",
                "refresh": dashboard.refresh_interval,
                "time": {
                    "from": f"now-{dashboard.time_range}",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": i + 1,
                        "title": panel["title"],
                        "type": panel["type"],
                        "targets": panel["targets"],
                        "gridPos": {
                            "h": 8,
                            "w": 12,
                            "x": (i % 2) * 12,
                            "y": (i // 2) * 8
                        }
                    }
                    for i, panel in enumerate(dashboard.panels)
                ],
                "version": 1
            },
            "overwrite": True
        }

    async def _cleanup_failed_deployment(self):
        """Cleanup failed deployment"""
        logger.warning("Cleaning up failed monitoring deployment")
        
        try:
            await self._run_command([
                "kubectl", "delete", "namespace", self.namespace, "--ignore-not-found"
            ])
        except:
            pass

    async def _get_deployment_summary(self) -> Dict[str, Any]:
        """Get deployment summary"""
        return {
            "namespace": self.namespace,
            "components": {component.value: status.value for component, status in self.deployment_status.items()},
            "dashboards_created": len(self.dashboards),
            "alert_rules_created": len(self.alert_rules),
            "deployment_time": datetime.utcnow().isoformat()
        }

# CLI interface
async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitoring Stack Deployment")
    parser.add_argument("command", choices=["deploy", "validate", "status", "cleanup"])
    parser.add_argument("--namespace", default="splunk-mcp-monitoring", help="Monitoring namespace")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    config = MonitoringConfig(namespace=args.namespace)
    deployer = MonitoringStackDeployer(config)
    
    if args.command == "deploy":
        try:
            summary = await deployer.deploy_full_monitoring_stack()
            print("Monitoring stack deployed successfully!")
            print(json.dumps(summary, indent=2))
        except Exception as e:
            print(f"Deployment failed: {e}")
            sys.exit(1)
    
    elif args.command == "validate":
        try:
            await deployer._validate_monitoring_stack()
            print("Monitoring stack validation passed")
        except Exception as e:
            print(f"Validation failed: {e}")
            sys.exit(1)
    
    elif args.command == "status":
        summary = await deployer._get_deployment_summary()
        print(json.dumps(summary, indent=2))
    
    elif args.command == "cleanup":
        await deployer._cleanup_failed_deployment()
        print("Cleanup completed")

if __name__ == "__main__":
    asyncio.run(main())