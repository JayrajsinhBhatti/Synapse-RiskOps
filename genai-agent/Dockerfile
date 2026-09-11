# genai-agent/Dockerfile
# Owner: Person 1
#
# Base Python image -> install requirements.txt -> copy app/ -> run uvicorn
# app.main:app on the GENAI_AGENT_PORT defined in .env
# To be filled in once the service has a runnable main.py (Week 1-3)

# =====================================================
# Synapse RiskOps - GenAI Agent
# FastAPI + LangGraph + Gemini
# =====================================================

FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# GenAI Agent listens on port 8001
EXPOSE 8001

# Start FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]