"""Placeholder GLiNER module and merge wiring."""

import pytest

from app.models import EntityCandidate
from app.services.extractor import extract_entities
from app.services.gliner_extractor import extract_with_model


def test_extract_with_model_returns_empty() -> None:
    assert extract_with_model("anything", None) == []
    assert extract_with_model("x", ["a", "b"]) == []


def test_use_model_true_merges_stubbed_model_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import gliner_extractor

    fake = EntityCandidate(
        text="ModelHit",
        label="stub",
        start=0,
        end=4,
        confidence=0.5,
    )

    def fake_extract(text: str, labels: list[str] | None = None) -> list[EntityCandidate]:
        _ = text, labels
        return [fake]

    monkeypatch.setattr(gliner_extractor, "extract_with_model", fake_extract)
    out = extract_entities("abcd", use_aliases=False, use_model=True)
    assert len(out) == 1
    assert out[0].text == "ModelHit"


def test_use_model_merges_with_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import gliner_extractor

    fake = EntityCandidate(
        text="Extra",
        label="stub",
        start=30,
        end=35,
        confidence=0.4,
    )

    monkeypatch.setattr(
        gliner_extractor,
        "extract_with_model",
        lambda t, labels=None: [fake],
    )
    text = "Girlfriend by Matt Sweet" + " " * 10 + "trail"
    out = extract_entities(text, use_aliases=True, use_model=True)
    labels_found = {e.label for e in out}
    assert "recording" in labels_found
    assert "artist" in labels_found
    assert "stub" in labels_found
