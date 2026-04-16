from typing import Annotated, Any

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
)


class EntityTypePayload(BaseModel):
    """Type-level hints from TS (future constraints / EntityRuler-style labels)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str
    aliases: list[str] = Field(default_factory=list)


def _coerce_entity_types(v: Any) -> list[Any]:
    """Accept `entityTypes` as string ids or `{ name, aliases }` objects (handoff §3.6)."""
    if v is None:
        return []
    if not isinstance(v, list):
        raise TypeError("entityTypes must be a list")
    out: list[Any] = []
    for item in v:
        if isinstance(item, str):
            out.append({"name": item, "aliases": []})
        elif isinstance(item, dict):
            out.append(item)
        elif isinstance(item, EntityTypePayload):
            out.append(item.model_dump())
        else:
            raise TypeError(f"Invalid entityTypes entry: {type(item)}")
    return out


class KnownEntityPayload(BaseModel):
    """One canonical entity plus optional surface strings (from schema / TypeDB)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    label: str
    canonical: str = Field(
        ...,
        validation_alias=AliasChoices("canonical", "canonical_text"),
    )
    aliases: list[str] = Field(default_factory=list)


class EntitySchemaPayload(BaseModel):
    """Schema context from the TS client (or from ``/schema-pipeline/formatted``)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    entity_types: Annotated[
        list[EntityTypePayload],
        BeforeValidator(_coerce_entity_types),
    ] = Field(default_factory=list, alias="entityTypes")
    known_entities: list[KnownEntityPayload] = Field(
        default_factory=list,
        alias="knownEntities",
    )


class ExtractOptions(BaseModel):
    """Optional extraction switches; omitted request.options defaults to aliases on, model off."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    use_aliases: bool = True
    use_model: bool = False
    use_gg_generic_for_unknown_catalog_labels: bool = Field(
        default=False,
        alias="useGgGenericForUnknownCatalogLabels",
        description=(
            "When true (and useTypeDbTypes is false), remap entity labels not present in schema "
            "(entityTypes + knownEntities labels) to gg-generic so narrow labels[] filters still return spans."
        ),
    )


class TypeCandidateItem(BaseModel):
    """A label the pipeline considered (TypeDB define, aliases, model, or generic bucket)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    label: str
    source: str = "pipeline"
    score: float | None = None
    fits_existing_type: bool | None = Field(default=None, alias="fitsExistingType")


class ExtractRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    text: str
    labels: list[str] = Field(default_factory=list)
    options: ExtractOptions | None = None
    entity_schema: EntitySchemaPayload | None = Field(
        default=None,
        alias="schema",
        description="Optional schema: known entities and aliases from the client.",
    )
    use_typedb_types: bool = Field(
        default=False,
        alias="useTypeDbTypes",
        description=(
            "When true, perform read-only TypeDB type-schema fetch on this process to align labels "
            "(requires TYPEDB_* on the FastAPI process)."
        ),
    )


class EntityCandidate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    text: str
    label: str
    start: int
    end: int
    confidence: float
    label_candidates: list[TypeCandidateItem] | None = Field(
        default=None,
        alias="labelCandidates",
        description="Optional per-span type alternatives when TypeDB alignment is enabled.",
    )


class ExtractResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    entities: list[EntityCandidate]
    type_candidates: list[TypeCandidateItem] = Field(
        default_factory=list,
        alias="typeCandidates",
        description="Union of labels considered for this request (TypeDB + schema + model/alias path).",
    )
