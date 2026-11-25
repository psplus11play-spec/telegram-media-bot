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


def playlist_keyboard(token: str, count: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in range(1, min(count, 10) + 1):
        kb.button(text=f"▶️ {i}", callback_data=f"pl:v:{token}:{i}:720p")
    kb.button(text="🎬 Лучшее качество", callback_data=f"pl:v:{token}:1:best")
    kb.button(text="🎵 Аудио MP3 (1-е видео)", callback_data=f"pl:a:{token}:1:best")
    kb.adjust(5, 5, 1, 1)
    return kb.as_markup()

