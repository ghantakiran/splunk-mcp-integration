# Excel Export Service

A comprehensive Excel export service for the Splunk MCP platform, providing advanced Excel generation with formatting, charts, and enterprise-grade security.

## Features

### Core Capabilities
- **Advanced Excel Generation**: High-quality Excel creation using openpyxl with custom formatting and themes
- **Multiple Worksheet Support**: Create complex workbooks with multiple worksheets and cross-references
- **Chart Integration**: Seamless embedding of charts and visualizations from the visualization service
- **Multiple Output Formats**: Support for XLSX, XLS, CSV, and ODS formats
- **Enterprise Security**: JWT authentication, role-based access control, and comprehensive audit logging
- **Background Processing**: Asynchronous Excel generation with job queuing and progress tracking

### Advanced Features
- **Custom Themes**: 5 built-in themes (Office, Modern, Colorful, Dark, Light) with custom styling
- **Rich Formatting**: Font styles, colors, borders, alignment, and number formatting
- **Data Validation**: Excel data validation rules with dropdown lists and input constraints
- **Formulas**: Support for Excel formulas with safety validation
- **Protection**: Workbook and worksheet protection with password security
- **Template System**: Reusable templates for consistent report generation
- **Bulk Operations**: Generate multiple Excel files in batch operations

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
   cd services/excel-export-service
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
   psql -U postgres -c "CREATE DATABASE excelservice;"
   psql -U postgres -d excelservice -f scripts/init-db.sql
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
   - API: http://localhost:8010
   - Documentation: http://localhost:8010/docs
   - Metrics: http://localhost:9010/metrics
   - Redis Commander: http://localhost:8085

## Configuration

### Environment Variables

Key environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `API_PORT` | API server port | `8010` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_SECRET_KEY` | JWT signing secret | Required |
| `EXCEL_OUTPUT_DIR` | Excel output directory | `/tmp/excel-exports` |
| `CHART_SERVICE_URL` | Visualization service URL | `http://localhost:8002` |

### Excel Generation Configuration

```bash
# Excel Generation Settings
EXCEL_OUTPUT_DIR=/tmp/excel-exports
EXCEL_TEMPLATE_DIR=app/templates
EXCEL_MAX_FILE_SIZE_MB=100
EXCEL_MAX_ROWS=1000000
EXCEL_MAX_COLUMNS=16384
EXCEL_TIMEOUT_SECONDS=300

# Chart Integration
CHART_SERVICE_URL=http://localhost:8002
CHART_TIMEOUT_SECONDS=30
CHART_MAX_WIDTH=1200
CHART_MAX_HEIGHT=800
CHART_FORMAT=png

# Themes and Formatting
DEFAULT_THEME=office
AVAILABLE_THEMES=office,modern,colorful,dark,light
ENABLE_FORMULAS=true
ENABLE_DATA_VALIDATION=true
```

## API Documentation

### Authentication

All API endpoints require JWT authentication. Include the token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

### Core Endpoints

#### Excel Generation

- `POST /api/v1/excel-exports/generate` - Generate Excel from configuration
- `POST /api/v1/excel-exports/bulk-generate` - Generate multiple Excel files
- `GET /api/v1/excel-exports/jobs` - List user's Excel jobs
- `GET /api/v1/excel-exports/jobs/{id}` - Get job details
- `GET /api/v1/excel-exports/jobs/{id}/status` - Get job status
- `POST /api/v1/excel-exports/jobs/{id}/cancel` - Cancel job
- `GET /api/v1/excel-exports/jobs/{id}/download` - Download Excel file
- `DELETE /api/v1/excel-exports/jobs/{id}` - Delete job

#### System Information

- `GET /api/v1/excel-exports/formats` - Get supported formats
- `GET /api/v1/excel-exports/capabilities` - Get service capabilities
- `GET /api/v1/excel-exports/analytics` - Get user analytics

### Example Usage

#### Generate Excel File

```bash
curl -X POST "http://localhost:8010/api/v1/excel-exports/generate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "Sales Report",
    "workbook_config": {
      "name": "Sales Report",
      "worksheets": [
        {
          "name": "Sales Data",
          "headers": ["Date", "Product", "Sales", "Region"],
          "data": [
            [
              {"value": "2024-01-01", "data_type": "date"},
              {"value": "Product A", "data_type": "string"},
              {"value": 1000, "data_type": "number"},
              {"value": "North", "data_type": "string"}
            ]
          ],
          "auto_filter": true,
          "freeze_panes": {"row": 2, "col": 1},
          "charts": [
            {
              "chart_id": "sales_chart",
              "chart_type": "bar",
              "title": "Sales by Region",
              "width": 600,
              "height": 400,
              "position": {"row": 10, "col": 1}
            }
          ]
        }
      ],
      "theme": "office"
    },
    "data_source": {
      "type": "splunk",
      "query": "search index=sales | stats sum(amount) by region"
    },
    "output_format": "xlsx",
    "theme": "modern",
    "validation_rules": [
      {
        "cell_range": "D2:D100",
        "validation_type": "list",
        "formula1": "North,South,East,West",
        "show_dropdown": true
      }
    ]
  }'
```

#### Bulk Generation

```bash
curl -X POST "http://localhost:8010/api/v1/excel-exports/bulk-generate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "output_format": "xlsx",
    "theme": "office",
    "jobs": [
      {
        "job_name": "Q1 Report",
        "workbook_config": {...},
        "data_source": {...}
      },
      {
        "job_name": "Q2 Report",
        "workbook_config": {...},
        "data_source": {...}
      }
    ]
  }'
```

## Development

### Project Structure

```
services/excel-export-service/
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
│   │   ├── excel_models.py     # Excel-related models
│   │   └── user_models.py      # User models
│   ├── services/               # Business logic
│   │   └── excel_generator.py  # Excel generation service
│   ├── utils/                  # Utilities
│   │   ├── auth.py             # Authentication
│   │   └── rate_limiter.py     # Rate limiting
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
pytest tests/test_excel_generator.py -v

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

## Excel Features

### Supported Formats

- **XLSX**: Modern Excel format with full feature support
- **XLS**: Legacy Excel format for compatibility
- **CSV**: Plain text format for data exchange
- **ODS**: OpenDocument Spreadsheet format

### Themes

- **Office**: Classic Microsoft Office theme
- **Modern**: Contemporary design with clean lines
- **Colorful**: Vibrant colors for visual impact
- **Dark**: Dark theme for reduced eye strain
- **Light**: Minimal light theme

### Chart Types

- **Line**: Line charts for trends
- **Bar**: Horizontal bar charts
- **Column**: Vertical column charts
- **Pie**: Pie charts for proportions
- **Scatter**: Scatter plots for correlations
- **Area**: Area charts for cumulative data
- **Radar**: Radar charts for multi-dimensional data
- **Bubble**: Bubble charts for three-dimensional data

### Formatting Features

- **Fonts**: Name, size, bold, italic, color
- **Backgrounds**: Solid colors and patterns
- **Borders**: Style, color, and thickness
- **Alignment**: Horizontal, vertical, and text wrap
- **Number Formats**: Currency, percentage, date, custom
- **Data Validation**: Lists, ranges, and custom rules
- **Protection**: Password-protected workbooks and worksheets

## Performance & Scalability

### Performance Metrics

- **Generation Speed**: <5 seconds for typical reports
- **Concurrent Jobs**: Up to 10 simultaneous generations
- **File Size Limits**: 100MB maximum file size
- **Row Limits**: 1 million rows per worksheet
- **Memory Usage**: Optimized for large datasets

### Scalability Features

- **Background Processing**: Async job queuing
- **Redis Caching**: Intelligent caching strategies
- **Database Optimization**: Indexed queries and connection pooling
- **File Management**: Automatic cleanup and retention policies

## Security

### Authentication & Authorization

- **JWT Authentication**: Token-based API access
- **Role-Based Access**: Granular permission system
- **Rate Limiting**: Prevent API abuse
- **Audit Logging**: Complete activity tracking

### Data Protection

- **Input Validation**: Comprehensive validation of all inputs
- **Formula Safety**: Restricted to safe Excel functions
- **File Security**: Secure file storage and access
- **Template Security**: Sandboxed template execution

## Monitoring & Observability

### Metrics

The service exposes Prometheus metrics at `/metrics`:

- `excel_generation_total` - Total Excel generations by format and status
- `excel_generation_duration_seconds` - Excel generation duration
- `excel_generation_file_size_bytes` - Generated file sizes
- `excel_generation_rows_total` - Total rows processed
- `excel_generation_charts_total` - Total charts created
- `errors_total` - Total errors by type

### Logging

Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2024-01-18T10:30:00Z",
  "level": "INFO",
  "message": "Excel generation completed",
  "correlation_id": "uuid",
  "user_id": "user123",
  "job_id": "job456",
  "generation_time_ms": 3000,
  "file_size": 2048000,
  "worksheet_count": 2,
  "chart_count": 3
}
```

### Health Checks

- `/health` - Basic health check
- `/health/detailed` - Detailed health with dependency status

## Troubleshooting

### Common Issues

1. **Excel Generation Fails**
   ```bash
   # Check openpyxl installation
   pip install openpyxl --upgrade
   
   # Check file permissions
   ls -la /tmp/excel-exports/
   
   # Check memory usage
   free -h
   ```

2. **Chart Integration Issues**
   ```bash
   # Test chart service connection
   curl -X GET "http://localhost:8002/health"
   
   # Check chart service logs
   docker logs visualization-service
   ```

3. **Database Connection Issues**
   ```bash
   # Check PostgreSQL connection
   psql -h localhost -p 5432 -U excelservice -d excelservice
   
   # Check database schema
   psql -d excelservice -c "\dt"
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

1. **Slow Excel Generation**
   - Check system resources (CPU, memory)
   - Optimize worksheet data size
   - Review chart complexity
   - Check database query performance

2. **High Memory Usage**
   - Monitor large dataset processing
   - Check file cleanup policies
   - Review Redis memory usage
   - Optimize worksheet configurations

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