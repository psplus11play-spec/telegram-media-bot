"""Song recognition handler: voice/audio/video-note -> Shazam -> download."""
import html
import time
import uuid
from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import get_settings
from bot.messages import DOWNLOAD_ERROR
from bot.providers import DEFAULT_PROVIDER, get_provider
from bot.services import recognition
from bot.services.recognition import Recognized

router = Router(name="shazam")

RECOGNIZE_TTL = 1800
_sessions: dict[str, dict] = {}


def _store() -> dict[str, dict]:
    now = time.monotonic()
    for token in [t for t, s in _sessions.items() if now - s["ts"] > RECOGNIZE_TTL]:
        _sessions.pop(token, None)
    return _sessions


def _kb(token: str, has_match: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_match:
        kb.row(InlineKeyboardButton(text="⬇️ Скачать трек", callback_data=f"sr:{token}"))
    kb.row(InlineKeyboardButton(text="🔄 Распознать ещё", callback_data="sr:retry"))
    return kb.as_markup()


def _card(match: Recognized) -> str:
    lines = ["🎼 <b>Трек распознан!</b>", f"🎵 <b>{html.escape(match.title)}</b>"]
    if match.artist:
        lines.append(f"👤 {html.escape(match.artist)}")
    if match.album:
        lines.append(f"💿 {html.escape(match.album)}" + (f" ({html.escape(match.year)})" if match.year else ""))
    if match.url:
        lines.append(f"🔗 {match.url}")
    return "\n".join(lines)


async def _download_media(message: Message) -> Path | None:
    settings = get_settings()
    out_dir = Path(settings.download_temp_dir) / f"shazam_{message.from_user.id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"in_{uuid.uuid4().hex[:8]}.ogg"
    try:
        await message.bot.download(message, destination=path)
    except Exception:
        return None
    return path


async def _match_on_music(match: Recognized) -> str | None:
    """Find the track in the music search provider; return a session token."""
    provider = get_provider(DEFAULT_PROVIDER)
    results = await provider.search(f"{match.artist} {match.title}".strip())
    if not results:
        return None
    best = results[0]
    best.artist = best.artist or match.artist
    best.title = best.title or match.title
    best.thumbnail = best.thumbnail or match.cover
    best.album = best.album or match.album
    token = uuid.uuid4().hex[:12]
    _store()[token] = {"track": best, "ts": time.monotonic()}
    return token


def _is_short_audio(message: Message) -> bool:
    """Audio up to 90 s goes to recognition; longer audio is a download job."""
    return message.audio is not None and (message.audio.duration or 0) <= 90


@router.message(F.voice | F.video_note | F.func(_is_short_audio))
async def handle_recognize(message: Message) -> None:
    status = await message.answer("🎧 Слушаю фрагмент…")
    src = await _download_media(message)
    if src is None:
        await status.edit_text(DOWNLOAD_ERROR.format(error="не удалось скачать файл"))
        return
    try:
        match = await recognition.recognize(src)
    except Exception as e:
        src.unlink(missing_ok=True)
        await status.edit_text(DOWNLOAD_ERROR.format(error=html.escape(str(e))))
        return
    src.unlink(missing_ok=True)
    if match is None:
        await status.edit_text("😔 Не смог узнать трек. Запишите фрагмент ближе к музыке, без шума.", reply_markup=_kb("", False))
        return
    token = await _match_on_music(match)
    await status.edit_text(_card(match), reply_markup=_kb(token, token is not None))


@router.callback_query(F.data.regexp(r"^sr:(retry|[0-9a-f]{12})$"))
async def cb_download(cb: CallbackQuery) -> None:
    arg = cb.data.split(":")[1]
    if arg == "retry":
        await cb.answer("Пришлите новый голосовой/аудио фрагмент", show_alert=True)
        return
    session = _store().get(arg)
    if session is None:
        await cb.answer("⌛ Результат устарел — распознайте заново", show_alert=True)
        return
    await cb.answer()
    track = session["track"]
    from bot.handlers.music import _format_keyboard

    await cb.message.edit_text(
        f"🎵 <b>{html.escape(track.display)}</b>\nВыберите формат аудио:",
        reply_markup=_format_keyboard(arg, 0),
    )
