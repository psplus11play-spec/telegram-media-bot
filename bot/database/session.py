"""Async engine/session management."""
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import get_settings

_engine = None
_factory = None


def get_session_factory():
    global _engine, _factory
    if _factory is None:
        settings = get_settings()
        _engine = create_async_engine(settings.db_url, echo=settings.db_echo)
        _factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _factory


async def init_db() -> None:
    from bot.database.models import Base
    url = make_url(get_settings().db_url)
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
