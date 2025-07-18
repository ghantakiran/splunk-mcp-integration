# HTML Report Service

Interactive HTML report generation service for the Splunk MCP Integration platform. This service provides comprehensive HTML report generation capabilities with embedded interactive charts, responsive tables, and advanced visualization features.

## Features

### 🎨 Interactive Reports
- **Rich HTML Templates**: Modern, classic, minimal, dark, and corporate themes
- **Interactive Charts**: Plotly.js integration with zoom, pan, hover, click, and brush interactions
- **Responsive Tables**: DataTables integration with sorting, filtering, pagination, and export
- **Real-time Controls**: Theme switching, chart filtering, fullscreen mode, and data export
- **Print-friendly CSS**: Optimized layouts for print and PDF generation

### 📊 Chart Types
- Bar and Column Charts
- Line and Area Charts
- Pie and Donut Charts
- Scatter Plots
- Heatmaps
- Treemaps and Sunburst Charts
- Histograms

### 🎭 Templates
- **Modern**: Bootstrap 5-based responsive design with gradient headers
- **Classic**: Traditional business report styling
- **Minimal**: Clean, distraction-free layout
- **Dark**: Dark mode optimized theme
- **Corporate**: Enterprise branding support

### 🔧 Advanced Features
- **Custom Branding**: Logo, colors, and styling customization
- **Cross-filtering**: Interactive filtering between charts and tables
- **Export Capabilities**: JSON data export and chart image downloads
- **Background Processing**: Asynchronous report generation with job tracking
- **Rate Limiting**: Configurable request throttling and burst protection
- **Caching**: Redis-based caching for improved performance

## Quick Start

### Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd services/html-report-service

# Start all services
docker-compose up -d

# Check service health
curl http://localhost:8012/health
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/htmlservice"
export REDIS_URL="redis://localhost:6379"
export JWT_SECRET_KEY="your-secret-key"

# Run the service
python main.py
```

## API Documentation

### Base URL
```
http://localhost:8012/api/v1/html-reports
```

### Authentication
All endpoints require JWT authentication via Bearer token:
```
Authorization: Bearer <jwt-token>
```

### Core Endpoints

#### Generate HTML Report
```http
POST /generate
Content-Type: application/json

{
  "job_name": "Monthly Sales Report",
  "report_config": {
    "metadata": {
      "title": "Sales Dashboard",
      "description": "Monthly sales performance analysis",
      "author": "Sales Team",
      "keywords": ["sales", "analytics", "dashboard"]
    },
    "template": "modern",
    "layout": {
      "sections": [
        {
          "id": "chart-section",
          "title": "Sales Trends",
          "width": 12,
          "content_type": "chart",
          "content_id": "sales-chart"
        }
      ]
    },
    "charts": [
      {
        "id": "sales-chart",
        "data": {
          "labels": ["Jan", "Feb", "Mar", "Apr"],
          "datasets": [
            {
              "label": "Revenue",
              "data": [12000, 15000, 13000, 17000]
            }
          ]
        },
        "config": {
          "chart_type": "line",
          "title": "Monthly Revenue",
          "width": 800,
          "height": 400,
          "interactive_features": ["zoom", "hover", "click"]
        }
      }
    ]
  },
  "data_source": {
    "source_type": "static",
    "static_source": {
      "data": []
    }
  },
  "output_format": "html",
  "expires_in_hours": 24
}
```

#### Check Job Status
```http
GET /jobs/{job_id}/status
```

#### Download Report
```http
GET /jobs/{job_id}/download
```

#### List Jobs
```http
GET /jobs?status=completed&page=1&page_size=20
```

#### Get Analytics
```http
GET /analytics?days=30
```

#### Service Capabilities
```http
GET /capabilities
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `API_PORT` | `8012` | Service port |
| `API_HOST` | `0.0.0.0` | Service host |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `JWT_SECRET_KEY` | - | JWT signing secret |
| `HTML_OUTPUT_DIR` | `/tmp/html-reports` | Output directory for reports |
| `HTML_TEMPLATE_DIR` | `app/templates` | Template directory |
| `MAX_CONCURRENT_JOBS` | `10` | Maximum concurrent report jobs |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Rate limit per minute |
| `USE_CDN` | `true` | Use CDN for JavaScript libraries |
| `ENABLE_PLOTLY` | `true` | Enable Plotly.js charts |
| `ENABLE_DATATABLES` | `true` | Enable DataTables |

### Database Schema

The service uses PostgreSQL with the following main tables:
- `html_report_jobs`: Job tracking and metadata
- `html_report_templates`: Custom template storage
- `html_report_users`: User preferences and settings
- `html_report_metrics`: Usage analytics and metrics

### Redis Usage

- **Caching**: Report templates, user sessions, and temporary data
- **Rate Limiting**: Sliding window algorithm for request throttling
- **Job Queue**: Background processing queue for report generation
- **Session Management**: User session storage and management

## Template Customization

### Creating Custom Templates

1. Create a new Jinja2 template in `app/templates/`:
```html
<!-- app/templates/custom.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <title>{{ metadata.title }}</title>
    <!-- Your custom styles -->
</head>
<body>
    <!-- Your custom layout -->
    {% for section in sections %}
        {{ section | safe }}
    {% endfor %}
</body>
</html>
```

2. Add the template to the configuration:
```python
# In app/core/config.py
AVAILABLE_TEMPLATES = ["modern", "classic", "minimal", "dark", "corporate", "custom"]
```

### Template Variables

Templates have access to:
- `metadata`: Report metadata (title, description, author, etc.)
- `sections`: Pre-rendered HTML sections
- `charts`: Chart configuration objects
- `tables`: Table configuration objects
- `layout`: Layout configuration
- `generated_at`: Generation timestamp
- `job_id`: Job identifier

## Development

### Running Tests

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Type checking
mypy app/

# Code formatting
black app/
isort app/
flake8 app/
```

### Project Structure

```
html-report-service/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Local development setup
├── README.md              # This file
├── app/
│   ├── api/               # API route definitions
│   │   └── v1/
│   │       └── endpoints/
│   │           └── html_reports.py
│   ├── core/              # Core infrastructure
│   │   ├── config.py      # Configuration settings
│   │   ├── database.py    # Database models and utilities
│   │   ├── logging.py     # Structured logging setup
│   │   └── redis_client.py # Redis client and utilities
│   ├── models/            # Pydantic data models
│   │   └── html_models.py
│   ├── services/          # Business logic
│   │   └── html_generator.py
│   ├── templates/         # Jinja2 templates
│   │   ├── modern.html
│   │   ├── classic.html
│   │   ├── minimal.html
│   │   ├── dark.html
│   │   └── corporate.html
│   └── utils/             # Utility functions
│       ├── auth.py        # Authentication utilities
│       └── rate_limiter.py # Rate limiting utilities
└── tests/                 # Test suite
    ├── test_api.py
    ├── test_generator.py
    └── test_models.py
```

### Adding New Features

1. **New Chart Types**: Extend `ChartType` enum and add mapping in `HTMLReportGenerator`
2. **New Templates**: Create template file and update configuration
3. **New Interactive Features**: Add to `InteractiveFeature` enum and implement JavaScript
4. **New Export Formats**: Extend `OutputFormat` enum and implement conversion

## Monitoring

### Health Checks

- **Health**: `GET /health` - Service and dependency status
- **Readiness**: `GET /ready` - Kubernetes readiness probe
- **Metrics**: `GET /metrics` - Prometheus-compatible metrics

### Key Metrics

- Report generation rate and success rate
- Queue sizes and processing times
- Database and Redis connection health
- Rate limiting statistics
- Error rates by endpoint

### Logging

Structured JSON logging with correlation IDs:
```json
{
  "timestamp": "2024-01-16T10:30:00Z",
  "level": "info",
  "service": "html-report-service",
  "correlation_id": "uuid-string",
  "message": "Report generation completed",
  "job_id": 123,
  "generation_time_ms": 2500,
  "chart_count": 3,
  "table_count": 2
}
```

## Security

### Authentication & Authorization
- JWT-based authentication with configurable expiration
- Role-based access control (RBAC)
- Permission-based endpoint protection
- Session management with Redis

### Input Validation
- Comprehensive Pydantic model validation
- SQL injection prevention
- XSS protection for template rendering
- File upload validation and sanitization

### Rate Limiting
- Sliding window algorithm
- Per-user and per-endpoint limits
- Burst allowance for legitimate traffic spikes
- Configurable limits and windows

## Deployment

### Production Checklist

- [ ] Set strong `JWT_SECRET_KEY`
- [ ] Configure database connection pooling
- [ ] Set up Redis clustering for high availability
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS termination
- [ ] Configure log aggregation
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategies
- [ ] Review rate limiting configuration
- [ ] Set resource limits (CPU, memory)

### Kubernetes Deployment

See `../infrastructure/kubernetes/` for deployment manifests.

### Scaling Considerations

- **Horizontal Scaling**: Multiple service instances behind load balancer
- **Database**: Connection pooling and read replicas
- **Redis**: Clustering for high availability
- **File Storage**: Shared storage or object storage for generated reports
- **Queue Processing**: Separate worker processes for background jobs

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify `DATABASE_URL` configuration
   - Check database server availability
   - Verify network connectivity

2. **Redis Connection Errors**
   - Verify `REDIS_URL` configuration
   - Check Redis server availability
   - Verify authentication if configured

3. **Template Rendering Errors**
   - Check template syntax
   - Verify template directory permissions
   - Check for missing template variables

4. **Rate Limiting Issues**
   - Check rate limit configuration
   - Verify Redis connectivity
   - Review client request patterns

5. **Chart Rendering Issues**
   - Verify CDN availability for JavaScript libraries
   - Check chart data format
   - Verify chart configuration syntax

### Debug Mode

Enable debug mode for detailed error information:
```bash
export DEBUG=true
python main.py
```

### Logs Analysis

Filter logs by correlation ID for request tracing:
```bash
docker-compose logs html-report-service | grep "correlation_id=abc-123"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style

- Use Black for code formatting
- Use isort for import sorting
- Follow PEP 8 guidelines
- Add type hints for all functions
- Write comprehensive docstrings

## License

This project is part of the Splunk MCP Integration platform.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Check service health endpoints
4. Contact the development team
