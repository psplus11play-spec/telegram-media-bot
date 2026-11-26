"""Foundational tests: queue, progress bar, service imports, config."""

import asyncio

import pytest

from bot.config import get_settings
from bot.services.progress import render_bar
from bot.services.queue import DownloadQueue


def test_render_bar_full_range():
    assert "0.0%" in render_bar(0, "dl")
    assert "50.0%" in render_bar(50, "dl")
    full = render_bar(100, "dl")
    assert "100.0%" in full
    assert "█" * 20 in full


def test_render_bar_clamps():
    assert "█" * 20 in render_bar(150, "dl")
    assert "█" * 0 in render_bar(-5, "dl")


@pytest.mark.asyncio
async def test_queue_runs_under_limits():
    get_settings.cache_clear()
    q = DownloadQueue()
    assert q.busy() == 0
    result = await q.run(42, _value)
    assert result == "ok"
    assert q.busy() == 0


@pytest.mark.asyncio
async def test_queue_busy_counted():
    get_settings.cache_clear()
    q = DownloadQueue()
    task = asyncio.create_task(q.run(1, _hold))
    await asyncio.sleep(0.01)
    assert q.busy() == 1
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)
    assert q.busy() == 0


@pytest.mark.asyncio
async def test_queue_notify_called_when_full():
    get_settings.cache_clear()
    q = DownloadQueue()
    notes = []
    first = [
        asyncio.create_task(q.run(1, _hold)) for _ in range(get_settings().download_max_concurrent_downloads)
    ]
    await asyncio.sleep(0.01)
    second = asyncio.create_task(q.run(2, _value, notify=notes.append))
    await asyncio.sleep(0.05)
    assert notes, "notify should be called while waiting for a slot"
    for t in first:
        t.cancel()
    second.cancel()
    await asyncio.gather(*first, second, return_exceptions=True)


@pytest.mark.asyncio
async def test_queue_per_user_serialized():
    get_settings.cache_clear()
    q = DownloadQueue()
    order = []

    async def job(n):
        return await q.run(7, lambda: _track(order, n))

    done = await asyncio.gather(job(1), job(2))
    assert done == ["ok-1", "ok-2"]
    assert order == [1, 2]


def test_settings_defaults():
    s = get_settings()
    assert s.download_max_concurrent_downloads >= 1
    assert s.download_max_concurrent_per_user >= 1
    assert s.download_max_file_size > 0


def test_service_imports():
    import bot.handlers.commands
    import bot.handlers.links
    import bot.handlers.music
    import bot.main
    import bot.providers
    import bot.services.downloader.ytdlp_service
    import bot.services.ffmpeg_tools
    import bot.services.music_service  # noqa: F401


async def _value():
    return "ok"


async def _hold():
    await asyncio.Event().wait()


async def _track(order, n):
    order.append(n)
    return f"ok-{n}"
