import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeTimers, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

GRID_ROWS = 6
GRID_COLS = 6

# Statically-declared element IDs, wired up in index.html's initial markup.
# Plot tiles ("plot-0", "plot-1", ...) are NOT in this list — game.py
# creates them dynamically via document.createElement on each render, and
# FakeDocument.createElement registers them into `elements` as soon as
# their `.id` is assigned (see fakes.py).
ELEMENT_IDS = [
    "plot-grid",
    "selected-plot-state",
    "clear-button",
    "replant-button",
]

# Buttons that carry the `disabled` attribute in index.html's initial markup
# (they read "Loading..." until Pyodide finishes and setup() enables/disables
# them based on real game state).
INITIALLY_DISABLED_IDS = [
    "clear-button",
    "replant-button",
]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM/timers."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

    def plot(self, index):
        return self.module.plots[index]

    def select(self, index):
        self.module.select_plot(index)

    def select_tile_click(self, index):
        """Clicks the rendered tile element for a plot, same path a real
        player click takes (as opposed to calling select_plot directly)."""
        self.elements[f"plot-{index}"].dispatch("click", None)

    def clear(self):
        self.elements["clear-button"].dispatch("click", None)

    def replant(self):
        self.elements["replant-button"].dispatch("click", None)


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
    test gets its own module object (and its own plot grid) rather than
    sharing state via Python's normal import cache.
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
