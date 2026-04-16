"""Tests for extraction pipeline: sorting, label filter, empty input."""

import pytest

from app.models import EntityCandidate
from app.services.extractor import extract_entities


def test_empty_input_returns_no_entities() -> None:
    assert extract_entities("") == []
    assert extract_entities("", labels=None) == []
    assert extract_entities("", labels=[]) == []


def test_irrelevant_text_returns_no_entities() -> None:
    assert extract_entities("nothing recognizable here xyz") == []


def test_girlfriend_example_sorted_by_span() -> None:
    entities = extract_entities("Girlfriend by Matt Sweet")
    assert [e.label for e in entities] == ["recording", "artist"]
    assert entities[0].text == "Girlfriend"
    assert entities[0].start == 0
    assert entities[1].text == "Matthew Sweet"
    assert entities[1].label == "artist"


def test_label_filter_keeps_only_requested_labels() -> None:
    entities = extract_entities("Girlfriend by Matt Sweet", labels=["artist"])
    assert len(entities) == 1
    assert entities[0].label == "artist"
    assert entities[0].text == "Matthew Sweet"


def test_label_filter_multiple_labels() -> None:
    entities = extract_entities(
        "Girlfriend by Matt Sweet",
        labels=["artist", "recording"],
    )
    assert len(entities) == 2


def test_no_label_filter_returns_all() -> None:
    entities_none = extract_entities("Girlfriend by Matt Sweet", labels=None)
    entities_empty = extract_entities("Girlfriend by Matt Sweet", labels=[])
    assert entities_none == entities_empty
    assert len(entities_none) == 2


def test_entities_are_sorted_even_when_matches_reverse_order() -> None:
    """Matcher order should not affect final order (start, end, label, text)."""

    later_first = extract_entities("Matt Sweet then Girlfriend")
    assert [e.text for e in later_first] == ["Matthew Sweet", "Girlfriend"]


def test_label_filter_excludes_unknown_label() -> None:
    entities = extract_entities("Girlfriend by Matt Sweet", labels=["work"])
    assert entities == []


def test_entity_candidate_shape() -> None:
    entities = extract_entities("Matt Sweet")
    assert len(entities) == 1
    e = entities[0]
    assert isinstance(e, EntityCandidate)
    assert set(e.model_dump(exclude_none=True).keys()) == {
        "text",
        "label",
        "start",
        "end",
        "confidence",
    }


def test_use_aliases_false_skips_alias_matches() -> None:
    assert extract_entities("Matt Sweet", use_aliases=False) == []


def test_use_model_true_without_integration_still_returns_aliases() -> None:
    """Model path is a no-op until GLiNER is wired; aliases unchanged when enabled."""
    entities = extract_entities(
        "Matt Sweet",
        use_aliases=True,
        use_model=True,
    )
    assert len(entities) == 1
    assert entities[0].text == "Matthew Sweet"


def test_use_aliases_false_and_use_model_true_returns_empty() -> None:
    assert extract_entities("Matt Sweet", use_aliases=False, use_model=True) == []
