# fraudshield/src/services/detector/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.common.db import engine, Base
from src.common.config import settings
from datetime import datetime

# ---------------------------------------------------------------------
# Compatibility patch for aiokafka + kafka-python>=2.0
# ---------------------------------------------------------------------
import kafka.conn  # must be imported before aiokafka
if not hasattr(kafka.conn, "collect_hosts"):
    def collect_hosts(hosts, **kwargs):
        # aiokafka expects this helper to exist in kafka-python<2.0
        return hosts
    kafka.conn.collect_hosts = collect_hosts

# Now import aiokafka safely
from aiokafka import AIOKafkaProducer
try:
    # aiokafka exposes the admin client under aiokafka.admin
    from aiokafka.admin import AIOKafkaAdminClient
except Exception:
    AIOKafkaAdminClient = None

# NewTopic helper is provided by kafka-python's admin module
from kafka.admin import NewTopic

# ---------------------------------------------------------------------
# Import API routers
# ---------------------------------------------------------------------
from src.services.detector.api.endpoints_v1 import router as v1_router
from src.services.detector.api.health import router as health_router

# Import ALL ORM models to ensure SQLAlchemy knows about them for `Base.metadata.create_all`
import src.models.payment_models
import src.models.user_models
import src.models.fraud_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    """
    print(f"[{datetime.utcnow().isoformat()}] Detector service starting...")

    # Ensure Kafka topics exist before producer/consumer operations
    try:
        admin = AIOKafkaAdminClient(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        await admin.start()
        existing = await admin.list_topics()
        topics_to_ensure = [
            settings.KAFKA_RAW_PAYMENTS_TOPIC,
            settings.KAFKA_PROCESSED_PAYMENTS_TOPIC,
            settings.KAFKA_FRAUD_ALERTS_TOPIC,
        ]
        new_topics = [
            NewTopic(name=t, num_partitions=1, replication_factor=1)
            for t in topics_to_ensure if t not in existing
        ]
        if new_topics:
            await admin.create_topics(new_topics=new_topics)
            print(f"Created topics: {[t.name for t in new_topics]}")
    except Exception as e:
        print(f"Warning: failed to ensure Kafka topics on startup: {e}")
    finally:
        try:
            await admin.stop()
        except Exception:
            pass

    # Start Kafka producer and attach to app state
    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    app.state.kafka_producer = producer

    yield  # Application runs here

    print(f"[{datetime.utcnow().isoformat()}] Detector service shutting down...")
    try:
        await app.state.kafka_producer.stop()
    except Exception:
        pass


app = FastAPI(
    title="FraudShield Detector API",
    version="1.0.0",
    description="API for ingesting payments and querying fraud status in real-time.",
    lifespan=lifespan
)

app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(v1_router, prefix="/api/v1", tags=["API v1"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.services.detector.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
