#!/usr/bin/env python3
"""
Operational Automation System
============================
Advanced operational automation for intelligent monitoring, incident response, 
and operational efficiency optimization
"""

import asyncio
import json
import logging
import aiohttp
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import kubernetes
from kubernetes import client, config
import redis
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"

class AutomationAction(Enum):
    """Available automation actions"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    ROTATE_LOGS = "rotate_logs"
    BACKUP_DATA = "backup_data"
    SEND_NOTIFICATION = "send_notification"
    CREATE_INCIDENT = "create_incident"
    GATHER_DIAGNOSTICS = "gather_diagnostics"
    OPTIMIZE_RESOURCES = "optimize_resources"

@dataclass
class OperationalMetric:
    """Operational metric data structure"""
    name: str
    value: float
    timestamp: datetime
    service: str
    labels: Dict[str, str] = field(default_factory=dict)
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

@dataclass
class AutomationRule:
    """Automation rule configuration"""
    name: str
    condition: str
    action: AutomationAction
    parameters: Dict[str, Any] = field(default_factory=dict)
    cooldown_seconds: int = 300
    enabled: bool = True
    severity: AlertSeverity = AlertSeverity.INFO

@dataclass
class IncidentContext:
    """Incident context for automated response"""
    incident_id: str
    severity: AlertSeverity
    service: str
    description: str
    metrics: List[OperationalMetric]
    timestamp: datetime
    automated_actions: List[str] = field(default_factory=list)
    escalation_level: int = 0

class OperationalAutomation:
    """Main operational automation system"""
    
    def __init__(self, config_path: str = "operational-dashboard-config.json"):
        self.config = self._load_config(config_path)
        self.redis_client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        self.k8s_client = self._setup_kubernetes()
        self.automation_rules: List[AutomationRule] = []
        self.active_incidents: Dict[str, IncidentContext] = {}
        self.metrics_history: List[OperationalMetric] = []
        self._setup_automation_rules()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load operational configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _setup_kubernetes(self):
        """Setup Kubernetes client"""
        try:
            config.load_incluster_config()  # For running in cluster
        except:
            try:
                config.load_kube_config()  # For local development
            except:
                logger.warning("Could not load Kubernetes config")
                return None
        
        return client.AppsV1Api()
    
    def _setup_automation_rules(self):
        """Setup automation rules from configuration"""
        automation_config = self.config.get("automation_workflows", {})
        
        # Auto-scaling rules
        auto_scaling = automation_config.get("auto_scaling", {})
        if auto_scaling.get("enabled", False):
            for trigger in auto_scaling.get("triggers", []):
                rule = AutomationRule(
                    name=f"auto_scaling_{trigger['action']}",
                    condition=trigger["metric"],
                    action=AutomationAction(trigger["action"]),
                    cooldown_seconds=self._parse_duration(trigger.get("cooldown", "300s"))
                )
                self.automation_rules.append(rule)
        
        # Incident response rules
        incident_response = automation_config.get("incident_response", {})
        if incident_response.get("enabled", False):
            for escalation in incident_response.get("escalation_matrix", []):
                for action_name in escalation.get("immediate_actions", []):
                    try:
                        action = AutomationAction(action_name)
                        rule = AutomationRule(
                            name=f"incident_{escalation['severity']}_{action_name}",
                            condition=f"severity == '{escalation['severity']}'",
                            action=action,
                            severity=AlertSeverity(escalation["severity"])
                        )
                        self.automation_rules.append(rule)
                    except ValueError:
                        logger.warning(f"Unknown action: {action_name}")
        
        logger.info(f"Loaded {len(self.automation_rules)} automation rules")
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string to seconds"""
        if duration_str.endswith('s'):
            return int(duration_str[:-1])
        elif duration_str.endswith('m'):
            return int(duration_str[:-1]) * 60
        elif duration_str.endswith('h'):
            return int(duration_str[:-1]) * 3600
        else:
            return int(duration_str)
    
    async def collect_metrics(self) -> List[OperationalMetric]:
        """Collect operational metrics from various sources"""
        metrics = []
        
        try:
            # Collect Prometheus metrics
            prometheus_metrics = await self._collect_prometheus_metrics()
            metrics.extend(prometheus_metrics)
            
            # Collect Kubernetes metrics
            k8s_metrics = await self._collect_kubernetes_metrics()
            metrics.extend(k8s_metrics)
            
            # Collect application metrics
            app_metrics = await self._collect_application_metrics()
            metrics.extend(app_metrics)
            
            # Store metrics history
            self.metrics_history.extend(metrics)
            
            # Keep only last 1000 metrics
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    async def _collect_prometheus_metrics(self) -> List[OperationalMetric]:
        """Collect metrics from Prometheus"""
        metrics = []
        prometheus_url = "http://prometheus:9090"
        
        # Define key operational queries
        queries = [
            {
                "query": "up{job=~\"splunk-mcp-.*\"}",
                "name": "service_availability"
            },
            {
                "query": "rate(http_requests_total[5m])",
                "name": "request_rate"
            },
            {
                "query": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                "name": "response_time_95th"
            },
            {
                "query": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
                "name": "error_rate"
            },
            {
                "query": "avg(rate(container_cpu_usage_seconds_total{namespace=\"splunk-mcp-prod\"}[5m]))",
                "name": "cpu_usage"
            },
            {
                "query": "avg(container_memory_usage_bytes{namespace=\"splunk-mcp-prod\"}) / avg(container_spec_memory_limit_bytes{namespace=\"splunk-mcp-prod\"})",
                "name": "memory_utilization"
            }
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                for query_config in queries:
                    url = f"{prometheus_url}/api/v1/query"
                    params = {"query": query_config["query"]}
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for result in data.get("data", {}).get("result", []):
                                metric = OperationalMetric(
                                    name=query_config["name"],
                                    value=float(result["value"][1]),
                                    timestamp=datetime.utcnow(),
                                    service=result.get("metric", {}).get("job", "unknown"),
                                    labels=result.get("metric", {})
                                )
                                metrics.append(metric)
        
        except Exception as e:
            logger.error(f"Error collecting Prometheus metrics: {e}")
        
        return metrics
    
    async def _collect_kubernetes_metrics(self) -> List[OperationalMetric]:
        """Collect metrics from Kubernetes"""
        metrics = []
        
        if not self.k8s_client:
            return metrics
        
        try:
            # Get deployment status
            deployments = self.k8s_client.list_namespaced_deployment(namespace="splunk-mcp-prod")
            
            for deployment in deployments.items:
                # Deployment readiness
                ready_replicas = deployment.status.ready_replicas or 0
                desired_replicas = deployment.spec.replicas or 0
                readiness_ratio = ready_replicas / desired_replicas if desired_replicas > 0 else 0
                
                metric = OperationalMetric(
                    name="deployment_readiness",
                    value=readiness_ratio,
                    timestamp=datetime.utcnow(),
                    service=deployment.metadata.name,
                    labels={"namespace": deployment.metadata.namespace},
                    threshold_warning=0.8,
                    threshold_critical=0.5
                )
                metrics.append(metric)
                
                # Pod restart count
                restart_count = 0
                if deployment.status.conditions:
                    for condition in deployment.status.conditions:
                        if condition.type == "Progressing" and condition.reason == "NewReplicaSetAvailable":
                            restart_count = getattr(condition, 'observedGeneration', 0) - 1
                
                metric = OperationalMetric(
                    name="pod_restarts",
                    value=restart_count,
                    timestamp=datetime.utcnow(),
                    service=deployment.metadata.name,
                    labels={"namespace": deployment.metadata.namespace},
                    threshold_warning=5,
                    threshold_critical=10
                )
                metrics.append(metric)
        
        except Exception as e:
            logger.error(f"Error collecting Kubernetes metrics: {e}")
        
        return metrics
    
    async def _collect_application_metrics(self) -> List[OperationalMetric]:
        """Collect application-specific metrics"""
        metrics = []
        
        # Simulate application metrics collection
        # In practice, this would connect to application APIs or databases
        app_services = [
            "api-gateway", "nlp-engine", "visualization", "alert-manager",
            "user-adoption-service"
        ]
        
        for service in app_services:
            try:
                # Simulate health check
                health_url = f"http://{service}:8000/health"
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(health_url, timeout=5) as response:
                            health_status = 1.0 if response.status == 200 else 0.0
                    except:
                        health_status = 0.0
                
                metric = OperationalMetric(
                    name="health_check",
                    value=health_status,
                    timestamp=datetime.utcnow(),
                    service=service,
                    threshold_critical=0.5
                )
                metrics.append(metric)
                
            except Exception as e:
                logger.debug(f"Could not collect metrics for {service}: {e}")
        
        return metrics
    
    async def evaluate_automation_rules(self, metrics: List[OperationalMetric]) -> List[Tuple[AutomationRule, OperationalMetric]]:
        """Evaluate automation rules against current metrics"""
        triggered_rules = []
        
        for rule in self.automation_rules:
            if not rule.enabled:
                continue
            
            # Check cooldown
            cooldown_key = f"automation_cooldown:{rule.name}"
            if self.redis_client.exists(cooldown_key):
                continue
            
            for metric in metrics:
                if self._evaluate_rule_condition(rule, metric):
                    triggered_rules.append((rule, metric))
                    
                    # Set cooldown
                    self.redis_client.setex(cooldown_key, rule.cooldown_seconds, "1")
                    break
        
        return triggered_rules
    
    def _evaluate_rule_condition(self, rule: AutomationRule, metric: OperationalMetric) -> bool:
        """Evaluate if a rule condition is met"""
        try:
            # Simple condition evaluation
            condition = rule.condition
            
            # Replace metric placeholders
            condition = condition.replace("cpu_usage", str(metric.value if metric.name == "cpu_usage" else 0))
            condition = condition.replace("memory_utilization", str(metric.value if metric.name == "memory_utilization" else 0))
            condition = condition.replace("error_rate", str(metric.value if metric.name == "error_rate" else 0))
            condition = condition.replace("response_time", str(metric.value if metric.name == "response_time_95th" else 0))
            
            # For severity-based conditions
            if "severity ==" in condition:
                return True  # Would be evaluated based on incident context
            
            # Evaluate numeric conditions
            try:
                return eval(condition)
            except:
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating rule condition: {e}")
            return False
    
    async def execute_automation_action(self, rule: AutomationRule, metric: OperationalMetric, context: Optional[IncidentContext] = None):
        """Execute automation action"""
        try:
            action_result = None
            
            if rule.action == AutomationAction.SCALE_UP:
                action_result = await self._scale_service(metric.service, "up", rule.parameters)
                
            elif rule.action == AutomationAction.SCALE_DOWN:
                action_result = await self._scale_service(metric.service, "down", rule.parameters)
                
            elif rule.action == AutomationAction.RESTART_SERVICE:
                action_result = await self._restart_service(metric.service)
                
            elif rule.action == AutomationAction.CLEAR_CACHE:
                action_result = await self._clear_cache(metric.service)
                
            elif rule.action == AutomationAction.SEND_NOTIFICATION:
                action_result = await self._send_notification(rule, metric, context)
                
            elif rule.action == AutomationAction.CREATE_INCIDENT:
                action_result = await self._create_incident(metric, rule.severity)
                
            elif rule.action == AutomationAction.GATHER_DIAGNOSTICS:
                action_result = await self._gather_diagnostics(metric.service)
                
            elif rule.action == AutomationAction.OPTIMIZE_RESOURCES:
                action_result = await self._optimize_resources(metric.service)
            
            # Log action execution
            logger.info(f"Executed action {rule.action} for rule {rule.name}: {action_result}")
            
            # Update incident context if provided
            if context:
                context.automated_actions.append(f"{rule.action}: {action_result}")
            
            return action_result
            
        except Exception as e:
            logger.error(f"Error executing action {rule.action}: {e}")
            return f"Error: {e}"
    
    async def _scale_service(self, service: str, direction: str, parameters: Dict[str, Any]) -> str:
        """Scale service up or down"""
        if not self.k8s_client:
            return "Kubernetes client not available"
        
        try:
            # Get current deployment
            deployment = self.k8s_client.read_namespaced_deployment(
                name=service, 
                namespace="splunk-mcp-prod"
            )
            
            current_replicas = deployment.spec.replicas
            max_replicas = parameters.get("max_replicas", 10)
            min_replicas = parameters.get("min_replicas", 1)
            scale_factor = parameters.get("scale_factor", 1)
            
            if direction == "up":
                new_replicas = min(current_replicas + scale_factor, max_replicas)
            else:
                new_replicas = max(current_replicas - scale_factor, min_replicas)
            
            if new_replicas != current_replicas:
                # Update deployment
                deployment.spec.replicas = new_replicas
                self.k8s_client.patch_namespaced_deployment(
                    name=service,
                    namespace="splunk-mcp-prod",
                    body=deployment
                )
                
                return f"Scaled {service} from {current_replicas} to {new_replicas} replicas"
            else:
                return f"No scaling needed for {service} (already at limits)"
                
        except Exception as e:
            return f"Failed to scale {service}: {e}"
    
    async def _restart_service(self, service: str) -> str:
        """Restart service by updating deployment"""
        if not self.k8s_client:
            return "Kubernetes client not available"
        
        try:
            # Add restart annotation to trigger rolling restart
            body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": datetime.utcnow().isoformat()
                            }
                        }
                    }
                }
            }
            
            self.k8s_client.patch_namespaced_deployment(
                name=service,
                namespace="splunk-mcp-prod",
                body=body
            )
            
            return f"Initiated rolling restart for {service}"
            
        except Exception as e:
            return f"Failed to restart {service}: {e}"
    
    async def _clear_cache(self, service: str) -> str:
        """Clear cache for service"""
        try:
            # Clear Redis cache
            pattern = f"{service}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                return f"Cleared {len(keys)} cache entries for {service}"
            else:
                return f"No cache entries found for {service}"
                
        except Exception as e:
            return f"Failed to clear cache for {service}: {e}"
    
    async def _send_notification(self, rule: AutomationRule, metric: OperationalMetric, context: Optional[IncidentContext]) -> str:
        """Send notification"""
        try:
            alerting_config = self.config.get("alerting_config", {})
            channels = alerting_config.get("notification_channels", [])
            
            # Determine notification channel based on severity
            channel_name = "operations_team"  # default
            if rule.severity == AlertSeverity.CRITICAL:
                channel_name = "executive_team"
            
            # Find channel config
            channel_config = None
            for channel in channels:
                if channel["name"] == channel_name:
                    channel_config = channel
                    break
            
            if not channel_config:
                return f"No notification channel configured for {channel_name}"
            
            # Prepare message
            message = self._format_notification_message(rule, metric, context)
            
            if channel_config["type"] == "slack":
                return await self._send_slack_notification(channel_config, message)
            elif channel_config["type"] == "email":
                return await self._send_email_notification(channel_config, message)
            else:
                return f"Unknown notification type: {channel_config['type']}"
                
        except Exception as e:
            return f"Failed to send notification: {e}"
    
    def _format_notification_message(self, rule: AutomationRule, metric: OperationalMetric, context: Optional[IncidentContext]) -> str:
        """Format notification message"""
        severity_emoji = {
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.SUCCESS: "✅"
        }
        
        emoji = severity_emoji.get(rule.severity, "ℹ️")
        
        message = f"{emoji} **Operational Alert: {rule.name}**\n\n"
        message += f"**Service**: {metric.service}\n"
        message += f"**Metric**: {metric.name} = {metric.value}\n"
        message += f"**Severity**: {rule.severity.value.upper()}\n"
        message += f"**Time**: {metric.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if context:
            message += f"**Incident ID**: {context.incident_id}\n"
            if context.automated_actions:
                message += f"**Automated Actions**: {', '.join(context.automated_actions)}\n"
        
        message += f"\n**Rule**: {rule.condition}"
        
        return message
    
    async def _send_slack_notification(self, channel_config: Dict[str, Any], message: str) -> str:
        """Send Slack notification"""
        try:
            webhook_url = channel_config["webhook_url"]
            payload = {
                "channel": channel_config["channel"],
                "text": message,
                "username": "Operational Automation",
                "icon_emoji": ":robot_face:"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        return "Slack notification sent successfully"
                    else:
                        return f"Failed to send Slack notification: {response.status}"
                        
        except Exception as e:
            return f"Error sending Slack notification: {e}"
    
    async def _send_email_notification(self, channel_config: Dict[str, Any], message: str) -> str:
        """Send email notification"""
        try:
            # Email configuration would come from environment variables
            smtp_host = "smtp.gmail.com"
            smtp_port = 587
            smtp_user = "ops@company.com"
            smtp_password = "password"  # From environment
            
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = ', '.join(channel_config["recipients"])
            msg['Subject'] = "Operational Alert - Splunk MCP Platform"
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            return "Email notification sent successfully"
            
        except Exception as e:
            return f"Error sending email notification: {e}"
    
    async def _create_incident(self, metric: OperationalMetric, severity: AlertSeverity) -> str:
        """Create incident record"""
        try:
            incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{metric.service}"
            
            incident = IncidentContext(
                incident_id=incident_id,
                severity=severity,
                service=metric.service,
                description=f"{metric.name} threshold exceeded: {metric.value}",
                metrics=[metric],
                timestamp=datetime.utcnow()
            )
            
            self.active_incidents[incident_id] = incident
            
            # Store incident in Redis for persistence
            incident_data = {
                "incident_id": incident_id,
                "severity": severity.value,
                "service": metric.service,
                "description": incident.description,
                "timestamp": incident.timestamp.isoformat(),
                "status": "open"
            }
            
            self.redis_client.hset(f"incident:{incident_id}", mapping=incident_data)
            
            return f"Created incident {incident_id}"
            
        except Exception as e:
            return f"Failed to create incident: {e}"
    
    async def _gather_diagnostics(self, service: str) -> str:
        """Gather diagnostic information"""
        try:
            diagnostics = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": service,
                "data": {}
            }
            
            # Gather logs
            if self.k8s_client:
                try:
                    core_v1 = client.CoreV1Api()
                    pods = core_v1.list_namespaced_pod(
                        namespace="splunk-mcp-prod",
                        label_selector=f"app={service}"
                    )
                    
                    if pods.items:
                        pod_name = pods.items[0].metadata.name
                        logs = core_v1.read_namespaced_pod_log(
                            name=pod_name,
                            namespace="splunk-mcp-prod",
                            tail_lines=100
                        )
                        diagnostics["data"]["recent_logs"] = logs.split('\n')[-10:]  # Last 10 lines
                except Exception as e:
                    diagnostics["data"]["logs_error"] = str(e)
            
            # Gather metrics
            recent_metrics = [
                m for m in self.metrics_history 
                if m.service == service and 
                m.timestamp > datetime.utcnow() - timedelta(minutes=10)
            ]
            
            diagnostics["data"]["recent_metrics"] = [
                {
                    "name": m.name,
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in recent_metrics
            ]
            
            # Store diagnostics
            diagnostics_key = f"diagnostics:{service}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            self.redis_client.setex(diagnostics_key, 86400, json.dumps(diagnostics))  # 24h TTL
            
            return f"Gathered diagnostics for {service} (key: {diagnostics_key})"
            
        except Exception as e:
            return f"Failed to gather diagnostics for {service}: {e}"
    
    async def _optimize_resources(self, service: str) -> str:
        """Optimize resource allocation"""
        try:
            # Analyze recent resource usage
            cpu_metrics = [
                m for m in self.metrics_history 
                if m.service == service and m.name == "cpu_usage" and
                m.timestamp > datetime.utcnow() - timedelta(hours=1)
            ]
            
            memory_metrics = [
                m for m in self.metrics_history 
                if m.service == service and m.name == "memory_utilization" and
                m.timestamp > datetime.utcnow() - timedelta(hours=1)
            ]
            
            optimizations = []
            
            if cpu_metrics:
                avg_cpu = sum(m.value for m in cpu_metrics) / len(cpu_metrics)
                if avg_cpu < 0.2:
                    optimizations.append("CPU: Consider reducing CPU requests")
                elif avg_cpu > 0.8:
                    optimizations.append("CPU: Consider increasing CPU limits")
            
            if memory_metrics:
                avg_memory = sum(m.value for m in memory_metrics) / len(memory_metrics)
                if avg_memory < 0.5:
                    optimizations.append("Memory: Consider reducing memory requests")
                elif avg_memory > 0.9:
                    optimizations.append("Memory: Consider increasing memory limits")
            
            if optimizations:
                # Store optimization recommendations
                opt_key = f"optimization:{service}:{datetime.utcnow().strftime('%Y%m%d')}"
                self.redis_client.setex(opt_key, 86400, json.dumps(optimizations))
                
                return f"Generated {len(optimizations)} optimization recommendations for {service}"
            else:
                return f"No optimization recommendations for {service} at this time"
                
        except Exception as e:
            return f"Failed to optimize resources for {service}: {e}"
    
    async def run_operational_cycle(self):
        """Run one cycle of operational monitoring and automation"""
        try:
            logger.info("Starting operational automation cycle")
            
            # Collect metrics
            metrics = await self.collect_metrics()
            logger.info(f"Collected {len(metrics)} metrics")
            
            # Evaluate automation rules
            triggered_rules = await self.evaluate_automation_rules(metrics)
            logger.info(f"Triggered {len(triggered_rules)} automation rules")
            
            # Execute automation actions
            for rule, metric in triggered_rules:
                try:
                    result = await self.execute_automation_action(rule, metric)
                    logger.info(f"Executed {rule.action} for {rule.name}: {result}")
                except Exception as e:
                    logger.error(f"Failed to execute {rule.action}: {e}")
            
            # Check for incident escalation
            await self._check_incident_escalation()
            
            # Cleanup old data
            await self._cleanup_old_data()
            
            logger.info("Operational automation cycle completed")
            
        except Exception as e:
            logger.error(f"Error in operational cycle: {e}")
    
    async def _check_incident_escalation(self):
        """Check for incidents that need escalation"""
        for incident_id, incident in self.active_incidents.items():
            try:
                # Check if incident is older than escalation threshold
                escalation_time = timedelta(minutes=15)  # Default escalation time
                
                if datetime.utcnow() - incident.timestamp > escalation_time:
                    if incident.escalation_level == 0:
                        # First escalation
                        await self._escalate_incident(incident)
                        incident.escalation_level = 1
            
            except Exception as e:
                logger.error(f"Error checking escalation for incident {incident_id}: {e}")
    
    async def _escalate_incident(self, incident: IncidentContext):
        """Escalate incident to higher level"""
        try:
            # Send escalation notification
            message = f"🚨 **INCIDENT ESCALATION**\n\n"
            message += f"**Incident ID**: {incident.incident_id}\n"
            message += f"**Service**: {incident.service}\n"
            message += f"**Description**: {incident.description}\n"
            message += f"**Duration**: {datetime.utcnow() - incident.timestamp}\n"
            message += f"**Automated Actions**: {', '.join(incident.automated_actions)}\n\n"
            message += "Incident requires immediate attention!"
            
            # Send to executive team
            alerting_config = self.config.get("alerting_config", {})
            channels = alerting_config.get("notification_channels", [])
            
            for channel in channels:
                if channel["name"] == "executive_team":
                    await self._send_email_notification(channel, message)
            
            logger.warning(f"Escalated incident {incident.incident_id}")
            
        except Exception as e:
            logger.error(f"Error escalating incident {incident.incident_id}: {e}")
    
    async def _cleanup_old_data(self):
        """Cleanup old operational data"""
        try:
            # Remove old metrics (keep last 1000)
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            # Cleanup old incidents (closed incidents older than 7 days)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            incidents_to_remove = []
            
            for incident_id, incident in self.active_incidents.items():
                if incident.timestamp < cutoff_date:
                    incidents_to_remove.append(incident_id)
            
            for incident_id in incidents_to_remove:
                del self.active_incidents[incident_id]
                self.redis_client.delete(f"incident:{incident_id}")
            
            logger.info(f"Cleaned up {len(incidents_to_remove)} old incidents")
            
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")

async def main():
    """Main function to run operational automation"""
    automation = OperationalAutomation()
    
    logger.info("Starting Operational Automation System")
    
    # Run continuous monitoring loop
    while True:
        try:
            await automation.run_operational_cycle()
            await asyncio.sleep(60)  # Run every minute
            
        except KeyboardInterrupt:
            logger.info("Shutting down operational automation")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            await asyncio.sleep(30)  # Wait before retrying

if __name__ == "__main__":
    asyncio.run(main())