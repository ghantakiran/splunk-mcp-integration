#!/usr/bin/env python3
"""
Environment Configuration Validation Script
===========================================

This script validates environment configuration files to ensure all required
variables are present and properly formatted for the Splunk MCP Integration platform.

Usage:
    python scripts/validate-env-config.py [--env-file .env] [--strict]

Arguments:
    --env-file: Path to environment file to validate (default: .env)
    --strict: Enable strict validation mode
    --verbose: Enable verbose output
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass
class ValidationResult:
    """Container for validation results"""
    variable: str
    status: str  # PASS, FAIL, WARNING, MISSING
    message: str
    value: Optional[str] = None

class EnvironmentValidator:
    """Main environment configuration validator"""
    
    def __init__(self, env_file: str = ".env", strict: bool = False, verbose: bool = False):
        self.env_file = env_file
        self.strict = strict
        self.verbose = verbose
        self.results: List[ValidationResult] = []
        self.env_vars: Dict[str, str] = {}
        
        # Required variables by category
        self.required_vars = {
            "core": [
                "ENVIRONMENT",
                "DATABASE_URL",
                "REDIS_URL",
                "JWT_SECRET_KEY"
            ],
            "database": [
                "POSTGRES_HOST",
                "POSTGRES_PORT", 
                "POSTGRES_DB",
                "POSTGRES_USER",
                "POSTGRES_PASSWORD"
            ],
            "redis": [
                "REDIS_HOST",
                "REDIS_PORT",
                "REDIS_PASSWORD"
            ],
            "splunk": [
                "SPLUNK_HOST",
                "SPLUNK_PORT",
                "SPLUNK_USERNAME",
                "SPLUNK_PASSWORD",
                "SPLUNK_SCHEME"
            ],
            "ai_services": [
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY"
            ]
        }
        
        # Optional but recommended variables
        self.recommended_vars = [
            "LOG_LEVEL",
            "MAX_WORKERS",
            "CORS_ORIGINS",
            "RATE_LIMIT_ENABLED"
        ]
        
        # Environment-specific requirements
        self.production_required = [
            "SSL_CERT_PATH",
            "SSL_KEY_PATH", 
            "BACKUP_ENABLED",
            "METRICS_ENABLED"
        ]
    
    def load_env_file(self) -> bool:
        """Load environment file and parse variables"""
        try:
            if not Path(self.env_file).exists():
                self.results.append(ValidationResult(
                    variable="FILE",
                    status="FAIL",
                    message=f"Environment file '{self.env_file}' not found"
                ))
                return False
            
            with open(self.env_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse variable assignment
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        # Handle variable substitution
                        value = self._substitute_variables(value)
                        
                        self.env_vars[key] = value
            
            self.results.append(ValidationResult(
                variable="FILE",
                status="PASS",
                message=f"Successfully loaded {len(self.env_vars)} variables from {self.env_file}"
            ))
            return True
            
        except Exception as e:
            self.results.append(ValidationResult(
                variable="FILE",
                status="FAIL",
                message=f"Error loading environment file: {str(e)}"
            ))
            return False
    
    def _substitute_variables(self, value: str) -> str:
        """Simple variable substitution for ${VAR} patterns"""
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            return self.env_vars.get(var_name, match.group(0))
        
        return re.sub(pattern, replace_var, value)
    
    def validate_required_variables(self) -> None:
        """Validate that all required variables are present"""
        environment = self.env_vars.get("ENVIRONMENT", "development")
        
        for category, variables in self.required_vars.items():
            for var in variables:
                if var not in self.env_vars:
                    self.results.append(ValidationResult(
                        variable=var,
                        status="MISSING",
                        message=f"Required variable missing (category: {category})"
                    ))
                elif not self.env_vars[var]:
                    self.results.append(ValidationResult(
                        variable=var,
                        status="FAIL",
                        message="Required variable is empty"
                    ))
                else:
                    self.results.append(ValidationResult(
                        variable=var,
                        status="PASS",
                        message="Required variable present",
                        value="***" if "PASSWORD" in var or "KEY" in var or "SECRET" in var else self.env_vars[var]
                    ))
        
        # Check production-specific requirements
        if environment == "production":
            for var in self.production_required:
                if var not in self.env_vars:
                    self.results.append(ValidationResult(
                        variable=var,
                        status="WARNING",
                        message="Production environment missing recommended variable"
                    ))
    
    def validate_recommended_variables(self) -> None:
        """Validate recommended but optional variables"""
        for var in self.recommended_vars:
            if var not in self.env_vars:
                self.results.append(ValidationResult(
                    variable=var,
                    status="WARNING",
                    message="Recommended variable missing (using defaults)"
                ))
    
    def validate_database_url(self) -> None:
        """Validate database URL format"""
        db_url = self.env_vars.get("DATABASE_URL")
        if not db_url:
            return
        
        try:
            parsed = urlparse(db_url)
            
            if parsed.scheme != "postgresql":
                self.results.append(ValidationResult(
                    variable="DATABASE_URL",
                    status="FAIL",
                    message=f"Invalid database scheme: {parsed.scheme} (expected: postgresql)"
                ))
                return
            
            if not parsed.hostname:
                self.results.append(ValidationResult(
                    variable="DATABASE_URL",
                    status="FAIL",
                    message="Database URL missing hostname"
                ))
                return
            
            if not parsed.port:
                self.results.append(ValidationResult(
                    variable="DATABASE_URL",
                    status="WARNING",
                    message="Database URL missing port (will use default 5432)"
                ))
            
            self.results.append(ValidationResult(
                variable="DATABASE_URL",
                status="PASS",
                message="Database URL format valid"
            ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                variable="DATABASE_URL",
                status="FAIL",
                message=f"Invalid database URL format: {str(e)}"
            ))
    
    def validate_redis_url(self) -> None:
        """Validate Redis URL format"""
        redis_url = self.env_vars.get("REDIS_URL")
        if not redis_url:
            return
        
        try:
            parsed = urlparse(redis_url)
            
            if parsed.scheme != "redis":
                self.results.append(ValidationResult(
                    variable="REDIS_URL",
                    status="FAIL",
                    message=f"Invalid Redis scheme: {parsed.scheme} (expected: redis)"
                ))
                return
            
            if not parsed.hostname:
                self.results.append(ValidationResult(
                    variable="REDIS_URL",
                    status="FAIL",
                    message="Redis URL missing hostname"
                ))
                return
            
            self.results.append(ValidationResult(
                variable="REDIS_URL",
                status="PASS",
                message="Redis URL format valid"
            ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                variable="REDIS_URL",
                status="FAIL",
                message=f"Invalid Redis URL format: {str(e)}"
            ))
    
    def validate_jwt_secret(self) -> None:
        """Validate JWT secret key strength"""
        jwt_secret = self.env_vars.get("JWT_SECRET_KEY")
        if not jwt_secret:
            return
        
        if len(jwt_secret) < 32:
            self.results.append(ValidationResult(
                variable="JWT_SECRET_KEY",
                status="FAIL",
                message=f"JWT secret too short: {len(jwt_secret)} characters (minimum: 32)"
            ))
        elif len(jwt_secret) < 64:
            self.results.append(ValidationResult(
                variable="JWT_SECRET_KEY",
                status="WARNING",
                message=f"JWT secret could be longer: {len(jwt_secret)} characters (recommended: 64+)"
            ))
        else:
            self.results.append(ValidationResult(
                variable="JWT_SECRET_KEY",
                status="PASS",
                message=f"JWT secret length adequate: {len(jwt_secret)} characters"
            ))
    
    def validate_api_keys(self) -> None:
        """Validate AI service API keys format"""
        # OpenAI API key validation
        openai_key = self.env_vars.get("OPENAI_API_KEY")
        if openai_key:
            if not openai_key.startswith("sk-"):
                self.results.append(ValidationResult(
                    variable="OPENAI_API_KEY",
                    status="FAIL",
                    message="OpenAI API key should start with 'sk-'"
                ))
            elif len(openai_key) < 50:
                self.results.append(ValidationResult(
                    variable="OPENAI_API_KEY",
                    status="WARNING",
                    message="OpenAI API key seems too short"
                ))
            else:
                self.results.append(ValidationResult(
                    variable="OPENAI_API_KEY",
                    status="PASS",
                    message="OpenAI API key format looks valid"
                ))
        
        # Anthropic API key validation
        anthropic_key = self.env_vars.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            if len(anthropic_key) < 20:
                self.results.append(ValidationResult(
                    variable="ANTHROPIC_API_KEY",
                    status="WARNING",
                    message="Anthropic API key seems too short"
                ))
            else:
                self.results.append(ValidationResult(
                    variable="ANTHROPIC_API_KEY",
                    status="PASS",
                    message="Anthropic API key format looks valid"
                ))
    
    def validate_ports(self) -> None:
        """Validate port configurations"""
        port_vars = [
            "POSTGRES_PORT", "REDIS_PORT", "SPLUNK_PORT",
            "API_GATEWAY_PORT", "NLP_ENGINE_PORT", "VISUALIZATION_PORT",
            "ALERT_MANAGER_PORT", "FRONTEND_PORT"
        ]
        
        for port_var in port_vars:
            port_value = self.env_vars.get(port_var)
            if port_value:
                try:
                    port = int(port_value)
                    if port < 1 or port > 65535:
                        self.results.append(ValidationResult(
                            variable=port_var,
                            status="FAIL",
                            message=f"Port out of valid range: {port}"
                        ))
                    elif port < 1024 and port_var not in ["POSTGRES_PORT", "REDIS_PORT", "SPLUNK_PORT"]:
                        self.results.append(ValidationResult(
                            variable=port_var,
                            status="WARNING",
                            message=f"Using privileged port: {port}"
                        ))
                    else:
                        self.results.append(ValidationResult(
                            variable=port_var,
                            status="PASS",
                            message=f"Port valid: {port}"
                        ))
                except ValueError:
                    self.results.append(ValidationResult(
                        variable=port_var,
                        status="FAIL",
                        message=f"Invalid port value: {port_value}"
                    ))
    
    def validate_environment_specific(self) -> None:
        """Validate environment-specific settings"""
        environment = self.env_vars.get("ENVIRONMENT", "development")
        
        if environment == "production":
            # Production validations
            debug = self.env_vars.get("DEBUG", "false").lower()
            if debug == "true":
                self.results.append(ValidationResult(
                    variable="DEBUG",
                    status="WARNING",
                    message="DEBUG should be false in production"
                ))
            
            force_https = self.env_vars.get("FORCE_HTTPS", "false").lower()
            if force_https != "true":
                self.results.append(ValidationResult(
                    variable="FORCE_HTTPS",
                    status="WARNING",
                    message="FORCE_HTTPS should be true in production"
                ))
            
            # Check for default passwords
            for var in ["POSTGRES_PASSWORD", "REDIS_PASSWORD"]:
                value = self.env_vars.get(var, "")
                if "change" in value.lower() or "password" in value.lower():
                    self.results.append(ValidationResult(
                        variable=var,
                        status="FAIL",
                        message="Using default/placeholder password in production"
                    ))
        
        elif environment == "development":
            # Development validations
            mock_apis = self.env_vars.get("MOCK_EXTERNAL_APIS", "false").lower()
            if mock_apis == "true":
                self.results.append(ValidationResult(
                    variable="MOCK_EXTERNAL_APIS",
                    status="PASS",
                    message="Mock APIs enabled for development"
                ))
    
    def validate_security_settings(self) -> None:
        """Validate security-related settings"""
        # CORS validation
        cors_origins = self.env_vars.get("CORS_ORIGINS")
        if cors_origins:
            if "*" in cors_origins and self.env_vars.get("ENVIRONMENT") == "production":
                self.results.append(ValidationResult(
                    variable="CORS_ORIGINS",
                    status="WARNING",
                    message="Wildcard CORS origins in production may be insecure"
                ))
        
        # Rate limiting
        rate_limit = self.env_vars.get("RATE_LIMIT_ENABLED", "false").lower()
        if rate_limit != "true" and self.env_vars.get("ENVIRONMENT") == "production":
            self.results.append(ValidationResult(
                variable="RATE_LIMIT_ENABLED",
                status="WARNING",
                message="Rate limiting should be enabled in production"
            ))
    
    def run_all_validations(self) -> Dict:
        """Run all validation checks"""
        print(f"🔍 Validating environment configuration: {self.env_file}")
        print("=" * 60)
        
        # Load environment file
        if not self.load_env_file():
            return self.generate_report()
        
        # Run all validations
        self.validate_required_variables()
        self.validate_recommended_variables()
        self.validate_database_url()
        self.validate_redis_url()
        self.validate_jwt_secret()
        self.validate_api_keys()
        self.validate_ports()
        self.validate_environment_specific()
        self.validate_security_settings()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive validation report"""
        # Categorize results
        passed = [r for r in self.results if r.status == "PASS"]
        failed = [r for r in self.results if r.status == "FAIL"]
        warnings = [r for r in self.results if r.status == "WARNING"]
        missing = [r for r in self.results if r.status == "MISSING"]
        
        # Calculate overall status
        if failed or missing:
            overall_status = "FAIL"
        elif warnings:
            overall_status = "WARNING"
        else:
            overall_status = "PASS"
        
        report = {
            "validation_summary": {
                "env_file": self.env_file,
                "overall_status": overall_status,
                "total_variables": len(self.env_vars)
            },
            "statistics": {
                "total_checks": len(self.results),
                "passed": len(passed),
                "failed": len(failed),
                "warnings": len(warnings),
                "missing": len(missing)
            },
            "results_by_status": {
                "PASS": [{"variable": r.variable, "message": r.message} for r in passed],
                "FAIL": [{"variable": r.variable, "message": r.message} for r in failed],
                "WARNING": [{"variable": r.variable, "message": r.message} for r in warnings],
                "MISSING": [{"variable": r.variable, "message": r.message} for r in missing]
            }
        }
        
        return report
    
    def print_results(self, report: Dict) -> None:
        """Print validation results to console"""
        stats = report["statistics"]
        summary = report["validation_summary"]
        
        print(f"\n{'='*60}")
        print(f"ENVIRONMENT CONFIGURATION VALIDATION REPORT")
        print(f"{'='*60}")
        print(f"File: {summary['env_file']}")
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Variables Loaded: {summary['total_variables']}")
        print(f"Total Checks: {stats['total_checks']}")
        print(f"\nResults:")
        print(f"  ✅ PASSED: {stats['passed']}")
        print(f"  ❌ FAILED: {stats['failed']}")
        print(f"  ⚠️  WARNINGS: {stats['warnings']}")
        print(f"  📋 MISSING: {stats['missing']}")
        
        # Show details if verbose or if there are issues
        if self.verbose or stats['failed'] > 0 or stats['missing'] > 0:
            print(f"\n📋 Detailed Results:")
            
            for status in ["FAIL", "MISSING", "WARNING"]:
                items = report["results_by_status"][status]
                if items:
                    status_icon = {"FAIL": "❌", "MISSING": "📋", "WARNING": "⚠️"}[status]
                    print(f"\n{status_icon} {status}:")
                    for item in items:
                        print(f"  - {item['variable']}: {item['message']}")
        
        print(f"\n{'='*60}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Environment Configuration Validator")
    parser.add_argument("--env-file", default=".env", help="Environment file to validate")
    parser.add_argument("--strict", action="store_true", help="Enable strict validation mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = EnvironmentValidator(args.env_file, args.strict, args.verbose)
    
    try:
        # Run validation
        report = validator.run_all_validations()
        
        # Print results
        validator.print_results(report)
        
        # Exit with appropriate code
        exit_code = 0 if report["validation_summary"]["overall_status"] == "PASS" else 1
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"❌ Validation failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()