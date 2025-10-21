# fraudshield/src/common/kafka_utils.py
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from src.common.config import settings
from typing import AsyncGenerator
import asyncio

async def get_kafka_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

async def get_kafka_consumer(
    topic: str,
    group_id: str,
    auto_offset_reset: str = "earliest"
) -> AsyncGenerator[AIOKafkaConsumer, None]:
    # Retry loop in case Kafka is not ready
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
            break
        except Exception as e:
            if i < 4:
                await asyncio.sleep(5)
            else:
                raise e

    try:
        yield consumer
    finally:
        await consumer.stop()
