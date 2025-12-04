# fraudshield/src/services/detector/schemas/payment.py

from pydantic import BaseModel, Field, condecimal
from pydantic import ConfigDict
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import ipaddress

class PaymentCreate(BaseModel):
    user_id: uuid.UUID
    merchant_id: uuid.UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)
    payment_method: str = Field(..., min_length=2, max_length=50)
    card_type: Optional[str] = None
    card_last_four: Optional[str] = None
    transaction_type: str = Field(..., min_length=2, max_length=20)
    ip_address: Optional[str] = None
    device_info: Optional[dict] = None
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
    card_type: Optional[str] = None
    card_last_four: Optional[str] = None
    transaction_type: str
    ip_address: Optional[str] = None
    device_info: Optional[dict] = None
    country: Optional[str] = None
    reason_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, json_encoders={
        Decimal: str,
        uuid.UUID: str,
        ipaddress.IPv4Address: str,
        ipaddress.IPv6Address: str,
    })

class PaymentFraudStatus(BaseModel):
    payment_id: uuid.UUID
    status: str
    fraud_score: Decimal
    fraud_flag: bool
    risk_level: str
    reason_code: Optional[str]

    model_config = ConfigDict(from_attributes=True, json_encoders={
        Decimal: str,
        uuid.UUID: str,
    })

class PaymentRequest(BaseModel):
    transaction_id: str = Field(..., example="txn_abc123", description="Unique identifier for the transaction")
    idempotency_key: str = Field(..., example="key_def456", description="Key for idempotent processing")
    user_id: str = Field(..., example="user_789", description="Identifier of the user initiating the payment")
    merchant_id: str = Field(..., example="merch_001", description="Identifier of the merchant receiving the payment")
    amount: condecimal(decimal_places=2, gt=0) = Field(..., example=100.50, description="Payment amount in decimal format")
    currency: str = Field(..., example="USD", min_length=3, max_length=3, description="Currency code (e.g., USD, EUR)")
    payment_method: str = Field(..., example="credit_card", description="Type of payment method used")
    card_last_four: Optional[str] = Field(None, example="4242", min_length=4, max_length=4, description="Last 4 digits of card number (if applicable)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the request")
    ip_address: Optional[str] = Field(None, example="192.168.1.1", description="User's IP address")
    device_fingerprint: Optional[str] = Field(None, example="a1b2c3d4e5f6...", description="Device identifier for fraud analytics")
    metadata: Optional[dict] = Field(None, description="Arbitrary additional metadata")

class FraudDecisionEvent(BaseModel):
    transaction_id: str = Field(..., description="Unique ID of the transaction")
    user_id: str
    merchant_id: str
    amount: condecimal(decimal_places=2)
    currency: str
    decision: str = Field(..., example="approve", description="Fraud decision: approve, decline, review")
    fraud_score: float = Field(..., example=0.75, description="Composite fraud score")
    rules_triggered: List[str] = Field(..., example=["velocity_rule_1h", "ip_blacklist_match"], description="List of triggered rules")
    decision_timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or rule details")
