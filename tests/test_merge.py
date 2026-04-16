"""Merge policy for overlapping alias + model candidates."""

from app.models import EntityCandidate
from app.services.merge import merge_entity_candidates


def test_merge_keeps_disjoint_spans() -> None:
    a = EntityCandidate(text="A", label="x", start=0, end=1, confidence=0.9)
    b = EntityCandidate(text="B", label="x", start=5, end=6, confidence=0.8)
    out = merge_entity_candidates([a, b])
    assert len(out) == 2


def test_merge_collapses_overlapping_same_label_same_surface() -> None:
    low = EntityCandidate(text="Matthew Sweet", label="artist", start=0, end=13, confidence=0.5)
    high = EntityCandidate(text="Matthew Sweet", label="artist", start=0, end=13, confidence=0.99)
    out = merge_entity_candidates([low, high])
    assert len(out) == 1
    assert out[0].confidence == 0.99


def test_merge_fuzzy_typos_same_span_prefers_higher_confidence() -> None:
    low = EntityCandidate(text="Mathew Sweet", label="artist", start=0, end=12, confidence=0.5)
    high = EntityCandidate(text="Matthew Sweet", label="artist", start=0, end=12, confidence=0.99)
    out = merge_entity_candidates([low, high])
    assert len(out) == 1
    assert out[0].text == "Matthew Sweet"
