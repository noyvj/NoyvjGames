"""Teach the Machine's engine modules are plain Python with no DOM, so the tests import them directly."""

import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
for path in (GAME_DIR, GAME_DIR / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# tests/browser_helpers.py (the shared browser-test set-up) is imported by plain name: `from browser_helpers import base, open_game`.
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from browser_helpers import base  # noqa: E402,F401  (fixture for the browser tests)
