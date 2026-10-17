"""get_state(): everything that goes into a save."""

import copy

import trade_runstate as runstate
from trade_achievements import achievement_ids_earned
from trade_blackout import blackout_bought
from trade_blueprints import blueprints
from trade_cartel import cartel_last
from trade_colony import colony_states
from trade_effects import cartel_effects, guild_contract
from trade_exchange import exchange_fills, exchange_orders
from trade_ghost import _ghost_for_save
from trade_market import (
    good_profit_recent, good_profit_total, good_trip_count, market_crash_ever, market_multiplier,
    need_history, price_history, price_memory, run_seed_draws, stockpile,
)
from trade_records import _records_for_save
from trade_ships import ships, trade_posts


# @@NEW-FEATURES-END@@ (new feature blocks are inserted above this line)


# ===========================================================================
# Save widget contract (planning/SAVE-BUTTON-INTEGRATION.md) — the shared
# shared/save-widget.js drop-in calls these two functions directly via
# Pyodide globals; nothing here needs to be wired to a button. get_state()
# returns a plain, JSON-serialisable dict of everything that makes a
# session distinct (ships, colonies, market, research, fleet priority,
# endgame progress); load_state() is its exact inverse, restoring onto the
# live module state field-by-field with a fallback to whatever's already
# live for any key an older/newer save doesn't carry — the same
# forward/backward-compatibility discipline every other game on the hub
# uses (see BCM114-DEV-LOG.md's 2026-09-02 entries for why bare `data[key]`
# indexing is the wrong default here).
# ===========================================================================


def get_state():
    if runstate.sandbox_active:  # Z-18: a save, an autosave or a board read while the sandbox is on is the REAL game
        return copy.deepcopy(runstate._sandbox_real["snapshot"])
    return {
        "ships": {
            ship_id: {
                "location": ship.location,
                "origin": ship.origin,
                "destination": ship.destination,
                "cargo_good": ship.cargo_good,
                "cargo_qty": ship.cargo_qty,
                "transit_ticks_remaining": ship.transit_ticks_remaining,
                "transit_total_ticks": ship.transit_total_ticks,
                "automated": ship.automated,
                "purchased": ship.purchased,
                "archetype": ship.archetype,
                **({"hull": dict(ship.hull)} if ship.hull is not None else {}),
                "name": ship.name,
                "idle_ticks": ship.idle_ticks,
                "route_key": sorted(ship.route_key) if ship.route_key else None,
                "route_legs": ship.route_legs,
                "total_earned": ship.total_earned,
                "units_moved": ship.units_moved,
                "ticks_owned": ship.ticks_owned,
                "units_by_good": dict(ship.units_by_good),
                "captain": ship.captain,
                "captain_deliveries": ship.captain_deliveries,
            }
            for ship_id, ship in ships.items()
        },
        "total_profit": runstate.total_profit,
        "sale_log": list(runstate.sale_log),
        "market_multiplier": dict(market_multiplier),
        "colony_states": {
            colony_id: {
                "need_satisfaction": state.need_satisfaction,
                "development_level": state.development_level,
                "cumulative_delivered": state.cumulative_delivered,
                "secondary_need_satisfaction": state.secondary_need_satisfaction,
                "neglect_ticks": state.neglect_ticks,
                "demand_ticks_left": state.demand_ticks_left,
                "demand_cooldown": state.demand_cooldown,
                "demands_made": state.demands_made,
                "concessions_granted": state.concessions_granted,
            }
            for colony_id, state in colony_states.items()
        },
        "research_points": runstate.research_points,
        "unlocked_research": sorted(runstate.unlocked_research),
        "fleet_priority_enabled": runstate.fleet_priority_enabled,
        "endgame_reached": runstate.endgame_reached,
        "ticks_since_endgame": runstate.ticks_since_endgame,
        "total_sales_count": runstate.total_sales_count,
        "max_profit_ever": runstate.max_profit_ever,
        "goods_sold_ever": sorted(runstate.goods_sold_ever),
        "ever_repositioned": runstate.ever_repositioned,
        "market_crash_ever": dict(market_crash_ever),
        "good_profit_total": dict(good_profit_total),
        "good_trip_count": dict(good_trip_count),
        "good_profit_recent": {g: list(v) for g, v in good_profit_recent.items()},
        "price_history": {good: list(values) for good, values in price_history.items()},
        "need_history": {colony_id: list(values) for colony_id, values in need_history.items()},
        "seasonal_demand": {"enabled": runstate.seasonal_demand_enabled, "ticks": runstate.season_ticks},
        "cross_system_units": runstate.cross_system_units,
        "trade_posts": list(trade_posts),
        "stockpile": {good: units for good, units in stockpile.items() if units},
        # J-4 -- only written once the player has made a stockpile trade.
        **({"price_memory": dict(price_memory)} if price_memory else {}),
        # J-7 -- fleet captains; only written once a seat is earned or a captain met.
        **(
            {
                "captains": {
                    "earned": sorted(runstate.captain_earned),
                    "assignments": {k: v for k, v in runstate.captain_assignments.items() if v},
                    "met": sorted(runstate.captains_met),
                }
            }
            if runstate.captain_earned or runstate.captains_met or any(runstate.captain_assignments.values())
            else {}
        ),
        # J21 -- only written once a new corporation has been founded, so a
        # first-run save is unchanged.
        **({"legacy": {"level": runstate.legacy_level, "achievements": list(runstate.legacy_achievements)}} if runstate.legacy_level else {}),
        # O-3 -- the lifetime ledger, only written once anything has been moved.
        **(
            {
                "ledger": {
                    "units": runstate.ledger_units_moved,
                    "routes": runstate.ledger_routes_established,
                    "hard_completed": runstate.ledger_hard_completed,
                    "routes_seen": sorted(sorted(key) for key in runstate.ledger_routes_seen),
                    "charter_units": runstate.ledger_charter_units,
                }
            }
            if runstate.ledger_units_moved or runstate.ledger_routes_established or runstate.ledger_hard_completed or runstate.ledger_routes_seen
            or runstate.ledger_charter_units
            else {}
        ),
        # O-1/O-2/O-4 -- charter tree, points and founding seed; only written
        # once a charter has been renewed (or a harder charter is queued).
        **(
            {
                "charter": {
                    "completed": runstate.charters_completed,
                    "points": runstate.charter_points_earned,
                    "perks": sorted(runstate.charter_perks),
                    "seed": runstate.founding_seed,
                    "hard": runstate.hard_charter_active,
                    "hard_next": runstate.hard_charter_next,
                    "career": [dict(entry) for entry in runstate.charter_career],
                }
            }
            if runstate.charters_completed or runstate.charter_points_earned or runstate.charter_perks or runstate.founding_seed
            or runstate.hard_charter_active or runstate.hard_charter_next
            else {}
        ),
        # J3 -- only written once the guild has done anything at all.
        **(
            {"guild": {"state": runstate.guild_state, **guild_contract, "completed": runstate.guild_completed, "failed": runstate.guild_failed,
                       **({"offers": runstate.guild_offers} if runstate.guild_offers else {})}}
            if runstate.guild_state != "none" or runstate.guild_completed or runstate.guild_failed or runstate.guild_offers
            else {}
        ),
        # J-29/J-30 -- Blackout and the lifetime records; only written once used.
        **(
            {"blackout": {"enabled": runstate.blackout_enabled, "clean": runstate.blackout_clean, "done": runstate.blackout_done,
                          "bought": sorted(blackout_bought)}}
            if runstate.blackout_enabled or runstate.blackout_done or blackout_bought
            else {}
        ),
        **(
            {"weather": {"enabled": runstate.weather_enabled, "n": runstate.weather_n,
                         "event": dict(runstate.weather_event) if runstate.weather_event is not None else None}}
            if runstate.weather_enabled or runstate.weather_n
            else {}
        ),
        **({"records": _records_for_save()} if _records_for_save() else {}),
        **({"ghost": _ghost_for_save()} if _ghost_for_save() else {}),  # Z-3e5
        **({"expedition": dict(runstate.expedition)} if runstate.expedition is not None else {}),
        **({"blueprints": [dict(d) for d in blueprints]} if blueprints else {}),
        **({"hub": runstate.hub_colony} if runstate.hub_colony is not None else {}),
        **(
            {"meridian": {
                "enabled": runstate.meridian_enabled, "ticks": runstate.meridian_ticks, "units": runstate.meridian_units,
                "contest": dict(runstate.meridian_contest) if runstate.meridian_contest is not None else None,
                "shield": dict(runstate.meridian_shield) if runstate.meridian_shield is not None else None,
                "intel": runstate.meridian_intel_bought,
            }}
            if runstate.meridian_enabled or runstate.meridian_ticks or runstate.meridian_intel_bought
            else {}
        ),
        **(
            {"cartel": {"effects": {g: dict(e) for g, e in cartel_effects.items()}, "last": dict(cartel_last)}}
            if cartel_effects or cartel_last
            else {}
        ),
        **(
            {"exchange": {"orders": [dict(o) for o in exchange_orders], "fills": [dict(f) for f in exchange_fills]}}
            if exchange_orders or exchange_fills
            else {}
        ),
        "route_hazards": {
            "hazards": runstate.route_hazards_enabled,
            "insurance": runstate.route_insurance_enabled,
            "disruptions": runstate.disruptions_suffered,
            "payouts": runstate.insurance_payouts,
            "premiums": runstate.premiums_paid,
            **({"rolls": runstate.hazard_rolls} if runstate.hazard_rolls else {}),
        },
        # Z-1b -- the run seed, only once it has been typed or used (a brand-new save is unchanged).
        **({"run_seed": runstate.run_seed} if runstate.run_seed and (runstate.run_seed_pinned or run_seed_draws()) else {}),
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed here, never read back in load_state() below.
        "achievements_earned": achievement_ids_earned(),
    }
