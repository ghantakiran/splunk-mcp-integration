# Webhook Service

A comprehensive webhook management and delivery service for the Splunk MCP Integration platform. This service enables external tools to receive real-time notifications and data from Splunk through webhook endpoints.

## Features

### 🔗 Webhook Management
- **Endpoint Registration**: Create and manage webhook endpoints with custom headers and authentication
- **Event Subscription**: Subscribe to specific event types with advanced filtering
- **Signature Verification**: HMAC-SHA256 signature verification for secure webhook delivery
- **Rate Limiting**: Per-user and per-endpoint rate limiting with sliding window algorithm

### 📡 Event Processing
- **Event Types**: Support for 8+ event types (query completion, alerts, dashboards, reports, etc.)
- **Real-time Processing**: Asynchronous event processing with Redis-backed queues
- **Event Filtering**: Advanced filtering based on event metadata and custom criteria
- **Batch Processing**: Efficient batch processing for high-volume events

### 🚀 Delivery System
- **Reliable Delivery**: Retry logic with exponential backoff for failed deliveries
- **Concurrent Processing**: Support for 50+ concurrent webhook deliveries
- **Response Tracking**: Detailed tracking of delivery attempts and response times
- **Timeout Handling**: Configurable timeouts for webhook endpoints

### 📊 Analytics & Monitoring
- **Prometheus Metrics**: Comprehensive metrics for monitoring and alerting
- **Delivery Analytics**: Success rates, response times, and failure analysis
- **User Quotas**: Role-based quotas for endpoints, events, and deliveries
- **Activity Logging**: Detailed logging of all webhook activities

### 🔒 Security Features
- **JWT Authentication**: Secure API access with JWT tokens
- **Permission System**: Role-based access control (Basic, Premium, Enterprise, Admin)
- **Input Validation**: Comprehensive validation of URLs, headers, and payloads
- **Domain Filtering**: Whitelist/blacklist support for webhook domains

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Webhook Service Architecture                  │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Application (Port 8007)                               │
│  ├── Webhook Management API                                     │
│  ├── Event Processing API                                       │
│  ├── Delivery Management API                                    │
│  └── Analytics & Metrics API                                    │
├─────────────────────────────────────────────────────────────────┤
│  Core Services                                                  │
│  ├── WebhookManager - Endpoint CRUD operations                 │
│  ├── EventProcessor - Event creation and routing               │
│  ├── DeliveryService - Webhook delivery and retry logic        │
│  └── MetricsCollector - Analytics and monitoring               │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                     │
│  ├── PostgreSQL - Persistent storage                           │
│  ├── Redis - Caching and queue management                      │
│  └── 10+ specialized tables                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (recommended)

### Using Docker Compose (Recommended)

1. **Clone and navigate to the service directory**:
   ```bash
   cd services/webhook-service
   ```

2. **Copy environment configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Access the service**:
   - API: http://localhost:8007
   - Documentation: http://localhost:8007/docs
   - Metrics: http://localhost:9007/metrics

### Manual Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up database**:
   ```bash
   createdb webhook_db
   psql webhook_db < init.sql
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the service**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8007 --reload
   ```

## API Usage

### Authentication

All API endpoints require JWT authentication:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8007/webhooks/endpoints
```

### Create Webhook Endpoint

```bash
curl -X POST http://localhost:8007/webhooks/endpoints \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Webhook",
    "description": "Webhook for query notifications",
    "url": "https://my-app.com/webhook",
    "event_types": ["query.completed", "alert.triggered"],
    "headers": {
      "X-API-Key": "your-api-key"
    },
    "timeout": 30,
    "retry_attempts": 3
  }'
```

### Trigger Event Manually

```bash
curl -X POST http://localhost:8007/webhooks/events/trigger \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "query.completed",
    "source": "splunk-search",
    "payload": {
      "query_id": "12345",
      "status": "completed",
      "results_count": 1500
    }
  }'
```

### List Deliveries

```bash
curl http://localhost:8007/webhooks/deliveries \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Event Types

The webhook service supports the following event types:

| Event Type | Description |
|------------|-------------|
| `query.completed` | Splunk search query completed |
| `alert.triggered` | Alert condition triggered |
| `dashboard.created` | New dashboard created |
| `report.generated` | Report generation completed |
| `error.occurred` | System error occurred |
| `system.status_changed` | System status change |
| `user.action` | User performed an action |
| `data.updated` | Data source updated |

## Configuration

### Environment Variables

Key configuration options:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `MAX_WEBHOOKS_PER_USER`: Maximum webhooks per user
- `WEBHOOK_RETRY_ATTEMPTS`: Default retry attempts
- `RATE_LIMIT_PER_USER`: Rate limit per user (per hour)

### User Roles and Quotas

| Role | Endpoints | Events/Hour | Events/Day | Deliveries/Hour | Deliveries/Day |
|------|-----------|-------------|------------|-----------------|----------------|
| Basic | 5 | 100 | 1,000 | 200 | 2,000 |
| Premium | 25 | 1,000 | 10,000 | 2,000 | 20,000 |
| Enterprise | 100 | 10,000 | 100,000 | 20,000 | 200,000 |
| Admin | 500 | 50,000 | 500,000 | 100,000 | 1,000,000 |

## Monitoring

### Health Checks

- **Basic**: `GET /health`
- **Detailed**: `GET /health/detailed`

### Metrics

Prometheus metrics available at `/metrics`:

- `webhook_requests_total` - Total API requests
- `webhook_events_total` - Total events processed
- `webhook_deliveries_total` - Total deliveries attempted
- `webhook_delivery_duration_seconds` - Delivery response times
- `webhook_endpoints_active` - Number of active endpoints
- `webhook_queue_size` - Delivery queue size

### Analytics

- **User Analytics**: `GET /webhooks/analytics/overview`
- **System Metrics**: `GET /webhooks/analytics/metrics`
- **Endpoint Statistics**: Per-endpoint success rates and response times

## Security

### Webhook Signature Verification

When a webhook secret is configured, the service generates HMAC-SHA256 signatures:

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Rate Limiting

The service implements sliding window rate limiting:

- **User-based**: Per authenticated user
- **IP-based**: For unauthenticated requests
- **Endpoint-specific**: Per webhook endpoint
- **Burst protection**: Short-term burst limits

### Input Validation

Comprehensive validation for:
- Webhook URLs (scheme, domain restrictions)
- Headers (dangerous header prevention)
- Payloads (size limits, content scanning)
- Event filters (structure validation)

## Development

### Running Tests

```bash
pytest tests/ -v --cov=app
```

### Development with Docker

```bash
# Start with development profile
docker-compose --profile dev up -d

# Access development tools
# - pgAdmin: http://localhost:8083 (admin@webhook.local / admin123)
# - Redis Commander: http://localhost:8082
```

### Code Quality

```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
mypy app/
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database connectivity
   docker-compose logs postgres
   ```

2. **Redis Connection Issues**
   ```bash
   # Check Redis connectivity
   docker-compose logs redis
   ```

3. **Webhook Delivery Failures**
   ```bash
   # Check delivery logs
   curl http://localhost:8007/webhooks/deliveries?status=failed
   ```

4. **Rate Limiting Issues**
   ```bash
   # Check rate limit headers in responses
   curl -I http://localhost:8007/webhooks/endpoints
   ```

### Debugging

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
export DEBUG=true
```

Check service health:
```bash
curl http://localhost:8007/health/detailed
```

## Performance Tuning

### Database Optimization

1. **Connection Pooling**:
   ```env
   DATABASE_POOL_SIZE=20
   DATABASE_MAX_OVERFLOW=30
   ```

2. **Index Optimization**: Indexes are pre-configured for common queries

3. **Cleanup**: Automatic cleanup of old events and deliveries

### Delivery Optimization

1. **Concurrent Deliveries**:
   ```env
   MAX_CONCURRENT_DELIVERIES=50
   ```

2. **Queue Management**:
   ```env
   DELIVERY_QUEUE_SIZE=10000
   EVENT_BATCH_SIZE=100
   ```

3. **HTTP Client Tuning**:
   ```env
   HTTP_CLIENT_MAX_CONNECTIONS=100
   HTTP_CLIENT_TIMEOUT=30
   ```

## Contributing

1. Follow the existing code style (Black, isort)
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before submitting

## License

This service is part of the Splunk MCP Integration project.