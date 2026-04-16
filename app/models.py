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

    model_config = ConfigDict(populate_by_name=True)

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

    model_config = ConfigDict(populate_by_name=True)

    label: str
    canonical: str = Field(
        ...,
        validation_alias=AliasChoices("canonical", "canonical_text"),
    )
    aliases: list[str] = Field(default_factory=list)


class EntitySchemaPayload(BaseModel):
    """Schema context from the TS client. No database access in Python — TS sends slices."""

    model_config = ConfigDict(populate_by_name=True)

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

    use_aliases: bool = True
    use_model: bool = False


class ExtractRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str
    labels: list[str] = Field(default_factory=list)
    options: ExtractOptions | None = None
    entity_schema: EntitySchemaPayload | None = Field(
        default=None,
        alias="schema",
        description="Optional schema: known entities and aliases from the client.",
    )


class EntityCandidate(BaseModel):
    text: str
    label: str
    start: int
    end: int
    confidence: float


class ExtractResponse(BaseModel):
    entities: list[EntityCandidate]
