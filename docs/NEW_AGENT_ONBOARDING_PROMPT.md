# New agent onboarding — copy into your first message

**How to use this file:** Copy everything **from the horizontal rule below through the end of section 10** into a new agent chat as your opening message (or attach this file and say: “Read `docs/NEW_AGENT_ONBOARDING_PROMPT.md` from the divider and treat it as your operating brief”). Sections **11–12** are reference only—do not need to be pasted.

---

You are taking over **entity-service**: a small **FastAPI** repo plus **TypeScript** tooling for NER-style extraction and optional **TypeDB** integration. Your job is to ship changes **without breaking the stable `POST /extract` response** and to respect the split between **extraction** (Python) and **graph/schema preparation** (TS primary; Python optional read-only pipeline).

## 1. Read these in order (canonical truth)

1. **`docs/USER_AND_AGENT_GUIDE.md`** — end-to-end architecture, HTTP contracts, `schema` shape, TypeDB env, tests, troubleshooting. **Primary handbook.**
2. **`README.md`** — bootstrap, commands, HTTP tables, layout.
3. **`AGENTS.md`** — maintainer roadmap, constraints, historical objectives.
4. **`docs/ENTITY_SERVICE_PUNCH_LIST.md`** — **tracking tags** plus a **status table**: entity-service deliveries vs **GrooveGraph client** follow-ups (env on ES process, `gg doctor` URL, CI commands).
5. **`docs/ENTITY_SERVICE_WORKFLOWS.md`** — Mermaid diagrams: extract-only, client `schema`, `/schema-pipeline/*`, TS-first TypeDB, tests/smoke.

Repository URLs (if published): see the table at the top of `docs/USER_AND_AGENT_GUIDE.md`.

## 2. Non-negotiables (violating these creates regressions)

- **`POST /extract` response** stays: `{ "entities": [ { "text", "label", "start", "end", "confidence" } ] }`. Do not rename or remove those fields. New behavior = **optional request fields** only.
- **`POST /extract` must not query TypeDB.** It only consumes optional JSON **`schema`** (`entityTypes`, `knownEntities`) built elsewhere.
- **Optional** server-side TypeDB: **`POST /schema-pipeline/raw`**, **`/schema-pipeline/validate`**, **`POST /schema-pipeline/formatted`** — **read-only** HTTP to TypeDB when **`TYPEDB_*`** / **`TYPEDB_CONNECTION_STRING`** is set on the **same process** as FastAPI. **`/validate`** has no live DB requirement (body carries `typeSchemaDefine` text).
- **Routes stay thin**; orchestration lives in **`app/services/`**.
- **Do not** commit **`.env`** (gitignored). TypeDB credentials belong in env, not source.

## 3. Mental model (one paragraph)

Callers send **`text`** + optional **`labels`**, **`options`**, **`schema`**. The Python pipeline runs: optional aliases (file + `schema` rows) → optional GLiNER (`ml` extra + `GLINER_ENABLED`) → **RapidFuzz merge** → label filter → sort → **`entities`**. TypeDB is never consulted inside **`/extract`**. If the product needs “raw define + validate types + formatted schema,” use **`/schema-pipeline/*`** or build **`schema`** in **`src/typedb/`** with `@typedb/driver-http`.

## 4. Repo map (where to edit what)

| Area | Path |
|------|------|
| FastAPI app | `app/main.py` — routers: `health`, `extract`, `schema_pipeline` |
| Extract contract | `app/models.py`, `app/routes/extract.py`, `app/services/extractor.py` |
| Aliases | `app/config/aliases.py`, `app/services/alias_matcher.py`, `app/services/schema_aliases.py` |
| Merge / GLiNER | `app/services/merge.py`, `app/services/gliner_extractor.py` |
| Schema pipeline (TypeDB HTTP) | `app/routes/schema_pipeline.py`, `app/services/schema_pipeline.py`, `app/services/typedb_*.py`, `app/services/typeql_builders.py`, `app/schema_pipeline_models.py` |
| TS HTTP client | `src/ner-client/client.ts`, `src/ner-client/types.ts` |
| TS TypeDB helpers | `src/typedb/` — `env`, `connection-string`, `verify-connection`, `fetch-schema-for-extraction`, `introspect-ontology`, tests, `scripts/dump-ontology.ts` |
| Python tests | `tests/` — pytest |
| TS tests | `src/**/*.test.ts` — Vitest; **`npm test`** |
| Smoke CLI | `src/test-ner.ts`, **`test.ps1`** |
| Workflow diagrams | **`docs/ENTITY_SERVICE_WORKFLOWS.md`** |

## 5. Commands to prove you are set up

```bash
uv sync --all-groups          # Python + pytest
uv run pytest -q              # expect all green
npm install && npm test       # Vitest (TypeDB integration may skip without .env)
npm run typecheck             # tsc --noEmit (tests excluded from main tsconfig)
# Terminal A:
uv run fastapi dev app/main.py   # or app\main.py on Windows
# Terminal B:
npm run smoke                 # needs NER_SERVICE_URL / default localhost:8000
```

## 6. Environment (high-signal)

- **API / extract:** no special env required beyond running FastAPI.
- **TypeDB (Python pipeline or TS):** `TYPEDB_CONNECTION_STRING` (`typedb://user:pass@https://host:port/?name=db`) and/or `TYPEDB_ADDRESSES`, `TYPEDB_USERNAME`, `TYPEDB_PASSWORD`, `TYPEDB_DATABASE`. Values are trimmed (spaces after `=` in `.env` are OK).
- **GLiNER:** `uv sync --extra ml`, `GLINER_ENABLED`, optional `GLINER_MODEL_ID`; see README.
- **Smoke:** `NER_SERVICE_URL` if not default.

## 7. Integration pitfalls (institutional knowledge)

- **503 on `/schema-pipeline/raw` or `/formatted`:** almost always **TypeDB env not loaded on the FastAPI process** (e.g. vars only in another app’s `.env`). See punch list item **1** and tag **`typedb_not_configured_on_entity_service`**.
- **`labels` filter:** returned entities must have **`label` ∈ `labels`** when `labels` is non-empty; **`schema.knownEntities[].label`** must align with that vocabulary (GrooveGraph / MO uses labels like **`mo-music-artist`** — see punch list **5**).
- **Ontology parsing:** Python and TS parse **`getDatabaseTypeSchema`** / `define` text for entity types and string `owns`; fragile if define syntax drifts—extend parsers and tests together.
- **TypeQL `sub entity`:** avoid for Cloud/TypeDB 3 compatibility in new code; prefer define parsing + bounded **`match` / `select`** built via **`typeql_builders`** / TS **`typeql-builders.ts`**.

## 8. What “done” looks like for a typical change

- **`uv run pytest`** and **`npm test`** (and **`npm run typecheck`** if you touched TS) pass.
- **`docs/USER_AND_AGENT_GUIDE.md`**, **`docs/ENTITY_SERVICE_WORKFLOWS.md`**, and **`README.md`** updated if behavior or contracts change.
- **`docs/ENTITY_SERVICE_PUNCH_LIST.md`** updated if you close an item GrooveGraph tracks.
- No secrets, no `node_modules` / `.venv` commits, no drift of **`/extract`** JSON shape.

## 9. Suggested first actions when landing on an unclear bug

1. Reproduce with **`uv run pytest`** or minimal **`TestClient`** against **`app.main:app`**.
2. Decide: **extract-only** vs **schema-pipeline** vs **TS TypeDB** — logs and tags above narrow this quickly.
3. Read the **relevant section** of **`docs/USER_AND_AGENT_GUIDE.md`** before large refactors.

## 10. Explicit non-goals for drive-by refactors

- Do not “simplify” by moving TypeDB reads into **`/extract`**.
- Do not change **`entities[]`** field names for cosmetic reasons.
- Do not delete **`AGENTS.md`** / punch list cross-links without replacing them elsewhere.

---

## 11. Reference — optional deep links (do not paste into agent unless needed)

- OpenAPI: run the dev server and open **`/docs`**.
- Music Ontology alignment: README “Music Ontology” section; punch list **5**.

## 12. Optional opening line for the human

Paste above, then add one line of your own, e.g.: *“Current priority: [ticket]. Branch: [name]. Blocker: [none | describe].”*
