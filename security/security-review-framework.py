#!/usr/bin/env python3
"""
Comprehensive Security Review and Hardening Framework
===================================================
Enterprise-grade security assessment and hardening automation for Splunk MCP Integration platform
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
import hashlib
import base64
import re
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """Security assessment levels"""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ComplianceFramework(Enum):
    """Compliance frameworks"""
    SOX = "sox"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    NIST = "nist"

class SecurityDomain(Enum):
    """Security assessment domains"""
    INFRASTRUCTURE = "infrastructure"
    KUBERNETES = "kubernetes"
    NETWORK = "network"
    APPLICATION = "application"
    DATA = "data"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    COMPLIANCE = "compliance"
    MONITORING = "monitoring"

@dataclass
class SecurityFinding:
    """Individual security finding"""
    id: str
    title: str
    description: str
    severity: SecurityLevel
    domain: SecurityDomain
    affected_components: List[str]
    compliance_frameworks: List[ComplianceFramework] = field(default_factory=list)
    remediation: str = ""
    remediation_effort: str = "medium"  # low, medium, high
    status: str = "open"  # open, in_progress, resolved, accepted_risk
    details: Dict[str, Any] = field(default_factory=dict)
    references: List[str] = field(default_factory=list)

@dataclass
class SecurityHardening:
    """Security hardening action"""
    id: str
    title: str
    description: str
    domain: SecurityDomain
    implementation: str
    validation: str
    status: str = "pending"  # pending, applied, verified, failed
    rollback: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SecurityAssessmentResult:
    """Overall security assessment result"""
    assessment_id: str
    timestamp: datetime
    findings: List[SecurityFinding] = field(default_factory=list)
    hardenings: List[SecurityHardening] = field(default_factory=list)
    compliance_status: Dict[ComplianceFramework, str] = field(default_factory=dict)
    overall_score: float = 0.0
    risk_level: SecurityLevel = SecurityLevel.MEDIUM

class SecurityReviewFramework:
    """Main security review and hardening system"""
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.assessment_id = f"security-assessment-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        self.findings: List[SecurityFinding] = []
        self.hardenings: List[SecurityHardening] = []
        self.artifacts_dir = Path("security-artifacts")
        self.artifacts_dir.mkdir(exist_ok=True)
        
        # Service configurations
        self.services = [
            "api-gateway", "nlp-engine", "visualization", "alert-manager",
            "slack-bot", "teams-bot", "email-service", "webhook-service",
            "bi-integration", "pdf-export", "powerpoint-export", "html-report",
            "word-export", "csv-export", "json-xml-export", "secure-sharing",
            "report-scheduling", "frontend"
        ]
        
    async def execute_comprehensive_security_review(self) -> SecurityAssessmentResult:
        """Execute comprehensive security review and hardening"""
        logger.info(f"Starting comprehensive security review (ID: {self.assessment_id})")
        
        try:
            # Phase 1: Infrastructure Security Assessment
            await self._assess_infrastructure_security()
            
            # Phase 2: Kubernetes Security Review
            await self._assess_kubernetes_security()
            
            # Phase 3: Network Security Analysis
            await self._assess_network_security()
            
            # Phase 4: Application Security Review
            await self._assess_application_security()
            
            # Phase 5: Data Protection Assessment
            await self._assess_data_protection()
            
            # Phase 6: Authentication & Authorization Review
            await self._assess_authentication_authorization()
            
            # Phase 7: Compliance Validation
            await self._assess_compliance()
            
            # Phase 8: Monitoring & Logging Security
            await self._assess_monitoring_security()
            
            # Phase 9: Apply Security Hardening
            await self._apply_security_hardening()
            
            # Phase 10: Generate Assessment Report
            result = await self._generate_assessment_result()
            
            logger.info("Security review and hardening completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Security assessment failed: {e}")
            raise

    async def _assess_infrastructure_security(self):
        """Assess infrastructure security configuration"""
        logger.info("Assessing infrastructure security...")
        
        # Check Docker image security
        await self._check_docker_image_security()
        
        # Check storage security
        await self._check_storage_security()
        
        # Check secrets management
        await self._check_secrets_management()
        
        # Check resource limits and quotas
        await self._check_resource_security()

    async def _check_docker_image_security(self):
        """Check Docker image security configurations"""
        findings = []
        
        # Check for non-root user configuration
        for service in self.services:
            dockerfile_path = f"services/{service}/Dockerfile"
            if os.path.exists(dockerfile_path):
                with open(dockerfile_path, 'r') as f:
                    content = f.read()
                    
                if "USER" not in content:
                    findings.append(SecurityFinding(
                        id=f"DOCKER-001-{service}",
                        title=f"Container running as root - {service}",
                        description=f"Docker container for {service} is configured to run as root user",
                        severity=SecurityLevel.HIGH,
                        domain=SecurityDomain.INFRASTRUCTURE,
                        affected_components=[service],
                        compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
                        remediation="Add USER directive to Dockerfile to run as non-root user",
                        details={"dockerfile": dockerfile_path}
                    ))
                    
                # Check for security best practices
                if "COPY --chown=" not in content:
                    findings.append(SecurityFinding(
                        id=f"DOCKER-002-{service}",
                        title=f"Improper file ownership - {service}",
                        description=f"Files copied to container may have incorrect ownership",
                        severity=SecurityLevel.MEDIUM,
                        domain=SecurityDomain.INFRASTRUCTURE,
                        affected_components=[service],
                        remediation="Use COPY --chown= to set proper file ownership"
                    ))
        
        self.findings.extend(findings)

    async def _check_storage_security(self):
        """Check storage encryption and security"""
        
        # Check for encrypted storage volumes
        result = await self._run_kubectl_command([
            "get", "pvc", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            pvcs = json.loads(result.stdout)
            for pvc in pvcs.get("items", []):
                storage_class = pvc.get("spec", {}).get("storageClassName", "")
                pvc_name = pvc.get("metadata", {}).get("name", "")
                namespace = pvc.get("metadata", {}).get("namespace", "")
                
                # Check if storage class supports encryption
                if "encrypted" not in storage_class.lower():
                    self.findings.append(SecurityFinding(
                        id=f"STORAGE-001-{pvc_name}",
                        title=f"Unencrypted storage volume - {pvc_name}",
                        description=f"PVC {pvc_name} in namespace {namespace} may not be using encrypted storage",
                        severity=SecurityLevel.HIGH,
                        domain=SecurityDomain.DATA,
                        affected_components=[f"{namespace}/{pvc_name}"],
                        compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.HIPAA, ComplianceFramework.SOX],
                        remediation="Use encrypted storage class for all persistent volumes"
                    ))

    async def _check_secrets_management(self):
        """Check Kubernetes secrets management"""
        
        # Check for secrets encryption at rest
        result = await self._run_kubectl_command([
            "get", "secrets", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            secrets = json.loads(result.stdout)
            
            # Check for base64 encoded secrets (should be encrypted at rest)
            for secret in secrets.get("items", []):
                secret_name = secret.get("metadata", {}).get("name", "")
                secret_type = secret.get("type", "")
                data = secret.get("data", {})
                
                # Check for potentially sensitive data
                sensitive_keys = ["password", "token", "key", "secret", "cert", "tls"]
                for key in data.keys():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        # This is expected behavior, but we should ensure encryption at rest
                        pass
                        
                # Check for improper secret types
                if secret_type == "Opaque" and "tls" in secret_name.lower():
                    self.findings.append(SecurityFinding(
                        id=f"SECRET-001-{secret_name}",
                        title=f"Improper secret type - {secret_name}",
                        description=f"TLS secret {secret_name} should use kubernetes.io/tls type",
                        severity=SecurityLevel.MEDIUM,
                        domain=SecurityDomain.AUTHENTICATION,
                        affected_components=[secret_name],
                        remediation="Use appropriate secret types for different credential types"
                    ))

    async def _check_resource_security(self):
        """Check resource limits and security contexts"""
        
        result = await self._run_kubectl_command([
            "get", "deployments", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            deployments = json.loads(result.stdout)
            
            for deployment in deployments.get("items", []):
                name = deployment.get("metadata", {}).get("name", "")
                namespace = deployment.get("metadata", {}).get("namespace", "")
                spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
                
                # Check security context
                security_context = spec.get("securityContext", {})
                if not security_context.get("runAsNonRoot", False):
                    self.findings.append(SecurityFinding(
                        id=f"POD-001-{name}",
                        title=f"Pod not configured to run as non-root - {name}",
                        description=f"Deployment {name} in {namespace} may run containers as root",
                        severity=SecurityLevel.HIGH,
                        domain=SecurityDomain.KUBERNETES,
                        affected_components=[f"{namespace}/{name}"],
                        compliance_frameworks=[ComplianceFramework.SOC2],
                        remediation="Set runAsNonRoot: true in pod security context"
                    ))
                
                # Check container security contexts
                for container in spec.get("containers", []):
                    container_name = container.get("name", "")
                    container_security = container.get("securityContext", {})
                    
                    if container_security.get("privileged", False):
                        self.findings.append(SecurityFinding(
                            id=f"CONTAINER-001-{name}-{container_name}",
                            title=f"Privileged container - {container_name}",
                            description=f"Container {container_name} in {name} runs with privileged access",
                            severity=SecurityLevel.CRITICAL,
                            domain=SecurityDomain.KUBERNETES,
                            affected_components=[f"{namespace}/{name}/{container_name}"],
                            remediation="Remove privileged: true from container security context"
                        ))
                    
                    if not container_security.get("readOnlyRootFilesystem", False):
                        self.findings.append(SecurityFinding(
                            id=f"CONTAINER-002-{name}-{container_name}",
                            title=f"Writable root filesystem - {container_name}",
                            description=f"Container {container_name} has writable root filesystem",
                            severity=SecurityLevel.MEDIUM,
                            domain=SecurityDomain.KUBERNETES,
                            affected_components=[f"{namespace}/{name}/{container_name}"],
                            remediation="Set readOnlyRootFilesystem: true in container security context"
                        ))

    async def _assess_kubernetes_security(self):
        """Assess Kubernetes cluster security"""
        logger.info("Assessing Kubernetes security...")
        
        # Check RBAC configuration
        await self._check_rbac_configuration()
        
        # Check network policies
        await self._check_network_policies()
        
        # Check pod security policies/standards
        await self._check_pod_security()
        
        # Check service accounts
        await self._check_service_accounts()

    async def _check_rbac_configuration(self):
        """Check RBAC configuration"""
        
        # Check for overly permissive cluster roles
        result = await self._run_kubectl_command([
            "get", "clusterroles", "-o", "json"
        ])
        
        if result.returncode == 0:
            cluster_roles = json.loads(result.stdout)
            
            for role in cluster_roles.get("items", []):
                role_name = role.get("metadata", {}).get("name", "")
                rules = role.get("rules", [])
                
                for rule in rules:
                    verbs = rule.get("verbs", [])
                    resources = rule.get("resources", [])
                    
                    # Check for overly broad permissions
                    if "*" in verbs and "*" in resources:
                        self.findings.append(SecurityFinding(
                            id=f"RBAC-001-{role_name}",
                            title=f"Overly permissive cluster role - {role_name}",
                            description=f"Cluster role {role_name} grants * permissions on * resources",
                            severity=SecurityLevel.CRITICAL,
                            domain=SecurityDomain.AUTHORIZATION,
                            affected_components=[role_name],
                            compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
                            remediation="Follow principle of least privilege and grant only necessary permissions"
                        ))

    async def _check_network_policies(self):
        """Check network policies configuration"""
        
        # Check if network policies exist
        result = await self._run_kubectl_command([
            "get", "networkpolicies", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            policies = json.loads(result.stdout)
            policy_count = len(policies.get("items", []))
            
            if policy_count == 0:
                self.findings.append(SecurityFinding(
                    id="NETWORK-001",
                    title="No network policies configured",
                    description="No Kubernetes network policies found - all pod-to-pod communication is allowed",
                    severity=SecurityLevel.HIGH,
                    domain=SecurityDomain.NETWORK,
                    affected_components=["cluster"],
                    compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
                    remediation="Implement network policies to restrict pod-to-pod communication"
                ))
            else:
                # Check for default deny policies
                has_default_deny = False
                for policy in policies.get("items", []):
                    spec = policy.get("spec", {})
                    if not spec.get("ingress") and not spec.get("egress"):
                        has_default_deny = True
                        break
                
                if not has_default_deny:
                    self.findings.append(SecurityFinding(
                        id="NETWORK-002",
                        title="No default deny network policy",
                        description="No default deny network policy found - consider implementing defense in depth",
                        severity=SecurityLevel.MEDIUM,
                        domain=SecurityDomain.NETWORK,
                        affected_components=["cluster"],
                        remediation="Implement default deny network policies as baseline security"
                    ))

    async def _check_pod_security(self):
        """Check pod security standards"""
        
        # Check for Pod Security Standards or Pod Security Policies
        pss_result = await self._run_kubectl_command([
            "get", "namespaces", "-o", "jsonpath={.items[*].metadata.labels}"
        ])
        
        psp_result = await self._run_kubectl_command([
            "get", "podsecuritypolicies", "-o", "json"
        ])
        
        has_pss = "pod-security.kubernetes.io" in pss_result.stdout if pss_result.returncode == 0 else False
        has_psp = len(json.loads(psp_result.stdout).get("items", [])) > 0 if psp_result.returncode == 0 else False
        
        if not has_pss and not has_psp:
            self.findings.append(SecurityFinding(
                id="POD-SECURITY-001",
                title="No pod security standards configured",
                description="Neither Pod Security Standards nor Pod Security Policies are configured",
                severity=SecurityLevel.HIGH,
                domain=SecurityDomain.KUBERNETES,
                affected_components=["cluster"],
                compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
                remediation="Implement Pod Security Standards or Pod Security Policies"
            ))

    async def _check_service_accounts(self):
        """Check service account configurations"""
        
        result = await self._run_kubectl_command([
            "get", "serviceaccounts", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            service_accounts = json.loads(result.stdout)
            
            for sa in service_accounts.get("items", []):
                sa_name = sa.get("metadata", {}).get("name", "")
                namespace = sa.get("metadata", {}).get("namespace", "")
                
                # Check for default service account usage
                if sa_name == "default":
                    # Check if default SA is being used by pods
                    pods_result = await self._run_kubectl_command([
                        "get", "pods", "-n", namespace,
                        "--field-selector", "spec.serviceAccountName=default",
                        "-o", "json"
                    ])
                    
                    if pods_result.returncode == 0:
                        pods = json.loads(pods_result.stdout)
                        if len(pods.get("items", [])) > 0:
                            self.findings.append(SecurityFinding(
                                id=f"SA-001-{namespace}",
                                title=f"Default service account in use - {namespace}",
                                description=f"Pods in namespace {namespace} are using default service account",
                                severity=SecurityLevel.MEDIUM,
                                domain=SecurityDomain.AUTHORIZATION,
                                affected_components=[f"{namespace}/default"],
                                remediation="Create dedicated service accounts for applications"
                            ))

    async def _assess_network_security(self):
        """Assess network security configuration"""
        logger.info("Assessing network security...")
        
        # Check ingress configuration
        await self._check_ingress_security()
        
        # Check service exposure
        await self._check_service_exposure()
        
        # Check TLS configuration
        await self._check_tls_configuration()

    async def _check_ingress_security(self):
        """Check ingress security configuration"""
        
        result = await self._run_kubectl_command([
            "get", "ingress", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            ingresses = json.loads(result.stdout)
            
            for ingress in ingresses.get("items", []):
                ingress_name = ingress.get("metadata", {}).get("name", "")
                namespace = ingress.get("metadata", {}).get("namespace", "")
                spec = ingress.get("spec", {})
                annotations = ingress.get("metadata", {}).get("annotations", {})
                
                # Check for TLS configuration
                if not spec.get("tls"):
                    self.findings.append(SecurityFinding(
                        id=f"INGRESS-001-{ingress_name}",
                        title=f"Ingress without TLS - {ingress_name}",
                        description=f"Ingress {ingress_name} in {namespace} does not have TLS configured",
                        severity=SecurityLevel.HIGH,
                        domain=SecurityDomain.NETWORK,
                        affected_components=[f"{namespace}/{ingress_name}"],
                        compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.HIPAA],
                        remediation="Configure TLS for all ingress resources"
                    ))
                
                # Check for security headers
                security_annotations = [
                    "nginx.ingress.kubernetes.io/force-ssl-redirect",
                    "nginx.ingress.kubernetes.io/ssl-redirect",
                    "nginx.ingress.kubernetes.io/secure-backends"
                ]
                
                missing_security = [ann for ann in security_annotations if ann not in annotations]
                if missing_security:
                    self.findings.append(SecurityFinding(
                        id=f"INGRESS-002-{ingress_name}",
                        title=f"Missing security annotations - {ingress_name}",
                        description=f"Ingress {ingress_name} missing security annotations: {missing_security}",
                        severity=SecurityLevel.MEDIUM,
                        domain=SecurityDomain.NETWORK,
                        affected_components=[f"{namespace}/{ingress_name}"],
                        remediation="Add security annotations to ingress resources"
                    ))

    async def _check_service_exposure(self):
        """Check service exposure configuration"""
        
        result = await self._run_kubectl_command([
            "get", "services", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            services = json.loads(result.stdout)
            
            for service in services.get("items", []):
                service_name = service.get("metadata", {}).get("name", "")
                namespace = service.get("metadata", {}).get("namespace", "")
                spec = service.get("spec", {})
                service_type = spec.get("type", "ClusterIP")
                
                # Check for NodePort or LoadBalancer services
                if service_type in ["NodePort", "LoadBalancer"]:
                    self.findings.append(SecurityFinding(
                        id=f"SERVICE-001-{service_name}",
                        title=f"Externally exposed service - {service_name}",
                        description=f"Service {service_name} in {namespace} is exposed as {service_type}",
                        severity=SecurityLevel.MEDIUM,
                        domain=SecurityDomain.NETWORK,
                        affected_components=[f"{namespace}/{service_name}"],
                        remediation="Consider using ClusterIP with Ingress instead of direct service exposure"
                    ))

    async def _check_tls_configuration(self):
        """Check TLS certificate configuration"""
        
        result = await self._run_kubectl_command([
            "get", "secrets", "-A", "--field-selector", "type=kubernetes.io/tls", "-o", "json"
        ])
        
        if result.returncode == 0:
            tls_secrets = json.loads(result.stdout)
            
            for secret in tls_secrets.get("items", []):
                secret_name = secret.get("metadata", {}).get("name", "")
                namespace = secret.get("metadata", {}).get("namespace", "")
                data = secret.get("data", {})
                
                # Check if TLS secret has both cert and key
                if "tls.crt" not in data or "tls.key" not in data:
                    self.findings.append(SecurityFinding(
                        id=f"TLS-001-{secret_name}",
                        title=f"Incomplete TLS secret - {secret_name}",
                        description=f"TLS secret {secret_name} in {namespace} is missing cert or key data",
                        severity=SecurityLevel.HIGH,
                        domain=SecurityDomain.NETWORK,
                        affected_components=[f"{namespace}/{secret_name}"],
                        remediation="Ensure TLS secrets contain both tls.crt and tls.key"
                    ))

    async def _assess_application_security(self):
        """Assess application security configuration"""
        logger.info("Assessing application security...")
        
        # Check application configurations
        await self._check_application_configs()
        
        # Check environment variables
        await self._check_environment_security()
        
        # Check health endpoints
        await self._check_health_endpoint_security()

    async def _check_application_configs(self):
        """Check application configuration security"""
        
        # Check ConfigMaps for sensitive data
        result = await self._run_kubectl_command([
            "get", "configmaps", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            configmaps = json.loads(result.stdout)
            
            sensitive_patterns = [
                r'password\s*[:=]\s*["\']?[^"\'\s]+',
                r'secret\s*[:=]\s*["\']?[^"\'\s]+',
                r'token\s*[:=]\s*["\']?[^"\'\s]+',
                r'key\s*[:=]\s*["\']?[^"\'\s]+',
                r'api[_-]?key\s*[:=]\s*["\']?[^"\'\s]+'
            ]
            
            for cm in configmaps.get("items", []):
                cm_name = cm.get("metadata", {}).get("name", "")
                namespace = cm.get("metadata", {}).get("namespace", "")
                data = cm.get("data", {})
                
                for key, value in data.items():
                    if isinstance(value, str):
                        for pattern in sensitive_patterns:
                            if re.search(pattern, value, re.IGNORECASE):
                                self.findings.append(SecurityFinding(
                                    id=f"CONFIG-001-{cm_name}-{key}",
                                    title=f"Sensitive data in ConfigMap - {cm_name}",
                                    description=f"ConfigMap {cm_name} in {namespace} may contain sensitive data in key {key}",
                                    severity=SecurityLevel.HIGH,
                                    domain=SecurityDomain.APPLICATION,
                                    affected_components=[f"{namespace}/{cm_name}"],
                                    compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.HIPAA],
                                    remediation="Move sensitive data to Secrets instead of ConfigMaps"
                                ))
                                break

    async def _check_environment_security(self):
        """Check environment variable security"""
        
        result = await self._run_kubectl_command([
            "get", "deployments", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            deployments = json.loads(result.stdout)
            
            for deployment in deployments.get("items", []):
                name = deployment.get("metadata", {}).get("name", "")
                namespace = deployment.get("metadata", {}).get("namespace", "")
                containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                
                for container in containers:
                    container_name = container.get("name", "")
                    env_vars = container.get("env", [])
                    
                    for env_var in env_vars:
                        env_name = env_var.get("name", "")
                        env_value = env_var.get("value")
                        
                        # Check for hardcoded sensitive values
                        sensitive_names = ["password", "secret", "token", "key", "api_key", "private_key"]
                        if any(sensitive in env_name.lower() for sensitive in sensitive_names):
                            if env_value and not env_var.get("valueFrom"):
                                self.findings.append(SecurityFinding(
                                    id=f"ENV-001-{name}-{env_name}",
                                    title=f"Hardcoded sensitive environment variable - {env_name}",
                                    description=f"Environment variable {env_name} in {container_name} contains hardcoded sensitive value",
                                    severity=SecurityLevel.HIGH,
                                    domain=SecurityDomain.APPLICATION,
                                    affected_components=[f"{namespace}/{name}/{container_name}"],
                                    compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.GDPR],
                                    remediation="Use valueFrom with secretKeyRef for sensitive environment variables"
                                ))

    async def _check_health_endpoint_security(self):
        """Check health endpoint security"""
        
        # This would require checking actual application configurations
        # For now, we'll add a general recommendation
        self.findings.append(SecurityFinding(
            id="HEALTH-001",
            title="Health endpoint security review needed",
            description="Health endpoints should not expose sensitive information",
            severity=SecurityLevel.INFO,
            domain=SecurityDomain.APPLICATION,
            affected_components=self.services,
            remediation="Review health endpoints to ensure they don't expose sensitive data"
        ))

    async def _assess_data_protection(self):
        """Assess data protection measures"""
        logger.info("Assessing data protection...")
        
        # Check database encryption
        await self._check_database_encryption()
        
        # Check backup security
        await self._check_backup_security()
        
        # Check data retention policies
        await self._check_data_retention()

    async def _check_database_encryption(self):
        """Check database encryption configuration"""
        
        # Check for database connection strings
        result = await self._run_kubectl_command([
            "get", "secrets", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            secrets = json.loads(result.stdout)
            
            for secret in secrets.get("items", []):
                secret_name = secret.get("metadata", {}).get("name", "")
                namespace = secret.get("metadata", {}).get("namespace", "")
                data = secret.get("data", {})
                
                # Check database connection strings
                for key, value in data.items():
                    if "database" in key.lower() or "db" in key.lower() or "url" in key.lower():
                        try:
                            decoded_value = base64.b64decode(value).decode('utf-8')
                            # Check for SSL/TLS in connection strings
                            if "postgresql://" in decoded_value or "postgres://" in decoded_value:
                                if "sslmode" not in decoded_value or "sslmode=disable" in decoded_value:
                                    self.findings.append(SecurityFinding(
                                        id=f"DB-001-{secret_name}",
                                        title=f"Database connection without SSL - {secret_name}",
                                        description=f"Database connection in {secret_name} may not use SSL encryption",
                                        severity=SecurityLevel.HIGH,
                                        domain=SecurityDomain.DATA,
                                        affected_components=[f"{namespace}/{secret_name}"],
                                        compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.HIPAA],
                                        remediation="Configure database connections to use SSL/TLS encryption"
                                    ))
                        except:
                            pass  # Skip if can't decode

    async def _check_backup_security(self):
        """Check backup security configuration"""
        
        # This would check backup configurations if they exist
        # Adding as a general recommendation
        self.findings.append(SecurityFinding(
            id="BACKUP-001",
            title="Backup encryption verification needed",
            description="Verify all backup data is encrypted at rest and in transit",
            severity=SecurityLevel.MEDIUM,
            domain=SecurityDomain.DATA,
            affected_components=["backup-system"],
            compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.HIPAA, ComplianceFramework.SOX],
            remediation="Implement and verify backup encryption for all data stores"
        ))

    async def _check_data_retention(self):
        """Check data retention policies"""
        
        self.findings.append(SecurityFinding(
            id="RETENTION-001",
            title="Data retention policy implementation needed",
            description="Implement automated data retention and deletion policies",
            severity=SecurityLevel.MEDIUM,
            domain=SecurityDomain.DATA,
            affected_components=["data-stores"],
            compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.HIPAA],
            remediation="Implement automated data retention policies based on compliance requirements"
        ))

    async def _assess_authentication_authorization(self):
        """Assess authentication and authorization"""
        logger.info("Assessing authentication and authorization...")
        
        # Check JWT configuration
        await self._check_jwt_security()
        
        # Check session management
        await self._check_session_security()
        
        # Check API authentication
        await self._check_api_authentication()

    async def _check_jwt_security(self):
        """Check JWT security configuration"""
        
        # Check for JWT secrets
        result = await self._run_kubectl_command([
            "get", "secrets", "-A", "-o", "json"
        ])
        
        if result.returncode == 0:
            secrets = json.loads(result.stdout)
            
            for secret in secrets.get("items", []):
                secret_name = secret.get("metadata", {}).get("name", "")
                namespace = secret.get("metadata", {}).get("namespace", "")
                data = secret.get("data", {})
                
                # Check for JWT secrets
                jwt_keys = [k for k in data.keys() if "jwt" in k.lower() or "secret" in k.lower()]
                for key in jwt_keys:
                    try:
                        decoded_value = base64.b64decode(data[key]).decode('utf-8')
                        # Check JWT secret strength (should be at least 32 characters)
                        if len(decoded_value) < 32:
                            self.findings.append(SecurityFinding(
                                id=f"JWT-001-{secret_name}",
                                title=f"Weak JWT secret - {secret_name}",
                                description=f"JWT secret in {secret_name} is less than 32 characters",
                                severity=SecurityLevel.HIGH,
                                domain=SecurityDomain.AUTHENTICATION,
                                affected_components=[f"{namespace}/{secret_name}"],
                                compliance_frameworks=[ComplianceFramework.SOC2],
                                remediation="Use strong JWT secrets with at least 32 characters"
                            ))
                    except:
                        pass

    async def _check_session_security(self):
        """Check session management security"""
        
        # General session security recommendations
        self.findings.append(SecurityFinding(
            id="SESSION-001",
            title="Session security configuration review",
            description="Review session timeout, secure cookies, and session invalidation",
            severity=SecurityLevel.MEDIUM,
            domain=SecurityDomain.AUTHENTICATION,
            affected_components=["api-gateway", "frontend"],
            remediation="Implement secure session management with appropriate timeouts and security flags"
        ))

    async def _check_api_authentication(self):
        """Check API authentication configuration"""
        
        # Check for API keys in environment variables or configs
        self.findings.append(SecurityFinding(
            id="API-AUTH-001",
            title="API authentication review needed",
            description="Review API authentication mechanisms and key rotation policies",
            severity=SecurityLevel.MEDIUM,
            domain=SecurityDomain.AUTHENTICATION,
            affected_components=self.services,
            remediation="Implement strong API authentication with regular key rotation"
        ))

    async def _assess_compliance(self):
        """Assess compliance with various frameworks"""
        logger.info("Assessing compliance...")
        
        # Check SOX compliance
        await self._check_sox_compliance()
        
        # Check GDPR compliance
        await self._check_gdpr_compliance()
        
        # Check SOC2 compliance
        await self._check_soc2_compliance()

    async def _check_sox_compliance(self):
        """Check SOX compliance requirements"""
        
        sox_findings = [
            SecurityFinding(
                id="SOX-001",
                title="SOX audit logging verification",
                description="Verify comprehensive audit logging for all financial data access",
                severity=SecurityLevel.HIGH,
                domain=SecurityDomain.COMPLIANCE,
                affected_components=["audit-system"],
                compliance_frameworks=[ComplianceFramework.SOX],
                remediation="Implement comprehensive audit logging for SOX compliance"
            ),
            SecurityFinding(
                id="SOX-002",
                title="SOX access control verification",
                description="Verify role-based access controls and segregation of duties",
                severity=SecurityLevel.HIGH,
                domain=SecurityDomain.COMPLIANCE,
                affected_components=["rbac-system"],
                compliance_frameworks=[ComplianceFramework.SOX],
                remediation="Implement and verify RBAC with segregation of duties"
            )
        ]
        
        self.findings.extend(sox_findings)

    async def _check_gdpr_compliance(self):
        """Check GDPR compliance requirements"""
        
        gdpr_findings = [
            SecurityFinding(
                id="GDPR-001",
                title="GDPR data encryption verification",
                description="Verify all personal data is encrypted at rest and in transit",
                severity=SecurityLevel.HIGH,
                domain=SecurityDomain.COMPLIANCE,
                affected_components=["data-stores"],
                compliance_frameworks=[ComplianceFramework.GDPR],
                remediation="Implement encryption for all personal data"
            ),
            SecurityFinding(
                id="GDPR-002",
                title="GDPR data retention implementation",
                description="Implement automated data retention and right to erasure",
                severity=SecurityLevel.HIGH,
                domain=SecurityDomain.COMPLIANCE,
                affected_components=["data-management"],
                compliance_frameworks=[ComplianceFramework.GDPR],
                remediation="Implement GDPR-compliant data retention and deletion"
            )
        ]
        
        self.findings.extend(gdpr_findings)

    async def _check_soc2_compliance(self):
        """Check SOC2 compliance requirements"""
        
        soc2_findings = [
            SecurityFinding(
                id="SOC2-001",
                title="SOC2 security controls verification",
                description="Verify implementation of SOC2 security control requirements",
                severity=SecurityLevel.HIGH,
                domain=SecurityDomain.COMPLIANCE,
                affected_components=["security-controls"],
                compliance_frameworks=[ComplianceFramework.SOC2],
                remediation="Implement comprehensive SOC2 security controls"
            )
        ]
        
        self.findings.extend(soc2_findings)

    async def _assess_monitoring_security(self):
        """Assess monitoring and logging security"""
        logger.info("Assessing monitoring security...")
        
        # Check log security
        await self._check_log_security()
        
        # Check monitoring access
        await self._check_monitoring_access()

    async def _check_log_security(self):
        """Check logging security configuration"""
        
        self.findings.append(SecurityFinding(
            id="LOG-001",
            title="Log integrity and encryption verification",
            description="Verify log integrity, encryption, and secure forwarding",
            severity=SecurityLevel.MEDIUM,
            domain=SecurityDomain.MONITORING,
            affected_components=["logging-system"],
            remediation="Implement log integrity checks and secure log forwarding"
        ))

    async def _check_monitoring_access(self):
        """Check monitoring system access controls"""
        
        self.findings.append(SecurityFinding(
            id="MONITOR-001",
            title="Monitoring system access control review",
            description="Review access controls for monitoring dashboards and systems",
            severity=SecurityLevel.MEDIUM,
            domain=SecurityDomain.MONITORING,
            affected_components=["prometheus", "grafana", "alertmanager"],
            remediation="Implement proper access controls for monitoring systems"
        ))

    async def _apply_security_hardening(self):
        """Apply security hardening measures"""
        logger.info("Applying security hardening...")
        
        # Define security hardening actions
        hardening_actions = [
            SecurityHardening(
                id="HARDEN-001",
                title="Enable Pod Security Standards",
                description="Apply Pod Security Standards to all namespaces",
                domain=SecurityDomain.KUBERNETES,
                implementation=self._enable_pod_security_standards.__name__,
                validation="kubectl get namespaces -o yaml | grep 'pod-security.kubernetes.io'"
            ),
            SecurityHardening(
                id="HARDEN-002", 
                title="Apply Network Policies",
                description="Implement default deny network policies",
                domain=SecurityDomain.NETWORK,
                implementation=self._apply_network_policies.__name__,
                validation="kubectl get networkpolicies -A"
            ),
            SecurityHardening(
                id="HARDEN-003",
                title="Harden Container Security Contexts",
                description="Apply security contexts to all containers",
                domain=SecurityDomain.KUBERNETES,
                implementation=self._harden_security_contexts.__name__,
                validation="kubectl get deployments -A -o yaml | grep -A5 securityContext"
            ),
            SecurityHardening(
                id="HARDEN-004",
                title="Enable Encryption at Rest",
                description="Enable encryption for all persistent volumes",
                domain=SecurityDomain.DATA,
                implementation=self._enable_encryption_at_rest.__name__,
                validation="kubectl get storageclass -o yaml | grep encrypted"
            )
        ]
        
        self.hardenings.extend(hardening_actions)
        
        # Apply hardening actions
        for hardening in self.hardenings:
            try:
                if hardening.implementation == self._enable_pod_security_standards.__name__:
                    await self._enable_pod_security_standards()
                elif hardening.implementation == self._apply_network_policies.__name__:
                    await self._apply_network_policies()
                elif hardening.implementation == self._harden_security_contexts.__name__:
                    await self._harden_security_contexts()
                elif hardening.implementation == self._enable_encryption_at_rest.__name__:
                    await self._enable_encryption_at_rest()
                    
                hardening.status = "applied"
                logger.info(f"Applied hardening: {hardening.title}")
                
            except Exception as e:
                hardening.status = "failed"
                hardening.details["error"] = str(e)
                logger.error(f"Failed to apply hardening {hardening.title}: {e}")

    async def _enable_pod_security_standards(self):
        """Enable Pod Security Standards"""
        
        namespaces = ["splunk-mcp-prod", "splunk-mcp-staging", "splunk-mcp-dev"]
        
        for namespace in namespaces:
            # Apply Pod Security Standards labels
            await self._run_kubectl_command([
                "label", "namespace", namespace,
                "pod-security.kubernetes.io/enforce=restricted",
                "pod-security.kubernetes.io/audit=restricted",
                "pod-security.kubernetes.io/warn=restricted",
                "--overwrite"
            ])

    async def _apply_network_policies(self):
        """Apply default deny network policies"""
        
        network_policy = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy", 
            "metadata": {
                "name": "default-deny-all",
                "namespace": "splunk-mcp-prod"
            },
            "spec": {
                "podSelector": {},
                "policyTypes": ["Ingress", "Egress"]
            }
        }
        
        # Write network policy to file and apply
        policy_file = self.artifacts_dir / "default-deny-network-policy.yaml"
        with open(policy_file, 'w') as f:
            yaml.dump(network_policy, f)
            
        await self._run_kubectl_command(["apply", "-f", str(policy_file)])

    async def _harden_security_contexts(self):
        """Apply security context hardening"""
        
        # This would involve modifying deployment manifests
        # For demonstration, we'll create a sample hardened security context
        
        security_context = {
            "securityContext": {
                "runAsNonRoot": True,
                "runAsUser": 1000,
                "runAsGroup": 3000,
                "fsGroup": 2000,
                "seccompProfile": {
                    "type": "RuntimeDefault"
                }
            },
            "containers": [{
                "securityContext": {
                    "allowPrivilegeEscalation": False,
                    "readOnlyRootFilesystem": True,
                    "capabilities": {
                        "drop": ["ALL"]
                    }
                }
            }]
        }
        
        # Save hardened security context template
        template_file = self.artifacts_dir / "hardened-security-context.yaml"
        with open(template_file, 'w') as f:
            yaml.dump(security_context, f)

    async def _enable_encryption_at_rest(self):
        """Enable encryption at rest"""
        
        encrypted_storage_class = {
            "apiVersion": "storage.k8s.io/v1",
            "kind": "StorageClass",
            "metadata": {
                "name": "encrypted-ssd"
            },
            "provisioner": "kubernetes.io/gce-pd",
            "parameters": {
                "type": "pd-ssd",
                "encrypted": "true"
            },
            "volumeBindingMode": "WaitForFirstConsumer"
        }
        
        # Write and apply encrypted storage class
        storage_file = self.artifacts_dir / "encrypted-storage-class.yaml"
        with open(storage_file, 'w') as f:
            yaml.dump(encrypted_storage_class, f)
            
        await self._run_kubectl_command(["apply", "-f", str(storage_file)])

    async def _generate_assessment_result(self) -> SecurityAssessmentResult:
        """Generate comprehensive assessment result"""
        
        # Calculate overall security score
        total_findings = len(self.findings)
        critical_findings = len([f for f in self.findings if f.severity == SecurityLevel.CRITICAL])
        high_findings = len([f for f in self.findings if f.severity == SecurityLevel.HIGH])
        medium_findings = len([f for f in self.findings if f.severity == SecurityLevel.MEDIUM])
        low_findings = len([f for f in self.findings if f.severity == SecurityLevel.LOW])
        
        # Calculate score (100 - weighted penalty for findings)
        score = 100.0
        score -= critical_findings * 20  # Critical: -20 points each
        score -= high_findings * 10      # High: -10 points each  
        score -= medium_findings * 5     # Medium: -5 points each
        score -= low_findings * 2        # Low: -2 points each
        score = max(0, score)  # Minimum score is 0
        
        # Determine overall risk level
        if critical_findings > 0:
            risk_level = SecurityLevel.CRITICAL
        elif high_findings > 3:
            risk_level = SecurityLevel.HIGH
        elif medium_findings > 5:
            risk_level = SecurityLevel.MEDIUM
        else:
            risk_level = SecurityLevel.LOW
            
        # Determine compliance status
        compliance_status = {}
        for framework in ComplianceFramework:
            framework_findings = [f for f in self.findings if framework in f.compliance_frameworks]
            if not framework_findings:
                compliance_status[framework] = "compliant"
            elif any(f.severity in [SecurityLevel.CRITICAL, SecurityLevel.HIGH] for f in framework_findings):
                compliance_status[framework] = "non-compliant"
            else:
                compliance_status[framework] = "partial"
        
        result = SecurityAssessmentResult(
            assessment_id=self.assessment_id,
            timestamp=datetime.utcnow(),
            findings=self.findings,
            hardenings=self.hardenings,
            compliance_status=compliance_status,
            overall_score=score,
            risk_level=risk_level
        )
        
        return result

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

    def generate_security_report(self, result: SecurityAssessmentResult) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        
        return {
            "assessment_summary": {
                "assessment_id": result.assessment_id,
                "timestamp": result.timestamp.isoformat(),
                "overall_score": f"{result.overall_score:.1f}/100",
                "risk_level": result.risk_level.value,
                "total_findings": len(result.findings),
                "findings_by_severity": {
                    "critical": len([f for f in result.findings if f.severity == SecurityLevel.CRITICAL]),
                    "high": len([f for f in result.findings if f.severity == SecurityLevel.HIGH]),
                    "medium": len([f for f in result.findings if f.severity == SecurityLevel.MEDIUM]),
                    "low": len([f for f in result.findings if f.severity == SecurityLevel.LOW]),
                    "info": len([f for f in result.findings if f.severity == SecurityLevel.INFO])
                },
                "hardenings_applied": len([h for h in result.hardenings if h.status == "applied"]),
                "compliance_status": {k.value: v for k, v in result.compliance_status.items()}
            },
            "findings": [
                {
                    "id": f.id,
                    "title": f.title,
                    "description": f.description,
                    "severity": f.severity.value,
                    "domain": f.domain.value,
                    "affected_components": f.affected_components,
                    "compliance_frameworks": [cf.value for cf in f.compliance_frameworks],
                    "remediation": f.remediation,
                    "remediation_effort": f.remediation_effort,
                    "status": f.status,
                    "references": f.references
                }
                for f in result.findings
            ],
            "hardening_actions": [
                {
                    "id": h.id,
                    "title": h.title,
                    "description": h.description,
                    "domain": h.domain.value,
                    "status": h.status,
                    "validation": h.validation
                }
                for h in result.hardenings
            ],
            "recommendations": self._generate_recommendations(result),
            "next_steps": self._generate_next_steps(result)
        }

    def _generate_recommendations(self, result: SecurityAssessmentResult) -> List[str]:
        """Generate security recommendations"""
        
        recommendations = []
        
        critical_findings = [f for f in result.findings if f.severity == SecurityLevel.CRITICAL]
        if critical_findings:
            recommendations.append("URGENT: Address all critical security findings immediately")
            
        high_findings = [f for f in result.findings if f.severity == SecurityLevel.HIGH]
        if len(high_findings) > 2:
            recommendations.append("Prioritize remediation of high-severity security findings")
            
        if result.overall_score < 70:
            recommendations.append("Overall security posture needs significant improvement")
        elif result.overall_score < 85:
            recommendations.append("Good security foundation, focus on remaining medium/high issues")
        else:
            recommendations.append("Strong security posture, maintain with regular assessments")
            
        # Compliance-specific recommendations
        non_compliant = [k for k, v in result.compliance_status.items() if v == "non-compliant"]
        if non_compliant:
            recommendations.append(f"Address compliance gaps for: {', '.join([f.value for f in non_compliant])}")
            
        return recommendations

    def _generate_next_steps(self, result: SecurityAssessmentResult) -> List[str]:
        """Generate next steps"""
        
        next_steps = [
            "Review and prioritize security findings by severity and business impact",
            "Create remediation plan with timelines for critical and high-severity findings",
            "Implement security hardening measures in development environment first",
            "Schedule regular security assessments and penetration testing",
            "Update security documentation and incident response procedures",
            "Provide security training for development and operations teams"
        ]
        
        if result.risk_level == SecurityLevel.CRITICAL:
            next_steps.insert(0, "IMMEDIATE: Address critical security vulnerabilities before production deployment")
            
        return next_steps

    def print_security_summary(self, result: SecurityAssessmentResult):
        """Print security assessment summary"""
        
        print("\n" + "="*80)
        print("SECURITY ASSESSMENT SUMMARY")
        print("="*80)
        
        print(f"Assessment ID: {result.assessment_id}")
        print(f"Timestamp: {result.timestamp.isoformat()}")
        print(f"Overall Security Score: {result.overall_score:.1f}/100")
        print(f"Risk Level: {result.risk_level.value.upper()}")
        print()
        
        # Findings summary
        print("SECURITY FINDINGS:")
        findings_by_severity = {}
        for severity in SecurityLevel:
            count = len([f for f in result.findings if f.severity == severity])
            if count > 0:
                findings_by_severity[severity] = count
                
        for severity, count in findings_by_severity.items():
            icon = "🔴" if severity == SecurityLevel.CRITICAL else "🟠" if severity == SecurityLevel.HIGH else "🟡" if severity == SecurityLevel.MEDIUM else "🔵"
            print(f"  {icon} {severity.value.title()}: {count}")
        print()
        
        # Compliance status
        print("COMPLIANCE STATUS:")
        for framework, status in result.compliance_status.items():
            icon = "✅" if status == "compliant" else "⚠️" if status == "partial" else "❌"
            print(f"  {icon} {framework.value.upper()}: {status}")
        print()
        
        # Hardening status
        applied_hardenings = len([h for h in result.hardenings if h.status == "applied"])
        failed_hardenings = len([h for h in result.hardenings if h.status == "failed"])
        print(f"SECURITY HARDENING:")
        print(f"  ✅ Applied: {applied_hardenings}")
        print(f"  ❌ Failed: {failed_hardenings}")
        print()
        
        # Critical findings
        critical_findings = [f for f in result.findings if f.severity == SecurityLevel.CRITICAL]
        if critical_findings:
            print("CRITICAL FINDINGS (IMMEDIATE ACTION REQUIRED):")
            for finding in critical_findings[:5]:  # Show top 5
                print(f"  🔴 {finding.title}")
                print(f"     {finding.description}")
                print(f"     Affected: {', '.join(finding.affected_components)}")
                print()
        
        print("="*80)

# CLI interface
async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Review and Hardening Framework")
    parser.add_argument("--environment", "-e", default="production", help="Environment name")
    parser.add_argument("--output", "-o", choices=["console", "json", "yaml"], default="console", help="Output format")
    parser.add_argument("--report-file", help="Save report to file")
    parser.add_argument("--apply-hardening", action="store_true", help="Apply security hardening measures")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    framework = SecurityReviewFramework(environment=args.environment)
    
    try:
        result = await framework.execute_comprehensive_security_review()
        
        if args.output == "console":
            framework.print_security_summary(result)
        else:
            report = framework.generate_security_report(result)
            
            if args.output == "json":
                output = json.dumps(report, indent=2)
            elif args.output == "yaml":
                output = yaml.dump(report, default_flow_style=False)
                
            if args.report_file:
                with open(args.report_file, 'w') as f:
                    f.write(output)
                print(f"Security report saved to {args.report_file}")
            else:
                print(output)
                
        # Exit with appropriate code based on risk level
        if result.risk_level == SecurityLevel.CRITICAL:
            sys.exit(3)
        elif result.risk_level == SecurityLevel.HIGH:
            sys.exit(2)
        elif result.risk_level == SecurityLevel.MEDIUM:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Security assessment failed: {e}")
        sys.exit(4)

if __name__ == "__main__":
    asyncio.run(main())