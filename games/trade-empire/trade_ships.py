"""Ship archetypes, the Ship class, the ship table, sale log and profit totals, automation, trade posts, colony investment and concessions, buying and renaming ships."""

import trade_runstate as runstate
from trade_blueprints import _blueprint_for_choice, hull_effects
from trade_captains import captain_adjusted_ticks, captain_cargo_multiplier, captain_proceeds_multiplier
from trade_charter import (
    CHARTER_CARGO_BONUS, LEDGER_MAX, automation_cost, charter_perk, colony_invest_cost, trade_post_cost,
    trade_post_income_each,
)
from trade_colony import (
    _system_label_for_colony, active_colony_ids, colony_states, galaxy_expansion_unlocked,
    outer_reaches_unlocked, umbral_reach_unlocked,
)
from trade_effects import legacy_sale_multiplier
from trade_hub import hub_trip_ticks
from trade_mapdraw import add_dock_pulse
from trade_market import (
    INSURANCE_COVERAGE, ROUTE_HAZARD_CHANCE, current_sell_price, diplomacy_multiplier, hazard_roll,
)
from trade_research import (
    AUTO_EFFICIENCY_BONUS, MAX_SHIP_NAME_LENGTH, fleet_cargo_multiplier, max_automated_ships, travel_ticks,
)
from trade_rules import (
    ALL_COLONIES, CONCESSION_COST, OPPORTUNIST_INVEST_DISCOUNT, OPPORTUNIST_NEED_BELOW,
    PURCHASABLE_SHIP_IDS, TEMPERAMENTS,
)


# J5 -- ship archetypes, chosen when buying ship 5 or 6 (the original four
# ships are always balanced). "cargo" carries more but is slower, "fast"
# arrives sooner but carries less; both trade off, so no archetype is
# strictly better. Saved per ship and validated on load.
SHIP_ARCHETYPES = {
    "balanced": {"label": "Balanced", "cargo": 1.0, "ticks": 0},
    "cargo": {"label": "Cargo-heavy", "cargo": 1.5, "ticks": 1},
    "fast": {"label": "Fast", "cargo": 0.75, "ticks": -1},
}
DEFAULT_ARCHETYPE = "balanced"


def archetype_for(ship):
    hull = getattr(ship, "hull", None)
    if hull is not None:  # J-19: a custom hull from the Blueprint Lab
        return hull_effects(hull)
    return SHIP_ARCHETYPES.get(getattr(ship, "archetype", DEFAULT_ARCHETYPE), SHIP_ARCHETYPES[DEFAULT_ARCHETYPE])


VETERAN_ROUND_TRIPS = 5  # J14 — round trips on one route for the badge
UNDERPERFORM_FRACTION = 0.5  # J25 — below this share of fleet-average earnings
ROUTE_TREND_WINDOW = 4  # J2 — sales per half-window compared for the arrow
DEFAULT_TREND_EPSILON = 0.05


class Ship:
    def __init__(self, ship_id, start_colony):
        self.id = ship_id
        self.location = start_colony  # colony id, or None while in transit
        self.origin = None  # colony id departed from, while in transit
        self.destination = None  # colony id being traveled to, while in transit
        self.cargo_good = None
        self.cargo_qty = 0
        self.transit_ticks_remaining = 0
        self.transit_total_ticks = 0  # ticks this specific trip started with, for map interpolation
        self.automated = False
        # J6 — ships 5/6 start unpurchased; the original 4-ship roster is
        # purchased from the moment the game starts, same as it always
        # was before this feature existed.
        self.purchased = True
        self.archetype = DEFAULT_ARCHETYPE  # J5
        self.hull = None  # J-19: {"name", "hold", "speed", "eff"} for a custom hull (archetype "custom")
        # J10 — player-chosen display name, defaults to "Ship N".
        self.name = f"Ship {ship_id}"
        # J15 — consecutive ticks this ship has spent docked, empty, and
        # not automated. Reset the instant any of those stop being true
        # (tick() does the resetting; see IDLE_WARNING_TICKS below).
        self.idle_ticks = 0
        # J14 — veteran-hauler bookkeeping: the (unordered) colony pair of
        # the last completed cargo leg, and how many consecutive legs
        # have been on that same pair. Two legs = one round trip.
        self.route_key = None
        self.route_legs = 0
        # J25 — lifetime credits this ship's own deliveries have earned.
        self.total_earned = 0
        # J-6 -- throughput bookkeeping: units this ship has delivered, the
        # ticks it has been part of the fleet, and units per good.
        self.units_moved = 0
        self.ticks_owned = 0
        self.units_by_good = {}
        # J-7 -- the captain's perk id (or None) and the deliveries made since
        # the captain was assigned (the Lucky Trader's every-fourth-trip count).
        self.captain = None
        self.captain_deliveries = 0

    @property
    def round_trips(self):
        return self.route_legs // 2

    @property
    def is_veteran(self):
        return self.round_trips >= VETERAN_ROUND_TRIPS

    @property
    def in_transit(self):
        return self.location is None

    @property
    def on_expedition(self):
        return _ship_on_expedition(self)

    @property
    def docked(self):
        return self.location is not None and not self.on_expedition

    @property
    def loaded(self):
        return self.cargo_qty > 0

    def load(self):
        if not self.purchased or not self.docked or self.loaded:
            return False
        self.cargo_good = ALL_COLONIES[self.location]["produces"]
        self.cargo_qty = max(
            1,
            round(
                colony_states[self.location].cargo_capacity() * fleet_cargo_multiplier() * archetype_for(self)["cargo"]
                * captain_cargo_multiplier(self)
            )
            + (CHARTER_CARGO_BONUS if charter_perk("surveyed_lanes") else 0),
        )
        return True

    def other_colonies(self):
        """Every colony this ship could plausibly be sent to right now —
        anywhere reachable except wherever it's currently docked."""
        if not self.docked:
            return []
        return [c for c in active_colony_ids() if c != self.location]

    def _begin_transit(self, destination):
        add_dock_pulse(self.location, "undock")
        self.origin = self.location
        self.destination = destination
        self.location = None
        self.transit_total_ticks = max(1, hub_trip_ticks(  # J-21: the Distribution Hub halves trips to its neighbours
            self.origin, destination, max(1, captain_adjusted_ticks(self, travel_ticks() + archetype_for(self)["ticks"]))
        ))
        self.transit_ticks_remaining = self.transit_total_ticks

    def depart(self, destination):
        if not self.purchased or not self.docked or not self.loaded:
            return False
        if destination == self.location or destination not in active_colony_ids():
            return False
        self._begin_transit(destination)
        return True

    def reposition(self, destination):
        """Milestone 12: fleet-priority repositioning — an automated ship
        travels empty to a different producer colony, abandoning its
        current home shuttle. Unlike depart(), this doesn't require
        cargo, but it's only ever called by run_automation() under
        fleet-priority mode; manual play has no button that reaches it,
        so the "must be loaded to leave" rule still holds for the
        player."""
        if not self.docked or self.loaded:
            return False
        if destination == self.location or destination not in active_colony_ids():
            return False
        self._begin_transit(destination)
        return True

    def advance_transit(self):
        """Ticks the transit countdown by one. Returns the sale proceeds
        (good, qty, profit) if this tick completed the transit, else None."""
        if not self.in_transit:
            return None
        self.transit_ticks_remaining -= 1
        if self.transit_ticks_remaining > 0:
            return None
        good, qty = self.cargo_good, self.cargo_qty
        destination = self.destination
        result = None
        if good is not None:
            # Milestone 12's empty reposition() trips have no cargo, so
            # there's nothing to sell or deliver on arrival -- just dock.
            efficiency = 1.0 + (AUTO_EFFICIENCY_BONUS if self.automated and "auto_efficiency" in runstate.unlocked_research else 0.0)
            profit = int(round(
                qty * current_sell_price(good) * diplomacy_multiplier() * legacy_sale_multiplier() * efficiency
                * captain_proceeds_multiplier(self, destination, good) * colony_premium_multiplier(destination)
                * archetype_for(self).get("proceeds", 1.0)
            ))
            if runstate.route_hazards_enabled and hazard_roll() < ROUTE_HAZARD_CHANCE:
                # J11 -- a route disruption: the cargo is lost, nothing is
                # delivered or sold. Insurance pays a share of what the
                # trip would have earned. qty == 0 marks the disruption
                # for tick(), which logs it instead of a sale.
                payout = int(round(profit * INSURANCE_COVERAGE)) if runstate.route_insurance_enabled else 0
                runstate.disruptions_suffered += 1
                runstate.insurance_payouts += payout
                result = (good, 0, payout)
                self.total_earned += payout
            else:
                if self.origin is not None and _system_label_for_colony(self.origin) != _system_label_for_colony(destination):
                    runstate.cross_system_units = min(runstate.cross_system_units + qty, 10_000_000)
                dest_state = colony_states[destination]
                if ALL_COLONIES[destination]["needs"] == good:
                    dest_state.deliver(qty)
                elif dest_state.is_developed() and dest_state.secondary_need() == good:
                    dest_state.deliver_secondary(qty)
                result = (good, qty, profit)
                self.total_earned += profit
                self.units_moved = min(LEDGER_MAX, self.units_moved + qty)
                self.units_by_good[good] = min(LEDGER_MAX, self.units_by_good.get(good, 0) + qty)
                if self.captain is not None:
                    self.captain_deliveries += 1
            key = frozenset((self.origin, destination))
            if key == self.route_key:
                self.route_legs += 1
            else:
                self.route_key = key
                self.route_legs = 1
        self.location = destination
        add_dock_pulse(destination, "dock")
        self.origin = None
        self.destination = None
        self.cargo_good = None
        self.cargo_qty = 0
        return result


SHIP_PURCHASE_COST = {"5": 400, "6": 1000}

ships = {
    "1": Ship("1", "aurum"),
    "2": Ship("2", "verdant"),
    "3": Ship("3", "ferrum"),
    "4": Ship("4", "cryo"),
    "5": Ship("5", "aurum"),
    "6": Ship("6", "aurum"),
}
for _purchasable_id in PURCHASABLE_SHIP_IDS:
    ships[_purchasable_id].purchased = False

# Z25 save-portability audit: only sale_log[-1] is ever read (the status
# line and its own regression test both index just the last entry), but
# tick() appended to this list every sale with no truncation at all --
# unlike every sibling rolling-history field in this file
# (good_profit_recent/price_history/need_history), which are all capped.
# Left unbounded, a long automated session (this game ticks once a second
# via setInterval regardless of whether the player is present, see
# TICK_INTERVAL_MS) grows this without limit: measured ~100KB of a
# ~110KB save payload after 5000 ticks (~83 simulated minutes) in a
# fully-automated session. Capped generously above the "just the last
# one" need in case a future feature wants a short recent-sales view.
SALE_LOG_MAX_ENTRIES = 20

MARKET_RECOVERY_THRESHOLD = 0.9


def automated_ship_count():
    return sum(1 for s in ships.values() if s.automated)


def automation_slots_available():
    return automated_ship_count() < max_automated_ships()


def automate_ship(ship_id):
    ship = ships[ship_id]
    if not ship.purchased or ship.automated or not automation_slots_available() or runstate.total_profit < automation_cost():
        return False
    runstate.total_profit -= automation_cost()
    ship.automated = True
    return True


# J17 -- player-run trade posts. Once every automation slot is filled
# (automation is "maxed"), the player can establish a trade post in a
# reachable star system: a passive income source that needs no ship. One
# post per system, so it scales with how far the empire has expanded, and
# it pays a small flat amount each tick (not counted as a sale).
TRADE_POST_SYSTEMS = ("Home system", "Kepler Cluster", "Rift Colonies", "Umbral Deep")

trade_posts = []


def automation_is_maxed():
    return not automation_slots_available()


def _system_is_reachable(system_label):
    if system_label == "Home system":
        return True
    if system_label == "Kepler Cluster":
        return galaxy_expansion_unlocked()
    if system_label == "Rift Colonies":
        return outer_reaches_unlocked()
    return umbral_reach_unlocked()


def next_trade_post_system():
    for system_label in TRADE_POST_SYSTEMS:
        if system_label not in trade_posts and _system_is_reachable(system_label):
            return system_label
    return None


def can_build_trade_post():
    return (
        automation_is_maxed()
        and next_trade_post_system() is not None
        and runstate.total_profit >= trade_post_cost()
    )


def build_trade_post():
    if not can_build_trade_post():
        return False
    runstate.total_profit -= trade_post_cost()
    trade_posts.append(next_trade_post_system())
    return True


def trade_post_income_per_tick():
    return len(trade_posts) * trade_post_income_each()


COLONY_INVEST_UNITS = 10


def can_grant_concession(colony_id):
    state = colony_states.get(colony_id)
    return state is not None and state.has_demand() and runstate.total_profit >= CONCESSION_COST


def grant_concession(colony_id):
    if not can_grant_concession(colony_id):
        return False
    runstate.total_profit -= CONCESSION_COST
    colony_states[colony_id].grant_concession()
    return True


def colony_invest_cost_for(colony_id):
    """What an Invest costs at this colony right now (J-25: an Opportunistic
    colony with a low need takes it at a discount)."""
    base = colony_invest_cost()
    state = colony_states.get(colony_id)
    if (
        state is not None
        and state.temperament() == "opportunistic"
        and state.need_satisfaction < OPPORTUNIST_NEED_BELOW
    ):
        return max(1, int(round(base * OPPORTUNIST_INVEST_DISCOUNT)))
    return base


def can_invest_in_colony(colony_id):
    if colony_id not in active_colony_ids() or colony_id not in colony_states:
        return False
    return not colony_states[colony_id].is_developed() and runstate.total_profit >= colony_invest_cost_for(colony_id)


def invest_in_colony(colony_id):
    if not can_invest_in_colony(colony_id):
        return False
    runstate.total_profit -= colony_invest_cost_for(colony_id)
    colony_states[colony_id].add_development(COLONY_INVEST_UNITS)
    return True


def colony_premium_multiplier(colony_id):
    """J-25 -- the temperament premium on proceeds delivered to this colony."""
    state = colony_states.get(colony_id)
    if state is None:
        return 1.0
    return 1.0 + TEMPERAMENTS[state.temperament()]["premium"]


def can_purchase_ship(ship_id):
    ship = ships[ship_id]
    if ship.purchased:
        return False
    if ship_id == "6" and not ships["5"].purchased:
        return False
    return runstate.total_profit >= SHIP_PURCHASE_COST[ship_id]


def purchase_ship(ship_id, archetype=DEFAULT_ARCHETYPE):
    """J6 — a one-time credit spend that unlocks a 5th/6th ship, same
    shape as automate_ship()'s one-time AUTOMATION_COST spend. J5 -- the
    buyer also picks an archetype (an unknown value falls back to balanced)."""
    if not can_purchase_ship(ship_id):
        return False
    runstate.total_profit -= SHIP_PURCHASE_COST[ship_id]
    ships[ship_id].purchased = True
    design = _blueprint_for_choice(archetype)
    if design is not None:  # J-19: a saved design; the hull is copied onto the ship
        ships[ship_id].archetype = "custom"
        ships[ship_id].hull = dict(design)
    else:
        ships[ship_id].archetype = archetype if archetype in SHIP_ARCHETYPES else DEFAULT_ARCHETYPE
        ships[ship_id].hull = None
    return True


def rename_ship(ship_id, new_name):
    """J10 — a blank/whitespace-only name is rejected rather than
    silently accepted, so a ship can never end up with an empty label."""
    name = (new_name or "").strip()
    if not name:
        return False
    ships[ship_id].name = name[:MAX_SHIP_NAME_LENGTH]
    return True


def reset_ship_name(ship_id):
    """J12 — restore the default "Ship N" name."""
    ships[ship_id].name = f"Ship {ship_id}"
    return True


def _ship_on_expedition(ship):
    return runstate.expedition is not None and runstate.expedition["ship"] == ship.id
