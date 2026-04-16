"""HTTP tests for schema-pipeline routes (validate is always available)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ready_matches_health_contract() -> None:
    h = client.get("/health")
    r = client.get("/ready")
    assert h.status_code == 200 and r.status_code == 200
    assert h.json() == r.json() == {"ok": True}


def test_validate_route_returns_issues() -> None:
    r = client.post(
        "/schema-pipeline/validate",
        json={
            "typeSchemaDefine": "define\nentity x, owns y;\n",
            "assumptions": {"entityTypes": ["missing"], "nameAttribute": "name"},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is False
    assert len(body["issues"]) >= 1


def test_raw_route_503_when_typedb_unconfigured(monkeypatch) -> None:
    import app.routes.schema_pipeline as sp

    monkeypatch.delenv("TYPEDB_USERNAME", raising=False)
    monkeypatch.delenv("TYPEDB_DATABASE", raising=False)
    monkeypatch.delenv("TYPEDB_CONNECTION_STRING", raising=False)

    def _no_settings() -> None:
        return None

    monkeypatch.setattr(sp, "load_typedb_http_settings", _no_settings)

    r = client.post(
        "/schema-pipeline/raw",
        json={"assumptions": {"entityTypes": ["musician"], "nameAttribute": "name"}},
    )
    assert r.status_code == 503
    detail = r.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "typedb_not_configured_on_entity_service"
    assert "hint" in detail
