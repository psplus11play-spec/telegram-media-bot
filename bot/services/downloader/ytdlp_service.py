"""yt-dlp based downloader with quality selection."""
import asyncio
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

from bot.config import get_settings

QUALITY_FORMATS = {
    "360p": "bv*[height<=360]+ba/b[height<=360]",
    "720p": "bv*[height<=720]+ba/b[height<=720]",
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "best": "bv*+ba/b",
}


@dataclass
class MediaInfo:
    title: str
    duration: int
    platform: str
    is_playlist: bool
    entries_count: int = 0


class _ThreadSafeHook:
    """Bridge sync yt-dlp hook to async reporter running in the event loop."""

    def __init__(self, async_hook):
        self._async_hook = async_hook
        self._loop = asyncio.get_event_loop()

    def __call__(self, data: dict) -> None:
        asyncio.run_coroutine_threadsafe(self._async_hook(data), self._loop)


def probe(url: str) -> MediaInfo:
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    if info is None:
        raise RuntimeError("Не удалось получить информацию по ссылке")
    is_playlist = info.get("_type") == "playlist"
    return MediaInfo(
        title=info.get("title") or "media",
        duration=int(info.get("duration") or 0),
        platform=info.get("extractor_key") or "",
        is_playlist=is_playlist,
        entries_count=len(info.get("entries") or []) if is_playlist else 0,
    )


async def probe_async(url: str) -> MediaInfo:
    return await asyncio.to_thread(probe, url)


def _download(url: str, quality: str | None, audio_only: bool, out_dir: Path, progress_hook=None) -> list[Path]:
    settings = get_settings()
    outtmpl = str(out_dir / "%(title).80s.%(ext)s")
    common = {
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": settings.download_max_file_size,
        "restrictfilenames": True,
    }
    if progress_hook is not None:
        common["progress_hooks"] = [_ThreadSafeHook(progress_hook)]
    if audio_only:
        common.update({
            "format": "ba/b",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": settings.download_default_audio_format,
                "preferredquality": settings.download_default_audio_bitrate,
            }],
        })
    else:
        common["format"] = QUALITY_FORMATS.get(quality or "720p", QUALITY_FORMATS["720p"])
        common["merge_output_format"] = "mp4"
    with yt_dlp.YoutubeDL(common) as ydl:
        ydl.extract_info(url, download=True)
    files = sorted(out_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return [f for f in files if f.is_file()][:1]


async def download_async(url: str, quality: str | None, audio_only: bool, out_dir: Path, progress_hook=None) -> list[Path]:
    if progress_hook is not None:
        return await asyncio.to_thread(_download, url, quality, audio_only, out_dir, progress_hook)
    return await asyncio.to_thread(_download, url, quality, audio_only, out_dir)
