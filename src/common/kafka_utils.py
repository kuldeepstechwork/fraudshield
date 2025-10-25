# fraudshield/src/common/kafka_utils.py
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from src.common.config import settings
from typing import AsyncGenerator
from contextlib import asynccontextmanager
import asyncio
import logging
import json

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_kafka_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    # Configure key and value serializers so callers can pass human-friendly keys (like country codes)
    # and dicts/bytes for values. If caller already encodes bytes for value, the value_serializer
    # will pass them through.
    def _key_serializer(k):
        if k is None:
            return None
        if isinstance(k, (bytes, bytearray)):
            return bytes(k)
        return str(k).encode("utf-8")

    def _value_serializer(v):
        if v is None:
            return None
        # bytes already encoded
        if isinstance(v, (bytes, bytearray)):
            return bytes(v)
        # If caller passed a dict or other object, JSON-encode it
        try:
            return json.dumps(v).encode("utf-8")
        except Exception:
            # fallback: str encode
            return str(v).encode("utf-8")

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        key_serializer=_key_serializer,
        value_serializer=_value_serializer,
    )
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()


@asynccontextmanager
async def get_kafka_consumer(
    topic: str,
    group_id: str,
    auto_offset_reset: str = "earliest"
) -> AsyncGenerator[AIOKafkaConsumer, None]:
    # Retry loop in case Kafka is not ready
    consumer = None
    for i in range(5):
        try:
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=False  # prefer manual commit after successful processing
            )
            await consumer.start()
            logger.info(f"Kafka consumer started for topic={topic} group_id={group_id} bootstrap={settings.KAFKA_BOOTSTRAP_SERVERS}")
            break
        except Exception as e:
            if i < 4:
                await asyncio.sleep(5)
            else:
                raise e

    try:
        yield consumer
    finally:
        if consumer is not None:
            await consumer.stop()
