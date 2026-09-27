"""Signal's engine (game.py) never touches the DOM -- app.js draws whatever it
returns -- so unlike the older Pyodide games there is no fake-DOM harness to
build: the module is loaded once and every test resets it through `g`.
"""

import datetime
import importlib.util
import random
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
GAME_PY = GAME_DIR / "game.py"

EPOCH_DATE = datetime.date(2026, 9, 27)


def _load_module():
    # game.py optionally does `import js`; under CPython that must fail cleanly.
    sys.modules.pop("js", None)
    spec = importlib.util.spec_from_file_location("signal_game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["signal_game"] = module
    spec.loader.exec_module(module)
    return module


_MODULE = _load_module()


class Engine:
    """Thin wrapper so tests read like play."""

    def __init__(self, module):
        self.m = module

    def call(self, action, **kwargs):
        req = {"action": action}
        req.update(kwargs)
        return self.m.handle_dict(req)

    def set_day(self, offset=0):
        day = EPOCH_DATE + datetime.timedelta(days=offset)
        self.m.set_clock(lambda: day)
        return day.isoformat()

    def truth(self):
        return sorted(self.m._cur["puzzle"].transmitters)

    def truth_rc(self):
        n = self.m.board_for(self.m._cur["mode"]).n
        return [[t // n, t % n] for t in self.truth()]

    def win_current(self, pings=1):
        """Ping a few tiles, mark the true transmitters and commit."""
        n = self.m.board_for(self.m._cur["mode"]).n
        for i in range(pings):
            self.call("ping", r=i % n, c=(i * 2) % n)
        for r, c in self.truth_rc():
            assert self.call("mark", r=r, c=c)["ok"]
        return self.call("commit")

    def lose_current(self):
        n = self.m.board_for(self.m._cur["mode"]).n
        truth = set(self.truth())
        # mark k interior tiles that are not transmitters
        marked = 0
        board = self.m.board_for(self.m._cur["mode"])
        for cell in board.cells:
            if cell not in truth and marked < board.k:
                assert self.call("mark", r=cell // n, c=cell % n)["ok"]
                marked += 1
        return self.call("commit")


@pytest.fixture
def g():
    """The engine module reset to a brand-new player on launch day."""
    m = _MODULE
    m.reset_engine()
    m.set_random_source(random.Random(20260927))
    engine = Engine(m)
    engine.set_day(0)
    yield engine
    m.set_clock(None)
    m.set_random_source(None)
    m.reset_engine()


@pytest.fixture
def game():
    return _MODULE
