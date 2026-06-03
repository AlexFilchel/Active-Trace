from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from app.core.config import Settings, get_settings


def configure_observability(app: FastAPI, settings: Settings | None = None) -> bool:
    active_settings = settings or get_settings()

    if not active_settings.otel_enabled:
        return False

    if getattr(app.state, "otel_instrumented", False):
        return True

    tracer_provider = TracerProvider(
        resource=Resource.create({"service.name": active_settings.otel_service_name})
    )
    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    app.state.otel_instrumented = True
    return True
