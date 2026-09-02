import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

# game.py imports the shared info-page widget (shared/info_page.py) the
# same way the real Pyodide boot script does -- see any game's index.html
# -- so the repo-root shared/ directory has to be importable before
# game.py can be exec'd.
SHARED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

PLANT_TYPES = ["coal", "gas", "nuclear", "solar", "wind", "hydro"]

ELEMENT_IDS = [
    "round-display",
    "demand-display",
    "funds-display",
    "capacity-display",
    "emissions-display",
    "fossil-share-display",
    "event-display",
    "score-display",
    "trend-display",
    "aging-event-display",
    "emissions-bar",
    "disruption-risk-display",
    "score-bar",
    "trend-graph",
    "trend-graph-message",
    "global-comparison-message",
    "renewable-blurb",
    "advance-round-button",
    "info-page-toggle-button",
    "info-page-panel",
    "info-page-framing",
    "info-page-tie-in",
    "info-page-sources",
]
for _plant in PLANT_TYPES:
    ELEMENT_IDS += [
        f"{_plant}-count",
        f"{_plant}-build-button",
        f"{_plant}-retire-button",
        f"{_plant}-maintain-button",
        f"{_plant}-name",
    ]

INITIALLY_DISABLED_IDS = (
    [f"{p}-build-button" for p in PLANT_TYPES]
    + [f"{p}-retire-button" for p in PLANT_TYPES]
    + [f"{p}-maintain-button" for p in PLANT_TYPES]
)


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements):
        self.module = module
        self.elements = elements

    @property
    def state(self):
        return self.module.state

    def build(self, plant_type):
        self.elements[f"{plant_type}-build-button"].dispatch("click", None)

    def retire(self, plant_type):
        self.elements[f"{plant_type}-retire-button"].dispatch("click", None)

    def maintain(self, plant_type):
        self.elements[f"{plant_type}-maintain-button"].dispatch("click", None)

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
    # "info_page" is popped too, alongside "game" -- it's a plain `import
    # info_page` (not spec_from_file_location like game.py), so without
    # this it would stay cached in sys.modules across tests with its
    # `from js import document` binding pinned to whichever test's fake
    # document happened to be active on its first import.
    for name in ("js", "pyodide", "pyodide.ffi", "game", "info_page"):
        sys.modules.pop(name, None)


@pytest.fixture
def game_env():
    """Loads a brand-new game.py module against a fresh fake DOM.

    game.py runs setup() as a module-level side effect on import, so every
    test gets its own module object (and its own GridState) rather than
    sharing state via Python's normal import cache.
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
