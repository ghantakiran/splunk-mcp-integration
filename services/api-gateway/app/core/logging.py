"""
Structured logging configuration
"""

import logging
import sys
from typing import Any, Dict
from datetime import datetime
import structlog
from structlog.stdlib import LoggerFactory
from .config import settings


def configure_logging():
    """Configure structured logging with structlog"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add timestamp
            structlog.processors.TimeStamper(fmt="ISO"),
            # Add log level
            structlog.stdlib.add_log_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add extra context
            structlog.processors.CallsiteParameterAdder(),
            # Format for console output
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
    
    # Set logging levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )
    logging.getLogger("redis").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)


class RequestLoggingMiddleware:
    """Middleware for logging HTTP requests and responses"""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("request")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            
            # Extract request info
            method = scope["method"]
            path = scope["path"]
            query_string = scope.get("query_string", b"").decode()
            client_ip = None
            
            # Extract client IP
            if scope.get("client"):
                client_ip = scope["client"][0]
            
            # Check for forwarded headers
            headers = dict(scope.get("headers", []))
            x_forwarded_for = headers.get(b"x-forwarded-for")
            if x_forwarded_for:
                client_ip = x_forwarded_for.decode().split(",")[0].strip()
            
            # Log request start
            self.logger.info(
                "Request started",
                request_id=request_id,
                method=method,
                path=path,
                query_string=query_string,
                client_ip=client_ip,
                user_agent=headers.get(b"user-agent", b"").decode(),
            )
            
            # Capture response
            status_code = None
            
            async def send_wrapper(message):
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                await send(message)
            
            try:
                await self.app(scope, receive, send_wrapper)
                
                # Log request completion
                self.logger.info(
                    "Request completed",
                    request_id=request_id,
                    method=method,
                    path=path,
                    status_code=status_code,
                    client_ip=client_ip,
                )
                
            except Exception as e:
                # Log request error
                self.logger.error(
                    "Request failed",
                    request_id=request_id,
                    method=method,
                    path=path,
                    client_ip=client_ip,
                    error=str(e),
                    exc_info=True,
                )
                raise
        else:
            await self.app(scope, receive, send)


class SecurityEventLogger:
    """Logger for security-related events"""
    
    def __init__(self):
        self.logger = get_logger("security")
    
    def log_authentication_success(
        self, 
        user_id: str, 
        username: str, 
        client_ip: str = None,
        user_agent: str = None
    ):
        """Log successful authentication"""
        self.logger.info(
            "Authentication successful",
            event_type="auth_success",
            user_id=user_id,
            username=username,
            client_ip=client_ip,
            user_agent=user_agent,
        )
    
    def log_authentication_failure(
        self, 
        username: str, 
        reason: str,
        client_ip: str = None,
        user_agent: str = None
    ):
        """Log failed authentication"""
        self.logger.warning(
            "Authentication failed",
            event_type="auth_failure",
            username=username,
            reason=reason,
            client_ip=client_ip,
            user_agent=user_agent,
        )
    
    def log_authorization_failure(
        self, 
        user_id: str, 
        resource: str, 
        action: str,
        client_ip: str = None
    ):
        """Log authorization failure"""
        self.logger.warning(
            "Authorization failed",
            event_type="authz_failure",
            user_id=user_id,
            resource=resource,
            action=action,
            client_ip=client_ip,
        )
    
    def log_suspicious_activity(
        self, 
        event_type: str, 
        description: str, 
        details: Dict[str, Any] = None,
        client_ip: str = None,
        user_id: str = None
    ):
        """Log suspicious activity"""
        self.logger.error(
            "Suspicious activity detected",
            event_type=event_type,
            description=description,
            details=details or {},
            client_ip=client_ip,
            user_id=user_id,
        )
    
    def log_session_event(
        self, 
        event_type: str, 
        user_id: str, 
        session_id: str,
        client_ip: str = None
    ):
        """Log session-related events"""
        self.logger.info(
            f"Session {event_type}",
            event_type=f"session_{event_type}",
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
        )


# Global instances
security_logger = SecurityEventLogger()


class QueryLogger:
    """Logger for query-related events"""
    
    def __init__(self):
        self.logger = get_logger("query")
    
    def log_query_start(
        self, 
        query_id: str, 
        user_id: str, 
        natural_query: str,
        spl_query: str = None
    ):
        """Log query start"""
        self.logger.info(
            "Query started",
            query_id=query_id,
            user_id=user_id,
            natural_query=natural_query,
            spl_query=spl_query,
        )
    
    def log_query_success(
        self, 
        query_id: str, 
        execution_time_ms: int,
        result_count: int = None
    ):
        """Log query success"""
        self.logger.info(
            "Query completed successfully",
            query_id=query_id,
            execution_time_ms=execution_time_ms,
            result_count=result_count,
        )
    
    def log_query_failure(
        self, 
        query_id: str, 
        error: str,
        execution_time_ms: int = None
    ):
        """Log query failure"""
        self.logger.error(
            "Query failed",
            query_id=query_id,
            error=error,
            execution_time_ms=execution_time_ms,
        )


# Global query logger instance
query_logger = QueryLogger()