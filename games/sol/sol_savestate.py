"""serialize_state / deserialize_state, the session additions, welcome-back snapshot and get_save_state_json."""

import copy
import json

import sol_runstate as runstate
from sol_achievements import TROPHY_HISTORY_MAX, achievement_ids_earned, recent_trophies
from sol_charter import (
    MISSION_BY_ID, MISSION_SLOTS, _load_megaprojects, _slots_are_default, megaproject_progress,
    mission_slots, mission_stamps,
)
from sol_codex import CLUE_BY_ID, codex_found
from sol_doctrines import _clean_doctrine_rules, _doctrine_reset_runtime, doctrine_rules
from sol_econ import _clean_researched_nodes, _migrate_legacy_research, _recompute_research
from sol_observatory import _load_observatory, comets_caught_run, point_claims
from sol_rhythm import (
    CHAIN_BY_ID, _action_log, _chain_cooldown_until, _clean_splits, chain_counts, pb_splits, run_splits,
)
from sol_rules import (
    BUILD_PLAN_MAX_LEN, BUILD_PLAN_MAX_STEPS, GOVERNOR_PERSONALITIES, PLANETS, PRESTIGE_TREE_BY_ID,
    SPECIALIZATION_LABELS, _ecology_low_seen, _ecology_zero_seen, build_plan, planet_state,
    researched_nodes,
)
from sol_runmods import ANOMALY_BY_ID, _clean_mutators, anomalies_seen, megaprojects_built, mutators_next
from sol_scarcity import _load_scarcity, scarcity_days
from sol_story import ACHIEVEMENTS, STORY_LOG_MAX, story_line, story_log
from sol_util import _clean_ids, _display_toast, _read_local_storage_item, _write_local_storage_item


# --- Save system (SAVE-SYSTEM-DESIGN.md Phase 1) ---
# Bridges to the plain-JS block in index.html: Python only ever crosses
# the Pyodide/JS boundary as a plain string (json.dumps/json.loads),
# never a raw dict/set — Pyodide auto-converts a returned `str` to a
# native JS string with no proxy involved, and the reverse on the way
# in, which sidesteps PyProxy lifetime/conversion entirely. The JS side
# owns the actual fetch() calls to the /saves API (documented plain-JS
# exception, same pattern as every other game's feedback prompt).


def serialize_state():
    """Every module-level mutable global, packaged as one JSON-safe
    dict. `planet_state` is deep-copied — it's a dict of dicts (each
    with its own nested `trade_routes` dict), and a shallow copy would
    still alias those inner dicts, so continued play after taking a
    "snapshot" would silently mutate it. `unlocked_bodies`/`visited_bodies`
    are the only non-JSON-native types in the state (sets) — converted to a
    list here and back to a set on load.

    `achievements_earned` (ACHIEVEMENTS-SYSTEM-DESIGN.md) is a write-only
    projection, not part of this game's own state: it rides the existing
    save/sync mechanism purely so the hub's aggregate dashboard can read a
    signed-in player's progress without a new backend endpoint, and it is
    always recomputed fresh here rather than read back on load — see
    deserialize_state() below, which doesn't reference this key at all."""
    return {
        "planet_state": copy.deepcopy(planet_state),
        "research_progress": runstate.research_progress,
        "completed_tiers": runstate.completed_tiers,
        "researched_nodes": sorted(researched_nodes),
        "unlocked_bodies": sorted(runstate.unlocked_bodies),
        "visited_bodies": sorted(runstate.visited_bodies),
        "current_planet": runstate.current_planet,
        "governor_priority": runstate.governor_priority,
        "governor_budget_pct": runstate.governor_budget_pct,
        "governor_tick_count": runstate.governor_tick_count,
        "governor_purchase_count": runstate.governor_purchase_count,
        # A1 (Prestige / New Game+): the one piece of state a prestige is
        # FOR keeping -- see _prestige()'s own comment for what does and
        # doesn't reset.
        "prestige_level": runstate.prestige_level,
        # A4 (lifetime stats) + A2/A13 (second achievement wave): all of
        # these only ever go up (or, for the *_hit flags, flip once), and
        # none of them are touched by a world reset (A18) or reset by
        # prestige (A1) except any_generator_ever_built -- see _prestige().
        "total_ticks": runstate.total_ticks,
        **({"full_system_completed_tick": runstate.full_system_completed_tick} if runstate.full_system_completed_tick is not None else {}),
        **({"run_start_tick": runstate.run_start_tick} if runstate.run_start_tick else {}),
        **({"run_completed": True} if runstate.run_completed else {}),
        **({"best_run_ticks": runstate.best_run_ticks} if runstate.best_run_ticks is not None else {}),
        "total_manual_clicks": runstate.total_manual_clicks,
        "lifetime_resources_mined_by_click": runstate.lifetime_resources_mined_by_click,
        "lifetime_resources_generated_by_automation": runstate.lifetime_resources_generated_by_automation,
        "lifetime_generators_built": runstate.lifetime_generators_built,
        "lifetime_recyclers_built": runstate.lifetime_recyclers_built,
        "lifetime_trade_routes_built": runstate.lifetime_trade_routes_built,
        "lifetime_sky_cities_built": runstate.lifetime_sky_cities_built,
        "any_generator_ever_built": runstate.any_generator_ever_built,
        "quick_start_hit": runstate.quick_start_hit,
        "swift_expansion_hit": runstate.swift_expansion_hit,
        "manual_labor_hit": runstate.manual_labor_hit,
        "off_the_grid_hit": runstate.off_the_grid_hit,
        # Prestige tree (A1/A3), sandbox (A15), build plan (A13), close calls (A19).
        "prestige_points_earned": runstate.prestige_points_earned,
        "prestige_nodes": sorted(runstate.prestige_nodes),
        "ng_challenge_active": runstate.ng_challenge_active,
        "sandbox_mode": runstate.sandbox_mode,
        "build_plan": copy.deepcopy(build_plan),
        "close_call_hit": runstate.close_call_hit,
        "back_from_brink_hit": runstate.back_from_brink_hit,
        "ecology_low_seen": sorted(_ecology_low_seen),
        "ecology_zero_seen": sorted(_ecology_zero_seen),
        "achievements_earned": achievement_ids_earned(),
        **({"story_log": list(story_log)} if story_log else {}),
        **({"best_click_streak": runstate.best_click_streak} if runstate.best_click_streak else {}),
        **({"chain_counts": dict(chain_counts)} if chain_counts else {}),
        **({"recent_trophies": list(recent_trophies)} if recent_trophies else {}),
        **({"run_splits": dict(run_splits)} if run_splits else {}),
        **({"pb_splits": dict(pb_splits)} if pb_splits else {}),
        **({"anomalies_seen": sorted(anomalies_seen)} if anomalies_seen else {}),
        **({"codex_found": list(codex_found)} if codex_found else {}),
        **({"doctrine_rules": [dict(rule) for rule in doctrine_rules]} if doctrine_rules else {}),
        **({"stress_best_margin": runstate.stress_best_margin} if runstate.stress_best_margin is not None else {}),
        **({"megaproject_progress": {k: dict(v) for k, v in megaproject_progress.items()}} if megaproject_progress else {}),
        **({"megaprojects_built": list(megaprojects_built)} if megaprojects_built else {}),
        **({"megaprojects_all_ever": True} if runstate.megaprojects_all_ever else {}),
        **({"mission_stamps": list(mission_stamps)} if mission_stamps else {}),
        **({"mission_slots": list(mission_slots)} if mission_slots and not _slots_are_default() else {}),
        **({"mutators_next": list(mutators_next)} if mutators_next else {}),
        **({"mutators_run": list(runstate.mutators_run)} if runstate.mutators_run else {}),
        **({"survey_data": runstate.survey_data} if runstate.survey_data else {}),
        **({"chart_revealed": runstate.chart_revealed} if runstate.chart_revealed else {}),
        **({"point_claims": dict(point_claims)} if point_claims else {}),
        **({"comets_caught_run": list(comets_caught_run)} if comets_caught_run else {}),
        **({"comets_caught_total": runstate.comets_caught_total} if runstate.comets_caught_total else {}),
        **({"scarcity_days": {d: dict(r) for d, r in scarcity_days.items()}} if scarcity_days else {}),
    }


def deserialize_state(data):

    # Merge in place rather than clear()+update(): a save whose
    # planet_state is missing a body (an older save format from before
    # that body's economy existed, or a corrupted payload) must not wipe
    # that body's freshly-initialized state out of the dict entirely --
    # every other function (tick() in particular) does `planet_state[p]`
    # for every `p in PLANETS` unconditionally, so a missing key would
    # crash the whole game on the very next tick.
    #
    # The same reasoning applies one level down: a body's own saved dict
    # must be merged key-by-key too, not swapped in wholesale. A save
    # made before a later milestone added a new per-planet field (e.g.
    # "trade_destination" pre-9f, "terraform_progress" pre-8,
    # "sky_city_count" pre-10) would otherwise wipe that planet's
    # freshly-initialized default for the missing field, and the very
    # next access (tick()'s terraform step, current_trade_destination(),
    # _buy_sky_city()) would KeyError and crash the game.
    #
    # And the same reasoning applies one level further OUT: every
    # top-level scalar (plus "planet_state" itself) is read with a
    # `.get(..., <current live value>)` fallback rather than bare `[...]`
    # indexing, so a save missing any single top-level field -- a
    # corrupted payload, or a hand-edited/truncated save code -- falls
    # back to whatever is already running instead of KeyError-ing inside
    # deserialize_state() itself, before the game even gets as far as the
    # next tick().
    for planet, saved_planet_state in data.get("planet_state", {}).items():
        if planet in planet_state:
            planet_state[planet].update(saved_planet_state)
        else:
            planet_state[planet] = saved_planet_state
    # U10: research is a set of nodes now. A save from before the tree only
    # has (completed_tiers, research_progress); convert it without losing
    # anything, refunding any Iron the partial progress can't buy a node with.
    saved_nodes = data.get("researched_nodes")
    if isinstance(saved_nodes, list):
        researched_nodes.clear()
        researched_nodes.update(_clean_researched_nodes(saved_nodes))
    else:
        legacy_tiers = data.get("completed_tiers", 0)
        legacy_tiers = legacy_tiers if isinstance(legacy_tiers, int) and not isinstance(legacy_tiers, bool) else 0
        migrated, refund = _migrate_legacy_research(max(0, legacy_tiers), data.get("research_progress", 0.0))
        researched_nodes.clear()
        researched_nodes.update(_clean_researched_nodes(migrated))
        if refund > 0:
            planet_state["Earth"]["resource_count"] += refund
    _recompute_research()
    runstate.unlocked_bodies = set(data.get("unlocked_bodies", runstate.unlocked_bodies))
    # A save made before this field existed simply has no key here, so this
    # falls back to whatever's already running (the module default,
    # {"Earth"}, on a fresh load) — same defensive fallback as every other
    # top-level field in this function, per the reasoning above.
    runstate.visited_bodies = set(data.get("visited_bodies", runstate.visited_bodies))
    runstate.current_planet = data.get("current_planet", runstate.current_planet)
    # Wherever the save says the player currently is, they have — by
    # definition — actually been there, even if this is an old save from
    # before "visited_bodies" existed at all. Without this, such a save
    # loaded mid-Mars-trip would forget Mars was ever visited until the
    # player traveled again.
    runstate.visited_bodies.add(runstate.current_planet)
    runstate.governor_priority = data.get("governor_priority", runstate.governor_priority)
    runstate.governor_budget_pct = data.get("governor_budget_pct", runstate.governor_budget_pct)
    runstate.governor_tick_count = data.get("governor_tick_count", runstate.governor_tick_count)
    runstate.governor_purchase_count = data.get("governor_purchase_count", runstate.governor_purchase_count)
    runstate.prestige_level = data.get("prestige_level", runstate.prestige_level)
    runstate.total_ticks = data.get("total_ticks", runstate.total_ticks)
    runstate.total_manual_clicks = data.get("total_manual_clicks", runstate.total_manual_clicks)
    runstate.lifetime_resources_mined_by_click = data.get(
        "lifetime_resources_mined_by_click", runstate.lifetime_resources_mined_by_click
    )
    runstate.lifetime_resources_generated_by_automation = data.get(
        "lifetime_resources_generated_by_automation", runstate.lifetime_resources_generated_by_automation
    )
    runstate.lifetime_generators_built = data.get("lifetime_generators_built", runstate.lifetime_generators_built)
    runstate.lifetime_recyclers_built = data.get("lifetime_recyclers_built", runstate.lifetime_recyclers_built)
    runstate.lifetime_trade_routes_built = data.get("lifetime_trade_routes_built", runstate.lifetime_trade_routes_built)
    runstate.lifetime_sky_cities_built = data.get("lifetime_sky_cities_built", runstate.lifetime_sky_cities_built)
    runstate.any_generator_ever_built = data.get("any_generator_ever_built", runstate.any_generator_ever_built)
    runstate.quick_start_hit = data.get("quick_start_hit", runstate.quick_start_hit)
    runstate.swift_expansion_hit = data.get("swift_expansion_hit", runstate.swift_expansion_hit)
    runstate.manual_labor_hit = data.get("manual_labor_hit", runstate.manual_labor_hit)
    runstate.off_the_grid_hit = data.get("off_the_grid_hit", runstate.off_the_grid_hit)
    _load_session_additions(data)


def _load_session_additions(data):
    """Loads the fields added with the A1-A30 batch, each defensively: a
    missing key keeps the current value, a wrongly-typed one is ignored, so
    an old save (or a hand-edited one) can never crash the load."""

    def _tick_count(value):
        return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 10 ** 12 else None

    runstate.run_start_tick = _tick_count(data.get("run_start_tick")) or 0
    runstate.run_completed = data.get("run_completed") is True
    runstate.best_run_ticks = _tick_count(data.get("best_run_ticks"))
    # Round-3 batch: every field optional and defensively typed.
    runstate.best_click_streak = _tick_count(data.get("best_click_streak")) or 0
    run_splits.clear()
    run_splits.update(_clean_splits(data.get("run_splits")))
    pb_splits.clear()
    pb_splits.update(_clean_splits(data.get("pb_splits")))
    chain_counts.clear()
    saved_chains = data.get("chain_counts")
    if isinstance(saved_chains, dict):
        for chain_id, count in saved_chains.items():
            if chain_id in CHAIN_BY_ID and isinstance(count, int) and not isinstance(count, bool) and 0 < count < 10 ** 6:
                chain_counts[chain_id] = count
    del _action_log[:]
    _chain_cooldown_until.clear()
    runstate._trophy_fresh_id = None
    saved_trophies = data.get("recent_trophies")
    recent_trophies.clear()
    if isinstance(saved_trophies, list):
        known = {entry["id"] for entry in ACHIEVEMENTS}
        for aid in saved_trophies:
            if isinstance(aid, str) and aid in known and aid not in recent_trophies:
                recent_trophies.append(aid)
        del recent_trophies[:-TROPHY_HISTORY_MAX]
    else:
        # A save from before the shelf existed: the most recent earned ones, in catalog order.
        recent_trophies.extend(achievement_ids_earned()[-TROPHY_HISTORY_MAX:])

    anomalies_seen.clear()
    saved_anomalies = data.get("anomalies_seen")
    if isinstance(saved_anomalies, list):
        anomalies_seen.update(a for a in saved_anomalies if isinstance(a, str) and a in ANOMALY_BY_ID)
    _load_megaprojects(data)
    codex_found[:] = _clean_ids(data.get("codex_found"), CLUE_BY_ID)
    doctrine_rules[:] = _clean_doctrine_rules(data.get("doctrine_rules"))
    saved_margin = data.get("stress_best_margin")
    runstate.stress_best_margin = (
        round(float(saved_margin), 1)
        if isinstance(saved_margin, (int, float)) and not isinstance(saved_margin, bool)
        and -100.0 <= saved_margin <= 100.0 and saved_margin == saved_margin
        else None
    )
    _doctrine_reset_runtime()
    mission_stamps[:] = _clean_ids(data.get("mission_stamps"), MISSION_BY_ID)
    mission_slots[:] = [m_id for m_id in _clean_ids(data.get("mission_slots"), MISSION_BY_ID)
                        if m_id not in mission_stamps][:MISSION_SLOTS]
    mutators_next[:] = _clean_mutators(data.get("mutators_next"))
    runstate.mutators_run[:] = _clean_mutators(data.get("mutators_run"))
    _load_observatory(data)
    _load_scarcity(data)

    saved_story = data.get("story_log")
    story_log.clear()
    if isinstance(saved_story, list):
        for entry_id in saved_story:
            if isinstance(entry_id, str) and story_line(entry_id) and entry_id not in story_log:
                story_log.append(entry_id)
        del story_log[:-STORY_LOG_MAX]

    saved_completion = data.get("full_system_completed_tick")
    runstate.full_system_completed_tick = (
        saved_completion
        if isinstance(saved_completion, int) and not isinstance(saved_completion, bool) and saved_completion >= 0
        else None
    )
    runstate._leaderboard_reported = False

    # Legacy saves: prestige_level existed before points did, and each
    # prestige is worth 1 point, so an old save's points equal its level.
    earned = data.get("prestige_points_earned", runstate.prestige_level)
    runstate.prestige_points_earned = earned if isinstance(earned, int) and not isinstance(earned, bool) and earned >= 0 else runstate.prestige_level
    nodes = data.get("prestige_nodes", sorted(runstate.prestige_nodes))
    if isinstance(nodes, list):
        runstate.prestige_nodes = {n for n in nodes if isinstance(n, str) and n in PRESTIGE_TREE_BY_ID}
    runstate.ng_challenge_active = data.get("ng_challenge_active", runstate.ng_challenge_active) is True
    runstate.sandbox_mode = data.get("sandbox_mode", runstate.sandbox_mode) is True
    runstate.close_call_hit = data.get("close_call_hit", runstate.close_call_hit) is True
    runstate.back_from_brink_hit = data.get("back_from_brink_hit", runstate.back_from_brink_hit) is True
    for key, target in (("ecology_low_seen", _ecology_low_seen), ("ecology_zero_seen", _ecology_zero_seen)):
        raw = data.get(key)
        if isinstance(raw, list):
            target.clear()
            target.update(p for p in raw if p in PLANETS)
    plan = data.get("build_plan")
    if isinstance(plan, list):
        cleaned = []
        for step in plan[:BUILD_PLAN_MAX_STEPS]:
            if isinstance(step, dict) and isinstance(step.get("text"), str) and step["text"].strip():
                cleaned.append({"text": step["text"].strip()[:BUILD_PLAN_MAX_LEN], "done": step.get("done") is True})
        build_plan[:] = cleaned
    # A run-scoped, in-memory report baseline: never meaningful across a load.
    runstate._departure_snapshots = {}
    for state in planet_state.values():
        actions = state.get("player_actions", 0)
        if not isinstance(actions, int) or isinstance(actions, bool) or actions < 0:
            state["player_actions"] = 0
        if state.get("governor_personality") not in GOVERNOR_PERSONALITIES:
            state["governor_personality"] = "default"
        if state.get("specialization") not in (None, *SPECIALIZATION_LABELS):
            state["specialization"] = None


# V-CD-4 (planning/TODO.md, from the completion audit's A3 follow-up):
# the welcome-back toast's "last time" reference point, persisted PER
# BROWSER via localStorage -- deliberately NOT part of get_state()/the
# save-code payload, since a save code is meant to be portable across
# devices/browsers while "what this browser last saw" is a per-browser
# fact, not a save-state fact. Same lazy `import js`/getattr-defaulting
# pattern as Canopy's personal_best / Tide's best_coastline_saved
# (`_read_local_storage_item()`/`_write_local_storage_item()`), SOL's
# first use of Python-side localStorage (settings.js's text-scale/
# reduced-motion prefs use the same storage but from plain JS, outside
# Pyodide entirely).
WELCOME_BACK_SNAPSHOT_STORAGE_KEY = "sol_welcome_back_snapshot_v1"


def _load_welcome_back_snapshot():
    """Reads the (worlds_visited, achievements_earned) pair this browser
    recorded the last time a save loaded here. Returns None if nothing is
    stored yet, storage is unavailable, or the stored value is
    malformed."""
    raw = _read_local_storage_item(WELCOME_BACK_SNAPSHOT_STORAGE_KEY)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        snapshot = {
            "worlds_visited": int(data["worlds_visited"]),
            "achievements_earned": int(data["achievements_earned"]),
        }
        # R-9: machines built and hand-mined clicks were added later; an older
        # snapshot simply lacks them (None = nothing to diff against).
        for key in ("machines_built", "manual_clicks"):
            value = data.get(key)
            snapshot[key] = int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
        return snapshot
    except (ValueError, TypeError, KeyError):
        return None


def _save_welcome_back_snapshot(worlds_visited, achievements_earned):
    _write_local_storage_item(
        WELCOME_BACK_SNAPSHOT_STORAGE_KEY,
        json.dumps({
            "worlds_visited": worlds_visited,
            "achievements_earned": achievements_earned,
            "machines_built": int(runstate.lifetime_generators_built),
            "manual_clicks": int(runstate.total_manual_clicks),
        }),
    )


def _show_welcome_back_toast():
    """A3: a "welcome back" return-visit summary toast. Fires whenever a
    save is loaded -- the only situation SOL can actually call "a
    returning player" (see load_state()/load_save_state_json() below, the
    two entry points a loaded save ever arrives through).

    Originally a static current-standing snapshot: SOL has no
    offline-production system (the project's own "no idle/wait-timer
    mechanics" rule means nothing advances while the tab is closed), so
    there was no real "here's what changed while you were away" delta to
    report against the save's own numbers. Revised per V-CD-4 to a
    genuine "+X since last time" delta by comparing this load's numbers
    against what this same BROWSER last recorded (`_load_welcome_back_
    snapshot()`), not the save code itself -- so the delta is meaningful
    per browser while the save stays portable across devices. Falls back
    to the original static wording when there's nothing sensible to
    diff against: this browser's first-ever load (nothing stored yet),
    or the just-loaded save's numbers sitting at or below the stored
    snapshot (an older or different save code loaded into the same
    browser) -- never shows a negative "-N" as though something was
    lost. The stored snapshot is updated to this load's numbers only
    AFTER computing the delta against the OLD stored values, so next
    time compares against this visit, not some frozen baseline."""
    worlds = len(runstate.visited_bodies)
    earned = len(achievement_ids_earned())
    previous = _load_welcome_back_snapshot()

    message = None
    if previous is not None:
        delta_worlds = worlds - previous["worlds_visited"]
        delta_achievements = earned - previous["achievements_earned"]
        delta_machines = (
            int(runstate.lifetime_generators_built) - previous["machines_built"] if previous.get("machines_built") is not None else 0
        )
        delta_clicks = (
            int(runstate.total_manual_clicks) - previous["manual_clicks"] if previous.get("manual_clicks") is not None else 0
        )
        if (
            delta_worlds >= 0 and delta_achievements >= 0 and delta_machines >= 0 and delta_clicks >= 0
            and (delta_worlds > 0 or delta_achievements > 0 or delta_machines > 0 or delta_clicks > 0)
        ):
            message = (
                f"👋 Welcome back! +{delta_worlds} world(s) visited, "
                f"+{delta_achievements} achievement(s)"
            )
            if delta_machines > 0:
                message += f", +{delta_machines} machine(s) built"
            if delta_clicks > 0:
                message += f", +{delta_clicks} hand-mined load(s)"
            message += " since you were last here."

    if message is None:
        message = (
            f"👋 Welcome back! {worlds}/{len(PLANETS)} worlds visited, "
            f"{earned}/{len(ACHIEVEMENTS)} achievements earned."
        )

    _display_toast(message)
    _save_welcome_back_snapshot(worlds, earned)
