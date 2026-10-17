"""Click-rhythm streak, speedrun splits (data), trophy shelf data, chain reactions and the Governor's mood."""

import math

from js import document

import sol_runstate as runstate
from sol_econ import _yield_multiplier, update_resource_display
from sol_rules import PLANETS, planet_state
from sol_util import _display_toast, _setting_on


# ===========================================================================
# Round-3 SOL batch: rhythm streak (A-26), speedrun splits (A-30), trophy
# shelf (A-31), chain reactions (A-25), Governor mood (A-22). None of it
# changes a cost, a cap or an unlock; the two small yield effects (the streak
# and a chain's bonus) are capped, and both have an off switch in Settings.
# ===========================================================================

# Browser preferences from the Settings panel (settings.js keeps them in
# localStorage as "on"/"off"; anything but "off" counts as on, so a fresh
# browser gets the defaults and a locked-down one that cannot read storage
# does too).
CLICK_STREAK_KEY = "sol-click-streak"
CHAIN_BONUS_KEY = "sol-chain-bonus"


# --- A-26: a soft click-rhythm meter ---------------------------------------
# Manual clicks that follow each other within STREAK_WINDOW_TICKS (1.5 s of
# game time) build a streak; every STREAK_CLICKS_PER_PCT clicks of it adds 1%
# to a manual click's yield, up to STREAK_MAX_BONUS_PCT. Automation is never
# touched, so it stays a nudge for hands that are already clicking, never a
# reason to click. The streak itself is transient; only the best one is saved.
STREAK_WINDOW_TICKS = 15
STREAK_CLICKS_PER_PCT = 10
STREAK_MAX_BONUS_PCT = 5
STREAK_SHOW_AT = 3
IN_RHYTHM_STREAK = 40


def streak_bonus_pct():
    return min(STREAK_MAX_BONUS_PCT, runstate.click_streak // STREAK_CLICKS_PER_PCT)


def render_click_streak():
    el = document.getElementById("click-streak")
    visible = runstate.click_streak >= STREAK_SHOW_AT
    el.hidden = not visible
    if not visible:
        el.innerText = ""
        return
    pct = streak_bonus_pct()
    bonus = f"+{pct}% mining yield" if pct else f"bonus starts at {STREAK_CLICKS_PER_PCT}"
    el.innerText = f"Rhythm streak: {runstate.click_streak} ({bonus})"


def _streak_click():
    """Registers one manual click and returns its yield multiplier."""
    if not _setting_on(CLICK_STREAK_KEY):
        if runstate.click_streak:
            runstate.click_streak = 0
            render_click_streak()
        runstate._streak_last_tick = None
        return 1.0
    if runstate._streak_last_tick is not None and runstate.total_ticks - runstate._streak_last_tick <= STREAK_WINDOW_TICKS:
        runstate.click_streak += 1
    else:
        runstate.click_streak = 1
    runstate._streak_last_tick = runstate.total_ticks
    runstate.best_click_streak = max(runstate.best_click_streak, runstate.click_streak)
    render_click_streak()
    return 1.0 + streak_bonus_pct() / 100.0


def _decay_click_streak():
    """Called every tick: a streak ends once the player stops clicking."""
    if runstate.click_streak and (runstate._streak_last_tick is None or runstate.total_ticks - runstate._streak_last_tick > STREAK_WINDOW_TICKS):
        runstate.click_streak = 0
        render_click_streak()


# --- A-30: speedrun splits --------------------------------------------------
# A split is how far into the current run (in game time, the same clock the
# other run records use) a world was first unlocked; "full" is the whole
# system terraformed. The personal best is the splits of the fastest completed
# run, so a run is compared against one real run rather than a patchwork of
# best segments. Both are shown only when "Show timing" is on in Settings.
SPLIT_KEYS = ["Moon", "Mars", "Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons", "full"]
run_splits = {}
pb_splits = {}


def _note_split(key):
    if key in SPLIT_KEYS and key not in run_splits:
        run_splits[key] = max(0, runstate.total_ticks - runstate.run_start_tick)


def _clean_splits(raw):
    cleaned = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in SPLIT_KEYS and isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 10 ** 12:
                cleaned[key] = value
    return cleaned


# --- A-25: chain reactions ----------------------------------------------------
# Doing the right short sequence of actions inside CHAIN_WINDOW_TICKS (60 s of
# game time) fires a small bonus. Only your own actions count (the Governor's
# purchases do not). Mining many times in a row is a single "mine" entry;
# every other action is its own entry. A step's world is a name, None (anywhere) or
# "*" (anywhere, but every "*" step in the chain must be a different world).
# Each chain can fire again after CHAIN_COOLDOWN_TICKS, so the page is a
# collection to complete rather than a farm. Every chain shows a hint until
# found and its full recipe afterwards.
CHAIN_WINDOW_TICKS = 600
CHAIN_COOLDOWN_TICKS = 1200
CHAIN_REWARD_BASE = 40
CHAIN_REWARD_PER_GENERATOR = 4
ACTION_LOG_MAX = 24
CHAINS = [
    {
        "id": "spin_up", "name": "Spin-Up",
        "steps": [("mine", "Earth"), ("gen", "Earth"), ("mine", "Earth")],
        "recipe": "On Earth: mine, buy an Auto-Miner, then mine again.",
        "hint": "Warm up the first world: dig, build, dig.",
    },
    {
        "id": "whistle_stop", "name": "Whistle-Stop",
        "steps": [("travel", None), ("travel", None), ("travel", None)],
        "recipe": "Make three trips between worlds within a minute.",
        "hint": "Three trips in one minute.",
    },
    {
        "id": "closed_loop", "name": "Closed Loop",
        "steps": [("route", None), ("rec", None), ("research", None)],
        "recipe": "Open a trade route, build a Recycler (anywhere), then buy a research node.",
        "hint": "Open a route, clean up after yourself, then think about the future.",
    },
    {
        "id": "mars_landing", "name": "Mars Landing",
        "steps": [("travel", "Mars"), ("mine", "Mars"), ("gen", "Mars")],
        "recipe": "Travel to Mars, mine there, then buy an Auto-Extractor.",
        "hint": "Land on the red planet and get to work straight away.",
    },
    {
        "id": "spread_thin", "name": "Spread Thin",
        "steps": [("gen", "*"), ("gen", "*"), ("gen", "*")],
        "recipe": "Buy an automation building on three different worlds within a minute (travelling between them).",
        "hint": "Automation on three different worlds in one minute.",
    },
    {
        "id": "skyward", "name": "Skyward",
        "steps": [("sky", None), ("route", None)],
        "recipe": "Build a Sky City, then open a trade route.",
        "hint": "After the clouds get a city, the cargo ships follow.",
    },
    {
        "id": "scholars_dash", "name": "Scholar's Dash",
        "steps": [("research", None), ("research", None), ("research", None)],
        "recipe": "Buy three research nodes within a minute.",
        "hint": "Three research nodes in one minute.",
    },
]
CHAIN_BY_ID = {chain["id"]: chain for chain in CHAINS}
chain_counts = {}  # chain id -> times fired, for life

_action_log = []  # (tick, kind, planet), oldest first, collapsed, never saved
_chain_cooldown_until = {}


def chains_found():
    return sum(1 for chain in CHAINS if chain_counts.get(chain["id"], 0) > 0)


def _step_matches(step, record, used):
    kind, planet = step
    if record[1] != kind:
        return False
    if planet is None:
        return True
    if planet == "*":
        return record[2] not in used
    return record[2] == planet


def _chain_match(steps, records):
    """True when `steps` occur in order among `records` (not necessarily
    adjacent), the last step on the newest record."""
    if len(records) < len(steps) or not _step_matches(steps[-1], records[-1], frozenset()):
        return False

    def search(step_index, record_index, used):
        if step_index < 0:
            return True
        for i in range(record_index, -1, -1):
            if _step_matches(steps[step_index], records[i], used):
                next_used = used | {records[i][2]} if steps[step_index][1] == "*" else used
                if search(step_index - 1, i - 1, next_used):
                    return True
        return False

    last_used = frozenset({records[-1][2]}) if steps[-1][1] == "*" else frozenset()
    return search(len(steps) - 2, len(records) - 2, last_used)


def _chain_reward(planet):
    state = planet_state[planet]
    return (CHAIN_REWARD_BASE + CHAIN_REWARD_PER_GENERATOR * state["generator_count"]) * _yield_multiplier()


def _fire_chain(chain, planet):
    _chain_cooldown_until[chain["id"]] = runstate.total_ticks + CHAIN_COOLDOWN_TICKS
    first = chain_counts.get(chain["id"], 0) == 0
    chain_counts[chain["id"]] = chain_counts.get(chain["id"], 0) + 1
    bonus = _chain_reward(planet)
    planet_state[planet]["resource_count"] += bonus
    update_resource_display(planet)
    unit = PLANETS[planet]["resource_name"]
    prefix = "⚡ New chain reaction" if first else "⚡ Chain reaction"
    _display_toast(f"{prefix}: {chain['name']}! +{math.floor(bonus)} {unit}")
    update_chains_display()


def _check_chains(planet):
    for chain in CHAINS:
        if runstate.total_ticks < _chain_cooldown_until.get(chain["id"], -1):
            continue
        records = [r for r in _action_log if r[0] >= runstate.total_ticks - CHAIN_WINDOW_TICKS]
        if _chain_match(chain["steps"], records):
            _fire_chain(chain, planet)


def _player_action(kind, planet):
    """Every action the player takes themselves passes through here: it
    counts towards that world's 'micromanagement' (A-22) and feeds the chain
    reactions. kind: mine | gen | rec | route | sky | travel | research."""
    if kind not in ("travel", "research"):
        state = planet_state[planet]
        state["player_actions"] = state.get("player_actions", 0) + 1
    if kind == "mine" and _action_log and _action_log[-1][1] == kind and _action_log[-1][2] == planet:
        _action_log[-1] = (runstate.total_ticks, kind, planet)
    else:
        _action_log.append((runstate.total_ticks, kind, planet))
        del _action_log[:-ACTION_LOG_MAX]
    if _setting_on(CHAIN_BONUS_KEY):
        _check_chains(planet)


def update_chains_display():
    toggle = document.getElementById("chains-toggle-button")
    panel = document.getElementById("chains-panel")
    found = chains_found()
    toggle.innerText = (
        f"Hide Chain Reactions ({found}/{len(CHAINS)})" if runstate.chains_open else f"⚡ Chain Reactions ({found}/{len(CHAINS)})"
    )
    panel.hidden = not runstate.chains_open
    if not runstate.chains_open:
        return
    panel.innerHTML = ""
    heading = document.createElement("h2")
    heading.className = "stats-panel-heading"
    heading.innerText = f"Chain reactions: {found} of {len(CHAINS)} found"
    panel.appendChild(heading)
    intro = document.createElement("p")
    intro.className = "chains-intro"
    intro.innerText = (
        "Do the right actions in the right order within a minute and a small bonus drops into that world. "
        "Each one can fire again after a couple of minutes. The Governor's purchases do not count. "
        "Turn the bonus off in Settings if you would rather not."
    )
    panel.appendChild(intro)
    for chain in CHAINS:
        count = chain_counts.get(chain["id"], 0)
        card = document.createElement("div")
        card.className = "chain-card chain-card--found" if count else "chain-card"
        name = document.createElement("p")
        name.className = "chain-card-name"
        name.innerText = f"⚡ {chain['name']}" if count else "Not found yet"
        card.appendChild(name)
        detail = document.createElement("p")
        detail.className = "chain-card-detail"
        detail.innerText = chain["recipe"] if count else f"Hint: {chain['hint']}"
        card.appendChild(detail)
        if count:
            times = document.createElement("p")
            times.className = "chain-card-count"
            times.innerText = f"Found, fired {count} time{'s' if count != 1 else ''}"
            card.appendChild(times)
        panel.appendChild(card)


# --- A-22: the Governor's mood ---------------------------------------------------
MOOD_ATTENTIVE_ACTIONS = 10
MOOD_HOVERING_ACTIONS = 100
GOVERNOR_MOODS = {
    "aggressive": (
        "Delighted to be left alone: has already ordered three more Auto-Miners and is not sorry.",
        "Tolerates your visits, as long as you do not touch the throttle.",
        "Says this is the fourth time you have rearranged its crates today.",
    ),
    "balanced": (
        "Serene. Has made a spreadsheet about it and the spreadsheet is happy.",
        "Notes your fingerprints on the ledger, politely.",
        "Is pretending not to notice you hovering over the buttons.",
    ),
    "conservative": (
        "Quietly pleased. Has recycled the paperwork twice already.",
        "Would like to remind you that every click has an ecological cost.",
        "Sighs, and files a complaint about unscheduled enthusiasm.",
    ),
}
GLOBAL_PRIORITY_PERSONALITY = {"growth": "aggressive", "balance": "balanced", "ecology": "conservative"}


def governor_mood(planet):
    state = planet_state[planet]
    personality = state.get("governor_personality", "default")
    if personality not in GOVERNOR_MOODS:
        personality = GLOBAL_PRIORITY_PERSONALITY.get(runstate.governor_priority, "balanced")
    actions = state.get("player_actions", 0)
    level = 0 if actions < MOOD_ATTENTIVE_ACTIONS else (1 if actions < MOOD_HOVERING_ACTIONS else 2)
    return GOVERNOR_MOODS[personality][level]
