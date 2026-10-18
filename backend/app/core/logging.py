"""
app/core/logging.py
────────────────────
Structured JSON logging for CascadeIQ.

Uses the stdlib `logging` module with a custom JSON formatter so that every
log record is emitted as a single-line JSON object. A `request_id` field is
threaded through via a `contextvars.ContextVar` so that every log line
emitted during a FastAPI request lifecycle automatically carries the ID of
that request.

Usage
─────
    from app.core.logging import configure_logging, bind_request_id, get_logger

    configure_logging("INFO")               # called once at startup
    bind_request_id("req-abc-123")          # called in middleware per-request
    logger = get_logger(__name__)
    logger.info("Processing route", extra={"node_count": 42})
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# ── Context variable carrying the current request-id ──────────────────────────
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def bind_request_id(request_id: str | None = None) -> str:
    """
    Bind a request-id to the current async context.

    If *request_id* is None a new UUID4 is generated and used.
    Returns the id that was bound.
    """
    rid = request_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """Return the request-id bound to the current context (empty string if none)."""
    return _request_id_var.get()


# ── JSON formatter ─────────────────────────────────────────────────────────────
class _JsonFormatter(logging.Formatter):
    """
    Emit each log record as a single-line JSON object.

    Standard fields:
        timestamp   ISO-8601 UTC
        level       DEBUG / INFO / WARNING / ERROR / CRITICAL
        logger      __name__ of the calling module
        message     formatted log message
        request_id  current request context (empty string if not in a request)

    Extra fields from ``extra={}`` are merged into the top-level object.
    Exception info is serialised to ``exc_info``.
    """

    SKIP_ATTRS = frozenset(
        {
            "args", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "message",
            "module", "msecs", "msg", "name", "pathname", "process",
            "processName", "relativeCreated", "stack_info", "taskName",
            "thread", "threadName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        record.message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "request_id": get_request_id(),
        }

        # Merge any extra= fields the caller supplied
        for key, value in record.__dict__.items():
            if key not in self.SKIP_ATTRS:
                payload[key] = value

        # Serialise exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        try:
            return json.dumps(payload, default=str)
        except Exception:  # pragma: no cover  — safety net
            return json.dumps({"message": str(payload), "level": "ERROR"})


# ── Public helpers ─────────────────────────────────────────────────────────────
def configure_logging(level: str = "INFO") -> None:
    """
    Configure the root logger to emit structured JSON to *stdout*.

    Call this **once** during application startup (e.g. in the lifespan
    context manager).  Subsequent calls are idempotent — the root logger's
    handlers are replaced, not duplicated.

    Parameters
    ----------
    level:
        A stdlib log-level string: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = _JsonFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(numeric_level)

    root = logging.getLogger()
    # Remove pre-existing handlers to avoid duplicate output
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Silence noisy third-party loggers unless we are in DEBUG mode
    if numeric_level > logging.DEBUG:
        for noisy in ("urllib3", "httpx", "httpcore", "osmnx", "fiona"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Return a standard `logging.Logger` pre-configured by `configure_logging`.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.
    """
    return logging.getLogger(name)
