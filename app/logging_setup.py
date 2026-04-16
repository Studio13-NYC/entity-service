"""Application logging: request id in every line, env-driven verbosity."""

from __future__ import annotations

import logging
import os

from app.request_context import request_id_ctx

_configured = False


class RequestIdFilter(logging.Filter):
    """Inject ``request_id`` from contextvar into log records (``%(request_id)s`` in format)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = request_id_ctx.get()
        except LookupError:
            record.request_id = "—"
        return True


def configure_app_logging() -> None:
    """Attach formatter + request-id filter to the ``app`` logger (idempotent across reload)."""
    global _configured
    if _configured:
        return

    trace_level_name = os.environ.get("ENTITY_SERVICE_REQUEST_TRACE_LEVEL", "DEBUG").strip().upper()
    trace_level = getattr(logging, trace_level_name, logging.DEBUG)

    fmt = os.environ.get(
        "ENTITY_SERVICE_LOG_FORMAT",
        "%(asctime)s | %(request_id)s | %(levelname)s | %(name)s | %(message)s",
    )
    datefmt = os.environ.get("ENTITY_SERVICE_LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    handler.addFilter(RequestIdFilter())

    app_log = logging.getLogger("app")
    app_log.handlers.clear()
    app_log.addHandler(handler)
    app_log.setLevel(trace_level)
    app_log.propagate = False

    from app.pipeline_file_log import configure_pipeline_file_logging

    configure_pipeline_file_logging()

    _configured = True
