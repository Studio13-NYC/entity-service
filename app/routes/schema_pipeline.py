"""HTTP surface for TypeDB schema resolution: raw → validate → formatted ``schema``."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends

from app.schema_pipeline_http_errors import (
    CODE_SCHEMA_PIPELINE_VALIDATION,
    CODE_TYPEDB_DATABASE_NOT_FOUND,
    CODE_TYPEDB_HTTP_ERROR,
    CODE_TYPEDB_NOT_CONFIGURED,
    schema_pipeline_error,
)
from app.schema_pipeline_models import (
    SchemaPipelineFormattedRequest,
    SchemaPipelineFormattedResponse,
    SchemaPipelineRawRequest,
    SchemaPipelineRawResponse,
    SchemaPipelineValidateRequest,
    SchemaPipelineValidateResponse,
)
from app.services.schema_pipeline import (
    run_pipeline_formatted,
    run_pipeline_raw,
    run_pipeline_validate,
)
from app.services.typedb_connection import TypeDbHttpSettings, load_typedb_http_settings
from app.services.typedb_http_client import TypeDbHttpClient

router = APIRouter(prefix="/schema-pipeline", tags=["schema-pipeline"])


def _require_typedb_settings() -> TypeDbHttpSettings:
    s = load_typedb_http_settings()
    if s is None:
        raise schema_pipeline_error(
            503,
            code=CODE_TYPEDB_NOT_CONFIGURED,
            message="TypeDB HTTP is not configured on this server process.",
            hint=(
                "Set TYPEDB_USERNAME, TYPEDB_DATABASE, and either TYPEDB_CONNECTION_STRING "
                "or TYPEDB_ADDRESSES (and TYPEDB_PASSWORD when required) in the environment of "
                "the same OS process that runs FastAPI — not only in another app’s .env."
            ),
        )
    return s


@router.post("/raw", response_model=SchemaPipelineRawResponse, response_model_by_alias=True)
async def post_schema_pipeline_raw(
    body: SchemaPipelineRawRequest,
    settings: TypeDbHttpSettings = Depends(_require_typedb_settings),
) -> SchemaPipelineRawResponse:
    """Fetch define type schema plus bounded sample rows per assumed entity type (ER assumptions)."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as http:
        client = TypeDbHttpClient(http, settings)
        dbs = await client.get_databases()
        if settings.database not in dbs:
            raise schema_pipeline_error(
                404,
                code=CODE_TYPEDB_DATABASE_NOT_FOUND,
                message=f"Database {settings.database!r} not found on this TypeDB server.",
                hint=f"Known databases: {', '.join(sorted(dbs)) or '(none)'}",
            )
        try:
            return await run_pipeline_raw(client, settings.database, body.assumptions)
        except httpx.HTTPError as e:
            raise schema_pipeline_error(
                502,
                code=CODE_TYPEDB_HTTP_ERROR,
                message=f"TypeDB HTTP error: {e}",
                hint="Check TypeDB reachability, TLS, and credentials; compare with a working TS driver config.",
            ) from e


@router.post(
    "/validate",
    response_model=SchemaPipelineValidateResponse,
    response_model_by_alias=True,
)
def post_schema_pipeline_validate(body: SchemaPipelineValidateRequest) -> SchemaPipelineValidateResponse:
    """Examine a previously retrieved ``typeSchemaDefine`` string: entity types and string ``owns``."""
    return run_pipeline_validate(body.type_schema_define, body.assumptions)


@router.post(
    "/formatted",
    response_model=SchemaPipelineFormattedResponse,
    response_model_by_alias=True,
)
async def post_schema_pipeline_formatted(
    body: SchemaPipelineFormattedRequest,
    settings: TypeDbHttpSettings = Depends(_require_typedb_settings),
) -> SchemaPipelineFormattedResponse:
    """After types are valid, fetch normalized ``schema`` suitable for ``POST /extract``."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as http:
        client = TypeDbHttpClient(http, settings)
        dbs = await client.get_databases()
        if settings.database not in dbs:
            raise schema_pipeline_error(
                404,
                code=CODE_TYPEDB_DATABASE_NOT_FOUND,
                message=f"Database {settings.database!r} not found on this TypeDB server.",
                hint=f"Known databases: {', '.join(sorted(dbs)) or '(none)'}",
            )
        try:
            return await run_pipeline_formatted(
                client,
                settings.database,
                body.assumptions,
                skip_ontology_precheck=body.skip_ontology_precheck,
            )
        except ValueError as e:
            raise schema_pipeline_error(
                400,
                code=CODE_SCHEMA_PIPELINE_VALIDATION,
                message=str(e),
                hint="Call POST /schema-pipeline/validate with the same typeSchemaDefine and assumptions.",
            ) from e
        except httpx.HTTPError as e:
            raise schema_pipeline_error(
                502,
                code=CODE_TYPEDB_HTTP_ERROR,
                message=f"TypeDB HTTP error: {e}",
                hint="Check TypeDB reachability, TLS, and credentials; compare with a working TS driver config.",
            ) from e
