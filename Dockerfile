# Multi-stage build for SRESource Flask application
FROM python:3.11-alpine AS builder

WORKDIR /tmp

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-alpine

WORKDIR /app

# Install runtime dependencies only
RUN apk add --no-cache \
    libffi \
    openssl

# Copy Python packages from builder
COPY --from=builder /root/.local /home/flask/.local

# Create non-root user for security
RUN addgroup -g 1000 flask && \
    adduser -u 1000 -G flask -s /bin/sh -D flask && \
    chown -R flask:flask /app && \
    chown -R flask:flask /home/flask/.local

# Set PATH to include local Python packages
ENV PATH=/home/flask/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

# Copy application files
COPY app.py .
COPY gunicorn_config.py .
COPY requirements.txt .
COPY templates/ ./templates/
COPY static/ ./static/
COPY docs/ ./docs/

# Create static directory if it doesn't exist and ensure proper permissions
RUN mkdir -p /app/static && \
    chmod -R 755 /app/docs && \
    chmod -R 755 /app/templates && \
    chmod -R 755 /app/static

USER flask

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/', timeout=3)" || exit 1

# Run with gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]