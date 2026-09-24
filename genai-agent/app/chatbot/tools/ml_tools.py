"""
genai-agent/app/chatbot/tools/ml_tools.py

Tools interfacing with ml-engine (Port 8000) and service metrics.
Powers:
- Feature #1: Service Health Query (get_service_risk_score)
- Feature #11: Metric Snapshot & Comparison
"""

import os
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests
from loguru import logger

ML_ENGINE_URL = os.getenv("ML_ENGINE_URL", "http://localhost:8000")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

# Canonical service list
KNOWN_SERVICES = [
    "api-gateway",
    "auth-service",
    "user-service",
    "order-service",
    "payment-service",
    "inventory-service",
    "notification-svc",
    "search-service",
    "cache-layer",
    "message-queue",
    "postgres-primary",
    "postgres-replica",
]

# Service name aliases for natural language queries
SERVICE_ALIASES = {
    "api": "api-gateway",
    "gateway": "api-gateway",
    "auth": "auth-service",
    "user": "user-service",
    "users": "user-service",
    "order": "order-service",
    "orders": "order-service",
    "payment": "payment-service",
    "payments": "payment-service",
    "inventory": "inventory-service",
    "notification": "notification-svc",
    "notifications": "notification-svc",
    "search": "search-service",
    "cache": "cache-layer",
    "redis": "cache-layer",
    "queue": "message-queue",
    "rabbitmq": "message-queue",
    "postgres": "postgres-primary",
    "database": "postgres-primary",
    "db": "postgres-primary",
    "db-primary": "postgres-primary",
    "db-replica": "postgres-replica",
}

# Baseline fallback metrics if no data sources are reachable
DEFAULT_BASELINE_METRICS: Dict[str, Dict[str, Any]] = {
    "payment-service": {
        "cpu_usage": 32.4,
        "memory_usage": 64.2,
        "disk_io": 18.5,
        "network_latency_ms": 28.1,
        "request_count": 2100,
        "error_rate": 0.012,
        "response_time_p99": 42.0,
        "active_connections": 88,
        "gc_pause_ms": 7.5,
        "thread_count": 36,
    },
    "order-service": {
        "cpu_usage": 48.2,
        "memory_usage": 72.1,
        "disk_io": 34.0,
        "network_latency_ms": 19.4,
        "request_count": 4300,
        "error_rate": 0.024,
        "response_time_p99": 58.5,
        "active_connections": 140,
        "gc_pause_ms": 8.9,
        "thread_count": 52,
    },
    "api-gateway": {
        "cpu_usage": 24.5,
        "memory_usage": 58.0,
        "disk_io": 12.0,
        "network_latency_ms": 6.8,
        "request_count": 8200,
        "error_rate": 0.008,
        "response_time_p99": 18.2,
        "active_connections": 310,
        "gc_pause_ms": 5.4,
        "thread_count": 120,
    },
    "auth-service": {
        "cpu_usage": 18.2,
        "memory_usage": 46.5,
        "disk_io": 8.4,
        "network_latency_ms": 4.5,
        "request_count": 3900,
        "error_rate": 0.005,
        "response_time_p99": 12.0,
        "active_connections": 160,
        "gc_pause_ms": 4.2,
        "thread_count": 60,
    },
}


def normalize_service_name(name: str) -> Optional[str]:
    """
    Resolve aliases and fuzzy names into canonical microservice names.
    Returns normalized service name, or None if unrecognized.
    """
    if not name:
        return None
    cleaned = name.strip().lower().replace("_", "-")
    if cleaned in KNOWN_SERVICES:
        return cleaned
    if cleaned in SERVICE_ALIASES:
        return SERVICE_ALIASES[cleaned]
    # Check suffix variations e.g. "payment service" or "payment"
    cleaned_no_spaces = cleaned.replace(" ", "-")
    if cleaned_no_spaces in KNOWN_SERVICES:
        return cleaned_no_spaces
    if cleaned_no_spaces in SERVICE_ALIASES:
        return SERVICE_ALIASES[cleaned_no_spaces]

    for known in KNOWN_SERVICES:
        if cleaned in known or known in cleaned:
            return known
    return None


def get_all_known_services() -> List[str]:
    """Returns list of canonical services monitored in Synapse RiskOps."""
    return list(KNOWN_SERVICES)


def _load_metric_from_csv(service_name: str) -> Optional[Dict[str, Any]]:
    """
    Look for latest metrics for service_name from sample_metrics.csv.
    """
    csv_paths = [
        Path("sample-data/sample_metrics.csv"),
        Path("../sample-data/sample_metrics.csv"),
        Path("/sample-data/sample_metrics.csv"),
        Path("e:/Users/Jayraj/synapse-riskops/sample-data/sample_metrics.csv"),
    ]
    for p in csv_paths:
        if p.exists():
            try:
                # Read last matching row for the service
                last_match = None
                with open(p, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("service_name") == service_name:
                            last_match = row
                if last_match:
                    return {
                        "service_name": service_name,
                        "cpu_usage": float(last_match.get("cpu_usage", 25.0)),
                        "memory_usage": float(last_match.get("memory_usage", 50.0)),
                        "disk_io": float(last_match.get("disk_io", 10.0)),
                        "network_latency_ms": float(last_match.get("network_latency_ms", 15.0)),
                        "request_count": int(float(last_match.get("request_count", 1000))),
                        "error_rate": float(last_match.get("error_rate", 0.01)),
                        "response_time_p99": float(last_match.get("response_time_p99", 25.0)),
                        "active_connections": int(float(last_match.get("active_connections", 50))),
                        "gc_pause_ms": float(last_match.get("gc_pause_ms", 5.0)),
                        "thread_count": int(float(last_match.get("thread_count", 40))),
                        "timestamp": last_match.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                    }
            except Exception as exc:
                logger.debug(f"Could not load metric from CSV {p}: {exc}")
    return None


def get_service_metrics(service_name: str) -> Dict[str, Any]:
    """
    Retrieve current metric snapshot for a service.
    Queries CSV or baseline defaults with fallback.
    """
    from_csv = _load_metric_from_csv(service_name)
    if from_csv:
        return from_csv

    baseline = DEFAULT_BASELINE_METRICS.get(service_name)
    if not baseline:
        baseline = {
            "cpu_usage": 30.0,
            "memory_usage": 55.0,
            "disk_io": 15.0,
            "network_latency_ms": 12.0,
            "request_count": 2500,
            "error_rate": 0.01,
            "response_time_p99": 28.0,
            "active_connections": 95,
            "gc_pause_ms": 6.0,
            "thread_count": 45,
        }
    return {
        "service_name": service_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **baseline,
    }


def _calculate_fallback_risk(service_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Heuristic risk calculation when ml-engine is unavailable or unready.
    Calculates weighted composite score (0-100) and risk tier.
    """
    cpu = metrics.get("cpu_usage", 20.0)
    mem = metrics.get("memory_usage", 40.0)
    err = metrics.get("error_rate", 0.01) * 100  # as percentage
    p99 = metrics.get("response_time_p99", 20.0)

    # Risk weights
    score = (
        (cpu / 100.0) * 25.0 +
        (mem / 100.0) * 30.0 +
        min(100.0, err * 10.0) * 0.25 +
        min(100.0, (p99 / 200.0) * 100.0) * 0.20
    )
    score = max(0.0, min(100.0, round(score, 1)))

    if score >= 75.0:
        tier = "CRITICAL"
        failure_type = "latency_degradation" if p99 > 100 else "memory_exhaustion" if mem > 85 else "cpu_saturation"
        horizon = 30
    elif score >= 40.0:
        tier = "WATCH"
        failure_type = "latency_degradation" if p99 > 60 else "none"
        horizon = 60
    else:
        tier = "HEALTHY"
        failure_type = "none"
        horizon = 0

    return {
        "risk_score": score,
        "risk_tier": tier,
        "confidence": 0.88,
        "predicted_failure_type": failure_type,
        "prediction_horizon_minutes": horizon,
        "anomaly_detail": {
            "anomaly_score": round(score / 100.0, 2),
            "is_anomaly": score >= 75.0,
            "top_contributing_features": ["memory_usage" if mem > 70 else "cpu_usage"],
        },
        "forecast_detail": {
            "forecast_risk": round(score / 100.0, 2),
            "predicted_failure_type": failure_type,
            "prediction_horizon_minutes": horizon,
            "trend_direction": "rising" if score >= 40 else "stable",
        },
    }


def get_service_risk_score(service_name: str) -> Dict[str, Any]:
    """
    Feature #1: Service Health Query.
    Calls ml-engine POST /api/risk-score for the requested service.
    Returns:
    - risk score, risk tier, predicted failure type, prediction horizon
    - clean readable card payload for the UI
    """
    canonical_name = normalize_service_name(service_name)
    if not canonical_name:
        canonical_name = service_name.strip()

    metrics = get_service_metrics(canonical_name)

    prediction: Dict[str, Any]
    try:
        resp = requests.post(
            f"{ML_ENGINE_URL}/api/risk-score",
            json={"metrics": metrics},
            timeout=5,
        )
        if resp.status_code == 200:
            prediction = resp.json()
        else:
            logger.warning(
                f"ml-engine returned status {resp.status_code}, using fallback risk calculation for {canonical_name}"
            )
            prediction = _calculate_fallback_risk(canonical_name, metrics)
    except Exception as exc:
        logger.warning(
            f"Could not reach ml-engine at {ML_ENGINE_URL} ({exc}), using fallback calculation for {canonical_name}"
        )
        prediction = _calculate_fallback_risk(canonical_name, metrics)

    risk_score = float(prediction.get("risk_score", 0.0))
    raw_tier = str(prediction.get("risk_tier", "healthy")).upper()
    risk_tier = "HEALTHY" if "HEALTHY" in raw_tier else "CRITICAL" if "CRITICAL" in raw_tier else "WATCH"
    predicted_failure_type = prediction.get("predicted_failure_type", "none")
    prediction_horizon = int(prediction.get("prediction_horizon_minutes", 0))
    confidence = float(prediction.get("confidence", 0.90))

    # Build human-readable status summary
    if risk_tier == "CRITICAL":
        status_summary = (
            f"⚠️ **{canonical_name}** is at **CRITICAL RISK** ({risk_score}/100). "
            f"Potential failure: `{predicted_failure_type}` predicted within {prediction_horizon} minutes."
        )
    elif risk_tier == "WATCH":
        status_summary = (
            f"👀 **{canonical_name}** is under **ELEVATED WATCH** ({risk_score}/100). "
            f"Metrics show minor drift. Predicted failure: `{predicted_failure_type}` in {prediction_horizon} min."
            if predicted_failure_type != "none"
            else f"👀 **{canonical_name}** is under **ELEVATED WATCH** ({risk_score}/100). No immediate failure predicted."
        )
    else:
        status_summary = (
            f"✅ **{canonical_name}** is operating **HEALTHY** (Risk Score: {risk_score}/100). "
            f"All vitals within nominal thresholds."
        )

    # Card payload formatted for the frontend RiskScoreCard
    card_data = {
        "service_name": canonical_name,
        "risk_score": round(risk_score, 1),
        "risk_tier": risk_tier,
        "prediction_confidence": round(confidence, 2),
        "predicted_failure_type": predicted_failure_type,
        "prediction_horizon_minutes": prediction_horizon,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "cpu_usage": round(float(metrics.get("cpu_usage", 0.0)), 1),
            "memory_usage": round(float(metrics.get("memory_usage", 0.0)), 1),
            "error_rate": round(float(metrics.get("error_rate", 0.0)), 3),
            "response_time_p99": round(float(metrics.get("response_time_p99", 0.0)), 1),
        },
        "anomaly_detail": prediction.get("anomaly_detail", {}),
        "forecast_detail": prediction.get("forecast_detail", {}),
    }

    return {
        "service_name": canonical_name,
        "risk_score": round(risk_score, 1),
        "risk_tier": risk_tier,
        "confidence": round(confidence, 2),
        "predicted_failure_type": predicted_failure_type,
        "prediction_horizon_minutes": prediction_horizon,
        "status_summary": status_summary,
        "metrics": metrics,
        "card": {
            "type": "risk_score",
            "data": card_data,
        },
    }
