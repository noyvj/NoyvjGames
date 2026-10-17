"""Autosaves and the custom-rules workshop."""

import json

from js import document

import tide_runstate as runstate
from tide_bridge import _read_local_storage_item
from tide_rules import FISH_LAG_SEASONS, WORKSHOP_DEFAULTS, WORKSHOP_RANGES


# D-11 autosave history ---------------------------------------------------------------------------------------------
AUTOSAVE_KEY = "tide_autosaves_v1"
AUTOSAVE_SLOTS = 3
AUTOSAVE_MAX_BYTES = 300000  # a slot bigger than this is skipped rather than risk filling the browser's storage
_autosave_info = {"load_failed": False}


def load_autosaves():
    """The stored slots, newest last: [{"season", "funds", "state"}], with anything malformed dropped."""
    raw = _read_local_storage_item(AUTOSAVE_KEY)
    try:
        data = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        return []
    out = []
    for item in data if isinstance(data, list) else []:
        if (isinstance(item, dict) and isinstance(item.get("state"), dict)
                and isinstance(item.get("season"), int) and not isinstance(item.get("season"), bool)
                and isinstance(item.get("funds"), (int, float)) and not isinstance(item.get("funds"), bool)):
            out.append({"season": item["season"], "funds": float(item["funds"]), "state": item["state"]})
    return out[-AUTOSAVE_SLOTS:]


def render_autosaves():
    panel, box = document.getElementById("autosave-panel"), document.getElementById("autosave-list")
    slots = load_autosaves()
    if panel is not None and _autosave_info["load_failed"]:
        panel.open = True
    note = document.getElementById("autosave-note")
    if note is not None:
        note.innerText = ("The last load could not be read. Pick an earlier autosave below." if _autosave_info["load_failed"]
                          else f"The last {AUTOSAVE_SLOTS} seasons are kept automatically in this browser.")
    if box is None:
        return
    box.innerHTML = ""
    if not slots:
        box.innerText = "No autosaves yet: they start once a season has been played."
        return
    for i, slot in enumerate(reversed(slots)):
        index = len(slots) - 1 - i
        button = document.createElement("button")
        button.type = "button"
        button.className = "secondary autosave-button"
        button.setAttribute("data-slot", str(index))
        button.innerText = f"Restore Season {slot['season']} (funds {slot['funds']:.0f})"
        box.appendChild(button)


# D-5 Tide Workshop ---------------------------------------------------------------------------------------------
workshop_pending = dict(WORKSHOP_DEFAULTS)


def clean_workshop_value(key, value):
    """A value snapped onto the dial's steps and range; anything unusable becomes the default."""
    low, high, step = WORKSHOP_RANGES[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return WORKSHOP_DEFAULTS[key]
    snapped = round(float(value) / step) * step
    snapped = min(high, max(low, snapped))
    return int(round(snapped)) if key in ("funds", "lag") else round(snapped, 2)


def workshop_rating(values):
    """(score, label): 1.0 is the standard game, higher is harder. A readout only."""
    funds_factor = (WORKSHOP_DEFAULTS["funds"] / max(1, values["funds"])) ** 0.5
    lag = values["lag"] or FISH_LAG_SEASONS
    lag_factor = 1.0 + 0.08 * (lag - FISH_LAG_SEASONS)  # a longer lag hides the cause for longer, so it is harder
    score = (0.30 * values["rise"] + 0.15 * values["surge"] + 0.25 * values["fish"] + 0.15 * lag_factor + 0.15 * funds_factor)
    label = "Gentle" if score < 0.85 else "Standard" if score < 1.15 else "Hard" if score < 1.5 else "Brutal"
    return score, label


def workshop_text():
    score, label = workshop_rating(workshop_pending)
    custom = any(workshop_pending[k] != WORKSHOP_DEFAULTS[k] for k in WORKSHOP_DEFAULTS)
    live = "Live run: custom rules (kept out of the Almanac, best and library)." if runstate.state.workshop_active() else "Live run: standard rules."
    return f"Difficulty rating {score:.2f} ({label}){' - custom rules' if custom else ''}. {live} Apply starts a new run."


def render_workshop():
    for key in WORKSHOP_DEFAULTS:
        slider, readout = document.getElementById(f"workshop-{key}"), document.getElementById(f"workshop-{key}-value")
        if slider is not None:
            low, high, step = WORKSHOP_RANGES[key]
            slider.min, slider.max, slider.step = str(low), str(high), str(step)
            slider.value = f"{workshop_pending[key]:g}"
        if readout is not None:
            readout.innerText = f"{workshop_pending[key]:g}"
    text = document.getElementById("workshop-status")
    if text is not None:
        text.innerText = workshop_text()
    badge = document.getElementById("custom-rules-badge")
    if badge is not None:
        badge.hidden = not runstate.state.workshop_active()
        badge.innerText = "Custom rules" if runstate.state.workshop_active() else ""
