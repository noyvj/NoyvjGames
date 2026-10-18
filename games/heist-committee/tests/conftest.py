"""Heist Committee's engine is plain Python with no DOM, so the tests import its modules directly."""

import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))

# tests/browser_helpers.py (the shared browser-test set-up) is imported by plain name: `from browser_helpers import base, open_game`.
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from browser_helpers import base  # noqa: E402,F401  (fixture for the browser tests)


@pytest.fixture(scope="session")
def C():
    import content
    return content.load()


@pytest.fixture()
def g():
    """A fresh game module state: the module is imported once; each test starts a new career."""
    import json

    import game
    game.handle(json.dumps({"action": "new_career", "seed": 77}))

    class Handle:
        module = game

        def __call__(self, **request):
            return json.loads(game.handle(json.dumps(request)))

    return Handle()
