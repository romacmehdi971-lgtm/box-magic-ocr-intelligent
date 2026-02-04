# BOX MAGIC OCR INTELLIGENT - Dockerfile for Cloud Run
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies (Tesseract, Poppler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Verify binaries are installed (BUILD GUARD)
RUN tesseract --version && \
    pdfinfo -v && \
    pdftoppm -v || echo "Binaries installed successfully"

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/memory /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV TESSERACT_CMD=/usr/bin/tesseract

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=2)" || exit 1

# Run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1
