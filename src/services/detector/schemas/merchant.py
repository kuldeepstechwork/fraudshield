# fraudshield/src/services/detector/schemas/merchant.py

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import uuid

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
        json_encoders = {
            uuid.UUID: str
        }