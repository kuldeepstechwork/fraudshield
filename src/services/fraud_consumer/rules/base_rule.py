from abc import ABC, abstractmethod
from src.services.detector.schemas import PaymentRequest
import redis.asyncio as redis

class BaseRule(ABC):
    def __init__(self, name: str, threshold: float = 0.0, priority: int = 10):
        self.name = name
        self.threshold = threshold
        self.priority = priority  # Lower number = higher priority

    @abstractmethod
    async def evaluate(self, event: PaymentRequest, redis_service: redis.Redis) -> tuple[bool, dict]:
        """
        Evaluates the rule against the payment event.
        Returns (is_triggered, rule_details).
        """
        pass

    def __lt__(self, other):
        return self.priority < other.priority
