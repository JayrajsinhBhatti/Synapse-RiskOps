FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic psutil prometheus_client

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "run_demo.py"]
