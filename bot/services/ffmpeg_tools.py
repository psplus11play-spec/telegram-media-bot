"""FFmpeg helpers run via asyncio subprocess."""
import asyncio
import json
from pathlib import Path


async def _run(*args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {err.decode()[:500]}")


async def probe_duration(src: Path) -> float:
    """Media duration in seconds via ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(src),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe error: {err.decode()[:300]}")
    return float(json.loads(out.decode())["format"]["duration"])


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


async def video_to_gif(src: Path, dst: Path, start: str = "0", duration: int = 15, fps: int = 12, width: int = 480) -> Path:
    await _run(
        "-ss", start, "-t", str(duration), "-i", str(src),
        "-vf", f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        "-loop", "0", str(dst),
    )
    return dst


async def compress_to_size(src: Path, dst: Path, target_mb: float) -> Path:
    """Two-pass compression targeting a size in MB (video 70% of the budget)."""
    duration = await probe_duration(src)
    budget_kbits = target_mb * 8192 * 0.7 / max(duration, 1)
    rate = f"{max(int(budget_kbits), 100)}k"
    await _run("-i", str(src), "-c:v", "libx264", "-b:v", rate, "-pass", "1",
               "-an", "-f", "null", "/dev/null")
    await _run("-i", str(src), "-c:v", "libx264", "-b:v", rate, "-pass", "2",
               "-c:a", "aac", "-b:a", "128k", str(dst))
    for log in (Path("ffmpeg2pass-0.log"), Path("ffmpeg2pass-0.log.mbtree")):
        log.unlink(missing_ok=True)
    return dst


async def to_m4r(src: Path, dst: Path, start: str = "0") -> Path:
    """iPhone ringtone: AAC in .m4r, up to 30 seconds."""
    await _run("-ss", start, "-t", "30", "-i", str(src), "-vn",
               "-c:a", "aac", "-b:a", "192k", "-f", "ipod", str(dst))
    return dst


async def voice_to_mp3(src: Path, dst: Path) -> Path:
    await _run("-i", str(src), "-vn", "-c:a", "libmp3lame", "-b:a", "192k", str(dst))
    return dst


async def to_voice(src: Path, dst: Path) -> Path:
    """Opus OGG for Telegram voice notes."""
    await _run("-i", str(src), "-vn", "-c:a", "libopus", "-b:a", "64k",
               "-application", "voip", str(dst))
    return dst
