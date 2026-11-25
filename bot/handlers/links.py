"""Link and quality-choice handlers with progress bar."""
import time
import uuid
from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.config import get_settings
from bot.database.models import add_history
from bot.database.session import get_session_factory
from bot.keyboards.inline import playlist_keyboard, quality_keyboard
from bot.messages import (
    CHOOSE_QUALITY,
    DOWNLOAD_ERROR,
    DOWNLOAD_START,
    DURATION,
    PLAYLIST_LIST,
    SEND_ERROR,
    STALE,
)
from bot.services.downloader import ytdlp_service
from bot.services.progress import ProgressReporter
from bot.services.queue import queue

router = Router()
URL_PATTERN = r"^https?://\S+$"
# urls kept out of callback_data (64-byte limit) and addressed by token;
# entries expire after PENDING_TTL so the dict cannot grow unbounded
_pending: dict[str, tuple[str, float]] = {}
PENDING_TTL = 3600.0


def remember_url(url: str) -> str:
    now = time.monotonic()
    expired = [t for t, (_, ts) in _pending.items() if now - ts > PENDING_TTL]
    for t in expired:
        _pending.pop(t, None)
    token = uuid.uuid4().hex[:24]
    _pending[token] = (url, now)
    return token


def _pending_url(token: str) -> str | None:
    entry = _pending.get(token)
    return entry[0] if entry else None


MAX_PLAYLIST_ITEMS = 10


@router.message(F.text.regexp(URL_PATTERN))
async def handle_link(message: Message) -> None:
    url = message.text.strip()
    try:
        info = await ytdlp_service.probe_async(url)
    except Exception as e:
        await message.answer(DOWNLOAD_ERROR.format(error=e))
        return
    if info.is_playlist and info.entries:
        await message.answer(
            PLAYLIST_LIST.format(title=info.title, count=info.entries_count),
            reply_markup=playlist_keyboard(remember_url(url), len(info.entries)),
        )
        return
    extra = ""
    if info.duration:
        extra += DURATION.format(m=info.duration // 60, s=info.duration % 60)
    await message.answer(
        CHOOSE_QUALITY.format(title=info.title, extra=extra),
        reply_markup=quality_keyboard(remember_url(url)),
    )


@router.callback_query(F.data.regexp(r"^dl:(v|a):([0-9a-f]{24})(?::(\w+))?$"))
async def do_download(cb: CallbackQuery) -> None:
    _, kind, token, quality = [*cb.data.split(":"), None][:4]
    url = _pending_url(token)
    if not url:
        await cb.answer(STALE, show_alert=True)
        return
    _pending.pop(token, None)
    await cb.answer(DOWNLOAD_START)
    status = await cb.message.answer("🔎 Ищу свободный слот…")
    reporter = ProgressReporter(status, "⬇️ Скачиваю")

    async def notify(text: str) -> None:
        await status.edit_text(text)

    settings = get_settings()
    out_dir = Path(settings.download_temp_dir) / str(cb.from_user.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        files = await queue.run(
            cb.from_user.id,
            lambda: ytdlp_service.download_async(
                url, quality if kind == "v" else None, kind == "a", out_dir, reporter.hook
            ),
            notify=notify,
        )
    except Exception as e:
        await status.edit_text(DOWNLOAD_ERROR.format(error=e))
        return
    if not files:
        await status.edit_text(DOWNLOAD_ERROR.format(error="файл не найден"))
        return
    path = files[0]
    try:
        if kind == "a":
            await cb.message.answer_audio(FSInputFile(path))
            media_type = "audio"
        else:
            await cb.message.answer_video(FSInputFile(path))
            media_type = "video"
        async with get_session_factory()() as session:
            await add_history(session, cb.from_user.id, url, path.stem, media_type, "")
    except Exception as e:
        await status.edit_text(SEND_ERROR.format(error=e))
        path.unlink(missing_ok=True)
        return
    await status.delete()
    path.unlink(missing_ok=True)


@router.callback_query(F.data.regexp(r"^pl:(v|a):([0-9a-f]{24}):(\d+):(\w+)$"))
async def do_playlist_download(cb: CallbackQuery) -> None:
    """Download one playlist entry by index (1-based) at a chosen quality."""
    _, kind, token, idx_s, quality = cb.data.split(":")
    url = _pending_url(token)
    if not url:
        await cb.answer(STALE, show_alert=True)
        return
    try:
        entry_url = await ytdlp_service.playlist_entry_url_async(url, int(idx_s))
    except Exception as e:
        await cb.answer(DOWNLOAD_ERROR.format(error=e), show_alert=True)
        return
    _pending.pop(token, None)
    cb.data = f"dl:{kind}:{remember_url(entry_url)}:{quality}"
    await do_download(cb)
