# Use official Python runtime as base image
FROM python:3.9-slim

# Set working directory in container
WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Configure container to run in a non-root user
RUN useradd -m myuser
USER myuser

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV QUART_APP=app:app
ENV QUART_ENV=production
ENV HYPERCORN_WORKERS=1
ENV HYPERCORN_ACCESS_LOG='-'
ENV HYPERCORN_ERROR_LOG='-'
ENV HYPERCORN_BIND="0.0.0.0:${PORT}"

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/_ah/health || exit 1

# Command to run the application
CMD hypercorn app:app \
    --bind ${HYPERCORN_BIND} \
    --workers ${HYPERCORN_WORKERS} \
    --access-logfile ${HYPERCORN_ACCESS_LOG} \
    --error-logfile ${HYPERCORN_ERROR_LOG} \
    --graceful-timeout 180 \
    --worker-class asyncio \
    --keep-alive 120 \
    --log-level info