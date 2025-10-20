# fraudshield/src/models/payment_models.py

from datetime import datetime
import uuid
from sqlalchemy import Column, String, Float, DateTime, Boolean, DECIMAL, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship
from src.models.base import Base # Import Base from the new central location

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False, index=True)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey('merchants.merchant_id'), nullable=False, index=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    payment_method = Column(String(50), nullable=False)
    card_type = Column(String(20), nullable=True)
    card_last_four = Column(String(4), nullable=True)
    transaction_type = Column(String(20), nullable=False)
    status = Column(String(20), default="Pending", nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ip_address = Column(INET, nullable=True)
    device_info = Column(JSONB, nullable=True)
    country = Column(String(50), nullable=True)
    fraud_score = Column(DECIMAL(5, 2), default=0.0, nullable=False)
    fraud_flag = Column(Boolean, default=False, nullable=False)
    reason_code = Column(String(100), nullable=True)
    risk_level = Column(String(20), default="Low", nullable=False)

    # Relationships - defined as strings to avoid circular imports, or import later
    # 'User' and 'Merchant' are in user_models.py, 'Alert' in fraud_models.py
    # These will be set up in the respective models using back_populates
    # user = relationship("User", back_populates="payments")
    # merchant = relationship("Merchant", back_populates="payments")
    # alerts = relationship("Alert", back_populates="payment", cascade="all, delete-orphan")


class LogRequest(Base):
    __tablename__ = "log_requests"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ip_address = Column(INET, nullable=True)
    device_info = Column(JSONB, nullable=True)
    country = Column(String(50), nullable=True)
    request_details = Column(JSONB, nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    is_successful = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    # user = relationship("User", back_populates="log_requests")