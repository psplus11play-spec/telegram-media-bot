#!/usr/bin/env python3
"""Run the bot with the project root on sys.path."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.main import main

if __name__ == "__main__":
    asyncio.run(main())
