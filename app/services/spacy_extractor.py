"""Optional spaCy precision layer (EntityRuler / linking). Stub — no spaCy dependency yet.

Integrate here when the pipeline needs deterministic pattern spans alongside GLiNER.
This service must not perform database I/O.
"""

from app.models import EntityCandidate


def extract_with_spacy_rules(text: str, labels: list[str] | None = None) -> list[EntityCandidate]:
    """Reserved for spaCy ``EntityRuler`` or similar; returns [] until implemented."""
    _ = text, labels
    return []
