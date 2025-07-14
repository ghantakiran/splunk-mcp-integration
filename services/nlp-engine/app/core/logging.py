"""
Structured logging configuration for NLP Engine service
"""

import logging
import sys
from typing import Any, Dict, Optional
import structlog
from structlog.typing import EventDict, WrappedLogger
import json
from datetime import datetime

from .config import settings


def add_timestamp(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add timestamp to log entries"""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_service_info(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service information to log entries"""
    event_dict["service"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def add_log_level(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to event dict"""
    event_dict["level"] = method_name.upper()
    return event_dict


def serialize_json(obj: Any) -> str:
    """Custom JSON serializer for log events"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, "__dict__"):
        return str(obj)
    return str(obj)


def configure_logging():
    """Configure structured logging for the application"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
    
    # Shared processors for all configurations
    shared_processors = [
        structlog.stdlib.filter_by_level,
        add_timestamp,
        add_service_info,
        add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if settings.structured_logging:
        if settings.log_json_format:
            # JSON formatting for production
            processors = shared_processors + [
                structlog.processors.JSONRenderer(serializer=lambda obj, **kwargs: json.dumps(obj, default=serialize_json))
            ]
        else:
            # Pretty formatting for development
            processors = shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True)
            ]
    else:
        # Simple string formatting
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Set up specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding context to logs"""
    
    def __init__(self, **context):
        self.context = context
        self.token = None
    
    def __enter__(self):
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            structlog.contextvars.unbind_contextvars(self.token)


def log_function_call(logger: structlog.stdlib.BoundLogger):
    """Decorator to log function calls"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug("Function call started", function=func_name, args=len(args), kwargs=list(kwargs.keys()))
            try:
                result = await func(*args, **kwargs)
                logger.debug("Function call completed", function=func_name)
                return result
            except Exception as e:
                logger.error("Function call failed", function=func_name, error=str(e), error_type=type(e).__name__)
                raise
        
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug("Function call started", function=func_name, args=len(args), kwargs=list(kwargs.keys()))
            try:
                result = func(*args, **kwargs)
                logger.debug("Function call completed", function=func_name)
                return result
            except Exception as e:
                logger.error("Function call failed", function=func_name, error=str(e), error_type=type(e).__name__)
                raise
        
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # Check if coroutine
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_api_request(logger: structlog.stdlib.BoundLogger):
    """Decorator to log API requests"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request info if available
            request_info = {}
            for arg in args:
                if hasattr(arg, "method") and hasattr(arg, "url"):
                    request_info = {
                        "method": arg.method,
                        "path": str(arg.url.path),
                        "query_params": str(arg.url.query) if arg.url.query else None
                    }
                    break
            
            logger.info("API request started", **request_info)
            try:
                result = await func(*args, **kwargs)
                logger.info("API request completed", **request_info)
                return result
            except Exception as e:
                logger.error(
                    "API request failed", 
                    error=str(e), 
                    error_type=type(e).__name__,
                    **request_info
                )
                raise
        
        return wrapper
    return decorator


class NLPMetrics:
    """NLP-specific metrics logging"""
    
    def __init__(self, logger: structlog.stdlib.BoundLogger):
        self.logger = logger
    
    def log_nlp_request(
        self, 
        request_type: str, 
        input_text: str, 
        processing_time: Optional[float] = None,
        token_count: Optional[int] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log NLP processing request"""
        metrics = {
            "request_type": request_type,
            "input_length": len(input_text),
            "processing_time": processing_time,
            "token_count": token_count,
            "success": success
        }
        
        if error:
            metrics["error"] = error
        
        if success:
            self.logger.info("NLP request processed", **metrics)
        else:
            self.logger.error("NLP request failed", **metrics)
    
    def log_ai_api_call(
        self,
        provider: str,
        model: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        processing_time: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log AI API calls"""
        metrics = {
            "ai_provider": provider,
            "ai_model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "processing_time": processing_time,
            "success": success
        }
        
        if error:
            metrics["error"] = error
        
        if success:
            self.logger.info("AI API call completed", **metrics)
        else:
            self.logger.error("AI API call failed", **metrics)
    
    def log_spl_translation(
        self,
        natural_query: str,
        generated_spl: Optional[str] = None,
        confidence_score: Optional[float] = None,
        processing_time: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log SPL translation attempts"""
        metrics = {
            "query_length": len(natural_query),
            "spl_length": len(generated_spl) if generated_spl else 0,
            "confidence_score": confidence_score,
            "processing_time": processing_time,
            "success": success
        }
        
        if error:
            metrics["error"] = error
        
        if success:
            self.logger.info("SPL translation completed", **metrics)
        else:
            self.logger.error("SPL translation failed", **metrics)