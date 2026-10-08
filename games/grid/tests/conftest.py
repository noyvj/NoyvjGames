import importlib.util
import random
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeTimers, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

# game.py imports the shared info-page widget (shared/info_page.py) the
# same way the real Pyodide boot script does -- see any game's index.html
# -- so the repo-root shared/ directory has to be importable before
# game.py can be exec'd.
SHARED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

QUIET_SEED = "GRID-BCDFG"
PLANT_TYPES = ["coal", "gas", "nuclear", "solar", "wind", "hydro", "battery"]
# C2: battery is storage, not generation -- it has no plant-mix chart row
# (see game.py's GENERATION_TYPES comment).
GENERATION_PLANT_TYPES = [t for t in PLANT_TYPES if t != "battery"]

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
    "real-grid-select",
    "real-grid-verdict",
    "real-grid-table",
    "real-grid-source",
    "shadow-select",
    "shadow-verdict",
    "shadow-table",
    "renewable-blurb",
    "regional-grid-connect-button",
    "regional-grid-display",
    "advance-round-button",
    "info-page-toggle-button",
    "info-page-panel",
    "info-page-framing",
    "info-page-tie-in",
    "info-page-sources",
    "achievements-toggle-button",
    "achievements-panel",
    # "What's New" changelog panel (site-wide goal, origin K16)
    "changelog-toggle-button",
    "changelog-panel",
    "summary-toggle-button",
    "summary-panel",
    # Round-3 pass (2026-09-20): demand response (C7), weather log (C17),
    # policy lever (C19).
    "weather-log-toggle-button",
    "weather-log-panel",
    "demand-response-button",
    "demand-response-level-display",
    "policy-lever-banner",
    "active-policy-display",
    "policy-accept-carbon-pricing-button",
    "policy-accept-renewable-subsidy-button",
    "policy-decline-button",
    "achievement-toast",
    "achievement-toast-text",
    "retire-callout",
    "retire-callout-dismiss-button",
    "maintain-callout",
    "maintain-callout-dismiss-button",
    "renewable-milestone-callout",
    "renewable-milestone-dismiss-button",
    "disruption-toast",
    "disruption-toast-text",
    "funds-breakdown-revenue",
    "funds-breakdown-build",
    "funds-breakdown-maintenance",
    "funds-breakdown-disruption",
    "steeper-demand-toggle-button",
    "weather-variability-toggle-button",
    "scenario-toggle-button",
    "streak-display",
    "career-toggle-button",
    "career-panel",
    "career-stats-display",
    "career-preview-display",
    "career-finish-button",
    "career-tree-summary",
    "career-tree",
    "career-whatif",
    "career-whatif-verdict",
    "start-option-select",
    "start-option-note",
    "run-seed-display",
    "run-seed-input",
    "run-seed-apply-button",
    "run-seed-note",
    "ironman-toggle-button",
    "undo-build-button",
    "grant-banner",
    "grant-text",
    "grant-accept-button",
    "grant-decline-button",
    "grant-message-display",
    "peek-forecast-button",
    "peek-forecast-display",
    "perfect-streak-display",
    "eulogy-display",
    "career-records-display",
    "career-record-flash",
    "career-next-perk-display",
    "career-history-chart",
    "career-history-list",
    "career-lifetime-display",
    "career-heatmap",
    "career-data-field",
    "career-export-button",
    "career-import-button",
    "career-reset-button",
    "career-data-status",
    "auto-advance-button",
    "auto-advance-status",
    "round-recap-summary",
    "round-recap-body",
    "difficulty-preset-select",
    "difficulty-header-display",
    "difficulty-preset-note",
    "arbitrage-mode-button",
    "arbitrage-status-display",
    "emergency-status-display",
    "funds-bar-revenue",
    "funds-bar-build",
    "funds-bar-maintenance",
    "funds-bar-disruption",
]
for _plant in PLANT_TYPES:
    ELEMENT_IDS += [
        f"{_plant}-count",
        f"{_plant}-build-button",
        f"{_plant}-retire-button",
        f"{_plant}-maintain-button",
        f"{_plant}-maintenance-schedule-select",
        f"{_plant}-name",
        f"{_plant}-wear-pct",
        f"{_plant}-risk-badge",
        f"{_plant}-names",
    ]
for _plant in GENERATION_PLANT_TYPES:
    ELEMENT_IDS += [
        f"{_plant}-mix-bar",
        f"{_plant}-mix-pct",
        f"{_plant}-mix-row",
    ]
for _plant in PLANT_TYPES:
    ELEMENT_IDS.append(f"{_plant}-row")
ELEMENT_IDS.append("mix-hover-readout")

INITIALLY_DISABLED_IDS = (
    [f"{p}-build-button" for p in PLANT_TYPES]
    + [f"{p}-retire-button" for p in PLANT_TYPES]
    + [f"{p}-maintain-button" for p in PLANT_TYPES]
    + [f"{p}-maintenance-schedule-select" for p in PLANT_TYPES]
)


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

    @property
    def state(self):
        return self.module.state

    def build(self, plant_type):
        self.elements[f"{plant_type}-build-button"].dispatch("click", None)

    def retire(self, plant_type):
        self.elements[f"{plant_type}-retire-button"].dispatch("click", None)

    def maintain(self, plant_type):
        self.elements[f"{plant_type}-maintain-button"].dispatch("click", None)

    def set_maintenance_schedule(self, plant_type, interval):
        """TODO-C23: mirrors a real <select> 'change' event -- sets the
        element's own `.value` (what a browser does natively before
        dispatching change) then fires a change event whose `.target` is
        the select itself, so game.py's handler can read
        `event.target.value` the same way it would from a real DOM
        event."""
        select = self.elements[f"{plant_type}-maintenance-schedule-select"]
        select.value = str(interval)

        class _FakeChangeEvent:
            pass

        event = _FakeChangeEvent()
        event.target = select
        select.dispatch("change", event)

    def advance_round(self):
        self.elements["advance-round-button"].dispatch("click", None)

    def toggle_info_page(self):
        self.elements["info-page-toggle-button"].dispatch("click", None)

    def toggle_achievements(self):
        self.elements["achievements-toggle-button"].dispatch("click", None)

    def toggle_changelog(self):
        self.elements["changelog-toggle-button"].dispatch("click", None)

    def toggle_summary_panel(self):
        self.elements["summary-toggle-button"].dispatch("click", None)

    def toggle_steeper_demand(self):
        self.elements["steeper-demand-toggle-button"].dispatch("click", None)

    def toggle_weather_variability(self):
        self.elements["weather-variability-toggle-button"].dispatch("click", None)

    def toggle_weather_log(self):
        self.elements["weather-log-toggle-button"].dispatch("click", None)

    def auto_advance(self):
        self.elements["auto-advance-button"].dispatch("click", None)

    def choose_difficulty_preset(self, key):
        select = self.elements["difficulty-preset-select"]
        select.value = key

        class _Event:
            pass

        event = _Event()
        event.target = select
        select.dispatch("change", event)

    def toggle_career(self):
        self.elements["career-toggle-button"].dispatch("click", None)

    def cycle_arbitrage_mode(self):
        self.elements["arbitrage-mode-button"].dispatch("click", None)

    def invest_demand_response(self):
        self.elements["demand-response-button"].dispatch("click", None)

    def enact_carbon_pricing(self):
        self.elements["policy-accept-carbon-pricing-button"].dispatch("click", None)

    def enact_renewable_subsidy(self):
        self.elements["policy-accept-renewable-subsidy-button"].dispatch("click", None)

    def decline_policy(self):
        self.elements["policy-decline-button"].dispatch("click", None)


def _install_pyodide_fakes(elements, timers):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
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
    # Run seeds are drawn from Python's random (game.new_run_seed), so fix it: every test starts from the
    # same seed and nothing depends on a lucky or unlucky grant offer.
    random.seed(20261008)
    elements = {id_: FakeElement(id_) for id_ in ELEMENT_IDS}
    for id_ in INITIALLY_DISABLED_IDS:
        elements[id_].disabled = True
    timers = FakeTimers()
    _install_pyodide_fakes(elements, timers)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py
    # A seed that offers no surprise grant in its first 40 rounds, so the older tests (which count rounds
    # and funds exactly) never meet one; the grant tests set their own seeds.
    module.state.seed = QUIET_SEED

    yield GameEnv(module, elements, timers)

    _remove_pyodide_fakes()
