"""Seasons, rain and drought episodes, the perfect-season streak and the end of a season."""

import canopy_runstate as runstate
from canopy_helpers import _announce, _flash_element, _gb_hash, _gb_toast, _log_event
from canopy_rules import SEASONS, SEASON_CYCLE_TICKS, SEASON_LABEL, current_season, current_season_multiplier
from canopy_worldvars import (
    DUSK_TICKS_IN_AUTUMN, PERFECT_SEASON_MIN_RELATIONS, PERFECT_STREAK_BONUS_PER_SEASON,
    PERFECT_STREAK_MAX_BONUS_SEASONS, SEASON_FRAME_LETTER, SEASON_FRAMES_MAX, WEATHER_BLOCK_TICKS,
    WEATHER_DROUGHT_MULTIPLIER, WEATHER_DURATION_TICKS, WEATHER_EPISODE_PERCENT, WEATHER_FIRST_TICK,
    WEATHER_RAIN_MULTIPLIER, WEATHER_SEASON_KIND, season_frames,
)


# --- GB-23: weather ---------------------------------------------------------

def _season_at(tick):
    return SEASONS[(tick // SEASON_CYCLE_TICKS) % len(SEASONS)]


def _weather_episode(tick):
    """(kind, start_tick) of the rain/drought episode covering `tick`, or
    None. A pure function of the tick, so it needs no saved state and the
    counterfactual can price it in. Rain comes in spring and autumn, drought in
    summer, nothing in winter; at most one episode starts per block."""
    block = tick // WEATHER_BLOCK_TICKS
    for b in (block - 1, block):
        if b < 0 or _gb_hash(b, 23) % 100 >= WEATHER_EPISODE_PERCENT:
            continue
        start = b * WEATHER_BLOCK_TICKS + _gb_hash(b, 11) % (WEATHER_BLOCK_TICKS - 4)
        if start < WEATHER_FIRST_TICK or not (start <= tick < start + WEATHER_DURATION_TICKS):
            continue
        kind = WEATHER_SEASON_KIND[_season_at(start)]
        if kind:
            return kind, start
    return None


def weather_at(tick):
    episode = _weather_episode(tick)
    return episode[0] if episode else None


def weather_multiplier_at(tick):
    kind = weather_at(tick)
    if kind == "rain":
        return WEATHER_RAIN_MULTIPLIER
    if kind == "drought":
        return WEATHER_DROUGHT_MULTIPLIER
    return 1.0


def weather_ticks_left():
    episode = _weather_episode(runstate.forest_tick)
    return episode[1] + WEATHER_DURATION_TICKS - runstate.forest_tick if episode else 0


# --- GB-30: Perfect Season streak ---------------------------------------------


def _note_season_relations():
    if runstate.season_min_relations is None:
        runstate.season_min_relations = runstate.community_relations
    else:
        runstate.season_min_relations = min(runstate.season_min_relations, runstate.community_relations)


def perfect_season_status():
    """(on_track, reason): whether this season is still perfect so far. A
    season is perfect when no main-forest plot was cleared (nothing turned BARE
    and cut your standing value) and community trust never sank below
    PERFECT_SEASON_MIN_RELATIONS (a run of refusals you would come to regret)."""
    if runstate.season_cleared:
        return False, "a plot was cleared this season"
    low = runstate.season_min_relations if runstate.season_min_relations is not None else runstate.community_relations
    if low < PERFECT_SEASON_MIN_RELATIONS:
        return False, f"community trust dipped below {PERFECT_SEASON_MIN_RELATIONS}"
    return True, ""


def _end_season():
    """Called on the first tick of each new season: scores the season that just
    ended, then starts a fresh one."""
    _note_season_relations()
    on_track, reason = perfect_season_status()
    ended = SEASON_LABEL[_season_at(runstate.forest_tick - 1)]
    if on_track:
        runstate.perfect_streak += 1
        _log_event(
            "season",
            f"Perfect Season: {ended} ended with every plot standing and the village's trust intact "
            f"(streak {runstate.perfect_streak})",
        )
        if runstate.perfect_streak in (1, 3, 5):
            bonus = round(min(runstate.perfect_streak, PERFECT_STREAK_MAX_BONUS_SEASONS) * PERFECT_STREAK_BONUS_PER_SEASON * 100)
            _gb_toast(f"\U0001F525 Perfect Season x{runstate.perfect_streak}: +{bonus}% growth")
        _flash_element("perfect-streak-text")
    else:
        if runstate.perfect_streak > 0:
            _log_event("season", f"{ended} broke a {runstate.perfect_streak}-season Perfect Season streak: {reason}")
        runstate.perfect_streak = 0
    runstate.season_cleared = False
    runstate.season_min_relations = runstate.community_relations
    season_frames.append({
        "n": runstate.forest_tick // SEASON_CYCLE_TICKS,
        "label": ended,
        "cols": runstate.GRID_COLS,
        "cells": "".join("X" if plot.blocked else SEASON_FRAME_LETTER[plot.state] for plot in runstate.plots),
    })
    del season_frames[:-SEASON_FRAMES_MAX]
    _announce(
        f"{SEASON_LABEL[current_season()]} begins, growth x{current_season_multiplier():.2f}"
    )  # B-7


def is_dusk_window(tick=None):
    """The night-tinted late-autumn ticks: the last DUSK_TICKS_IN_AUTUMN of autumn."""
    tick = runstate.forest_tick if tick is None else tick
    return _season_at(tick) == "autumn" and tick % SEASON_CYCLE_TICKS >= SEASON_CYCLE_TICKS - DUSK_TICKS_IN_AUTUMN
