"""The copyable settings code: export, decode, import and re-apply."""

import base64
import json

import thaw_runstate as runstate
from thaw_bridge import _num, _read_local_storage_item, _write_local_storage_item
from thaw_presets import CONFIRM_THRESHOLDS, set_confirm_threshold
from thaw_readouts import set_temp_unit
from thaw_records import (
    ARCHIVE_REGIONS, ARCHIVE_STORAGE_KEY, PERSONAL_BEST_STORAGE_KEY, _clean_archive_entry, climate_archive,
    personal_best,
)
from thaw_rules import TEMP_UNITS


# ===========================================================================
# G-25: settings export and import. "Copy settings code" packs the local preferences (text size,
# the display switches, the temperature unit, the big-spend threshold) and the personal bests
# (overall record and the climate archive) into one short text code; pasting it in on another device
# restores them, no account needed. The code is plain, checksummed and fully validated on the way in
# (anything unreadable is skipped and named), and bests merge by keeping the HIGHER of the two so an
# import can never lower a record. Not included: the saved game itself (use the save widget), field
# notes, the pace line, and the site-wide lite mode (it has its own switch on the hub).
# ===========================================================================
SETTINGS_CODE_PREFIX = "THAW1-"
SETTINGS_CODE_MAX = 4000
SETTING_FLAG_KEYS = (
    "thaw-reduced-motion", "thaw-blindfold", "thaw-graph-patterns", "thaw-high-contrast",
    "thaw-tip-shake", "thaw-hide-pace", "thaw-hide-mascots", "thaw-instant-digits",
)
TEXT_SCALE_KEY = "thaw-text-scale"
TEXT_SCALE_MIN, TEXT_SCALE_MAX = 0.85, 1.5


def _checksum(raw_bytes):
    return f"{sum(raw_bytes) % 65521:04x}"


def settings_snapshot():
    """The exportable settings as a plain dict (only what is actually stored on this device)."""
    snap = {}
    scale = _read_local_storage_item(TEXT_SCALE_KEY)
    try:
        if scale is not None and TEXT_SCALE_MIN <= float(scale) <= TEXT_SCALE_MAX:
            snap["t"] = round(float(scale), 2)
    except (TypeError, ValueError):
        pass
    flags = {}
    for key in SETTING_FLAG_KEYS:
        value = _read_local_storage_item(key)
        if value in ("true", "false"):
            flags[key] = value == "true"
    if flags:
        snap["f"] = flags
    snap["u"] = runstate.temp_unit
    snap["c"] = runstate.confirm_threshold
    snap["pb"] = dict(personal_best)
    snap["ar"] = {label: dict(entry) for label, entry in climate_archive.items()}
    return snap


def export_settings_code():
    raw = json.dumps(settings_snapshot(), separators=(",", ":"), sort_keys=True).encode("utf-8")
    return SETTINGS_CODE_PREFIX + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") + "." + _checksum(raw)


def decode_settings_code(code):
    """The dict inside a settings code, or None when it is not a Thaw settings code (wrong prefix,
    bad length, bad base64, checksum mismatch, not an object)."""
    if not isinstance(code, str):
        return None
    code = code.strip()
    if not code.startswith(SETTINGS_CODE_PREFIX) or len(code) > SETTINGS_CODE_MAX or "." not in code:
        return None
    body, _dot, check = code[len(SETTINGS_CODE_PREFIX):].rpartition(".")
    try:
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, TypeError):
        return None
    if _checksum(raw) != check or not isinstance(data, dict):
        return None
    return data


def import_settings_code(code):
    """Applies a settings code. Returns (restored item names, skipped item names), or None when the code
    is not readable at all."""
    data = decode_settings_code(code)
    if data is None:
        return None
    restored, skipped = [], []
    scale = data.get("t")
    if "t" in data:
        if _num(scale, TEXT_SCALE_MIN, TEXT_SCALE_MAX):
            _write_local_storage_item(TEXT_SCALE_KEY, str(round(float(scale), 2)))
            restored.append("text size")
        else:
            skipped.append("text size")
    flags = data.get("f")
    if "f" in data:
        if isinstance(flags, dict):
            count = 0
            for key, value in flags.items():
                if key in SETTING_FLAG_KEYS and isinstance(value, bool):
                    _write_local_storage_item(key, "true" if value else "false")
                    count += 1
                else:
                    skipped.append("a display switch")
            if count:
                restored.append("display switches")
        else:
            skipped.append("display switches")
    if "u" in data:
        if data["u"] in TEMP_UNITS:
            set_temp_unit(data["u"])
            restored.append("temperature unit")
        else:
            skipped.append("temperature unit")
    if "c" in data:
        value = data["c"]
        if isinstance(value, int) and not isinstance(value, bool) and value in CONFIRM_THRESHOLDS:
            set_confirm_threshold(value)
            restored.append("big-spend threshold")
        else:
            skipped.append("big-spend threshold")
    if "pb" in data:
        pb = data["pb"]
        saved = pb.get("temperature_saved") if isinstance(pb, dict) else None
        if _num(saved, 0, 1000000000):
            if saved > personal_best["temperature_saved"]:
                label = pb.get("region") if pb.get("region") in ("A", "B", "C") else None
                personal_best["temperature_saved"] = float(saved)
                personal_best["region"] = label
                _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))
            restored.append("personal best")
        else:
            skipped.append("personal best")
    if "ar" in data:
        archive = data["ar"]
        if isinstance(archive, dict):
            for label in ARCHIVE_REGIONS:
                incoming = _clean_archive_entry(archive.get(label))
                mine = climate_archive[label]
                for field in mine:
                    mine[field] = max(mine[field], incoming[field])
            _write_local_storage_item(ARCHIVE_STORAGE_KEY, json.dumps(climate_archive))
            restored.append("climate archive")
        else:
            skipped.append("climate archive")
    _reapply_page_settings()
    return restored, skipped


def _reapply_page_settings():
    """Asks settings.js to re-read what was just stored (text size, switches) so the page and its
    checkboxes show it at once; harmless where that script is absent (the tests)."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(getattr(window, "ThawSettings", None), "reapply", None)
    if hook is not None:
        hook()


def settings_code_message(result):
    if result is None:
        return "That does not look like a Thaw settings code (it should start with THAW1- and be copied whole)."
    restored, skipped = result
    text = "Restored: " + (", ".join(restored) if restored else "nothing") + "."
    if skipped:
        text += " Skipped (unreadable): " + ", ".join(sorted(set(skipped))) + "."
    return text + " Bests keep the higher of the two."
