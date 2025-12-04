# FraudShield 🛡️

> A real-time fraud detection microservice suite built with Python, featuring ML-ready rule engine, streaming architecture, and production-grade security.

![FraudShield Architecture](https://github.com/kuldeepstechwork/fraudshield/blob/main/docs/A1.png#:~:text=A1.png)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.123-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Overview

FraudShield is a high-performance, event-driven fraud detection platform that processes payment transactions in real-time. Built with modern Python async patterns, it demonstrates production-ready microservice architecture with:

- **FastAPI** for high-performance HTTP API ingress
- **Apache Kafka** for scalable event streaming
- **PostgreSQL** for durable transactional storage
- **Redis** for real-time fraud rules (velocity checks, blacklists)
- **Rule Engine** for extensible fraud detection logic

### Key Features

✅ **API Key Authentication** - Secure payment endpoints  
✅ **Real-time Fraud Detection** - IP blacklist & velocity rules  
✅ **Async Processing** - Sub-10ms API response times  
✅ **Horizontal Scalability** - Kafka-based partitioning by country  
✅ **Automatic Alerting** - High-risk transaction alerts  
✅ **Production Ready** - Docker Compose deployment included

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Features](#-features)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Production Deployment](#-production-deployment)
- [Troubleshooting](#-troubleshooting)

---

## 🏗️ Architecture

### System Flow

```
Client → FastAPI Detector → Kafka → Consumer (Fraud Engine) → PostgreSQL
                                          ↓
                                       Redis (Rules Cache)
```

### Components

1. **Detector Service** (FastAPI)
   - Validates incoming payments
   - Creates pending payment records in PostgreSQL
   - Publishes events to Kafka `raw_payments` topic
   - Returns HTTP 202 (Accepted) immediately

2. **Consumer Service** (Async Worker)
   - Subscribes to Kafka `raw_payments` topic
   - Runs fraud detection via **RuleEngine**
   - Updates payment status with fraud scores
   - Creates alerts for high-risk transactions
   - Publishes results to downstream topics

3. **Rule Engine**
   - **IP Blacklist Rule**: Checks IP against Redis blacklist
   - **Velocity Rule**: Tracks transaction count per user/hour
   - Extensible architecture for custom rules

4. **Data Stores**
   - **PostgreSQL**: Authoritative payment & alert storage
   - **Redis**: Real-time rule caching and counters
   - **Kafka**: Event streaming and replay capability

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)

### 1. Clone & Setup

```bash
git clone https://github.com/your-username/fraudshield.git
cd fraudshield
cp .env.example .env  # Edit with your configuration
```

### 2. Start Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Zookeeper & Kafka (port 9092)
- Redis (port 6379)
- Detector API (port 8000)
- Fraud Consumer

### 3. Initialize Database

```bash
docker exec fraudshield_detector alembic upgrade head
```

### 4. Create Test User & Merchant

```bash
# Create user
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "user_name": "testuser"}'

# Create merchant  
curl -X POST http://localhost:8000/api/v1/merchants/ \
  -H "Content-Type: application/json" \
  -d '{"merchant_name": "Test Merchant", "industry": "ecommerce"}'
```

### 5. Submit a Payment

```bash
curl -X POST http://localhost:8000/api/v1/payments/ \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID",
    "merchant_id": "YOUR_MERCHANT_ID",
    "amount": 100.00,
    "currency": "USD",
    "payment_method": "credit_card",
    "transaction_type": "sale"
  }'
```

### 6. Check Logs

```bash
# View consumer processing
docker logs -f fraudshield_consumer

# View detector API
docker logs -f fraudshield_detector
```

---

## 🎯 Features

### Security
- **API Key Authentication**: Required `X-API-Key` header for payment submissions
- **Input Validation**: Pydantic schemas with strict type checking
- **Environment Secrets**: All credentials in `.env` file

### Fraud Detection
- **IP Blacklist Rule**: Instant decline for blacklisted IPs (stored in Redis)
- **Velocity Rule**: Tracks transactions per user per time window
- **Risk Scoring**: Aggregated fraud score (0.0 - 10.0)
- **Automatic Decisions**: Approve (<0.5), Review (0.5-1.0), Decline (>1.0)

### Performance
- **Async/Await**: Non-blocking I/O throughout
- **Connection Pooling**: Reusable DB and Kafka connections
- **Kafka Partitioning**: By country for ordered processing
- **Redis Caching**: Sub-millisecond rule lookups

### Observability
- **Structured Logging**: JSON logs with correlation IDs
- **Database Audit Trail**: All payments and alerts persisted
- **Kafka Replay**: Reprocess events for debugging

---

## 📡 API Reference

### Authentication

All payment endpoints require API key authentication:

```bash
-H "X-API-Key: your-secret-key"
```

### Endpoints

#### Submit Payment
```http
POST /api/v1/payments/
Content-Type: application/json
X-API-Key: dev-secret-key

{
  "user_id": "uuid",
  "merchant_id": "uuid",
  "amount": 100.00,
  "currency": "USD",
  "payment_method": "credit_card",
  "transaction_type": "sale",
  "ip_address": "192.168.1.1",  // optional
  "country": "US"               // optional
}

Response: 202 Accepted
{
  "message": "Payment received and sent to Kafka for processing",
  "status": "accepted",
  "payment_id": "uuid"
}
```

#### Get Payment Status
```http
GET /api/v1/payments/{payment_id}

Response: 200 OK
{
  "payment_id": "uuid",
  "status": "Approved",
  "fraud_score": 0.15,
  "fraud_flag": false,
  "risk_level": "Low",
  ...
}
```

#### Get Payment Alerts
```http
GET /api/v1/alerts/payment/{payment_id}

Response: 200 OK
[
  {
    "alert_id": "uuid",
    "alert_type": "Potential Fraud",
    "description": "Flagged: decline. Score: 5.0. Rules: velocity_rule_1h",
    "status": "New"
  }
]
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql+asyncpg://fraudshield_user:your_password@postgres:5432/fraud_detection

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_RAW_PAYMENTS_TOPIC=raw_payments
KAFKA_PROCESSED_PAYMENTS_TOPIC=processed_payments
KAFKA_FRAUD_ALERTS_TOPIC=fraud_alerts
KAFKA_CONSUMER_GROUP_ID=fraud_detector_group
KAFKA_TOPIC_PARTITIONS=3

# Redis
REDIS_URL=redis://redis:6379

# API Security
API_KEY=your-strong-secret-key  # CHANGE THIS!

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
```

### Rule Configuration

Add IPs to Redis blacklist:
```bash
docker exec fraudshield-redis-1 redis-cli SADD global:ip_blacklist "203.0.113.45"
```

---

## 🧪 Testing

### Load Testing

Run the included load test script:

```bash
docker exec fraudshield_detector python src/services/producer_cli/load_test.py \
  --total 100 \
  --concurrency 10
```

This generates:
- Normal transactions
- High-value payments
- Velocity bursts
- Multiple scenarios to test rules

### Manual Testing

Test different fraud scenarios:

```bash
# High-risk amount
curl -X POST http://localhost:8000/api/v1/payments/ \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "...",
    "merchant_id": "...",
    "amount": 15000.00,  # Very high amount
    "currency": "USD",
    "payment_method": "credit_card",
    "transaction_type": "sale"
  }'

# Check consumer logs for fraud score
docker logs fraudshield_consumer --tail 20
```

---

## 🚢 Production Deployment

### Security Checklist

Before deploying to production:

- [ ] Change `API_KEY` to a strong random secret (32+ characters)
- [ ] Update PostgreSQL password
- [ ] Enable TLS/SSL for all services
- [ ] Set up firewall rules (limit port access)
- [ ] Use secrets management (AWS Secrets Manager, Vault)
- [ ] Enable authentication for Kafka and Redis

### Scaling

**Horizontal Scaling:**
```bash
# Scale consumers for higher throughput
docker-compose up -d --scale consumer=3
```

**Kafka Partitions:**
```bash
# Increase partitions for parallel processing
docker exec fraudshield-kafka-1 kafka-topics \
  --bootstrap-server localhost:9092 \
  --alter --topic raw_payments --partitions 10
```

### Monitoring

Recommended stack:
- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and visualization
- **ELK Stack**: Log aggregation and analysis

### High Availability

- Deploy PostgreSQL with replication
- Use Kafka cluster (3+ brokers)
- Redis Cluster or Redis Sentinel
- Load balancer for detector API

---

## 🧯 Troubleshooting

### Consumer Not Processing Messages

**Check Kafka connectivity:**
```bash
docker exec fraudshield_consumer nc -zv kafka 9092
```

**View consumer group status:**
```bash
docker exec fraudshield-kafka-1 kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group fraud_detector_group
```

### Redis Connection Errors

**Verify Redis is running:**
```bash
docker exec fraudshield-redis-1 redis-cli ping
# Should return: PONG
```

**Check connection URL:**
```bash
# In Docker, use service name not localhost
REDIS_URL=redis://redis:6379  # ✅ Correct
REDIS_URL=redis://localhost:6379  # ❌ Wrong
```

### API Returns 403 Forbidden

**Check API key:**
```bash
# Ensure X-API-Key header matches API_KEY in .env
curl -v -H "X-API-Key: dev-secret-key" http://localhost:8000/api/v1/payments/
```

---

## 🛠️ Development

### Project Structure

```
fraudshield/
├── src/
│   ├── common/          # Shared utilities
│   │   ├── config.py    # Configuration
│   │   ├── db.py        # Database connection
│   │   ├── kafka_utils.py
│   │   └── redis_utils.py
│   ├── models/          # SQLAlchemy ORM models
│   ├── services/
│   │   ├── detector/    # FastAPI service
│   │   └── fraud_consumer/  # Kafka consumer
│   │       ├── rule_engine.py
│   │       └── rules/   # Fraud detection rules
├── alembic/            # Database migrations
├── docker-compose.yml
└── requirements.txt
```

### Adding Custom Fraud Rules

1. Create a new rule in `src/services/fraud_consumer/rules/`:

```python
from .base_rule import BaseRule

class CustomRule(BaseRule):
    async def evaluate(self, event, redis_service):
        # Your logic here
        is_triggered = False  # Your condition
        details = "Explanation"
        return is_triggered, details
```

2. Register in `rule_engine.py`:

```python
from .rules.custom_rule import CustomRule

engine = RuleEngine([
    IPBlacklistRule(threshold=10.0, priority=1),
    VelocityRule(threshold=5.0, priority=5),
    CustomRule(threshold=3.0, priority=10),  # Add here
])
```

---

## 📈 Roadmap

- [ ] Machine learning fraud models (Random Forest, XGBoost)
- [ ] GraphQL API support
- [ ] OpenTelemetry distributed tracing
- [ ] Kubernetes deployment manifests
- [ ] Real-time fraud dashboard (Streamlit/React)
- [ ] Device fingerprinting integration
- [ ] Multi-currency support with exchange rates
- [ ] Webhook notifications for alerts

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ using Python, FastAPI, Kafka, and PostgreSQL**
