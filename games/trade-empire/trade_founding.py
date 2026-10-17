"""Founding a new corporation: legacy levels and starting credits, founding conditions from the seed, the immediate effect of a bought charter perk, the endgame test."""

import trade_runstate as runstate
from trade_charter import (
    CHARTER_PERKS, COLONIAL_GOODWILL_START_BONUS, FOUNDING_SEED_MAX, FOUNDING_STRETCHED_NEED,
    FOUNDING_THRIVING_NEED, can_buy_charter_perk, charter_rng, founding_from_seed,
)
from trade_colony import colony_states, galaxy_expansion_unlocked
from trade_effects import legacy_sale_multiplier
from trade_market import run_stream
from trade_research import max_automated_ships
from trade_rules import COLONIES
from trade_ships import automated_ship_count, automation_slots_available, ships


# J21 -- "trade empire legacy": once the endgame is reached, the player may
# found a NEW corporation. The world resets to a fresh start, but each
# founding permanently raises a small legacy bonus (built independently of
# any shared meta-progression module, per Z3's resolution). It rides the
# save file (so it travels with the account's save), never localStorage.
LEGACY_MAX_LEVEL = 5
LEGACY_STARTING_CREDITS = 150  # extra starting credits per legacy level


def legacy_starting_credits(level=None):
    return LEGACY_STARTING_CREDITS * (runstate.legacy_level if level is None else level)


def can_found_new_corporation():
    # O-1: renewal is no longer capped (the legacy BONUS still is, at
    # LEGACY_MAX_LEVEL); the charter tree and ledger keep growing.
    return runstate.endgame_reached and runstate._fresh_state is not None and not runstate.sandbox_active  # Z-18: no renewal from the sandbox


def legacy_summary_text():
    if runstate.legacy_level <= 0:
        return "Legacy: none yet — reach the endgame to renew the charter with a permanent bonus."
    maxed = " (maxed)" if runstate.legacy_level >= LEGACY_MAX_LEVEL else ""
    return (
        f"Legacy level {runstate.legacy_level}/{LEGACY_MAX_LEVEL}{maxed}: +{legacy_starting_credits():,} starting credits "
        f"and +{round((legacy_sale_multiplier() - 1.0) * 100)}% on every sale."
    )


def buy_charter_perk(perk_id):
    if not can_buy_charter_perk(perk_id):
        return False
    runstate.charter_perks.add(perk_id)
    _apply_founding_perk(perk_id)
    return True


def _apply_founding_perk(perk_id):
    """Founding perks act on the world once (at a renewal, or the moment they
    are bought). Everything else is a live modifier read where it applies."""
    if perk_id == "standing_convoy":
        ship = ships["1"]
        if ship.purchased and not ship.automated and automation_slots_available():
            ship.automated = True
    elif perk_id == "colonial_goodwill":
        for colony_id in COLONIES:
            state = colony_states.get(colony_id)
            if state is not None:
                state.need_satisfaction = min(1.0, state.need_satisfaction + COLONIAL_GOODWILL_START_BONUS)


def apply_founding_conditions():
    """Called once, right after a renewal reset: rolls a fresh seed, sets the
    thriving pair against the stretched rest, docks ships 1 and 2 at the pair
    and applies any founding perks."""
    rng = charter_rng if charter_rng is not None else run_stream("charter", runstate.charters_completed)
    runstate.founding_seed = rng.randint(1, FOUNDING_SEED_MAX)
    info = founding_from_seed(runstate.founding_seed)
    for colony_id in COLONIES:
        state = colony_states.get(colony_id)
        if state is not None:
            state.need_satisfaction = FOUNDING_THRIVING_NEED if colony_id in info["pair"] else FOUNDING_STRETCHED_NEED
    ships["1"].location = info["pair"][0]
    ships["2"].location = info["pair"][1]
    for perk_id in sorted(runstate.charter_perks):
        if CHARTER_PERKS[perk_id].get("founding"):
            _apply_founding_perk(perk_id)


def endgame_criteria_met():
    """"Fully automated fleet" means every automation slot the player
    has unlocked is filled, not literally every ship -- the automation
    slot cap (currently 2, or 3 with its own research node) is well
    below the 4-ship roster, so requiring all 4 would make this
    unreachable."""
    return (
        automated_ship_count() >= max_automated_ships()
        and runstate.fleet_priority_enabled
        and galaxy_expansion_unlocked()
    )
