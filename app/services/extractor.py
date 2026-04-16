from app.models import EntityCandidate, EntitySchemaPayload
from app.services import gliner_extractor
from app.services.alias_matcher import find_alias_matches
from app.services.merge import merge_entity_candidates
from app.services.schema_aliases import alias_rows_from_schema


def extract_entities(
    text: str,
    labels: list[str] | None = None,
    *,
    use_aliases: bool = True,
    use_model: bool = False,
    schema: EntitySchemaPayload | None = None,
) -> list[EntityCandidate]:
    entities: list[EntityCandidate] = []

    if use_aliases:
        extra = alias_rows_from_schema(schema)
        alias_matches = find_alias_matches(text, extra_aliases=extra or None)
        for match in alias_matches:
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
        entities.extend(gliner_extractor.extract_with_model(text, labels))

    entities = merge_entity_candidates(entities)

    if labels:
        entities = [entity for entity in entities if entity.label in labels]

    return _sort_entities(entities)


def _sort_entities(entities: list[EntityCandidate]) -> list[EntityCandidate]:
    return sorted(
        entities,
        key=lambda entity: (entity.start, entity.end, entity.label, entity.text),
    )
