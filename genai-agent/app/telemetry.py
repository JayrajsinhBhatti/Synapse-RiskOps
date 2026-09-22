"""
genai-agent/app/telemetry.py

OpenTelemetry instrumentation for the GenAI Agent service.
Configures traces, metrics, and logs export to the OTel Collector.
Auto-instruments FastAPI and adds custom spans for LangGraph pipeline nodes.
"""

import os
from loguru import logger

# OTel environment
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "synapse-genai-agent")

_tracer = None


def init_telemetry(app=None):
    """
    Initialize OpenTelemetry for the GenAI Agent.
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

        # Resource identifies this service in traces
        resource = Resource.create({SERVICE_NAME: OTEL_SERVICE_NAME})

        # Configure the tracer provider
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer(OTEL_SERVICE_NAME)

        # Auto-instrument FastAPI if an app instance is provided
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


def trace_pipeline_node(node_name: str):
    """
    Decorator to add OpenTelemetry span tracing to a LangGraph node function.

    Usage:
        @trace_pipeline_node("ml_node")
        def get_ml_prediction(state):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if tracer:
                with tracer.start_as_current_span(
                    f"pipeline.{node_name}",
                    attributes={
                        "pipeline.node": node_name,
                        "pipeline.service": "synapse-genai-agent",
                    },
                ) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("pipeline.status", "success")
                        return result
                    except Exception as exc:
                        span.set_attribute("pipeline.status", "error")
                        span.record_exception(exc)
                        raise
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator
