# fraudshield/detector/db.py


"""Wrapper module that re-exports centralized DB objects for the detector service.

This avoids duplicate engine/session definitions across services. Import the actual
objects from `src.common.db`.
"""
from src.common.db import engine, SessionLocal, Base, get_db

__all__ = ["engine", "SessionLocal", "Base", "get_db"]

