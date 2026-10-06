"""Lexis -- the engine's single entry point (the Signal pattern).

The view (app.js, milestone 2) never reads engine objects: it sends one JSON string to `handle` and draws
the JSON that comes back. `get_state()` / `load_state()` are the shared save widget's contract
(planning/SAVE-BUTTON-INTEGRATION.md). Everything is deterministic: there is no random state.

Actions (all take and return plain JSON):
  open                       the current view: scenes seen so far, notebook, station, what is proven
  next_scene                 reveal the next scene of the curriculum (no-op at the end)
  write {form, gloss}        write or clear a notebook entry (never judged)
  confirm {forms}            how many of the chosen entries are right, not which
  speak {marks}              send a signal to the station; the world answers in-world
  reset                      start over
"""

import json

from deduce import determinate
from notebook import LexisState
from pulse import PULSE
from scenes import pulse_scenes
from world import Station, describe, react

SCENES = pulse_scenes()
LANGUAGE = PULSE

state = LexisState()
station = Station(0, "shut")


def _view():
    seen = SCENES[:state.scenes_seen]
    return {
        "language": {"id": LANGUAGE.id, "name": LANGUAGE.name, "token_len": LANGUAGE.token_len},
        "scenes": [scene.to_dict() for scene in seen],
        "scenes_total": len(SCENES),
        "notebook": dict(state.notebook.entries),
        "station": station.to_dict(),
        "station_text": describe(station),
        # Whether the evidence shown so far fully settles the language. The view may use this to
        # encourage trying a sentence; it never says which guesses are right.
        "settled": determinate(seen) if seen else False,
        "spoken": list(state.spoken[-20:]),
    }


def handle(request_json):
    global station
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})

    if action == "next_scene":
        state.see_next_scene(len(SCENES))
    elif action == "write":
        form, gloss = str(request.get("form", "")), request.get("gloss", "")
        if form and set(form) <= set("01") and len(form) == LANGUAGE.token_len:
            state.notebook.write(form, gloss)
    elif action == "confirm":
        forms = [str(f) for f in request.get("forms", [])]
        return json.dumps({"right": state.notebook.confirm(forms, LANGUAGE), "chosen": len(forms)})
    elif action == "speak":
        marks = str(request.get("marks", ""))
        reaction = react(marks, station, LANGUAGE)
        station = reaction.station
        if set(marks) <= set("01") and marks:
            state.spoken.append(marks)
            del state.spoken[:-200]
        view = _view()
        view["reaction"] = {"understood": reaction.understood, "text": reaction.text, "reason": reaction.reason}
        return json.dumps(view)
    elif action == "reset":
        state.__init__()
        station = Station(0, "shut")
    elif action != "open":
        return json.dumps({"error": f"unknown action {action!r}"})
    return json.dumps(_view())


def get_state():
    data = state.to_dict()
    data["station"] = station.to_dict()
    return data


def load_state(data):
    """Merge a saved state in: the notebook is unioned (a saved guess never deletes a newer one), scenes seen
    takes the larger count, and the station is restored."""
    global station
    incoming = LexisState.from_dict(data)
    for form, gloss in incoming.notebook.entries.items():
        state.notebook.entries.setdefault(form, gloss)
    state.scenes_seen = min(max(state.scenes_seen, incoming.scenes_seen), len(SCENES))
    state.spoken = (incoming.spoken + [s for s in state.spoken if s not in incoming.spoken])[-200:]
    try:
        station = Station.from_dict((data or {}).get("station"))
    except (KeyError, TypeError, ValueError):
        pass
