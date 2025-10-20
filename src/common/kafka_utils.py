# fraudshield/src/common/kafka_utils.py

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from src.common.config import settings
from typing import AsyncGenerator

async def get_kafka_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

async def get_kafka_consumer(topic: str, group_id: str, auto_offset_reset: str = "earliest") -> AsyncGenerator[AIOKafkaConsumer, None]:
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        auto_offset_reset=auto_offset_reset # Start reading from the beginning if no offset is committed
    )
    await consumer.start()
    try:
        yield consumer
    finally:
        await consumer.stop()