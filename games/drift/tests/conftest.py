import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

ELEMENT_IDS = [
    "round-display",
    "funds-display",
    "total-capacity-display",
    "arrivals-display",
    "total-arrivals-display",
    "strain-display",
    "strain-bar",
    "integrated-display",
    "pending-display",
    "service-quality-display",
    "economic-health-display",
    "social-cohesion-display",
    "wellbeing-display",
    "wellbeing-message-display",
    "housing-name",
    "housing-count",
    "housing-invest-button",
    "services-name",
    "services-count",
    "services-invest-button",
    "infrastructure-name",
    "infrastructure-count",
    "infrastructure-invest-button",
    "advance-round-button",
]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements):
        self.module = module
        self.elements = elements

    @property
    def region(self):
        return self.module.region

    def advance_round(self):
        self.elements["advance-round-button"].dispatch("click", None)


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
    test gets its own module object (and its own RegionState) rather than
    sharing state via Python's normal import cache.
    """
    elements = {id_: FakeElement(id_) for id_ in ELEMENT_IDS}
    _install_pyodide_fakes(elements)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements)

    _remove_pyodide_fakes()
