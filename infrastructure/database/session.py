"""Database infrastructure (ADR-001: PostgreSQL).

Manages the async SQLAlchemy engine and session factory.  The engine is
created once during bootstrap and disposed on shutdown.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings


class Base(DeclarativeBase):
  """Declarative base for all ORM models."""


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_database() -> None:
  """Create the engine and session factory from settings.

  For local development, ECLMS_DATABASE_URL may point at a SQLite file
  (e.g. sqlite+aiosqlite:///./eclms.db); production targets PostgreSQL.
  """
  global _engine, _session_factory
  settings = get_settings()
  url = settings.database_url
  kwargs: dict = {'echo': settings.database_echo}
  if 'postgresql' in url:
    kwargs['pool_size'] = settings.database_pool_size
    kwargs['max_overflow'] = settings.database_max_overflow
    kwargs['pool_pre_ping'] = settings.database_pool_pre_ping
    kwargs['pool_recycle'] = settings.database_pool_recycle
  _engine = create_async_engine(url, **kwargs)
  _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def create_schema() -> None:
  """Create all tables.  For development and tests only; production uses Alembic."""
  if _engine is None:
    init_database()
  from infrastructure.database import models  # noqa: F401  (register all models)

  async with _engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)


async def dispose_database() -> None:
  """Dispose the engine and release pooled connections."""
  if _engine is not None:
    await _engine.dispose()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
  if _session_factory is None:
    raise RuntimeError('Database not initialised. Call init_database() during bootstrap.')
  return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
  """FastAPI dependency that yields an async session."""
  async with get_session_factory()() as session:
    yield session


async def check_database_health() -> bool:
  """Return True when the database is reachable.

  A missing or unreachable database must never crash the health endpoint;
  it is reported as unavailable so operators can react.
  """
  if _engine is None:
    return False
  from sqlalchemy import text
  from sqlalchemy.exc import SQLAlchemyError

  try:
    async with _engine.connect() as conn:
      await conn.execute(text('SELECT 1'))
    return True
  except (SQLAlchemyError, OSError):
    return False


def database_pool_stats() -> dict:
  """Expose live connection-pool gauges for observability.

  Returns None when the database isn't initialised or the engine is not a
  pooled engine (e.g. SQLite), so consumers can omit the block safely.
  """
  if _engine is None:
    return None
  sync_engine = getattr(_engine, 'sync_engine', None)
  pool = getattr(sync_engine, 'pool', None) if sync_engine is not None else None
  if pool is None or not hasattr(pool, 'checkedout'):
    return None
  try:
    return {
      'checked_out': pool.checkedout(),
      'size': pool.size(),
      'overflow': pool.overflow(),
    }
  except (AttributeError, RuntimeError, ValueError):  # pragma: no cover
    return None
