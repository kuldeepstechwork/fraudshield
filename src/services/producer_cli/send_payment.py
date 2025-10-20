# fraudshield/src/services/producer_cli/send_payment.py

import argparse
import asyncio
import json
import logging
import sys
import uuid
from decimal import Decimal
from datetime import datetime

from aiokafka import AIOKafkaProducer
from src.common.config import settings

LOG = logging.getLogger("producer_cli")


def build_test_messages(seed: uuid.UUID | None = None) -> list[dict]:
    """Return a list of test payment dicts (strings for JSON-serializable values).

    If seed is provided, use deterministic UUIDs based on it.
    """
    if seed:
        base = uuid.UUID(int=seed.int)
        u1 = uuid.uuid5(base, "u1")
        u2 = uuid.uuid5(base, "u2")
        u3 = uuid.uuid5(base, "u3")
        m = uuid.uuid5(base, "m1")
    else:
        u1, u2, u3, m = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    now = datetime.utcnow().isoformat()

    low = {
        "user_id": str(u1),
        "merchant_id": str(m),
        "amount": str(Decimal("550.75")),
        "currency": "USD",
        "payment_method": "Credit Card",
        "card_type": "Visa",
        "card_last_four": "5678",
        "transaction_type": "Purchase",
        "ip_address": "203.0.113.45",
        "device_info": {"os": "iOS", "browser": "Safari"},
        "country": "US",
        "timestamp": now,
    }

    high_value = {
        "user_id": str(u2),
        "merchant_id": str(m),
        "amount": str(Decimal("1500.00")),
        "currency": "EUR",
        "payment_method": "Bank Transfer",
        "transaction_type": "Purchase",
        "ip_address": "10.0.0.1",
        "device_info": {"os": "Android", "browser": "Firefox"},
        "country": "DE",
        "timestamp": now,
    }

    high_risk = {
        "user_id": str(u3),
        "merchant_id": str(m),
        "amount": str(Decimal("50.00")),
        "currency": "NGN",
        "payment_method": "Mobile Money",
        "transaction_type": "Purchase",
        "ip_address": "41.0.0.1",
        "device_info": {"os": "Android", "browser": "Chrome"},
        "country": "NG",
        "timestamp": now,
    }

    return [low, high_value, high_risk]


async def send_messages(loop, bootstrap_servers: str, topic: str, messages: list[dict], interval: float = 1.0):
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers, loop=loop)
    try:
        LOG.info("Starting producer to %s", bootstrap_servers)
        await producer.start()
    except Exception as e:
        LOG.exception("Failed to start Kafka producer: %s", e)
        raise

    try:
        for msg in messages:
            try:
                payload = json.dumps(msg, ensure_ascii=False).encode("utf-8")
                LOG.info("Sending message to topic=%s payload=%s", topic, payload)
                await producer.send_and_wait(topic, payload)
                LOG.info("Message sent")
            except Exception:
                LOG.exception("Failed to send message to Kafka")
            await asyncio.sleep(interval)
    finally:
        await producer.stop()


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Send test payments to Kafka (FraudShield)")
    p.add_argument("--bootstrap", default=None, help="Kafka bootstrap servers (overrides .env)")
    p.add_argument("--topic", default=None, help="Kafka topic to send to (overrides .env)")
    p.add_argument("--count", type=int, default=1, help="How many cycles of the three test messages to send")
    p.add_argument("--interval", type=float, default=1.0, help="Seconds between messages")
    p.add_argument("--seed", type=str, default=None, help="Seed UUID for deterministic test IDs")
    p.add_argument("--debug", action="store_true", help="Enable debug logging")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    bootstrap = args.bootstrap or settings.KAFKA_BOOTSTRAP_SERVERS
    topic = args.topic or settings.KAFKA_RAW_PAYMENTS_TOPIC

    seed = None
    if args.seed:
        try:
            seed = uuid.UUID(args.seed)
        except Exception:
            LOG.warning("Invalid seed provided, ignoring")
            seed = None

    # Build message list repeated as requested
    base_messages = build_test_messages(seed=seed)
    messages = base_messages * max(1, args.count)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(send_messages(loop, bootstrap, topic, messages, interval=args.interval))
    finally:
        loop.close()


if __name__ == "__main__":
    main()