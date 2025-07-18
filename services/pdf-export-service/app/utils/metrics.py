"""
Metrics utilities for PDF Export Service.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import structlog
from typing import Dict, Any

logger = structlog.get_logger(__name__)

# PDF Generation Metrics
PDF_GENERATION_COUNT = Counter(
    'pdf_generation_total',
    'Total PDF generations',
    ['template_type', 'status', 'output_format']
)

PDF_GENERATION_DURATION = Histogram(
    'pdf_generation_duration_seconds',
    'PDF generation duration in seconds',
    ['template_type', 'output_format']
)

PDF_GENERATION_FILE_SIZE = Histogram(
    'pdf_generation_file_size_bytes',
    'PDF generation file size in bytes',
    ['template_type', 'output_format']
)

PDF_GENERATION_PAGE_COUNT = Histogram(
    'pdf_generation_page_count',
    'PDF generation page count',
    ['template_type', 'output_format']
)

# Template Metrics
TEMPLATE_OPERATIONS = Counter(
    'template_operations_total',
    'Total template operations',
    ['operation', 'template_type', 'status']
)

TEMPLATE_USAGE = Counter(
    'template_usage_total',
    'Total template usage',
    ['template_id', 'template_type']
)

# Active Jobs Metrics
ACTIVE_JOBS = Gauge(
    'active_jobs',
    'Number of active PDF generation jobs'
)

QUEUED_JOBS = Gauge(
    'queued_jobs', 
    'Number of queued PDF generation jobs'
)

# User Metrics
USER_OPERATIONS = Counter(
    'user_operations_total',
    'Total user operations',
    ['operation', 'user_role']
)

# System Metrics
SYSTEM_INFO = Info(
    'pdf_export_service_info',
    'PDF Export Service information'
)

# Error Metrics
ERROR_COUNT = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'operation']
)

# Cache Metrics
CACHE_OPERATIONS = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'cache_type']
)

CACHE_HIT_RATIO = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio',
    ['cache_type']
)

# Database Metrics
DATABASE_OPERATIONS = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'table']
)

DATABASE_QUERY_DURATION = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table']
)

# Rate Limiting Metrics
RATE_LIMIT_HITS = Counter(
    'rate_limit_hits_total',
    'Total rate limit hits',
    ['limit_type', 'user_id']
)

# File Operations Metrics
FILE_OPERATIONS = Counter(
    'file_operations_total',
    'Total file operations',
    ['operation', 'file_type']
)

FILE_CLEANUP = Counter(
    'file_cleanup_total',
    'Total file cleanup operations',
    ['status']
)


def setup_metrics():
    """Setup and initialize metrics."""
    try:
        # Set system info
        SYSTEM_INFO.info({
            'version': '1.0.0',
            'service': 'pdf-export-service',
            'description': 'Advanced PDF generation service'
        })
        
        logger.info("Metrics setup completed")
        
    except Exception as e:
        logger.error("Failed to setup metrics", error=str(e))


def record_pdf_generation(template_type: str, output_format: str, status: str, 
                         duration: float, file_size: int = None, page_count: int = None):
    """Record PDF generation metrics."""
    try:
        # Record generation count
        PDF_GENERATION_COUNT.labels(
            template_type=template_type,
            status=status,
            output_format=output_format
        ).inc()
        
        # Record duration
        PDF_GENERATION_DURATION.labels(
            template_type=template_type,
            output_format=output_format
        ).observe(duration)
        
        # Record file size if provided
        if file_size is not None:
            PDF_GENERATION_FILE_SIZE.labels(
                template_type=template_type,
                output_format=output_format
            ).observe(file_size)
        
        # Record page count if provided
        if page_count is not None:
            PDF_GENERATION_PAGE_COUNT.labels(
                template_type=template_type,
                output_format=output_format
            ).observe(page_count)
        
    except Exception as e:
        logger.error("Failed to record PDF generation metrics", error=str(e))


def record_template_operation(operation: str, template_type: str, status: str):
    """Record template operation metrics."""
    try:
        TEMPLATE_OPERATIONS.labels(
            operation=operation,
            template_type=template_type,
            status=status
        ).inc()
        
    except Exception as e:
        logger.error("Failed to record template operation metrics", error=str(e))


def record_template_usage(template_id: str, template_type: str):
    """Record template usage metrics."""
    try:
        TEMPLATE_USAGE.labels(
            template_id=template_id,
            template_type=template_type
        ).inc()
        
    except Exception as e:
        logger.error("Failed to record template usage metrics", error=str(e))


def update_active_jobs(count: int):
    """Update active jobs gauge."""
    try:
        ACTIVE_JOBS.set(count)
        
    except Exception as e:
        logger.error("Failed to update active jobs metrics", error=str(e))


def update_queued_jobs(count: int):
    """Update queued jobs gauge."""
    try:
        QUEUED_JOBS.set(count)
        
    except Exception as e:
        logger.error("Failed to update queued jobs metrics", error=str(e))


def record_user_operation(operation: str, user_role: str):
    """Record user operation metrics."""
    try:
        USER_OPERATIONS.labels(
            operation=operation,
            user_role=user_role
        ).inc()
        
    except Exception as e:
        logger.error("Failed to record user operation metrics", error=str(e))


def record_error(error_type: str, operation: str):
    """Record error metrics."""
    try:
        ERROR_COUNT.labels(
            error_type=error_type,
            operation=operation
        ).inc()
        
    except Exception as e:
        logger.error("Failed to record error metrics", error=str(e))


def record_cache_operation(operation: str, cache_type: str):
    """Record cache operation metrics."""
    try:
        CACHE_OPERATIONS.labels(
            operation=operation,
            cache_type=cache_type
        ).inc()
        
    except Exception as e:
        logger.error("Failed to record cache operation metrics", error=str(e))


def update_cache_hit_ratio(cache_type: str, ratio: float):
    """Update cache hit ratio gauge."""
    try:
        CACHE_HIT_RATIO.labels(cache_type=cache_type).set(ratio)
        
    except Exception as e:
        logger.error("Failed to update cache hit ratio metrics", error=str(e))


def record_database_operation(operation: str, table: str, duration: float = None):
    """Record database operation metrics."""
    try:
        DATABASE_OPERATIONS.labels(
            operation=operation,
            table=table
        ).inc()
        
        if duration is not None:
            DATABASE_QUERY_DURATION.labels(
                operation=operation,
                table=table
            ).observe(duration)
        
    except Exception as e:
        logger.error("Failed to record database operation metrics", error=str(e))


def record_rate_limit_hit(limit_type: str, user_id: str):
    """Record rate limit hit metrics."""
    try:
        RATE_LIMIT_HITS.labels(
            limit_type=limit_type,
            user_id=user_id
        ).inc()
        
    except Exception as e:
        logger.error("Failed to record rate limit hit metrics", error=str(e))


def record_file_operation(operation: str, file_type: str):
    """Record file operation metrics."""
    try:
        FILE_OPERATIONS.labels(
            operation=operation,
            file_type=file_type
        ).inc()
        
    except Exception as e:
        logger.error("Failed to record file operation metrics", error=str(e))


def record_file_cleanup(status: str):
    """Record file cleanup metrics."""
    try:
        FILE_CLEANUP.labels(status=status).inc()
        
    except Exception as e:
        logger.error("Failed to record file cleanup metrics", error=str(e))


def get_metrics_summary() -> Dict[str, Any]:
    """Get metrics summary."""
    try:
        return {
            "pdf_generations": PDF_GENERATION_COUNT._value.sum(),
            "template_operations": TEMPLATE_OPERATIONS._value.sum(),
            "active_jobs": ACTIVE_JOBS._value.get(),
            "queued_jobs": QUEUED_JOBS._value.get(),
            "total_errors": ERROR_COUNT._value.sum(),
            "cache_operations": CACHE_OPERATIONS._value.sum(),
            "database_operations": DATABASE_OPERATIONS._value.sum(),
            "rate_limit_hits": RATE_LIMIT_HITS._value.sum(),
            "file_operations": FILE_OPERATIONS._value.sum()
        }
        
    except Exception as e:
        logger.error("Failed to get metrics summary", error=str(e))
        return {}


# Initialize metrics on import
setup_metrics()