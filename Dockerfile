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

# Command to run the application using hypercorn
CMD exec hypercorn app:app --bind 0.0.0.0:$PORT --workers 1 --access-log - --error-log - --log-level INFO