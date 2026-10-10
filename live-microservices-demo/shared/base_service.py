"""
Base FastAPI Microservice Application Factory.
Standardizes metrics, structured logging, health checks, correlation tracking,
and chaos engineering across all 10 microservices.
"""

import time
import os
import uuid
import psutil
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)

from shared.chaos import ChaosEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)


class ChaosInjectRequest(BaseModel):
    fault_type: str = Field(..., description="'latency', 'error_rate', 'cpu_spike', 'memory_leak', 'service_outage'")
    duration_seconds: int = Field(120, ge=5, le=3600)
    intensity: float = Field(0.8, ge=0.05, le=1.0)
    extra_params: Optional[Dict[str, Any]] = None


def create_microservice_app(
    service_name: str,
    title: str,
    port: int,
    description: str = "",
) -> FastAPI:
    """Factory to create a fully instrumented microservice application."""
    app = FastAPI(
        title=title,
        description=description,
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach Chaos Engine
    chaos_engine = ChaosEngine(service_name=service_name)
    app.state.chaos = chaos_engine
    app.state.service_name = service_name
    app.state.service_port = port

    # Prometheus Instrumentation with custom isolated registry
    registry = CollectorRegistry()

    http_requests_total = Counter(
        "http_requests_total",
        "Total HTTP requests handled",
        ["service", "method", "endpoint", "status"],
        registry=registry,
    )
    http_request_duration_seconds = Histogram(
        "http_request_duration_seconds",
        "Request duration distribution in seconds",
        ["service", "method", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        registry=registry,
    )
    http_requests_in_progress = Gauge(
        "http_requests_in_progress",
        "Concurrent active requests being processed",
        ["service"],
        registry=registry,
    )
    app_error_rate = Gauge(
        "app_error_rate",
        "Error rate percentage (0 - 100)",
        ["service"],
        registry=registry,
    )
    app_active_connections = Gauge(
        "app_active_connections",
        "Current estimated active connections",
        ["service"],
        registry=registry,
    )
    app_cpu_usage = Gauge(
        "app_cpu_usage",
        "Host / container CPU usage percent",
        ["service"],
        registry=registry,
    )
    app_memory_usage = Gauge(
        "app_memory_usage",
        "Host / container memory usage percent",
        ["service"],
        registry=registry,
    )
    app_thread_count = Gauge(
        "app_thread_count",
        "Process active thread count",
        ["service"],
        registry=registry,
    )

    app.state.registry = registry

    # Rolling window state for error calculation
    window_stats = {"total": 0, "errors": 0, "last_reset": time.time()}

    @app.middleware("http")
    async def telemetry_middleware(request: Request, call_next):
        # Propagate or create correlation ID
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = corr_id

        # Skip instrumentation on internal metrics & health checks to avoid skew
        path = request.url.path
        if path in ("/metrics", "/health", "/chaos/status"):
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response

        # Apply runtime chaos faults (latency, errors, outages)
        http_requests_in_progress.labels(service=service_name).inc()
        start_time = time.time()
        status_code = 200

        try:
            try:
                chaos_engine.apply_runtime_faults()
            except HTTPException as he:
                status_code = he.status_code
                http_requests_total.labels(
                    service=service_name,
                    method=request.method,
                    endpoint=path,
                    status=str(he.status_code),
                ).inc()
                raise he

            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Correlation-ID"] = corr_id
            return response
        except Exception as exc:
            if not isinstance(exc, HTTPException):
                status_code = 500
            raise exc
        finally:
            duration = time.time() - start_time
            http_requests_in_progress.labels(service=service_name).dec()
            http_requests_total.labels(
                service=service_name,
                method=request.method,
                endpoint=path,
                status=str(status_code),
            ).inc()
            http_request_duration_seconds.labels(
                service=service_name,
                method=request.method,
                endpoint=path,
            ).observe(duration)

            # Update rolling error rate
            window_stats["total"] += 1
            if status_code >= 400:
                window_stats["errors"] += 1
            if time.time() - window_stats["last_reset"] > 60:
                window_stats["total"] = max(1, window_stats["total"] // 2)
                window_stats["errors"] = window_stats["errors"] // 2
                window_stats["last_reset"] = time.time()

            err_rate = (window_stats["errors"] / max(1, window_stats["total"])) * 100.0

            # If chaos fault is active, ensure gauge reflects it
            ch_status = chaos_engine.get_status()
            if ch_status["has_active_fault"]:
                f_map = ch_status["active_faults"]
                if "error_rate" in f_map:
                    err_rate = max(err_rate, float(f_map["error_rate"]["intensity"]) * 100.0)
                elif "service_outage" in f_map:
                    err_rate = 100.0

            app_error_rate.labels(service=service_name).set(round(err_rate, 2))


    # Standard Endpoints
    @app.get("/health", tags=["Operational"])
    async def health_check():
        status = chaos_engine.get_status()
        is_healthy = not status["has_active_fault"]
        return {
            "status": "healthy" if is_healthy else "degraded",
            "service_name": service_name,
            "port": port,
            "has_active_fault": status["has_active_fault"],
            "active_faults": status["active_faults"],
            "timestamp": time.time(),
        }

    @app.get("/metrics", tags=["Operational"])
    async def metrics_endpoint():
        # Update system resource gauges
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            threads = len(psutil.Process().threads())
            app_cpu_usage.labels(service=service_name).set(cpu)
            app_memory_usage.labels(service=service_name).set(mem)
            app_thread_count.labels(service=service_name).set(threads)
            # Estimate active connections
            conns = len(psutil.Process().net_connections(kind="inet"))
            app_active_connections.labels(service=service_name).set(conns)
        except Exception:
            pass

        data = generate_latest(registry)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    @app.post("/chaos/inject", tags=["Chaos Testing"])
    async def inject_chaos(req: ChaosInjectRequest):
        return chaos_engine.inject_fault(
            fault_type=req.fault_type,
            duration_seconds=req.duration_seconds,
            intensity=req.intensity,
            extra_params=req.extra_params,
        )

    @app.post("/chaos/clear", tags=["Chaos Testing"])
    async def clear_chaos():
        return chaos_engine.clear_faults()

    @app.get("/chaos/status", tags=["Chaos Testing"])
    async def chaos_status():
        return chaos_engine.get_status()

    return app
