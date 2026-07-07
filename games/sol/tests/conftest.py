import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeTimers, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

# Buttons that carry the `disabled` attribute in index.html's initial markup
# (they read "Loading..." until Pyodide finishes and setup() enables them).
# The fixture mirrors this so a setup() that forgets to re-enable one of
# them shows up as a real test failure, not a false negative from the fake
# defaulting to enabled.
INITIALLY_DISABLED_IDS = [
    "click-button",
    "buy-generator-button",
    "buy-recycler-button",
    "fund-research-button",
    "travel-moon-button",
    "travel-mars-button",
    "mars-click-button",
    "mars-buy-generator-button",
    "mars-buy-recycler-button",
    "buy-trade-route-button",
    "mars-buy-trade-route-button",
]

# Element IDs wired up in index.html — kept in one place so tests and the
# fixture agree on what "the DOM" contains.
ELEMENT_IDS = [
    # Earth
    "click-button",
    "resource-count",
    "resource-label",
    "buy-generator-button",
    "generator-count",
    "generator-rate",
    "ecology-percent",
    "ecology-bar",
    "ecology-status",
    "buy-recycler-button",
    "recycler-count",
    "recycler-rate",
    # Research (Earth/global)
    "research-progress",
    "research-bar",
    "research-status",
    "fund-research-button",
    # Views
    "earth-view",
    "mars-view",
    "away-view",
    # Governor
    "priority-growth-button",
    "priority-balance-button",
    "priority-ecology-button",
    "governor-budget-value",
    "budget-increase-button",
    "budget-decrease-button",
    # Travel
    "travel-status",
    "travel-moon-button",
    "travel-mars-button",
    # Moon placeholder (away-view)
    "away-planet-name",
    "away-iron",
    "away-generators",
    "away-recyclers",
    "away-ecology",
    "return-to-earth-button",
    # Mars's own economy
    "mars-click-button",
    "mars-resource-count",
    "mars-resource-label",
    "mars-buy-generator-button",
    "mars-generator-count",
    "mars-generator-rate",
    "mars-ecology-percent",
    "mars-ecology-bar",
    "mars-ecology-status",
    "mars-buy-recycler-button",
    "mars-recycler-count",
    "mars-recycler-rate",
    "mars-return-to-earth-button",
    # Cross-planet governed summaries
    "mars-summary",
    "mars-summary-resource",
    "mars-summary-generators",
    "mars-summary-recyclers",
    "mars-summary-ecology",
    "earth-summary-resource",
    "earth-summary-generators",
    "earth-summary-recyclers",
    "earth-summary-ecology",
    # Trade routes
    "earth-trade",
    "trade-route-count",
    "trade-route-rate",
    "trade-route-destination",
    "buy-trade-route-button",
    "mars-trade-route-count",
    "mars-trade-route-rate",
    "mars-trade-route-destination",
    "mars-buy-trade-route-button",
]

_BUTTON_ID = {
    "Earth": {
        "click": "click-button",
        "buy_generator": "buy-generator-button",
        "buy_recycler": "buy-recycler-button",
        "buy_trade_route": "buy-trade-route-button",
    },
    "Mars": {
        "click": "mars-click-button",
        "buy_generator": "mars-buy-generator-button",
        "buy_recycler": "mars-buy-recycler-button",
        "buy_trade_route": "mars-buy-trade-route-button",
    },
}


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM/timers."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

    @property
    def earth(self):
        return self.module.planet_state["Earth"]

    @property
    def mars(self):
        return self.module.planet_state["Mars"]

    def state(self, planet):
        return self.module.planet_state[planet]

    def click(self, planet="Earth"):
        self.elements[_BUTTON_ID[planet]["click"]].dispatch("click", None)

    def buy_generator(self, planet="Earth"):
        self.elements[_BUTTON_ID[planet]["buy_generator"]].dispatch("click", None)

    def buy_recycler(self, planet="Earth"):
        self.elements[_BUTTON_ID[planet]["buy_recycler"]].dispatch("click", None)

    def buy_trade_route(self, planet="Earth"):
        self.elements[_BUTTON_ID[planet]["buy_trade_route"]].dispatch("click", None)

    def fund_research(self):
        self.elements["fund-research-button"].dispatch("click", None)

    def set_priority(self, priority):
        self.elements[f"priority-{priority}-button"].dispatch("click", None)

    def increase_budget(self):
        self.elements["budget-increase-button"].dispatch("click", None)

    def decrease_budget(self):
        self.elements["budget-decrease-button"].dispatch("click", None)

    def travel_to_moon(self):
        self.elements["travel-moon-button"].dispatch("click", None)

    def travel_to_mars(self):
        self.elements["travel-mars-button"].dispatch("click", None)

    def return_to_earth(self):
        # Whichever "Return to Earth" button is relevant depends on where
        # the player currently is (Moon's placeholder vs Mars's own view).
        if self.module.current_planet == "Mars":
            self.elements["mars-return-to-earth-button"].dispatch("click", None)
        else:
            self.elements["return-to-earth-button"].dispatch("click", None)


def _install_pyodide_fakes(elements, timers):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
    fake_js.setTimeout = timers.setTimeout
    fake_js.setInterval = timers.setInterval

    fake_pyodide = types.ModuleType("pyodide")
    fake_pyodide_ffi = types.ModuleType("pyodide.ffi")
    fake_pyodide_ffi.create_proxy = create_proxy
    fake_pyodide.ffi = fake_pyodide_ffi

    sys.modules["js"] = fake_js
    sys.modules["pyodide"] = fake_pyodide
    sys.modules["pyodide.ffi"] = fake_pyodide_ffi


def _remove_pyodide_fakes():
    for name in ("js", "pyodide", "pyodide.ffi", "game"):
        sys.modules.pop(name, None)


@pytest.fixture
def game_env():
    """Loads a brand-new game.py module against a fresh fake DOM.

    game.py runs setup() as a module-level side effect on import, so every
    test gets its own module object (and its own planet_state) rather than
    sharing state via Python's normal import cache.
    """
    elements = {id_: FakeElement(id_) for id_ in ELEMENT_IDS}
    for id_ in INITIALLY_DISABLED_IDS:
        elements[id_].disabled = True
    timers = FakeTimers()
    _install_pyodide_fakes(elements, timers)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements, timers)

    _remove_pyodide_fakes()
