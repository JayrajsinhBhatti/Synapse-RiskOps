"""
ml-engine/app/telemetry.py

OpenTelemetry instrumentation for the ML Engine service.
Configures traces, metrics, and logs export to the OTel Collector.
Auto-instruments FastAPI and adds custom spans for ML operations.
"""

import os
from loguru import logger

# OTel environment
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "synapse-ml-engine")

_tracer = None


def init_telemetry(app=None):
    """
    Initialize OpenTelemetry for the ML Engine.
    Call this once at application startup.

    Args:
        app: FastAPI application instance (for auto-instrumentation)
    """
    global _tracer

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource.create({SERVICE_NAME: OTEL_SERVICE_NAME})

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer(OTEL_SERVICE_NAME)

        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
            logger.info(
                f"[Telemetry] FastAPI auto-instrumented. "
                f"Exporting to {OTEL_ENDPOINT}"
            )

        logger.info(
            f"[Telemetry] OpenTelemetry initialized for {OTEL_SERVICE_NAME}"
        )

    except ImportError as exc:
        logger.warning(
            f"[Telemetry] OpenTelemetry packages not installed: {exc}. "
            "Tracing will be disabled."
        )
    except Exception as exc:
        logger.error(f"[Telemetry] Failed to initialize: {exc}")


def get_tracer():
    """Get the configured tracer instance (or a no-op fallback)."""
    global _tracer
    if _tracer is None:
        try:
            from opentelemetry import trace
            _tracer = trace.get_tracer(OTEL_SERVICE_NAME)
        except ImportError:
            return None
    return _tracer


def trace_operation(operation_name: str):
    """
    Decorator to add OpenTelemetry span tracing to ML operations.

    Usage:
        @trace_operation("risk_scoring")
        def score(self, metrics):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if tracer:
                with tracer.start_as_current_span(
                    f"ml.{operation_name}",
                    attributes={
                        "ml.operation": operation_name,
                        "ml.service": "synapse-ml-engine",
                    },
                ) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("ml.status", "success")
                        return result
                    except Exception as exc:
                        span.set_attribute("ml.status", "error")
                        span.record_exception(exc)
                        raise
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator
