# PostgreSQL migrations

Run commands from the project root with `DATABASE_URL` configured:

```powershell
$env:DATABASE_URL='postgresql+psycopg://user:password@localhost:5432/stillwater'
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini downgrade -1
```

After changing ORM models, generate a candidate revision and review every line
before applying it:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini revision --autogenerate -m "describe change"
```

Never edit an applied migration or replace production upgrades with
`drop_all()`/`create_all()`.
