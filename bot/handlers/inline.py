"""Inline mode: @VidTuner_bot <song name> -> results -> track sent to any chat.

Telegram inline mode cannot stream an audio file as an inline result, so the
chosen result is downloaded under the queue and sent as audio into the chat
where the user picked it (inline_message_id carries the target chat via the
inline_message's chat, delivered by send to that chat id).
"""
import html
import time
import uuid
from pathlib import Path

from aiogram import Router
from aiogram.types import (
    ChosenInlineResult,
    FSInputFile,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from bot.config import get_settings
from bot.messages import DOWNLOAD_ERROR as DOWNLOAD_ERROR_SIMPLE
from bot.providers import SEARCH_PAGE_SIZE, get_provider
from bot.providers.base import Track
from bot.services import music_service
from bot.services.queue import queue

router = Router(name="inline")

_INLINE_TTL = 900
_PENDING: dict[str, dict] = {}


def _store() -> dict[str, dict]:
    now = time.monotonic()
    for key in [k for k, v in _PENDING.items() if now - v["ts"] > _INLINE_TTL]:
        _PENDING.pop(key, None)
    return _PENDING


@router.inline_query()
async def inline_search(query: InlineQuery) -> None:
    text = (query.query or "").strip()
    if len(text) < 3:
        await query.answer(
            [],
            cache_time=5,
            switch_pm_text="Введите название трека (мин. 3 символа)",
            switch_pm_parameter="start",
        )
        return
    try:
        provider = get_provider("ytmusic")
        results = await provider.search(text)
    except Exception:
        results = []
    articles = []
    for track in results[:SEARCH_PAGE_SIZE]:
        token = uuid.uuid4().hex[:12]
        _store()[token] = {"track": track, "ts": time.monotonic()}
        articles.append(InlineQueryResultArticle(
            id=token,
            title=track.display[:256],
            description="Отправит трек в этот чат"[:128],
            input_message_content=InputTextMessageContent(
                message_text=f"🎵 <b>{html.escape(track.display)}</b>\n<i>⬇️ Файл будет отправлен сюда…</i>",
                parse_mode="HTML",
            ),
        ))
    await query.answer(articles, cache_time=10, is_personal=True)


@router.chosen_inline_result()
async def inline_chosen(chosen: ChosenInlineResult) -> None:
    """Download the picked track and send audio to the user's chat with the bot.

    The chosen result's inline message cannot be resolved to a chat id by bots
    (inline_message_id has no chat resolver in Bot API), so the audio is sent
    into the private chat with the requesting user.
    """
    session = _PENDING.get(chosen.result_id)
    if session is None:
        return
    _PENDING.pop(chosen.result_id, None)
    track: Track = session["track"]
    bot = chosen.bot
    settings = get_settings()
    out_dir = Path(settings.download_temp_dir) / f"inline_{chosen.from_user.id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    status = await bot.send_message(
        chosen.from_user.id,
        f"🎵 <b>{html.escape(track.display)}</b>\n⬇️ Скачиваю (MP3 320)…",
    )

    async def _work() -> None:
        result = await music_service.download_and_tag(track.url, track, "mp3_320", out_dir)
        try:
            await bot.send_audio(
                chosen.from_user.id,
                FSInputFile(result.path),
                title=track.title[:64],
                performer=track.artist[:64] or None,
                duration=track.duration or None,
            )
        finally:
            result.path.unlink(missing_ok=True)

    try:
        await queue.run(chosen.from_user.id, _work)
        await status.edit_text(f"✅ Готово: <b>{html.escape(track.display)}</b> — файл выше.")
    except Exception as e:
        await status.edit_text(DOWNLOAD_ERROR_SIMPLE.format(error=html.escape(str(e))))
