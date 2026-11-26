# Repository Audit — VidTune (telegram-media-bot)

Date: 2026-11-26 · Stage 1 · Audited live source, git history and runtime behaviour.
Bot: @VidTuner_bot (aiogram 3, SQLite via SQLAlchemy 2.0 async, yt-dlp, FFmpeg).

## Scope inspected

- `bot/` — main, config, messages, handlers (commands, links), keyboards, database (models, session), services (queue, progress, ffmpeg_tools, downloader/ytdlp_service)
- `scripts/` — run_bot.py, init_db.py
- `pyproject.toml`, `.env.example`, `.gitignore`, README.md, git history (commits `0d0c669`, `5e00257` and earlier)

## Findings

Severity: CRITICAL / HIGH / MEDIUM / LOW.

| # | Severity | Finding | Files | Status |
|---|----------|---------|-------|--------|
| 1 | CRITICAL | Playlist links crash the handler: `links.py` accessed `info.entries`, which does not exist on `MediaInfo` (fields are `title, duration, platform, is_playlist, entries_count`) → `AttributeError` on every playlist link. | `bot/handlers/links.py` | FIXED — uses `info.entries_count` |
| 2 | CRITICAL | yt-dlp progress hook raised `RuntimeError: There is no current event loop in thread 'Thread-N'`: the hook was constructed inside `asyncio.to_thread` worker and called `asyncio.get_event_loop()`. Confirmed by reproducing the worker-thread failure. | `bot/services/downloader/ytdlp_service.py` | FIXED — hook built on the event-loop thread via `get_running_loop()` |
| 3 | CRITICAL | YouTube cookies (`data/cookies.txt`) were committed to the public repository — session credentials leaked. | git index | FIXED — `git rm --cached`, ignored in `.gitignore`. Session cookies must still be treated as compromised; re-export after rotating the YouTube session. |
| 4 | HIGH | `scripts/init_db.py` imported `bot.database` (empty `__init__.py`) and `bot.logging` (module does not exist) → both admin scripts were broken. | `scripts/init_db.py` | REWRITTEN — imports `bot.database.session.init_db`, runs `asyncio.run` |
| 5 | HIGH | `scripts/run_bot.py` imported and called `main()` (an async function) without `asyncio.run` → coroutine never awaited, bot did not start. | `scripts/run_bot.py` | FIXED |
| 6 | HIGH | HTML injection into bot messages: global `ParseMode.HTML` is set in `bot/main.py`, but yt-dlp video titles (untrusted input) were interpolated into `CHOOSE_QUALITY` / `PLAYLIST_LIST` unescaped — malformed titles break messages, crafted ones allow markup injection. | `bot/handlers/links.py` | FIXED — `html.escape` on titles |
| 7 | HIGH | Invalid `pyproject.toml`: `[tool.ruff]`-style flat keys (`ignore = [...]`, `per-file-ignores = {…}`, `format.*`) appeared at top level after `[tool.pytest.ini_options]`, making the file invalid TOML — `pytest` could not even parse it (exit 2 on collection). `ruff` still worked because `ruff.toml` shadows it. | `pyproject.toml` | FIXED — moved under `[tool.ruff.lint.per-file-ignores]` / `[tool.ruff.format]` |
| 8 | MEDIUM | `DownloadQueue.busy()` returned the number of FREE slots (`Semaphore._value`), inverted semantics — any consumer showing "active downloads" would display the wrong count. | `bot/services/queue.py` | FIXED — returns occupied slots |
| 9 | MEDIUM | Error messages interpolate raw exception text into HTML messages without escaping (`DOWNLOAD_ERROR.format(error=e)`), so provider error text with `<`/`&` breaks rendering. | `bot/handlers/links.py` | OPEN — recommended: escape in the message templates or at call site |
| 10 | MEDIUM | No automated tests existed (`tests/` absent). | — | FIXED — `tests/test_foundational.py` (8 tests) |
| 11 | MEDIUM | `bot/database/__init__.py` is empty while scripts expected it to re-export `initialize_database` / `close_database` — either populate it or keep imports on `bot.database.session` (done in scripts). | `bot/database/__init__.py` | OPEN — low priority |
| 12 | LOW | Russian user-facing strings and error text inside service code (`RuntimeError("плейлист изменился…")`) — fine for now, blocks i18n later (Stage 7). | services | OPEN — noted for locales stage |
| 13 | LOW | `.env` present in working tree (ignored, not committed) — correct after fix #3; keep monitoring. | — | OK |

## Architecture notes (current state)

- Single-process polling bot; SQLite at `data/bot.db`; per-user + global download queue (`DownloadQueue.run`) with waiting notification.
- Download path: link → `ytdlp_service.fetch_info_async` → quality keyboard → `download_async` in `asyncio.to_thread` with thread-safe progress hook → FSInputFile upload; temp files under `data/temp`, cleaned after send.
- YouTube access currently requires cookies (`data/cookies.txt`) + EJS challenge solver; SABR experiment limits available formats.

## Security review (Stage 1 scope)

- Cookies leak fixed (see #3). No other secrets tracked in git.
- Filenames from yt-dlp are used for temp files but Telegram sends by path only; directory traversal risk is limited to the configured temp dir — recommend explicit sanitisation in Stage 2.
- No command injection: ffmpeg is invoked via `create_subprocess_exec` argument lists, no `shell=True`.
- Missing (planned): URL/SSRF validation layer, rate limiting per user, callback authorization checks — scheduled for Stages 2 and 15.

## Recommended next steps (Stage 2)

1. Persistent Telegram `file_id` cache keyed by (platform, media id, quality, format).
2. Task states + cancellation and retry in the queue (PENDING→…→COMPLETED/FAILED/CANCELLED).
3. URL validation and per-user rate limiting middleware.
4. Escape all provider-supplied strings in every message template.
