"""
Splunk MCP Integration - API Gateway
Main FastAPI application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from datetime import datetime

# Create FastAPI application
app = FastAPI(
    title="Splunk MCP Integration API",
    description="API Gateway for Splunk Model Context Protocol Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Splunk MCP Integration API Gateway",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/status")
async def status():
    """Detailed status endpoint"""
    return {
        "service": "api-gateway",
        "status": "running",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "calculating...",
        "dependencies": {
            "database": "checking...",
            "redis": "checking...",
            "nlp_engine": "checking...",
            "spl_translator": "checking..."
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )