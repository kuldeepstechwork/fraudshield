# fraudshield/src/services/fraud_consumer/consumer_logic.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
from decimal import Decimal
import json

# Import ORM models
from src.services.fraud_consumer.models import Payment, User, Merchant, FraudRule, Alert

# --- Placeholder Fraud Detection Logic ---
async def run_fraud_detection_logic(
    payment_data: dict, 
    db_session: AsyncSession
) -> (Decimal, bool, str | None, str):
    """
    Applies fraud rules and/or ML models to determine fraud score and flag.
    Returns (fraud_score, fraud_flag, reason_code, risk_level).
    
    This is where your sophisticated fraud detection will live.
    For now, it uses simple rule-based logic.
    """
    amount = Decimal(payment_data['amount'])
    ip_address = payment_data.get('ip_address')
    country = payment_data.get('country')
    user_id = uuid.UUID(payment_data['user_id']) # Convert to UUID for DB queries

    fraud_score = Decimal("0.10") # Base score
    fraud_flag = False
    reason_code = None
    risk_level = "Low"

    triggered_rules = []

    # Example: Check for high-value transactions
    if amount >= 1000:
        fraud_score += Decimal("0.40")
        triggered_rules.append("HighValueTransaction")

    # Example: Check for high-risk countries (placeholder list)
    high_risk_countries = ["NG", "RU", "CN"]
    if country in high_risk_countries:
        fraud_score += Decimal("0.30")
        triggered_rules.append("HighRiskCountry")

    # Example: Check for multiple transactions from same IP in short time (requires fetching historical data)
    # This is a simplified example, a real check would be more complex and indexed.
    # For now, let's just make a dummy check
    
    # In a real scenario, you'd query the DB for user's past transactions or IP history
    # Example: Get recent payments by this user
    # result = await db_session.execute(
    #     select(Payment).where(
    #         Payment.user_id == user_id,
    #         Payment.timestamp > (datetime.utcnow() - timedelta(minutes=5))
    #     )
    # )
    # recent_payments_count = len(result.scalars().all())
    # if recent_payments_count > 3: # More than 3 payments in 5 minutes
    #     fraud_score += Decimal("0.20")
    #     triggered_rules.append("RapidTransactions")


    # Determine final fraud flag and risk level
    if fraud_score >= 0.70:
        fraud_flag = True
        risk_level = "High"
    elif fraud_score >= 0.40:
        fraud_flag = True
        risk_level = "Medium"
    
    if triggered_rules:
        reason_code = ", ".join(triggered_rules)
    
    return fraud_score, fraud_flag, reason_code, risk_level

# --- Message Processing Function ---
async def process_payment_message(message_data: dict, db_session: AsyncSession):
    """
    Processes a single payment message from Kafka.
    Applies fraud detection logic and persists the result to the database.
    """
    try:
        # Convert incoming string UUIDs and Decimals back to their types
        user_id = uuid.UUID(message_data['user_id'])
        merchant_id = uuid.UUID(message_data['merchant_id'])
        amount = Decimal(message_data['amount'])

        # --- Run Fraud Detection ---
        fraud_score, fraud_flag, reason_code, risk_level = await run_fraud_detection_logic(message_data, db_session)

        # --- Save Payment Record to Database ---
        # If producer provided a client-visible payment_id include it; otherwise generate one
        incoming_payment_id = message_data.get("payment_id")
        if incoming_payment_id:
            try:
                payment_uuid = uuid.UUID(incoming_payment_id)
            except Exception:
                payment_uuid = uuid.uuid4()
        else:
            payment_uuid = uuid.uuid4()

        new_payment = Payment(
            payment_id=payment_uuid,
            user_id=user_id,
            merchant_id=merchant_id,
            amount=amount,
            currency=message_data['currency'],
            payment_method=message_data['payment_method'],
            card_type=message_data.get('card_type'),
            card_last_four=message_data.get('card_last_four'),
            transaction_type=message_data['transaction_type'],
            status="Approved" if not fraud_flag else "Review Required", # Initial status post-detection
            timestamp=datetime.fromisoformat(message_data.get('timestamp')) if message_data.get('timestamp') else datetime.utcnow(),
            ip_address=message_data.get('ip_address'),
            device_info=message_data.get('device_info'),
            country=message_data.get('country'),
            fraud_score=fraud_score,
            fraud_flag=fraud_flag,
            reason_code=reason_code,
            risk_level=risk_level,
        )

        db_session.add(new_payment)
        await db_session.flush()  # Flush to get new_payment.payment_id before commit if needed for alert

        # --- Create Alert if Fraud Flagged ---
        new_alert = None
        if fraud_flag:
            new_alert = Alert(
                alert_id=uuid.uuid4(),
                payment_id=new_payment.payment_id,
                user_id=user_id,
                alert_type="Potential Fraud",
                description=f"Payment flagged with score {fraud_score} (Risk: {risk_level}) due to: {reason_code or 'Various indicators'}",
                timestamp=datetime.utcnow(),
                status="New"  # Analyst needs to review
            )
            db_session.add(new_alert)

        await db_session.commit()
        await db_session.refresh(new_payment)  # Refresh to get latest state including auto-generated fields if any
        if new_alert:
            await db_session.refresh(new_alert)

        print(f"Successfully processed payment {new_payment.payment_id}. Fraud Flag: {new_payment.fraud_flag}, Score: {new_payment.fraud_score}")

        # Return result info for publishing
        result = {
            "payment_id": str(new_payment.payment_id),
            "user_id": str(new_payment.user_id),
            "merchant_id": str(new_payment.merchant_id),
            "amount": str(new_payment.amount),
            "fraud_score": str(new_payment.fraud_score),
            "fraud_flag": bool(new_payment.fraud_flag),
            "risk_level": new_payment.risk_level,
            "status": new_payment.status,
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
        print(f"Error in process_payment_message for data {message_data}: {e}")
        await db_session.rollback() # Rollback transaction on error
        raise