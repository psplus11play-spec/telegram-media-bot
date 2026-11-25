#!/usr/bin/env python3
"""
Run bot script with proper environment setup.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.main import main

if __name__ == "__main__":
    main()