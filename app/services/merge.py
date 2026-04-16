"""Merge alias + model entity candidates (overlap / near-duplicate resolution).

Uses RapidFuzz for soft string similarity when spans overlap with the same label.
This module performs in-memory consolidation only — no database I/O.
"""

from rapidfuzz import fuzz

from app.models import EntityCandidate


def _spans_overlap(a: EntityCandidate, b: EntityCandidate) -> bool:
    return not (a.end <= b.start or a.start >= b.end)


def merge_entity_candidates(entities: list[EntityCandidate]) -> list[EntityCandidate]:
    """Greedy merge: overlapping same-label candidates with similar surface text
    collapse to the higher-confidence span; disjoint spans preserved.
    """
    if not entities:
        return []

    ordered = sorted(
        entities,
        key=lambda e: (e.start, e.end, -e.confidence, -len(e.text)),
    )
    kept: list[EntityCandidate] = []

    for e in ordered:
        replaced = False
        for i, existing in enumerate(kept):
            if existing.label != e.label:
                continue
            if not _spans_overlap(e, existing):
                continue
            ratio = fuzz.ratio(e.text.lower(), existing.text.lower())
            same_surface = e.text == existing.text or ratio >= 88
            if not same_surface:
                continue
            if e.confidence >= existing.confidence:
                kept[i] = e
            replaced = True
            break
        if not replaced:
            kept.append(e)

    return sorted(kept, key=lambda x: (x.start, x.end, x.label, x.text))
