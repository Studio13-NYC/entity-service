"""Request / response model parsing (API contract)."""

from app.models import ExtractOptions, ExtractRequest


def test_extract_request_ignores_unknown_top_level_keys() -> None:
    req = ExtractRequest.model_validate(
        {"text": "hello", "clientMetadata": {"version": 2}, "traceId": "abc"},
    )
    assert req.text == "hello"


def test_extract_request_omits_options_by_default() -> None:
    req = ExtractRequest.model_validate({"text": "hello"})
    assert req.text == "hello"
    assert req.labels == []
    assert req.options is None
    assert req.entity_schema is None
    assert req.use_typedb_types is False


def test_extract_request_use_typedb_types_alias() -> None:
    req = ExtractRequest.model_validate({"text": "hello", "useTypeDbTypes": True})
    assert req.use_typedb_types is True


def test_extract_request_options_defaults_when_empty_object() -> None:
    req = ExtractRequest.model_validate({"text": "hello", "options": {}})
    assert req.options is not None
    assert req.options.use_aliases is True
    assert req.options.use_model is False


def test_extract_request_options_partial_overrides() -> None:
    req = ExtractRequest.model_validate(
        {"text": "hello", "options": {"use_aliases": False}},
    )
    assert req.options is not None
    assert req.options.use_aliases is False
    assert req.options.use_model is False
    assert req.options.use_gg_generic_for_unknown_catalog_labels is False


def test_extract_request_options_both_flags() -> None:
    req = ExtractRequest.model_validate(
        {
            "text": "x",
            "options": {"use_aliases": False, "use_model": True},
        },
    )
    assert req.options.use_aliases is False
    assert req.options.use_model is True


def test_extract_options_nullable_on_request() -> None:
    req = ExtractRequest.model_validate({"text": "a", "options": None})
    assert req.options is None


def test_extract_options_model_validate() -> None:
    o = ExtractOptions.model_validate({"use_model": True})
    assert o.use_aliases is True
    assert o.use_model is True
    assert o.use_gg_generic_for_unknown_catalog_labels is False


def test_extract_options_use_gg_generic_catalog_fallback_alias() -> None:
    o = ExtractOptions.model_validate({"useGgGenericForUnknownCatalogLabels": True})
    assert o.use_gg_generic_for_unknown_catalog_labels is True
    assert o.use_aliases is True
    assert o.use_model is False


def test_known_entity_accepts_canonical_text_key() -> None:
    from app.models import KnownEntityPayload

    ke = KnownEntityPayload.model_validate(
        {"label": "artist", "canonical_text": "Matthew Sweet", "aliases": []},
    )
    assert ke.canonical == "Matthew Sweet"


def test_extract_request_schema_camel_case() -> None:
    req = ExtractRequest.model_validate(
        {
            "text": "x",
            "schema": {
                "entityTypes": ["book"],
                "knownEntities": [
                    {"label": "book", "canonical": "X", "aliases": []},
                ],
            },
        },
    )
    assert req.entity_schema is not None
    assert len(req.entity_schema.entity_types) == 1
    assert req.entity_schema.entity_types[0].name == "book"
    assert req.entity_schema.known_entities[0].canonical == "X"


def test_entity_types_object_form() -> None:
    from app.models import EntitySchemaPayload

    payload = EntitySchemaPayload.model_validate(
        {
            "entityTypes": [
                {"name": "artist", "aliases": ["artist", "performer"]},
                {"name": "recording", "aliases": ["track"]},
            ],
            "knownEntities": [],
        },
    )
    assert payload.entity_types[0].name == "artist"
    assert "performer" in payload.entity_types[0].aliases


def test_extract_request_entity_schema_snake_case() -> None:
    req = ExtractRequest.model_validate(
        {
            "text": "a",
            "entity_schema": {
                "entity_types": [],
                "known_entities": [],
            },
        },
    )
    assert req.entity_schema is not None
    assert req.entity_schema.known_entities == []
