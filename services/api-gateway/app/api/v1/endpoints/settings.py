"""
User settings and configuration endpoints
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query as QueryParam
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.logging import get_logger
from ....api.deps import get_async_session, get_current_user, require_permissions
from ....models.user import User
from ....models.profile import (
    NotificationPreferences,
    UIPreferences,
    QueryPreferences,
    SecurityPreferences,
    IntegrationPreferences,
    ThemeMode,
    ChartType,
    DashboardLayout,
    NotificationMethod
)
from ....models.responses import SuccessResponse, COMMON_RESPONSES
from ....services.profile_service import ProfileService
from ....core.exceptions import ValidationError
from ....core.audit import audit_action, AuditAction, AuditResource

router = APIRouter()
logger = get_logger(__name__)
profile_service = ProfileService()


@router.get(
    "/themes",
    status_code=status.HTTP_200_OK,
    summary="Get available themes",
    description="Retrieve list of available UI themes and their configurations",
    responses=COMMON_RESPONSES
)
async def get_available_themes(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get available UI themes"""
    
    themes = {
        "light": {
            "name": "Light",
            "description": "Clean light theme for daytime use",
            "primary_color": "#1976d2",
            "secondary_color": "#424242",
            "background_color": "#fafafa",
            "surface_color": "#ffffff",
            "preview_url": "/static/previews/theme-light.png"
        },
        "dark": {
            "name": "Dark",
            "description": "Dark theme for reduced eye strain",
            "primary_color": "#90caf9",
            "secondary_color": "#f48fb1",
            "background_color": "#121212",
            "surface_color": "#1e1e1e",
            "preview_url": "/static/previews/theme-dark.png"
        },
        "auto": {
            "name": "Auto",
            "description": "Automatically switch based on system preference",
            "primary_color": "dynamic",
            "secondary_color": "dynamic",
            "background_color": "dynamic",
            "surface_color": "dynamic",
            "preview_url": "/static/previews/theme-auto.png"
        }
    }
    
    return {
        "themes": themes,
        "current_theme": current_user.get_preference("ui.theme", "light"),
        "system_preference": "light"  # Would detect from request headers in production
    }


@router.get(
    "/chart-types",
    status_code=status.HTTP_200_OK,
    summary="Get available chart types",
    description="Retrieve list of supported chart types and their configurations",
    responses=COMMON_RESPONSES
)
async def get_available_chart_types(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get available chart types"""
    
    chart_types = {
        "line": {
            "name": "Line Chart",
            "description": "Best for showing trends over time",
            "icon": "line_style",
            "use_cases": ["time series", "trends", "continuous data"],
            "preview_url": "/static/previews/chart-line.png"
        },
        "bar": {
            "name": "Bar Chart",
            "description": "Best for comparing categories",
            "icon": "bar_chart",
            "use_cases": ["categorical comparison", "rankings", "counts"],
            "preview_url": "/static/previews/chart-bar.png"
        },
        "pie": {
            "name": "Pie Chart",
            "description": "Best for showing proportions",
            "icon": "pie_chart",
            "use_cases": ["percentages", "parts of whole", "distribution"],
            "preview_url": "/static/previews/chart-pie.png"
        },
        "scatter": {
            "name": "Scatter Plot",
            "description": "Best for showing correlations",
            "icon": "scatter_plot",
            "use_cases": ["correlation", "clustering", "outliers"],
            "preview_url": "/static/previews/chart-scatter.png"
        },
        "heatmap": {
            "name": "Heat Map",
            "description": "Best for showing patterns in matrix data",
            "icon": "grid_view",
            "use_cases": ["correlation matrix", "time patterns", "geographic data"],
            "preview_url": "/static/previews/chart-heatmap.png"
        },
        "table": {
            "name": "Data Table",
            "description": "Best for detailed data inspection",
            "icon": "table_view",
            "use_cases": ["detailed data", "exact values", "sorting"],
            "preview_url": "/static/previews/chart-table.png"
        },
        "auto": {
            "name": "Auto Select",
            "description": "Automatically choose the best chart type",
            "icon": "auto_awesome",
            "use_cases": ["smart defaults", "quick visualization", "exploration"],
            "preview_url": "/static/previews/chart-auto.png"
        }
    }
    
    return {
        "chart_types": chart_types,
        "current_default": current_user.get_preference("ui.default_chart_type", "auto"),
        "recommendations": {
            "temporal_data": "line",
            "categorical_data": "bar",
            "proportional_data": "pie",
            "correlation_data": "scatter",
            "matrix_data": "heatmap",
            "tabular_data": "table"
        }
    }


@router.get(
    "/dashboard-layouts",
    status_code=status.HTTP_200_OK,
    summary="Get available dashboard layouts",
    description="Retrieve list of supported dashboard layouts and their configurations",
    responses=COMMON_RESPONSES
)
async def get_available_dashboard_layouts(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get available dashboard layouts"""
    
    layouts = {
        "grid": {
            "name": "Grid Layout",
            "description": "Fixed grid with resizable panels",
            "icon": "grid_view",
            "features": ["resizable", "draggable", "snap to grid"],
            "best_for": ["structured dashboards", "consistent sizing"],
            "preview_url": "/static/previews/layout-grid.png"
        },
        "masonry": {
            "name": "Masonry Layout",
            "description": "Pinterest-style flexible layout",
            "icon": "view_module",
            "features": ["auto-sizing", "flow layout", "compact"],
            "best_for": ["varied content sizes", "content-driven"],
            "preview_url": "/static/previews/layout-masonry.png"
        },
        "vertical": {
            "name": "Vertical Layout",
            "description": "Single column stacked layout",
            "icon": "view_agenda",
            "features": ["full width", "vertical scroll", "mobile-friendly"],
            "best_for": ["mobile devices", "reports", "simple layout"],
            "preview_url": "/static/previews/layout-vertical.png"
        },
        "horizontal": {
            "name": "Horizontal Layout",
            "description": "Side-by-side panel layout",
            "icon": "view_column",
            "features": ["side-by-side", "horizontal scroll", "wide screens"],
            "best_for": ["wide screens", "comparison", "multi-panel"],
            "preview_url": "/static/previews/layout-horizontal.png"
        }
    }
    
    return {
        "layouts": layouts,
        "current_default": current_user.get_preference("ui.default_dashboard_layout", "grid"),
        "responsive_breakpoints": {
            "mobile": "vertical",
            "tablet": "grid",
            "desktop": "grid",
            "wide": "horizontal"
        }
    }


@router.get(
    "/notification-methods",
    status_code=status.HTTP_200_OK,
    summary="Get available notification methods",
    description="Retrieve list of supported notification delivery methods",
    responses=COMMON_RESPONSES
)
async def get_available_notification_methods(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get available notification methods"""
    
    methods = {
        "email": {
            "name": "Email",
            "description": "Email notifications to your registered address",
            "icon": "email",
            "available": True,
            "requires_setup": False,
            "instant": False,
            "supports_rich_content": True
        },
        "slack": {
            "name": "Slack",
            "description": "Notifications via Slack workspace",
            "icon": "chat",
            "available": bool(current_user.get_preference("integrations.slack_webhook_url")),
            "requires_setup": True,
            "instant": True,
            "supports_rich_content": True
        },
        "teams": {
            "name": "Microsoft Teams",
            "description": "Notifications via Teams channel",
            "icon": "groups",
            "available": bool(current_user.get_preference("integrations.teams_webhook_url")),
            "requires_setup": True,
            "instant": True,
            "supports_rich_content": True
        },
        "webhook": {
            "name": "Custom Webhook",
            "description": "HTTP POST to custom endpoint",
            "icon": "webhook",
            "available": True,
            "requires_setup": True,
            "instant": True,
            "supports_rich_content": True
        },
        "sms": {
            "name": "SMS",
            "description": "Text message notifications",
            "icon": "sms",
            "available": bool(current_user.get_preference("phone_number")),
            "requires_setup": True,
            "instant": True,
            "supports_rich_content": False
        },
        "push": {
            "name": "Push Notifications",
            "description": "Browser or mobile app push notifications",
            "icon": "notifications",
            "available": True,
            "requires_setup": False,
            "instant": True,
            "supports_rich_content": True
        },
        "in_app": {
            "name": "In-App",
            "description": "Notifications within the application",
            "icon": "notifications_active",
            "available": True,
            "requires_setup": False,
            "instant": True,
            "supports_rich_content": True
        }
    }
    
    return {
        "methods": methods,
        "current_preferences": {
            "default_method": current_user.get_preference("notifications.default_method", "email"),
            "alert_method": current_user.get_preference("notifications.alert_method", "email"),
            "security_method": current_user.get_preference("notifications.security_method", "email")
        },
        "setup_guides": {
            "slack": "/docs/integrations/slack",
            "teams": "/docs/integrations/teams", 
            "webhook": "/docs/integrations/webhook",
            "sms": "/docs/integrations/sms"
        }
    }


@router.get(
    "/timezones",
    status_code=status.HTTP_200_OK,
    summary="Get available timezones",
    description="Retrieve list of supported timezones",
    responses=COMMON_RESPONSES
)
async def get_available_timezones(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get available timezones"""
    
    # Common timezones grouped by region
    timezones = {
        "UTC": {
            "UTC": {"name": "Coordinated Universal Time", "offset": "+00:00"}
        },
        "Americas": {
            "US/Eastern": {"name": "Eastern Time", "offset": "-05:00"},
            "US/Central": {"name": "Central Time", "offset": "-06:00"},
            "US/Mountain": {"name": "Mountain Time", "offset": "-07:00"},
            "US/Pacific": {"name": "Pacific Time", "offset": "-08:00"},
            "America/Toronto": {"name": "Toronto", "offset": "-05:00"},
            "America/Mexico_City": {"name": "Mexico City", "offset": "-06:00"},
            "America/Sao_Paulo": {"name": "São Paulo", "offset": "-03:00"}
        },
        "Europe": {
            "Europe/London": {"name": "London", "offset": "+00:00"},
            "Europe/Paris": {"name": "Paris", "offset": "+01:00"},
            "Europe/Berlin": {"name": "Berlin", "offset": "+01:00"},
            "Europe/Moscow": {"name": "Moscow", "offset": "+03:00"}
        },
        "Asia": {
            "Asia/Tokyo": {"name": "Tokyo", "offset": "+09:00"},
            "Asia/Shanghai": {"name": "Shanghai", "offset": "+08:00"},
            "Asia/Kolkata": {"name": "Kolkata", "offset": "+05:30"},
            "Asia/Dubai": {"name": "Dubai", "offset": "+04:00"}
        },
        "Pacific": {
            "Australia/Sydney": {"name": "Sydney", "offset": "+11:00"},
            "Pacific/Auckland": {"name": "Auckland", "offset": "+13:00"}
        }
    }
    
    return {
        "timezones": timezones,
        "current_timezone": current_user.timezone or "UTC",
        "auto_detect": True,  # Could detect from request headers
        "dst_info": "Daylight saving time is automatically handled"
    }


@router.get(
    "/languages",
    status_code=status.HTTP_200_OK,
    summary="Get available languages",
    description="Retrieve list of supported languages and locales",
    responses=COMMON_RESPONSES
)
async def get_available_languages(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get available languages"""
    
    languages = {
        "en": {
            "name": "English",
            "native_name": "English",
            "country": "United States",
            "rtl": False,
            "completion": 100
        },
        "es": {
            "name": "Spanish",
            "native_name": "Español",
            "country": "Spain",
            "rtl": False,
            "completion": 85
        },
        "fr": {
            "name": "French",
            "native_name": "Français",
            "country": "France",
            "rtl": False,
            "completion": 80
        },
        "de": {
            "name": "German",
            "native_name": "Deutsch",
            "country": "Germany",
            "rtl": False,
            "completion": 75
        },
        "ja": {
            "name": "Japanese",
            "native_name": "日本語",
            "country": "Japan",
            "rtl": False,
            "completion": 60
        },
        "zh": {
            "name": "Chinese (Simplified)",
            "native_name": "简体中文",
            "country": "China",
            "rtl": False,
            "completion": 70
        },
        "pt": {
            "name": "Portuguese",
            "native_name": "Português",
            "country": "Brazil",
            "rtl": False,
            "completion": 65
        },
        "it": {
            "name": "Italian",
            "native_name": "Italiano",
            "country": "Italy",
            "rtl": False,
            "completion": 55
        },
        "ru": {
            "name": "Russian",
            "native_name": "Русский",
            "country": "Russia",
            "rtl": False,
            "completion": 50
        }
    }
    
    return {
        "languages": languages,
        "current_language": current_user.language or "en",
        "auto_detect": True,  # Could detect from Accept-Language header
        "fallback_language": "en"
    }


@router.get(
    "/defaults",
    status_code=status.HTTP_200_OK,
    summary="Get default settings",
    description="Retrieve default values for all setting categories",
    responses=COMMON_RESPONSES
)
async def get_default_settings(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get default settings for all categories"""
    
    defaults = {
        "notifications": NotificationPreferences().dict(),
        "ui": UIPreferences().dict(),
        "query": QueryPreferences().dict(),
        "security": SecurityPreferences().dict(),
        "integrations": IntegrationPreferences().dict()
    }
    
    # Add role-specific defaults if applicable
    if current_user.has_role("admin"):
        defaults["security"]["log_queries"] = True
        defaults["security"]["log_exports"] = True
        defaults["security"]["log_dashboard_views"] = True
    
    if current_user.has_role("analyst"):
        defaults["query"]["max_results"] = 5000
        defaults["query"]["query_timeout"] = 600
        defaults["ui"]["default_chart_type"] = "auto"
    
    return {
        "defaults": defaults,
        "role_based": True,
        "user_roles": current_user.roles or [],
        "customizable": True
    }


@router.post(
    "/validate",
    status_code=status.HTTP_200_OK,
    summary="Validate settings",
    description="Validate settings configuration before applying",
    responses=COMMON_RESPONSES
)
async def validate_settings(
    settings_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Validate settings configuration"""
    
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "suggestions": []
    }
    
    # Validate each category
    for category, config in settings_data.items():
        if category == "notifications":
            try:
                NotificationPreferences(**config)
            except Exception as e:
                validation_results["valid"] = False
                validation_results["errors"].append({
                    "category": "notifications",
                    "message": str(e)
                })
        
        elif category == "ui":
            try:
                UIPreferences(**config)
            except Exception as e:
                validation_results["valid"] = False
                validation_results["errors"].append({
                    "category": "ui",
                    "message": str(e)
                })
        
        elif category == "query":
            try:
                QueryPreferences(**config)
                # Additional business logic validation
                if config.get("max_results", 0) > 10000:
                    validation_results["warnings"].append({
                        "category": "query",
                        "message": "Max results over 10,000 may impact performance"
                    })
            except Exception as e:
                validation_results["valid"] = False
                validation_results["errors"].append({
                    "category": "query",
                    "message": str(e)
                })
        
        elif category == "security":
            try:
                SecurityPreferences(**config)
                # Security-specific validation
                if config.get("session_timeout", 0) > 86400:
                    validation_results["warnings"].append({
                        "category": "security",
                        "message": "Session timeout over 24 hours may pose security risk"
                    })
            except Exception as e:
                validation_results["valid"] = False
                validation_results["errors"].append({
                    "category": "security",
                    "message": str(e)
                })
        
        elif category == "integrations":
            try:
                IntegrationPreferences(**config)
            except Exception as e:
                validation_results["valid"] = False
                validation_results["errors"].append({
                    "category": "integrations",
                    "message": str(e)
                })
    
    # Add suggestions based on user role or current settings
    if current_user.has_role("admin"):
        validation_results["suggestions"].append({
            "category": "security",
            "message": "Consider enabling audit logging for administrative accounts"
        })
    
    return validation_results


@router.get(
    "/templates",
    status_code=status.HTTP_200_OK,
    summary="Get setting templates",
    description="Retrieve predefined setting templates for different user types",
    responses=COMMON_RESPONSES,
    dependencies=[Depends(require_permissions(["settings:read"]))]
)
async def get_setting_templates(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get predefined setting templates"""
    
    templates = {
        "executive": {
            "name": "Executive Dashboard",
            "description": "High-level overview with minimal technical details",
            "settings": {
                "ui": {
                    "theme": "light",
                    "density": "spacious",
                    "default_chart_type": "bar",
                    "show_tooltips": True,
                    "animations_enabled": True
                },
                "notifications": {
                    "email_notifications": True,
                    "weekly_summary": True,
                    "system_updates": False
                },
                "query": {
                    "default_time_range": "7d",
                    "max_results": 100
                }
            }
        },
        "analyst": {
            "name": "Data Analyst",
            "description": "Advanced features for data exploration and analysis",
            "settings": {
                "ui": {
                    "theme": "dark",
                    "density": "compact",
                    "default_chart_type": "auto",
                    "show_tooltips": True,
                    "animations_enabled": False
                },
                "query": {
                    "default_time_range": "24h",
                    "max_results": 5000,
                    "streaming_enabled": True,
                    "cache_results": True
                },
                "notifications": {
                    "query_completion": True,
                    "alert_triggers": True
                }
            }
        },
        "security": {
            "name": "Security Operations",
            "description": "Security-focused configuration with enhanced logging",
            "settings": {
                "security": {
                    "activity_tracking": True,
                    "log_queries": True,
                    "log_exports": True,
                    "session_timeout": 1800
                },
                "notifications": {
                    "security_events": True,
                    "alert_triggers": True,
                    "alert_method": "email"
                },
                "ui": {
                    "theme": "dark",
                    "high_contrast": True
                }
            }
        },
        "developer": {
            "name": "Developer",
            "description": "Technical configuration with debugging features",
            "settings": {
                "ui": {
                    "theme": "dark",
                    "density": "compact",
                    "show_tooltips": False,
                    "animations_enabled": False
                },
                "query": {
                    "auto_complete_enabled": True,
                    "syntax_highlighting": True,
                    "query_validation": True,
                    "include_metadata": True
                },
                "security": {
                    "error_reporting": True,
                    "log_queries": True
                }
            }
        }
    }
    
    return {
        "templates": templates,
        "can_create_custom": current_user.has_permission("settings:create_template"),
        "default_template": "analyst"
    }


@router.get(
    "/export-options",
    status_code=status.HTTP_200_OK,
    summary="Get export options",
    description="Retrieve available data export formats and settings",
    responses=COMMON_RESPONSES
)
async def get_export_options(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get available export options"""
    
    formats = {
        "csv": {
            "name": "CSV",
            "description": "Comma-separated values for spreadsheet applications",
            "mime_type": "text/csv",
            "extension": ".csv",
            "supports_formatting": False,
            "max_size_mb": 100,
            "use_cases": ["data analysis", "Excel import", "simple data transfer"]
        },
        "json": {
            "name": "JSON",
            "description": "JavaScript Object Notation for APIs and programming",
            "mime_type": "application/json",
            "extension": ".json",
            "supports_formatting": True,
            "max_size_mb": 50,
            "use_cases": ["API integration", "programming", "data exchange"]
        },
        "excel": {
            "name": "Excel",
            "description": "Microsoft Excel format with charts and formatting",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "extension": ".xlsx",
            "supports_formatting": True,
            "max_size_mb": 200,
            "use_cases": ["business reports", "formatted data", "presentations"]
        },
        "pdf": {
            "name": "PDF",
            "description": "Portable Document Format for sharing and printing",
            "mime_type": "application/pdf",
            "extension": ".pdf",
            "supports_formatting": True,
            "max_size_mb": 50,
            "use_cases": ["reports", "documentation", "sharing"]
        }
    }
    
    return {
        "formats": formats,
        "current_default": current_user.get_preference("query.export_format", "csv"),
        "compression_options": ["none", "zip", "gzip"],
        "scheduling_available": True,
        "batch_export_limit": 10
    }