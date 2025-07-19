# JSON/XML Export Service

Advanced JSON and XML data export service for the Splunk MCP Integration platform with enterprise-grade features, flexible formatting options, and comprehensive API capabilities.

## Features

### Core Export Capabilities
- **High-performance JSON generation** with configurable formatting
- **Professional XML generation** with schema validation and custom layouts
- **JSON Lines (JSONL)** support for streaming data processing
- **Custom formatting** for both JSON and XML outputs
- **Advanced data transformation** with field mapping and type conversion

### Advanced Features
- **Compression support** (GZIP, ZIP) for large files
- **Data flattening** for nested object structures
- **Field mapping and transformation** with custom rules
- **Bulk export operations** with parallel processing
- **Metadata inclusion** with configurable options
- **Real-time processing** with background job queuing

### Enterprise Features
- **JWT-based authentication** with role-based access control
- **Comprehensive rate limiting** with sliding window algorithms
- **Audit logging** with structured JSON logging and correlation IDs
- **Performance monitoring** with Prometheus-compatible metrics
- **File management** with automatic cleanup and retention policies

## API Overview

### Supported Export Formats
- `json` - Standard JSON format with configurable formatting
- `xml` - XML format with custom schema and validation
- `jsonl` - JSON Lines format for streaming data
- `custom-json` - JSON with advanced customization options
- `custom-xml` - XML with custom namespaces and schema locations

### Key Endpoints
- `POST /api/v1/json-xml-exports/generate` - Generate single export
- `POST /api/v1/json-xml-exports/bulk-generate` - Generate multiple exports
- `GET /api/v1/json-xml-exports/jobs` - List export jobs
- `GET /api/v1/json-xml-exports/jobs/{id}` - Get job details
- `GET /api/v1/json-xml-exports/jobs/{id}/download` - Download export file
- `DELETE /api/v1/json-xml-exports/jobs/{id}` - Delete export job
- `GET /api/v1/json-xml-exports/capabilities` - Get service capabilities

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the service directory:**
   ```bash
   cd services/json-xml-export-service
   ```

2. **Start the service stack:**
   ```bash
   docker-compose up -d
   ```

3. **Verify the service is running:**
   ```bash
   curl http://localhost:8015/health
   ```

4. **Access the interactive API documentation:**
   - Swagger UI: http://localhost:8015/docs
   - ReDoc: http://localhost:8015/redoc

### Manual Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost/json_xml_export"
   export REDIS_URL="redis://localhost:6379/0"
   export JWT_SECRET_KEY="your-secret-key"
   ```

3. **Initialize the database:**
   ```bash
   # Run the database initialization script
   psql -h localhost -U postgres -d json_xml_export -f scripts/init-db.sql
   ```

4. **Start the service:**
   ```bash
   python main.py
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Service host |
| `API_PORT` | `8015` | Service port |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | - | Redis connection string |
| `JWT_SECRET_KEY` | - | JWT signing secret |
| `DEBUG` | `false` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_CONCURRENT_JOBS` | `10` | Maximum concurrent export jobs |
| `MAX_FILE_SIZE_MB` | `100` | Maximum export file size |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Rate limit per user |
| `FILE_RETENTION_HOURS` | `24` | File retention period |

### JSON Configuration Options

```json
{
  "json_config": {
    "indent": 2,
    "sort_keys": true,
    "ensure_ascii": false,
    "compact": false,
    "separators": [",", ":"]
  }
}
```

### XML Configuration Options

```json
{
  "xml_config": {
    "pretty_print": true,
    "encoding": "utf-8",
    "xml_declaration": true,
    "root_tag": "root",
    "item_tag": "item",
    "namespace": "http://example.com/ns",
    "schema_location": "http://example.com/schema.xsd"
  }
}
```

## Usage Examples

### Basic JSON Export

```bash
curl -X POST "http://localhost:8015/api/v1/json-xml-exports/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data_source": {
      "type": "static",
      "config": {
        "data": [
          {"id": 1, "name": "John Doe", "email": "john@example.com"},
          {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
        ]
      }
    },
    "export_config": {
      "format": "json",
      "json_config": {
        "indent": 2,
        "sort_keys": true
      },
      "include_metadata": true
    },
    "filename": "users_export.json"
  }'
```

### XML Export with Custom Schema

```bash
curl -X POST "http://localhost:8015/api/v1/json-xml-exports/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data_source": {
      "type": "static",
      "config": {
        "data": [
          {"id": 1, "name": "Product A", "price": 99.99},
          {"id": 2, "name": "Product B", "price": 149.99}
        ]
      }
    },
    "export_config": {
      "format": "xml",
      "xml_config": {
        "pretty_print": true,
        "root_tag": "products",
        "item_tag": "product",
        "namespace": "http://company.com/products"
      }
    }
  }'
```

### Compressed JSON Lines Export

```bash
curl -X POST "http://localhost:8015/api/v1/json-xml-exports/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data_source": {
      "type": "static",
      "config": {"data": [...]}
    },
    "export_config": {
      "format": "jsonl",
      "compression": "gzip",
      "max_records": 10000
    }
  }'
```

### Bulk Export Operation

```bash
curl -X POST "http://localhost:8015/api/v1/json-xml-exports/bulk-generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exports": [
      {
        "data_source": {"type": "static", "config": {"data": [...]}},
        "export_config": {"format": "json"},
        "filename": "export1.json"
      },
      {
        "data_source": {"type": "static", "config": {"data": [...]}},
        "export_config": {"format": "xml"},
        "filename": "export2.xml"
      }
    ],
    "parallel": true
  }'
```

### Field Mapping and Transformation

```bash
curl -X POST "http://localhost:8015/api/v1/json-xml-exports/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data_source": {
      "type": "static",
      "config": {"data": [...]}
    },
    "export_config": {
      "format": "json",
      "field_mappings": [
        {
          "source_field": "first_name",
          "target_field": "name",
          "transform": "upper"
        },
        {
          "source_field": "age",
          "target_field": "age_years",
          "data_type": "string"
        }
      ],
      "flatten_nested": true
    }
  }'
```

## API Reference

### Authentication

All API endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

### Permissions

- `json_xml_export:create` - Create new export jobs
- `json_xml_export:read` - View export jobs and download files
- `json_xml_export:delete` - Delete export jobs
- `json_xml_export:admin` - Administrative operations

### Rate Limiting

Rate limits are applied per user:
- **Export Creation**: 30 requests/minute
- **Bulk Exports**: 10 requests/minute
- **File Downloads**: 100 requests/minute
- **General API**: 60 requests/minute

Rate limit headers are included in responses:
- `X-RateLimit-Limit` - Request limit for the time window
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Time when the rate limit resets

### Error Handling

The API uses standard HTTP status codes and returns detailed error information:

```json
{
  "success": false,
  "error": "Validation failed",
  "code": "VALIDATION_ERROR",
  "details": {
    "field": "export_config.format",
    "message": "Invalid format specified"
  },
  "timestamp": "2025-01-01T10:00:00Z"
}
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_json_xml_generator.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Database Management

```bash
# Initialize database
psql -h localhost -U postgres -d json_xml_export -f scripts/init-db.sql

# Connect to database
psql -h localhost -U postgres -d json_xml_export

# View export jobs
SELECT job_id, user_id, status, format, created_at FROM json_xml_export_jobs;
```

## Monitoring and Metrics

### Health Checks

- **Health**: `GET /health` - Basic health check
- **Readiness**: `GET /ready` - Kubernetes readiness probe
- **Metrics**: `GET /metrics` - Prometheus metrics

### Key Metrics

- `json_xml_export_queue_pending` - Pending export jobs
- `json_xml_export_queue_processing` - Active export jobs
- `json_xml_export_service_healthy` - Service health status

### Logging

Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2025-01-01T10:00:00Z",
  "level": "INFO",
  "message": "Export job created successfully",
  "job_id": "12345",
  "user_id": "user-123",
  "format": "json",
  "file_size": 1024
}
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   - Check database connection
   - Verify Redis availability
   - Review environment variables

2. **Export jobs fail**
   - Check file permissions on export directory
   - Verify disk space availability
   - Review export configuration

3. **Authentication errors**
   - Verify JWT secret key
   - Check token expiration
   - Confirm user permissions

4. **Rate limiting issues**
   - Check Redis connection
   - Review rate limit configuration
   - Monitor user activity

### Debugging

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

View service logs:

```bash
# Docker Compose
docker-compose logs -f json-xml-export-service

# Direct execution
tail -f /var/log/json-xml-export-service.log
```

## Production Deployment

### Docker Image

Build production image:

```bash
docker build -t json-xml-export-service:latest .
```

### Kubernetes Deployment

See `infrastructure/kubernetes/` for Kubernetes manifests.

### Security Considerations

1. **Use strong JWT secret keys**
2. **Enable TLS/SSL in production**
3. **Configure proper firewall rules**
4. **Regular security updates**
5. **Monitor for suspicious activity**

### Performance Tuning

1. **Adjust concurrent job limits**
2. **Configure Redis for performance**
3. **Optimize database queries**
4. **Monitor resource usage**
5. **Scale horizontally as needed**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

## License

This service is part of the Splunk MCP Integration project. See the main project LICENSE file for details.