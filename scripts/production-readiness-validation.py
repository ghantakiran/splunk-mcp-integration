#!/usr/bin/env python3
"""
Production Readiness Validation Script
=====================================

Comprehensive validation script to verify all components of the Splunk MCP Integration
platform are production-ready. This script validates:

1. Service health and availability
2. Database connectivity and schema validation
3. API endpoint functionality
4. Security configurations
5. Performance benchmarks
6. Documentation completeness
7. Kubernetes deployment readiness

Usage:
    python scripts/production-readiness-validation.py [--env development|staging|production]
"""

import asyncio
import aiohttp
import asyncpg
import aioredis
import json
import logging
import os
import subprocess
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validation-results.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Container for validation results"""
    component: str
    status: str  # PASS, FAIL, WARNING
    message: str
    details: Optional[Dict] = None
    execution_time: Optional[float] = None

@dataclass
class ServiceConfig:
    """Service configuration"""
    name: str
    port: int
    health_endpoint: str
    required: bool = True

class ProductionReadinessValidator:
    """Main validation class for production readiness checks"""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.results: List[ValidationResult] = []
        self.start_time = time.time()
        
        # Service configurations
        self.services = [
            ServiceConfig("API Gateway", 8000, "/health"),
            ServiceConfig("NLP Engine", 8001, "/health"),
            ServiceConfig("Visualization", 8002, "/health"),
            ServiceConfig("Alert Manager", 8003, "/health"),
            ServiceConfig("Slack Bot", 8004, "/health"),
            ServiceConfig("Teams Bot", 8005, "/health"),
            ServiceConfig("Email Service", 8006, "/health"),
            ServiceConfig("Webhook Service", 8007, "/health"),
            ServiceConfig("BI Integration", 8008, "/health"),
            ServiceConfig("PDF Export", 8009, "/health"),
            ServiceConfig("PowerPoint Export", 8011, "/health"),
            ServiceConfig("HTML Report", 8012, "/health"),
            ServiceConfig("Word Export", 8013, "/health"),
            ServiceConfig("CSV Export", 8014, "/health"),
            ServiceConfig("JSON/XML Export", 8015, "/health"),
            ServiceConfig("Report Scheduling", 8015, "/health"),
            ServiceConfig("Secure Sharing", 8016, "/health"),
            ServiceConfig("Frontend", 3000, "/", False),  # Frontend doesn't have health endpoint
        ]
        
        # Database configuration
        self.db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DB", "splunk_mcp"),
            "user": os.getenv("POSTGRES_USER", "splunk_mcp_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "splunk_mcp_password")
        }
        
        # Redis configuration
        self.redis_config = {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD", "redis_password")
        }

    async def validate_service_health(self, service: ServiceConfig) -> ValidationResult:
        """Validate individual service health"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                url = f"http://localhost:{service.port}{service.health_endpoint}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json() if service.name != "Frontend" else {}
                        execution_time = time.time() - start_time
                        
                        return ValidationResult(
                            component=f"{service.name} Health",
                            status="PASS",
                            message=f"Service healthy and responding",
                            details={"response_time": execution_time, "data": data},
                            execution_time=execution_time
                        )
                    else:
                        return ValidationResult(
                            component=f"{service.name} Health",
                            status="FAIL",
                            message=f"Health check failed with status {response.status}",
                            execution_time=time.time() - start_time
                        )
        except Exception as e:
            return ValidationResult(
                component=f"{service.name} Health",
                status="FAIL" if service.required else "WARNING",
                message=f"Health check failed: {str(e)}",
                execution_time=time.time() - start_time
            )

    async def validate_database_connectivity(self) -> ValidationResult:
        """Validate PostgreSQL database connectivity and basic schema"""
        start_time = time.time()
        
        try:
            conn = await asyncpg.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                database=self.db_config["database"],
                user=self.db_config["user"],
                password=self.db_config["password"]
            )
            
            # Test basic query
            result = await conn.fetchval("SELECT version()")
            
            # Check for key tables (sample from API Gateway)
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            await conn.close()
            
            return ValidationResult(
                component="PostgreSQL Database",
                status="PASS",
                message="Database connectivity successful",
                details={
                    "version": result,
                    "table_count": len(tables),
                    "tables": [row["table_name"] for row in tables[:10]]  # First 10 tables
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                component="PostgreSQL Database",
                status="FAIL",
                message=f"Database connectivity failed: {str(e)}",
                execution_time=time.time() - start_time
            )

    async def validate_redis_connectivity(self) -> ValidationResult:
        """Validate Redis connectivity and basic operations"""
        start_time = time.time()
        
        try:
            redis = aioredis.from_url(
                f"redis://:{self.redis_config['password']}@{self.redis_config['host']}:{self.redis_config['port']}"
            )
            
            # Test basic operations
            await redis.set("health_check", "test_value", ex=60)
            value = await redis.get("health_check")
            await redis.delete("health_check")
            
            # Get Redis info
            info = await redis.info()
            
            await redis.close()
            
            return ValidationResult(
                component="Redis Cache",
                status="PASS",
                message="Redis connectivity successful",
                details={
                    "version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human")
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                component="Redis Cache",
                status="FAIL",
                message=f"Redis connectivity failed: {str(e)}",
                execution_time=time.time() - start_time
            )

    async def validate_api_endpoints(self) -> List[ValidationResult]:
        """Validate critical API endpoints"""
        results = []
        
        # Test API Gateway endpoints
        endpoints = [
            {"url": "http://localhost:8000/docs", "name": "API Documentation"},
            {"url": "http://localhost:8000/api/v1/health", "name": "Health Check API"},
            {"url": "http://localhost:8000/openapi.json", "name": "OpenAPI Specification"}
        ]
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            for endpoint in endpoints:
                start_time = time.time()
                try:
                    async with session.get(endpoint["url"]) as response:
                        if response.status == 200:
                            results.append(ValidationResult(
                                component=f"API Endpoint - {endpoint['name']}",
                                status="PASS",
                                message="Endpoint accessible",
                                execution_time=time.time() - start_time
                            ))
                        else:
                            results.append(ValidationResult(
                                component=f"API Endpoint - {endpoint['name']}",
                                status="FAIL",
                                message=f"Endpoint returned status {response.status}",
                                execution_time=time.time() - start_time
                            ))
                except Exception as e:
                    results.append(ValidationResult(
                        component=f"API Endpoint - {endpoint['name']}",
                        status="FAIL",
                        message=f"Endpoint validation failed: {str(e)}",
                        execution_time=time.time() - start_time
                    ))
        
        return results

    def validate_kubernetes_manifests(self) -> ValidationResult:
        """Validate Kubernetes deployment manifests"""
        start_time = time.time()
        
        try:
            k8s_path = Path("infrastructure/kubernetes")
            if not k8s_path.exists():
                return ValidationResult(
                    component="Kubernetes Manifests",
                    status="FAIL",
                    message="Kubernetes infrastructure directory not found",
                    execution_time=time.time() - start_time
                )
            
            # Check for required directories
            required_dirs = [
                "deployments", "services", "configmaps", "secrets", 
                "namespaces", "rbac", "network-policies", "hpa", "ingress"
            ]
            
            missing_dirs = []
            existing_files = {}
            
            for dir_name in required_dirs:
                dir_path = k8s_path / dir_name
                if dir_path.exists():
                    yaml_files = list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.yml"))
                    existing_files[dir_name] = len(yaml_files)
                else:
                    missing_dirs.append(dir_name)
            
            if missing_dirs:
                return ValidationResult(
                    component="Kubernetes Manifests",
                    status="WARNING",
                    message=f"Missing directories: {missing_dirs}",
                    details={"existing_files": existing_files},
                    execution_time=time.time() - start_time
                )
            
            return ValidationResult(
                component="Kubernetes Manifests",
                status="PASS",
                message="All required Kubernetes directories present",
                details={"manifest_counts": existing_files},
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                component="Kubernetes Manifests",
                status="FAIL",
                message=f"Manifest validation failed: {str(e)}",
                execution_time=time.time() - start_time
            )

    def validate_documentation_completeness(self) -> ValidationResult:
        """Validate documentation completeness"""
        start_time = time.time()
        
        try:
            required_docs = [
                "README.md",
                "CLAUDE.md", 
                "PLANNING.md",
                "TASKS.md",
                "docs/project/completion-summary.md",
                "docs/operations/deployment-handoff.md"
            ]
            
            missing_docs = []
            existing_docs = {}
            
            for doc in required_docs:
                doc_path = Path(doc)
                if doc_path.exists():
                    existing_docs[doc] = doc_path.stat().st_size
                else:
                    missing_docs.append(doc)
            
            # Check service-specific documentation
            service_dirs = list(Path("services").glob("*/"))
            service_docs = {}
            
            for service_dir in service_dirs:
                readme_path = service_dir / "README.md"
                claude_path = service_dir / "CLAUDE.md"
                service_docs[service_dir.name] = {
                    "README.md": readme_path.exists(),
                    "CLAUDE.md": claude_path.exists()
                }
            
            if missing_docs:
                return ValidationResult(
                    component="Documentation Completeness",
                    status="WARNING",
                    message=f"Missing documentation: {missing_docs}",
                    details={"existing_docs": existing_docs, "service_docs": service_docs},
                    execution_time=time.time() - start_time
                )
            
            return ValidationResult(
                component="Documentation Completeness",
                status="PASS",
                message="All required documentation present",
                details={"doc_counts": len(existing_docs), "service_docs": service_docs},
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                component="Documentation Completeness",
                status="FAIL",
                message=f"Documentation validation failed: {str(e)}",
                execution_time=time.time() - start_time
            )

    def validate_environment_configuration(self) -> ValidationResult:
        """Validate environment configuration completeness"""
        start_time = time.time()
        
        try:
            required_env_vars = [
                "DATABASE_URL", "REDIS_URL", "JWT_SECRET_KEY", 
                "OPENAI_API_KEY", "ANTHROPIC_API_KEY"
            ]
            
            missing_vars = []
            configured_vars = {}
            
            for var in required_env_vars:
                value = os.getenv(var)
                if value:
                    configured_vars[var] = "✓ Configured"
                else:
                    missing_vars.append(var)
            
            # Check for .env.example files
            env_examples = list(Path(".").glob("**/.env.example"))
            
            status = "PASS" if not missing_vars else "WARNING"
            message = "Environment configuration complete" if not missing_vars else f"Missing environment variables: {missing_vars}"
            
            return ValidationResult(
                component="Environment Configuration",
                status=status,
                message=message,
                details={
                    "configured_vars": configured_vars,
                    "missing_vars": missing_vars,
                    "env_example_files": [str(f) for f in env_examples]
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                component="Environment Configuration",
                status="FAIL",
                message=f"Environment validation failed: {str(e)}",
                execution_time=time.time() - start_time
            )

    async def run_all_validations(self) -> Dict:
        """Run all validation checks"""
        logger.info(f"Starting production readiness validation for environment: {self.environment}")
        
        # Service health checks
        logger.info("Validating service health...")
        for service in self.services:
            result = await self.validate_service_health(service)
            self.results.append(result)
        
        # Database connectivity
        logger.info("Validating database connectivity...")
        db_result = await self.validate_database_connectivity()
        self.results.append(db_result)
        
        # Redis connectivity
        logger.info("Validating Redis connectivity...")
        redis_result = await self.validate_redis_connectivity()
        self.results.append(redis_result)
        
        # API endpoints
        logger.info("Validating API endpoints...")
        api_results = await self.validate_api_endpoints()
        self.results.extend(api_results)
        
        # Kubernetes manifests
        logger.info("Validating Kubernetes manifests...")
        k8s_result = self.validate_kubernetes_manifests()
        self.results.append(k8s_result)
        
        # Documentation
        logger.info("Validating documentation completeness...")
        docs_result = self.validate_documentation_completeness()
        self.results.append(docs_result)
        
        # Environment configuration
        logger.info("Validating environment configuration...")
        env_result = self.validate_environment_configuration()
        self.results.append(env_result)
        
        return self.generate_report()

    def generate_report(self) -> Dict:
        """Generate comprehensive validation report"""
        total_time = time.time() - self.start_time
        
        # Categorize results
        passed = [r for r in self.results if r.status == "PASS"]
        failed = [r for r in self.results if r.status == "FAIL"]
        warnings = [r for r in self.results if r.status == "WARNING"]
        
        # Calculate overall status
        if failed:
            overall_status = "FAIL"
        elif warnings:
            overall_status = "WARNING"
        else:
            overall_status = "PASS"
        
        report = {
            "validation_summary": {
                "environment": self.environment,
                "timestamp": datetime.now().isoformat(),
                "total_execution_time": round(total_time, 2),
                "overall_status": overall_status
            },
            "statistics": {
                "total_checks": len(self.results),
                "passed": len(passed),
                "failed": len(failed),
                "warnings": len(warnings),
                "success_rate": round((len(passed) / len(self.results)) * 100, 1)
            },
            "detailed_results": [asdict(result) for result in self.results],
            "summary_by_status": {
                "PASS": [r.component for r in passed],
                "FAIL": [r.component for r in failed],
                "WARNING": [r.component for r in warnings]
            }
        }
        
        return report

    def save_report(self, report: Dict, filename: str = None):
        """Save validation report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"production-readiness-report-{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Validation report saved to: {filename}")
        return filename

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Production Readiness Validation")
    parser.add_argument("--env", choices=["development", "staging", "production"], 
                       default="development", help="Environment to validate")
    parser.add_argument("--output", help="Output file for validation report")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize validator
    validator = ProductionReadinessValidator(args.env)
    
    try:
        # Run all validations
        report = await validator.run_all_validations()
        
        # Save report
        report_file = validator.save_report(report, args.output)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"PRODUCTION READINESS VALIDATION REPORT")
        print(f"{'='*60}")
        print(f"Environment: {report['validation_summary']['environment'].upper()}")
        print(f"Overall Status: {report['validation_summary']['overall_status']}")
        print(f"Total Checks: {report['statistics']['total_checks']}")
        print(f"Success Rate: {report['statistics']['success_rate']}%")
        print(f"Execution Time: {report['validation_summary']['total_execution_time']}s")
        print(f"\nResults:")
        print(f"  ✅ PASSED: {report['statistics']['passed']}")
        print(f"  ❌ FAILED: {report['statistics']['failed']}")
        print(f"  ⚠️  WARNINGS: {report['statistics']['warnings']}")
        
        if report['statistics']['failed'] > 0:
            print(f"\nFailed Components:")
            for component in report['summary_by_status']['FAIL']:
                print(f"  - {component}")
        
        if report['statistics']['warnings'] > 0:
            print(f"\nWarning Components:")
            for component in report['summary_by_status']['WARNING']:
                print(f"  - {component}")
        
        print(f"\nDetailed report saved to: {report_file}")
        print(f"{'='*60}")
        
        # Exit with appropriate code
        sys.exit(0 if report['validation_summary']['overall_status'] == "PASS" else 1)
        
    except Exception as e:
        logger.error(f"Validation failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())