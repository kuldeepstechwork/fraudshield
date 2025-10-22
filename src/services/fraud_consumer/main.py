# fraudshield/src/services/fraud_consumer/main.py

import asyncio
import json
from contextlib import asynccontextmanager
import logging

# Import common utilities
from src.common.config import settings
from src.common.db import SessionLocal, engine, Base
from src.common.kafka_utils import get_kafka_consumer
from aiokafka import AIOKafkaProducer
from datetime import datetime
# Import consumer-specific logic and models
from src.services.fraud_consumer.consumer_logic import process_payment_message
import src.services.fraud_consumer.models # Ensure models are loaded

# Import ALL ORM models from the centralized location to ensure Base.metadata sees them
import src.models.payment_models
import src.models.user_models
import src.models.fraud_models

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def consume_messages():
    """
    Main function for the Kafka consumer.
    Connects to Kafka, consumes messages, and delegates processing.
    """
    producer = getattr(consume_messages, "producer", None)
    created_producer = False
    if producer is None:
        producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        await producer.start()
        # save producer so subsequent calls reuse it (and so we can clean it up later)
        setattr(consume_messages, "producer", producer)
        created_producer = True

    logger.info(f"Starting Kafka consumer for topic '{settings.KAFKA_RAW_PAYMENTS_TOPIC}' with group_id '{settings.KAFKA_CONSUMER_GROUP_ID}'...")

    try:
        async with get_kafka_consumer(
            settings.KAFKA_RAW_PAYMENTS_TOPIC,
            settings.KAFKA_CONSUMER_GROUP_ID
        ) as consumer:
            # Diagnostic logs: show subscription and assignment after start
            try:
                logger.info(f"Consumer subscription: {consumer.subscription()}")
                # assignment() may be empty until rebalance completes, but log it anyway
                logger.info(f"Consumer assignment after start: {consumer.assignment()}")
            except Exception:
                logger.exception("Failed to read consumer subscription/assignment")

            async for msg in consumer:
                logger.info(f"Consumed message: Topic={msg.topic}, Partition={msg.partition}, Offset={msg.offset}")
                try:
                    message_data = json.loads(msg.value.decode('utf-8'))
                    
                    # Create a new async DB session for each message
                    async with SessionLocal() as db_session:
                        result, alert_result = await process_payment_message(message_data, db_session)

                    # Publish processed result to Kafka (so other services can react)
                    try:
                        if result:
                            await producer.send_and_wait(settings.KAFKA_PROCESSED_PAYMENTS_TOPIC, json.dumps(result).encode("utf-8"))
                        if alert_result:
                            await producer.send_and_wait(settings.KAFKA_FRAUD_ALERTS_TOPIC, json.dumps(alert_result).encode("utf-8"))

                        # Manually commit offset after successful processing and publishing
                        await consumer.commit()
                        logger.info(f"Successfully processed and committed offset {msg.offset}.")
                    except Exception as e:
                        logger.error(f"Failed to publish processed result or commit offset for offset {msg.offset}: {e}", exc_info=True)
                        # Optionally: send to DLQ or handle retry. Offset NOT committed so message will be retried.
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from Kafka message at offset {msg.offset}: {e}")
                except Exception as e:
                    logger.error(f"Unhandled error processing message at offset {msg.offset}: {e}", exc_info=True)
                
    except asyncio.CancelledError:
        logger.info(f"Consumer task cancelled.")
    except Exception as e:
        logger.critical(f"Consumer encountered an unrecoverable error: {e}", exc_info=True)
    finally:
        if created_producer:
            try:
                await producer.stop()
            finally:
                # remove saved attribute to avoid leaking between runs
                if hasattr(consume_messages, "producer"):
                    delattr(consume_messages, "producer")
        logger.info(f"Kafka consumer stopped.")

@asynccontextmanager
async def lifespan_consumer():
    """
    Handles startup and shutdown events for the consumer application.
    """
    logger.info(f"Fraud Consumer service starting...")
    # Optional: Create all tables for development. Use Alembic in production.
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    # logger.info(f"Database tables checked/created (if create_all was enabled).")

    # Start the consumer task in the background
    consumer_task = asyncio.create_task(consume_messages())
    yield
    # On shutdown, cancel the consumer task
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass # Expected when cancelled
    logger.info(f"Fraud Consumer service shutting down gracefully.")


async def _main():
    # Run the lifespan manager and keep the process alive until cancelled.
    async with lifespan_consumer():
        # Wait forever until the process is interrupted (Ctrl+C / SIGTERM)
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("Fraud Consumer stopped by user.")