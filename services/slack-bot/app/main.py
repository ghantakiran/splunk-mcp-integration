"""
Slack Bot Service Main Application

FastAPI application that handles Slack bot interactions for the Splunk MCP integration.
"""

import os
import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from .core.config import settings
from .core.logging import setup_logging, get_logger
from .bot.slack_handler import SlackHandler
from .bot.auth import verify_slack_request
from .api.v1.endpoints import router as api_router

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize Slack handler
slack_handler = SlackHandler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    logger.info("Starting Slack Bot service")
    await slack_handler.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Slack Bot service")
    await slack_handler.cleanup()

# Create FastAPI application
app = FastAPI(
    title="Splunk MCP Slack Bot Service",
    description="Slack bot integration for natural language Splunk queries",
    version=settings.app_version,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Splunk MCP Slack Bot",
        "version": settings.app_version,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        is_healthy = await slack_handler.health_check()
        status_code = 200 if is_healthy else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if is_healthy else "unhealthy",
                "service": "slack-bot",
                "version": settings.app_version,
                "slack_connected": is_healthy
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "slack-bot",
                "error": str(e)
            }
        )

@app.post("/slack/events")
async def slack_events(
    request: Request,
    verified_request: dict = Depends(verify_slack_request)
):
    """Handle Slack events."""
    try:
        event_data = verified_request
        logger.info(f"Received Slack event: {event_data.get('type')}")
        
        # Handle URL verification challenge
        if event_data.get("type") == "url_verification":
            return {"challenge": event_data.get("challenge")}
        
        # Handle app mention events
        if event_data.get("type") == "event_callback":
            event = event_data.get("event", {})
            
            if event.get("type") == "app_mention":
                await slack_handler.handle_mention(event)
            elif event.get("type") == "message" and event.get("channel_type") == "im":
                await slack_handler.handle_direct_message(event)
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Error handling Slack event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/slack/interactive")
async def slack_interactive(
    request: Request,
    verified_request: dict = Depends(verify_slack_request)
):
    """Handle Slack interactive components (buttons, modals, etc.)."""
    try:
        payload = verified_request
        logger.info(f"Received Slack interactive: {payload.get('type')}")
        
        response = await slack_handler.handle_interactive(payload)
        return response
        
    except Exception as e:
        logger.error(f"Error handling Slack interactive: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/slack/commands")
async def slack_commands(
    request: Request,
    verified_request: dict = Depends(verify_slack_request)
):
    """Handle Slack slash commands."""
    try:
        command_data = verified_request
        logger.info(f"Received Slack command: {command_data.get('command')}")
        
        response = await slack_handler.handle_slash_command(command_data)
        return response
        
    except Exception as e:
        logger.error(f"Error handling Slack command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )