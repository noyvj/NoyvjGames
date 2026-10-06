"""Lexis -- the engine's single entry point (the Signal pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that
comes back. `get_state()` / `load_state()` are the shared save widget's contract
(planning/SAVE-BUTTON-INTEGRATION.md). Everything is deterministic: there is no random state.

Planets (one language each; the ladder in planning/lexis-plan.md section 6b):
  pulse     planet 1, the quiet beacon: marks "0"/"1", a station of lamps and a door
  compound  planet 2: signs built from components, a tray of things; unlocks after contact with planet 1
  bridge    planet 3: nouns from planet 2, numbers from planet 1, and three marker letters (plural, negate,
            ask) after a noun; a counter of things with counts; unlocks after contact with planet 2

Every request carries `"planet"` (default "pulse"). Actions:
  open                       the current view of that planet
  next_scene                 reveal the next scene of that planet's curriculum (no-op at the end)
  write {form, gloss}        write or clear a notebook entry (never judged). form = a token (pulse) or a letter
                             (compound: a component; bridge: a marker p, n or q)
  confirm {forms}            how many of the chosen entries are right, not which
  speak {marks} | {glyph} | {message}   send a signal; the world answers in-world (the bridge language
                             sends a whole message: space-separated tokens such as "ku p 0011")
  reset                      start over (everything)
"""

import json

import bridge
import compound
import achievements
import deduce
import deduce_bridge
import deduce_compound
import info
import report
import story
from bridge import MARKERS, Stock, describe_stock
from bridge_scenes import bridge_scenes
from compound import COMPONENTS, Tray, all_valid_glyphs, describe_tray
from compound_scenes import compound_scenes
from glyphs import COMPONENT_PATHS, all_paths
from notebook import LexisState, is_message
from pulse import MAX_NUMBER, PULSE, spell_number
from scenes import pulse_scenes
from world import Station, describe, react

SCENES = pulse_scenes()
CSCENES = compound_scenes()
BSCENES = bridge_scenes()
LANGUAGE = PULSE
PLANETS = ("pulse", "compound", "bridge")

state = LexisState()
station = Station(0, "shut")
tray = Tray()
stock = Stock()

# Whether the first k scenes settle each language never changes, and checking enumerates thousands of
# readings, so each answer is computed once per k (the view asks on every request).
_settled_cache = {}


def _settled(planet, k):
    key = (planet, k)
    if key not in _settled_cache:
        scenes = {"compound": CSCENES, "bridge": BSCENES}.get(planet, SCENES)[:k]
        check = {"compound": deduce_compound.determinate, "bridge": deduce_bridge.determinate}.get(planet, deduce.determinate)
        _settled_cache[key] = bool(scenes) and check(scenes)
    return _settled_cache[key]


# --- contact: what the crew needs from each planet before the ship moves on -----------------------
def pulse_goal_met(st):
    """First contact with planet 1: the beacon's door open and exactly five lamps lit."""
    return st.door == "open" and st.lamps == 5


def compound_goal_met(t):
    """Planet 2 asks for two things the player has never been shown: a big water and a big fire."""
    labels = {item.label() for item in t.items}
    return {"big water", "big fire"} <= labels


def bridge_goal_met(st, flags):
    """Planet 3 asks for exactly five big fire on the counter AND that the player has used the ask sign."""
    return st.count("big fire") == 5 and bool(flags.get("asked"))


def unlocked(planet):
    if planet == "bridge":
        return state.contact["compound"]
    return planet == "pulse" or state.contact["pulse"]


def _planets_view():
    return {
        "pulse": {"name": "Planet 1: the quiet beacon", "unlocked": True, "contact": state.contact["pulse"]},
        "compound": {"name": "Planet 2: the market world", "unlocked": unlocked("compound"),
                     "contact": state.contact["compound"]},
        "bridge": {"name": "Planet 3: the counting station", "unlocked": unlocked("bridge"),
                   "contact": state.contact["bridge"]},
    }


# --- views ----------------------------------------------------------------------------------------
def _pulse_view():
    seen = SCENES[:state.scenes_seen]
    return {
        "planet": "pulse",
        "planets": _planets_view(),
        "language": {"id": LANGUAGE.id, "name": LANGUAGE.name, "token_len": LANGUAGE.token_len},
        "scenes": [scene.to_dict() for scene in seen],
        "scenes_total": len(SCENES),
        "notebook": dict(state.notebook.entries),
        "station": station.to_dict(),
        "station_text": describe(station),
        # Whether the evidence shown so far fully settles the language. The view may use this to
        # encourage trying a sentence; it never says which guesses are right.
        "settled": _settled("pulse", len(seen)),
        "spoken": list(state.spoken[-20:]),
        "goal": "Open the door and light exactly five lamps.",
        "achievements": achievements.view(state, station, tray),
    }


def _letters_seen():
    seen = []
    for scene in CSCENES[:state.compound_scenes_seen]:
        for letter in scene.glyph:
            if letter not in seen:
                seen.append(letter)
    return seen


def _compound_view():
    seen = CSCENES[:state.compound_scenes_seen]
    return {
        "planet": "compound",
        "planets": _planets_view(),
        "components": dict(COMPONENT_PATHS),
        "letters": _letters_seen(),
        "scenes": [scene.to_dict() for scene in seen],
        "scenes_total": len(CSCENES),
        "notebook": dict(state.compound_notebook.entries),
        "tray": [item.label() for item in tray.items],
        "tray_text": describe_tray(tray),
        "settled": _settled("compound", len(seen)),
        "spoken": list(state.compound_spoken[-20:]),
        "goal": "Ask for a big water and a big fire, two things nobody has shown you.",
        "achievements": achievements.view(state, station, tray),
    }


def _bridge_nouns_and_markers():
    """What the player may build with. Planet 3 only opens after contact with planet 2, so every noun that
    planet's parts can spell is theirs to use (the goal asks for one no transmission here shows); the
    markers are only the ones transmissions have shown, in first-seen order."""
    scenes = BSCENES[:state.bridge_scenes_seen]
    markers = []
    for scene in scenes:
        for token in scene.message.split()[1:]:
            if token in MARKERS and token not in markers:
                markers.append(token)
    return all_valid_glyphs(), markers


def _bridge_view():
    seen = BSCENES[:state.bridge_scenes_seen]
    nouns, markers = _bridge_nouns_and_markers()
    return {
        "planet": "bridge",
        "planets": _planets_view(),
        "components": all_paths(),
        "nouns": nouns,
        "markers": markers,
        "numbers": [spell_number(n) for n in range(MAX_NUMBER + 1)],
        "scenes": [scene.to_dict() for scene in seen],
        "scenes_total": len(BSCENES),
        "notebook": dict(state.bridge_notebook.entries),
        "stock": stock.to_dict()["items"],
        "stock_text": describe_stock(stock),
        "settled": _settled("bridge", len(seen)),
        "spoken": list(state.bridge_spoken[-20:]),
        "goal": "Leave exactly five big fire on the counter, and ask the station how many there are.",
        "achievements": achievements.view(state, station, tray),
    }


def _extras():
    """Story, info and the contact report ride on every view. All three are derived from the contact flags
    and the state, never stored."""
    return {
        "story": story.view(state.contact),
        "info": info.view(state.contact),
        "report": report.build(state, achievements.view(state, station, tray),
                               {"pulse": len(SCENES), "compound": len(CSCENES), "bridge": len(BSCENES)}),
    }


def _view(planet):
    if planet == "bridge":
        view = _bridge_view()
    else:
        view = _compound_view() if planet == "compound" else _pulse_view()
    view.update(_extras())
    return view


def _compound_truth(letter):
    entry = COMPONENTS.get(letter)
    return entry[0] if entry else None


def _bridge_truth(letter):
    return MARKERS.get(letter)


# --- the one entry point --------------------------------------------------------------------------
def handle(request_json):
    global station, tray, stock
    try:
        request = json.loads(request_json)
        action = request.get("action")
        planet = request.get("planet", "pulse")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    if planet not in PLANETS:
        return json.dumps({"error": f"unknown planet {planet!r}"})
    if not unlocked(planet):
        return json.dumps({"error": "that planet is not in range yet"})
    compound_planet = planet == "compound"
    bridge_planet = planet == "bridge"

    if action == "next_scene":
        if bridge_planet:
            state.bridge_scenes_seen = min(state.bridge_scenes_seen + 1, len(BSCENES))
        elif compound_planet:
            state.compound_scenes_seen = min(state.compound_scenes_seen + 1, len(CSCENES))
        else:
            state.see_next_scene(len(SCENES))
    elif action == "write":
        form, gloss = str(request.get("form", "")), request.get("gloss", "")
        if bridge_planet:
            if form in MARKERS:
                state.bridge_notebook.write(form, gloss)
        elif compound_planet:
            if form in COMPONENTS:
                state.compound_notebook.write(form, gloss)
        elif form and set(form) <= set("01") and len(form) == LANGUAGE.token_len:
            state.notebook.write(form, gloss)
    elif action == "confirm":
        forms = [str(f) for f in request.get("forms", [])]
        if bridge_planet:
            right = state.bridge_notebook.confirm(forms, truth=_bridge_truth)
        elif compound_planet:
            right = state.compound_notebook.confirm(forms, truth=_compound_truth)
        else:
            right = state.notebook.confirm(forms, LANGUAGE)
        if len(forms) >= 3 and right == len(forms):
            state.flags["perfect_check"] = True
        return json.dumps({"right": right, "chosen": len(forms)})
    elif action == "speak":
        if bridge_planet:
            message = " ".join(str(request.get("message", "")).split())
            reaction = bridge.react(message, stock)
            stock = reaction.stock
            if is_message(message):
                state.bridge_spoken.append(message)
                del state.bridge_spoken[:-200]
            if reaction.reply:
                state.flags["asked"] = True
            if bridge_goal_met(stock, state.flags):
                state.contact["bridge"] = True
            if reaction.understood:
                state.flags["understood"] = True
            else:
                state.flags["misunderstood"] = True
            view = _view("bridge")
            view["reaction"] = {"understood": reaction.understood, "text": reaction.text, "reason": reaction.reason,
                                "reply": reaction.reply}
            return json.dumps(view)
        if compound_planet:
            glyph = str(request.get("glyph", ""))
            reaction = compound.react(glyph, tray)
            tray = reaction.tray
            if glyph and glyph.isalpha():
                state.compound_spoken.append(glyph)
                del state.compound_spoken[:-200]
            if compound_goal_met(tray):
                state.contact["compound"] = True
            if reaction.understood:
                state.flags["understood"] = True
                if glyph in {"ku", "tu"}:
                    state.flags["understood_unseen"] = True
            else:
                state.flags["misunderstood"] = True
            view = _view("compound")
        else:
            marks = str(request.get("marks", ""))
            reaction = react(marks, station, LANGUAGE)
            station = reaction.station
            if marks and set(marks) <= set("01"):
                state.spoken.append(marks)
                del state.spoken[:-200]
            if pulse_goal_met(station):
                state.contact["pulse"] = True
            if reaction.understood:
                state.flags["understood"] = True
                if station.lamps == 7:
                    state.flags["all_lamps"] = True
            else:
                state.flags["misunderstood"] = True
            view = _view("pulse")
        view["reaction"] = {"understood": reaction.understood, "text": reaction.text, "reason": reaction.reason}
        return json.dumps(view)
    elif action == "reset":
        state.__init__()
        station = Station(0, "shut")
        tray = Tray()
        stock = Stock()
    elif action != "open":
        return json.dumps({"error": f"unknown action {action!r}"})
    return json.dumps(_view(planet))


def get_state():
    data = state.to_dict()
    data["station"] = station.to_dict()
    data["tray"] = [i.label() for i in tray.items]
    data["stock"] = [[label, count] for label, count in stock.items]
    # A write-only projection for the hub's achievements dashboard, recomputed here, never read back.
    data["achievements_earned"] = achievements.earned(state, station, tray)
    return data


def load_state(data):
    """Merge a saved state in: notebooks are unioned (a saved guess never deletes a newer one), scenes seen
    takes the larger count, contact is kept once earned, and the station and tray are restored."""
    global station, tray, stock
    try:
        incoming = LexisState.from_dict(data)
    except (ValueError, TypeError, AttributeError, OverflowError):
        incoming = LexisState()
    for form, gloss in incoming.notebook.entries.items():
        state.notebook.entries.setdefault(form, gloss)
    for letter, gloss in incoming.compound_notebook.entries.items():
        state.compound_notebook.entries.setdefault(letter, gloss)
    state.scenes_seen = min(max(state.scenes_seen, incoming.scenes_seen), len(SCENES))
    state.compound_scenes_seen = min(max(state.compound_scenes_seen, incoming.compound_scenes_seen), len(CSCENES))
    for letter, gloss in incoming.bridge_notebook.entries.items():
        state.bridge_notebook.entries.setdefault(letter, gloss)
    state.bridge_scenes_seen = min(max(state.bridge_scenes_seen, incoming.bridge_scenes_seen), len(BSCENES))
    state.bridge_spoken = (incoming.bridge_spoken
                           + [s for s in state.bridge_spoken if s not in incoming.bridge_spoken])[-200:]
    state.spoken = (incoming.spoken + [s for s in state.spoken if s not in incoming.spoken])[-200:]
    state.compound_spoken = (incoming.compound_spoken
                             + [s for s in state.compound_spoken if s not in incoming.compound_spoken])[-200:]
    for planet in PLANETS:
        state.contact[planet] = state.contact[planet] or incoming.contact[planet]
    state.flags.update(incoming.flags)
    try:
        station = Station.from_dict((data or {}).get("station"))
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    try:
        labels = [str(x) for x in ((data or {}).get("tray") or [])][-compound.MAX_TRAY:]
        items = []
        for label in labels:
            size, root = label.split(" ", 1)
            if root in {m for m, slot in COMPONENTS.values() if slot == "root"} and size in ("small", "big"):
                items.append(compound.Item(root, size))
        tray = Tray(tuple(items))
    except (ValueError, TypeError, AttributeError):
        pass
    try:
        sizes, roots = {"small", "big"}, {m for m, slot in COMPONENTS.values() if slot == "root"}
        rebuilt = Stock()
        for entry in ((data or {}).get("stock") or [])[:12]:
            try:
                label, count = entry
                size, root = str(label).split(" ", 1)
            except (ValueError, TypeError):
                continue                                  # one bad entry never costs the good ones
            if size in sizes and root in roots and isinstance(count, int) and not isinstance(count, bool):
                rebuilt = rebuilt.with_count(f"{size} {root}", count)
        stock = rebuilt
    except (TypeError, AttributeError):
        pass
    _refresh_view()


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly and knows
    nothing about this game's view). Under plain CPython there is no page, so this is a no-op."""
    try:
        import js
        refresh = getattr(js.window, "lexisRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
