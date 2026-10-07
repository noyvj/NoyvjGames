"""Chronicle's engine modules are plain Python with no DOM, so the tests import them directly."""

import copy
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
SETS_DIR = GAME_DIR / "sets"
SAMPLE_DIR = SETS_DIR / "presidents-sample"
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))

import game as _game  # noqa: E402
import setdata  # noqa: E402


def strip_extras(raw):
    """Remove the whose-account and decision-point parts from a copy of the sample, leaving a set with only the older mechanics."""
    raw.pop("accounts", None)
    raw.pop("decisions", None)
    raw["claims"] = [c for c in raw["claims"] if c["field"] not in ("account", "decision")]


@pytest.fixture
def raw():
    """The sample set's seven files as plain dicts: a fresh deep copy per test, free to break."""
    return copy.deepcopy(setdata.read_set_files(SAMPLE_DIR))


@pytest.fixture(scope="session")
def sample():
    return setdata.load_set(SAMPLE_DIR)


@pytest.fixture
def g():
    """The engine reset to a brand-new player with the sample set loaded."""
    _game.load_sets(SETS_DIR)
    _game.reset_engine()
    yield _game
    _game.reset_engine()


class Player:
    """Thin wrapper so engine tests read like play."""

    def __init__(self, module):
        self.m = module

    def call(self, action, **kwargs):
        req = {"action": action}
        req.update(kwargs)
        return self.m.handle_dict(req)

    def puzzle(self):
        sess = self.m.S["session"]
        import puzzle as pz
        return pz.make_puzzle(self.m.SETS[sess["set"]], sess["section"], sess["round"])

    def solve(self, wrong_first=False):
        """Fill the current puzzle (optionally wrongly first) and check until it is solved."""
        puz = self.puzzle()
        order = list(puz.answer)
        if wrong_first:
            order = order[1:] + order[:1]
        for i, e in enumerate(order):
            self.call("place", event=e, slot=i)
        r = self.call("check")
        while self.m.S["session"]["status"] == "playing":
            puz = self.puzzle()
            sess = self.m.S["session"]
            for i, e in enumerate(puz.answer):
                if not sess["locked"][i]:
                    self.call("place", event=e, slot=i)
            r = self.call("check")
        return r


@pytest.fixture
def p(g):
    player = Player(g)
    player.call("boot")
    return player
