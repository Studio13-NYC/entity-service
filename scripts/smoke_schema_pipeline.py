#!/usr/bin/env python3
"""Smoke-check entity-service with the API already running.

Steps:
  1. ``GET /health`` (or ``/ready``)
  2. ``POST /schema-pipeline/validate`` (offline; always works)
  3. Optional ``POST /schema-pipeline/raw`` when ``--typedb`` (needs ``TYPEDB_*`` on the **server**)

Run from repo root (uses project deps via ``uv run``)::

    # Terminal A — load TypeDB into the **same** process as the API, e.g.:
    uv run --env-file .env fastapi dev app/main.py

    # Terminal B — hit the running API (no TypeDB vars required here):
    uv run python scripts/smoke_schema_pipeline.py

    # Also verify TypeDB-backed raw (server must have TYPEDB_*):
    uv run python scripts/smoke_schema_pipeline.py --typedb

Env:
  ``NER_SERVICE_URL`` — base URL (default ``http://127.0.0.1:8000``).
  ``SMOKE_ENTITY_TYPES`` — comma-separated types for ``/raw`` (default ``musician``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

_VALIDATE_BODY = {
    "typeSchemaDefine": (
        "define\n"
        "attribute name, value string;\n"
        "entity musician, owns name;\n"
    ),
    "assumptions": {
        "entityTypes": ["musician"],
        "nameAttribute": "name",
    },
}


def _raw_assumptions() -> dict:
    raw_types = os.environ.get("SMOKE_ENTITY_TYPES", "musician").strip()
    entity_types = [t.strip() for t in raw_types.split(",") if t.strip()]
    if not entity_types:
        entity_types = ["musician"]
    return {
        "assumptions": {
            "entityTypes": entity_types,
            "nameAttribute": "name",
            "limitPerType": 5,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke entity-service schema pipeline + health.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("NER_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/"),
        help="API base URL (default: NER_SERVICE_URL or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--typedb",
        action="store_true",
        help="Also POST /schema-pipeline/raw (requires TYPEDB_* on the server process)",
    )
    args = parser.parse_args()
    base = args.base_url

    with httpx.Client(timeout=60.0) as client:
        r = client.get(f"{base}/health")
        if r.status_code != 200 or r.json() != {"ok": True}:
            print(f"FAIL: GET /health -> {r.status_code} {r.text!r}", file=sys.stderr)
            return 1
        print("OK: GET /health")

        r = client.get(f"{base}/ready")
        if r.status_code != 200 or r.json() != {"ok": True}:
            print(f"FAIL: GET /ready -> {r.status_code} {r.text!r}", file=sys.stderr)
            return 1
        print("OK: GET /ready")

        r = client.post(f"{base}/schema-pipeline/validate", json=_VALIDATE_BODY)
        if r.status_code != 200:
            print(f"FAIL: POST /schema-pipeline/validate -> {r.status_code} {r.text!r}", file=sys.stderr)
            return 1
        body = r.json()
        if not body.get("ready"):
            print(f"FAIL: validate not ready: {json.dumps(body, indent=2)}", file=sys.stderr)
            return 1
        print('OK: POST /schema-pipeline/validate ("ready": true)')

        if args.typedb:
            r = client.post(f"{base}/schema-pipeline/raw", json=_raw_assumptions())
            if r.status_code == 503:
                detail = r.json().get("detail")
                print(
                    "FAIL: POST /schema-pipeline/raw -> 503 (TypeDB not configured on API process). "
                    f"detail={detail!r}",
                    file=sys.stderr,
                )
                print(
                    "Hint: start FastAPI with TYPEDB_* in **its** environment "
                    "(e.g. `uv run --env-file .env fastapi dev app/main.py`).",
                    file=sys.stderr,
                )
                return 2
            if r.status_code != 200:
                print(f"FAIL: POST /schema-pipeline/raw -> {r.status_code} {r.text!r}", file=sys.stderr)
                return 1
            print("OK: POST /schema-pipeline/raw (200) — schema pipeline + TypeDB reachable from API")
        else:
            print("Skip: /schema-pipeline/raw (pass --typedb to require TypeDB on server)")

    print("schema pipeline smoke: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
