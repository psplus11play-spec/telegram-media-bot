"""Command handlers: /start, /help, /history, /favorites, /settings."""
import html

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import (
    get_or_create_user,
    remove_favorite,
    user_favorites,
    user_history,
)
from bot.database.session import get_session_factory
from bot.messages import (
    FAVORITES_EMPTY,
    FAVORITES_HEAD,
    HELP,
    HISTORY_EMPTY,
    HISTORY_HEAD,
    HISTORY_ROW,
    SETTINGS_LANG_SET,
    START,
)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with get_session_factory()() as session:
        await get_or_create_user(session, message.from_user.id, message.from_user.full_name)
    await message.answer(START.format(name=message.from_user.first_name))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP)


@router.message(Command("history"))
async def cmd_history(message: Message) -> None:
    async with get_session_factory()() as session:
        items, total = await user_history(session, message.from_user.id)
    if not items:
        await message.answer(HISTORY_EMPTY)
        return
    lines = [HISTORY_ROW.format(icon="🎬" if i.media_type == "video" else "🎵", title=html.escape(i.title or i.url)) for i in items]
    await message.answer(HISTORY_HEAD.format(total=total) + "\n".join(lines))


@router.message(Command("favorites"))
async def cmd_favorites(message: Message) -> None:
    async with get_session_factory()() as session:
        favs = await user_favorites(session, message.from_user.id)
    if not favs:
        await message.answer(FAVORITES_EMPTY)
        return
    kb = InlineKeyboardBuilder()
    lines = [FAVORITES_HEAD.format(total=len(favs))]
    for fav in favs:
        lines.append(f"🎵 {html.escape((fav.artist + ' — ' if fav.artist else '') + fav.title)}")
        kb.row(InlineKeyboardButton(text=f"❌ {fav.title[:32]}", callback_data=f"fr:{fav.url[:192]}"))
    await message.answer("\n".join(lines), reply_markup=kb.as_markup())


@router.callback_query(F.data.regexp(r"^fr:(.+)$"))
async def cb_remove_favorite(cb: CallbackQuery) -> None:
    url = cb.data.split(":", 1)[1]
    async with get_session_factory()() as session:
        await remove_favorite(session, cb.from_user.id, url)
        favs = await user_favorites(session, cb.from_user.id)
    await cb.answer("Удалено из избранного")
    if not favs:
        await cb.message.edit_text(FAVORITES_EMPTY)
        return
    kb = InlineKeyboardBuilder()
    lines = [FAVORITES_HEAD.format(total=len(favs))]
    for fav in favs:
        lines.append(f"🎵 {html.escape((fav.artist + ' — ' if fav.artist else '') + fav.title)}")
        kb.row(InlineKeyboardButton(text=f"❌ {fav.title[:32]}", callback_data=f"fr:{fav.url[:192]}"))
    await cb.message.edit_text("\n".join(lines), reply_markup=kb.as_markup())


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
           InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"))
    await message.answer("⚙️ <b>Настройки</b>\nВыберите язык интерфейса:", reply_markup=kb.as_markup())


@router.callback_query(F.data.regexp(r"^lang:(ru|en)$"))
async def cb_set_language(cb: CallbackQuery) -> None:
    lang = cb.data.split(":")[1]
    async with get_session_factory()() as session:
        await get_or_create_user(session, cb.from_user.id, cb.from_user.full_name, language=lang)
    await cb.answer()
    await cb.message.edit_text(SETTINGS_LANG_SET[lang])
