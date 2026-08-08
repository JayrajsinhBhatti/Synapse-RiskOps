"""
Synapse RiskOps - Data Ingestion API
======================================
Owner: Person 2 | Week: 2

Endpoints for uploading and ingesting server metrics/logs data.
Supports CSV file upload and JSON payload ingestion.
After ingestion, automatically triggers model training.
"""

import pandas as pd
from io import StringIO
from fastapi import APIRouter, UploadFile, File, HTTPException
from loguru import logger

from app.schemas.prediction import IngestResponse

router = APIRouter(prefix="/api/ingest", tags=["Data Ingestion"])


@router.post("/metrics", response_model=IngestResponse)
async def ingest_metrics(file: UploadFile = File(...)):
    """
    Upload a CSV file of server metrics for model training.

    The CSV must contain columns matching the sample_metrics.csv schema:
    timestamp, service_name, cpu_usage, memory_usage, disk_io,
    network_latency_ms, request_count, error_rate, response_time_p99,
    active_connections, gc_pause_ms, thread_count

    Optionally includes 'is_anomaly' ground truth column.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    try:
        contents = await file.read()
        text = contents.decode("utf-8")
        df = pd.read_csv(StringIO(text))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    # Validate required columns
    required = {"timestamp", "service_name", "cpu_usage", "memory_usage"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required columns: {missing}"
        )

    services = df["service_name"].unique().tolist()
    anomaly_count = int(df["is_anomaly"].sum()) if "is_anomaly" in df.columns else 0

    logger.info(
        f"Ingested {len(df)} metric rows from '{file.filename}' "
        f"across {len(services)} services"
    )

    # Train models with new data
    from app.main import get_risk_engine
    engine = get_risk_engine()
    if engine:
        try:
            engine.train(df)
            logger.info("Models retrained with ingested data")
        except Exception as e:
            logger.error(f"Model training failed after ingestion: {e}")

    return IngestResponse(
        status="success",
        rows_ingested=len(df),
        services_found=services,
        anomaly_count=anomaly_count,
        message=f"Successfully ingested {len(df)} rows from {file.filename}",
    )


@router.post("/logs", response_model=IngestResponse)
async def ingest_logs(file: UploadFile = File(...)):
    """
    Upload a CSV file of server logs for analysis.

    The CSV should contain: timestamp, service_name, log_level, message
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    try:
        contents = await file.read()
        text = contents.decode("utf-8")
        df = pd.read_csv(StringIO(text))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    required = {"timestamp", "service_name"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required columns: {missing}"
        )

    services = df["service_name"].unique().tolist()

    logger.info(
        f"Ingested {len(df)} log rows from '{file.filename}' "
        f"across {len(services)} services"
    )

    return IngestResponse(
        status="success",
        rows_ingested=len(df),
        services_found=services,
        anomaly_count=0,
        message=f"Successfully ingested {len(df)} log entries from {file.filename}",
    )
