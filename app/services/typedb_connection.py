"""Resolve TypeDB HTTP settings from environment (mirrors ``src/typedb/env.ts`` + connection string)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class TypeDbHttpSettings:
    base_url: str
    username: str
    password: str
    database: str


def _parse_typedb_connection_string(raw: str) -> dict[str, Any] | None:
    s = raw.strip()
    if not s.lower().startswith("typedb://"):
        return None
    without = s[len("typedb://") :]
    user: str | None = None
    password: str | None = None
    host_part = without
    at_idx = without.find("@")
    if at_idx != -1:
        auth = without[:at_idx]
        host_part = without[at_idx + 1 :]
        colon = auth.find(":")
        if colon >= 0:
            user = auth[:colon].strip() or None
            password = auth[colon + 1 :].strip() or None
        else:
            user = auth.strip() or None
    url_candidate = (
        host_part if host_part.startswith(("http://", "https://")) else f"https://{host_part}"
    )
    parsed = urlparse(url_candidate)
    if not parsed.scheme or not parsed.netloc:
        return None
    base = f"{parsed.scheme}://{parsed.netloc}"
    q = parsed.query
    db_from_query: str | None = None
    if q:
        for part in q.split("&"):
            if part.startswith("name="):
                db_from_query = unquote(part[5:].strip()) or None
                break
    return {"addresses": [base], "username": user, "password": password, "databaseFromQuery": db_from_query}


def load_typedb_http_settings() -> TypeDbHttpSettings | None:
    """Return settings when the server can perform TypeDB HTTP reads; otherwise ``None``."""
    conn = os.environ.get("TYPEDB_CONNECTION_STRING", "").strip()
    parsed = _parse_typedb_connection_string(conn) if conn else None

    raw_addresses = os.environ.get("TYPEDB_ADDRESSES", "").strip()
    if raw_addresses:
        addresses = [a.strip() for a in raw_addresses.split(",") if a.strip()]
    elif parsed and parsed.get("addresses"):
        addresses = list(parsed["addresses"])
    else:
        addresses = ["http://localhost:1729"]

    base = addresses[0].rstrip("/")
    if not base.startswith("http://") and not base.startswith("https://"):
        base = f"http://{base}"

    username = (os.environ.get("TYPEDB_USERNAME") or "").strip() or (parsed or {}).get("username") or ""
    password = (os.environ.get("TYPEDB_PASSWORD") or "").strip() or (parsed or {}).get("password") or ""
    database = (
        (os.environ.get("TYPEDB_DATABASE") or "").strip()
        or (parsed or {}).get("databaseFromQuery")
        or ""
    ).strip()

    if not username or not database:
        return None
    return TypeDbHttpSettings(base_url=base, username=username, password=password, database=database)
