# Credentials Setup Guide

This guide provides step-by-step instructions for setting up all required credentials for the Splunk MCP Integration platform.

## Overview

The platform requires several types of credentials:
- Database credentials (PostgreSQL, Redis)
- Splunk connection credentials
- AI/ML service API keys
- Authentication secrets
- Integration service credentials
- SSL/TLS certificates

## 1. Database Credentials Setup

### PostgreSQL Setup

#### Option A: Using Docker Compose (Development)
```bash
# Database credentials are already configured in docker-compose.yml
# Default credentials (change for production):
POSTGRES_DB=splunk_mcp
POSTGRES_USER=splunk_mcp_user
POSTGRES_PASSWORD=splunk_mcp_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

#### Option B: External PostgreSQL Database
```bash
# For production or external database
export POSTGRES_HOST=your-postgres-server.com
export POSTGRES_PORT=5432
export POSTGRES_DB=splunk_mcp_production
export POSTGRES_USER=splunk_mcp_user
export POSTGRES_PASSWORD=your_secure_password

# Test connection
psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version();"
```

#### Database User Creation (Manual Setup)
```sql
-- Connect as postgres superuser and create application user
CREATE USER splunk_mcp_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE splunk_mcp OWNER splunk_mcp_user;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE splunk_mcp TO splunk_mcp_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO splunk_mcp_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO splunk_mcp_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO splunk_mcp_user;

-- For future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO splunk_mcp_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO splunk_mcp_user;
```

### Redis Setup

#### Option A: Using Docker Compose (Development)
```bash
# Redis credentials in docker-compose.yml
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password
```

#### Option B: External Redis Instance
```bash
# For production Redis setup
export REDIS_HOST=your-redis-server.com
export REDIS_PORT=6379
export REDIS_PASSWORD=your_redis_password

# Test connection
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping
```

#### Redis Security Configuration
```bash
# Redis configuration for production (/etc/redis/redis.conf)
requirepass your_redis_password
bind 127.0.0.1 your-server-ip
port 6379
timeout 0
tcp-keepalive 300
maxmemory 512mb
maxmemory-policy allkeys-lru
```

## 2. AI/ML Service API Keys

### OpenAI API Setup

#### Step 1: Create OpenAI Account
1. Visit https://platform.openai.com/
2. Sign up for an account or log in
3. Navigate to API Keys section
4. Click "Create new secret key"
5. Copy the API key (starts with `sk-`)

#### Step 2: Configure OpenAI Credentials
```bash
# Set environment variable
export OPENAI_API_KEY=sk-your-openai-api-key-here

# Add to .env file
echo "OPENAI_API_KEY=sk-your-openai-api-key-here" >> .env

# Verify API key works
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### Step 3: Set Usage Limits (Optional)
```bash
# Configure usage limits in OpenAI dashboard
# Recommended for production:
# - Monthly usage limit: $100-500 depending on scale
# - Rate limits: 3000 requests per minute
# - Model access: GPT-4, GPT-3.5-turbo
```

### Anthropic Claude API Setup

#### Step 1: Create Anthropic Account
1. Visit https://console.anthropic.com/
2. Sign up for an account
3. Navigate to API Keys section
4. Generate a new API key
5. Copy the API key

#### Step 2: Configure Anthropic Credentials
```bash
# Set environment variable
export ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Add to .env file
echo "ANTHROPIC_API_KEY=your-anthropic-api-key-here" >> .env

# Verify API key works
curl https://api.anthropic.com/v1/messages \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3-sonnet-20240229", "max_tokens": 10, "messages": [{"role": "user", "content": "test"}]}'
```

## 3. JWT Authentication Setup

### Generate JWT Secret Key
```bash
# Generate a secure random key
JWT_SECRET_KEY=$(openssl rand -base64 32)
echo "Generated JWT Secret: $JWT_SECRET_KEY"

# Add to environment
export JWT_SECRET_KEY="$JWT_SECRET_KEY"
echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> .env

# Configure JWT settings
export JWT_ALGORITHM=HS256
export JWT_EXPIRATION_HOURS=1
export JWT_REFRESH_EXPIRATION_DAYS=30
```

### JWT Configuration Options
```bash
# JWT configuration in .env
JWT_SECRET_KEY=your-generated-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=1
JWT_REFRESH_EXPIRATION_DAYS=30
JWT_ISSUER=splunk-mcp-platform
JWT_AUDIENCE=splunk-mcp-users
```

## 4. Integration Service Credentials

### Slack Bot Credentials

#### Step 1: Create Slack App
1. Visit https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Enter app name: "Splunk MCP Bot"
4. Select your workspace
5. Click "Create App"

#### Step 2: Configure Bot Permissions
```bash
# Required OAuth Scopes:
# - app_mentions:read
# - channels:history
# - channels:read
# - chat:write
# - files:write
# - groups:history
# - groups:read
# - im:history
# - im:read
# - im:write
# - mpim:history
# - mpim:read
# - mpim:write
# - users:read
```

#### Step 3: Get Bot Token
1. Go to "OAuth & Permissions"
2. Click "Install to Workspace"
3. Copy "Bot User OAuth Token" (starts with `xoxb-`)

#### Step 4: Configure Slack Credentials
```bash
# Set environment variables
export SLACK_BOT_TOKEN=xoxb-your-bot-token-here
export SLACK_SIGNING_SECRET=your-signing-secret-here
export SLACK_APP_TOKEN=xapp-your-app-token-here

# Add to .env file
echo "SLACK_BOT_TOKEN=xoxb-your-bot-token-here" >> .env
echo "SLACK_SIGNING_SECRET=your-signing-secret-here" >> .env
echo "SLACK_APP_TOKEN=xapp-your-app-token-here" >> .env
```

### Microsoft Teams Bot Credentials

#### Step 1: Register Azure App
1. Visit https://portal.azure.com/
2. Go to "Azure Active Directory" → "App registrations"
3. Click "New registration"
4. Enter name: "Splunk MCP Teams Bot"
5. Select "Accounts in any organizational directory"
6. Click "Register"

#### Step 2: Configure Teams Bot
```bash
# Required information from Azure:
TEAMS_APP_ID=your-azure-app-id
TEAMS_APP_PASSWORD=your-azure-app-password
TEAMS_TENANT_ID=your-azure-tenant-id

# Add to .env file
echo "TEAMS_APP_ID=your-azure-app-id" >> .env
echo "TEAMS_APP_PASSWORD=your-azure-app-password" >> .env
echo "TEAMS_TENANT_ID=your-azure-tenant-id" >> .env
```

### Email Service Credentials

#### SMTP Configuration
```bash
# Gmail SMTP example
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_USE_TLS=true

# Office 365 SMTP example
export SMTP_HOST=smtp-mail.outlook.com
export SMTP_PORT=587
export SMTP_USER=your-email@company.com
export SMTP_PASSWORD=your-password
export SMTP_USE_TLS=true

# Add to .env file
cat >> .env << EOF
SMTP_HOST=$SMTP_HOST
SMTP_PORT=$SMTP_PORT
SMTP_USER=$SMTP_USER
SMTP_PASSWORD=$SMTP_PASSWORD
SMTP_USE_TLS=$SMTP_USE_TLS
EOF
```

#### Gmail App Password Setup
1. Enable 2-Factor Authentication on Gmail
2. Go to Google Account settings
3. Security → 2-Step Verification → App passwords
4. Generate app password for "Mail"
5. Use the generated password as SMTP_PASSWORD

## 5. SSL/TLS Certificates

### Development Certificates (Self-Signed)
```bash
# Generate self-signed certificate for development
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Create certificate files
mkdir -p certs/
mv cert.pem certs/
mv key.pem certs/

# Set permissions
chmod 600 certs/key.pem
chmod 644 certs/cert.pem
```

### Production Certificates (Let's Encrypt)
```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com -d api.your-domain.com

# Certificate files will be in:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

### Kubernetes TLS Secret
```bash
# Create TLS secret from certificate files
kubectl create secret tls splunk-mcp-tls \
  --cert=certs/cert.pem \
  --key=certs/key.pem \
  --namespace=splunk-mcp-prod
```

## 6. Environment Variables Template

### Complete .env Template
```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=splunk_mcp
POSTGRES_USER=splunk_mcp_user
POSTGRES_PASSWORD=secure_database_password
DATABASE_URL=postgresql://splunk_mcp_user:secure_database_password@localhost:5432/splunk_mcp

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=secure_redis_password
REDIS_URL=redis://:secure_redis_password@localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=your_generated_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=1
JWT_REFRESH_EXPIRATION_DAYS=30

# AI/ML Service API Keys
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Splunk Configuration (will be detailed in SPLUNK_SETUP.md)
SPLUNK_HOST=your-splunk-instance.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=splunk_admin_password
SPLUNK_SCHEME=https

# Integration Service Credentials
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_SIGNING_SECRET=your-slack-signing-secret-here
SLACK_APP_TOKEN=xapp-your-slack-app-token-here

TEAMS_APP_ID=your-azure-app-id
TEAMS_APP_PASSWORD=your-azure-app-password
TEAMS_TENANT_ID=your-azure-tenant-id

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-email-app-password
SMTP_USE_TLS=true

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=false

# Service Ports
API_GATEWAY_PORT=8000
NLP_ENGINE_PORT=8001
VISUALIZATION_PORT=8002
ALERT_MANAGER_PORT=8003
FRONTEND_PORT=3000
```

## 7. Credential Validation Scripts

### Validation Script
```python
#!/usr/bin/env python3
"""
Credential validation script to verify all required credentials are properly configured.
"""

import os
import sys
import asyncio
import aiohttp
import asyncpg
import aioredis
import openai
import anthropic
from datetime import datetime

class CredentialValidator:
    def __init__(self):
        self.results = []
    
    async def validate_database(self):
        """Validate PostgreSQL connection"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return False, "DATABASE_URL not set"
            
            conn = await asyncpg.connect(database_url)
            result = await conn.fetchval("SELECT version()")
            await conn.close()
            return True, f"Connected to PostgreSQL: {result[:50]}..."
        except Exception as e:
            return False, f"Database connection failed: {str(e)}"
    
    async def validate_redis(self):
        """Validate Redis connection"""
        try:
            redis_url = os.getenv('REDIS_URL')
            if not redis_url:
                return False, "REDIS_URL not set"
            
            redis = aioredis.from_url(redis_url)
            await redis.ping()
            await redis.close()
            return True, "Redis connection successful"
        except Exception as e:
            return False, f"Redis connection failed: {str(e)}"
    
    async def validate_openai(self):
        """Validate OpenAI API key"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return False, "OPENAI_API_KEY not set"
            
            openai.api_key = api_key
            models = openai.Model.list()
            return True, f"OpenAI API validated, {len(models['data'])} models available"
        except Exception as e:
            return False, f"OpenAI API validation failed: {str(e)}"
    
    async def validate_anthropic(self):
        """Validate Anthropic API key"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                return False, "ANTHROPIC_API_KEY not set"
            
            client = anthropic.Anthropic(api_key=api_key)
            # Basic validation - attempt to create a very short message
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True, "Anthropic API validated successfully"
        except Exception as e:
            return False, f"Anthropic API validation failed: {str(e)}"
    
    def validate_jwt_config(self):
        """Validate JWT configuration"""
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret:
            return False, "JWT_SECRET_KEY not set"
        if len(jwt_secret) < 32:
            return False, "JWT_SECRET_KEY too short (minimum 32 characters)"
        return True, f"JWT configuration valid (key length: {len(jwt_secret)})"
    
    async def run_all_validations(self):
        """Run all credential validations"""
        print("🔍 Starting credential validation...")
        print("=" * 60)
        
        validations = [
            ("Database (PostgreSQL)", self.validate_database()),
            ("Cache (Redis)", self.validate_redis()),
            ("OpenAI API", self.validate_openai()),
            ("Anthropic API", self.validate_anthropic()),
            ("JWT Configuration", self.validate_jwt_config()),
        ]
        
        for name, validation in validations:
            if asyncio.iscoroutine(validation):
                success, message = await validation
            else:
                success, message = validation
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {name}: {message}")
            self.results.append((name, success, message))
        
        print("=" * 60)
        
        # Summary
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        if passed == total:
            print(f"🎉 All {total} credential validations passed!")
            return True
        else:
            print(f"⚠️  {passed}/{total} validations passed. Please fix the failing credentials.")
            return False

async def main():
    validator = CredentialValidator()
    success = await validator.run_all_validations()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
```

### Usage Instructions
```bash
# Save the validation script
curl -o scripts/validate-credentials.py https://raw.githubusercontent.com/your-repo/scripts/validate-credentials.py

# Install required packages
pip install asyncpg aioredis openai anthropic

# Run validation
python scripts/validate-credentials.py
```

## 8. Security Best Practices

### Credential Storage
- **Never commit credentials to git**
- Use environment variables or secret management systems
- Rotate credentials regularly (every 90 days)
- Use least-privilege principle for all accounts

### Environment Separation
```bash
# Use different credentials for each environment
# Development
cp .env.example .env.development

# Staging
cp .env.example .env.staging

# Production
cp .env.example .env.production
```

### Kubernetes Secrets
```bash
# Create namespace-specific secrets
kubectl create secret generic app-secrets \
  --from-env-file=.env.production \
  --namespace=splunk-mcp-prod

# Verify secret creation
kubectl get secrets -n splunk-mcp-prod
kubectl describe secret app-secrets -n splunk-mcp-prod
```

## 9. Troubleshooting

### Common Issues

#### Database Connection Fails
```bash
# Check if PostgreSQL is running
kubectl get pods -l app=postgres

# Check database logs
kubectl logs postgres-0

# Test connection manually
kubectl exec -it postgres-0 -- psql -U splunk_mcp_user -d splunk_mcp
```

#### API Key Validation Fails
```bash
# Check if API key is set
echo $OPENAI_API_KEY | cut -c1-10

# Test API key manually
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

#### Redis Connection Issues
```bash
# Check Redis status
kubectl get pods -l app=redis

# Test Redis connection
kubectl exec -it redis-0 -- redis-cli ping
```

---

**Next Steps**: After completing credential setup, proceed to [Splunk Setup Guide](./SPLUNK_SETUP.md) for Splunk REST endpoint configuration.