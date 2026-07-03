import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeTimers, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

# Element IDs wired up in index.html — kept in one place so tests and the
# fixture agree on what "the DOM" contains.
ELEMENT_IDS = [
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
]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM/timers."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

    def click(self):
        self.elements["click-button"].dispatch("click", None)

    def buy_generator(self):
        self.elements["buy-generator-button"].dispatch("click", None)

    def buy_recycler(self):
        self.elements["buy-recycler-button"].dispatch("click", None)


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
    test gets its own module object (and its own resource_count) rather than
    sharing state via Python's normal import cache.
    """
    elements = {id_: FakeElement(id_) for id_ in ELEMENT_IDS}
    timers = FakeTimers()
    _install_pyodide_fakes(elements, timers)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements, timers)

    _remove_pyodide_fakes()
