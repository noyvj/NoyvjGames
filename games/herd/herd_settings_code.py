"""Settings export and import code (F-25).
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import json

import export_progress
from js import document

import herd_runstate as runstate
from herd_rules import BASE_COUPLING_RATIO, MIN_COUPLING_RATIO, RULE_SPECS
from herd_util import _is_finite_number, _read_local_storage_item, _write_local_storage_item
from herd_model import clean_rule_value, rules_are_custom
from herd_visuals import RECORD_COUPLING_RATIO_STORAGE_KEY
from herd_rules_ui import set_rule
from herd_pins import PINS_STORAGE_KEY, clean_pins


# ===========================================================================
# Round-7 batch (planning/TODO.md "GF + F. Herd").
# ===========================================================================

# ---- F-25 settings export / import -------------------------------------------------------------
# One short code carries every setting this browser keeps for Herd (text size, motion, the display
# switches, play style, purchase check, tactile and celebration switches, ranch rules, pinned stats)
# plus the personal best coupling ratio, so a second device can be set up in one paste. It is a
# structural bundle that REPLACES local settings (shared/export_progress.py, the Aftermath shape); the
# personal best is the one exception, where the better of the two ratios is kept so an old code can
# never undo a record. The shared lite-mode switch has its own account sync and is not in the code.
SETTINGS_CODE_PREFIX = "HERDSET1:"
SETTINGS_TEXT_SCALE_KEY = "herd-text-scale"
SETTINGS_BOOL_KEYS = (
    "herd-reduced-motion", "herd-high-contrast", "herd-dyslexia-font", "herd-hatch-patterns",
    "herd-tactile", "herd-cha-ching",
)
SETTINGS_CHOICE_KEYS = {
    "herd-confirm-percent": ("0", "25", "50", "75"),
    "herd-profile": ("beginner", "standard", "expert"),
}
SETTINGS_TEXT_SCALE_RANGE = (0.85, 1.5)


def _clean_setting(key, value):
    """The stored string for one UI setting from untrusted data, or None when it is not usable."""
    if key == SETTINGS_TEXT_SCALE_KEY:
        if not _is_finite_number(value):
            return None
        low, high = SETTINGS_TEXT_SCALE_RANGE
        return None if value < low or value > high else str(round(float(value), 2))
    if key in SETTINGS_BOOL_KEYS:
        return value if value in ("true", "false") else None
    if key in SETTINGS_CHOICE_KEYS:
        return value if value in SETTINGS_CHOICE_KEYS[key] else None
    return None


def settings_snapshot():
    """Everything the settings code carries, as a plain dict (only what this browser actually has set)."""
    saved = {}
    raw_scale = _read_local_storage_item(SETTINGS_TEXT_SCALE_KEY)
    try:
        cleaned = _clean_setting(SETTINGS_TEXT_SCALE_KEY, float(raw_scale)) if raw_scale else None
    except (TypeError, ValueError):
        cleaned = None
    if cleaned is not None:
        saved[SETTINGS_TEXT_SCALE_KEY] = float(cleaned)
    for key in list(SETTINGS_BOOL_KEYS) + list(SETTINGS_CHOICE_KEYS):
        cleaned = _clean_setting(key, _read_local_storage_item(key))
        if cleaned is not None:
            saved[key] = cleaned
    payload = {"v": 1, "s": saved, "rules": {n: v for n, v in runstate.ranch_rules.items()}}
    if runstate.pinned_stats:
        payload["pins"] = list(runstate.pinned_stats)
    if runstate.record_coupling_ratio is not None:
        payload["record"] = round(runstate.record_coupling_ratio, 4)
    return payload


def export_settings_code():
    return export_progress.encode_progress_code(settings_snapshot(), SETTINGS_CODE_PREFIX)


def import_settings_code(code):
    """Applies a settings code. Returns (True, plain summary) or (False, plain reason); nothing is
    changed unless the code is sound and carries at least one usable value."""
    if runstate.sandbox_active:
        return False, "Leave the practice sandbox first; settings are not changed from inside it."
    ok, payload = export_progress.decode_progress_code(
        code, SETTINGS_CODE_PREFIX,
        "That does not look like a Herd settings code. It should start with " + SETTINGS_CODE_PREFIX + " and be copied whole.",
    )
    if not ok:
        return False, payload
    if payload.get("v") != 1:
        return False, "This settings code comes from a different version of Herd, so it was not used."
    found = payload.get("s")
    found = found if isinstance(found, dict) else {}
    settings = {}
    for key, value in found.items():
        if key == SETTINGS_TEXT_SCALE_KEY or key in SETTINGS_BOOL_KEYS or key in SETTINGS_CHOICE_KEYS:
            cleaned = _clean_setting(key, value)
            if cleaned is not None:
                settings[key] = cleaned
    rules = {}
    if isinstance(payload.get("rules"), dict):
        for name in RULE_SPECS:
            cleaned = clean_rule_value(name, payload["rules"].get(name))
            if cleaned is not None:
                rules[name] = cleaned
    pins = clean_pins(payload.get("pins")) if "pins" in payload else None
    record = payload.get("record")
    record = float(record) if _is_finite_number(record) and MIN_COUPLING_RATIO <= record < BASE_COUPLING_RATIO else None
    if not settings and not rules and pins is None and record is None:
        return False, "That code is a valid Herd settings code but holds nothing this version can use."
    for key, value in settings.items():
        _write_local_storage_item(key, value)
    custom_before = rules_are_custom()
    for name, value in rules.items():
        set_rule(name, value)
    if pins is not None:
        runstate.pinned_stats = pins
        _write_local_storage_item(PINS_STORAGE_KEY, json.dumps(runstate.pinned_stats))
    if record is not None and (runstate.record_coupling_ratio is None or record < runstate.record_coupling_ratio - 1e-9):
        runstate.record_coupling_ratio = record
        _write_local_storage_item(RECORD_COUPLING_RATIO_STORAGE_KEY, json.dumps(runstate.record_coupling_ratio))
    _reload_page_settings()
    summary = f"Restored {len(settings)} display and play settings"
    if rules:
        summary += ", the ranch rules"
    if pins is not None:
        summary += ", the pinned stats"
    if record is not None:
        summary += ", the best coupling ratio"
    summary += "."
    if rules_are_custom() and not custom_before:
        summary += " The code carries custom ranch rules, so this run is now unranked."
    return True, summary


def _reload_page_settings():
    """Asks settings.js to bring its controls and data attributes in line with localStorage."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    settings = getattr(window, "HerdSettings", None)
    if settings is not None:
        settings.reloadFromStorage()


def _copy_to_clipboard(text, status_id):
    try:
        from js import window  # noqa: PLC0415
    except ImportError:
        return False
    settings = getattr(window, "HerdSettings", None)
    return bool(settings is not None and settings.copyText(text, status_id))


def _set_settings_code_status(text):
    runstate.settings_code_status_text = text
    document.getElementById("settings-code-status").innerText = text


def on_settings_export(event=None):
    code = export_settings_code()
    document.getElementById("settings-code-box").value = code
    copying = _copy_to_clipboard(code, "settings-code-status")
    _set_settings_code_status(
        "Settings code made" + (" (copying it now)" if copying else "") + ". If it was not copied, select the box and copy it yourself."
    )
