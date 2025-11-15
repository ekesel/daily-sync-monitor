# app/db/session.py
import os
from collections.abc import AsyncGenerator
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()

# Detect if we're running under pytest
IS_TEST = "PYTEST_CURRENT_TEST" in os.environ

# ---------------------------------------------------------------------------
# Main application engine + session (used by app code, not by test init_db)
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DB_URL,
    echo=False,
    future=True,
    # In tests we *still* use the main engine sometimes (for AsyncSessionLocal),
    # so use NullPool to avoid connection reuse across loops.
    poolclass=NullPool if IS_TEST else None,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async SQLAlchemy session.

    The session is automatically closed when the request is completed.
    """
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# PRODUCTION / DEV: DB init for app startup
# ---------------------------------------------------------------------------
async def init_db_for_startup() -> None:
    """
    Initialize DB schema for application startup.

    Safe to call from FastAPI startup in non-test environments.
    Typically you'd eventually replace this with Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ---------------------------------------------------------------------------
# TESTS ONLY: reset schema using a SYNC Postgres engine
# ---------------------------------------------------------------------------

def _build_sync_db_url(async_url: str) -> str:
    """
    Convert 'postgresql+asyncpg://...' -> 'postgresql://...'
    so we can use a synchronous psycopg driver for DDL.
    """
    if "+asyncpg" in async_url:
        return async_url.replace("+asyncpg", "")
    return async_url


def _reset_schema_sync() -> None:
    """
    Run drop_all + create_all using a synchronous SQLAlchemy engine.

    This completely bypasses asyncpg and event-loop issues.
    """
    sync_url = _build_sync_db_url(settings.DB_URL)
    sync_engine = create_sync_engine(sync_url, future=True)

    with sync_engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)
        Base.metadata.create_all(bind=conn)

    sync_engine.dispose()

async def init_db() -> None:
    """
    TEST-ONLY: reset the database schema.

    Drops all tables and recreates them using the current models.
    Do NOT call this from production code. Only from tests/fixtures.
    """
    async with engine.begin() as conn:
        # Drop everything to guarantee a clean slate per test
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)