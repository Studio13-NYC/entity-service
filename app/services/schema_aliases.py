"""Build alias rows from client-supplied schema (TypeDB / TS layer)."""

from collections.abc import Sequence

from app.config.aliases import AliasRow
from app.models import EntitySchemaPayload, KnownEntityPayload


def alias_rows_from_schema(schema: EntitySchemaPayload | None) -> list[AliasRow]:
    """Turn known entities into (label, canonical, surface) rows merged with file config."""
    if schema is None:
        return []

    rows: list[AliasRow] = []
    for entity in schema.known_entities:
        rows.extend(_rows_for_known_entity(entity))
    return _dedupe_rows(rows)


def _rows_for_known_entity(entity: KnownEntityPayload) -> list[AliasRow]:
    label = entity.label
    canonical = entity.canonical
    out: list[AliasRow] = [(label, canonical, canonical)]
    for surface in entity.aliases:
        if surface:
            out.append((label, canonical, surface))
    return out


def _dedupe_rows(rows: Sequence[AliasRow]) -> list[AliasRow]:
    seen: set[AliasRow] = set()
    unique: list[AliasRow] = []
    for row in rows:
        if row not in seen:
            seen.add(row)
            unique.append(row)
    return unique
