from typing import List
from src.services.detector.schemas import PaymentRequest
from src.services.fraud_consumer.rules.base_rule import BaseRule
import redis.asyncio as redis

class RuleEngine:
    def __init__(self, rules: List[BaseRule], redis_service: redis.Redis):
        self.rules = sorted(rules)  # Sort by priority
        self.redis_service = redis_service

    async def evaluate_event(self, event: PaymentRequest) -> tuple[str, float, List[str]]:
        triggered_rules = []
        fraud_score = 0.0

        for rule in self.rules:
            is_triggered, details = await rule.evaluate(event, self.redis_service)
            if is_triggered:
                triggered_rules.append(rule.name)
                fraud_score += rule.threshold  # Simple scoring for example, can be complex

                # Optionally add rule_details to event metadata
                if not event.metadata:
                    event.metadata = {}
                event.metadata[rule.name] = details

                # Short-circuit if a high-priority rule declines
                if rule.name == "ip_blacklist_check":
                    return "decline", 1.0, triggered_rules

        decision = "approve" if fraud_score < 0.5 else "review"  # Example logic
        if fraud_score >= 1.0:
            decision = "decline"

        return decision, fraud_score, triggered_rules
