from app.services.spacy_extractor import extract_with_spacy_rules


def test_spacy_stub_returns_empty() -> None:
    assert extract_with_spacy_rules("any text", None) == []
