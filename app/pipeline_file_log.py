"""Rotating file logs for ``app.pipeline`` under ``docs/logs`` (always on unless disabled)."""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

from app.request_context import request_id_ctx

_configured = False

_DEFAULT_LOG_DIR = "docs/logs"


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = request_id_ctx.get()
        except LookupError:
            record.request_id = "—"
        return True


def configure_pipeline_file_logging() -> None:
    """Attach ``app.pipeline`` RotatingFileHandler under ``docs/logs`` by default.

    Set ``ENTITY_SERVICE_PIPELINE_LOG_FILE`` to ``0`` / ``false`` / ``no`` / ``off`` to disable
    file output (e.g. in constrained CI). Override directory with ``ENTITY_SERVICE_PIPELINE_LOG_DIR``.
    """
    global _configured
    if _configured:
        return

    raw = os.environ.get("ENTITY_SERVICE_PIPELINE_LOG_FILE", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        pl = logging.getLogger("app.pipeline")
        if not pl.handlers:
            pl.addHandler(logging.NullHandler())
        pl.propagate = False
        _configured = True
        return

    rel = os.environ.get("ENTITY_SERVICE_PIPELINE_LOG_DIR", _DEFAULT_LOG_DIR).strip() or _DEFAULT_LOG_DIR
    root = Path(rel)
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)

    max_bytes = int(os.environ.get("ENTITY_SERVICE_PIPELINE_LOG_MAX_BYTES", "10485760"))
    backups = int(os.environ.get("ENTITY_SERVICE_PIPELINE_LOG_BACKUPS", "5"))

    path = root / "entity-service-pipeline.log"
    fmt = os.environ.get(
        "ENTITY_SERVICE_PIPELINE_LOG_FORMAT",
        "%(asctime)s | %(request_id)s | %(levelname)s | %(name)s | %(message)s",
    )
    datefmt = os.environ.get("ENTITY_SERVICE_PIPELINE_LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")

    handler = logging.handlers.RotatingFileHandler(
        path,
        maxBytes=max(1_000_000, max_bytes),
        backupCount=max(1, backups),
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    handler.addFilter(_RequestIdFilter())

    pl = logging.getLogger("app.pipeline")
    pl.handlers.clear()
    pl.addHandler(handler)
    pl.setLevel(logging.DEBUG)
    pl.propagate = False

    pl.info("pipeline_file_logging_started path=%s", path.resolve())
    _configured = True
