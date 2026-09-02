import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, create_proxy

GAME_DIR = Path(__file__).resolve().parent.parent
GAME_PY = GAME_DIR / "game.py"
CATALOG_PATH = GAME_DIR / "fren_combined_catalog.json"

# The page's boot script fetches the catalog and hands it to Python as a
# window global before running game.py (see index.html); the fake `js`
# module below stands in for that, so tests exercise the real 966-item
# catalog rather than a stub.
CATALOG_JSON = CATALOG_PATH.read_text(encoding="utf-8")

ELEMENT_IDS = [
    "farm",
    "day-display",
    "due-display",
    "pace-display",
    "progress-display",
    "stage-summary-display",
    "row-summary-display",
    "practice-panel",
    "practice-context",
    "practice-instruction",
    "practice-prompt",
    "practice-note",
    "practice-choices",
    "practice-answer-input",
    "practice-submit-button",
    "practice-feedback",
    "practice-close-button",
    "water-next-button",
    "next-day-button",
    "legend",
    "accent-toggle-checkbox",
]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements):
        self.module = module
        self.elements = elements

    @property
    def state(self):
        return self.module.state

    def plot(self, plot_id):
        return self.state.plots_by_id[plot_id]

    def water_next(self):
        self.elements["water-next-button"].dispatch("click", None)

    def next_day(self):
        self.elements["next-day-button"].dispatch("click", None)

    def close_practice(self):
        self.elements["practice-close-button"].dispatch("click", None)


def _install_pyodide_fakes(elements):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
    fake_js.CATALOG_JSON = CATALOG_JSON

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
    elements = {id_: FakeElement(id_) for id_ in ELEMENT_IDS}
    _install_pyodide_fakes(elements)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)

    yield GameEnv(module, elements)

    _remove_pyodide_fakes()
