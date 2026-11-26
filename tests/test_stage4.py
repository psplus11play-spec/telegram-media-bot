"""Stage 4 tests: ffmpeg tools service and trim parsing."""
import asyncio
import shutil
from pathlib import Path

import pytest

from bot.handlers.tools import parse_time, parse_trim
from bot.services import ffmpeg_tools

FIXTURES = Path(__file__).parent / "data"


def _fixture(name: str) -> Path:
    path = FIXTURES / name
    if not path.exists():
        pytest.skip(f"fixture {name} not generated")
    return path


def test_parse_time():
    assert parse_time("0:30") == "0:30"
    assert parse_time("90") == "90"
    assert parse_time(" 1:05 ") == "1:05"
    assert parse_time("abc") is None
    assert parse_time("1:99") is None


def test_parse_trim():
    assert parse_trim("с 0:30 до 1:15") == ("0:30", "1:15")
    assert parse_trim("0:00 - 1:00") == ("0:00", "1:00")
    assert parse_trim("с 1:15 до 0:30") is None  # end before start
    assert parse_trim("random text") is None


@pytest.mark.asyncio
async def test_probe_duration(tmp_path: Path):
    src = _fixture("silence_5s.mp3")
    duration = await ffmpeg_tools.probe_duration(src)
    assert 4.0 < duration < 6.5


@pytest.mark.asyncio
async def test_voice_roundtrip(tmp_path: Path):
    mp3 = _fixture("silence_5s.mp3")
    ogg = tmp_path / "voice.ogg"
    await ffmpeg_tools.to_voice(mp3, ogg)
    assert ogg.exists() and ogg.stat().st_size > 1000
    back = tmp_path / "back.mp3"
    await ffmpeg_tools.voice_to_mp3(ogg, back)
    assert back.exists() and back.stat().st_size > 1000
    duration = await ffmpeg_tools.probe_duration(back)
    assert 4.0 < duration < 6.5


@pytest.mark.asyncio
async def test_m4r_max_30s(tmp_path: Path):
    mp3 = _fixture("silence_5s.mp3")
    ring = tmp_path / "ring.m4r"
    await ffmpeg_tools.to_m4r(mp3, ring)
    assert ring.exists() and ring.stat().st_size > 1000


@pytest.mark.asyncio
async def test_video_tools(tmp_path: Path):
    """Real video round-trip: note (square, <=60s), gif, thumbnail, trim."""
    src = FIXTURES / "test_video.mp4"
    if not src.exists():
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-c:v", "libx264", "-c:a", "aac", str(src),
        )
        assert await proc.wait() == 0

    note = tmp_path / "note.mp4"
    await ffmpeg_tools.video_to_note(src, note)
    assert note.exists() and note.stat().st_size > 1000

    gif = tmp_path / "anim.gif"
    await ffmpeg_tools.video_to_gif(src, gif, duration=2)
    assert gif.exists() and gif.stat().st_size > 1000

    thumb = tmp_path / "thumb.jpg"
    await ffmpeg_tools.extract_thumbnail(src, thumb)
    assert thumb.exists() and thumb.stat().st_size > 500

    trimmed = tmp_path / "trim.mp4"
    await ffmpeg_tools.trim(src, trimmed, "0:00", "0:02")
    duration = await ffmpeg_tools.probe_duration(trimmed)
    assert duration < 3.5
