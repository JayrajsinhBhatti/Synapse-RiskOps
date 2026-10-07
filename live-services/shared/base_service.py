"""
Base FastAPI Application Factory for Synapse Live Microservices.
Provides standardized Prometheus metrics, Chaos API, OpenTelemetry, and health endpoints.
"""

import time
import asyncio
import threading
import logging
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from shared.chaos import ChaosEngine
from shared.telemetry import init_telemetry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("base_service")


class ChaosRequest(BaseModel):
    fault_type: str = Field(..., description="cpu_spike | memory_leak | latency | error_rate | crash | dependency_timeout")
    duration_seconds: int = Field(120, ge=1, le=3600)
    intensity: float = Field(0.8, ge=0.01, le=1.0)


def create_base_app(service_name: str, title: str, description: str = "") -> FastAPI:
    app = FastAPI(title=title, description=description, version="1.0.0")

    # Add CORS
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

    # Standard Prometheus Metrics
    http_requests_total = Counter(
        "http_requests_total",
        "Total HTTP requests processed",
        ["method", "endpoint", "status"]
    )
    http_request_duration_seconds = Histogram(
        "http_request_duration_seconds",
        "Request latency distribution in seconds",
        ["method", "endpoint"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
    )
    http_requests_in_progress = Gauge(
        "http_requests_in_progress",
        "Currently processing requests",
        ["method"]
    )
    app_error_rate = Gauge(
        "app_error_rate",
        "Rolling error rate percentage",
        ["service"]
    )
    app_active_connections = Gauge(
        "app_active_connections",
        "Current active connections",
        ["service"]
    )
    app_thread_count = Gauge(
        "app_thread_count",
        "Active thread/coroutine count",
        ["service"]
    )

    # Real Python Garbage Collection pause instrumentation
    app_gc_pause_ms = Gauge(
        "app_gc_pause_ms",
        "Real Python garbage collection pause duration in milliseconds",
        ["service"]
    )

    # Real Container Process Disk I/O operations from /proc/self/io
    app_disk_io_operations_total = Counter(
        "app_disk_io_operations_total",
        "Total disk I/O operations (system read/write calls from /proc/self/io)",
        ["service"]
    )

    # Register GC callback for real pause duration
    import gc
    gc_start_times = {}

    def _gc_callback(phase, info):
        tid = threading.get_ident()
        if phase == "start":
            gc_start_times[tid] = time.perf_counter()
        elif phase == "stop":
            start_t = gc_start_times.pop(tid, None)
            if start_t is not None:
                pause_ms = (time.perf_counter() - start_t) * 1000.0
                app_gc_pause_ms.labels(service=service_name).set(pause_ms)

    gc.callbacks.append(_gc_callback)
    # Trigger an initial collection to calibrate the gauge
    gc.collect()

    # Disk I/O helper
    last_io_ops = [0]
    io_lock = threading.Lock()

    def _update_disk_io():
        try:
            with open("/proc/self/io", "r") as f:
                data = {}
                for line in f:
                    parts = line.strip().split(": ")
                    if len(parts) == 2:
                        data[parts[0]] = int(parts[1])
                total_ops = data.get("syscr", 0) + data.get("syscw", 0)
                with io_lock:
                    if last_io_ops[0] == 0:
                        last_io_ops[0] = total_ops
                        app_disk_io_operations_total.labels(service=service_name).inc(total_ops)
                    else:
                        diff = total_ops - last_io_ops[0]
                        if diff > 0:
                            app_disk_io_operations_total.labels(service=service_name).inc(diff)
                            last_io_ops[0] = total_ops
        except Exception:
            pass

    # Initial disk I/O read
    _update_disk_io()

    # Rolling window for error rate calculation
    recent_requests = []
    recent_lock = threading.Lock()

    app.state.metrics = {
        "http_requests_total": http_requests_total,
        "http_request_duration_seconds": http_request_duration_seconds,
        "http_requests_in_progress": http_requests_in_progress,
        "app_error_rate": app_error_rate,
        "app_active_connections": app_active_connections,
        "app_thread_count": app_thread_count,
        "app_gc_pause_ms": app_gc_pause_ms,
        "app_disk_io_operations_total": app_disk_io_operations_total,
    }

    @app.middleware("http")
    async def metrics_and_chaos_middleware(request: Request, call_next):
        # Skip metrics/chaos logic for internal Prometheus scrape and health check
        path = request.url.path
        is_internal = path in ("/metrics", "/health", "/chaos")

        if is_internal:
            return await call_next(request)

        method = request.method
        endpoint = path

        start_time = time.time()
        http_requests_in_progress.labels(method=method).inc()
        app_active_connections.labels(service=service_name).inc()
        app_thread_count.labels(service=service_name).set(threading.active_count())

        status_code = 500
        try:
            # Chaos latency injection
            latency = chaos_engine.get_latency_delay()
            if latency > 0:
                await asyncio.sleep(latency)

            # Chaos error injection
            if chaos_engine.should_inject_error():
                status_code = 500
                return Response(content='{"error": "Chaos injected internal server error"}', status_code=500, media_type="application/json")

            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            http_requests_in_progress.labels(method=method).dec()
            app_active_connections.labels(service=service_name).dec()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
            http_requests_total.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
            _record_request(status_code)

    def _record_request(status_code: int):
        with recent_lock:
            now = time.time()
            recent_requests.append((now, status_code >= 500))
            # Keep last 60 seconds of requests
            cutoff = now - 60.0
            while recent_requests and recent_requests[0][0] < cutoff:
                recent_requests.pop(0)

            total = len(recent_requests)
            if total > 0:
                errors = sum(1 for _, is_err in recent_requests if is_err)
                rate = (errors / total) * 100.0
            else:
                rate = 0.0
            app_error_rate.labels(service=service_name).set(rate)

    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "service": service_name,
            "timestamp": time.time(),
        }

    @app.get("/metrics", tags=["System"])
    async def get_metrics():
        app_thread_count.labels(service=service_name).set(threading.active_count())
        _update_disk_io()
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/chaos", tags=["Chaos Engineering"])
    async def inject_chaos(req: ChaosRequest):
        result = chaos_engine.inject_fault(
            fault_type=req.fault_type,
            duration_seconds=req.duration_seconds,
            intensity=req.intensity
        )
        return result

    @app.get("/chaos", tags=["Chaos Engineering"])
    async def get_chaos():
        return chaos_engine.get_status()

    @app.delete("/chaos", tags=["Chaos Engineering"])
    async def clear_chaos():
        return chaos_engine.clear_faults()

    # Startup event: Initialize OTel
    @app.on_event("startup")
    async def startup_event():
        init_telemetry(app=app, service_name=service_name)
        logger.info(f"Service {service_name} started successfully")

    return app
