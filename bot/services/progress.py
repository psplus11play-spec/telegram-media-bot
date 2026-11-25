"""Telegram progress bar fed by a yt-dlp progress hook."""
import asyncio
import time

from aiogram.exceptions import TelegramRetryAfter

BAR_LEN = 20


def render_bar(percent: float, label: str, speed: str = "", eta: str = "") -> str:
    filled = int(BAR_LEN * percent / 100)
    bar = "█" * filled + "░" * (BAR_LEN - filled)
    line = f"{label}\n{bar} {percent:5.1f}%"
    extras = " ".join(x for x in (speed, eta) if x)
    if extras:
        line += f"\n{extras}"
    return f"<pre>{line}</pre>"


class ProgressReporter:
    """Throttled message editor safe for Telegram rate limits."""

    def __init__(self, message, label: str = "⬇️ Скачиваю"):
        self._message = message
        self._label = label
        self._last_text = ""
        self._last_edit = 0.0
        self._min_interval = 3.0

    async def hook(self, data: dict) -> None:
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            done = data.get("downloaded_bytes") or 0
            percent = done / total * 100 if total else 0
            speed = data.get("speed")
            eta = data.get("eta")
            extras = []
            if speed:
                extras.append(f"🚀 {_fmt_size(speed)}/с")
            if eta:
                extras.append(f"⏳ {eta // 60}:{eta % 60:02d}")
            await self.update(percent, " ".join(extras))
        elif status == "finished":
            await self.update(100.0, "🔧 Обрабатываю…")

    async def update(self, percent: float, extras: str = "") -> None:
        now = time.monotonic()
        if now - self._last_edit < self._min_interval:
            return
        text = render_bar(percent, self._label, extras)
        if text == self._last_text:
            return
        try:
            await self._message.edit_text(text)
            self._last_text = text
            self._last_edit = now
        except TelegramRetryAfter as e:
            self._last_edit = now + e.retry_after - self._min_interval
        except Exception:  # noqa: BLE001 - старое сообщение могло быть удалено
            pass


def _fmt_size(num: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} ТБ"
