"""SQLAlchemy 2.0 async models."""
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func, select
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
