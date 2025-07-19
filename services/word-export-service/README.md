# Word Export Service

Professional Word document generation service for the Splunk MCP Integration platform. This service provides comprehensive Word document creation capabilities with advanced formatting, chart embedding, and template management.

## Features

### 📄 Document Generation
- **Professional Templates**: 5 built-in templates (Professional, Corporate, Academic, Report, Minimal)
- **Custom Layouts**: Flexible section-based document structure
- **Advanced Formatting**: Headers, footers, watermarks, and custom styling
- **Chart Integration**: Embedded charts using matplotlib with multiple chart types
- **Table Support**: Advanced table generation with custom styling
- **Page Management**: Custom page setup, margins, and orientation

### 🎨 Chart Types Supported
- Bar charts
- Column charts
- Line charts
- Pie charts
- Area charts
- Scatter plots
- Tables with advanced formatting

### 🔧 Technical Features
- **Async Processing**: Background job processing with Redis queues
- **Rate Limiting**: User and IP-based rate limiting
- **Authentication**: JWT-based authentication with RBAC
- **Caching**: Redis-based caching for performance
- **Analytics**: Comprehensive usage analytics and reporting
- **File Management**: Automatic file cleanup and expiration
- **Health Monitoring**: Comprehensive health checks and metrics

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd word-export-service
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up database**
```bash
# Create PostgreSQL database
createdb wordservice

# Run migrations (handled automatically on startup)
```

6. **Start the service**
```bash
python main.py
```

### Docker Setup

1. **Start services with Docker Compose**
```bash
docker-compose up -d
```

2. **View logs**
```bash
docker-compose logs -f word-export-service
```

3. **Stop services**
```bash
docker-compose down
```

## API Documentation

### Base URL
```
http://localhost:8013/api/v1/word-export
```

### Authentication
All endpoints require JWT authentication via Bearer token:
```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
     http://localhost:8013/api/v1/word-export/capabilities
```

### Key Endpoints

#### Create Word Export Job
```http
POST /jobs
Content-Type: application/json

{
  "job_name": "Monthly Report",
  "document_config": {
    "metadata": {
      "title": "Monthly Performance Report",
      "author": "John Doe",
      "company": "Acme Corp"
    },
    "template": "professional",
    "layout": {
      "sections": [
        {
          "id": "intro",
          "title": "Introduction",
          "content_type": "text",
          "text_content": "This is our monthly performance report."
        }
      ]
    }
  },
  "data_source": {
    "source_type": "static",
    "static_source": {
      "data": [
        {"metric": "Sales", "value": 150000},
        {"metric": "Users", "value": 2500}
      ]
    }
  }
}
```

#### Get Job Status
```http
GET /jobs/{job_id}/status
```

#### Download Generated Document
```http
GET /jobs/{job_id}/download
```

#### List User Jobs
```http
GET /jobs?page=1&page_size=20&status_filter=completed
```

#### Get Service Capabilities
```http
GET /capabilities
```

### Complete API Documentation
Visit `http://localhost:8013/docs` for interactive Swagger documentation.

## Document Configuration

### Basic Document Structure
```json
{
  "metadata": {
    "title": "Document Title",
    "subject": "Document Subject",
    "author": "Author Name",
    "company": "Company Name",
    "keywords": ["keyword1", "keyword2"]
  },
  "template": "professional",
  "layout": {
    "page_setup": {
      "orientation": "portrait",
      "margins": {
        "top": 1.0,
        "bottom": 1.0,
        "left": 1.0,
        "right": 1.0
      }
    },
    "header": {
      "text": "Header Text",
      "include_page_number": true,
      "include_date": true
    },
    "footer": {
      "text": "Footer Text",
      "alignment": "center"
    },
    "sections": [
      {
        "id": "section1",
        "title": "Section Title",
        "content_type": "text",
        "text_content": "Section content..."
      }
    ]
  }
}
```

### Chart Configuration
```json
{
  "id": "chart1",
  "data": {
    "labels": ["Jan", "Feb", "Mar"],
    "datasets": [
      {
        "label": "Sales",
        "data": [100, 150, 200]
      }
    ]
  },
  "config": {
    "chart_type": "bar",
    "title": "Monthly Sales",
    "width": 400,
    "height": 300,
    "color_scheme": "blue",
    "show_legend": true,
    "show_grid": true
  }
}
```

### Table Configuration
```json
{
  "id": "table1",
  "data": [
    {"name": "Product A", "sales": 1000, "profit": 200},
    {"name": "Product B", "sales": 1500, "profit": 300}
  ],
  "config": {
    "columns": [
      {"name": "name", "label": "Product", "alignment": "left"},
      {"name": "sales", "label": "Sales ($)", "alignment": "right"},
      {"name": "profit", "label": "Profit ($)", "alignment": "right"}
    ],
    "header_style": {
      "font_size": 12,
      "bold": true,
      "color": "#ffffff"
    }
  }
}
```

## Templates

### Available Templates

1. **Professional** - Clean, business-oriented design
2. **Corporate** - Formal corporate styling with company branding
3. **Academic** - Academic paper formatting
4. **Report** - Technical report layout
5. **Minimal** - Simple, minimal design

### Custom Templates
Create custom templates via the templates API:
```http
POST /templates
Content-Type: application/json

{
  "name": "Custom Template",
  "description": "My custom template",
  "template_type": "professional",
  "template_data": {
    // Template configuration
  }
}
```

## Data Sources

### Static Data
```json
{
  "source_type": "static",
  "static_source": {
    "data": [
      {"key": "value"}
    ]
  }
}
```

### Query Data
```json
{
  "source_type": "query",
  "query_source": {
    "query": "SELECT * FROM metrics WHERE date >= ?",
    "parameters": {"date": "2024-01-01"},
    "connection_id": "main_db"
  }
}
```

### File Data
```json
{
  "source_type": "file",
  "file_source": {
    "file_path": "/path/to/data.csv",
    "file_format": "csv",
    "sheet_name": "Sheet1"
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `API_PORT` | Service port | `8013` |
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `REDIS_URL` | Redis connection URL | Required |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `WORD_OUTPUT_DIR` | Output directory | `/tmp/word-exports` |
| `WORD_MAX_FILE_SIZE_MB` | Max file size | `50` |
| `MAX_CONCURRENT_JOBS` | Max concurrent jobs | `10` |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Rate limit | `60` |

### Database Configuration
The service uses PostgreSQL for persistent storage:
- Job management and tracking
- Template storage
- User analytics
- System configuration

### Redis Configuration
Redis is used for:
- Job queuing and processing
- Rate limiting
- Caching
- Session management

## Monitoring

### Health Checks
- **Health endpoint**: `GET /health`
- **Readiness endpoint**: `GET /ready`
- **Metrics endpoint**: `GET /metrics`

### Logging
Structured JSON logging with correlation IDs:
```json
{
  "timestamp": "2024-01-16T10:30:00Z",
  "level": "INFO",
  "message": "Job completed successfully",
  "correlation_id": "abc12345",
  "job_id": 123,
  "user_id": 456,
  "duration_ms": 2500
}
```

### Metrics
Prometheus-compatible metrics available at `/metrics`:
- Job processing times
- Success/failure rates
- Queue sizes
- Active connections

## Development

### Running Tests
```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Code Quality
```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Development Tools
```bash
# Start with auto-reload
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8013

# Start with debugging
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn main:app
```

## Performance

### Optimization Tips
1. **Caching**: Enable Redis caching for frequently accessed data
2. **Rate Limiting**: Configure appropriate rate limits for your use case
3. **Connection Pooling**: Tune database connection pool settings
4. **Background Processing**: Use background tasks for long-running operations
5. **File Cleanup**: Configure automatic cleanup of old files

### Scaling
- **Horizontal Scaling**: Deploy multiple service instances behind a load balancer
- **Database Scaling**: Use read replicas for analytics queries
- **Redis Clustering**: Use Redis cluster for high availability
- **Queue Workers**: Scale background workers based on queue size

## Security

### Authentication
- JWT-based authentication with configurable expiration
- Support for refresh tokens
- Integration with external auth providers

### Authorization
- Role-based access control (RBAC)
- User-level permissions
- Resource-level access control

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- Rate limiting for abuse prevention

## Troubleshooting

### Common Issues

1. **Service won't start**
   - Check database connectivity
   - Verify Redis connection
   - Review environment configuration

2. **Jobs fail to process**
   - Check worker logs
   - Verify data source connectivity
   - Review job configuration

3. **Performance issues**
   - Monitor database queries
   - Check Redis performance
   - Review rate limiting settings

### Debug Mode
Enable debug mode for detailed logging:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Log Analysis
Use structured logging for troubleshooting:
```bash
# Filter by correlation ID
cat logs/app.log | jq 'select(.correlation_id == "abc12345")'

# Filter by job ID
cat logs/app.log | jq 'select(.job_id == 123)'
```

## Support

For support and bug reports:
1. Check the [troubleshooting guide](#troubleshooting)
2. Review service logs
3. Create an issue with:
   - Service version
   - Error logs
   - Reproduction steps
   - Environment details

## License

This service is part of the Splunk MCP Integration platform.

---

*Generated with Word Export Service v1.0.0*