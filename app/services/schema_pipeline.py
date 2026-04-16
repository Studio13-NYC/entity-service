"""TypeDB schema pipeline: raw define + samples → validate types → formatted ``schema`` for ``/extract``."""

from __future__ import annotations

import logging
from typing import Any, cast

from app.models import KnownEntityPayload, TypeCandidateItem
from app.schema_pipeline_models import (
    ErAssumptions,
    GenericEntityPayload,
    PerTypeRawSegment,
    SchemaPipelineFormattedResponse,
    SchemaPipelineIssue,
    SchemaPipelineRawResponse,
    SchemaPipelineValidateResponse,
)
from app.services.typeql_builders import build_select_entity_with_string_attribute
from app.services.typedb_define_parse import (
    parse_entity_type_labels_from_define_schema,
    parse_string_attribute_types_owned_by_entity_from_define_schema,
)
from app.services.typedb_http_client import TypeDbHttpClient

# TypeDB ``answerCountLimit`` — clamp here because request models do not hard-cap ``limitPerType``.
_MAX_ANSWER_LIMIT = 50_000
# When ``assumptions.entityTypes`` is empty, auto-sample up to this many types from the define schema.
_MAX_RAW_AUTOSAMPLE_TYPES = 30

_PL = logging.getLogger("app.pipeline")


def _clamp_answer_limit(n: int) -> int:
    if n < 1:
        return 1
    return min(n, _MAX_ANSWER_LIMIT)


def _build_generic_entities(
    per_type: list[PerTypeRawSegment],
    name_attribute: str,
) -> list[GenericEntityPayload]:
    out: list[GenericEntityPayload] = []
    for seg in per_type:
        for idx, ans in enumerate(seg.sample_answers):
            surface: str | None = None
            if isinstance(ans, dict):
                data = ans.get("data")
                if isinstance(data, dict):
                    surface = _parse_string_attribute_row(data, name_attribute)
            out.append(
                GenericEntityPayload(
                    entity_type=seg.entity_type,
                    name_attribute=name_attribute,
                    surface=surface,
                    sample_index=idx,
                ),
            )
    return out


def _parse_string_attribute_row(row: dict[str, Any], expected_attr: str) -> str | None:
    """Return attribute string value when row matches typed entity + string attribute."""
    for c in row.values():
        if not isinstance(c, dict):
            continue
        if c.get("kind") != "attribute":
            continue
        t = c.get("type")
        if not isinstance(t, dict):
            continue
        if (
            t.get("kind") == "attributeType"
            and t.get("valueType") == "string"
            and t.get("label") == expected_attr
        ):
            val = c.get("value")
            return None if val is None else str(val)
    return None


async def run_pipeline_raw(
    client: TypeDbHttpClient,
    database: str,
    assumptions: ErAssumptions,
) -> SchemaPipelineRawResponse:
    define = await client.get_database_type_schema(database)
    parsed_labels = parse_entity_type_labels_from_define_schema(define)
    label_set = set(parsed_labels)
    per_type: list[PerTypeRawSegment] = []

    effective_types = (
        list(assumptions.entity_types)
        if assumptions.entity_types
        else list(parsed_labels[:_MAX_RAW_AUTOSAMPLE_TYPES])
    )

    for et in effective_types:
        declared = et in label_set
        owns: list[str] = []
        name_ok = False
        err: str | None = None
        sample: list[Any] = []
        if declared:
            try:
                owns = parse_string_attribute_types_owned_by_entity_from_define_schema(define, et)
            except ValueError as e:
                err = str(e)
                owns = []
            name_ok = assumptions.name_attribute in owns
            if name_ok:
                try:
                    q = build_select_entity_with_string_attribute(et, assumptions.name_attribute)
                    raw = await client.one_shot_query(
                        database=database,
                        query=q,
                        answer_count_limit=_clamp_answer_limit(assumptions.limit_per_type),
                    )
                    sample = cast(list[Any], raw.get("answers") or [])
                except Exception as e:  # noqa: BLE001 — surface to caller
                    err = str(e)
            elif err is None:
                err = (
                    f"nameAttribute {assumptions.name_attribute!r} is not a declared string "
                    f"ownership on entity type {et!r}; owns: {owns!r}"
                )
        else:
            err = f"entity type {et!r} is not declared in the define type schema"

        per_type.append(
            PerTypeRawSegment(
                entity_type=et,
                declared_in_define_schema=declared,
                owns_string_attributes=owns,
                name_attribute_declared=name_ok,
                sample_query_error=err,
                sample_answers=sample,
            ),
        )

    generic_entities = _build_generic_entities(per_type, assumptions.name_attribute)
    type_candidates = [
        TypeCandidateItem(label=lab, source="typedb_define") for lab in sorted(parsed_labels)
    ]

    return SchemaPipelineRawResponse(
        type_schema_define=define,
        parsed_entity_type_labels=parsed_labels,
        assumptions=assumptions,
        per_type=per_type,
        generic_entities=generic_entities,
        type_candidates=type_candidates,
    )


def run_pipeline_validate(define: str, assumptions: ErAssumptions) -> SchemaPipelineValidateResponse:
    labels = set(parse_entity_type_labels_from_define_schema(define))
    issues: list[SchemaPipelineIssue] = []

    for et in assumptions.entity_types:
        if et not in labels:
            issues.append(
                SchemaPipelineIssue(
                    code="unknown_entity_type",
                    message=f"Entity type {et!r} does not appear in the define schema.",
                    entity_type=et,
                ),
            )
            continue
        try:
            owns = parse_string_attribute_types_owned_by_entity_from_define_schema(define, et)
        except ValueError as e:
            issues.append(
                SchemaPipelineIssue(
                    code="invalid_entity_type_label",
                    message=str(e),
                    entity_type=et,
                ),
            )
            continue
        if assumptions.name_attribute not in owns:
            issues.append(
                SchemaPipelineIssue(
                    code="missing_string_attribute",
                    message=(
                        f"Entity type {et!r} does not own string attribute "
                        f"{assumptions.name_attribute!r}. Declared string owns: {owns!r}"
                    ),
                    entity_type=et,
                ),
            )

    return SchemaPipelineValidateResponse(ready=len(issues) == 0, issues=issues)


async def run_pipeline_formatted(
    client: TypeDbHttpClient,
    database: str,
    assumptions: ErAssumptions,
    *,
    skip_ontology_precheck: bool = False,
) -> SchemaPipelineFormattedResponse:
    define = await client.get_database_type_schema(database)
    if not skip_ontology_precheck:
        v = run_pipeline_validate(define, assumptions)
        if not v.ready:
            msgs = "; ".join(i.message for i in v.issues)
            raise ValueError(f"Ontology not ready for formatted fetch: {msgs}")

    known: list[KnownEntityPayload] = []
    for et in assumptions.entity_types:
        q = build_select_entity_with_string_attribute(et, assumptions.name_attribute)
        raw = await client.one_shot_query(
            database=database,
            query=q,
            answer_count_limit=_clamp_answer_limit(assumptions.limit_per_type),
        )
        for ans in cast(list[Any], raw.get("answers") or []):
            if not isinstance(ans, dict):
                continue
            data = ans.get("data")
            if not isinstance(data, dict):
                continue
            val = _parse_string_attribute_row(data, assumptions.name_attribute)
            if val is None:
                continue
            known.append(KnownEntityPayload(label=et, canonical=val, aliases=[]))

    if not known:
        _PL.warning(
            "schema_pipeline_formatted_empty_known database=%s entity_types=%s skip_ontology_precheck=%s",
            database,
            assumptions.entity_types,
            skip_ontology_precheck,
        )

    return SchemaPipelineFormattedResponse(
        entity_types=list(assumptions.entity_types),
        known_entities=known,
    )
