# FraudShield

Lightweight fraud detection microservice suite (FastAPI + Kafka + Postgres).

This repository contains a small demo/starting point for building a fraud-detection pipeline:
- A FastAPI "detector" service to ingest payments and publish them to Kafka.
- A Kafka consumer that runs detection logic and persists payments + alerts to Postgres.
- Centralized common utilities for DB, config and Kafka helpers.

This README explains how the repo is organized and how to run the services locally.

## Contents

- `src/common/` — shared helpers (configuration, DB, Kafka utilities)
- `src/models/` — canonical SQLAlchemy ORM model definitions
- `src/services/detector/` — FastAPI app that ingests payments and exposes admin endpoints
- `src/services/fraud_consumer/` — Kafka consumer that runs fraud detection logic and persists results
- `src/services/producer_cli/` — small CLI helpers to send example payments to Kafka

## Requirements

This project uses Python 3.10+ and the packages in `requirements.txt`.

Key dependencies (from `requirements.txt`):
- fastapi
- uvicorn[standard]
- aiokafka
- sqlalchemy
- asyncpg
- pydantic
- pydantic-settings
- alembic

Install dependencies into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration / environment

Configuration lives in `src/common/config.py` and uses Pydantic Settings. By default it will look for a `.env` file in the project root.

Important environment variables (defaults are set in `src/common/config.py`):
- DATABASE_URL — e.g. `postgresql+asyncpg://fraud_user:fraudpass@localhost/fraudshield_db`
- KAFKA_BOOTSTRAP_SERVERS — e.g. `localhost:9092`
- KAFKA_RAW_PAYMENTS_TOPIC — topic for raw payments (default `raw_payments`)
- API_HOST, API_PORT — host/port for detector FastAPI

Create a `.env` file in the repository root to override the defaults for local testing. Example:

```env
DATABASE_URL=postgresql+asyncpg://fraud_user:fraudpass@localhost/fraudshield_db
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
API_HOST=0.0.0.0
API_PORT=8000
```

## Running locally (development)

1) Start Kafka and Postgres. You can use Docker or your local services. The repo contains a `docker-compose.yml` placeholder — you can add one to run `zookeeper`, `kafka`, and `postgres` together.

2) Create the database (if needed) and ensure `DATABASE_URL` points to it.

3) Start the detector API (development mode):

```bash
# from project root
uvicorn src.services.detector.app:app --reload --host 0.0.0.0 --port 8000
```

4) Start the consumer (run as a script or integrate into an ASGI app):

```bash
python -m src.services.fraud_consumer.main
```

5) Use the producer CLI to send a test payment (you can implement a quick JSON POST to `/api/v1/payments` or use the `producer_cli` folder).

## Running with Docker Compose

If you provide a `docker-compose.yml` that includes Postgres and Kafka, you can run both services in containers. Example high-level steps:

```bash
# start services: postgres + kafka
docker-compose up -d

# in separate terminals, run detector and consumer inside appropriate containers or locally
```

Note: There is a minimal `docker-compose.yml` file in the repo currently empty — you can copy a standard kafka+postgres compose from examples online and set the same env values used in `src/common/config.py`.

## Project layout tips & notes

- I recommend keeping a single source-of-truth for models in `src/models`. Services should import models from `src.models` rather than redefining them locally.
- Centralized DB and Kafka helpers are in `src/common/` (`db.py`, `kafka_utils.py`, `config.py`) — services should re-use these to avoid duplicate engines or producer/consumer code.
- Use Alembic for schema migrations (the repo includes `alembic` in requirements). Don't rely on `Base.metadata.create_all` in production.

## Troubleshooting

- "Unable to import 'src.models'" or similar: ensure your Python path is configured so `src` is importable (run commands from the project root). Use `PYTHONPATH=.` when running scripts if necessary:

```bash
PYTHONPATH=. uvicorn src.services.detector.app:app --reload
```

- Lint/static import errors: fix misnamed modules (e.g. `user_model.py` vs `user_models.py`) and ensure `src/models/__init__.py` correctly exports the canonical models.

## Next steps / suggestions

- Add a complete `docker-compose.yml` that runs Postgres and Kafka for local development.
- Add unit tests for the consumer logic and API endpoints.
- Add Alembic migration scripts for schema evolution.

If you want, I can:
- Add a sample `docker-compose.yml` for Kafka + Postgres,
- Run the linter and fix remaining import errors,
- Add a small smoke-test script that verifies imports and can create DB tables locally.

---
Updated: 20 October 2025

