# FastAPI backend

The backend is currently a read-only compatibility sidecar. It does not generate speech, operate the legacy queue, or alter the legacy SQLite database.

Run from the project root: `.\.venv\Scripts\python.exe -m backend.app`.

Configuration uses `APP_HOST`, `APP_PORT`, `API_PREFIX`, and an explicit `CORS_ORIGINS` allowlist. `DATABASE_URL` configures the central async PostgreSQL engine. `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, and `DB_POOL_RECYCLE` tune its process-local connection pool. Credentials are environment-only and hidden from the settings representation.

The engine is lazy: startup does not open a connection, and the current catalog routes do not require PostgreSQL. Future database-backed routes will receive one request-scoped `AsyncSession` through `get_database_session`; failed operations roll back and application shutdown disposes the pool. The working SQLite queue remains unchanged until its own migration stage.

All future ORM tables share `backend.app.models.Base`, deterministic constraint
names, UUID primary keys, and timezone-aware timestamp mixins. No application
tables are part of this foundation step.

Alembic configuration lives in `backend/alembic.ini`, reads `DATABASE_URL` from
the environment, and compares migrations against the shared model metadata.
See `backend/migrations/README.md` for upgrade, downgrade, and autogeneration
commands. The initial `0001` revision is an empty migration baseline.

Authorization uses server-owned `Principal` objects and reusable FastAPI guards
such as `Depends(require_permission('posts.create'))`. Client identity headers
are ignored. The default identity resolver is anonymous until a signed
session/token implementation is added; protected routes therefore fail closed.

`LegacyCatalogAdapter` imports the current catalog temporarily. `EdgeTTSService` and `KokoroTTSService` provide stable engine boundaries and delegate read-only voice lookup to the adapter. No synthesis or model download occurs on these endpoints.

Build the backend container from the project root: `docker build -f backend/Dockerfile -t stillwater-api .`.
