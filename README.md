# FraudShield

FraudShield is a lightweight, dummy prototype fraud detection microservice suite built with Python. It demonstrates a real-world streaming architecture using **FastAPI** (HTTP ingress), **Kafka** (stream transport), and **PostgreSQL** (durable storage).

The project is designed as:
- A learning reference for distributed microservice architecture.
- A local development environment to simulate streaming systems.
- A foundation for building production-grade fraud detection pipelines.

## 🚀 High-Level Summary

![FraudShield Architecture](https://github.com/kuldeepstechwork/fraudshield/blob/main/docs/A1.png#:~:text=A1.png)

- **Ingest**: A FastAPI "detector" service accepts payment submissions via HTTP and publishes them to a Kafka topic (`raw_payments`).
- **Process**: A Kafka consumer subscribes to `raw_payments`, runs rule-based fraud detection, stores records and alerts in Postgres, and publishes enriched messages downstream.
- **Observe & Scale**: Kafka partitions (country-based by default) enable horizontal scalability and ordered message processing.

**Core principles**:
- Keep synchronous request latency small by offloading heavy tasks to asynchronous stream-based workers.
- Preserve ordering per business key (country).
- Use durable, queryable storage (Postgres) for authoritative data and alerts.

## 🧠 Architecture & Data Flow

1. **Client → Detector API (FastAPI)**  
   - `POST /api/v1/payments/` validates and normalizes incoming payments, assigns a `payment_id`, publishes to Kafka (`raw_payments`), and returns HTTP 202.
2. **Kafka (Raw Topic)**  
   - The `raw_payments` topic receives raw payment messages.
   - Message keys are set to `country`, driving partition routing and per-country ordering.
3. **Consumer (Fraud Detector Worker)**  
   - Subscribes to `raw_payments`, executes fraud detection rules, writes results to Postgres, and publishes enriched messages to downstream topics (`processed_payments`, `fraud_alerts`).
4. **Storage & Observability**  
   - Postgres stores all transactions, fraud scores, and alerts for long-term analysis.
   - Metrics (consumer lag, message rates, latency) can be visualized via Prometheus + Grafana.
5. **Downstream Consumers**  
   - Other services (e.g., analytics, notifications) can subscribe to `processed_payments` or `fraud_alerts`.
  

## ⚙️ Why These Components

- **FastAPI**: Async-first, high-performance HTTP API layer.
- **Kafka (aiokafka)**: Durable, partitioned event streaming with replayability.
- **Postgres (asyncpg + SQLAlchemy)**: Reliable, transactional storage with strong analytical capabilities.
- **Alembic**: Safe database schema migrations.

**Design trade-offs**:
- Kafka adds operational overhead but enables scalability and decoupling.
- Partitioning by country simplifies scaling but can be adjusted to other keys as needed.

## 🧩 Key Implementation Notes

- **ORM Models**: Centralized in `src/models/` with a shared SQLAlchemy `Base`.
- **Utilities**:
  - `src/common/db.py` — database setup
  - `src/common/kafka_utils.py` — Kafka producer/consumer helpers
  - `src/common/config.py` — centralized configuration (Pydantic)
- **Producer Lifecycle**: Long-lived producer instance (`app.state.kafka_producer`).
- **Consumer Commit Strategy**: Manual commits after successful downstream publish (avoiding data loss).
- **Pydantic v2**: Uses modern model configs and JSON encoders.

## 🔄 Partitioning (Country-Based Ordering)

- Messages are keyed by `country` to ensure per-country ordering.
- Default partition count: `3` (configurable via `.env`).
- To inspect or change partition count:
  ```bash
  docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --topic raw_payments --describe
  docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --alter --topic raw_payments --partitions 6


## 🧪 Testing & Load Generation

- Use `src/services/producer_cli/load_test.py` to simulate mixed payment payloads and validate consumer scalability.
- For higher throughput, test direct Kafka production using `aiokafka`.

## ⚡ Operational Considerations

- **Topic Management**: Use a deterministic creation strategy (CI/CD or init container).
- **DLQ**: Implement a dead-letter queue for failed messages.
- **Monitoring**: Export metrics (Prometheus) and monitor consumer lag & latency.
- **Backpressure**: Implement async + bounded concurrency.
- **Schema Registry**: Add Avro/Protobuf for schema compatibility.

## 🧯 Troubleshooting

- **INET Types**: Use Pydantic encoders or normalize before response.
- **aiokafka Issues**: Pin compatible versions in `requirements.txt`.
- **Consumer Group Issues**: Check group ID and connectivity using `kafka-consumer-groups`.

## 🧑‍💻 Developer Notes

- Keep ORM models centralized in `src/models`.
- Maintain a single SQLAlchemy `Base`.
- Use long-lived Kafka producers and commit offsets post-success.
- Implement retries and DLQ for failed messages.

## 📈 Next Steps & Roadmap

- Add deterministic Kafka topic initializer (CI job or init container).
- Implement DLQ + backoff/retry for consumers.
- Add Prometheus metrics and Grafana dashboards.
- Introduce contract testing (JSON Schema/Avro) in CI pipelines.

## 💡 How to Extend and Learn More

This prototype was developed for educational and learning purposes. To deepen your understanding and evolve this project further:

- ✅ Implement machine learning-based fraud scoring on top of the rule engine.
- ✅ Add real-time dashboards (Grafana or Streamlit) to visualize fraud trends.
- ✅ Introduce OpenTelemetry for distributed tracing across API, Kafka, and DB layers.
- ✅ Integrate CI/CD pipelines for automated testing and deployment.
- ✅ Explore container orchestration with Kubernetes for production scaling.
- ✅ Replace rule-based checks with anomaly detection models trained on synthetic data.



