# fraudshield/src/common/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.common.config import settings

# Use the canonical Base from src.models.base so Alembic and the ORM
# share the same metadata/registry.
from src.models.base import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
