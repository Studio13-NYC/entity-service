"""Stable, machine-readable HTTP errors for ``/schema-pipeline/*`` (GrooveGraph / ops)."""

from __future__ import annotations

from fastapi import HTTPException

# Stable codes — grep logs and tests for these strings (see docs/ENTITY_SERVICE_PUNCH_LIST.md).
CODE_TYPEDB_NOT_CONFIGURED = "typedb_not_configured_on_entity_service"
CODE_TYPEDB_DATABASE_NOT_FOUND = "typedb_database_not_found"
CODE_TYPEDB_HTTP_ERROR = "typedb_http_error"
CODE_SCHEMA_PIPELINE_VALIDATION = "schema_pipeline_validation_failed"


def schema_pipeline_error(
    status_code: int,
    *,
    code: str,
    message: str,
    hint: str | None = None,
) -> HTTPException:
    """Return a FastAPI HTTPException whose JSON ``detail`` is always a small object."""
    detail: dict[str, str] = {"code": code, "message": message}
    if hint:
        detail["hint"] = hint
    return HTTPException(status_code=status_code, detail=detail)
