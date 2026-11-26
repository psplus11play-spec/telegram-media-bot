"""Song recognition: media fragment -> Shazam via shazamio."""
from dataclasses import dataclass
from functools import lru_cache

from shazamio import Shazam

from bot.services import ffmpeg_tools

FRAGMENT_SECONDS = 12


@dataclass
class Recognized:
    title: str
    artist: str = ""
    album: str = ""
    year: str = ""
    cover: str = ""
    url: str = ""

    @property
    def display(self) -> str:
        return f"{self.artist} — {self.title}" if self.artist else self.title


@lru_cache(maxsize=1)
def _shazam() -> Shazam:
    return Shazam()


async def recognize(src: str | bytes) -> Recognized | None:
    """Recognize a song from a media file path or raw audio bytes.

    Returns None when nothing matched (not an error).
    """
    shazam = _shazam()
    try:
        if isinstance(src, bytes):
            data = await shazam.recognize(src)
        else:
            # shazamio wants raw audio bytes; cut a fragment with ffmpeg first
            fragment = await ffmpeg_tools.audio_fragment(src, FRAGMENT_SECONDS)
            data = await shazam.recognize(fragment.read_bytes())
            fragment.unlink(missing_ok=True)
    except Exception as e:
        raise RuntimeError(f"распознавание не удалось: {e}") from e
    track = (data or {}).get("track")
    if not track:
        return None
    meta = track.get("metadata") or []
    def _get(section: str) -> str:
        for item in meta:
            if item.get("title") == section and item.get("text"):
                return str(item["text"][0])
        return ""
    images = track.get("images") or {}
    return Recognized(
        title=track.get("title") or "Неизвестный трек",
        artist=(track.get("subtitle") or "").strip(),
        album=_get("Album"),
        year=_get("Releasedate")[:4],
        cover=images.get("coverart") or images.get("background") or "",
        url=(track.get("url") or track.get("share", {}).get("html") or ""),
    )
