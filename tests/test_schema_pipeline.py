"""Tests for TypeDB schema pipeline (validate step is offline; raw/formatted need TypeDB)."""

from __future__ import annotations

from app.schema_pipeline_models import ErAssumptions
from app.services.schema_pipeline import run_pipeline_validate


def _define_minimal() -> str:
    return """
define
attribute name, value string;
entity musician, owns name;
"""


def test_er_assumptions_accepts_large_limit_per_type() -> None:
    """``limitPerType`` is no longer capped at the Pydantic layer (service clamps for TypeDB)."""
    a = ErAssumptions.model_validate(
        {"entityTypes": ["musician"], "nameAttribute": "name", "limitPerType": 99_999},
    )
    assert a.limit_per_type == 99_999


def test_validate_ready_when_types_and_attribute_match() -> None:
    assumptions = ErAssumptions.model_validate(
        {"entityTypes": ["musician"], "nameAttribute": "name"},
    )
    r = run_pipeline_validate(_define_minimal(), assumptions)
    assert r.ready is True
    assert r.issues == []


def test_validate_fails_for_unknown_entity_type() -> None:
    assumptions = ErAssumptions.model_validate(
        {"entityTypes": ["band"], "nameAttribute": "name"},
    )
    r = run_pipeline_validate(_define_minimal(), assumptions)
    assert r.ready is False
    assert any(i.code == "unknown_entity_type" for i in r.issues)


def test_validate_fails_for_missing_name_attribute() -> None:
    define = """
define
attribute title, value string;
entity album, owns title;
"""
    assumptions = ErAssumptions.model_validate(
        {"entityTypes": ["album"], "nameAttribute": "name"},
    )
    r = run_pipeline_validate(define, assumptions)
    assert r.ready is False
    assert any(i.code == "missing_string_attribute" for i in r.issues)


def test_define_parse_hyphenated_entity_type_and_owns() -> None:
    """MO-style labels must parse and resolve string ``owns`` (``mo_label_vocabulary``)."""
    from app.services.typedb_define_parse import (
        parse_entity_type_labels_from_define_schema,
        parse_string_attribute_types_owned_by_entity_from_define_schema,
    )

    define = """
define
attribute name, value string;
entity mo-music-artist, owns name;
"""
    labels = parse_entity_type_labels_from_define_schema(define)
    assert "mo-music-artist" in labels
    owns = parse_string_attribute_types_owned_by_entity_from_define_schema(define, "mo-music-artist")
    assert owns == ["name"]


def test_formatted_response_matches_extract_schema_payload() -> None:
    """GrooveGraph: formatted ``schema`` must deserialize as ``POST /extract`` ``schema``."""
    from app.models import EntitySchemaPayload
    from app.schema_pipeline_models import SchemaPipelineFormattedResponse

    formatted = SchemaPipelineFormattedResponse(
        entity_types=["mo-music-artist"],
        known_entities=[
            {"label": "mo-music-artist", "canonical": "Example Artist", "aliases": ["Ex."]},
        ],
    )
    wire = formatted.model_dump(by_alias=True)
    parsed = EntitySchemaPayload.model_validate(wire)
    assert parsed.entity_types[0].name == "mo-music-artist"
    assert parsed.known_entities[0].label == "mo-music-artist"
    assert parsed.known_entities[0].canonical == "Example Artist"
    assert parsed.known_entities[0].aliases == ["Ex."]


def test_parse_entity_labels_type_db3_style() -> None:
    from app.services.typedb_define_parse import parse_entity_type_labels_from_define_schema

    define = """
define
entity user, owns username;
entity company, sub organization;
"""
    labels = parse_entity_type_labels_from_define_schema(define)
    assert "user" in labels
    assert "company" in labels
