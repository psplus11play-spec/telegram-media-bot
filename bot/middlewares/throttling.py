"""Per-user rate limiting for link submissions."""
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import Message

from bot.config import get_settings
from bot.messages import RATE_LIMITED

_window: dict[int, deque[float]] = defaultdict(deque)


def hits_in_window(user_id: int, window: float = 60.0) -> int:
    now = time.monotonic()
    hits = _window[user_id]
    while hits and now - hits[0] > window:
        hits.popleft()
    return len(hits)


def _register_hit(user_id: int) -> None:
    hits = _window[user_id]
    hits.append(time.monotonic())
    if len(_window) > 10_000:  # hard bound on tracked users
        _window.clear()


def is_limited(user_id: int) -> bool:
    limit = get_settings().ratelimit_links_per_minute
    if hits_in_window(user_id) >= limit:
        return True
    _register_hit(user_id)
    return False


class ThrottlingMiddleware:
    """Drop link messages that exceed the per-user per-minute limit."""

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user is not None and is_limited(event.from_user.id):
            await event.answer(RATE_LIMITED)
            return None
        return await handler(event, data)
