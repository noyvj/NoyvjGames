import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeTimers, create_proxy

GAME_DIR = Path(__file__).resolve().parent.parent
GAME_PY = GAME_DIR / "game.py"

# game.py is split into trade_*.py modules in the same folder (see "File map" in CLAUDE.md), so the game
# folder has to be importable, the same way the Pyodide boot script (boot.js) writes them next to game.py.
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))
# browser_helpers.py (the browser-test setup) sits in this folder, so a test can write
# `from browser_helpers import open_game`; the `base` fixture is registered below for every test.
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from browser_helpers import base  # noqa: E402,F401  (pytest fixture: the local server for browser tests)
# game.py imports the shared seed module (shared/seed.py, Z-1b), which Pyodide gets from its virtual filesystem.
SHARED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

# J6 — ships 5/6 are purchasable, not present from the start.
SHIP_IDS = ["1", "2", "3", "4", "5", "6"]
PURCHASABLE_SHIP_IDS = ["5", "6"]
COLONY_IDS = ["aurum", "verdant", "ferrum", "cryo", "helion"]
EXPANSION_COLONY_IDS = ["kepler_a", "kepler_b", "kepler_c"]
# J13 — the Rift Colonies, a third self-contained cluster.
RIFT_COLONY_IDS = ["rift_a", "rift_b", "rift_c"]
# J1 — the Umbral Deep, a fourth self-contained cluster.
DEEP_COLONY_IDS = ["deep_a", "deep_b", "deep_c"]
ALL_COLONY_IDS = COLONY_IDS + EXPANSION_COLONY_IDS + RIFT_COLONY_IDS + DEEP_COLONY_IDS

# Statically-declared element IDs, wired up in index.html's initial markup.
ELEMENT_IDS = [
    "profit-display",
    "ghost-note",
    "profit-display-text",
    "sale-spark-container",
    "sale-log",
    "automation-slots-display",
    "map-canvas",
    "research-points-display",
    "fleet-priority-status",
    "fleet-priority-button",
    "expansion-colonies-panel",
    "almanac-body",
    "ship-5-archetype-select",
    "ship-6-archetype-select",
    "seasonal-demand-toggle-button",
    "seasonal-demand-status",
    "diplomacy-status",
    "trade-post-button",
    "trade-post-status",
    "route-hazards-toggle-button",
    "route-insurance-toggle-button",
    "route-hazards-status",
    "run-seed-display",
    "run-seed-input",
    "run-seed-apply-button",
    "run-seed-copy-button",
    "run-seed-note",
    "expansion-market-panel",
    "expansion2-colonies-panel",
    "expansion2-market-panel",
    "expansion3-colonies-panel",
    "expansion3-market-panel",
    "endgame-panel",
    "endgame-message-display",
    "endgame-worlds-display",
    "endgame-galaxy-canvas",
    "legacy-display",
    "guild-panel",
    "guild-status-display",
    "guild-accept-button",
    "guild-decline-button",
    "found-new-corporation-button",
    "hard-charter-toggle-button",
    "charter-renew-preview-display",
    "charter-toggle-button",
    "charter-panel",
    "charter-points-display",
    "charter-founding-display",
    "ledger-units-display",
    "ledger-routes-display",
    "ledger-charters-display",
    "ledger-hard-display",
    "achievements-toggle-button",
    "achievements-panel",
    "achievement-toast",
    "changelog-toggle-button",
    "changelog-panel",
    "summary-toggle-button",
    "summary-panel",
    "summary-copy-result",
    "notice-toast",
    # Batch (J-4..J-31): crest, career log, ribbon, throughput, captains panel.
    "charter-crest",
    "charter-crest-display",
    "charter-career-list",
    "ledger-ribbon",
    "throughput-display",
    "captains-toggle-button",
    "captains-panel",
    "captains-summary-display",
    # Blackout (J-29/J-30).
    "blackout-toggle-button",
    "blackout-buy-feed-button",
    "blackout-buy-chart-button",
    "blackout-status",
    "ledger-dark-display",
    # Market Weather (J-17/J-18).
    "weather-toggle-button",
    "weather-status",
    "news-ticker",
    # Fleet Lab (J-19..J-24).
    "lab-toggle-button",
    "lab-panel",
    "expedition-status",
    "expedition-odds",
    "expedition-curios",
    # Market Desk (J-3, J-11, J-12, J-27, J-28).
    "desk-toggle-button",
    "desk-panel",
    "exchange-status",
    "exchange-controls",
    "exchange-kind-select",
    "exchange-good-select",
    "exchange-pct-select",
    "exchange-add-button",
    "exchange-book",
    # Blueprint Lab (J-19, J-20).
    "bp-status", "bp-controls", "bp-chart", "bp-name-input", "bp-save-button", "bp-reset-button",
    "bp-hold-value", "bp-hold-down-button", "bp-hold-up-button",
    "bp-speed-value", "bp-speed-down-button", "bp-speed-up-button",
    "bp-eff-value", "bp-eff-down-button", "bp-eff-up-button",
]
ELEMENT_IDS += ["hub-status", "hub-clear-button"] + [f"hub-set-{_c}-button" for _c in ALL_COLONY_IDS]
ELEMENT_IDS += ["meridian-toggle-button", "meridian-undercut-button", "meridian-intel-button", "meridian-status",
                "cartel-status", "cartel-controls"]
for _g in (
    "ore", "grain", "machinery", "water", "energy", "rare_metals", "biomass", "isotopes",
    "crystal", "polymer", "antimatter", "neutronium", "superfluid", "aerogel",
):
    ELEMENT_IDS += [f"cartel-{_g}-row", f"cartel-{_g}-text", f"cartel-{_g}-squeeze-button", f"cartel-{_g}-dump-button"]
# Chain Builder (J-5) and the Modes button (GN-17).
ELEMENT_IDS += [
    "chain-toggle-button", "chain-panel", "chain-progress", "chain-status", "chain-pick-button", "chain-leave-button",
    "chain-board", "chain-title", "chain-blurb", "chain-rules", "chain-goals", "chain-goal-0", "chain-goal-1", "chain-goal-2",
    "chain-map", "chain-product-0-tab", "chain-product-1-tab", "chain-p0-block", "chain-p1-block",
    "chain-p0-title", "chain-p1-title", "chain-result", "chain-lock-button", "chain-clear-button", "chain-hint-button",
    "chain-hint-0-text", "chain-hint-1-text", "chain-hint-2-text", "chain-sites-text", "chain-distances-text",
    "modes-open-button",
]
for _p in range(2):
    for _k in range(3):
        ELEMENT_IDS += [f"chain-p{_p}-s{_k}-row", f"chain-p{_p}-s{_k}-label", f"chain-p{_p}-s{_k}-select",
                        f"chain-p{_p}-l{_k}-text", f"chain-p{_p}-l{_k}-down-button", f"chain-p{_p}-l{_k}-up-button"]
ELEMENT_IDS += ["crisis-status", "crisis-restart-button", "crisis-leave-button"]
for _c in ("grain_famine", "isotope_glut", "broken_network"):
    ELEMENT_IDS += [f"crisis-{_c}-text", f"crisis-{_c}-start-button"]
for _i in range(4):
    ELEMENT_IDS += [f"bp-design-{_i}-row", f"bp-design-{_i}-text", f"bp-design-{_i}-delete-button"]
    ELEMENT_IDS += [f"ship-5-bp{_i}-option", f"ship-6-bp{_i}-option"]
for _i in range(5):
    ELEMENT_IDS += [f"exchange-order-{_i}-row", f"exchange-order-{_i}-text", f"exchange-order-{_i}-remove-button"]
for _s in SHIP_IDS:
    ELEMENT_IDS.append(f"expedition-ship-{_s}-button")
CAPTAIN_PERK_IDS = ["frugal", "lucky", "night_owl", "perfectionist"]
for _node_id in (
    "automation_slot", "fast_ships", "hauler", "galaxy_expansion",
    "automation_slot_2", "outer_reaches", "deep_survey", "umbral_reach",
    "auto_efficiency", "auto_efficiency_2", "market_insight", "market_insight_2",
):
    ELEMENT_IDS += [f"research-{_node_id}-status", f"research-{_node_id}-unlock-button"]
# O-1 -- the twelve charter perks.
CHARTER_PERK_IDS = [
    "surveyed_lanes", "waystation_network", "standing_convoy",
    "standing_orders", "lab_automation", "auto_balancers",
    "frontier_grants", "settler_guilds", "charter_colonies",
    "guild_standing", "colonial_goodwill", "trusted_name",
]
for _perk_id in CHARTER_PERK_IDS:
    ELEMENT_IDS += [f"charter-perk-{_perk_id}-status", f"charter-perk-{_perk_id}-buy-button"]
for _perk_id in CAPTAIN_PERK_IDS:
    ELEMENT_IDS += [f"captain-{_perk_id}-status", f"captain-{_perk_id}-quote", f"captain-{_perk_id}-release-button"]
    ELEMENT_IDS += [f"captain-{_perk_id}-ship-{_s}-button" for _s in SHIP_IDS]
for _colony_id in ALL_COLONY_IDS:
    ELEMENT_IDS += [
        f"colony-{_colony_id}-temperament",
        f"colony-{_colony_id}-name",
        f"colony-{_colony_id}-flavor",
        f"colony-{_colony_id}-need-display",
        f"colony-{_colony_id}-need-bar",
        f"colony-{_colony_id}-need-sparkline",
        f"colony-{_colony_id}-invest-button",
        f"colony-{_colony_id}-demand-display",
        f"colony-{_colony_id}-concede-button",
        f"colony-{_colony_id}-development-display",
        f"mobile-needs-strip-{_colony_id}",
    ]
for _good in (
    "ore", "grain", "machinery", "water", "energy",
    "rare_metals", "biomass", "isotopes",
    "crystal", "polymer", "antimatter",
    "neutronium", "superfluid", "aerogel",
):
    ELEMENT_IDS += [f"market-{_good}-display", f"market-{_good}-bar", f"market-{_good}-sparkline"]
    ELEMENT_IDS += [f"stockpile-{_good}-buy-button", f"stockpile-{_good}-sell-button", f"stockpile-{_good}-status"]
for _ship_id in SHIP_IDS:
    ELEMENT_IDS.append(f"ship-{_ship_id}-label")
    ELEMENT_IDS.append(f"ship-{_ship_id}-status")
    ELEMENT_IDS += [f"ship-{_ship_id}-captain", f"ship-{_ship_id}-captain-text", f"ship-{_ship_id}-captain-quote"]
    ELEMENT_IDS.append(f"ship-{_ship_id}-load-button")
    ELEMENT_IDS.append(f"ship-{_ship_id}-automate-button")
    ELEMENT_IDS.append(f"ship-{_ship_id}-name-input")
    ELEMENT_IDS.append(f"ship-{_ship_id}-rename-button")
    ELEMENT_IDS.append(f"ship-{_ship_id}-reset-name-button")
    if _ship_id in PURCHASABLE_SHIP_IDS:
        ELEMENT_IDS.append(f"ship-{_ship_id}-purchase-button")
    for _colony_id in ALL_COLONY_IDS:
        ELEMENT_IDS.append(f"ship-{_ship_id}-depart-{_colony_id}-button")

INITIALLY_DISABLED_IDS = [f"ship-{s}-depart-{c}-button" for s in SHIP_IDS for c in ALL_COLONY_IDS]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM/timers."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

    def ship(self, ship_id="1"):
        return self.module.ships[ship_id]

    @property
    def total_profit(self):
        return self.module.total_profit

    def load(self, ship_id="1"):
        self.elements[f"ship-{ship_id}-load-button"].dispatch("click", None)

    def depart(self, destination, ship_id="1"):
        self.elements[f"ship-{ship_id}-depart-{destination}-button"].dispatch("click", None)

    def automate(self, ship_id="1"):
        self.elements[f"ship-{ship_id}-automate-button"].dispatch("click", None)

    def unlock_research(self, node_id):
        self.elements[f"research-{node_id}-unlock-button"].dispatch("click", None)

    def toggle_fleet_priority(self):
        self.elements["fleet-priority-button"].dispatch("click", None)

    def toggle_achievements(self):
        self.elements["achievements-toggle-button"].dispatch("click", None)

    def toggle_changelog(self):
        self.elements["changelog-toggle-button"].dispatch("click", None)

    def toggle_charter(self):
        self.elements["charter-toggle-button"].dispatch("click", None)

    def toggle_captains(self):
        self.elements["captains-toggle-button"].dispatch("click", None)

    def toggle_summary(self):
        self.elements["summary-toggle-button"].dispatch("click", None)

    def purchase_ship(self, ship_id):
        self.elements[f"ship-{ship_id}-purchase-button"].dispatch("click", None)

    def rename_ship(self, ship_id, new_name):
        self.elements[f"ship-{ship_id}-name-input"].value = new_name
        self.elements[f"ship-{ship_id}-rename-button"].dispatch("click", None)

    def tick(self, times=1):
        self.timers.tick_intervals(times)


def _install_pyodide_fakes(elements, timers):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
    fake_js.setTimeout = timers.setTimeout
    fake_js.setInterval = timers.setInterval

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
    _forget_game_modules()


def _forget_game_modules():
    # game.py is split into trade_*.py modules next to it; each binds `document`, `setTimeout` and friends from the
    # fake `js` at import, so every test needs fresh copies, exactly as it needs a fresh game.py.
    for name, module in list(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if path and Path(path).resolve().parent == GAME_DIR:
            sys.modules.pop(name, None)


@pytest.fixture
def game_env():
    """Loads a brand-new game.py module against a fresh fake DOM.

    game.py runs setup() as a module-level side effect on import, so every
    test gets its own module object (and its own ships/colony state) rather
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
    module.run_seed = "TRADEEMPIRE-23456"  # a fixed run seed, so no test depends on a random one

    yield GameEnv(module, elements, timers)

    _remove_pyodide_fakes()
