import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeTimers, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

SHIP_IDS = ["1", "2"]
COLONY_IDS = ["aurum", "verdant", "ferrum"]

# Statically-declared element IDs, wired up in index.html's initial markup.
ELEMENT_IDS = [
    "profit-display",
    "sale-log",
]
for _ship_id in SHIP_IDS:
    ELEMENT_IDS.append(f"ship-{_ship_id}-status")
    ELEMENT_IDS.append(f"ship-{_ship_id}-load-button")
    for _colony_id in COLONY_IDS:
        ELEMENT_IDS.append(f"ship-{_ship_id}-depart-{_colony_id}-button")

INITIALLY_DISABLED_IDS = [f"ship-{s}-depart-{c}-button" for s in SHIP_IDS for c in COLONY_IDS]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM/timers."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

    def ship(self, ship_id="1"):
        return self.module.ships[ship_id]

    @property
    def total_profit(self):
        return self.module.total_profit

    def load(self, ship_id="1"):
        self.elements[f"ship-{ship_id}-load-button"].dispatch("click", None)

    def depart(self, destination, ship_id="1"):
        self.elements[f"ship-{ship_id}-depart-{destination}-button"].dispatch("click", None)

    def tick(self, times=1):
        self.timers.tick_intervals(times)


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
    test gets its own module object (and its own ships/colony state) rather
    than sharing state via Python's normal import cache.
    """
    elements = {}
    for id_ in ELEMENT_IDS:
        FakeElement(id_, registry=elements)
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
