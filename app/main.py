import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.logging_setup import configure_app_logging
from app.middleware.request_trace import RequestTraceMiddleware
from app.routes import extract, health, schema_pipeline
from app.services.typedb_connection import load_typedb_http_settings

configure_app_logging()

_LOG = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Log once at startup when TypeDB-backed routes cannot reach a database (operator triage)."""
    if load_typedb_http_settings() is None:
        _LOG.warning(
            "TypeDB HTTP is not configured in this process (missing TYPEDB_USERNAME / TYPEDB_DATABASE "
            "and connection settings). POST /schema-pipeline/raw and /schema-pipeline/formatted will "
            "return 503 with detail.code typedb_not_configured_on_entity_service until the **same** OS "
            "process that runs FastAPI has credentials — not only in another app (e.g. GrooveGraph) "
            ".env. See docs/ENTITY_SERVICE_PUNCH_LIST.md and docs/USER_AND_AGENT_GUIDE.md.",
        )
    yield


app = FastAPI(title="NER Services", lifespan=lifespan)
app.add_middleware(RequestTraceMiddleware)

app.include_router(health.router)
app.include_router(extract.router)
app.include_router(schema_pipeline.router)
