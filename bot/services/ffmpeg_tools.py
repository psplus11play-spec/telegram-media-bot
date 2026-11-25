"""FFmpeg helpers run via asyncio subprocess."""
import asyncio
from pathlib import Path


async def _run(*args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {err.decode()[:500]}")


async def video_to_audio(src: Path, dst: Path, bitrate: str = "320") -> Path:
    await _run("-i", str(src), "-vn", "-b:a", f"{bitrate}k", str(dst))
    return dst


async def video_to_note(src: Path, dst: Path, duration: int = 60) -> Path:
    await _run(
        "-i", str(src), "-t", str(duration),
        "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=640:640",
        "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", str(dst),
    )
    return dst


async def trim(src: Path, dst: Path, start: str, end: str) -> Path:
    await _run("-ss", start, "-to", end, "-i", str(src), "-c", "copy", str(dst))
    return dst


async def extract_thumbnail(src: Path, dst: Path) -> Path:
    await _run("-ss", "1", "-i", str(src), "-frames:v", "1", str(dst))
    return dst
