"""Station Medic's engine modules are plain Python with no DOM, so the tests import them directly."""

import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
for path in (GAME_DIR, GAME_DIR / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
