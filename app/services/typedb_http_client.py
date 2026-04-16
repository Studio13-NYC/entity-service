"""Minimal TypeDB HTTP API client (read-only) for schema pipeline endpoints."""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, cast
from urllib.parse import quote

import httpx

from app.services.typedb_connection import TypeDbHttpSettings

_LOGGER = logging.getLogger(__name__)


class TypeDbHttpClient:
    def __init__(self, http: httpx.AsyncClient, settings: TypeDbHttpSettings) -> None:
        self._http = http
        self._settings = settings
        self._base = settings.base_url.rstrip("/")
        self._token: str | None = None

    async def _ensure_token(self) -> str:
        if self._token:
            return self._token
        r = await self._http.post(
            f"{self._base}/v1/signin",
            json={"username": self._settings.username, "password": self._settings.password},
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = cast(dict[str, Any], r.json())
        token = data.get("token")
        if not isinstance(token, str):
            raise RuntimeError(f"TypeDB signin: unexpected response: {data!r}")
        self._token = token
        return self._token

    async def _headers(self) -> dict[str, str]:
        t = await self._ensure_token()
        return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}

    async def get_database_type_schema(self, database: str) -> str:
        h = await self._headers()
        r = await self._http.get(
            f"{self._base}/v1/databases/{quote(database, safe='')}/type-schema",
            headers=h,
        )
        r.raise_for_status()
        text = r.text
        raw_bytes = len(text.encode("utf-8", errors="replace"))
        digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        _LOGGER.info(
            "TypeDB type-schema fetched database=%s bytes=%d sha256=%s",
            database,
            raw_bytes,
            digest,
        )
        if os.environ.get("ENTITY_SERVICE_DEBUG_TYPEDB_BODY", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            preview = text if len(text) <= 4000 else text[:4000] + "…(truncated)"
            _LOGGER.warning(
                "ENTITY_SERVICE_DEBUG_TYPEDB_BODY is on — logging type-schema preview (%d chars)",
                len(preview),
            )
            _LOGGER.debug("type-schema preview: %s", preview)
        return text

    async def get_databases(self) -> list[str]:
        h = await self._headers()
        r = await self._http.get(f"{self._base}/v1/databases", headers=h)
        r.raise_for_status()
        data = cast(dict[str, Any], r.json())
        dbs = data.get("databases")
        if not isinstance(dbs, list):
            return []
        names: list[str] = []
        for item in dbs:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
        return names

    async def one_shot_query(
        self,
        *,
        database: str,
        query: str,
        transaction_type: str = "read",
        transaction_timeout_ms: int = 30_000,
        answer_count_limit: int = 50,
        include_instance_types: bool = True,
    ) -> dict[str, Any]:
        h = await self._headers()
        body: dict[str, Any] = {
            "query": query,
            "commit": False,
            "databaseName": database,
            "transactionType": transaction_type,
            "transactionOptions": {"transactionTimeoutMillis": transaction_timeout_ms},
            "queryOptions": {
                "answerCountLimit": answer_count_limit,
                "includeInstanceTypes": include_instance_types,
            },
        }
        q_bytes = query.encode("utf-8", errors="replace")
        q_digest = hashlib.sha256(q_bytes).hexdigest()
        _LOGGER.info(
            "TypeDB one-shot query database=%s answer_limit=%d query_bytes=%d query_sha256=%s",
            database,
            answer_count_limit,
            len(q_bytes),
            q_digest,
        )
        if os.environ.get("ENTITY_SERVICE_DEBUG_TYPEDB_BODY", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            q_preview = query if len(query) <= 2000 else query[:2000] + "…(truncated)"
            _LOGGER.warning(
                "ENTITY_SERVICE_DEBUG_TYPEDB_BODY is on — logging TypeQL preview (%d chars)",
                len(q_preview),
            )
            _LOGGER.debug("TypeQL preview: %s", q_preview)

        r = await self._http.post(f"{self._base}/v1/query", json=body, headers=h)
        if r.status_code >= 400:
            try:
                err = r.json()
            except Exception:
                err = {"message": r.text}
            raise RuntimeError(f"TypeDB query HTTP {r.status_code}: {err}")
        data = cast(dict[str, Any], r.json())
        if isinstance(data, dict) and "err" in data:
            raise RuntimeError(f"TypeDB query error: {data['err']}")
        if isinstance(data, dict) and "ok" in data:
            return cast(dict[str, Any], data["ok"])
        return data
