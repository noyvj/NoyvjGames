"""Difficulty tiers with per-tier bests and the band helpers."""

import json
import re

from js import document

import drift_runstate as runstate
from drift_messages import arrival_stream_dot_count
from drift_model_region import region
from drift_pages import _read_local_storage_item, _write_local_storage_item
from drift_rules import (
    ACCELERATED_SEVERITY_MULTIPLIER, CRISIS_START_FUNDS, STARTING_FUNDS, _is_number, _small_int,
)
from drift_trendgraph import wellbeing_band
from drift_undo import _take_round_start_snapshot


# ===========================================================================
# Oct 11 batch 3: named difficulty tiers with per-tier bests (I-9, I-25), planner assist (I-3),
# confirm large moves (I-28), manual-save nudge (I-27), glossary popovers (I-29), Region Report (I-4),
# band-change confetti (GI-29). Everything here is a display, a record or advice: no number in a run changes
# unless the player flips one of the existing options (a tier only sets the options the game already had).
# ===========================================================================

BAND_ORDER = ["Struggling", "Managing", "Thriving", "Model Region"]


def band_rank(score):
    return BAND_ORDER.index(wellbeing_band(score))


def _today():
    import datetime  # noqa: PLC0415 -- stdlib, imported where used

    return datetime.date.today().isoformat()


def _now_ms():
    import time  # noqa: PLC0415

    return time.time() * 1000.0


# ---- I-9: named difficulty tiers -------------------------------------------------------------------
# A tier is only a name for a set of the three existing options (Crisis Calendar, Accelerated Severity,
# Crisis Start). The base game with every option off is the easiest the game gets, so it is called Gentle.
TIERS = [
    {"id": "gentle", "name": "Gentle", "calendar": False, "accelerated": False, "crisis": False},
    {"id": "standard", "name": "Standard", "calendar": True, "accelerated": False, "crisis": False},
    {"id": "rigorous", "name": "Rigorous", "calendar": True, "accelerated": True, "crisis": False},
    {"id": "demanding", "name": "Demanding", "calendar": True, "accelerated": True, "crisis": True},
]
TIER_BY_ID = {tier["id"]: tier for tier in TIERS}
TIER_BESTS_STORAGE_KEY = "drift_tier_bests_v1"


def tier_summary_line(tier_id):
    """One line saying what a tier changes, built from the game's own constants."""
    if tier_id == "gentle":
        return (
            f"The base game: no Crisis Calendar, normal pressure growth and a full {STARTING_FUNDS:.0f}-fund start. "
            "Every option below is off."
        )
    if tier_id == "standard":
        return (
            "Turns on the Crisis Calendar: fixed, telegraphed events (surges, a budget cut, a flood, a bumper harvest) "
            "and three Surge Tests. You can pay to brace for most of them."
        )
    if tier_id == "rigorous":
        return (
            f"Standard, plus Accelerated Severity: background pressure grows {ACCELERATED_SEVERITY_MULTIPLIER:.0f}x as fast, "
            "so arrivals climb sooner."
        )
    if tier_id == "demanding":
        return (
            f"Rigorous, plus Crisis Start: begin with {CRISIS_START_FUNDS:.0f} funds and a backlog already arrived. "
            "Chosen before round 1."
        )
    return "A mix of the options that does not match a named tier. Custom mixes do not update the tier bests."


def current_tier_id(region_state=None):
    """The named tier the region's three options spell out, or 'custom' for any other mix."""
    r = region if region_state is None else region_state
    for tier in TIERS:
        if (
            bool(r.calendar_enabled) == tier["calendar"]
            and bool(r.accelerated_severity_enabled) == tier["accelerated"]
            and bool(r.crisis_start_enabled) == tier["crisis"]
        ):
            return tier["id"]
    return "custom"


def tier_name(tier_id):
    return TIER_BY_ID[tier_id]["name"] if tier_id in TIER_BY_ID else "Custom mix"


def tier_available(tier_id):
    """A tier can be picked unless it needs a different Crisis Start after round 1 (that option is
    only choosable before the first round)."""
    tier = TIER_BY_ID.get(tier_id)
    if tier is None:
        return False
    return tier["crisis"] == region.crisis_start_enabled or region.can_toggle_crisis_start()


def _set_accelerated_severity(enabled):
    """The Accelerated Severity switch, with the first-time dot-density baseline the callout needs (I20)."""
    region.accelerated_severity_enabled = bool(enabled)
    if (
        region.accelerated_severity_enabled
        and region.severity_toggle_dot_baseline is None
        and not region.severity_density_callout_shown
    ):
        region.severity_toggle_dot_baseline = arrival_stream_dot_count(region.arrivals_this_round())


def apply_tier(tier_id):
    """Set the three options to a tier. Returns (ok, message). Nothing changes when it cannot be done."""
    tier = TIER_BY_ID.get(tier_id)
    if tier is None:
        return False, "That tier does not exist."
    if not tier_available(tier_id):
        return False, (
            f"{tier['name']} needs Crisis Start {'on' if tier['crisis'] else 'off'}, and that can only be changed "
            "before round 1. Start a new region to use it."
        )
    region.calendar_enabled = tier["calendar"]
    _set_accelerated_severity(tier["accelerated"])
    if tier["crisis"] != region.crisis_start_enabled:
        region.set_crisis_start(tier["crisis"])
        runstate.round_start_snapshot = _take_round_start_snapshot()
    return True, f"Difficulty set to {tier['name']}. " + tier_summary_line(tier_id)


def _clean_tier_bests(raw):
    """Stored per-tier bests with anything unreadable dropped: {tier id: {score, band, net_positive, date}}."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for tier_id in TIER_BY_ID:
        entry = raw.get(tier_id)
        if not isinstance(entry, dict):
            continue
        score = entry.get("score")
        if not _is_number(score) or score > 100:
            continue
        net = entry.get("net_positive")
        date = entry.get("date")
        out[tier_id] = {
            "score": float(score),
            "band": wellbeing_band(float(score)),
            "net_positive": net if _small_int(net, 1) else None,
            "date": date if isinstance(date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else "",
        }
    return out


def _load_tier_bests():
    raw = _read_local_storage_item(TIER_BESTS_STORAGE_KEY)
    if not raw:
        return {}
    try:
        return _clean_tier_bests(json.loads(raw))
    except (ValueError, TypeError):
        return {}


tier_bests = _load_tier_bests()


def _maybe_update_tier_best():
    """Called every render. A named tier's best moves up when a round has been played, the run is not assisted
    and the wellbeing score or the net-positive round beats what that tier holds."""
    if runstate.assisted_run or region.round_number <= 1:
        return
    tier_id = current_tier_id()
    if tier_id == "custom":
        return
    score = region.wellbeing_score()
    entry = tier_bests.get(tier_id)
    changed = False
    if entry is None:
        entry = {"score": score, "band": wellbeing_band(score), "net_positive": region.net_positive_round, "date": _today()}
        tier_bests[tier_id] = entry
        changed = True
    else:
        if score > entry["score"]:
            entry["score"] = score
            entry["band"] = wellbeing_band(score)
            changed = True
        net = region.net_positive_round
        if net is not None and (entry["net_positive"] is None or net < entry["net_positive"]):
            entry["net_positive"] = net
            changed = True
        if changed:
            entry["date"] = _today()
    if changed:
        _write_local_storage_item(TIER_BESTS_STORAGE_KEY, json.dumps(tier_bests))


def tier_best_table_html():
    head = "<tr><th>Tier</th><th>Best band</th><th>Best wellbeing</th><th>Fastest net-positive</th><th>Date</th></tr>"
    rows = []
    for tier in TIERS:
        entry = tier_bests.get(tier["id"])
        if entry is None:
            rows.append(f"<tr><td>{tier['name']}</td><td colspan=\"4\">not played yet</td></tr>")
            continue
        net = f"round {entry['net_positive']}" if entry["net_positive"] is not None else "not yet"
        rows.append(
            f"<tr><td>{tier['name']}</td><td>{entry['band']}</td><td>{entry['score']:.0f}</td>"
            f"<td>{net}</td><td>{entry['date'] or '-'}</td></tr>"
        )
    return f"<table class=\"ledger-table tier-table\"><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def render_tier_panel():
    tier_id = current_tier_id()
    label = f"Difficulty tier: {tier_name(tier_id)}" + (" (assisted run)" if runstate.assisted_run else "")
    document.getElementById("tier-summary").innerText = label
    document.getElementById("tier-line").innerText = tier_summary_line(tier_id)
    for tier in TIERS:
        button = document.getElementById(f"tier-{tier['id']}-button")
        button.setAttribute("aria-pressed", "true" if tier["id"] == tier_id else "false")
        button.disabled = not tier_available(tier["id"])
        button.title = tier_summary_line(tier["id"])
        if tier["id"] == tier_id:
            button.classList.add("active")
        else:
            button.classList.remove("active")
    document.getElementById("tier-note").innerText = runstate.tier_note_text
    document.getElementById("tier-best-table").innerHTML = tier_best_table_html()
    document.getElementById("tier-best-note").innerText = (
        "Bests are kept in this browser. Assisted runs and custom mixes do not update them."
        if runstate.assisted_run is False
        else "This run is assisted, so it does not update any bests."
    )
