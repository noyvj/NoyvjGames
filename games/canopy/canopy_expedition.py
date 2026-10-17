"""The Expedition (GB-3): seeded map, perks tree, scoring, bests and renders."""

import json

import seed as seed_lib
import skill_tree

import canopy_runstate as runstate
from canopy_effects import (
    EXPEDITION_RICH_GROWTH, EXPEDITION_THIN_GROWTH, EXPEDITION_TREE, _expedition_effect_cache,
    expedition_effects, expedition_terrain,
)
from canopy_helpers import (
    _announce, _gb_toast, _log_event, _number_or, _read_local_storage_item, _write_local_storage_item,
)
from canopy_levels import _js_window
from canopy_rules import (
    BARE, DIFFICULTY_NORMAL, GRID_SIZE_PRESETS, SCENARIO_NONE, SEASON_CYCLE_TICKS, expedition_meta,
)
from canopy_valuation import standing_forest_value
from canopy_worldvars import CHALLENGE_NONE, PACE_NORMAL


# ===========================================================================
# GB-3 (2026-10-10): the Expedition. A separate game mode (its own button and panel, not a level and not the base
# game): 12 seasons (EXPEDITION_TICKS) on a map decided by a shareable seed, with fixed upgrades CHOSEN from a skill tree.
# It is not a roguelike run: nothing is random during play, there are no random boons, nothing can be lost, and there is
# no permadeath (no fail state; the run simply ends with a score). The seed (shared/seed.py, "CANOPY-K7F2Q") decides ONLY
# the map: which plots are rich soil (+25% growth), which are thin (-20%) and which four start bare. The upgrade tree uses
# the shared rules (shared/skill_tree.py, drawn by shared/skill-tree.js): 3 points at the start and one more each season,
# free and unlimited to take back and re-spend. The Seed Vault's perks and crews rest during an Expedition so every run
# on a seed is comparable. Leave Expedition goes back to normal play on the same forest; the save format only gains an
# `expedition` key while one is running. See games/canopy/CLAUDE.md.
# ===========================================================================

SEED_GAME = "canopy"
EXPEDITION_SEASONS = 12
EXPEDITION_TICKS = EXPEDITION_SEASONS * SEASON_CYCLE_TICKS
EXPEDITION_START_POINTS = 3
EXPEDITION_MAX_POINTS = EXPEDITION_START_POINTS + EXPEDITION_SEASONS - 1  # a new point at the start of each season after the first
EXPEDITION_RICH_PLOTS = 6
EXPEDITION_THIN_PLOTS = 6
EXPEDITION_BARE_PLOTS = 4

EXPEDITION_PAYOUT_BONUS = 0.15  # manual clears and clear-cuts

EXPEDITION_STORAGE_KEY = "canopy_expedition_v1"
EXPEDITION_BEST_MAX_SEEDS = 40
EXPEDITION_TERRAIN_MARK = {"rich": "▲", "thin": "▽"}

_expedition_proxies = []


def new_expedition_seed():
    """A fresh seed from the operating system's entropy (shared/seed.py), the one place the game draws on chance: it only
    decides the map, never anything during play. Tests replace this function to fix the seed."""
    return seed_lib.new_seed(SEED_GAME)


def _new_expedition_run(seed_text):
    return {"seed": seed_text, "owned": [], "done_tick": None, "score": None}


def expedition_map(seed_text):
    """(rich, thin, bare) plot indices of the normal grid for a seed: sorted lists, 6 + 6 + 4 distinct plots drawn
    from the seed's own "map" stream, so the same seed always gives the same map in Python and in JavaScript."""
    plot_count = GRID_SIZE_PRESETS["normal"][0] * GRID_SIZE_PRESETS["normal"][1]
    picks = seed_lib.Rng(seed_text).fork("map").sample(range(plot_count), EXPEDITION_RICH_PLOTS + EXPEDITION_THIN_PLOTS + EXPEDITION_BARE_PLOTS)
    rich = sorted(picks[:EXPEDITION_RICH_PLOTS])
    thin = sorted(picks[EXPEDITION_RICH_PLOTS:EXPEDITION_RICH_PLOTS + EXPEDITION_THIN_PLOTS])
    bare = sorted(picks[EXPEDITION_RICH_PLOTS + EXPEDITION_THIN_PLOTS:])
    return rich, thin, bare


def _rebuild_expedition_terrain():
    expedition_terrain.clear()
    _expedition_effect_cache.clear()
    if runstate.current_expedition is None:
        return
    rich, thin, _bare = expedition_map(runstate.current_expedition["seed"])
    expedition_terrain.update({i: "rich" for i in rich})
    expedition_terrain.update({i: "thin" for i in thin})


def _apply_expedition_start():
    """Called by reset_session(): the seed's map, and its bare plots (soil untouched, no clear counted)."""
    _rebuild_expedition_terrain()
    if runstate.current_expedition is None:
        return
    for index in expedition_map(runstate.current_expedition["seed"])[2]:
        plot = runstate.plots[index]
        plot.state = BARE
        plot.value = 0.0
        plot.ticks_intact = 0
        plot.biodiversity = 0.0


def expedition_payout_multiplier():
    return 1.0 + EXPEDITION_PAYOUT_BONUS if "exp_trade" in expedition_effects() else 1.0


def expedition_season():
    return min(EXPEDITION_SEASONS, runstate.forest_tick // SEASON_CYCLE_TICKS + 1)


def expedition_points_earned():
    if runstate.current_expedition is None:
        return 0
    return min(EXPEDITION_MAX_POINTS, EXPEDITION_START_POINTS + runstate.forest_tick // SEASON_CYCLE_TICKS)


def expedition_points_free():
    if runstate.current_expedition is None:
        return 0
    return skill_tree.points_left(EXPEDITION_TREE, runstate.current_expedition["owned"], expedition_points_earned())


def expedition_score():
    """Standing forest value plus harvested income, rounded: the one number to compare on a seed."""
    return int(round(standing_forest_value() + runstate.total_income))


def expedition_finished():
    return runstate.current_expedition is not None and runstate.current_expedition["done_tick"] is not None


def expedition_best_for(seed_text):
    return expedition_meta["best"].get(seed_text)


def _save_expedition_meta():
    blob = {"best": dict(expedition_meta["best"]), "finished": expedition_meta["finished"], "last_seed": expedition_meta["last_seed"]}
    _write_local_storage_item(EXPEDITION_STORAGE_KEY, json.dumps(blob))


def _load_expedition_meta():
    """This browser's Expedition records at start-up; anything malformed simply means none."""
    expedition_meta["best"] = {}
    expedition_meta["finished"] = 0
    expedition_meta["last_seed"] = ""
    raw = _read_local_storage_item(EXPEDITION_STORAGE_KEY)
    if not raw:
        return
    try:
        blob = json.loads(raw)
    except (ValueError, TypeError):
        return
    if not isinstance(blob, dict):
        return
    best = blob.get("best")
    if isinstance(best, dict):
        for key, score in best.items():
            if isinstance(key, str) and seed_lib.is_valid(key, SEED_GAME) and seed_lib.normalize(key, SEED_GAME) == key:
                value = _number_or(score, None, 0, 10 ** 9)
                if value is not None and len(expedition_meta["best"]) < EXPEDITION_BEST_MAX_SEEDS:
                    expedition_meta["best"][key] = int(value)
    expedition_meta["finished"] = int(_number_or(blob.get("finished"), 0, 0, 10 ** 6))
    last = blob.get("last_seed")
    if isinstance(last, str) and seed_lib.is_valid(last, SEED_GAME):
        expedition_meta["last_seed"] = seed_lib.normalize(last, SEED_GAME)


def _expedition_settings_ok():
    """An Expedition only exists on the plain game: normal grid, normal difficulty and pace, no challenge, scenario,
    level or custom layout."""
    return (
        runstate.current_grid_size == "normal" and runstate.current_difficulty == DIFFICULTY_NORMAL and runstate.current_challenge == CHALLENGE_NONE
        and runstate.current_pace == PACE_NORMAL and runstate.current_scenario == SCENARIO_NONE and runstate.current_level is None and runstate.current_layout is None
    )


def _finish_expedition():
    """The twelfth season is over: record the score, say so, and let play go on until the player leaves."""
    score = expedition_score()
    seed_text = runstate.current_expedition["seed"]
    runstate.current_expedition["done_tick"] = runstate.forest_tick
    runstate.current_expedition["score"] = score
    previous = expedition_meta["best"].get(seed_text)
    new_best = previous is None or score > previous
    if new_best:
        expedition_meta["best"].pop(seed_text, None)
        expedition_meta["best"][seed_text] = score
        while len(expedition_meta["best"]) > EXPEDITION_BEST_MAX_SEEDS:
            expedition_meta["best"].pop(next(iter(expedition_meta["best"])))
    expedition_meta["finished"] += 1
    _save_expedition_meta()
    note = "a new best on this seed" if new_best and previous is not None else (f"your best here is {previous}" if previous is not None else "your first run on this seed")
    _log_event("expedition", f"Expedition {seed_text} complete: score {score} ({note})", None)
    _record_shared_daily(seed_text, score)  # Z-5c: a run on today's shared seed counts once in the shared daily record
    _gb_toast(f"\U0001F9ED Expedition complete: score {score} ({note}). Keep playing, or leave from the Expedition panel")


def _advance_expedition():
    """On the tick: a new upgrade point at each season start, and the finish after season 12."""
    if runstate.current_expedition is None or runstate.current_expedition["done_tick"] is not None:
        return
    if runstate.forest_tick >= EXPEDITION_TICKS:
        _finish_expedition()
    elif runstate.forest_tick > 0 and runstate.forest_tick % SEASON_CYCLE_TICKS == 0:
        text = f"Expedition: season {expedition_season()} of {EXPEDITION_SEASONS} begins. +1 upgrade point ({expedition_points_free()} to spend)"
        _gb_toast("\U0001F9ED " + text)
        _announce(text)


def expedition_map_text():
    if runstate.current_expedition is None:
        return ""
    return (
        f"Map for {runstate.current_expedition['seed']}: {EXPEDITION_TERRAIN_MARK['rich']} {EXPEDITION_RICH_PLOTS} rich-soil plots "
        f"(+{round((EXPEDITION_RICH_GROWTH - 1) * 100)}% growth), {EXPEDITION_TERRAIN_MARK['thin']} {EXPEDITION_THIN_PLOTS} thin-soil plots "
        f"(-{round((1 - EXPEDITION_THIN_GROWTH) * 100)}% growth), and {EXPEDITION_BARE_PLOTS} plots start bare."
    )


def expedition_status_text():
    if runstate.current_expedition is None:
        return ""
    seed_text = runstate.current_expedition["seed"]
    if runstate.current_expedition["done_tick"] is not None:
        best = expedition_best_for(seed_text)
        return f"Expedition {seed_text} complete: score {runstate.current_expedition['score']} (best on this seed {best}). Leave it from the Expedition panel when you like."
    to_next = SEASON_CYCLE_TICKS - runstate.forest_tick % SEASON_CYCLE_TICKS
    return (
        f"Expedition {seed_text}: season {expedition_season()} of {EXPEDITION_SEASONS}"
        + ("" if expedition_season() >= EXPEDITION_SEASONS else f" ({to_next} ticks to the next)")
        + f". {expedition_points_free()} upgrade point{'s' if expedition_points_free() != 1 else ''} to spend."
    )


def _record_shared_daily(seed_text, score):
    """Z-5c: a finished Expedition whose seed is TODAY's shared seed counts once for the day in the record the hub's Today strip
    reads (`localStorage["noyvj-daily-v1"]`, written by `NoyvjSeed.daily.markCompleted`). The page decides what today is
    (`isDaily`), so an older day's seed or any other seed records nothing. Fails soft: no shared script (pytest, an old page) or
    any error means nothing, and finishing the Expedition is never affected."""
    window = _js_window()
    try:
        daily = getattr(getattr(window, "NoyvjSeed", None), "daily", None)
        if daily is None or not daily.isDaily(SEED_GAME, seed_text):
            return
        from js import Object  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        info = Object.new()
        info.score = int(score)
        info.text = f"Expedition score {int(score)}"
        daily.markCompleted(SEED_GAME, info)
    except Exception:  # noqa: BLE001 -- a courtesy record must never break finishing an Expedition
        pass


def _tell_footer_seed():
    """Put the Expedition's own seed back in the info footer (the shared button shows today's seed the moment it is pressed)."""
    window = _js_window()
    try:
        seed_api = getattr(window, "NoyvjSeed", None)
        if seed_api is not None:
            seed_api.set(runstate.current_expedition["seed"] if runstate.current_expedition is not None else "")
    except Exception:  # noqa: BLE001 -- the footer's seed line is a courtesy
        pass


def expedition_summary_text():
    if runstate.current_expedition is None:
        return ("No Expedition running. Press New seed (or type one a friend shared) and Start Expedition. "
                "You get 3 upgrade points at the start and 1 more every season, 14 in all, and the whole tree costs more than that, so the build is your choice.")
    totals = skill_tree.totals(EXPEDITION_TREE, runstate.current_expedition["owned"], expedition_points_earned())
    return (
        f"Season {expedition_season()} of {EXPEDITION_SEASONS}. {expedition_points_free()} upgrade points to spend ({expedition_points_earned()} earned so far). "
        f"{totals['owned_count']} of {totals['node_count']} upgrades owned. Taking an upgrade back is free."
    )


def expedition_result_text():
    if not expedition_finished():
        return ""
    return f"Complete: score {runstate.current_expedition['score']} (standing forest value plus harvested income). Leave the Expedition for normal play, or keep going on this forest."


def expedition_bests_text():
    best = expedition_meta["best"]
    parts = [f"Expeditions finished on this device: {expedition_meta['finished']}."]
    if runstate.current_expedition is not None and expedition_best_for(runstate.current_expedition["seed"]) is not None:
        parts.append(f"Best on {runstate.current_expedition['seed']}: {expedition_best_for(runstate.current_expedition['seed'])}.")
    elif best:
        newest = list(best.items())[-3:]
        parts.append("Recent bests: " + ", ".join(f"{seed_text} {score}" for seed_text, score in reversed(newest)) + ".")
    return " ".join(parts)


def _load_expedition(data):
    """Validates and applies the `expedition` key: a save is authoritative, so no key (or a bad one) means no
    Expedition. The map is rebuilt from the seed; owned upgrades are trimmed to the points this forest has earned."""
    runstate.current_expedition = None
    raw = data.get("expedition")
    if isinstance(raw, dict) and isinstance(raw.get("seed"), str) and _expedition_settings_ok():
        check = seed_lib.validate(raw["seed"], SEED_GAME)
        if check["ok"]:
            run = _new_expedition_run(check["seed"])
            runstate.current_expedition = run
            run["owned"] = skill_tree.sanitize_owned(EXPEDITION_TREE, raw.get("owned"), expedition_points_earned(), overspend="trim")
            done = _number_or(raw.get("done_tick"), None, EXPEDITION_TICKS)
            if done is not None and runstate.forest_tick >= EXPEDITION_TICKS:
                run["done_tick"] = int(min(done, runstate.forest_tick))
                score = _number_or(raw.get("score"), None, 0, 10 ** 9)
                run["score"] = int(score) if score is not None else expedition_score()
    _rebuild_expedition_terrain()
