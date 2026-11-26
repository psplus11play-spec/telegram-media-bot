"""Stage 6 tests: inline mode sessions and group behaviour."""
import time

from bot.handlers.inline import _PENDING, _store
from bot.handlers.music import GROUP_NOTE
from bot.providers.base import Track


def test_inline_session_store_roundtrip():
    _PENDING.clear()
    token = "abc123def456"
    track = Track(provider="ytmusic", url="u", title="Song", artist="Artist", track_id="1")
    _store()[token] = {"track": track, "ts": time.monotonic()}
    assert _PENDING.get(token)["track"].display == "Artist — Song"
    _PENDING.clear()


def test_inline_session_expiry():
    _PENDING.clear()
    _store()["old"] = {"ts": time.monotonic() - 10_000}
    assert _store().get("old") is None  # pruned on next store access
    _PENDING.clear()


def test_group_note_mentions_inline():
    assert "inline" in GROUP_NOTE.lower() or "инлайн" in GROUP_NOTE.lower()
    assert "@VidTuner_bot" in GROUP_NOTE
