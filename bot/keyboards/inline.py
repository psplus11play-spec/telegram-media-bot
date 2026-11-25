from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

QUALITIES = ["360p", "720p", "1080p", "best"]


def quality_keyboard(token: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for q in QUALITIES:
        kb.button(text=q, callback_data=f"dl:v:{token}:{q}")
    kb.button(text="🎵 Аудио MP3", callback_data=f"dl:a:{token}")
    kb.adjust(2, 2, 1)
    return kb.as_markup()
