import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

CATEGORIES = ["output", "preserve", "monitor"]

ELEMENT_IDS = [
    "game",
    "round-display",
    "funds-display",
    "temperature-display",
    "temperature-bar",
    "rise-rate-display",
    "melt-status-display",
    "dampening-display",
    "intervention-feedback-display",
    "acceleration-display",
    "acceleration-bar",
    "trajectory-display",
    "graph",
    "advance-round-button",
]
for _category in CATEGORIES:
    ELEMENT_IDS += [f"{_category}-name", f"{_category}-count", f"{_category}-invest-button"]

for _prefix in ("b", "c"):
    ELEMENT_IDS += [
        f"{_prefix}-region-card",
        f"{_prefix}-graph",
        f"{_prefix}-temperature-display",
        f"{_prefix}-funds-display",
        f"{_prefix}-melt-status-display",
    ]
    for _category in CATEGORIES:
        ELEMENT_IDS += [f"{_prefix}-{_category}-count", f"{_prefix}-{_category}-invest-button"]

ELEMENT_IDS += [
    "info-page-toggle-button",
    "info-page-panel",
    "info-page-framing",
    "info-page-tie-in",
    "info-page-sources",
]

INITIALLY_DISABLED_IDS = [f"{c}-invest-button" for c in CATEGORIES] + [
    f"{p}-{c}-invest-button" for p in ("b", "c") for c in CATEGORIES
]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements):
        self.module = module
        self.elements = elements

    @property
    def region(self):
        return self.module.region

    def invest(self, category):
        self.elements[f"{category}-invest-button"].dispatch("click", None)

    def invest_secondary(self, prefix, category):
        self.elements[f"{prefix}-{category}-invest-button"].dispatch("click", None)

    def advance_round(self):
        self.elements["advance-round-button"].dispatch("click", None)

    def toggle_info_page(self):
        self.elements["info-page-toggle-button"].dispatch("click", None)


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
