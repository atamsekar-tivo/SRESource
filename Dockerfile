# Multi-stage build for SRESource Flask application
FROM python:3.11-alpine as builder

WORKDIR /tmp

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

# Install Python dependencies
RUN pip install --user --no-cache-dir \
    Flask==3.0.0 \
    Markdown==3.5.1 \
    Werkzeug==3.0.0 \
    gunicorn==21.2.0

# Production stage
FROM python:3.11-alpine

WORKDIR /app

# Install runtime dependencies only
RUN apk add --no-cache \
    curl \
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
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py

# Copy application files
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/
COPY docs/ ./docs/

# Create static directory if it doesn't exist
RUN mkdir -p /app/static

USER flask

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8080/ || exit 1

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--threads", "2", "--worker-class", "gthread", "--timeout", "30", "app:app"]