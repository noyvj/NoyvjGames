"""The season indicator, the screen-reader announcer, selection announcements and the season forecast."""

from js import document

import canopy_runstate as runstate
from canopy_effects import current_perfect_streak_multiplier
from canopy_helpers import _el, _plot_ref, _shared_announce
from canopy_rules import (
    ACCRUING_STATES, BARE, REPLANTING, SEASONS, SEASON_CYCLE_TICKS, SEASON_GROWTH_MULTIPLIER, SEASON_ICON,
    SEASON_LABEL, STATE_LABEL, current_season, ticks_until_next_season,
)
from canopy_weather import (
    _weather_episode, is_dusk_window, perfect_season_status, weather_at, weather_multiplier_at,
    weather_ticks_left,
)
from canopy_worldvars import (
    PERFECT_SEASON_MIN_RELATIONS, PERFECT_STREAK_BONUS_PER_SEASON, PERFECT_STREAK_MAX_BONUS_SEASONS,
    WEATHER_DURATION_TICKS, WEATHER_ICON, WEATHER_LABEL, _announce_queue,
)


def render_season_indicator():
    season = current_season()
    root = getattr(document, "documentElement", None)  # B-17: seasonal foliage colours come from this attribute
    if root is not None and hasattr(root, "setAttribute"):
        root.setAttribute("data-season", season)
    next_season = SEASONS[(SEASONS.index(season) + 1) % len(SEASONS)]
    season_el = _el("season-text")
    if season_el is not None:
        season_el.innerText = (
            f"{SEASON_ICON[season]} {SEASON_LABEL[season]} "
            f"· {ticks_until_next_season()} ticks to {SEASON_LABEL[next_season]}"
        )
    weather = weather_at(runstate.forest_tick)
    weather_el = _el("weather-text")
    if weather_el is not None:
        if weather is None:
            weather_el.hidden = True
            weather_el.innerText = ""
        else:
            change = round((weather_multiplier_at(runstate.forest_tick) - 1) * 100)
            weather_el.hidden = False
            weather_el.innerText = (
                f"{WEATHER_ICON[weather]} {WEATHER_LABEL[weather]}: growth {change:+d}% "
                f"· {weather_ticks_left()} ticks left"
            )
    on_track, reason = perfect_season_status()
    streak_el = _el("perfect-streak-text")
    if streak_el is not None:
        bonus = round((current_perfect_streak_multiplier() - 1) * 100)
        streak_el.innerText = f"\U0001F525 Perfect Season streak: {runstate.perfect_streak}" + (f" (+{bonus}% growth)" if bonus else "")
        status = "on track this season" if on_track else f"broken this season ({reason})"
        streak_el.title = (
            "End a season without clearing any plot and without community trust sinking below "
            f"{PERFECT_SEASON_MIN_RELATIONS} to add a flame: +{round(PERFECT_STREAK_BONUS_PER_SEASON * 100)}% growth each, "
            f"up to +{round(PERFECT_STREAK_BONUS_PER_SEASON * PERFECT_STREAK_MAX_BONUS_SEASONS * 100)}%. "
            f"This season: {status}."
        )
        streak_el.setAttribute("aria-label", f"Perfect Season streak {runstate.perfect_streak}. {streak_el.title}")
    grid = _el("plot-grid")
    if grid is not None:
        for kind in ("rain", "drought"):
            if kind == weather:
                grid.classList.add(f"plot-grid--{kind}")
            else:
                grid.classList.remove(f"plot-grid--{kind}")
        if is_dusk_window():
            grid.classList.add("plot-grid--dusk")
        else:
            grid.classList.remove("plot-grid--dusk")


# --- B-7: screen-reader announcer, C / R hotkeys -------------------------------------------------------------


def render_announcer():
    if not _announce_queue:
        return
    text = ". ".join(m.rstrip(". ") for m in _announce_queue)
    del _announce_queue[:]
    if _shared_announce(text):
        return
    element = _el("sr-announcer")
    if element is not None:
        # A live region only speaks when its text changes, so a repeated message (a second refusal, the same
        # selection again) alternates an invisible zero-width space.
        runstate._announce_flip = not runstate._announce_flip
        element.innerText = text + ("\u200b" if runstate._announce_flip else "")


def selection_announcement(index):
    """What the live region says when a plot is selected (Enter, Space or a click): which plot, what it is, what keys act on it."""
    plot = runstate.plots[index]
    text = f"Selected {_plot_ref(index)}: {STATE_LABEL[plot.state]}, value {plot.value:.1f}, soil {round(plot.productivity_multiplier() * 100)}%"
    if plot.state in ACCRUING_STATES and index != runstate.heart_tree_index:
        text += ". Press C to clear it or K to clear-cut it"
    elif plot.state == BARE:
        text += ". Press R to replant it"
    return text


def _hotkey_refusal(index, action):
    """Why C, K or R did nothing on the selected plot, in a sentence for the live region."""
    plot = runstate.plots[index]
    ref = _plot_ref(index)
    if runstate.survey_mode and action != "replant":
        return f"{ref}: Survey mode is on. Use the Clear button to add it to the plan, or leave Survey mode"
    if action == "replant":
        return f"{ref} is {STATE_LABEL[plot.state].lower()}: only a bare plot can be replanted"
    if index == runstate.heart_tree_index:
        return "The Heart Tree is never felled"
    if plot.state == BARE:
        return f"{ref} is already bare: nothing to clear. Press R to replant it"
    if plot.state == REPLANTING:
        return f"{ref} is replanting: wait for it to recover before clearing it"
    return f"{ref} cannot be cleared right now"


# --- B-12: season forecast -----------------------------------------------------------------------------------

def _next_weather_episode():
    """(kind, ticks until it starts, start tick) of the next rain or drought episode that has not
    started yet, or None. weather_at() is a pure function of the tick, so this is exact."""
    for ahead in range(1, SEASON_CYCLE_TICKS * len(SEASONS) + 1):  # a full year: episodes can be 100+ ticks apart
        episode = _weather_episode(runstate.forest_tick + ahead)
        if episode is not None and episode[1] > runstate.forest_tick:
            return episode[0], episode[1] - runstate.forest_tick, episode[1]
    return None


def season_forecast_text():
    first = SEASONS[(SEASONS.index(current_season()) + 1) % len(SEASONS)]
    second = SEASONS[(SEASONS.index(first) + 1) % len(SEASONS)]
    ticks_first = ticks_until_next_season()
    ticks_second = ticks_first + SEASON_CYCLE_TICKS
    text = (
        f"Forecast: {SEASON_LABEL[first]} x{SEASON_GROWTH_MULTIPLIER[first]:.2f} in {ticks_first} ticks, "
        f"then {SEASON_LABEL[second]} x{SEASON_GROWTH_MULTIPLIER[second]:.2f} in {ticks_second} ticks"
    )
    upcoming = _next_weather_episode()
    if upcoming is not None:
        kind, begins_in, _start = upcoming
        change = round((weather_multiplier_at(runstate.forest_tick + begins_in) - 1) * 100)
        text += (
            f" · {WEATHER_ICON[kind]} {WEATHER_LABEL[kind]} (growth {change:+d}%) "
            f"in {begins_in} ticks, lasting {WEATHER_DURATION_TICKS}"
        )
    return text


def render_season_forecast():
    element = _el("season-forecast")
    if element is not None:
        element.innerText = season_forecast_text()
