import logging
import json
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.services.fraud_consumer.models import Payment, Alert
from src.services.fraud_consumer.rule_engine import RuleEngine
from src.services.fraud_consumer.rules.blacklist_rule import IPBlacklistRule
from src.services.fraud_consumer.rules.velocity_rule import VelocityRule
from src.common.redis_utils import get_redis_client
from src.services.detector.schemas import PaymentRequest

logger = logging.getLogger(__name__)

async def process_payment_message(message_data: dict, db_session: AsyncSession):
    """
    Processes a single payment message from Kafka.
    Applies fraud detection logic using RuleEngine and updates the payment record.
    """
    logger.info(f"Processing payment message for user_id={message_data.get('user_id')} amount={message_data.get('amount')}")
    
    try:
        # 1. Parse message into PaymentRequest schema (validates data)
        try:
            payment_request = PaymentRequest(**message_data)
        except Exception as e:
            logger.error(f"Invalid message format: {e}")
            # If we can't parse it, we can't process it. 
            # In a real system, we might DLQ this.
            return None, None

        # 2. Initialize Rule Engine
        async with get_redis_client() as redis_client:
            rules = [IPBlacklistRule(), VelocityRule()]
            rule_engine = RuleEngine(rules, redis_client)

            # 3. Evaluate Fraud
            decision, fraud_score, triggered_rules = await rule_engine.evaluate_event(payment_request)

        # 4. Update Payment Record in DB
        # transaction_id is used as payment_id in app.py
        try:
            payment_id = uuid.UUID(payment_request.transaction_id) 
        except ValueError:
             logger.error(f"Invalid payment_id UUID: {payment_request.transaction_id}")
             return None, None

        payment = await db_session.get(Payment, payment_id)

        if not payment:
            logger.error(f"Payment {payment_id} not found in database. It should have been created by Detector.")
            return None, None

        payment.fraud_score = Decimal(str(fraud_score))
        payment.fraud_flag = (decision != "approve")
        payment.risk_level = "High" if decision == "decline" else ("Medium" if decision == "review" else "Low")
        payment.reason_code = ", ".join(triggered_rules)
        payment.status = "Rejected" if decision == "decline" else ("Review Required" if decision == "review" else "Approved")
        
        # 5. Create Alert if needed
        new_alert = None
        if payment.fraud_flag:
            new_alert = Alert(
                alert_id=uuid.uuid4(),
                payment_id=payment.payment_id,
                user_id=payment.user_id,
                alert_type="Potential Fraud",
                description=f"Flagged: {decision}. Score: {fraud_score}. Rules: {payment.reason_code}",
                timestamp=datetime.utcnow(),
                status="New"
            )
            db_session.add(new_alert)

        await db_session.commit()
        await db_session.refresh(payment)
        if new_alert:
            await db_session.refresh(new_alert)

        logger.info(f"Processed payment {payment.payment_id}. Decision: {decision}")

        # 6. Prepare Result for Downstream
        result = {
            "payment_id": str(payment.payment_id),
            "user_id": str(payment.user_id),
            "merchant_id": str(payment.merchant_id),
            "amount": str(payment.amount),
            "fraud_score": str(payment.fraud_score),
            "fraud_flag": bool(payment.fraud_flag),
            "risk_level": payment.risk_level,
            "status": payment.status,
        }
        
        alert_result = None
        if new_alert:
            alert_result = {
                "alert_id": str(new_alert.alert_id),
                "payment_id": str(new_alert.payment_id),
                "user_id": str(new_alert.user_id),
                "description": new_alert.description,
                "status": new_alert.status,
            }
            
        return result, alert_result

    except Exception as e:
        logger.error(f"Error in process_payment_message: {e}", exc_info=True)
        await db_session.rollback()
        raise