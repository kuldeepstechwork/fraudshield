# fraudshield/src/services/detector/schemas/payment.py

from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from datetime import datetime
import uuid

# Schema for creating a new payment (incoming request body)
class PaymentCreate(BaseModel):
    user_id: uuid.UUID
    merchant_id: uuid.UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2) # Greater than 0, 2 decimal places
    currency: str = Field(..., min_length=3, max_length=3)
    payment_method: str = Field(..., min_length=2, max_length=50)
    card_type: Optional[str] = None
    card_last_four: Optional[str] = None
    transaction_type: str = Field(..., min_length=2, max_length=20)
    ip_address: Optional[str] = None # Will be parsed to INET by DB, use str for input
    device_info: Optional[dict] = None # JSON data
    country: Optional[str] = None

# Schema for the response after processing a payment (when it's saved in DB)
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
    card_type: Optional[str] = None
    card_last_four: Optional[str] = None
    transaction_type: str
    ip_address: Optional[str] = None
    device_info: Optional[dict] = None
    country: Optional[str] = None
    reason_code: Optional[str] = None

    class Config:
        from_attributes = True # Allows Pydantic to read ORM models
        json_encoders = {
            Decimal: str, # Ensure Decimal is serialized as string
            uuid.UUID: str # Ensure UUID is serialized as string
        }

# Simplified schema for just fraud status (e.g., if you only want to query fraud for an ID)
class PaymentFraudStatus(BaseModel):
    payment_id: uuid.UUID
    status: str
    fraud_score: Decimal
    fraud_flag: bool
    risk_level: str
    reason_code: Optional[str]

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: str,
            uuid.UUID: str
        }