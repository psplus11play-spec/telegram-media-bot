"""SQLAlchemy 2.0 async models."""
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    full_name: Mapped[str] = mapped_column(String(128), default="")
    language: Mapped[str] = mapped_column(String(2), default="ru")
    is_blocked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    history: Mapped[list["DownloadHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class DownloadHistory(Base):
    __tablename__ = "download_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(512), default="")
    media_type: Mapped[str] = mapped_column(String(16))  # video | audio
    platform: Mapped[str] = mapped_column(String(32), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="history")


class FileCache(Base):
    """Telegram file_id cache so re-downloads are sent instantly.

    Keyed by (url, quality, media_type): the url identifies the media item
    on its platform, quality distinguishes renditions, media_type separates
    video from audio-only downloads of the same url.
    """

    __tablename__ = "file_cache"
    __table_args__ = (UniqueConstraint("url", "quality", "media_type", name="uq_file_cache_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), index=True)
    quality: Mapped[str] = mapped_column(String(16), default="")
    media_type: Mapped[str] = mapped_column(String(16))  # video | audio
    file_id: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


async def get_cached_file_id(session: AsyncSession, url: str, quality: str, media_type: str) -> str | None:
    """Return a fresh file_id for the key, or None (expired/absent)."""
    from bot.config import get_settings

    ttl = get_settings().cache_ttl_days
    cached = await session.scalar(
        select(FileCache).where(
            FileCache.url == url,
            FileCache.quality == quality,
            FileCache.media_type == media_type,
        )
    )
    if cached is None:
        return None
    age = datetime.now(UTC) - cached.created_at
    if age.total_seconds() > ttl * 86400:
        await session.delete(cached)
        await session.commit()
        return None
    return cached.file_id


async def put_cached_file_id(session: AsyncSession, url: str, quality: str, media_type: str, file_id: str) -> None:
    cached = await session.scalar(
        select(FileCache).where(
            FileCache.url == url,
            FileCache.quality == quality,
            FileCache.media_type == media_type,
        )
    )
    if cached is None:
        session.add(FileCache(url=url, quality=quality, media_type=media_type, file_id=file_id))
    else:
        cached.file_id = file_id
        cached.created_at = datetime.now(UTC)
    await session.commit()


class SearchHistory(Base):
    """Recent music search queries per user, for quick repeat."""

    __tablename__ = "search_history"
    __table_args__ = (UniqueConstraint("user_id", "query", name="uq_search_history_query"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    query: Mapped[str] = mapped_column(String(256))
    provider: Mapped[str] = mapped_column(String(16), default="ytmusic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


async def save_search(session: AsyncSession, user_id: int, query: str, provider: str) -> None:
    query = query.strip()[:256]
    if not query:
        return
    existing = await session.scalar(
        select(SearchHistory).where(SearchHistory.user_id == user_id, SearchHistory.query == query)
    )
    if existing is None:
        session.add(SearchHistory(user_id=user_id, query=query, provider=provider))
    else:
        existing.created_at = datetime.now(UTC)
        existing.provider = provider
    await session.commit()


async def recent_searches(session: AsyncSession, user_id: int, limit: int = 5) -> list[str]:
    items = (await session.scalars(
        select(SearchHistory).where(SearchHistory.user_id == user_id)
        .order_by(SearchHistory.created_at.desc()).limit(limit)
    )).all()
    return [i.query for i in items]


async def get_or_create_user(session: AsyncSession, user_id: int, full_name: str, language: str = "ru") -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, full_name=full_name, language=language)
        session.add(user)
        await session.commit()
    elif user.full_name != full_name:
        user.full_name = full_name
        await session.commit()
    return user


async def add_history(session: AsyncSession, user_id: int, url: str, title: str, media_type: str, platform: str, file_size: int = 0) -> None:
    session.add(DownloadHistory(user_id=user_id, url=url, title=title, media_type=media_type, platform=platform, file_size=file_size))
    await session.commit()


async def user_history(session: AsyncSession, user_id: int, limit: int = 10, offset: int = 0) -> tuple[list[DownloadHistory], int]:
    total = await session.scalar(select(func.count()).select_from(DownloadHistory).where(DownloadHistory.user_id == user_id)) or 0
    items = (await session.scalars(
        select(DownloadHistory).where(DownloadHistory.user_id == user_id)
        .order_by(DownloadHistory.created_at.desc()).offset(offset).limit(limit)
    )).all()
    return list(items), int(total)
