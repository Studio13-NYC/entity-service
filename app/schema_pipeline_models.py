"""Request/response models for the TypeDB schema resolution pipeline (raw → validate → formatted)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import KnownEntityPayload, TypeCandidateItem


class ErAssumptions(BaseModel):
    """What the entity recognizer (or upstream app) assumes about TypeDB types for this resolution pass."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    entity_types: list[str] = Field(alias="entityTypes")
    name_attribute: str = Field(default="name", alias="nameAttribute")
    # Bounds enforced in ``app/services/schema_pipeline.py`` when calling TypeDB (not at JSON parse).
    limit_per_type: int = Field(default=50, alias="limitPerType")


class SchemaPipelineRawRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    assumptions: ErAssumptions


class PerTypeRawSegment(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    entity_type: str = Field(alias="entityType")
    declared_in_define_schema: bool = Field(alias="declaredInDefineSchema")
    owns_string_attributes: list[str] = Field(default_factory=list, alias="ownsStringAttributes")
    name_attribute_declared: bool = Field(alias="nameAttributeDeclared")
    sample_query_error: str | None = Field(default=None, alias="sampleQueryError")
    sample_answers: list[Any] = Field(default_factory=list, alias="sampleAnswers")


class GenericEntityPayload(BaseModel):
    """One sampled or inferred row for GrooveGraph discovery (``/schema-pipeline/raw``)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    entity_type: str = Field(alias="entityType")
    name_attribute: str = Field(alias="nameAttribute")
    surface: str | None = None
    source: str = "typedb_sample"
    sample_index: int = Field(default=0, alias="sampleIndex")


class SchemaPipelineRawResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type_schema_define: str = Field(alias="typeSchemaDefine")
    parsed_entity_type_labels: list[str] = Field(alias="parsedEntityTypeLabels")
    assumptions: ErAssumptions
    per_type: list[PerTypeRawSegment] = Field(alias="perType")
    generic_entities: list[GenericEntityPayload] = Field(default_factory=list, alias="genericEntities")
    type_candidates: list[TypeCandidateItem] = Field(default_factory=list, alias="typeCandidates")


class SchemaPipelineIssue(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    code: str
    message: str
    entity_type: str | None = Field(default=None, alias="entityType")


class SchemaPipelineValidateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type_schema_define: str = Field(alias="typeSchemaDefine")
    assumptions: ErAssumptions


class SchemaPipelineValidateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    ready: bool
    issues: list[SchemaPipelineIssue] = Field(default_factory=list)


class SchemaPipelineFormattedRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    assumptions: ErAssumptions
    skip_ontology_precheck: bool = Field(default=False, alias="skipOntologyPrecheck")


class SchemaPipelineFormattedResponse(BaseModel):
    """Same shape as the optional ``schema`` field on ``POST /extract``."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # Wire format stays a string list (GrooveGraph / older clients); ``POST /extract`` also accepts objects.
    entity_types: list[str] = Field(default_factory=list, alias="entityTypes")
    known_entities: list[KnownEntityPayload] = Field(default_factory=list, alias="knownEntities")
