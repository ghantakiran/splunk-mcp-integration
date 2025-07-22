# Troubleshooting and Maintenance Guide

## Overview

This comprehensive guide covers troubleshooting procedures, maintenance tasks, and operational procedures for the Splunk MCP Integration platform. It includes common issues, diagnostic procedures, performance optimization, and preventive maintenance.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues](#common-issues)
- [Service-Specific Troubleshooting](#service-specific-troubleshooting)
- [Performance Issues](#performance-issues)
- [Database Issues](#database-issues)
- [Network and Connectivity](#network-and-connectivity)
- [Security Issues](#security-issues)
- [Maintenance Procedures](#maintenance-procedures)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Backup and Recovery](#backup-and-recovery)

## Quick Diagnostics

### System Health Check Script
```bash
#!/bin/bash
# health-check.sh - Quick system health assessment

echo "=== Splunk MCP Health Check ==="
echo "Timestamp: $(date)"
echo

# Check service availability
echo "1. Service Availability:"
services=("api-gateway:8000" "nlp-engine:8001" "visualization:8002" "alert-manager:8003")
for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    if curl -s -f "http://localhost:$port/health" >/dev/null; then
        echo "  ✓ $name (port $port) - Healthy"
    else
        echo "  ✗ $name (port $port) - Unhealthy"
    fi
done

# Check database connectivity
echo
echo "2. Database Connectivity:"
if docker-compose exec -T postgres pg_isready -U splunk_mcp_user >/dev/null 2>&1; then
    echo "  ✓ PostgreSQL - Connected"
else
    echo "  ✗ PostgreSQL - Connection failed"
fi

if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    echo "  ✓ Redis - Connected"
else
    echo "  ✗ Redis - Connection failed"
fi

# Check disk space
echo
echo "3. Disk Space:"
df -h | grep -E '/(|var|tmp|opt)$' | awk '{
    if ($5+0 > 90) print "  ✗ " $6 " - " $5 " (Critical)"
    else if ($5+0 > 80) print "  ⚠ " $6 " - " $5 " (Warning)"
    else print "  ✓ " $6 " - " $5 " (OK)"
}'

# Check memory usage
echo
echo "4. Memory Usage:"
free -h | awk 'NR==2{
    used_pct = ($3/$2) * 100
    if (used_pct > 90) print "  ✗ Memory: " $3 "/" $2 " (" int(used_pct) "%) - Critical"
    else if (used_pct > 80) print "  ⚠ Memory: " $3 "/" $2 " (" int(used_pct) "%) - Warning"
    else print "  ✓ Memory: " $3 "/" $2 " (" int(used_pct) "%) - OK"
}'

# Check container status
echo
echo "5. Container Status:"
docker-compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}" | tail -n +2 | while read line; do
    state=$(echo $line | awk '{print $2}')
    if [ "$state" = "running" ]; then
        echo "  ✓ $line"
    else
        echo "  ✗ $line"
    fi
done

echo
echo "=== Health Check Complete ==="
```

### Quick API Test
```bash
#!/bin/bash
# api-test.sh - Quick API functionality test

API_BASE="http://localhost:8000"

echo "=== API Functionality Test ==="

# Test authentication
echo "1. Testing Authentication..."
AUTH_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin"}')

if echo "$AUTH_RESPONSE" | grep -q "access_token"; then
    TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.data.access_token')
    echo "  ✓ Authentication successful"
else
    echo "  ✗ Authentication failed"
    echo "  Response: $AUTH_RESPONSE"
    exit 1
fi

# Test NLP query processing
echo "2. Testing NLP Query Processing..."
QUERY_RESPONSE=$(curl -s -X POST "$API_BASE/nlp/process-query" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query": "show me errors from last hour", "conversation_id": "test"}')

if echo "$QUERY_RESPONSE" | grep -q "spl_query"; then
    echo "  ✓ NLP query processing successful"
else
    echo "  ✗ NLP query processing failed"
    echo "  Response: $QUERY_RESPONSE"
fi

# Test visualization
echo "3. Testing Visualization..."
VIZ_RESPONSE=$(curl -s -X POST "$API_BASE/visualization/generate-chart" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"data": {"labels": ["A", "B"], "datasets": [{"data": [1, 2]}]}, "chart_type": "bar"}')

if echo "$VIZ_RESPONSE" | grep -q "chart_id"; then
    echo "  ✓ Visualization generation successful"
else
    echo "  ✗ Visualization generation failed"
    echo "  Response: $VIZ_RESPONSE"
fi

echo "=== API Test Complete ==="
```

## Common Issues

### 1. Service Startup Issues

#### Symptoms
- Services fail to start
- Containers exit immediately
- Health checks fail

#### Diagnosis
```bash
# Check container logs
docker-compose logs api-gateway

# Check container status
docker-compose ps

# Check resource usage
docker stats

# Check for port conflicts
netstat -tulpn | grep 8000
```

#### Solutions
```bash
# Check environment variables
docker-compose config

# Restart with fresh build
docker-compose down
docker-compose up --build -d

# Clear volumes and restart
docker-compose down -v
docker-compose up -d
```

### 2. Database Connection Issues

#### Symptoms
- "Connection refused" errors
- Database timeout errors
- Migration failures

#### Diagnosis
```bash
# Check PostgreSQL status
docker-compose logs postgres

# Test database connection
docker-compose exec postgres pg_isready -U splunk_mcp_user

# Check connection from application
docker-compose exec api-gateway python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='postgres',
        database='splunk_mcp',
        user='splunk_mcp_user',
        password='password'
    )
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

#### Solutions
```bash
# Restart PostgreSQL
docker-compose restart postgres

# Check and fix permissions
docker-compose exec postgres chown -R postgres:postgres /var/lib/postgresql/data

# Reset database
docker-compose down
docker volume rm splunk-mcp_postgres_data
docker-compose up -d postgres
# Wait for database to be ready, then run migrations
docker-compose exec api-gateway python -m alembic upgrade head
```

### 3. Authentication Issues

#### Symptoms
- 401 Unauthorized errors
- JWT token validation failures
- Login endpoint not working

#### Diagnosis
```bash
# Check JWT secret configuration
docker-compose exec api-gateway env | grep JWT

# Test login endpoint
curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin"}'

# Check user table
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "SELECT * FROM users;"
```

#### Solutions
```bash
# Create admin user if missing
docker-compose exec api-gateway python scripts/create_admin_user.py

# Reset JWT secret
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env
docker-compose restart api-gateway

# Clear Redis cache
docker-compose exec redis redis-cli flushall
```

### 4. API Rate Limiting Issues

#### Symptoms
- 429 Too Many Requests errors
- Clients getting rate limited unexpectedly

#### Diagnosis
```bash
# Check rate limiting configuration
docker-compose exec api-gateway python -c "
from app.core.config import settings
print(f'Rate limit: {settings.RATE_LIMIT_PER_MINUTE}')
"

# Check Redis rate limit keys
docker-compose exec redis redis-cli keys "rate_limit:*"

# Monitor rate limit metrics
curl http://localhost:8000/metrics | grep rate_limit
```

#### Solutions
```bash
# Clear rate limit cache
docker-compose exec redis redis-cli --scan --pattern "rate_limit:*" | xargs docker-compose exec redis redis-cli del

# Adjust rate limits in configuration
# Edit .env file and restart services
docker-compose restart api-gateway

# Disable rate limiting temporarily
docker-compose exec api-gateway python -c "
import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
r.delete('rate_limit:global')
"
```

## Service-Specific Troubleshooting

### API Gateway Service

#### Common Issues
1. **Port binding failures**
2. **Middleware configuration errors**
3. **Route resolution issues**

#### Troubleshooting Steps
```bash
# Check port availability
sudo lsof -i :8000

# Validate configuration
docker-compose exec api-gateway python -c "
from app.core.config import settings
print('Config loaded successfully')
print(f'Database URL: {settings.DATABASE_URL}')
print(f'Redis URL: {settings.REDIS_URL}')
"

# Test middleware chain
curl -v http://localhost:8000/health

# Check route registration
docker-compose exec api-gateway python -c "
from app.main import app
for route in app.routes:
    print(f'{route.methods} {route.path}')
"
```

### NLP Engine Service

#### Common Issues
1. **AI API connection failures**
2. **Model loading issues**
3. **Query processing timeouts**

#### Troubleshooting Steps
```bash
# Check AI API connectivity
docker-compose exec nlp-engine python -c "
import openai
openai.api_key = 'your_api_key'
try:
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': 'test'}],
        max_tokens=10
    )
    print('OpenAI API connection successful')
except Exception as e:
    print(f'OpenAI API connection failed: {e}')
"

# Check model cache
docker-compose exec nlp-engine ls -la /app/models/

# Test query processing
curl -X POST http://localhost:8001/process-query \
    -H "Content-Type: application/json" \
    -d '{"query": "test query", "conversation_id": "test"}'

# Monitor processing times
docker-compose logs nlp-engine | grep "processing_time"
```

### Visualization Service

#### Common Issues
1. **Chart generation failures**
2. **File storage issues**
3. **Memory leaks from chart libraries**

#### Troubleshooting Steps
```bash
# Check chart storage
docker-compose exec visualization ls -la /app/charts/

# Test chart generation
curl -X POST http://localhost:8002/generate-chart \
    -H "Content-Type: application/json" \
    -d '{
        "data": {"labels": ["A", "B"], "datasets": [{"data": [1, 2]}]},
        "chart_type": "bar"
    }'

# Monitor memory usage
docker stats splunk-mcp-visualization

# Check for memory leaks
docker-compose exec visualization python -c "
import psutil
process = psutil.Process()
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

## Performance Issues

### High Response Times

#### Diagnosis Tools
```bash
# Monitor API response times
curl -w "@curl-format.txt" -s http://localhost:8000/health

# Create curl-format.txt
cat > curl-format.txt << 'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF

# Monitor database query performance
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "
SELECT query, calls, total_time, rows, 100.0 * shared_blks_hit /
       nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
"

# Check application metrics
curl http://localhost:8000/metrics | grep -E "(response_time|request_duration)"
```

#### Optimization Strategies
```bash
# Database optimization
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "
-- Update statistics
ANALYZE;

-- Reindex tables
REINDEX DATABASE splunk_mcp;

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
AND n_distinct > 100
AND correlation < 0.1;
"

# Application optimization
# Increase worker processes
echo "WORKERS=8" >> .env
docker-compose restart api-gateway

# Tune connection pools
docker-compose exec api-gateway python -c "
from app.core.database import engine
print(f'Pool size: {engine.pool.size()}')
print(f'Checked out connections: {engine.pool.checkedout()}')
print(f'Overflow: {engine.pool.overflow()}')
"
```

### Memory Issues

#### Diagnosis
```bash
# Monitor container memory usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check for memory leaks
while true; do
    docker stats --no-stream --format "{{.Container}}\t{{.MemUsage}}" | grep splunk-mcp
    sleep 30
done

# Analyze memory usage patterns
docker-compose exec api-gateway python -c "
import psutil
import gc
print(f'Memory info: {psutil.virtual_memory()}')
print(f'Process memory: {psutil.Process().memory_info()}')
print(f'GC stats: {gc.get_stats()}')
"
```

#### Solutions
```bash
# Restart services with memory issues
docker-compose restart api-gateway nlp-engine

# Tune garbage collection
docker-compose exec api-gateway python -c "
import gc
gc.set_threshold(700, 10, 10)
gc.collect()
print('GC tuning applied')
"

# Add memory limits
# Edit docker-compose.yml
services:
  api-gateway:
    deploy:
      resources:
        limits:
          memory: 1G
```

### CPU Issues

#### Diagnosis
```bash
# Monitor CPU usage
top -p $(docker-compose exec api-gateway pgrep -f uvicorn)

# Check Python profiling
docker-compose exec api-gateway python -c "
import cProfile
import pstats
from io import StringIO

# Profile a sample operation
pr = cProfile.Profile()
pr.enable()
# Your operation here
pr.disable()

s = StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats()
print(s.getvalue())
"

# Monitor database CPU usage
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
WHERE calls > 100
ORDER BY mean_time DESC
LIMIT 10;
"
```

## Database Issues

### PostgreSQL Troubleshooting

#### Connection Pool Exhaustion
```bash
# Check active connections
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "
SELECT count(*) as active_connections,
       state,
       application_name
FROM pg_stat_activity
WHERE state = 'active'
GROUP BY state, application_name;
"

# Check connection limits
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "
SHOW max_connections;
SELECT count(*) as current_connections FROM pg_stat_activity;
"

# Fix connection leaks
docker-compose exec api-gateway python -c "
from app.core.database import engine
engine.dispose()
print('Connection pool disposed')
"
```

#### Lock Issues
```bash
# Check for locks
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
"

# Kill blocking queries (use with caution)
# docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "SELECT pg_terminate_backend(PID);"
```

#### Performance Tuning
```bash
# Check database statistics
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "
SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > 1000 OR seq_tup_read > 10000
ORDER BY seq_tup_read DESC;
"

# Update PostgreSQL configuration
docker-compose exec postgres bash -c "
echo 'shared_buffers = 256MB' >> /var/lib/postgresql/data/postgresql.conf
echo 'effective_cache_size = 1GB' >> /var/lib/postgresql/data/postgresql.conf
echo 'maintenance_work_mem = 64MB' >> /var/lib/postgresql/data/postgresql.conf
"

# Restart PostgreSQL
docker-compose restart postgres
```

### Redis Troubleshooting

#### Memory Issues
```bash
# Check Redis memory usage
docker-compose exec redis redis-cli info memory

# Check key distribution
docker-compose exec redis redis-cli --bigkeys

# Monitor memory usage over time
docker-compose exec redis redis-cli --latency-history -i 1

# Clear specific key patterns
docker-compose exec redis redis-cli --scan --pattern "cache:*" | head -1000 | xargs docker-compose exec redis redis-cli del
```

#### Performance Issues
```bash
# Monitor Redis performance
docker-compose exec redis redis-cli --latency

# Check slow queries
docker-compose exec redis redis-cli slowlog get 10

# Monitor commands
docker-compose exec redis redis-cli monitor | head -20
```

## Network and Connectivity

### Docker Network Issues

#### Diagnosis
```bash
# Check Docker networks
docker network ls
docker network inspect splunk-mcp_splunk-mcp-network

# Test inter-service connectivity
docker-compose exec api-gateway ping postgres
docker-compose exec api-gateway ping redis
docker-compose exec api-gateway ping nlp-engine

# Check port bindings
docker port splunk-mcp-api-gateway
docker port splunk-mcp-postgres

# Test external connectivity
docker-compose exec api-gateway curl -I https://api.openai.com
```

#### Solutions
```bash
# Recreate networks
docker-compose down
docker network prune
docker-compose up -d

# Fix DNS resolution
docker-compose exec api-gateway cat /etc/resolv.conf
docker-compose exec api-gateway nslookup postgres

# Check firewall rules
sudo iptables -L | grep 8000
sudo ufw status
```

### External API Connectivity

#### OpenAI/Anthropic API Issues
```bash
# Test OpenAI connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "test"}], "max_tokens": 5}' \
     https://api.openai.com/v1/chat/completions

# Test from container
docker-compose exec nlp-engine python -c "
import requests
import os
response = requests.get(
    'https://api.openai.com/v1/models',
    headers={'Authorization': f'Bearer {os.getenv(\"OPENAI_API_KEY\")}'}
)
print(f'Status: {response.status_code}')
print(f'Response: {response.text[:200]}')
"

# Check proxy settings
docker-compose exec nlp-engine env | grep -i proxy
```

### Splunk Connectivity

#### Connection Testing
```bash
# Test Splunk API connectivity
curl -k -u "$SPLUNK_USERNAME:$SPLUNK_PASSWORD" \
     "https://$SPLUNK_HOST:$SPLUNK_PORT/services/server/info"

# Test from container
docker-compose exec nlp-engine python -c "
import requests
import os
from requests.auth import HTTPBasicAuth

url = f'https://{os.getenv(\"SPLUNK_HOST\")}:{os.getenv(\"SPLUNK_PORT\")}/services/server/info'
auth = HTTPBasicAuth(os.getenv('SPLUNK_USERNAME'), os.getenv('SPLUNK_PASSWORD'))

try:
    response = requests.get(url, auth=auth, verify=False)
    print(f'Status: {response.status_code}')
    print('Splunk connection successful')
except Exception as e:
    print(f'Splunk connection failed: {e}')
"
```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks
```bash
#!/bin/bash
# daily-maintenance.sh

echo "=== Daily Maintenance - $(date) ==="

# Check system health
./health-check.sh

# Clean up old logs
find logs/ -name "*.log" -mtime +7 -delete

# Update container stats
docker stats --no-stream > /tmp/container-stats-$(date +%Y%m%d).txt

# Check disk space
df -h | mail -s "Daily Disk Space Report" admin@company.com

# Backup database
docker-compose exec postgres pg_dump -U splunk_mcp_user splunk_mcp | gzip > backups/daily-$(date +%Y%m%d).sql.gz

echo "Daily maintenance completed"
```

#### Weekly Tasks
```bash
#!/bin/bash
# weekly-maintenance.sh

echo "=== Weekly Maintenance - $(date) ==="

# Update system packages
sudo apt update && sudo apt upgrade -y

# Pull latest Docker images
docker-compose pull

# Clean up Docker resources
docker system prune -f
docker volume prune -f

# Rotate logs
docker-compose logs --no-color > logs/services-$(date +%Y%m%d).log
docker-compose restart

# Update SSL certificates
certbot renew --quiet

# Performance analysis
./performance-report.sh

echo "Weekly maintenance completed"
```

#### Monthly Tasks
```bash
#!/bin/bash
# monthly-maintenance.sh

echo "=== Monthly Maintenance - $(date) ==="

# Full system backup
./full-backup.sh

# Security updates
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y

# Database maintenance
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "
VACUUM ANALYZE;
REINDEX DATABASE splunk_mcp;
"

# Review logs for security issues
./security-log-analysis.sh

# Update documentation
git pull origin main
./update-docs.sh

echo "Monthly maintenance completed"
```

### Performance Monitoring

#### System Metrics Collection
```bash
#!/bin/bash
# collect-metrics.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
METRICS_DIR="metrics/$TIMESTAMP"
mkdir -p "$METRICS_DIR"

# System metrics
top -b -n1 > "$METRICS_DIR/top.txt"
free -h > "$METRICS_DIR/memory.txt"
df -h > "$METRICS_DIR/disk.txt"
iostat 1 3 > "$METRICS_DIR/io.txt"

# Docker metrics
docker stats --no-stream > "$METRICS_DIR/docker-stats.txt"
docker-compose ps > "$METRICS_DIR/containers.txt"

# Application metrics
curl -s http://localhost:8000/metrics > "$METRICS_DIR/app-metrics.txt"

# Database metrics
docker-compose exec postgres psql -U splunk_mcp_user -d splunk_mcp -c "
SELECT * FROM pg_stat_database WHERE datname = 'splunk_mcp';
" > "$METRICS_DIR/db-stats.txt"

# Redis metrics
docker-compose exec redis redis-cli info > "$METRICS_DIR/redis-info.txt"

echo "Metrics collected in $METRICS_DIR"
```

### Backup Procedures

#### Database Backup
```bash
#!/bin/bash
# backup-database.sh

BACKUP_DIR="/backups/$(date +%Y/%m)"
mkdir -p "$BACKUP_DIR"

# PostgreSQL backup
echo "Creating PostgreSQL backup..."
docker-compose exec postgres pg_dump -U splunk_mcp_user -Fc splunk_mcp > "$BACKUP_DIR/postgres-$(date +%Y%m%d_%H%M%S).dump"

# Redis backup
echo "Creating Redis backup..."
docker-compose exec redis redis-cli BGSAVE
sleep 5
docker cp splunk-mcp-redis:/data/dump.rdb "$BACKUP_DIR/redis-$(date +%Y%m%d_%H%M%S).rdb"

# Compress backups
gzip "$BACKUP_DIR"/*.dump
gzip "$BACKUP_DIR"/*.rdb

# Upload to cloud storage (optional)
# aws s3 sync "$BACKUP_DIR" s3://your-backup-bucket/splunk-mcp/

# Clean old backups
find /backups -name "*.gz" -mtime +30 -delete

echo "Backup completed successfully"
```

#### Application State Backup
```bash
#!/bin/bash
# backup-application.sh

BACKUP_DIR="/backups/app-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup configuration
cp -r config/ "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"
cp docker-compose.yml "$BACKUP_DIR/"

# Backup user-generated content
docker cp splunk-mcp-visualization:/app/charts "$BACKUP_DIR/"
docker cp splunk-mcp-pdf-export:/app/exports "$BACKUP_DIR/"

# Backup logs
cp -r logs/ "$BACKUP_DIR/"

# Create archive
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

echo "Application backup created: $BACKUP_DIR.tar.gz"
```

### Security Maintenance

#### Security Updates
```bash
#!/bin/bash
# security-updates.sh

echo "=== Security Updates - $(date) ==="

# Update Docker images
docker-compose pull

# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  -v /tmp:/root/.cache/ aquasec/trivy:latest \
  image splunk-mcp-api-gateway:latest

# Update certificates
certbot renew --quiet

# Review security logs
grep -i "failed\|error\|unauthorized" logs/*.log | tail -50

# Check for security updates
apt list --upgradable | grep -i security

echo "Security updates completed"
```

#### Log Analysis
```bash
#!/bin/bash
# security-log-analysis.sh

echo "=== Security Log Analysis - $(date) ==="

# Failed login attempts
echo "Failed login attempts:"
docker-compose logs api-gateway | grep -i "401\|unauthorized\|failed.*login" | tail -20

# Rate limiting triggers
echo "Rate limiting events:"
docker-compose logs api-gateway | grep -i "429\|rate.*limit" | tail -10

# Database errors
echo "Database security events:"
docker-compose logs postgres | grep -i "authentication\|connection.*failed" | tail -10

# Suspicious API calls
echo "Suspicious API activity:"
docker-compose logs api-gateway | grep -E "(admin|delete|drop|truncate)" | tail -20

echo "Security log analysis completed"
```

---

*Last Updated: January 22, 2025*
*Version: 1.0*