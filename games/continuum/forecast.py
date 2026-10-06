"""Continuum -- a one-season forecast for the HUD dropdowns (engine half).

The HUD shows a handful of headline numbers (People, Food, Materials, Tools,
Knowledge, Land health). Clicking one opens a small dropdown that answers the
question a player actually has when they look at it: "and what happens next
season?" -- "+1 person per season", "-3.0 food per season", "the land is
wearing down".

The one rule this module is built around: the forecast must be what the
simulation will REALLY do, not a second, hand-maintained approximation of it.
sim.py's `advance_season` is deterministic (no RNG anywhere in the season
loop, see its module docstring), so the honest way to predict a season is to
run that exact season on a throwaway copy of the state and read off what
changed. A re-implementation of the production, spoilage and growth maths
here would drift the first time a research node or an era added a term; this
cannot, because it contains no game maths of its own.

Two functions, and nothing else:

  - `preview(state, effects=None)` deep-copies the state, runs one season on
    the COPY, and returns the before/after numbers per HUD stat. The real
    state (resources, season counter, allocation, `last_report`, lagged
    stocks like pollution) and the `effects` dict are never touched.
  - `lines(key, view)` turns one stat's numbers into one to four short
    plain-language sentences for its dropdown. Rounding and wording live
    here, never in `preview`, so the numbers stay exact for anything else
    that wants them.

No DOM code and no `js` imports: game.py (and the PC layout) own rendering.
Nothing is swallowed -- if a probe season raises, the caller sees it.
"""

import copy
import math

import sim

# Anything smaller than this (in the unit the text shows) reads as "no change"
# rather than a misleading "+0.0" / "-0.0".
_EPSILON = 0.05

KEYS = ("population", "food", "materials", "tools", "knowledge", "land_health")


def preview(state, effects=None):
    """What the next season will do, without doing it.

    Returns a dict with exactly the keys in `KEYS`, each a dict of plain
    numbers (no rounding). `delta` is always "after minus before" across the
    probe season, so for tools it includes wear and for food it includes
    anything banked as surplus, not just gathered minus eaten.
    """
    probe = copy.deepcopy(state)
    report = probe.advance_season(effects)

    before = state.resources
    after = probe.resources

    return {
        "population": {
            "now": state.population,
            "housing": state.housing_capacity(effects),
            "delta": probe.population - state.population,
            "births": report["births"],
            "deaths": report["deaths"],
            "idle": state.idle_workers(),
            "growth_before": float(state.growth_progress),
            "growth_after": float(probe.growth_progress),
        },
        "food": {
            "now": float(before["food"]),
            "capacity": float(state.food_storage_capacity(effects)),
            "delta": float(after["food"] - before["food"]),
            "gathered": float(report["food_gathered"]),
            "consumed": float(report["food_consumed"]),
            "spoiled": float(report["spoiled"]),
            "fed_fraction": float(report["fed_fraction"]),
        },
        "materials": {
            "now": float(before["materials"]),
            "delta": float(after["materials"] - before["materials"]),
            "gathered": float(report["materials_gathered"]),
            "spent_on_tools": float(report["tools_made"] * sim.MATERIALS_PER_TOOL),
        },
        "tools": {
            "now": float(before["tools"]),
            "delta": float(after["tools"] - before["tools"]),
        },
        "knowledge": {
            "now": float(before["knowledge"]),
            "delta": float(after["knowledge"] - before["knowledge"]),
        },
        "land_health": {
            "now": float(state.land_health),
            "delta": float(probe.land_health - state.land_health),
            "extraction": float(report["extraction"]),
            "sustainable_yield": float(report["sustainable_yield"]),
        },
    }


# --- wording helpers -----------------------------------------------------

def _amount(x):
    """One decimal, no sign: 8.0"""
    return f"{x:.1f}"


def _plain(x):
    """One decimal, but a whole number drops the '.0': 20 / 19.5"""
    text = f"{x:.1f}"
    return text[:-2] if text.endswith(".0") else text


def _is_zero(x):
    return abs(x) < _EPSILON


def _signed(x):
    """Explicit sign with one decimal: +4.0 / -1.5 (callers handle zero)."""
    return f"{x:+.1f}"


def _per_season(x):
    if _is_zero(x):
        return "No change per season"
    return f"{_signed(x)} per season"


def _people(n):
    n = int(n)
    return "1 person" if n == 1 else f"{n} people"


def _signed_people(n):
    n = int(n)
    if n == 0:
        return "No change"
    sign = "+" if n > 0 else "-"
    return f"{sign}{_people(abs(n))}"


# --- per-stat lines ------------------------------------------------------

def _population_lines(view):
    delta = int(view["delta"])
    out = []
    if delta > 0:
        out.append(
            f"{_signed_people(delta)} per season "
            f"({view['births']} born, {view['deaths']} lost)"
        )
    elif delta < 0:
        out.append(f"{_signed_people(delta)} per season (not enough food)")
    else:
        # Growth builds up over several seasons before a person is actually born, so a settlement
        # can read "no change" while a birth is coming. Say so, and roughly when.
        step = view.get("growth_after", 0.0) - view.get("growth_before", 0.0)
        has_room = view["housing"] - view["now"] > 1e-9
        if has_room and step > 0.01:
            seasons = max(1, math.ceil((1.0 - view["growth_after"]) / step) + 1)
            out.append(f"No change next season, but growth is building (a birth in about {seasons} seasons)")
        else:
            out.append("No change per season")

    housing = view["housing"]
    room = int(housing - view["now"] + 1e-9)
    shelter_for = int(housing)
    if room <= 0:
        out.append(f"Shelter for {shelter_for}, housing is full")
    else:
        out.append(f"Shelter has room for {room} more")

    idle = int(view["idle"])
    if idle <= 0:
        out.append("No idle workers")
    elif idle == 1:
        out.append("1 idle worker")
    else:
        out.append(f"{idle} idle workers")
    return out


def _food_lines(view):
    out = [
        f"{_per_season(view['delta'])}: {_amount(view['gathered'])} gathered, "
        f"{_amount(view['consumed'])} eaten, {_amount(view['spoiled'])} spoiled"
    ]
    out.append(f"Storage {_plain(view['now'])} of {_plain(view['capacity'])}")
    if view["spoiled"] > 0:
        out.append("Food past the storage ceiling spoils")
    if view["fed_fraction"] < 1.0:
        out.append(
            f"Some people would go hungry (only {round(view['fed_fraction'] * 100)}% fed)"
        )
    return out


def _materials_lines(view):
    return [
        f"{_per_season(view['delta'])}: {_amount(view['gathered'])} gathered, "
        f"{_amount(view['spent_on_tools'])} used for tools"
    ]


def _tools_lines(view):
    out = [_per_season(view["delta"])]
    if view["delta"] <= -_EPSILON:
        out.append(
            f"Tools wear out by {sim.TOOL_DECAY_RATE * 100:.0f}% each season; Crafters make new ones"
        )
    return out


def _knowledge_lines(view):
    out = [_per_season(view["delta"])]
    if _is_zero(view["delta"]):
        out.append("Keepers produce knowledge")
    return out


def _land_health_lines(view):
    points = view["delta"] * 100.0
    percent = round(view["now"] * 100)
    harvest = (
        f"Harvest {_amount(view['extraction'])}, "
        f"the land sustains {_amount(view['sustainable_yield'])}"
    )
    if _is_zero(points):
        out = [f"Land health {percent}%, steady"]
        if view["extraction"] > view["sustainable_yield"] + 1e-9:
            # Pinned at its floor: it cannot fall further, but it is not safe.
            out.append(harvest)
        return out

    magnitude = _plain(abs(points))
    noun = "point" if magnitude == "1" else "points"
    sign = "+" if points > 0 else "-"
    if points > 0:
        reason = "recovering"
    else:
        reason = "harvest is above what the land sustains"
    return [
        f"{sign}{magnitude} {noun} per season ({reason})",
        f"Land health {percent}%",
        harvest,
    ]


_BUILDERS = {
    "population": _population_lines,
    "food": _food_lines,
    "materials": _materials_lines,
    "tools": _tools_lines,
    "knowledge": _knowledge_lines,
    "land_health": _land_health_lines,
}


def lines(key, view):
    """One to four short sentences for `key`'s dropdown, given
    `preview(...)[key]`. An unknown key gives []."""
    builder = _BUILDERS.get(key)
    if builder is None:
        return []
    return builder(view)
