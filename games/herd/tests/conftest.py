import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeLocalStorage, FakeTimers, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

# game.py imports the shared info-page widget (shared/info_page.py) the
# same way the real Pyodide boot script does -- see any game's index.html
# -- so the repo-root shared/ directory has to be importable before
# game.py can be exec'd.
SHARED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

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
    "achievements-toggle-button",
    "achievements-panel",
    "achievement-toast",
    "achievement-toast-text",
    "milestone-toast",
    "milestone-toast-text",
    "report-card-toggle-button",
    "report-card-panel",
    # K16: "What's New" changelog panel.
    "changelog-toggle-button",
    "changelog-panel",
    "grow-consequence-preview",
    "combined-decoupling-display",
    "gauge-range-display",
    "real-world-comparison-display",
    "methane-trend-graph",
    "counterfactual-comparison-display",
    "baseline-herd-display",
    "baseline-funds-display",
    "baseline-methane-display",
    "baseline-score-display",
    "pasture-cow-a",
    "pasture-cow-b",
    "pasture-cow-c",
    "pasture-cow-d",
    "pasture-cow-e",
    "pasture-herd-count",
    "pasture-wisp-a",
    "pasture-wisp-c",
    "certification-display",
    # F8: per-browser record-decoupling-ratio marker/label.
    "coupling-gauge-record-display",
    # Round-3 extras (F23/F5/F13/F9/F3/F15/F17/F19/F27/F29).
    "vignette-display", "season-display", "welfare-display", "biogas-display",
    "genetics-display", "genetics-invest-button", "supply-chain-display",
    "supply-chain-invest-button", "variation-checkbox", "cap-checkbox", "cap-display",
    "policy-panel", "policy-display", "policy-subsidy-button", "policy-cash-button",
    "poultry-panel", "poultry-display", "poultry-grow-button",
    "litter-count", "litter-invest-button", "biofilter-count", "biofilter-invest-button",
]
for _measure in MEASURE_IDS:
    ELEMENT_IDS += [f"{_measure}-name", f"{_measure}-count", f"{_measure}-invest-button"]

INITIALLY_DISABLED_IDS = (
    ["grow-herd-button", "plant-pivot-invest-button"] + [f"{m}-invest-button" for m in MEASURE_IDS]
)


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements, timers, local_storage):
        self.module = module
        self.elements = elements
        self.timers = timers
        self.local_storage = local_storage

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

    def toggle_achievements(self):
        self.elements["achievements-toggle-button"].dispatch("click", None)

    def toggle_report_card(self):
        self.elements["report-card-toggle-button"].dispatch("click", None)

    def toggle_changelog(self):
        self.elements["changelog-toggle-button"].dispatch("click", None)

    def reload(self):
        """Re-execs a brand-new game.py module against the *same*
        FakeLocalStorage instance -- simulates a fresh page load on a
        browser that already has a record stored, which is what F8's
        "record persists across a fresh module load" test needs. Reuses
        this env's existing fake DOM elements/timers (a real page reload
        would build fresh DOM nodes too, but nothing under test here reads
        stale state off them -- setup() at the bottom of game.py
        overwrites everything on exec)."""
        for name in ("game", "info_page"):
            sys.modules.pop(name, None)
        module = _load_module(self.elements, self.timers, self.local_storage)
        self.module = module
        return module


def _install_pyodide_fakes(elements, timers, local_storage):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
    fake_js.setTimeout = timers.setTimeout
    fake_js.localStorage = local_storage

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


def _load_module(elements, timers, local_storage):
    """Execs a fresh game.py module against the given fake DOM/storage.
    Factored out of the game_env fixture so GameEnv.reload() (F8's "fresh
    module load against the same localStorage" test) can reuse it."""
    _install_pyodide_fakes(elements, timers, local_storage)
    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py
    return module


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
    timers = FakeTimers()
    local_storage = FakeLocalStorage()
    module = _load_module(elements, timers, local_storage)

    yield GameEnv(module, elements, timers, local_storage)

    _remove_pyodide_fakes()
