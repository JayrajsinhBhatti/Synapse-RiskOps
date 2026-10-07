FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY telemetry-bridge/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY telemetry-bridge/ /app/telemetry-bridge/

ENV PYTHONPATH=/app
EXPOSE 9010

CMD ["uvicorn", "telemetry-bridge.main:app", "--host", "0.0.0.0", "--port", "9010"]
