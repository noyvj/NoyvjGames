import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeTimers, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

# Buttons that carry the `disabled` attribute in index.html's initial markup
# (they read "Loading..." until Pyodide finishes and setup() enables them).
# The fixture mirrors this so a setup() that forgets to re-enable one of
# them shows up as a real test failure, not a false negative from the fake
# defaulting to enabled.
INITIALLY_DISABLED_IDS = [
    "click-button",
    "buy-generator-button",
    "buy-recycler-button",
    "fund-research-button",
    "travel-moon-button",
    "travel-mars-button",
    "travel-venus-button",
    "travel-asteroid-belt-button",
    "travel-pluto-button",
    "travel-jupiter-moons-button",
    "travel-saturn-moons-button",
    "mars-click-button",
    "mars-buy-generator-button",
    "mars-buy-recycler-button",
    "buy-trade-route-button",
    "cycle-trade-destination-button",
    "mars-buy-trade-route-button",
    "mars-cycle-trade-destination-button",
    "moon-click-button",
    "moon-buy-generator-button",
    "moon-buy-recycler-button",
    "moon-buy-trade-route-button",
    "moon-cycle-trade-destination-button",
    "venus-click-button",
    "venus-buy-generator-button",
    "venus-buy-recycler-button",
    "venus-buy-trade-route-button",
    "venus-cycle-trade-destination-button",
    "asteroidbelt-click-button",
    "asteroidbelt-buy-generator-button",
    "asteroidbelt-buy-recycler-button",
    "asteroidbelt-buy-trade-route-button",
    "asteroidbelt-cycle-trade-destination-button",
    "pluto-click-button",
    "pluto-buy-generator-button",
    "pluto-buy-recycler-button",
    "pluto-buy-trade-route-button",
    "pluto-cycle-trade-destination-button",
    "jupitermoons-click-button",
    "jupitermoons-buy-generator-button",
    "jupitermoons-buy-recycler-button",
    "jupitermoons-buy-trade-route-button",
    "jupitermoons-cycle-trade-destination-button",
    "jupitermoons-buy-sky-city-button",
    "saturnmoons-click-button",
    "saturnmoons-buy-generator-button",
    "saturnmoons-buy-recycler-button",
    "saturnmoons-buy-trade-route-button",
    "saturnmoons-cycle-trade-destination-button",
    "saturnmoons-buy-sky-city-button",
]

# Maps the internal body identifier (used as current_planet / in
# unlocked_bodies) to its travel button id — kept in one place so tests
# don't have to hardcode the id-naming convention themselves.
TRAVEL_BUTTON_ID = {
    "Moon": "travel-moon-button",
    "Mars": "travel-mars-button",
    "Venus": "travel-venus-button",
    "AsteroidBelt": "travel-asteroid-belt-button",
    "Pluto": "travel-pluto-button",
    "JupiterMoons": "travel-jupiter-moons-button",
    "SaturnMoons": "travel-saturn-moons-button",
}

# Element IDs wired up in index.html — kept in one place so tests and the
# fixture agree on what "the DOM" contains.
ELEMENT_IDS = [
    # Win state (Milestone 11)
    "win-banner",
    "win-banner-heading",
    "win-banner-subtext",
    # Earth
    "click-button",
    "resource-count",
    "resource-label",
    "buy-generator-button",
    "generator-count",
    "generator-rate",
    "ecology-percent",
    "ecology-bar",
    "ecology-status",
    "buy-recycler-button",
    "recycler-count",
    "recycler-rate",
    # Research (Earth/global)
    "research-label",
    "research-progress",
    "research-bar",
    "research-status",
    "fund-research-button",
    # Views
    "earth-view",
    "mars-view",
    "moon-view",
    "venus-view",
    "asteroidbelt-view",
    "pluto-view",
    "jupitermoons-view",
    "saturnmoons-view",
    "away-view",
    # Governor
    "priority-growth-button",
    "priority-balance-button",
    "priority-ecology-button",
    "governor-budget-value",
    "budget-increase-button",
    "budget-decrease-button",
    # Travel
    "travel-status",
    "travel-moon-button",
    "travel-mars-button",
    "travel-venus-button",
    "travel-asteroid-belt-button",
    "travel-pluto-button",
    "travel-jupiter-moons-button",
    "travel-saturn-moons-button",
    # Undeveloped-body placeholder (away-view, unreachable now that every Far
    # Body has an economy — kept because update_away_summary() unconditionally
    # writes all of PLANETS every tick) — one summary block per real economy
    "away-planet-name",
    "away-earth-resource",
    "away-earth-generators",
    "away-earth-recyclers",
    "away-earth-ecology",
    "away-mars-resource",
    "away-mars-generators",
    "away-mars-recyclers",
    "away-mars-ecology",
    "away-moon-resource",
    "away-moon-generators",
    "away-moon-recyclers",
    "away-moon-ecology",
    "away-venus-resource",
    "away-venus-generators",
    "away-venus-recyclers",
    "away-venus-ecology",
    "away-asteroidbelt-resource",
    "away-asteroidbelt-generators",
    "away-asteroidbelt-recyclers",
    "away-asteroidbelt-ecology",
    "away-pluto-resource",
    "away-pluto-generators",
    "away-pluto-recyclers",
    "away-pluto-ecology",
    "away-jupitermoons-resource",
    "away-jupitermoons-generators",
    "away-jupitermoons-recyclers",
    "away-jupitermoons-ecology",
    "away-saturnmoons-resource",
    "away-saturnmoons-generators",
    "away-saturnmoons-recyclers",
    "away-saturnmoons-ecology",
    "return-to-earth-button",
    # Mars's own economy
    "mars-click-button",
    "mars-resource-count",
    "mars-resource-label",
    "mars-buy-generator-button",
    "mars-generator-count",
    "mars-generator-rate",
    "mars-ecology-percent",
    "mars-ecology-bar",
    "mars-ecology-status",
    "mars-buy-recycler-button",
    "mars-recycler-count",
    "mars-recycler-rate",
    "mars-return-to-earth-button",
    # Moon's own economy
    "moon-click-button",
    "moon-resource-count",
    "moon-resource-label",
    "moon-buy-generator-button",
    "moon-generator-count",
    "moon-generator-rate",
    "moon-ecology-percent",
    "moon-ecology-bar",
    "moon-ecology-status",
    "moon-buy-recycler-button",
    "moon-recycler-count",
    "moon-recycler-rate",
    "moon-return-to-earth-button",
    # Venus's own economy
    "venus-click-button",
    "venus-resource-count",
    "venus-resource-label",
    "venus-buy-generator-button",
    "venus-generator-count",
    "venus-generator-rate",
    "venus-ecology-percent",
    "venus-ecology-bar",
    "venus-ecology-status",
    "venus-buy-recycler-button",
    "venus-recycler-count",
    "venus-recycler-rate",
    "venus-return-to-earth-button",
    # Asteroid Belt's own economy
    "asteroidbelt-click-button",
    "asteroidbelt-resource-count",
    "asteroidbelt-resource-label",
    "asteroidbelt-buy-generator-button",
    "asteroidbelt-generator-count",
    "asteroidbelt-generator-rate",
    "asteroidbelt-ecology-percent",
    "asteroidbelt-ecology-bar",
    "asteroidbelt-ecology-status",
    "asteroidbelt-buy-recycler-button",
    "asteroidbelt-recycler-count",
    "asteroidbelt-recycler-rate",
    "asteroidbelt-return-to-earth-button",
    # Pluto's own economy
    "pluto-click-button",
    "pluto-resource-count",
    "pluto-resource-label",
    "pluto-buy-generator-button",
    "pluto-generator-count",
    "pluto-generator-rate",
    "pluto-ecology-percent",
    "pluto-ecology-bar",
    "pluto-ecology-status",
    "pluto-buy-recycler-button",
    "pluto-recycler-count",
    "pluto-recycler-rate",
    "pluto-return-to-earth-button",
    # Jupiter's Moons's own economy
    "jupitermoons-click-button",
    "jupitermoons-resource-count",
    "jupitermoons-resource-label",
    "jupitermoons-buy-generator-button",
    "jupitermoons-generator-count",
    "jupitermoons-generator-rate",
    "jupitermoons-ecology-percent",
    "jupitermoons-ecology-bar",
    "jupitermoons-ecology-status",
    "jupitermoons-buy-recycler-button",
    "jupitermoons-recycler-count",
    "jupitermoons-recycler-rate",
    "jupitermoons-sky-city-count",
    "jupitermoons-sky-city-bonus",
    "jupitermoons-buy-sky-city-button",
    "jupitermoons-return-to-earth-button",
    # Saturn's Moons's own economy
    "saturnmoons-click-button",
    "saturnmoons-resource-count",
    "saturnmoons-resource-label",
    "saturnmoons-buy-generator-button",
    "saturnmoons-generator-count",
    "saturnmoons-generator-rate",
    "saturnmoons-ecology-percent",
    "saturnmoons-ecology-bar",
    "saturnmoons-ecology-status",
    "saturnmoons-buy-recycler-button",
    "saturnmoons-recycler-count",
    "saturnmoons-recycler-rate",
    "saturnmoons-sky-city-count",
    "saturnmoons-sky-city-bonus",
    "saturnmoons-buy-sky-city-button",
    "saturnmoons-return-to-earth-button",
    # Cross-planet governed summaries (viewer-prefixed: Earth's ids are
    # unprefixed via _dom_id, every other viewer gets "<viewer>-" first)
    "mars-summary",
    "mars-summary-resource",
    "mars-summary-generators",
    "mars-summary-recyclers",
    "mars-summary-ecology",
    "moon-summary",
    "moon-summary-resource",
    "moon-summary-generators",
    "moon-summary-recyclers",
    "moon-summary-ecology",
    "venus-summary",
    "venus-summary-resource",
    "venus-summary-generators",
    "venus-summary-recyclers",
    "venus-summary-ecology",
    "asteroidbelt-summary",
    "asteroidbelt-summary-resource",
    "asteroidbelt-summary-generators",
    "asteroidbelt-summary-recyclers",
    "asteroidbelt-summary-ecology",
    "pluto-summary",
    "pluto-summary-resource",
    "pluto-summary-generators",
    "pluto-summary-recyclers",
    "pluto-summary-ecology",
    "jupitermoons-summary",
    "jupitermoons-summary-resource",
    "jupitermoons-summary-generators",
    "jupitermoons-summary-recyclers",
    "jupitermoons-summary-ecology",
    "saturnmoons-summary",
    "saturnmoons-summary-resource",
    "saturnmoons-summary-generators",
    "saturnmoons-summary-recyclers",
    "saturnmoons-summary-ecology",
    # Bare cross-summary container ids for non-Earth viewers (Earth's own
    # viewer-unprefixed containers, e.g. "mars-summary", are listed above;
    # every other viewer's container needs its own bare id too now that
    # update_cross_summary() toggles `.hidden` on it directly).
    "mars-earth-summary",
    "mars-moon-summary",
    "mars-venus-summary",
    "mars-asteroidbelt-summary",
    "mars-pluto-summary",
    "mars-jupitermoons-summary",
    "mars-saturnmoons-summary",
    "moon-earth-summary",
    "moon-mars-summary",
    "moon-venus-summary",
    "moon-asteroidbelt-summary",
    "moon-pluto-summary",
    "moon-jupitermoons-summary",
    "moon-saturnmoons-summary",
    "venus-earth-summary",
    "venus-mars-summary",
    "venus-moon-summary",
    "venus-asteroidbelt-summary",
    "venus-pluto-summary",
    "venus-jupitermoons-summary",
    "venus-saturnmoons-summary",
    "asteroidbelt-earth-summary",
    "asteroidbelt-mars-summary",
    "asteroidbelt-moon-summary",
    "asteroidbelt-venus-summary",
    "asteroidbelt-pluto-summary",
    "asteroidbelt-jupitermoons-summary",
    "asteroidbelt-saturnmoons-summary",
    "pluto-earth-summary",
    "pluto-mars-summary",
    "pluto-moon-summary",
    "pluto-venus-summary",
    "pluto-asteroidbelt-summary",
    "pluto-jupitermoons-summary",
    "pluto-saturnmoons-summary",
    "jupitermoons-earth-summary",
    "jupitermoons-mars-summary",
    "jupitermoons-moon-summary",
    "jupitermoons-venus-summary",
    "jupitermoons-asteroidbelt-summary",
    "jupitermoons-pluto-summary",
    "jupitermoons-saturnmoons-summary",
    "saturnmoons-earth-summary",
    "saturnmoons-mars-summary",
    "saturnmoons-moon-summary",
    "saturnmoons-venus-summary",
    "saturnmoons-asteroidbelt-summary",
    "saturnmoons-pluto-summary",
    "saturnmoons-jupitermoons-summary",
    "mars-earth-summary-resource",
    "mars-earth-summary-generators",
    "mars-earth-summary-recyclers",
    "mars-earth-summary-ecology",
    "mars-moon-summary-resource",
    "mars-moon-summary-generators",
    "mars-moon-summary-recyclers",
    "mars-moon-summary-ecology",
    "mars-venus-summary-resource",
    "mars-venus-summary-generators",
    "mars-venus-summary-recyclers",
    "mars-venus-summary-ecology",
    "mars-asteroidbelt-summary-resource",
    "mars-asteroidbelt-summary-generators",
    "mars-asteroidbelt-summary-recyclers",
    "mars-asteroidbelt-summary-ecology",
    "mars-pluto-summary-resource",
    "mars-pluto-summary-generators",
    "mars-pluto-summary-recyclers",
    "mars-pluto-summary-ecology",
    "mars-jupitermoons-summary-resource",
    "mars-jupitermoons-summary-generators",
    "mars-jupitermoons-summary-recyclers",
    "mars-jupitermoons-summary-ecology",
    "mars-saturnmoons-summary-resource",
    "mars-saturnmoons-summary-generators",
    "mars-saturnmoons-summary-recyclers",
    "mars-saturnmoons-summary-ecology",
    "moon-earth-summary-resource",
    "moon-earth-summary-generators",
    "moon-earth-summary-recyclers",
    "moon-earth-summary-ecology",
    "moon-mars-summary-resource",
    "moon-mars-summary-generators",
    "moon-mars-summary-recyclers",
    "moon-mars-summary-ecology",
    "moon-venus-summary-resource",
    "moon-venus-summary-generators",
    "moon-venus-summary-recyclers",
    "moon-venus-summary-ecology",
    "moon-asteroidbelt-summary-resource",
    "moon-asteroidbelt-summary-generators",
    "moon-asteroidbelt-summary-recyclers",
    "moon-asteroidbelt-summary-ecology",
    "moon-pluto-summary-resource",
    "moon-pluto-summary-generators",
    "moon-pluto-summary-recyclers",
    "moon-pluto-summary-ecology",
    "moon-jupitermoons-summary-resource",
    "moon-jupitermoons-summary-generators",
    "moon-jupitermoons-summary-recyclers",
    "moon-jupitermoons-summary-ecology",
    "moon-saturnmoons-summary-resource",
    "moon-saturnmoons-summary-generators",
    "moon-saturnmoons-summary-recyclers",
    "moon-saturnmoons-summary-ecology",
    "venus-earth-summary-resource",
    "venus-earth-summary-generators",
    "venus-earth-summary-recyclers",
    "venus-earth-summary-ecology",
    "venus-mars-summary-resource",
    "venus-mars-summary-generators",
    "venus-mars-summary-recyclers",
    "venus-mars-summary-ecology",
    "venus-moon-summary-resource",
    "venus-moon-summary-generators",
    "venus-moon-summary-recyclers",
    "venus-moon-summary-ecology",
    "venus-asteroidbelt-summary-resource",
    "venus-asteroidbelt-summary-generators",
    "venus-asteroidbelt-summary-recyclers",
    "venus-asteroidbelt-summary-ecology",
    "venus-pluto-summary-resource",
    "venus-pluto-summary-generators",
    "venus-pluto-summary-recyclers",
    "venus-pluto-summary-ecology",
    "venus-jupitermoons-summary-resource",
    "venus-jupitermoons-summary-generators",
    "venus-jupitermoons-summary-recyclers",
    "venus-jupitermoons-summary-ecology",
    "venus-saturnmoons-summary-resource",
    "venus-saturnmoons-summary-generators",
    "venus-saturnmoons-summary-recyclers",
    "venus-saturnmoons-summary-ecology",
    "asteroidbelt-earth-summary-resource",
    "asteroidbelt-earth-summary-generators",
    "asteroidbelt-earth-summary-recyclers",
    "asteroidbelt-earth-summary-ecology",
    "asteroidbelt-mars-summary-resource",
    "asteroidbelt-mars-summary-generators",
    "asteroidbelt-mars-summary-recyclers",
    "asteroidbelt-mars-summary-ecology",
    "asteroidbelt-moon-summary-resource",
    "asteroidbelt-moon-summary-generators",
    "asteroidbelt-moon-summary-recyclers",
    "asteroidbelt-moon-summary-ecology",
    "asteroidbelt-venus-summary-resource",
    "asteroidbelt-venus-summary-generators",
    "asteroidbelt-venus-summary-recyclers",
    "asteroidbelt-venus-summary-ecology",
    "asteroidbelt-pluto-summary-resource",
    "asteroidbelt-pluto-summary-generators",
    "asteroidbelt-pluto-summary-recyclers",
    "asteroidbelt-pluto-summary-ecology",
    "asteroidbelt-jupitermoons-summary-resource",
    "asteroidbelt-jupitermoons-summary-generators",
    "asteroidbelt-jupitermoons-summary-recyclers",
    "asteroidbelt-jupitermoons-summary-ecology",
    "asteroidbelt-saturnmoons-summary-resource",
    "asteroidbelt-saturnmoons-summary-generators",
    "asteroidbelt-saturnmoons-summary-recyclers",
    "asteroidbelt-saturnmoons-summary-ecology",
    "pluto-earth-summary-resource",
    "pluto-earth-summary-generators",
    "pluto-earth-summary-recyclers",
    "pluto-earth-summary-ecology",
    "pluto-mars-summary-resource",
    "pluto-mars-summary-generators",
    "pluto-mars-summary-recyclers",
    "pluto-mars-summary-ecology",
    "pluto-moon-summary-resource",
    "pluto-moon-summary-generators",
    "pluto-moon-summary-recyclers",
    "pluto-moon-summary-ecology",
    "pluto-venus-summary-resource",
    "pluto-venus-summary-generators",
    "pluto-venus-summary-recyclers",
    "pluto-venus-summary-ecology",
    "pluto-asteroidbelt-summary-resource",
    "pluto-asteroidbelt-summary-generators",
    "pluto-asteroidbelt-summary-recyclers",
    "pluto-asteroidbelt-summary-ecology",
    "pluto-jupitermoons-summary-resource",
    "pluto-jupitermoons-summary-generators",
    "pluto-jupitermoons-summary-recyclers",
    "pluto-jupitermoons-summary-ecology",
    "pluto-saturnmoons-summary-resource",
    "pluto-saturnmoons-summary-generators",
    "pluto-saturnmoons-summary-recyclers",
    "pluto-saturnmoons-summary-ecology",
    "jupitermoons-earth-summary-resource",
    "jupitermoons-earth-summary-generators",
    "jupitermoons-earth-summary-recyclers",
    "jupitermoons-earth-summary-ecology",
    "jupitermoons-mars-summary-resource",
    "jupitermoons-mars-summary-generators",
    "jupitermoons-mars-summary-recyclers",
    "jupitermoons-mars-summary-ecology",
    "jupitermoons-moon-summary-resource",
    "jupitermoons-moon-summary-generators",
    "jupitermoons-moon-summary-recyclers",
    "jupitermoons-moon-summary-ecology",
    "jupitermoons-venus-summary-resource",
    "jupitermoons-venus-summary-generators",
    "jupitermoons-venus-summary-recyclers",
    "jupitermoons-venus-summary-ecology",
    "jupitermoons-asteroidbelt-summary-resource",
    "jupitermoons-asteroidbelt-summary-generators",
    "jupitermoons-asteroidbelt-summary-recyclers",
    "jupitermoons-asteroidbelt-summary-ecology",
    "jupitermoons-pluto-summary-resource",
    "jupitermoons-pluto-summary-generators",
    "jupitermoons-pluto-summary-recyclers",
    "jupitermoons-pluto-summary-ecology",
    "jupitermoons-saturnmoons-summary-resource",
    "jupitermoons-saturnmoons-summary-generators",
    "jupitermoons-saturnmoons-summary-recyclers",
    "jupitermoons-saturnmoons-summary-ecology",
    "saturnmoons-earth-summary-resource",
    "saturnmoons-earth-summary-generators",
    "saturnmoons-earth-summary-recyclers",
    "saturnmoons-earth-summary-ecology",
    "saturnmoons-mars-summary-resource",
    "saturnmoons-mars-summary-generators",
    "saturnmoons-mars-summary-recyclers",
    "saturnmoons-mars-summary-ecology",
    "saturnmoons-moon-summary-resource",
    "saturnmoons-moon-summary-generators",
    "saturnmoons-moon-summary-recyclers",
    "saturnmoons-moon-summary-ecology",
    "saturnmoons-venus-summary-resource",
    "saturnmoons-venus-summary-generators",
    "saturnmoons-venus-summary-recyclers",
    "saturnmoons-venus-summary-ecology",
    "saturnmoons-asteroidbelt-summary-resource",
    "saturnmoons-asteroidbelt-summary-generators",
    "saturnmoons-asteroidbelt-summary-recyclers",
    "saturnmoons-asteroidbelt-summary-ecology",
    "saturnmoons-pluto-summary-resource",
    "saturnmoons-pluto-summary-generators",
    "saturnmoons-pluto-summary-recyclers",
    "saturnmoons-pluto-summary-ecology",
    "saturnmoons-jupitermoons-summary-resource",
    "saturnmoons-jupitermoons-summary-generators",
    "saturnmoons-jupitermoons-summary-recyclers",
    "saturnmoons-jupitermoons-summary-ecology",
    # Trade routes
    "earth-trade",
    "trade-route-count",
    "trade-route-rate",
    "trade-route-destination",
    "buy-trade-route-button",
    "cycle-trade-destination-button",
    "mars-trade-route-count",
    "mars-trade-route-rate",
    "mars-trade-route-destination",
    "mars-buy-trade-route-button",
    "mars-cycle-trade-destination-button",
    "moon-trade-route-count",
    "moon-trade-route-rate",
    "moon-trade-route-destination",
    "moon-buy-trade-route-button",
    "moon-cycle-trade-destination-button",
    "venus-trade-route-count",
    "venus-trade-route-rate",
    "venus-trade-route-destination",
    "venus-buy-trade-route-button",
    "venus-cycle-trade-destination-button",
    "asteroidbelt-trade-route-count",
    "asteroidbelt-trade-route-rate",
    "asteroidbelt-trade-route-destination",
    "asteroidbelt-buy-trade-route-button",
    "asteroidbelt-cycle-trade-destination-button",
    "pluto-trade-route-count",
    "pluto-trade-route-rate",
    "pluto-trade-route-destination",
    "pluto-buy-trade-route-button",
    "pluto-cycle-trade-destination-button",
    "jupitermoons-trade-route-count",
    "jupitermoons-trade-route-rate",
    "jupitermoons-trade-route-destination",
    "jupitermoons-buy-trade-route-button",
    "jupitermoons-cycle-trade-destination-button",
    "saturnmoons-trade-route-count",
    "saturnmoons-trade-route-rate",
    "saturnmoons-trade-route-destination",
    "saturnmoons-buy-trade-route-button",
    "saturnmoons-cycle-trade-destination-button",
    # Terraforming
    "terraform-percent",
    "terraform-bar",
    "terraform-status",
    "mars-terraform-percent",
    "mars-terraform-bar",
    "mars-terraform-status",
    "moon-terraform-percent",
    "moon-terraform-bar",
    "moon-terraform-status",
    "venus-terraform-percent",
    "venus-terraform-bar",
    "venus-terraform-status",
    "asteroidbelt-terraform-percent",
    "asteroidbelt-terraform-bar",
    "asteroidbelt-terraform-status",
    "pluto-terraform-percent",
    "pluto-terraform-bar",
    "pluto-terraform-status",
    "jupitermoons-terraform-percent",
    "jupitermoons-terraform-bar",
    "jupitermoons-terraform-status",
    "saturnmoons-terraform-percent",
    "saturnmoons-terraform-bar",
    "saturnmoons-terraform-status",
]

_BUTTON_ID = {
    "Earth": {
        "click": "click-button",
        "buy_generator": "buy-generator-button",
        "buy_recycler": "buy-recycler-button",
        "buy_trade_route": "buy-trade-route-button",
        "cycle_trade_destination": "cycle-trade-destination-button",
    },
    "Mars": {
        "click": "mars-click-button",
        "buy_generator": "mars-buy-generator-button",
        "buy_recycler": "mars-buy-recycler-button",
        "buy_trade_route": "mars-buy-trade-route-button",
        "cycle_trade_destination": "mars-cycle-trade-destination-button",
    },
    "Moon": {
        "click": "moon-click-button",
        "buy_generator": "moon-buy-generator-button",
        "buy_recycler": "moon-buy-recycler-button",
        "buy_trade_route": "moon-buy-trade-route-button",
        "cycle_trade_destination": "moon-cycle-trade-destination-button",
    },
    "Venus": {
        "click": "venus-click-button",
        "buy_generator": "venus-buy-generator-button",
        "buy_recycler": "venus-buy-recycler-button",
        "buy_trade_route": "venus-buy-trade-route-button",
        "cycle_trade_destination": "venus-cycle-trade-destination-button",
    },
    "AsteroidBelt": {
        "click": "asteroidbelt-click-button",
        "buy_generator": "asteroidbelt-buy-generator-button",
        "buy_recycler": "asteroidbelt-buy-recycler-button",
        "buy_trade_route": "asteroidbelt-buy-trade-route-button",
        "cycle_trade_destination": "asteroidbelt-cycle-trade-destination-button",
    },
    "Pluto": {
        "click": "pluto-click-button",
        "buy_generator": "pluto-buy-generator-button",
        "buy_recycler": "pluto-buy-recycler-button",
        "buy_trade_route": "pluto-buy-trade-route-button",
        "cycle_trade_destination": "pluto-cycle-trade-destination-button",
    },
    "JupiterMoons": {
        "click": "jupitermoons-click-button",
        "buy_generator": "jupitermoons-buy-generator-button",
        "buy_recycler": "jupitermoons-buy-recycler-button",
        "buy_trade_route": "jupitermoons-buy-trade-route-button",
        "cycle_trade_destination": "jupitermoons-cycle-trade-destination-button",
        "buy_sky_city": "jupitermoons-buy-sky-city-button",
    },
    "SaturnMoons": {
        "click": "saturnmoons-click-button",
        "buy_generator": "saturnmoons-buy-generator-button",
        "buy_recycler": "saturnmoons-buy-recycler-button",
        "buy_trade_route": "saturnmoons-buy-trade-route-button",
        "cycle_trade_destination": "saturnmoons-cycle-trade-destination-button",
        "buy_sky_city": "saturnmoons-buy-sky-city-button",
    },
}

_RETURN_BUTTON_ID = {
    "Mars": "mars-return-to-earth-button",
    "Moon": "moon-return-to-earth-button",
    "Venus": "venus-return-to-earth-button",
    "AsteroidBelt": "asteroidbelt-return-to-earth-button",
    "Pluto": "pluto-return-to-earth-button",
    "JupiterMoons": "jupitermoons-return-to-earth-button",
    "SaturnMoons": "saturnmoons-return-to-earth-button",
}


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM/timers."""

    def __init__(self, module, elements, timers):
        self.module = module
        self.elements = elements
        self.timers = timers

    @property
    def earth(self):
        return self.module.planet_state["Earth"]

    @property
    def mars(self):
        return self.module.planet_state["Mars"]

    @property
    def moon(self):
        return self.module.planet_state["Moon"]

    @property
    def venus(self):
        return self.module.planet_state["Venus"]

    @property
    def asteroid_belt(self):
        return self.module.planet_state["AsteroidBelt"]

    @property
    def pluto(self):
        return self.module.planet_state["Pluto"]

    @property
    def jupiter_moons(self):
        return self.module.planet_state["JupiterMoons"]

    @property
    def saturn_moons(self):
        return self.module.planet_state["SaturnMoons"]

    def state(self, planet):
        return self.module.planet_state[planet]

    def click(self, planet="Earth"):
        self.elements[_BUTTON_ID[planet]["click"]].dispatch("click", None)

    def buy_generator(self, planet="Earth"):
        self.elements[_BUTTON_ID[planet]["buy_generator"]].dispatch("click", None)

    def buy_recycler(self, planet="Earth"):
        self.elements[_BUTTON_ID[planet]["buy_recycler"]].dispatch("click", None)

    def buy_trade_route(self, planet="Earth"):
        self.elements[_BUTTON_ID[planet]["buy_trade_route"]].dispatch("click", None)

    def cycle_trade_destination(self, planet="Earth"):
        self.elements[_BUTTON_ID[planet]["cycle_trade_destination"]].dispatch("click", None)

    def buy_sky_city(self, planet="JupiterMoons"):
        self.elements[_BUTTON_ID[planet]["buy_sky_city"]].dispatch("click", None)

    def fund_research(self):
        self.elements["fund-research-button"].dispatch("click", None)

    def set_priority(self, priority):
        self.elements[f"priority-{priority}-button"].dispatch("click", None)

    def increase_budget(self):
        self.elements["budget-increase-button"].dispatch("click", None)

    def decrease_budget(self):
        self.elements["budget-decrease-button"].dispatch("click", None)

    def travel_to(self, body):
        self.elements[TRAVEL_BUTTON_ID[body]].dispatch("click", None)

    def travel_to_moon(self):
        self.travel_to("Moon")

    def travel_to_mars(self):
        self.travel_to("Mars")

    def return_to_earth(self):
        # Whichever "Return to Earth" button is relevant depends on where
        # the player currently is (an undeveloped-body placeholder vs a
        # real economy's own dedicated view).
        button_id = _RETURN_BUTTON_ID.get(self.module.current_planet, "return-to-earth-button")
        self.elements[button_id].dispatch("click", None)


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


@pytest.fixture
def game_env():
    """Loads a brand-new game.py module against a fresh fake DOM.

    game.py runs setup() as a module-level side effect on import, so every
    test gets its own module object (and its own planet_state) rather than
    sharing state via Python's normal import cache.
    """
    elements = {id_: FakeElement(id_) for id_ in ELEMENT_IDS}
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
