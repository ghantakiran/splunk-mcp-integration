"""
API documentation configuration and metadata
"""

from typing import Dict, Any, List
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI
from .config import settings


def get_api_metadata() -> Dict[str, Any]:
    """Get API metadata for OpenAPI documentation"""
    return {
        "title": "Splunk MCP Integration API",
        "description": """
# Splunk MCP Integration API

A comprehensive API for the Splunk Model Context Protocol (MCP) Integration project.

## Features

- **Natural Language Processing**: Convert natural language queries to SPL
- **Authentication & Authorization**: JWT-based authentication with RBAC
- **Chat Interface**: Real-time conversational interface for Splunk queries
- **Dashboard Management**: Create and manage interactive dashboards
- **Alert Management**: Set up and manage intelligent alerts
- **Query Management**: Execute, optimize, and cache SPL queries
- **User Management**: Complete user lifecycle management

## Authentication

This API uses JWT (JSON Web Tokens) for authentication. To authenticate:

1. **Login**: POST to `/api/v1/auth/login` with email and password
2. **Get Token**: Receive `access_token` and `refresh_token` in response
3. **Use Token**: Include `Authorization: Bearer <access_token>` in subsequent requests
4. **Refresh**: Use refresh token at `/api/v1/auth/refresh` to get new access token

## Rate Limiting

API requests are rate limited to prevent abuse:
- **Authenticated users**: 1000 requests per hour
- **Unauthenticated users**: 100 requests per hour

## Error Handling

All API errors follow a consistent format:

```json
{
  "error": {
    "message": "Human readable error message",
    "code": "machine_readable_error_code",
    "details": {
      "field": "Additional error details"
    }
  }
}
```

## Versioning

This API uses URL path versioning (e.g., `/api/v1/`). Current version is `v1`.

## Support

For API support, please contact the development team or create an issue in the repository.
        """,
        "version": settings.app_version,
        "contact": {
            "name": "Splunk MCP Integration Team",
            "email": "support@splunk-mcp.local",
            "url": "https://github.com/ghantakiran/splunk-mcp-integration"
        },
        "license": {
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        "servers": [
            {
                "url": "http://localhost:8000/api/v1",
                "description": "Development server"
            },
            {
                "url": "https://api.splunk-mcp.local/api/v1", 
                "description": "Production server"
            }
        ],
        "externalDocs": {
            "description": "Full Documentation",
            "url": "https://github.com/ghantakiran/splunk-mcp-integration/blob/main/README.md"
        }
    }


def get_api_tags() -> List[Dict[str, Any]]:
    """Get API tags for organizing endpoints"""
    return [
        {
            "name": "Health",
            "description": "System health and status endpoints"
        },
        {
            "name": "Authentication", 
            "description": "User authentication and session management"
        },
        {
            "name": "Users",
            "description": "User management and profile operations"
        },
        {
            "name": "Chat",
            "description": "Conversational interface for natural language queries"
        },
        {
            "name": "Queries",
            "description": "SPL query management, execution, and optimization"
        },
        {
            "name": "Dashboards",
            "description": "Dashboard creation, management, and sharing"
        },
        {
            "name": "Alerts",
            "description": "Alert rule management and incident handling"
        },
        {
            "name": "System",
            "description": "System administration and configuration"
        }
    ]


def get_security_schemes() -> Dict[str, Any]:
    """Get security schemes for OpenAPI documentation"""
    return {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token obtained from /auth/login"
        },
        "refreshAuth": {
            "type": "http", 
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT refresh token for obtaining new access tokens"
        }
    }


def get_response_examples() -> Dict[str, Any]:
    """Get common response examples"""
    return {
        "ValidationError": {
            "description": "Request validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "message": "Request validation failed",
                            "code": "validation_error",
                            "details": {
                                "errors": [
                                    {
                                        "loc": ["body", "email"],
                                        "msg": "field required",
                                        "type": "value_error.missing"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        "AuthenticationError": {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "message": "Invalid or expired token",
                            "code": "authentication_error"
                        }
                    }
                }
            }
        },
        "AuthorizationError": {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "message": "Insufficient permissions for this operation",
                            "code": "authorization_error"
                        }
                    }
                }
            }
        },
        "NotFoundError": {
            "description": "Resource not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "message": "Resource not found",
                            "code": "not_found_error"
                        }
                    }
                }
            }
        },
        "RateLimitError": {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "message": "Rate limit exceeded",
                            "code": "rate_limit_error"
                        }
                    }
                }
            }
        },
        "InternalServerError": {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "message": "Internal server error",
                            "code": "internal_error"
                        }
                    }
                }
            }
        }
    }


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Generate custom OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema
    
    metadata = get_api_metadata()
    
    openapi_schema = get_openapi(
        title=metadata["title"],
        version=metadata["version"],
        description=metadata["description"],
        routes=app.routes,
        servers=metadata["servers"]
    )
    
    # Add metadata
    openapi_schema["info"]["contact"] = metadata["contact"]
    openapi_schema["info"]["license"] = metadata["license"]
    openapi_schema["externalDocs"] = metadata["externalDocs"]
    
    # Add tags
    openapi_schema["tags"] = get_api_tags()
    
    # Add security schemes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    openapi_schema["components"]["securitySchemes"] = get_security_schemes()
    
    # Add global security requirement
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    # Add common response schemas
    response_examples = get_response_examples()
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "responses" not in openapi_schema["components"]:
        openapi_schema["components"]["responses"] = {}
    openapi_schema["components"]["responses"].update(response_examples)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def get_custom_swagger_ui_html(
    *,
    openapi_url: str,
    title: str,
    swagger_js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
    swagger_css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
    swagger_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
    oauth2_redirect_url: str = None,
    init_oauth: dict = None,
) -> str:
    """Get custom Swagger UI HTML with enhanced styling"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <link rel="stylesheet" type="text/css" href="{swagger_css_url}" />
        <link rel="icon" type="image/png" href="{swagger_favicon_url}" />
        <style>
            .swagger-ui .topbar {{
                background-color: #1f2937;
                border-bottom: 3px solid #10b981;
            }}
            .swagger-ui .topbar .download-url-wrapper .download-url-button {{
                background: #10b981;
                color: white;
                border-color: #10b981;
            }}
            .swagger-ui .info .title {{
                color: #1f2937;
            }}
            .swagger-ui .scheme-container {{
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 10px;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="{swagger_js_url}"></script>
        <script>
            const ui = SwaggerUIBundle({{
                url: '{openapi_url}',
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.presets.standalone
                ],
                layout: "BaseLayout",
                deepLinking: true,
                showExtensions: true,
                showCommonExtensions: true,
                defaultModelRendering: 'model',
                docExpansion: 'list',
                tagsSorter: 'alpha',
                operationsSorter: 'alpha',
                filter: true,
                syntaxHighlight: {{
                    activate: true,
                    theme: 'agate'
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html


def get_custom_redoc_html(
    *,
    openapi_url: str,
    title: str,
    redoc_js_url: str = "https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
    redoc_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
) -> str:
    """Get custom ReDoc HTML with enhanced styling"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="icon" type="image/png" href="{redoc_favicon_url}" />
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
        </style>
    </head>
    <body>
        <redoc spec-url="{openapi_url}" theme="{{
            colors: {{
                primary: {{
                    main: '#10b981'
                }}
            }},
            typography: {{
                fontSize: '14px',
                fontFamily: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'
            }}
        }}"></redoc>
        <script src="{redoc_js_url}"></script>
    </body>
    </html>
    """
    return html


class APIVersionConfig:
    """Configuration for API versioning"""
    
    V1_PREFIX = "/api/v1"
    CURRENT_VERSION = "1.0.0"
    SUPPORTED_VERSIONS = ["1.0.0"]
    
    @classmethod
    def get_version_info(cls) -> Dict[str, Any]:
        """Get API version information"""
        return {
            "current_version": cls.CURRENT_VERSION,
            "supported_versions": cls.SUPPORTED_VERSIONS,
            "prefix": cls.V1_PREFIX,
            "deprecation_policy": "Versions are supported for 12 months after replacement",
            "migration_guide": "https://github.com/ghantakiran/splunk-mcp-integration/blob/main/docs/api/migration.md"
        }
    
    @classmethod
    def is_version_supported(cls, version: str) -> bool:
        """Check if a version is supported"""
        return version in cls.SUPPORTED_VERSIONS