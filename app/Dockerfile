# Use an official lightweight Python image
FROM python:3.15-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Directory for the Prometheus multiprocess metric files, emptied by gunicorn.conf.py on start
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc

# Expose the app port and the metrics port
EXPOSE 5000 9200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Use Gunicorn for production
CMD ["gunicorn", "--config", "gunicorn.conf.py", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "60", "main:app"] 