"""Log every HTTP request with a stable request id, timing, and optional JSON body (verbose phase)."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.request_context import request_id_ctx

_LOG = logging.getLogger("app.request_trace")

_SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
    },
)


def _truthy(name: str, default: bool = True) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _body_max() -> int:
    try:
        return max(256, int(os.environ.get("ENTITY_SERVICE_LOG_BODY_MAX_BYTES", "16384")))
    except ValueError:
        return 16384


def _safe_headers(scope: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for raw_name, raw_val in scope.get("headers") or []:
        name = raw_name.decode("latin-1").lower()
        if name in _SENSITIVE_HEADERS:
            out.append((name, "<redacted>"))
        else:
            try:
                out.append((name, raw_val.decode("utf-8", errors="replace")))
            except Exception:
                out.append((name, "<binary>"))
    return out


def _preview_body(raw: bytes, max_bytes: int) -> str:
    if not raw:
        return ""
    chunk = raw[:max_bytes]
    try:
        text = chunk.decode("utf-8")
    except UnicodeDecodeError:
        return f"<non-utf8 {len(raw)} bytes>"
    if len(raw) > max_bytes:
        text += f"\n… truncated ({len(raw)} bytes total, max_log={max_bytes})"
    if os.environ.get("ENTITY_SERVICE_LOG_BODY_SINGLE_LINE", "").strip().lower() in ("1", "true", "yes"):
        return text.replace("\n", "\\n")
    return text


class RequestTraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = uuid.uuid4().hex[:12]
        token = request_id_ctx.set(rid)

        t0 = time.monotonic()
        method = request.method
        path = request.url.path
        query = request.url.query
        client = request.client.host if request.client else "?"
        scope = request.scope
        headers = _safe_headers(scope)

        log_bodies = _truthy("ENTITY_SERVICE_LOG_REQUEST_BODIES", default=True)
        max_body = _body_max()

        _LOG.info(
            "start %s %s query=%r client=%s headers=%s",
            method,
            path,
            query,
            client,
            headers,
        )

        body = b""
        if method in ("POST", "PUT", "PATCH") and log_bodies:
            body = await request.body()
            if body:
                ct = request.headers.get("content-type", "")
                if "json" in ct.lower() or path.startswith(("/extract", "/schema-pipeline")):
                    preview = _preview_body(body, max_body)
                    _LOG.debug("request_json_body path=%s bytes=%d preview=\n%s", path, len(body), preview)
                else:
                    _LOG.debug(
                        "request_body path=%s bytes=%d content_type=%r (raw preview omitted)",
                        path,
                        len(body),
                        ct,
                    )

            async def receive() -> dict:
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(scope, receive)

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            _LOG.exception(
                "failed request_id=%s %s %s elapsed_ms=%.2f",
                rid,
                method,
                path,
                elapsed_ms,
            )
            raise
        else:
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            _LOG.info(
                "end request_id=%s %s %s status=%s elapsed_ms=%.2f",
                rid,
                method,
                path,
                response.status_code,
                elapsed_ms,
            )
            response.headers["X-Request-Id"] = rid
            return response
        finally:
            request_id_ctx.reset(token)
