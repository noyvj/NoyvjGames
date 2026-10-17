"""get_state() and the steward summary, plus the developer history readout."""

import json

from js import document

import thaw_runstate as runstate
from thaw_achievements import achievement_ids_earned
from thaw_graphs import graph_indexes
from thaw_mechanics import run_unranked
from thaw_model import region, region_b, region_c, region_d
from thaw_saveparts import _region_state_dict
from thaw_sciencelog import science_log


def history_readout_text():
    """G-11: the developer line (shown with ?debug=1): how long the histories are, how many points
    the graphs really draw and roughly how big the save is."""
    stored = len(region.temperature_history)
    drawn = len(graph_indexes(region.temperature_history))
    size = len(json.dumps(get_state(), separators=(",", ":")))
    return (
        f"History: {stored} rounds stored per region, graphs draw {drawn} points each; "
        f"save about {size / 1024:.1f} KB."
    )


def render_history_readout():
    element = document.getElementById("history-readout")
    if not element.hidden:  # only measured when the developer line is on show
        element.innerText = history_readout_text()


def get_state():
    """Return every module-level mutable global needed to fully
    reconstruct the game — all four regions (primary + Region B/C/D) plus
    the info-page toggle and the two achievement-only flags — as a plain,
    JSON-serialisable dict. No custom objects, no functions: just numbers,
    strings, lists, dicts, booleans.

    "achievements_earned" is a write-only projection
    (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always freshly recomputed here,
    never read back in load_state()."""
    state = {
        "region": _region_state_dict(region),
        "region_b": _region_state_dict(region_b),
        "region_c": _region_state_dict(region_c),
        "region_d": _region_state_dict(region_d),
        "info_page_open": runstate.info_page_open,
        "worst_case_region_revealed": runstate.worst_case_region_revealed,
        "preset_used_ever": runstate.preset_used_ever,
        "worst_case_intro_seen": runstate.worst_case_intro_seen,
        "science_log": [dict(entry) for entry in science_log],
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
    }
    # G27: the forecast record is written only once a forecast has been scored.
    if runstate.forecast_total > 0:
        state["forecast"] = {"total": runstate.forecast_total, "hits": runstate.forecast_hits}
        if runstate.forecast_miss_total > 0:
            state["forecast"]["miss"] = round(runstate.forecast_miss_total, 4)
    # GG-23 / G-20: written only when on / filled.
    if runstate.hard_mode:
        state["hard_mode"] = True
    if runstate.custom_preset:
        state["custom_preset"] = dict(runstate.custom_preset)
    # G3: the carbon bank is written only when it holds credits.
    if runstate.carbon_bank > 0:
        state["carbon_bank"] = runstate.carbon_bank
    # G29: only the non-default framing is written.
    if runstate.framing != "regional":
        state["framing"] = runstate.framing
    # G9: only written when the long game is on.
    if runstate.long_game:
        state["long_game"] = True
    # GG-2: only written when Hold the Line is on; the result only once the run is over.
    if runstate.hold_the_line:
        state["hold_the_line"] = True
        if runstate.run_over and runstate.run_result is not None:
            state["run"] = dict(runstate.run_result)
    # GG-5 / GG-27: only written once a convoy or a balance bonus has happened.
    if runstate.convoys_sent > 0:
        state["routing"] = {"convoys": runstate.convoys_sent, "tax_lost": runstate.convoy_tax_lost}
    if runstate.balance_bonuses > 0:
        state["balance_bonuses"] = runstate.balance_bonuses
    # GG-17: written only once the run's one rewind has been spent.
    if runstate.undo_used:
        state["undo_used"] = True
    # GG-22: written only once a crate has arrived.
    if runstate.crates_delivered > 0:
        state["crates"] = {"delivered": runstate.crates_delivered, "opened": runstate.crates_opened}
    # FY-32: write-only marker for the shared stats; never read back (load_state recomputes it).
    if run_unranked():
        state["unranked"] = True
    return state


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    return [
        {"label": "Warming held back", "value": round(max(0.0, region.temperature_saved()), 1), "unit": "\u00b0C"},
        {"label": "Warming pulled back by restoration", "value": round(max(0.0, region.restored_total), 1), "unit": "\u00b0C"},
        {"label": "Rounds played", "value": max(0, int(region.round_number) - 1), "unit": ""},
    ]
