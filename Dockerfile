# Use official Python runtime as base image
FROM python:3.9-slim

# Set working directory in container
WORKDIR /app

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

# Command to run the application using hypercorn with increased timeout
CMD exec hypercorn app:app \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --graceful-timeout 180 \
    --worker-class asyncio \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --timeout 300