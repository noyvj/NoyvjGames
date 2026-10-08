"""Heist Committee's engine is plain Python with no DOM, so the tests import its modules directly."""

import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))


@pytest.fixture(scope="session")
def C():
    import content
    return content.load()
