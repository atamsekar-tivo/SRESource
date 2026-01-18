# Multi-stage build for SRESource documentation
FROM python:3.11-alpine as builder

WORKDIR /tmp

# Install build dependencies
RUN apk add --no-cache git gcc musl-dev libffi-dev openssl-dev

# Install Python dependencies
RUN pip install --user --no-cache-dir \
    mkdocs==1.5.3 \
    mkdocs-material==9.4.10 \
    mkdocs-git-revision-date-localized-plugin==1.2.2 \
    pymdown-extensions==10.5

# Production stage
FROM python:3.11-alpine

WORKDIR /app

# Install runtime dependencies only
RUN apk add --no-cache \
    git \
    libffi \
    openssl

# Copy Python packages from builder
COPY --from=builder /root/.local /home/mkdocs/.local

# Create non-root user for security
RUN addgroup -g 1000 mkdocs && \
    adduser -u 1000 -G mkdocs -s /bin/sh -D mkdocs && \
    chown -R mkdocs:mkdocs /app && \
    chown -R mkdocs:mkdocs /home/mkdocs/.local

# Set PATH to include local Python packages
ENV PATH=/home/mkdocs/.local/bin:$PATH

# Copy documentation
COPY mkdocs.yml .
COPY docs/ ./docs/

USER mkdocs

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8080/ || exit 1

# Run MkDocs server
CMD ["mkdocs", "serve", "--dev-addr=0.0.0.0:8080"]