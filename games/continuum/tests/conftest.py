import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeTimers, create_proxy

GAME_DIR = Path(__file__).resolve().parent.parent
GAME_PY = GAME_DIR / "game.py"

# Continuum is split into separate engine modules (sim / research /
# sustainability / save / info_content / log / transition) per its own
# CLAUDE.md tech notes, so the game directory has to be importable before
# game.py can be exec'd.
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))

# game.py also imports the shared info-page widget (shared/info_page.py)
# the same way the real Pyodide boot script does (see index.html) and the
# same way every climate-quartet game's tests already do -- so the
# repo-root shared/ directory has to be importable too.
SHARED_DIR = GAME_DIR.parent.parent / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

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
    "surplus-display",  # Milestone 8 — Agrarian+
    "land-health-display",
    "land-health-bar",
    "season-report-display",
    "speed-pause-button",
    "speed-1x-button",
    "speed-2x-button",
    "speed-4x-button",
    "season-progress-fill",
    "season-clock-display",
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
    "research-locked-list",
    "research-known-list",
    "research-locked-details",
    "research-locked-summary",
    "research-known-details",
    "research-known-summary",
    # Milestone 5 — collapsed real-world info panel
    "info-page-toggle-button",
    "info-page-panel",
    "info-page-framing",
    "info-page-tie-in",
    "info-page-sources",
    # Z16 audit — info-panel "report an issue" button
    "info-page-report-button",
    # Milestone 6 — the ongoing log (rows are created at runtime)
    "log-status-display",
    "log-list",
    # Milestone 8 — Work/Build panels became dynamic (role/building rows
    # are created at runtime now, the same as research rows always were),
    # and the era-progress control that finally wires up transition.py.
    "work-list",
    "buildings-list",
    "era-progress-status-display",
    "era-progress-reasons-display",
    "advance-era-button",
    # Milestone 15 — achievements panel + unlock toast (rows/cards are
    # created at runtime), and the "look back at a completed era" UI
    # (Milestone 15/K7) whose era rows are also created at runtime.
    "achievements-toggle-button",
    "achievements-panel",
    "achievement-toast",
    "achievement-toast-text",
    "revisit-active-banner",
    "revisit-status-display",
    "revisit-era-list",
    "exit-revisit-button",
    # Milestone 17 — research tree search/filter.
    "research-search-input",
    # "What's New" changelog panel (site-wide goal, planning/TODO.md,
    # origin K16) — rows are created at runtime.
    "changelog-toggle-button",
    "changelog-panel",
    # K5 — the civilization summary report (rows are created at runtime).
    "summary-toggle-button",
    "summary-panel",
    # K12 — starting scenario select (three static buttons, never rebuilt).
    "scenario-standard-button",
    "scenario-frontier-button",
    "scenario-fertile-button",
    "scenario-select-note",
    # K18 — opt-in hard-mode toggle.
    "hard-mode-toggle-button",
    # K2/K8/K10/K21a readouts, K11 civic challenges, K19/K13/K25 charts.
    "founded-display",
    "efficiency-display",
    "calm-streak-display",
    "play-time-display",
    "founders-toggle-button",
    "minutes-toggle-button",
    "minutes-panel",
    "minutes-list",
    "founders-add-button",
    "founders-panel",
    "founders-list",
    "founders-input",
    "research-completion-display",
    "challenges-summary",
    "challenge-status-display",
    "challenge-list",
    "trajectory-graph",
    "livability-scatter",
    "trajectory-summary",
    "trajectory-source",
    "research-branch-provision-button",
    "research-branch-community-button",
    "research-branch-craft-button",
    # K1/K24/K28 -- optional City Views panel.
    "consulting-case-smokestack-button",
    "consulting-case-sprawl-button",
    "consulting-status-display",
    "consulting-abandon-button",
    "views-toggle-button",
    "views-panel",
    "views-tab-dashboard-button",
    "views-tab-map-button",
    "views-tab-flow-button",
    "views-dashboard",
    "views-map",
    "views-map-svg",
    "views-map-caption",
    "views-flow",
    "views-flow-svg",
    "views-flow-caption",
]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

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
        # U1: seasons pass on a clock now; tests step the season directly.
        for _ in range(count):
            self.module.on_advance_season()

    def toggle_views(self):
        self.elements["views-toggle-button"].dispatch("click", None)

    def toggle_changelog(self):
        self.elements["changelog-toggle-button"].dispatch("click", None)


def _install_pyodide_fakes(elements, timers):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
    # Milestone 15: game.py does `from js import document, setTimeout` at
    # module level for the achievement-unlock toast's auto-dismiss — see
    # FakeTimers in fakes.py, same pattern SOL's own tests/conftest.py uses.
    fake_js.setTimeout = timers.setTimeout

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
    # document happened to be active on its first import. Same reasoning
    # as the climate quartet's own conftest.py (e.g. canopy's).
    for name in ("js", "pyodide", "pyodide.ffi", "game", "info_page"):
        sys.modules.pop(name, None)


@pytest.fixture
def game_env():
    """Loads a brand-new game.py module against a fresh fake DOM.

    game.py runs setup() as a module-level side effect on import, so every
    test gets its own module object (and its own CityState) rather than
    sharing state via Python's normal import cache. The engine modules
    (sim/research/sustainability/save/log/transition/info_content) are
    deliberately left cached — they hold only constants, classes and pure
    functions, no mutable state.
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
