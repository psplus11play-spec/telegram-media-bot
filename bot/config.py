"""Configuration loaded from .env via pydantic-settings."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: str
    bot_admin_ids: str = ""

    db_url: str = f"sqlite+aiosqlite:///{ROOT / 'data' / 'bot.db'}"
    db_echo: bool = False

    download_temp_dir: Path = ROOT / "data" / "temp"
    download_downloads_dir: Path = ROOT / "data" / "downloads"
    download_max_file_size: int = 2_000_000_000
    download_max_concurrent_downloads: int = 3
    download_max_concurrent_per_user: int = 2
    download_default_video_quality: str = "720p"
    download_default_audio_format: str = "mp3"
    download_default_audio_bitrate: str = "320"

    log_level: str = "INFO"

    @property
    def admin_ids(self) -> set[int]:
        raw = self.bot_admin_ids.strip().strip("[]")
        return {int(x) for x in raw.replace(" ", "").split(",") if x}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]
    settings.download_temp_dir.mkdir(parents=True, exist_ok=True)
    settings.download_downloads_dir.mkdir(parents=True, exist_ok=True)
    return settings
