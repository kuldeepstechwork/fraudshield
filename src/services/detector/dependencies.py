# fraudshield/src/services/detector/dependencies.py

from typing import AsyncGenerator
from aiokafka import AIOKafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

# Import shared dependencies from src/common
from src.common.db import get_db as get_common_db
from src.common.kafka_utils import get_kafka_producer as get_common_kafka_producer


# Re-export or wrap common dependencies for detector service
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an asynchronous database session."""
    async for session in get_common_db():
        yield session


async def get_kafka_producer_instance(request: Request) -> AsyncGenerator[AIOKafkaProducer, None]:
    """Provides an AIOKafkaProducer instance.

    Prefer the app-level producer (created at startup and stored in app.state.kafka_producer).
    Fall back to the shared common generator if not present (for tests/local runs).
    """
    app = request.app
    producer = getattr(app.state, "kafka_producer", None)
    if producer is not None:
        # Yield the long-lived producer (do not stop it here)
        yield producer
        return

    # Fallback: use the common per-request producer generator
    async for producer in get_common_kafka_producer():
        yield producer