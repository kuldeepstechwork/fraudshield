# fraudshield/src/services/producer_cli/send_payment.py

import asyncio
import json
import uuid
from decimal import Decimal
from datetime import datetime

from aiokafka import AIOKafkaProducer
from src.common.config import settings 


async def send_test_payments():
    """
    Sends various test payment messages to the Kafka raw payments topic.
    """
    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    try:
        # Generate some consistent test IDs for users and merchants
        test_user_id_low_risk = uuid.uuid4()
        test_user_id_high_value = uuid.uuid4()
        test_user_id_high_risk_country = uuid.uuid4()
        test_merchant_id_general = uuid.uuid4()

        # --- Low-risk payment ---
        payment_data_low_risk = {
            "user_id": str(test_user_id_low_risk),
            "merchant_id": str(test_merchant_id_general),
            "amount": str(Decimal("550.75")),
            "currency": "USD",
            "payment_method": "Credit Card",
            "card_type": "Visa",
            "card_last_four": "5678",
            "transaction_type": "Purchase",
            "ip_address": "203.0.113.45",
            "device_info": {"os": "iOS", "browser": "Safari"},
            "country": "US",
            "timestamp": datetime.utcnow().isoformat() # Include timestamp
        }

        # --- High-value payment (to trigger rule) ---
        payment_data_high_value = {
            "user_id": str(test_user_id_high_value),
            "merchant_id": str(test_merchant_id_general),
            "amount": str(Decimal("1500.00")), # Amount >= 1000
            "currency": "EUR",
            "payment_method": "Bank Transfer",
            "transaction_type": "Purchase",
            "ip_address": "10.0.0.1",
            "device_info": {"os": "Android", "browser": "Firefox"},
            "country": "DE",
            "timestamp": datetime.utcnow().isoformat()
        }

        # --- High-risk country payment (to trigger rule) ---
        payment_data_high_risk_country = {
            "user_id": str(test_user_id_high_risk_country),
            "merchant_id": str(test_merchant_id_general),
            "amount": str(Decimal("50.00")),
            "currency": "NGN",
            "payment_method": "Mobile Money",
            "transaction_type": "Purchase",
            "ip_address": "41.0.0.1",
            "device_info": {"os": "Android", "browser": "Chrome"},
            "country": "NG", # High-risk country
            "timestamp": datetime.utcnow().isoformat()
        }

        print(f"Sending low-risk test payment to topic '{settings.KAFKA_RAW_PAYMENTS_TOPIC}'...")
        await producer.send_and_wait(settings.KAFKA_RAW_PAYMENTS_TOPIC, json.dumps(payment_data_low_risk).encode('utf-8'))
        print("Low-risk payment sent!")
        await asyncio.sleep(1) # Small delay

        print(f"Sending high-value test payment to topic '{settings.KAFKA_RAW_PAYMENTS_TOPIC}'...")
        await producer.send_and_wait(settings.KAFKA_RAW_PAYMENTS_TOPIC, json.dumps(payment_data_high_value).encode('utf-8'))
        print("High-value payment sent!")
        await asyncio.sleep(1) # Small delay

        print(f"Sending high-risk country test payment to topic '{settings.KAFKA_RAW_PAYMENTS_TOPIC}'...")
        await producer.send_and_wait(settings.KAFKA_RAW_PAYMENTS_TOPIC, json.dumps(payment_data_high_risk_country).encode('utf-8'))
        print("High-risk country payment sent!")


    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(send_test_payments())