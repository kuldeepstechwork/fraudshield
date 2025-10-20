# fraudshield/src/services/detector/schemas/alert.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class AlertResponse(BaseModel):
    alert_id: uuid.UUID
    payment_id: Optional[uuid.UUID]
    user_id: uuid.UUID
    rule_id: Optional[uuid.UUID]
    alert_type: str
    description: str
    timestamp: datetime
    status: str
    assigned_to: Optional[uuid.UUID]
    resolution_notes: Optional[str]
    resolution_time: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str
        }