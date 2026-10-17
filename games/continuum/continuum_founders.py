"""The Founder's Log (notes, play time), the settlement name input, and the Minutes panel."""

import time

from js import document

import minutes
import naming
import sim

import continuum_runstate as runstate
from continuum_base import year_and_season

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# --- K15 founder's log + K29 time played --------------------------------
# Both ride in campaign.ui (already saved as a plain dict) and are
# validated/defaulted on every read, so an old or hand-edited save can
# never break the panel: bad shapes read as empty / zero.
FOUNDERS_NOTE_MAX = 200
FOUNDERS_LOG_MAX = 60
PLAY_GAP_CAP_SECONDS = 300.0


def founders_entries():
    raw = runstate.campaign.ui.get("founders_log")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[-FOUNDERS_LOG_MAX:]:
        if not isinstance(item, dict):
            continue
        note = item.get("note")
        era = item.get("era")
        season = item.get("season")
        if not isinstance(note, str) or not note.strip():
            continue
        if era not in sim.ERA_LABEL or isinstance(season, bool) or not isinstance(season, int) or season < 1:
            continue
        out.append({"era": era, "season": season, "note": note[:FOUNDERS_NOTE_MAX]})
    return out


def add_founders_note(text):
    """Append a personal annotation stamped with the current era/season."""
    if not isinstance(text, str) or not text.strip():
        return False
    entries = founders_entries()
    entries.append({"era": runstate.state.era, "season": int(runstate.state.season), "note": text.strip()[:FOUNDERS_NOTE_MAX]})
    runstate.campaign.ui["founders_log"] = entries[-FOUNDERS_LOG_MAX:]
    return True


def play_seconds():
    value = runstate.campaign.ui.get("play_seconds")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or value < 0:
        return 0.0
    return min(float(value), 1e9)


def _tick_play_time():
    """Accumulate active time between actions; long idle gaps are capped."""
    now = time.time()
    runstate.campaign.ui["play_seconds"] = play_seconds() + max(0.0, min(now - runstate._last_tick, PLAY_GAP_CAP_SECONDS))
    runstate._last_tick = now


def format_play_time(seconds):
    mins = int(seconds // 60)
    if mins < 60:
        return f"{mins} min"
    return f"{mins // 60} h {mins % 60} min"


def update_founders_panel():
    toggle = document.getElementById("founders-toggle-button")
    panel = document.getElementById("founders-panel")
    toggle.innerText = "Hide Founder's Log" if runstate.founders_log_open else "📓 Founder's Log"
    panel.hidden = not runstate.founders_log_open
    if not runstate.founders_log_open:
        return
    container = document.getElementById("founders-list")
    container.innerHTML = ""
    entries = founders_entries()
    if not entries:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = "No entries yet. Note what you decided and why, as the founder."
        container.appendChild(empty)
    for entry in reversed(entries):
        year, season_name = year_and_season(entry["season"])
        row = document.createElement("p")
        row.className = "status-line founders-entry"
        row.innerText = f"Year {year}, {season_name} ({sim.ERA_LABEL[entry['era']]}): {entry['note']}"
        container.appendChild(row)


def on_toggle_founders(event=None):
    runstate.founders_log_open = not runstate.founders_log_open
    if runstate.founders_log_open:
        sync_name_input()
    update_founders_panel()


def on_add_founders_note(event=None):
    field = document.getElementById("founders-input")
    if add_founders_note(field.value):
        field.value = ""
        update_founders_panel()


# --- K-24: naming the settlement --------------------------------------------


def settlement_name():
    return naming.get(runstate.campaign.ui)


def sync_name_input():
    document.getElementById("settlement-name-input").value = settlement_name()


def _name_status(text):
    document.getElementById("settlement-name-status").innerText = text


def on_name_suggest(event=None):
    runstate._name_roll += 1
    suggestion = naming.suggest(runstate.state.era, runstate._name_roll)
    document.getElementById("settlement-name-input").value = suggestion
    _name_status(f"Suggested: {suggestion}. Press Save name to keep it, or suggest another.")


def on_name_save(event=None):
    field = document.getElementById("settlement-name-input")
    stored = naming.set_name(runstate.campaign.ui, field.value)
    field.value = stored
    _name_status(f"Your settlement is named {stored}." if stored else "No name set. The settlement is unnamed.")
    render()


def on_name_keydown(event=None):
    if getattr(event, "key", None) == "Enter":
        on_name_save()


# --- K5 council minutes -------------------------------------------------


def record_motion(kind, subject):
    minutes.record(runstate.campaign.ui, kind, subject, runstate.state.era, int(runstate.state.season))


def update_minutes_panel():
    toggle = document.getElementById("minutes-toggle-button")
    panel = document.getElementById("minutes-panel")
    toggle.innerText = "Hide Council Minutes" if runstate.minutes_open else "🏛️ Council Minutes"
    panel.hidden = not runstate.minutes_open
    if not runstate.minutes_open:
        return
    container = document.getElementById("minutes-list")
    container.innerHTML = ""
    entries = minutes.entries(runstate.campaign.ui)
    if not entries:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = "No motions recorded yet. Research a discovery or raise a building and it will be minuted here."
        container.appendChild(empty)
    for entry in reversed(entries):
        year, season_name = year_and_season(entry["season"])
        row = document.createElement("p")
        row.className = "status-line minutes-entry"
        row.innerText = f"Year {year}, {season_name} ({sim.ERA_LABEL[entry['era']]}): {entry['text']}"
        container.appendChild(row)


def on_toggle_minutes(event=None):
    runstate.minutes_open = not runstate.minutes_open
    update_minutes_panel()
