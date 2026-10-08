"""Dead Reckoning's engine modules are plain Python with no DOM, so the tests import them directly."""

import copy
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))

import pytest  # noqa: E402

BASE_CHART = {
    "id": "test-base", "name": "Test water", "chapter": "open", "size": 20,
    "start": [2.0, 2.0], "dest": [18.0, 18.0], "arrival_radius": 1.5, "deadline": 12.0,
    "speeds": [3.0, 8.0], "start_hour": 0.0,
    "land": [], "hazards": [], "currents": [], "landmarks": [],
}


@pytest.fixture
def chart():
    """A fresh empty 20 nm square of open water; tests add what they need."""
    return copy.deepcopy(BASE_CHART)


@pytest.fixture
def g():
    """The engine module with fresh state, plus a small `call(action, **fields)` that returns the decoded view."""
    import json
    import game
    game.handle(json.dumps({"action": "reset"}))
    game.call = lambda action, **fields: json.loads(game.handle(json.dumps(dict(fields, action=action))))
    return game
