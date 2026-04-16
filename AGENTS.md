# AGENTS.md — entity-service

## Read this first (canonical)

| Doc | Use |
|-----|-----|
| [`docs/USER_AND_AGENT_GUIDE.md`](docs/USER_AND_AGENT_GUIDE.md) | HTTP contracts, `schema` shape, TypeDB env, tests, troubleshooting, request tracing (§8). |
| [`docs/ENTITY_SERVICE_WORKFLOWS.md`](docs/ENTITY_SERVICE_WORKFLOWS.md) | Mermaid flows: `/extract`, `/schema-pipeline/*`, TS TypeDB helpers. |
| [`docs/NEW_AGENT_ONBOARDING_PROMPT.md`](docs/NEW_AGENT_ONBOARDING_PROMPT.md) | Copy-paste handoff for a new coding agent (sections 1–10). |
| [`docs/GROOVEGRAPH_TYPEDB_ON_ENTITY_SERVICE.md`](docs/GROOVEGRAPH_TYPEDB_ON_ENTITY_SERVICE.md) | Why **`TYPEDB_*`** must be on the **FastAPI process**, not only in GrooveGraph’s `.env`. |
| [`docs/ENTITY_SERVICE_PUNCH_LIST.md`](docs/ENTITY_SERVICE_PUNCH_LIST.md) | Delivery status table + **GrooveGraph tracking tags** (e.g. `typedb_not_configured_on_entity_service`). |
| [`docs/AGENT_ENTITY_SERVICE_ISSUES.md`](docs/AGENT_ENTITY_SERVICE_ISSUES.md) | Symptom matrix when `/extract` or `/formatted` look empty or wrong. |

[`README.md`](README.md) has bootstrap commands, smoke scripts, and repository layout.

---

## GrooveGraph contract: `gg-generic`

**`POST /extract`** may emit **`entities[].label`** = **`gg-generic`** when no finer catalog type applies (aligned with TypeQL **`entity gg-generic`** in GrooveGraph’s schema). Keep the string stable.

- **`useTypeDbTypes`: true** — TypeDB-backed alignment takes precedence when configured on this process.
- **`options.useGgGenericForUnknownCatalogLabels`** (default **false**) — when **`useTypeDbTypes`** is **false**, map labels outside the request **`schema`** slice to **`gg-generic`** for alignment. See models and extractor tests.

---

## Non-negotiables

- **Stable `/extract` entities[] shape:** each item keeps **`text`**, **`label`**, **`start`**, **`end`**, **`confidence`**. Additive fields (**`typeCandidates`**, optional **`labelCandidates`**) are OK; do not rename or remove core fields.
- **No TypeDB writes** from this service. **`/schema-pipeline/*`** and **`useTypeDbTypes`** paths are **read-only** when env is set.
- **Routes thin**; orchestration in **`app/services/`**.
- **Never commit `.env`** (gitignored).
- **Request tracing:** responses include **`X-Request-Id`**; avoid logging raw secrets (see handbook §8, `ENTITY_SERVICE_LOG_REQUEST_BODIES`).

---

## Architecture (current)

- **Python (FastAPI):** **`POST /extract`** — optional read-only TypeDB define fetch when **`useTypeDbTypes`**, aliases, optional GLiNER (**`ml`** extra), merge, label filter → **`entities`** + **`typeCandidates`**.
- **Python:** **`POST /schema-pipeline/raw|validate|formatted`** — optional TypeDB HTTP when **`TYPEDB_*`** / **`TYPEDB_CONNECTION_STRING`** on this process.
- **TypeScript (`src/`):** HTTP client, TypeDB connection helpers, schema adapter; Vitest + optional integration tests.
- **Pipeline file logs:** default **`docs/logs/`** (gitignored); disable with **`ENTITY_SERVICE_PIPELINE_LOG_FILE=0`**.

---

## When you ship a change

1. **`uv run pytest`** (and **`npm test`** / **`npm run typecheck`** if TS touched).
2. Update **`docs/USER_AND_AGENT_GUIDE.md`** (and **`README.md`**) if the HTTP contract or env story changes.
3. Update **`docs/ENTITY_SERVICE_PUNCH_LIST.md`** if you add or close a tracked integration item.
4. Regenerate or align **`src/ner-client/types.ts`** with **`app/models.py`** when request/response shapes change.

---

## Historical note

Older versions of this file contained a long “immediate objectives” checklist and duplicate JSON examples. Those are **superseded** by the documents above; use **git history** if you need the verbatim old text.
