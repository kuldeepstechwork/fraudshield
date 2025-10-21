# fraudshield/src/models/user_models.py
"""
Central user and merchant ORM models (correctly named module).
"""
from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    kyc_status = Column(String(20), default="Unverified", nullable=False)
    country = Column(String(50), nullable=True)
    phone_number = Column(String(20), nullable=True)

    # Relationships
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    log_requests = relationship("LogRequest", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")


class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    merchant_name = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), nullable=True)
    country = Column(String(50), nullable=True)
    website_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    contact_email = Column(String(255), nullable=True)

    # Relationships
    payments = relationship("Payment", back_populates="merchant", cascade="all, delete-orphan")
