from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class FraudRuleResponse(BaseModel):
    rule_id: uuid.UUID
    rule_name: str
    rule_expression: str
    severity: str
    action: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str
        }
