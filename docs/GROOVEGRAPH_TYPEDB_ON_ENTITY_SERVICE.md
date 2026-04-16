# GrooveGraph: TypeDB must be on the entity-service process

GrooveGraph (`gg`) reads `TYPEDB_*` from its own repo `.env`. **That does not configure entity-service.**

For **`POST /schema-pipeline/raw`**, **`/formatted`**, and **`POST /extract`** with **`useTypeDbTypes`: true**, the **FastAPI / uvicorn process** must have the same variables in **its** environment (for example `uv run --env-file .env fastapi dev app/main.py` so `.env` is loaded **into that process**).

If TypeDB is missing on ES, you will see **`503`** with **`detail.code`** **`typedb_not_configured_on_entity_service`**, or a startup log line:

`TypeDB HTTP is not configured in this process ...`

See also `docs/ENTITY_SERVICE_PUNCH_LIST.md` and `docs/USER_AND_AGENT_GUIDE.md` §3.
