# VidTune Telegram bot — single-stage image.
# ffmpeg is a runtime dependency (media tools + yt-dlp postprocessing).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DOWNLOAD_TEMP_DIR=/app/data/temp

# ffmpeg for media tools and yt-dlp; ca-certificates for HTTPS
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY bot/ ./bot/
COPY scripts/ ./scripts/

RUN pip install --no-cache-dir .

# Non-root: the bot only needs its data dir
RUN useradd -m botuser \
    && mkdir -p /app/data/temp \
    && chown -R botuser:botuser /app/data
USER botuser

VOLUME ["/app/data"]
EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=10s --start-period=15s \
    CMD python -c "import pathlib, time; p = pathlib.Path('/app/data/temp'); assert p.exists()" || exit 1

CMD ["python", "-m", "bot.main"]
