# Telegram Media Bot

A powerful Telegram bot for downloading videos, music, recognizing songs, and processing media files.

## Features

### 🎬 Video Downloads
- YouTube, TikTok, Instagram, Twitter/X, Vimeo, Facebook, Twitch, and 50+ sites
- Playlist and channel support
- Quality selection (144p to 1080p+)
- Progress tracking and cancellation

### 🎵 Music Downloads
- Spotify (tracks, albums, playlists via spotdl)
- Yandex Music
- SoundCloud
- YouTube Music
- ID3 metadata with embedded cover art
- Multiple formats (MP3, M4A, FLAC, OGG, OPUS, WAV)
- Configurable bitrates (64k to 512k)

### 🔍 Song Recognition (Shazam)
- Recognize songs from audio, voice messages, video files
- Display title, artist, album, release date, cover art
- Links to streaming platforms
- Search/download recognized songs

### 🎤 Lyrics
- Synchronized and plain lyrics via Genius API
- Search by track title/artist

### ⚙️ Media Tools (FFmpeg)
- Format conversion (video↔video, audio↔audio, video→audio)
- Video trimming with timestamps
- Video/audio compression
- Video notes (circles) for Telegram
- GIF creation from video
- Frame extraction
- Audio/video merging

### 🤖 Bot Features
- **Inline mode** - search and send music directly in chats
- **Group support** - admin permissions, anti-spam, rate limiting
- **Download history** - personal history with search, pagination, re-download
- **Task queue** - concurrent downloads with per-user limits, retry logic
- **Caching** - metadata, artwork, search results, Shazam results
- **User settings** - language, quality, format, source preferences
- **Localization** - Russian and English
- **Admin panel** - global stats, broadcast, maintenance mode

## Architecture

```
bot/
├── config.py              # Pydantic Settings configuration
├── logging.py             # Structured logging (structlog)
├── database/              # SQLAlchemy 2.0 async
│   ├── models/            # ORM models
│   ├── repositories/      # Data access layer
│   └── session.py         # Session management
├── handlers/              # Telegram handlers
│   ├── commands/          # /start, /help, /settings, etc.
│   ├── callbacks/         # Inline button handlers
│   ├── inline/            # InlineQueryHandler
│   └── messages/          # Text, URL, media handlers
├── middlewares/           # Auth, throttling, i18n, maintenance
├── services/              # Business logic (future stages)
├── keyboards/             # Reusable inline keyboards
├── i18n/                  # Localization system
└── utils/                 # Validators, formatters, helpers
```

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (recommended)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- (Optional) Telegram API ID/Hash for local Bot API server
- (Optional) Spotify API credentials for music downloads
- (Optional) Genius API token for lyrics

### Option 1: Docker (Recommended)

1. **Clone and configure:**
```bash
git clone <repository>
cd telegram-media-bot
cp .env.example .env
# Edit .env with your tokens
```

2. **Start with Docker Compose:**
```bash
# Production
docker-compose -f docker/docker-compose.yml up -d

# Development
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.local.yml up -d
```

3. **View logs:**
```bash
docker-compose -f docker/docker-compose.yml logs -f bot
```

### Option 2: Local Development

1. **Install dependencies:**
```bash
# Using pip
pip install -e ".[dev]"

# Or using Poetry
poetry install --with dev
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your tokens
```

3. **Run the bot:**
```bash
python -m bot.main
```

### Option 3: Local Bot API Server (for >50MB files)

The docker-compose includes a local Telegram Bot API server that supports 2GB uploads:

```bash
# Get API credentials from https://my.telegram.org/apps
# Add to .env:
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# Start with local API server
docker-compose -f docker/docker-compose.yml up -d
```

The bot will automatically use the local API server at `http://telegram-bot-api:8081`.

## Configuration

All configuration is done via environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram Bot Token | **Required** |
| `BOT_ADMIN_IDS` | Comma-separated admin user IDs | - |
| `BOT_LOCAL_API_URL` | Local Bot API server URL | - |
| `DB_URL` | Database connection string | `sqlite+aiosqlite:///data/bot.db` |
| `DOWNLOAD_MAX_FILE_SIZE` | Max download size (bytes) | `2000000000` (2GB) |
| `DOWNLOAD_MAX_CONCURRENT_DOWNLOADS` | Global concurrent downloads | `3` |
| `DOWNLOAD_MAX_CONCURRENT_PER_USER` | Per-user concurrent downloads | `2` |
| `DOWNLOAD_DEFAULT_VIDEO_QUALITY` | Default video quality | `720p` |
| `DOWNLOAD_DEFAULT_AUDIO_FORMAT` | Default audio format | `mp3` |
| `DOWNLOAD_DEFAULT_AUDIO_BITRATE` | Default audio bitrate | `320k` |
| `CACHE_ENABLED` | Enable caching | `true` |
| `RATELIMIT_ENABLED` | Enable rate limiting | `true` |
| `I18N_DEFAULT_LANGUAGE` | Default language | `ru` |
| `LOG_LEVEL` | Log level | `INFO` |
| `ENVIRONMENT` | Environment | `production` |

## Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome message and main menu |
| `/help` | Full help and supported sites |
| `/settings` | Personal settings menu |
| `/history` | Download history |
| `/queue` | Current download queue |
| `/cancel` | Cancel active task |
| `/language` | Change interface language |
| `/stats` | Personal statistics |
| `/about` | Bot information |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/admin` | Administration panel |
| `/stats_all` | Global statistics |
| `/queue_all` | Global queue overview |
| `/broadcast` | Send announcement to all users |
| `/maintenance` | Toggle maintenance mode |

## Development

### Code Quality
```bash
# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy bot/

# Run tests
pytest

# Run tests with coverage
pytest --cov=bot --cov-report=html
```

### Project Structure
- **Stage 1** (Current): Foundation - config, database, logging, i18n, basic commands
- **Stage 2**: Video downloads (yt-dlp integration)
- **Stage 3**: Music search/downloads (Spotify, Yandex, SoundCloud)
- **Stage 4**: Shazam recognition & lyrics
- **Stage 5**: FFmpeg media toolkit
- **Stage 6**: Queue, cache, history
- **Stage 7**: Inline mode & groups
- **Stage 8**: AI features & optimization

### Adding Dependencies
```bash
# Add runtime dependency
poetry add package_name

# Add dev dependency
poetry add --group dev package_name
```

## Security

- Environment-based secrets (never hardcoded)
- Input validation & URL sanitization
- SSRF protection (blocks private IPs)
- Safe subprocess execution (no shell interpolation)
- Rate limiting & anti-spam
- Admin access control
- Path traversal protection
- File type & size verification

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Support

- Issues: GitHub Issues
- Telegram: @your_support_channel