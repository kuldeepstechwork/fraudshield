# fraudshield/src/services/detector/models.py

"""Detector service model wrapper.

This module used to contain full ORM model definitions which duplicated the
central `src.models` package. Replace those definitions by importing the
canonical models so SQLAlchemy has a single source of truth.
"""

from src.models import Payment, LogRequest, User, Merchant, FraudRule, Alert

__all__ = ["Payment", "LogRequest", "User", "Merchant", "FraudRule", "Alert"]