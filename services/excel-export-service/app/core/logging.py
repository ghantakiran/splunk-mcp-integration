"""
Logging configuration.
"""

import logging
import logging.config
import sys
from typing import Dict, Any

from app.core.config import settings


def setup_logging():
    """Setup logging configuration."""
    
    # Logging configuration
    log_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            }
        },
        "handlers": {
            "default": {
                "formatter": "json" if settings.LOG_FORMAT == "json" else "default",
                "class": "logging.StreamHandler",
                "stream": sys.stdout
            }
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["default"]
        },
        "loggers": {
            "uvicorn": {
                "level": "INFO",
                "handlers": ["default"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["default"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["default"],
                "propagate": False
            },
            "app": {
                "level": settings.LOG_LEVEL,
                "handlers": ["default"],
                "propagate": False
            }
        }
    }
    
    # Apply configuration
    logging.config.dictConfig(log_config)
    
    # Set up root logger
    logging.getLogger().setLevel(settings.LOG_LEVEL)