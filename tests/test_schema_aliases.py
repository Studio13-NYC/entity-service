"""Schema → alias rows and extraction with injected known entities."""

from app.models import EntitySchemaPayload, KnownEntityPayload
from app.services.extractor import extract_entities
from app.services.schema_aliases import alias_rows_from_schema


def test_alias_rows_from_schema_none() -> None:
    assert alias_rows_from_schema(None) == []


def test_alias_rows_from_schema_empty_payload() -> None:
    payload = EntitySchemaPayload.model_validate(
        {"entityTypes": [], "knownEntities": []},
    )
    assert alias_rows_from_schema(payload) == []


def test_alias_rows_includes_canonical_and_aliases() -> None:
    payload = EntitySchemaPayload.model_validate(
        {
            "entityTypes": ["book"],
            "knownEntities": [
                {
                    "label": "book",
                    "canonical": "Moby-Dick",
                    "aliases": ["Moby Dick", "MD"],
                },
            ],
        },
    )
    rows = alias_rows_from_schema(payload)
    assert ("book", "Moby-Dick", "Moby-Dick") in rows
    assert ("book", "Moby-Dick", "Moby Dick") in rows
    assert ("book", "Moby-Dick", "MD") in rows


def test_extract_entities_schema_only_novel_entity() -> None:
    """Without file aliases matching, schema-only row still matches text."""
    schema = EntitySchemaPayload(
        entity_types=["work"],
        known_entities=[
            KnownEntityPayload(
                label="work",
                canonical="Invisible Cities",
                aliases=["Invis Cities"],
            ),
        ],
    )
    entities = extract_entities(
        "Have you read Invis Cities?",
        use_aliases=True,
        schema=schema,
    )
    assert len(entities) == 1
    assert entities[0].text == "Invisible Cities"
    assert entities[0].label == "work"


def test_extract_entities_merges_file_config_and_schema() -> None:
    schema = EntitySchemaPayload(
        entity_types=["work"],
        known_entities=[
            KnownEntityPayload(
                label="work",
                canonical="The Trial",
                aliases=["Trial"],
            ),
        ],
    )
    text = "Girlfriend by Matt Sweet and The Trial"
    entities = extract_entities(text, schema=schema)
    labels = {e.label for e in entities}
    assert "recording" in labels
    assert "artist" in labels
    assert "work" in labels
    canonicals = {e.text for e in entities}
    assert "Girlfriend" in canonicals
    assert "Matthew Sweet" in canonicals
    assert "The Trial" in canonicals


def test_schema_accepts_snake_case_keys() -> None:
    payload = EntitySchemaPayload.model_validate(
        {
            "entity_types": ["x"],
            "known_entities": [
                {"label": "x", "canonical": "Y", "aliases": ["y"]},
            ],
        },
    )
    assert len(payload.entity_types) == 1
    assert payload.entity_types[0].name == "x"
    assert len(payload.known_entities) == 1
