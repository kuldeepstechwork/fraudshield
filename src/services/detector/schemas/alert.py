# fraudshield/src/services/detector/schemas/alert.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class AlertCreate(BaseModel):
    payment_id: Optional[uuid.UUID]
    user_id: uuid.UUID
    rule_id: Optional[uuid.UUID]
    alert_type: str
    description: str
    status: Optional[str] = "New"
    assigned_to: Optional[uuid.UUID] = None
    resolution_notes: Optional[str] = None
    resolution_time: Optional[datetime] = None

class AlertResponse(AlertCreate):
    alert_id: uuid.UUID
    timestamp: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str
        }
