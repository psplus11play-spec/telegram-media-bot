"""FFmpeg tools handler: /tools menu, media tools on sent files."""
import html
import re
import time
import uuid
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import get_settings
from bot.handlers.links import URL_PATTERN  # noqa: F401  (re-exported for tests)
from bot.messages import DOWNLOAD_ERROR
from bot.services import ffmpeg_tools
from bot.services.progress import ProgressReporter

router = Router(name="tools")

TOOLS_MENU = (
    "🛠 <b>Инструменты</b>\n\n"
    "Пришлите видео/аудио/голосовое — и выберите действие под файлом:\n"
    "• 🎵 Видео → MP3\n"
    "• ⭕️ Видео → видеозаметка (до 60 сек)\n"
    "• 🎞 Видео → GIF (до 15 сек)\n"
    "• ✂️ Обрезка по времени (ответ вида «с 0:30 до 1:15»)\n"
    "• 🗜 Сжать видео до заданного размера\n"
    "• 🎤 Голосовое ⇄ MP3\n"
    "• 📱 Рингтон .m4r (до 30 сек)\n"
    "• 🖼 Обложка/превью видео\n\n"
    "Или отправьте файл прямо сейчас."
)

TRIM_RE = re.compile(r"^\s*(?:с\s*)?(\d{1,2}):([0-5]?\d)\s*(?:до|-|—|–)\s*(\d{1,2}):([0-5]?\d)\s*$")
TOOL_TTL = 1800  # seconds a tool session stays available


def _store() -> dict[str, dict]:
    now = time.monotonic()
    for token in [t for t, s in _TOOL_SESSIONS.items() if now - s["ts"] > TOOL_TTL]:
        _TOOL_SESSIONS.pop(token, None)
    return _TOOL_SESSIONS


_TOOL_SESSIONS: dict[str, dict] = {}


def _tools_kb(token: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎵 Видео → MP3", callback_data=f"t:{token}:mp3"),
           InlineKeyboardButton(text="⭕️ Видеозаметка", callback_data=f"t:{token}:note"))
    kb.row(InlineKeyboardButton(text="🎞 GIF", callback_data=f"t:{token}:gif"),
           InlineKeyboardButton(text="🖼 Обложка", callback_data=f"t:{token}:thumb"))
    kb.row(InlineKeyboardButton(text="📱 Рингтон .m4r", callback_data=f"t:{token}:m4r"),
           InlineKeyboardButton(text="🎤 Голосовое", callback_data=f"t:{token}:voice"))
    kb.row(InlineKeyboardButton(text="✂️ Обрезка (напишите: с 0:30 до 1:15)", callback_data=f"t:{token}:trim"))
    kb.row(InlineKeyboardButton(text="🗜 Сжать до 25 МБ", callback_data=f"t:{token}:compress"))
    return kb.as_markup()


def _register_file(message: Message, path: Path, is_video: bool) -> str:
    token = uuid.uuid4().hex[:12]
    _store()[token] = {"path": path, "video": is_video, "ts": time.monotonic()}
    return token


def parse_time(s: str) -> str | None:
    """Normalize '0:30' or '30' or '90' to an ffmpeg timestamp; None if bad."""
    s = s.strip()
    if s.isdigit():
        return s
    if re.match(r"^\d{1,2}:[0-5]?\d$", s):
        return s
    return None


def parse_trim(text: str) -> tuple[str, str] | None:
    m = TRIM_RE.match(text)
    if not m:
        return None
    m1, s1, m2, s2 = m.groups()
    start = int(m1) * 60 + int(s1)
    end = int(m2) * 60 + int(s2)
    if end <= start:
        return None
    return f"{m1}:{s1}", f"{m2}:{s2}"


@router.message(Command("tools"))
async def cmd_tools(message: Message) -> None:
    await message.answer(TOOLS_MENU)


@router.message(F.video | F.document)
async def handle_media(message: Message) -> None:
    if message.from_user is not None and message.text and message.text.startswith("/"):
        return  # commands are not files
    if message.video is not None:
        file = message.video
        is_video = True
    else:
        file = message.document
        is_video = (message.document.mime_type or "").startswith("video/")
    if (file.file_size or 0) > 2_000_000_000:
        await message.answer("😕 Файл слишком большой (лимит Telegram 2 ГБ).")
        return
    status = await message.answer("⬇️ Загружаю файл…")
    settings = get_settings()
    out_dir = Path(settings.download_temp_dir) / f"tools_{message.from_user.id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = getattr(file, "file_name", None) or f"{uuid.uuid4().hex[:8]}.mp4"
    ext = Path(name).suffix or (".mp4" if is_video else ".mp3")
    path = out_dir / f"src_{uuid.uuid4().hex[:8]}{ext}"
    try:
        await message.bot.download(message, destination=path)
    except Exception as e:
        await status.edit_text(DOWNLOAD_ERROR.format(error=html.escape(str(e))))
        return
    token = _register_file(message, path, is_video)
    if not is_video:
        await status.edit_text("🎧 Файл загружен. Доступно: 🎤 конвертировать в голосовое.")
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🎤 В голосовое", callback_data=f"t:{token}:tovoice"))
        await status.edit_reply_markup(reply_markup=kb.as_markup())
        return
    await status.edit_text("🛠 Файл загружен — выберите инструмент:", reply_markup=_tools_kb(token))


@router.message(F.voice | F.audio | F.video_note)
async def handle_audio_media(message: Message) -> None:
    kind, _file = (("voice", message.voice) if message.voice is not None
                  else (("audio", message.audio) if message.audio is not None
                        else ("note", message.video_note)))
    status = await message.answer("⬇️ Загружаю…")
    settings = get_settings()
    out_dir = Path(settings.download_temp_dir) / f"tools_{message.from_user.id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"src_{uuid.uuid4().hex[:8]}.ogg" if kind != "audio" else out_dir / f"src_{uuid.uuid4().hex[:8]}.mp3"
    try:
        await message.bot.download(message, destination=path)
    except Exception as e:
        await status.edit_text(DOWNLOAD_ERROR.format(error=html.escape(str(e))))
        return
    token = _register_file(message, path, False)
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎵 В MP3", callback_data=f"t:{token}:mp3"))
    kb.row(InlineKeyboardButton(text="🎤 В голосовое", callback_data=f"t:{token}:tovoice"))
    await status.edit_text("🎧 Файл загружен — выберите действие:", reply_markup=kb.as_markup())


@router.callback_query(F.data.regexp(r"^t:([0-9a-f]{12}):(\w+)$"))
async def cb_tool(cb: CallbackQuery) -> None:  # noqa: PLR0912, PLR0915
    token, tool = cb.data.split(":")[1:]
    session = _store().get(token)
    if session is None:
        await cb.answer("⌛ Файл устарел — отправьте его заново", show_alert=True)
        return
    if not session["video"] and tool in {"mp3", "note", "gif", "thumb", "m4r", "compress", "trim"}:
        await cb.answer("Этот инструмент только для видео", show_alert=True)
        return
    await cb.answer()
    src: Path = session["path"]
    out_dir = src.parent
    status = await cb.message.edit_text("🛠 Обрабатываю…")
    ProgressReporter(status, label="🛠 " + tool)
    dst = out_dir / f"{tool}_{uuid.uuid4().hex[:8]}{TOOL_EXT[tool]}"
    try:
        if tool == "mp3":
            await ffmpeg_tools.video_to_audio(src, dst)
            await cb.message.answer_audio(FSInputFile(dst), title="Audio")
        elif tool == "note":
            await ffmpeg_tools.video_to_note(src, dst)
            await cb.message.answer_video_note(FSInputFile(dst))
        elif tool == "gif":
            await ffmpeg_tools.video_to_gif(src, dst)
            await cb.message.answer_animation(FSInputFile(dst))
        elif tool == "thumb":
            await ffmpeg_tools.extract_thumbnail(src, dst)
            await cb.message.answer_photo(FSInputFile(dst))
        elif tool == "m4r":
            await ffmpeg_tools.to_m4r(src, dst)
            await cb.message.answer_audio(FSInputFile(dst), title="Ringtone.m4r")
        elif tool == "voice":
            await ffmpeg_tools.to_voice(src, dst)
            await cb.message.answer_voice(FSInputFile(dst))
        elif tool == "tovoice":
            await ffmpeg_tools.to_voice(src, dst)
            await cb.message.answer_voice(FSInputFile(dst))
        elif tool == "compress":
            await status.edit_text("🗜 Сжимаю до 25 МБ (двухпроходное кодирование — это долго)…")
            await ffmpeg_tools.compress_to_size(src, dst, 25.0)
            await cb.message.answer_video(FSInputFile(dst), supports_streaming=True)
        elif tool == "trim":
            await cb.message.edit_text(
                "✂️ Ответьте на это сообщение в формате:\n<code>с 0:30 до 1:15</code>"
            )
            _store()[token]["await_trim"] = True
            return
        else:
            await status.edit_text("😕 Неизвестный инструмент")
            return
    except Exception as e:
        await status.edit_text(DOWNLOAD_ERROR.format(error=html.escape(str(e))))
        dst.unlink(missing_ok=True)
        return
    dst.unlink(missing_ok=True)
    try:
        await status.delete()
    except Exception:
        pass


TOOL_EXT = {
    "mp3": ".mp3", "note": ".mp4", "gif": ".gif", "thumb": ".jpg",
    "m4r": ".m4r", "voice": ".ogg", "tovoice": ".ogg", "compress": ".mp4",
    "trim": ".mp4",
}


@router.message(F.text.regexp(r"^\s*(?:с\s*)?\d{1,2}:[0-5]?\d\s*(?:до|-|—|–)\s*\d{1,2}:[0-5]?\d\s*$"))
async def handle_trim_reply(message: Message) -> None:
    """Trim applied by replying to a tool message with a time range."""
    if message.reply_to_message is None:
        return
    target = _find_session_for_message(message.reply_to_message.message_id, message.chat.id)
    if target is None:
        await message.answer("🤔 Это не ответ на сообщение с инструментом — пришлите файл заново.")
        return
    _token, session = target
    parsed = parse_trim(message.text or "")
    if parsed is None:
        await message.answer("😕 Не понял диапазон. Пример: <code>с 0:30 до 1:15</code>")
        return
    start, end = parsed
    status = await message.answer(f"✂️ Режу {start} → {end}…")
    src: Path = session["path"]
    dst = src.parent / f"trim_{uuid.uuid4().hex[:8]}.mp4"
    try:
        await ffmpeg_tools.trim(src, dst, start, end)
        await message.answer_video(FSInputFile(dst), supports_streaming=True)
    except Exception as e:
        await status.edit_text(DOWNLOAD_ERROR.format(error=html.escape(str(e))))
        dst.unlink(missing_ok=True)
        return
    dst.unlink(missing_ok=True)
    await status.delete()


def _find_session_for_message(message_id: int, chat_id: int) -> tuple[str, dict] | None:
    # sessions don't store the message id (handlers are stateless); matching a
    # reply to the source file happens via the most recent session in the chat
    latest = None
    for token, session in _store().items():
        if latest is None or session["ts"] > latest[1]["ts"]:
            latest = (token, session)
    return latest
