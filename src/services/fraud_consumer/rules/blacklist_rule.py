from src.services.fraud_consumer.rules.base_rule import BaseRule
from src.services.detector.schemas import PaymentRequest
import redis.asyncio as redis

class IPBlacklistRule(BaseRule):
    def __init__(self, name: str = "ip_blacklist_check"):
        super().__init__(name, priority=1)  # Highest priority, quick reject

    async def evaluate(self, event: PaymentRequest, redis_service: redis.Redis) -> tuple[bool, dict]:
        if not event.ip_address:
            return False, {}

        is_blacklisted = await redis_service.sismember("global:ip_blacklist", event.ip_address)
        return is_blacklisted, {"ip_address": event.ip_address}
