# FraudShield

FraudShield is a lightweight, production-oriented fraud detection microservice suite implemented in Python.
It demonstrates a real-world streaming architecture using FastAPI (HTTP ingress), Kafka (streaming transport), and
Postgres (durable storage). The project is structured so it can be used as a learning reference, a local dev
environment, or a starting point for a production-grade fraud pipeline.

This README is written from the perspective of an engineering owner: it explains the architecture, the data flow,
why design decisions were made, how to run and test the system, operational considerations, and next steps for hardening.

## High-level summary

- Ingest: a FastAPI "detector" service accepts payment submissions via HTTP and publishes them to a Kafka topic (`raw_payments`).
- Process: a separate Kafka consumer service subscribes to `raw_payments`, runs rule-based fraud detection, persists payment records and alerts to Postgres, and publishes enriched messages to downstream topics.
- Observe & scale: Kafka partitions are used to shard traffic (this repo uses country-based partitioning by default). Consumers scale horizontally across partitions.

Core principles used here:
- Keep synchronous request latency small by offloading heavy processing to async, stream-based workers.
- Preserve ordering per business key (country) by producing messages with a stable message key.
- Use durable storage (Postgres) for authoritative records and alerts.

## Architecture & data flow

1. Client -> Detector API (FastAPI)
	- Client POSTs a payment payload to `/api/v1/payments/`. The API validates and normalizes the request, generates a client-visible `payment_id`, then publishes the payload to Kafka (`raw_payments`) and returns HTTP 202.

2. Kafka (Raw Topic)
	- `raw_payments` receives raw payment messages. The detector's producer sets the message key to the payment `country` (or `UNK` if missing). This drives partition routing and per-country ordering.

3. Consumer (Fraud Detector Worker)
	- A Kafka consumer (part of `src/services/fraud_consumer/`) subscribes to `raw_payments` as a consumer group. It processes messages, runs rule-based checks, writes payments and alerts to Postgres and publishes processed/enriched messages and alerts to downstream topics (e.g., `processed_payments`, `fraud_alerts`).

4. Storage and Observability
	- Payments, fraud scores and alerts are stored in Postgres. Use Postgres for queryability and long-term forensic analysis.
	- Metrics (consumer lag, message rates, processing latency) should be scraped and visualized (Prometheus + Grafana recommended).

5. Downstream consumers
	- Other services (analytics, notifications) can subscribe to `processed_payments` or `fraud_alerts` for further action.

Diagram (text):

Client -> FastAPI (detector) -> Kafka(raw_payments) -> Consumer(worker) -> Postgres
																				-> Kafka(processed_payments, fraud_alerts)

## Why these components were chosen (engineering rationale)

- FastAPI: minimal, async-first web framework. Good request handling throughput for incoming payment events.
- Kafka (aiokafka): durable, partitioned streaming. Provides ordering by key, retention, replay, and consumer group semantics.
- Postgres (asyncpg + SQLAlchemy): reliable, transactional storage with mature tooling for analytical queries and joins.
- Alembic: migration management for evolving schemas safely in production.

Design trade-offs:
- Using Kafka adds operational complexity but provides decoupling and better scalability and replayability compared to direct HTTP-to-worker patterns.
- Partitioning by country gives per-country ordering and simpler scaling, but is a coarse partitioning scheme — choose a partition key that matches your operational needs and cardinality.

## Key implementation notes (repo ownership)

- Single source of ORM truth: `src/models/` contains canonical SQLAlchemy models and a shared `Base` used across services (necessary for alembic autogenerate).
- Centralized utilities: `src/common/db.py` (database engine and session helpers), `src/common/kafka_utils.py` (producer/consumer helpers), `src/common/config.py` (Pydantic settings).
- Long-lived producer: the detector opens a single long-lived aiokafka producer stored on `app.state.kafka_producer` to avoid costly create/close per request.
- Manual commit strategy: the consumer uses manual commits (enable_auto_commit=False) and commits offsets only after successful processing and downstream publish, preventing data loss on failures.
- Pydantic v2: schemas use `model_config` and `json_encoders` for types like Decimal and ipaddress to avoid serialization issues.

## Partitioning behavior (country-based ordering)

- By default, messages are produced with `key=country` so all messages for a given country are routed to the same partition. This preserves ordering for that key and enables per-country processing guarantees.
- Topics created by the detector on startup honor `KAFKA_TOPIC_PARTITIONS` (default is 3). You can change this value in `.env`.

Important operational notes:
- If a topic already exists with a different partition count, creating the topic again will not change partitions. To use multiple partitions you must either:
  - Increase partitions for the existing topic (allowed), or
  - Delete and recreate the topic (local dev) so the detector creates it with the new partition count.

Commands to inspect/alter partitions (example using the Kafka container):

```bash
# Inspect current partition count
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --topic raw_payments --describe

# Increase partitions (e.g., to 6)
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --alter --topic raw_payments --partitions 6

# Verify
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --topic raw_payments --describe
```

## How to run (developer flow)

1) Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Create `.env` in repo root (example):

```env
DATABASE_URL=postgresql+asyncpg://fraud_user:fraudpass@localhost/fraudshield_db
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_RAW_PAYMENTS_TOPIC=raw_payments
KAFKA_PROCESSED_PAYMENTS_TOPIC=processed_payments
KAFKA_FRAUD_ALERTS_TOPIC=fraud_alerts
KAFKA_CONSUMER_GROUP_ID=fraudshield_consumer_group
KAFKA_TOPIC_PARTITIONS=3
API_HOST=0.0.0.0
API_PORT=8000
```

3) Start Postgres + Kafka (recommended via docker-compose). The repository includes a `docker-compose.yml` you can adapt; a sample compose that includes Zookeeper, Kafka and Postgres is a standard pattern.

4) Run database migrations (Alembic):

```bash
# Create revision (if models changed)
alembic revision --autogenerate -m "add some models"

# Apply migrations
alembic upgrade head
```

5) Start the detector API (development):

```bash
# from project root
uvicorn src.services.detector.main:app --reload --host 0.0.0.0 --port 8000
```

6) Start the consumer worker (separate terminal/process):

```bash
python -m src.services.fraud_consumer.main
```

7) Send a test payment (example using curl):

```bash
curl -X POST http://localhost:8000/api/v1/payments/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": "<uuid>", "merchant_id": "<uuid>", "amount": "12.34", "currency":"USD", "payment_method":"card", "card_last_four":"4242", "country":"US"}'
```

8) Verify Kafka routing by consuming specific partitions (see partition commands above).

## Testing & load generation

- A load test script exists at `src/services/producer_cli/load_test.py` which can send mixed payloads to the detector API and exercise fraud rules. Use it to validate throughput and consumer scaling.
- For higher-throughput tests consider bypassing HTTP and producing directly to Kafka with an aiokafka-based producer.

## Operational considerations and recommendations

- Topic management: prefer a deterministic topic creation tool (CI job or an init container) to avoid race conditions in startup. The detector attempts to create topics on startup but that's best-effort in dev.
- Dead-letter queue (DLQ): add a DLQ topic and retry policy for poison messages or repeated processing failures.
- Monitoring: export metrics (Prometheus) from FastAPI and consumer. Monitor consumer lag and processing latency. Alert on consumer group lag and error rate.
- Backpressure: design consumer processing with bounded concurrency and async I/O so spikes do not exhaust memory.
- Schema registry: consider adding a schema registry (Avro/Protobuf/JSON-Schema) for strict schema compatibility across producers/consumers.

## Troubleshooting

- Pydantic / INET types: Postgres INET columns map to Python `ipaddress` objects. Use `json_encoders` in Pydantic models or normalize values in CRUD before returning responses to avoid validation errors.
- aiokafka version issues: if you see install/runtime incompatibilities, check `requirements.txt` (this repo pins `aiokafka` to a known-compatible version) and ensure the runtime image uses that exact version.
- Consumer not joining group: check broker connectivity and the consumer group id. Use `kafka-consumer-groups` to inspect members and lag.

## Developer notes / ownership checklist

- Keep models centralized in `src/models` and export them from `src/models/__init__.py`.
- Keep a single SQLAlchemy `Base` and reuse it across services (required for alembic autogenerate).
- Producer lifecycle: keep a single long-lived producer on the FastAPI app state.
- Consumer commit strategy: commit offsets only after downstream publish succeeds; log and send failing messages to DLQ after N retries.

## Next steps & roadmap

1. Add a deterministic Kafka topic init container or CI job for creating topics with exact partition counts and ACLs.
2. Add a DLQ and backoff/retry middleware for consumers.
3. Add Prometheus metrics and Grafana dashboards for consumer lag and processing latency.
4. Add contract tests (JSON-schema or Avro) and CI gates for schema compatibility.

---
Updated: 25 October 2025

