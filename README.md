# VidTune (telegram-media-bot)

Телеграм-бот @VidTuner_bot: видео и музыка по ссылке, поиск музыки, распознавание песен, медиа-инструменты.

## Возможности

- **Видео** — ссылка на YouTube/TikTok/VK и др.: выбор качества (360p–max), плейлисты (первые 10 / лучшее качество / MP3), прогресс-бар со скоростью и ETA, очередь, кэш file_id (повторная ссылка отправляется мгновенно).
- **Музыка** — текстовый запрос → 8 результатов на страницу (◀️/▶️), форматы **MP3 128/192/320, M4A, Opus**, теги ID3/M4A + обложка; Spotify-ссылки → метаданные + аудио через совпадение в YT Music.
- **Распознавание** — голосовое/видеозаметка/короткое аудио → Shazam: карточка трека + кнопка «Скачать».
- **Инструменты** (`/tools`) — видео→MP3, видеозаметка (≤60 c), GIF (≤15 c), обрезка («с 0:30 до 1:15»), сжатие до целевого размера, рингтон .m4r (≤30 c), голосовое⇄MP3, обложка.
- **Инлайн-режим** — `@VidTuner_bot <название>` в любом чате; файл приходит в личку бота.
- **Прочее** — история `/history`, избранное `/favorites`, язык `/settings` (ru/en), лимит ссылок (10/мин), отмена/повтор задач в очереди.

## Команды

`/start` `/help` `/history` `/favorites` `/recent` `/settings` `/tools`

## Запуск без Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env        # вписать BOT_TOKEN
python scripts/init_db.py
python -m bot.main
```

Нужен ffmpeg в системе (`apt install ffmpeg`).

## Запуск в Docker

```bash
cp .env.example .env        # вписать BOT_TOKEN
docker compose up -d --build
docker compose logs -f
```

База данных, временные файлы и опциональный `cookies.txt` живут в `./data` (volume). Cookies: смонтированы автоматически, включаются переменной `DOWNLOAD_YTDLP_COOKIES_FILE=/app/data/cookies.txt`.

## Структура

```
bot/
  main.py                  # входная точка, регистрация роутеров
  config.py                # настройки из .env (pydantic-settings)
  handlers/                # commands, links (видео), music, shazam, tools, inline
  providers/               # адаптеры провайдеров музыки (base/search/spotify)
  services/                # очередь, прогресс, ffmpeg_tools, music_service, recognition, downloader/
  database/                # SQLAlchemy 2.0 async модели и сессия (SQLite)
  utils/                   # urlcheck (SSRF-защита)
scripts/                   # init_db.py, run_bot.py
tests/                     # pytest (47 тестов)
```

## Безопасность

- URL-валидация с блокировкой приватных адресов (SSRF), CRLF-защита.
- HTML-экранирование всех пользовательских данных в сообщениях.
- Секреты (.env, cookies) не попадают в git — см. `.gitignore`.
- Контейнер работает от непривилегированного пользователя.
