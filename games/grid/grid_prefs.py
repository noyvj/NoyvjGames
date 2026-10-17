"""Display preferences (C-12, C-19, GC-8, GC-9 ...) and the settings built on them: skipped confirmations, number format,
units and funds deltas.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import json

from js import document

import grid_runstate as runstate
from grid_rules import PLANT_LABEL, PLANT_TYPES, PREFS_STORAGE_KEY, PREF_CHOICES, PREF_DEFAULTS
from grid_career_data import _career_storage


def validate_prefs(raw):
    """Every key falls back to its default; unknown keys and wrong types are dropped."""
    out = dict(PREF_DEFAULTS)
    if not isinstance(raw, dict):
        return out
    for key, default in PREF_DEFAULTS.items():
        value = raw.get(key)
        if key in PREF_CHOICES:
            if value in PREF_CHOICES[key]:
                out[key] = value
        elif isinstance(value, bool):
            out[key] = value
    return out


def load_prefs_from_storage():
    storage = _career_storage()
    if storage is None:
        return dict(PREF_DEFAULTS)
    try:
        raw = storage.getItem(PREFS_STORAGE_KEY)
        return validate_prefs(json.loads(raw)) if raw else dict(PREF_DEFAULTS)
    except Exception:  # noqa: BLE001 -- private mode / corrupt JSON: defaults
        return dict(PREF_DEFAULTS)


def save_prefs_to_storage():
    storage = _career_storage()
    if storage is None:
        return
    try:
        storage.setItem(PREFS_STORAGE_KEY, json.dumps(runstate.prefs))
    except Exception:  # noqa: BLE001 -- a refused write must never break play
        pass


def set_pref(key, value):
    """Change one display preference. Returns False (and changes nothing) for an unknown key or a bad value."""
    if key not in PREF_DEFAULTS:
        return False
    if key in PREF_CHOICES:
        if value not in PREF_CHOICES[key]:
            return False
    elif not isinstance(value, bool):
        return False
    runstate.prefs[key] = value
    save_prefs_to_storage()
    return True


def reset_prefs():
    """Settings > Reset to Default also puts every display choice back (the page's own script resets text size
    and reduced motion)."""
    runstate.prefs = dict(PREF_DEFAULTS)
    save_prefs_to_storage()


# ---- C-22 / FY-24 skipped confirmations --------------------------------------------------------------------------
# Grid asks before two things only: finishing a run, and retiring the LAST unit of a plant type (any other retire is
# instant -- the owner's answer to FY-24 is "last plant only"). Each question has a "don't ask again" box kept by
# shared/confirm-dialog.js under confirm-dialog:skip:<id>. This lists which ones were switched off and lets the
# player switch them all back on. The career import and reset questions can never be skipped, so are not listed.
CONFIRM_SKIP_PREFIX = "confirm-dialog:skip:"
SKIPPABLE_CONFIRMATIONS = (
    [("grid-finish-run", "finishing a run")]
    + [(f"grid-retire-last-{t}", f"retiring the last {PLANT_LABEL[t]} unit") for t in PLANT_TYPES]
)


def skipped_confirmations():
    """Labels of the Grid questions the player has switched off with 'don't ask again'."""
    storage = _career_storage()
    if storage is None:
        return []
    out = []
    for action_id, label in SKIPPABLE_CONFIRMATIONS:
        try:
            if storage.getItem(CONFIRM_SKIP_PREFIX + action_id) == "true":
                out.append(label)
        except Exception:  # noqa: BLE001 -- blocked storage reads as "none skipped"
            return []
    return out


def reset_skipped_confirmations():
    """Switch every skipped Grid question back on. Returns how many were switched off before."""
    skipped = skipped_confirmations()
    storage = _career_storage()
    if storage is not None:
        for action_id, _label in SKIPPABLE_CONFIRMATIONS:
            try:
                storage.removeItem(CONFIRM_SKIP_PREFIX + action_id)
            except Exception:  # noqa: BLE001
                pass
    return len(skipped)


def confirmations_status_text():
    if runstate.confirm_reset_message:
        return runstate.confirm_reset_message
    skipped = skipped_confirmations()
    if not skipped:
        return "Grid asks before finishing a run and before retiring the last unit of a plant type. Nothing is switched off."
    return "Switched off with 'don't ask again': " + ", ".join(skipped) + "."


def render_confirmation_settings():
    skipped = skipped_confirmations()
    document.getElementById("confirm-reset-status").innerText = confirmations_status_text()
    document.getElementById("confirm-reset-button").disabled = not skipped


# ---- C-6 number format, units and funds deltas ---------------------------------------------------------------------
# Settings choose how the headline numbers read: full (default, exactly as before) or compact (1.2k, 3M), and whether
# demand and capacity carry a "MW" label (the game's capacity units are nameplate megawatts in spirit; the label is
# only a label, no rule changes). The funds change of the last round is also written as an arrow plus words.
def format_amount(value):
    """A number as the player chose to read it: whole numbers, or compact (1.2k, 3M) from 1,000 up."""
    n = float(value)
    if runstate.prefs["number_format"] == "compact" and abs(n) >= 1000:
        for scale, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1000, "k")):
            if abs(n) >= scale:
                text = f"{n / scale:.1f}".rstrip("0").rstrip(".")
                return f"{text}{suffix}"
    return f"{n:.0f}"


def format_demand(value):
    """Demand and capacity: untouched (the raw number) in full mode so the display is exactly what it always was."""
    if runstate.prefs["number_format"] == "compact":
        return format_amount(value)
    return f"{value}"


def unit_suffix():
    return " MW" if runstate.prefs["unit"] == "mw" else ""


def funds_delta_text():
    """Arrow plus words for the funds change of the last round; "" before any round and in the sandbox."""
    recap = runstate.state.last_round_recap
    if runstate.sandbox_active or not recap:
        return ""
    net = int(round(recap["net"]))
    if net > 0:
        return f"\u25B2 Funds up {format_amount(net)} last round"
    if net < 0:
        return f"\u25BC Funds down {format_amount(-net)} last round"
    return "\u25C6 Funds unchanged last round"


def render_number_settings():
    document.getElementById("pref-number-format").value = runstate.prefs["number_format"]
    document.getElementById("pref-unit").value = runstate.prefs["unit"]
    delta_el = document.getElementById("funds-delta-display")
    text = funds_delta_text()
    delta_el.innerText = text
    delta_el.hidden = not text
    delta_el.className = "funds-delta " + (
        "funds-delta--up" if text.startswith("\u25B2") else ("funds-delta--down" if text.startswith("\u25BC") else "funds-delta--flat")
    )
