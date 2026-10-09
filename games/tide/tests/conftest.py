import importlib.util
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

CATEGORIES = ["output", "reduction", "adaptation"]

ELEMENT_IDS = [
    "season-display",
    "funds-display",
    "acidity-display",
    "acidity-past-display",
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
    "sea-level-wave-cue",
    "ticker-log",
    "coastline-before-grid",
    "coastline-now-grid",
    "coastline-now-label",
    "advance-season-button",
    "info-page-toggle-button",
    "info-page-panel",
    "info-page-framing",
    "info-page-tie-in",
    "info-page-sources",
    # Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md).
    "achievements-toggle-button",
    "achievements-panel",
    "achievement-toast",
    # "What's New" changelog panel (site-wide goal, origin K16).
    "changelog-toggle-button",
    "changelog-panel",
    # D7: end-of-session summary.
    "session-summary-toggle-button",
    "session-summary-panel",
    "session-summary-text",
    "net-funds-chip",
    "scene-theme-select",
    "critter-seal",
    "critter-whale",
    "harbor-quip",
    "sightings-list",
    "storm-bell",
    "rewind-button",
    "ironman-badge",
    "tin-hat-badge",
    "speedrun-display",
    "balance-display",
    "domino-display",
    "rescue-burst",
    "season-report-card",
    "quiet-seasons-display",
    "afford-pinned",
    "afford-pin-select",
    "afford-list",
    "goal-select",
    "goal-bar",
    "goal-text",
    "roll-name-button",
    # D16: output-mix sub-choice.
    "output-mix-select",
    # D9: harder-lag difficulty toggle.
    "hard-lag-toggle-button",
    "sister-enable-button",
    "sister-display",
    # D18: player-chosen comparison baseline.
    "set-baseline-button",
    "coastline-before-label",
    # D3/D4/D6/D12/D13/D14/D15/D5 misc readouts.
    "next-flood-display",
    "worst-season-display",
    "then-vs-now-display",
    "counterfactual-display",
    "best-coastline-display",
    "acidity-fish-graph",
    "ticker-history-list",
    "fish-warning-banner",
    "fish-recovery-banner",
    "seasons-survived-display",
    "sea-scenario-select",
    "then-vs-now-graph",
    "output-mix-preview",
    "adaptation-tier-badge",
    # D7 / D8 / D29.
    "delayed-consequence-graph",
    "delayed-consequence-text",
    "tide-indicator",
    "settlement-heading",
    "settlement-name-input",
    "settlement-chronicle",
    # D17 / D21 / D13.
    "heritage-status-0",
    "heritage-protect-0",
    "heritage-status-1",
    "heritage-protect-1",
    "monitor-button",
    "monitor-log",
    "storm-toggle-button",
    "storm-forecast",
    # D1 / D5+D15 / D11 / D27.
    "retreat-button",
    "retreat-status",
    "population-display",
    "diversify-tourism-button",
    "diversify-aquaculture-button",
    "diversify-status",
    "checkpoint-button",
    "replay-button",
    "checkpoint-status",
    "foresight-display",
    # 2026-10-07 pass: ledger, announcer, x5, ticker filters, copy as text.
    "ledger-toggle-button",
    "ledger-panel",
    "ledger-summary",
    "ledger-body",
    "season-announcer",
    "coastline-description",
    "advance-x5-button",
    "advance-x5-note",
    "ticker-filter-status",
    "ticker-search-input",
    "copy-text-button",
    "copy-text-status",
    "copy-text-area",
    # 2026-10-08 pass: graph controls, scrubber, library, almanac, planner.
    "graph-markers-toggle",
    "scrub-section",
    "scrub-slider",
    "scrub-readout",
    "scrub-live-button",
    "library-toggle-button",
    "library-panel",
    "library-save-button",
    "library-status",
    "library-list",
    "library-select-a",
    "library-select-b",
    "library-overlay-select",
    "library-compare-graph",
    "library-compare-caption",
    "almanac-toggle-button",
    "almanac-panel",
    "almanac-lifetime",
    "almanac-best-body",
    "planner-toggle-button",
    "planner-panel",
    "planner-length",
    "planner-body",
    "planner-chart",
    "planner-summary",
    "planner-commit-button",
    "planner-clear-button",
]
for _key in ("10", "20", "all"):
    ELEMENT_IDS.append(f"graph-range-{_key}")
for _n in range(1, 6):
    ELEMENT_IDS.append(f"planner-row-{_n}")
    for _c in ("output", "reduction", "adaptation"):
        ELEMENT_IDS.append(f"planner-s{_n}-{_c}")
LEDGER_KEYS = [
    "season", "funds", "acidity", "fish_yield", "damage", "rows_dry", "population", "tier", "invested",
]
for _key in LEDGER_KEYS:
    ELEMENT_IDS += [f"ledger-sort-{_key}", f"ledger-th-{_key}", f"ledger-chart-{_key}"]
for _key in ("all", "fish", "sea", "economy", "storm", "chronicle"):
    ELEMENT_IDS.append(f"ticker-filter-{_key}")
for _category in CATEGORIES:
    ELEMENT_IDS += [f"{_category}-count", f"{_category}-invest-button"]

INITIALLY_DISABLED_IDS = [f"{c}-invest-button" for c in CATEGORIES]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

    @property
    def state(self):
        return self.module.state

    def invest(self, category):
        self.elements[f"{category}-invest-button"].dispatch("click", None)

    def advance_season(self):
        self.elements["advance-season-button"].dispatch("click", None)

    def toggle_info_page(self):
        self.elements["info-page-toggle-button"].dispatch("click", None)

    def toggle_achievements(self):
        self.elements["achievements-toggle-button"].dispatch("click", None)

    def toggle_changelog(self):
        self.elements["changelog-toggle-button"].dispatch("click", None)

    def toggle_session_summary(self):
        self.elements["session-summary-toggle-button"].dispatch("click", None)

    def toggle_hard_lag(self):
        self.elements["hard-lag-toggle-button"].dispatch("click", None)

    def advance_x5(self):
        self.elements["advance-x5-button"].dispatch("click", None)

    def toggle_ledger(self):
        self.elements["ledger-toggle-button"].dispatch("click", None)

    def set_baseline(self):
        self.elements["set-baseline-button"].dispatch("click", None)

    def set_output_mix(self, value):
        """Sets the <select>'s value then fires a change event whose
        `.target` is the select itself, same pattern Canopy's own
        on_grid_size_change() integration test helper uses."""
        select = self.elements["output-mix-select"]
        select.value = value

        class _FakeChangeEvent:
            pass

        event = _FakeChangeEvent()
        event.target = select
        select.dispatch("change", event)


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
    test gets its own module object (and its own SettlementState) rather
    than sharing state via Python's normal import cache.
    """
    elements = {}
    for id_ in ELEMENT_IDS:
        FakeElement(id_, registry=elements)
    for id_ in INITIALLY_DISABLED_IDS:
        elements[id_].disabled = True
    timers = FakeTimers()
    _install_pyodide_fakes(elements, timers)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements, timers)

    _remove_pyodide_fakes()
