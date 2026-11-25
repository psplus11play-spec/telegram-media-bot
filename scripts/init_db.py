#!/usr/bin/env python3
"""
Database initialization script.

Creates all tables and can optionally seed initial data.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.config import get_settings
from bot.database import close_database, initialize_database
from bot.logging import get_logger, setup_logging

logger = get_logger("scripts.init_db")


async def main() -> None:
    """Initialize database."""
    settings = get_settings()

    # Setup logging
    setup_logging()

    logger.info("Initializing database...", url=settings.db_url)

    try:
        await initialize_database()
        logger.info("Database initialized successfully")
    except Exception:
        logger.exception("Failed to initialize database")
        sys.exit(1)
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
