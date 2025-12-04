#fraudshield/src/services/detector/api/endpoints_v1.py

from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from aiokafka import AIOKafkaProducer
import json
import uuid
from decimal import Decimal
from typing import List

# Import Pydantic schemas
from src.services.detector.schemas import (
    PaymentCreate,
    PaymentResponse,
    UserCreate,
    UserResponse,
    MerchantCreate,
    MerchantResponse,
    AlertResponse,
    PaymentFraudStatus,
    FraudRuleResponse,
)

# Import CRUD operations
from src.services.detector import crud

# Import dependencies
from src.services.detector.dependencies import get_db_session, get_kafka_producer_instance

# Import config for Kafka topic names
from src.common.config import settings
import logging

LOG = logging.getLogger("detector.api")

router = APIRouter()

# --- Security ---
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == settings.API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )

# ----------------------
# User Endpoints
# ----------------------
@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_data: UserCreate, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Creates a new user.
    """
    existing_user = await crud.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    new_user = await crud.create_user(db, user_data)
    return new_user

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_endpoint(
    user_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves user details by ID.
    """
    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# ----------------------
# Merchant Endpoints
# ----------------------
@router.post("/merchants/", response_model=MerchantResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant_endpoint(
    merchant_data: MerchantCreate, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Creates a new merchant.
    """
    existing_merchant = await crud.get_merchant_by_name(db, merchant_data.merchant_name)
    if existing_merchant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Merchant name already exists")
    
    new_merchant = await crud.create_merchant(db, merchant_data)
    return new_merchant

@router.get("/merchants/{merchant_id}", response_model=MerchantResponse)
async def get_merchant_endpoint(
    merchant_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves merchant details by ID.
    """
    merchant = await crud.get_merchant_by_id(db, merchant_id)
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")
    return merchant

# ----------------------
# Payment Endpoints
# ----------------------
@router.post("/payments/", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def process_payment_endpoint(
    payment_data: PaymentCreate,
    api_key: str = Depends(get_api_key),
    producer: AIOKafkaProducer = Depends(get_kafka_producer_instance),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Receives payment transaction data and sends it to Kafka for asynchronous fraud detection.
    """
    # Validate user
    user = await crud.get_user_by_id(db, payment_data.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Validate merchant
    merchant = await crud.get_merchant_by_id(db, payment_data.merchant_id)
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")

    try:
        # Generate a client-visible payment_id so the caller can poll status
        client_payment_id = uuid.uuid4()

        # Create a pending payment record in the database
        from src.models import Payment
        pending_payment = Payment(
            payment_id=client_payment_id,
            user_id=payment_data.user_id,
            merchant_id=payment_data.merchant_id,
            amount=payment_data.amount,
            currency=payment_data.currency,
            payment_method=payment_data.payment_method,
            card_type=payment_data.card_type,
            card_last_four=payment_data.card_last_four,
            transaction_type=payment_data.transaction_type,
            status="Pending",
            ip_address=payment_data.ip_address,
            device_info=payment_data.device_info,
            country=payment_data.country,
        )
        db.add(pending_payment)
        await db.commit()
        await db.refresh(pending_payment)

        # Convert Pydantic model to dict and include client-generated id
        payment_dict = payment_data.model_dump()
        payment_dict["payment_id"] = str(client_payment_id)
        payment_dict["transaction_id"] = str(client_payment_id)  # Use payment_id as transaction_id
        payment_dict["idempotency_key"] = str(client_payment_id)  # Use same for idempotency

        # Convert Decimal/UUID for JSON serialization
        for k, v in list(payment_dict.items()):
            if isinstance(v, Decimal):
                payment_dict[k] = str(v)
            elif isinstance(v, uuid.UUID):
                payment_dict[k] = str(v)

        message_bytes = json.dumps(payment_dict).encode("utf-8")

        # Use the country field as the partitioning key so all payments from the
        # same country are routed to the same topic partition. Default to 'UNK'.
        country_key = payment_dict.get("country") or "UNK"

        # Log payload before sending for debugging
        LOG.info("Sending payment message to Kafka topic=%s country=%s payload=%s",
                 settings.KAFKA_RAW_PAYMENTS_TOPIC, country_key, payment_dict)

        # Send to Kafka with a key (country) to control partitioning
        # producer has been configured with key/value serializers in app startup
        await producer.send_and_wait(
            settings.KAFKA_RAW_PAYMENTS_TOPIC,
            value=message_bytes,
            key=country_key,
        )

        # Return accepted and the client-visible payment id so callers can query later
        return {"message": "Payment received and sent to Kafka for processing", "status": "accepted", "payment_id": str(client_payment_id)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send payment to Kafka: {e}"
        )

@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment_status_endpoint(
    payment_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves the current status and fraud details of a processed payment.
    """
    payment = await crud.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment

@router.get("/payments/{payment_id}/fraud-status", response_model=PaymentFraudStatus)
async def get_payment_fraud_status_endpoint(
    payment_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves a simplified fraud status for a payment.
    """
    payment = await crud.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment

# ----------------------
# Fraud Rules Endpoints
# ----------------------
@router.get("/fraud-rules/", response_model=List[FraudRuleResponse])
async def get_all_fraud_rules_endpoint(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves a list of all active fraud rules.
    """
    rules = await crud.get_active_fraud_rules(db)
    return rules

# ----------------------
# Alerts Endpoints
# ----------------------
@router.get("/alerts/payment/{payment_id}", response_model=List[AlertResponse])
async def get_alerts_for_payment_endpoint(
    payment_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves all alerts associated with a specific payment.
    """
    alerts = await crud.get_alerts_for_payment(db, payment_id)
    if not alerts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No alerts found for this payment.")
    return alerts

@router.get("/alerts/user/{user_id}", response_model=List[AlertResponse])
async def get_alerts_for_user_endpoint(
    user_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves all alerts associated with a specific user.
    """
    alerts = await crud.get_alerts_for_user(db, user_id)
    if not alerts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No alerts found for this user.")
    return alerts
