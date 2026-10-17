"""Achievements (catalog, checks, progress, panel, toast), event badges and the end-of-run message helpers."""

import json

from js import document, localStorage, setTimeout
from pyodide.ffi import create_proxy

import aftermath_runstate as runstate
from aftermath_persist import SOCIETAL_MEMORY_BONUS, SOCIETAL_MEMORY_LABEL, _storage_write, societal_memory
from aftermath_rules import CODEX_CORE_TYPES, EVENT_LABEL, SKILLS


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL/Canopy/Grid's
# reference integrations. Every achievement's earned status is a pure
# function of state that already exists elsewhere in this module, recomputed
# fresh every call — never a separately hand-maintained "earned" flag.
#
# Several achievements here genuinely can't be derived from run_history/
# skill_tree/legacy_events alone: things like "ever invested in Resilience"
# or "ever finished a run in profit" are facts about a *specific run's*
# transient RunState, which resets every new run (§4's five-step pattern
# from the design doc — a persistent fact needs its own persistent tracked
# state, or it would flicker unearned the instant a new run starts). Those
# live in `achievement_progress`, a small persistent dict alongside the
# skill tree/run history/legacy events already in localStorage, mutated
# only where the real event happens (inside RunState's own methods, since
# that's where each of these facts actually becomes true) and otherwise
# read-only from every achievement checker below.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"
ACHIEVEMENT_PROGRESS_STORAGE_KEY = "aftermath_achievement_progress_v1"


def _read_achievements_json():
    """Same loading contract as SOL/Canopy/Grid's `_read_achievements_json()`:
    the boot script fetches achievements.json and hands it to Python as a
    window global before this file runs; the pytest harness's fake `js`
    module has no such attribute, so this falls through to reading the file
    straight off disk, keeping the module importable outside a real
    browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Aftermath's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

RUN_COMPLETE_TARGETS = {"run_complete_1": 1, "run_complete_5": 5, "run_complete_10": 10}
KNOWLEDGE_TARGETS = {"knowledge_25": 25, "knowledge_100": 100}
SKILL_ACHIEVEMENT_IDS = {
    "reinforced_infrastructure": "unlock_reinforced_infrastructure",
    "community_reserves": "unlock_community_reserves",
    "early_warning": "unlock_early_warning",
}


def _default_achievement_progress():
    return {
        "ever_faced_event": False,
        "ever_invested_resilience": False,
        "ever_invested_growth": False,
        "ever_maxed_mitigation": False,
        "ever_survived_severe_event": False,
        "ever_profitable_run": False,
        "ever_growth_heavy_run": False,
        "ever_resilience_heavy_run": False,
        "ever_balanced_run": False,
        # E15: build-diversity family.
        "ever_deep_specialist_run": False,
        "ever_broad_generalist_run": False,
        # GE-15: a Flawless Defense (event damage held to 15% of base).
        "ever_flawless_defense": False,
    }


def load_achievement_progress():
    progress = _default_achievement_progress()
    raw = localStorage.getItem(ACHIEVEMENT_PROGRESS_STORAGE_KEY)
    if not raw:
        return progress
    try:
        data = json.loads(raw)
    except ValueError:
        return progress
    if isinstance(data, dict):
        for key in progress:
            if key in data:
                progress[key] = bool(data[key])
    return progress


def save_achievement_progress():
    _storage_write(ACHIEVEMENT_PROGRESS_STORAGE_KEY, json.dumps(runstate.achievement_progress))


runstate.achievement_progress = load_achievement_progress()


def _note_achievement_progress(**updates):
    """Sets one or more achievement_progress flags to True (only ever True
    — these are one-way "has this ever happened" facts, never unset) and
    persists if anything actually changed."""
    changed = False
    for key, value in updates.items():
        if value and not runstate.achievement_progress.get(key):
            runstate.achievement_progress[key] = True
            changed = True
    if changed:
        save_achievement_progress()


def _full_skill_tree_earned():
    return all(skill_id in runstate.skill_tree.unlocked for skill_id in SKILLS)


ACHIEVEMENT_CHECKS = {
    "first_event_faced": lambda: runstate.achievement_progress["ever_faced_event"],
    "first_resilience_investment": lambda: runstate.achievement_progress["ever_invested_resilience"],
    "first_growth_investment": lambda: runstate.achievement_progress["ever_invested_growth"],
    "run_complete_1": lambda: len(runstate.run_history) >= RUN_COMPLETE_TARGETS["run_complete_1"],
    "run_complete_5": lambda: len(runstate.run_history) >= RUN_COMPLETE_TARGETS["run_complete_5"],
    "run_complete_10": lambda: len(runstate.run_history) >= RUN_COMPLETE_TARGETS["run_complete_10"],
    "unlock_reinforced_infrastructure": lambda: "reinforced_infrastructure" in runstate.skill_tree.unlocked,
    "unlock_community_reserves": lambda: "community_reserves" in runstate.skill_tree.unlocked,
    "unlock_early_warning": lambda: "early_warning" in runstate.skill_tree.unlocked,
    "full_skill_tree": _full_skill_tree_earned,
    "knowledge_25": lambda: runstate.skill_tree.lifetime_knowledge >= KNOWLEDGE_TARGETS["knowledge_25"],
    "knowledge_100": lambda: runstate.skill_tree.lifetime_knowledge >= KNOWLEDGE_TARGETS["knowledge_100"],
    "iron_defenses": lambda: runstate.achievement_progress["ever_maxed_mitigation"],
    "severe_survivor": lambda: runstate.achievement_progress["ever_survived_severe_event"],
    "profitable_run": lambda: runstate.achievement_progress["ever_profitable_run"],
    "growth_focused": lambda: runstate.achievement_progress["ever_growth_heavy_run"],
    "resilience_focused": lambda: runstate.achievement_progress["ever_resilience_heavy_run"],
    "balanced_strategy": lambda: runstate.achievement_progress["ever_balanced_run"],
    "deep_specialist": lambda: runstate.achievement_progress["ever_deep_specialist_run"],
    "broad_generalist": lambda: runstate.achievement_progress["ever_broad_generalist_run"],
    "both_paths": lambda: runstate.achievement_progress["ever_deep_specialist_run"]
    and runstate.achievement_progress["ever_broad_generalist_run"],
    "come_back_stronger": lambda: len(runstate.run_history) >= 2 and runstate.run_history[-1] > runstate.run_history[0],
    # GE-15 / E-12: collector and mastery achievements.
    "flawless_defense": lambda: runstate.achievement_progress["ever_flawless_defense"],
    "codex_complete": lambda: all(t in runstate.legacy_events for t in CODEX_CORE_TYPES),
    "codex_full_record": lambda: all(t in runstate.legacy_events for t in EVENT_LABEL),
    "heat_health_faced": lambda: "heat_mortality" in runstate.legacy_events,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone.
ACHIEVEMENT_PROGRESS = {
    "run_complete_5": lambda: (min(len(runstate.run_history), 5), 5),
    "run_complete_10": lambda: (min(len(runstate.run_history), 10), 10),
    "full_skill_tree": lambda: (len(runstate.skill_tree.unlocked & set(SKILLS)), len(SKILLS)),
    "knowledge_25": lambda: (min(runstate.skill_tree.lifetime_knowledge, 25), 25),
    "knowledge_100": lambda: (min(runstate.skill_tree.lifetime_knowledge, 100), 100),
    "codex_complete": lambda: (sum(1 for t in CODEX_CORE_TYPES if t in runstate.legacy_events), len(CODEX_CORE_TYPES)),
    "codex_full_record": lambda: (sum(1 for t in EVENT_LABEL if t in runstate.legacy_events), len(EVENT_LABEL)),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


def _seed_achievement_toast_baseline():
    runstate._achievements_seen_ids = set(achievement_ids_earned())


def _display_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (invest resilience/growth, resolve an event, unlock a skill, start a
    new run) — never from render() itself, since load_state() also calls
    render() and a loaded save with several achievements already earned
    must not flood the player with toasts for all of them at once (see
    _seed_achievement_toast_baseline)."""
    earned_now = set(achievement_ids_earned())
    newly = earned_now - runstate._achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    runstate._achievements_seen_ids = earned_now


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if runstate.achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not runstate.achievements_open
    if not runstate.achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        card.dataset.achievementId = entry["id"]

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5).
    # Relative path, no leading "/" (site-level milestone 7's GitHub Pages
    # subpath fix). Rebuilt each open alongside the cards since the panel
    # is cleared first. Note: the hub-side script.js registration that
    # makes Aftermath's save data actually show up on that dashboard is a
    # root-file change, out of scope for this games/aftermath/-only
    # dispatch.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


# N-2: seasonal event badges (shared/seasonal-events.js grants them; this list is the copy that rides the save).
EVENT_BADGE_MAX = 40


def _clean_event_badges(raw):
    """Keep only well-formed hub badge entries ({id, label, earned_at}); drop duplicates and junk."""
    out = []
    seen = set()
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        badge_id, label, earned = item.get("id"), item.get("label"), item.get("earned_at", "")
        if not (isinstance(badge_id, str) and 1 <= len(badge_id) <= 64 and badge_id not in seen):
            continue
        if not all(c.isascii() and (c.islower() or c.isdigit() or c == "-") for c in badge_id):
            continue
        if not (isinstance(label, str) and 1 <= len(label.strip()) <= 80):
            continue
        if not (isinstance(earned, str) and len(earned) <= 32):
            earned = ""
        seen.add(badge_id)
        out.append({"id": badge_id, "label": label.strip(), "earned_at": earned})
        if len(out) >= EVENT_BADGE_MAX:
            break
    return out


def set_event_badges(badges_json):
    """Called by the page (shared/seasonal-events.js onGrant) with the whole badge list as JSON text."""
    try:
        runstate.event_badges = _clean_event_badges(json.loads(badges_json))
    except (TypeError, ValueError):
        return False
    return True


def _season_hook(name, argument):
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, name, None)
    if hook is not None:
        hook(argument)


def _season_run_finished(resources_left):
    """N-2 Halloween task ("Night of Storms"): the page counts a finished run with resources left."""
    _season_hook("aftermathRunFinished", resources_left)


def societal_memory_message():
    """E29: what the settlement remembers, plus a one-time note the round a
    memory forms."""
    parts = []
    if runstate.memory_just_formed:
        bonus = round(SOCIETAL_MEMORY_BONUS[runstate.memory_just_formed] * 100)
        parts.append(
            f"That run left a mark: your settlement will remember {SOCIETAL_MEMORY_LABEL[runstate.memory_just_formed]} "
            f"and take {bonus}% less damage from that kind of shock from now on."
        )
        runstate.memory_just_formed = None
    if societal_memory:
        remembered = ", ".join(sorted(societal_memory))
        parts.append(f"Societal memory: {remembered} shocks (permanent protection earned the hard way).")
    return " ".join(parts)


def legacy_message():
    if not runstate.legacy_events:
        return "No history yet — this is the settlement's first trial."
    labels = sorted(EVENT_LABEL[event_type] for event_type in runstate.legacy_events)
    return (
        f"This settlement has weathered {', '.join(labels)} before — every run's "
        f"damage becomes part of what the next one is built to withstand."
    )


def progress_comparison():
    """The hope-angle payoff: run 1 vs. the most recent run, same event
    schedule. None until at least two runs have been completed."""
    if len(runstate.run_history) < 2:
        return None
    return runstate.run_history[0], runstate.run_history[-1]


def progress_message(comparison):
    if comparison is None:
        return "Play more runs to see how far you've come."
    first, latest = comparison
    if latest > first:
        return (
            f"Look how far you've come — your first run scored {first:.0f}, "
            f"your most recent scored {latest:.0f}. Same events, handled better."
        )
    if latest < first:
        return f"Your most recent run ({latest:.0f}) scored lower than your first ({first:.0f})."
    return f"Your run performance has held steady at {latest:.0f}."
