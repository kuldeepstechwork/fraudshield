# fraudshield/src/common/db.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from src.common.config import settings # Import settings

# The DATABASE_URL is now pulled from settings
engine = create_async_engine(settings.DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Async dependency for FastAPI and potential consumer usage
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session