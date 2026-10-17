"""The small multipliers that feed a sale price or output: market weather, the Meridian Cartel's contest, the Cartel squeeze, the legacy sale bonus."""

import trade_runstate as runstate
from trade_colony import active_colony_ids, colony_needing
from trade_rules import ALL_COLONIES


guild_contract = {"good": None, "destination": None, "units": 0, "delivered": 0, "ticks_left": 0, "reward": 0}

LEGACY_SALE_BONUS = 0.02  # +2% on every sale per legacy level (max +10%)


def legacy_sale_multiplier():
    return 1.0 + LEGACY_SALE_BONUS * runstate.legacy_level


WEATHER_BOOM = 0.30
WEATHER_SLUMP = -0.25
WEATHER_CASCADE_SHARE = 0.5


def weather_active_event():
    ev = runstate.weather_event
    if runstate.weather_enabled and ev is not None and ev["wait"] == 0 and ev["left"] > 0:
        return ev
    return None


def weather_cascade_good(good):
    """The good made at the colony that needs `good` (it follows the event at half strength), if reachable."""
    consumer = colony_needing(good)
    if consumer is None or consumer not in active_colony_ids():
        return None
    other = ALL_COLONIES[consumer]["produces"]
    return other if other != good else None


def weather_multiplier(good):
    ev = weather_active_event()
    if ev is None:
        return 1.0
    effect = WEATHER_BOOM if ev["kind"] == "boom" else WEATHER_SLUMP
    if good == ev["good"]:
        return 1.0 + effect
    if good == weather_cascade_good(ev["good"]):
        return 1.0 + effect * WEATHER_CASCADE_SHARE
    return 1.0


MERIDIAN_PRESSURE = 0.12


def meridian_exclusive_good():
    """The good an active exclusive Trade Guild contract covers (Meridian keeps away from it), or None."""
    return guild_contract["good"] if runstate.guild_state == "active" else None


def meridian_active_contest():
    if not runstate.meridian_enabled or runstate.meridian_contest is None:
        return None
    if runstate.meridian_contest["good"] == meridian_exclusive_good():
        return None
    return runstate.meridian_contest


def meridian_multiplier(good):
    contest = meridian_active_contest()
    return 1.0 - MERIDIAN_PRESSURE if contest is not None and contest["good"] == good else 1.0


CARTEL_SPIKE = 0.30

CARTEL_SLUMP = -0.25

cartel_effects = {}  # good -> {"kind": "spike" | "slump", "left": ticks}


def cartel_multiplier(good):
    effect = cartel_effects.get(good)
    if effect is None:
        return 1.0
    return 1.0 + (CARTEL_SPIKE if effect["kind"] == "spike" else CARTEL_SLUMP)
