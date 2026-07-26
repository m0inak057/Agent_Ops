"""Database engine and session management for the AgentOps backend.

Provides the async SQLAlchemy engine, session factory, the shared
declarative Base used by all models, and a FastAPI dependency for
obtaining a database session per request.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops"
)


class Base(DeclarativeBase):
    """Shared declarative base class for all AgentOps ORM models."""

    pass


engine = create_async_engine(DATABASE_URL, future=True)

SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables registered on Base.metadata."""
    import backend.models  # noqa: F401  ensures all models are registered on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
