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
    "automated-meter",
    "automated-bar",
    "practice-score-display",
    "stage-summary-display",
    "row-summary-display",
    "combo-display",
    "cultural-notes-toggle-button",
    "cultural-notes-panel",
    "dashboard-toggle-button",
    "dashboard-panel",
    "srs-explainer",
    "srs-explainer-body",
    "liaison-toggle-button",
    "liaison-panel",
    "liaison-progress",
    "liaison-context",
    "liaison-instruction",
    "liaison-prompt",
    "liaison-legend",
    "liaison-choices",
    "liaison-feedback",
    "liaison-explanation",
    "liaison-summary",
    "liaison-next-button",
    "liaison-close-button",
    "achievements-toggle-button",
    "achievements-panel",
    "achievement-toast",
    "changelog-toggle-button",
    "changelog-panel",
    "blitz-toggle-button",
    "blitz-panel",
    "blitz-lock-message",
    "blitz-time-display",
    "blitz-lives-display",
    "blitz-score-display",
    "blitz-combo-display",
    "blitz-start-button",
    "blitz-summary",
    "blitz-context",
    "blitz-prompt",
    "blitz-choices",
    "blitz-feedback",
    "blitz-close-button",
    "racer-toggle-button",
    "racer-panel",
    "racer-lock-message",
    "racer-player-marker",
    "racer-rival-marker",
    "racer-progress-display",
    "racer-start-button",
    "racer-summary",
    "racer-context",
    "racer-prompt",
    "racer-choices",
    "racer-feedback",
    "racer-close-button",
    "boutique-toggle-button",
    "boutique-panel",
    "boutique-lock-message",
    "boutique-served-display",
    "boutique-missed-display",
    "boutique-score-display",
    "boutique-patience-fill",
    "boutique-start-button",
    "boutique-summary",
    "boutique-order",
    "boutique-options",
    "boutique-feedback",
    "boutique-close-button",
    "cafe-toggle-button",
    "cafe-panel",
    "cafe-lock-message",
    "cafe-served-display",
    "cafe-missed-display",
    "cafe-score-display",
    "cafe-patience-fill",
    "cafe-start-button",
    "cafe-summary",
    "cafe-order",
    "cafe-options",
    "cafe-feedback",
    "cafe-twist-panel",
    "cafe-twist-context",
    "cafe-twist-prompt",
    "cafe-twist-choices",
    "cafe-close-button",
    "practice-panel",
    "practice-confidence",
    "practice-confidence-stats",
    "gender-accuracy-display",
    "practice-confidence-sure-button",
    "practice-confidence-unsure-button",
    "practice-context",
    "practice-instruction",
    "practice-prompt",
    "practice-note",
    "practice-choices",
    "practice-answer-input",
    "practice-submit-button",
    "practice-feedback",
    "practice-next-button",
    "practice-blurb",
    "practice-blurb-what",
    "practice-blurb-tip",
    "practice-blurb-why",
    "practice-report-button",
    "practice-pronunciation-note",
    "practice-pronunciation-report-button",
    "practice-close-button",
    "water-next-button",
    "next-day-button",
    "legend",
    "accent-toggle-checkbox",
    "review-toggle-button",
    "review-controls",
    "review-count-input",
    "review-min-stage-select",
    "review-word-button",
    "review-grammar-button",
    "review-marathon-button",
    "review-empty-message",
    "review-panel",
    "review-progress",
    "review-context",
    "review-instruction",
    "review-prompt",
    "review-note",
    "review-choices",
    "review-answer-input",
    "review-submit-button",
    "review-feedback",
    "review-next-button",
    "review-summary",
    "review-close-button",
    "review-report-button",
    "review-pronunciation-report-button",
    "proficiency-panel",
    "proficiency-progress",
    "proficiency-context",
    "proficiency-instruction",
    "proficiency-prompt",
    "proficiency-note",
    "proficiency-choices",
    "proficiency-answer-input",
    "proficiency-submit-button",
    "proficiency-feedback",
    "proficiency-next-button",
    "proficiency-summary",
    "proficiency-topic-breakdown",
    "proficiency-close-button",
    "proficiency-report-button",
    "proficiency-pronunciation-report-button",
    "bonus-panel",
    "bonus-progress",
    "bonus-order-section",
    "bonus-tile-pool",
    "bonus-tile-placed",
    "bonus-order-feedback",
    "bonus-order-continue-button",
    "bonus-tiles-section",
    "bonus-tile-progress",
    "bonus-tile-prompt",
    "bonus-tile-answer-input",
    "bonus-tile-submit-button",
    "bonus-tile-feedback",
    "bonus-tile-next-button",
    "bonus-tile-report-button",
    "bonus-tile-pronunciation-report-button",
    "bonus-sentence-section",
    "bonus-sentence-prompt",
    "bonus-sentence-answer-input",
    "bonus-sentence-submit-button",
    "bonus-sentence-feedback",
    "bonus-sentence-next-button",
    "bonus-sentence-report-button",
    "bonus-sentence-pronunciation-report-button",
    "bonus-summary",
    "bonus-close-button",
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
    # "minigames" is a real file-based import (game.py's own `import
    # minigames` statement, see Milestone 27's build note), not the
    # exec_module-loaded "game" module below -- left cached in sys.modules,
    # it would keep the *same* minigames module object (and all its
    # module-level session state: blitz_open, cached candidate pools, etc.)
    # alive across every test in this file, silently leaking state from one
    # test's farm into the next. Popping it here gives every test a
    # genuinely fresh minigames module, exactly like "game" already gets.
    for name in ("js", "pyodide", "pyodide.ffi", "game", "minigames"):
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
