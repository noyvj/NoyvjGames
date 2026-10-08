"""Lighthouse's engine modules are plain Python with no DOM, so the tests import them directly."""

import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))
