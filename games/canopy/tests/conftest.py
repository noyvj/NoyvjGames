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

GRID_ROWS = 6
GRID_COLS = 6

# Statically-declared element IDs, wired up in index.html's initial markup.
# Plot tiles ("plot-0", "plot-1", ...) are NOT in this list — game.py
# creates them dynamically via document.createElement on each render, and
# FakeDocument.createElement registers them into `elements` as soon as
# their `.id` is assigned (see fakes.py).
ELEMENT_IDS = [
    "plot-grid",
    "selected-plot-state",
    "clear-button",
    "replant-button",
    "income-display",
    "standing-value-display",
    "biodiversity-display",
    "comparison-message",
    "state-breakdown-display",
    "community-relations-display",
    "personal-best-display",
    "legacy-bonus-display",
    "stakeholder-panel",
    "stakeholder-message",
    "stakeholder-grant-button",
    "stakeholder-decline-button",
    "info-page-toggle-button",
    "info-page-panel",
    "info-page-framing",
    "info-page-tie-in",
    "info-page-sources",
    "achievements-toggle-button",
    "achievements-panel",
    "achievement-toast",
    # "What's New" changelog panel (site-wide goal, origin K16)
    "changelog-toggle-button",
    "changelog-panel",
    # W2-canopy: sourced real-world note
    "real-world-note",
    "real-world-text",
    "real-world-source",
    "example-toggle-button",
    "example-panel",
    "reset-session-button",
    "grid-size-select",
    "difficulty-select",
    "session-summary-toggle-button",
    "session-summary-panel",
    "session-summary-counterfactual",
    "session-summary-sparkline",
    "session-summary-share-text",
    "session-summary-playstyle-comparison",
    "save-playstyle-run-a-button",
    "save-playstyle-run-b-button",
    "adopt-plot-button",
    "specialist-row",
    "specialize-economic-button",
    "specialize-biodiversity-button",
    "adopted-plot-panel",
    "session-summary-badge",
    "report-card-biodiversity",
    "report-card-standing",
    "report-card-relations",
    "forest-history-list",
    "wildlife-log-list",
    "highland-lock-banner",
    "highland-unlock-progress",
    "soil-hint",
    "stakeholder-badge",
    "highland-section",
    "highland-plot-grid",
    "highland-income-display",
    "highland-standing-value-display",
    "highland-selected-plot-state",
    "highland-clear-button",
    "highland-replant-button",
    "wetland-lock-banner",
    "wetland-unlock-progress",
    "wetland-section",
    "wetland-plot-grid",
    "wetland-flood-status",
    "wetland-income-display",
    "wetland-standing-value-display",
    "wetland-selected-plot-state",
    "wetland-clear-button",
    "wetland-replant-button",
    # GB batch 1: season indicator, tier title, Tend, undo, names, Almanac
    "season-indicator",
    "season-text",
    "weather-text",
    "perfect-streak-text",
    "forest-visual",
    "forest-title-display",
    "tend-button",
    "tend-status",
    "undo-clear-button",
    "forest-name-input",
    "plot-nickname-input",
    "almanac-toggle-button",
    "almanac-panel",
    # GB batch 2: forecast, challenge, contracts, announcer, request pace
    "season-forecast",
    "stakeholder-counter-button",
    "perf-indicator",
    "coach-hints-panel",
    "coach-hints",
    "coach-dismiss",
    "forest-card-download",
    "scenario-select",
    "scenario-best-display",
    "lifetime-stats-table",
    "plot-note-input",
    "plot-note-save",
    "request-history-table",
    "request-history-sort",
    "request-history-kind",
    "away-chip",
    "challenge-status",
    "challenge-select",
    "request-pace-select",
    "contracts-toggle-button",
    "contracts-panel",
    "sr-announcer",
    # GB batch 3: level select, Seed Vault, level box
    "levels-open-button",
    "vault-toggle-button",
    "vault-panel",
    "vault-summary",
    "vault-crews",
    "vault-note",
    "vault-tree",
    "level-box",
    "level-status",
    "spirit-line",
    "level-leave-button",
]

# Buttons that carry the `disabled` attribute in index.html's initial markup
# (they read "Loading..." until Pyodide finishes and setup() enables/disables
# them based on real game state).
INITIALLY_DISABLED_IDS = [
    "clear-button",
    "replant-button",
    "stakeholder-grant-button",
    "stakeholder-decline-button",
    "highland-clear-button",
    "highland-replant-button",
    "wetland-clear-button",
    "wetland-replant-button",
    "tend-button",
    "plot-nickname-input",
]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM/timers."""

    def __init__(self, module, elements, timers, local_storage=None):
        self.module = module
        self.elements = elements
        self.timers = timers
        self.local_storage = local_storage

    def plot(self, index):
        return self.module.plots[index]

    @property
    def total_income(self):
        return self.module.total_income

    def select(self, index):
        self.module.select_plot(index)

    def select_tile_click(self, index):
        """Clicks the rendered tile element for a plot, same path a real
        player click takes (as opposed to calling select_plot directly)."""
        self.elements[f"plot-{index}"].dispatch("click", None)

    def clear(self):
        self.elements["clear-button"].dispatch("click", None)

    def replant(self):
        self.elements["replant-button"].dispatch("click", None)

    def grant_stakeholder(self):
        self.elements["stakeholder-grant-button"].dispatch("click", None)

    def decline_stakeholder(self):
        self.elements["stakeholder-decline-button"].dispatch("click", None)

    def tick(self, times=1):
        self.timers.tick_intervals(times)

    def toggle_info_page(self):
        self.elements["info-page-toggle-button"].dispatch("click", None)

    def toggle_achievements(self):
        self.elements["achievements-toggle-button"].dispatch("click", None)

    def toggle_changelog(self):
        self.elements["changelog-toggle-button"].dispatch("click", None)

    def toggle_almanac(self):
        self.elements["almanac-toggle-button"].dispatch("click", None)

    def toggle_session_summary(self):
        self.elements["session-summary-toggle-button"].dispatch("click", None)

    def save_playstyle_run_a(self):
        self.elements["save-playstyle-run-a-button"].dispatch("click", None)

    def save_playstyle_run_b(self):
        self.elements["save-playstyle-run-b-button"].dispatch("click", None)

    def highland_plot(self, index):
        return self.module.highland_plots[index]

    def highland_select(self, index):
        self.module.highland_select_plot(index)

    def highland_select_tile_click(self, index):
        self.elements[f"highland-plot-{index}"].dispatch("click", None)

    def highland_clear(self):
        self.elements["highland-clear-button"].dispatch("click", None)

    def highland_replant(self):
        self.elements["highland-replant-button"].dispatch("click", None)

    def reset_session(self):
        """Clicks Reset Session. The harness has no shared ConfirmDialog, so
        (like every game's confirm helper) the reset happens at once."""
        self.elements["reset-session-button"].dispatch("click", None)

    def change_difficulty(self, value):
        select = self.elements["difficulty-select"]
        select.value = value

        class _FakeChangeEvent:
            pass

        event = _FakeChangeEvent()
        event.target = select
        select.dispatch("change", event)

    def change_challenge(self, value):
        self._change_select("challenge-select", value)

    def change_pace(self, value):
        self._change_select("request-pace-select", value)

    def _change_select(self, element_id, value):
        select = self.elements[element_id]
        select.value = value

        class _FakeChangeEvent:
            pass

        event = _FakeChangeEvent()
        event.target = select
        select.dispatch("change", event)

    def toggle_contracts(self):
        self.elements["contracts-toggle-button"].dispatch("click", None)

    def set_pref(self, key, value):
        """Sets one of settings.js's per-browser display options in the fake localStorage."""
        self.local_storage.setItem(key, value)

    def change_grid_size(self, value):
        """Mirrors a real <select> "change" event: sets the element's own
        `.value` (what a browser does natively before dispatching change)
        then fires a change event whose `.target` is the select itself, so
        game.py's on_grid_size_change() can read `event.target.value` the
        same way it would from a real DOM event."""
        select = self.elements["grid-size-select"]
        select.value = value

        class _FakeChangeEvent:
            pass

        event = _FakeChangeEvent()
        event.target = select
        select.dispatch("change", event)


def _install_pyodide_fakes(elements, timers, local_storage):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
    fake_js.setTimeout = timers.setTimeout
    fake_js.setInterval = timers.setInterval
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


@pytest.fixture
def game_env():
    """Loads a brand-new game.py module against a fresh fake DOM.

    game.py runs setup() as a module-level side effect on import, so every
    test gets its own module object (and its own plot grid) rather than
    sharing state via Python's normal import cache.
    """
    elements = {}
    for id_ in ELEMENT_IDS:
        FakeElement(id_, registry=elements)
    for id_ in INITIALLY_DISABLED_IDS:
        elements[id_].disabled = True
    timers = FakeTimers()
    local_storage = FakeLocalStorage()
    _install_pyodide_fakes(elements, timers, local_storage)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements, timers, local_storage)

    _remove_pyodide_fakes()


class FakeConfirmDialog:
    """Stands in for shared/confirm-dialog.js's window.ConfirmDialog: records
    each ask() and lets a test press Confirm or Cancel."""

    def __init__(self):
        self.asks = []

    def ask(self, id=None, message=None, confirmLabel=None, allowSkip=True, onConfirm=None, **_):
        self.asks.append({
            "id": id, "message": message, "confirmLabel": confirmLabel,
            "allowSkip": allowSkip, "onConfirm": onConfirm,
        })

    def confirm(self):
        ask = self.asks.pop()
        ask["onConfirm"]()

    def cancel(self):
        self.asks.pop()


@pytest.fixture
def fake_confirm_dialog(game_env):
    """Installs a fake window.ConfirmDialog into the fake `js` module (game.py
    reads it lazily with `from js import window`)."""
    dialog = FakeConfirmDialog()
    sys.modules["js"].window = types.SimpleNamespace(ConfirmDialog=dialog)
    return dialog
