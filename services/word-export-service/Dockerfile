# Multi-stage Dockerfile for Word Export Service
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r wordservice && useradd -r -g wordservice wordservice

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/word-exports /app/logs && \
    chown -R wordservice:wordservice /app /tmp/word-exports

# Switch to non-root user
USER wordservice

# Expose port
EXPOSE 8013

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8013/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8013"]


# Development stage
FROM base as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    black==23.11.0 \
    isort==5.12.0 \
    flake8==6.1.0 \
    mypy==1.7.1 \
    debugpy==1.8.0

# Switch back to wordservice user
USER wordservice

# Override command for development
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8013", "--reload"]


# Production stage
FROM base as production

# Set production environment
ENV ENVIRONMENT=production

# Copy only necessary files for production
COPY --chown=wordservice:wordservice main.py .
COPY --chown=wordservice:wordservice app/ app/

# Final command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8013", "--workers", "4"]