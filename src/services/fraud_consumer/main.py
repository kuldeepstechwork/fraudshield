# fraudshield/src/services/fraud_consumer/main.py

import asyncio
import json
from contextlib import asynccontextmanager

# Import common utilities
from src.common.config import settings
from src.common.db import SessionLocal, engine, Base
from src.common.kafka_utils import get_kafka_consumer

# Import consumer-specific logic and models
from src.services.fraud_consumer.consumer_logic import process_payment_message
import src.services.fraud_consumer.models # Ensure models are loaded

# Import ALL ORM models from the centralized location to ensure Base.metadata sees them
import src.models.payment_models
import src.models.user_models
import src.models.fraud_models


async def consume_messages():
    """
    Main function for the Kafka consumer.
    Connects to Kafka, consumes messages, and delegates processing.
    """
    # Use the async generator to get a consumer instance
    consumer_generator = get_kafka_consumer(
        settings.KAFKA_RAW_PAYMENTS_TOPIC,
        settings.KAFKA_CONSUMER_GROUP_ID
    )
    consumer = await anext(consumer_generator) # Get the consumer from the generator

    print(f"[{datetime.utcnow().isoformat()}] Starting Kafka consumer for topic '{settings.KAFKA_RAW_PAYMENTS_TOPIC}' with group_id '{settings.KAFKA_CONSUMER_GROUP_ID}'...")

    try:
        async for msg in consumer:
            print(f"[{datetime.utcnow().isoformat()}] Consumed message: Topic={msg.topic}, Partition={msg.partition}, Offset={msg.offset}")
            try:
                message_data = json.loads(msg.value.decode('utf-8'))
                
                # Create a new async DB session for each message
                async with SessionLocal() as db_session:
                    await process_payment_message(message_data, db_session)

                # Manually commit offset after successful processing
                # For high throughput, consider committing in batches.
                await consumer.commit()
                
            except json.JSONDecodeError as e:
                print(f"[{datetime.utcnow().isoformat()}] Error decoding JSON from Kafka message at offset {msg.offset}: {e}")
            except Exception as e:
                print(f"[{datetime.utcnow().isoformat()}] Unhandled error processing message at offset {msg.offset}: {e}")
            
    except asyncio.CancelledError:
        print(f"[{datetime.utcnow().isoformat()}] Consumer task cancelled.")
    except Exception as e:
        print(f"[{datetime.utcnow().isoformat()}] Consumer encountered an unrecoverable error: {e}")
    finally:
        await consumer_generator.aclose() # Ensure the consumer is properly stopped
        print(f"[{datetime.utcnow().isoformat()}] Kafka consumer stopped.")

@asynccontextmanager
async def lifespan_consumer():
    """
    Handles startup and shutdown events for the consumer application.
    """
    print(f"[{datetime.utcnow().isoformat()}] Fraud Consumer service starting...")
    # Optional: Create all tables for development. Use Alembic in production.
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    # print(f"[{datetime.utcnow().isoformat()}] Database tables checked/created (if create_all was enabled).")

    # Start the consumer task in the background
    consumer_task = asyncio.create_task(consume_messages())
    yield
    # On shutdown, cancel the consumer task
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass # Expected when cancelled
    print(f"[{datetime.utcnow().isoformat()}] Fraud Consumer service shutting down gracefully.")


if __name__ == "__main__":
    from datetime import datetime
    # This block allows running the consumer directly as a Python script
    try:
        asyncio.run(lifespan_consumer().__aenter__()) # Enter lifespan manually for direct run
        asyncio.run(asyncio.sleep(9999999)) # Keep consumer running until interrupted
    except KeyboardInterrupt:
        print(f"[{datetime.utcnow().isoformat()}] Fraud Consumer stopped by user.")
    finally:
        asyncio.run(lifespan_consumer().__aexit__(None, None, None)) # Exit lifespan manually