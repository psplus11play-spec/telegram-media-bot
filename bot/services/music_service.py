"""Audio download for music search: formats, ID3/Vorbis tags, cover art.

Formats offered map to real transcoded outputs from the best available audio
source; genuine lossless sources do not exist here, so WAV/FLAC are never
advertised.
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path

import yt_dlp
from mutagen.flac import Picture
from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TRCK
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from bot.config import get_settings
from bot.providers.base import Track, download_cover
from bot.services.downloader.ytdlp_service import _ThreadSafeHook

AUDIO_FORMATS: dict[str, dict] = {
    # key: (extension, codec, bitrate or None for codec-default)
    "mp3_128": {"ext": "mp3", "codec": "mp3", "bitrate": "128"},
    "mp3_192": {"ext": "mp3", "codec": "mp3", "bitrate": "192"},
    "mp3_320": {"ext": "mp3", "codec": "mp3", "bitrate": "320"},
    "m4a": {"ext": "m4a", "codec": "m4a", "bitrate": None},
    "opus": {"ext": "opus", "codec": "opus", "bitrate": None},
}


@dataclass
class AudioResult:
    path: Path
    track: Track
    format_key: str


def _extract_codec(fmt: str, bitrate: str | None) -> str:
    if fmt == "m4a":
        return "aac"
    if fmt == "opus":
        return "opus"
    return "libmp3lame" if fmt == "mp3" else fmt


def _download_audio(track_url: str, fmt: str, out_dir: Path, progress_hook=None) -> Path:
    spec = AUDIO_FORMATS[fmt]
    opts = {
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "format": "ba/b",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": spec["codec"],
            "preferredquality": spec["bitrate"] or "5",
        }],
    }
    settings = get_settings()
    if settings.download_ytdlp_cookies_file is not None:
        opts["cookiefile"] = str(settings.download_ytdlp_cookies_file)
    if progress_hook is not None:
        opts["progress_hooks"] = [progress_hook]
    before = set(out_dir.iterdir())
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(track_url, download=True)
    new = [p for p in out_dir.iterdir() if p not in before and p.suffix.lstrip(".") == spec["ext"]]
    if not new:
        raise RuntimeError("файл не найден после конвертации")
    return max(new, key=lambda p: p.stat().st_mtime)


def _tag_mp3(path: Path, track: Track, cover: Path | None) -> None:
    audio = MP3(path)
    tags = ID3()
    tags.add(TIT2(encoding=3, text=track.title))
    tags.add(TPE1(encoding=3, text=track.artist))
    if track.album:
        tags.add(TALB(encoding=3, text=track.album))
    if track.year:
        tags.add(TDRC(encoding=3, text=track.year))
    if track.track_number:
        tags.add(TRCK(encoding=3, text=str(track.track_number)))
    if cover:
        tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover.read_bytes()))
    audio.tags = tags
    audio.save()


def _tag_m4a(path: Path, track: Track, cover: Path | None) -> None:
    audio = MP4(path)
    audio["\xa9nam"] = [track.title]
    audio["\xa9ART"] = [track.artist]
    if track.album:
        audio["\xa9alb"] = [track.album]
    if track.year:
        audio["\xa9day"] = [track.year]
    if cover:
        audio["covr"] = [MP4Cover(cover.read_bytes(), imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save()


def _tag_vorbis(path: Path, track: Track, cover: Path | None, cls) -> None:
    audio = cls(path)
    audio["title"] = [track.title]
    audio["artist"] = [track.artist]
    if track.album:
        audio["album"] = [track.album]
    if track.year:
        audio["date"] = [track.year]
    if cover:
        pic = Picture()
        pic.type = 3
        pic.mime = "image/jpeg"
        pic.desc = "Cover"
        pic.data = cover.read_bytes()
        audio["metadata_block_picture"] = [pic.base64()]
    audio.save()


def _tag_file_sync(path: Path, track: Track, cover: Path | None) -> None:
    ext = path.suffix.lstrip(".")
    if ext == "mp3":
        _tag_mp3(path, track, cover)
    elif ext == "m4a":
        _tag_m4a(path, track, cover)
    elif ext == "opus":
        _tag_vorbis(path, track, cover, OggOpus)
    elif ext == "ogg":
        _tag_vorbis(path, track, cover, OggVorbis)


async def download_and_tag(track_url: str, track: Track, fmt: str, out_dir: Path, progress_hook=None) -> AudioResult:
    """Download the track as the chosen format, embed tags and cover art."""
    if fmt not in AUDIO_FORMATS:
        raise RuntimeError(f"неизвестный формат: {fmt}")
    out_dir.mkdir(parents=True, exist_ok=True)
    # bridge the async reporter hook into yt-dlp's sync worker thread;
    # the bridge must be created on the event-loop thread, not in to_thread
    bridge = _ThreadSafeHook(progress_hook) if progress_hook is not None else None
    path = await asyncio.to_thread(_download_audio, track_url, fmt, out_dir, bridge)

    cover: Path | None = None
    if track.thumbnail:
        cover = out_dir / f"cover_{track.track_id or 'art'}.jpg"
        try:
            await download_cover(track.thumbnail, cover)
        except Exception:
            cover = None
    try:
        await asyncio.to_thread(_tag_file_sync, path, track, cover)
    except Exception:
        pass  # untagged audio beats a failed send
    if cover:
        cover.unlink(missing_ok=True)
    return AudioResult(path=path, track=track, format_key=fmt)
