"""Music provider registry."""
from bot.providers.base import (
    SEARCH_PAGE_SIZE,
    MusicProvider,
    ProviderCaps,
    ProviderError,
    Track,
    dedupe,
    provider_for_url,
)
from bot.providers.search import SoundCloudProvider, YouTubeMusicProvider
from bot.providers.spotify import SpotifyProvider

_providers: dict[str, MusicProvider] = {}
for cls in (YouTubeMusicProvider, SoundCloudProvider, SpotifyProvider):
    instance = cls()
    _providers[instance.name] = instance

DEFAULT_PROVIDER = "ytmusic"
# audio for a metadata-only provider is resolved by matching on this one
MATCH_PROVIDER = "ytmusic"


def get_provider(name: str) -> MusicProvider:
    provider = _providers.get(name)
    if provider is None:
        raise ProviderError(f"неизвестный провайдер: {name}")
    return provider


def search_providers() -> list[MusicProvider]:
    return [p for p in _providers.values() if p.caps.search and p.available()]


__all__ = [
    "DEFAULT_PROVIDER",
    "MATCH_PROVIDER",
    "SEARCH_PAGE_SIZE",
    "MusicProvider",
    "ProviderCaps",
    "ProviderError",
    "SoundCloudProvider",
    "SpotifyProvider",
    "Track",
    "dedupe",
    "get_provider",
    "provider_for_url",
    "search_providers",
]
