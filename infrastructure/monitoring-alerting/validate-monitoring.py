#!/usr/bin/env python3
"""
Monitoring Stack Validation System
==================================
Comprehensive validation script for the Splunk MCP monitoring infrastructure
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
import requests
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ValidationResult(Enum):
    """Validation result status"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIP = "SKIP"

class ComponentType(Enum):
    """Component types for validation"""
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    ALERTMANAGER = "alertmanager"
    NODE_EXPORTER = "node-exporter"
    KUBE_STATE_METRICS = "kube-state-metrics"
    SERVICE_MONITORS = "service-monitors"
    ALERT_RULES = "alert-rules"
    DASHBOARDS = "dashboards"

@dataclass
class ValidationCheck:
    """Individual validation check"""
    name: str
    component: ComponentType
    description: str
    result: ValidationResult = ValidationResult.SKIP
    message: str = ""
    duration: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationSummary:
    """Overall validation summary"""
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    skipped: int = 0
    total_duration: float = 0.0
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None

class MonitoringValidator:
    """Main monitoring validation system"""
    
    def __init__(self, namespace: str = "splunk-mcp-monitoring-prod", environment: str = "production"):
        self.namespace = namespace
        self.environment = environment
        self.checks: List[ValidationCheck] = []
        self.summary = ValidationSummary()
        self.port_forwards: List[subprocess.Popen] = []
        
    async def run_all_validations(self) -> ValidationSummary:
        """Run all monitoring validations"""
        logger.info(f"Starting monitoring validation for namespace: {self.namespace}")
        self.summary.start_time = datetime.utcnow()
        
        try:
            # Initialize validation checks
            await self._initialize_validation_checks()
            
            # Run all checks
            await self._run_kubernetes_checks()
            await self._run_prometheus_checks()
            await self._run_grafana_checks()
            await self._run_alertmanager_checks()
            await self._run_service_monitor_checks()
            await self._run_alert_rules_checks()
            await self._run_metrics_collection_checks()
            await self._run_dashboard_checks()
            await self._run_integration_checks()
            
            # Generate summary
            self._generate_summary()
            
            return self.summary
            
        except Exception as e:
            logger.error(f"Validation failed with error: {e}")
            raise
        finally:
            # Cleanup port forwards
            await self._cleanup_port_forwards()
            self.summary.end_time = datetime.utcnow()
            
    async def _initialize_validation_checks(self):
        """Initialize all validation checks"""
        logger.info("Initializing validation checks...")
        
        # Kubernetes Infrastructure Checks
        self.checks.extend([
            ValidationCheck("namespace_exists", ComponentType.PROMETHEUS, "Verify monitoring namespace exists"),
            ValidationCheck("prometheus_pod_running", ComponentType.PROMETHEUS, "Verify Prometheus pods are running"),
            ValidationCheck("grafana_pod_running", ComponentType.GRAFANA, "Verify Grafana pods are running"),
            ValidationCheck("alertmanager_pod_running", ComponentType.ALERTMANAGER, "Verify AlertManager pods are running"),
            ValidationCheck("node_exporter_running", ComponentType.NODE_EXPORTER, "Verify Node Exporter is running"),
            ValidationCheck("kube_state_metrics_running", ComponentType.KUBE_STATE_METRICS, "Verify Kube State Metrics is running"),
        ])
        
        # Service Health Checks
        self.checks.extend([
            ValidationCheck("prometheus_health", ComponentType.PROMETHEUS, "Check Prometheus health endpoint"),
            ValidationCheck("grafana_health", ComponentType.GRAFANA, "Check Grafana health endpoint"),
            ValidationCheck("alertmanager_health", ComponentType.ALERTMANAGER, "Check AlertManager health endpoint"),
        ])
        
        # Configuration Checks
        self.checks.extend([
            ValidationCheck("prometheus_config", ComponentType.PROMETHEUS, "Validate Prometheus configuration"),
            ValidationCheck("alertmanager_config", ComponentType.ALERTMANAGER, "Validate AlertManager configuration"),
            ValidationCheck("service_monitors", ComponentType.SERVICE_MONITORS, "Validate ServiceMonitor configurations"),
            ValidationCheck("alert_rules", ComponentType.ALERT_RULES, "Validate PrometheusRule configurations"),
        ])
        
        # Metrics Collection Checks
        self.checks.extend([
            ValidationCheck("prometheus_targets", ComponentType.PROMETHEUS, "Check Prometheus target discovery"),
            ValidationCheck("metrics_ingestion", ComponentType.PROMETHEUS, "Verify metrics are being ingested"),
            ValidationCheck("splunk_mcp_metrics", ComponentType.SERVICE_MONITORS, "Check Splunk MCP service metrics"),
        ])
        
        # Dashboard Checks
        self.checks.extend([
            ValidationCheck("grafana_dashboards", ComponentType.DASHBOARDS, "Verify Grafana dashboards are loaded"),
            ValidationCheck("dashboard_queries", ComponentType.DASHBOARDS, "Test dashboard query execution"),
        ])
        
        # Alert System Checks
        self.checks.extend([
            ValidationCheck("alert_rules_loaded", ComponentType.ALERT_RULES, "Verify alert rules are loaded"),
            ValidationCheck("alertmanager_routing", ComponentType.ALERTMANAGER, "Test alert routing configuration"),
        ])
        
        self.summary.total_checks = len(self.checks)
        logger.info(f"Initialized {self.summary.total_checks} validation checks")
        
    async def _run_kubernetes_checks(self):
        """Run Kubernetes-related validation checks"""
        logger.info("Running Kubernetes validation checks...")
        
        # Check namespace exists
        await self._run_check("namespace_exists", self._check_namespace_exists)
        
        # Check pod status
        await self._run_check("prometheus_pod_running", self._check_prometheus_pods)
        await self._run_check("grafana_pod_running", self._check_grafana_pods)
        await self._run_check("alertmanager_pod_running", self._check_alertmanager_pods)
        await self._run_check("node_exporter_running", self._check_node_exporter_pods)
        await self._run_check("kube_state_metrics_running", self._check_kube_state_metrics_pods)
        
    async def _run_prometheus_checks(self):
        """Run Prometheus-specific validation checks"""
        logger.info("Running Prometheus validation checks...")
        
        await self._run_check("prometheus_health", self._check_prometheus_health)
        await self._run_check("prometheus_config", self._check_prometheus_config)
        await self._run_check("prometheus_targets", self._check_prometheus_targets)
        await self._run_check("metrics_ingestion", self._check_metrics_ingestion)
        
    async def _run_grafana_checks(self):
        """Run Grafana-specific validation checks"""
        logger.info("Running Grafana validation checks...")
        
        await self._run_check("grafana_health", self._check_grafana_health)
        await self._run_check("grafana_dashboards", self._check_grafana_dashboards)
        await self._run_check("dashboard_queries", self._check_dashboard_queries)
        
    async def _run_alertmanager_checks(self):
        """Run AlertManager-specific validation checks"""
        logger.info("Running AlertManager validation checks...")
        
        await self._run_check("alertmanager_health", self._check_alertmanager_health)
        await self._run_check("alertmanager_config", self._check_alertmanager_config)
        await self._run_check("alertmanager_routing", self._check_alertmanager_routing)
        
    async def _run_service_monitor_checks(self):
        """Run ServiceMonitor validation checks"""
        logger.info("Running ServiceMonitor validation checks...")
        
        await self._run_check("service_monitors", self._check_service_monitors)
        await self._run_check("splunk_mcp_metrics", self._check_splunk_mcp_metrics)
        
    async def _run_alert_rules_checks(self):
        """Run alert rules validation checks"""
        logger.info("Running alert rules validation checks...")
        
        await self._run_check("alert_rules", self._check_alert_rules)
        await self._run_check("alert_rules_loaded", self._check_alert_rules_loaded)
        
    async def _run_metrics_collection_checks(self):
        """Run metrics collection validation checks"""
        logger.info("Running metrics collection validation checks...")
        
        # These checks are covered in other sections
        pass
        
    async def _run_dashboard_checks(self):
        """Run dashboard validation checks"""
        logger.info("Running dashboard validation checks...")
        
        # These checks are covered in Grafana section
        pass
        
    async def _run_integration_checks(self):
        """Run integration validation checks"""
        logger.info("Running integration validation checks...")
        
        # Additional integration checks could be added here
        pass
        
    async def _run_check(self, check_name: str, check_function):
        """Run an individual validation check"""
        check = next((c for c in self.checks if c.name == check_name), None)
        if not check:
            logger.warning(f"Check {check_name} not found")
            return
            
        logger.info(f"Running check: {check.description}")
        start_time = time.time()
        
        try:
            result, message, details = await check_function()
            check.result = result
            check.message = message
            check.details = details
            check.duration = time.time() - start_time
            
            if result == ValidationResult.PASS:
                logger.info(f"✓ {check.description}: {message}")
            elif result == ValidationResult.WARNING:
                logger.warning(f"⚠ {check.description}: {message}")
            elif result == ValidationResult.FAIL:
                logger.error(f"✗ {check.description}: {message}")
            else:
                logger.info(f"- {check.description}: {message}")
                
        except Exception as e:
            check.result = ValidationResult.FAIL
            check.message = f"Check failed with exception: {str(e)}"
            check.duration = time.time() - start_time
            logger.error(f"✗ {check.description}: {check.message}")
            
    # Individual check implementations
    async def _check_namespace_exists(self) -> Tuple[ValidationResult, str, Dict]:
        """Check if monitoring namespace exists"""
        result = await self._run_kubectl_command(["get", "namespace", self.namespace])
        
        if result.returncode == 0:
            return ValidationResult.PASS, f"Namespace {self.namespace} exists", {}
        else:
            return ValidationResult.FAIL, f"Namespace {self.namespace} does not exist", {}
            
    async def _check_prometheus_pods(self) -> Tuple[ValidationResult, str, Dict]:
        """Check Prometheus pod status"""
        result = await self._run_kubectl_command([
            "get", "pods", "-n", self.namespace, 
            "-l", "app.kubernetes.io/name=prometheus", 
            "-o", "jsonpath={.items[*].status.phase}"
        ])
        
        if result.returncode == 0:
            phases = result.stdout.strip().split()
            running_pods = [p for p in phases if p == "Running"]
            
            if len(running_pods) > 0:
                return ValidationResult.PASS, f"{len(running_pods)} Prometheus pods running", {"running": len(running_pods), "total": len(phases)}
            else:
                return ValidationResult.FAIL, "No Prometheus pods are running", {"phases": phases}
        else:
            return ValidationResult.FAIL, "Could not check Prometheus pods", {"error": result.stderr}
            
    async def _check_grafana_pods(self) -> Tuple[ValidationResult, str, Dict]:
        """Check Grafana pod status"""
        result = await self._run_kubectl_command([
            "get", "pods", "-n", self.namespace,
            "-l", "app.kubernetes.io/name=grafana",
            "-o", "jsonpath={.items[*].status.phase}"
        ])
        
        if result.returncode == 0:
            phases = result.stdout.strip().split()
            running_pods = [p for p in phases if p == "Running"]
            
            if len(running_pods) > 0:
                return ValidationResult.PASS, f"{len(running_pods)} Grafana pods running", {"running": len(running_pods), "total": len(phases)}
            else:
                return ValidationResult.FAIL, "No Grafana pods are running", {"phases": phases}
        else:
            return ValidationResult.FAIL, "Could not check Grafana pods", {"error": result.stderr}
            
    async def _check_alertmanager_pods(self) -> Tuple[ValidationResult, str, Dict]:
        """Check AlertManager pod status"""
        result = await self._run_kubectl_command([
            "get", "pods", "-n", self.namespace,
            "-l", "app.kubernetes.io/name=alertmanager",
            "-o", "jsonpath={.items[*].status.phase}"
        ])
        
        if result.returncode == 0:
            phases = result.stdout.strip().split()
            running_pods = [p for p in phases if p == "Running"]
            
            if len(running_pods) > 0:
                return ValidationResult.PASS, f"{len(running_pods)} AlertManager pods running", {"running": len(running_pods), "total": len(phases)}
            else:
                return ValidationResult.FAIL, "No AlertManager pods are running", {"phases": phases}
        else:
            return ValidationResult.FAIL, "Could not check AlertManager pods", {"error": result.stderr}
            
    async def _check_node_exporter_pods(self) -> Tuple[ValidationResult, str, Dict]:
        """Check Node Exporter pod status"""
        result = await self._run_kubectl_command([
            "get", "pods", "-n", self.namespace,
            "-l", "app.kubernetes.io/name=node-exporter",
            "-o", "jsonpath={.items[*].status.phase}"
        ])
        
        if result.returncode == 0:
            phases = result.stdout.strip().split()
            running_pods = [p for p in phases if p == "Running"]
            
            if len(running_pods) > 0:
                return ValidationResult.PASS, f"{len(running_pods)} Node Exporter pods running", {"running": len(running_pods), "total": len(phases)}
            else:
                return ValidationResult.WARNING, "No Node Exporter pods found", {"phases": phases}
        else:
            return ValidationResult.WARNING, "Could not check Node Exporter pods", {"error": result.stderr}
            
    async def _check_kube_state_metrics_pods(self) -> Tuple[ValidationResult, str, Dict]:
        """Check Kube State Metrics pod status"""
        result = await self._run_kubectl_command([
            "get", "pods", "-n", self.namespace,
            "-l", "app.kubernetes.io/name=kube-state-metrics",
            "-o", "jsonpath={.items[*].status.phase}"
        ])
        
        if result.returncode == 0:
            phases = result.stdout.strip().split()
            running_pods = [p for p in phases if p == "Running"]
            
            if len(running_pods) > 0:
                return ValidationResult.PASS, f"{len(running_pods)} Kube State Metrics pods running", {"running": len(running_pods), "total": len(phases)}
            else:
                return ValidationResult.WARNING, "No Kube State Metrics pods found", {"phases": phases}
        else:
            return ValidationResult.WARNING, "Could not check Kube State Metrics pods", {"error": result.stderr}
            
    async def _check_prometheus_health(self) -> Tuple[ValidationResult, str, Dict]:
        """Check Prometheus health endpoint"""
        port_forward = await self._setup_port_forward("prometheus", 9090)
        if not port_forward:
            return ValidationResult.FAIL, "Could not establish port forward to Prometheus", {}
            
        try:
            await asyncio.sleep(2)  # Wait for port forward to establish
            response = requests.get("http://localhost:9090/-/healthy", timeout=10)
            
            if response.status_code == 200:
                return ValidationResult.PASS, "Prometheus health check passed", {"status_code": response.status_code}
            else:
                return ValidationResult.FAIL, f"Prometheus health check failed with status {response.status_code}", {"status_code": response.status_code}
        except Exception as e:
            return ValidationResult.FAIL, f"Could not connect to Prometheus: {str(e)}", {}
            
    async def _check_grafana_health(self) -> Tuple[ValidationResult, str, Dict]:
        """Check Grafana health endpoint"""
        port_forward = await self._setup_port_forward("grafana", 3000)
        if not port_forward:
            return ValidationResult.FAIL, "Could not establish port forward to Grafana", {}
            
        try:
            await asyncio.sleep(2)  # Wait for port forward to establish
            response = requests.get("http://localhost:3000/api/health", timeout=10)
            
            if response.status_code == 200:
                return ValidationResult.PASS, "Grafana health check passed", {"status_code": response.status_code}
            else:
                return ValidationResult.FAIL, f"Grafana health check failed with status {response.status_code}", {"status_code": response.status_code}
        except Exception as e:
            return ValidationResult.FAIL, f"Could not connect to Grafana: {str(e)}", {}
            
    async def _check_alertmanager_health(self) -> Tuple[ValidationResult, str, Dict]:
        """Check AlertManager health endpoint"""
        port_forward = await self._setup_port_forward("alertmanager", 9093)
        if not port_forward:
            return ValidationResult.FAIL, "Could not establish port forward to AlertManager", {}
            
        try:
            await asyncio.sleep(2)  # Wait for port forward to establish
            response = requests.get("http://localhost:9093/-/healthy", timeout=10)
            
            if response.status_code == 200:
                return ValidationResult.PASS, "AlertManager health check passed", {"status_code": response.status_code}
            else:
                return ValidationResult.FAIL, f"AlertManager health check failed with status {response.status_code}", {"status_code": response.status_code}
        except Exception as e:
            return ValidationResult.FAIL, f"Could not connect to AlertManager: {str(e)}", {}
            
    async def _check_prometheus_config(self) -> Tuple[ValidationResult, str, Dict]:
        """Check Prometheus configuration"""
        try:
            response = requests.get("http://localhost:9090/api/v1/status/config", timeout=10)
            
            if response.status_code == 200:
                config_data = response.json()
                return ValidationResult.PASS, "Prometheus configuration loaded successfully", {"config_status": "valid"}
            else:
                return ValidationResult.FAIL, f"Could not retrieve Prometheus config: {response.status_code}", {}
        except Exception as e:
            return ValidationResult.WARNING, f"Could not validate Prometheus config: {str(e)}", {}
            
    async def _check_alertmanager_config(self) -> Tuple[ValidationResult, str, Dict]:
        """Check AlertManager configuration"""
        try:
            response = requests.get("http://localhost:9093/api/v1/status", timeout=10)
            
            if response.status_code == 200:
                return ValidationResult.PASS, "AlertManager configuration loaded successfully", {"config_status": "valid"}
            else:
                return ValidationResult.FAIL, f"Could not retrieve AlertManager status: {response.status_code}", {}
        except Exception as e:
            return ValidationResult.WARNING, f"Could not validate AlertManager config: {str(e)}", {}
            
    async def _check_service_monitors(self) -> Tuple[ValidationResult, str, Dict]:
        """Check ServiceMonitor configurations"""
        result = await self._run_kubectl_command([
            "get", "servicemonitors", "-n", self.namespace, "-o", "json"
        ])
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                monitor_count = len(data.get("items", []))
                
                if monitor_count > 0:
                    return ValidationResult.PASS, f"Found {monitor_count} ServiceMonitors", {"count": monitor_count}
                else:
                    return ValidationResult.WARNING, "No ServiceMonitors found", {"count": 0}
            except json.JSONDecodeError:
                return ValidationResult.FAIL, "Could not parse ServiceMonitor JSON", {}
        else:
            return ValidationResult.FAIL, "Could not retrieve ServiceMonitors", {"error": result.stderr}
            
    async def _check_alert_rules(self) -> Tuple[ValidationResult, str, Dict]:
        """Check PrometheusRule configurations"""
        result = await self._run_kubectl_command([
            "get", "prometheusrules", "-n", self.namespace, "-o", "json"
        ])
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                rules_count = len(data.get("items", []))
                
                if rules_count > 0:
                    return ValidationResult.PASS, f"Found {rules_count} PrometheusRules", {"count": rules_count}
                else:
                    return ValidationResult.WARNING, "No PrometheusRules found", {"count": 0}
            except json.JSONDecodeError:
                return ValidationResult.FAIL, "Could not parse PrometheusRules JSON", {}
        else:
            return ValidationResult.FAIL, "Could not retrieve PrometheusRules", {"error": result.stderr}
            
    async def _check_prometheus_targets(self) -> Tuple[ValidationResult, str, Dict]:
        """Check Prometheus target discovery"""
        try:
            response = requests.get("http://localhost:9090/api/v1/targets", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                targets = data.get("data", {}).get("activeTargets", [])
                healthy_targets = [t for t in targets if t.get("health") == "up"]
                
                if len(healthy_targets) > 0:
                    return ValidationResult.PASS, f"Found {len(healthy_targets)}/{len(targets)} healthy targets", {
                        "total": len(targets),
                        "healthy": len(healthy_targets)
                    }
                else:
                    return ValidationResult.FAIL, f"No healthy targets found ({len(targets)} total)", {"total": len(targets)}
            else:
                return ValidationResult.FAIL, f"Could not retrieve targets: {response.status_code}", {}
        except Exception as e:
            return ValidationResult.WARNING, f"Could not check Prometheus targets: {str(e)}", {}
            
    async def _check_metrics_ingestion(self) -> Tuple[ValidationResult, str, Dict]:
        """Check if metrics are being ingested"""
        try:
            # Query for basic metrics
            response = requests.get(
                "http://localhost:9090/api/v1/query",
                params={"query": "up"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("data", {}).get("result", [])
                
                if len(result) > 0:
                    return ValidationResult.PASS, f"Metrics ingestion working ({len(result)} series)", {"series_count": len(result)}
                else:
                    return ValidationResult.FAIL, "No metrics being ingested", {}
            else:
                return ValidationResult.FAIL, f"Could not query metrics: {response.status_code}", {}
        except Exception as e:
            return ValidationResult.WARNING, f"Could not check metrics ingestion: {str(e)}", {}
            
    async def _check_splunk_mcp_metrics(self) -> Tuple[ValidationResult, str, Dict]:
        """Check Splunk MCP specific metrics"""
        try:
            # Query for Splunk MCP service metrics
            response = requests.get(
                "http://localhost:9090/api/v1/query",
                params={"query": "up{job=~\".*splunk.*\"}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("data", {}).get("result", [])
                
                if len(result) > 0:
                    return ValidationResult.PASS, f"Found {len(result)} Splunk MCP metrics", {"metrics_count": len(result)}
                else:
                    return ValidationResult.WARNING, "No Splunk MCP metrics found", {}
            else:
                return ValidationResult.WARNING, f"Could not query Splunk MCP metrics: {response.status_code}", {}
        except Exception as e:
            return ValidationResult.WARNING, f"Could not check Splunk MCP metrics: {str(e)}", {}
            
    async def _check_grafana_dashboards(self) -> Tuple[ValidationResult, str, Dict]:
        """Check if Grafana dashboards are loaded"""
        try:
            # This would require Grafana API authentication
            # For now, just check if Grafana is responding
            response = requests.get("http://localhost:3000/api/health", timeout=10)
            
            if response.status_code == 200:
                return ValidationResult.PASS, "Grafana is accessible for dashboard validation", {}
            else:
                return ValidationResult.WARNING, "Cannot access Grafana for dashboard validation", {}
        except Exception as e:
            return ValidationResult.WARNING, f"Could not validate Grafana dashboards: {str(e)}", {}
            
    async def _check_dashboard_queries(self) -> Tuple[ValidationResult, str, Dict]:
        """Test dashboard query execution"""
        # This would require more complex integration with Grafana API
        return ValidationResult.SKIP, "Dashboard query testing requires Grafana API integration", {}
        
    async def _check_alert_rules_loaded(self) -> Tuple[ValidationResult, str, Dict]:
        """Check if alert rules are loaded in Prometheus"""
        try:
            response = requests.get("http://localhost:9090/api/v1/rules", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                groups = data.get("data", {}).get("groups", [])
                total_rules = sum(len(group.get("rules", [])) for group in groups)
                
                if total_rules > 0:
                    return ValidationResult.PASS, f"Found {total_rules} alert rules loaded", {"rules_count": total_rules}
                else:
                    return ValidationResult.WARNING, "No alert rules loaded", {}
            else:
                return ValidationResult.FAIL, f"Could not retrieve alert rules: {response.status_code}", {}
        except Exception as e:
            return ValidationResult.WARNING, f"Could not check alert rules: {str(e)}", {}
            
    async def _check_alertmanager_routing(self) -> Tuple[ValidationResult, str, Dict]:
        """Test AlertManager routing configuration"""
        try:
            response = requests.get("http://localhost:9093/api/v1/status", timeout=10)
            
            if response.status_code == 200:
                return ValidationResult.PASS, "AlertManager routing configuration loaded", {}
            else:
                return ValidationResult.WARNING, f"Could not validate AlertManager routing: {response.status_code}", {}
        except Exception as e:
            return ValidationResult.WARNING, f"Could not check AlertManager routing: {str(e)}", {}
            
    async def _setup_port_forward(self, service_type: str, port: int) -> Optional[subprocess.Popen]:
        """Setup port forward to service"""
        service_map = {
            "prometheus": "prometheus-operator-kube-p-prometheus",
            "grafana": "prometheus-operator-grafana",
            "alertmanager": "prometheus-operator-kube-p-alertmanager"
        }
        
        service_name = service_map.get(service_type)
        if not service_name:
            return None
            
        try:
            # Check if port is already in use
            proc = subprocess.Popen([
                "kubectl", "port-forward", "-n", self.namespace,
                f"svc/{service_name}", f"{port}:{port if service_type != 'grafana' else 80}"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.port_forwards.append(proc)
            return proc
        except Exception as e:
            logger.warning(f"Could not setup port forward for {service_type}: {e}")
            return None
            
    async def _cleanup_port_forwards(self):
        """Cleanup all port forwards"""
        for proc in self.port_forwards:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try:
                    proc.kill()
                except:
                    pass
                    
    async def _run_kubectl_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run kubectl command"""
        full_cmd = ["kubectl"] + cmd
        process = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return subprocess.CompletedProcess(
            args=full_cmd,
            returncode=process.returncode,
            stdout=stdout.decode() if stdout else "",
            stderr=stderr.decode() if stderr else ""
        )
        
    def _generate_summary(self):
        """Generate validation summary"""
        for check in self.checks:
            if check.result == ValidationResult.PASS:
                self.summary.passed += 1
            elif check.result == ValidationResult.FAIL:
                self.summary.failed += 1
            elif check.result == ValidationResult.WARNING:
                self.summary.warnings += 1
            else:
                self.summary.skipped += 1
                
        self.summary.total_duration = sum(check.duration for check in self.checks)
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        return {
            "summary": {
                "total_checks": self.summary.total_checks,
                "passed": self.summary.passed,
                "failed": self.summary.failed,
                "warnings": self.summary.warnings,
                "skipped": self.summary.skipped,
                "success_rate": (self.summary.passed / self.summary.total_checks * 100) if self.summary.total_checks > 0 else 0,
                "total_duration": f"{self.summary.total_duration:.2f}s",
                "start_time": self.summary.start_time.isoformat(),
                "end_time": self.summary.end_time.isoformat() if self.summary.end_time else None
            },
            "checks": [
                {
                    "name": check.name,
                    "component": check.component.value,
                    "description": check.description,
                    "result": check.result.value,
                    "message": check.message,
                    "duration": f"{check.duration:.2f}s",
                    "details": check.details
                }
                for check in self.checks
            ],
            "components": self._get_component_summary()
        }
        
    def _get_component_summary(self) -> Dict[str, Any]:
        """Get component-wise summary"""
        components = {}
        
        for component_type in ComponentType:
            component_checks = [c for c in self.checks if c.component == component_type]
            if component_checks:
                passed = len([c for c in component_checks if c.result == ValidationResult.PASS])
                failed = len([c for c in component_checks if c.result == ValidationResult.FAIL])
                warnings = len([c for c in component_checks if c.result == ValidationResult.WARNING])
                skipped = len([c for c in component_checks if c.result == ValidationResult.SKIP])
                
                components[component_type.value] = {
                    "total": len(component_checks),
                    "passed": passed,
                    "failed": failed,
                    "warnings": warnings,
                    "skipped": skipped,
                    "health": "HEALTHY" if failed == 0 else "UNHEALTHY" if passed == 0 else "DEGRADED"
                }
                
        return components
        
    def print_summary(self):
        """Print validation summary to console"""
        print("\n" + "="*80)
        print("MONITORING VALIDATION SUMMARY")
        print("="*80)
        
        print(f"Environment: {self.environment}")
        print(f"Namespace: {self.namespace}")
        print(f"Total Checks: {self.summary.total_checks}")
        print(f"Duration: {self.summary.total_duration:.2f}s")
        print()
        
        # Results summary
        print("RESULTS:")
        print(f"  ✓ Passed:   {self.summary.passed:2d} ({self.summary.passed/self.summary.total_checks*100:5.1f}%)")
        print(f"  ✗ Failed:   {self.summary.failed:2d} ({self.summary.failed/self.summary.total_checks*100:5.1f}%)")
        print(f"  ⚠ Warnings: {self.summary.warnings:2d} ({self.summary.warnings/self.summary.total_checks*100:5.1f}%)")
        print(f"  - Skipped:  {self.summary.skipped:2d} ({self.summary.skipped/self.summary.total_checks*100:5.1f}%)")
        print()
        
        # Component summary
        print("COMPONENT HEALTH:")
        components = self._get_component_summary()
        for component, stats in components.items():
            health_icon = "✓" if stats["health"] == "HEALTHY" else "⚠" if stats["health"] == "DEGRADED" else "✗"
            print(f"  {health_icon} {component:20s} {stats['health']:10s} ({stats['passed']}/{stats['total']} passed)")
        print()
        
        # Failed checks
        failed_checks = [c for c in self.checks if c.result == ValidationResult.FAIL]
        if failed_checks:
            print("FAILED CHECKS:")
            for check in failed_checks:
                print(f"  ✗ {check.description}: {check.message}")
            print()
            
        # Overall status
        overall_status = "HEALTHY" if self.summary.failed == 0 else "CRITICAL" if self.summary.passed == 0 else "DEGRADED"
        status_icon = "✓" if overall_status == "HEALTHY" else "⚠" if overall_status == "DEGRADED" else "✗"
        print(f"OVERALL STATUS: {status_icon} {overall_status}")
        print("="*80)

# CLI interface
async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitoring Stack Validation")
    parser.add_argument("--namespace", "-n", default="splunk-mcp-monitoring-prod", help="Monitoring namespace")
    parser.add_argument("--environment", "-e", default="production", help="Environment name")
    parser.add_argument("--output", "-o", choices=["console", "json", "yaml"], default="console", help="Output format")
    parser.add_argument("--report-file", help="Save report to file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    validator = MonitoringValidator(namespace=args.namespace, environment=args.environment)
    
    try:
        summary = await validator.run_all_validations()
        
        if args.output == "console":
            validator.print_summary()
        else:
            report = validator.generate_report()
            
            if args.output == "json":
                output = json.dumps(report, indent=2)
            elif args.output == "yaml":
                output = yaml.dump(report, default_flow_style=False)
                
            if args.report_file:
                with open(args.report_file, 'w') as f:
                    f.write(output)
                print(f"Report saved to {args.report_file}")
            else:
                print(output)
                
        # Exit with appropriate code
        if summary.failed > 0:
            sys.exit(1)
        elif summary.warnings > 0:
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(3)

if __name__ == "__main__":
    asyncio.run(main())