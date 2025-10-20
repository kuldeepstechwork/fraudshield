# fraudshield/src/services/detector/schemas/user.py

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import uuid

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
        from_attributes = True
        json_encoders = {
            uuid.UUID: str
        }