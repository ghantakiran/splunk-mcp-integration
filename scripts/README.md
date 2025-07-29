# Project Scripts

This directory contains utility scripts for the Splunk MCP Integration project.

## Available Scripts

### Production Readiness Validation

#### production-readiness-validation.py
Comprehensive production readiness validation for all environments.

**Usage:**
```bash
python3 scripts/production-readiness-validation.py --env development
python3 scripts/production-readiness-validation.py --env production --verbose
```

**Features:**
- Environment-specific validation (development, staging, production)
- Kubernetes cluster validation for production environments
- Docker container validation for development
- Service health checks and endpoint validation
- Database and Redis connectivity tests
- Security and compliance validation
- Comprehensive JSON reporting

#### simple-validation.py
Quick project structure and implementation verification.

**Usage:**
```bash
python3 scripts/simple-validation.py
```

**Features:**
- Project structure validation
- Service implementation status
- Documentation completeness checks
- Frontend implementation verification
- Basic infrastructure configuration validation

#### run-validation.sh
Automated validation runner with environment management.

**Usage:**
```bash
./scripts/run-validation.sh --env development
./scripts/run-validation.sh --env production --verbose
```

**Features:**
- Automatic service startup for development
- Environment-specific configuration
- Report generation and summarization
- Colored output and status indicators

#### validation-config.yaml
Configuration file for validation parameters and thresholds.

### Performance Testing

#### production-performance-testing.py
Load testing and performance validation for production readiness.

#### performance-test-config.yaml
Configuration for performance testing parameters.

### Security & Deployment

#### production-security-hardening.sh
Security hardening script for production environments.

#### production-deployment.sh
Automated production deployment script.

### Monitoring & Analysis

#### monitor_claude_files.py
Monitors CLAUDE.md files across the project to ensure they stay within manageable token limits.

**Usage:**
```bash
python scripts/monitor_claude_files.py
```

**Features:**
- Scans all CLAUDE.md files in the project
- Estimates token count using character-based heuristics
- Provides color-coded status (OK, WARNING, CRITICAL)
- Shows file statistics (lines, words, characters, tokens)
- Summarizes total project documentation size

**Token Limits:**
- **OK**: < 20,000 tokens (green)
- **WARNING**: 20,000-25,000 tokens (yellow)
- **CRITICAL**: > 25,000 tokens (red)

**Files Monitored:**
- `CLAUDE.md` (main project file)
- `services/*/CLAUDE.md` (service-specific files)
- `frontend/CLAUDE.md` (frontend documentation)
- `infrastructure/CLAUDE.md` (infrastructure documentation)

#### test_coverage_analysis.py
Analyzes test coverage across all services.

### Environment Validation

#### validate-env-config.py
Validates environment configuration and secrets.

## Adding New Scripts

When adding new scripts:

1. Create the script file with appropriate permissions
2. Add a shebang line (`#!/usr/bin/env python3`)
3. Include proper documentation and error handling
4. Update this README with script description
5. Test the script thoroughly

## Development Guidelines

- Use Python 3.9+ for all scripts
- Include proper error handling and logging
- Follow project coding standards
- Add type hints where appropriate
- Include docstrings for functions and classes