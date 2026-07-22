import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from src.config import settings

LOG_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "latency_ms",
    "actor_type",
    "actor_id",
    "actor_role",
    "organization_id",
    "invite_id",
    "error_code",
    "failure_reason",
    "auth_stage",
    "token_purpose",
    "database",
)


class JsonFormatter(logging.Formatter):
    """Serialize only explicitly approved fields to prevent sensitive log leaks."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for field in LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        safe_message = getattr(record, "safe_message", None)
        if safe_message is not None:
            payload["message"] = safe_message
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """Configure compact structured logs for local and production execution."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(
        logging.DEBUG if settings.ENV == "development" else logging.INFO
    )

    for noisy_logger in ("pymongo", "motor", "multipart"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
