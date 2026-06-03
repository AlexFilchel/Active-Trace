from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base reserved for ORM models in later changes."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def initialize_database() -> AsyncEngine:
    global _engine, _session_factory

    if _engine is None or _session_factory is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url.unicode_string(), pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory

    if _session_factory is None:
        initialize_database()

    assert _session_factory is not None
    return _session_factory


async def dispose_database() -> None:
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()

    _engine = None
    _session_factory = None
