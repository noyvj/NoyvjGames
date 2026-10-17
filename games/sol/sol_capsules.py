"""Time Capsules: frozen run snapshots you can compare and branch from."""

import copy
import json

from js import document

import sol_runstate as runstate
from sol_headless import _run_headless
from sol_rules import GOVERNOR_PERSONALITIES, PLANETS, SPECIALIZATION_LABELS, planet_state
from sol_runmods import _run_ticks
from sol_util import (
    _fresh_planet_state, _make_button, _make_text, _mmss, _read_local_storage_item,
    _write_local_storage_item,
)


# --- A-17 / A-18: Time Capsules ---------------------------------------------------------
# A capsule is a photograph of every world at one moment (kept in this browser, never in
# the save code, at most three, each with a name). It never changes your game. "Replay"
# runs a three-minute branch on a copy (the same copy-run-restore machinery as the Doctrine
# dry run and the Stress Test) with nobody at the controls: the Governor and your Doctrines
# run every world, using your current research and perks. "Compare with now" (A-18) puts
# how far you have come since the capsule beside what the Governor alone would have done in
# the same time (up to five minutes). A branch never touches the DOM, achievements, boards,
# lifetime counters or the real save: everything is put back in a `finally`.
CAPSULE_MAX = 3
CAPSULE_NAME_MAX = 30
CAPSULE_BRANCH_TICKS = 1800  # the replay: 3 minutes of game time
CAPSULE_DIFF_CAP = 3000  # the comparison replays as long as you have played since, up to 5 minutes
CAPSULE_STORAGE_KEY = "sol-capsules-v1"
_CAPSULE_NUMBERS = ("resource_count", "generator_count", "recycler_count", "ecology_health",
                    "terraform_progress", "governed_resource_generated", "player_actions", "sky_city_count")
capsules = []  # [{"id", "name", "tick", "prestige", "unlocked", "planets", "metrics"}], oldest first
_capsule_notes = {}  # capsule id -> {"replay": text, "diff": text}, this session only

_capsule_refs = {}


def capsule_metrics(planets, unlocked):
    """The few numbers a capsule is compared by, from a {planet: state} dict over the worlds that were open."""
    worlds = [p for p in PLANETS if p == "Earth" or p in unlocked]
    count = len(worlds)
    return {
        "worlds": count,
        "terraform": round(sum(planets[p]["terraform_progress"] for p in worlds) / count, 1),
        "ecology": round(sum(planets[p]["ecology_health"] for p in worlds) / count, 1),
        "machines": sum(planets[p]["generator_count"] + planets[p]["recycler_count"] for p in worlds),
        "banked": round(sum(planets[p]["resource_count"] for p in worlds)),
    }


def _live_metrics():
    return capsule_metrics(planet_state, set(runstate.unlocked_bodies))


def freeze_capsule(name=""):
    """Freezes every world as a new capsule. Returns the capsule, or None when three are already kept."""
    if len(capsules) >= CAPSULE_MAX or runstate._scarcity is not None:
        return None
    clean = " ".join(str(name).split())[:CAPSULE_NAME_MAX] or f"Capsule {runstate._capsule_next_id} at {_mmss(_run_ticks())}"
    capsule = {
        "id": runstate._capsule_next_id, "name": clean, "tick": runstate.total_ticks, "prestige": runstate.prestige_level,
        "unlocked": sorted(runstate.unlocked_bodies), "planets": copy.deepcopy(planet_state),
        "metrics": _live_metrics(),
    }
    runstate._capsule_next_id += 1
    capsules.append(capsule)
    _save_capsules()
    return capsule


def delete_capsule(capsule_id):
    for capsule in list(capsules):
        if capsule["id"] == capsule_id:
            capsules.remove(capsule)
            _capsule_notes.pop(capsule_id, None)
            _save_capsules()
            return True
    return False


def _find_capsule(capsule_id):
    for capsule in capsules:
        if capsule["id"] == capsule_id:
            return capsule
    return None


def branch_from_capsule(capsule, ticks):
    """A-17: the sandbox branch. Runs `ticks` of simulate + Governor + Doctrines from the capsule's worlds with nobody
    standing anywhere, on a copy: the live game is put back exactly. Returns the metrics after the branch."""
    live_state = copy.deepcopy(planet_state)
    live_unlocked = set(runstate.unlocked_bodies)
    result = []
    try:
        for planet, values in capsule["planets"].items():
            planet_state[planet].clear()
            planet_state[planet].update(copy.deepcopy(values))
        runstate.unlocked_bodies = set(capsule["unlocked"])

        def _grab(index):
            if index == ticks - 1:
                result.append(capsule_metrics(planet_state, runstate.unlocked_bodies))

        _run_headless(ticks, on_tick=_grab, all_governed=True)
    finally:
        runstate.unlocked_bodies = live_unlocked
        for planet, values in live_state.items():
            planet_state[planet].clear()
            planet_state[planet].update(values)
    return result[0] if result else capsule["metrics"]


def _signed(value, unit=""):
    return f"{value:+,.0f}{unit}" if abs(value - round(value)) < 0.05 else f"{value:+,.1f}{unit}"


def _metrics_change(before, after):
    return (f"terraform {_signed(after['terraform'] - before['terraform'], ' points')} "
            f"({before['terraform']:g}% to {after['terraform']:g}%), "
            f"ecology {_signed(after['ecology'] - before['ecology'], ' points')} "
            f"({before['ecology']:g}% to {after['ecology']:g}%), "
            f"machines {_signed(after['machines'] - before['machines'])}, "
            f"banked {_signed(after['banked'] - before['banked'])}")


def _capsule_blocked(capsule_id):
    text = "A Scarcity Run is on. Leave it first: capsules belong to your campaign."
    _capsule_notes.setdefault(capsule_id, {})["replay"] = text
    _capsule_notes[capsule_id]["diff"] = text
    return text


def capsule_replay(capsule_id):
    """A-17: the three-minute Governor-only branch. Returns the one-line outcome (and keeps it for the card)."""
    capsule = _find_capsule(capsule_id)
    if capsule is None:
        return None
    if runstate._scarcity is not None:
        return _capsule_blocked(capsule_id)
    after = branch_from_capsule(capsule, CAPSULE_BRANCH_TICKS)
    text = (f"Replay, {_mmss(CAPSULE_BRANCH_TICKS)} with nobody at the controls (the Governor and your Doctrines on every world, "
            f"your current research and perks): {_metrics_change(capsule['metrics'], after)}. Nothing in your game changed.")
    _capsule_notes.setdefault(capsule_id, {})["replay"] = text
    return text


def capsule_diff(capsule_id):
    """A-18: the one-line diff of your game now against a capsule, beside the Governor alone over the same time."""
    capsule = _find_capsule(capsule_id)
    if capsule is None:
        return None
    if runstate._scarcity is not None:
        return _capsule_blocked(capsule_id)
    elapsed = runstate.total_ticks - capsule["tick"]
    if elapsed < 0 or capsule["prestige"] != runstate.prestige_level:
        text = "This capsule is from a different run or save, so it cannot be compared with where you are now."
    elif elapsed == 0:
        text = "Nothing has changed since this capsule was frozen."
    else:
        now = _live_metrics()
        text = f"You, {_mmss(elapsed)} later: {_metrics_change(capsule['metrics'], now)}."
        if elapsed <= CAPSULE_DIFF_CAP:
            alone = branch_from_capsule(capsule, elapsed)
            text += (f" The Governor alone over the same {_mmss(elapsed)}: {_metrics_change(capsule['metrics'], alone)}. "
                     f"Gap (you minus the Governor alone): terraform {_signed(now['terraform'] - alone['terraform'], ' points')}, "
                     f"machines {_signed(now['machines'] - alone['machines'])}, banked {_signed(now['banked'] - alone['banked'])}.")
        else:
            text += f" (That is longer than {_mmss(CAPSULE_DIFF_CAP)}, so no same-length replay was run.)"
    _capsule_notes.setdefault(capsule_id, {})["diff"] = text
    return text


# persistence: this browser only, validated on read, never part of the save code
def _clean_capsule(raw):
    """A well-formed capsule, or None. Every number is checked; a world that is missing is simply a fresh one."""
    if not isinstance(raw, dict):
        return None
    cap_id, tick, prestige = raw.get("id"), raw.get("tick"), raw.get("prestige")
    for number in (cap_id, tick, prestige):
        if not isinstance(number, int) or isinstance(number, bool) or not 0 <= number < 10 ** 12:
            return None
    name = raw.get("name")
    planets_raw = raw.get("planets")
    if not isinstance(name, str) or not name.strip() or not isinstance(planets_raw, dict):
        return None
    unlocked = sorted({p for p in raw.get("unlocked", []) if p in PLANETS and p != "Earth"}) if isinstance(raw.get("unlocked"), list) else []
    planets = {}
    for planet in PLANETS:
        state = _fresh_planet_state(planet)
        saved = planets_raw.get(planet)
        if isinstance(saved, dict):
            for key in _CAPSULE_NUMBERS:
                value = saved.get(key)
                if key in state and isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value < 1e15 and value == value:
                    state[key] = type(state[key])(value) if isinstance(state[key], int) else float(value)
            routes = saved.get("trade_routes")
            if isinstance(routes, dict):
                state["trade_routes"] = {
                    dest: count for dest, count in routes.items()
                    if dest in PLANETS and isinstance(count, int) and not isinstance(count, bool) and 0 < count < 10 ** 6}
            if saved.get("trade_destination") in PLANETS:
                state["trade_destination"] = saved["trade_destination"]
            if saved.get("governor_personality") in GOVERNOR_PERSONALITIES:
                state["governor_personality"] = saved["governor_personality"]
            if saved.get("specialization") in SPECIALIZATION_LABELS:
                state["specialization"] = saved["specialization"]
        planets[planet] = state
    return {"id": cap_id, "name": " ".join(name.split())[:CAPSULE_NAME_MAX], "tick": tick, "prestige": prestige,
            "unlocked": unlocked, "planets": planets, "metrics": capsule_metrics(planets, set(unlocked))}


def _save_capsules():
    keep = [{k: c[k] for k in ("id", "name", "tick", "prestige", "unlocked", "planets")} for c in capsules]
    _write_local_storage_item(CAPSULE_STORAGE_KEY, json.dumps(keep) if keep else "")


def _load_capsules():
    """Reads the capsules this browser kept. Anything malformed is dropped; never raises."""
    capsules.clear()
    raw = _read_local_storage_item(CAPSULE_STORAGE_KEY)
    try:
        items = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        items = []
    if isinstance(items, list):
        for item in items[:CAPSULE_MAX]:
            capsule = _clean_capsule(item)
            if capsule is not None and all(capsule["id"] != c["id"] for c in capsules):
                capsules.append(capsule)
    runstate._capsule_next_id = max([c["id"] for c in capsules] + [0]) + 1


def _capsules_structure_signature():
    return (tuple((c["id"], c["name"]) for c in capsules),
            tuple((cid, tuple(sorted(notes.items()))) for cid, notes in sorted(_capsule_notes.items())))


def _build_capsules():
    panel = document.getElementById("capsules-panel")
    panel.innerHTML = ""
    panel.appendChild(_make_text("stats-panel-heading", "Time Capsules"))
    panel.appendChild(_make_text(
        "chains-intro",
        "Freeze every world as a named capsule (up to three, kept in this browser). A capsule never changes your game. "
        "Replay runs three minutes on a copy with nobody at the controls, and Compare with now sets how far you have come "
        "beside what the Governor alone would have done in the same time. Nothing here touches your achievements or your save."))
    previous = _capsule_refs.get("name")
    kept_name = previous.value if previous is not None else ""
    _capsule_refs.clear()
    field = document.createElement("input")
    field.value = kept_name  # a rebuild (after a replay, say) must not eat a half-typed name
    field.type = "text"
    field.maxLength = CAPSULE_NAME_MAX
    field.placeholder = "Name this capsule (optional)"
    field.setAttribute("aria-label", "Capsule name")
    field.className = "build-plan-input capsule-name"
    panel.appendChild(field)
    _capsule_refs["name"] = field
    freeze = _make_button("Freeze a capsule", {"data-action": "freeze"}, None)
    freeze.disabled = len(capsules) >= CAPSULE_MAX
    if freeze.disabled:
        freeze.innerText = f"Freeze a capsule (all {CAPSULE_MAX} are kept: delete one first)"
    panel.appendChild(freeze)
    if not capsules:
        panel.appendChild(_make_text("chain-card-detail", "No capsules yet."))
    for capsule in capsules:
        card = document.createElement("div")
        card.className = "chain-card"
        card.appendChild(_make_text("chain-card-name", capsule["name"]))
        metrics = capsule["metrics"]
        card.appendChild(_make_text(
            "chain-card-detail",
            f"Frozen at game time {_mmss(capsule['tick'])}, prestige {capsule['prestige']}: {metrics['worlds']} worlds, "
            f"terraform {metrics['terraform']:g}%, ecology {metrics['ecology']:g}%, {metrics['machines']} machines, {metrics['banked']:,} banked."))
        for label, action in (("Replay 3 minutes without you", "replay"), ("Compare with now", "diff"), ("Delete", "delete")):
            card.appendChild(_make_button(label, {"data-action": action, "data-capsule": str(capsule["id"])}, None))
        notes = _capsule_notes.get(capsule["id"], {})
        for key in ("replay", "diff"):
            if key in notes:
                card.appendChild(_make_text("chain-card-count", notes[key]))
        panel.appendChild(card)


def update_capsules_display():
    toggle = document.getElementById("capsules-toggle-button")
    panel = document.getElementById("capsules-panel")
    toggle.innerText = ("Hide Time Capsules" if runstate.capsules_open else "⏳ Time Capsules") + f" ({len(capsules)}/{CAPSULE_MAX})"
    panel.hidden = not runstate.capsules_open
    if not runstate.capsules_open:
        runstate._capsules_signature = None
        return
    signature = _capsules_structure_signature()
    if signature != runstate._capsules_signature:
        _build_capsules()
        runstate._capsules_signature = signature
