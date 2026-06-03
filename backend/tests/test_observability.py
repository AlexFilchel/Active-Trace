from fastapi import FastAPI


def test_configure_observability_instruments_app_when_enabled(monkeypatch, valid_env):
    from app.core import observability

    app = FastAPI()
    captured = {}

    def fake_instrument_app(target_app, tracer_provider=None):
        captured["app"] = target_app
        captured["tracer_provider"] = tracer_provider

    monkeypatch.setattr(observability.FastAPIInstrumentor, "instrument_app", fake_instrument_app)

    assert observability.configure_observability(app) is True
    assert captured["app"] is app
    assert captured["tracer_provider"] is not None


def test_configure_observability_skips_instrumentation_when_disabled(monkeypatch, valid_env):
    from app.core import observability

    monkeypatch.setenv("OTEL_ENABLED", "false")
    app = FastAPI()
    called = False

    def fake_instrument_app(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(observability.FastAPIInstrumentor, "instrument_app", fake_instrument_app)

    assert observability.configure_observability(app) is False
    assert called is False
