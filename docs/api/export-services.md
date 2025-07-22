# Export Services Documentation

## Overview

The Export Services provide comprehensive document generation capabilities supporting multiple formats including PDF, PowerPoint, Word, CSV, and HTML reports. Each service offers advanced customization, templating, and background processing capabilities.

**Service Ports:**
- PDF Export Service: 8009
- PowerPoint Export Service: 8011  
- Word Export Service: 8013
- CSV Export Service: 8014
- HTML Report Service: 8012

**Base URL Pattern**: `/api/v1/export/{service}`

## PDF Export Service

### POST /api/v1/export/pdf/generate
Generate PDF document with custom layout and content.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Splunk Analysis Report",
  "template": "professional",
  "content": [
    {
      "type": "text",
      "content": "# Executive Summary\n\nThis report provides comprehensive analysis of system performance metrics.",
      "style": {
        "font_size": 12,
        "font_family": "Arial",
        "color": "#333333"
      }
    },
    {
      "type": "chart",
      "chart_id": "chart_123",
      "title": "Error Trends",
      "width": 600,
      "height": 400
    },
    {
      "type": "table",
      "data": {
        "headers": ["Metric", "Value", "Status"],
        "rows": [
          ["Error Rate", "2.3%", "Normal"],
          ["Response Time", "150ms", "Good"],
          ["Uptime", "99.9%", "Excellent"]
        ]
      },
      "style": {
        "border": true,
        "header_background": "#f5f5f5"
      }
    },
    {
      "type": "page_break"
    },
    {
      "type": "image",
      "url": "https://example.com/logo.png",
      "width": 200,
      "height": 100,
      "alignment": "center"
    }
  ],
  "layout": {
    "page_size": "A4",
    "orientation": "portrait",
    "margins": {
      "top": 20,
      "bottom": 20,
      "left": 20,
      "right": 20
    }
  },
  "header": {
    "text": "Splunk MCP Report",
    "font_size": 10,
    "alignment": "center"
  },
  "footer": {
    "text": "Page {page_number} of {total_pages}",
    "font_size": 8,
    "alignment": "right"
  },
  "metadata": {
    "author": "Splunk MCP",
    "subject": "System Analysis Report",
    "keywords": ["splunk", "analysis", "performance"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "pdf_job_123",
    "status": "completed",
    "file_path": "/tmp/reports/report_123.pdf",
    "download_url": "/api/v1/export/pdf/jobs/pdf_job_123/download",
    "file_size": "2.5MB",
    "pages": 5,
    "generation_time": "3.2s",
    "expires_at": "2025-01-29T11:00:00Z"
  }
}
```

---

### GET /api/v1/export/pdf/templates
Get available PDF templates.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "id": "professional",
        "name": "Professional Report",
        "description": "Clean, corporate style with header/footer",
        "preview_url": "/api/v1/export/pdf/templates/professional/preview",
        "variables": ["company_logo", "primary_color", "font_family"]
      },
      {
        "id": "minimal",
        "name": "Minimal Design",
        "description": "Simple, clean layout without decorative elements",
        "preview_url": "/api/v1/export/pdf/templates/minimal/preview",
        "variables": ["font_size", "line_spacing"]
      },
      {
        "id": "technical",
        "name": "Technical Document", 
        "description": "Optimized for technical documentation with code blocks",
        "preview_url": "/api/v1/export/pdf/templates/technical/preview",
        "variables": ["code_theme", "highlight_color"]
      }
    ]
  }
}
```

## PowerPoint Export Service

### POST /api/v1/export/powerpoint/generate
Generate PowerPoint presentation with themes and animations.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "System Performance Analysis",
  "theme": "corporate",
  "slides": [
    {
      "type": "title_slide",
      "title": "System Performance Analysis",
      "subtitle": "Monthly Review - January 2025",
      "author": "DevOps Team"
    },
    {
      "type": "content_slide",
      "title": "Key Metrics Overview",
      "content": [
        {
          "type": "text",
          "content": "• System uptime: 99.9%\n• Average response time: 150ms\n• Error rate: 2.3%",
          "bullet_style": "modern"
        },
        {
          "type": "chart",
          "chart_id": "chart_124",
          "position": {
            "x": 400,
            "y": 200,
            "width": 500,
            "height": 300
          }
        }
      ]
    },
    {
      "type": "comparison_slide",
      "title": "Before vs After Optimization",
      "left_content": {
        "title": "Before",
        "items": ["Response time: 300ms", "Error rate: 5.2%", "Uptime: 98.5%"]
      },
      "right_content": {
        "title": "After",
        "items": ["Response time: 150ms", "Error rate: 2.3%", "Uptime: 99.9%"]
      }
    },
    {
      "type": "chart_slide",
      "title": "Performance Trends",
      "chart_id": "chart_125",
      "notes": "Significant improvement seen after optimization implementation"
    }
  ],
  "animations": {
    "slide_transition": "fade",
    "content_animation": "fly_in_from_left",
    "timing": "automatic"
  },
  "export_format": "pptx"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "ppt_job_456",
    "status": "completed",
    "file_path": "/tmp/presentations/presentation_456.pptx",
    "download_url": "/api/v1/export/powerpoint/jobs/ppt_job_456/download",
    "file_size": "8.7MB",
    "slides": 4,
    "generation_time": "5.1s",
    "export_formats": ["pptx", "pdf", "png"],
    "expires_at": "2025-01-29T11:00:00Z"
  }
}
```

---

### GET /api/v1/export/powerpoint/themes
Get available PowerPoint themes.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "themes": [
      {
        "id": "corporate",
        "name": "Corporate",
        "description": "Professional business theme",
        "colors": {
          "primary": "#003366",
          "secondary": "#0066CC",
          "accent": "#FF9900"
        },
        "fonts": {
          "title": "Calibri Bold",
          "body": "Calibri"
        }
      },
      {
        "id": "modern",
        "name": "Modern",
        "description": "Clean, contemporary design",
        "colors": {
          "primary": "#2E86AB",
          "secondary": "#A23B72",
          "accent": "#F18F01"
        },
        "fonts": {
          "title": "Segoe UI Semibold",
          "body": "Segoe UI"
        }
      }
    ]
  }
}
```

## Word Export Service

### POST /api/v1/export/word/generate
Generate Word document with professional formatting.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "System Analysis Report",
  "template": "report",
  "content": [
    {
      "type": "heading",
      "level": 1,
      "text": "Executive Summary",
      "style": "Heading 1"
    },
    {
      "type": "paragraph",
      "text": "This document provides a comprehensive analysis of system performance metrics for the month of January 2025.",
      "style": "Normal"
    },
    {
      "type": "table",
      "data": {
        "headers": ["Metric", "Current Value", "Target", "Status"],
        "rows": [
          ["Response Time", "150ms", "< 200ms", "✓ Met"],
          ["Error Rate", "2.3%", "< 5%", "✓ Met"],
          ["Uptime", "99.9%", "> 99%", "✓ Met"]
        ]
      },
      "style": {
        "table_style": "Medium Grid 1",
        "width": "100%"
      }
    },
    {
      "type": "chart",
      "chart_id": "chart_126",
      "title": "Performance Metrics Trend",
      "width": 600,
      "height": 400
    },
    {
      "type": "page_break"
    },
    {
      "type": "heading",
      "level": 2,
      "text": "Detailed Analysis",
      "style": "Heading 2"
    }
  ],
  "formatting": {
    "font_family": "Calibri",
    "font_size": 11,
    "line_spacing": 1.15,
    "page_margins": {
      "top": 2.54,
      "bottom": 2.54,
      "left": 2.54,
      "right": 2.54
    }
  },
  "header": {
    "text": "Splunk MCP Analysis Report",
    "include_date": true
  },
  "footer": {
    "include_page_numbers": true,
    "text": "Confidential"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "word_job_789",
    "status": "completed", 
    "file_path": "/tmp/documents/document_789.docx",
    "download_url": "/api/v1/export/word/jobs/word_job_789/download",
    "file_size": "1.8MB",
    "pages": 3,
    "word_count": 1247,
    "generation_time": "2.8s",
    "expires_at": "2025-01-29T11:00:00Z"
  }
}
```

## CSV Export Service

### POST /api/v1/export/csv/generate
Generate CSV file with advanced formatting options.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "data_source": {
    "type": "query",
    "query": "search index=main error | stats count by source, severity | sort -count",
    "time_range": {
      "earliest": "-24h@h",
      "latest": "now"
    }
  },
  "format": {
    "delimiter": ",",
    "quote_char": "\"",
    "escape_char": "\\",
    "encoding": "utf-8",
    "include_headers": true,
    "header_case": "original"
  },
  "processing": {
    "null_value": "N/A",
    "trim_whitespace": true,
    "remove_duplicates": false,
    "max_rows": 10000
  },
  "compression": {
    "enabled": true,
    "type": "gzip",
    "level": 6
  },
  "column_mapping": [
    {
      "source": "source",
      "target": "Error Source",
      "data_type": "string"
    },
    {
      "source": "severity",
      "target": "Severity Level",
      "data_type": "string"
    },
    {
      "source": "count",
      "target": "Count",
      "data_type": "integer",
      "format": "#,##0"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "csv_job_101",
    "status": "completed",
    "file_path": "/tmp/exports/export_101.csv.gz",
    "download_url": "/api/v1/export/csv/jobs/csv_job_101/download",
    "file_size": "45.2KB",
    "uncompressed_size": "180.5KB",
    "rows": 1500,
    "columns": 3,
    "generation_time": "1.5s",
    "compression_ratio": 0.25,
    "expires_at": "2025-01-29T11:00:00Z"
  }
}
```

---

### GET /api/v1/export/csv/templates
Get predefined CSV export templates.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "id": "standard_csv",
        "name": "Standard CSV",
        "description": "Basic CSV format with headers",
        "format": {
          "delimiter": ",",
          "encoding": "utf-8",
          "include_headers": true
        }
      },
      {
        "id": "excel_compatible",
        "name": "Excel Compatible",
        "description": "CSV format optimized for Excel import",
        "format": {
          "delimiter": ",",
          "encoding": "utf-8-bom",
          "quote_all": true
        }
      },
      {
        "id": "tab_separated",
        "name": "Tab Separated",
        "description": "Tab-delimited format for database imports",
        "format": {
          "delimiter": "\t",
          "encoding": "utf-8",
          "include_headers": true
        }
      }
    ]
  }
}
```

## HTML Report Service

### POST /api/v1/export/html/generate
Generate interactive HTML report.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Interactive System Dashboard",
  "template": "modern",
  "content": [
    {
      "type": "header",
      "title": "System Performance Report",
      "subtitle": "Real-time Analytics Dashboard",
      "logo_url": "https://company.com/logo.png"
    },
    {
      "type": "metrics_grid",
      "metrics": [
        {
          "label": "Uptime",
          "value": "99.9%",
          "trend": "up",
          "color": "green"
        },
        {
          "label": "Response Time",
          "value": "150ms",
          "trend": "down",
          "color": "blue"
        },
        {
          "label": "Error Rate",
          "value": "2.3%",
          "trend": "down",
          "color": "orange"
        }
      ]
    },
    {
      "type": "interactive_chart",
      "chart_id": "chart_127",
      "title": "Performance Trends",
      "controls": {
        "time_range_selector": true,
        "filter_controls": true,
        "export_button": true
      }
    },
    {
      "type": "data_table",
      "data": {
        "headers": ["Service", "Status", "Response Time", "Last Check"],
        "rows": [
          ["API Gateway", "Healthy", "45ms", "2025-01-22T11:30:00Z"],
          ["Database", "Healthy", "12ms", "2025-01-22T11:30:00Z"],
          ["Cache", "Warning", "89ms", "2025-01-22T11:29:00Z"]
        ]
      },
      "features": {
        "sortable": true,
        "filterable": true,
        "paginated": true,
        "exportable": true
      }
    }
  ],
  "interactivity": {
    "theme_switcher": true,
    "fullscreen_mode": true,
    "print_friendly": true,
    "mobile_responsive": true
  },
  "branding": {
    "primary_color": "#007bff",
    "secondary_color": "#6c757d",
    "logo_url": "https://company.com/logo.png",
    "company_name": "Acme Corporation"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "html_job_202",
    "status": "completed",
    "file_path": "/tmp/reports/report_202.html",
    "view_url": "/api/v1/export/html/jobs/html_job_202/view",
    "download_url": "/api/v1/export/html/jobs/html_job_202/download",
    "file_size": "2.1MB",
    "interactive_elements": 8,
    "generation_time": "2.3s",
    "mobile_optimized": true,
    "expires_at": "2025-01-29T11:00:00Z"
  }
}
```

## Job Management (Common Across All Services)

### GET /api/v1/export/{service}/jobs
List export jobs with filtering.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `status`: Filter by status (pending, processing, completed, failed)
- `start_date`: Start date for job creation
- `end_date`: End date for job creation
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)

**Response:**
```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": "pdf_job_123",
        "title": "System Analysis Report",
        "status": "completed",
        "format": "pdf",
        "file_size": "2.5MB",
        "created_at": "2025-01-22T11:00:00Z",
        "completed_at": "2025-01-22T11:00:03Z",
        "expires_at": "2025-01-29T11:00:00Z",
        "download_url": "/api/v1/export/pdf/jobs/pdf_job_123/download"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 5,
      "pages": 1
    }
  }
}
```

---

### GET /api/v1/export/{service}/jobs/{job_id}
Get job details and status.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "pdf_job_123",
    "title": "System Analysis Report",
    "status": "completed",
    "progress": 100,
    "format": "pdf",
    "template": "professional",
    "file_size": "2.5MB",
    "pages": 5,
    "generation_time": "3.2s",
    "created_at": "2025-01-22T11:00:00Z",
    "started_at": "2025-01-22T11:00:01Z",
    "completed_at": "2025-01-22T11:00:03Z",
    "expires_at": "2025-01-29T11:00:00Z",
    "download_url": "/api/v1/export/pdf/jobs/pdf_job_123/download",
    "metadata": {
      "author": "user_123",
      "content_sections": 4,
      "charts_embedded": 2,
      "tables_included": 1
    }
  }
}
```

---

### GET /api/v1/export/{service}/jobs/{job_id}/download
Download generated file.

**Headers:** `Authorization: Bearer <token>`

**Response:** File download with appropriate MIME type and headers

---

### DELETE /api/v1/export/{service}/jobs/{job_id}
Delete export job and file.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Job and associated file deleted successfully"
  }
}
```

## Bulk Operations

### POST /api/v1/export/bulk
Generate multiple exports in batch.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "exports": [
    {
      "service": "pdf",
      "title": "Weekly Report - PDF",
      "template": "professional",
      "content": {...}
    },
    {
      "service": "powerpoint",
      "title": "Weekly Report - Presentation",
      "theme": "corporate",
      "slides": [...]
    },
    {
      "service": "csv",
      "title": "Raw Data Export",
      "data_source": {...}
    }
  ],
  "batch_settings": {
    "parallel_processing": true,
    "notify_on_completion": true,
    "auto_zip": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "batch_id": "batch_555",
    "total_jobs": 3,
    "job_ids": ["pdf_job_123", "ppt_job_456", "csv_job_789"],
    "estimated_completion": "2025-01-22T11:05:00Z",
    "status_url": "/api/v1/export/bulk/batch_555/status"
  }
}
```

## Service Configuration

### GET /api/v1/export/{service}/capabilities
Get service capabilities and limits.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "service": "pdf",
    "version": "1.0.0",
    "supported_formats": ["pdf", "html"],
    "max_file_size": "50MB",
    "max_pages": 500,
    "max_content_sections": 100,
    "max_concurrent_jobs": 10,
    "job_retention_days": 7,
    "supported_templates": ["professional", "minimal", "technical"],
    "features": {
      "custom_headers_footers": true,
      "chart_embedding": true,
      "table_formatting": true,
      "page_breaks": true,
      "watermarks": true
    }
  }
}
```

## Error Handling

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_TEMPLATE` | 400 | Template not found or invalid |
| `CONTENT_TOO_LARGE` | 400 | Content exceeds size limits |
| `INVALID_FORMAT` | 400 | Unsupported export format |
| `CHART_NOT_FOUND` | 404 | Referenced chart ID not found |
| `JOB_NOT_FOUND` | 404 | Export job ID not found |
| `GENERATION_FAILED` | 500 | Document generation failed |
| `FILE_NOT_AVAILABLE` | 410 | Generated file expired or deleted |
| `QUOTA_EXCEEDED` | 429 | User export quota exceeded |

---

*Last Updated: January 22, 2025*
*Service Version: 1.0*