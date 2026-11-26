#!/usr/bin/env python3
"""Create all database tables."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.database.session import init_db


def main() -> None:
    asyncio.run(init_db())
    print("Database initialized.")


if __name__ == "__main__":
    main()
