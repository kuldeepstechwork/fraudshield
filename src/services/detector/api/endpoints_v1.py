#fraudshield/src/services/detector/api/endpoints_v1.py

from fastapi import APIRouter, Depends, HTTPException, status
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
        client_payment_id = str(uuid.uuid4())

        # Convert Pydantic model to dict and include client-generated id
        payment_dict = payment_data.model_dump()
        payment_dict["payment_id"] = client_payment_id

        # Convert Decimal/UUID for JSON serialization
        for k, v in list(payment_dict.items()):
            if isinstance(v, Decimal):
                payment_dict[k] = str(v)
            elif isinstance(v, uuid.UUID):
                payment_dict[k] = str(v)

        message_bytes = json.dumps(payment_dict).encode("utf-8")

        # Log payload before sending for debugging
        LOG.info("Sending payment message to Kafka topic=%s payload=%s", settings.KAFKA_RAW_PAYMENTS_TOPIC, payment_dict)

        # Send to Kafka
        await producer.send_and_wait(settings.KAFKA_RAW_PAYMENTS_TOPIC, message_bytes)

        # Return accepted and the client-visible payment id so callers can query later
        return {"message": "Payment received and sent to Kafka for processing", "status": "accepted", "payment_id": client_payment_id}

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
