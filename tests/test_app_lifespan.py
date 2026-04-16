"""FastAPI lifespan: startup diagnostics for optional TypeDB."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_lifespan_logs_warning_when_typedb_not_configured(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    for key in (
        "TYPEDB_CONNECTION_STRING",
        "TYPEDB_USERNAME",
        "TYPEDB_PASSWORD",
        "TYPEDB_DATABASE",
        "TYPEDB_ADDRESSES",
    ):
        monkeypatch.delenv(key, raising=False)

    caplog.set_level(logging.WARNING)
    with TestClient(app):
        pass

    assert any("TypeDB HTTP is not configured" in r.message for r in caplog.records)


def test_lifespan_silent_when_minimal_typedb_env_set(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("TYPEDB_USERNAME", "smoke_user")
    monkeypatch.setenv("TYPEDB_DATABASE", "smoke_db")
    monkeypatch.setenv("TYPEDB_ADDRESSES", "http://127.0.0.1:1729")
    monkeypatch.delenv("TYPEDB_CONNECTION_STRING", raising=False)

    caplog.set_level(logging.WARNING)
    with TestClient(app):
        pass

    assert not any("TypeDB HTTP is not configured" in r.message for r in caplog.records)
