import json
import logging
from datetime import datetime, timezone
from typing import TextIO


SENSITIVE_FIELD_MARKERS = ("secret", "password", "token", "encryption", "dni", "cbu", "cuil")
STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in STANDARD_LOG_RECORD_FIELDS or key.startswith("_"):
                continue

            payload[key] = self._redact_if_sensitive(key, value)

        return json.dumps(payload, default=str)

    @staticmethod
    def _redact_if_sensitive(key: str, value: object) -> object:
        if any(marker in key.lower() for marker in SENSITIVE_FIELD_MARKERS):
            return "[REDACTED]"
        return value


def configure_logging(stream: TextIO | None = None) -> None:
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
