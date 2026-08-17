import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

CATEGORIES = ["output", "reduction", "adaptation"]

ELEMENT_IDS = [
    "season-display",
    "funds-display",
    "acidity-display",
    "acidity-bar",
    "fish-yield-display",
    "fish-yield-bar",
    "sea-level-display",
    "damage-display",
    "damage-saved-display",
    "damage-trend-display",
    "adaptation-tier-display",
    "adaptation-tier-progress",
    "coastline-grid",
    "sea-level-bar",
    "ticker-log",
    "coastline-before-grid",
    "coastline-now-grid",
    "coastline-now-label",
    "advance-season-button",
]
for _category in CATEGORIES:
    ELEMENT_IDS += [f"{_category}-count", f"{_category}-invest-button"]

INITIALLY_DISABLED_IDS = [f"{c}-invest-button" for c in CATEGORIES]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements):
        self.module = module
        self.elements = elements

    @property
    def state(self):
        return self.module.state

    def invest(self, category):
        self.elements[f"{category}-invest-button"].dispatch("click", None)

    def advance_season(self):
        self.elements["advance-season-button"].dispatch("click", None)


def _install_pyodide_fakes(elements):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)

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
    test gets its own module object (and its own SettlementState) rather
    than sharing state via Python's normal import cache.
    """
    elements = {}
    for id_ in ELEMENT_IDS:
        FakeElement(id_, registry=elements)
    for id_ in INITIALLY_DISABLED_IDS:
        elements[id_].disabled = True
    _install_pyodide_fakes(elements)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements)

    _remove_pyodide_fakes()
