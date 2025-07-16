# Visualization Service - CLAUDE.md

## Inherits From
- [Main Project Guidelines](../../CLAUDE.md)
- [Shared Standards](../../CLAUDE.md#core-data-models)

## Service Overview
The Visualization service provides comprehensive chart generation, dashboard creation, and data visualization capabilities. It offers intelligent chart type selection, advanced customization options, and interactive features for creating dynamic dashboards.

## Architecture
- **Chart Generation**: Plotly-based chart rendering with 8+ chart types
- **Dashboard Management**: Grid-based layout engine with responsive design
- **Interactive Features**: Zoom, filter, drill-down capabilities
- **Export System**: Multi-format export (PNG, PDF, SVG, HTML, JSON)
- **Customization Engine**: Advanced styling and theming options

## Development Guidelines

### Code Structure
```
services/visualization/
├── app/
│   ├── services/              # Core services
│   │   ├── chart_generator.py      # Chart generation
│   │   ├── chart_selector.py       # Intelligent chart selection
│   │   ├── chart_customization.py  # Styling and theming
│   │   ├── chart_export.py         # Export functionality
│   │   ├── dashboard_layout.py     # Dashboard management
│   │   └── interactive_charts.py   # Interactive features
│   ├── models/                # Data models
│   │   └── chart.py           # Chart and dashboard models
│   ├── api/v1/                # API endpoints
│   │   └── endpoints.py       # All visualization endpoints
│   ├── core/                  # Core configuration
│   └── main.py                # FastAPI application
├── tests/                     # Test suites
└── requirements.txt
```

### Key Components

#### Chart Generation
- **8 Chart Types**: Line, bar, pie, scatter, histogram, heatmap, treemap, table
- **Plotly Integration**: Full Plotly.js integration for interactive charts
- **Data Processing**: Automatic data type conversion and validation
- **Performance Optimization**: Efficient rendering and memory management

#### Chart Selection
- **Intelligent Selection**: AI-powered chart type recommendations
- **Pattern Recognition**: Time series, correlation, distribution detection
- **Confidence Scoring**: 0-1 scoring system with reasoning
- **User Preferences**: Customizable chart type preferences

#### Dashboard Management
- **Grid Layout**: 12-column responsive grid system
- **Panel Management**: Full CRUD operations for dashboard panels
- **Responsive Design**: 5 breakpoints for mobile/tablet support
- **Layout Templates**: Pre-built dashboard templates

#### Interactive Features
- **Filtering**: 13 filter operations with performance optimization
- **Drill-down**: Hierarchical navigation with breadcrumb support
- **Crossfilter**: Multi-chart synchronization and linked interactions
- **Selection**: Brush, lasso, and click selection modes

## API Endpoints

### Chart Generation
- `POST /api/v1/charts/generate` - Generate charts with data
- `POST /api/v1/charts/recommend` - Get chart type recommendations
- `POST /api/v1/charts/analyze` - Analyze data patterns
- `GET /api/v1/charts/types` - Get supported chart types

### Dashboard Management
- `POST /dashboards` - Create new dashboard
- `GET /dashboards/{dashboard_id}` - Get dashboard configuration
- `PUT /dashboards/{dashboard_id}` - Update dashboard
- `DELETE /dashboards/{dashboard_id}` - Delete dashboard

### Interactive Features
- `POST /charts/interactive` - Create interactive charts
- `POST /charts/{chart_id}/interactions` - Handle interactions
- `POST /charts/linked` - Create linked charts
- `GET /charts/{chart_id}/state` - Get chart state

### Export System
- `POST /charts/{chart_id}/export` - Basic chart export
- `POST /charts/{chart_id}/export-advanced` - Advanced export options
- `POST /charts/batch-export` - Batch export multiple charts
- `GET /charts/export/formats` - Available export formats

### Customization
- `POST /charts/customize` - Apply custom styling
- `GET /charts/templates` - Available chart templates
- `POST /charts/templates` - Create custom templates
- `GET /charts/customization/options` - Customization options

## Testing Guidelines

### Test Structure
```
tests/
├── test_chart_generator.py      # Chart generation tests
├── test_chart_selector.py       # Chart selection tests
├── test_dashboard_layout.py     # Dashboard tests
├── test_interactive_charts.py   # Interactive features tests
├── test_chart_export.py         # Export functionality tests
├── test_chart_customization.py  # Customization tests
└── test_export_endpoints.py     # Export API tests
```

### Testing Patterns
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end chart generation
- **Performance Tests**: Chart rendering performance
- **Visual Tests**: Chart output validation

## Configuration

### Environment Variables
```bash
# Service Configuration
VISUALIZATION_SERVICE_PORT=8002
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379

# Chart Generation
MAX_CHART_DIMENSIONS=2000x2000
MAX_DATA_POINTS=10000
CHART_TIMEOUT_SECONDS=30

# Export Settings
EXPORT_QUALITY_DEFAULT=high
EXPORT_FORMAT_DEFAULT=png
EXPORT_DPI_DEFAULT=300
```

### Dependencies
- FastAPI for API framework
- Plotly for chart generation
- Pillow (PIL) for image processing
- pandas for data processing
- Pydantic for data validation

## Chart Types and Features

### Supported Chart Types
1. **Line Charts**: Time series, multi-series, trend analysis
2. **Bar Charts**: Categorical comparison, grouped bars
3. **Pie Charts**: Part-to-whole, donut mode
4. **Scatter Plots**: Correlation, bubble charts
5. **Histograms**: Distribution analysis
6. **Heatmaps**: Multi-dimensional data, correlation matrices
7. **Treemaps**: Hierarchical data representation
8. **Tables**: Detailed data display with pagination

### Advanced Chart Types
- **Sankey Diagrams**: Flow visualization
- **Gauge Charts**: KPI visualization
- **Interactive Features**: Zoom, pan, hover

### Customization Options
- **5 Themes**: Default, Dark, Minimal, Presentation, Seaborn
- **12 Color Schemes**: Various palettes including colorblind-friendly
- **8 Font Families**: Typography control
- **Export Templates**: Presentation, print, web, social, report

## Performance Considerations

### Optimization Strategies
- **Data Sampling**: Intelligent sampling for large datasets
- **Memory Management**: Efficient chart generation
- **Caching**: Chart configuration and result caching
- **Async Processing**: Non-blocking chart generation

### Monitoring
- **Generation Times**: Chart creation performance
- **Memory Usage**: Resource consumption tracking
- **Export Performance**: Export speed and file sizes
- **Error Tracking**: Chart generation failures

## Troubleshooting

### Common Issues
1. **Chart Generation Failures**: Check data format and size limits
2. **Export Errors**: Verify format compatibility and quality settings
3. **Interactive Feature Issues**: Check browser compatibility
4. **Performance Problems**: Monitor data size and chart complexity

### Debugging Tools
- Structured logging with correlation IDs
- Performance metrics collection
- Chart generation validation
- Export format testing

## Development Workflow

### Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables
3. Start Redis server
4. Run FastAPI application: `uvicorn main:app --reload`

### Testing
1. Unit tests: `pytest tests/`
2. Integration tests: `pytest tests/integration/`
3. Performance tests: `pytest tests/performance/`

### Deployment
- Docker containerization
- Environment-based configuration
- Health check endpoints
- Monitoring integration

## Recent Implementations

### Session 23 - Visualization Engine Foundation (2025-07-16)
- FastAPI-based microservice architecture
- Intelligent chart type selection system
- 8 chart types with pattern recognition
- Comprehensive API endpoints

### Session 24 - Basic Chart Types Rendering (2025-07-16)
- Plotly integration for chart generation
- Multi-format export support
- Performance optimization
- Comprehensive test suite

### Session 25 - Advanced Chart Types (2025-07-16)
- Sankey diagrams for flow visualization
- Gauge charts for KPI display
- Pattern detection enhancements
- Integration with chart selector

### Session 26 - Interactive Chart Features (2025-07-16)
- Filtering system with 13 operations
- Drill-down functionality
- Crossfilter capabilities
- Selection modes and state management

### Session 27 - Chart Customization (2025-07-16)
- 5 comprehensive themes
- 12 color schemes
- Font management system
- Template system for reusable configurations

### Session 28 - Chart Export Functionality (2025-07-16)
- 7 export formats (PNG, PDF, SVG, HTML, JSON, JPEG, WebP)
- 4 quality levels with optimization
- 5 export templates for different use cases
- Batch export capabilities

### Session 29 - Dashboard Layout Engine (2025-07-16)
- Grid-based layout management
- Responsive design with 5 breakpoints
- Panel management system
- Layout optimization algorithms

## Next Steps
- Real-time chart updates and data streaming
- Advanced animation and transition effects
- Machine learning for automatic chart optimization
- Enhanced dashboard collaboration features