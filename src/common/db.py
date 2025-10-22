# fraudshield/src/common/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker # <-- Import async_sessionmaker
from src.common.config import settings
from src.models.base import Base # Use the canonical Base
from typing import AsyncGenerator # <-- Import AsyncGenerator

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True
)

# Use async_sessionmaker for async sessions
SessionLocal = async_sessionmaker( # <-- Changed from sessionmaker
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False, # <-- Explicitly set autocommit for clarity
    autoflush=False   # <-- Explicitly set autoflush for clarity
)

async def get_db() -> AsyncGenerator[AsyncSession, None]: # <-- Correct type hint
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() # Ensure session is closed