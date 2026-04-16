# Entity service (ES) — workflows and diagrams

This document complements **[`USER_AND_AGENT_GUIDE.md`](./USER_AND_AGENT_GUIDE.md)** (contracts, env, troubleshooting) with **decision-oriented** views: what runs where, and which paths touch TypeDB.

**Legend:** **ES** = this FastAPI app. **TypeDB** = database (Cloud or CE). **TS** = TypeScript in `src/`.

---

## 1. Which workflow am I using?

| You need… | TypeDB in ES process? | TypeDB in Node/TS? | Primary HTTP calls |
|-----------|------------------------|---------------------|---------------------|
| NER only, no catalog | No | No | `POST /extract` |
| NER + runtime vocabulary from your app | No | Optional | `POST /extract` + `schema` body |
| Raw define + validate + `schema` from **Python** | **Yes** (`TYPEDB_*` on ES) | Optional elsewhere | `POST /schema-pipeline/raw` → `validate` → `formatted` → `POST /extract` |
| Build `schema` in **TypeScript** | No | **Yes** | TS → TypeDB; then `POST /extract` |

**Rule:** `POST /extract` **never** opens a TypeDB connection inside Python. TypeDB in ES exists **only** for `/schema-pipeline/*`.

---

## 2. Workflow A — Extract only (minimal)

No `schema`, no TypeDB. Aliases from `app/config/aliases.py` (+ optional GLiNER if enabled).

```mermaid
flowchart LR
  C[HTTP client]
  ES[FastAPI POST /extract]
  P[Extractor: aliases merge labels]
  C -->|text labels options| ES --> P --> R["JSON entities"]
```

---

## 3. Workflow B — Extract + client `schema`

Caller (any HTTP client or TS) sends **`schema`** with `entityTypes` / `knownEntities`. Still **no** TypeDB in Python.

```mermaid
flowchart LR
  C[Caller]
  ES[POST /extract]
  P[Extractor + schema-derived alias rows]
  C -->|text schema labels| ES --> P --> R[entities]
```

---

## 4. Workflow C — Schema pipeline on ES (optional TypeDB)

Use when the **same machine/process** as FastAPI has **`TYPEDB_*`** and you want ES to read define text and samples, then emit a **`schema`** for `/extract`.

```mermaid
sequenceDiagram
  participant Client
  participant ES as FastAPI ES
  participant TDB as TypeDB HTTP

  Client->>ES: POST /schema-pipeline/raw
  ES->>TDB: type-schema + bounded queries
  TDB-->>ES: define + samples
  ES-->>Client: typeSchemaDefine perType …

  Client->>ES: POST /schema-pipeline/validate
  Note over ES: No live DB; body carries define text
  ES-->>Client: ready issues

  Client->>ES: POST /schema-pipeline/formatted
  ES->>TDB: queries per entity type
  TDB-->>ES: rows
  ES-->>Client: entityTypes knownEntities

  Client->>ES: POST /extract schema from formatted
  ES-->>Client: entities
```

```mermaid
flowchart TB
  subgraph es [FastAPI ES]
    RAW[POST /raw]
    VAL[POST /validate]
    FMT[POST /formatted]
    EXT[POST /extract]
  end
  TDB[(TypeDB)]
  RAW --> TDB
  FMT --> TDB
  VAL -.->|no DB| VAL
  FMT -->|schema JSON| EXT
```

---

## 5. Workflow D — TypeScript–first (TypeDB only in Node)

GrooveGraph / apps use **`src/typedb/`** + `@typedb/driver-http`. ES stays dumb to the database; it only receives **`schema`** on `/extract`.

```mermaid
flowchart LR
  subgraph node [Node / TS]
    TD[typedb helpers]
    AD[schema-adapter]
  end
  DB[(TypeDB)]
  ES[POST /extract]

  DB <--> TD --> AD -->|schema JSON| ES
```

---

## 6. Workflow E — Validate without live DB

Offline check of define text + ER assumptions (no credentials needed on caller for this step).

```mermaid
flowchart LR
  C[Client]
  ES[POST /schema-pipeline/validate]
  C -->|typeSchemaDefine assumptions| ES --> Out["ready + issues"]
```

---

## 7. Testing and smoke (where things run)

```mermaid
flowchart TB
  subgraph local [Repo / CI]
    PY[pytest / pytest -m contract]
    VIT[vitest]
    TSC[tsc --noEmit]
  end
  subgraph live [API must be up]
    SM1[npm run smoke]
    SM2[scripts/smoke_schema_pipeline.py]
  end
  ESrv[uv run fastapi dev]

  PY --> ESrv
  VIT -.->|optional TypeDB in .env| DB[(TypeDB)]
  SM1 --> ESrv
  SM2 --> ESrv
```

---

## 8. Failure routing (operational)

```mermaid
flowchart TD
  A[POST /schema-pipeline/raw or formatted]
  B{TypeDB configured on ES process?}
  C[503 detail.code typedb_not_configured_on_entity_service]
  D[Call TypeDB]
  E{HTTP / DB error?}
  F[502 / 404 with detail.code]

  A --> B
  B -->|no| C
  B -->|yes| D --> E
  E -->|yes| F
```

See **`docs/USER_AND_AGENT_GUIDE.md`** §3 for stable **`detail`** shapes.

---

## Related files

| Area | Path |
|------|------|
| Extract | `app/routes/extract.py`, `app/services/extractor.py` |
| Schema pipeline | `app/routes/schema_pipeline.py`, `app/services/schema_pipeline.py` |
| TS TypeDB | `src/typedb/*` |
| Smoke | `scripts/smoke_schema_pipeline.py`, `src/test-ner.ts`, `npm run smoke*` |

When you add a new **HTTP-facing** flow, update this document and the handbook so integrators keep one mental model.
