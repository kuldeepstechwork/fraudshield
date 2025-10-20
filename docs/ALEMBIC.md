Alembic usage (project-specific notes)

1) Ensure your virtualenv is activated and `requirements.txt` dependencies are installed.

2) Make sure `src.common.config.settings.DATABASE_URL` points to your database (or set `DATABASE_URL` env var / `.env`).

3) Initialize (we already added a minimal `alembic/` layout). To generate an autogenerate migration:

```bash
PYTHONPATH=. alembic revision --autogenerate -m "create initial tables"
```

4) Apply migrations:

```bash
PYTHONPATH=. alembic upgrade head
```

Notes:
- `env.py` uses `src.common.db.Base.metadata` for `target_metadata`, so Alembic will read your models in `src/models` as long as they are imported by `src.models.__init__` or `env.py` imports the model modules.
- If autogenerate doesn't detect models, make sure `src/models/__init__.py` imports all model modules or add explicit imports in `alembic/env.py` before setting `target_metadata`.
