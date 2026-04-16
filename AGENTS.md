# AGENTS.md — NER / Entity Service

## Overview

**Shareable system documentation** (HTTP contract, `schema`, TypeDB TS layer, env, tests): [`docs/USER_AND_AGENT_GUIDE.md`](docs/USER_AND_AGENT_GUIDE.md). **Workflow diagrams (Mermaid):** [`docs/ENTITY_SERVICE_WORKFLOWS.md`](docs/ENTITY_SERVICE_WORKFLOWS.md). **GrooveGraph + TypeDB on ES:** [`docs/GROOVEGRAPH_TYPEDB_ON_ENTITY_SERVICE.md`](docs/GROOVEGRAPH_TYPEDB_ON_ENTITY_SERVICE.md). **New agent handoff prompt:** [`docs/NEW_AGENT_ONBOARDING_PROMPT.md`](docs/NEW_AGENT_ONBOARDING_PROMPT.md).

This project implements a FastAPI-based entity extraction service with a TypeScript client. The system is evolving toward:

- schema-aware extraction (TypeDB-driven, via TS-provided payloads — not embedded in Python yet)
- configurable alias handling (no hardcoded tuples)
- optional model-based extraction (GLiNER behind `ml` extra + `GLINER_ENABLED`; merge policy documented in code)

---

## Mission

Stabilize and extend the NER service so it becomes:

- **Schema-aware** (TypeDB-driven context from the client)
- **Configurable** (aliases and behavior via config / runtime schema)
- **Extensible** (GLiNER with feature flags and merge hooks)
- **Safely consumable** by a TypeScript client (stable contracts)

---

## Current State

- FastAPI service running (`/health`, `/extract`)
- Alias-based extraction with canonicalization
- TS client operational
- Example: `"Girlfriend by Matt Sweet"` → `"Girlfriend"` + `"Matthew Sweet"`

---

## Immediate Objectives (in order)

### 1. Stabilize

- Ensure all Python files contain only valid Python (no `@'` / `'@`, no PowerShell or shell syntax pasted into `.py` files)
- Confirm clean restart: `uv run fastapi dev app\main.py`
- Validate `/health` and `/extract`

### 2. Add Test Coverage

- Alias matching correctness
- Canonicalization behavior
- Overlap deduplication
- Label filtering
- Files: `tests/test_alias_matcher.py`, `tests/test_extractor.py`

### 3. Externalize Alias Data

- Move aliases into `app/config/aliases.py` (structured format)
- Refactor matcher to consume config; remove hardcoded tuples

### 4. Enforce Label Filtering

- Only return entities matching requested `labels` when provided
- Preserve backward compatibility when `labels` is omitted

### 5. Extend API Safely (non-breaking)

Optional request field:

```json
{
  "options": {
    "use_aliases": true,
    "use_model": false
  }
}
```

Existing clients must keep working without sending `options`.

### 6. Schema Awareness

Define a schema payload contract (TS → Python): entity types, canonical entities, aliases. The extractor accepts **runtime** alias sets via `schema`. TypeDB and other databases stay **out of Python** (TS builds `schema`).

### 7. Model integration (GLiNER)

- `app/services/gliner_extractor.py` implements `extract_with_model(text, labels)` behind `GLINER_ENABLED` and the `ml` extra.
- Merge of alias + model output lives in `app/services/merge.py`; refine policy with tests as needed.

---

## Constraints

- **Do not** change the **core** `/extract` **response** fields on each **`entities[]`** item (`text`, `label`, `start`, `end`, `confidence`). Additive fields (`typeCandidates`, optional `labelCandidates`) are OK.
- **`POST /extract`:** default = **no** TypeDB. Optional **`useTypeDbTypes`: true** = **read-only** TypeDB define fetch on the FastAPI process. **`/schema-pipeline/*`** remains read-only when env is set. TS remains a common way to build **`schema`**, but is not the only path.
- Keep **routes thin**; keep **extraction logic in `app/services/`** only
- Prefer strict typing in Python and TypeScript

---

## Deliverables

- Clean Python service (no stray shell artifacts)
- Alias config system (`app/config/aliases.py`)
- Test suite covering matcher and extractor behaviors
- Schema-aware request handling (additive, non-breaking)
- Extractor refactored for optional model path and merge

---

## Architecture

### Python (FastAPI)

**Responsibilities**

- Accept extraction requests
- Perform alias-based matching (and later optional model extraction)
- Return structured entity candidates

**Must not**

- Write to TypeDB (no commits / schema migrations from this service)
- Contain frontend logic
- Contain shell/script syntax inside `.py` files

### TypeScript (`src/`)

**Responsibilities**

- Call the NER service
- Supply schema context (derived from TypeDB or other sources)
- Consume structured entity results

---

## API Contract

### `POST /extract`

#### Request

```json
{
  "text": "string",
  "labels": ["optional", "list"],
  "options": {
    "use_aliases": true,
    "use_model": false
  }
}
```

`labels` and `options` are optional for backward compatibility.

#### Response (stable — do not change shape)

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

---

## Extraction Pipeline

**Current**

```text
text → alias matcher → canonical entities → response
```

**Target**

```text
text
  → alias matcher (config / runtime schema)
  → model extractor (GLiNER) [optional]
  → merge
  → response
```

---

## Alias System

- Externalized configuration — avoid hardcoding tuples in services
- Default / static aliases live in `app/config/aliases.py`
- Runtime schema from TS may **supplement or override** alias sets; keep both paths until schema-only is proven

---

## Schema Integration

Schema is provided by the TypeScript layer. Expected payload shape (illustrative — refine types in code as needed):

```json
{
  "entityTypes": [],
  "knownEntities": []
}
```

Python must:

- Accept schema input on the request when present
- Use it for extraction constraints and alias expansion
- **Not** own schema persistence

---

## Development Rules

### Do

- Keep routes thin (`app/routes/` or equivalent)
- Isolate logic in `app/services/`
- Write tests for all extraction logic
- Maintain strict typing

### Do not

- Mix PowerShell or shell syntax into Python files
- Break the `/extract` response contract
- Require TypeDB for **`/extract`** unless the client explicitly sets **`useTypeDbTypes`**
- Ship full model extraction before the alias path and tests are stable

---

## Directory Structure (target)

```text
app/
  config/
  services/
  routes/
tests/
src/
```

---

## Roadmap

1. Stabilize alias extraction
2. Add test coverage
3. Externalize config
4. Add schema-aware extraction (additive)
5. Integrate GLiNER
6. Add merge logic

---

## Key Principle

The **interface** (API + TS client) must stabilize **before** extraction internals become complex.

---

## Cursor Task Checklist

Use this as a step-by-step execution list while implementing.

### Setup / validation

- [ ] Open `app/services/*.py` and confirm: no `@'` or `'@`, no PowerShell syntax
- [ ] Restart server: `uv run fastapi dev app\main.py`
- [ ] Validate `/health` and `/extract`

### Testing layer

- [ ] Create `tests/test_alias_matcher.py`
- [ ] Create `tests/test_extractor.py`
- [ ] Tests: exact alias match; fuzzy alias (e.g. Matt → Matthew); overlap handling; label filtering; empty input

### Alias refactor

- [ ] Create `app/config/aliases.py`
- [ ] Move alias definitions into structured format
- [ ] Update `alias_matcher.py` to consume config
- [ ] Remove hardcoded tuples
- [ ] Verify extraction still works

### Label filtering

- [ ] Update extractor to accept labels
- [ ] Filter output by requested labels
- [ ] Add tests for filtering behavior

### API extension

- [ ] Update `app/models.py` with optional `options`
- [ ] Ensure backward compatibility
- [ ] Validate request parsing

### Schema integration (baseline done)

- Schema payload and runtime alias injection are implemented; see `app/models.py`, `docs/USER_AND_AGENT_GUIDE.md`, and `src/typedb/`.

### TypeScript / TypeDB (baseline done)

- `src/typedb/schema-adapter.ts`, connection helpers, ontology checks, and tests are in place; see `docs/USER_AND_AGENT_GUIDE.md`.

### GLiNER (optional `ml` extra)

- Implemented in `app/services/gliner_extractor.py` behind `GLINER_ENABLED` and `uv sync --extra ml`; further tuning is incremental (labels, merge policy, tests).

### Ongoing cleanup

- Keep directory layout (`app/config`, `app/services`, `app/routes`, `tests`, `src`) consistent; remove dead code as features land; keep Python + TS types aligned with `POST /extract`.
