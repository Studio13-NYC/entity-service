# entity-service

FastAPI **named-entity style extraction** service with a **TypeScript HTTP client**, **alias + optional schema-driven matching**, optional **GLiNER** (off by default), **merge** logic for overlapping spans, and **pytest** coverage. This service is a **pure data-processing pipeline**: it **never connects to a database** (including TypeDB); the TS layer supplies any schema slice on the request. The **`/extract` response JSON shape is stable**; new behavior is added only via optional request fields.

This document is written so you can **reproduce the setup from an empty machine** after you have this repository’s source tree (clone or copy files). It does not duplicate every source line; it describes **layout, contracts, tooling, and commands** end to end.

### Shareable end-to-end documentation

For **integrators and AI agents** (architecture, HTTP contract, `schema`, TypeDB env, tests, and troubleshooting in one place), use:

**[`docs/USER_AND_AGENT_GUIDE.md`](docs/USER_AND_AGENT_GUIDE.md)**

---

## What you get

| Layer | Role |
|--------|------|
| **`app/`** | FastAPI app: routes, Pydantic models, services (matcher, extractor, schema → aliases, optional GLiNER). |
| **`app/config/aliases.py`** | Default aliases as a **nested dict** (flattened to rows for matching). |
| **`app/services/merge.py`** | Merges alias + model candidates (RapidFuzz-assisted overlap handling). |
| **`tests/`** | `pytest` for matcher, extractor, models, schema, merge, GLiNER wiring. |
| **`src/`** | TypeScript: `NerServiceClient`, types, smoke CLI, TypeDB-oriented **schema adapter**. |

---

## Prerequisites

Install on your PATH:

| Tool | Version | Purpose |
|------|---------|---------|
| **[uv](https://docs.astral.sh/uv/)** | current | Python 3.12+ env, lockfile, `uv run`. |
| **Node.js + npm** | LTS | TypeScript client, `ts-node`, smoke script. |
| **Git** | any | Clone / version control. |

Target: **Python 3.12+** (`requires-python` in `pyproject.toml`).

---

## Repository layout

```text
entity-service/
  docs/
    USER_AND_AGENT_GUIDE.md # End-to-end guide for users and AI agents
  AGENTS.md                 # Agent / roadmap notes (optional for humans)
  README.md                 # This file
  vitest.config.ts          # Vitest (TS tests, including optional TypeDB integration)
  pyproject.toml            # Python project, deps, hatchling wheel, pytest config
  uv.lock                   # Locked Python deps (commit this)
  package.json              # npm scripts + TS devDependencies
  package-lock.json         # npm lock (commit if you use npm ci)
  tsconfig.json             # TypeScript compiler options
  test.ps1                  # PowerShell wrapper: sets NER_SERVICE_URL, runs npm smoke

  app/
    __init__.py
    main.py                 # FastAPI app + router includes
    models.py                 # Request/response + schema + options Pydantic models
    config/
      __init__.py
      aliases.py              # Default ALIASES rows
    routes/
      __init__.py
      health.py               # GET /health
      extract.py              # POST /extract
    services/
      __init__.py
      alias_matcher.py        # AliasMatcher: substring scan + overlap dedupe
      extractor.py            # Orchestrates aliases, schema, model, merge, labels, options
      schema_aliases.py       # EntitySchemaPayload → extra alias rows
      merge.py                # Overlap / near-duplicate merge (RapidFuzz)
      gliner_extractor.py   # extract_with_model (optional GLiNER; off by default)
      spacy_extractor.py      # Stub for future spaCy EntityRuler path

  tests/
    test_alias_matcher.py
    test_extractor.py
    test_models.py
    test_schema_aliases.py
    test_gliner_extractor.py
    test_merge.py
    test_spacy_extractor.py

  src/
    test-ner.ts               # Smoke: health + several extract scenarios
    ner-client/
      client.ts               # fetch() client
      types.ts                # Mirrors Python API types
    typedb/
      index.ts                  # Barrel exports (client, env, verify, fetch schema, …)
      env.ts                    # TYPEDB_* + TYPEDB_CONNECTION_STRING → TypeDbEnv
      connection-string.ts      # typedb://… Cloud URI parser
      verify-connection.ts      # verifyTypeDbConnection (health + DB + type schema)
      schema-adapter.ts         # TypeDbSchemaSnapshot → EntitySchemaPayload
      fetch-schema-for-extraction.ts
      introspect-ontology.ts    # Ontology checks from define type schema
      …                         # typeql-builders, validate-data-concepts, tests, scripts
```

**Wheel packaging:** `pyproject.toml` uses **Hatchling** with `packages = ["app"]` only. There is no separate publishable `entity_service` Python package under `src/` (that tree is TypeScript only).

---

## Bootstrap from scratch (after you have the files)

### 1. Create / enter the project directory

Either **clone** this repo or **copy** the tree above into an empty folder and `cd` into it.

### 2. Python environment and dependencies

```bash
# Install runtime + dev (pytest) from uv.lock
uv sync --all-groups
```

If `uv.lock` is missing (truly blank start), generate it once:

```bash
uv lock
uv sync --all-groups
```

**Editable install:** `uv sync` installs the local package `entity-service` (wheel contains the `app` package only).

### 3. Run the API (development)

From the repo root:

```bash
uv run fastapi dev app/main.py
```

On Windows, backslashes are fine:

```powershell
uv run fastapi dev app\main.py
```

Default URL: **`http://127.0.0.1:8000`**. Open **`/docs`** for Swagger.

**Production-style (no dev reload):**

```bash
uv run fastapi run app/main.py
```

### 4. TypeScript client dependencies

```bash
npm install
```

### 5. Verify Python tests

```bash
uv run --group dev pytest
```

Quiet:

```bash
uv run --group dev pytest -q
```

### 6. Verify TypeScript (no emit)

```bash
npm run typecheck
```

### 7. End-to-end smoke (needs API running)

Terminal A: start the server (step 3).  
Terminal B:

```bash
npm run smoke
```

Optional base URL:

```bash
# Unix
NER_SERVICE_URL=http://127.0.0.1:8000 npm run smoke
```

```powershell
# Windows PowerShell
$env:NER_SERVICE_URL = "http://127.0.0.1:8000"; npm run smoke
```

Or use **`.\test.ps1`** / **`.\test.ps1 http://127.0.0.1:9000`** on Windows.

---

## HTTP API

### `GET /health`

**Response:** `{ "ok": true }`

### `POST /extract`

**Content-Type:** `application/json`

**Response shape (stable, do not change field names or top-level structure):**

```json
{
  "entities": [
    {
      "text": "string",
      "label": "string",
      "start": 0,
      "end": 0,
      "confidence": 0.0
    }
  ]
}
```

#### Request body (all optional fields are additive)

| Field | Type | Default / omit behavior |
|--------|------|-------------------------|
| `text` | string | **Required.** Input text. |
| `labels` | string[] | Omit or `[]`: no label filter. Non-empty: only entities whose `label` is in the list. |
| `options` | object | Omit: `{ "use_aliases": true, "use_model": false }`. |
| `options.use_aliases` | boolean | If `false`, skips file + schema alias matching. |
| `options.use_model` | boolean | If `true`, merges GLiNER spans when `GLINER_ENABLED` and the `ml` extra are installed; otherwise the model path returns no entities. |
| `schema` | object | Omit: no extra runtime aliases. See below. |

**`schema`** (JSON key; Python attribute `entity_schema`):

```json
{
  "entityTypes": ["work", "person"],
  "knownEntities": [
    {
      "label": "work",
      "canonical": "Invisible Cities",
      "aliases": ["Invis Cities"]
    }
  ]
}
```

- **`entityTypes`**: each entry may be a **string** (type id) or an object `{ "name": "...", "aliases": [...] }` for richer hints; carried for future constraints. Matching today uses **`knownEntities`**.
- **`knownEntities`**: each row becomes alias catalog entries `(label, canonical, canonical)` plus one row per non-empty alias string.
- Runtime rows are **merged after** `app/config/aliases.py` rows (same matcher pass).

Pydantic accepts **camelCase** (`entityTypes`, `knownEntities`) or **snake_case** (`entity_types`, `known_entities`) on nested objects where configured.

#### Example requests

Minimal:

```json
{ "text": "Girlfriend by Matt Sweet" }
```

With labels and options:

```json
{
  "text": "Girlfriend by Matt Sweet",
  "labels": ["artist"],
  "options": { "use_aliases": true, "use_model": false }
}
```

With schema (or build the same object in TS via `toEntitySchemaPayload` in `src/typedb/schema-adapter.ts`):

```json
{
  "text": "Reading Invis Cities tonight",
  "schema": {
    "entityTypes": ["work"],
    "knownEntities": [
      {
        "label": "work",
        "canonical": "Invisible Cities",
        "aliases": ["Invis Cities"]
      }
    ]
  }
}
```

---

## TypeScript client

| Module | Purpose |
|--------|---------|
| `src/ner-client/types.ts` | `ExtractRequest`, `ExtractResponse`, `EntitySchemaPayload`, `ExtractOptions`, etc. |
| `src/ner-client/client.ts` | `NerServiceClient`: `health()`, `extract(req)`. |
| `src/typedb/` | TypeDB HTTP helpers, env + connection string, `verifyTypeDbConnection`, schema fetch, `toEntitySchemaPayload` — see **`docs/USER_AND_AGENT_GUIDE.md` §6–§7**. |
| `src/test-ner.ts` | Manual smoke scenarios. |

**`fetch`** is used (requires **DOM** lib in `tsconfig.json`; Node 18+ has global `fetch`).

**Tests:** `npm test` (Vitest: parsers + optional live TypeDB if `.env` is set), `npm run test:typedb`, `npm run typedb:dump-ontology` for ontology introspection.

---

## Extraction pipeline (conceptual)

```text
text
  → [optional] alias matcher (file ALIASES + schema-derived rows)
  → [optional] extract_with_model (GLiNER when enabled + ml extra)
  → merge_entity_candidates (RapidFuzz overlap policy)
  → label filter (if labels non-empty)
  → sort by (start, end, label, text)
  → JSON entities[]
```

Routes stay thin; logic lives under **`app/services/`**.

---

## Configuration

- **Default aliases:** edit **`app/config/aliases.py`** — nested dict `ALIASES_NESTED` keyed by entity label, then canonical string, then a list of surface substrings. Flattened rows power the matcher.
- **No database in Python:** schema and TypeDB access live in TypeScript; see **`src/typedb/schema-adapter.ts`** for a TS-side normalization shape.

## Music Ontology ([MO](https://github.com/motools/musicontology))

The [Music Ontology](https://github.com/motools/musicontology) defines **RDF/OWL concepts** (artists, recordings, performances, etc.). This HTTP service does **not** parse MO TTL/RDF itself. To make extraction **ontology-aware**, supply a **schema slice** on each request (built in TS or another service):

1. **Label vocabulary** — Map MO classes or roles you care about (e.g. artist-like vs release-like concepts) to the **string `label`** values you send in `labels` / `schema.knownEntities[].label` / default aliases in `app/config/aliases.py`.
2. **Known entities + synonyms** — From your knowledge graph or curated data, emit **`knownEntities`**: `{ label, canonical | canonical_text, aliases[] }` so substring + GLiNER outputs align with your MO instances.
3. **Optional `entityTypes`** — Use objects `{ "name": "...", "aliases": [...] }` for future ruler / constraint layers.

If you share a **concrete MO subset** (labels you use, example individuals, synonym policy), that can drive the **TS adapter** and default **alias config** without adding database calls to Python.

## Optional ML stack (`ml` extra: GLiNER + spaCy)

Heavy wheels (**torch**, **transformers**, **onnxruntime**, **spaCy**, **gliner**, etc.) are **optional** so a default `uv sync` stays lean.

```bash
uv sync --all-groups --extra ml
```

**English spaCy pipeline** (required if you call spaCy code that loads `en_core_web_sm`; not bundled as a normal PyPI dep for all Python versions):

```bash
uv run python -m spacy download en_core_web_sm
```

**GLiNER** (example):

```bash
export GLINER_ENABLED=1
export GLINER_MODEL_ID=urchade/gliner_small-v2.1   # optional override
```

If `GLINER_ENABLED` is unset or the `ml` extra was not installed, **`extract_with_model`** returns no entities and alias extraction is unchanged. The **`spacy_extractor`** stub is present for a future EntityRuler path; it is not wired into the main extractor yet.

---

## `pyproject.toml` essentials (recreation reference)

If you recreate the repo by hand, you need at least:

- **`[project]`**: `name`, `requires-python >= 3.12`, `dependencies` including `fastapi[standard]>=0.115.0` and `rapidfuzz`.
- **`[project.optional-dependencies].ml`**: `gliner` and `spacy` (install with `uv sync --extra ml`).
- **`[build-system]`**: `hatchling` + **`[tool.hatch.build.targets.wheel]`** `packages = ["app"]`.
- **`[dependency-groups].dev`**: `pytest` and **`[tool.pytest.ini_options]`** with `testpaths = ["tests"]`, `pythonpath = ["."]` so `import app` works from the repo root.

Lock with **`uv lock`** and commit **`uv.lock`**.

---

## `package.json` scripts

| Script | Command |
|--------|---------|
| `npm run smoke` | `ts-node src/test-ner.ts` |
| `npm run typecheck` | `tsc --noEmit` |

---

## Troubleshooting

### Windows: `uv sync` fails on `pydantic_core` `.pyd` (“Access is denied”)

Another process is locking the venv (editor, antivirus, old Python). Close it, remove `.venv`, then:

```powershell
uv sync --all-groups
```

If hardlinks are problematic:

```powershell
$env:UV_LINK_MODE = "copy"
uv sync --all-groups
```

### TypeScript: `moduleResolution` / deprecation

`tsconfig.json` sets **`ignoreDeprecations": "6.0"`** and explicit **`moduleResolution`** compatible with TypeScript 6.

### Imports: `ModuleNotFoundError: app`

Run pytest via **`uv run --group dev pytest`** from the **repository root** so `pythonpath` in `pyproject.toml` applies.

---

## Agent / product notes

Longer-lived goals, checklist, and constraints for contributors and automation live in **`AGENTS.md`**.

---

## License

See **`package.json`** (`license` field) for the npm package stub; set a project-wide license as needed for your organization.
