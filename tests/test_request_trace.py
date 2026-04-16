"""Request trace middleware: request id header and structured logs."""

from __future__ import annotations

import io
import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_x_request_id_header_on_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert "x-request-id" in {k.lower() for k in r.headers}
    assert len(r.headers["x-request-id"]) >= 8


def test_post_extract_logs_include_body_and_extract_done() -> None:
    """Attach a temporary handler: capsys does not reliably capture logging StreamHandler."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    app_log = logging.getLogger("app")
    app_log.addHandler(handler)
    try:
        r = client.post("/extract", json={"text": "Talking Heads"})
        assert r.status_code == 200
        out = buf.getvalue()
        assert "Talking Heads" in out
        assert "extract_done" in out
        assert "POST /extract" in out
    finally:
        app_log.removeHandler(handler)
