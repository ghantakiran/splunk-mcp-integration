"""
Metrics utilities for Email Service.
"""

from prometheus_client import (
    CollectorRegistry, Counter, Histogram, Gauge, Info,
    generate_latest, CONTENT_TYPE_LATEST
)

from app.core.config import settings

# Global metrics registry
_metrics_registry = None


def setup_metrics() -> CollectorRegistry:
    """Setup Prometheus metrics."""
    global _metrics_registry
    
    if _metrics_registry is None:
        _metrics_registry = CollectorRegistry()
        
        # Application info
        app_info = Info(
            'email_service_info',
            'Email service information',
            registry=_metrics_registry
        )
        app_info.info({
            'version': settings.version,
            'environment': settings.environment
        })
        
        # Email metrics
        Counter(
            'emails_sent_total',
            'Total number of emails sent',
            ['email_type', 'status'],
            registry=_metrics_registry
        )
        
        Counter(
            'email_processing_errors_total',
            'Total number of email processing errors',
            ['error_type'],
            registry=_metrics_registry
        )
        
        Histogram(
            'email_processing_duration_seconds',
            'Time spent processing emails',
            ['email_type'],
            registry=_metrics_registry
        )
        
        Histogram(
            'email_delivery_duration_seconds',
            'Time spent delivering emails',
            ['delivery_type'],
            registry=_metrics_registry
        )
        
        # Queue metrics
        Gauge(
            'email_queue_size',
            'Current size of email queue',
            ['queue_name'],
            registry=_metrics_registry
        )
        
        Gauge(
            'email_queue_processing_time_seconds',
            'Average processing time for email queue',
            ['queue_name'],
            registry=_metrics_registry
        )
        
        # Report metrics
        Counter(
            'reports_generated_total',
            'Total number of reports generated',
            ['report_type', 'format', 'status'],
            registry=_metrics_registry
        )
        
        Histogram(
            'report_generation_duration_seconds',
            'Time spent generating reports',
            ['report_type', 'format'],
            registry=_metrics_registry
        )
        
        # User metrics
        Gauge(
            'active_users_total',
            'Number of active users',
            registry=_metrics_registry
        )
        
        Counter(
            'user_actions_total',
            'Total number of user actions',
            ['action_type'],
            registry=_metrics_registry
        )
        
        # System metrics
        Gauge(
            'database_connections_active',
            'Number of active database connections',
            registry=_metrics_registry
        )
        
        Gauge(
            'redis_connections_active', 
            'Number of active Redis connections',
            registry=_metrics_registry
        )
        
        # Rate limiting metrics
        Counter(
            'rate_limit_exceeded_total',
            'Total number of rate limit violations',
            ['limit_type'],
            registry=_metrics_registry
        )
        
        Counter(
            'api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status_code'],
            registry=_metrics_registry
        )
        
        Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint'],
            registry=_metrics_registry
        )
    
    return _metrics_registry


def get_metrics_registry() -> CollectorRegistry:
    """Get the metrics registry."""
    if _metrics_registry is None:
        return setup_metrics()
    return _metrics_registry


def record_email_sent(email_type: str, status: str):
    """Record email sent metric."""
    registry = get_metrics_registry()
    counter = None
    for collector in registry._collector_to_names:
        if hasattr(collector, '_name') and collector._name == 'emails_sent_total':
            counter = collector
            break
    
    if counter:
        counter.labels(email_type=email_type, status=status).inc()


def record_email_processing_time(email_type: str, duration: float):
    """Record email processing time metric."""
    registry = get_metrics_registry()
    histogram = None
    for collector in registry._collector_to_names:
        if hasattr(collector, '_name') and collector._name == 'email_processing_duration_seconds':
            histogram = collector
            break
    
    if histogram:
        histogram.labels(email_type=email_type).observe(duration)


def record_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record API request metrics."""
    registry = get_metrics_registry()
    
    # Find and update counter
    for collector in registry._collector_to_names:
        if hasattr(collector, '_name') and collector._name == 'api_requests_total':
            collector.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
            break
    
    # Find and update histogram
    for collector in registry._collector_to_names:
        if hasattr(collector, '_name') and collector._name == 'api_request_duration_seconds':
            collector.labels(method=method, endpoint=endpoint).observe(duration)
            break


def update_queue_size(queue_name: str, size: int):
    """Update queue size metric."""
    registry = get_metrics_registry()
    for collector in registry._collector_to_names:
        if hasattr(collector, '_name') and collector._name == 'email_queue_size':
            collector.labels(queue_name=queue_name).set(size)
            break


def record_rate_limit_exceeded(limit_type: str):
    """Record rate limit exceeded metric."""
    registry = get_metrics_registry()
    for collector in registry._collector_to_names:
        if hasattr(collector, '_name') and collector._name == 'rate_limit_exceeded_total':
            collector.labels(limit_type=limit_type).inc()
            break