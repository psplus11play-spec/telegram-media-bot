"""Spotify metadata provider: metadata only, never an audio source.

Spotify does not provide audio through a public API, so this adapter serves
track metadata only; audio for a Spotify link is resolved through an
authorized alternative source (YouTube Music search-match) by the caller.
"""
import asyncio
from dataclasses import dataclass

import aiohttp

from bot.providers.base import (
    PROVIDER_TIMEOUT,
    MusicProvider,
    ProviderCaps,
    ProviderError,
    Track,
    split_artist_title,
    spotify_track_id,
)

_OEMBED = "https://open.spotify.com/oembed?url={url}"


@dataclass
class _Matched:
    track: Track


class SpotifyProvider(MusicProvider):
    name = "spotify"
    caps = ProviderCaps(search=False, metadata=True, lossless=False)

    async def search(self, query: str, page: int = 0) -> list[Track]:
        raise ProviderError("поиск в Spotify недоступен — отправьте ссылку на трек")

    async def metadata(self, url: str) -> Track:
        self._check()
        if not spotify_track_id(url):
            raise ProviderError("это не ссылка на трек Spotify")
        try:
            async with asyncio.timeout(PROVIDER_TIMEOUT):
                async with aiohttp.ClientSession() as session:
                    async with session.get(_OEMBED.format(url=url)) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
        except Exception as e:
            raise ProviderError(f"не удалось получить данные Spotify: {e}") from e
        title = data.get("title") or ""
        artist, track = split_artist_title(title)
        return Track(
            provider=self.name,
            url=url,
            title=track,
            artist=artist,
            thumbnail=data.get("thumbnail_url") or "",
            track_id=spotify_track_id(url) or "",
        )
