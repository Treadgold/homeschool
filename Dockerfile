# Use an official Python runtime as a parent image
FROM python:3.12-slim-bullseye

# Set the working directory in the container to /app
WORKDIR /app

# Install system dependencies including libmagic
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt into the container at /app
COPY requirements.txt .

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt alembic pytest pytest-asyncio

# Copy the rest of the application code into the container at /app
COPY . .

# Create test results directory
RUN mkdir -p /app/test_results

# Define environment variable
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Conditionally run tests during build based on environment variable
# Tests are only run if RUN_TESTS_ON_BUILD is set to "true"
RUN if [ "${RUN_TESTS_ON_BUILD:-false}" = "true" ]; then \
        echo "🧪 Running tests during Docker build..."; \
        python docker_test_runner.py || echo "⚠️  Tests completed with issues - check test_results/ for details"; \
    else \
        echo "⏭️  Skipping tests during build (RUN_TESTS_ON_BUILD=${RUN_TESTS_ON_BUILD})"; \
    fi

# Make port 8000 available to the world outside this container
EXPOSE 8000

# For development, use --reload for live updates
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# In production, remove --reload and use a production server like gunicorn or uvicorn without reload