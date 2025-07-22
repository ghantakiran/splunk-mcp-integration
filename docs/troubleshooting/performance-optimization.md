# Performance Optimization Guide

## Overview

This guide provides comprehensive performance optimization strategies for the Splunk MCP Integration platform, covering database optimization, application tuning, caching strategies, and infrastructure scaling.

## Performance Monitoring

### Key Performance Indicators (KPIs)

#### Application Metrics
- **API Response Time**: Target <100ms (95th percentile)
- **Query Processing Time**: Target <2s average
- **Dashboard Load Time**: Target <3s
- **Document Generation Time**: Target <30s
- **Concurrent Users**: Support 1000+ simultaneous users
- **Throughput**: 10,000+ requests/hour per service

#### Infrastructure Metrics
- **CPU Utilization**: <70% under normal load
- **Memory Usage**: <80% of available RAM
- **Disk I/O**: <80% utilization
- **Network Latency**: <10ms between services
- **Database Connections**: <80% of pool size

### Monitoring Setup

#### Prometheus Metrics Collection
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'splunk-mcp-services'
    static_configs:
      - targets: 
        - 'api-gateway:8000'
        - 'nlp-engine:8001'
        - 'visualization:8002'
        - 'alert-manager:8003'
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### Custom Application Metrics
```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary
import time
from functools import wraps

# Request metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('app_request_duration_seconds', 'Request latency', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('app_active_connections', 'Active database connections')
CACHE_HIT_RATE = Gauge('app_cache_hit_rate', 'Cache hit rate percentage')

# Business metrics
QUERIES_PROCESSED = Counter('nlp_queries_total', 'Total NLP queries processed', ['status'])
QUERY_PROCESSING_TIME = Histogram('nlp_query_duration_seconds', 'NLP query processing time')
CHARTS_GENERATED = Counter('visualization_charts_total', 'Total charts generated', ['type'])
ALERTS_TRIGGERED = Counter('alerts_triggered_total', 'Total alerts triggered', ['severity'])

def track_performance(metric_name: str):
    """Decorator to track function performance"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(method='async', endpoint=metric_name, status='success').inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(method='async', endpoint=metric_name, status='error').inc()
                raise
            finally:
                REQUEST_LATENCY.labels(method='async', endpoint=metric_name).observe(time.time() - start_time)
        return wrapper
    return decorator

def update_business_metrics():
    """Update business-specific metrics"""
    # Cache hit rate calculation
    cache_hits = get_cache_hits()
    cache_misses = get_cache_misses()
    if cache_hits + cache_misses > 0:
        hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100
        CACHE_HIT_RATE.set(hit_rate)
    
    # Active connections
    from app.core.database import engine
    ACTIVE_CONNECTIONS.set(engine.pool.checkedout())
```

## Database Optimization

### PostgreSQL Performance Tuning

#### Configuration Optimization
```sql
-- postgresql.conf optimizations
-- Memory settings
shared_buffers = 256MB                    -- 25% of RAM for dedicated server
effective_cache_size = 1GB                -- 75% of available RAM
work_mem = 64MB                           -- For complex queries
maintenance_work_mem = 256MB              -- For VACUUM, CREATE INDEX

-- Checkpoint settings
wal_buffers = 16MB
checkpoint_completion_target = 0.9
checkpoint_timeout = 10min

-- Connection settings
max_connections = 200
shared_preload_libraries = 'pg_stat_statements'

-- Query planner settings
random_page_cost = 1.1                    -- For SSD storage
effective_io_concurrency = 200            -- For SSD storage
default_statistics_target = 100
```

#### Index Optimization
```sql
-- Query to find missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100
  AND correlation < 0.1
ORDER BY n_distinct DESC;

-- Create performance indexes
CREATE INDEX CONCURRENTLY idx_queries_user_created 
ON queries (user_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_alerts_status_severity 
ON alerts (status, severity) WHERE status = 'active';

CREATE INDEX CONCURRENTLY idx_dashboards_user_updated 
ON dashboards (user_id, updated_at DESC);

-- Partial indexes for common queries
CREATE INDEX CONCURRENTLY idx_sessions_active 
ON user_sessions (user_id, created_at) 
WHERE expires_at > NOW();

-- Composite indexes for complex queries
CREATE INDEX CONCURRENTLY idx_query_history_complex 
ON query_history (user_id, conversation_id, created_at DESC);
```

#### Query Optimization
```sql
-- Enable query statistics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries
SELECT query, calls, total_time, rows, 
       100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- Find queries with low cache hit rates
SELECT query, calls, total_time,
       shared_blks_hit, shared_blks_read,
       100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
WHERE shared_blks_hit + shared_blks_read > 0
ORDER BY hit_percent ASC
LIMIT 10;

-- Optimize specific queries
EXPLAIN (ANALYZE, BUFFERS) 
SELECT q.*, u.username 
FROM queries q 
JOIN users u ON q.user_id = u.id 
WHERE q.created_at > NOW() - INTERVAL '1 hour'
ORDER BY q.created_at DESC;
```

#### Connection Pool Optimization
```python
# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

def create_optimized_engine(database_url: str):
    return create_engine(
        database_url,
        # Connection pool settings
        poolclass=QueuePool,
        pool_size=20,                    # Base connections
        max_overflow=30,                 # Additional connections
        pool_pre_ping=True,              # Validate connections
        pool_recycle=3600,               # Recycle after 1 hour
        pool_timeout=30,                 # Wait timeout
        
        # Query optimization
        echo=False,                      # Disable SQL logging in production
        future=True,                     # Use SQLAlchemy 2.0 style
        
        # Connection options
        connect_args={
            "application_name": "splunk_mcp",
            "options": "-c timezone=UTC -c statement_timeout=30000"
        }
    )

# Monitor connection pool
def monitor_connection_pool(engine):
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
        "invalid": pool.invalid(),
        "total": pool.size() + pool.overflow()
    }
```

### Redis Optimization

#### Configuration Tuning
```conf
# redis.conf optimizations
# Memory settings
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence settings for caching
save ""                                   # Disable RDB snapshots
appendonly no                            # Disable AOF for cache-only usage

# Network settings
tcp-keepalive 300
timeout 0

# Performance settings
tcp-backlog 511
databases 16
hz 10

# Slow log settings
slowlog-log-slower-than 10000            # Log queries > 10ms
slowlog-max-len 128
```

#### Cache Optimization Strategies
```python
# app/core/cache.py
import redis
import json
import pickle
from typing import Any, Optional
from functools import wraps
import hashlib

class OptimizedCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get_or_set(self, key: str, factory, ttl: int = 300):
        """Get from cache or set using factory function"""
        value = await self.redis.get(key)
        if value is not None:
            return pickle.loads(value)
        
        # Generate value
        result = await factory() if callable(factory) else factory
        await self.redis.setex(key, ttl, pickle.dumps(result))
        return result
    
    def cached_query(self, ttl: int = 300):
        """Decorator for caching database queries"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                cache_key = self.cache_key(func.__name__, *args, **kwargs)
                return await self.get_or_set(cache_key, lambda: func(*args, **kwargs), ttl)
            return wrapper
        return decorator

# Cache warming strategies
async def warm_cache():
    """Pre-populate frequently accessed data"""
    cache = OptimizedCache(redis_client)
    
    # Warm user session cache
    active_users = await get_active_users()
    for user in active_users:
        cache_key = f"user_profile:{user.id}"
        await cache.get_or_set(cache_key, lambda: get_user_profile(user.id), 3600)
    
    # Warm dashboard cache
    popular_dashboards = await get_popular_dashboards()
    for dashboard in popular_dashboards:
        cache_key = f"dashboard:{dashboard.id}"
        await cache.get_or_set(cache_key, lambda: get_dashboard_data(dashboard.id), 1800)
```

## Application Performance Optimization

### FastAPI Optimization

#### Async/Await Best Practices
```python
# app/api/v1/endpoints/optimized.py
from fastapi import APIRouter, Depends, BackgroundTasks
import asyncio
from typing import List
from app.core.cache import OptimizedCache

router = APIRouter()

# Optimize database queries with async
@router.get("/users/{user_id}/dashboard-summary")
async def get_user_dashboard_summary(user_id: int):
    # Parallel data fetching
    user_task = get_user_profile(user_id)
    dashboards_task = get_user_dashboards(user_id)
    recent_queries_task = get_recent_queries(user_id, limit=10)
    
    # Wait for all tasks concurrently
    user, dashboards, recent_queries = await asyncio.gather(
        user_task, dashboards_task, recent_queries_task
    )
    
    return {
        "user": user,
        "dashboard_count": len(dashboards),
        "dashboards": dashboards,
        "recent_queries": recent_queries
    }

# Optimize with caching
@router.get("/analytics/performance-metrics")
@cached_query(ttl=300)  # Cache for 5 minutes
async def get_performance_metrics():
    # Expensive aggregation query
    metrics = await calculate_performance_metrics()
    return metrics

# Background task optimization
@router.post("/reports/generate")
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks
):
    # Start generation in background
    background_tasks.add_task(
        generate_report_async,
        request.report_id,
        request.parameters
    )
    
    return {"status": "generating", "report_id": request.report_id}

# Optimize response serialization
from fastapi.encoders import jsonable_encoder
from fastapi.responses import ORJSONResponse

@router.get("/large-dataset", response_class=ORJSONResponse)
async def get_large_dataset():
    # Use faster JSON encoder for large responses
    data = await fetch_large_dataset()
    return ORJSONResponse(content=jsonable_encoder(data))
```

#### Request/Response Optimization
```python
# app/core/middleware.py
from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
import gzip
import time

def add_performance_middleware(app: FastAPI):
    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    
    # Response time middleware
    @app.middleware("http")
    async def add_response_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Cache headers middleware
    @app.middleware("http")
    async def add_cache_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Add cache headers for static content
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=86400"
        
        # Add no-cache headers for API responses
        elif request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        
        return response

# Request body size optimization
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_size:
            raise HTTPException(413, "Request too large")
        return await call_next(request)
```

### Memory Optimization

#### Memory Usage Patterns
```python
# app/core/memory.py
import gc
import psutil
import asyncio
from typing import Dict, Any
import weakref

class MemoryOptimizer:
    def __init__(self):
        self.object_pool = weakref.WeakValueDictionary()
        self.gc_threshold = (700, 10, 10)
    
    def configure_gc(self):
        """Optimize garbage collection settings"""
        gc.set_threshold(*self.gc_threshold)
        gc.enable()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss": memory_info.rss / 1024 / 1024,  # MB
            "vms": memory_info.vms / 1024 / 1024,  # MB
            "percent": process.memory_percent(),
            "gc_counts": gc.get_count(),
            "gc_stats": gc.get_stats()
        }
    
    async def memory_cleanup_task(self):
        """Periodic memory cleanup"""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            
            # Force garbage collection
            collected = gc.collect()
            
            # Log memory statistics
            stats = self.get_memory_stats()
            if stats["percent"] > 80:
                logger.warning(f"High memory usage: {stats}")
            
            # Clear weak references
            self.object_pool.clear()

# Memory-efficient data processing
class StreamProcessor:
    """Process large datasets in chunks"""
    
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
    
    async def process_large_dataset(self, query_func, process_func):
        """Process data in chunks to avoid memory issues"""
        offset = 0
        while True:
            # Fetch chunk
            chunk = await query_func(offset=offset, limit=self.chunk_size)
            if not chunk:
                break
            
            # Process chunk
            await process_func(chunk)
            
            # Clear chunk from memory
            del chunk
            offset += self.chunk_size
            
            # Force garbage collection periodically
            if offset % (self.chunk_size * 10) == 0:
                gc.collect()
```

## Caching Strategies

### Multi-Level Caching

#### Application-Level Caching
```python
# app/core/cache_layers.py
from functools import lru_cache
import asyncio
from typing import Dict, Any, Optional

class MultiLevelCache:
    def __init__(self, redis_client, local_cache_size: int = 1000):
        self.redis = redis_client
        self.local_cache_size = local_cache_size
        
    # L1 Cache: In-memory LRU cache
    @lru_cache(maxsize=1000)
    def get_l1_cache(self, key: str) -> Optional[Any]:
        return None  # Placeholder for actual implementation
    
    # L2 Cache: Redis
    async def get_l2_cache(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        return pickle.loads(value) if value else None
    
    async def set_l2_cache(self, key: str, value: Any, ttl: int = 300):
        await self.redis.setex(key, ttl, pickle.dumps(value))
    
    # L3 Cache: Database query result cache
    async def get_l3_cache(self, query_func, *args, **kwargs):
        return await query_func(*args, **kwargs)
    
    async def get(self, key: str, factory_func=None, ttl: int = 300):
        """Get value from multi-level cache"""
        # Try L1 cache first
        value = self.get_l1_cache(key)
        if value is not None:
            return value
        
        # Try L2 cache (Redis)
        value = await self.get_l2_cache(key)
        if value is not None:
            # Update L1 cache
            self.get_l1_cache.__wrapped__(self, key, value)
            return value
        
        # Generate value using factory function
        if factory_func:
            value = await factory_func()
            
            # Update all cache levels
            await self.set_l2_cache(key, value, ttl)
            self.get_l1_cache.__wrapped__(self, key, value)
            
            return value
        
        return None

# Smart cache invalidation
class CacheInvalidation:
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.invalidation_patterns = {
            "user": ["user:{user_id}:*", "dashboard:user:{user_id}:*"],
            "dashboard": ["dashboard:{dashboard_id}:*", "user:*:dashboards"],
            "query": ["query:{query_id}:*", "user:{user_id}:queries:*"]
        }
    
    async def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a user"""
        patterns = [p.format(user_id=user_id) for p in self.invalidation_patterns["user"]]
        for pattern in patterns:
            keys = await self.cache.redis.keys(pattern)
            if keys:
                await self.cache.redis.delete(*keys)
    
    async def invalidate_dashboard_cache(self, dashboard_id: int, user_id: int):
        """Invalidate dashboard-related cache entries"""
        patterns = [
            p.format(dashboard_id=dashboard_id, user_id=user_id) 
            for p in self.invalidation_patterns["dashboard"]
        ]
        for pattern in patterns:
            keys = await self.cache.redis.keys(pattern)
            if keys:
                await self.cache.redis.delete(*keys)
```

#### Query Result Caching
```python
# app/core/query_cache.py
from sqlalchemy import event
from sqlalchemy.engine import Engine
import hashlib
import json

class QueryResultCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = {
            "user_data": 3600,      # 1 hour
            "dashboard_data": 1800,  # 30 minutes
            "query_results": 600,    # 10 minutes
            "system_stats": 300,     # 5 minutes
        }
    
    def generate_query_key(self, query: str, params: dict = None) -> str:
        """Generate deterministic cache key for query"""
        query_normalized = query.strip().lower()
        params_str = json.dumps(params or {}, sort_keys=True)
        key_data = f"{query_normalized}:{params_str}"
        return f"query_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get_cached_result(self, query: str, params: dict = None):
        """Get cached query result"""
        cache_key = self.generate_query_key(query, params)
        result = await self.redis.get(cache_key)
        return pickle.loads(result) if result else None
    
    async def cache_result(self, query: str, params: dict, result: Any, 
                          cache_type: str = "query_results"):
        """Cache query result"""
        cache_key = self.generate_query_key(query, params)
        ttl = self.cache_ttl.get(cache_type, 600)
        await self.redis.setex(cache_key, ttl, pickle.dumps(result))

# Automatic query caching decorator
def cached_database_query(cache_type: str = "query_results"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = QueryResultCache(redis_client)
            
            # Generate cache key from function and arguments
            cache_key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            
            # Try to get from cache
            result = await cache.get_cached_result(cache_key)
            if result is not None:
                return result
            
            # Execute query and cache result
            result = await func(*args, **kwargs)
            await cache.cache_result(cache_key, {}, result, cache_type)
            
            return result
        return wrapper
    return decorator
```

## Infrastructure Scaling

### Horizontal Scaling

#### Service Scaling Strategy
```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  api-gateway:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3

  nlp-engine:
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2G
          cpus: '1.5'
        reservations:
          memory: 1G
          cpus: '0.75'

  visualization:
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1.5G
          cpus: '1.0'
        reservations:
          memory: 750M
          cpus: '0.5'

  # Load balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx-scaled.conf:/etc/nginx/nginx.conf
    depends_on:
      - api-gateway
```

#### Load Balancer Configuration
```nginx
# nginx/nginx-scaled.conf
upstream api_gateway_backend {
    least_conn;
    server api-gateway-1:8000 max_fails=3 fail_timeout=30s;
    server api-gateway-2:8000 max_fails=3 fail_timeout=30s;
    server api-gateway-3:8000 max_fails=3 fail_timeout=30s;
}

upstream nlp_engine_backend {
    least_conn;
    server nlp-engine-1:8001 max_fails=3 fail_timeout=30s;
    server nlp-engine-2:8001 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    
    location /api/ {
        proxy_pass http://api_gateway_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Connection pooling
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Health checks
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_next_upstream_tries 3;
        proxy_next_upstream_timeout 10s;
    }
    
    location /nlp/ {
        proxy_pass http://nlp_engine_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Longer timeout for NLP processing
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

### Auto-scaling Configuration

#### Kubernetes HPA
```yaml
# kubernetes/hpa/api-gateway-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 2
        periodSeconds: 60
```

## Performance Testing

### Load Testing with Locust

#### Comprehensive Load Test
```python
# performance/load_test.py
from locust import HttpUser, task, between, events
import random
import json
import time

class PerformanceTestUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and setup user session"""
        self.auth_token = self.login()
        self.conversation_id = f"perf_test_{random.randint(1000, 9999)}"
    
    def login(self):
        """Authenticate user"""
        response = self.client.post("/auth/login", json={
            "username": f"test_user_{random.randint(1, 100)}",
            "password": "test_password"
        })
        if response.status_code == 200:
            return response.json()["data"]["access_token"]
        return None
    
    @task(10)
    def process_nlp_query(self):
        """Test NLP query processing performance"""
        queries = [
            "show me errors from the last hour",
            "count events by source",
            "find failed login attempts",
            "display performance metrics",
            "analyze network traffic patterns"
        ]
        
        with self.client.post("/nlp/process-query",
                            headers={"Authorization": f"Bearer {self.auth_token}"},
                            json={
                                "query": random.choice(queries),
                                "conversation_id": self.conversation_id
                            },
                            catch_response=True) as response:
            if response.status_code == 200:
                response_time = response.elapsed.total_seconds()
                if response_time > 2.0:  # Target: <2s
                    response.failure(f"Query processing too slow: {response_time}s")
                else:
                    response.success()
    
    @task(5)
    def generate_visualization(self):
        """Test visualization generation performance"""
        chart_data = {
            "data": {
                "labels": [f"Item {i}" for i in range(10)],
                "datasets": [{
                    "label": "Test Data",
                    "data": [random.randint(10, 100) for _ in range(10)]
                }]
            },
            "chart_type": "bar",
            "title": "Performance Test Chart"
        }
        
        with self.client.post("/visualization/generate-chart",
                            headers={"Authorization": f"Bearer {self.auth_token}"},
                            json=chart_data,
                            catch_response=True) as response:
            if response.status_code == 200:
                response_time = response.elapsed.total_seconds()
                if response_time > 1.0:  # Target: <1s
                    response.failure(f"Chart generation too slow: {response_time}s")
                else:
                    response.success()
    
    @task(3)
    def dashboard_operations(self):
        """Test dashboard operations"""
        # Create dashboard
        dashboard_data = {
            "title": f"Test Dashboard {random.randint(1, 1000)}",
            "description": "Performance test dashboard",
            "layout": {"type": "grid", "columns": 2}
        }
        
        with self.client.post("/dashboards",
                            headers={"Authorization": f"Bearer {self.auth_token}"},
                            json=dashboard_data) as response:
            if response.status_code == 201:
                dashboard_id = response.json()["data"]["dashboard_id"]
                
                # Get dashboard
                self.client.get(f"/dashboards/{dashboard_id}",
                              headers={"Authorization": f"Bearer {self.auth_token}"})

# Performance test events
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Starting performance test...")
    environment.start_time = time.time()

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print(f"Performance test completed in {time.time() - environment.start_time:.2f}s")
    
    # Print performance summary
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Failed requests: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
```

### Continuous Performance Monitoring

#### Performance Regression Detection
```python
# performance/regression_detector.py
import asyncio
import aiohttp
import statistics
from datetime import datetime, timedelta

class PerformanceRegrationDetector:
    def __init__(self, baseline_metrics: dict):
        self.baseline = baseline_metrics
        self.threshold_multiplier = 1.5  # 50% degradation threshold
    
    async def run_performance_check(self):
        """Run automated performance check"""
        current_metrics = await self.collect_current_metrics()
        regressions = self.detect_regressions(current_metrics)
        
        if regressions:
            await self.alert_performance_regression(regressions)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "current_metrics": current_metrics,
            "baseline_metrics": self.baseline,
            "regressions": regressions
        }
    
    async def collect_current_metrics(self):
        """Collect current performance metrics"""
        async with aiohttp.ClientSession() as session:
            # Test API response times
            api_times = []
            for _ in range(10):
                start = time.time()
                async with session.get("http://localhost:8000/health") as response:
                    if response.status == 200:
                        api_times.append((time.time() - start) * 1000)
            
            # Test NLP processing times
            nlp_times = []
            for _ in range(5):
                start = time.time()
                async with session.post("http://localhost:8001/process-query",
                                      json={"query": "test query", "conversation_id": "test"}) as response:
                    if response.status == 200:
                        nlp_times.append((time.time() - start) * 1000)
            
            return {
                "api_response_time_avg": statistics.mean(api_times),
                "api_response_time_p95": statistics.quantiles(api_times, n=20)[18],
                "nlp_processing_time_avg": statistics.mean(nlp_times),
                "nlp_processing_time_p95": statistics.quantiles(nlp_times, n=20)[18]
            }
    
    def detect_regressions(self, current_metrics: dict) -> list:
        """Detect performance regressions"""
        regressions = []
        
        for metric_name, current_value in current_metrics.items():
            baseline_value = self.baseline.get(metric_name)
            if baseline_value and current_value > baseline_value * self.threshold_multiplier:
                regression_pct = ((current_value - baseline_value) / baseline_value) * 100
                regressions.append({
                    "metric": metric_name,
                    "baseline": baseline_value,
                    "current": current_value,
                    "regression_percent": regression_pct
                })
        
        return regressions
    
    async def alert_performance_regression(self, regressions: list):
        """Send alerts for performance regressions"""
        alert_message = "Performance regression detected:\n"
        for regression in regressions:
            alert_message += f"- {regression['metric']}: {regression['regression_percent']:.1f}% slower\n"
        
        # Send to monitoring system
        print(f"ALERT: {alert_message}")
```

---

*Last Updated: January 22, 2025*
*Version: 1.0*