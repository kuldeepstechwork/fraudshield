import asyncio
import json
from fraudshield.src.common.kafka_utils import get_kafka_consumer
from fraudshield.src.common.db import get_db
from fraudshield.src.models.payment_models import Payment
from fraudshield.src.services.detector.schemas import FraudDecisionEvent
from fraudshield.src.common.config import settings
from sqlalchemy.dialects.postgresql import insert

async def main():
    batch = []
    batch_size = 100
    batch_interval = 10  # seconds

    async with get_kafka_consumer(
        settings.KAFKA_PROCESSED_PAYMENTS_TOPIC,
        f"{settings.KAFKA_CONSUMER_GROUP_ID}_persistor"
    ) as consumer, get_db() as db_session:
        last_commit_time = asyncio.get_event_loop().time()

        while True:
            try:
                msg = await asyncio.wait_for(consumer.getone(), timeout=batch_interval)
                decision_data = json.loads(msg.value)
                batch.append(decision_data)

                if len(batch) >= batch_size:
                    await commit_batch(db_session, batch)
                    await consumer.commit()
                    batch = []
                    last_commit_time = asyncio.get_event_loop().time()

            except asyncio.TimeoutError:
                if batch:
                    await commit_batch(db_session, batch)
                    await consumer.commit()
                    batch = []
                last_commit_time = asyncio.get_event_loop().time()
            except Exception as e:
                print(f"Error processing message: {e}")

async def commit_batch(db_session, batch):
    if not batch:
        return

    print(f"Committing batch of {len(batch)} decisions.")

    for decision_data in batch:
        stmt = (
            insert(Payment)
            .values(decision_data)
            .on_conflict_do_update(
                index_elements=['payment_id'],
                set_=dict(
                    status=decision_data['decision'],
                    fraud_score=decision_data['fraud_score'],
                    risk_level="High" if decision_data['fraud_score'] > 0.75 else ("Medium" if decision_data['fraud_score'] > 0.5 else "Low"),
                    fraud_flag=decision_data['decision'] == 'decline',
                    reason_code=",".join(decision_data['rules_triggered'])
                )
            )
        )
        await db_session.execute(stmt)
    await db_session.commit()

if __name__ == "__main__":
    asyncio.run(main())
