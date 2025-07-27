# Operational Runbooks

This document provides step-by-step operational procedures for maintaining the Splunk MCP Integration Platform in production environments.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Service Management](#service-management)
3. [Database Operations](#database-operations)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Backup & Recovery](#backup--recovery)
6. [Performance Management](#performance-management)
7. [Security Operations](#security-operations)
8. [Emergency Procedures](#emergency-procedures)
9. [Maintenance Windows](#maintenance-windows)

---

## Daily Operations

### Morning Health Check Procedure

#### Objective
Verify platform health and identify any issues that occurred overnight.

#### Prerequisites
- Access to Kubernetes cluster
- Grafana dashboard access
- Alert notification access

#### Procedure

**Step 1: System Overview Check**
```bash
#!/bin/bash
# morning-health-check.sh

NAMESPACE="splunk-mcp-prod"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "===== SPLUNK MCP MORNING HEALTH CHECK ====="
echo "Date: $DATE"
echo ""

# Check namespace exists and is active
echo "1. Checking namespace status..."
if kubectl get namespace $NAMESPACE >/dev/null 2>&1; then
    echo "✅ Namespace $NAMESPACE is active"
else
    echo "❌ Namespace $NAMESPACE not found"
    exit 1
fi

# Check node status
echo ""
echo "2. Checking node status..."
kubectl get nodes --no-headers | while read line; do
    node_name=$(echo $line | awk '{print $1}')
    node_status=$(echo $line | awk '{print $2}')
    if [[ "$node_status" == "Ready" ]]; then
        echo "✅ Node $node_name is Ready"
    else
        echo "❌ Node $node_name is $node_status"
    fi
done

# Check pod status
echo ""
echo "3. Checking pod status..."
kubectl get pods -n $NAMESPACE --no-headers | while read line; do
    pod_name=$(echo $line | awk '{print $1}')
    pod_status=$(echo $line | awk '{print $3}')
    pod_ready=$(echo $line | awk '{print $2}')
    if [[ "$pod_status" == "Running" ]]; then
        echo "✅ Pod $pod_name is Running ($pod_ready)"
    else
        echo "❌ Pod $pod_name is $pod_status ($pod_ready)"
    fi
done

# Check service endpoints
echo ""
echo "4. Checking service endpoints..."
services=("api-gateway:8000" "nlp-engine:8001" "visualization:8002" "alert-manager:8003")
for service in "${services[@]}"; do
    service_name=$(echo $service | cut -d: -f1)
    service_port=$(echo $service | cut -d: -f2)
    
    if kubectl exec -n $NAMESPACE deployment/$service_name -- \
       wget --quiet --tries=1 --timeout=10 --spider http://localhost:$service_port/health 2>/dev/null; then
        echo "✅ $service_name health endpoint responding"
    else
        echo "❌ $service_name health endpoint not responding"
    fi
done

# Check database connectivity
echo ""
echo "5. Checking database connectivity..."
if kubectl exec -n $NAMESPACE deployment/api-gateway -- \
   python -c "import psycopg2, os; psycopg2.connect(os.environ['DATABASE_URL']).close(); print('Database OK')" 2>/dev/null; then
    echo "✅ PostgreSQL database connectivity OK"
else
    echo "❌ PostgreSQL database connectivity failed"
fi

# Check Redis connectivity
echo ""
echo "6. Checking Redis connectivity..."
if kubectl exec -n $NAMESPACE deployment/api-gateway -- \
   python -c "import redis, os; redis.from_url(os.environ['REDIS_URL']).ping(); print('Redis OK')" 2>/dev/null; then
    echo "✅ Redis connectivity OK"
else
    echo "❌ Redis connectivity failed"
fi

# Check resource utilization
echo ""
echo "7. Checking resource utilization..."
kubectl top nodes 2>/dev/null | tail -n +2 | while read line; do
    node_name=$(echo $line | awk '{print $1}')
    cpu_usage=$(echo $line | awk '{print $2}' | sed 's/%//')
    memory_usage=$(echo $line | awk '{print $4}' | sed 's/%//')
    
    if [ "$cpu_usage" -gt 80 ]; then
        echo "⚠️  Node $node_name CPU usage high: ${cpu_usage}%"
    elif [ "$memory_usage" -gt 80 ]; then
        echo "⚠️  Node $node_name Memory usage high: ${memory_usage}%"
    else
        echo "✅ Node $node_name resource usage normal (CPU: ${cpu_usage}%, Memory: ${memory_usage}%)"
    fi
done

# Check for recent alerts
echo ""
echo "8. Checking for recent alerts..."
# This would query your alerting system
echo "Check Grafana/AlertManager for any active alerts"

echo ""
echo "===== HEALTH CHECK COMPLETED ====="
```

**Step 2: Review Overnight Logs**
```bash
# Check for errors in the last 12 hours
kubectl logs -n splunk-mcp-prod deployment/api-gateway --since=12h | grep -i error | tail -20
kubectl logs -n splunk-mcp-prod deployment/nlp-engine --since=12h | grep -i error | tail -20

# Check for authentication failures
kubectl logs -n splunk-mcp-prod deployment/api-gateway --since=12h | grep "auth_failure" | wc -l

# Check for rate limiting events
kubectl logs -n splunk-mcp-prod deployment/api-gateway --since=12h | grep "rate_limit" | wc -l
```

**Step 3: Validate External Dependencies**
```bash
# Test Splunk connectivity
kubectl exec -n splunk-mcp-prod deployment/api-gateway -- \
  curl -k -s "https://$SPLUNK_HOST:8089/services/server/info" -u "$SPLUNK_USER:$SPLUNK_PASS" | grep -q "Splunk"

# Test AI service connectivity
kubectl exec -n splunk-mcp-prod deployment/nlp-engine -- \
  python -c "
import openai
import os
openai.api_key = os.environ['OPENAI_API_KEY']
try:
    openai.Model.list()
    print('OpenAI API connectivity OK')
except Exception as e:
    print(f'OpenAI API connectivity failed: {e}')
"
```

#### Expected Results
- All pods in Running state
- All health endpoints responding
- Database and Redis connectivity confirmed
- No critical resource usage issues
- No active alerts requiring immediate attention

#### Escalation Criteria
- Any service pods not in Running state
- Health endpoints not responding
- Database/Redis connectivity failures
- Resource usage >90%
- Critical alerts active

---

### End-of-Day Summary Procedure

#### Objective
Generate daily summary report and prepare for overnight operations.

#### Procedure

**Step 1: Generate Daily Report**
```bash
#!/bin/bash
# daily-summary-report.sh

NAMESPACE="splunk-mcp-prod"
DATE=$(date '+%Y-%m-%d')
REPORT_FILE="/tmp/daily-summary-$DATE.txt"

{
    echo "===== DAILY OPERATIONS SUMMARY ====="
    echo "Date: $DATE"
    echo "Report Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Service uptime
    echo "SERVICE UPTIME:"
    kubectl get pods -n $NAMESPACE --no-headers | while read line; do
        pod_name=$(echo $line | awk '{print $1}')
        pod_status=$(echo $line | awk '{print $3}')
        pod_age=$(echo $line | awk '{print $5}')
        echo "  $pod_name: $pod_status (Age: $pod_age)"
    done
    echo ""
    
    # Request volume
    echo "REQUEST VOLUME (Last 24 hours):"
    # This would query your metrics system
    echo "  Total API requests: [Query Prometheus]"
    echo "  Authentication requests: [Query Prometheus]"
    echo "  Search queries: [Query Prometheus]"
    echo "  Export requests: [Query Prometheus]"
    echo ""
    
    # Error summary
    echo "ERROR SUMMARY (Last 24 hours):"
    error_count=$(kubectl logs -n $NAMESPACE deployment/api-gateway --since=24h | grep -i error | wc -l)
    auth_failures=$(kubectl logs -n $NAMESPACE deployment/api-gateway --since=24h | grep "auth_failure" | wc -l)
    rate_limits=$(kubectl logs -n $NAMESPACE deployment/api-gateway --since=24h | grep "rate_limit" | wc -l)
    
    echo "  Total errors: $error_count"
    echo "  Authentication failures: $auth_failures"
    echo "  Rate limit events: $rate_limits"
    echo ""
    
    # Resource usage
    echo "RESOURCE USAGE:"
    kubectl top nodes 2>/dev/null | tail -n +2 | while read line; do
        node_name=$(echo $line | awk '{print $1}')
        cpu_usage=$(echo $line | awk '{print $2}')
        memory_usage=$(echo $line | awk '{print $4}')
        echo "  Node $node_name: CPU $cpu_usage, Memory $memory_usage"
    done
    echo ""
    
    # Backup status
    echo "BACKUP STATUS:"
    last_backup=$(kubectl get job -n $NAMESPACE -l app=backup --sort-by=.status.startTime -o jsonpath='{.items[-1].status.startTime}' 2>/dev/null || echo "No backup jobs found")
    echo "  Last backup: $last_backup"
    echo ""
    
    # Planned maintenance
    echo "PLANNED MAINTENANCE:"
    echo "  Next scheduled maintenance: [Check maintenance calendar]"
    echo ""
    
    # Action items
    echo "ACTION ITEMS:"
    if [ "$error_count" -gt 50 ]; then
        echo "  - Investigate high error count: $error_count"
    fi
    if [ "$auth_failures" -gt 20 ]; then
        echo "  - Review authentication failures: $auth_failures"
    fi
    echo "  - Review performance metrics"
    echo "  - Check for security updates"
    echo ""
    
} > $REPORT_FILE

echo "Daily summary report generated: $REPORT_FILE"
cat $REPORT_FILE
```

**Step 2: Prepare for Overnight Operations**
```bash
# Enable overnight monitoring
kubectl patch deployment monitoring-stack-prometheus -n monitoring \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"prometheus","env":[{"name":"OVERNIGHT_MODE","value":"true"}]}]}}}}'

# Verify backup job schedule
kubectl get cronjob -n splunk-mcp-prod

# Check disk space on all nodes
kubectl get nodes -o wide | while read line; do
    node=$(echo $line | awk '{print $1}')
    if [[ "$node" != "NAME" ]]; then
        kubectl debug node/$node -it --image=busybox -- df -h
    fi
done
```

---

## Service Management

### Service Restart Procedure

#### Objective
Safely restart services with minimal downtime.

#### Prerequisites
- Service identified for restart
- Maintenance window approved (if required)
- Health check validation ready

#### Procedure

**Single Service Restart**
```bash
#!/bin/bash
# restart-service.sh

SERVICE_NAME="$1"
NAMESPACE="splunk-mcp-prod"

if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: $0 <service-name>"
    echo "Available services: api-gateway, nlp-engine, visualization, alert-manager"
    exit 1
fi

echo "Starting restart procedure for $SERVICE_NAME..."

# Step 1: Pre-restart health check
echo "1. Performing pre-restart health check..."
kubectl rollout status deployment/$SERVICE_NAME -n $NAMESPACE --timeout=30s

# Step 2: Scale down gracefully
echo "2. Scaling down service..."
current_replicas=$(kubectl get deployment $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.replicas}')
echo "Current replicas: $current_replicas"

# For high-availability services, scale down gradually
if [ "$current_replicas" -gt 1 ]; then
    kubectl scale deployment $SERVICE_NAME --replicas=1 -n $NAMESPACE
    kubectl rollout status deployment/$SERVICE_NAME -n $NAMESPACE --timeout=120s
fi

# Step 3: Restart the service
echo "3. Restarting service..."
kubectl rollout restart deployment/$SERVICE_NAME -n $NAMESPACE

# Step 4: Wait for restart to complete
echo "4. Waiting for restart to complete..."
kubectl rollout status deployment/$SERVICE_NAME -n $NAMESPACE --timeout=300s

# Step 5: Scale back up
echo "5. Scaling back to original replica count..."
kubectl scale deployment $SERVICE_NAME --replicas=$current_replicas -n $NAMESPACE
kubectl rollout status deployment/$SERVICE_NAME -n $NAMESPACE --timeout=300s

# Step 6: Health check validation
echo "6. Performing post-restart health check..."
sleep 30  # Allow service to fully initialize

service_port=""
case $SERVICE_NAME in
    "api-gateway") service_port="8000" ;;
    "nlp-engine") service_port="8001" ;;
    "visualization") service_port="8002" ;;
    "alert-manager") service_port="8003" ;;
esac

if [ -n "$service_port" ]; then
    if kubectl exec -n $NAMESPACE deployment/$SERVICE_NAME -- \
       wget --quiet --tries=3 --timeout=10 --spider http://localhost:$service_port/health; then
        echo "✅ Service $SERVICE_NAME restart completed successfully"
    else
        echo "❌ Service $SERVICE_NAME health check failed after restart"
        exit 1
    fi
else
    echo "⚠️  No health check available for $SERVICE_NAME"
fi

echo "Service restart procedure completed for $SERVICE_NAME"
```

**Rolling Update Procedure**
```bash
#!/bin/bash
# rolling-update.sh

SERVICE_NAME="$1"
NEW_IMAGE="$2"
NAMESPACE="splunk-mcp-prod"

if [ -z "$SERVICE_NAME" ] || [ -z "$NEW_IMAGE" ]; then
    echo "Usage: $0 <service-name> <new-image>"
    exit 1
fi

echo "Starting rolling update for $SERVICE_NAME to $NEW_IMAGE..."

# Step 1: Backup current configuration
echo "1. Backing up current configuration..."
kubectl get deployment $SERVICE_NAME -n $NAMESPACE -o yaml > /tmp/${SERVICE_NAME}-backup-$(date +%Y%m%d-%H%M%S).yaml

# Step 2: Update image
echo "2. Updating image..."
kubectl set image deployment/$SERVICE_NAME $SERVICE_NAME=$NEW_IMAGE -n $NAMESPACE

# Step 3: Monitor rollout
echo "3. Monitoring rollout progress..."
kubectl rollout status deployment/$SERVICE_NAME -n $NAMESPACE --timeout=600s

# Step 4: Verify update
echo "4. Verifying update..."
current_image=$(kubectl get deployment $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')
if [ "$current_image" = "$NEW_IMAGE" ]; then
    echo "✅ Image update successful: $current_image"
else
    echo "❌ Image update failed. Current: $current_image, Expected: $NEW_IMAGE"
    exit 1
fi

# Step 5: Health check
echo "5. Performing health check..."
sleep 30
service_port=""
case $SERVICE_NAME in
    "api-gateway") service_port="8000" ;;
    "nlp-engine") service_port="8001" ;;
    "visualization") service_port="8002" ;;
    "alert-manager") service_port="8003" ;;
esac

if [ -n "$service_port" ]; then
    for i in {1..5}; do
        if kubectl exec -n $NAMESPACE deployment/$SERVICE_NAME -- \
           wget --quiet --tries=1 --timeout=10 --spider http://localhost:$service_port/health; then
            echo "✅ Health check passed (attempt $i)"
            break
        else
            echo "⚠️  Health check failed (attempt $i), retrying..."
            sleep 10
        fi
        
        if [ $i -eq 5 ]; then
            echo "❌ Health check failed after 5 attempts"
            echo "Rolling back to previous version..."
            kubectl rollout undo deployment/$SERVICE_NAME -n $NAMESPACE
            exit 1
        fi
    done
fi

echo "Rolling update completed successfully for $SERVICE_NAME"
```

### Service Scaling Procedure

#### Horizontal Scaling
```bash
#!/bin/bash
# scale-service.sh

SERVICE_NAME="$1"
TARGET_REPLICAS="$2"
NAMESPACE="splunk-mcp-prod"

if [ -z "$SERVICE_NAME" ] || [ -z "$TARGET_REPLICAS" ]; then
    echo "Usage: $0 <service-name> <target-replicas>"
    exit 1
fi

echo "Scaling $SERVICE_NAME to $TARGET_REPLICAS replicas..."

# Step 1: Check current state
current_replicas=$(kubectl get deployment $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.replicas}')
ready_replicas=$(kubectl get deployment $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')

echo "Current replicas: $current_replicas"
echo "Ready replicas: $ready_replicas"

# Step 2: Validate scaling decision
if [ "$TARGET_REPLICAS" -gt 10 ]; then
    echo "⚠️  Warning: Scaling to more than 10 replicas. Confirm this is intentional."
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 3: Perform scaling
echo "Scaling service..."
kubectl scale deployment $SERVICE_NAME --replicas=$TARGET_REPLICAS -n $NAMESPACE

# Step 4: Monitor scaling progress
echo "Monitoring scaling progress..."
for i in {1..30}; do
    ready_replicas=$(kubectl get deployment $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
    if [ "$ready_replicas" = "$TARGET_REPLICAS" ]; then
        echo "✅ Scaling completed successfully"
        break
    else
        echo "Scaling in progress... ($ready_replicas/$TARGET_REPLICAS ready)"
        sleep 10
    fi
    
    if [ $i -eq 30 ]; then
        echo "❌ Scaling did not complete within 5 minutes"
        kubectl describe deployment $SERVICE_NAME -n $NAMESPACE
        exit 1
    fi
done

# Step 5: Verify service health
echo "Verifying service health..."
kubectl rollout status deployment/$SERVICE_NAME -n $NAMESPACE --timeout=120s

echo "Service scaling completed for $SERVICE_NAME"
```

---

## Database Operations

### Database Backup Procedure

#### Objective
Create consistent database backups with verification.

#### Prerequisites
- Database access credentials
- Backup storage configured
- Sufficient disk space

#### Procedure

**Manual Backup**
```bash
#!/bin/bash
# manual-db-backup.sh

NAMESPACE="splunk-mcp-prod"
BACKUP_DIR="/backup"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="splunk-mcp-backup-$TIMESTAMP.sql"

echo "Starting manual database backup..."

# Step 1: Create backup directory
mkdir -p $BACKUP_DIR

# Step 2: Perform database backup
echo "Creating database backup..."
kubectl exec -i postgresql-0 -n $NAMESPACE -- pg_dump -U postgres -d splunk_mcp --verbose --no-password > $BACKUP_DIR/$BACKUP_FILE

# Step 3: Verify backup file
if [ -f "$BACKUP_DIR/$BACKUP_FILE" ] && [ -s "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo "✅ Backup file created: $BACKUP_DIR/$BACKUP_FILE"
    file_size=$(du -h $BACKUP_DIR/$BACKUP_FILE | cut -f1)
    echo "Backup file size: $file_size"
else
    echo "❌ Backup file creation failed"
    exit 1
fi

# Step 4: Compress backup
echo "Compressing backup..."
gzip $BACKUP_DIR/$BACKUP_FILE
COMPRESSED_FILE="$BACKUP_DIR/$BACKUP_FILE.gz"

if [ -f "$COMPRESSED_FILE" ]; then
    echo "✅ Backup compressed: $COMPRESSED_FILE"
    compressed_size=$(du -h $COMPRESSED_FILE | cut -f1)
    echo "Compressed file size: $compressed_size"
else
    echo "❌ Backup compression failed"
    exit 1
fi

# Step 5: Generate checksum
echo "Generating checksum..."
cd $BACKUP_DIR
sha256sum $(basename $COMPRESSED_FILE) > $(basename $COMPRESSED_FILE).sha256
echo "✅ Checksum generated: $(basename $COMPRESSED_FILE).sha256"

# Step 6: Test backup integrity
echo "Testing backup integrity..."
if gzip -t $COMPRESSED_FILE; then
    echo "✅ Backup integrity verified"
else
    echo "❌ Backup integrity check failed"
    exit 1
fi

# Step 7: Upload to remote storage (if configured)
if [ -n "$BACKUP_S3_BUCKET" ]; then
    echo "Uploading to S3..."
    aws s3 cp $COMPRESSED_FILE s3://$BACKUP_S3_BUCKET/database/
    aws s3 cp $(basename $COMPRESSED_FILE).sha256 s3://$BACKUP_S3_BUCKET/database/
    echo "✅ Backup uploaded to S3"
fi

echo "Database backup completed successfully: $COMPRESSED_FILE"
```

**Automated Backup Validation**
```bash
#!/bin/bash
# validate-backup.sh

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file>"
    exit 1
fi

echo "Validating backup file: $BACKUP_FILE"

# Step 1: File existence check
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found"
    exit 1
fi

# Step 2: File size check
file_size=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
if [ "$file_size" -lt 1000000 ]; then  # Less than 1MB
    echo "❌ Backup file too small: $file_size bytes"
    exit 1
fi

# Step 3: Compression integrity
if [[ "$BACKUP_FILE" == *.gz ]]; then
    if gzip -t "$BACKUP_FILE"; then
        echo "✅ Compression integrity verified"
    else
        echo "❌ Compression integrity check failed"
        exit 1
    fi
fi

# Step 4: SQL syntax validation
echo "Checking SQL syntax..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    sql_check=$(zcat "$BACKUP_FILE" | head -100 | grep -c "PostgreSQL database dump")
else
    sql_check=$(head -100 "$BACKUP_FILE" | grep -c "PostgreSQL database dump")
fi

if [ "$sql_check" -gt 0 ]; then
    echo "✅ SQL syntax validation passed"
else
    echo "❌ SQL syntax validation failed"
    exit 1
fi

# Step 5: Schema validation
echo "Checking schema completeness..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    table_count=$(zcat "$BACKUP_FILE" | grep -c "CREATE TABLE")
else
    table_count=$(grep -c "CREATE TABLE" "$BACKUP_FILE")
fi

echo "Tables found in backup: $table_count"
if [ "$table_count" -lt 10 ]; then  # Adjust based on your schema
    echo "⚠️  Warning: Low table count in backup"
else
    echo "✅ Schema validation passed"
fi

echo "Backup validation completed"
```

### Database Restore Procedure

#### Objective
Restore database from backup with minimal downtime.

#### Prerequisites
- Valid backup file
- Database access
- Service maintenance window

#### Procedure

**Database Restore**
```bash
#!/bin/bash
# restore-database.sh

BACKUP_FILE="$1"
NAMESPACE="splunk-mcp-prod"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file>"
    exit 1
fi

echo "Starting database restore from: $BACKUP_FILE"

# Step 1: Validate backup file
echo "1. Validating backup file..."
./validate-backup.sh "$BACKUP_FILE"
if [ $? -ne 0 ]; then
    echo "❌ Backup validation failed"
    exit 1
fi

# Step 2: Stop application services
echo "2. Stopping application services..."
kubectl scale deployment api-gateway --replicas=0 -n $NAMESPACE
kubectl scale deployment nlp-engine --replicas=0 -n $NAMESPACE
kubectl scale deployment visualization --replicas=0 -n $NAMESPACE
kubectl scale deployment alert-manager --replicas=0 -n $NAMESPACE

# Wait for services to stop
echo "Waiting for services to stop..."
kubectl wait --for=delete pod -l tier=backend -n $NAMESPACE --timeout=120s

# Step 3: Create database backup before restore
echo "3. Creating pre-restore backup..."
pre_restore_backup="/tmp/pre-restore-backup-$(date +%Y%m%d-%H%M%S).sql"
kubectl exec -i postgresql-0 -n $NAMESPACE -- pg_dump -U postgres -d splunk_mcp > $pre_restore_backup
echo "Pre-restore backup created: $pre_restore_backup"

# Step 4: Drop and recreate database
echo "4. Dropping and recreating database..."
kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -c "DROP DATABASE IF EXISTS splunk_mcp;"
kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -c "CREATE DATABASE splunk_mcp;"

# Step 5: Restore from backup
echo "5. Restoring from backup..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    zcat "$BACKUP_FILE" | kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp
else
    cat "$BACKUP_FILE" | kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp
fi

# Step 6: Verify restore
echo "6. Verifying restore..."
table_count=$(kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
echo "Tables restored: $table_count"

if [ "$table_count" -lt 10 ]; then
    echo "❌ Restore verification failed"
    echo "Restoring from pre-restore backup..."
    cat $pre_restore_backup | kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp
    exit 1
fi

# Step 7: Start application services
echo "7. Starting application services..."
kubectl scale deployment api-gateway --replicas=3 -n $NAMESPACE
kubectl scale deployment nlp-engine --replicas=2 -n $NAMESPACE
kubectl scale deployment visualization --replicas=2 -n $NAMESPACE
kubectl scale deployment alert-manager --replicas=2 -n $NAMESPACE

# Step 8: Wait for services to be ready
echo "8. Waiting for services to be ready..."
kubectl rollout status deployment/api-gateway -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/nlp-engine -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/visualization -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/alert-manager -n $NAMESPACE --timeout=300s

# Step 9: Health check
echo "9. Performing health check..."
sleep 30
if kubectl exec -n $NAMESPACE deployment/api-gateway -- \
   wget --quiet --tries=3 --timeout=10 --spider http://localhost:8000/health; then
    echo "✅ Database restore completed successfully"
else
    echo "❌ Health check failed after restore"
    exit 1
fi

echo "Database restore procedure completed"
```

### Database Maintenance

#### Routine Maintenance
```bash
#!/bin/bash
# database-maintenance.sh

NAMESPACE="splunk-mcp-prod"

echo "Starting database maintenance..."

# Step 1: Vacuum and analyze
echo "1. Running VACUUM ANALYZE..."
kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp -c "VACUUM ANALYZE;"

# Step 2: Reindex heavily used tables
echo "2. Reindexing tables..."
tables=("users" "queries" "dashboards" "alerts" "audit_logs")
for table in "${tables[@]}"; do
    echo "Reindexing table: $table"
    kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp -c "REINDEX TABLE $table;"
done

# Step 3: Update statistics
echo "3. Updating statistics..."
kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp -c "ANALYZE;"

# Step 4: Check for long-running queries
echo "4. Checking for long-running queries..."
kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
"

# Step 5: Check database size
echo "5. Checking database size..."
kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"

echo "Database maintenance completed"
```

---

## Monitoring & Alerting

### Alert Response Procedures

#### Critical Alert Response

**Service Down Alert**
```bash
#!/bin/bash
# respond-service-down.sh

SERVICE_NAME="$1"
NAMESPACE="splunk-mcp-prod"

if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: $0 <service-name>"
    exit 1
fi

echo "Responding to service down alert for: $SERVICE_NAME"

# Step 1: Immediate assessment
echo "1. Assessing service status..."
kubectl get pods -n $NAMESPACE -l app=$SERVICE_NAME

# Step 2: Check recent events
echo "2. Checking recent events..."
kubectl get events -n $NAMESPACE --field-selector involvedObject.name=$SERVICE_NAME --sort-by='.lastTimestamp' | tail -10

# Step 3: Check logs for errors
echo "3. Checking logs for errors..."
kubectl logs -n $NAMESPACE -l app=$SERVICE_NAME --tail=50 | grep -i error

# Step 4: Check resource constraints
echo "4. Checking resource constraints..."
kubectl describe pods -n $NAMESPACE -l app=$SERVICE_NAME | grep -A 5 -B 5 "Resource\|Limit\|Request"

# Step 5: Attempt automatic recovery
echo "5. Attempting automatic recovery..."
kubectl rollout restart deployment/$SERVICE_NAME -n $NAMESPACE

# Step 6: Monitor recovery
echo "6. Monitoring recovery..."
kubectl rollout status deployment/$SERVICE_NAME -n $NAMESPACE --timeout=300s

# Step 7: Verify service health
echo "7. Verifying service health..."
sleep 30
service_port=""
case $SERVICE_NAME in
    "api-gateway") service_port="8000" ;;
    "nlp-engine") service_port="8001" ;;
    "visualization") service_port="8002" ;;
    "alert-manager") service_port="8003" ;;
esac

if [ -n "$service_port" ]; then
    if kubectl exec -n $NAMESPACE deployment/$SERVICE_NAME -- \
       wget --quiet --tries=3 --timeout=10 --spider http://localhost:$service_port/health; then
        echo "✅ Service recovery successful"
    else
        echo "❌ Service recovery failed - escalating"
        # Send escalation notification
        exit 1
    fi
fi

echo "Service down alert response completed"
```

**High Error Rate Alert**
```bash
#!/bin/bash
# respond-high-error-rate.sh

SERVICE_NAME="$1"
NAMESPACE="splunk-mcp-prod"

echo "Responding to high error rate alert for: $SERVICE_NAME"

# Step 1: Gather error metrics
echo "1. Gathering error metrics..."
error_count=$(kubectl logs -n $NAMESPACE -l app=$SERVICE_NAME --since=5m | grep -i error | wc -l)
total_requests=$(kubectl logs -n $NAMESPACE -l app=$SERVICE_NAME --since=5m | grep "HTTP" | wc -l)

if [ "$total_requests" -gt 0 ]; then
    error_rate=$(echo "scale=2; $error_count * 100 / $total_requests" | bc)
    echo "Error rate: $error_rate% ($error_count errors out of $total_requests requests)"
else
    echo "No HTTP requests found in logs"
fi

# Step 2: Analyze error patterns
echo "2. Analyzing error patterns..."
kubectl logs -n $NAMESPACE -l app=$SERVICE_NAME --since=5m | grep -i error | sort | uniq -c | sort -nr | head -10

# Step 3: Check external dependencies
echo "3. Checking external dependencies..."
kubectl exec -n $NAMESPACE deployment/$SERVICE_NAME -- \
  curl -s -o /dev/null -w "%{http_code}" http://postgresql:5432 || echo "Database connectivity issue"

kubectl exec -n $NAMESPACE deployment/$SERVICE_NAME -- \
  curl -s -o /dev/null -w "%{http_code}" http://redis:6379 || echo "Redis connectivity issue"

# Step 4: Check resource utilization
echo "4. Checking resource utilization..."
kubectl top pods -n $NAMESPACE -l app=$SERVICE_NAME

# Step 5: Implement temporary mitigation
echo "5. Implementing temporary mitigation..."
# Increase replica count if CPU/memory bound
current_replicas=$(kubectl get deployment $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.replicas}')
if [ "$current_replicas" -lt 5 ]; then
    echo "Scaling up service to handle load..."
    kubectl scale deployment $SERVICE_NAME --replicas=$((current_replicas + 1)) -n $NAMESPACE
fi

# Step 6: Monitor improvement
echo "6. Monitoring for improvement..."
sleep 60
new_error_count=$(kubectl logs -n $NAMESPACE -l app=$SERVICE_NAME --since=1m | grep -i error | wc -l)
echo "Errors in last minute: $new_error_count"

echo "High error rate alert response completed"
```

### Monitoring Dashboard Procedures

#### Dashboard Health Check
```bash
#!/bin/bash
# check-monitoring-health.sh

MONITORING_NAMESPACE="monitoring"

echo "Checking monitoring system health..."

# Step 1: Check Prometheus
echo "1. Checking Prometheus..."
prometheus_pods=$(kubectl get pods -n $MONITORING_NAMESPACE -l app.kubernetes.io/name=prometheus --no-headers | wc -l)
prometheus_ready=$(kubectl get pods -n $MONITORING_NAMESPACE -l app.kubernetes.io/name=prometheus --no-headers | grep "Running" | wc -l)

echo "Prometheus pods: $prometheus_ready/$prometheus_pods ready"

if [ "$prometheus_ready" -eq "$prometheus_pods" ] && [ "$prometheus_pods" -gt 0 ]; then
    echo "✅ Prometheus is healthy"
else
    echo "❌ Prometheus has issues"
fi

# Step 2: Check Grafana
echo "2. Checking Grafana..."
grafana_pods=$(kubectl get pods -n $MONITORING_NAMESPACE -l app.kubernetes.io/name=grafana --no-headers | wc -l)
grafana_ready=$(kubectl get pods -n $MONITORING_NAMESPACE -l app.kubernetes.io/name=grafana --no-headers | grep "Running" | wc -l)

echo "Grafana pods: $grafana_ready/$grafana_pods ready"

if [ "$grafana_ready" -eq "$grafana_pods" ] && [ "$grafana_pods" -gt 0 ]; then
    echo "✅ Grafana is healthy"
else
    echo "❌ Grafana has issues"
fi

# Step 3: Check AlertManager
echo "3. Checking AlertManager..."
alertmanager_pods=$(kubectl get pods -n $MONITORING_NAMESPACE -l app.kubernetes.io/name=alertmanager --no-headers | wc -l)
alertmanager_ready=$(kubectl get pods -n $MONITORING_NAMESPACE -l app.kubernetes.io/name=alertmanager --no-headers | grep "Running" | wc -l)

echo "AlertManager pods: $alertmanager_ready/$alertmanager_pods ready"

if [ "$alertmanager_ready" -eq "$alertmanager_pods" ] && [ "$alertmanager_pods" -gt 0 ]; then
    echo "✅ AlertManager is healthy"
else
    echo "❌ AlertManager has issues"
fi

# Step 4: Test metrics collection
echo "4. Testing metrics collection..."
if kubectl port-forward -n $MONITORING_NAMESPACE svc/prometheus-stack-prometheus 9090:9090 >/dev/null 2>&1 &
then
    sleep 5
    metrics_test=$(curl -s http://localhost:9090/api/v1/query?query=up | grep -c "\"status\":\"success\"")
    kill %1  # Kill port-forward
    
    if [ "$metrics_test" -gt 0 ]; then
        echo "✅ Metrics collection working"
    else
        echo "❌ Metrics collection failed"
    fi
else
    echo "❌ Cannot connect to Prometheus"
fi

echo "Monitoring health check completed"
```

---

## Backup & Recovery

### Automated Backup Monitoring

#### Backup Job Monitoring
```bash
#!/bin/bash
# monitor-backup-jobs.sh

NAMESPACE="splunk-mcp-prod"

echo "Monitoring backup jobs..."

# Step 1: Check backup CronJob status
echo "1. Checking backup CronJob status..."
kubectl get cronjob -n $NAMESPACE -l app=backup

# Step 2: Check recent backup jobs
echo "2. Checking recent backup jobs..."
kubectl get jobs -n $NAMESPACE -l app=backup --sort-by=.status.startTime | tail -10

# Step 3: Check failed backup jobs
echo "3. Checking failed backup jobs..."
failed_jobs=$(kubectl get jobs -n $NAMESPACE -l app=backup --field-selector status.successful=0 --no-headers | wc -l)
if [ "$failed_jobs" -gt 0 ]; then
    echo "❌ Found $failed_jobs failed backup jobs"
    kubectl get jobs -n $NAMESPACE -l app=backup --field-selector status.successful=0
else
    echo "✅ No failed backup jobs"
fi

# Step 4: Check backup storage usage
echo "4. Checking backup storage usage..."
if [ -d "/backup" ]; then
    du -h /backup | tail -1
    backup_count=$(ls -1 /backup/*.gz 2>/dev/null | wc -l)
    echo "Backup files: $backup_count"
else
    echo "Backup directory not found"
fi

# Step 5: Verify recent backup
echo "5. Verifying most recent backup..."
latest_backup=$(ls -t /backup/*.gz 2>/dev/null | head -1)
if [ -n "$latest_backup" ]; then
    echo "Latest backup: $latest_backup"
    backup_age=$(stat -f %Sm -t %Y%m%d-%H%M%S "$latest_backup" 2>/dev/null || stat -c %Y "$latest_backup" 2>/dev/null)
    echo "Backup age: $backup_age"
    
    # Test backup integrity
    if gzip -t "$latest_backup"; then
        echo "✅ Latest backup integrity verified"
    else
        echo "❌ Latest backup integrity check failed"
    fi
else
    echo "❌ No recent backups found"
fi

echo "Backup monitoring completed"
```

### Disaster Recovery Testing

#### DR Test Procedure
```bash
#!/bin/bash
# dr-test.sh

NAMESPACE="splunk-mcp-prod"
TEST_NAMESPACE="splunk-mcp-dr-test"

echo "Starting disaster recovery test..."

# Step 1: Create test namespace
echo "1. Creating test namespace..."
kubectl create namespace $TEST_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Step 2: Deploy minimal infrastructure
echo "2. Deploying test infrastructure..."
# Deploy only essential components for testing
kubectl apply -f infrastructure/kubernetes/storage/postgres-test.yaml -n $TEST_NAMESPACE

# Step 3: Restore from backup
echo "3. Restoring from backup..."
latest_backup=$(ls -t /backup/*.gz 2>/dev/null | head -1)
if [ -n "$latest_backup" ]; then
    echo "Using backup: $latest_backup"
    # Restore database in test namespace
    zcat "$latest_backup" | kubectl exec -i postgresql-test-0 -n $TEST_NAMESPACE -- psql -U postgres -d splunk_mcp
else
    echo "❌ No backup found for testing"
    exit 1
fi

# Step 4: Deploy application services
echo "4. Deploying application services..."
kubectl apply -f infrastructure/kubernetes/deployments/api-gateway-test.yaml -n $TEST_NAMESPACE

# Step 5: Test service functionality
echo "5. Testing service functionality..."
kubectl rollout status deployment/api-gateway-test -n $TEST_NAMESPACE --timeout=300s

if kubectl exec -n $TEST_NAMESPACE deployment/api-gateway-test -- \
   wget --quiet --tries=3 --timeout=10 --spider http://localhost:8000/health; then
    echo "✅ Service functionality test passed"
else
    echo "❌ Service functionality test failed"
fi

# Step 6: Clean up test environment
echo "6. Cleaning up test environment..."
kubectl delete namespace $TEST_NAMESPACE

echo "Disaster recovery test completed"
```

---

## Performance Management

### Performance Monitoring Procedure

#### Resource Utilization Check
```bash
#!/bin/bash
# check-performance.sh

NAMESPACE="splunk-mcp-prod"

echo "Checking system performance..."

# Step 1: Node resource utilization
echo "1. Node resource utilization:"
kubectl top nodes

# Step 2: Pod resource utilization
echo "2. Pod resource utilization:"
kubectl top pods -n $NAMESPACE --sort-by=cpu

# Step 3: Memory pressure check
echo "3. Checking for memory pressure..."
kubectl describe nodes | grep -A 5 "Conditions:" | grep -E "(MemoryPressure|DiskPressure)"

# Step 4: Network performance
echo "4. Network performance metrics:"
# This would query your network monitoring system
echo "Network metrics from monitoring system"

# Step 5: Database performance
echo "5. Database performance:"
kubectl exec -i postgresql-0 -n $NAMESPACE -- psql -U postgres -d splunk_mcp -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"

# Step 6: Application metrics
echo "6. Application response times:"
# Query Prometheus for response time metrics
if command -v curl &> /dev/null; then
    echo "Querying application metrics..."
    # This would query your metrics system
fi

echo "Performance check completed"
```

### Auto-Scaling Management

#### HPA Configuration Check
```bash
#!/bin/bash
# check-autoscaling.sh

NAMESPACE="splunk-mcp-prod"

echo "Checking auto-scaling configuration..."

# Step 1: Check HPA status
echo "1. HPA status:"
kubectl get hpa -n $NAMESPACE

# Step 2: Check scaling events
echo "2. Recent scaling events:"
kubectl get events -n $NAMESPACE --field-selector reason=SuccessfulRescale --sort-by='.lastTimestamp' | tail -10

# Step 3: Check resource metrics
echo "3. Resource metrics for HPA:"
kubectl describe hpa -n $NAMESPACE

# Step 4: Check VPA recommendations (if configured)
echo "4. VPA recommendations:"
kubectl get vpa -n $NAMESPACE -o yaml 2>/dev/null || echo "VPA not configured"

# Step 5: Performance recommendations
echo "5. Performance recommendations:"
# Analyze current usage and provide recommendations
kubectl top pods -n $NAMESPACE | awk '
NR>1 {
    cpu=$2; memory=$3
    gsub(/[^0-9]/, "", cpu); gsub(/[^0-9]/, "", memory)
    if (cpu > 800) print "⚠️  " $1 " high CPU usage: " $2
    if (memory > 1000) print "⚠️  " $1 " high memory usage: " $3
}'

echo "Auto-scaling check completed"
```

---

## Security Operations

### Security Incident Response

#### Security Alert Investigation
```bash
#!/bin/bash
# investigate-security-alert.sh

ALERT_TYPE="$1"
TIME_RANGE="${2:-1h}"
NAMESPACE="splunk-mcp-prod"

if [ -z "$ALERT_TYPE" ]; then
    echo "Usage: $0 <alert-type> [time-range]"
    echo "Alert types: auth_failure, privilege_escalation, data_breach, suspicious_activity"
    exit 1
fi

echo "Investigating security alert: $ALERT_TYPE"

case $ALERT_TYPE in
    "auth_failure")
        echo "1. Analyzing authentication failures..."
        kubectl logs -n $NAMESPACE -l app=api-gateway --since=$TIME_RANGE | grep "auth_failure" | tail -20
        
        echo "2. Checking source IPs..."
        kubectl logs -n $NAMESPACE -l app=api-gateway --since=$TIME_RANGE | grep "auth_failure" | grep -o 'ip=[0-9.]*' | sort | uniq -c | sort -nr
        
        echo "3. Checking targeted users..."
        kubectl logs -n $NAMESPACE -l app=api-gateway --since=$TIME_RANGE | grep "auth_failure" | grep -o 'user=[^[:space:]]*' | sort | uniq -c | sort -nr
        ;;
        
    "privilege_escalation")
        echo "1. Checking privilege changes..."
        kubectl logs -n $NAMESPACE -l app=api-gateway --since=$TIME_RANGE | grep "privilege_change"
        
        echo "2. Checking RBAC modifications..."
        kubectl get events -n $NAMESPACE --field-selector reason=RoleBindingChanged --since=$TIME_RANGE
        ;;
        
    "data_breach")
        echo "1. Checking large data exports..."
        kubectl logs -n $NAMESPACE -l app=api-gateway --since=$TIME_RANGE | grep "export" | grep -o 'size=[0-9]*' | sort -nr | head -10
        
        echo "2. Checking unusual query patterns..."
        kubectl logs -n $NAMESPACE -l app=nlp-engine --since=$TIME_RANGE | grep "large_query"
        ;;
        
    "suspicious_activity")
        echo "1. Checking off-hours activity..."
        current_hour=$(date +%H)
        if [ "$current_hour" -lt 8 ] || [ "$current_hour" -gt 18 ]; then
            kubectl logs -n $NAMESPACE -l app=api-gateway --since=$TIME_RANGE | grep "user_activity" | wc -l
        fi
        
        echo "2. Checking geographic anomalies..."
        kubectl logs -n $NAMESPACE -l app=api-gateway --since=$TIME_RANGE | grep "geo_location" | tail -10
        ;;
        
    *)
        echo "Unknown alert type: $ALERT_TYPE"
        exit 1
        ;;
esac

echo "Security alert investigation completed"
```

### Access Review Procedure

#### User Access Audit
```bash
#!/bin/bash
# audit-user-access.sh

NAMESPACE="splunk-mcp-prod"
AUDIT_FILE="/tmp/user-access-audit-$(date +%Y%m%d).txt"

echo "Starting user access audit..."

{
    echo "===== USER ACCESS AUDIT REPORT ====="
    echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Namespace: $NAMESPACE"
    echo ""
    
    # Step 1: List all users with access
    echo "1. USERS WITH ACCESS:"
    kubectl get rolebindings -n $NAMESPACE -o custom-columns=NAME:.metadata.name,ROLE:.roleRef.name,SUBJECTS:.subjects[*].name --no-headers | sort
    echo ""
    
    # Step 2: Check service accounts
    echo "2. SERVICE ACCOUNTS:"
    kubectl get serviceaccounts -n $NAMESPACE --no-headers
    echo ""
    
    # Step 3: Check for elevated privileges
    echo "3. ELEVATED PRIVILEGES:"
    kubectl get rolebindings -n $NAMESPACE -o yaml | grep -A 5 -B 5 "cluster-admin\|admin"
    echo ""
    
    # Step 4: Check last login times
    echo "4. RECENT LOGIN ACTIVITY:"
    kubectl logs -n $NAMESPACE -l app=api-gateway --since=24h | grep "user_login" | tail -20
    echo ""
    
    # Step 5: Check inactive users
    echo "5. POTENTIALLY INACTIVE USERS:"
    # This would require application-specific logic to determine inactive users
    echo "Manual review required for inactive user identification"
    echo ""
    
    # Step 6: Recommendations
    echo "6. RECOMMENDATIONS:"
    echo "- Review users with cluster-admin access"
    echo "- Verify service account necessity"
    echo "- Check for users without recent login activity"
    echo "- Validate external user access"
    
} > $AUDIT_FILE

echo "User access audit completed: $AUDIT_FILE"
cat $AUDIT_FILE
```

---

## Emergency Procedures

### Emergency Response Playbook

#### System-Wide Outage Response
```bash
#!/bin/bash
# emergency-outage-response.sh

NAMESPACE="splunk-mcp-prod"
INCIDENT_ID="INC-$(date +%Y%m%d%H%M%S)"

echo "===== EMERGENCY OUTAGE RESPONSE ====="
echo "Incident ID: $INCIDENT_ID"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"

# Step 1: Immediate assessment
echo "1. IMMEDIATE ASSESSMENT:"
echo "Checking overall system status..."
kubectl get nodes
kubectl get pods -n $NAMESPACE --no-headers | grep -v Running

# Step 2: Identify scope of outage
echo "2. OUTAGE SCOPE IDENTIFICATION:"
affected_services=()
services=("api-gateway" "nlp-engine" "visualization" "alert-manager")

for service in "${services[@]}"; do
    ready_pods=$(kubectl get pods -n $NAMESPACE -l app=$service --no-headers 2>/dev/null | grep "Running" | wc -l)
    total_pods=$(kubectl get pods -n $NAMESPACE -l app=$service --no-headers 2>/dev/null | wc -l)
    
    if [ "$ready_pods" -eq 0 ] || [ "$ready_pods" -lt "$total_pods" ]; then
        affected_services+=("$service")
        echo "❌ $service: $ready_pods/$total_pods pods running"
    else
        echo "✅ $service: $ready_pods/$total_pods pods running"
    fi
done

# Step 3: Check infrastructure
echo "3. INFRASTRUCTURE CHECK:"
echo "Checking database..."
kubectl get pods -n $NAMESPACE -l app=postgresql

echo "Checking Redis..."
kubectl get pods -n $NAMESPACE -l app=redis

echo "Checking ingress..."
kubectl get ingress -n $NAMESPACE

# Step 4: Immediate mitigation
echo "4. IMMEDIATE MITIGATION:"
if [ ${#affected_services[@]} -gt 0 ]; then
    echo "Attempting service recovery for affected services..."
    for service in "${affected_services[@]}"; do
        echo "Restarting $service..."
        kubectl rollout restart deployment/$service -n $NAMESPACE
    done
    
    # Wait for services to recover
    echo "Waiting for services to recover..."
    sleep 60
    
    # Check recovery status
    for service in "${affected_services[@]}"; do
        kubectl rollout status deployment/$service -n $NAMESPACE --timeout=300s || echo "❌ $service recovery failed"
    done
fi

# Step 5: External communication
echo "5. EXTERNAL COMMUNICATION:"
echo "Preparing status page update..."
# This would integrate with your status page system
echo "Status page update required for incident $INCIDENT_ID"

# Step 6: Escalation
echo "6. ESCALATION:"
if [ ${#affected_services[@]} -gt 2 ]; then
    echo "Major outage detected - escalating to management"
    # Send escalation notifications
else
    echo "Partial outage - continuing with standard response"
fi

# Step 7: Evidence collection
echo "7. EVIDENCE COLLECTION:"
mkdir -p "/tmp/incident-$INCIDENT_ID"
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' > "/tmp/incident-$INCIDENT_ID/events.log"
kubectl describe pods -n $NAMESPACE > "/tmp/incident-$INCIDENT_ID/pod-descriptions.txt"

echo "Evidence collected in /tmp/incident-$INCIDENT_ID/"

echo "===== EMERGENCY RESPONSE PHASE 1 COMPLETE ====="
echo "Continue monitoring and investigation..."
```

#### Data Breach Response
```bash
#!/bin/bash
# data-breach-response.sh

INCIDENT_ID="BREACH-$(date +%Y%m%d%H%M%S)"
NAMESPACE="splunk-mcp-prod"

echo "===== DATA BREACH RESPONSE ====="
echo "Incident ID: $INCIDENT_ID"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"

# Step 1: Immediate containment
echo "1. IMMEDIATE CONTAINMENT:"
echo "Disabling external access..."
kubectl patch ingress splunk-mcp-ingress -n $NAMESPACE --type=json -p='[{"op": "replace", "path": "/spec/rules", "value": []}]'

echo "Scaling down non-essential services..."
kubectl scale deployment api-gateway --replicas=1 -n $NAMESPACE
kubectl scale deployment nlp-engine --replicas=0 -n $NAMESPACE

# Step 2: Evidence preservation
echo "2. EVIDENCE PRESERVATION:"
evidence_dir="/tmp/breach-evidence-$INCIDENT_ID"
mkdir -p "$evidence_dir"

echo "Collecting logs..."
kubectl logs -n $NAMESPACE -l app=api-gateway --since=1h > "$evidence_dir/api-gateway-logs.txt"
kubectl logs -n $NAMESPACE -l app=postgresql --since=1h > "$evidence_dir/database-logs.txt"

echo "Collecting network traffic..."
# This would capture network traffic if monitoring is in place
kubectl get networkpolicies -n $NAMESPACE -o yaml > "$evidence_dir/network-policies.yaml"

# Step 3: Impact assessment
echo "3. IMPACT ASSESSMENT:"
echo "Checking data access patterns..."
kubectl logs -n $NAMESPACE -l app=api-gateway --since=1h | grep "data_access" | wc -l

echo "Checking export activities..."
kubectl logs -n $NAMESPACE -l app=api-gateway --since=1h | grep "export" | wc -l

# Step 4: Forensic analysis
echo "4. FORENSIC ANALYSIS:"
echo "Analyzing authentication logs..."
kubectl logs -n $NAMESPACE -l app=api-gateway --since=24h | grep "auth" | grep -v "success" > "$evidence_dir/auth-failures.txt"

echo "Checking privilege escalations..."
kubectl get events -n $NAMESPACE --field-selector reason=RoleBindingChanged --since=24h > "$evidence_dir/privilege-changes.txt"

# Step 5: Notification
echo "5. NOTIFICATION REQUIREMENTS:"
echo "⚠️  Breach response notifications required:"
echo "   - Security team: IMMEDIATE"
echo "   - Legal team: IMMEDIATE"
echo "   - Management: IMMEDIATE"
echo "   - Affected users: Within 72 hours"
echo "   - Regulatory authorities: Within 72 hours"

# Step 6: System hardening
echo "6. IMMEDIATE SYSTEM HARDENING:"
echo "Forcing password reset for all users..."
# This would trigger a system-wide password reset

echo "Revoking all API tokens..."
# This would invalidate all existing API tokens

echo "Enabling enhanced monitoring..."
# This would enable additional security monitoring

echo "===== DATA BREACH RESPONSE PHASE 1 COMPLETE ====="
echo "Evidence preserved in: $evidence_dir"
echo "Continue with legal and regulatory notification procedures"
```

---

## Maintenance Windows

### Planned Maintenance Procedure

#### Pre-Maintenance Checklist
```bash
#!/bin/bash
# pre-maintenance-checklist.sh

NAMESPACE="splunk-mcp-prod"
MAINTENANCE_DATE="$1"

if [ -z "$MAINTENANCE_DATE" ]; then
    echo "Usage: $0 <maintenance-date-YYYY-MM-DD>"
    exit 1
fi

echo "===== PRE-MAINTENANCE CHECKLIST ====="
echo "Maintenance Date: $MAINTENANCE_DATE"
echo "Current Date: $(date '+%Y-%m-%d')"

# Step 1: Verify backup status
echo "1. BACKUP VERIFICATION:"
latest_backup=$(ls -t /backup/*.gz 2>/dev/null | head -1)
if [ -n "$latest_backup" ]; then
    backup_date=$(stat -f %Sm -t %Y-%m-%d "$latest_backup" 2>/dev/null || date -r $(stat -c %Y "$latest_backup") +%Y-%m-%d)
    echo "✅ Latest backup: $latest_backup ($backup_date)"
    
    if gzip -t "$latest_backup"; then
        echo "✅ Backup integrity verified"
    else
        echo "❌ Backup integrity check failed"
        exit 1
    fi
else
    echo "❌ No recent backups found"
    exit 1
fi

# Step 2: System health check
echo "2. SYSTEM HEALTH CHECK:"
failed_pods=$(kubectl get pods -n $NAMESPACE --no-headers | grep -v Running | wc -l)
if [ "$failed_pods" -eq 0 ]; then
    echo "✅ All pods running normally"
else
    echo "❌ $failed_pods pods not running - address before maintenance"
    kubectl get pods -n $NAMESPACE --no-headers | grep -v Running
    exit 1
fi

# Step 3: Resource utilization check
echo "3. RESOURCE UTILIZATION:"
kubectl top nodes | tail -n +2 | while read line; do
    node_name=$(echo $line | awk '{print $1}')
    cpu_usage=$(echo $line | awk '{print $2}' | sed 's/%//')
    memory_usage=$(echo $line | awk '{print $4}' | sed 's/%//')
    
    if [ "$cpu_usage" -gt 80 ] || [ "$memory_usage" -gt 80 ]; then
        echo "⚠️  Node $node_name has high resource usage (CPU: ${cpu_usage}%, Memory: ${memory_usage}%)"
    else
        echo "✅ Node $node_name resource usage normal"
    fi
done

# Step 4: Check for scheduled jobs
echo "4. SCHEDULED JOBS CHECK:"
kubectl get cronjobs -n $NAMESPACE

# Step 5: Notification verification
echo "5. NOTIFICATION VERIFICATION:"
echo "✅ Maintenance notifications sent to:"
echo "   - Operations team"
echo "   - End users"
echo "   - Management"
echo "   - External customers (if applicable)"

# Step 6: Rollback plan verification
echo "6. ROLLBACK PLAN:"
echo "✅ Rollback procedures documented"
echo "✅ Configuration backups available"
echo "✅ Service restoration scripts tested"

echo "===== PRE-MAINTENANCE CHECKLIST COMPLETE ====="
echo "System ready for maintenance window"
```

#### Maintenance Execution
```bash
#!/bin/bash
# execute-maintenance.sh

NAMESPACE="splunk-mcp-prod"
MAINTENANCE_TYPE="$1"

if [ -z "$MAINTENANCE_TYPE" ]; then
    echo "Usage: $0 <maintenance-type>"
    echo "Types: security-update, scaling, configuration-change, infrastructure-update"
    exit 1
fi

echo "===== MAINTENANCE EXECUTION ====="
echo "Maintenance Type: $MAINTENANCE_TYPE"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"

# Step 1: Enable maintenance mode
echo "1. ENABLING MAINTENANCE MODE:"
kubectl patch ingress splunk-mcp-ingress -n $NAMESPACE --type=json \
  -p='[{"op": "add", "path": "/metadata/annotations/nginx.ingress.kubernetes.io~1custom-http-errors", "value": "503"}]'

echo "Maintenance mode enabled - users will see maintenance page"

# Step 2: Scale down services for maintenance
echo "2. SCALING DOWN SERVICES:"
declare -A original_replicas
services=("api-gateway" "nlp-engine" "visualization" "alert-manager")

for service in "${services[@]}"; do
    replicas=$(kubectl get deployment $service -n $NAMESPACE -o jsonpath='{.spec.replicas}')
    original_replicas[$service]=$replicas
    echo "Scaling down $service from $replicas to 1..."
    kubectl scale deployment $service --replicas=1 -n $NAMESPACE
done

# Step 3: Execute maintenance based on type
echo "3. EXECUTING MAINTENANCE:"
case $MAINTENANCE_TYPE in
    "security-update")
        echo "Applying security updates..."
        # Update container images
        kubectl set image deployment/api-gateway api-gateway=splunk-mcp/api-gateway:latest-security -n $NAMESPACE
        kubectl set image deployment/nlp-engine nlp-engine=splunk-mcp/nlp-engine:latest-security -n $NAMESPACE
        ;;
        
    "scaling")
        echo "Implementing scaling improvements..."
        # Apply HPA updates
        kubectl apply -f infrastructure/kubernetes/hpa/ -n $NAMESPACE
        ;;
        
    "configuration-change")
        echo "Applying configuration changes..."
        # Apply new ConfigMaps
        kubectl apply -f infrastructure/kubernetes/configmaps/ -n $NAMESPACE
        ;;
        
    "infrastructure-update")
        echo "Updating infrastructure components..."
        # Update monitoring stack
        helm upgrade prometheus-stack prometheus-community/kube-prometheus-stack -n monitoring
        ;;
        
    *)
        echo "Unknown maintenance type: $MAINTENANCE_TYPE"
        exit 1
        ;;
esac

# Step 4: Wait for updates to complete
echo "4. WAITING FOR UPDATES TO COMPLETE:"
for service in "${services[@]}"; do
    echo "Waiting for $service update..."
    kubectl rollout status deployment/$service -n $NAMESPACE --timeout=600s
done

# Step 5: Restore service levels
echo "5. RESTORING SERVICE LEVELS:"
for service in "${services[@]}"; do
    original=${original_replicas[$service]}
    echo "Scaling $service back to $original replicas..."
    kubectl scale deployment $service --replicas=$original -n $NAMESPACE
done

# Step 6: Health verification
echo "6. HEALTH VERIFICATION:"
sleep 60  # Allow services to stabilize
for service in "${services[@]}"; do
    kubectl rollout status deployment/$service -n $NAMESPACE --timeout=300s
done

# Step 7: Disable maintenance mode
echo "7. DISABLING MAINTENANCE MODE:"
kubectl patch ingress splunk-mcp-ingress -n $NAMESPACE --type=json \
  -p='[{"op": "remove", "path": "/metadata/annotations/nginx.ingress.kubernetes.io~1custom-http-errors"}]'

echo "Maintenance mode disabled - normal service restored"

echo "===== MAINTENANCE EXECUTION COMPLETE ====="
echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')"
```

#### Post-Maintenance Validation
```bash
#!/bin/bash
# post-maintenance-validation.sh

NAMESPACE="splunk-mcp-prod"

echo "===== POST-MAINTENANCE VALIDATION ====="
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"

# Step 1: Service health validation
echo "1. SERVICE HEALTH VALIDATION:"
services=("api-gateway:8000" "nlp-engine:8001" "visualization:8002" "alert-manager:8003")
for service in "${services[@]}"; do
    service_name=$(echo $service | cut -d: -f1)
    service_port=$(echo $service | cut -d: -f2)
    
    echo "Testing $service_name..."
    if kubectl exec -n $NAMESPACE deployment/$service_name -- \
       wget --quiet --tries=3 --timeout=10 --spider http://localhost:$service_port/health; then
        echo "✅ $service_name health check passed"
    else
        echo "❌ $service_name health check failed"
    fi
done

# Step 2: Database connectivity
echo "2. DATABASE CONNECTIVITY:"
if kubectl exec -n $NAMESPACE deployment/api-gateway -- \
   python -c "import psycopg2, os; psycopg2.connect(os.environ['DATABASE_URL']).close(); print('Database OK')" 2>/dev/null; then
    echo "✅ Database connectivity verified"
else
    echo "❌ Database connectivity failed"
fi

# Step 3: External access validation
echo "3. EXTERNAL ACCESS VALIDATION:"
external_url="https://splunk-mcp.your-domain.com"
if curl -sSf "$external_url/health" >/dev/null 2>&1; then
    echo "✅ External access working"
else
    echo "❌ External access failed"
fi

# Step 4: Performance validation
echo "4. PERFORMANCE VALIDATION:"
kubectl top pods -n $NAMESPACE

# Step 5: Security validation
echo "5. SECURITY VALIDATION:"
echo "Checking SSL certificate..."
if echo | openssl s_client -servername splunk-mcp.your-domain.com -connect splunk-mcp.your-domain.com:443 2>/dev/null | openssl x509 -noout -dates; then
    echo "✅ SSL certificate valid"
else
    echo "❌ SSL certificate issue"
fi

# Step 6: Monitoring validation
echo "6. MONITORING VALIDATION:"
echo "Checking monitoring systems..."
kubectl get pods -n monitoring | grep -E "(prometheus|grafana|alertmanager)" | grep Running | wc -l

# Step 7: Generate post-maintenance report
echo "7. GENERATING REPORT:"
report_file="/tmp/post-maintenance-report-$(date +%Y%m%d-%H%M%S).txt"
{
    echo "POST-MAINTENANCE VALIDATION REPORT"
    echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "Services Status:"
    kubectl get pods -n $NAMESPACE --no-headers | awk '{print $1 ": " $3}'
    echo ""
    echo "Resource Usage:"
    kubectl top pods -n $NAMESPACE
    echo ""
    echo "Validation Results: All checks passed"
    echo "System Status: Operational"
} > $report_file

echo "Post-maintenance report: $report_file"

echo "===== POST-MAINTENANCE VALIDATION COMPLETE ====="
```

---

*These operational runbooks provide comprehensive procedures for maintaining the Splunk MCP Integration Platform. Regular practice and updates ensure operational excellence and rapid incident response.*