import os
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/anomaly_test",
    ),
)
os.environ.setdefault(
    "REDIS_URL", os.getenv("TEST_REDIS_URL", "redis://127.0.0.1:6379/15")
)

from app.cache.redis_client import RedisClient
from app.models import Base


@pytest_asyncio.fixture
async def test_engine():
    url = os.environ["DATABASE_URL"]
    engine = create_async_engine(url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_redis() -> AsyncIterator[RedisClient]:
    r = RedisClient(os.environ["REDIS_URL"])
    await r.connect()
    yield r
    await r.close()
