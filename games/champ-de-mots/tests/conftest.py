import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, create_proxy

GAME_DIR = Path(__file__).resolve().parent.parent
GAME_PY = GAME_DIR / "game.py"
CATALOG_PATH = GAME_DIR / "fren_combined_catalog.json"

# Z11: game.py imports the shared narrative-log widget (shared/
# narrative_log.py) the same way the real Pyodide boot script does (see
# index.html) and the same way Continuum's/Thaw's own tests already do --
# so the repo-root shared/ directory has to be importable before game.py
# can be exec'd.
SHARED_DIR = GAME_DIR.parent.parent / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

# The page's boot script fetches the catalog and hands it to Python as a
# window global before running game.py (see index.html); the fake `js`
# module below stands in for that, so tests exercise the real 966-item
# catalog rather than a stub.
CATALOG_JSON = CATALOG_PATH.read_text(encoding="utf-8")

# FS (FREN152 slides) additions: topics whose id carries "-fs" were added after the original
# 23-week catalogue. The original counts are fixed here; every added topic is counted from the
# catalogue itself, so the farm's headline numbers may grow without a test pinning an old size.
BASE_COUNTS = {"weeks": 23, "topics": 138, "items": 1047, "plots": 790}


def catalog_counts():
    import json

    weeks = json.loads(CATALOG_JSON)["weeks"]
    topics = [t for w in weeks for t in w["topics"]]
    plots = sum(1 if t["topic_type"] == "grammar" else len(t["items"]) for t in topics)
    return {
        "weeks": len(weeks),
        "topics": len(topics),
        "items": sum(len(t["items"]) for t in topics),
        "plots": plots,
    }


ELEMENT_IDS = [
    "farm",
    "semester-summary",
    "legend-panel",
    "legend-toggle-button",
    "farm-legend-button",
    "growth-marker-practice",
    "growth-marker-review",
    "growth-marker-proficiency",
    "growth-marker-bonus",
    "growth-marker-builder",
    "growth-marker-conversation",
    "growth-marker-listening",
    "growth-marker-liaison",
    "growth-marker-placement",
    "growth-marker-blitz",
    "growth-marker-racer",
    "growth-marker-sprint",
    "growth-marker-boutique",
    "growth-marker-cafe",
    "golden-display",
    "coins-display",
    "shop-toggle-button",
    "shop-panel",
    "shop-close-button",
    "shop-coins-line",
    "shop-source-line",
    "shop-progress-line",
    "shop-list",
    "quest-display",
    "practice-slip-button",
    "practice-slip-note",
    "practice-leech",
    "practice-leech-what",
    "practice-leech-pieces",
    "practice-leech-hook",
    "practice-leech-rest-button",
    "farm-controls",
    "accent-bar-practice",
    "accent-bar-review",
    "accent-bar-proficiency",
    "accent-bar-placement",
    "accent-bar-bonus-tile",
    "accent-bar-bonus-sentence",
    "farm-filter-select",
    "farm-sort-select",
    "farm-filter-count",
    "day-display",
    "due-display",
    "pace-display",
    "progress-display",
    "automated-meter",
    "automated-bar",
    "practice-score-display",
    "player-title-display",
    "study-buddy-toggle-button",
    "study-buddy-display",
    "stage-summary-display",
    "row-summary-display",
    "combo-display",
    "cultural-notes-toggle-button",
    "cultural-notes-panel",
    "dashboard-toggle-button",
    "calendar-toggle-button",
    "phrasebook-toggle-button",
    "phrasebook-panel",
    "phrasebook-list",
    "phrasebook-practice-button",
    "practice-bookmark-button",
    "practice-deepdive-button",
    "practice-deepdive",
    "review-bookmark-button",
    "calendar-panel",
    "calendar-prev-button",
    "calendar-next-button",
    "calendar-month-label",
    "calendar-grid",
    "calendar-summary",
    "planner-toggle-button",
    "planner-panel",
    "planner-date-input",
    "planner-clear-button",
    "planner-default-button",
    "planner-minutes-input",
    "planner-minutes-label",
    "planner-summary",
    "planner-projection",
    "planner-suggestion",
    "exam-countdown-tile",
    "exam-countdown-display",
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
    "report-log-toggle-button",
    "report-log-panel",
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
    "sprint-toggle-button",
    "sprint-panel",
    "sprint-lock-message",
    "sprint-time-display",
    "sprint-lives-display",
    "sprint-score-display",
    "sprint-combo-display",
    "sprint-start-button",
    "sprint-summary",
    "sprint-context",
    "sprint-prompt",
    "sprint-choices",
    "sprint-feedback",
    "sprint-close-button",
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
    "quick-water-button",
    "sentence-builder-button",
    "conversation-button",
    "formats-button",
    "growth-marker-formats",
    "formats-panel",
    "formats-progress",
    "formats-picker",
    "formats-card",
    "formats-instruction",
    "formats-context",
    "formats-clock",
    "formats-prompt",
    "formats-choices",
    "formats-typed-row",
    "formats-input",
    "formats-submit-button",
    "formats-feedback",
    "formats-next-button",
    "formats-summary",
    "formats-close-button",
    "listening-button",
    "listening-panel",
    "listening-progress",
    "listening-empty-message",
    "listening-card",
    "listening-play-button",
    "listening-slow-button",
    "listening-choices",
    "listening-feedback",
    "listening-next-button",
    "listening-summary",
    "listening-close-button",
    "conversation-panel",
    "conversation-title",
    "conversation-progress",
    "conversation-empty-message",
    "conversation-card",
    "conversation-line",
    "conversation-gloss",
    "conversation-choices",
    "conversation-feedback",
    "conversation-next-button",
    "conversation-summary",
    "conversation-close-button",
    "placement-button",
    "placement-hint",
    "placement-panel",
    "placement-intro",
    "placement-start-button",
    "placement-card",
    "placement-progress",
    "placement-context",
    "placement-instruction",
    "placement-prompt",
    "placement-note",
    "placement-choices",
    "placement-answer-input",
    "placement-submit-button",
    "placement-feedback",
    "placement-next-button",
    "placement-summary",
    "placement-bands",
    "placement-plan",
    "placement-status",
    "placement-apply-button",
    "placement-retry-button",
    "placement-cancel-button",
    "placement-close-button",
    "builder-panel",
    "builder-progress",
    "builder-empty-message",
    "builder-card",
    "builder-prompt",
    "builder-placed",
    "builder-pool",
    "builder-feedback",
    "builder-undo-button",
    "builder-next-button",
    "builder-summary",
    "builder-close-button",
    "review-cram-button",
    "review-weakspots-button",
    "review-cram-from-select",
    "review-cram-to-select",
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
    "result-copy-review",
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
    "pairs-toggle-button",
    "gaps-toggle-button",
    "listenpick-toggle-button",
    "wordorder-toggle-button",
    "always-mc-checkbox",
    "format-schedule-note",
    "blitz-difficulty-select",
    "blitz-difficulty-note",
    "blitz-waters",
    "sprint-difficulty-select",
    "sprint-difficulty-note",
    "sprint-waters",
    "pairs-panel",
    "growth-marker-pairs",
    "pairs-difficulty-select",
    "pairs-difficulty-note",
    "pairs-lock-message",
    "pairs-time-display",
    "pairs-lives-display",
    "pairs-score-display",
    "pairs-combo-display",
    "pairs-start-button",
    "pairs-summary",
    "pairs-progress",
    "pairs-waters",
    "pairs-board",
    "pairs-feedback",
    "pairs-close-button",
    "gaps-panel",
    "growth-marker-gaps",
    "gaps-difficulty-select",
    "gaps-difficulty-note",
    "gaps-lock-message",
    "gaps-time-display",
    "gaps-lives-display",
    "gaps-score-display",
    "gaps-combo-display",
    "gaps-start-button",
    "gaps-summary",
    "gaps-context",
    "gaps-prompt",
    "gaps-waters",
    "gaps-choices",
    "gaps-feedback",
    "gaps-close-button",
    "listenpick-panel",
    "growth-marker-listenpick",
    "listenpick-difficulty-select",
    "listenpick-difficulty-note",
    "listenpick-lock-message",
    "listenpick-time-display",
    "listenpick-lives-display",
    "listenpick-score-display",
    "listenpick-combo-display",
    "listenpick-start-button",
    "listenpick-summary",
    "listenpick-context",
    "listenpick-prompt",
    "listenpick-play-button",
    "listenpick-slow-button",
    "listenpick-show-button",
    "listenpick-waters",
    "listenpick-choices",
    "listenpick-feedback",
    "listenpick-close-button",
    "wordorder-panel",
    "growth-marker-wordorder",
    "wordorder-difficulty-select",
    "wordorder-difficulty-note",
    "wordorder-lock-message",
    "wordorder-time-display",
    "wordorder-lives-display",
    "wordorder-score-display",
    "wordorder-combo-display",
    "wordorder-start-button",
    "wordorder-summary",
    "wordorder-prompt",
    "wordorder-waters",
    "wordorder-placed",
    "wordorder-pool",
    "wordorder-undo-button",
    "wordorder-feedback",
    "wordorder-close-button",
    "amis-toggle-button",
    "amis-panel",
    "growth-marker-amis",
    "amis-difficulty-select",
    "amis-difficulty-note",
    "amis-source",
    "amis-source-link",
    "amis-lock-message",
    "amis-time-display",
    "amis-lives-display",
    "amis-score-display",
    "amis-combo-display",
    "amis-start-button",
    "amis-summary",
    "amis-context",
    "amis-prompt",
    "amis-waters",
    "amis-choices",
    "amis-feedback",
    "amis-close-button",
    "racer-difficulty-select",
    "racer-difficulty-note",
    "racer-waters",
    "boutique-difficulty-select",
    "boutique-difficulty-note",
    "boutique-waters",
    "cafe-difficulty-select",
    "cafe-difficulty-note",
    "cafe-waters",
    "cafe-twist-waters",
    "water-options-toggle-button",
    "water-options-panel",
    "water-today-line",
    "water-opt-next-count",
    "water-opt-next-button",
    "water-row-select",
    "water-opt-row-count",
    "water-opt-row-button",
    "water-topic-select",
    "water-opt-topic-count",
    "water-opt-topic-button",
    "water-opt-wilting-count",
    "water-opt-wilting-button",
    "water-opt-mc-count",
    "water-opt-mc-button",
    "water-opt-typed-count",
    "water-opt-typed-button",
    "water-opt-listen-count",
    "water-opt-listen-button",
    "water-games-list",
    "water-options-close-button",
    "practice-water-note",
    "review-listen-button",
    "review-listen-show-button",
    "review-water-note",
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
    for name in ("js", "pyodide", "pyodide.ffi", "game", "minigames", "formats"):
        sys.modules.pop(name, None)


def _load_game_env():
    elements = {id_: FakeElement(id_) for id_ in ELEMENT_IDS}
    _install_pyodide_fakes(elements)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)
    return GameEnv(module, elements)


@pytest.fixture
def progressive_env():
    """Loads a brand-new game.py module with the REAL progressive question
    format (2026-10-08): typed questions appear as a plot grows."""
    env = _load_game_env()
    yield env
    _remove_pyodide_fakes()


@pytest.fixture
def game_env():
    """Loads a brand-new game.py module against a fresh fake DOM.

    game.py runs setup() as a module-level side effect on import, so every
    test gets its own module object (and its own FarmState) rather than
    sharing state via Python's normal import cache.

    Since 2026-10-08 a plot that has grown is asked as a typed question some of
    the time (game.py's progressive format). Most tests grow plots on the way
    to something else (they open a row, water things) and then expect multiple
    choice, so this fixture pins `wants_typed` to False; a test that wants a
    typed question sets `module.wants_typed = lambda plot: True`, and
    test_progressive_format.py uses `progressive_env` for the real schedule.
    """
    env = _load_game_env()
    env.module.wants_typed = lambda plot: False
    yield env
    _remove_pyodide_fakes()
