# fraudshield/detector/app.py

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, List, Optional
from datetime import datetime
import json
import uuid

# Kafka
from aiokafka import AIOKafkaProducer
import asyncio

# Pydantic schemas for request/response
from pydantic import BaseModel, Field, EmailStr
from decimal import Decimal

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

# --- Pydantic Schemas ---

# Schemas for User
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    country: Optional[str] = None
    phone_number: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    user_id: uuid.UUID
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    kyc_status: str

    class Config:
        from_attributes = True # Allows Pydantic to read ORM models

# Schemas for Merchant
class MerchantBase(BaseModel):
    merchant_name: str = Field(..., min_length=3, max_length=255)
    category: Optional[str] = None
    country: Optional[str] = None
    website_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None

class MerchantCreate(MerchantBase):
    pass

class MerchantResponse(MerchantBase):
    merchant_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas for Payment (for incoming requests)
class PaymentCreate(BaseModel):
    user_id: uuid.UUID
    merchant_id: uuid.UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2) # Greater than 0, 2 decimal places
    currency: str = Field(..., min_length=3, max_length=3)
    payment_method: str = Field(..., min_length=2, max_length=50)
    card_type: Optional[str] = None
    card_last_four: Optional[str] = None
    transaction_type: str = Field(..., min_length=2, max_length=20)
    ip_address: Optional[str] = None # Will be parsed to INET in DB, use str for input
    device_info: Optional[dict] = None # JSON data
    country: Optional[str] = None

class PaymentResponse(BaseModel):
    payment_id: uuid.UUID
    user_id: uuid.UUID
    merchant_id: uuid.UUID
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    timestamp: datetime
    fraud_score: Decimal
    fraud_flag: bool
    risk_level: str

    class Config:
        from_attributes = True # Enable Pydantic to read ORM models

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
    payment_data: PaymentCreate,
    producer: AIOKafkaProducer = Depends(get_kafka_producer),
    db: AsyncSession = Depends(get_db) # We need DB to check user/merchant existence
):
    """
    Receives payment transaction data and sends it to Kafka for asynchronous processing.
    Returns an immediate acceptance response.
    """
    # Basic validation: Check if user and merchant exist
    user = await db.get(User, payment_data.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    merchant = await db.get(Merchant, payment_data.merchant_id)
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")

    try:
        # Convert Pydantic model to dict, then to JSON bytes
        # Use str() for Decimal and UUID before json.dumps
        payment_dict = payment_data.model_dump()
        payment_dict['amount'] = str(payment_dict['amount']) # Convert Decimal to string
        payment_dict['user_id'] = str(payment_dict['user_id']) # Convert UUID to string
        payment_dict['merchant_id'] = str(payment_dict['merchant_id']) # Convert UUID to string

        message_bytes = json.dumps(payment_dict).encode('utf-8')
        
        # Send to Kafka
        await producer.send_and_wait(settings.KAFKA_RAW_PAYMENTS_TOPIC, message_bytes)

        return {"message": "Payment received and sent to Kafka for processing", "payment_id_placeholder": "awaiting processing"}
    except Exception as e:
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