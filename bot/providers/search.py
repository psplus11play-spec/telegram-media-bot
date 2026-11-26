"""YouTube Music and SoundCloud search via yt-dlp search prefixes."""
import asyncio

import yt_dlp

from bot.config import get_settings
from bot.providers.base import (
    SEARCH_PAGE_SIZE,
    MusicProvider,
    ProviderCaps,
    ProviderError,
    Track,
    dedupe,
    split_artist_title,
)


def _ydl_opts(extra: dict | None = None) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "noplaylist": True,
    }
    settings = get_settings()
    if settings.download_ytdlp_cookies_file is not None:
        opts["cookiefile"] = str(settings.download_ytdlp_cookies_file)
    if extra:
        opts.update(extra)
    return opts


def _search_sync(prefix: str, query: str, page: int) -> list[Track]:
    # yt-dlp search prefixes have no offset; fetch all pages up to the
    # requested one and slice, so pagination stays stable for new entries
    count = SEARCH_PAGE_SIZE * (page + 1)
    opts = _ydl_opts({"extract_flat": True})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"{prefix}{count}:{query}", download=False)
    entries = (info or {}).get("entries") or []
    start = SEARCH_PAGE_SIZE * page
    out: list[Track] = []
    for e in entries[start:start + SEARCH_PAGE_SIZE]:
        if not e:
            continue
        artist, title = split_artist_title(e.get("title") or "", e.get("uploader") or "")
        out.append(Track(
            provider="ytmusic" if prefix.startswith("yt") else "soundcloud",
            url=e.get("url") or e.get("webpage_url") or "",
            title=title,
            artist=artist,
            duration=int(e.get("duration") or 0),
            thumbnail=e.get("thumbnails") and (e["thumbnails"][-1].get("url") or ""),
            track_id=str(e.get("id") or ""),
        ))
    return [t for t in out if t.url]


class _YtDlpSearchProvider(MusicProvider):
    """Search over yt-dlp flat extracts; subclass sets the search prefix."""

    prefix = "ytsearch"
    caps = ProviderCaps(search=True, metadata=True, lossless=False)

    async def search(self, query: str, page: int = 0) -> list[Track]:
        self._check()
        if not query.strip():
            raise ProviderError("пустой поисковый запрос")
        results = await asyncio.to_thread(self._search, query, page)
        return dedupe(results)

    def _search(self, query: str, page: int) -> list[Track]:
        try:
            return _search_sync(self.prefix, query, page)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"поиск не удался: {e}") from e

    async def metadata(self, url: str) -> Track:
        self._check()

        def _meta() -> Track:
            with yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
                info = ydl.extract_info(url, download=False)
            if info is None:
                raise ProviderError("не удалось получить данные трека")
            artist, title = split_artist_title(info.get("title") or "", info.get("uploader") or "")
            return Track(
                provider=self.name,
                url=info.get("webpage_url") or url,
                title=title,
                artist=artist,
                album=info.get("album") or "",
                duration=int(info.get("duration") or 0),
                year=str(info.get("release_year") or info.get("release_date") or "")[:4],
                track_number=int(info.get("track_number") or 0),
                thumbnail=(info.get("thumbnails") or [{}])[-1].get("url", ""),
                track_id=str(info.get("id") or ""),
            )

        try:
            return await asyncio.to_thread(_meta)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"не удалось получить данные трека: {e}") from e


class YouTubeMusicProvider(_YtDlpSearchProvider):
    """YouTube Music search. Audio is downloaded from YouTube sources; no
    genuine lossless exists, so FLAC is never offered from this provider."""

    name = "ytmusic"
    prefix = "ytsearch"
    caps = ProviderCaps(search=True, metadata=True, lossless=False)


class SoundCloudProvider(_YtDlpSearchProvider):
    """SoundCloud search via the scsearch yt-dlp prefix."""

    name = "soundcloud"
    prefix = "scsearch"
    caps = ProviderCaps(search=True, metadata=True, lossless=False)
