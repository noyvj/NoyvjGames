import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeConfirm, FakeDocument, FakeElement, FakeNavigator, FakeTimers, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"
# game.py imports the batch B modules (wf_*.py), which index.html writes into Pyodide's file system.
sys.path.insert(0, str(GAME_PY.parent))

ELEMENT_IDS = [
    "components-body",
    "resources-body",
    "component-progress",
    "progress-bar",
    "summary",
    "refinery-summary",
    "route-planner",
    "syndicate-summary",
    "market-summary",
    "farm-log-text",
    "combo-compare",
    "combo-name-input",
    "combo-parts-input",
    "combo-add-button",
    "combo-remove-input",
    "combo-remove-button",
    "combo-message",
    "clear-farm-log-button",
    "status-message",
    "reset-button",
    "toast",
    "data-updated",
    "category-progress",
    "blocking-summary",
    "search-input",
    "sort-select",
    "hide-complete-toggle",
    "shopping-text",
    "copy-shopping-button",
    "shortcut-help-button",
    "week-section",
    "week-pins",
    "week-pin-input",
    "week-pin-button",
    "week-message",
    "recent-completed",
    "build-names-list",
    "tag-filter-select",
    "budget-summary",
    "budget-credits-input",
    "budget-endo-input",
    "shopping-details",
    "wishlist-text",
    "copy-wishlist-button",
    "tools-section",
    "timer-name-input",
    "timer-start-input",
    "timer-duration-input",
    "timer-ready-input",
    "timer-notify-check",
    "timer-add-button",
    "timer-notify-button",
    "timer-message",
    "timer-hint",
    "timer-list",
    "mastery-base-input",
    "mastery-summary",
    "mastery-name-input",
    "mastery-type-select",
    "mastery-add-button",
    "mastery-message",
    "mastery-list",
    "trader-date-input",
    "trader-reminder",
    "trader-item-input",
    "trader-add-button",
    "trader-message",
    "trader-list",
    "checklist-reset-info",
    "checklist-name-input",
    "checklist-kind-select",
    "checklist-add-button",
    "checklist-message",
    "checklist-daily",
    "checklist-weekly",
    "history-snapshot-button",
    "history-clear-button",
    "history-chart",
    "history-summary",
    "goal-input",
    "goal-add-button",
    "goal-message",
    "goal-list",
    "share-export-text",
    "share-copy-button",
    "share-import-input",
    "share-import-button",
    "share-result",
    "tag-legend",
    "tag-label-input",
    "tag-add-label-button",
    "tag-remove-label-button",
    "tag-name-input",
    "tag-assign-select",
    "tag-assign-button",
    "tag-clear-button",
    "tag-message",
    "loadout-name-input",
    "loadout-mods-input",
    "loadout-play-input",
    "loadout-save-button",
    "loadout-message",
    "loadout-list",
    "edit-log-text",
    "clear-edit-log-button",
    "shortcut-overlay",
    "shortcut-list",
    "shortcut-close-button",
    "adv-section",
    "meta-select", "meta-bar", "meta-text",
    "session-text",
    "relic-source", "relic-want-input", "relic-want-add-button", "relic-want-remove-button",
    "relic-owned-name-input", "relic-owned-count-input", "relic-owned-set-button",
    "relic-custom-name-input", "relic-custom-parts-input", "relic-custom-unvaulted-check",
    "relic-custom-add-button", "relic-custom-remove-button", "relic-message", "relic-plan",
    "relic-part-list", "relic-name-list",
    "craft-import-note", "craft-name-input", "craft-kind-select", "craft-add-button",
    "craft-need-item-input", "craft-need-name-input", "craft-need-qty-input", "craft-need-add-button",
    "craft-message", "craft-list", "craft-name-list",
    "forma-build-input", "forma-current-input", "forma-wanted-input", "forma-add-button",
    "forma-have-input", "forma-used-input", "forma-message", "forma-total", "forma-note",
    "forma-list", "forma-target-list",
    "pet-facts", "pet-name-input", "pet-kind-select", "pet-imprints-input", "pet-mods-input",
    "pet-note-input", "pet-add-button", "pet-message", "pet-list",
    "diff-text", "audit-list",
    "ready-score", "ready-breakdown", "ready-mod-name-input", "ready-mod-rank-input",
    "ready-mod-max-input", "ready-mod-add-button", "ready-message", "ready-mod-list",
    "tips-summary", "tips-list",
]

# The planner-tools tabs: one button and one panel each.
for _key in ("timers", "mastery", "trader", "dailies", "history", "goals", "share", "tags", "notes", "log"):
    ELEMENT_IDS += [f"tab-btn-{_key}", f"tab-{_key}"]

# The batch B "Deeper planners" tabs.
for _key in ("meta", "session", "relics", "crafts", "forma", "pets", "diff", "audit", "ready", "tips"):
    ELEMENT_IDS += [f"adv-btn-{_key}", f"adv-{_key}"]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements, confirm_fn):
        self.module = module
        self.elements = elements
        self.confirm = confirm_fn

    @property
    def js(self):
        return sys.modules["js"]

    def reset(self):
        self.elements["reset-button"].dispatch("click", None)


def _install_pyodide_fakes(elements, confirm_fn):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
    fake_js.confirm = confirm_fn
    fake_js.navigator = FakeNavigator()
    fake_js.timers = FakeTimers()
    fake_js.setTimeout = fake_js.timers.set_timeout
    fake_js.clearTimeout = fake_js.timers.clear_timeout

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
    test gets its own module object (and its own `state` dict) rather than
    sharing state via Python's normal import cache.
    """
    elements = {}
    for id_ in ELEMENT_IDS:
        el = FakeElement(registry=elements)
        el.id = id_
    elements["sort-select"].value = "category"
    elements["hide-complete-toggle"].checked = False
    elements["toast"].hidden = True

    confirm_fn = FakeConfirm()
    _install_pyodide_fakes(elements, confirm_fn)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements, confirm_fn)

    _remove_pyodide_fakes()
