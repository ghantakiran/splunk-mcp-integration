# PowerPoint Export Service

A comprehensive microservice for generating PowerPoint presentations with advanced features including themes, charts, animations, and multiple export formats.

## 🚀 Features

### Core Capabilities
- **PowerPoint Generation**: Create PPTX presentations programmatically using python-pptx
- **Multiple Export Formats**: Support for PPTX, PDF, PNG, and JPG exports
- **Theme System**: Built-in themes (Office, Modern, Colorful, Dark, Minimal)
- **Chart Integration**: Embed interactive charts with multiple chart types
- **Template Management**: Create, manage, and reuse presentation templates
- **Batch Processing**: Generate multiple presentations simultaneously

### Advanced Features
- **Slide Layouts**: Multiple pre-defined slide layouts (Title, Content, Two Column, etc.)
- **Animations & Transitions**: Add slide animations and transitions
- **Image Support**: Embed images from URLs or file paths
- **Table Creation**: Generate formatted tables with styling
- **Custom Fonts & Colors**: Extensive typography and color scheme options
- **Background Customization**: Set custom backgrounds for slides

### Enterprise Features
- **JWT Authentication**: Secure API access with role-based permissions
- **Rate Limiting**: Configurable rate limiting with Redis backend
- **Job Management**: Asynchronous job processing with progress tracking
- **Analytics**: Comprehensive usage analytics and reporting
- **Health Monitoring**: Health checks and metrics for monitoring
- **Docker Support**: Containerized deployment with multi-stage builds

## 📋 Requirements

### System Requirements
- Python 3.11+
- PostgreSQL 12+
- Redis 6+
- Docker (optional)

### Python Dependencies
- FastAPI 0.104+
- python-pptx 0.6.23
- Pillow 10.1+
- asyncpg 0.29+
- aioredis 2.0+
- structlog 23.2+

## 🛠️ Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd powerpoint-export-service
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

5. **Start dependencies**
   ```bash
   # PostgreSQL
   createdb pptservice
   
   # Redis (if not running)
   redis-server
   ```

6. **Initialize database**
   ```bash
   python -c "import asyncio; from app.core.database import create_tables; asyncio.run(create_tables())"
   ```

7. **Start the service**
   ```bash
   python main.py
   ```

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t powerpoint-export-service .
   ```

2. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `DEBUG` | Enable debug mode | `false` |
| `API_PORT` | API server port | `8011` |
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `REDIS_URL` | Redis connection URL | Required |
| `JWT_SECRET_KEY` | JWT token secret | Required |
| `PPT_OUTPUT_DIR` | Output directory for files | `/tmp/ppt-exports` |
| `PPT_MAX_FILE_SIZE_MB` | Maximum file size limit | `200` |
| `PPT_MAX_SLIDES` | Maximum slides per presentation | `100` |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Rate limit per user | `50` |
| `CHART_SERVICE_URL` | Chart service endpoint | `http://localhost:8002` |

### Theme Configuration

Available themes:
- `office` - Traditional Office theme
- `modern` - Clean modern design
- `colorful` - Vibrant color palette
- `dark` - Dark mode theme
- `minimal` - Minimalist design

### Animation & Transition Types

**Animations**: `fade`, `slide`, `zoom`, `flip`, `none`
**Transitions**: `fade`, `slide`, `push`, `cover`, `uncover`, `none`

## 📚 API Documentation

### Authentication

All API endpoints require JWT authentication:

```bash
curl -H "Authorization: Bearer <jwt-token>" \
     http://localhost:8011/api/v1/powerpoint-exports/jobs
```

### Core Endpoints

#### Generate Presentation
```http
POST /api/v1/powerpoint-exports/generate
```

**Request Body:**
```json
{
  "job_name": "My Presentation",
  "presentation_config": {
    "metadata": {
      "title": "Quarterly Report",
      "author": "John Doe",
      "description": "Q4 2023 Performance"
    },
    "slides": [
      {
        "title": "Introduction",
        "slide_type": "title",
        "layout": "title_slide",
        "content": {
          "texts": [
            {
              "text": "Welcome to Q4 Report",
              "position": {"x": 1, "y": 2, "width": 8, "height": 1},
              "style": {
                "font": {
                  "family": "Calibri",
                  "size": 24,
                  "bold": true
                }
              }
            }
          ]
        }
      }
    ],
    "theme": "office",
    "color_scheme": "blue"
  },
  "data_source": {
    "source_type": "static",
    "static_source": {
      "data": []
    }
  },
  "output_format": "pptx"
}
```

#### List Jobs
```http
GET /api/v1/powerpoint-exports/jobs?status=completed&page=1&page_size=20
```

#### Get Job Status
```http
GET /api/v1/powerpoint-exports/jobs/{job_id}/status
```

#### Download File
```http
GET /api/v1/powerpoint-exports/jobs/{job_id}/download
```

#### Bulk Generation
```http
POST /api/v1/powerpoint-exports/bulk-generate
```

### Template Management

#### Create Template
```http
POST /api/v1/templates/
```

#### List Templates
```http
GET /api/v1/templates/?theme=office&is_default=true
```

#### Update Template
```http
PUT /api/v1/templates/{template_id}
```

### Analytics

#### Get Usage Analytics
```http
GET /api/v1/powerpoint-exports/analytics?days=30
```

#### Get Service Capabilities
```http
GET /api/v1/powerpoint-exports/capabilities
```

## 🎨 Usage Examples

### Basic Presentation

```python
import httpx
import asyncio

async def create_basic_presentation():
    async with httpx.AsyncClient() as client:
        # Create a simple presentation
        presentation_data = {
            "job_name": "Basic Presentation",
            "presentation_config": {
                "metadata": {
                    "title": "My First Presentation",
                    "author": "API User"
                },
                "slides": [
                    {
                        "title": "Welcome",
                        "slide_type": "title",
                        "layout": "title_slide",
                        "content": {
                            "texts": [
                                {
                                    "text": "Hello, World!",
                                    "position": {"x": 1, "y": 3, "width": 8, "height": 2}
                                }
                            ]
                        }
                    }
                ],
                "theme": "modern"
            },
            "data_source": {
                "source_type": "static",
                "static_source": {"data": []}
            }
        }
        
        response = await client.post(
            "http://localhost:8011/api/v1/powerpoint-exports/generate",
            json=presentation_data,
            headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
        )
        
        job = response.json()
        print(f"Job created: {job['job_id']}")
        return job['job_id']

# Run the example
job_id = asyncio.run(create_basic_presentation())
```

### Chart Integration

```python
# Add a chart slide
chart_slide = {
    "title": "Sales Data",
    "slide_type": "chart",
    "layout": "title_and_content",
    "content": {
        "charts": [
            {
                "data": {
                    "labels": ["Q1", "Q2", "Q3", "Q4"],
                    "datasets": [
                        {
                            "label": "Sales",
                            "data": [100, 150, 120, 180]
                        }
                    ]
                },
                "config": {
                    "chart_type": "column",
                    "title": "Quarterly Sales",
                    "show_legend": true,
                    "color_scheme": "blue"
                },
                "position": {"x": 1, "y": 2, "width": 8, "height": 5}
            }
        ]
    }
}
```

### Table Creation

```python
# Add a table slide
table_slide = {
    "title": "Performance Metrics",
    "slide_type": "table",
    "layout": "title_and_content",
    "content": {
        "tables": [
            {
                "headers": ["Metric", "Q3", "Q4", "Change"],
                "rows": [
                    {"cells": ["Revenue", "$100K", "$120K", "+20%"]},
                    {"cells": ["Users", "1,000", "1,200", "+20%"]},
                    {"cells": ["Conversion", "5%", "6%", "+1%"]}
                ],
                "position": {"x": 1, "y": 2, "width": 8, "height": 4},
                "show_grid": true,
                "alternating_rows": true
            }
        ]
    }
}
```

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_powerpoint_generator.py
```

### Test Structure

```
tests/
├── conftest.py                 # Test configuration and fixtures
├── test_api_endpoints.py       # API endpoint tests
├── test_powerpoint_generator.py # Core generation logic tests
├── test_auth.py               # Authentication tests
├── test_rate_limiter.py       # Rate limiting tests
└── test_models.py             # Data model validation tests
```

## 📊 Monitoring

### Health Checks

- **Basic Health**: `GET /health`
- **Detailed Health**: `GET /health/detailed`
- **Readiness Probe**: `GET /api/v1/health/ready`
- **Liveness Probe**: `GET /api/v1/health/live`

### Metrics

Prometheus metrics available at `/metrics`:

- `ppt_jobs_total` - Total number of jobs created
- `ppt_jobs_duration_seconds` - Job completion duration
- `ppt_jobs_file_size_bytes` - Generated file sizes
- `ppt_api_requests_total` - API request counts
- `ppt_api_request_duration_seconds` - API response times

### Logging

Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2023-12-07T10:30:00Z",
  "level": "info",
  "logger": "app.services.powerpoint_generator",
  "message": "PowerPoint generation completed",
  "job_id": 123,
  "user_id": 456,
  "generation_time_ms": 5000,
  "file_size": 2048576
}
```

## 🔧 Development

### Code Quality

```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
mypy app/

# Run all quality checks
make lint
```

### Project Structure

```
powerpoint-export-service/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── powerpoint_exports.py
│   │       │   ├── templates.py
│   │       │   └── health.py
│   │       └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging.py
│   │   └── redis_client.py
│   ├── models/
│   │   └── powerpoint_models.py
│   ├── services/
│   │   └── powerpoint_generator.py
│   ├── utils/
│   │   ├── auth.py
│   │   └── rate_limiter.py
│   └── templates/             # PowerPoint templates
├── tests/
├── main.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🚀 Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  powerpoint-service:
    build: .
    ports:
      - "8011:8011"
      - "9011:9011"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/pptservice
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: pptservice
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes

See `infrastructure/kubernetes/` for complete Kubernetes manifests.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive tests
- Update documentation for new features
- Use structured logging
- Handle errors gracefully

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check PostgreSQL is running
   pg_isready -h localhost -p 5432
   
   # Verify database exists
   psql -h localhost -U postgres -l
   ```

2. **Redis Connection Errors**
   ```bash
   # Check Redis is running
   redis-cli ping
   
   # Check Redis connection
   redis-cli -h localhost -p 6379 info
   ```

3. **Permission Errors**
   ```bash
   # Ensure output directory is writable
   mkdir -p /tmp/ppt-exports
   chmod 755 /tmp/ppt-exports
   ```

4. **Memory Issues**
   - Increase Docker memory limits
   - Monitor memory usage with `docker stats`
   - Adjust `PPT_MAX_FILE_SIZE_MB` setting

5. **Rate Limiting Issues**
   - Check Redis for rate limit keys: `redis-cli keys "rate_limit:*"`
   - Adjust rate limits in configuration
   - Clear rate limit data: `redis-cli flushdb`

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python main.py
```

### Performance Tuning

- Adjust `MAX_CONCURRENT_JOBS` based on system resources
- Increase database connection pool size for high load
- Use Redis clustering for better cache performance
- Monitor and tune garbage collection settings

## 📞 Support

For support and questions:

- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation
- Contact the development team

---

**PowerPoint Export Service** - Enterprise-grade presentation generation with advanced features and scalability.
