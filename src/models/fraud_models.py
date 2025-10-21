# fraudshield/src/models/fraud_models.py
"""
Fraud-related ORM models: FraudRule and Alert.
"""
from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models.base import Base


class FraudRule(Base):
    __tablename__ = "fraud_rules"

    rule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    rule_name = Column(String(100), unique=True, nullable=False)
    rule_expression = Column(Text, nullable=False)
    severity = Column(String(20), default="Medium", nullable=False)
    action = Column(String(20), default="Flag", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    alerts = relationship("Alert", back_populates="rule")


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    payment_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rule_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status = Column(String(20), default="New", nullable=False)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolution_time = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    payment = relationship("Payment", back_populates="alerts")
    user = relationship("User", back_populates="alerts")
    rule = relationship("FraudRule", back_populates="alerts")