"""Saving and loading: storage helpers and health, the saved records (skill tree, run history, legacy, societal memory, curriculum, meta and its sanitizers, second founding data) and the skill-tree strength."""

import json
import time

import ghost as ghost_lib
from js import document, localStorage

import aftermath_runstate as runstate
from aftermath_rules import (
    AWARDED_RUN_STORAGE_KEY, EVENT_LABEL, LEGACY_COUNTS_STORAGE_KEY, LEGACY_STORAGE_KEY,
    RUN_HISTORY_STORAGE_KEY, RUN_LOG_HISTORY_STORAGE_KEY, SCENARIOS, SKILLS, SKILL_TREE_STORAGE_KEY,
)


# ---------------------------------------------------------------------------
# E-30: save health. Every write to the browser's localStorage goes through
# _storage_write(), which remembers when the last write succeeded and which
# keys failed (a full or blocked store throws), so the badge can say "Saved 12s
# ago", "Not saved: storage full or blocked" or "Unsaved changes" truthfully.
# ---------------------------------------------------------------------------
STORAGE_PROBE_KEY = "aftermath_storage_probe"
_storage_state = {"last_ok": None, "failed": {}}


def _now():
    """Seconds since the epoch (tests replace this to move the clock)."""
    return time.time()


def _storage_write(key, value):
    """localStorage.setItem that never raises: returns True when the write went through."""
    try:
        localStorage.setItem(key, value)
    except Exception as error:  # a JsException (quota or blocked) in Pyodide; any error here means "not saved"
        _storage_state["failed"][key] = str(error)[:120] or "storage error"
        return False
    _storage_state["failed"].pop(key, None)
    _storage_state["last_ok"] = _now()
    return True


def probe_storage():
    """Tries a tiny write and delete. A failure is remembered under STORAGE_PROBE_KEY and cleared
    again by the next probe that works, so the badge recovers after space is freed."""
    try:
        localStorage.setItem(STORAGE_PROBE_KEY, "1")
        localStorage.removeItem(STORAGE_PROBE_KEY)
    except Exception as error:
        _storage_state["failed"][STORAGE_PROBE_KEY] = str(error)[:120] or "storage error"
        return False
    _storage_state["failed"].pop(STORAGE_PROBE_KEY, None)
    return True


def format_age(seconds):
    """'just now', '12s ago', '3 min ago', '2 h ago' (ui.js keeps the same wording while the page is open)."""
    seconds = max(0, int(seconds))
    if seconds < 5:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    return f"{seconds // 3600} h ago"


def _read_json(key):
    """(found, value): the parsed stored JSON, (False, None) when absent, (None, None) when unreadable."""
    try:
        raw = localStorage.getItem(key)
    except Exception:
        return None, None
    if not raw:
        return False, None
    try:
        return True, json.loads(raw)
    except ValueError:
        return None, None


def unsaved_progress():
    """Which kinds of progress in memory differ from what the browser has stored. Normally empty:
    every change is written at once. Not empty if the stored copy was cleared or replaced from outside
    (another tab, browser tools, storage eviction) or a write silently did not stick."""
    problems = []
    found, stored = _read_json(SKILL_TREE_STORAGE_KEY)
    mine = runstate.skill_tree.to_dict()
    if found is None:
        problems.append("skill tree")
    elif found and (
        not isinstance(stored, dict)
        or stored.get("knowledge_points", 0) != mine["knowledge_points"]
        or sorted(stored.get("unlocked", [])) != mine["unlocked"]
    ):
        problems.append("skill tree")
    elif not found and (mine["knowledge_points"] or mine["unlocked"]):
        problems.append("skill tree")
    found, stored = _read_json(RUN_HISTORY_STORAGE_KEY)
    if found is None or (found and stored != runstate.run_history) or (not found and runstate.run_history):
        problems.append("run history")
    found, stored = _read_json(META_STORAGE_KEY)
    if found is None or (found and _sanitize_meta(stored) != runstate.meta) or (not found and runstate.meta != _default_meta()):
        problems.append("settlement notes and presets")
    return problems


def storage_health():
    """(state, text): state is 'failed', 'unsaved', 'saved' or 'ready'."""
    if _storage_state["failed"]:
        if STORAGE_PROBE_KEY in _storage_state["failed"]:
            probe_storage()  # space may have been freed since
        if _storage_state["failed"]:
            return "failed", (
                "\u26a0 Not saved: this browser's storage is full or blocked, so new progress is only "
                "kept until you close the page. Export your progress now."
            )
    problems = unsaved_progress()
    if problems:
        return "unsaved", (
            "\u26a0 Unsaved changes: your " + ", ".join(problems) + " on this page differ from what this browser has "
            "stored. Export your progress to be safe."
        )
    last = _storage_state["last_ok"]
    if last is None:
        return "ready", "\u2713 Progress saves to this browser automatically."
    return "saved", f"\u2713 Saved {format_age(_now() - last)}"


def skill_tree_strength():
    """How many resilience skills are unlocked overall — the signal Pass
    3 uses to widen event-severity variation so a stronger skill tree
    keeps facing a wider spread of challenge, not a flat one."""
    return len(runstate.skill_tree.unlocked)


def load_highest_awarded_run():
    raw = localStorage.getItem(AWARDED_RUN_STORAGE_KEY)
    if not raw:
        return 0
    try:
        return int(json.loads(raw))
    except (ValueError, TypeError):
        return 0


def save_highest_awarded_run(run_number):
    _storage_write(AWARDED_RUN_STORAGE_KEY, json.dumps(run_number))


def load_legacy_events():
    raw = localStorage.getItem(LEGACY_STORAGE_KEY)
    if not raw:
        return set()
    try:
        return set(json.loads(raw))
    except ValueError:
        return set()


def save_legacy_events(events):
    _storage_write(LEGACY_STORAGE_KEY, json.dumps(sorted(events)))


# E29: societal memory. A settlement that comes through a run in ruins does
# not forget: the category of shock that did the most damage in that run
# leaves a permanent, unique defence (the memory of what went wrong). It is
# not a purchase and cannot be bought otherwise: a non-weather category
# (supply chain, infrastructure) has no specialization in the skill tree at
# all, so its memory is the only dedicated protection it can ever get and is
# the strongest; a weather or social memory is smaller because the tree already
# offers those. Kept per browser like the skill tree, and only formed by a run
# that ends at or below VERY_BAD_RUN_SCORE, so a rough-but-alive run never
# triggers it.
SOCIETAL_MEMORY_STORAGE_KEY = "aftermath_societal_memory_v1"
VERY_BAD_RUN_SCORE = 10.0
SOCIETAL_MEMORY_BONUS = {"weather": 0.15, "social": 0.15, "non-weather": 0.25, "health": 0.25}
SOCIETAL_MEMORY_LABEL = {
    "weather": "the weather that broke it",
    "social": "the unrest that broke it",
    "non-weather": "the systems failure that broke it",
    "health": "the health emergency that broke it",
}


def load_societal_memory():
    raw = localStorage.getItem(SOCIETAL_MEMORY_STORAGE_KEY)
    if not raw:
        return set()
    try:
        data = json.loads(raw)
    except ValueError:
        return set()
    if not isinstance(data, list):
        return set()
    return {c for c in data if isinstance(c, str) and c in SOCIETAL_MEMORY_BONUS}


def save_societal_memory(categories):
    _storage_write(SOCIETAL_MEMORY_STORAGE_KEY, json.dumps(sorted(categories)))


# E19: the resilience curriculum. A guided sequence of runs, each with one
# specific goal that teaches one idea, done in order: the current lesson is the
# only one that can be completed, and it is judged on the run's FINAL state when
# it pays out. Progress is a plain count kept per browser
# (aftermath_curriculum_v1), like the skill tree; the lessons never change
# any number in a run, they only name a goal and notice when it is met.
CURRICULUM_STORAGE_KEY = "aftermath_curriculum_v1"
CURRICULUM = [
    {
        "id": "first_steps",
        "title": "First steps",
        "goal": "Finish a run with resources still in hand.",
        "idea": "A settlement can absorb a bad year if it isn't running on empty.",
        "check": lambda r: r.resources > 0,
    },
    {
        "id": "resilience_first",
        "title": "Resilience first",
        "goal": "Finish with at least 3 resilience and resources still in hand.",
        "idea": "Resilience shrinks every shock that follows it, so it pays back the earlier it is built.",
        "check": lambda r: r.resilience_capacity >= 3 and r.resources > 0,
    },
    {
        "id": "growth_pays",
        "title": "Growth pays",
        "goal": "Finish with at least 2 growth and more resources than you started with.",
        "idea": "Growth is an income that keeps arriving between disasters.",
        "check": lambda r: r.growth_capacity >= 2 and r.resources > r.starting_resources,
    },
    {
        "id": "balance",
        "title": "Balance",
        "goal": "Finish with at least 2 growth, at least 2 resilience and 100+ resources.",
        "idea": "Protection and income together beat either alone.",
        "check": lambda r: r.growth_capacity >= 2 and r.resilience_capacity >= 2 and r.resources >= 100,
    },
    {
        "id": "coastal_test",
        "title": "The coastal test",
        "goal": "Choose the Coastal scenario and finish with resources in hand.",
        "idea": "Different places face different shocks, so the same plan is tested differently.",
        "check": lambda r: r.scenario == "coastal" and r.resources > 0,
    },
]


def load_curriculum_progress():
    raw = localStorage.getItem(CURRICULUM_STORAGE_KEY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(0, min(len(CURRICULUM), value))


def save_curriculum_progress(value):
    _storage_write(CURRICULUM_STORAGE_KEY, str(value))


def curriculum_current():
    """The lesson the player is on, or None once every lesson is done."""
    if runstate.curriculum_progress >= len(CURRICULUM):
        return None
    return CURRICULUM[runstate.curriculum_progress]


def note_curriculum_run(finished_run):
    """Called once when a run completes and pays out. If it meets the CURRENT
    lesson's goal, advances the curriculum and returns that lesson; else None."""
    lesson = curriculum_current()
    if lesson is None or not lesson["check"](finished_run):
        return None
    runstate.curriculum_progress += 1
    save_curriculum_progress(runstate.curriculum_progress)
    return lesson


def curriculum_message():
    parts = []
    if runstate.curriculum_just_completed:
        parts.append(f"Lesson complete: {runstate.curriculum_just_completed['title']}. {runstate.curriculum_just_completed['idea']}")
        runstate.curriculum_just_completed = None
    lesson = curriculum_current()
    if lesson is None:
        parts.append(f"Curriculum complete: all {len(CURRICULUM)} lessons done.")
    else:
        parts.append(
            f"Curriculum, lesson {runstate.curriculum_progress + 1} of {len(CURRICULUM)}: {lesson['title']}. Goal: {lesson['goal']}"
        )
    return " ".join(parts)


def load_run_history():
    raw = localStorage.getItem(RUN_HISTORY_STORAGE_KEY)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except ValueError:
        return []


def save_run_history(history):
    _storage_write(RUN_HISTORY_STORAGE_KEY, json.dumps(history))


def load_legacy_event_counts():
    """E4: how many times this settlement has weathered each event type,
    additive to (not a replacement for) the pre-existing ever-weathered
    `legacy_events` set above."""
    raw = localStorage.getItem(LEGACY_COUNTS_STORAGE_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): int(value) for key, value in data.items() if isinstance(value, (int, float))}


def save_legacy_event_counts(counts):
    _storage_write(LEGACY_COUNTS_STORAGE_KEY, json.dumps(counts))


def load_run_log_history():
    """E7: the persisted event-by-event breakdown for every completed run
    (a superset of run_history, which only ever stored the final score).
    Starts empty even for a returning player with existing run_history --
    runs completed before this feature shipped simply have no detailed
    breakdown to show, which the review UI handles gracefully."""
    raw = localStorage.getItem(RUN_LOG_HISTORY_STORAGE_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def save_run_log_history(history):
    _storage_write(RUN_LOG_HISTORY_STORAGE_KEY, json.dumps(history))


# Small persistent "settlement meta" dict (E25 settlement name, E30b pinned
# skills, E8/E28 one-time-callout flags). Lives in localStorage next to the
# skill tree, same category and same reasoning (cross-run progress, not
# per-run save-widget state); safe defaults for every field so an older
# browser profile with no such key just gets the empty defaults.
META_STORAGE_KEY = "aftermath_meta_v1"
SETTLEMENT_NAME_MAX = 30
RUN_NOTE_MAX_CHARS = 140
RUN_NOTES_MAX = 500


def _default_meta():
    return {
        "settlement_name": "",
        "pinned_skills": [],
        "seen_negative_tip": False,
        "seen_harsh_callout": False,
        # E-22 / E-21: a short note per completed run (keyed by run number as a string) and the
        # run numbers the player has archived from the Past Runs list.
        "run_notes": {},
        "archived_runs": [],
        # E-25: named allocation presets ([{"name", "resilience", "growth"}]).
        "presets": [],
        # E-13: named player-built schedules ([{"name", "events"}]).
        "custom_schedules": [],
        # E-4: how many friend challenges have been finished, and the best score per code.
        "challenge_runs": 0,
        "challenge_best": {},
        # E-11: proven-use progress per skill ({skill_id: count}); a skill's rank is read from its count.
        "skill_progress": {},
        # GE-10: Founding stars and the Founding skills owned ({"stars", "owned"}).
        "founding": {"stars": 0, "owned": []},
        # E-7: the chronicle's lines that cannot be worked out from the run history ([{"after", "kind", "text"}]).
        "chronicle": [],
    }


PRESET_MAX = 8
PRESET_NAME_MAX = 24
PRESET_UNITS_MAX = 20
CUSTOM_SCHEDULES_MAX = 12
CUSTOM_NAME_MAX = 24
CUSTOM_MIN_EVENTS = 3
CUSTOM_MAX_EVENTS = 7
CHALLENGE_BEST_MAX = 40


def _clean_name(text, limit):
    return " ".join(str(text or "").split())[:limit]


def _units(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = int(value)
    return value if 0 <= value <= PRESET_UNITS_MAX else None


def _sanitize_presets(value):
    out = []
    if not isinstance(value, list):
        return out
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _clean_name(item.get("name"), PRESET_NAME_MAX)
        resilience, growth = _units(item.get("resilience")), _units(item.get("growth"))
        if not name or resilience is None or growth is None or resilience + growth < 1:
            continue
        if any(p["name"].casefold() == name.casefold() for p in out):
            continue
        out.append({"name": name, "resilience": resilience, "growth": growth})
        if len(out) >= PRESET_MAX:
            break
    return out


def _sanitize_custom_schedules(value):
    out = []
    if not isinstance(value, list):
        return out
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _clean_name(item.get("name"), CUSTOM_NAME_MAX)
        events = item.get("events")
        if (
            not name
            or not isinstance(events, list)
            or not CUSTOM_MIN_EVENTS <= len(events) <= CUSTOM_MAX_EVENTS
            or not all(isinstance(e, str) and e in EVENT_LABEL for e in events)
        ):
            continue
        if any(c["name"].casefold() == name.casefold() for c in out):
            continue
        out.append({"name": name, "events": list(events)})
        if len(out) >= CUSTOM_SCHEDULES_MAX:
            break
    return out


# E-7: the Settlement Chronicle. Most of its lines are WORKED OUT from the run history (first of each event, worst
# disaster, new best score, first Flawless Defense), so every old save already has a chronicle. The few things the
# history cannot know (a skill adopted, a point moved, a memory formed, a lesson finished, a Second Founding) are
# stored here: `after` = how many runs had been paid out when it happened, `kind` one of CHRONICLE_KINDS, `text` the line.
CHRONICLE_KINDS = {"skill": "\U0001f9e0", "move": "\U0001f501", "memory": "\U0001f56f", "lesson": "\U0001f393", "founding": "\u2b50"}
CHRONICLE_MAX = 300
CHRONICLE_TEXT_MAX = 160
CHRONICLE_AFTER_MAX = 1_000_000


def _sanitize_chronicle(value):
    """Known kinds only, `after` a whole number 0 to 1,000,000, text a non-empty string cut to 160 characters; anything
    else is dropped, and only the newest CHRONICLE_MAX lines are kept."""
    out = []
    if not isinstance(value, list):
        return out
    for item in value:
        if not isinstance(item, dict):
            continue
        kind, after, text = item.get("kind"), item.get("after"), item.get("text")
        if (
            not isinstance(kind, str) or kind not in CHRONICLE_KINDS
            or isinstance(after, bool) or not isinstance(after, (int, float)) or not 0 <= after <= CHRONICLE_AFTER_MAX
            or not isinstance(text, str) or not text.strip()
        ):
            continue
        out.append({"after": int(after), "kind": kind, "text": " ".join(text.split())[:CHRONICLE_TEXT_MAX]})
    return out[-CHRONICLE_MAX:]


SKILL_PROGRESS_MAX = 1_000_000


def _sanitize_skill_progress(value):
    """E-11: known skill ids only, each a whole number from 0 to SKILL_PROGRESS_MAX (anything else is dropped,
    so a hand-edited or damaged code can never invent a rank)."""
    out = {}
    if not isinstance(value, dict):
        return out
    for skill_id, count in value.items():
        if skill_id not in SKILLS or isinstance(count, bool) or not isinstance(count, (int, float)):
            continue
        count = int(count)
        if count > 0:
            out[skill_id] = min(count, SKILL_PROGRESS_MAX)
    return out


# GE-10: the Second Founding. An OPTIONAL prestige: once every skill is owned the tree can be given up for a
# permanent Founding star (a small starting perk) and three Founding-only skills with strong trade-offs. They
# live apart from SKILLS (so "X of 7 skills", every old save and the tree's storage are untouched) in
# meta["founding"] = {"stars": 0..3, "owned": [ids]}. Every effect is a flat, deterministic number.
FOUNDING_MAX_STARS = 3
FOUNDING_STAR_RESOURCES = 10  # starting resources per star, for good
FOUNDING_SKILLS = {
    "stormwall_doctrine": {
        "label": "Stormwall Doctrine",
        "cost": 8,
        "gain": "Flood, Heatwave and Storm damage -40% (it adds to Climate Hardening)",
        "price": "you start every run with 80 fewer resources",
    },
    "open_granaries": {
        "label": "Open Granaries",
        "cost": 8,
        "gain": "Supply-chain, infrastructure-failure and heat-health damage -30%",
        "price": "you start every run with 60 fewer resources",
    },
    "frontier_charter": {
        "label": "Frontier Charter",
        "cost": 10,
        "gain": "+100 starting resources and +2 starting growth",
        "price": "Early Warning Systems and Mutual Aid Network stop adding any mitigation",
    },
}
FOUNDING_START_RESOURCES = {"stormwall_doctrine": -80, "open_granaries": -60, "frontier_charter": 100}
FOUNDING_START_GROWTH = {"frontier_charter": 2}
FOUNDING_CATEGORY_BONUS = (
    ("stormwall_doctrine", "weather", 0.40),
    ("open_granaries", "non-weather", 0.30),
    ("open_granaries", "health", 0.30),
)
FOUNDING_SILENCES = {"frontier_charter": ("early_warning", "mutual_aid_network")}


def _default_founding():
    return {"stars": 0, "owned": []}


def _sanitize_founding(value):
    """Stars 0 to FOUNDING_MAX_STARS (whole numbers), owned = known Founding skill ids, no repeats, and none at all
    without a star (a hand-edited code cannot hand out Founding skills)."""
    out = _default_founding()
    if not isinstance(value, dict):
        return out
    stars = value.get("stars", 0)
    if isinstance(stars, bool) or not isinstance(stars, (int, float)):
        return out
    out["stars"] = max(0, min(FOUNDING_MAX_STARS, int(stars)))
    owned = value.get("owned", [])
    if out["stars"] >= 1 and isinstance(owned, list):
        out["owned"] = [s for s in FOUNDING_SKILLS if s in owned]
    return out


GHOST_STORAGE_KEY = "aftermath-ghost-on"   # a display preference (not part of any save): "0" switches the ghost note off


def ghost_mode_lengths():
    """Z-3d: the ghost modes and how many events each one's run has: every scenario, and its doubled
    (extended) form under the key "<scenario>:long"."""
    out = {}
    for name, scenario in SCENARIOS.items():
        out[name] = len(scenario["schedule"])
        out[name + ":long"] = len(scenario["schedule"]) * 2
    return out


def ghost_mode_key(scenario, extended):
    return scenario + (":long" if extended else "")


def _sanitize_ghosts(value):
    """Z-3d: meta["ghosts"], {mode key: {"run", "score", "trace"}}: your best finished run per schedule, as a
    shared ghost trace of the resources left after each event. Every entry is cleaned through ghost.load; an
    unknown mode, a bad score or a trace whose length is not that schedule's event count is dropped."""
    out = {}
    if not isinstance(value, dict):
        return out
    lengths = ghost_mode_lengths()
    for key, item in value.items():
        if key not in lengths or not isinstance(item, dict):
            continue
        trace = ghost_lib.load(item.get("trace"))
        score = ghost_lib.clean_number(item.get("score"))
        run_number = item.get("run")
        if trace is None or score is None or trace["turns"] != lengths[key]:
            continue
        if isinstance(run_number, bool) or not isinstance(run_number, int) or run_number < 1:
            run_number = 0
        out[key] = {"run": min(run_number, 10 ** 9), "score": score, "trace": trace}
    return out


def _sanitize_meta(data):
    meta = _default_meta()
    if not isinstance(data, dict):
        return meta
    name = data.get("settlement_name", "")
    if isinstance(name, str):
        meta["settlement_name"] = name.strip()[:SETTLEMENT_NAME_MAX]
    pinned = data.get("pinned_skills", [])
    if isinstance(pinned, list):
        meta["pinned_skills"] = [p for p in pinned if isinstance(p, str)]
    meta["seen_negative_tip"] = bool(data.get("seen_negative_tip", False))
    meta["seen_harsh_callout"] = bool(data.get("seen_harsh_callout", False))
    notes = data.get("run_notes", {})
    if isinstance(notes, dict):
        for key, value in list(notes.items())[:RUN_NOTES_MAX]:
            if isinstance(value, str) and value.strip() and str(key).isdigit():
                meta["run_notes"][str(key)] = value.strip()[:RUN_NOTE_MAX_CHARS]
    archived = data.get("archived_runs", [])
    if isinstance(archived, list):
        meta["archived_runs"] = sorted({a for a in archived if isinstance(a, int) and not isinstance(a, bool) and a > 0})
    meta["presets"] = _sanitize_presets(data.get("presets", []))
    meta["custom_schedules"] = _sanitize_custom_schedules(data.get("custom_schedules", []))
    played = data.get("challenge_runs", 0)
    if isinstance(played, int) and not isinstance(played, bool) and played > 0:
        meta["challenge_runs"] = played
    best = data.get("challenge_best", {})
    if isinstance(best, dict):
        for code, value in list(best.items())[:CHALLENGE_BEST_MAX]:
            if isinstance(code, str) and isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                meta["challenge_best"][code[:90]] = int(value)
    meta["skill_progress"] = _sanitize_skill_progress(data.get("skill_progress", {}))
    meta["founding"] = _sanitize_founding(data.get("founding", {}))
    meta["chronicle"] = _sanitize_chronicle(data.get("chronicle", []))
    ghosts = _sanitize_ghosts(data.get("ghosts"))  # Z-3d: the key exists only once a ghost does
    if ghosts:
        meta["ghosts"] = ghosts
    return meta


def load_meta():
    raw = localStorage.getItem(META_STORAGE_KEY)
    if not raw:
        return _default_meta()
    try:
        return _sanitize_meta(json.loads(raw))
    except ValueError:
        return _default_meta()


def save_meta():
    _storage_write(META_STORAGE_KEY, json.dumps(runstate.meta))


runstate.meta = load_meta()

societal_memory = load_societal_memory()  # E29

run_log_history = load_run_log_history()


def _el(element_id):
    """getElementById that returns None for an id a cached older page does not have (the real DOM
    returns null; the test fake raises KeyError)."""
    try:
        return document.getElementById(element_id)
    except KeyError:
        return None


def _focus(element):
    try:
        element.focus()
    except Exception:
        pass
