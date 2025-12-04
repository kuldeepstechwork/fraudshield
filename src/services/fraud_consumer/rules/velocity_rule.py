from src.services.fraud_consumer.rules.base_rule import BaseRule
from src.services.detector.schemas import PaymentRequest
import redis.asyncio as redis

class VelocityRule(BaseRule):
    def __init__(self, name: str = "velocity_rule_1h", threshold: float = 5, time_window_seconds: int = 3600):
        super().__init__(name, threshold, priority=5)  # High priority
        self.time_window_seconds = time_window_seconds

    async def evaluate(self, event: PaymentRequest, redis_service: redis.Redis) -> tuple[bool, dict]:
        key = f"user:{event.user_id}:tx_count_last_{self.time_window_seconds}s"
        current_count = await redis_service.incr(key)
        await redis_service.expire(key, self.time_window_seconds)

        is_triggered = current_count > self.threshold
        return is_triggered, {"current_count": current_count, "threshold": self.threshold}
