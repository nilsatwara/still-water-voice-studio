# Target architecture

```text
Browser
  |
  v
Next.js static frontend (Cloudflare)
  |
  | HTTPS REST API
  v
Python FastAPI backend (Render / Docker / VPS)
  |-- Edge TTS
  |-- Kokoro
  |-- PostgreSQL (future migration)
  `-- Shared cache (future migration)
```

`frontend/` and `backend/` are independently deployable. The Next.js app uses
static export and only calls public API contracts. Python dependencies, Kokoro
weights, generated audio, database connections, and cache access stay on the
backend.

During migration, the production-like aiohttp application remains on port
8766. FastAPI on port 8767 uses a narrow read-only adapter to the existing
catalog. Generation, the SQLite queue, output files, and model lifecycle remain
unchanged until separately migrated and tested.
