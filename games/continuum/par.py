"""Continuum -- K-26: the par-time badges.

A run is "finished" when the settlement reaches the last era (the Relay Age,
the same test the Civilization Summary calls `journey_complete`). Two badges
ask whether it got there quickly, each against a par set per starting scenario:

- Seasons par: reach the last era within `par_seasons(scenario)` seasons.
- Time par: reach it within `par_minutes(scenario, ...)` minutes of play (the
  game's own "Time played" readout, which does not count long idle gaps).

How the pars are set. Nothing here comes from playtesting a full run. A
settlement cannot get bigger faster than `sim.GROWTH_RATE` people a season (one
birth takes `1 / GROWTH_RATE` seasons of surplus and housing), and every era
change needs a minimum population (`transition.TRANSITION_REQUIREMENTS`). So
the fewest seasons any run can take is the people it must grow, divided by the
growth rate, and the least real time is those seasons priced at each era's
season length and the fastest speed (4x). Par is that floor times a margin per
scenario (`SEASONS_MARGIN`, `MINUTES_MARGIN`), rounded up to a tidy number: a
reachable target for a tight, well-planned run, never a record. Because the
floor is computed from the game's own tables, a rebalance moves the par with it
and the badge stays honest.

The result is stored when the last era is entered, in `campaign.ui["par"]`
(`{"season", "seconds", "scenario"}`), validated on every read. Settlements
already in the last era when this was added have no record, so they cannot earn
the badge retroactively; a consulting case never records one (it starts mid-arc).

Pure functions only (no DOM, no clock): `game.py` supplies the numbers.
"""

import math

import sim
import transition

KEY = "par"
SPEED_MAX = 4  # the fastest game speed, used for the time floor
# Margin on top of the theoretical floor, per starting scenario. The harsher
# opening starts smaller and gets more room; the generous one gets less.
SEASONS_MARGIN = {"standard": 1.30, "fertile": 1.25, "frontier": 1.40, "refuge": 1.30}
MINUTES_MARGIN = {"standard": 1.60, "fertile": 1.55, "frontier": 1.70, "refuge": 1.60}
DEFAULT_MARGIN = (1.30, 1.60)


def final_era():
    return sim.ERA_ORDER[-1]


def _populations():
    """[(era, population needed to leave it)] in era order."""
    out = []
    for era in sim.ERA_ORDER:
        requirement = transition.TRANSITION_REQUIREMENTS.get(era)
        if requirement is not None:
            out.append((era, int(requirement["min_population"])))
    return out


def start_population(scenario):
    return int(sim.scenario_config(scenario)["population"])


def floor_seasons(scenario):
    """The fewest seasons any run could take to reach the last era."""
    needed = max(pop for _era, pop in _populations()) - start_population(scenario)
    return max(1, math.ceil(needed / sim.GROWTH_RATE))


def floor_seconds_at_top_speed(scenario, season_seconds):
    """The least real time, in seconds, at the fastest speed. `season_seconds`
    maps an era id to seconds per season at 1x."""
    seconds = 0.0
    previous = start_population(scenario)
    for era, pop in _populations():
        grow = max(0, pop - previous)
        seasons = math.ceil(grow / sim.GROWTH_RATE)
        seconds += seasons * float(season_seconds.get(era, 10.0)) / SPEED_MAX
        previous = max(previous, pop)
    return seconds


def _round_up(value, step):
    return int(math.ceil(value / step) * step)


def par_seasons(scenario):
    margin = SEASONS_MARGIN.get(scenario, DEFAULT_MARGIN[0])
    return _round_up(floor_seasons(scenario) * margin, 10)


def par_minutes(scenario, season_seconds):
    margin = MINUTES_MARGIN.get(scenario, DEFAULT_MARGIN[1])
    return _round_up(floor_seconds_at_top_speed(scenario, season_seconds) / 60.0 * margin, 5)


def clean(raw):
    """A validated result dict, or None for anything unusable."""
    if not isinstance(raw, dict):
        return None
    season, seconds, scenario = raw.get("season"), raw.get("seconds"), raw.get("scenario")
    if isinstance(season, bool) or not isinstance(season, int) or season < 1:
        return None
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
        return None
    if not isinstance(scenario, str) or scenario not in sim.SCENARIOS:
        return None
    return {"season": min(season, 10**7), "seconds": min(float(seconds), 1e9), "scenario": scenario}


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else None


def record(ui, completed_seasons, play_seconds, scenario, already_inherited=False):
    """Stores the result once, on entering the last era. Returns True if stored.

    Refused (False) when one is already stored, when the settlement started
    mid-arc (`already_inherited`, a consulting case) or when the numbers are bad.
    """
    if already_inherited or get(ui) is not None:
        return False
    entry = clean({"season": completed_seasons, "seconds": play_seconds, "scenario": scenario})
    if entry is None:
        return False
    ui[KEY] = entry
    return True


def seasons_earned(entry):
    entry = clean(entry)
    return entry is not None and entry["season"] <= par_seasons(entry["scenario"])


def time_earned(entry, season_seconds):
    entry = clean(entry)
    return entry is not None and entry["seconds"] <= par_minutes(entry["scenario"], season_seconds) * 60.0


def lines(scenario, season_seconds, entry, now_season, now_seconds):
    """The summary panel's par text, one string per line."""
    entry = clean(entry)
    if entry is not None:
        scenario = entry["scenario"]
    label = sim.scenario_config(scenario)["label"]
    p_seasons = par_seasons(scenario)
    p_minutes = par_minutes(scenario, season_seconds)
    last = sim.ERA_LABEL[final_era()]
    out = [
        f"Par for {label}: reach the {last} within {p_seasons} seasons (Seasons par), "
        f"or within {p_minutes} minutes of play (Time par).",
    ]
    if entry is None:
        out.append(f"So far: season {now_season}, {now_seconds / 60.0:.0f} minutes played. Not at the {last} yet.")
        return out
    mins = entry["seconds"] / 60.0
    out.append(f"Reached the {last} at season {entry['season']} after {mins:.0f} minutes.")
    out.append(
        "Seasons par: " + ("earned." if seasons_earned(entry) else f"not earned (par {p_seasons}).")
    )
    out.append(
        "Time par: " + ("earned." if time_earned(entry, season_seconds) else f"not earned (par {p_minutes} min).")
    )
    return out
