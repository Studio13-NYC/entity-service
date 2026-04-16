"""TypeQL builder safety (hyphenated MO-style entity labels)."""

from app.services.typeql_builders import assert_safe_typeql_identifier, build_select_entity_with_string_attribute


def test_mo_style_entity_type_allowed_in_select() -> None:
    assert_safe_typeql_identifier("mo-music-artist", "entityType")
    q = build_select_entity_with_string_attribute("mo-music-artist", "name")
    assert "mo-music-artist" in q
    assert "has name" in q
