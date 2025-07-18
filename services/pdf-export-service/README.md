# PDF Export Service

A comprehensive PDF generation service for the Splunk MCP platform, providing advanced PDF creation with custom layouts, chart embedding, and enterprise-grade security.

## Features

### Core Capabilities
- **Advanced PDF Generation**: High-quality PDF creation using WeasyPrint with custom layouts
- **Template System**: Jinja2-based template engine with custom filters and functions
- **Chart Integration**: Seamless embedding of charts and visualizations from the visualization service
- **Multiple Output Formats**: PDF, HTML, PNG, and JPG export options
- **Enterprise Security**: JWT authentication, role-based access control, and comprehensive audit logging
- **Scalable Architecture**: Built with FastAPI, PostgreSQL, and Redis for high performance

### Template Features
- **Custom Layouts**: Flexible page sizes, orientations, and margins
- **Rich Content**: Support for HTML, CSS, images, charts, and tables
- **Variable Substitution**: Dynamic content generation with Jinja2 templating
- **Template Management**: Create, update, delete, and duplicate templates
- **Preview System**: Real-time template preview with sample data
- **Import/Export**: Template sharing and backup capabilities

### PDF Generation Features
- **Background Processing**: Asynchronous PDF generation with job queuing
- **Progress Tracking**: Real-time job status and progress monitoring
- **Batch Operations**: Bulk PDF generation for multiple reports
- **File Management**: Automatic cleanup and retention policies
- **Error Handling**: Comprehensive error reporting and recovery

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd services/pdf-export-service
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

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   # Set up PostgreSQL database
   psql -U postgres -c "CREATE DATABASE pdfservice;"
   psql -U postgres -d pdfservice -f scripts/init-db.sql
   ```

6. **Start the service**
   ```bash
   python main.py
   ```

### Docker Deployment

1. **Using Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **Access the service**
   - API: http://localhost:8009
   - Documentation: http://localhost:8009/docs
   - Metrics: http://localhost:9009/metrics
   - Redis Commander: http://localhost:8084

## Configuration

### Environment Variables

Key environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `API_PORT` | API server port | `8009` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_SECRET_KEY` | JWT signing secret | Required |
| `PDF_OUTPUT_DIR` | PDF output directory | `/tmp/pdf-exports` |
| `CHART_SERVICE_URL` | Visualization service URL | `http://localhost:8002` |

See `.env.example` for complete configuration options.

### PDF Generation Configuration

```bash
# PDF Generation Settings
PDF_OUTPUT_DIR=/tmp/pdf-exports
PDF_TEMPLATE_DIR=app/templates
PDF_MAX_FILE_SIZE_MB=100
PDF_MAX_PAGES=1000
PDF_TIMEOUT_SECONDS=300
PDF_DPI=300
PDF_QUALITY=high

# Chart Integration
CHART_SERVICE_URL=http://localhost:8002
CHART_TIMEOUT_SECONDS=30
CHART_MAX_WIDTH=1200
CHART_MAX_HEIGHT=800
CHART_FORMAT=png
```

## API Documentation

### Authentication

All API endpoints require JWT authentication. Include the token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

### Core Endpoints

#### PDF Generation

- `POST /api/v1/pdf-exports/generate` - Generate PDF from template
- `POST /api/v1/pdf-exports/bulk-generate` - Generate multiple PDFs
- `GET /api/v1/pdf-exports/jobs` - List user's PDF jobs
- `GET /api/v1/pdf-exports/jobs/{id}` - Get job details
- `GET /api/v1/pdf-exports/jobs/{id}/status` - Get job status
- `POST /api/v1/pdf-exports/jobs/{id}/cancel` - Cancel job
- `GET /api/v1/pdf-exports/jobs/{id}/download` - Download PDF file
- `DELETE /api/v1/pdf-exports/jobs/{id}` - Delete job

#### Template Management

- `POST /api/v1/templates/` - Create new template
- `GET /api/v1/templates/` - List templates
- `GET /api/v1/templates/{id}` - Get template details
- `PUT /api/v1/templates/{id}` - Update template
- `DELETE /api/v1/templates/{id}` - Delete template
- `POST /api/v1/templates/{id}/preview` - Preview template
- `POST /api/v1/templates/{id}/duplicate` - Duplicate template
- `GET /api/v1/templates/{id}/analytics` - Get template analytics

#### System Information

- `GET /api/v1/pdf-exports/formats` - Get supported formats
- `GET /api/v1/pdf-exports/capabilities` - Get service capabilities
- `GET /api/v1/pdf-exports/analytics` - Get user analytics
- `GET /api/v1/templates/types` - Get template types
- `GET /api/v1/templates/defaults` - Get default templates

### Example Usage

#### Generate PDF

```bash
curl -X POST "http://localhost:8009/api/v1/pdf-exports/generate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "job_name": "Monthly Report",
    "output_format": "pdf",
    "parameters": {
      "title": "Monthly Sales Report",
      "content": "Sales data for January 2024"
    },
    "data_source": {
      "charts": [
        {
          "chart_id": "sales_chart",
          "title": "Sales by Region",
          "chart_type": "bar",
          "width": 800,
          "height": 600,
          "data": {
            "labels": ["North", "South", "East", "West"],
            "values": [100, 200, 150, 300]
          }
        }
      ]
    },
    "layout_config": {
      "page_size": "a4",
      "orientation": "portrait",
      "margin_top": 20,
      "margin_bottom": 20,
      "margin_left": 20,
      "margin_right": 20
    }
  }'
```

#### Create Template

```bash
curl -X POST "http://localhost:8009/api/v1/templates/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Report Template",
    "template_type": "report",
    "description": "Template for monthly sales reports",
    "template_content": "<!DOCTYPE html><html><head><title>{{ title }}</title></head><body><h1>{{ title }}</h1><div class=\"content\">{{ content }}</div>{% if charts %}<div class=\"charts\">{% for chart in charts %}<div class=\"chart\"><h3>{{ chart.title }}</h3><img src=\"{{ chart.image }}\" alt=\"{{ chart.title }}\"></div>{% endfor %}</div>{% endif %}</body></html>",
    "css_content": "body { font-family: Arial, sans-serif; margin: 40px; } .chart { margin: 20px 0; text-align: center; } .chart img { max-width: 100%; }",
    "variables": {
      "title": "Default Title",
      "content": "Default content"
    },
    "layout_config": {
      "page_size": "a4",
      "orientation": "portrait"
    }
  }'
```

## Development

### Project Structure

```
services/pdf-export-service/
├── app/
│   ├── api/v1/                 # API endpoints
│   │   ├── endpoints/          # Endpoint implementations
│   │   └── router.py           # API router
│   ├── core/                   # Core infrastructure
│   │   ├── config.py           # Configuration
│   │   ├── database.py         # Database connection
│   │   ├── redis_client.py     # Redis client
│   │   └── logging.py          # Logging configuration
│   ├── models/                 # Data models
│   │   ├── pdf_models.py       # PDF-related models
│   │   └── user_models.py      # User models
│   ├── services/               # Business logic
│   │   ├── pdf_generator.py    # PDF generation service
│   │   └── template_service.py # Template management
│   ├── utils/                  # Utilities
│   │   ├── auth.py             # Authentication
│   │   ├── rate_limiter.py     # Rate limiting
│   │   └── metrics.py          # Metrics collection
│   └── templates/              # Default templates
├── tests/                      # Test suite
├── scripts/                    # Database scripts
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Multi-container setup
└── README.md                   # This file
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_pdf_generator.py -v

# Run tests with markers
pytest -m "not slow" -v
```

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/
mypy app/

# Security check
bandit -r app/
```

### Performance Testing

```bash
# Start service
python main.py

# Run performance tests
pytest tests/test_performance.py -v

# Load testing with locust
locust -f tests/locustfile.py --host=http://localhost:8009
```

## Template Development

### Template Structure

Templates use Jinja2 syntax with custom filters and functions:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        {{ css_content }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>Generated on {{ now() | format_date }}</p>
    </div>
    
    <div class="content">
        {{ content }}
        
        {% if charts %}
        <div class="charts">
            {% for chart in charts %}
            <div class="chart">
                <h3>{{ chart.title }}</h3>
                <img src="{{ chart.image }}" alt="{{ chart.title }}">
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        {% if tables %}
        <div class="tables">
            {% for table in tables %}
            {{ format_table(table) }}
            {% endfor %}
        </div>
        {% endif %}
    </div>
    
    <div class="footer">
        <p>Generated by PDF Export Service</p>
    </div>
</body>
</html>
```

### Custom Filters

Available template filters:

- `format_date(value, format='%Y-%m-%d %H:%M:%S')` - Format datetime
- `format_number(value, decimals=2)` - Format numbers with commas
- `format_currency(value, currency='$')` - Format currency
- `truncate_text(value, length=100, suffix='...')` - Truncate text

### Custom Functions

Available template functions:

- `now()` - Current timestamp
- `format_chart(chart_config)` - Format chart for embedding
- `format_table(table_config)` - Format table for embedding

### Template Variables

Common template variables:

- `title` - Report title
- `content` - Main content
- `generation_date` - Generation timestamp
- `charts` - List of chart configurations
- `tables` - List of table configurations
- `parameters` - User-provided parameters
- `data_source` - Data source information

## Monitoring & Observability

### Metrics

The service exposes Prometheus metrics at `/metrics`:

- `pdf_generation_total` - Total PDF generations by type and status
- `pdf_generation_duration_seconds` - PDF generation duration
- `pdf_generation_file_size_bytes` - Generated file sizes
- `template_operations_total` - Template operations
- `active_jobs` - Number of active jobs
- `errors_total` - Total errors by type

### Logging

Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2024-01-18T10:30:00Z",
  "level": "INFO",
  "message": "PDF generation completed",
  "correlation_id": "uuid",
  "user_id": "user123",
  "job_id": "job456",
  "template_id": "template789",
  "generation_time_ms": 5000,
  "file_size": 1024000
}
```

### Health Checks

- `/health` - Basic health check
- `/health/detailed` - Detailed health with dependency status

### Dashboard

Access Grafana dashboard at http://localhost:3001 (admin/admin) to monitor:

- PDF generation metrics
- Template usage statistics
- System performance
- Error rates and trends

## Security

### Authentication & Authorization

- JWT-based authentication with refresh tokens
- Role-based access control (RBAC)
- Permission-based endpoint protection
- Comprehensive audit logging

### Data Protection

- Input validation and sanitization
- SQL injection prevention
- XSS protection in templates
- File upload security
- Rate limiting for API abuse prevention

### Template Security

- Jinja2 template sandboxing
- Dangerous function filtering
- Content validation
- XSS prevention in generated PDFs

## Troubleshooting

### Common Issues

1. **PDF Generation Fails**
   ```bash
   # Check WeasyPrint dependencies
   pip install weasyprint --upgrade
   
   # Check system fonts
   fc-list | grep -i arial
   
   # Check file permissions
   ls -la /tmp/pdf-exports/
   ```

2. **Template Rendering Errors**
   ```bash
   # Validate template syntax
   curl -X POST "http://localhost:8009/api/v1/templates/validate" \
     -H "Content-Type: application/json" \
     -d '{"template_content": "your template here"}'
   ```

3. **Database Connection Issues**
   ```bash
   # Check PostgreSQL connection
   psql -h localhost -p 5432 -U pdfservice -d pdfservice
   
   # Check database schema
   psql -d pdfservice -c "\dt"
   ```

4. **Redis Connection Issues**
   ```bash
   # Check Redis connection
   redis-cli -h localhost -p 6379 ping
   
   # Check Redis memory
   redis-cli info memory
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true python main.py
```

### Performance Issues

1. **Slow PDF Generation**
   - Check WeasyPrint version
   - Optimize template complexity
   - Review image sizes
   - Check system resources

2. **High Memory Usage**
   - Implement file cleanup
   - Optimize image processing
   - Review template caching

3. **Database Performance**
   - Check query execution plans
   - Review database indexes
   - Monitor connection pool

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guide
- Write comprehensive tests
- Use type hints
- Document API changes
- Update changelog

## License

This project is part of the Splunk MCP Integration platform.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the API documentation
- Check application logs
- Contact the development team

---

**Version**: 1.0.0  
**Last Updated**: January 2024  
**Maintainer**: Splunk MCP Team