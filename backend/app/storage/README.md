# Runtime storage

`generated/` and `cache/` are reserved for backend runtime data. Deployments
should mount persistent storage or use an object store before generation is
migrated to FastAPI. Generated media and cache data are ignored by Git.
