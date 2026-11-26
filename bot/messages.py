"""Messages shown to the user (single place to tweak wording)."""

START = (
    "👋 <b>Привет, {name}!</b>\n\n"
    "Я — <b>Media Bot</b>, умею:\n"
    "🎬 скачивать видео с YouTube, TikTok, VK и других сайтов\n"
    "🎵 искать и скачивать музыку (MP3/M4A/Opus)\n"
    "🎼 узнавать песни по голосовому сообщению\n"
    "🛠 обрабатывать медиа: GIF, обрезка, сжатие, рингтоны\n"
    "⭐ избранные треки (/favorites) и история (/history)\n"
    "⚙️ язык интерфейса (/settings)\n\n"
    "Просто отправьте ссылку или напишите название трека."
)

HELP = (
    "📖 <b>Что я умею</b>\n\n"
    "🔗 Пришли ссылку на видео — предложу качество: 360p / 720p / 1080p / максимум\n"
    "🎵 Кнопка «Аудио MP3» — вытащит звуковую дорожку в MP3 320 kbps\n"
    "📊 Во время скачивания показываю прогресс-бар\n\n"
    "<b>Команды</b>\n"
    "/start — начать\n"
    "/help — эта справка\n"
    "/history — последние загрузки"
)

CHOOSE_QUALITY = "🧩 <b>{title}</b>{extra}\n\nВыбери, что скачать:"
DURATION = "\n⏱ {m}:{s:02d}"
PLAYLIST_LIST = "🗂 <b>{title}</b>\n\nВ плейлисте {count} видео — выбери, что скачать (первые 10):"

DOWNLOAD_START = "🚀 Поехали!"
DOWNLOAD_ERROR = "😕 Не получилось скачать:\n<code>{error}</code>"
SEND_ERROR = "😕 Файл скачался, но не влез в Telegram:\n<code>{error}</code>"
RATE_LIMITED = "⏳ Слишком много ссылок подряд — подождите минуту."
BAD_URL = "🚫 {reason}"
CACHED = "⚡ Файл уже был в кэше — отправляю мгновенно"
FAVORITES_EMPTY = "⭐ В избранном пока пусто. После скачивания музыки жмите «⭐ В избранное»."
FAVORITES_HEAD = "⭐ <b>Избранное</b> ({total}):\n"
SETTINGS_LANG_SET = {
    "ru": "✅ Язык интерфейса: русский.",
    "en": "✅ Interface language: English.",
}
STALE = "⌛ Ссылка устарела — отправь её заново"
HISTORY_EMPTY = "📭 Ты ещё ничего не скачивал(а)."
HISTORY_HEAD = "🗂 <b>Твои загрузки</b> (всего {total}):\n"
HISTORY_ROW = "  {icon} {title}"
