from __future__ import annotations

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_telemetry(app: FastAPI) -> str:
    mode = os.environ.get("CONTINUUM_OTEL_EXPORTER", "disabled").lower()
    if mode in {"disabled", "none"}:
        return "disabled"
    if mode != "google_cloud_trace":
        raise RuntimeError(
            "CONTINUUM_OTEL_EXPORTER must be disabled or google_cloud_trace"
        )
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
        "GCLOUD_PROJECT"
    )
    if not project:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is required for Google Cloud Trace export"
        )
    service_name = os.environ.get("K_SERVICE", "continuum-control-plane")
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "continuum",
            "service.version": os.environ.get("K_REVISION", "local"),
            "deployment.environment.name": os.environ.get(
                "CONTINUUM_ENVIRONMENT",
                "production",
            ),
            "gcp.project_id": project,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(CloudTraceSpanExporter(project_id=project))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="/api/health",
    )
    return "google_cloud_trace"
