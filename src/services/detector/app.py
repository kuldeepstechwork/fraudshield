# fraudshield/detector/app.py

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, List, Optional
from datetime import datetime
import json
import uuid

# Kafka
from aiokafka import AIOKafkaProducer
import asyncio

# Pydantic schemas for request/response
from .schemas import PaymentRequest, UserCreate, UserResponse, MerchantCreate, MerchantResponse, PaymentResponse

# Import database and models
from .db import SessionLocal, engine, Base
from .models import Payment, User, Merchant, FraudRule, Alert, LogRequest 

# --- Configuration (using Pydantic Settings for robustness) ---
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092" # Adjust if Kafka is elsewhere
    # You might want to define Kafka topics here too
    KAFKA_RAW_PAYMENTS_TOPIC: str = "raw_payments"

    class Config:
        env_file = ".env" # Load from .env file

settings = Settings()

# --- FastAPI App Initialization ---
app = FastAPI(title="FraudShield Detector Service")

# --- Database Dependency ---
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

# --- Kafka Producer Dependency ---
async def get_kafka_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

# --- Security ---
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == settings.API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    # Optional: Create all tables if they don't exist.
    # In production, use Alembic migrations instead.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables checked/created.")


@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new user. For testing purposes.
    """
    db_user = await db.execute(User.__table__.select().where(User.email == user_data.email))
    if db_user.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = User(**user_data.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@app.post("/merchants/", response_model=MerchantResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant(merchant_data: MerchantCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new merchant. For testing purposes.
    """
    db_merchant = await db.execute(Merchant.__table__.select().where(Merchant.merchant_name == merchant_data.merchant_name))
    if db_merchant.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Merchant name already exists")

    new_merchant = Merchant(**merchant_data.model_dump())
    db.add(new_merchant)
    await db.commit()
    await db.refresh(new_merchant)
    return new_merchant


@app.post("/payments/", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def process_payment(
    payment_data: PaymentRequest,
    api_key: str = Depends(get_api_key),
    producer: AIOKafkaProducer = Depends(get_kafka_producer),
    db: AsyncSession = Depends(get_db)
):
    """
    Receives payment transaction data, creates a pending payment record, 
    and sends it to Kafka for asynchronous processing.
    Returns an immediate acceptance response.
    """
    # Create a new Payment record with a "Pending" status
    new_payment = Payment(
        payment_id=payment_data.transaction_id, # Use transaction_id as payment_id
        user_id=payment_data.user_id,
        merchant_id=payment_data.merchant_id,
        amount=payment_data.amount,
        currency=payment_data.currency,
        payment_method=payment_data.payment_method,
        status="Pending",
        timestamp=payment_data.timestamp,
        ip_address=payment_data.ip_address,
        device_info=payment_data.device_fingerprint,
        country=None # Or extract from IP if you have a service for that
    )
    db.add(new_payment)
    await db.commit()
    await db.refresh(new_payment)

    try:
        # Send to Kafka
        await producer.send_and_wait(
            settings.KAFKA_RAW_PAYMENTS_TOPIC,
            payment_data.model_dump_json().encode("utf-8")
        )

        return {"message": "Payment received and sent to Kafka for processing", "transaction_id": payment_data.transaction_id}
    except Exception as e:
        # Rollback the database transaction if Kafka fails
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send payment to Kafka: {e}"
        )

# You can add more endpoints here, e.g., for getting payment status, managing fraud rules, etc.
# Example: Get a specific payment's status (after it's been processed and saved to DB)
@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment_status(payment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieves the current status and fraud details of a processed payment.
    """
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment

# Example: Fetch all existing fraud rules
@app.get("/fraud-rules/", response_model=List[dict]) # You'd make a Pydantic schema for FraudRuleResponse
async def get_fraud_rules(db: AsyncSession = Depends(get_db)):
    """
    Retrieves a list of all active fraud rules.
    """
    result = await db.execute(FraudRule.__table__.select().where(FraudRule.is_active == True))
    rules = result.scalars().all()
    # Convert SQLAlchemy ORM objects to dictionaries for a simple response,
    # or create a dedicated Pydantic FraudRuleResponse schema.
    return [rule.__dict__ for rule in rules]