"""The Seed Vault (GB-10/GB-26) and crew helpers, and the loaders for levels and vault saves."""

import json

import skill_tree

import canopy_runstate as runstate
from canopy_achievements import ACHIEVEMENTS
from canopy_effects import VAULT_TREE, vault_effects, vault_owned
from canopy_helpers import _log_event, _number_or, _plot_ref, _read_local_storage_item
from canopy_levels import (
    CREW_LEAD_FASTER_TICKS, CREW_REPLANT_INTERVAL_TICKS, CREW_TEND_DELAY_TICKS, LEVEL_MODE_POACHER,
    LEVEL_MODE_SPIRIT, LEVEL_MODE_STORM, LEVEL_SPECS, META_STORAGE_KEY, POACHER_FIRST_TICKS,
    POACHER_GAP_MIN, POACHER_GAP_SPREAD, POACHER_STAY_TICKS, SPIRIT_STEPS, STORM_INTERVAL_TICKS,
    VAULT_ACHIEVEMENTS_PER_POINT, VAULT_ACHIEVEMENT_POINTS_MAX, _level_matches_settings, _level_mode,
    _merge_levels_state, _note_vault_progress, _reset_level_run, _sanitize_levels_state, _save_meta,
    _sync_levels_js, crew_stats, poacher_run, spirit_run, storm_run, vault_meta, vault_points_earned,
    vault_points_free,
)
from canopy_rules import ACCRUING_STATES, BARE, REPLANTING
from canopy_tend import _tendable, _tended_plot, collect_golden_seedling
from canopy_worldvars import STANDING_TIERS, TEND_DURATION_TICKS


# --- GB-10 / GB-26: the Seed Vault ------------------------------------------------------------------------------


def _sanitize_vault_blob(raw, earned_hint=None):
    """(owned, best_tier, best_ach) from a saved blob; anything malformed falls back to nothing owned."""
    if not isinstance(raw, dict):
        return [], 0, 0
    owned = skill_tree.sanitize_owned(VAULT_TREE, raw.get("owned"))
    best_tier = int(_number_or(raw.get("best_tier"), 0, 0, len(STANDING_TIERS)))
    best_ach = int(_number_or(raw.get("best_ach", raw.get("best_achievements")), 0, 0, len(ACHIEVEMENTS)))
    return owned, best_tier, best_ach


def _load_meta():
    """Reads this browser's meta-progress at start-up (a fresh or unreadable store simply means none)."""
    raw = _read_local_storage_item(META_STORAGE_KEY)
    if not raw:
        return
    try:
        blob = json.loads(raw)
    except (ValueError, TypeError):
        return
    if not isinstance(blob, dict):
        return
    runstate.levels_state = _sanitize_levels_state(blob.get("levels"))
    owned, best_tier, best_ach = _sanitize_vault_blob(blob.get("seed_vault"))
    vault_meta["best_tier"] = best_tier
    vault_meta["best_ach"] = best_ach
    vault_owned[:] = skill_tree.sanitize_owned(VAULT_TREE, owned, vault_points_earned(), overspend="trim")


def _crew_tend_target():
    candidates = [p for p in runstate.plots if _tendable(p) and p.maturity_fraction() < 1.0]
    if not candidates:
        return None
    return min(candidates, key=lambda p: (p.state != REPLANTING, p.maturity_fraction(), p.index))


def _advance_crews():
    """Idle ranger crews (GB-26): small deterministic jobs on the tick, only while their perk is owned."""
    effects = vault_effects()
    if not effects:
        return
    if "crew_tend" in effects:
        if _tended_plot() is None and runstate.tend_cooldown_ticks <= 0:
            runstate._crew_tend_wait += 1
            if runstate._crew_tend_wait >= CREW_TEND_DELAY_TICKS:
                target = _crew_tend_target()
                if target is not None:
                    target.tend_ticks_left = TEND_DURATION_TICKS
                    crew_stats["tends"] += 1
                    _log_event("crew", f"Tending crew tended {_plot_ref(target.index)}", target.index)
                    runstate._crew_tend_wait = 0
        else:
            runstate._crew_tend_wait = 0
    if "crew_seedling" in effects and runstate.golden_seedling is not None and runstate.golden_seedling["ticks_left"] <= 1:
        if collect_golden_seedling():
            crew_stats["seedlings"] += 1
    if "crew_replant" in effects:
        runstate._crew_replant_clock += 1
        interval = CREW_REPLANT_INTERVAL_TICKS - (CREW_LEAD_FASTER_TICKS if "crew_lead" in effects else 0)
        if runstate._crew_replant_clock >= interval:
            target = next((p for p in runstate.plots if p.state == BARE and not p.blocked), None)
            if target is not None and target.replant():
                runstate.total_replants += 1
                crew_stats["replants"] += 1
                _log_event("crew", f"Replant crew replanted {_plot_ref(target.index)}", target.index)
                runstate._crew_replant_clock = 0
            else:
                runstate._crew_replant_clock = interval  # nothing bare: replant the first one that appears


def vault_summary_text():
    totals = skill_tree.totals(VAULT_TREE, vault_owned, vault_points_earned())
    return (
        f"{vault_points_free()} seed points to spend ({vault_points_earned()} earned in all). "
        f"{totals['owned_count']} of {totals['node_count']} perks owned. "
        "Earn points: 1 for each level completed, 1 for each forest tier reached "
        f"({vault_meta['best_tier']} of {len(STANDING_TIERS)} so far), 1 for every {VAULT_ACHIEVEMENTS_PER_POINT} achievements "
        f"({min(VAULT_ACHIEVEMENT_POINTS_MAX, vault_meta['best_ach'] // VAULT_ACHIEVEMENTS_PER_POINT)} of {VAULT_ACHIEVEMENT_POINTS_MAX} so far)."
    )


def vault_crews_text():
    return (
        f"Crew work this session: {crew_stats['tends']} tends, {crew_stats['seedlings']} seedlings caught, "
        f"{crew_stats['replants']} plots replanted."
    )


# --- saved state --------------------------------------------------------------------------------------------------


def _load_levels(data):
    """Validates and applies the levels / seed_vault / level_run keys. Meta-progress is MERGED (a save from an
    older point never takes progress away); the running level comes from the save, or there is none."""
    saved_levels = data.get("levels")
    if saved_levels is not None:
        runstate.levels_state = _merge_levels_state(runstate.levels_state, _sanitize_levels_state(saved_levels))
    saved_vault = data.get("seed_vault")
    if isinstance(saved_vault, dict):
        owned, best_tier, best_ach = _sanitize_vault_blob(saved_vault)
        vault_meta["best_tier"] = max(vault_meta["best_tier"], best_tier)
        vault_meta["best_ach"] = max(vault_meta["best_ach"], best_ach)
        vault_owned[:] = skill_tree.sanitize_owned(VAULT_TREE, owned, vault_points_earned(), overspend="trim")
        crews = saved_vault.get("crews")
        if isinstance(crews, dict):
            for key in crew_stats:
                crew_stats[key] = int(_number_or(crews.get(key), 0, 0, 10 ** 9))
    else:
        vault_owned[:] = skill_tree.sanitize_owned(VAULT_TREE, vault_owned, vault_points_earned(), overspend="trim")
    runstate.current_level = None
    raw = data.get("level_run")
    saved_id = raw.get("id") if isinstance(raw, dict) else None
    if isinstance(saved_id, str) and saved_id in LEVEL_SPECS and _level_matches_settings(LEVEL_SPECS[saved_id]):
        runstate.current_level = saved_id
    crews_kept = dict(crew_stats)
    _reset_level_run()
    crew_stats.update(crews_kept)
    if runstate.current_level is not None:
        runstate.level_ticks = int(_number_or(raw.get("ticks"), 0, 0, 10 ** 9))
        done = raw.get("done_tick")
        runstate.level_done_tick = int(_number_or(done, 0, 0, 10 ** 9)) if done is not None and _number_or(done, None) is not None else None
        _load_level_mode_state(raw)
    _note_vault_progress(silent=True)
    _save_meta()
    _sync_levels_js()


def _load_level_mode_state(raw):
    mode = _level_mode()
    if mode == LEVEL_MODE_POACHER and isinstance(raw.get("poacher"), dict):
        saved = raw["poacher"]
        plot = saved.get("plot")
        valid_plot = isinstance(plot, int) and not isinstance(plot, bool) and 0 <= plot < len(runstate.plots) and runstate.plots[plot].state in ACCRUING_STATES
        poacher_run.update(
            plot=plot if valid_plot else None,
            ticks_left=int(_number_or(saved.get("ticks_left"), 0, 0, POACHER_STAY_TICKS)) if valid_plot else 0,
            driven=int(_number_or(saved.get("driven"), 0, 0, 10 ** 6)),
            missed=int(_number_or(saved.get("missed"), 0, 0, 10 ** 6)),
            next_in=int(_number_or(saved.get("next_in"), POACHER_FIRST_TICKS, 1, POACHER_GAP_MIN + POACHER_GAP_SPREAD + POACHER_FIRST_TICKS)),
        )
        last = saved.get("last_plot")
        poacher_run["last_plot"] = last if isinstance(last, int) and not isinstance(last, bool) and 0 <= last < len(runstate.plots) else None
    elif mode == LEVEL_MODE_STORM and isinstance(raw.get("storm"), dict):
        saved = raw["storm"]
        storm_run.update(
            next_in=int(_number_or(saved.get("next_in"), STORM_INTERVAL_TICKS, 1, STORM_INTERVAL_TICKS)),
            fronts=int(_number_or(saved.get("fronts"), 0, 0, 10 ** 6)),
            lost=float(_number_or(saved.get("lost"), 0.0, 0.0)),
            hits=int(_number_or(saved.get("hits"), 0, 0, 10 ** 9)),
            shielded=int(_number_or(saved.get("shielded"), 0, 0, 10 ** 9)),
        )
    elif mode == LEVEL_MODE_SPIRIT and isinstance(raw.get("spirit"), dict):
        saved = raw["spirit"]
        step = int(_number_or(saved.get("step"), 0, 0, len(SPIRIT_STEPS)))
        spirit_run.update(step=step, said=int(_number_or(saved.get("said"), -1, -1, len(SPIRIT_STEPS))))
