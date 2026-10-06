"""Lexis -- the engine's single entry point (the Signal pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that
comes back. `get_state()` / `load_state()` are the shared save widget's contract
(planning/SAVE-BUTTON-INTEGRATION.md). Everything is deterministic: there is no random state.

Planets (one language each; the ladder in planning/lexis-plan.md section 6b):
  pulse     planet 1, the quiet beacon: marks "0"/"1", a station of lamps and a door
  compound  planet 2: signs built from components, a tray of things; unlocks after contact with planet 1

Every request carries `"planet"` (default "pulse"). Actions:
  open                       the current view of that planet
  next_scene                 reveal the next scene of that planet's curriculum (no-op at the end)
  write {form, gloss}        write or clear a notebook entry (never judged). form = a token (pulse) or a letter (compound)
  confirm {forms}            how many of the chosen entries are right, not which
  speak {marks} | {glyph}    send a signal; the world answers in-world
  reset                      start over (everything)
"""

import json

import compound
import achievements
import deduce
import deduce_compound
from compound import COMPONENTS, Tray, describe_tray
from compound_scenes import compound_scenes
from glyphs import COMPONENT_PATHS
from notebook import LexisState
from pulse import PULSE
from scenes import pulse_scenes
from world import Station, describe, react

SCENES = pulse_scenes()
CSCENES = compound_scenes()
LANGUAGE = PULSE
PLANETS = ("pulse", "compound")

state = LexisState()
station = Station(0, "shut")
tray = Tray()

# Whether the first k scenes settle each language never changes, and checking enumerates thousands of
# readings, so each answer is computed once per k (the view asks on every request).
_settled_cache = {}


def _settled(planet, k):
    key = (planet, k)
    if key not in _settled_cache:
        scenes = (CSCENES if planet == "compound" else SCENES)[:k]
        check = deduce_compound.determinate if planet == "compound" else deduce.determinate
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


def unlocked(planet):
    return planet == "pulse" or state.contact["pulse"]


def _planets_view():
    return {
        "pulse": {"name": "Planet 1: the quiet beacon", "unlocked": True, "contact": state.contact["pulse"]},
        "compound": {"name": "Planet 2: the market world", "unlocked": unlocked("compound"),
                     "contact": state.contact["compound"]},
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


def _view(planet):
    return _compound_view() if planet == "compound" else _pulse_view()


def _compound_truth(letter):
    entry = COMPONENTS.get(letter)
    return entry[0] if entry else None


# --- the one entry point --------------------------------------------------------------------------
def handle(request_json):
    global station, tray
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

    if action == "next_scene":
        if compound_planet:
            state.compound_scenes_seen = min(state.compound_scenes_seen + 1, len(CSCENES))
        else:
            state.see_next_scene(len(SCENES))
    elif action == "write":
        form, gloss = str(request.get("form", "")), request.get("gloss", "")
        if compound_planet:
            if form in COMPONENTS:
                state.compound_notebook.write(form, gloss)
        elif form and set(form) <= set("01") and len(form) == LANGUAGE.token_len:
            state.notebook.write(form, gloss)
    elif action == "confirm":
        forms = [str(f) for f in request.get("forms", [])]
        if compound_planet:
            right = state.compound_notebook.confirm(forms, truth=_compound_truth)
        else:
            right = state.notebook.confirm(forms, LANGUAGE)
        if len(forms) >= 3 and right == len(forms):
            state.flags["perfect_check"] = True
        return json.dumps({"right": right, "chosen": len(forms)})
    elif action == "speak":
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
            view = _compound_view()
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
            view = _pulse_view()
        view["reaction"] = {"understood": reaction.understood, "text": reaction.text, "reason": reaction.reason}
        return json.dumps(view)
    elif action == "reset":
        state.__init__()
        station = Station(0, "shut")
        tray = Tray()
    elif action != "open":
        return json.dumps({"error": f"unknown action {action!r}"})
    return json.dumps(_view(planet))


def get_state():
    data = state.to_dict()
    data["station"] = station.to_dict()
    data["tray"] = [i.label() for i in tray.items]
    # A write-only projection for the hub's achievements dashboard, recomputed here, never read back.
    data["achievements_earned"] = achievements.earned(state, station, tray)
    return data


def load_state(data):
    """Merge a saved state in: notebooks are unioned (a saved guess never deletes a newer one), scenes seen
    takes the larger count, contact is kept once earned, and the station and tray are restored."""
    global station, tray
    incoming = LexisState.from_dict(data)
    for form, gloss in incoming.notebook.entries.items():
        state.notebook.entries.setdefault(form, gloss)
    for letter, gloss in incoming.compound_notebook.entries.items():
        state.compound_notebook.entries.setdefault(letter, gloss)
    state.scenes_seen = min(max(state.scenes_seen, incoming.scenes_seen), len(SCENES))
    state.compound_scenes_seen = min(max(state.compound_scenes_seen, incoming.compound_scenes_seen), len(CSCENES))
    state.spoken = (incoming.spoken + [s for s in state.spoken if s not in incoming.spoken])[-200:]
    state.compound_spoken = (incoming.compound_spoken
                             + [s for s in state.compound_spoken if s not in incoming.compound_spoken])[-200:]
    for planet in PLANETS:
        state.contact[planet] = state.contact[planet] or incoming.contact[planet]
    state.flags.update(incoming.flags)
    try:
        station = Station.from_dict((data or {}).get("station"))
    except (KeyError, TypeError, ValueError):
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
