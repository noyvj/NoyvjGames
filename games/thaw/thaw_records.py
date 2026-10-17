"""Personal best and the climate archive (kept in localStorage, never in the save)."""

import json
import math

from js import document, setTimeout
from pyodide.ffi import create_proxy

import thaw_runstate as runstate
from thaw_bridge import _read_local_storage_item, _write_local_storage_item
from thaw_model import deg, region, region_b, region_c


# G19: a per-browser "best run" — the highest temperature_saved()
# (the hope-angle payoff stat, per CLAUDE.md) any session on this device
# has ever reached, persisted via localStorage. Deliberately NOT part of
# get_state()/the save-code system — this tracks the best this *browser*
# has ever seen across every session/save on this device, not one save's
# snapshot, the same distinction Canopy's B14/Tide's D13 personal-best
# features already draw.
PERSONAL_BEST_STORAGE_KEY = "thaw_personal_best_v1"

# Z6 (planning/TODO.md "Z. Games"): duration of the shared
# .personal-best-display.just-improved pulse (shared/personal-best.css) --
# matches the CSS animation's own length so the class is gone right as
# the pulse finishes. Same value Canopy uses for the same reason.
PERSONAL_BEST_BADGE_MS = 1800


def load_personal_best():
    """Reads the stored best temperature_saved(), defaulting to 0.0 if
    nothing is stored yet, storage is unavailable, or the stored value is
    malformed (e.g. hand-edited or from a future incompatible format)."""
    raw = _read_local_storage_item(PERSONAL_BEST_STORAGE_KEY)
    if not raw:
        return {"temperature_saved": 0.0, "region": None}
    try:
        data = json.loads(raw)
        region_label = data.get("region")
        if region_label not in ("A", "B", "C"):
            region_label = None
        return {
            "temperature_saved": float(data.get("temperature_saved", 0.0)),
            "region": region_label,
        }
    except (ValueError, TypeError, AttributeError):
        return {"temperature_saved": 0.0, "region": None}


personal_best = load_personal_best()


def _maybe_update_personal_best():
    """Called every render(); bumps + persists personal_best whenever the
    live session exceeds it."""
    # G22: consider all three player-managed regions and remember which
    # one earned the record.
    label, saved = max(
        (("A", region.temperature_saved()), ("B", region_b.temperature_saved()),
         ("C", region_c.temperature_saved())),
        key=lambda pair: pair[1],
    )
    if saved > personal_best["temperature_saved"]:
        personal_best["temperature_saved"] = saved
        personal_best["region"] = label
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))
        _flash_personal_best_badge()


def _flash_personal_best_badge():
    """Z6: briefly adds the shared .just-improved class (see
    shared/personal-best.css) right when a session beats its stored best.
    Same setTimeout+create_proxy shape as this game's other one-shot UI
    cues (e.g. the achievement toast)."""
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = document.getElementById("personal-best-display")
        if el is not None:
            el.classList.remove("just-improved")

    setTimeout(create_proxy(_unflash), PERSONAL_BEST_BADGE_MS)


def render_personal_best():
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    text = f"Personal best: {deg(personal_best['temperature_saved'])} saved"
    if personal_best.get("region"):
        text += f" (Region {personal_best['region']})"
    element.innerText = text


# ===========================================================================
# G23: the climate archive -- a persistent, per-browser record across many
# sessions of each player-managed region's best-ever performance (the most
# degrees saved, the furthest round reached, the highest dampening built).
# Same storage rules as personal_best above (localStorage, never part of
# get_state()/the save code, every read validated), but per region rather
# than one overall best. Region D is the unmanaged baseline and has no
# archive entry.
# ===========================================================================
ARCHIVE_STORAGE_KEY = "thaw_climate_archive_v1"
ARCHIVE_REGIONS = ("A", "B", "C")
ARCHIVE_MAX_ROUND = 1000000


def _blank_archive_entry():
    return {"best_saved": 0.0, "furthest_round": 1, "peak_dampening": 0.0}


def _clean_archive_entry(raw):
    """One region's stored record, with every field forced back into range
    (a malformed or hand-edited value falls back to that field's default)."""
    entry = _blank_archive_entry()
    if not isinstance(raw, dict):
        return entry
    saved = raw.get("best_saved")
    if isinstance(saved, (int, float)) and not isinstance(saved, bool) and math.isfinite(saved) and saved >= 0:
        entry["best_saved"] = float(saved)
    rounds = raw.get("furthest_round")
    if isinstance(rounds, int) and not isinstance(rounds, bool) and 1 <= rounds <= ARCHIVE_MAX_ROUND:
        entry["furthest_round"] = rounds
    damp = raw.get("peak_dampening")
    if (
        isinstance(damp, (int, float)) and not isinstance(damp, bool)
        and math.isfinite(damp) and 0 <= damp <= 1
    ):
        entry["peak_dampening"] = float(damp)
    return entry


def load_climate_archive():
    archive = {label: _blank_archive_entry() for label in ARCHIVE_REGIONS}
    raw = _read_local_storage_item(ARCHIVE_STORAGE_KEY)
    if not raw:
        return archive
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return archive
    if isinstance(data, dict):
        for label in ARCHIVE_REGIONS:
            archive[label] = _clean_archive_entry(data.get(label))
    return archive


climate_archive = load_climate_archive()


def _maybe_update_climate_archive():
    """Called every render(); raises and persists any record the live
    session has beaten."""
    changed = False
    for label, r in (("A", region), ("B", region_b), ("C", region_c)):
        entry = climate_archive[label]
        saved = max(0.0, r.temperature_saved())
        if saved > entry["best_saved"]:
            entry["best_saved"] = saved
            changed = True
        if r.round_number > entry["furthest_round"]:
            entry["furthest_round"] = min(r.round_number, ARCHIVE_MAX_ROUND)
            changed = True
        damp = r.feedback_dampening_fraction()
        if damp > entry["peak_dampening"]:
            entry["peak_dampening"] = damp
            changed = True
    if changed:
        _write_local_storage_item(ARCHIVE_STORAGE_KEY, json.dumps(climate_archive))


def render_climate_archive():
    toggle = document.getElementById("archive-toggle-button")
    panel = document.getElementById("archive-panel")
    toggle.innerText = "Hide climate archive" if runstate.archive_open else "\U0001F5C4\uFE0F Climate archive"
    panel.hidden = not runstate.archive_open
    for label in ARCHIVE_REGIONS:
        entry = climate_archive[label]
        document.getElementById(f"archive-row-{label.lower()}").innerText = (
            f"Region {label} \u2014 best {deg(entry['best_saved'])} saved, "
            f"furthest round {entry['furthest_round']}, "
            f"peak dampening {entry['peak_dampening'] * 100:.0f}%"
        )
