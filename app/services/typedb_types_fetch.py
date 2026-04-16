"""Read-only TypeDB fetch of define schema → entity type labels (for ``useTypeDbTypes`` on ``/extract``)."""

from __future__ import annotations

import httpx

from app.services.typedb_connection import TypeDbHttpSettings
from app.services.typedb_define_parse import parse_entity_type_labels_from_define_schema
from app.services.typedb_http_client import TypeDbHttpClient


async def fetch_parsed_entity_type_labels(settings: TypeDbHttpSettings) -> list[str]:
    """Return entity type labels parsed from the live define type-schema for ``settings.database``."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as http:
        client = TypeDbHttpClient(http, settings)
        dbs = await client.get_databases()
        if settings.database not in dbs:
            known = ", ".join(sorted(dbs)) or "(none)"
            raise ValueError(
                f"database_not_found:{settings.database!r}:known={known}",
            )
        define = await client.get_database_type_schema(settings.database)
        return parse_entity_type_labels_from_define_schema(define)
