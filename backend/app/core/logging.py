"""Structured application logging.

Plain stdlib `logging`, no external dependency. Every log line carries a
timestamp, level, logger name, and an `event` key so entries are easy to
grep and, later, easy to feed into the security/audit layer. Call
`configure_logging()` once at startup and `get_logger(__name__)` /
`log_event(...)` everywhere else.
"""

from __future__ import annotations

import logging
import sys

_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"event"}

# Field names that must never reach the log output, even if a caller
# accidentally passes one through.
_SENSITIVE_KEYS = {"password", "token", "api_key", "apikey", "secret", "authorization"}
_MAX_FIELD_LEN = 200


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        parts = [f"{timestamp} {record.levelname:<8} {record.name}"]

        event = getattr(record, "event", None)
        message = record.getMessage()
        if event:
            parts.append(f"event={event}")
        if message and message != event:
            parts.append(message)

        for key, value in record.__dict__.items():
            if key in _RESERVED:
                continue
            parts.append(f"{key}={value}")

        text = " ".join(parts)
        if record.exc_info:
            text += "\n" + self.formatException(record.exc_info)
        return text


def _sanitize(fields: dict[str, object]) -> dict[str, object]:
    """Redacts sensitive keys, truncates long values, and renames any key
    that collides with a built-in `LogRecord` attribute (e.g. `filename`,
    `module`, `process`) — passing one of those through `extra=` raises
    `KeyError` deep inside stdlib `logging`, so callers must be free to use
    natural field names like `filename` without knowing that reserved set.
    """
    clean: dict[str, object] = {}
    for key, value in fields.items():
        out_key = f"{key}_" if key in _RESERVED else key
        if key.lower() in _SENSITIVE_KEYS:
            clean[out_key] = "***redacted***"
        elif isinstance(value, str) and len(value) > _MAX_FIELD_LEN:
            clean[out_key] = value[:_MAX_FIELD_LEN] + "...(truncated)"
        else:
            clean[out_key] = value
    return clean


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)

    # Quiet down noisy third-party loggers; our own events stay at `level`.
    logging.getLogger("uvicorn.access").setLevel("WARNING")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields: object) -> None:
    """Logs a structured application event.

    Never pass credentials or full document/message content in `fields` —
    values are best-effort sanitized (sensitive keys redacted, long strings
    truncated) but callers should still avoid sensitive content by design.
    """
    logger.log(level, event, extra={"event": event, **_sanitize(fields)})
