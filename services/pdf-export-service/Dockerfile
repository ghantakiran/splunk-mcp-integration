# Multi-stage build for PDF Export Service
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for PDF generation
RUN apt-get update && apt-get install -y \
    # WeasyPrint dependencies
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    # PDF processing dependencies
    poppler-utils \
    # Build tools
    gcc \
    g++ \
    make \
    # Fonts
    fonts-liberation \
    fonts-dejavu-core \
    # Image processing
    libjpeg-dev \
    libpng-dev \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r pdfuser && useradd -r -g pdfuser pdfuser

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY main.py .

# Create necessary directories
RUN mkdir -p /app/logs /app/temp /app/output /app/templates && \
    chown -R pdfuser:pdfuser /app

# Switch to non-root user
USER pdfuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

# Expose ports
EXPOSE 8009 9009

# Run the application
CMD ["python", "main.py"]


# Development stage
FROM base as development

# Install development dependencies
USER root
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black isort flake8 mypy

# Create test directory
RUN mkdir -p /app/tests && chown -R pdfuser:pdfuser /app/tests

USER pdfuser

# Run with hot reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8009", "--reload"]


# Production stage
FROM base as production

# Copy only necessary files
COPY --from=base /app /app

# Switch to non-root user
USER pdfuser

# Run the application
CMD ["python", "main.py"]