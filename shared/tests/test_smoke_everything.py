"""Z-11: 'smoke everything'. Every game is booted headlessly the way its own tests boot it (the
game's `game_env` fixture, a fake DOM, no browser, no network), then driven by a seeded random
fuzzer for a few hundred steps. After every few steps `get_state()` is checked: the call must not
raise, the state must be clean JSON (no NaN, no infinity) and no number may be negative unless its
key is signed by design (net, delta, change, pct ... see smoke_support.SIGNED_KEY). Any exception
from a click handler or an engine call fails the test.

Two kinds of games:
  * the 12 DOM games are driven by clicking a seeded-random enabled button (the game's real
    handlers run, including the panels, the achievements code and the info page);
  * Signal, Chronicle, Lexis and Heist Committee have no DOM, only a request/response engine, so they get a
    small action grammar (smoke_support.signal_request / chronicle_request / lexis_request / heist_request).

Deterministic: fixed seeds, `random.seed` set before each run. The whole file takes well under a
minute. NOT covered (listed so nobody assumes otherwise): `change`/`input`/`keydown` handlers
(select menus and text boxes are never touched), the canvas / 3D renderers and anything that
needs a real browser (see the Playwright tests in this folder), the Desktop boot (`pc.html`), and
the deeper modes of Chronicle (web, myth, account, decision, review) which the grammar only
switches to.

Run one game: python3 -m pytest -q shared/tests/test_smoke_everything.py -k grid
"""

import pytest

import smoke_support as ss

# steps per game: more for the fast ones, fewer where one get_state() is slow (Drift, Thaw, Champ).
STEPS = {"aftermath": 1200, "canopy": 800, "champ-de-mots": 300, "continuum": 600, "drift": 300,
         "grid": 1200, "herd": 1200, "loop": 1000, "sol": 1200, "thaw": 300, "tide": 800, "trade-empire": 800,
         "signal": 600, "chronicle": 400, "lexis": 400, "heist-committee": 400}
SEEDS = (20261008, 7)

# Extra paths that may legitimately be negative in one game (regex over the state path).
SIGNED_OK = {}

# The fuzzer must really have played: at least this many handlers fired and this many distinct
# buttons/actions were used, or the harness is silently doing nothing.
MIN_CLICKS = 20
MIN_DISTINCT = 3


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("slug", ss.FAKE_DOM_GAMES)
def test_dom_game_survives_random_clicking(slug, seed):
    with ss.fake_dom_game(slug) as env:
        result = ss.fuzz_fake_dom(env, seed=seed, steps=STEPS[slug], signed_ok=SIGNED_OK.get(slug, ""))
    assert not result["errors"], "\n".join(result["errors"][:5])
    assert result["clicks"] >= MIN_CLICKS and result["distinct"] >= MIN_DISTINCT, result


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("slug", ss.ENGINE_GAMES)
def test_engine_game_survives_random_requests(slug, seed):
    with ss.engine_game(slug) as (call, get_state, next_request):
        result = ss.fuzz_requests(call, get_state, next_request, seed=seed, steps=STEPS[slug],
                                  signed_ok=SIGNED_OK.get(slug, ""))
    assert not result["errors"], "\n".join(result["errors"][:5])
    assert result["clicks"] >= MIN_CLICKS and result["distinct"] >= MIN_DISTINCT, result


def test_every_game_folder_is_covered():
    """A new game must be added to the harness (or listed here with a reason)."""
    folders = sorted(p.name for p in ss.GAMES.iterdir() if (p / "game.py").is_file())
    assert folders == ss.ALL_GAMES, "games on disk and games in smoke_support differ"


def test_state_checker_catches_what_it_should():
    assert ss.state_problems({"funds": 10, "net_profit": -5, "nested": {"wear_pct": -2.5}}) == []
    assert any("NaN" in p or "nan" in p for p in ss.state_problems({"funds": float("nan")}))
    assert any("inf" in p for p in ss.state_problems({"energy": {"a": float("inf")}}))
    negative = ss.state_problems({"resources": [1, -3]})
    assert negative and "/resources/1" in negative[0]
    assert ss.state_problems({"x": -1}, signed_ok=r"^/x$") == []
    assert ss.state_problems({"x": {1, 2}})                   # not JSON-clean


def test_fuzzer_reports_a_handler_that_raises():
    class Element:
        disabled = False
        hidden = False

        def __init__(self):
            self._listeners = {"click": [self.boom]}

        def boom(self, event):
            raise ValueError("broken handler")

        def dispatch(self, name, event=None):
            for handler in self._listeners[name]:
                handler(event)

    class Env:
        elements = {"go": Element()}
        timers = None

        class module:  # noqa: N801
            @staticmethod
            def get_state():
                return {}

    result = ss.fuzz_fake_dom(Env, seed=1, steps=5)
    assert result["errors"] and "broken handler" in result["errors"][0]
