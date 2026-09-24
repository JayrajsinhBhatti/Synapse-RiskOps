"""
Synapse RiskOps - Database Connection & Session Management
==========================================================
Owner: Person 2 | Week: 5

Async PostgreSQL database connection using SQLAlchemy 2.0 and asyncpg.
"""

import sys
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Engine configuration (use NullPool in tests to avoid event-loop connection cross-talk)
engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}
if "pytest" in sys.modules or any("test" in arg for arg in sys.argv):
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
    })

# Async database engine
async_engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Base class for all ORM models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session per request.
    Automatically commits on success or rolls back on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
