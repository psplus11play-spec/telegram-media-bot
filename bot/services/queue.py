"""Per-user download queue with global concurrency limits."""
import asyncio
from dataclasses import dataclass

from bot.config import get_settings


@dataclass
class QueueSlot:
    position: int = 0
    total: int = 0


class DownloadQueue:
    """Bounds concurrent downloads globally and per user, reports waiting position."""

    def __init__(self) -> None:
        self._sem: asyncio.Semaphore | None = None
        self._user_sems: dict[int, asyncio.Semaphore] = {}

    def _get_sem(self) -> asyncio.Semaphore:
        if self._sem is None:
            self._sem = asyncio.Semaphore(get_settings().download_max_concurrent_downloads)
        return self._sem

    def _user_sem(self, user_id: int) -> asyncio.Semaphore:
        sem = self._user_sems.get(user_id)
        if sem is None:
            sem = asyncio.Semaphore(get_settings().download_max_concurrent_per_user)
            self._user_sems[user_id] = sem
        return sem

    def busy(self) -> int:
        """Number of currently occupied global slots."""
        if self._sem is None:
            return 0
        return get_settings().download_max_concurrent_downloads - self._sem._value

    async def run(self, user_id: int, coro_factory, notify=None):
        """Run coro_factory() under queue limits; notify(text) on waits.

        coro_factory is called only once it is this job's turn, so the
        download starts when a slot frees up.
        """
        sem = self._get_sem()
        usem = self._user_sem(user_id)
        waiting = not (sem._value > 0 and usem._value > 0)
        if waiting and notify:
            await notify("⏳ Все слоты заняты — вы в очереди, скоро начнём")
        async with sem, usem:
            return await coro_factory()


queue = DownloadQueue()
