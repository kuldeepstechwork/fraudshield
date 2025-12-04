# fraudshield/src/common/redis_utils.py
import redis.asyncio as redis
from src.common.config import settings
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """
    Provides an async Redis client that is properly closed.
    """
    redis_client = None
    try:
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        yield redis_client
    finally:
        if redis_client:
            await redis_client.close()
