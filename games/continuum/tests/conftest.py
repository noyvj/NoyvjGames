import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, create_proxy

GAME_DIR = Path(__file__).resolve().parent.parent
GAME_PY = GAME_DIR / "game.py"

# Continuum is split into separate engine modules (sim / research /
# sustainability / save) per its own CLAUDE.md tech notes, so the game
# directory has to be importable before game.py can be exec'd.
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))

ROLES = ["foragers", "gatherers", "crafters", "keepers"]
BUILDINGS = ["shelter", "granary", "hearth", "toolworks"]

ELEMENT_IDS = [
    "era-display",
    "season-display",
    "population-display",
    "housing-display",
    "idle-display",
    "food-display",
    "materials-display",
    "tools-display",
    "knowledge-display",
    "land-health-display",
    "land-health-bar",
    "season-report-display",
    "advance-season-button",
    # Milestone 2 — sustainability score panel
    "score-display",
    "score-bar",
    "score-note-display",
    "livability-display",
    "equity-display",
    "balance-display",
    "resilience-display",
    # Milestone 3 — research panel (node rows are created at runtime)
    "research-status-display",
    "research-list",
]
for _role in ROLES:
    ELEMENT_IDS += [f"{_role}-count", f"{_role}-add-button", f"{_role}-remove-button"]
for _building in BUILDINGS:
    ELEMENT_IDS += [f"{_building}-count", f"{_building}-build-button"]

INITIALLY_DISABLED_IDS = (
    [f"{r}-add-button" for r in ROLES]
    + [f"{r}-remove-button" for r in ROLES]
    + [f"{b}-build-button" for b in BUILDINGS]
)


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements):
        self.module = module
        self.elements = elements

    @property
    def state(self):
        return self.module.state

    def assign(self, role, count=1):
        for _ in range(count):
            self.elements[f"{role}-add-button"].dispatch("click", None)

    def unassign(self, role, count=1):
        for _ in range(count):
            self.elements[f"{role}-remove-button"].dispatch("click", None)

    def build(self, building):
        self.elements[f"{building}-build-button"].dispatch("click", None)

    def advance_season(self, count=1):
        for _ in range(count):
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
    test gets its own module object (and its own CityState) rather than
    sharing state via Python's normal import cache. The engine modules
    (sim/research/sustainability/save) are deliberately left cached — they
    hold only constants, classes and pure functions, no mutable state.
    """
    elements = {id_: FakeElement(id_) for id_ in ELEMENT_IDS}
    for id_ in INITIALLY_DISABLED_IDS:
        elements[id_].disabled = True
    _install_pyodide_fakes(elements)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements)

    _remove_pyodide_fakes()
