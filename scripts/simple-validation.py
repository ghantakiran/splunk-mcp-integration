#!/usr/bin/env python3
"""
Simple Production Readiness Validation
Basic checks for development environment
"""

import os
import sys
import json
import subprocess
import requests
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_project_structure():
    """Check if essential project files exist"""
    required_files = [
        'CLAUDE.md',
        'PLANNING.md', 
        'TASKS.md',
        'docker-compose.yml',
        'Makefile'
    ]
    
    results = {}
    for file in required_files:
        if os.path.exists(file):
            results[file] = {'status': 'PASS', 'message': f'{file} exists'}
        else:
            results[file] = {'status': 'FAIL', 'message': f'{file} missing'}
    
    failed = [k for k, v in results.items() if v['status'] == 'FAIL']
    return {
        'status': 'FAIL' if failed else 'PASS',
        'message': f'Project structure check: {len(failed)} failures',
        'details': results
    }

def check_documentation():
    """Check if documentation is comprehensive"""
    doc_dirs = ['docs/project', 'docs/operations', 'docs/user']
    results = {}
    
    for dir_path in doc_dirs:
        if os.path.exists(dir_path):
            file_count = len([f for f in os.listdir(dir_path) if f.endswith('.md')])
            results[dir_path] = {
                'status': 'PASS',
                'message': f'{dir_path} contains {file_count} documentation files',
                'details': f'{file_count} files'
            }
        else:
            results[dir_path] = {
                'status': 'FAIL',
                'message': f'{dir_path} directory missing',
                'details': 'Documentation incomplete'
            }
    
    failed = [k for k, v in results.items() if v['status'] == 'FAIL']
    return {
        'status': 'FAIL' if failed else 'PASS',
        'message': f'Documentation check: {len(failed)} failures',
        'details': results
    }

def check_services_directory():
    """Check if all services have been implemented"""
    services_dir = 'services'
    if not os.path.exists(services_dir):
        return {
            'status': 'FAIL',
            'message': 'Services directory not found',
            'details': 'No microservices implemented'
        }
    
    service_dirs = [d for d in os.listdir(services_dir) if os.path.isdir(os.path.join(services_dir, d))]
    
    expected_services = [
        'api-gateway', 'nlp-engine', 'visualization', 'alert-manager',
        'slack-bot', 'teams-bot', 'email-service', 'webhook-service',
        'pdf-export', 'powerpoint-export', 'word-export', 'csv-export',
        'secure-sharing', 'report-scheduling'
    ]
    
    results = {}
    for service in expected_services:
        service_path = os.path.join(services_dir, service)
        if os.path.exists(service_path):
            # Check for essential files
            has_dockerfile = os.path.exists(os.path.join(service_path, 'Dockerfile'))
            has_requirements = os.path.exists(os.path.join(service_path, 'requirements.txt'))
            has_main = os.path.exists(os.path.join(service_path, 'app', 'main.py'))
            
            if has_dockerfile and has_requirements and has_main:
                results[service] = {
                    'status': 'PASS',
                    'message': f'{service} service implemented',
                    'details': 'Has Dockerfile, requirements.txt, and main.py'
                }
            else:
                results[service] = {
                    'status': 'WARN',
                    'message': f'{service} service incomplete',
                    'details': f'Missing: {", ".join([f for f, exists in [("Dockerfile", has_dockerfile), ("requirements.txt", has_requirements), ("main.py", has_main)] if not exists])}'
                }
        else:
            results[service] = {
                'status': 'FAIL',
                'message': f'{service} service not found',
                'details': 'Service directory missing'
            }
    
    failed = [k for k, v in results.items() if v['status'] == 'FAIL']
    warnings = [k for k, v in results.items() if v['status'] == 'WARN']
    
    if failed:
        status = 'FAIL'
    elif warnings:
        status = 'WARN'
    else:
        status = 'PASS'
    
    return {
        'status': status,
        'message': f'Services check: {len(failed)} failures, {len(warnings)} warnings',
        'details': results
    }

def check_frontend():
    """Check if frontend is implemented"""
    frontend_dir = 'frontend'
    if not os.path.exists(frontend_dir):
        return {
            'status': 'FAIL',
            'message': 'Frontend directory not found',
            'details': 'No frontend implementation'
        }
    
    required_files = ['package.json', 'src/App.js', 'public/index.html']
    results = {}
    
    for file in required_files:
        file_path = os.path.join(frontend_dir, file)
        if os.path.exists(file_path):
            results[file] = {'status': 'PASS', 'message': f'{file} exists'}
        else:
            results[file] = {'status': 'FAIL', 'message': f'{file} missing'}
    
    failed = [k for k, v in results.items() if v['status'] == 'FAIL']
    return {
        'status': 'FAIL' if failed else 'PASS',
        'message': f'Frontend check: {len(failed)} failures',
        'details': results
    }

def check_infrastructure_configs():
    """Check infrastructure configuration files"""
    infra_files = [
        'infrastructure/docker/docker-compose.yml',
        'infrastructure/kubernetes/README.md'
    ]
    
    results = {}
    for file in infra_files:
        if os.path.exists(file):
            results[file] = {'status': 'PASS', 'message': f'{file} exists'}
        else:
            results[file] = {'status': 'WARN', 'message': f'{file} missing (optional)'}
    
    warnings = [k for k, v in results.items() if v['status'] == 'WARN']
    return {
        'status': 'WARN' if warnings else 'PASS',
        'message': f'Infrastructure configs: {len(warnings)} missing optional files',
        'details': results
    }

def run_validation():
    """Run all validation checks"""
    logger.info("Starting simple production readiness validation...")
    
    checks = [
        ('project_structure', check_project_structure),
        ('documentation', check_documentation),
        ('services', check_services_directory),
        ('frontend', check_frontend),
        ('infrastructure_configs', check_infrastructure_configs)
    ]
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'validation_type': 'simple',
        'environment': 'development',
        'checks': {},
        'summary': {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
    }
    
    for check_name, check_function in checks:
        logger.info(f"Running check: {check_name}")
        try:
            result = check_function()
            results['checks'][check_name] = result
            
            results['summary']['total'] += 1
            if result['status'] == 'PASS':
                results['summary']['passed'] += 1
            elif result['status'] == 'FAIL':
                results['summary']['failed'] += 1
            elif result['status'] == 'WARN':
                results['summary']['warnings'] += 1
                
        except Exception as e:
            logger.error(f"Check {check_name} failed with exception: {e}")
            results['checks'][check_name] = {
                'status': 'FAIL',
                'message': f'Check failed with exception',
                'details': str(e)
            }
            results['summary']['total'] += 1
            results['summary']['failed'] += 1
    
    # Determine overall status
    if results['summary']['failed'] > 0:
        results['overall_status'] = 'NOT_READY'
    elif results['summary']['warnings'] > 0:
        results['overall_status'] = 'READY_WITH_WARNINGS'
    else:
        results['overall_status'] = 'PRODUCTION_READY'
    
    return results

def main():
    """Main function"""
    try:
        results = run_validation()
        
        # Save results
        output_file = f'simple-validation-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("SIMPLE PRODUCTION READINESS VALIDATION")
        print("="*60)
        print(f"Overall Status: {results['overall_status']}")
        print(f"Total Checks: {results['summary']['total']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Failed: {results['summary']['failed']}")
        print(f"Warnings: {results['summary']['warnings']}")
        print()
        
        for check_name, result in results['checks'].items():
            status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
            print(f"{status_icon} {check_name}: {result['message']}")
        
        print(f"\nReport saved to: {output_file}")
        print("="*60)
        
        # Exit with appropriate code
        if results['overall_status'] == 'NOT_READY':
            sys.exit(1)
        elif results['overall_status'] == 'READY_WITH_WARNINGS':
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()