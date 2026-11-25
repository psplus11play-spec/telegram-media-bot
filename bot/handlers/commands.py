"""Command handlers: /start, /help, /history."""
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.database.models import get_or_create_user, user_history
from bot.database.session import get_session_factory
from bot.messages import HELP, HISTORY_EMPTY, HISTORY_HEAD, HISTORY_ROW, START

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
    lines = [HISTORY_ROW.format(icon="🎬" if i.media_type == "video" else "🎵", title=i.title or i.url) for i in items]
    await message.answer(HISTORY_HEAD.format(total=total) + "\n".join(lines))
