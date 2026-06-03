import io
import json
import logging


def test_configure_logging_emits_json_lines_and_redacts_sensitive_fields():
    from app.core.logging import configure_logging

    stream = io.StringIO()
    configure_logging(stream=stream)

    logging.getLogger().info(
        "foundation-ready",
        extra={"request_id": "req-123", "secret_key": "super-secret", "dni": "12345678"},
    )

    payload = json.loads(stream.getvalue().strip())

    assert payload["message"] == "foundation-ready"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-123"
    assert payload["secret_key"] == "[REDACTED]"
    assert payload["dni"] == "[REDACTED]"
    assert payload["timestamp"]
