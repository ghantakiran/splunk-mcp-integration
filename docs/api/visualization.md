# Visualization Service Documentation

## Overview

The Visualization Service provides comprehensive chart generation, dashboard management, and interactive visualization capabilities. It supports multiple chart types, custom layouts, real-time updates, and various export formats.

**Base URL**: `/api/v1/visualization`  
**Service Port**: 8002  
**Version**: 1.0

## Chart Generation

### POST /generate-chart
Generate a chart from data with automatic type selection or explicit configuration.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "data": {
    "labels": ["Web Server", "Database", "API Gateway", "Auth Service"],
    "datasets": [{
      "label": "Error Count",
      "data": [150, 89, 75, 23],
      "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0"]
    }]
  },
  "chart_type": "bar",
  "title": "Error Count by Source",
  "options": {
    "width": 800,
    "height": 400,
    "responsive": true,
    "legend": {
      "display": true,
      "position": "top"
    },
    "axes": {
      "x": {
        "title": "Source",
        "grid": true
      },
      "y": {
        "title": "Count",
        "grid": true,
        "beginAtZero": true
      }
    }
  },
  "style": {
    "theme": "default",
    "color_scheme": "modern"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "chart_id": "chart_123",
    "chart_url": "/api/v1/visualization/charts/chart_123",
    "embed_url": "/api/v1/visualization/charts/chart_123/embed",
    "download_url": "/api/v1/visualization/charts/chart_123/download",
    "chart_config": {
      "type": "bar",
      "width": 800,
      "height": 400,
      "interactive": true
    },
    "metadata": {
      "created_at": "2025-01-22T10:30:00Z",
      "data_points": 4,
      "file_size": "15.2KB"
    }
  }
}
```

---

### POST /auto-chart
Generate chart with automatic type selection based on data.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "data": {
    "columns": ["timestamp", "cpu_usage", "memory_usage"],
    "rows": [
      ["2025-01-22T10:00:00Z", 45.2, 68.1],
      ["2025-01-22T10:05:00Z", 52.1, 71.3],
      ["2025-01-22T10:10:00Z", 48.7, 69.8]
    ]
  },
  "intent": "time_series",
  "preferences": {
    "style": "modern",
    "interactivity": "high"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "recommended_chart": {
      "type": "line",
      "confidence": 0.94,
      "reasoning": "Time-based data with multiple metrics suggests line chart for trend visualization"
    },
    "alternatives": [
      {
        "type": "area",
        "confidence": 0.78,
        "reasoning": "Shows volume and trends effectively"
      },
      {
        "type": "multi_axis",
        "confidence": 0.65,
        "reasoning": "Different scales for CPU and memory"
      }
    ],
    "chart_id": "chart_124",
    "chart_url": "/api/v1/visualization/charts/chart_124"
  }
}
```

---

### GET /charts/{chart_id}
Retrieve chart configuration and metadata.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "chart_id": "chart_123",
    "title": "Error Count by Source",
    "type": "bar",
    "config": {
      "width": 800,
      "height": 400,
      "responsive": true
    },
    "data_summary": {
      "total_points": 4,
      "date_range": "N/A",
      "last_updated": "2025-01-22T10:30:00Z"
    },
    "interactions": {
      "click_events": true,
      "hover_tooltips": true,
      "zoom": false,
      "pan": false
    },
    "created_by": "user_123",
    "created_at": "2025-01-22T10:30:00Z"
  }
}
```

---

### PUT /charts/{chart_id}
Update existing chart configuration.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Updated Error Count by Source",
  "options": {
    "width": 1000,
    "height": 500,
    "legend": {
      "position": "bottom"
    }
  },
  "style": {
    "theme": "dark",
    "color_scheme": "blue"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Chart updated successfully",
    "chart_url": "/api/v1/visualization/charts/chart_123",
    "updated_at": "2025-01-22T10:35:00Z"
  }
}
```

---

### DELETE /charts/{chart_id}
Delete a chart.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Chart deleted successfully"
  }
}
```

## Chart Types

### Supported Chart Types

| Type | Description | Best For |
|------|-------------|----------|
| `bar` | Vertical bar chart | Categorical comparisons |
| `horizontal_bar` | Horizontal bar chart | Long category names |
| `line` | Line chart | Time series, trends |
| `area` | Area chart | Volume over time |
| `pie` | Pie chart | Part-to-whole relationships |
| `doughnut` | Doughnut chart | Part-to-whole with center space |
| `scatter` | Scatter plot | Correlation analysis |
| `bubble` | Bubble chart | 3-dimensional data |
| `radar` | Radar/spider chart | Multi-dimensional comparison |
| `polar` | Polar area chart | Circular data representation |
| `heatmap` | Heat map | Matrix data visualization |
| `treemap` | Tree map | Hierarchical data |
| `sankey` | Sankey diagram | Flow visualization |
| `gauge` | Gauge chart | Single metric display |
| `table` | Data table | Detailed data view |

### Chart Type Selection API

#### POST /suggest-chart-type
Get chart type recommendations based on data characteristics.

**Request Body:**
```json
{
  "data_characteristics": {
    "data_type": "numerical",
    "temporal": true,
    "dimensions": 2,
    "data_points": 100,
    "categorical_fields": 1,
    "numerical_fields": 2
  },
  "use_case": "performance_monitoring"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "chart_type": "line",
        "confidence": 0.92,
        "reasoning": "Time series data with numerical values ideal for line charts",
        "pros": ["Shows trends clearly", "Good for time-based analysis"],
        "cons": ["May be cluttered with too many series"]
      },
      {
        "chart_type": "area",
        "confidence": 0.85,
        "reasoning": "Area charts show volume and trends effectively",
        "pros": ["Shows magnitude", "Stacked areas show composition"],
        "cons": ["Can obscure individual series"]
      }
    ]
  }
}
```

## Dashboard Management

### POST /dashboards
Create a new dashboard.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "System Performance Dashboard",
  "description": "Real-time monitoring of system metrics",
  "layout": {
    "type": "grid",
    "columns": 3,
    "rows": 2,
    "responsive": true
  },
  "panels": [
    {
      "id": "panel_1",
      "title": "CPU Usage",
      "chart_id": "chart_123",
      "position": {
        "row": 0,
        "col": 0,
        "width": 1,
        "height": 1
      },
      "refresh_interval": 30
    },
    {
      "id": "panel_2", 
      "title": "Memory Usage",
      "chart_id": "chart_124",
      "position": {
        "row": 0,
        "col": 1,
        "width": 1,
        "height": 1
      },
      "refresh_interval": 30
    }
  ],
  "settings": {
    "auto_refresh": true,
    "theme": "light",
    "public": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dashboard_id": "dash_456",
    "title": "System Performance Dashboard",
    "url": "/api/v1/visualization/dashboards/dash_456",
    "embed_url": "/api/v1/visualization/dashboards/dash_456/embed",
    "share_url": "/api/v1/visualization/dashboards/dash_456/share",
    "created_at": "2025-01-22T10:40:00Z",
    "panels_count": 2
  }
}
```

---

### GET /dashboards
List user's dashboards with filtering and pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `search`: Search term for title/description
- `tag`: Filter by tag
- `sort`: Sort field (title, created_at, updated_at)
- `order`: Sort order (asc, desc)

**Response:**
```json
{
  "success": true,
  "data": {
    "dashboards": [
      {
        "dashboard_id": "dash_456",
        "title": "System Performance Dashboard",
        "description": "Real-time monitoring of system metrics",
        "panels_count": 2,
        "created_at": "2025-01-22T10:40:00Z",
        "updated_at": "2025-01-22T10:40:00Z",
        "is_public": false,
        "tags": ["monitoring", "performance"]
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 1,
      "pages": 1
    }
  }
}
```

---

### GET /dashboards/{dashboard_id}
Get detailed dashboard configuration.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "dashboard_id": "dash_456",
    "title": "System Performance Dashboard",
    "description": "Real-time monitoring of system metrics",
    "layout": {
      "type": "grid",
      "columns": 3,
      "rows": 2
    },
    "panels": [
      {
        "id": "panel_1",
        "title": "CPU Usage",
        "chart_id": "chart_123",
        "chart_type": "line",
        "position": {"row": 0, "col": 0, "width": 1, "height": 1},
        "refresh_interval": 30,
        "last_updated": "2025-01-22T10:42:00Z"
      }
    ],
    "settings": {
      "auto_refresh": true,
      "refresh_interval": 60,
      "theme": "light"
    },
    "permissions": {
      "owner": "user_123",
      "shared_with": [],
      "public": false
    },
    "created_at": "2025-01-22T10:40:00Z",
    "updated_at": "2025-01-22T10:42:00Z"
  }
}
```

---

### PUT /dashboards/{dashboard_id}
Update dashboard configuration.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Updated System Dashboard",
  "description": "Updated description",
  "layout": {
    "columns": 4
  },
  "settings": {
    "theme": "dark",
    "auto_refresh": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Dashboard updated successfully",
    "updated_at": "2025-01-22T10:45:00Z"
  }
}
```

---

### DELETE /dashboards/{dashboard_id}
Delete a dashboard.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Dashboard deleted successfully"
  }
}
```

## Dashboard Panels

### POST /dashboards/{dashboard_id}/panels
Add a panel to a dashboard.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Network Traffic",
  "chart_id": "chart_125",
  "position": {
    "row": 0,
    "col": 2,
    "width": 1,
    "height": 1
  },
  "settings": {
    "refresh_interval": 60,
    "auto_resize": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "panel_id": "panel_3",
    "message": "Panel added successfully"
  }
}
```

---

### PUT /dashboards/{dashboard_id}/panels/{panel_id}
Update a dashboard panel.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Updated Network Traffic",
  "position": {
    "row": 1,
    "col": 0,
    "width": 2,
    "height": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Panel updated successfully"
  }
}
```

---

### DELETE /dashboards/{dashboard_id}/panels/{panel_id}
Remove a panel from dashboard.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Panel removed successfully"
  }
}
```

## Export and Sharing

### GET /charts/{chart_id}/export
Export chart in various formats.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `format`: Export format (png, svg, pdf, json)
- `width`: Image width (default: chart width)
- `height`: Image height (default: chart height)
- `dpi`: Image DPI for raster formats (default: 96)

**Response:** File download or data URL

---

### GET /dashboards/{dashboard_id}/export
Export entire dashboard.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `format`: Export format (pdf, png, json)
- `layout`: Layout mode (grid, stacked)
- `quality`: Export quality (low, medium, high)

**Response:** File download

---

### POST /dashboards/{dashboard_id}/share
Create shareable link for dashboard.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "expires_in": 86400,
  "permissions": ["view"],
  "password_protected": false,
  "allowed_domains": ["company.com"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "share_id": "share_789",
    "share_url": "https://api.splunk-mcp.com/shared/dash_456/share_789",
    "expires_at": "2025-01-23T10:45:00Z",
    "permissions": ["view"]
  }
}
```

## Real-time Updates

### WebSocket: /ws/charts/{chart_id}
Subscribe to real-time chart updates.

**Connection:** `ws://localhost:8002/ws/charts/chart_123?token=jwt_token`

**Message Types:**
```json
// Data update
{
  "type": "data_update",
  "chart_id": "chart_123",
  "data": {
    "new_point": {
      "timestamp": "2025-01-22T10:45:00Z",
      "value": 75.2
    }
  }
}

// Configuration change
{
  "type": "config_update", 
  "chart_id": "chart_123",
  "config": {
    "title": "Updated Chart Title"
  }
}
```

### WebSocket: /ws/dashboards/{dashboard_id}
Subscribe to real-time dashboard updates.

**Connection:** `ws://localhost:8002/ws/dashboards/dash_456?token=jwt_token`

**Message Types:**
```json
// Panel update
{
  "type": "panel_update",
  "dashboard_id": "dash_456",
  "panel_id": "panel_1",
  "data": {
    "chart_data": {...}
  }
}

// Layout change
{
  "type": "layout_update",
  "dashboard_id": "dash_456",
  "layout": {
    "panels": [...]
  }
}
```

## Templates and Themes

### GET /templates
Get available chart and dashboard templates.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "chart_templates": [
      {
        "id": "template_1",
        "name": "Performance Monitoring",
        "chart_type": "line",
        "description": "Time series chart for performance metrics",
        "preview_url": "/api/v1/visualization/templates/template_1/preview"
      }
    ],
    "dashboard_templates": [
      {
        "id": "dash_template_1",
        "name": "System Overview",
        "description": "Complete system monitoring dashboard",
        "panels_count": 6,
        "preview_url": "/api/v1/visualization/templates/dash_template_1/preview"
      }
    ]
  }
}
```

---

### GET /themes
Get available themes and color schemes.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "themes": [
      {
        "id": "light",
        "name": "Light Theme",
        "background": "#ffffff",
        "text": "#333333",
        "primary": "#007bff"
      },
      {
        "id": "dark",
        "name": "Dark Theme", 
        "background": "#1a1a1a",
        "text": "#ffffff",
        "primary": "#4dabf7"
      }
    ],
    "color_schemes": [
      {
        "id": "modern",
        "name": "Modern",
        "colors": ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0"]
      },
      {
        "id": "professional",
        "name": "Professional",
        "colors": ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D"]
      }
    ]
  }
}
```

## Service Configuration

### GET /capabilities
Get visualization service capabilities.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "supported_formats": {
      "input": ["json", "csv", "splunk_results"],
      "output": ["png", "svg", "pdf", "html", "json"]
    },
    "chart_types": ["bar", "line", "pie", "scatter", "heatmap", "treemap"],
    "max_data_points": 10000,
    "max_dashboard_panels": 50,
    "real_time_updates": true,
    "features": {
      "interactive_charts": true,
      "custom_themes": true,
      "export_capabilities": true,
      "dashboard_sharing": true,
      "responsive_design": true
    },
    "limits": {
      "charts_per_user": 1000,
      "dashboards_per_user": 100,
      "concurrent_websocket_connections": 50
    }
  }
}
```

---

### GET /health
Service health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-22T10:50:00Z",
  "dependencies": {
    "database": "healthy",
    "redis": "healthy",
    "file_storage": "healthy"
  },
  "performance": {
    "avg_chart_generation_time": "95ms",
    "charts_generated_last_hour": 543,
    "active_dashboards": 127,
    "websocket_connections": 23
  }
}
```

## Error Handling

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_CHART_TYPE` | 400 | Unsupported chart type |
| `INVALID_DATA_FORMAT` | 400 | Data format not supported |
| `DATA_TOO_LARGE` | 400 | Data exceeds size limits |
| `CHART_NOT_FOUND` | 404 | Chart ID does not exist |
| `DASHBOARD_NOT_FOUND` | 404 | Dashboard ID does not exist |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `EXPORT_FAILED` | 500 | Chart/dashboard export failed |
| `GENERATION_TIMEOUT` | 504 | Chart generation timed out |

---

*Last Updated: January 22, 2025*
*Service Version: 1.0*