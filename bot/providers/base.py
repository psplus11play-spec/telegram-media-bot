"""Music provider adapters: search, metadata, availability, capabilities."""
import asyncio
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlparse

import aiohttp

SEARCH_PAGE_SIZE = 8
PROVIDER_TIMEOUT = 30
RATE_LIMIT_PER_MINUTE = 20


class ProviderError(RuntimeError):
    """User-presentable provider failure."""


@dataclass
class ProviderCaps:
    search: bool = False
    metadata: bool = False
    lossless: bool = False  # genuine lossless sources only


@dataclass
class Track:
    provider: str
    url: str
    title: str
    artist: str = ""
    duration: int = 0
    album: str = ""
    year: str = ""
    track_number: int = 0
    thumbnail: str = ""
    track_id: str = ""

    @property
    def display(self) -> str:
        left = f"{self.artist} — {self.title}" if self.artist else self.title
        if self.duration:
            return f"{left} [{self.duration // 60}:{self.duration % 60:02d}]"
        return left


class _RateLimiter:
    """Sliding-window limiter shared by all calls of one provider."""

    def __init__(self, per_minute: int = RATE_LIMIT_PER_MINUTE) -> None:
        self._per_minute = per_minute
        self._hits: list[float] = []

    def check(self) -> None:
        now = time.monotonic()
        self._hits = [t for t in self._hits if now - t < 60]
        if len(self._hits) >= self._per_minute:
            raise ProviderError("слишком много запросов к провайдеру, подождите минуту")
        self._hits.append(now)


class MusicProvider(ABC):
    """Base adapter. One subclass per source; capabilities are declared."""

    name: str = "base"
    caps: ProviderCaps = ProviderCaps()

    def __init__(self) -> None:
        self._limiter = _RateLimiter()

    def available(self) -> bool:
        """Whether the provider can be used right now (credentials etc.)."""
        return True

    def _check(self) -> None:
        if not self.available():
            raise ProviderError("провайдер недоступен: нет доступа к сервису")
        self._limiter.check()

    @abstractmethod
    async def search(self, query: str, page: int = 0) -> list[Track]:
        """Return one page of results (SEARCH_PAGE_SIZE tracks)."""

    @abstractmethod
    async def metadata(self, url: str) -> Track:
        """Fetch metadata for a single track URL."""


async def download_cover(url: str, dest) -> None:
    """Fetch cover art bytes to dest; raises ProviderError on failure."""
    if not url:
        raise ProviderError("обложка недоступна")
    try:
        async with asyncio.timeout(PROVIDER_TIMEOUT):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.read()
    except Exception as e:
        raise ProviderError(f"не удалось загрузить обложку: {e}") from e
    dest.write_bytes(data)


# --- shared helpers ---------------------------------------------------------

_SPOTIFY_RE = re.compile(r"https?://open\.spotify\.com/(?:intl-\w+/)?track/([A-Za-z0-9]+)")
_YOUTUBE_RE = re.compile(r"(youtube\.com/watch|youtu\.be/|youtube\.com/shorts)")


def spotify_track_id(url: str) -> str | None:
    m = _SPOTIFY_RE.search(url)
    return m.group(1) if m else None


def split_artist_title(title: str, uploader: str = "") -> tuple[str, str]:
    """Best-effort split of 'Artist - Title' patterns used by audio sources."""
    for sep in (" - ", " — ", " – "):
        if sep in title:
            artist, _, track = title.partition(sep)
            return artist.strip(), track.strip()
    if uploader:
        for suffix in (" - Topic", " VEVO", " Official"):
            if uploader.endswith(suffix):
                return uploader[: -len(suffix)].strip(), title.strip()
        return uploader.strip(), title.strip()
    return "", title.strip()


def provider_for_url(url: str) -> str | None:
    """Route a music link to the provider that owns it."""
    host = urlparse(url).hostname or ""
    if "spotify.com" in host:
        return "spotify"
    if "soundcloud.com" in host:
        return "soundcloud"
    if _YOUTUBE_RE.search(host + url):
        return "ytmusic"
    return None


def dedupe(tracks: list[Track]) -> list[Track]:
    """Drop duplicate results, keeping the first occurrence."""
    seen: set[tuple[str, str]] = set()
    out: list[Track] = []
    for t in tracks:
        key = (t.track_id or t.url.lower(), (t.artist + "|" + t.title).lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out
