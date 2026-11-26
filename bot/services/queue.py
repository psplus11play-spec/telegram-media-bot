"""Per-user download queue with global concurrency limits, task states,
cancellation and retry."""
import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from bot.config import get_settings

_FINISHED_HISTORY = 100


class TaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueSlot:
    position: int = 0
    total: int = 0


@dataclass
class Task:
    id: str
    user_id: int
    state: TaskState = TaskState.PENDING
    position: int = 0
    total: int = 0
    label: str = ""
    error: str = ""
    asyncio_task: asyncio.Task | None = field(default=None, repr=False, compare=False)


class DownloadQueue:
    """Bounds concurrent downloads globally and per user, tracks task state,
    supports cancellation of waiting/running tasks and retry of failed ones."""

    def __init__(self) -> None:
        self._sem: asyncio.Semaphore | None = None
        self._user_sems: dict[int, asyncio.Semaphore] = {}
        self._tasks: dict[str, Task] = {}

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

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def user_tasks(self, user_id: int) -> list[Task]:
        self._prune()
        return [t for t in self._tasks.values() if t.user_id == user_id]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task. Returns True if cancelled now."""
        task = self._tasks.get(task_id)
        if task is None or task.state in (TaskState.COMPLETED, TaskState.CANCELLED):
            return False
        task.state = TaskState.CANCELLED
        if task.asyncio_task is not None and not task.asyncio_task.done():
            task.asyncio_task.cancel()
        return True

    def retry_task(self, task_id: str) -> Task | None:
        """Mark a failed or cancelled task as pending again.

        The caller must reschedule the work with run_resumed().
        """
        task = self._tasks.get(task_id)
        if task is None or task.state not in (TaskState.FAILED, TaskState.CANCELLED):
            return None
        task.state = TaskState.PENDING
        task.error = ""
        return task

    def _prune(self) -> None:
        finished = [t for t in self._tasks.values() if t.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)]
        excess = len(finished) - _FINISHED_HISTORY
        for task in finished[:max(excess, 0)]:
            self._tasks.pop(task.id, None)

    async def run(self, user_id: int, coro_factory: Callable[[], object], notify=None, label: str = ""):
        """Run coro_factory() under queue limits; notify(text) on waits.

        coro_factory is called only once it is this job's turn, so the
        download starts when a slot frees up. The task's final state is
        recorded: completed, failed (with error) or cancelled.
        """
        task = Task(id=uuid.uuid4().hex[:12], user_id=user_id, label=label)
        self._tasks[task.id] = task
        task.asyncio_task = asyncio.current_task()

        sem = self._get_sem()
        usem = self._user_sem(user_id)
        waiting = not (sem._value > 0 and usem._value > 0)
        if waiting and notify:
            await notify("⏳ Все слоты заняты — вы в очереди, скоро начнём")
        try:
            async with sem, usem:
                task.state = TaskState.RUNNING
                result = await coro_factory()
        except asyncio.CancelledError:
            task.state = TaskState.CANCELLED
            raise
        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            raise
        finally:
            self._prune()
        task.state = TaskState.COMPLETED
        return result


queue = DownloadQueue()
