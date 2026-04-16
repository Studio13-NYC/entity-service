"""FastAPI lifespan: startup diagnostics for optional TypeDB."""

from __future__ import annotations

import io
import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _capture_app_logs() -> tuple[io.StringIO, logging.Handler]:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.WARNING)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger("app").addHandler(handler)
    return buf, handler


def _remove_handler(handler: logging.Handler) -> None:
    logging.getLogger("app").removeHandler(handler)


def test_lifespan_logs_warning_when_typedb_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "TYPEDB_CONNECTION_STRING",
        "TYPEDB_USERNAME",
        "TYPEDB_PASSWORD",
        "TYPEDB_DATABASE",
        "TYPEDB_ADDRESSES",
    ):
        monkeypatch.delenv(key, raising=False)

    buf, handler = _capture_app_logs()
    try:
        with TestClient(app):
            pass
        out = buf.getvalue()
        assert "TypeDB HTTP is not configured" in out
    finally:
        _remove_handler(handler)


def test_lifespan_silent_when_minimal_typedb_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TYPEDB_USERNAME", "smoke_user")
    monkeypatch.setenv("TYPEDB_DATABASE", "smoke_db")
    monkeypatch.setenv("TYPEDB_ADDRESSES", "http://127.0.0.1:1729")
    monkeypatch.delenv("TYPEDB_CONNECTION_STRING", raising=False)

    buf, handler = _capture_app_logs()
    try:
        with TestClient(app):
            pass
        out = buf.getvalue()
        assert "TypeDB HTTP is not configured" not in out
    finally:
        _remove_handler(handler)
