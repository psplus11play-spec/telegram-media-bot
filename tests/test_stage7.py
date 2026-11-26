"""Stage 7 tests: favorites storage and language setting (temp sqlite db)."""
import pytest

from bot.database import session as session_mod
from bot.database.models import (
    add_favorite,
    get_or_create_user,
    remove_favorite,
    user_favorites,
)
from bot.database.session import init_db


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db = tmp_path / "stage7.db"

    original = session_mod.get_settings

    def _settings():
        s = original()
        s.db_url = f"sqlite+aiosqlite:///{db}"
        return s

    monkeypatch.setattr(session_mod, "get_settings", _settings)
    session_mod._engine = None
    session_mod._factory = None
    yield db
    session_mod._engine = None
    session_mod._factory = None


@pytest.mark.asyncio
async def test_favorites_crud(temp_db):
    await init_db()
    factory = session_mod.get_session_factory()
    async with factory() as session:
        await add_favorite(session, 777001, "https://ex/1", "Song A", "Artist A")
        await add_favorite(session, 777001, "https://ex/2", "Song B")
        await add_favorite(session, 777001, "https://ex/1", "Song A again")  # dedupe
        favs = await user_favorites(session, 777001)
        assert len(favs) == 2
        await remove_favorite(session, 777001, "https://ex/1")
        favs = await user_favorites(session, 777001)
        assert len(favs) == 1 and favs[0].url == "https://ex/2"


@pytest.mark.asyncio
async def test_user_language_persist(temp_db):
    await init_db()
    factory = session_mod.get_session_factory()
    async with factory() as session:
        user = await get_or_create_user(session, 777002, "Tester")
        assert user.language == "ru"
        await get_or_create_user(session, 777002, "Tester", language="en")
        user = await get_or_create_user(session, 777002, "Tester")
        assert user.language == "en"
