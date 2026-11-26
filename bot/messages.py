"""Messages shown to the user (single place to tweak wording)."""

START = (
    "👋 <b>Привет, {name}!</b>\n\n"
    "Я — <b>Media Bot</b>, умею:\n"
    "🎬 скачивать видео с YouTube, TikTok, VK и других сайтов\n"
    "🎵 вытаскивать аудио в MP3\n"
    "🗂 помнить твои загрузки\n\n"
    "Просто пришли <b>ссылку</b> — и выбери качество.\n"
    "<i>/help — что я ещё умею</i>"
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
STALE = "⌛ Ссылка устарела — отправь её заново"
HISTORY_EMPTY = "📭 Ты ещё ничего не скачивал(а)."
HISTORY_HEAD = "🗂 <b>Твои загрузки</b> (всего {total}):\n"
HISTORY_ROW = "  {icon} {title}"
