# fraudshield/src/services/detector/dependencies.py

from typing import AsyncGenerator
from aiokafka import AIOKafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession

# Import shared dependencies from src/common
from src.common.db import get_db as get_common_db
from src.common.kafka_utils import get_kafka_producer as get_common_kafka_producer

# Re-export or wrap common dependencies for detector service
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an asynchronous database session."""
    async for session in get_common_db():
        yield session

async def get_kafka_producer_instance() -> AsyncGenerator[AIOKafkaProducer, None]:
    """Provides an AIOKafkaProducer instance."""
    async for producer in get_common_kafka_producer():
        yield producer