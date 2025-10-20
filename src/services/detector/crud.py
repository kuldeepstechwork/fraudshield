# fraudshield/src/services/detector/crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

# Import ORM models from the central models directory
from src.models import User, Merchant, Payment, FraudRule, Alert
# Import Pydantic schemas for type hinting
from src.services.detector.schemas import UserCreate, MerchantCreate, PaymentCreate, AlertResponse

# --- User CRUD ---
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)

async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    new_user = User(**user_data.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

# --- Merchant CRUD ---
async def get_merchant_by_name(db: AsyncSession, merchant_name: str) -> Merchant | None:
    result = await db.execute(select(Merchant).where(Merchant.merchant_name == merchant_name))
    return result.scalar_one_or_none()

async def get_merchant_by_id(db: AsyncSession, merchant_id: uuid.UUID) -> Merchant | None:
    return await db.get(Merchant, merchant_id)

async def create_merchant(db: AsyncSession, merchant_data: MerchantCreate) -> Merchant:
    new_merchant = Merchant(**merchant_data.model_dump())
    db.add(new_merchant)
    await db.commit()
    await db.refresh(new_merchant)
    return new_merchant

# --- Payment CRUD ---
async def get_payment_by_id(db: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    return await db.get(Payment, payment_id)

# Note: Payment creation is handled by the Kafka consumer, so no `create_payment` here for direct API calls.
# However, for testing, you might need it, but generally payments are ingested via Kafka.

# --- FraudRule CRUD ---
async def get_all_fraud_rules(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[FraudRule]:
    result = await db.execute(select(FraudRule).offset(skip).limit(limit))
    return list(result.scalars().all())

async def get_active_fraud_rules(db: AsyncSession) -> list[FraudRule]:
    result = await db.execute(select(FraudRule).where(FraudRule.is_active == True))
    return list(result.scalars().all())

# --- Alert CRUD ---
async def get_alert_by_id(db: AsyncSession, alert_id: uuid.UUID) -> Alert | None:
    return await db.get(Alert, alert_id)

async def get_alerts_for_payment(db: AsyncSession, payment_id: uuid.UUID) -> list[Alert]:
    result = await db.execute(select(Alert).where(Alert.payment_id == payment_id))
    return list(result.scalars().all())

async def get_alerts_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Alert]:
    result = await db.execute(select(Alert).where(Alert.user_id == user_id))
    return list(result.scalars().all())

async def get_alerts_by_status(db: AsyncSession, status: str) -> list[Alert]:
    result = await db.execute(select(Alert).where(Alert.status == status))
    return list(result.scalars().all())