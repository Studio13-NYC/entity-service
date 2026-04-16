"""Offline contract tests: ``/extract`` + ``/schema-pipeline/*`` with mocks (no Brave, no live TypeDB).

Tagged for GrooveGraph CI: ``entity_service_contract_tests_no_brave`` (pytest marker: ``contract``).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.typedb_connection import TypeDbHttpSettings

client = TestClient(app)

_DEFINE_MO_ARTIST = """
define
attribute name, value string;
entity mo-music-artist, owns name;
"""


def _sample_answer_row(*, attr: str, value: str) -> dict[str, Any]:
    return {
        "data": {
            "v": {
                "kind": "attribute",
                "type": {
                    "kind": "attributeType",
                    "valueType": "string",
                    "label": attr,
                },
                "value": value,
            },
        },
    }


@pytest.mark.contract
def test_post_extract_mo_style_schema_and_labels_contract() -> None:
    """``labels`` must match ``schema.knownEntities[].label`` (e.g. MO hyphenated types)."""
    r = client.post(
        "/extract",
        json={
            "text": "Ex. played a show",
            "labels": ["mo-music-artist"],
            "schema": {
                "entityTypes": ["mo-music-artist"],
                "knownEntities": [
                    {
                        "label": "mo-music-artist",
                        "canonical": "Example Artist",
                        "aliases": ["Ex."],
                    },
                ],
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "entities" in body
    assert len(body["entities"]) == 1
    ent = body["entities"][0]
    assert ent["label"] == "mo-music-artist"
    assert ent["text"] == "Example Artist"
    assert set(ent) == {"text", "label", "start", "end", "confidence"}


@pytest.mark.contract
def test_post_extract_mo_style_default_alias_and_label_filter() -> None:
    r = client.post(
        "/extract",
        json={
            "text": "Order parts from Widget today",
            "labels": ["mo-test-widget"],
        },
    )
    assert r.status_code == 200
    ents = r.json()["entities"]
    assert len(ents) == 1
    assert ents[0]["label"] == "mo-test-widget"
    assert ents[0]["text"] == "Widget Company"


@pytest.mark.contract
def test_get_health_and_ready_contract() -> None:
    assert client.get("/health").json() == {"ok": True}
    assert client.get("/ready").json() == {"ok": True}


@pytest.mark.contract
def test_schema_pipeline_raw_with_mocked_typedb(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.routes.schema_pipeline as sp

    settings = TypeDbHttpSettings(
        base_url="https://typedb.example",
        username="u",
        password="p",
        database="music",
    )
    monkeypatch.setattr(sp, "load_typedb_http_settings", lambda: settings)

    class _FakeClient:
        def __init__(self, _http: object, _settings: TypeDbHttpSettings) -> None:
            pass

        async def get_databases(self) -> list[str]:
            return ["music"]

        async def get_database_type_schema(self, _database: str) -> str:
            return _DEFINE_MO_ARTIST

        async def one_shot_query(self, **kwargs: Any) -> dict[str, Any]:
            return {"answers": [_sample_answer_row(attr="name", value="Sample Name")]}

    monkeypatch.setattr(sp, "TypeDbHttpClient", _FakeClient)

    r = client.post(
        "/schema-pipeline/raw",
        json={
            "assumptions": {
                "entityTypes": ["mo-music-artist"],
                "nameAttribute": "name",
                "limitPerType": 5,
            },
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "mo-music-artist" in body["parsedEntityTypeLabels"]
    per = {seg["entityType"]: seg for seg in body["perType"]}
    assert per["mo-music-artist"]["declaredInDefineSchema"] is True
    assert len(per["mo-music-artist"]["sampleAnswers"]) >= 1


@pytest.mark.contract
def test_schema_pipeline_formatted_with_mocked_typedb(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.routes.schema_pipeline as sp

    settings = TypeDbHttpSettings(
        base_url="https://typedb.example",
        username="u",
        password="p",
        database="music",
    )
    monkeypatch.setattr(sp, "load_typedb_http_settings", lambda: settings)

    class _FakeClient:
        def __init__(self, _http: object, _settings: TypeDbHttpSettings) -> None:
            pass

        async def get_databases(self) -> list[str]:
            return ["music"]

        async def get_database_type_schema(self, _database: str) -> str:
            return _DEFINE_MO_ARTIST

        async def one_shot_query(self, **kwargs: Any) -> dict[str, Any]:
            return {"answers": [_sample_answer_row(attr="name", value="Sample Name")]}

    monkeypatch.setattr(sp, "TypeDbHttpClient", _FakeClient)

    r = client.post(
        "/schema-pipeline/formatted",
        json={
            "assumptions": {
                "entityTypes": ["mo-music-artist"],
                "nameAttribute": "name",
                "limitPerType": 5,
            },
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["entityTypes"] == ["mo-music-artist"]
    assert len(body["knownEntities"]) == 1
    ke = body["knownEntities"][0]
    assert ke["label"] == "mo-music-artist"
    assert ke["canonical"] == "Sample Name"
    assert ke["aliases"] == []
