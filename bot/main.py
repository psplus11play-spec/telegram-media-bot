"""Application entry point."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import get_settings
from bot.database.session import init_db
from bot.handlers import commands, links, music
from bot.middlewares.throttling import ThrottlingMiddleware


async def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    await init_db()

    bot = Bot(get_settings().bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    links.router.message.middleware(ThrottlingMiddleware())
    dp.include_routers(commands.router, music.router, links.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
