FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY shared/requirements.txt /app/shared/requirements.txt
RUN pip install --no-cache-dir -r /app/shared/requirements.txt

COPY shared/ /app/shared/
COPY payments/ /app/payments/

ENV PYTHONPATH=/app
EXPOSE 9004

CMD ["uvicorn", "payments.main:app", "--host", "0.0.0.0", "--port", "9004"]
