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

ELEMENT_IDS = [
    "chain-flow",
    "stage-extract",
    "stage-discard",
    "chain-flow-message",
    "cycle-display",
    "funds-display",
    "extraction-display",
    "production-display",
    "total-extracted-display",
    "damage-display",
    "damage-bar",
    "circular-fraction-display",
    "lifetime-circular-display",
    "circular-bar",
    "score-display",
    "trend-display",
    "real-world-comparison-display",
    "return-flow-row",
    "import-flow-row",
    "vignette-display",
    "trade-network-display",
    "trade-link-count",
    "trade-link-invest-button",
    "advance-cycle-button",
    "repair-name",
    "repair-count",
    "repair-invest-button",
    "reuse-name",
    "reuse-count",
    "reuse-invest-button",
    "recycle-name",
    "recycle-count",
    "recycle-invest-button",
    "info-page-toggle-button",
    "info-page-panel",
    "info-page-framing",
    "info-page-tie-in",
    "info-page-sources",
    "achievements-toggle-button",
    "achievements-panel",
    "achievement-toast",
    "achievement-toast-text",
    # K16: "What's New" changelog panel.
    "changelog-toggle-button",
    "changelog-panel",
    "loop-closed-banner",
    "goods-category-picker",
    "goods-category-electronics-button",
    "goods-category-clothing-button",
    "goods-category-furniture-button",
    "reset-chain-button",
    "regional-trade-count",
    "regional-trade-invest-button",
    "repair-stats",
    "reuse-stats",
    "recycle-stats",
    "loop-ring-node-repair",
    "loop-ring-node-reuse",
    "loop-ring-node-recycle",
    "score-breakdown-display",
    "loop-projection-display",
    "sector-comparison-display",
    "streak-display",
]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

    @property
    def chain(self):
        return self.module.chain

    def advance_cycle(self):
        self.elements["advance-cycle-button"].dispatch("click", None)

    def toggle_info_page(self):
        self.elements["info-page-toggle-button"].dispatch("click", None)

    def toggle_achievements(self):
        self.elements["achievements-toggle-button"].dispatch("click", None)

    def toggle_changelog(self):
        self.elements["changelog-toggle-button"].dispatch("click", None)

    def invest_trade_link(self):
        self.elements["trade-link-invest-button"].dispatch("click", None)

    def invest_regional_trade(self):
        self.elements["regional-trade-invest-button"].dispatch("click", None)

    def invest_circularity(self, measure):
        self.elements[f"{measure}-invest-button"].dispatch("click", None)

    def reset_chain(self):
        self.elements["reset-chain-button"].dispatch("click", None)

    def select_goods_category(self, category):
        self.elements[f"goods-category-{category}-button"].dispatch("click", None)


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
    test gets its own module object (and its own ChainState) rather than
    sharing state via Python's normal import cache.
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
