import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

MEASURE_IDS = ["feed", "caps", "capture"]

ELEMENT_IDS = [
    "round-display",
    "funds-display",
    "herd-display",
    "methane-display",
    "coupling-display",
    "pressure-display",
    "methane-bar",
    "score-display",
    "decoupling-summary-display",
    "coupling-gauge",
    "coupling-gauge-label",
    "haze-overlay",
    "grow-herd-button",
    "advance-round-button",
    "plant-pivot-display",
    "plant-pivot-count",
    "plant-pivot-invest-button",
    "info-page-toggle-button",
    "info-page-panel",
    "info-page-framing",
    "info-page-tie-in",
    "info-page-sources",
]
for _measure in MEASURE_IDS:
    ELEMENT_IDS += [f"{_measure}-name", f"{_measure}-count", f"{_measure}-invest-button"]

INITIALLY_DISABLED_IDS = (
    ["grow-herd-button", "plant-pivot-invest-button"] + [f"{m}-invest-button" for m in MEASURE_IDS]
)


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements):
        self.module = module
        self.elements = elements

    @property
    def farm(self):
        return self.module.farm

    def grow_herd(self):
        self.elements["grow-herd-button"].dispatch("click", None)

    def advance_round(self):
        self.elements["advance-round-button"].dispatch("click", None)

    def toggle_info_page(self):
        self.elements["info-page-toggle-button"].dispatch("click", None)

    def invest_decoupling(self, measure):
        self.elements[f"{measure}-invest-button"].dispatch("click", None)

    def invest_plant_pivot(self):
        self.elements["plant-pivot-invest-button"].dispatch("click", None)


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
    test gets its own module object (and its own FarmState) rather than
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
