"""load_state(), _apply_state() and the practice sandbox's enter and leave, which reuse it: restores a save into the live game, then redraws."""

import copy

import seed as seed_lib

import trade_runstate as runstate
from trade_achievements import ACHIEVEMENTS, _earned_snapshot
from trade_blueprints import BLUEPRINT_STAT_KEYS, _hull_ok
from trade_captains import CAPTAINS
from trade_chain_logic import _chain_clear
from trade_charter import LEDGER_MAX
from trade_colony import (
    ColonyState, active_colony_ids, colony_states, galaxy_expansion_unlocked, outer_reaches_unlocked,
    umbral_reach_unlocked,
)
from trade_crises import _crisis_clear
from trade_founding import LEGACY_MAX_LEVEL
from trade_loadparts import (
    _load_blackout, _load_blueprints, _load_captains, _load_cartel, _load_charter, _load_exchange,
    _load_expedition, _load_ghost, _load_guild, _load_hub, _load_meridian, _load_records, _load_weather,
)
from trade_market import (
    SEED_GAME, STOCKPILE_CAPACITY, good_profit_recent, good_profit_total, good_trip_count,
    market_crash_ever, market_multiplier, need_history, price_history, price_memory, stockpile,
)
from trade_records import _saved_float, _saved_int
from trade_renderer import render
from trade_research import RESEARCH_NODES
from trade_rules import (
    DEEP_COLONIES, DEMAND_COOLDOWN_TICKS, DEMAND_WINDOW_TICKS, EXPANSION_COLONIES, RIFT_COLONIES,
    SELL_PRICE, TEMPERAMENT_COUNT_MAX,
)
from trade_sandbox import (
    _reset_running_tables, _sandbox_notify_page, _sandbox_set_real_aside, _sandbox_state, _sandbox_top_up,
)
from trade_ships import DEFAULT_ARCHETYPE, SHIP_ARCHETYPES, TRADE_POST_SYSTEMS, ships, trade_posts


def load_state(data):
    """The public entry the save widget calls: leaves the practice sandbox first (Z-18), then loads."""
    if runstate.sandbox_active:
        _sandbox_restore_real(apply_snapshot=False)
    result = _apply_state(data)
    _sandbox_notify_page()
    return result


def _apply_state(data):
    """Exact inverse of get_state(). Colony state for the Kepler Cluster
    is (re)created here if the save has galaxy_expansion unlocked but the
    live module hasn't gotten there yet — mirroring what unlock_research()
    itself does — so a save loaded fresh into a brand-new session doesn't
    leave Fleet Priority's most_urgent_colony() unable to see colonies the
    save says should exist."""

    stockpile_raw = data.get("stockpile")
    for good in stockpile:
        units = stockpile_raw.get(good) if isinstance(stockpile_raw, dict) else None
        valid = isinstance(units, int) and not isinstance(units, bool) and 0 <= units <= STOCKPILE_CAPACITY
        stockpile[good] = units if valid else 0

    posts_raw = data.get("trade_posts")
    trade_posts[:] = []
    if isinstance(posts_raw, list):
        for label in posts_raw:
            if isinstance(label, str) and label in TRADE_POST_SYSTEMS and label not in trade_posts:
                trade_posts.append(label)

    hazards_raw = data.get("route_hazards")
    if not isinstance(hazards_raw, dict):
        hazards_raw = {}

    def _count(key):
        value = hazards_raw.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10_000_000 else 0

    runstate.route_hazards_enabled = hazards_raw.get("hazards") is True
    runstate.route_insurance_enabled = hazards_raw.get("insurance") is True
    runstate.disruptions_suffered, runstate.insurance_payouts, runstate.premiums_paid = _count("disruptions"), _count("payouts"), _count("premiums")
    runstate.hazard_rolls = _count("rolls")
    seed_check = seed_lib.validate(data.get("run_seed"), SEED_GAME) if isinstance(data.get("run_seed"), str) else {"ok": False}
    runstate.run_seed, runstate.run_seed_pinned = (seed_check["seed"], True) if seed_check["ok"] else ("", False)

    units_raw = data.get("cross_system_units")
    runstate.cross_system_units = units_raw if isinstance(units_raw, int) and not isinstance(units_raw, bool) and 0 <= units_raw <= 10_000_000 else 0

    seasonal_raw = data.get("seasonal_demand")
    if isinstance(seasonal_raw, dict):
        runstate.seasonal_demand_enabled = seasonal_raw.get("enabled") is True
        ticks_raw = seasonal_raw.get("ticks")
        runstate.season_ticks = ticks_raw if isinstance(ticks_raw, int) and not isinstance(ticks_raw, bool) and 0 <= ticks_raw <= 10_000_000 else 0
    else:
        runstate.seasonal_demand_enabled, runstate.season_ticks = False, 0

    # Untrusted save value: only known node ids survive (a non-list, or a
    # list holding unhashable/non-string/unknown entries, must not crash the
    # set() build or invent research).
    research_raw = data.get("unlocked_research", sorted(runstate.unlocked_research))
    runstate.unlocked_research = {
        node for node in (research_raw if isinstance(research_raw, list) else [])
        if isinstance(node, str) and node in RESEARCH_NODES
    }

    # A save that hasn't unlocked an expansion must not keep that expansion's
    # colonies from whatever was running before (loading an earlier save, or
    # J21's fresh start after a late-game corporation).
    if not galaxy_expansion_unlocked():
        for colony_id in EXPANSION_COLONIES:
            colony_states.pop(colony_id, None)
    if not outer_reaches_unlocked():
        for colony_id in RIFT_COLONIES:
            colony_states.pop(colony_id, None)
    if not umbral_reach_unlocked():
        for colony_id in DEEP_COLONIES:
            colony_states.pop(colony_id, None)

    legacy_raw = data.get("legacy")
    runstate.legacy_level = 0
    runstate.legacy_achievements = []
    if isinstance(legacy_raw, dict):
        level = legacy_raw.get("level")
        if isinstance(level, int) and not isinstance(level, bool):
            runstate.legacy_level = max(0, min(LEGACY_MAX_LEVEL, level))
        known = {entry["id"] for entry in ACHIEVEMENTS}
        raw_ids = legacy_raw.get("achievements")
        if runstate.legacy_level and isinstance(raw_ids, list):
            runstate.legacy_achievements = [a for a in dict.fromkeys(raw_ids) if isinstance(a, str) and a in known]
    _load_charter(data.get("charter"), data.get("ledger"))
    _load_guild(data.get("guild"))  # after the charter: Guild Standing shortens the first wait

    if galaxy_expansion_unlocked():
        for colony_id in EXPANSION_COLONIES:
            if colony_id not in colony_states:
                colony_states[colony_id] = ColonyState(colony_id)
    if outer_reaches_unlocked():
        for colony_id in RIFT_COLONIES:
            if colony_id not in colony_states:
                colony_states[colony_id] = ColonyState(colony_id)
    if umbral_reach_unlocked():
        for colony_id in DEEP_COLONIES:
            if colony_id not in colony_states:
                colony_states[colony_id] = ColonyState(colony_id)

    saved_colony_states = data.get("colony_states", {})
    for colony_id, state in colony_states.items():
        saved = saved_colony_states.get(colony_id)
        if not saved:
            continue
        if not isinstance(saved, dict):
            continue
        # Untrusted save values: numbers only (never bool), finite, and inside
        # each field's real range; anything else keeps the colony's default.
        state.need_satisfaction = _saved_float(saved.get("need_satisfaction"), 0.0, 1.0, state.need_satisfaction)
        level = saved.get("development_level")
        if isinstance(level, int) and not isinstance(level, bool) and 1 <= level <= 2:
            state.development_level = level
        state.cumulative_delivered = _saved_float(
            saved.get("cumulative_delivered"), 0.0, 10_000_000.0, state.cumulative_delivered
        )
        state.secondary_need_satisfaction = _saved_float(
            saved.get("secondary_need_satisfaction"), 0.0, 1.0, state.secondary_need_satisfaction
        )
        for loyalty_key, limit in (
            ("neglect_ticks", TEMPERAMENT_COUNT_MAX),  # keeps counting through a cooldown, so it can pass NEGLECT_DEMAND_TICKS
            ("demand_ticks_left", DEMAND_WINDOW_TICKS),
            ("demand_cooldown", DEMAND_COOLDOWN_TICKS),
        ):
            raw = saved.get(loyalty_key)
            valid = isinstance(raw, int) and not isinstance(raw, bool) and 0 <= raw <= limit
            setattr(state, loyalty_key, raw if valid else 0)
        state.demands_made = _saved_int(saved.get("demands_made"), 0, TEMPERAMENT_COUNT_MAX)
        state.concessions_granted = _saved_int(saved.get("concessions_granted"), 0, TEMPERAMENT_COUNT_MAX)

    saved_ships = data.get("ships", {})
    if not isinstance(saved_ships, dict):
        saved_ships = {}
    for ship_id, ship in ships.items():
        saved = saved_ships.get(ship_id)
        if not saved or not isinstance(saved, dict):
            continue
        ship.location = saved.get("location", ship.location)
        ship.origin = saved.get("origin", ship.origin)
        ship.destination = saved.get("destination", ship.destination)
        ship.cargo_good = saved.get("cargo_good", ship.cargo_good)
        ship.cargo_qty = saved.get("cargo_qty", ship.cargo_qty)
        ship.transit_ticks_remaining = saved.get(
            "transit_ticks_remaining", ship.transit_ticks_remaining
        )
        ship.transit_total_ticks = saved.get("transit_total_ticks", ship.transit_total_ticks)
        ship.automated = saved.get("automated", ship.automated)
        ship.purchased = saved.get("purchased", ship.purchased)
        saved_archetype = saved.get("archetype")
        ship.archetype = saved_archetype if isinstance(saved_archetype, str) and saved_archetype in SHIP_ARCHETYPES else DEFAULT_ARCHETYPE
        ship.hull = None
        hull_raw = saved.get("hull")
        if saved_archetype == "custom" and _hull_ok(hull_raw):  # J-19: a custom hull, fully re-validated
            ship.archetype = "custom"
            ship.hull = {k: hull_raw[k] for k in (*BLUEPRINT_STAT_KEYS, "name")}
            ship.hull["name"] = ship.hull["name"].strip()
        ship.name = saved.get("name", ship.name)
        ship.idle_ticks = saved.get("idle_ticks", ship.idle_ticks)
        saved_key = saved.get("route_key")
        ship.route_key = frozenset(saved_key) if saved_key else None
        ship.route_legs = saved.get("route_legs", 0)
        ship.total_earned = saved.get("total_earned", 0)
        ship.units_moved = _saved_int(saved.get("units_moved"), 0, LEDGER_MAX)
        ship.ticks_owned = _saved_int(saved.get("ticks_owned"), 0, LEDGER_MAX)
        by_good = saved.get("units_by_good")
        ship.units_by_good = {}
        if isinstance(by_good, dict):
            for good_id, units in by_good.items():
                if isinstance(good_id, str) and good_id in SELL_PRICE and _saved_int(units, 1, LEDGER_MAX, 0):
                    ship.units_by_good[good_id] = units
        captain_raw = saved.get("captain")
        ship.captain = captain_raw if isinstance(captain_raw, str) and captain_raw in CAPTAINS else None
        ship.captain_deliveries = _saved_int(saved.get("captain_deliveries"), 0, LEDGER_MAX)

    # A ship can't be docked at, or flying to/from, a colony this save hasn't
    # unlocked (its colony state was just pruned above, and a docked ship
    # would crash load()): send it home, empty, rather than trusting the save.
    reachable_now = active_colony_ids()
    for ship in ships.values():
        docked_ok = ship.location in reachable_now if isinstance(ship.location, str) else False
        transit_ok = (
            ship.location is None
            and isinstance(ship.origin, str) and ship.origin in reachable_now
            and isinstance(ship.destination, str) and ship.destination in reachable_now
        )
        if not (docked_ok or transit_ok):
            ship.location = "aurum"
            ship.origin = ship.destination = None
            ship.cargo_good, ship.cargo_qty = None, 0
            ship.transit_ticks_remaining = ship.transit_total_ticks = 0

    _load_captains(data.get("captains"))
    _load_records(data.get("records"))
    _load_ghost(data.get("ghost"))  # Z-3e5
    _load_expedition(data.get("expedition"))
    _load_exchange(data.get("exchange"))
    _load_blueprints(data.get("blueprints"))
    _load_hub(data.get("hub"))
    _load_meridian(data.get("meridian"))
    _load_cartel(data.get("cartel"))
    _load_blackout(data.get("blackout"))
    _load_weather(data.get("weather"))
    price_memory.clear()
    memory_raw = data.get("price_memory")
    if isinstance(memory_raw, dict):
        for good_id, value in memory_raw.items():
            if isinstance(good_id, str) and good_id in SELL_PRICE:
                remembered = _saved_float(value, 0.0, 1.0, -1.0)
                if remembered >= 0.0:
                    price_memory[good_id] = remembered

    market_multiplier.update(data.get("market_multiplier", {}))
    runstate.total_profit = data.get("total_profit", runstate.total_profit)
    runstate.sale_log = list(data.get("sale_log", runstate.sale_log))
    runstate.research_points = data.get("research_points", runstate.research_points)
    runstate.fleet_priority_enabled = data.get("fleet_priority_enabled", runstate.fleet_priority_enabled)
    runstate.endgame_reached = data.get("endgame_reached", runstate.endgame_reached)
    runstate.ticks_since_endgame = data.get("ticks_since_endgame", runstate.ticks_since_endgame)

    runstate.total_sales_count = data.get("total_sales_count", runstate.total_sales_count)
    runstate.max_profit_ever = data.get("max_profit_ever", runstate.max_profit_ever)
    runstate.goods_sold_ever = set(data.get("goods_sold_ever", runstate.goods_sold_ever))
    runstate.ever_repositioned = data.get("ever_repositioned", runstate.ever_repositioned)
    market_crash_ever.update(data.get("market_crash_ever", {}))
    good_profit_total.update(data.get("good_profit_total", {}))
    good_trip_count.update(data.get("good_trip_count", {}))
    for good, values in data.get("good_profit_recent", {}).items():
        good_profit_recent[good] = list(values)
    for good, values in data.get("price_history", {}).items():
        price_history[good] = list(values)
    for colony_id, values in data.get("need_history", {}).items():
        need_history[colony_id] = list(values)
    # Belt-and-suspenders backfill, same idea as Canopy's community_
    # relations_min_ever: an old save predating this field can't have
    # recorded it, but the restored total_profit is itself a valid lower
    # bound on the highest profit this session must have reached.
    runstate.max_profit_ever = max(runstate.max_profit_ever, runstate.total_profit)

    # achievements_earned itself is never read back (write-only) -- but
    # the toast-diffing baseline must be reset here, before render() below
    # calls _sync_earned_and_toast(), so a loaded save's already-earned
    # achievements don't all fire toasts on load.
    runstate._previously_earned_ids = _earned_snapshot()

    render()
    return True


def sandbox_enter():
    """Sets the real corporation aside and starts a practice one. True when the sandbox is on."""
    if runstate.sandbox_active and (runstate.crisis_active is not None or runstate.chain_active is not None):
        sandbox_leave()  # J-9, J-5: leave a crisis or a chain puzzle first, then start the sandbox from the real game
    if runstate.sandbox_active:
        return True
    _sandbox_set_real_aside()
    _reset_running_tables()
    _apply_state(_sandbox_state())
    _sandbox_top_up()
    render()
    return True


def _sandbox_restore_real(apply_snapshot=True):
    """Puts the real corporation back exactly as it was. With apply_snapshot False the caller loads a save instead."""
    real = runstate._sandbox_real
    runstate.sandbox_active = False
    runstate._sandbox_real = None
    _crisis_clear()
    _chain_clear()
    if real is None:
        return
    if apply_snapshot:
        _reset_running_tables()
        _apply_state(copy.deepcopy(real["snapshot"]))
        runstate.guild_cooldown = real["guild_cooldown"]
        runstate.run_seed, runstate.run_seed_pinned = real["seed"]
    else:
        _reset_running_tables()


def sandbox_leave():
    """Leaves the sandbox; the real corporation is back and untouched. True when it is."""
    if not runstate.sandbox_active:
        return True
    _sandbox_restore_real()
    return True
