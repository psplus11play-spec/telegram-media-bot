# Complete Project Directory Structure

```
telegram-media-bot/
├── .github/
│   └── workflows/
│       └── ci.yml
├── bot/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config.py               # Pydantic Settings configuration
│   ├── logging.py              # Structured logging setup
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py          # Async session management
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # Base model with common fields
│   │   │   ├── user.py         # User model
│   │   │   ├── settings.py     # User settings model
│   │   │   ├── history.py      # Download history model
│   │   │   └── queue.py        # Download queue/task model
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py         # Base repository
│   │       ├── user_repo.py
│   │       ├── settings_repo.py
│   │       ├── history_repo.py
│   │       └── queue_repo.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── router.py           # Main router registration
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── start.py        # /start, /help
│   │   │   ├── settings.py     # /settings
│   │   │   ├── history.py      # /history
│   │   │   ├── queue.py        # /queue, /cancel
│   │   │   ├── language.py     # /language
│   │   │   ├── stats.py        # /stats
│   │   │   ├── about.py        # /about
│   │   │   └── admin.py        # Admin commands
│   │   ├── callbacks/
│   │   │   ├── __init__.py
│   │   │   ├── settings_cb.py
│   │   │   ├── history_cb.py
│   │   │   ├── queue_cb.py
│   │   │   └── navigation_cb.py
│   │   ├── inline/
│   │   │   ├── __init__.py
│   │   │   └── search.py
│   │   └── messages/
│   │       ├── __init__.py
│   │       ├── text.py
│   │       ├── url.py
│   │       └── media.py
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── throttling.py
│   │   ├── i18n.py
│   │   ├── maintenance.py
│   │   └── db_session.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── downloader/
│   │   │   ├── __init__.py
│   │   │   ├── ytdlp.py
│   │   │   ├── spotdl.py
│   │   │   └── yandex.py
│   │   ├── music/
│   │   │   ├── __init__.py
│   │   │   ├── spotify.py
│   │   │   ├── yandex.py
│   │   │   ├── soundcloud.py
│   │   │   └── youtube.py
│   │   ├── shazam/
│   │   │   ├── __init__.py
│   │   │   └── recognition.py
│   │   ├── lyrics/
│   │   │   ├── __init__.py
│   │   │   └── genius.py
│   │   ├── ffmpeg/
│   │   │   ├── __init__.py
│   │   │   ├── converter.py
│   │   │   ├── trimmer.py
│   │   │   └── extractor.py
│   │   ├── queue/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py
│   │   │   └── task.py
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py
│   │   │   └── backends.py
│   │   ├── history/
│   │   │   ├── __init__.py
│   │   │   └── manager.py
│   │   └── settings/
│   │       ├── __init__.py
│   │       └── manager.py
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── builder.py
│   │   ├── main_menu.py
│   │   ├── settings_kb.py
│   │   ├── history_kb.py
│   │   ├── queue_kb.py
│   │   ├── pagination.py
│   │   └── inline_kb.py
│   ├── i18n/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   └── locales/
│   │       ├── ru.json
│   │       └── en.json
│   └── utils/
│       ├── __init__.py
│       ├── validators.py
│       ├── formatters.py
│       ├── helpers.py
│       └── constants.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_validators.py
│   │   ├── test_formatters.py
│   │   ├── test_i18n.py
│   │   └── test_repositories.py
│   └── integration/
│       ├── test_database.py
│       └── test_handlers.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.local.yml
│   └── telegram-bot-api/
│       └── Dockerfile
├── scripts/
│   ├── init_db.py
│   ├── run_bot.py
│   └── run_tests.py
├── data/
│   ├── temp/                   # Temporary media files (gitignored)
│   ├── cache/                  # Cache storage (gitignored)
│   └── downloads/              # Downloaded media (gitignored)
├── logs/                       # Log files (gitignored)
├── .env.example
├── .env                        # Not committed
├── .gitignore
├── pyproject.toml
├── ruff.toml
├── README.md
├── ARCHITECTURE.md
└── PROJECT_STRUCTURE.md
```