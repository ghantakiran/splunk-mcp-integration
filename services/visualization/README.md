# Splunk MCP Visualization Service

Intelligent visualization service for the Splunk MCP (Model Context Protocol) integration that provides automatic chart type selection, chart generation, and dashboard management capabilities.

## Features

### 🧠 Intelligent Chart Selection
- **Automatic Chart Type Detection**: Analyzes data characteristics to recommend optimal chart types
- **Pattern Recognition**: Detects time series, correlation, distribution, and categorical patterns
- **Confidence Scoring**: Provides confidence scores for recommendations with reasoning
- **Alternative Suggestions**: Offers multiple chart type alternatives with trade-offs

### 📊 Supported Chart Types
- **Line Charts**: Time series data, trends, continuous data
- **Bar Charts**: Categorical comparisons, rankings, discrete data
- **Pie Charts**: Part-to-whole relationships, composition analysis
- **Scatter Plots**: Correlation analysis, relationship exploration
- **Histograms**: Distribution analysis, frequency patterns
- **Heatmaps**: Multi-dimensional data patterns, correlation matrices
- **Treemaps**: Hierarchical data, space-efficient visualization
- **Tables**: Detailed data view, precise values

### 🎛️ Advanced Capabilities
- **User Preferences**: Customizable chart type preferences and styling
- **Performance Optimization**: Intelligent handling of large datasets
- **Export Formats**: PNG, PDF, SVG, HTML export support
- **Interactive Features**: Zoom, pan, hover, drill-down capabilities

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Visualization Service                        │
├─────────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                           │
│  ├── Chart Recommendation Endpoints                            │
│  ├── Chart Generation Endpoints                                │
│  ├── Dashboard Management Endpoints                            │
│  └── Health & Monitoring Endpoints                             │
├─────────────────────────────────────────────────────────────────┤
│  Core Services                                                 │
│  ├── ChartTypeSelector (Intelligent Selection)                 │
│  ├── ChartGenerator (Rendering Engine)                         │
│  ├── DashboardManager (Layout & Persistence)                   │
│  └── ExportService (Multi-format Export)                       │
├─────────────────────────────────────────────────────────────────┤
│  Data Processing                                               │
│  ├── Data Analysis (Statistical Analysis)                      │
│  ├── Pattern Detection (ML-based Classification)               │
│  ├── Performance Optimization (Sampling & Caching)             │
│  └── Format Validation (Data Quality Checks)                   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- PostgreSQL 15+ (for development)
- Redis 7+ (for caching)

### Development Setup

1. **Clone and navigate to service directory**:
   ```bash
   cd services/visualization
   ```

2. **Start development environment**:
   ```bash
   docker-compose up -d
   ```

3. **Access the service**:
   - API Documentation: http://localhost:8002/api/v1/docs
   - Health Check: http://localhost:8002/health
   - Interactive API: http://localhost:8002/api/v1/redoc

4. **Development tools** (optional):
   ```bash
   # Start with development tools
   docker-compose --profile dev up -d
   
   # Access development tools
   # pgAdmin: http://localhost:5052 (admin@splunk-mcp.com / admin)
   # Redis Commander: http://localhost:8083
   ```

### Running Tests

```bash
# Run all tests
python -m pytest test_chart_selector.py -v

# Run specific test categories
python -m pytest test_chart_selector.py::TestChartTypeSelector::test_time_series_recommendation -v

# Run with coverage
python -m pytest test_chart_selector.py --cov=app --cov-report=html
```

## API Usage

### 1. Chart Type Recommendation

Analyze data and get intelligent chart type recommendations:

```python
import requests

# Sample data
data = {
    "fields": [
        {"name": "timestamp", "data_type": "temporal"},
        {"name": "cpu_usage", "data_type": "numerical"}
    ],
    "rows": [
        {"timestamp": "2024-01-01T00:00:00Z", "cpu_usage": 45.2},
        {"timestamp": "2024-01-01T01:00:00Z", "cpu_usage": 52.1},
        # ... more data points
    ],
    "total_rows": 24
}

# Get recommendation
response = requests.post(
    "http://localhost:8002/api/v1/charts/recommend",
    json=data
)

recommendation = response.json()
print(f"Recommended: {recommendation['chart_type']}")
print(f"Confidence: {recommendation['confidence']}")
print(f"Reasoning: {recommendation['reasoning']}")
```

### 2. Data Analysis

Get detailed analysis of data characteristics:

```python
response = requests.post(
    "http://localhost:8002/api/v1/charts/analyze",
    json=data
)

analysis = response.json()
print(f"Data Pattern: {analysis['data_summary']['data_pattern']}")
print(f"Suitable Types: {analysis['suitable_chart_types']}")
```

### 3. Chart Generation

Generate charts with automatic or manual type selection:

```python
# Automatic chart type selection
chart_request = {
    "data": data,
    "auto_select": True,
    "export_format": "png",
    "user_preferences": {
        "preferred_chart_types": ["line", "bar"]
    }
}

response = requests.post(
    "http://localhost:8002/api/v1/charts/generate",
    json=chart_request
)

chart_response = response.json()
print(f"Generated Chart: {chart_response['chart_id']}")
print(f"Type: {chart_response['chart_type']}")
```

## Chart Selection Algorithm

The intelligent chart selection algorithm considers multiple factors:

### Data Analysis Factors
- **Field Types**: Categorical, numerical, temporal, geospatial
- **Data Volume**: Row count and field count optimization
- **Cardinality**: Unique value counts for categorical fields
- **Distribution**: Statistical properties of numerical data
- **Patterns**: Time series, correlation, part-to-whole relationships

### Selection Rules
1. **Time Series**: Temporal + Numerical → Line Chart (95% confidence)
2. **Correlation**: 2+ Numerical → Scatter Plot (90% confidence)
3. **Distribution**: Single Numerical → Histogram (90% confidence)
4. **Categorical Comparison**: Categorical + Numerical → Bar Chart (90% confidence)
5. **Part-to-Whole**: Low-cardinality Categorical → Pie Chart (85% confidence)
6. **Hierarchical**: Multiple Categorical → Treemap (80% confidence)

### User Preferences
- **Preferred Types**: Boost confidence by +0.1
- **Avoided Types**: Reduce confidence by -0.2
- **Custom Styling**: Apply user-defined color schemes and layouts

## Configuration

### Environment Variables

```bash
# Application Settings
APP_NAME="Splunk MCP Visualization Service"
APP_VERSION="1.0.0"
DEBUG=false
LOG_LEVEL=INFO

# API Settings
API_V1_PREFIX="/api/v1"
CORS_ORIGINS=["http://localhost:3000"]

# Database & Cache
DATABASE_URL="postgresql://user:pass@localhost:5432/splunk_mcp"
REDIS_URL="redis://localhost:6379"

# Chart Settings
CHART_MAX_WIDTH=1920
CHART_MAX_HEIGHT=1080
CHART_MAX_DATA_POINTS=10000
CHART_TIMEOUT_SECONDS=30

# Performance
CHART_CACHE_TTL_SECONDS=300
MAX_CONCURRENT_RENDERS=10

# External Services
NLP_ENGINE_URL="http://localhost:8001"
SPLUNK_HOST="https://splunk.example.com:8089"
```

### Chart Type Configuration

The service supports extensive configuration for each chart type:

```python
# Example: Custom bar chart configuration
config = {
    "chart_type": "bar",
    "title": "Sales by Department",
    "x_axis": "department",
    "y_axis": "sales",
    "color_scheme": "categorical",
    "width": 800,
    "height": 600,
    "interactive": True,
    "chart_options": {
        "sort_by": "value",
        "show_values": True,
        "orientation": "vertical"
    }
}
```

## Performance Considerations

### Data Optimization
- **Sampling**: Automatic sampling for datasets > 10,000 rows
- **Caching**: Redis-based caching for chart configurations
- **Compression**: Efficient data transfer with response compression
- **Lazy Loading**: On-demand chart generation and rendering

### Scalability Features
- **Async Processing**: Non-blocking chart generation
- **Connection Pooling**: Optimized database connections
- **Resource Limits**: Configurable limits for chart dimensions and data size
- **Health Monitoring**: Comprehensive health checks and metrics

## Monitoring & Observability

### Structured Logging
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "visualization",
  "correlation_id": "req-12345",
  "event": "chart_generation",
  "chart_type": "line",
  "data_points": 1000,
  "generation_time": 0.45,
  "success": true
}
```

### Health Endpoints
- `GET /health`: Service health status
- `GET /api/v1/health`: Detailed health with capabilities
- Prometheus metrics endpoint (if enabled)

### Performance Metrics
- Chart generation time by type
- Recommendation accuracy scores
- Memory usage and optimization stats
- Error rates and failure analysis

## Development

### Project Structure
```
services/visualization/
├── app/
│   ├── api/v1/           # API endpoints
│   ├── core/             # Core configuration and utilities
│   ├── models/           # Data models and schemas
│   ├── services/         # Business logic services
│   └── main.py           # Application entry point
├── tests/                # Test suites
├── docker-compose.yml    # Development environment
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Adding New Chart Types

1. **Update ChartType enum** in `models/chart.py`
2. **Add selection logic** in `services/chart_selector.py`
3. **Implement rendering** in chart generation service
4. **Add tests** in test suite
5. **Update documentation** and API specs

### Testing Strategy

```bash
# Unit tests for chart selection logic
pytest test_chart_selector.py::TestChartTypeSelector -v

# Integration tests with realistic data
pytest test_chart_selector.py::test_chart_selector_integration -v

# Performance tests for large datasets
pytest test_performance.py -v

# API endpoint tests
pytest test_api.py -v
```

## Integration

### With NLP Engine
- Receives data analysis requests from NLP service
- Provides visualization recommendations for SPL query results
- Supports context-aware chart selection based on query intent

### With Frontend
- REST API for chart recommendations and generation
- WebSocket support for real-time chart updates
- Export endpoints for various formats (PNG, PDF, SVG)

### With Splunk
- Direct integration with Splunk search results
- Respects Splunk RBAC and data permissions
- Optimized for Splunk data formats and field types

## Roadmap

### Phase 1: Foundation ✅
- [x] Intelligent chart type selection
- [x] Basic chart type support
- [x] API endpoints and documentation
- [x] Comprehensive testing suite

### Phase 2: Advanced Features (In Progress)
- [ ] Chart rendering engine implementation
- [ ] Dashboard management system
- [ ] Export functionality
- [ ] Interactive chart features

### Phase 3: Enterprise Features
- [ ] Advanced chart types (Sankey, Gauge, etc.)
- [ ] Real-time chart updates
- [ ] Custom chart templates
- [ ] Performance optimization for large datasets

### Phase 4: AI Enhancement
- [ ] ML-based chart recommendation improvement
- [ ] Anomaly detection in visualizations
- [ ] Automated insight generation
- [ ] Natural language chart descriptions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation
6. Submit a pull request

## License

This project is part of the Splunk MCP Integration system.
See the main project README for licensing information.

---

**Splunk MCP Visualization Service** - Intelligent, automatic, and scalable data visualization for enterprise analytics.