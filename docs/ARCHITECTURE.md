# Telegram Media Bot - Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Telegram Bot (aiogram 3.x)               │
├─────────────────────────────────────────────────────────────────┤
│  Handlers (Telegram interactions only)                          │
│  ├── commands/          # /start, /help, /settings, /history... │
│  ├── callbacks/         # Inline button handlers                │
│  ├── inline/            # InlineQueryHandler                    │
│  └── messages/          # Text, URL, media handlers             │
├─────────────────────────────────────────────────────────────────┤
│  Middlewares                                                    │
│  ├── auth.py            # User authentication & context         │
│  ├── throttling.py      # Rate limiting & anti-spam             │
│  ├── i18n.py            # Localization context                  │
│  └── maintenance.py     # Maintenance mode check                │
├─────────────────────────────────────────────────────────────────┤
│  Services (Business logic & external integrations)              │
│  ├── downloader/        # yt-dlp, spotdl, yandex-music          │
│  ├── music/             # Spotify, Yandex, SoundCloud, YT Music │
│  ├── shazam/            # ShazamIO recognition                  │
│  ├── lyrics/            # Genius API                            │
│  ├── ffmpeg/            # Media conversion & editing            │
│  ├── queue/             # Async task queue with concurrency     │
│  ├── cache/             # Multi-layer caching                   │
│  ├── history/           # Download history management           │
│  └── settings/          # User settings management              │
├─────────────────────────────────────────────────────────────────┤
│  Database (SQLAlchemy 2.0 async)                                │
│  ├── models/            # ORM models                            │
│  ├── repositories/      # Data access layer                     │
│  └── session.py         # Async session management              │
├─────────────────────────────────────────────────────────────────┤
│  Core Infrastructure                                            │
│  ├── config.py          # Pydantic Settings                     │
│  ├── logging.py         # Structured logging                    │
│  ├── i18n/              # Localization system                   │
│  ├── keyboards/         # Reusable inline keyboards             │
│  └── utils/             # Shared helpers                        │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

1. **Separation of Concerns**: Handlers only handle Telegram interactions; business logic lives in services
2. **Dependency Injection**: Services injected via middleware/context, not global state
3. **Async-First**: All I/O operations are async; sync operations run in thread pools
4. **Type Safety**: Full type hints, Pydantic for validation, SQLAlchemy 2.0 typed queries
5. **Configurability**: All settings via environment variables with Pydantic Settings
6. **Observability**: Structured logging, metrics, health checks
7. **Security**: Input validation, SSRF protection, safe subprocess execution, rate limiting

## Technology Stack

| Layer | Technology |
|-------|------------|
| Bot Framework | aiogram 3.x |
| Database | SQLite + SQLAlchemy 2.0 async |
| Configuration | Pydantic Settings v2 |
| Video/Audio Download | yt-dlp, spotdl |
| Music APIs | spotipy, yandex-music-api, soundcloud-api |
| Song Recognition | ShazamIO |
| Lyrics | Genius API (lyricsgenius) |
| Media Processing | FFmpeg via asyncio subprocess |
| Localization | Custom JSON-based i18n |
| Testing | pytest, pytest-asyncio, pytest-mock |
| Linting/Formatting | Ruff |
| Containerization | Docker, Docker Compose |
| Local Bot API | Telegram Bot API Server (Docker) |

## Data Flow

```
User Message → Middleware Chain → Handler → Service → Repository → Database
                    ↓                    ↓
               Rate Limit           Business Logic
               Auth Check           External APIs
               Locale Set           FFmpeg/Queue
                    ↓                    ↓
              Response ←────────── Result/Formatting
```

## Concurrency Model

- **Download Queue**: Semaphore-based concurrency control (configurable per-user and global)
- **FFmpeg Processing**: Separate semaphore for CPU-intensive operations
- **Database**: Connection pool with async sessions
- **Cache**: Async LRU with TTL, separate namespaces per user

## Security Boundaries

```
┌────────────────────────────────────────┐
│           Trusted Zone                 │
│  ┌─────────┐  ┌─────────┐  ┌────────┐  │
│  │ Config  │  │ Database│  │ Cache  │  │
│  └─────────┘  └─────────┘  └────────┘  │
└────────────────────────────────────────┘
                    │
        Validation & Sanitization
                    ▼
┌────────────────────────────────────────┐
│          Untrusted Zone                │
│  ┌─────────┐  ┌─────────┐  ┌────────┐  │
│  │ Telegram│  │  URLs   │  │ Files  │  │
│  │  Input  │  │  Input  │  │ Upload │  │
│  └─────────┘  └─────────┘  └────────┘  │
└────────────────────────────────────────┘
```