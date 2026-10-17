"""Local run slots (C-13): saving, switching, starting and clearing slots in this browser.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import json

from js import document

import grid_runstate as runstate
from grid_rules import SCENARIOS
from grid_career_data import _career_storage
from grid_savegame import get_state


# ---- C-13 local run slots ------------------------------------------------------------------------------------------
# Three named slots in this browser (no sign-in), each holding one whole run exactly as get_state() writes it (the same
# serialisation the save widget uses), so a slot keeps its own scenario, seed and career snapshot. Safety rules, so that
# nothing is lost by accident: a slot only autosaves (after each Advance Round) once the run is ATTACHED to it, which
# happens only when the player saves, loads or starts a run in it, never on page load; switching saves the current run
# into its slot first; and every action that would replace a run that is not in a slot, or overwrite or clear a slot,
# asks first (never skippable). Slots live in localStorage under their own key and are not part of a save.
SLOTS_STORAGE_KEY = "grid_slots_v1"
SLOT_COUNT = 3
SLOT_NAME_MAX = 24
SLOT_MAX_BYTES = 600_000


def _clean_slot_name(raw, index):
    name = " ".join(str(raw or "").split())[:SLOT_NAME_MAX]
    return name or f"Slot {index + 1}"


def _validate_slot(raw, index):
    """A stored slot or None: the name is cleaned, the run must be a dict with a sensible round number."""
    if not isinstance(raw, dict) or not isinstance(raw.get("state"), dict):
        return None
    data = raw["state"]
    round_number = data.get("round_number")
    if isinstance(round_number, bool) or not isinstance(round_number, int) or round_number < 1:
        return None
    # The numbers every screen does arithmetic on must be numbers (a hand-edited slot is treated as damaged).
    for key in ("funds", "demand", "emissions"):
        value = data.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value != value):
            return None
    counts = data.get("plant_counts")
    if counts is not None:
        if not isinstance(counts, dict):
            return None
        for count in counts.values():
            if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > 100_000:
                return None
    return {"name": _clean_slot_name(raw.get("name"), index), "state": data}


def load_slots():
    """The three slots (None for an empty or damaged one). Never raises."""
    slots = [None] * SLOT_COUNT
    storage = _career_storage()
    if storage is None:
        return slots
    try:
        raw = storage.getItem(SLOTS_STORAGE_KEY)
        parsed = json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001 -- private mode / corrupt JSON: no slots
        return slots
    if isinstance(parsed, dict) and isinstance(parsed.get("slots"), list):
        for index, entry in enumerate(parsed["slots"][:SLOT_COUNT]):
            slots[index] = _validate_slot(entry, index)
    return slots


def _write_slots(slots):
    storage = _career_storage()
    if storage is None:
        return False
    try:
        storage.setItem(SLOTS_STORAGE_KEY, json.dumps({"v": 1, "slots": slots}))
        return True
    except Exception:  # noqa: BLE001 -- a refused write (storage full) must never break play
        return False


def slot_summary(slot, index):
    if slot is None:
        return f"Slot {index + 1}: empty"
    data = slot["state"]
    scenario = SCENARIOS.get(data.get("scenario"), SCENARIOS["standard"])["label"]
    return f"Slot {index + 1}: {slot['name']} (round {data['round_number']}, {scenario})"


def _store_run_in_slot(index, name=None):
    """Writes the live run into a slot; returns an error sentence or ''."""
    slots = load_slots()
    snapshot = json.loads(json.dumps(get_state()))
    if len(json.dumps(snapshot)) > SLOT_MAX_BYTES:
        return "This run is too large to keep in a slot."
    previous = slots[index]["name"] if slots[index] else None
    slots[index] = {"name": _clean_slot_name(name or previous, index), "state": snapshot}
    if not _write_slots(slots):
        return "This browser would not store the slot (storage may be full or switched off)."
    return ""


def autosave_slot():
    """After a round: keeps the attached slot current. Silent, and a no-op when nothing is attached."""
    if runstate.slot_attached is None or runstate.sandbox_active:
        return
    _store_run_in_slot(runstate.slot_attached)


def _selected_slot():
    raw = getattr(document.getElementById("slot-select"), "value", "0")
    try:
        index = int(raw)
    except (TypeError, ValueError):
        return 0
    return index if 0 <= index < SLOT_COUNT else 0


def _attach(index):
    runstate.slot_attached = index
    document.getElementById("slot-name-input").value = ""  # the typed name has been used


def _load_slot_name(index):
    slot = load_slots()[index]
    return slot["name"] if slot else f"Slot {index + 1}"


def slot_status_text():
    if runstate.slot_attached is None:
        head = "No slot holds this run yet. Save it to a slot to keep it (nothing is saved to a slot by itself)."
    else:
        head = f"This run is in slot {runstate.slot_attached + 1} and saves itself after every round."
    return head + (" " + runstate.slot_message if runstate.slot_message else "")


def render_slots():
    select = document.getElementById("slot-select")
    slots = load_slots()
    chosen = _selected_slot()
    labels = [slot_summary(slot, i) + (" (this run)" if runstate.slot_attached == i else "") for i, slot in enumerate(slots)]
    select.innerHTML = "".join(
        f'<option value="{i}"{" selected" if i == chosen else ""}>{label}</option>' for i, label in enumerate(labels)
    )
    select.value = str(chosen)
    document.getElementById("slot-status").innerText = slot_status_text()
    document.getElementById("slot-load-button").disabled = slots[chosen] is None
    document.getElementById("slot-clear-button").disabled = slots[chosen] is None
