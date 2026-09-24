# =====================================================
# Synapse RiskOps - Core Backend Dockerfile
# =====================================================
# Owner: Person 2 | Week: 5
# Fast, lightweight Python 3.11 image replacing Spring Boot
# =====================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (curl for healthcheck, libpq for postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ /app/app/

# Expose backend port (8080)
EXPOSE 8080

# Run FastAPI via uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
