from __future__ import annotations

from fastapi import FastAPI

from app.observability.telemetry import configure_telemetry


def test_telemetry_is_explicitly_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CONTINUUM_OTEL_EXPORTER", raising=False)
    app = FastAPI()

    mode = configure_telemetry(app)

    assert mode == "disabled"


def test_google_cloud_trace_configures_provider_and_fastapi(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, *, resource):  # type: ignore[no-untyped-def]
            captured["resource"] = resource

        def add_span_processor(self, processor) -> None:  # type: ignore[no-untyped-def]
            captured["processor"] = processor

    class FakeExporter:
        def __init__(self, *, project_id: str) -> None:
            captured["project_id"] = project_id

    class FakeProcessor:
        def __init__(self, exporter) -> None:  # type: ignore[no-untyped-def]
            captured["exporter"] = exporter

    def fake_instrument(app, **options):  # type: ignore[no-untyped-def]
        captured["app"] = app
        captured["instrument_options"] = options

    monkeypatch.setenv("CONTINUUM_OTEL_EXPORTER", "google_cloud_trace")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "continuum-demo")
    monkeypatch.setenv("K_SERVICE", "continuum-control-plane")
    monkeypatch.setattr("app.observability.telemetry.TracerProvider", FakeProvider)
    monkeypatch.setattr(
        "app.observability.telemetry.CloudTraceSpanExporter",
        FakeExporter,
    )
    monkeypatch.setattr(
        "app.observability.telemetry.BatchSpanProcessor",
        FakeProcessor,
    )
    monkeypatch.setattr(
        "app.observability.telemetry.trace.set_tracer_provider",
        lambda provider: captured.setdefault("provider", provider),
    )
    monkeypatch.setattr(
        "app.observability.telemetry.FastAPIInstrumentor.instrument_app",
        fake_instrument,
    )
    app = FastAPI()

    mode = configure_telemetry(app)

    assert mode == "google_cloud_trace"
    assert captured["project_id"] == "continuum-demo"
    assert captured["app"] is app
    resource = captured["resource"]
    assert resource.attributes["service.name"] == "continuum-control-plane"
    assert resource.attributes["gcp.project_id"] == "continuum-demo"
    assert captured["instrument_options"] == {
        "tracer_provider": captured["provider"],
        "excluded_urls": "/api/health",
    }
