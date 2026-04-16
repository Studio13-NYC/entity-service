"""Tests for alias matching, canonicalization metadata, and overlap deduplication."""

import pytest

from app.services import alias_matcher
from app.services.alias_matcher import find_alias_matches


def test_empty_input_returns_no_matches() -> None:
    assert find_alias_matches("") == []


def test_exact_alias_match_recording() -> None:
    matches = find_alias_matches("Girlfriend")
    assert len(matches) == 1
    m = matches[0]
    assert m.canonical_text == "Girlfriend"
    assert m.label == "recording"
    assert m.alias_text == "Girlfriend"
    assert m.start == 0
    assert m.end == len("Girlfriend")


def test_fuzzy_alias_matt_to_matthew() -> None:
    matches = find_alias_matches("Matt Sweet")
    assert len(matches) == 1
    m = matches[0]
    assert m.canonical_text == "Matthew Sweet"
    assert m.label == "artist"
    assert m.alias_text == "Matt Sweet"


def test_misspelling_mathew_to_matthew() -> None:
    matches = find_alias_matches("Mathew Sweet")
    assert len(matches) == 1
    m = matches[0]
    assert m.canonical_text == "Matthew Sweet"
    assert m.alias_text == "Mathew Sweet"


def test_combined_example_spans_and_canonical_text() -> None:
    text = "Girlfriend by Matt Sweet"
    matches = find_alias_matches(text)
    by_label = {m.label: m for m in matches}
    rec = by_label["recording"]
    assert rec.canonical_text == "Girlfriend"
    assert text[rec.start : rec.end] == "Girlfriend"
    art = by_label["artist"]
    assert art.canonical_text == "Matthew Sweet"
    assert text[art.start : art.end] == "Matt Sweet"


def test_overlap_same_label_keeps_longer_at_shared_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        alias_matcher,
        "ALIASES",
        [
            ("recording", "Canon", "a"),
            ("recording", "Canon", "ab"),
        ],
    )
    matches = find_alias_matches("ab")
    assert len(matches) == 1
    assert matches[0].alias_text == "ab"
    assert matches[0].canonical_text == "Canon"


def test_overlap_same_label_prefers_earlier_start_when_both_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        alias_matcher,
        "ALIASES",
        [
            ("recording", "Canon", "ab"),
            ("recording", "Canon", "bc"),
        ],
    )
    matches = find_alias_matches("abc")
    assert len(matches) == 1
    assert matches[0].alias_text == "ab"


def test_overlap_different_labels_keeps_both(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        alias_matcher,
        "ALIASES",
        [
            ("recording", "R", "ab"),
            ("artist", "A", "bc"),
        ],
    )
    matches = find_alias_matches("abc")
    assert len(matches) == 2
    labels = {m.label for m in matches}
    assert labels == {"recording", "artist"}
