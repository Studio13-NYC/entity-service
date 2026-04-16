from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.models import EntityCandidate, EntitySchemaPayload, TypeCandidateItem
from app.services import gliner_extractor
from app.services.alias_matcher import find_alias_matches
from app.services.merge import merge_entity_candidates
from app.services.schema_aliases import alias_rows_from_schema

_PL = logging.getLogger("app.pipeline")

_GENERIC_LABEL_SAFE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def _sanitize_generic_suffix(label: str) -> str:
    s = _GENERIC_LABEL_SAFE.sub("_", label.strip())
    return s or "unknown"


@dataclass(frozen=True)
class ExtractEntitiesOutcome:
    entities: list[EntityCandidate]
    type_candidates: list[TypeCandidateItem]


def _collect_schema_labels(schema: EntitySchemaPayload | None) -> set[str]:
    out: set[str] = set()
    if schema is None:
        return out
    for ke in schema.known_entities:
        out.add(ke.label)
    for et in schema.entity_types:
        out.add(et.name)
    return out


def _build_global_type_candidates(
    *,
    pipeline_labels: set[str],
    typedb_labels: frozenset[str] | None,
) -> list[TypeCandidateItem]:
    items: list[TypeCandidateItem] = []
    seen: set[str] = set()
    if typedb_labels:
        for lab in sorted(typedb_labels):
            if lab not in seen:
                seen.add(lab)
                items.append(TypeCandidateItem(label=lab, source="typedb_define"))
    for lab in sorted(pipeline_labels):
        if lab not in seen:
            seen.add(lab)
            fits = typedb_labels is not None and lab in typedb_labels
            items.append(
                TypeCandidateItem(
                    label=lab,
                    source="pipeline",
                    fits_existing_type=fits if typedb_labels is not None else None,
                ),
            )
    return items


def _apply_typedb_label_alignment(
    entities: list[EntityCandidate],
    typedb_labels: frozenset[str],
) -> list[EntityCandidate]:
    out: list[EntityCandidate] = []
    for e in entities:
        fits = e.label in typedb_labels
        if fits:
            new_label = e.label
        else:
            new_label = f"generic:{_sanitize_generic_suffix(e.label)}"
        label_candidates = [
            TypeCandidateItem(
                label=e.label,
                source="extractor",
                score=e.confidence,
                fits_existing_type=fits,
            ),
        ]
        if not fits:
            label_candidates.append(
                TypeCandidateItem(
                    label=new_label,
                    source="generic_bucket",
                    score=e.confidence,
                    fits_existing_type=False,
                ),
            )
        out.append(
            EntityCandidate(
                text=e.text,
                label=new_label,
                start=e.start,
                end=e.end,
                confidence=e.confidence,
                label_candidates=label_candidates,
            ),
        )
    return out


def extract_entities_outcome(
    text: str,
    labels: list[str] | None = None,
    *,
    use_aliases: bool = True,
    use_model: bool = False,
    schema: EntitySchemaPayload | None = None,
    typedb_entity_labels: frozenset[str] | None = None,
) -> ExtractEntitiesOutcome:
    entities: list[EntityCandidate] = []
    candidate_labels: set[str] = _collect_schema_labels(schema)

    if use_aliases:
        extra = alias_rows_from_schema(schema)
        alias_matches = find_alias_matches(text, extra_aliases=extra or None)
        for match in alias_matches:
            candidate_labels.add(match.label)
            entities.append(
                EntityCandidate(
                    text=match.canonical_text,
                    label=match.label,
                    start=match.start,
                    end=match.end,
                    confidence=match.confidence,
                ),
            )

    if use_model:
        for ent in gliner_extractor.extract_with_model(text, labels):
            candidate_labels.add(ent.label)
            entities.append(ent)

    entities = merge_entity_candidates(entities)
    for ent in entities:
        candidate_labels.add(ent.label)

    if not entities:
        _PL.info(
            "extract_empty_after_merge text_len=%d use_aliases=%s use_model=%s has_schema=%s "
            "typedb_align=%s label_filter=%s",
            len(text),
            use_aliases,
            use_model,
            schema is not None,
            typedb_entity_labels is not None,
            labels,
        )

    if typedb_entity_labels is not None:
        entities = _apply_typedb_label_alignment(entities, typedb_entity_labels)

    if labels:
        before = len(entities)
        entities = [entity for entity in entities if entity.label in labels]
        if before and not entities:
            _PL.info(
                "extract_empty_after_label_filter text_len=%d labels=%s typedb_align=%s",
                len(text),
                labels,
                typedb_entity_labels is not None,
            )

    type_candidates = _build_global_type_candidates(
        pipeline_labels=candidate_labels,
        typedb_labels=typedb_entity_labels,
    )

    return ExtractEntitiesOutcome(_sort_entities(entities), type_candidates)


def extract_entities(
    text: str,
    labels: list[str] | None = None,
    *,
    use_aliases: bool = True,
    use_model: bool = False,
    schema: EntitySchemaPayload | None = None,
    typedb_entity_labels: frozenset[str] | None = None,
) -> list[EntityCandidate]:
    """Return sorted ``EntityCandidate`` rows (stable tests); see ``extract_entities_outcome`` for metadata."""
    return extract_entities_outcome(
        text,
        labels,
        use_aliases=use_aliases,
        use_model=use_model,
        schema=schema,
        typedb_entity_labels=typedb_entity_labels,
    ).entities


def _sort_entities(entities: list[EntityCandidate]) -> list[EntityCandidate]:
    return sorted(
        entities,
        key=lambda entity: (entity.start, entity.end, entity.label, entity.text),
    )
