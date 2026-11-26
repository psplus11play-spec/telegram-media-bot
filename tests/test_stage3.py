"""Stage 3 tests: providers, dedupe, audio tagging, search session helpers."""
from pathlib import Path

import pytest
from mutagen.id3 import ID3

from bot.providers import (
    SEARCH_PAGE_SIZE,
    Track,
    dedupe,
    get_provider,
    provider_for_url,
    search_providers,
)
from bot.providers.base import ProviderError, split_artist_title
from bot.providers.search import SoundCloudProvider, YouTubeMusicProvider
from bot.services import music_service


def test_provider_registry():
    assert SEARCH_PAGE_SIZE == 8
    for name in ("ytmusic", "soundcloud", "spotify"):
        get_provider(name)  # must not raise
    with pytest.raises(ProviderError):
        get_provider("nope")
    names = {p.name for p in search_providers()}
    assert "ytmusic" in names and "soundcloud" in names


def test_provider_url_routing():
    assert provider_for_url("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC") == "spotify"
    assert provider_for_url("https://soundcloud.com/artist/track") == "soundcloud"
    assert provider_for_url("https://www.youtube.com/watch?v=abc") == "ytmusic"
    assert provider_for_url("https://youtu.be/abc") == "ytmusic"
    assert provider_for_url("https://example.com/video") is None


def test_dedupe_keeps_first():
    a = Track(provider="ytmusic", url="https://x/1", title="T", artist="A", track_id="1")
    b = Track(provider="ytmusic", url="https://x/2", title="T", artist="A", track_id="1")
    c = Track(provider="ytmusic", url="https://x/3", title="Other", artist="B", track_id="2")
    out = dedupe([a, b, c])
    assert len(out) == 2 and out[0] is a and out[1] is c


def test_split_artist_title():
    assert split_artist_title("Daft Punk - One More Time") == ("Daft Punk", "One More Time")
    artist, title = split_artist_title("Just Title", "Some Channel - Topic")
    assert artist == "Some Channel" and title == "Just Title"


def test_track_display():
    t = Track(provider="ytmusic", url="u", title="Song", artist="Artist", duration=95)
    assert "Artist — Song" in t.display and "1:35" in t.display


def test_search_providers_declare_caps():
    for provider in (YouTubeMusicProvider(), SoundCloudProvider()):
        assert provider.caps.search is True
        assert provider.caps.lossless is False  # no genuine lossless sources


def test_audio_formats_no_fake_lossless():
    assert set(music_service.AUDIO_FORMATS) == {"mp3_128", "mp3_192", "mp3_320", "m4a", "opus"}


@pytest.mark.asyncio
async def test_mp3_tagging(tmp_path: Path):
    import shutil

    src = Path(__file__).parent / "data" / "silence_5s.mp3"
    if not src.exists():
        pytest.skip("test fixture mp3 not generated")
    path = tmp_path / "out.mp3"
    shutil.copy(src, path)
    track = Track(provider="ytmusic", url="u", title="Test Song", artist="Test Artist",
                  album="Test Album", year="2024", track_number=3)
    music_service._tag_file_sync(path, track, None)  # sync worker, runs in a thread in production
    tags = ID3(path)
    assert tags["TIT2"].text[0] == "Test Song"
    assert tags["TPE1"].text[0] == "Test Artist"
    assert tags["TALB"].text[0] == "Test Album"
