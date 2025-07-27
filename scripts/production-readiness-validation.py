#!/usr/bin/env python3
"""
Production Readiness Validation Script
Comprehensive validation for Splunk MCP Integration Platform production deployment
"""

import os
import sys
import json
import time
import subprocess
import requests
import yaml
from datetime import datetime
from typing import Dict, List, Tuple, Any
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'validation-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class ProductionValidator:
    """Main validation class for production readiness checks"""
    
    def __init__(self, config_file: str = None):
        self.config = self.load_config(config_file)
        self.namespace = self.config.get('namespace', 'splunk-mcp-prod')
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }
        
    def load_config(self, config_file: str) -> Dict:
        """Load validation configuration"""
        default_config = {
            'namespace': 'splunk-mcp-prod',
            'domain': 'splunk-mcp.your-domain.com',
            'monitoring_namespace': 'monitoring',
            'timeout': 300,
            'required_services': [
                'api-gateway', 'nlp-engine', 'visualization', 'alert-manager',
                'slack-bot', 'teams-bot', 'email-service', 'webhook-service',
                'pdf-export', 'powerpoint-export', 'word-export', 'csv-export',
                'secure-sharing', 'report-scheduling', 'frontend'
            ],
            'required_infrastructure': ['postgresql', 'redis'],
            'required_replicas': {
                'api-gateway': 3,
                'nlp-engine': 2,
                'visualization': 2,
                'alert-manager': 2
            },
            'health_endpoints': {
                'api-gateway': 8000,
                'nlp-engine': 8001,
                'visualization': 8002,
                'alert-manager': 8003
            }
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
                
        return default_config
    
    def run_kubectl(self, args: List[str]) -> Tuple[bool, str]:
        """Execute kubectl command and return result"""
        try:
            cmd = ['kubectl'] + args
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.config['timeout']
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def check_kubernetes_access(self) -> Dict:
        """Validate Kubernetes cluster access"""
        logger.info("Checking Kubernetes cluster access...")
        
        # Check cluster info
        success, output = self.run_kubectl(['cluster-info'])
        if not success:
            return {
                'status': 'FAIL',
                'message': 'Cannot access Kubernetes cluster',
                'details': output
            }
        
        # Check namespace exists
        success, output = self.run_kubectl(['get', 'namespace', self.namespace])
        if not success:
            return {
                'status': 'FAIL',
                'message': f'Namespace {self.namespace} not found',
                'details': output
            }
        
        # Check permissions
        success, output = self.run_kubectl(['auth', 'can-i', 'get', 'pods', '-n', self.namespace])
        if not success:
            return {
                'status': 'FAIL',
                'message': 'Insufficient permissions',
                'details': output
            }
        
        return {
            'status': 'PASS',
            'message': 'Kubernetes access verified',
            'details': 'Cluster accessible, namespace exists, permissions verified'
        }
    
    def check_infrastructure_services(self) -> Dict:
        """Check core infrastructure services (PostgreSQL, Redis)"""
        logger.info("Checking infrastructure services...")
        
        results = {}
        
        for service in self.config['required_infrastructure']:
            success, output = self.run_kubectl([
                'get', 'pods', '-n', self.namespace, 
                '-l', f'app={service}', '--no-headers'
            ])
            
            if not success:
                results[service] = {
                    'status': 'FAIL',
                    'message': f'Cannot get {service} pods',
                    'details': output
                }
                continue
            
            if not output:
                results[service] = {
                    'status': 'FAIL',
                    'message': f'No {service} pods found',
                    'details': 'Service not deployed'
                }
                continue
            
            # Check if pods are running
            running_pods = [line for line in output.split('\n') if 'Running' in line]
            total_pods = len(output.split('\n'))
            
            if len(running_pods) == total_pods and total_pods > 0:
                results[service] = {
                    'status': 'PASS',
                    'message': f'{service} is healthy',
                    'details': f'{len(running_pods)}/{total_pods} pods running'
                }
            else:
                results[service] = {
                    'status': 'FAIL',
                    'message': f'{service} has issues',
                    'details': f'{len(running_pods)}/{total_pods} pods running'
                }
        
        # Overall status
        failed_services = [k for k, v in results.items() if v['status'] == 'FAIL']
        if failed_services:
            return {
                'status': 'FAIL',
                'message': f'Infrastructure services failed: {", ".join(failed_services)}',
                'details': results
            }
        
        return {
            'status': 'PASS',
            'message': 'All infrastructure services healthy',
            'details': results
        }
    
    def check_application_services(self) -> Dict:
        """Check application services deployment and health"""
        logger.info("Checking application services...")
        
        results = {}
        
        for service in self.config['required_services']:
            # Check deployment exists
            success, output = self.run_kubectl([
                'get', 'deployment', service, '-n', self.namespace, '--no-headers'
            ])
            
            if not success:
                results[service] = {
                    'status': 'FAIL',
                    'message': f'{service} deployment not found',
                    'details': output
                }
                continue
            
            # Check pod status
            success, output = self.run_kubectl([
                'get', 'pods', '-n', self.namespace,
                '-l', f'app={service}', '--no-headers'
            ])
            
            if not success or not output:
                results[service] = {
                    'status': 'FAIL',
                    'message': f'{service} pods not found',
                    'details': output
                }
                continue
            
            # Analyze pod status
            pod_lines = output.split('\n')
            running_pods = [line for line in pod_lines if 'Running' in line and '1/1' in line]
            total_pods = len(pod_lines)
            
            # Check if meets replica requirements
            required_replicas = self.config['required_replicas'].get(service, 1)
            if len(running_pods) >= required_replicas:
                results[service] = {
                    'status': 'PASS',
                    'message': f'{service} is healthy',
                    'details': f'{len(running_pods)}/{total_pods} pods running (required: {required_replicas})'
                }
            else:
                results[service] = {
                    'status': 'FAIL',
                    'message': f'{service} insufficient replicas',
                    'details': f'{len(running_pods)}/{total_pods} pods running (required: {required_replicas})'
                }
        
        # Overall status
        failed_services = [k for k, v in results.items() if v['status'] == 'FAIL']
        if failed_services:
            return {
                'status': 'FAIL',
                'message': f'Application services failed: {", ".join(failed_services)}',
                'details': results
            }
        
        return {
            'status': 'PASS',
            'message': 'All application services healthy',
            'details': results
        }
    
    def check_health_endpoints(self) -> Dict:
        """Check service health endpoints"""
        logger.info("Checking service health endpoints...")
        
        results = {}
        
        for service, port in self.config['health_endpoints'].items():
            logger.info(f"Testing health endpoint for {service}...")
            
            # Test health endpoint
            success, output = self.run_kubectl([
                'exec', '-n', self.namespace, f'deployment/{service}', '--',
                'wget', '--quiet', '--tries=3', '--timeout=10', '--spider',
                f'http://localhost:{port}/health'
            ])
            
            if success:
                results[service] = {
                    'status': 'PASS',
                    'message': f'{service} health endpoint responding',
                    'details': f'Health check passed on port {port}'
                }
            else:
                results[service] = {
                    'status': 'FAIL',
                    'message': f'{service} health endpoint failed',
                    'details': output
                }
        
        # Overall status
        failed_endpoints = [k for k, v in results.items() if v['status'] == 'FAIL']
        if failed_endpoints:
            return {
                'status': 'FAIL',
                'message': f'Health endpoints failed: {", ".join(failed_endpoints)}',
                'details': results
            }
        
        return {
            'status': 'PASS',
            'message': 'All health endpoints responding',
            'details': results
        }
    
    def check_database_connectivity(self) -> Dict:
        """Check database connectivity and health"""
        logger.info("Checking database connectivity...")
        
        # Test PostgreSQL connectivity
        success, output = self.run_kubectl([
            'exec', '-n', self.namespace, 'deployment/api-gateway', '--',
            'python', '-c',
            'import psycopg2, os; psycopg2.connect(os.environ["DATABASE_URL"]).close(); print("Database OK")'
        ])
        
        if not success:
            return {
                'status': 'FAIL',
                'message': 'Database connectivity failed',
                'details': output
            }
        
        # Test Redis connectivity
        success, output = self.run_kubectl([
            'exec', '-n', self.namespace, 'deployment/api-gateway', '--',
            'python', '-c',
            'import redis, os; redis.from_url(os.environ["REDIS_URL"]).ping(); print("Redis OK")'
        ])
        
        if not success:
            return {
                'status': 'FAIL',
                'message': 'Redis connectivity failed',
                'details': output
            }
        
        return {
            'status': 'PASS',
            'message': 'Database connectivity verified',
            'details': 'PostgreSQL and Redis connections successful'
        }
    
    def check_ssl_certificates(self) -> Dict:
        """Check SSL certificate validity"""
        logger.info("Checking SSL certificates...")
        
        domain = self.config['domain']
        
        try:
            # Check certificate via openssl
            cmd = f'echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null | openssl x509 -noout -dates'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                cert_info = result.stdout
                return {
                    'status': 'PASS',
                    'message': 'SSL certificate is valid',
                    'details': cert_info
                }
            else:
                return {
                    'status': 'FAIL',
                    'message': 'SSL certificate check failed',
                    'details': result.stderr
                }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': 'SSL certificate check error',
                'details': str(e)
            }
    
    def check_external_access(self) -> Dict:
        """Check external access to the platform"""
        logger.info("Checking external access...")
        
        domain = self.config['domain']
        url = f'https://{domain}/health'
        
        try:
            response = requests.get(url, timeout=30, verify=True)
            if response.status_code == 200:
                return {
                    'status': 'PASS',
                    'message': 'External access verified',
                    'details': f'HTTP {response.status_code} from {url}'
                }
            else:
                return {
                    'status': 'FAIL',
                    'message': f'External access failed with HTTP {response.status_code}',
                    'details': response.text
                }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': 'External access error',
                'details': str(e)
            }
    
    def check_monitoring_stack(self) -> Dict:
        """Check monitoring and alerting systems"""
        logger.info("Checking monitoring stack...")
        
        monitoring_ns = self.config['monitoring_namespace']
        components = ['prometheus', 'grafana', 'alertmanager']
        results = {}
        
        for component in components:
            success, output = self.run_kubectl([
                'get', 'pods', '-n', monitoring_ns,
                '-l', f'app.kubernetes.io/name={component}', '--no-headers'
            ])
            
            if success and output:
                running_pods = [line for line in output.split('\n') if 'Running' in line]
                total_pods = len(output.split('\n'))
                
                if len(running_pods) == total_pods:
                    results[component] = {
                        'status': 'PASS',
                        'message': f'{component} is healthy',
                        'details': f'{len(running_pods)} pods running'
                    }
                else:
                    results[component] = {
                        'status': 'FAIL',
                        'message': f'{component} has issues',
                        'details': f'{len(running_pods)}/{total_pods} pods running'
                    }
            else:
                results[component] = {
                    'status': 'FAIL',
                    'message': f'{component} not found',
                    'details': output
                }
        
        # Overall status
        failed_components = [k for k, v in results.items() if v['status'] == 'FAIL']
        if failed_components:
            return {
                'status': 'FAIL',
                'message': f'Monitoring components failed: {", ".join(failed_components)}',
                'details': results
            }
        
        return {
            'status': 'PASS',
            'message': 'Monitoring stack healthy',
            'details': results
        }
    
    def check_secrets_and_config(self) -> Dict:
        """Check required secrets and configuration"""
        logger.info("Checking secrets and configuration...")
        
        required_secrets = ['app-secrets', 'splunk-secrets', 'ai-secrets']
        required_configmaps = ['app-config']
        results = {}
        
        # Check secrets
        for secret in required_secrets:
            success, output = self.run_kubectl([
                'get', 'secret', secret, '-n', self.namespace, '--no-headers'
            ])
            
            if success:
                results[f'secret-{secret}'] = {
                    'status': 'PASS',
                    'message': f'Secret {secret} exists',
                    'details': 'Secret found'
                }
            else:
                results[f'secret-{secret}'] = {
                    'status': 'FAIL',
                    'message': f'Secret {secret} missing',
                    'details': output
                }
        
        # Check configmaps
        for configmap in required_configmaps:
            success, output = self.run_kubectl([
                'get', 'configmap', configmap, '-n', self.namespace, '--no-headers'
            ])
            
            if success:
                results[f'configmap-{configmap}'] = {
                    'status': 'PASS',
                    'message': f'ConfigMap {configmap} exists',
                    'details': 'ConfigMap found'
                }
            else:
                results[f'configmap-{configmap}'] = {
                    'status': 'FAIL',
                    'message': f'ConfigMap {configmap} missing',
                    'details': output
                }
        
        # Overall status
        failed_configs = [k for k, v in results.items() if v['status'] == 'FAIL']
        if failed_configs:
            return {
                'status': 'FAIL',
                'message': f'Configuration failed: {", ".join(failed_configs)}',
                'details': results
            }
        
        return {
            'status': 'PASS',
            'message': 'All secrets and configuration present',
            'details': results
        }
    
    def check_network_policies(self) -> Dict:
        """Check network security policies"""
        logger.info("Checking network policies...")
        
        success, output = self.run_kubectl([
            'get', 'networkpolicy', '-n', self.namespace, '--no-headers'
        ])
        
        if not success:
            return {
                'status': 'FAIL',
                'message': 'Cannot check network policies',
                'details': output
            }
        
        if not output:
            return {
                'status': 'WARN',
                'message': 'No network policies found',
                'details': 'Consider implementing network policies for security'
            }
        
        policy_count = len(output.split('\n'))
        
        return {
            'status': 'PASS',
            'message': f'Network policies configured ({policy_count} policies)',
            'details': output
        }
    
    def check_resource_limits(self) -> Dict:
        """Check resource limits and requests"""
        logger.info("Checking resource limits...")
        
        results = {}
        
        for service in ['api-gateway', 'nlp-engine', 'visualization', 'alert-manager']:
            success, output = self.run_kubectl([
                'get', 'deployment', service, '-n', self.namespace,
                '-o', 'jsonpath={.spec.template.spec.containers[0].resources}'
            ])
            
            if success and output:
                try:
                    resources = json.loads(output) if output != '{}' else {}
                    if 'limits' in resources and 'requests' in resources:
                        results[service] = {
                            'status': 'PASS',
                            'message': f'{service} has resource limits',
                            'details': resources
                        }
                    else:
                        results[service] = {
                            'status': 'WARN',
                            'message': f'{service} missing resource limits',
                            'details': 'Consider adding resource limits'
                        }
                except:
                    results[service] = {
                        'status': 'WARN',
                        'message': f'{service} resource check failed',
                        'details': output
                    }
            else:
                results[service] = {
                    'status': 'FAIL',
                    'message': f'{service} deployment not found',
                    'details': output
                }
        
        # Count warnings and failures
        warnings = sum(1 for v in results.values() if v['status'] == 'WARN')
        failures = sum(1 for v in results.values() if v['status'] == 'FAIL')
        
        if failures > 0:
            status = 'FAIL'
        elif warnings > 0:
            status = 'WARN'
        else:
            status = 'PASS'
        
        return {
            'status': status,
            'message': f'Resource limits check: {failures} failures, {warnings} warnings',
            'details': results
        }
    
    def check_backup_system(self) -> Dict:
        """Check backup system configuration"""
        logger.info("Checking backup system...")
        
        # Check for backup CronJobs
        success, output = self.run_kubectl([
            'get', 'cronjob', '-n', self.namespace, '--no-headers'
        ])
        
        if not success:
            return {
                'status': 'FAIL',
                'message': 'Cannot check backup jobs',
                'details': output
            }
        
        backup_jobs = [line for line in output.split('\n') if 'backup' in line.lower()]
        
        if not backup_jobs:
            return {
                'status': 'WARN',
                'message': 'No backup jobs found',
                'details': 'Consider implementing automated backups'
            }
        
        return {
            'status': 'PASS',
            'message': f'Backup system configured ({len(backup_jobs)} jobs)',
            'details': backup_jobs
        }
    
    def check_autoscaling(self) -> Dict:
        """Check autoscaling configuration"""
        logger.info("Checking autoscaling...")
        
        success, output = self.run_kubectl([
            'get', 'hpa', '-n', self.namespace, '--no-headers'
        ])
        
        if not success:
            return {
                'status': 'FAIL',
                'message': 'Cannot check autoscaling',
                'details': output
            }
        
        if not output:
            return {
                'status': 'WARN',
                'message': 'No HPA configured',
                'details': 'Consider implementing horizontal pod autoscaling'
            }
        
        hpa_count = len(output.split('\n'))
        
        return {
            'status': 'PASS',
            'message': f'Autoscaling configured ({hpa_count} HPAs)',
            'details': output
        }
    
    def run_validation(self) -> Dict:
        """Run all validation checks"""
        logger.info("Starting production readiness validation...")
        
        checks = [
            ('kubernetes_access', self.check_kubernetes_access),
            ('infrastructure_services', self.check_infrastructure_services),
            ('application_services', self.check_application_services),
            ('health_endpoints', self.check_health_endpoints),
            ('database_connectivity', self.check_database_connectivity),
            ('ssl_certificates', self.check_ssl_certificates),
            ('external_access', self.check_external_access),
            ('monitoring_stack', self.check_monitoring_stack),
            ('secrets_and_config', self.check_secrets_and_config),
            ('network_policies', self.check_network_policies),
            ('resource_limits', self.check_resource_limits),
            ('backup_system', self.check_backup_system),
            ('autoscaling', self.check_autoscaling)
        ]
        
        for check_name, check_function in checks:
            logger.info(f"Running check: {check_name}")
            try:
                result = check_function()
                self.results['checks'][check_name] = result
                
                # Update summary
                self.results['summary']['total'] += 1
                if result['status'] == 'PASS':
                    self.results['summary']['passed'] += 1
                elif result['status'] == 'FAIL':
                    self.results['summary']['failed'] += 1
                elif result['status'] == 'WARN':
                    self.results['summary']['warnings'] += 1
                    
            except Exception as e:
                logger.error(f"Check {check_name} failed with exception: {e}")
                self.results['checks'][check_name] = {
                    'status': 'FAIL',
                    'message': f'Check failed with exception',
                    'details': str(e)
                }
                self.results['summary']['total'] += 1
                self.results['summary']['failed'] += 1
        
        # Determine overall status
        if self.results['summary']['failed'] > 0:
            self.results['overall_status'] = 'NOT_READY'
        elif self.results['summary']['warnings'] > 0:
            self.results['overall_status'] = 'READY_WITH_WARNINGS'
        else:
            self.results['overall_status'] = 'PRODUCTION_READY'
        
        return self.results
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate validation report"""
        if not output_file:
            output_file = f'production-validation-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Validation report saved to: {output_file}")
        return output_file
    
    def print_summary(self):
        """Print validation summary to console"""
        print("\n" + "="*60)
        print("PRODUCTION READINESS VALIDATION SUMMARY")
        print("="*60)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Namespace: {self.namespace}")
        print(f"Overall Status: {self.results['overall_status']}")
        print()
        print(f"Total Checks: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        print(f"Warnings: {self.results['summary']['warnings']}")
        print()
        
        # Print detailed results
        for check_name, result in self.results['checks'].items():
            status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
            print(f"{status_icon} {check_name}: {result['message']}")
        
        print("\n" + "="*60)
        
        if self.results['overall_status'] == 'PRODUCTION_READY':
            print("🎉 SYSTEM IS PRODUCTION READY!")
        elif self.results['overall_status'] == 'READY_WITH_WARNINGS':
            print("⚠️  SYSTEM IS READY BUT HAS WARNINGS - REVIEW RECOMMENDED")
        else:
            print("❌ SYSTEM IS NOT PRODUCTION READY - ISSUES MUST BE RESOLVED")
        
        print("="*60)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Validate Splunk MCP Platform production readiness')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--output', '-o', help='Output report file')
    parser.add_argument('--namespace', '-n', help='Kubernetes namespace')
    parser.add_argument('--domain', '-d', help='Platform domain')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create validator
        validator = ProductionValidator(args.config)
        
        # Override config with command line arguments
        if args.namespace:
            validator.namespace = args.namespace
            validator.config['namespace'] = args.namespace
        if args.domain:
            validator.config['domain'] = args.domain
        
        # Run validation
        results = validator.run_validation()
        
        # Generate report
        report_file = validator.generate_report(args.output)
        
        # Print summary
        validator.print_summary()
        
        # Exit with appropriate code
        if results['overall_status'] == 'NOT_READY':
            sys.exit(1)
        elif results['overall_status'] == 'READY_WITH_WARNINGS':
            sys.exit(2)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()