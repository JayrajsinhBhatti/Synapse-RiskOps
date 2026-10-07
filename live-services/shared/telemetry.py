"""
Shared OpenTelemetry instrumentation for live microservices.
Safely exports traces to OTel Collector without blocking or failing on network drops.
"""

import os
import logging

logger = logging.getLogger("telemetry")

_tracer = None

def init_telemetry(app=None, service_name=None):
    """Initialize OpenTelemetry tracing if available."""
    global _tracer
    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "synapse-live-service")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource.create({SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer(service_name)

        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
            logger.info(f"OpenTelemetry FastAPI instrumented for {service_name} -> {endpoint}")

    except Exception as exc:
        logger.warning(f"OpenTelemetry initialization skipped/failed: {exc}")

def get_tracer():
    global _tracer
    return _tracer
