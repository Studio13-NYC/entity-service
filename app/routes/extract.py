import logging

import httpx
from fastapi import APIRouter

from app.models import ExtractRequest, ExtractResponse
from app.schema_pipeline_http_errors import (
    CODE_TYPEDB_DATABASE_NOT_FOUND,
    CODE_TYPEDB_HTTP_ERROR,
    CODE_TYPEDB_NOT_CONFIGURED,
    schema_pipeline_error,
)
from app.services.extractor import extract_entities_outcome
from app.services.typedb_connection import load_typedb_http_settings
from app.services.typedb_types_fetch import fetch_parsed_entity_type_labels

router = APIRouter()
_LOG = logging.getLogger("app.routes.extract")


@router.post("/extract", response_model=ExtractResponse, response_model_exclude_none=True)
async def extract(req: ExtractRequest):
    label_filter = req.labels or None
    opts = req.options
    use_aliases = True if opts is None else opts.use_aliases
    use_model = False if opts is None else opts.use_model

    typedb_entity_labels: frozenset[str] | None = None
    if req.use_typedb_types:
        settings = load_typedb_http_settings()
        if settings is None:
            raise schema_pipeline_error(
                503,
                code=CODE_TYPEDB_NOT_CONFIGURED,
                message="TypeDB HTTP is not configured on this server process.",
                hint=(
                    "Set TYPEDB_USERNAME, TYPEDB_DATABASE, and either TYPEDB_CONNECTION_STRING "
                    "or TYPEDB_ADDRESSES on the same OS process as FastAPI, then retry with useTypeDbTypes."
                ),
            )
        try:
            labs = await fetch_parsed_entity_type_labels(settings)
            typedb_entity_labels = frozenset(labs)
        except ValueError as e:
            msg = str(e)
            if msg.startswith("database_not_found:"):
                raise schema_pipeline_error(
                    404,
                    code=CODE_TYPEDB_DATABASE_NOT_FOUND,
                    message=f"Database {settings.database!r} not found on this TypeDB server.",
                    hint=msg.split(":", 2)[-1] if ":" in msg else None,
                ) from e
            raise
        except httpx.HTTPError as e:
            raise schema_pipeline_error(
                502,
                code=CODE_TYPEDB_HTTP_ERROR,
                message=f"TypeDB HTTP error: {e}",
                hint="Check TypeDB reachability, TLS, and credentials.",
            ) from e

    out = extract_entities_outcome(
        req.text,
        label_filter,
        use_aliases=use_aliases,
        use_model=use_model,
        schema=req.entity_schema,
        typedb_entity_labels=typedb_entity_labels,
    )
    _LOG.info(
        "extract_done text_len=%d labels=%s entity_count=%d use_aliases=%s use_model=%s "
        "has_schema=%s use_typedb_types=%s type_candidate_count=%d",
        len(req.text),
        req.labels,
        len(out.entities),
        use_aliases,
        use_model,
        req.entity_schema is not None,
        req.use_typedb_types,
        len(out.type_candidates),
    )
    return ExtractResponse(entities=out.entities, type_candidates=out.type_candidates)
