# Cloud Connection Manager Service - CLAUDE.md

## Inherits From
- [Main Project Guidelines](../../CLAUDE.md)
- [Shared Standards](../../CLAUDE.md#core-data-models)

## Service Overview
The Cloud Connection Manager Service provides dynamic endpoint routing, connection pooling, and health monitoring for Splunk Enterprise and Cloud instances. It enables intelligent load balancing, automatic failover, and performance monitoring for hybrid Splunk deployments.

## Architecture
- **Dynamic Routing**: Smart endpoint routing between Enterprise and Cloud instances
- **Connection Pooling**: High-performance HTTP connection pool management
- **Load Balancing**: Multiple algorithms with circuit breaker protection
- **Health Monitoring**: Continuous health checking and performance tracking
- **Metrics Collection**: Real-time performance analytics and insights

## Development Guidelines

### Code Structure
```
services/cloud-connection-manager/
├── app/
│   ├── api/v1/                        # API endpoints
│   │   ├── endpoints/                 # Individual endpoint modules
│   │   │   ├── connections.py         # Connection management endpoints
│   │   │   ├── load_balancer.py       # Load balancer configuration
│   │   │   └── health.py              # Health monitoring endpoints
│   │   └── router.py                  # Main API router
│   ├── core/                          # Core functionality
│   │   ├── config.py                  # Configuration management
│   │   ├── database.py                # Database configuration
│   │   ├── redis_client.py            # Redis client and utilities
│   │   └── logging.py                 # Structured logging
│   ├── models/                        # Data models
│   │   └── connection_models.py       # Database and API models
│   ├── services/                      # Business logic
│   │   ├── connection_pool_manager.py # Connection pool management
│   │   ├── health_monitor.py          # Health monitoring service
│   │   └── metrics_collector.py       # Metrics collection service
│   └── main.py                        # FastAPI application
├── scripts/                           # Database scripts
├── tests/                             # Test suites
├── Dockerfile                         # Container configuration
├── requirements.txt                   # Python dependencies
├── docker-compose.yml                 # Local development setup
└── README.md                          # Service documentation
```

## Key Features

### Dynamic Endpoint Routing
- **Intelligent Routing**: Route requests to optimal Splunk instances based on health, load, and configuration
- **Multi-Tenant Support**: Tenant-aware routing for Cloud instances
- **Session Affinity**: Sticky sessions for stateful applications
- **Automatic Failover**: Circuit breaker pattern with configurable thresholds

### Connection Pool Management
- **High-Performance Pools**: aiohttp-based connection pools with configurable limits
- **Pool Statistics**: Real-time metrics on pool utilization and performance
- **Connection Validation**: Health checks for idle connections
- **Resource Management**: Automatic connection lifecycle management

### Load Balancing Algorithms
- **Round Robin**: Even distribution across healthy endpoints
- **Least Connections**: Route to endpoint with fewest active connections
- **Weighted Round Robin**: Consider endpoint weights and capacities
- **Random**: Random selection for stateless workloads

### Health Monitoring
- **Continuous Monitoring**: Real-time health checks for all endpoints
- **Health History**: Comprehensive health metrics storage and analysis
- **Multiple Checks**: HTTP status, response time, and custom health endpoints
- **Alert Integration**: Proactive alerts for endpoint degradation

### Performance Analytics
- **Real-time Metrics**: Live performance data collection and aggregation
- **Historical Analysis**: Time-series data with configurable retention
- **Performance Insights**: Automated performance issue detection
- **Trend Analysis**: Performance degradation and improvement tracking

## API Endpoints

### Connection Management
- `POST /api/v1/connections/endpoints` - Create connection endpoint
- `GET /api/v1/connections/endpoints` - List endpoints with filtering
- `GET /api/v1/connections/endpoints/{id}` - Get endpoint details
- `PUT /api/v1/connections/endpoints/{id}` - Update endpoint configuration
- `DELETE /api/v1/connections/endpoints/{id}` - Remove endpoint
- `GET /api/v1/connections/endpoints/{id}/health` - Get endpoint health status
- `POST /api/v1/connections/endpoints/{id}/health-check` - Trigger health check
- `GET /api/v1/connections/endpoints/{id}/metrics` - Get endpoint metrics

### Load Balancer Configuration
- `POST /api/v1/load-balancer/configs` - Create load balancer configuration
- `GET /api/v1/load-balancer/configs` - List configurations
- `GET /api/v1/load-balancer/configs/{id}` - Get configuration details
- `PUT /api/v1/load-balancer/configs/{id}` - Update configuration
- `DELETE /api/v1/load-balancer/configs/{id}` - Delete configuration
- `GET /api/v1/load-balancer/configs/{id}/failover-logs` - Get failover logs
- `GET /api/v1/load-balancer/stats` - Get load balancer statistics

### Health Monitoring
- `GET /api/v1/health/` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health with dependencies
- `GET /api/v1/health/ready` - Kubernetes readiness probe
- `GET /api/v1/health/live` - Kubernetes liveness probe
- `GET /api/v1/health/endpoints` - Health summary for all endpoints
- `GET /api/v1/health/endpoints/{id}/history` - Health history for endpoint
- `POST /api/v1/health/endpoints/{id}/check` - Trigger immediate health check

## Configuration

### Environment Variables
```bash
# Service Configuration
SERVICE_NAME=cloud-connection-manager
VERSION=1.0.0
DEBUG=false
HOST=0.0.0.0
PORT=8018

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# Redis Configuration
REDIS_URL=redis://host:6379/8
REDIS_MAX_CONNECTIONS=100
REDIS_RETRY_ON_TIMEOUT=true
REDIS_SOCKET_KEEPALIVE=true

# Connection Pool Configuration
CONNECTION_POOL_SIZE=50
CONNECTION_POOL_MAX_SIZE=200
CONNECTION_IDLE_TIMEOUT=300
CONNECTION_MAX_LIFETIME=3600
CONNECTION_RETRY_ATTEMPTS=3
CONNECTION_RETRY_DELAY=1.0
CONNECTION_HEALTH_CHECK_INTERVAL=30

# Load Balancer Configuration
LOAD_BALANCER_ALGORITHM=round_robin
LOAD_BALANCER_HEALTH_CHECK_TIMEOUT=10
LOAD_BALANCER_FAILOVER_TIMEOUT=30
LOAD_BALANCER_CIRCUIT_BREAKER_ENABLED=true
LOAD_BALANCER_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
LOAD_BALANCER_CIRCUIT_BREAKER_TIMEOUT=60

# Health Monitoring Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3
HEALTH_DEGRADED_THRESHOLD=0.7
HEALTH_UNHEALTHY_THRESHOLD=0.3

# Metrics Configuration
METRICS_COLLECTION_INTERVAL=60
METRICS_RETENTION_DAYS=30

# External Services
CLOUD_AUTH_SERVICE_URL=http://localhost:8017
API_GATEWAY_URL=http://localhost:8000
NLP_ENGINE_URL=http://localhost:8001

# Splunk Configuration
SPLUNK_CLOUD_BASE_URL=https://api.splunkcloud.com
SPLUNK_CLOUD_API_VERSION=v1
SPLUNK_CLOUD_DEFAULT_TIMEOUT=30
SPLUNK_ENTERPRISE_DEFAULT_PORT=8089
SPLUNK_ENTERPRISE_DEFAULT_SCHEME=https
SPLUNK_ENTERPRISE_DEFAULT_TIMEOUT=30
```

## Security Features

### Authentication & Authorization
- **JWT Integration**: Token-based authentication with Cloud Authentication Service
- **Role-based Access**: Granular permissions for endpoint management
- **Secure Credentials**: Encrypted storage of authentication tokens and passwords
- **Input Validation**: Comprehensive request validation and sanitization

### Connection Security
- **TLS Support**: Secure connections to all Splunk instances
- **Certificate Validation**: Strict certificate checking for security
- **Encrypted Storage**: Secure storage of sensitive configuration data
- **Rate Limiting**: Protection against abuse and DoS attacks

### Network Security
- **CORS Protection**: Configurable cross-origin resource sharing
- **IP Filtering**: Optional IP-based access control
- **Request Validation**: SQL injection and XSS prevention
- **Audit Logging**: Comprehensive security event logging

## Performance Considerations

### High Availability
- **Circuit Breakers**: Automatic failover with configurable thresholds
- **Health Monitoring**: Continuous health checks with intelligent routing
- **Load Distribution**: Smart load balancing across healthy endpoints
- **Graceful Degradation**: Service continues with reduced functionality

### Scalability
- **Horizontal Scaling**: Stateless service design for easy scaling
- **Connection Pooling**: Efficient resource utilization
- **Async Processing**: Non-blocking I/O operations
- **Caching Strategy**: Redis-based caching for performance

### Monitoring & Observability
- **Prometheus Metrics**: Comprehensive metrics for monitoring
- **Structured Logging**: JSON-based logs with correlation IDs
- **Health Endpoints**: Kubernetes-ready health checks
- **Performance Tracking**: Real-time performance analytics

## Integration Points

### Cloud Authentication Service
- **Token Validation**: Validate JWT tokens for API access
- **User Context**: Extract user and tenant information
- **Role Permissions**: Check user roles for endpoint management
- **Session Management**: Handle user sessions and authentication state

### API Gateway Integration
- **Optimal Routing**: Provide optimal Splunk connection for requests
- **Load Balancing**: Distribute API requests across healthy instances
- **Health Status**: Report endpoint health for routing decisions
- **Performance Metrics**: Share connection performance data

### Splunk Instances
- **Enterprise Integration**: Connect to on-premises Splunk deployments
- **Cloud Integration**: Native integration with Splunk Cloud instances
- **Multi-Tenant Support**: Tenant-aware routing for Cloud instances
- **Protocol Support**: HTTP, HTTPS with authentication

## Development Workflow

### Local Development
1. Clone repository and navigate to service directory
2. Install dependencies: `pip install -r requirements.txt`
3. Set up local PostgreSQL and Redis
4. Configure environment variables
5. Run service: `uvicorn main:app --reload --port 8018`

### Testing
- Unit tests: `pytest tests/ --cov=app`
- Integration tests: `pytest tests/integration/`
- Load tests: `pytest tests/performance/`
- Health checks: `curl http://localhost:8018/health/detailed`

### Docker Development
1. Build image: `docker build -t cloud-connection-manager .`
2. Run with compose: `docker-compose up -d`
3. Check logs: `docker-compose logs -f cloud-connection-manager`
4. Access service: `http://localhost:8018`

## Troubleshooting

### Common Issues
1. **Connection Pool Exhaustion**: Check pool size configuration and usage patterns
2. **Health Check Failures**: Verify endpoint URLs, network connectivity, and timeouts
3. **Load Balancer Issues**: Review configuration, circuit breaker status, and failover logs
4. **Performance Issues**: Monitor metrics, check database queries, and Redis health

### Debug Commands
```bash
# Service health check
curl http://localhost:8018/health/detailed

# Connection pool statistics  
curl http://localhost:8018/api/v1/connections/pools/stats

# Load balancer status
curl http://localhost:8018/api/v1/load-balancer/stats

# Recent failover events
curl "http://localhost:8018/api/v1/load-balancer/configs/1/failover-logs?hours=1"
```

### Log Analysis
```bash
# Health check events
docker logs cloud-connection-manager | grep "health_check"

# Connection pool events
docker logs cloud-connection-manager | grep "connection_event"

# Load balancer failovers
docker logs cloud-connection-manager | grep "failover"

# Performance issues
docker logs cloud-connection-manager | grep "performance_issue"
```

## Testing Guidelines

### Test Coverage Requirements
- **Unit Tests**: >95% code coverage for all service components
- **Integration Tests**: End-to-end connection and health monitoring flows
- **Performance Tests**: Load testing with concurrent connections
- **Security Tests**: Authentication, authorization, and input validation

### Test Patterns
- **Mock External Services**: Test without dependencies on Splunk instances
- **Health Check Testing**: Comprehensive health monitoring validation
- **Load Balancer Testing**: Circuit breaker and failover scenarios
- **Connection Pool Testing**: Pool lifecycle and resource management

## Deployment

### Production Configuration
- Use environment-specific configuration files
- Enable comprehensive logging and monitoring
- Configure health checks for Kubernetes
- Set appropriate resource limits and scaling policies

### Kubernetes Deployment
- Horizontal Pod Autoscaler based on CPU and memory
- Multiple replicas for high availability
- Proper health check configuration
- Service mesh integration for advanced traffic management

## Recent Implementations

### Session 47 - Cloud Connection Manager Implementation (2025-01-24)
- Created comprehensive connection pool management system
- Implemented dynamic endpoint routing with multiple load balancing algorithms
- Built continuous health monitoring with performance analytics
- Added circuit breaker pattern for automatic failover
- Created REST API for connection and load balancer management
- Integrated with Redis for caching and metrics collection
- Added comprehensive logging and structured monitoring

## Next Steps
1. Implement comprehensive test suite
2. Add Prometheus metrics integration
3. Create monitoring dashboards
4. Integrate with API Gateway service
5. Add advanced traffic shaping features