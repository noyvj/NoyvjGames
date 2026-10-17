"""The Scarcity Run engine: swap the real game out and a day's copy in, the Governor-alone headless run and the daily spec."""

import json

import challenges

import sol_runstate as runstate
from sol_achievements import recent_trophies
from sol_charter import stamp_bonus
from sol_doctrines import doctrine_rules
from sol_econ import _yield_multiplier
from sol_rules import RESEARCH_NODES, RESEARCH_TIERS, planet_state
from sol_savestate import deserialize_state, serialize_state
from sol_scarcity import (
    SCARCITY_BOT_BUDGET, SCARCITY_BOT_CLICKS_PER_TICK, SCARCITY_BOT_PRIORITY, SCARCITY_BOUND_TICKS,
    SCARCITY_MIN_TICKS, SCARCITY_RESEARCH_LEVEL, SCARCITY_STALL_CHECK, _scarcity_mean_progress,
    _scarcity_specs, scarcity_days, scarcity_goal_met, scarcity_yield,
)
from sol_sim import _incoming_trade_restore, _simulate_planet, governor_step


def _scarcity_start_data(spec):
    """A save-shaped dict for the start of a day: a fresh game with Near Bodies researched and the day's loadout."""
    data = json.loads(runstate._PRISTINE_JSON)
    data["researched_nodes"] = sorted(node["id"] for node in RESEARCH_NODES if node["tier"] == SCARCITY_RESEARCH_LEVEL)
    data["unlocked_bodies"] = sorted(RESEARCH_TIERS[SCARCITY_RESEARCH_LEVEL]["unlocks"])
    data["visited_bodies"] = ["Earth"]
    data["current_planet"] = "Earth"
    data["total_ticks"] = 0
    for world, load in spec["loadout"].items():
        state = data["planet_state"][world]
        state["resource_count"] = float(load["stock"])
        state["generator_count"] = int(load["generators"])
        state["recycler_count"] = int(load["recyclers"])
        state["ecology_health"] = float(load["ecology"])
    return data


def _apply_state_data(data):
    """Loads a save-shaped dict into the live game WITHOUT touching the run records, and clears the few pieces of
    transient state a save does not carry."""
    runstate._scarcity_keep_days = True
    try:
        deserialize_state(data)
    finally:
        runstate._scarcity_keep_days = False
    runstate._terraform_done_seen.clear()
    runstate.click_streak = 0
    runstate._streak_last_tick = None
    runstate._active_anomaly = None


def _scarcity_discard():
    """A save is being loaded over the game: a run that is on is simply dropped (the loaded save replaces its stash)."""
    if runstate._scarcity is not None:
        _scarcity_swap_out()  # the real game comes back first, then the save is loaded over it as usual


def _scarcity_swap_in(spec):
    """Stashes the real game and starts the day's copy. No DOM."""
    if runstate._scarcity is not None:
        raise RuntimeError("a Scarcity Run is already on")
    stash = json.dumps(serialize_state())
    runstate._scarcity = {"spec": spec, "stash": stash, "trophies": list(recent_trophies), "samples": [], "done": None,
                 "ghost": None, "ghost_label": ""}
    try:
        _apply_state_data(_scarcity_start_data(spec))
    except Exception:
        run, runstate._scarcity = runstate._scarcity, None
        _apply_state_data(json.loads(run["stash"]))
        raise


def _scarcity_swap_out():
    """Puts the real game back exactly. No DOM."""
    run, runstate._scarcity = runstate._scarcity, None
    if run is None:
        return
    _apply_state_data(json.loads(run["stash"]))
    recent_trophies[:] = run["trophies"]


def _scarcity_bot_hand():
    """The reference plan's one hand: SCARCITY_BOT_CLICKS_PER_TICK clicks a tick on whichever target world is furthest from
    the goal. It only ever adds the stock a click would (the Governor does all the buying), so a hand-mined pile can
    never be stuck behind a collapsed world."""
    spec = runstate._scarcity["spec"]
    laggard = min(spec["targets"], key=lambda w: planet_state[w]["terraform_progress"])
    planet_state[laggard]["resource_count"] += (
        SCARCITY_BOT_CLICKS_PER_TICK * _yield_multiplier() * scarcity_yield(laggard) * (1 + stamp_bonus(laggard)))


def _scarcity_headless(spec, rules=None, mutators=None, limit=SCARCITY_BOUND_TICKS):
    """The Governor alone (nobody standing anywhere, default settings, plus a friend's Doctrines and mutators when
    given) playing the day on a copy. Returns (ticks to the goal or None, recording {"ticks", "pct"}). Never touches
    the DOM and always puts the real game back."""
    _scarcity_swap_in(spec)
    samples = []
    done = None
    try:
        if rules is not None:
            doctrine_rules[:] = rules
        if mutators:
            runstate.mutators_run[:] = mutators
        runstate.current_planet = "Deep space"
        runstate.governor_priority, runstate.governor_budget_pct = SCARCITY_BOT_PRIORITY, SCARCITY_BOT_BUDGET
        runstate._dry_run = True
        runstate._research_effect_cache = {}
        stalled_at = -1.0
        samples.append(round(_scarcity_mean_progress() * 10))
        for _ in range(limit):
            runstate.total_ticks += 1
            incoming = {p: _incoming_trade_restore(p) for p in challenges.WORLDS}
            for planet in challenges.WORLDS:  # the five worlds that are still shut are inert, so they are skipped
                _simulate_planet(planet, incoming[planet])
            governor_step()
            _scarcity_bot_hand()
            if runstate.total_ticks % challenges.GHOST_STEP == 0:
                samples.append(round(_scarcity_mean_progress() * 10))
            if scarcity_goal_met():
                done = runstate.total_ticks
                break
            if runstate.total_ticks % SCARCITY_STALL_CHECK == 0:
                progress = round(_scarcity_mean_progress(), 3)
                if progress <= stalled_at:
                    break  # nothing moved for a long while: this candidate day is stuck, so it is not a fair one
                stalled_at = progress
        if done is not None and done % challenges.GHOST_STEP:
            samples.append(round(_scarcity_mean_progress() * 10))
        ticks_used = done if done is not None else runstate.total_ticks
    finally:
        runstate._dry_run = False
        runstate._research_effect_cache = None
        _scarcity_swap_out()
    if len(samples) < 2:
        samples.append(samples[-1])
    return done, {"ticks": max(1, ticks_used), "pct": [min(1000, max(0, v)) for v in samples]}


def scarcity_spec(date_text):
    """The day's challenge with its fairness proof: the first attempt whose Governor-alone run reaches the goal inside
    the bound. Adds "par" (that run's ticks) and "par_recording". Memoised per date. Must not be called mid-run."""
    if date_text in _scarcity_specs:
        return _scarcity_specs[date_text]
    for attempt in range(challenges.MAX_ATTEMPTS):
        spec = challenges.make_spec(date_text, attempt)
        ticks, recording = _scarcity_headless(spec)
        if ticks is not None and ticks >= SCARCITY_MIN_TICKS:
            spec["par"] = ticks
            spec["par_recording"] = recording
            if len(_scarcity_specs) > 60:
                _scarcity_specs.clear()
            _scarcity_specs[date_text] = spec
            return spec
    raise RuntimeError(f"no fair Scarcity Run for {date_text}")


def scarcity_leaderboard_entry(date_text):
    """HOOK for a future opt-in daily board (a separate backend job, NOT built in this pass): the entry the board
    would take for one finished date, or None. Pure; nothing sends it anywhere."""
    record = scarcity_days.get(date_text)
    return challenges.leaderboard_entry(date_text, record) if record else None
