"""Stage 5 tests: recognition service and handler helpers."""
import asyncio
from pathlib import Path

import pytest

from bot.handlers.shazam import _card
from bot.services import ffmpeg_tools, recognition
from bot.services.recognition import Recognized

FIXTURES = Path(__file__).parent / "data"


def _fixture(name: str) -> Path:
    path = FIXTURES / name
    if not path.exists():
        pytest.skip(f"fixture {name} not generated")
    return path


def test_recognized_display():
    m = Recognized(title="One More Time", artist="Daft Punk")
    assert m.display == "Daft Punk — One More Time"
    m2 = Recognized(title="Unknown Track")
    assert m2.display == "Unknown Track"


def test_card_escapes_html():
    m = Recognized(title="<b>Evil</b>", artist="Art & ist")
    card = _card(m)
    assert "&lt;b&gt;Evil&lt;/b&gt;" in card
    assert "Art &amp; ist" in card


@pytest.mark.asyncio
async def test_fragment_cut(tmp_path: Path):
    """A long mp3 is cut to <=12s WAV for the fingerprinter."""
    src = tmp_path / "long.mp3"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=20",
        "-c:a", "libmp3lame", str(src),
    )
    assert await proc.wait() == 0
    fragment = await ffmpeg_tools.audio_fragment(src, recognition.FRAGMENT_SECONDS)
    try:
        duration = await ffmpeg_tools.probe_duration(fragment)
        assert 0 < duration <= recognition.FRAGMENT_SECONDS + 0.5
    finally:
        fragment.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_recognize_silence_returns_none():
    """A pure tone can't be identified: service must return None, not raise."""
    src = _fixture("silence_5s.mp3")
    result = await recognition.recognize(src)
    assert result is None
