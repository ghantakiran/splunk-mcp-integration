# Multi-stage build for PowerPoint Export Service

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN groupadd -r pptservice && \
    useradd -r -g pptservice -d /app -s /bin/bash pptservice

# Create application directory and set permissions
RUN mkdir -p /app /tmp/ppt-exports /app/templates && \
    chown -R pptservice:pptservice /app /tmp/ppt-exports

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=pptservice:pptservice . .

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data && \
    chown -R pptservice:pptservice /app/logs /app/data

# Switch to non-root user
USER pptservice

# Expose ports
EXPOSE 8011 9011

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8011/health || exit 1

# Default command
CMD ["python", "main.py"]
