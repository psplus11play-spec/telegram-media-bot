"""Music search handler: text query -> paged results -> format -> tagged audio."""
import html
import re
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

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
from bot.database.models import add_favorite, add_history, recent_searches, save_search
from bot.database.session import get_session_factory
from bot.handlers.links import URL_PATTERN
from bot.messages import DOWNLOAD_ERROR, SEND_ERROR
from bot.providers import (
    DEFAULT_PROVIDER,
    MATCH_PROVIDER,
    SEARCH_PAGE_SIZE,
    ProviderError,
    Track,
    get_provider,
    provider_for_url,
)
from bot.services import music_service
from bot.services.progress import ProgressReporter
from bot.services.queue import queue
from bot.utils.urlcheck import URLValidationError, validate_url

GROUP_NOTE = (
    "ℹ️ В группах я ищу музыку в инлайн-режиме: наберите @VidTuner_bot и название трека. "
    "Ссылки на видео/треки работают и так."
)

router = Router(name="music")

PAGE_KEEP = 30  # results cached per search session (several pages)
SESSION_TTL = 900  # seconds

_FORMAT_ROWS = [
    [("🎧 MP3 128", "mp3_128"), ("🎧 MP3 192", "mp3_192"), ("🎧 MP3 320", "mp3_320")],
    [("🎵 M4A", "m4a"), ("🎵 Opus", "opus")],
]

_sessions: dict[str, dict] = {}


def _session_store() -> dict[str, dict]:
    now = time.monotonic()
    for token in [t for t, s in _sessions.items() if now - s["ts"] > SESSION_TTL]:
        _sessions.pop(token, None)
    return _sessions


def _results_keyboard(token: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for idx, track in enumerate(_sessions[token]["results"]):
        kb.button(text=track.display[:64], callback_data=f"mu:{token}:{idx}")
    kb.adjust(1)
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"mp:{token}:{page - 1}"))
    nav.append(InlineKeyboardButton(text="❌ Отмена", callback_data=f"mc:{token}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"mp:{token}:{page + 1}"))
    kb.row(*nav)
    return kb.as_markup()


def _format_keyboard(token: str, idx: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for row in _FORMAT_ROWS:
        kb.row(*[InlineKeyboardButton(text=t, callback_data=f"mf:{token}:{idx}:{f}") for t, f in row])
    kb.row(InlineKeyboardButton(text="⬅️ К результатам", callback_data=f"mb:{token}"))
    return kb.as_markup()


def _render_page(results: list[Track], page: int) -> str:
    lines = [f"🔎 <b>Результаты поиска</b> — стр. {page + 1}"]
    for i, track in enumerate(results, 1):
        lines.append(f"{i}. {html.escape(track.display)}")
    return "\n".join(lines)


@router.message(Command("recent"))
async def cmd_recent(message: Message) -> None:
    async with get_session_factory()() as session:
        queries = await recent_searches(session, message.from_user.id)
    if not queries:
        await message.answer("🕘 Пока нет сохранённых поисков — просто напишите название трека.")
        return
    lines = ["🕘 <b>Последние поиски:</b>"] + [f"• {html.escape(q)}" for q in queries]
    await message.answer("\n".join(lines))


def is_music_link(text: str | None) -> bool:
    """True for links owned by music platforms; video links stay with links.py."""
    if not text or not re.match(URL_PATTERN, text.strip()):
        return False
    host = (urlparse(text.strip()).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in MUSIC_HOSTS)


def is_link(text: str | None) -> bool:
    """Any http(s) link: routed to the links (video) handler."""
    return bool(text and re.match(URL_PATTERN, text.strip()))


@router.message(F.text & F.func(is_link), F.chat.type == "private")
async def handle_link_in_music(message: Message) -> None:
    """Links must not be treated as song-search queries.

    Music router is registered before links router, so without this guard a
    TikTok/YouTube URL reaches the search handler and ytsearch finds nothing
    ("Ничего не нашлось"). Anything link-shaped is answered here only when the
    links handler is not going to pick it up; links handler matches the same
    regexp, so in practice this handler stays a safety net — but the search
    handler below must never see a URL.
    """
    return  # links router (registered later) handles it


@router.message(F.text & ~F.text.func(is_link) & ~F.text.func(is_music_link) & ~F.text.startswith("/"), F.chat.type == "private")
async def handle_music_search(message: Message) -> None:
    query = (message.text or "").strip()
    if not query:
        return
    status = await message.answer("🔎 Ищу…")
    try:
        provider = get_provider(DEFAULT_PROVIDER)
        results = await provider.search(query)
    except ProviderError as e:
        await status.edit_text(f"😕 {e}")
        return
    except Exception as e:
        await status.edit_text(DOWNLOAD_ERROR.format(error=html.escape(str(e))))
        return
    if not results:
        await status.edit_text("😔 Ничего не нашлось — попробуйте другой запрос.")
        return
    results = results[:PAGE_KEEP]
    token = uuid.uuid4().hex[:12]
    _session_store()[token] = {"query": query, "results": results, "page": 0, "ts": time.monotonic()}
    async with get_session_factory()() as session:
        await save_search(session, message.from_user.id, query, DEFAULT_PROVIDER)
    total_pages = (len(results) + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE
    await status.edit_text(_render_page(results[:SEARCH_PAGE_SIZE], 0), reply_markup=_results_keyboard(token, 0, total_pages))


@router.callback_query(F.data.regexp(r"^mp:([0-9a-f]{12}):(\d+)$"))
async def cb_page(cb: CallbackQuery) -> None:
    token, page = cb.data.split(":")[1], int(cb.data.split(":")[2])
    session = _session_store().get(token)
    if session is None:
        await cb.answer("⌛ Поиск устарел — отправьте запрос заново", show_alert=True)
        return
    session["page"] = page
    results = session["results"]
    total_pages = (len(results) + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE
    chunk = results[page * SEARCH_PAGE_SIZE:(page + 1) * SEARCH_PAGE_SIZE]
    await cb.message.edit_text(_render_page(chunk, page), reply_markup=_results_keyboard(token, page, total_pages))
    await cb.answer()


@router.callback_query(F.data.regexp(r"^mc:([0-9a-f]{12})$"))
async def cb_cancel(cb: CallbackQuery) -> None:
    token = cb.data.split(":")[1]
    _session_store().pop(token, None)
    await cb.message.delete()
    await cb.answer("Отменено")


@router.callback_query(F.data.regexp(r"^mu:([0-9a-f]{12}):(\d+)$"))
async def cb_pick_track(cb: CallbackQuery) -> None:
    token, idx = cb.data.split(":")[1], int(cb.data.split(":")[2])
    session = _session_store().get(token)
    if session is None or idx >= len(session["results"]):
        await cb.answer("⌛ Поиск устарел — отправьте запрос заново", show_alert=True)
        return
    track = session["results"][idx]
    await cb.message.edit_text(
        f"🎵 <b>{html.escape(track.display)}</b>\nВыберите формат аудио:",
        reply_markup=_format_keyboard(token, idx),
    )
    await cb.answer()


@router.callback_query(F.data.regexp(r"^mb:([0-9a-f]{12})$"))
async def cb_back(cb: CallbackQuery) -> None:
    token = cb.data.split(":")[1]
    session = _session_store().get(token)
    if session is None:
        await cb.answer("⌛ Поиск устарел — отправьте запрос заново", show_alert=True)
        return
    page = session["page"]
    results = session["results"]
    total_pages = (len(results) + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE
    chunk = results[page * SEARCH_PAGE_SIZE:(page + 1) * SEARCH_PAGE_SIZE]
    await cb.message.edit_text(_render_page(chunk, page), reply_markup=_results_keyboard(token, page, total_pages))
    await cb.answer()


@router.callback_query(F.data.regexp(r"^mf:([0-9a-f]{12}):(\d+):(\w+)$"))
async def cb_download(cb: CallbackQuery) -> None:
    token, idx, fmt = cb.data.split(":")[1:]
    idx = int(idx)
    session = _session_store().get(token)
    if session is None or idx >= len(session["results"]):
        await cb.answer("⌛ Поиск устарел — отправьте запрос заново", show_alert=True)
        return
    await cb.answer()
    track: Track = session["results"][idx]
    status = await cb.message.edit_text("⬇️ Скачиваю аудио…")

    async def notify(text: str) -> None:
        try:
            await status.edit_text(text)
        except Exception:
            pass

    settings = get_settings()
    out_dir = Path(settings.download_temp_dir) / f"music_{cb.from_user.id}"
    reporter = ProgressReporter(status, label=f"🎵 {track.title[:32]}")
    try:
        result = await queue.run(
            cb.from_user.id,
            lambda: music_service.download_and_tag(track.url, track, fmt, out_dir, reporter.hook),
            notify=notify,
            label=track.display,
        )
    except Exception as e:
        await status.edit_text(DOWNLOAD_ERROR.format(error=html.escape(str(e))))
        return
    path = result.path
    try:
        await cb.message.answer_audio(
            FSInputFile(path),
            title=track.title[:64],
            performer=track.artist[:64] or None,
            duration=track.duration or None,
        )
        async with get_session_factory()() as session:
            await add_history(session, cb.from_user.id, track.url, path.stem, "audio", "")
            await add_favorite(session, cb.from_user.id, track.url, track.title, track.artist)
    except Exception as e:
        await status.edit_text(SEND_ERROR.format(error=html.escape(str(e))))
        path.unlink(missing_ok=True)
        return
    path.unlink(missing_ok=True)
    await status.edit_text("✅ Отправлено и добавлено в ⭐ /favorites")


MUSIC_HOSTS = ("open.spotify.com", "soundcloud.com", "music.youtube.com")


@router.message(F.text.func(is_music_link))
async def handle_music_url(message: Message) -> None:
    """Route a music-platform URL to metadata (Spotify resolves audio via match)."""
    url = (message.text or "").strip()
    try:
        url = validate_url(url)
    except URLValidationError as e:
        await message.answer(f"🚫 {e}")
        return
    owner = provider_for_url(url) or DEFAULT_PROVIDER
    status = await message.answer("🔎 Читаю данные трека…")
    try:
        provider = get_provider(owner)
        track = await provider.metadata(url)
        if not provider.caps.search and owner == "spotify":
            matcher = get_provider(MATCH_PROVIDER)
            matched = await matcher.search(f"{track.artist} {track.title}".strip())
            if not matched:
                await status.edit_text("😔 Не нашёл аудио-источник для этого трека Spotify.")
                return
            best = matched[0]
            best.artist = best.artist or track.artist
            best.title = best.title or track.title
            best.thumbnail = best.thumbnail or track.thumbnail
            best.album = track.album
            best.year = track.year
            track = best
        token = uuid.uuid4().hex[:12]
        _session_store()[token] = {"query": url, "results": [track], "page": 0, "ts": time.monotonic()}
        await status.edit_text(
            f"🎵 <b>{html.escape(track.display)}</b>\nВыберите формат аудио:",
            reply_markup=_format_keyboard(token, 0),
        )
    except ProviderError as e:
        await status.edit_text(f"😕 {e}")
    except Exception as e:
        await status.edit_text(DOWNLOAD_ERROR.format(error=html.escape(str(e))))
