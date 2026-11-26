"""Stage 2 tests: URL validation, queue task states, file_id cache, throttling."""
import asyncio

import pytest

from bot.config import get_settings
from bot.middlewares.throttling import hits_in_window, is_limited
from bot.services.queue import DownloadQueue, TaskState
from bot.utils.urlcheck import URLValidationError, validate_url

# --- URL validation -------------------------------------------------------

def test_validate_url_accepts_public_https():
    assert validate_url("https://www.youtube.com/watch?v=abc") == "https://www.youtube.com/watch?v=abc"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/video",
        "not a url",
        "https://",
        "http://localhost/video",
        "http://127.0.0.1/x",
        "http://192.168.1.5/x",
        "http://10.0.0.1/x",
        "http://[::1]/x",
        "https://host.internal/x",
        "",
    ],
)
def test_validate_url_rejects(url):
    with pytest.raises(URLValidationError):
        validate_url(url)


def test_validate_url_rejects_header_injection():
    with pytest.raises(URLValidationError):
        validate_url("https://example.com/a\r\nX-Injected: 1")


# --- queue task states ----------------------------------------------------

async def _value():
    return "ok"


async def _fail():
    raise RuntimeError("boom")


async def _hold(ev: asyncio.Event):
    await ev.wait()


@pytest.mark.asyncio
async def test_queue_states_completed_and_failed():
    get_settings.cache_clear()
    q = DownloadQueue()
    assert await q.run(1, _value) == "ok"
    with pytest.raises(RuntimeError):
        await q.run(1, _fail)
    states = [t.state for t in q.user_tasks(1)]
    assert TaskState.COMPLETED in states and TaskState.FAILED in states
    failed = next(t for t in q.user_tasks(1) if t.state is TaskState.FAILED)
    assert failed.error == "boom"


@pytest.mark.asyncio
async def test_queue_cancel_task():
    get_settings.cache_clear()
    q = DownloadQueue()
    ev = asyncio.Event()
    job = asyncio.create_task(q.run(1, lambda: _hold(ev)))
    await asyncio.sleep(0.01)
    task = q.user_tasks(1)[0]
    assert task.state is TaskState.RUNNING
    assert q.cancel_task(task.id) is True
    with pytest.raises(asyncio.CancelledError):
        await job
    assert q.get_task(task.id).state is TaskState.CANCELLED
    assert q.cancel_task(task.id) is False  # already cancelled


@pytest.mark.asyncio
async def test_queue_retry_task():
    get_settings.cache_clear()
    q = DownloadQueue()
    with pytest.raises(RuntimeError):
        await q.run(1, _fail)
    task = q.user_tasks(1)[0]
    assert q.retry_task(task.id) is not None
    assert task.state is TaskState.PENDING
    assert task.error == ""
    assert await q.run(1, _value) == "ok"
    assert q.retry_task("nope") is None


# --- throttling -----------------------------------------------------------

def test_throttling_counts_hits():
    get_settings.cache_clear()
    user = 9_001
    limit = get_settings().ratelimit_links_per_minute
    for _ in range(limit):
        assert is_limited(user) is False
    assert is_limited(user) is True
    assert hits_in_window(user) == limit
