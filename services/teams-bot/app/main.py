"""
FastAPI application for Microsoft Teams Bot service.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .core.config import settings
from .core.logging import setup_logging, get_logger
from .bot.teams_handler import TeamsHandler
from .bot.auth import verify_teams_request
from .api.health import router as health_router

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Global Teams handler instance
teams_handler: TeamsHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    global teams_handler
    
    # Startup
    logger.info("Starting Microsoft Teams Bot service", version=app.version)
    
    try:
        # Initialize Teams handler
        teams_handler = TeamsHandler()
        await teams_handler.initialize()
        
        # Set handler in health router
        from .api import health
        health.teams_handler = teams_handler
        
        logger.info("Teams Bot service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Teams Bot service: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Teams Bot service")
    
    try:
        if teams_handler:
            await teams_handler.cleanup()
        logger.info("Teams Bot service shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Microsoft Teams Bot service for Splunk MCP Integration",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http") 
async def logging_middleware(request: Request, call_next):
    """Log all requests."""
    import uuid
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Incoming request",
        method=request.method,
        url=str(request.url),
        correlation_id=correlation_id
    )
    
    # Add correlation ID to request state
    request.state.correlation_id = correlation_id
    
    try:
        response = await call_next(request)
        
        logger.info(
            "Request completed",
            status_code=response.status_code,
            correlation_id=correlation_id
        )
        
        response.headers["X-Correlation-ID"] = correlation_id
        return response
        
    except Exception as e:
        logger.error(
            "Request failed",
            error=str(e),
            correlation_id=correlation_id
        )
        raise


# Include routers
app.include_router(health_router, prefix="", tags=["health"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "teams-bot",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/teams/messages")
async def handle_teams_messages(
    request: Request,
    verified_request: dict = Depends(verify_teams_request)
):
    """Handle Microsoft Teams messages and activities."""
    try:
        activity = verified_request
        
        logger.info(
            "Received Teams activity",
            activity_type=activity.get("type"),
            channel_id=activity.get("channelId"),
            correlation_id=request.state.correlation_id
        )
        
        # Handle different activity types
        activity_type = activity.get("type")
        
        if activity_type == "message":
            await teams_handler.handle_message(activity)
        elif activity_type == "invoke":
            return await teams_handler.handle_invoke(activity)
        elif activity_type == "memberAdded":
            await teams_handler.handle_member_added(activity)
        elif activity_type == "installationUpdate":
            await teams_handler.handle_installation_update(activity)
        else:
            logger.warning(f"Unhandled activity type: {activity_type}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error handling Teams activity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/teams/invoke")
async def handle_teams_invoke(
    request: Request,
    verified_request: dict = Depends(verify_teams_request)
):
    """Handle Teams invoke activities (adaptive cards, task modules)."""
    try:
        activity = verified_request
        
        logger.info(
            "Received Teams invoke",
            name=activity.get("name"),
            channel_id=activity.get("channelId"),
            correlation_id=request.state.correlation_id
        )
        
        response = await teams_handler.handle_invoke(activity)
        return response
        
    except Exception as e:
        logger.error(f"Error handling Teams invoke: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/teams/commands")
async def handle_teams_commands(
    request: Request,
    verified_request: dict = Depends(verify_teams_request)
):
    """Handle Teams command activities."""
    try:
        activity = verified_request
        
        logger.info(
            "Received Teams command",
            command=activity.get("value", {}).get("commandId"),
            channel_id=activity.get("channelId"),
            correlation_id=request.state.correlation_id
        )
        
        response = await teams_handler.handle_command(activity)
        return response
        
    except Exception as e:
        logger.error(f"Error handling Teams command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        correlation_id=correlation_id
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "correlation_id": correlation_id
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )